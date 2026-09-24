"""Assemble site/data.json from the registry, history files and expert estimates."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from .store import ROOT, load_experts, load_questions, read_history

SITE = ROOT / "site"


def thin(rows: list[dict], daily_days: int = 120) -> list[list]:
    """Keep daily points for the recent window, one point per week before that.

    Keeps the published file small while preserving shape. The CSVs keep everything.
    """
    if not rows:
        return []
    last = date.fromisoformat(rows[-1]["date"])
    cut = (last - timedelta(days=daily_days)).isoformat()
    out, seen_weeks = [], {}
    for r in rows:
        if r["date"] >= cut:
            out.append([r["date"], round(r["p"], 4)])
        else:
            y, w, _ = date.fromisoformat(r["date"]).isocalendar()
            seen_weeks[(y, w)] = [r["date"], round(r["p"], 4)]
    older = sorted(seen_weeks.values())
    return older + out


def value_at(hist: list[list], d: str):
    v = None
    for dd, p in hist:
        if dd <= d:
            v = p
        else:
            break
    return v


def derive(q: dict, by_id: dict) -> tuple[float | None, list[list]]:
    parts = [by_id[i] for i in q["source"]["of"]]
    if any(not p.get("hist") for p in parts):
        return None, []
    dates = sorted({d for p in parts for d, _ in p["hist"]})
    hist = []
    for d in dates:
        vals = [value_at(p["hist"], d) for p in parts]
        if None in vals:
            continue
        prod = 1.0
        for v in vals:
            prod *= v
        hist.append([d, round(prod, 5)])
    cur = 1.0
    for p in parts:
        cur *= p["p"]
    return round(cur, 5), hist


def build() -> dict:
    qs = load_questions()
    items, by_id = [], {}
    for q in qs:
        it = {k: v for k, v in q.items() if k != "source"}
        it["nu"] = q.get("unit") or ""
        if q.get("conditional"):
            it["cond"] = True
        if q["source"]["type"] != "derived":
            rows = read_history(q["id"])
            it["hist"] = thin(rows)
            it["p"] = rows[-1]["p"] if rows else None
            ns = [r["n"] for r in rows if r["n"] is not None]
            it["n"] = ns[-1] if ns else None
        items.append(it)
        by_id[q["id"]] = it
    for q, it in zip(qs, items):
        if q["source"]["type"] == "derived":
            it["p"], it["hist"] = derive(q, by_id)
            it["n"] = None
    items = [it for it in items if it.get("p") is not None]
    last = max((it["hist"][-1][0] for it in items if it.get("hist")), default=None)
    ex = load_experts()
    data = {
        "updated": last or date.today().isoformat(),
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "items": items,
        "studies": ex["studies"],
        "people": ex["people"],
    }
    SITE.mkdir(exist_ok=True)
    (SITE / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return data
