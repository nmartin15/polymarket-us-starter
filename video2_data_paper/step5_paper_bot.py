"""Video 2, Step 5: The live paper bot. Real prices, fake money. It NEVER sends an order.

    python video2_data_paper/step5_paper_bot.py

Set MARKET_SLUG and FAIR_VALUE in .env first. Every book it sees is also recorded,
so each paper session grows your dataset for replays and for video 3.

Stop it any time: Ctrl+C, or create a file named STOP in the repo root.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from pmus.config import ROOT, public_client  # noqa: E402
from pmus.paper_broker import PaperBroker  # noqa: E402
from pmus.recording import append_event, levels  # noqa: E402
from pmus.strategy import Settings, decide  # noqa: E402

STOP_FILE = ROOT / "STOP"


def top_of_book(book: dict):
    """Returns (bid, bid_qty, ask, ask_qty). Prices are 0 to 1."""
    bid_px, bid_qty = levels(book.get("bids"))
    ask_px, ask_qty = levels(book.get("offers"))
    bids, asks = sorted(zip(bid_px, bid_qty), reverse=True), sorted(zip(ask_px, ask_qty))
    return (bids[0][0] if bids else None, bids[0][1] if bids else 0,
            asks[0][0] if asks else None, asks[0][1] if asks else 0)


def kill_switch(broker: PaperBroker, bid, s: Settings) -> str | None:
    if STOP_FILE.exists():
        return "STOP file found"
    if bid is not None and broker.total_pnl(bid) <= -s.max_loss:
        return f"daily loss limit hit ({broker.total_pnl(bid):.2f})"
    return None


def run(client, s: Settings, max_loops: int | None = None, record: bool = True) -> PaperBroker:
    if not s.slug or "paste" in s.slug:
        raise SystemExit("Set MARKET_SLUG in .env (find one with video1_setup/step1_market_data.py).")
    broker = PaperBroker(fee_rate=s.fee_rate, log_path=str(ROOT / "paper_trades.csv"))
    print(f"PAPER MODE. Market {s.slug}. Fair value {s.fair:.2f}. No real orders will be sent.\n")
    loops = 0
    while max_loops is None or loops < max_loops:
        loops += 1
        try:
            book = client.markets.book(s.slug)["marketData"]
        except Exception as e:  # network blip: wait and retry, don't crash
            print(f"data error: {e}; retrying")
            time.sleep(s.poll)
            continue
        if record:
            append_event(s.slug, "book", book)

        state = book.get("state")
        if state and state != "MARKET_STATE_OPEN":
            print(f"market state {state}; standing down")
            break

        bid, bid_qty, ask, ask_qty = top_of_book(book)
        reason = kill_switch(broker, bid, s)
        if reason:
            print(f"KILL SWITCH: {reason}")
            break

        action, why = decide(s, bid, ask, broker.position)
        mark = broker.total_pnl(bid) if bid is not None else 0
        print(f"bid {bid}  ask {ask}  pos {broker.position:g}  P&L {mark:+.2f}  -> {action or 'hold'} ({why})")
        if action == "BUY":
            broker.buy(s.size, ask, ask_qty)
        elif action == "SELL":
            broker.sell(s.size, bid, bid_qty)
        time.sleep(s.poll)

    print(f"\nDone. Position {broker.position:g}, realized {broker.realized_pnl:+.2f}, fees {broker.fees_paid:.2f}")
    print(f"Every paper trade is in {broker.log_path}")
    return broker


if __name__ == "__main__":
    c = public_client()
    try:
        run(c, Settings.from_env())
    except KeyboardInterrupt:
        print("\nStopped by you.")
    finally:
        c.close()
