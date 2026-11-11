"""Creates a FAKE recording so you can try every step before you record real data.

    python video2_data_paper/make_sample_data.py

It writes data/raw/sample-market/ in exactly the format step1_record.py produces.
The prices are invented (a random walk around 55 cents). Never judge a strategy on this.
"""

import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from pmus.recording import RAW, append_event  # noqa: E402

SLUG = "sample-market"
START_NS = 1_780_000_000 * 1_000_000_000   # a fixed moment, so every run is identical


def px(x: float) -> dict:
    return {"value": f"{x:.2f}", "currency": "USD"}


def main(hours: float = 6, step_s: int = 5, seed: int = 7) -> None:
    random.seed(seed)
    shutil.rmtree(RAW / SLUG, ignore_errors=True)
    mid, books, trades = 0.55, 0, 0
    for i in range(int(hours * 3600 / step_s)):
        ts = START_NS + i * step_s * 1_000_000_000
        mid += 0.04 * (0.55 - mid) + random.gauss(0, 0.012)      # drifts, but pulled back to 55 cents
        mid = min(0.95, max(0.05, mid))
        half = random.choice([0.005, 0.01, 0.01, 0.015])
        bid = round(mid - half - 0.0001, 2)
        ask = max(round(mid + half + 0.0001, 2), bid + 0.01)
        book = {
            "marketSlug": SLUG, "state": "MARKET_STATE_OPEN",
            "bids": [{"px": px(bid - 0.01 * k), "qty": str(random.randint(20, 400))} for k in range(5) if bid - 0.01 * k > 0],
            "offers": [{"px": px(ask + 0.01 * k), "qty": str(random.randint(20, 400))} for k in range(5) if ask + 0.01 * k < 1],
        }
        append_event(SLUG, "book", book, ts)
        books += 1
        if random.random() < 0.25:                                # someone crosses the spread
            buy = random.random() < 0.5
            trade = {
                "marketSlug": SLUG, "price": px(ask if buy else bid),
                "quantity": {"value": str(random.randint(1, 60))},
                "taker": {"side": "ORDER_SIDE_BUY" if buy else "ORDER_SIDE_SELL"},
            }
            append_event(SLUG, "trade", trade, ts + 1_000_000_000)
            trades += 1
    print(f"Wrote {books} fake book snapshots and {trades} fake trades to {RAW / SLUG}")
    print("Next: python video2_data_paper/step2_to_parquet.py sample-market")


if __name__ == "__main__":
    main()
