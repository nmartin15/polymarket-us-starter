"""Video 3, Step 2: Live paper trading on NautilusTrader, fed by Polymarket US.

    python video3_nautilus/step2_live_paper.py              # taker
    python video3_nautilus/step2_live_paper.py --maker

Every few seconds this pulls the live Polymarket US order book, hands it to the Nautilus
engine, and lets the strategy react. Orders go to Nautilus's simulated exchange only.
There is no code path here that can reach your real account.

Uses MARKET_SLUG and FAIR_VALUE from .env. Each book is also recorded for later backtests.
Stop it any time: Ctrl+C, or create a file named STOP in the repo root.
"""

import argparse
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder
sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.filterwarnings("ignore")  # hide library deprecation noise

import pandas as pd  # noqa: E402

from pmus.config import ROOT, public_client, setting  # noqa: E402
from pmus.recording import append_event, levels  # noqa: E402
from step1_backtest import STARTING_CASH, build_engine, show, strategy_config, summarize  # noqa: E402
from strategies import FairValueMaker, FairValueTaker  # noqa: E402
from us_bridge import make_instrument, snapshot_deltas  # noqa: E402

STOP_FILE = ROOT / "STOP"


def fetch(client, slug: str, record: bool):
    """One live book -> (timestamp, sorted bid levels, sorted ask levels, market state)."""
    book = client.markets.book(slug)["marketData"]
    ts = time.time_ns()
    if record:
        append_event(slug, "book", book, ts)
    bid_px, bid_qty = levels(book.get("bids"))
    ask_px, ask_qty = levels(book.get("offers"))
    return ts, sorted(zip(bid_px, bid_qty), reverse=True), sorted(zip(ask_px, ask_qty)), book.get("state")


def run(client, slug: str, strategy_cls, fair: float, poll: float, max_loss: float,
        max_loops: int | None = None, record: bool = True) -> dict:
    # The first book tells us the market's tick size, which the instrument needs.
    ts, bids, asks, _ = fetch(client, slug, record)
    first = pd.DataFrame([{"ts": ts, "bid_prices": [p for p, _ in bids], "bid_sizes": [q for _, q in bids],
                           "ask_prices": [p for p, _ in asks], "ask_sizes": [q for _, q in asks]}])
    instrument = make_instrument(slug, first, float(setting("TAKER_FEE_RATE", "0.095")))
    engine = build_engine(instrument)
    engine.add_strategy(strategy_cls(strategy_config(instrument, fair)))
    print(f"NAUTILUS PAPER MODE. {strategy_cls.__name__} on {slug}, fair value {fair:.2f}. No real orders.\n")

    loops, last_bid = 0, None
    try:
        while max_loops is None or loops < max_loops:
            loops += 1
            deltas = snapshot_deltas(instrument, ts, [p for p, _ in bids], [q for _, q in bids],
                                     [p for p, _ in asks], [q for _, q in asks])
            if deltas is not None:
                engine.add_data([deltas])
                engine.run(streaming=True)      # process this update, then wait for the next
                engine.clear_data()
            last_bid = bids[0][0] if bids else last_bid
            r = summarize(engine, instrument, strategy_cls.__name__, last_bid or 0.0)
            print(f"bid {bids[0][0] if bids else None}  ask {asks[0][0] if asks else None}  "
                  f"pos {r['open position']:g}  fills {r['orders filled']}  P&L {r['total P&L']:+.2f}")

            if STOP_FILE.exists():
                print("KILL SWITCH: STOP file found")
                break
            if r["total P&L"] <= -max_loss:
                print(f"KILL SWITCH: loss limit hit ({r['total P&L']:.2f})")
                break
            time.sleep(poll)
            while True:
                try:
                    ts, bids, asks, state = fetch(client, slug, record)
                    break
                except Exception as e:  # network blip: wait and retry, don't crash
                    print(f"data error: {e}; retrying")
                    time.sleep(max(poll, 1))
            if state and state != "MARKET_STATE_OPEN":
                print(f"market state {state}; standing down")
                break
    except KeyboardInterrupt:
        print("\nStopped by you.")
    engine.end()
    result = summarize(engine, instrument, strategy_cls.__name__, last_bid or 0.0)
    engine.dispose()
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--maker", action="store_true", help="rest quotes instead of crossing the spread")
    a = ap.parse_args()
    slug = setting("MARKET_SLUG", "")
    if not slug or "paste" in slug:
        raise SystemExit("Set MARKET_SLUG in .env (find one with video1_setup/step1_market_data.py).")
    c = public_client()
    try:
        res = run(c, slug, FairValueMaker if a.maker else FairValueTaker,
                  fair=float(setting("FAIR_VALUE", "0.50")), poll=float(setting("POLL_SECONDS", "10")),
                  max_loss=float(setting("MAX_DAILY_LOSS", "25")))
    finally:
        c.close()
    print(f"\nSession summary (${STARTING_CASH:,} paper cash)\n")
    show([res])
