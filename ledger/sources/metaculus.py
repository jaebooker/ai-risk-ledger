"""Metaculus community forecast (recency-weighted median).

Uses the official API when METACULUS_TOKEN is set (recommended; create one at
https://www.metaculus.com/accounts/settings/). Without a token it falls back to the
site's public api-proxy path, which the Metaculus web app itself uses.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from ..http import get_json
from . import Reading


def _post(spec, get):
    qid = spec["id"]
    token = os.environ.get("METACULUS_TOKEN")
    if token:
        return get(f"https://www.metaculus.com/api/posts/{qid}/?with_cp=true",
                   headers={"Authorization": f"Token {token}"})
    return get(f"https://www.metaculus.com/api-proxy/posts/{qid}/?with_cp=true")


def _agg(post):
    q = post.get("question") or {}
    return (q.get("aggregations") or {}).get("recency_weighted") or {}


def current(spec, get=get_json) -> Reading:
    post = _post(spec, get)
    agg = _agg(post)
    latest = agg.get("latest") or (agg.get("history") or [None])[-1]
    if not latest or not latest.get("centers"):
        raise ValueError(f"metaculus {spec['id']}: no community prediction")
    q = post.get("question") or {}
    resolved = q.get("resolution") if q.get("resolution") not in (None, "") else None
    return Reading(p=float(latest["centers"][0]), n=post.get("nr_forecasters"), resolved=resolved)


def history(spec, get=get_json):
    agg = _agg(_post(spec, get))
    out = {}
    for h in agg.get("history") or []:
        if not h.get("centers"):
            continue
        d = datetime.fromtimestamp(h["start_time"], tz=timezone.utc).date().isoformat()
        out[d] = float(h["centers"][0])  # last value of each day wins
    return sorted(out.items())
