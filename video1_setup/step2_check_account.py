"""Step 2: Prove your API key works. Read-only: this script never places orders."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from polymarket_us import AuthenticationError  # noqa: E402

from pmus.config import private_client  # noqa: E402


def main() -> None:
    client = private_client()
    try:
        balances = client.account.balances().get("balances", [])
        for b in balances:
            print(f"Cash: {b.get('currentBalance')} {b.get('currency')}   "
                  f"Buying power: {b.get('buyingPower')}   Open orders: {b.get('openOrders')}")

        positions = client.portfolio.positions()
        print(f"\nPositions: {len(positions.get('positions', []) or [])}")

        orders = client.orders.list()
        print(f"Open orders: {len(orders.get('orders', []) or [])}")
        print("\nKey works. You're connected.")
    except AuthenticationError as e:
        print(f"Auth failed: {e.message}\nCheck the key ID and secret in .env, or create a new key.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
