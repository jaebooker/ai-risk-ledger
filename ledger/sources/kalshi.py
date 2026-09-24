"""Kalshi (real money, CFTC-regulated). Probability is the YES bid/ask midpoint."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from ..http import get_json
from . import Reading

API = "https://api.elections.kalshi.com/trade-api/v2"


def _d(obj, key):
    """Read a price in dollars from either the *_dollars string field or the legacy cents int."""
    if obj is None:
        return None
    if obj.get(f"{key}_dollars") not in (None, ""):
        return float(obj[f"{key}_dollars"])
    if obj.get(key) is not None:
        return float(obj[key]) / 100
    return None


def current(spec, get=get_json) -> Reading:
    m = get(f"{API}/markets/{spec['ticker']}")["market"]
    bid, ask = _d(m, "yes_bid"), _d(m, "yes_ask")
    if bid is not None and ask and ask > 0:
        p = (bid + ask) / 2
    else:
        p = _d(m, "last_price")
    if p is None:
        raise ValueError(f"kalshi {spec['ticker']}: no price")
    vol = m.get("volume_fp") or m.get("volume")
    closed = m.get("status") not in ("active", "open")
    resolved = m.get("result") or None
    return Reading(p=p, n=float(vol) if vol not in (None, "") else None, closed=closed, resolved=resolved)


def history(spec, get=get_json):
    m = get(f"{API}/markets/{spec['ticker']}")["market"]
    start = int(datetime.fromisoformat(m["open_time"].replace("Z", "+00:00")).timestamp())
    end = int(time.time())
    daily = {}
    # Kalshi caps candles per request; walk in ~2-year windows.
    step = 86400 * 700
    s = start
    while s < end:
        e = min(end, s + step)
        url = (f"{API}/series/{spec['series']}/markets/{spec['ticker']}/candlesticks"
               f"?start_ts={s}&end_ts={e}&period_interval=1440")
        for c in get(url).get("candlesticks") or []:
            bid, ask = _d(c.get("yes_bid"), "close"), _d(c.get("yes_ask"), "close")
            p = (bid + ask) / 2 if bid is not None and ask else _d(c.get("price"), "close")
            if p is None:
                continue
            d = datetime.fromtimestamp(c["end_period_ts"], tz=timezone.utc).date().isoformat()
            daily[d] = p
        s = e
    return sorted(daily.items())
