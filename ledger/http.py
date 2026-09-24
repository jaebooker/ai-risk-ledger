"""Tiny stdlib HTTP helper with retries. No third-party dependencies."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

USER_AGENT = "ai-risk-ledger/1.0 (+https://github.com/ai-risk-ledger)"


class FetchError(RuntimeError):
    pass


def get_json(url: str, headers: dict | None = None, retries: int = 3, timeout: int = 30):
    """GET a URL and parse JSON. Retries on 429/5xx and network errors."""
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        h.update(headers)
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise FetchError(f"HTTP {e.code} for {url}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 2)
                continue
            raise FetchError(f"{type(e).__name__} for {url}: {e}") from e
    raise FetchError(f"failed {url}: {last}")


def polite_pause() -> None:
    """Small delay between requests to stay well inside public rate limits."""
    time.sleep(float(os.environ.get("LEDGER_PAUSE", "0.4")))
