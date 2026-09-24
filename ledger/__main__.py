"""Command line entry point.

    python -m ledger update            # fetch today's value for every question, then build
    python -m ledger backfill [--id X] # pull full history from each source (merges; never overwrites)
    python -m ledger build             # rebuild site/data.json only
    python -m ledger check             # validate data/questions.json
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from . import store
from .build import build
from .http import polite_pause
from .sources import ADAPTERS

MAX_JUMP = float(os.environ.get("LEDGER_MAX_JUMP", "0.30"))
CATS = {"catastrophe", "misuse", "governance", "context"}


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def summary(lines: list[str]) -> None:
    text = "\n".join(lines)
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as fh:
            fh.write(text + "\n")


def cmd_update(args) -> int:
    qs = store.load_questions()
    d = today()
    ok, skipped, failed, moves = 0, [], [], []
    for q in qs:
        src = q["source"]
        if src["type"] == "derived" or q.get("retired"):
            continue
        if args.id and q["id"] not in args.id:
            continue
        try:
            r = ADAPTERS[src["type"]].current(src)
        except Exception as e:  # noqa: BLE001 - one bad source must not stop the run
            failed.append(f"- `{q['id']}`: {e}")
            continue
        finally:
            polite_pause()
        if not 0 <= r.p <= 1:
            failed.append(f"- `{q['id']}`: value {r.p} out of range")
            continue
        hist = store.read_history(q["id"])
        prev = [h for h in hist if h["date"] < d]
        if prev and abs(r.p - prev[-1]["p"]) > MAX_JUMP and not r.resolved and not args.force:
            skipped.append(f"- `{q['id']}`: {prev[-1]['p']:.3f} → {r.p:.3f} exceeds {MAX_JUMP}; kept old value")
            continue
        old = store.upsert(q["id"], d, r.p, r.n)
        if old is not None:
            moves.append((abs(r.p - old), q["id"], old, r.p))
        ok += 1
    build()
    lines = [f"## Ledger update {d}", f"Updated {ok} questions."]
    if moves:
        lines.append("\n**Largest moves since previous reading**")
        for m, qid, a, b in sorted(moves, reverse=True)[:5]:
            lines.append(f"- `{qid}`: {a:.1%} → {b:.1%}")
    if skipped:
        lines += ["\n**Held back (sanity check)**"] + skipped
    if failed:
        lines += ["\n**Failed**"] + failed
    summary(lines)
    # Fail the job only if most sources failed, so one flaky API doesn't block publishing.
    return 1 if failed and len(failed) > ok else 0


def cmd_backfill(args) -> int:
    for q in store.load_questions():
        src = q["source"]
        if src["type"] == "derived" or (args.id and q["id"] not in args.id):
            continue
        try:
            pts = ADAPTERS[src["type"]].history(src)
            added = store.merge_backfill(q["id"], pts)
            print(f"{q['id']}: {len(pts)} points from source, {added} new")
        except Exception as e:  # noqa: BLE001
            print(f"{q['id']}: FAILED {e}", file=sys.stderr)
        polite_pause()
    build()
    return 0


def cmd_build(args) -> int:
    data = build()
    print(f"built site/data.json: {len(data['items'])} questions, updated {data['updated']}")
    return 0


def cmd_check(args) -> int:
    qs = store.load_questions()
    errors, ids = [], set()
    required = {"metaculus": ["id"], "manifold": ["slug"], "polymarket": ["event"],
                "kalshi": ["ticker", "series"], "derived": ["of"]}
    for q in qs:
        for k in ("id", "src", "cat", "q", "h", "url", "source"):
            if k not in q:
                errors.append(f"{q.get('id', '?')}: missing {k}")
        if q["id"] in ids:
            errors.append(f"{q['id']}: duplicate id")
        ids.add(q["id"])
        if q.get("cat") not in CATS:
            errors.append(f"{q['id']}: cat must be one of {sorted(CATS)}")
        t = q.get("source", {}).get("type")
        if t not in required:
            errors.append(f"{q['id']}: unknown source type {t}")
            continue
        for k in required[t]:
            if k not in q["source"]:
                errors.append(f"{q['id']}: source.{k} required for {t}")
    for q in qs:
        if q["source"]["type"] == "derived":
            for i in q["source"]["of"]:
                if i not in ids:
                    errors.append(f"{q['id']}: derived from unknown id {i}")
    for e in errors:
        print(e, file=sys.stderr)
    print(f"{len(qs)} questions, {len(errors)} problems")
    return 1 if errors else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("update")
    u.add_argument("--id", action="append")
    u.add_argument("--force", action="store_true", help="accept moves above the sanity threshold")
    b = sub.add_parser("backfill")
    b.add_argument("--id", action="append")
    sub.add_parser("build")
    sub.add_parser("check")
    args = ap.parse_args(argv)
    return {"update": cmd_update, "backfill": cmd_backfill, "build": cmd_build, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
