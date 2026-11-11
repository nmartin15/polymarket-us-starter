"""Video 2, Step 3: Look at your data before you trust any strategy.

    python video2_data_paper/step3_explore.py <slug>

Answers the questions that decide whether a market is tradable at all:
how wide is the spread, how much size is there, and what does a round trip cost?
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

import pandas as pd  # noqa: E402

from pmus.config import setting  # noqa: E402
from pmus.recording import PARQUET  # noqa: E402
from pmus.strategy import taker_fee  # noqa: E402


def explore(slug: str) -> dict:
    books = pd.read_parquet(PARQUET / slug / "books.parquet").dropna(subset=["bid", "ask"])
    trades = pd.read_parquet(PARQUET / slug / "trades.parquet")
    rate = float(setting("TAKER_FEE_RATE", "0.05"))

    hours = (books["ts"].iloc[-1] - books["ts"].iloc[0]) / 3.6e12
    mid = books["mid"].median()
    spread = books["spread"].median()
    fee_round_trip = 2 * taker_fee(1, mid, rate)
    cost = spread + fee_round_trip
    stats = {
        "hours recorded": round(hours, 2),
        "book snapshots": len(books),
        "trades": len(trades),
        "mid price (median)": round(mid, 3),
        "mid price (low to high)": f"{books['mid'].min():.2f} to {books['mid'].max():.2f}",
        "spread (median)": round(spread, 3),
        "spread (worst 5%)": round(books["spread"].quantile(0.95), 3),
        "size at best bid (median)": books["bid_qty"].median(),
        "size at best ask (median)": books["ask_qty"].median(),
        "taker round trip cost per contract": round(cost, 4),
    }
    print(f"\n{slug}")
    for k, v in stats.items():
        print(f"  {k:<38} {v}")
    print(f"\nA taker pays the spread ({spread:.3f}) plus two fees ({fee_round_trip:.4f}) on every round trip.")
    print(f"Your fair value must beat the market by more than {cost:.3f} per contract just to break even.")

    by_minute = books.set_index("time")["mid"].resample("1min").last().dropna()
    print(f"\nTypical 1-minute move in the mid: {by_minute.diff().abs().median():.4f}")
    return stats


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python video2_data_paper/step3_explore.py <slug>")
    explore(sys.argv[1])
