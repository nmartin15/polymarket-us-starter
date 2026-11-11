"""The bridge: your Polymarket US recordings -> NautilusTrader objects.

NautilusTrader ships a connector for global Polymarket, not Polymarket US. This file is the
missing piece for US traders. It converts the Parquet tables from video 2 into the three
things the Nautilus engine needs:

    1. An instrument   (a BinaryOption: pays $1 or $0, priced 0 to 1, settled in USD)
    2. Order book data (every recorded snapshot, full depth)
    3. Trade ticks     (every recorded trade, so resting limit orders can fill)

It also defines the Polymarket US fee model: takers pay rate x contracts x price x (1 - price),
rounded to the cent. Makers earn a small rebate on Polymarket US; we leave it out to stay conservative.
"""

import sys
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

import pandas as pd  # noqa: E402
from nautilus_trader.backtest.models import FeeModel  # noqa: E402
from nautilus_trader.model.currencies import USD  # noqa: E402
from nautilus_trader.model.data import BookOrder, OrderBookDelta, OrderBookDeltas, TradeTick  # noqa: E402
from nautilus_trader.model.enums import AggressorSide, AssetClass, BookAction, LiquiditySide, OrderSide, RecordFlag  # noqa: E402
from nautilus_trader.model.identifiers import InstrumentId, Symbol, TradeId, Venue  # noqa: E402
from nautilus_trader.model.instruments import BinaryOption  # noqa: E402
from nautilus_trader.model.objects import Money, Price, Quantity  # noqa: E402

from pmus.recording import PARQUET  # noqa: E402

VENUE = Venue("POLYMARKET_US")


def load_tables(slug: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    folder = PARQUET / slug
    if not (folder / "books.parquet").exists():
        raise SystemExit(f"No Parquet data for '{slug}'. Run video2_data_paper/step2_to_parquet.py {slug} first.")
    return pd.read_parquet(folder / "books.parquet"), pd.read_parquet(folder / "trades.parquet")


def _decimals(values) -> int:
    """How many decimal places the venue actually uses, read from the data."""
    places = 0
    for v in values:
        text = f"{float(v):.6f}".rstrip("0")
        places = max(places, len(text.split(".")[1]))
    return places


def make_instrument(slug: str, books: pd.DataFrame, taker_fee_rate: float) -> BinaryOption:
    """One YES contract on Polymarket US, described the way Nautilus wants it."""
    prices = [p for row in books["bid_prices"].head(500) for p in row] + [p for row in books["ask_prices"].head(500) for p in row]
    sizes = [q for row in books["bid_sizes"].head(500) for q in row]
    price_precision = max(2, _decimals(prices))
    size_precision = _decimals(sizes)
    ts = int(books["ts"].iloc[0])
    return BinaryOption(
        instrument_id=InstrumentId(Symbol(slug), VENUE),
        raw_symbol=Symbol(slug),
        outcome="Yes",
        description=slug,
        asset_class=AssetClass.ALTERNATIVE,
        currency=USD,
        price_precision=price_precision,
        price_increment=Price(10 ** -price_precision, price_precision),
        size_precision=size_precision,
        size_increment=Quantity(10 ** -size_precision, size_precision),
        activation_ns=0,
        expiration_ns=int(books["ts"].iloc[-1]) + 365 * 86_400 * 1_000_000_000,
        max_quantity=None,
        min_quantity=None,
        maker_fee=Decimal(0),
        taker_fee=Decimal(str(taker_fee_rate)),
        ts_event=ts,
        ts_init=ts,
    )


def snapshot_deltas(instrument: BinaryOption, ts: int, bid_prices, bid_sizes, ask_prices, ask_sizes) -> OrderBookDeltas | None:
    """One full book snapshot becomes: clear the book, then add every level back."""
    iid = instrument.id
    deltas = [OrderBookDelta.clear(iid, 0, ts, ts)]
    for side, prices, sizes in ((OrderSide.BUY, bid_prices, bid_sizes), (OrderSide.SELL, ask_prices, ask_sizes)):
        for px, qty in zip(prices, sizes):
            order = BookOrder(side, instrument.make_price(px), instrument.make_qty(qty), 0)
            deltas.append(OrderBookDelta(iid, BookAction.ADD, order, flags=0, sequence=0, ts_event=ts, ts_init=ts))
    if len(deltas) == 1:
        return None  # empty book, nothing to add
    last = deltas[-1]  # flag the final delta so the engine knows the snapshot is complete
    deltas[-1] = OrderBookDelta(iid, BookAction.ADD, last.order, flags=RecordFlag.F_LAST,
                                sequence=0, ts_event=ts, ts_init=ts)
    return OrderBookDeltas(iid, deltas)


def book_snapshots(instrument: BinaryOption, books: pd.DataFrame) -> list[OrderBookDeltas]:
    out = []
    for row in books.itertuples():
        d = snapshot_deltas(instrument, int(row.ts), row.bid_prices, row.bid_sizes, row.ask_prices, row.ask_sizes)
        if d is not None:
            out.append(d)
    return out


def trade_ticks(instrument: BinaryOption, trades: pd.DataFrame) -> list[TradeTick]:
    side = {"BUY": AggressorSide.BUYER, "SELL": AggressorSide.SELLER}
    out = []
    for i, row in enumerate(trades.dropna(subset=["price", "qty"]).itertuples()):
        if row.qty <= 0:
            continue
        ts = int(row.ts)
        out.append(TradeTick(
            instrument_id=instrument.id,
            price=instrument.make_price(row.price),
            size=instrument.make_qty(row.qty),
            aggressor_side=side.get(row.taker_side, AggressorSide.NO_AGGRESSOR),
            trade_id=TradeId(f"T{i}"),
            ts_event=ts,
            ts_init=ts,
        ))
    return out


class PolymarketUSFeeModel(FeeModel):
    """Takers pay rate x contracts x price x (1 - price), rounded to the cent, half to even.

    The rate comes from instrument.taker_fee, set from TAKER_FEE_RATE in .env. It depends on
    your trailing 30-day taker volume (0.095 below $10K). Makers pay no fee and actually earn
    a small rebate; this model counts maker fills as zero, which slightly understates them.
    Source: https://docs.polymarket.us/fees
    """

    def get_commission(self, order, fill_qty, fill_px, instrument) -> Money:
        if order.liquidity_side == LiquiditySide.MAKER:
            return Money(0, instrument.quote_currency)
        p = Decimal(str(fill_px))
        fee = Decimal(str(instrument.taker_fee)) * Decimal(str(fill_qty)) * p * (1 - p)
        return Money(fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN), instrument.quote_currency)
