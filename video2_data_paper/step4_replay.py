"""Video 2, Step 4: Replay your recording through the strategy. Hours of market in seconds.

    python video2_data_paper/step4_replay.py <slug>
    python video2_data_paper/step4_replay.py <slug> --fair 0.60

Same strategy and same pessimistic fills as the live paper bot (step 5).
A replay cannot show how the market would have reacted to your orders. Treat it as a filter:
a strategy that loses here is dead. One that wins here has only earned a live paper test.
"""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

import pandas as pd  # noqa: E402

from pmus.paper_broker import PaperBroker  # noqa: E402
from pmus.recording import PARQUET  # noqa: E402
from pmus.strategy import Settings, decide  # noqa: E402


def replay(slug: str, s: Settings, quiet: bool = True) -> PaperBroker:
    books = pd.read_parquet(PARQUET / slug / "books.parquet").dropna(subset=["bid", "ask"])
    broker = PaperBroker(fee_rate=s.fee_rate, log_path="", quiet=quiet)
    bid = None
    for row in books.itertuples():
        bid, ask = row.bid, row.ask
        if broker.total_pnl(bid) <= -s.max_loss:
            print(f"KILL SWITCH at {row.time}: loss limit hit")
            break
        broker.clock = str(row.time)
        action, _ = decide(s, bid, ask, broker.position)
        if action == "BUY":
            broker.buy(s.size, ask, row.ask_qty)
        elif action == "SELL":
            broker.sell(s.size, bid, row.bid_qty)

    buys = sum(t["side"] == "BUY" for t in broker.trades)
    total = broker.total_pnl(bid) if bid is not None else 0.0
    print(f"\nReplay of {slug} with fair value {s.fair:.2f}")
    print(f"  snapshots replayed   {len(books):,}")
    print(f"  paper fills          {len(broker.trades)} ({buys} buys, {len(broker.trades) - buys} sells)")
    print(f"  fees paid            ${broker.fees_paid:.2f}")
    print(f"  realized P&L         ${broker.realized_pnl:+.2f}")
    print(f"  open position        {broker.position:g} contracts, worth ${broker.unrealized_pnl(bid):+.2f} at the bid")
    print(f"  total P&L            ${total:+.2f}")
    return broker


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--fair", type=float, help="override FAIR_VALUE from .env")
    ap.add_argument("--show-fills", action="store_true")
    a = ap.parse_args()
    settings = Settings.from_env()
    if a.fair is not None:
        settings = replace(settings, fair=a.fair)
    replay(a.slug, settings, quiet=not a.show_fills)
