"""Shared helpers for recorded market data.

Raw files are JSON Lines, one event per line, under data/raw/<slug>/<date>.jsonl:
    {"ts": <nanoseconds, your clock>, "type": "book" | "trade", "slug": ..., "data": {...}}
"data" is exactly what Polymarket US sent, so nothing is lost.
"""

import json
import time
from pathlib import Path

from pmus.config import DATA_DIR

RAW = DATA_DIR / "raw"
PARQUET = DATA_DIR / "parquet"


def raw_path(slug: str, ts_ns: int | None = None) -> Path:
    day = time.strftime("%Y-%m-%d", time.gmtime((ts_ns or time.time_ns()) / 1e9))
    path = RAW / slug / f"{day}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def append_event(slug: str, kind: str, data: dict, ts_ns: int | None = None) -> None:
    ts_ns = ts_ns or time.time_ns()
    with open(raw_path(slug, ts_ns), "a") as f:
        f.write(json.dumps({"ts": ts_ns, "type": kind, "slug": slug, "data": data}) + "\n")


def read_events(slug: str):
    for path in sorted((RAW / slug).glob("*.jsonl")):
        with open(path) as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def amount(x) -> float | None:
    """Polymarket US sends prices as {"value": "0.55", "currency": "USD"}. Sizes are strings."""
    if x is None:
        return None
    if isinstance(x, dict):
        x = x.get("value")
    return float(x) if x not in (None, "") else None


def levels(side: list | None) -> tuple[list[float], list[float]]:
    """Order book side -> (prices, sizes)."""
    px, qty = [], []
    for lvl in side or []:
        p, q = amount(lvl.get("px")), amount(lvl.get("qty"))
        if p is not None and q:
            px.append(p)
            qty.append(q)
    return px, qty
