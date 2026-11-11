"""Video 2, Step 2: Turn the raw recording into Parquet tables pandas can read in one line.

    python video2_data_paper/step2_to_parquet.py <slug>

Writes data/parquet/<slug>/books.parquet and trades.parquet.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

import pandas as pd  # noqa: E402

from pmus.recording import PARQUET, amount, levels, read_events  # noqa: E402


def build(slug: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    books, trades = [], []
    for e in read_events(slug):
        d = e["data"]
        if e["type"] == "book":
            bid_px, bid_qty = levels(d.get("bids"))
            ask_px, ask_qty = levels(d.get("offers"))
            # Sort so index 0 is always the best price, whatever order the API sent.
            bids = sorted(zip(bid_px, bid_qty), reverse=True)
            asks = sorted(zip(ask_px, ask_qty))
            books.append({
                "ts": e["ts"], "state": d.get("state"),
                "bid": bids[0][0] if bids else None, "bid_qty": bids[0][1] if bids else 0.0,
                "ask": asks[0][0] if asks else None, "ask_qty": asks[0][1] if asks else 0.0,
                "bid_prices": [p for p, _ in bids], "bid_sizes": [q for _, q in bids],
                "ask_prices": [p for p, _ in asks], "ask_sizes": [q for _, q in asks],
            })
        elif e["type"] == "trade":
            trades.append({
                "ts": e["ts"], "price": amount(d.get("price")), "qty": amount(d.get("quantity")),
                "taker_side": ((d.get("taker") or {}).get("side") or "").replace("ORDER_SIDE_", ""),
            })
    if not books:
        raise SystemExit(f"No recording found for '{slug}'. Run step1_record.py or make_sample_data.py first.")

    books_df = pd.DataFrame(books).sort_values("ts").reset_index(drop=True)
    books_df["time"] = pd.to_datetime(books_df["ts"], unit="ns", utc=True)
    books_df["mid"] = (books_df["bid"] + books_df["ask"]) / 2
    books_df["spread"] = books_df["ask"] - books_df["bid"]

    trades_df = pd.DataFrame(trades, columns=["ts", "price", "qty", "taker_side"]).sort_values("ts").reset_index(drop=True)
    trades_df["time"] = pd.to_datetime(trades_df["ts"], unit="ns", utc=True)

    out = PARQUET / slug
    out.mkdir(parents=True, exist_ok=True)
    books_df.to_parquet(out / "books.parquet", index=False)
    trades_df.to_parquet(out / "trades.parquet", index=False)
    print(f"{len(books_df):,} book snapshots and {len(trades_df):,} trades -> {out}")
    return books_df, trades_df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python video2_data_paper/step2_to_parquet.py <slug>")
    build(sys.argv[1])
