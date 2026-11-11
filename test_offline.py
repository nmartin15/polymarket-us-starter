"""Offline check: runs the paper bot against a fake order book. No network needed.

    python test_offline.py
"""

import os

os.environ.update({"MARKET_SLUG": "demo-market", "FAIR_VALUE": "0.60", "POLL_SECONDS": "0",
                   "MIN_EDGE": "0.04", "TAKER_FEE_RATE": "0.05", "ORDER_SIZE": "10",
                   "MAX_POSITION": "20", "MAX_DAILY_LOSS": "25"})

import step3_paper_bot as bot  # noqa: E402
from paper_broker import taker_fee  # noqa: E402

# A market that dips (bot should buy), then rallies (bot should sell).
PATH = [(0.48, 0.50), (0.48, 0.50), (0.48, 0.50), (0.55, 0.57), (0.68, 0.70), (0.68, 0.70)]


class FakeMarkets:
    def __init__(self):
        self.i = 0

    def book(self, slug):
        bid, ask = PATH[min(self.i, len(PATH) - 1)]
        self.i += 1
        return {"marketData": {"state": "MARKET_STATE_OPEN",
                               "bids": [{"px": {"value": str(bid)}, "qty": "100"}],
                               "offers": [{"px": {"value": str(ask)}, "qty": "100"}]}}


class FakeClient:
    markets = FakeMarkets()


if os.path.exists("paper_trades.csv"):
    os.remove("paper_trades.csv")
b = bot.run(FakeClient(), max_loops=len(PATH))

assert abs(taker_fee(100, 0.50, 0.05) - 1.25) < 1e-9, "fee formula"
assert b.position == 0, "should have bought to the cap then sold out"
assert len([t for t in b.trades if t["side"] == "BUY"]) == 2, "position cap of 20 = 2 buys"
assert b.realized_pnl > 0
os.remove("paper_trades.csv")
print("\nAll offline checks passed.")
