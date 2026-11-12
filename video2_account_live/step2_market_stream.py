"""Video 2, Step 2: Stream a market live instead of polling it. Needs your key.

    python video2_account_live/step2_market_stream.py <market-slug>
    python video2_account_live/step2_market_stream.py <market-slug> --lite      # prices only
    python video2_account_live/step2_market_stream.py <market-slug> --minutes 5

Full book updates, lightweight prices, and every trade, pushed to you as they happen.
Ctrl+C to stop.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from pmus.config import async_private_client  # noqa: E402
from pmus.live import run_forever  # noqa: E402
from pmus.markets import best  # noqa: E402
from pmus.money import num  # noqa: E402


def on_book(msg) -> None:
    bid, bq, ask, aq = best(msg.get("marketData", {}))
    print(f"{time.strftime('%H:%M:%S')}  BOOK   bid {bid} x {bq:g}   ask {ask} x {aq:g}")


def on_lite(msg) -> None:
    d = msg.get("marketDataLite", {})
    print(f"{time.strftime('%H:%M:%S')}  PRICE  bid {num(d.get('bestBid'))}   ask {num(d.get('bestAsk'))}   "
          f"last {num(d.get('lastTradePx'))}")


def on_trade(msg) -> None:
    t = msg.get("trade", {})
    print(f"{time.strftime('%H:%M:%S')}  TRADE  {num(t.get('quantity'))} @ {num(t.get('price'))}")


async def main(slug: str, lite: bool, minutes: float | None) -> None:
    client = async_private_client()

    async def open_socket(last):
        ws = client.ws.markets()
        ws.on("message", lambda m: last.update(t=time.time()))
        ws.on("heartbeat", lambda: print(f"{time.strftime('%H:%M:%S')}  heartbeat"))
        ws.on("market_data", on_book)
        ws.on("market_data_lite", on_lite)
        ws.on("trade", on_trade)
        ws.on("error", lambda e: print(f"error: {e}"))
        await ws.connect()
        if lite:
            await ws.subscribe_market_data_lite("prices", [slug])
        else:
            await ws.subscribe_market_data("book", [slug])
        await ws.subscribe_trades("trades", [slug])
        print(f"Streaming {slug}. Ctrl+C to stop.\n")
        return ws

    try:
        await run_forever(open_socket, minutes)
    finally:
        await client.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--lite", action="store_true", help="prices only, instead of the full book")
    ap.add_argument("--minutes", type=float)
    a = ap.parse_args()
    try:
        asyncio.run(main(a.slug, a.lite, a.minutes))
    except KeyboardInterrupt:
        print("\nStopped.")
