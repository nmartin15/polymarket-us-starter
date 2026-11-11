"""Loads settings from .env so secrets never live in your code."""

import os

from dotenv import load_dotenv
from polymarket_us import PolymarketUS

load_dotenv()


def public_client() -> PolymarketUS:
    """No keys needed. Market data only."""
    return PolymarketUS()


def private_client() -> PolymarketUS:
    """Needs your API key. Can read your account."""
    key_id = os.getenv("POLYMARKET_KEY_ID")
    secret = os.getenv("POLYMARKET_SECRET_KEY")
    if not key_id or not secret or "your-" in key_id:
        raise SystemExit("Missing keys. Copy .env.example to .env and add your keys.")
    return PolymarketUS(key_id=key_id, secret_key=secret)


def setting(name: str, default: str) -> str:
    # Strip inline comments like "0.50   # note"
    return os.getenv(name, default).split("#")[0].strip()
