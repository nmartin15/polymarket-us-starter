"""Two strategies on the same idea, written for NautilusTrader.

Both trade around FAIR_VALUE, your own probability that the market resolves YES.

    FairValueTaker  crosses the spread when the price is far enough from fair value. Pays the fee.
    FairValueMaker  rests limit orders around fair value and waits to be hit. Pays no fee,
                    but only fills when someone else decides to trade with it.

Nautilus calls on_order_book_deltas() on every book update, in a backtest or live.
"""

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.enums import BookType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class FairValueConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    fair_value: float
    order_size: int = 10
    max_position: int = 50
    min_edge: float = 0.04        # taker: edge required after the fee
    quote_offset: float = 0.03    # maker: how far from fair value to rest quotes


class _FairValueBase(Strategy):
    def __init__(self, config: FairValueConfig) -> None:
        super().__init__(config)
        self.instrument = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.subscribe_order_book_deltas(self.config.instrument_id, book_type=BookType.L2_MBP)

    def position_size(self) -> float:
        return float(self.portfolio.net_position(self.config.instrument_id))

    def best_prices(self):
        book = self.cache.order_book(self.config.instrument_id)
        bid, ask = book.best_bid_price(), book.best_ask_price()
        return (float(bid) if bid else None, float(ask) if ask else None)

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)


class FairValueTaker(_FairValueBase):
    """Same rule as the video 2 paper bot, now on a professional engine."""

    def fee(self, price: float) -> float:
        return float(self.instrument.taker_fee) * price * (1 - price)

    def on_order_book_deltas(self, deltas) -> None:
        if self.cache.orders_inflight(strategy_id=self.id) or self.cache.orders_open(strategy_id=self.id):
            return  # wait for the last order to finish
        c, pos = self.config, self.position_size()
        bid, ask = self.best_prices()
        if ask and c.fair_value - ask - self.fee(ask) > c.min_edge and pos + c.order_size <= c.max_position:
            self._hit(OrderSide.BUY, ask, c.order_size)
        elif bid and pos > 0 and bid - c.fair_value - self.fee(bid) > c.min_edge:
            self._hit(OrderSide.SELL, bid, min(c.order_size, pos))

    def _hit(self, side: OrderSide, price: float, size: float) -> None:
        # Immediate-or-cancel limit: take what is there at this price, never chase.
        order = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=side,
            quantity=self.instrument.make_qty(size),
            price=self.instrument.make_price(price),
            time_in_force=TimeInForce.IOC,
        )
        self.submit_order(order)


class FairValueMaker(_FairValueBase):
    """Rests a bid below fair value. Once it owns contracts, rests an offer above fair value."""

    def __init__(self, config: FairValueConfig) -> None:
        super().__init__(config)
        self.bid_order = None
        self.ask_order = None

    def on_order_book_deltas(self, deltas) -> None:
        c, pos = self.config, self.position_size()
        bid, ask = self.best_prices()
        if bid is None or ask is None:
            return
        tick = float(self.instrument.price_increment)

        # Quote at fair value minus/plus the offset, but never cross the spread (stay a maker).
        want_bid = min(c.fair_value - c.quote_offset, ask - tick)
        want_ask = max(c.fair_value + c.quote_offset, bid + tick)

        buy_size = min(c.order_size, c.max_position - pos)
        self.bid_order = self._requote(self.bid_order, OrderSide.BUY, want_bid, buy_size)
        self.ask_order = self._requote(self.ask_order, OrderSide.SELL, want_ask, min(c.order_size, pos))

    def _requote(self, order, side: OrderSide, price: float, size: float):
        target = self.instrument.make_price(price)
        live = order is not None and not order.is_closed
        if live and (order.price == target and size > 0):
            return order                      # already quoting the right price
        if live:
            if order.is_inflight or order.is_pending_cancel:
                return order                  # let the last instruction land first
            self.cancel_order(order)
        if size <= 0 or not (Decimal("0") < target.as_decimal() < Decimal("1")):
            return None
        new = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=side,
            quantity=self.instrument.make_qty(size),
            price=target,
            post_only=True,                   # rejected rather than filled as a taker
        )
        self.submit_order(new)
        return new
