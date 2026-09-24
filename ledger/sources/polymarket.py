"""Polymarket (real money). Prices come from the CLOB price history of the YES token.

The spec needs `token` (YES clobTokenId). If it is missing, it is looked up from the
Gamma API using `event` (event slug) and optional `market` (substring of the market
question, for multi-market events). Gamma's search endpoints can serve stale prices, so
they are only used for metadata, never for the probability itself.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from ..http import get_json
from . import Reading

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


def _event(spec, get):
    ev = get(f"{GAMMA}/events?slug={spec['event']}")
    if not ev:
        raise ValueError(f"polymarket {spec['event']}: event not found")
    return ev[0]


def _market(spec, ev):
    ms = ev.get("markets") or []
    if spec.get("market"):
        ms = [m for m in ms if spec["market"] in m.get("question", "")]
    if not ms:
        raise ValueError(f"polymarket {spec['event']}: market not found")
    return ms[0]


def resolve_token(spec, get=get_json) -> str:
    if spec.get("token"):
        return spec["token"]
    m = _market(spec, _event(spec, get))
    return json.loads(m["clobTokenIds"])[0]


def current(spec, get=get_json) -> Reading:
    token = resolve_token(spec, get)
    h = (get(f"{CLOB}/prices-history?market={token}&interval=1d&fidelity=60") or {}).get("history") or []
    ev = _event(spec, get)
    m = _market(spec, ev)
    closed = bool(m.get("closed"))
    if h:
        p = float(h[-1]["p"])
    else:  # no trades in the last day: fall back to the order-book midpoint
        bid, ask = m.get("bestBid"), m.get("bestAsk")
        if bid is None or ask is None:
            raise ValueError(f"polymarket {spec['event']}: no price")
        p = (float(bid) + float(ask)) / 2
    return Reading(p=p, n=float(ev.get("volume") or 0) or None, closed=closed)


def history(spec, get=get_json):
    token = resolve_token(spec, get)
    h = (get(f"{CLOB}/prices-history?market={token}&interval=max&fidelity=1440") or {}).get("history") or []
    daily = {}
    for pt in h:
        d = datetime.fromtimestamp(pt["t"], tz=timezone.utc).date().isoformat()
        daily[d] = float(pt["p"])
    return sorted(daily.items())
