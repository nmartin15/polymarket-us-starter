"""Loads settings from .env (in the repo root) so secrets never live in your code."""

import os
from pathlib import Path

from dotenv import load_dotenv
from polymarket_us import PolymarketUS

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
load_dotenv(ROOT / ".env")


def public_client() -> PolymarketUS:
    """No keys needed. Market data only."""
    return PolymarketUS()


def keys() -> tuple[str, str]:
    key_id = os.getenv("POLYMARKET_KEY_ID")
    secret = os.getenv("POLYMARKET_SECRET_KEY")
    if not key_id or not secret or "your-" in key_id:
        raise SystemExit("Missing keys. Copy .env.example to .env and add your keys.")
    return key_id, secret


def private_client() -> PolymarketUS:
    """Needs your API key. Can read your account."""
    key_id, secret = keys()
    return PolymarketUS(key_id=key_id, secret_key=secret)


def setting(name: str, default: str) -> str:
    # Strip inline comments like "0.50   # note"
    return os.getenv(name, default).split("#")[0].strip()
