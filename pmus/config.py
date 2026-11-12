"""Loads your key and settings from .env (in the repo root), so secrets never live in your code.

One key from polymarket.us/developer does everything in this repo: it signs your REST
calls and opens both WebSockets. The key implies your account, so there is no account ID.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from polymarket_us import AsyncPolymarketUS, PolymarketUS

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def setting(name: str, default: str = "") -> str:
    """Read a value from .env, ignoring inline comments like '0.095   # note'."""
    return os.getenv(name, default).split("#")[0].strip()


def keys() -> tuple[str, str]:
    key_id, secret = setting("POLYMARKET_KEY_ID"), setting("POLYMARKET_SECRET_KEY")
    if not key_id or not secret or key_id.startswith("your-"):
        sys.exit("No API key found. Copy .env.example to .env and paste in your Key ID and Secret Key.")
    return key_id, secret


def public_client() -> PolymarketUS:
    """Public market data. No key needed."""
    return PolymarketUS()


def private_client() -> PolymarketUS:
    """Your account. The SDK signs every request with your key."""
    key_id, secret = keys()
    return PolymarketUS(key_id=key_id, secret_key=secret)


def async_private_client() -> AsyncPolymarketUS:
    """For the WebSockets, which are async. Both sockets need your key."""
    key_id, secret = keys()
    return AsyncPolymarketUS(key_id=key_id, secret_key=secret)
