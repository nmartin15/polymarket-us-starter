"""Video 3, Step 2: Place one real, tiny order, confirm it on the book, then cancel it.

    python video3_orders/step2_place_and_cancel.py <market-slug> buy-yes 0.05 1           # dry run
    python video3_orders/step2_place_and_cancel.py <market-slug> buy-yes 0.05 1 --live    # real

Guard rails, all on by default:
  - Without --live it only prints the request. Nothing is sent.
  - With --live you must type PLACE to continue.
  - At most MAX_LIVE_CONTRACTS contracts (default 1).
  - The order is maker-only: if it would cross the spread, the exchange cancels it instead of filling it.
    Price it away from the market so it rests.
  - It cancels the order after HOLD_SECONDS (default 10) and checks the cancel went through.

Run video2_account_live/step3_private_stream.py in a second terminal to watch it happen live.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from pmus.config import private_client, setting  # noqa: E402
from pmus.money import num  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from step1_preview import build, explain  # noqa: E402

MAX_LIVE = float(setting("MAX_LIVE_CONTRACTS", "1"))
HOLD = float(setting("HOLD_SECONDS", "10"))


def place_and_cancel(c, ticket, confirm=input) -> str | None:
    if ticket.qty > MAX_LIVE:
        sys.exit(f"Refusing: {ticket.qty:g} contracts is over MAX_LIVE_CONTRACTS ({MAX_LIVE:g}).")
    if confirm(f"\nType PLACE to send this real order for {ticket.qty:g} contracts: ").strip() != "PLACE":
        print("Not sent.")
        return None

    created = c.orders.create(ticket.request())
    order_id = created.get("id")
    print(f"\nSent. Order ID: {order_id}")
    for ex in created.get("executions") or []:
        print(f"  execution: {ex.get('type')}  {ex.get('text') or ''}")

    time.sleep(1)
    open_ids = {o.get("id") for o in c.orders.list().get("orders") or []}
    print("  On the book: " + ("yes" if order_id in open_ids else "no (it may have been cancelled as a taker)"))

    if order_id in open_ids:
        print(f"  Holding {HOLD:g}s, then cancelling...")
        time.sleep(HOLD)
        c.orders.cancel(order_id, {"marketSlug": ticket.slug})
        time.sleep(1)
        still = order_id in {o.get("id") for o in c.orders.list().get("orders") or []}
        print("  Cancelled." if not still else "  Still open! Cancel it in the app now.")

    order = c.orders.retrieve(order_id).get("order", {})
    print(f"  Final state: {order.get('state')}   filled {num(order.get('cumQuantity')) or 0}")
    return order_id


if __name__ == "__main__":
    live = "--live" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--live"]
    client = private_client()
    try:
        ticket, _ = build(client, args)
        explain(client, ticket)
        print("\nRequest:")
        print(json.dumps(ticket.request(), indent=2))
        if not live:
            print("\nDry run. Nothing was sent. Add --live to place it for real.")
        else:
            place_and_cancel(client, ticket)
    finally:
        client.close()
