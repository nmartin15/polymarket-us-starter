"""Step 1: Pull live market data. No API key required.

Usage:
    python step1_market_data.py                 # list active markets
    python step1_market_data.py <market-slug>   # quote + order book for one market
"""

import sys

from config import public_client


def price(amount) -> str:
    return amount["value"] if amount else "none"


def list_markets(client) -> None:
    resp = client.markets.list({"limit": 15, "active": True, "closed": False})
    print(f"{'SLUG':<55} {'VOLUME':>12} {'LIQUIDITY':>12}")
    for m in resp.get("markets", []):
        print(f"{m.get('slug', ''):<55} {m.get('volume', 0):>12,.0f} {m.get('liquidity', 0):>12,.0f}")
    print("\nPick a slug and run: python step1_market_data.py <slug>")


def show_market(client, slug: str) -> None:
    market = client.markets.retrieve_by_slug(slug)["market"]
    print(f"\n{market.get('title')}  ({slug})")
    print(f"Rules: {market.get('description', '')[:300]}...\n")

    bbo = client.markets.bbo(slug)["marketData"]
    bid, ask = bbo.get("bestBid"), bbo.get("bestAsk")
    print(f"Best bid: {price(bid)}   Best ask: {price(ask)}   Last: {price(bbo.get('lastTradePx'))}")
    if bid and ask:
        spread = float(ask["value"]) - float(bid["value"])
        print(f"Spread: {spread:.2f}  <- you pay this every round trip as a taker")

    book = client.markets.book(slug)["marketData"]
    print("\nTop of book")
    print(f"{'BID QTY':>10} {'BID':>6} | {'ASK':<6} {'ASK QTY':<10}")
    bids, offers = book.get("bids", [])[:5], book.get("offers", [])[:5]
    for i in range(max(len(bids), len(offers))):
        b = bids[i] if i < len(bids) else None
        o = offers[i] if i < len(offers) else None
        print(
            f"{b['qty'] if b else '':>10} {b['px']['value'] if b else '':>6} | "
            f"{o['px']['value'] if o else '':<6} {o['qty'] if o else '':<10}"
        )


if __name__ == "__main__":
    c = public_client()
    try:
        show_market(c, sys.argv[1]) if len(sys.argv) > 1 else list_markets(c)
    finally:
        c.close()
