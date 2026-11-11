"""The strategy, in one place. Video 2 runs it live and on recorded data.

You supply FAIR_VALUE: your own probability that the market resolves YES.
  Buy when the ask is below fair value by more than the fee plus MIN_EDGE.
  Sell what you hold when the bid is above fair value by the same margin.
"""

from dataclasses import dataclass

from pmus.config import setting


def taker_fee(contracts: float, price: float, rate: float) -> float:
    """Polymarket US taker fee: contracts x rate x price x (1 - price)."""
    return round(contracts * rate * price * (1 - price), 4)


@dataclass
class Settings:
    slug: str
    fair: float
    min_edge: float
    fee_rate: float
    size: float
    max_pos: float
    max_loss: float
    poll: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            slug=setting("MARKET_SLUG", ""),
            fair=float(setting("FAIR_VALUE", "0.50")),
            min_edge=float(setting("MIN_EDGE", "0.04")),
            fee_rate=float(setting("TAKER_FEE_RATE", "0.05")),
            size=float(setting("ORDER_SIZE", "10")),
            max_pos=float(setting("MAX_POSITION", "50")),
            max_loss=float(setting("MAX_DAILY_LOSS", "25")),
            poll=float(setting("POLL_SECONDS", "10")),
        )


def decide(s: Settings, bid, ask, position):
    """Returns ('BUY' | 'SELL' | None, reason)."""
    if ask is not None:
        buy_edge = s.fair - ask - taker_fee(1, ask, s.fee_rate)
        if buy_edge > s.min_edge and position + s.size <= s.max_pos:
            return "BUY", f"ask {ask:.2f} vs fair {s.fair:.2f}, edge after fee {buy_edge:.3f}"
    if bid is not None and position > 0:
        sell_edge = bid - s.fair - taker_fee(1, bid, s.fee_rate)
        if sell_edge > s.min_edge:
            return "SELL", f"bid {bid:.2f} vs fair {s.fair:.2f}, edge after fee {sell_edge:.3f}"
    return None, "no edge"
