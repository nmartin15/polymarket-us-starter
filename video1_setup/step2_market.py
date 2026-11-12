"""Video 1, Step 2: Read one market before you ever trade it. No API key needed.

    python video1_setup/step2_market.py <market-slug>

Shows what the market is, which side is YES, the price step and smallest order,
the order book, and what a trade would cost in fees.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from pmus.config import public_client, setting  # noqa: E402
from pmus.markets import best, describe, market_of  # noqa: E402
from pmus.money import num, taker_fee  # noqa: E402


def show(c, slug: str) -> None:
    m = market_of(c.markets.retrieve_by_slug(slug))
    print()
    for label, value in describe(m):
        print(f"  {label:<38} {value}")
    rules = (m.get("description") or "").strip()
    print(f"\n  Rules: {rules[:400]}{'...' if len(rules) > 400 else ''}")

    book = c.markets.book(slug).get("marketData", {})
    bid, bid_qty, ask, ask_qty = best(book)
    print(f"\n  Market state: {book.get('state')}")
    print(f"  Best bid {bid}  x {bid_qty:g}      Best ask {ask}  x {ask_qty:g}")
    if bid is not None and ask is not None:
        print(f"  Spread: {ask - bid:.3f}  <- you pay this every time you cross in and back out")

    print("\n  BID QTY     BID | ASK     ASK QTY")
    bids, offers = book.get("bids") or [], book.get("offers") or []
    for i in range(min(5, max(len(bids), len(offers)))):
        b = bids[i] if i < len(bids) else None
        o = offers[i] if i < len(offers) else None
        print(f"  {num(b['qty']) if b else '':>7} {num(b['px']) if b else '':>7} | "
              f"{num(o['px']) if o else '':<7} {num(o['qty']) if o else ''}")

    if ask is not None:
        theta = float(setting("TAKER_FEE_RATE", "0.095"))
        print(f"\n  Taker fee to buy 100 YES at {ask}, at your {theta:.2%} tier: ${taker_fee(theta, 100, ask):.2f}")
        print("  (Resting orders that get filled as a maker pay no fee.)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python video1_setup/step2_market.py <market-slug>")
    client = public_client()
    try:
        show(client, sys.argv[1])
    finally:
        client.close()
