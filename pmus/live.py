"""Shared WebSocket plumbing: heartbeats, reconnects, and readable one-line printing.

Polymarket US sends {"heartbeat": {}} on a timer. If they stop, the connection is stale:
close it and reconnect, waiting a little longer each time.
"""

import asyncio
import json
import time

STALE_AFTER = 45  # seconds without any message, heartbeat included


def short(obj, limit: int = 160) -> str:
    text = json.dumps(obj, separators=(",", ":"))
    return text if len(text) <= limit else text[: limit - 3] + "..."


def find_all(obj, key: str):
    """Every value stored under `key` anywhere inside a nested message."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield v
            yield from find_all(v, key)
    elif isinstance(obj, list):
        for v in obj:
            yield from find_all(v, key)


async def run_forever(open_socket, minutes: float | None = None) -> None:
    """open_socket() connects, subscribes, and returns the socket. We watch it and reconnect."""
    deadline = time.time() + minutes * 60 if minutes else None
    backoff = 1
    while deadline is None or time.time() < deadline:
        ws, last = None, {"t": time.time()}
        try:
            ws = await open_socket(last)
            backoff = 1
            while ws.is_connected and (deadline is None or time.time() < deadline):
                await asyncio.sleep(1)
                if time.time() - last["t"] > STALE_AFTER:
                    print(f"No heartbeat for {STALE_AFTER}s. Reconnecting.")
                    break
        except Exception as e:  # network drop, auth error, anything: report and retry
            print(f"Connection problem: {e}")
        finally:
            if ws is not None:
                await ws.close()
        if deadline is not None and time.time() >= deadline:
            break
        print(f"Reconnecting in {backoff}s...")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)
