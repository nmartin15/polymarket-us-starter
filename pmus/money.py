"""Prices, quantities, and fees, the way Polymarket US expects them.

Prices travel as {"value": "0.55", "currency": "USD"}. Quantities are contracts, and can be
fractional when a market's minimumTradeQty is below 1 (0.01 means 1% of a contract).
"""

from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal


def num(x) -> float | None:
    """Read a number from whatever the API sent: an Amount dict, a string, or a number."""
    if x is None:
        return None
    if isinstance(x, dict):
        x = x.get("value")
    if x in (None, ""):
        return None
    return float(x)


def usd(price: float | Decimal | str) -> dict:
    """A price in the shape the API wants."""
    return {"value": str(Decimal(str(price)).normalize()), "currency": "USD"}


def on_tick(price: float, tick: float) -> bool:
    """True if the price is a whole number of ticks (tick 0.005 means half-cent steps)."""
    p, t = Decimal(str(price)), Decimal(str(tick))
    return (p / t) == (p / t).to_integral_value()


def on_step(qty: float, step: float) -> bool:
    """True if the quantity is a whole number of minimum steps."""
    q, s = Decimal(str(qty)), Decimal(str(step))
    return q >= s and (q / s) == (q / s).to_integral_value()


def floor_to_step(qty: float, step: float) -> float:
    q, s = Decimal(str(qty)), Decimal(str(step))
    return float((q / s).to_integral_value(rounding=ROUND_DOWN) * s)


def taker_fee(theta: float, contracts: float, price: float) -> float:
    """Polymarket US taker fee: theta x contracts x price x (1 - price), rounded to the cent, half to even.

    theta is your account's fee tier (0.095 under $10K of 30-day volume, down to 0.0695).
    Source: https://docs.polymarket.us/fees
    """
    p = Decimal(str(price))
    fee = Decimal(str(theta)) * Decimal(str(contracts)) * p * (1 - p)
    return float(fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))
