"""Offline check for the whole repo. No internet and no API key needed.

    python check_everything.py

It runs every script against a fake Polymarket that answers with the documented response
shapes, so you know your install works before you touch your real account.
"""

import importlib.util
import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ.update({"TAKER_FEE_RATE": "0.095", "MAX_LIVE_CONTRACTS": "1", "HOLD_SECONDS": "0"})


def load(path: str):
    spec = importlib.util.spec_from_file_location(Path(path).stem, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def px(v: str) -> dict:
    return {"value": v, "currency": "USD"}


SLUG = "sample-nfl-game-team-a-team-b"
MARKET = {"market": {
    "slug": SLUG, "question": "Will Team A beat Team B?", "eventSlug": "sample-nfl-game",
    "description": "Resolves YES if Team A wins.", "active": True, "closed": False,
    "orderPriceMinTickSize": 0.005, "minimumTradeQty": 0.01, "feeCoefficient": 1,
    "marketSides": [{"long": True, "description": "Team A"}, {"long": False, "description": "Team B"}],
}}
BOOK = {"marketData": {"marketSlug": SLUG, "state": "MARKET_STATE_OPEN",
                       "bids": [{"px": px("0.48"), "qty": "350"}, {"px": px("0.475"), "qty": "900"}],
                       "offers": [{"px": px("0.50"), "qty": "120"}, {"px": px("0.505"), "qty": "400"}]}}


class Fake:
    """Answers like the SDK does, with documented shapes. Records every order call."""

    def __init__(self):
        self.created, self.cancelled, self.open = [], [], []
        outer = self

        class Series:
            def list(self, p=None): return {"series": [{"id": 7, "title": "NFL 2026-27", "slug": "nfl-2026"}]}

        class Events:
            def list(self, p=None): return {"events": [{"title": "Team A vs Team B", "slug": "sample-nfl-game"}]}
            def retrieve_by_slug(self, s): return {"event": {"title": "Team A vs Team B", "markets": [
                {"title": "Team A vs Team B", "outcome": "Team A", "slug": SLUG}]}}

        class Markets:
            def retrieve_by_slug(self, s): return MARKET
            def book(self, s): return BOOK

        class Account:
            def balances(self): return {"balances": [{"currentBalance": 500.0, "buyingPower": 460.0,
                                                      "marginRequirement": 40.0, "openOrders": 0.0}]}

        class Portfolio:
            def positions(self, p=None): return {"positions": {SLUG: {"netPosition": "-40", "avgPx": px("0.52"),
                                                                      "cashValue": px("19.20")}}}

        class Orders:
            def list(self, p=None): return {"orders": [{"id": i} for i in outer.open]}
            def preview(self, p): return {"order": {"marketSlug": p["request"]["marketSlug"], "state": "ORDER_STATE_PENDING_NEW"}}
            def create(self, p):
                outer.created.append(p); outer.open.append("ord-1")
                return {"id": "ord-1", "executions": [{"type": "EXECUTION_TYPE_NEW"}]}
            def cancel(self, oid, p): outer.cancelled.append((oid, p)); outer.open.remove(oid)
            def retrieve(self, oid): return {"order": {"id": oid, "state": "ORDER_STATE_CANCELED", "cumQuantity": 0}}

        self.series, self.events, self.markets = Series(), Events(), Markets()
        self.account, self.portfolio, self.orders = Account(), Portfolio(), Orders()

    def close(self): pass


def quiet(fn, *a, **k):
    buf = io.StringIO()
    with redirect_stdout(buf):
        out = fn(*a, **k)
    return out, buf.getvalue()


def main() -> None:
    import polymarket_us  # noqa: F401  (the SDK is installed)

    from pmus.money import on_step, on_tick, taker_fee
    from pmus.orders import Ticket

    # Fee formula: the two worked examples on docs.polymarket.us/fees
    assert taker_fee(0.095, 100, 0.50) == 2.38 and taker_fee(0.0695, 100, 0.10) == 0.63
    assert on_tick(0.555, 0.005) and not on_tick(0.552, 0.005)
    assert on_step(0.5, 0.01) and not on_step(0.005, 0.01)
    print("1/6 fee formula, price steps, and contract steps match the docs")

    t = Ticket(SLUG, "buy-no", 0.17, 1)
    assert t.intent == "ORDER_INTENT_BUY_SHORT" and t.yes_price == 0.83
    r = t.request()
    assert r["price"] == {"value": "0.83", "currency": "USD"} and r["participateDontInitiate"] is True
    assert Ticket(SLUG, "buy-yes", 0.452, 1).problems(0.005, 0.01)
    print("2/6 orders: buying NO at 0.17 sends BUY_SHORT at YES price 0.83")

    fake = Fake()
    browse = load("video1_setup/step1_browse.py")
    quiet(browse.list_series, fake); quiet(browse.list_events, fake, 7); quiet(browse.list_markets, fake, "sample-nfl-game")
    _, out = quiet(load("video1_setup/step2_market.py").show, fake, SLUG)
    assert "Team A" in out and "0.005" in out and "$2.38" in out
    print("3/6 video 1: browse series, events, markets, and read one market")

    _, out = quiet(load("video2_account_live/step1_account.py").show, fake)
    assert "SHORT (NO)" in out and "40 contracts" in out
    priv = load("video2_account_live/step3_private_stream.py")
    _, out = quiet(priv.on_order("update"), {"orderSubscriptionUpdate": {"execution": {
        "type": "EXECUTION_TYPE_FILL", "lastShares": "1", "lastPx": px("0.48")}}})
    assert "FILL" in out and "0.48" in out
    load("video2_account_live/step2_market_stream.py")
    print("4/6 video 2: account with a short position, and a fill seen on the private socket")

    pv = load("video3_orders/step1_preview.py")
    (ticket, _), _ = quiet(pv.build, fake, [SLUG, "buy-yes", "0.05", "1"])
    quiet(pv.explain, fake, ticket); quiet(pv.preview, fake, ticket)
    print("5/6 video 3: build and preview an order")

    pc = load("video3_orders/step2_place_and_cancel.py")
    oid, out = quiet(pc.place_and_cancel, fake, ticket, confirm=lambda _: "PLACE")
    assert oid == "ord-1" and fake.cancelled == [("ord-1", {"marketSlug": SLUG})] and not fake.open
    _, out = quiet(pc.place_and_cancel, Fake(), ticket, confirm=lambda _: "no")
    assert "Not sent" in out
    try:
        quiet(pc.place_and_cancel, Fake(), Ticket(SLUG, "buy-yes", 0.05, 5), confirm=lambda _: "PLACE")
        raise AssertionError("should refuse more than MAX_LIVE_CONTRACTS")
    except SystemExit:
        pass
    print("6/6 video 3: place, confirm, and cancel, with every guard rail")
    print("\nAll offline checks passed.")


if __name__ == "__main__":
    main()
