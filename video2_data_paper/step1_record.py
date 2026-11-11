"""Video 2, Step 1: Record the order book and trades to disk.

Two ways to record:
    python video2_data_paper/step1_record.py <slug>             # polling: no API key needed
    python video2_data_paper/step1_record.py <slug> --stream    # WebSocket: every update, needs your key

Add --minutes 30 to stop on its own. Otherwise stop with Ctrl+C.
Files land in data/raw/<slug>/<date>.jsonl. Nothing here places an order.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from pmus.config import keys, public_client  # noqa: E402
from pmus.recording import append_event, raw_path  # noqa: E402


def record_polling(slug: str, seconds: float, minutes: float | None) -> None:
    """Ask for the full book every few seconds. Simple and keyless, but you miss what happens in between."""
    client = public_client()
    deadline = time.time() + minutes * 60 if minutes else None
    n = 0
    try:
        while deadline is None or time.time() < deadline:
            try:
                book = client.markets.book(slug)["marketData"]
                append_event(slug, "book", book)
                n += 1
                if n % 10 == 1:
                    print(f"{n} snapshots saved")
            except Exception as e:  # network blip: keep recording
                print(f"data error: {e}; retrying")
            time.sleep(seconds)
    finally:
        client.close()
        print(f"Saved {n} snapshots to {raw_path(slug).parent}")


async def record_stream(slug: str, minutes: float | None) -> None:
    """Subscribe once and Polymarket US pushes every book update and every trade to you."""
    from polymarket_us import AsyncPolymarketUS

    key_id, secret = keys()
    counts = {"book": 0, "trade": 0}

    def on_book(msg):
        append_event(slug, "book", msg["marketData"])
        counts["book"] += 1

    def on_trade(msg):
        append_event(slug, "trade", msg["trade"])
        counts["trade"] += 1

    async with AsyncPolymarketUS(key_id=key_id, secret_key=secret) as client:
        ws = client.ws.markets()
        ws.on("market_data", on_book)
        ws.on("trade", on_trade)
        ws.on("error", lambda e: print(f"stream error: {e}"))
        await ws.connect()
        await ws.subscribe_market_data("book-1", [slug])
        await ws.subscribe_trades("trades-1", [slug])
        print(f"Streaming {slug}. Ctrl+C to stop.")
        deadline = time.time() + minutes * 60 if minutes else None
        try:
            while ws.is_connected and (deadline is None or time.time() < deadline):
                await asyncio.sleep(10)
                print(f"{counts['book']} book updates, {counts['trade']} trades saved")
        finally:
            await ws.close()
            print(f"Saved to {raw_path(slug).parent}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--stream", action="store_true", help="use the WebSocket (needs your API key)")
    ap.add_argument("--seconds", type=float, default=5, help="polling interval")
    ap.add_argument("--minutes", type=float, default=None, help="stop after this long")
    a = ap.parse_args()
    try:
        if a.stream:
            asyncio.run(record_stream(a.slug, a.minutes))
        else:
            record_polling(a.slug, a.seconds, a.minutes)
    except KeyboardInterrupt:
        print("\nStopped by you.")
