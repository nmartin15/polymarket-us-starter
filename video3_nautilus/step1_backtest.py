"""Video 3, Step 1: Backtest on NautilusTrader with your Polymarket US recordings.

    python video3_nautilus/step1_backtest.py <slug>                   # taker, then maker
    python video3_nautilus/step1_backtest.py <slug> --fair 0.60
    python video3_nautilus/step1_backtest.py <slug> --only maker

The engine rebuilds the full order book from your recording and matches your orders against it:
taker orders walk the real depth, resting orders fill only when the market trades through them.
"""

import argparse
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder
sys.path.insert(0, str(Path(__file__).resolve().parent))
warnings.filterwarnings("ignore")  # hide library deprecation noise

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig  # noqa: E402
from nautilus_trader.config import LoggingConfig  # noqa: E402
from nautilus_trader.model.currencies import USD  # noqa: E402
from nautilus_trader.model.enums import AccountType, BookType, LiquiditySide, OmsType, OrderSide  # noqa: E402
from nautilus_trader.model.objects import Money  # noqa: E402

from pmus.config import setting  # noqa: E402
from strategies import FairValueConfig, FairValueMaker, FairValueTaker  # noqa: E402
from us_bridge import VENUE, PolymarketUSFeeModel, book_snapshots, load_tables, make_instrument, trade_ticks  # noqa: E402

STARTING_CASH = 1_000


def build_engine(instrument, verbose: bool = False) -> BacktestEngine:
    """A simulated Polymarket US: USD cash account, full-depth book, US fee model."""
    engine = BacktestEngine(BacktestEngineConfig(
        trader_id="STUDENT-001",
        logging=LoggingConfig(log_level="INFO" if verbose else "ERROR"),
    ))
    engine.add_venue(
        venue=VENUE,
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,          # no leverage, no shorting: you can only sell what you own
        base_currency=USD,
        starting_balances=[Money(STARTING_CASH, USD)],
        book_type=BookType.L2_MBP,              # full depth, price by price
        fee_model=PolymarketUSFeeModel(),
    )
    engine.add_instrument(instrument)
    return engine


def strategy_config(instrument, fair: float) -> FairValueConfig:
    return FairValueConfig(
        instrument_id=instrument.id,
        fair_value=fair,
        order_size=int(float(setting("ORDER_SIZE", "10"))),
        max_position=int(float(setting("MAX_POSITION", "50"))),
        min_edge=float(setting("MIN_EDGE", "0.04")),
        quote_offset=float(setting("QUOTE_OFFSET", "0.03")),
    )


def summarize(engine: BacktestEngine, instrument, name: str, last_bid: float) -> dict:
    """Read the results straight from the engine's own records."""
    fills = [o for o in engine.cache.orders() if o.filled_qty > 0]
    position = float(engine.portfolio.net_position(instrument.id))
    cash = float(engine.portfolio.account(VENUE).balance_total(USD))
    return {
        "strategy": name,
        "orders sent": len(engine.cache.orders()),
        "orders filled": len(fills),
        "filled as maker": sum(o.liquidity_side == LiquiditySide.MAKER for o in fills),
        "filled as taker": sum(o.liquidity_side == LiquiditySide.TAKER for o in fills),
        "contracts bought": sum(float(o.filled_qty) for o in fills if o.side == OrderSide.BUY),
        "contracts sold": sum(float(o.filled_qty) for o in fills if o.side == OrderSide.SELL),
        "fees paid": round(sum(float(c) for o in fills for c in o.commissions()), 2),
        "open position": position,
        "total P&L": round(cash + position * last_bid - STARTING_CASH, 2),
    }


def run(slug: str, strategy_cls, fair: float, verbose: bool = False) -> dict:
    books, trades = load_tables(slug)
    instrument = make_instrument(slug, books, float(setting("TAKER_FEE_RATE", "0.095")))
    engine = build_engine(instrument, verbose)
    engine.add_data(book_snapshots(instrument, books))
    ticks = trade_ticks(instrument, trades)
    if ticks:
        engine.add_data(ticks)
    engine.add_strategy(strategy_cls(strategy_config(instrument, fair)))
    engine.run()
    last_bid = float(books.dropna(subset=["bid"])["bid"].iloc[-1])
    result = summarize(engine, instrument, strategy_cls.__name__, last_bid)
    engine.dispose()
    return result


def show(results: list[dict]) -> None:
    keys = list(results[0].keys())
    width = max(len(k) for k in keys) + 2
    for k in keys:
        print(f"  {k:<{width}}" + "".join(f"{str(r[k]):>18}" for r in results))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--fair", type=float, default=float(setting("FAIR_VALUE", "0.50")))
    ap.add_argument("--only", choices=["taker", "maker"])
    ap.add_argument("--verbose", action="store_true", help="show the engine's own log")
    a = ap.parse_args()
    classes = {"taker": [FairValueTaker], "maker": [FairValueMaker], None: [FairValueTaker, FairValueMaker]}[a.only]
    print(f"\nNautilusTrader backtest: {a.slug}, fair value {a.fair:.2f}, ${STARTING_CASH:,} starting cash\n")
    show([run(a.slug, cls, a.fair, a.verbose) for cls in classes])
    print("\nOpen positions are valued at the last recorded bid.")
