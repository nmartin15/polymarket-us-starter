"""Video 2, Step 1: Your account over REST. Read-only.

    python video2_account_live/step1_account.py

Balances (cash, buying power, margin), positions (long or short), and open orders.
Use this as your reconciliation check: the live sockets in steps 2 and 3 should agree with it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from pmus.config import private_client  # noqa: E402
from pmus.money import num  # noqa: E402


def show(c) -> None:
    for b in c.account.balances().get("balances", []):
        print("BALANCE")
        for label, key in [("Cash", "currentBalance"), ("Buying power", "buyingPower"),
                           ("Margin locked by shorts", "marginRequirement"), ("Held for open orders", "openOrders"),
                           ("Available to withdraw", "availableToWithdraw")]:
            print(f"  {label:<26} ${num(b.get(key)) or 0:,.2f}")

    positions = c.portfolio.positions().get("positions") or {}
    print(f"\nPOSITIONS ({len(positions)})")
    for slug, p in positions.items():
        net = num(p.get("netPositionDecimal") or p.get("netPosition")) or 0
        side = "LONG YES" if net > 0 else "SHORT (NO)" if net < 0 else "flat"
        print(f"  {slug:<45} {side:<11} {abs(net):g} contracts   avg {num(p.get('avgPx'))}   "
              f"value ${num(p.get('cashValue')) or 0:,.2f}")

    orders = c.orders.list().get("orders") or []
    print(f"\nOPEN ORDERS ({len(orders)})")
    for o in orders:
        print(f"  {o.get('id')}  {o.get('marketSlug')}  {o.get('intent', '').replace('ORDER_INTENT_', '')}  "
              f"{num(o.get('quantity'))} @ {num(o.get('price'))}  filled {num(o.get('cumQuantity')) or 0}  {o.get('state')}")


if __name__ == "__main__":
    client = private_client()
    try:
        show(client)
    finally:
        client.close()
