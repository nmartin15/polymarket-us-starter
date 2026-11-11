"""Offline check for the whole series. No network and no API key needed.

    python check_everything.py            # videos 1 and 2
    python check_everything.py --video3   # also the NautilusTrader steps

It builds a fake recording, runs every step on it, and confirms the numbers agree.
"""

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.update({"FAIR_VALUE": "0.55", "MIN_EDGE": "0.04", "TAKER_FEE_RATE": "0.095", "ORDER_SIZE": "10",
                   "MAX_POSITION": "50", "MAX_DAILY_LOSS": "25", "POLL_SECONDS": "0", "QUOTE_OFFSET": "0.03",
                   "MARKET_SLUG": "sample-market"})


def load(path: str):
    spec = importlib.util.spec_from_file_location(Path(path).stem, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    import polymarket_us  # noqa: F401  (video 1: the SDK is installed)

    from pmus.recording import read_events
    from pmus.strategy import Settings, taker_fee

    assert taker_fee(100, 0.50, 0.095) == 2.38 and taker_fee(100, 0.10, 0.0695) == 0.63, "fee formula (matches docs.polymarket.us/fees)"
    print("1/5 SDK installed and fee formula correct")

    load("video2_data_paper/make_sample_data.py").main()
    books, trades = load("video2_data_paper/step2_to_parquet.py").build("sample-market")
    assert len(books) == 4320 and (books["ask"] > books["bid"]).all()
    print("2/5 recording converted to Parquet")

    load("video2_data_paper/step3_explore.py").explore("sample-market")
    replay = load("video2_data_paper/step4_replay.py").replay("sample-market", Settings.from_env())
    assert replay.position == 0 and replay.realized_pnl > 0
    print("3/5 replay ran")

    # The live paper bot, fed the same recording through a stand-in for the API.
    events = [e["data"] for e in read_events("sample-market") if e["type"] == "book"]

    class FakeMarkets:
        i = 0

        def book(self, slug):
            FakeMarkets.i += 1
            return {"marketData": events[FakeMarkets.i - 1]}

    class FakeClient:
        markets = FakeMarkets()

    bot = load("video2_data_paper/step5_paper_bot.py")
    live = bot.run(FakeClient(), Settings.from_env(), max_loops=len(events), record=False)
    os.remove(live.log_path)
    assert abs(live.realized_pnl - replay.realized_pnl) < 1e-6, "live paper bot and replay must agree"
    print("4/5 paper bot matches the replay")

    if "--video3" in sys.argv:
        sys.path.insert(0, str(ROOT / "video3_nautilus"))
        bt = load("video3_nautilus/step1_backtest.py")
        from strategies import FairValueMaker, FairValueTaker

        taker = bt.run("sample-market", FairValueTaker, 0.55)
        maker = bt.run("sample-market", FairValueMaker, 0.55)
        bt.show([taker, maker])
        assert taker["orders filled"] == len(replay.trades), "Nautilus taker must make the same trades as the replay"
        assert abs(taker["total P&L"] - replay.realized_pnl) < 0.5, "and land on the same P&L, within fee rounding"
        assert maker["filled as taker"] == 0 and maker["fees paid"] == 0
        print("5/5 NautilusTrader backtest matches the replay")
    else:
        print("5/5 skipped (add --video3 once nautilus_trader is installed)")
    print("\nAll offline checks passed.")


if __name__ == "__main__":
    main()
