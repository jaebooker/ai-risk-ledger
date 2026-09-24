"""Manifold Markets (play money). Binary markets only."""
from __future__ import annotations

from datetime import datetime, timezone

from ..http import get_json, polite_pause
from . import Reading

API = "https://api.manifold.markets/v0"


def current(spec, get=get_json) -> Reading:
    m = get(f"{API}/slug/{spec['slug']}")
    if "probability" not in m:
        raise ValueError(f"manifold {spec['slug']}: not a binary market")
    resolved = m.get("resolution") if m.get("isResolved") else None
    return Reading(p=float(m["probability"]), n=m.get("uniqueBettorCount"), resolved=resolved)


def history(spec, get=get_json, max_pages: int = 60):
    """Daily closing probability reconstructed from the bet stream."""
    m = get(f"{API}/slug/{spec['slug']}")
    bets, before = [], None
    for _ in range(max_pages):
        url = f"{API}/bets?contractId={m['id']}&limit=1000" + (f"&before={before}" if before else "")
        page = get(url)
        if not page:
            break
        bets.extend(page)
        before = page[-1]["id"]
        if len(page) < 1000:
            break
        polite_pause()
    daily = {}
    for b in sorted(bets, key=lambda b: b["createdTime"]):
        if b.get("isCancelled") or not isinstance(b.get("probAfter"), (int, float)):
            continue
        d = datetime.fromtimestamp(b["createdTime"] / 1000, tz=timezone.utc).date().isoformat()
        daily[d] = float(b["probAfter"])
    return sorted(daily.items())
