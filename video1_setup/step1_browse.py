"""Video 1, Step 1: Browse Polymarket US the way it's organized. No API key needed.

    python video1_setup/step1_browse.py                       # series (a season, a recurring topic)
    python video1_setup/step1_browse.py --series 42           # the events in one series
    python video1_setup/step1_browse.py --event <event-slug>  # the markets in one event

Series -> event -> market. Each market is one thing you can trade.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # find the pmus folder

from pmus.config import public_client  # noqa: E402


def list_series(c) -> None:
    rows = c.series.list({"limit": 25, "active": True}).get("series", [])
    print(f"{'ID':>6}  {'SERIES':<45} SLUG")
    for s in rows:
        print(f"{s.get('id', ''):>6}  {s.get('title', '')[:45]:<45} {s.get('slug', '')}")
    print("\nNext: python video1_setup/step1_browse.py --series <ID>")


def list_events(c, series_id: int) -> None:
    rows = c.events.list({"limit": 25, "active": True, "closed": False, "seriesId": [series_id]}).get("events", [])
    print(f"{'EVENT':<50} SLUG")
    for e in rows:
        print(f"{e.get('title', '')[:50]:<50} {e.get('slug', '')}")
    print("\nNext: python video1_setup/step1_browse.py --event <event-slug>")


def list_markets(c, event_slug: str) -> None:
    e = c.events.retrieve_by_slug(event_slug).get("event", {})
    print(f"{e.get('title', '')}\n")
    print(f"{'MARKET':<45} {'OUTCOME':<14} SLUG")
    for m in e.get("markets", []):
        print(f"{m.get('title', '')[:45]:<45} {str(m.get('outcome', ''))[:14]:<14} {m.get('slug', '')}")
    print("\nNext: python video1_setup/step2_market.py <market-slug>")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", type=int)
    ap.add_argument("--event")
    a = ap.parse_args()
    client = public_client()
    try:
        if a.event:
            list_markets(client, a.event)
        elif a.series is not None:
            list_events(client, a.series)
        else:
            list_series(client)
    finally:
        client.close()
