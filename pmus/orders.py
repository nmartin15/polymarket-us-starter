"""Building an order correctly, before anything is sent.

Four intents:
    buy-yes   ORDER_INTENT_BUY_LONG     buy YES contracts
    sell-yes  ORDER_INTENT_SELL_LONG    sell YES contracts you hold
    buy-no    ORDER_INTENT_BUY_SHORT    buy NO contracts
    sell-no   ORDER_INTENT_SELL_SHORT   sell NO contracts you hold

The price is ALWAYS the YES price, whichever intent you use. To buy NO at 17 cents, you send
BUY_SHORT at 0.83. Selling YES you don't own opens a short, which locks $1.00 of margin per
contract. Source: https://docs.polymarket.us/api-reference/orders/overview
"""

from dataclasses import dataclass

from pmus.money import on_step, on_tick, usd

INTENTS = {
    "buy-yes": "ORDER_INTENT_BUY_LONG",
    "sell-yes": "ORDER_INTENT_SELL_LONG",
    "buy-no": "ORDER_INTENT_BUY_SHORT",
    "sell-no": "ORDER_INTENT_SELL_SHORT",
}


@dataclass
class Ticket:
    slug: str
    action: str          # one of INTENTS
    price: float         # the price YOU think in: YES price for yes orders, NO price for no orders
    qty: float

    @property
    def intent(self) -> str:
        return INTENTS[self.action]

    @property
    def yes_price(self) -> float:
        """What actually goes in price.value."""
        p = self.price if self.action.endswith("yes") else 1 - self.price
        return round(p, 6)

    def problems(self, tick: float, min_qty: float) -> list[str]:
        out = []
        if self.action not in INTENTS:
            out.append(f"action must be one of {', '.join(INTENTS)}")
        if not 0 < self.price < 1:
            out.append("price must be between 0 and 1, like 0.45")
        elif not on_tick(self.yes_price, tick):
            out.append(f"price must move in steps of {tick} on this market")
        if not on_step(self.qty, min_qty):
            out.append(f"quantity must be a multiple of {min_qty} contracts")
        return out

    def request(self, rest_only: bool = True) -> dict:
        """The exact create-order request. rest_only=True means it rests on the book as a maker
        and is cancelled rather than filled if it would cross the spread."""
        return {
            "marketSlug": self.slug,
            "intent": self.intent,
            "type": "ORDER_TYPE_LIMIT",
            "price": usd(self.yes_price),
            "quantity": self.qty,
            "tif": "TIME_IN_FORCE_GOOD_TILL_CANCEL",
            "participateDontInitiate": rest_only,
            "manualOrderIndicator": "MANUAL_ORDER_INDICATOR_AUTOMATIC",
        }


def cash_effect(t: Ticket) -> str:
    """Plain-English money math, before fees."""
    if t.action == "buy-yes":
        return f"You pay about ${t.price * t.qty:.2f}. You get $1 per contract if YES."
    if t.action == "buy-no":
        return f"You pay about ${t.price * t.qty:.2f}. You get $1 per contract if NO."
    if t.action == "sell-yes":
        return ("If you hold YES, this closes it. If you don't, it opens a SHORT: "
                f"you receive ${t.price * t.qty:.2f} and ${t.qty:.2f} of margin is locked ($1 per contract).")
    return "Closes NO contracts you hold."
