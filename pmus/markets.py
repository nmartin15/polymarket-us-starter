"""Reading a market the way the API describes it, instead of guessing from the slug.

Hierarchy: a series (a season, a recurring topic) holds events (one game, one election),
and an event holds markets. Each market is one instrument with a YES (long) side and a
NO (short) side. Only the long side trades directly; NO is synthetic, so every price you
send is the YES price. In a two-team slug, the first team is the YES side.
"""

from pmus.money import num


def market_of(response: dict) -> dict:
    """retrieve_by_slug returns {"market": {...}}; unwrap it either way."""
    return response.get("market", response)


def tick_size(m: dict) -> float:
    return num(m.get("orderPriceMinTickSize")) or 0.01


def min_qty(m: dict) -> float:
    return num(m.get("minimumTradeQty")) or 1.0


def sides(m: dict) -> tuple[str, str]:
    """(YES side, NO side) labels from marketSides, falling back to Yes / No."""
    yes, no = "Yes", "No"
    for s in m.get("marketSides") or []:
        label = s.get("description") or (s.get("team") or {}).get("name") or s.get("identifier") or ""
        if s.get("long") is True and label:
            yes = label
        elif s.get("long") is False and label:
            no = label
    return yes, no


def describe(m: dict) -> list[tuple[str, str]]:
    """The facts you need before you trade a market, as label/value pairs."""
    yes, no = sides(m)
    fc = m.get("feeCoefficient")
    rows = [
        ("Question", m.get("question") or m.get("title") or ""),
        ("Slug", m.get("slug", "")),
        ("Event", m.get("eventSlug") or ""),
        ("YES (long) side", yes),
        ("NO (short) side", no),
        ("Price step (orderPriceMinTickSize)", str(tick_size(m))),
        ("Smallest order (minimumTradeQty)", f"{min_qty(m)} contracts"),
        ("Fee coefficient on this market", "not listed" if fc is None else str(fc)),
        ("Open for trading", "yes" if m.get("active") and not m.get("closed") else "no"),
    ]
    return rows


def best(book: dict) -> tuple:
    """(best bid, bid size, best ask, ask size) from a book, sorted best first by the API."""
    bids, offers = book.get("bids") or [], book.get("offers") or []
    bid = num(bids[0]["px"]) if bids else None
    ask = num(offers[0]["px"]) if offers else None
    return bid, (num(bids[0]["qty"]) if bids else 0.0), ask, (num(offers[0]["qty"]) if offers else 0.0)
