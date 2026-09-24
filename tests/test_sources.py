"""Adapter tests against recorded response shapes (no network)."""
import json

import pytest

from ledger.sources import kalshi, manifold, metaculus, polymarket


def fake(routes):
    """Return a get() that serves JSON by URL substring."""
    def get(url, headers=None):
        for key, val in routes.items():
            if key in url:
                return val
        raise AssertionError(f"unexpected URL {url}")
    return get


METACULUS_POST = {
    "nr_forecasters": 475,
    "question": {"resolution": None, "aggregations": {"recency_weighted": {
        "history": [
            {"start_time": 1539420317.2, "end_time": 1540150588.6, "forecaster_count": 1, "centers": [0.25]},
            {"start_time": 1540150588.6, "end_time": 1541029511.6, "forecaster_count": 57, "centers": [0.24]},
        ],
        "latest": {"start_time": 1790278896.9, "forecaster_count": 465, "centers": [0.43]},
    }}},
}


def test_metaculus_current_uses_latest(monkeypatch):
    monkeypatch.delenv("METACULUS_TOKEN", raising=False)
    r = metaculus.current({"id": 1495}, get=fake({"api-proxy/posts/1495": METACULUS_POST}))
    assert r.p == 0.43 and r.n == 475 and r.resolved is None


def test_metaculus_token_uses_official_api(monkeypatch):
    monkeypatch.setenv("METACULUS_TOKEN", "abc")
    seen = {}

    def get(url, headers=None):
        seen["url"], seen["headers"] = url, headers
        return METACULUS_POST
    metaculus.current({"id": 1495}, get=get)
    assert "/api/posts/1495/" in seen["url"] and seen["headers"]["Authorization"] == "Token abc"


def test_metaculus_history_daily():
    h = metaculus.history({"id": 1495}, get=fake({"posts/1495": METACULUS_POST}))
    assert h == [("2018-10-13", 0.25), ("2018-10-21", 0.24)]


def test_manifold_current_and_history():
    market = {"id": "abc", "probability": 0.136, "uniqueBettorCount": 816, "isResolved": False}
    bets = [
        {"id": "b3", "createdTime": 1790200000000, "probAfter": 0.14},
        {"id": "b2", "createdTime": 1790100000000, "probAfter": 0.13, "isCancelled": True},
        {"id": "b1", "createdTime": 1790000000000, "probAfter": 0.12},
    ]
    get = fake({"/slug/x": market, "/bets?contractId=abc": bets})
    r = manifold.current({"slug": "x"}, get=get)
    assert (r.p, r.n) == (0.136, 816)
    h = manifold.history({"slug": "x"}, get=get)
    assert [p for _, p in h] == [0.12, 0.14]


def test_manifold_rejects_non_binary():
    with pytest.raises(ValueError):
        manifold.current({"slug": "x"}, get=fake({"/slug/x": {"id": "m", "answers": []}}))


POLY_EVENT = [{"volume": 167407.2, "markets": [
    {"question": "Google matches Anthropic's evaluator commitment by October 31?",
     "clobTokenIds": json.dumps(["111", "222"]), "bestBid": 0.34, "bestAsk": 0.36, "closed": False},
    {"question": "Microsoft matches Anthropic's evaluator commitment by October 31?",
     "clobTokenIds": json.dumps(["333", "444"]), "bestBid": 0.24, "bestAsk": 0.25, "closed": False},
]}]


def test_polymarket_picks_market_and_uses_clob():
    get = fake({"events?slug=e": POLY_EVENT,
                "prices-history?market=333&interval=1d": {"history": [{"t": 1790280000, "p": 0.2}, {"t": 1790286000, "p": 0.245}]}})
    r = polymarket.current({"event": "e", "market": "Microsoft"}, get=get)
    assert r.p == 0.245 and r.n == 167407.2


def test_polymarket_falls_back_to_midpoint():
    get = fake({"events?slug=e": POLY_EVENT, "prices-history": {"history": []}})
    r = polymarket.current({"event": "e", "market": "Google", "token": "111"}, get=get)
    assert r.p == pytest.approx(0.35)


def test_kalshi_midpoint_and_history():
    market = {"market": {"yes_bid_dollars": "0.1520", "yes_ask_dollars": "0.1840", "last_price_dollars": "0.1420",
                         "volume_fp": "346500.13", "status": "active", "result": "",
                         "open_time": "2026-09-01T00:00:00Z"}}
    candles = {"candlesticks": [
        {"end_period_ts": 1788300000, "yes_bid": {"close_dollars": "0.10"}, "yes_ask": {"close_dollars": "0.12"}, "price": {}},
        {"end_period_ts": 1788386400, "yes_bid": {"close": 15}, "yes_ask": {"close": 17}, "price": {}},
    ]}
    get = fake({"/candlesticks": candles, "/markets/OAIAGI-26": market})
    r = kalshi.current({"ticker": "OAIAGI-26", "series": "KXOAIAGI"}, get=get)
    assert r.p == pytest.approx(0.168) and not r.closed and r.n == pytest.approx(346500.13)
    h = kalshi.history({"ticker": "OAIAGI-26", "series": "KXOAIAGI"}, get=get)
    assert [round(p, 3) for _, p in h] == [0.11, 0.16]
