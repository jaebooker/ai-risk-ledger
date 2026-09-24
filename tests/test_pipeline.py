"""Update and build pipeline against a temporary data directory."""
import json

import pytest

import ledger.__main__ as cli
from ledger import build as buildmod, store
from ledger.sources import Reading


@pytest.fixture
def tmpdata(tmp_path, monkeypatch):
    data = tmp_path / "data"
    (data / "history").mkdir(parents=True)
    qs = {"questions": [
        {"id": "a", "src": "metaculus", "cat": "catastrophe", "q": "A?", "h": "by 2100", "url": "u", "unit": "forecasters", "source": {"type": "metaculus", "id": 1}},
        {"id": "b", "src": "manifold", "cat": "catastrophe", "q": "B?", "h": "by 2100", "url": "u", "unit": "traders", "source": {"type": "manifold", "slug": "b"}},
        {"id": "ab", "src": "derived", "cat": "catastrophe", "q": "A×B", "h": "by 2100", "url": "u", "source": {"type": "derived", "of": ["a", "b"]}},
    ]}
    (data / "questions.json").write_text(json.dumps(qs))
    (data / "experts.json").write_text(json.dumps({"studies": [], "people": []}))
    (data / "history" / "a.csv").write_text("date,p,n\n2026-01-01,0.3,\n2026-09-01,0.4,400\n")
    (data / "history" / "b.csv").write_text("date,p,n\n2026-09-01,0.5,\n")
    monkeypatch.setattr(store, "DATA", data)
    monkeypatch.setattr(store, "HIST", data / "history")
    monkeypatch.setattr(buildmod, "SITE", tmp_path / "site")
    monkeypatch.setattr(cli, "polite_pause", lambda: None)
    monkeypatch.setattr(cli, "today", lambda: "2026-09-25")
    return tmp_path


class Stub:
    def __init__(self, reading):
        self.reading = reading

    def current(self, spec):
        if isinstance(self.reading, Exception):
            raise self.reading
        return self.reading


def run_update(monkeypatch, a, b, *extra):
    monkeypatch.setitem(cli.ADAPTERS, "metaculus", Stub(a))
    monkeypatch.setitem(cli.ADAPTERS, "manifold", Stub(b))
    return cli.main(["update", *extra])


def test_update_appends_and_builds_derived(tmpdata, monkeypatch):
    assert run_update(monkeypatch, Reading(0.45, 410), Reading(0.6, 50)) == 0
    assert store.read_history("a")[-1] == {"date": "2026-09-25", "p": 0.45, "n": 410.0}
    data = json.loads((tmpdata / "site" / "data.json").read_text())
    ab = next(i for i in data["items"] if i["id"] == "ab")
    assert ab["p"] == pytest.approx(0.27)
    assert ab["hist"][-1] == ["2026-09-25", pytest.approx(0.27)]


def test_update_is_idempotent_within_a_day(tmpdata, monkeypatch):
    run_update(monkeypatch, Reading(0.45), Reading(0.6))
    run_update(monkeypatch, Reading(0.46), Reading(0.6))
    rows = store.read_history("a")
    assert [r["date"] for r in rows].count("2026-09-25") == 1 and rows[-1]["p"] == 0.46


def test_sanity_guard_holds_big_jumps(tmpdata, monkeypatch):
    run_update(monkeypatch, Reading(0.95), Reading(0.6))
    assert store.read_history("a")[-1]["date"] == "2026-09-01"
    run_update(monkeypatch, Reading(0.95), Reading(0.6), "--force")
    assert store.read_history("a")[-1]["p"] == 0.95


def test_one_failing_source_does_not_fail_run(tmpdata, monkeypatch):
    assert run_update(monkeypatch, RuntimeError("boom"), Reading(0.6)) == 0
    assert store.read_history("b")[-1]["p"] == 0.6


def test_backfill_never_overwrites(tmpdata):
    added = store.merge_backfill("a", [("2026-01-01", 0.99), ("2026-02-01", 0.35)])
    rows = store.read_history("a")
    assert added == 1 and rows[0]["p"] == 0.3 and rows[1] == {"date": "2026-02-01", "p": 0.35, "n": None}


def test_thin_keeps_recent_daily_and_weekly_before():
    rows = [{"date": f"2026-{m:02d}-{d:02d}", "p": 0.1, "n": None} for m in range(1, 10) for d in range(1, 29)]
    out = buildmod.thin(rows, daily_days=30)
    recent = [d for d, _ in out if d >= "2026-08-28"]
    assert len(recent) >= 28 and len(out) < len(rows) / 3


def test_check_passes_on_repo_registry():
    assert cli.main(["check"]) == 0
