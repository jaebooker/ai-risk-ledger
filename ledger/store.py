"""Read and write the registry and per-question history files."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HIST = DATA / "history"


def load_questions() -> list[dict]:
    return json.loads((DATA / "questions.json").read_text())["questions"]


def load_experts() -> dict:
    return json.loads((DATA / "experts.json").read_text())


def read_history(qid: str) -> list[dict]:
    """Rows of {date, p, n}. n is None except where recorded."""
    path = HIST / f"{qid}.csv"
    if not path.exists():
        return []
    rows = []
    with path.open() as fh:
        for r in csv.DictReader(fh):
            rows.append({
                "date": r["date"],
                "p": float(r["p"]),
                "n": float(r["n"]) if r.get("n") not in (None, "") else None,
            })
    return rows


def write_history(qid: str, rows: list[dict]) -> None:
    HIST.mkdir(parents=True, exist_ok=True)
    rows = sorted({r["date"]: r for r in rows}.values(), key=lambda r: r["date"])
    with (HIST / f"{qid}.csv").open("w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["date", "p", "n"])
        for r in rows:
            n = r.get("n")
            w.writerow([r["date"], round(r["p"], 5), "" if n is None else (int(n) if float(n).is_integer() else round(n, 2))])


def upsert(qid: str, date: str, p: float, n: float | None) -> float | None:
    """Set today's reading. Returns the previous reading's p (before today), if any."""
    rows = read_history(qid)
    prev = [r for r in rows if r["date"] < date]
    rows = [r for r in rows if r["date"] != date]
    rows.append({"date": date, "p": p, "n": n})
    write_history(qid, rows)
    return prev[-1]["p"] if prev else None


def merge_backfill(qid: str, points: list[tuple[str, float]]) -> int:
    """Add backfilled points for dates we don't already have. Existing rows win."""
    rows = read_history(qid)
    have = {r["date"] for r in rows}
    added = 0
    for d, p in points:
        if d not in have:
            rows.append({"date": d, "p": p, "n": None})
            added += 1
    write_history(qid, rows)
    return added
