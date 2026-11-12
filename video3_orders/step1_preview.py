"""Video 3, Step 1: Build an order and preview it. Nothing is sent to the market.

    python video3_orders/step1_preview.py <market-slug> buy-yes 0.45 1
    python video3_orders/step1_preview.py <market-slug> buy-no  0.17 1

Arguments: market, action (buy-yes, sell-yes, buy-no, sell-no), price, contracts.
Price is the price of the side you're trading: for buy-no 0.17, you pay 17 cents for NO.
The script converts it to the YES price the API expects, checks it against the market's
price step and smallest order, and asks Polymarket to preview it.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from pmus.config import private_client, setting  # noqa: E402
from pmus.markets import best, market_of, min_qty, tick_size  # noqa: E402
from pmus.money import taker_fee  # noqa: E402
from pmus.orders import Ticket, cash_effect  # noqa: E402


def build(c, argv: list[str]) -> tuple[Ticket, dict]:
    if len(argv) != 4:
        sys.exit(__doc__)
    t = Ticket(slug=argv[0], action=argv[1], price=float(argv[2]), qty=float(argv[3]))
    m = market_of(c.markets.retrieve_by_slug(t.slug))
    problems = t.problems(tick_size(m), min_qty(m))
    if problems:
        sys.exit("Fix this first:\n  " + "\n  ".join(problems))
    return t, m


def explain(c, t: Ticket) -> None:
    bid, _, ask, _ = best(c.markets.book(t.slug).get("marketData", {}))
    theta = float(setting("TAKER_FEE_RATE", "0.095"))
    print(f"\nOrder: {t.action} {t.qty:g} contracts at {t.price}")
    print(f"  intent       {t.intent}")
    print(f"  price.value  {t.yes_price}   (always the YES price)")
    print(f"  {cash_effect(t)}")
    print(f"  Market now: YES bid {bid}, YES ask {ask}")
    print(f"  If this crossed the spread as a taker, the fee at your {theta:.2%} tier would be about "
          f"${taker_fee(theta, t.qty, t.yes_price):.2f}. Resting as a maker, it's $0.")


def preview(c, t: Ticket) -> dict:
    result = c.orders.preview({"request": t.request()})
    print("\nPolymarket's preview:")
    print(json.dumps(result, indent=2)[:2000])
    return result


if __name__ == "__main__":
    client = private_client()
    try:
        ticket, _ = build(client, sys.argv[1:])
        explain(client, ticket)
        preview(client, ticket)
        print("\nNothing was sent. To place it for real, use step2_place_and_cancel.py.")
    finally:
        client.close()
