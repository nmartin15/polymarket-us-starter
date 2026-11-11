"""A fake broker. It fills your orders against the REAL order book, but no money moves.

Assumptions (deliberately pessimistic, so paper results don't flatter you):
  - You trade as a taker: buys fill at the best ask, sells at the best bid.
  - You only get the size showing at the top of the book.
  - Every fill pays the taker fee: contracts x rate x price x (1 - price).
  - Open positions are valued at the best bid (what you could sell for right now).
"""

import csv
import datetime as dt
from dataclasses import dataclass, field


def taker_fee(contracts: float, price: float, rate: float) -> float:
    return round(contracts * rate * price * (1 - price), 4)


@dataclass
class PaperBroker:
    fee_rate: float
    log_path: str = "paper_trades.csv"
    position: float = 0.0         # YES contracts held
    cost_basis: float = 0.0       # dollars paid for current position, incl. fees
    realized_pnl: float = 0.0
    fees_paid: float = 0.0
    trades: list = field(default_factory=list)

    def buy(self, qty: float, ask: float, ask_qty: float) -> float:
        filled = min(qty, ask_qty)
        if filled <= 0:
            return 0
        fee = taker_fee(filled, ask, self.fee_rate)
        self.position += filled
        self.cost_basis += filled * ask + fee
        self.fees_paid += fee
        self._log("BUY", filled, ask, fee)
        return filled

    def sell(self, qty: float, bid: float, bid_qty: float) -> float:
        filled = min(qty, bid_qty, self.position)
        if filled <= 0:
            return 0
        fee = taker_fee(filled, bid, self.fee_rate)
        avg_cost = self.cost_basis / self.position
        self.realized_pnl += filled * bid - fee - filled * avg_cost
        self.cost_basis -= filled * avg_cost
        self.position -= filled
        self.fees_paid += fee
        self._log("SELL", filled, bid, fee)
        return filled

    def unrealized_pnl(self, bid: float) -> float:
        return self.position * bid - self.cost_basis

    def total_pnl(self, bid: float) -> float:
        return self.realized_pnl + self.unrealized_pnl(bid)

    def _log(self, side: str, qty: float, px: float, fee: float) -> None:
        row = {
            "time": dt.datetime.now().isoformat(timespec="seconds"),
            "side": side, "qty": qty, "price": px, "fee": fee,
            "position": self.position, "realized_pnl": round(self.realized_pnl, 4),
        }
        self.trades.append(row)
        new_file = not _exists(self.log_path)
        with open(self.log_path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=row.keys())
            if new_file:
                w.writeheader()
            w.writerow(row)
        print(f"  PAPER {side} {qty:g} @ {px:.2f}  fee {fee:.4f}  pos {self.position:g}")


def _exists(path: str) -> bool:
    try:
        open(path).close()
        return True
    except FileNotFoundError:
        return False
