"""Video 2, Step 3: Watch your own account live: orders, fills, positions, balance. Needs your key.

    python video2_account_live/step3_private_stream.py
    python video2_account_live/step3_private_stream.py --minutes 10

This is how you know an order filled. When you stop it, it checks itself against REST
(your open orders and positions) so you can see the two agree.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from pmus.config import async_private_client, private_client  # noqa: E402
from pmus.live import find_all, run_forever, short  # noqa: E402
from pmus.money import num  # noqa: E402

FILL_TYPES = {"EXECUTION_TYPE_FILL", "EXECUTION_TYPE_PARTIAL_FILL"}


def stamp() -> str:
    return time.strftime("%H:%M:%S")


def on_order(kind: str):
    def handle(msg) -> None:
        fills = [t for t in find_all(msg, "type") if t in FILL_TYPES]
        if fills:
            shares = [num(s) for s in find_all(msg, "lastShares")]
            prices = [num(p) for p in find_all(msg, "lastPx")]
            qty = shares[0] if shares else "?"
            px = prices[0] if prices else "?"
            print(f"{stamp()}  FILL    {qty} @ {px}   {short(msg, 120)}")
        else:
            states = [s for s in find_all(msg, "state")]
            print(f"{stamp()}  ORDER   {kind} {states[0] if states else ''}   {short(msg, 120)}")
    return handle


def reconcile() -> None:
    """REST is the source of truth. Compare what the socket told you with what REST says now."""
    c = private_client()
    try:
        orders = c.orders.list().get("orders") or []
        positions = c.portfolio.positions().get("positions") or {}
        print(f"\nREST check: {len(orders)} open orders, {len(positions)} positions.")
        for slug, p in positions.items():
            print(f"  {slug}: net {num(p.get('netPositionDecimal') or p.get('netPosition'))}")
    finally:
        c.close()


async def main(minutes: float | None) -> None:
    client = async_private_client()

    async def open_socket(last):
        ws = client.ws.private()
        ws.on("message", lambda m: last.update(t=time.time()))
        ws.on("heartbeat", lambda: print(f"{stamp()}  heartbeat"))
        ws.on("order_snapshot", on_order("snapshot"))
        ws.on("order_update", on_order("update"))
        ws.on("position_snapshot", lambda m: print(f"{stamp()}  POSITIONS {short(m)}"))
        ws.on("position_update", lambda m: print(f"{stamp()}  POSITION  {short(m)}"))
        ws.on("account_balance_snapshot", lambda m: print(f"{stamp()}  BALANCE   {short(m)}"))
        ws.on("account_balance_update", lambda m: print(f"{stamp()}  BALANCE   {short(m)}"))
        ws.on("error", lambda e: print(f"error: {e}"))
        await ws.connect()
        await ws.subscribe_orders("my-orders")
        await ws.subscribe_positions("my-positions")
        await ws.subscribe_account_balance("my-balance")
        print("Watching your account. Ctrl+C to stop.\n")
        return ws

    try:
        await run_forever(open_socket, minutes)
    finally:
        await client.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float)
    a = ap.parse_args()
    try:
        asyncio.run(main(a.minutes))
    except KeyboardInterrupt:
        print("\nStopped.")
    reconcile()
