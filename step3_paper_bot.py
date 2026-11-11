"""Step 3: A paper-trading bot skeleton. It reads the live market but NEVER sends an order.

The strategy is intentionally simple so you can see every moving part:
  You supply FAIR_VALUE: your own probability that the market resolves YES.
  If the ask is below your fair value by more than fees + MIN_EDGE, buy.
  If the bid is above your fair value by more than fees + MIN_EDGE, sell what you hold.

The hard part of making money here is not this code. It's having a FAIR_VALUE
that is more accurate than the market's. The bot just enforces your discipline.

Stop the bot any time: Ctrl+C, or create a file named STOP in this folder.
"""

import os
import time

from config import public_client, setting
from paper_broker import PaperBroker, taker_fee

SLUG = setting("MARKET_SLUG", "")
FAIR = float(setting("FAIR_VALUE", "0.50"))
MIN_EDGE = float(setting("MIN_EDGE", "0.04"))
FEE_RATE = float(setting("TAKER_FEE_RATE", "0.05"))
SIZE = float(setting("ORDER_SIZE", "10"))
MAX_POS = float(setting("MAX_POSITION", "50"))
MAX_LOSS = float(setting("MAX_DAILY_LOSS", "25"))
POLL = float(setting("POLL_SECONDS", "10"))


def top_of_book(client, slug):
    """Returns (bid, bid_qty, ask, ask_qty, state). Prices are 0 to 1."""
    book = client.markets.book(slug)["marketData"]
    bids, offers = book.get("bids") or [], book.get("offers") or []
    bid = float(bids[0]["px"]["value"]) if bids else None
    ask = float(offers[0]["px"]["value"]) if offers else None
    bid_qty = float(bids[0]["qty"]) if bids else 0
    ask_qty = float(offers[0]["qty"]) if offers else 0
    return bid, bid_qty, ask, ask_qty, book.get("state")


def kill_switch(broker, bid) -> str | None:
    if os.path.exists("STOP"):
        return "STOP file found"
    if bid is not None and broker.total_pnl(bid) <= -MAX_LOSS:
        return f"daily loss limit hit ({broker.total_pnl(bid):.2f})"
    return None


def decide(bid, ask, position):
    """The 'strategy'. Returns ('BUY' | 'SELL' | None, reason)."""
    if ask is not None:
        buy_edge = FAIR - ask - taker_fee(1, ask, FEE_RATE)
        if buy_edge > MIN_EDGE and position + SIZE <= MAX_POS:
            return "BUY", f"ask {ask:.2f} vs fair {FAIR:.2f}, edge after fee {buy_edge:.3f}"
    if bid is not None and position > 0:
        sell_edge = bid - FAIR - taker_fee(1, bid, FEE_RATE)
        if sell_edge > MIN_EDGE:
            return "SELL", f"bid {bid:.2f} vs fair {FAIR:.2f}, edge after fee {sell_edge:.3f}"
    return None, "no edge"


def run(client, max_loops: int | None = None) -> PaperBroker:
    if not SLUG or "paste" in SLUG:
        raise SystemExit("Set MARKET_SLUG in .env (find one with step1_market_data.py).")
    broker = PaperBroker(fee_rate=FEE_RATE)
    print(f"PAPER MODE. Market {SLUG}. Fair value {FAIR:.2f}. No real orders will be sent.\n")
    loops = 0
    while max_loops is None or loops < max_loops:
        loops += 1
        try:
            bid, bid_qty, ask, ask_qty, state = top_of_book(client, SLUG)
        except Exception as e:  # network blip: wait and retry, don't crash
            print(f"data error: {e}; retrying")
            time.sleep(POLL)
            continue

        if state and state != "MARKET_STATE_OPEN":
            print(f"market state {state}; standing down")
            break

        reason = kill_switch(broker, bid)
        if reason:
            print(f"KILL SWITCH: {reason}")
            break

        action, why = decide(bid, ask, broker.position)
        mark = broker.total_pnl(bid) if bid is not None else 0
        print(f"bid {bid}  ask {ask}  pos {broker.position:g}  P&L {mark:+.2f}  -> {action or 'hold'} ({why})")
        if action == "BUY":
            broker.buy(SIZE, ask, ask_qty)
        elif action == "SELL":
            broker.sell(SIZE, bid, bid_qty)

        time.sleep(POLL)

    print(f"\nDone. Position {broker.position:g}, realized {broker.realized_pnl:+.2f}, fees {broker.fees_paid:.2f}")
    print(f"Every paper trade is in {broker.log_path}")
    return broker


if __name__ == "__main__":
    c = public_client()
    try:
        run(c)
    except KeyboardInterrupt:
        print("\nStopped by you.")
    finally:
        c.close()
