"""Source adapters.

Each adapter module exposes two functions:

    current(spec: dict, get=get_json) -> Reading
    history(spec: dict, get=get_json) -> list[tuple[str, float]]   # (YYYY-MM-DD, p), oldest first

`spec` is the question's "source" object from data/questions.json.
`get` is injectable so tests can pass fixture data instead of hitting the network.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Reading:
    p: float                     # probability of YES, 0..1
    n: float | None = None       # forecasters, traders, or dollar volume
    resolved: str | None = None  # resolution text if the question has resolved
    closed: bool = False


from . import kalshi, manifold, metaculus, polymarket  # noqa: E402

ADAPTERS = {
    "metaculus": metaculus,
    "manifold": manifold,
    "polymarket": polymarket,
    "kalshi": kalshi,
}
