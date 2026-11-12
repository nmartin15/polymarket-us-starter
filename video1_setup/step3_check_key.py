"""Video 1, Step 3: Prove your key works. Read-only: this script cannot place a trade.

    python video1_setup/step3_check_key.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from polymarket_us import AuthenticationError  # noqa: E402

from pmus.config import private_client  # noqa: E402


def main() -> None:
    client = private_client()
    try:
        balances = client.account.balances().get("balances", [])
        b = balances[0] if balances else {}
        print(f"Cash: ${b.get('currentBalance', 0):,.2f}   Buying power: ${b.get('buyingPower', 0):,.2f}")
        print("\nKey works. You're connected.")
    except AuthenticationError as e:
        print(f"Auth failed: {e}")
        print("Check for a stray space or quote in .env, or create a fresh key at polymarket.us/developer.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
