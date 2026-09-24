# Contributing

## Add a question

Add an object to `data/questions.json`:

```json
{
  "id": "pm-example",
  "src": "polymarket",
  "cat": "governance",
  "q": "Will the example happen before 2027?",
  "h": "by 2027",
  "url": "https://polymarket.com/event/example",
  "unit": "volume",
  "note": "Optional one-line caveat shown under the question.",
  "source": { "type": "polymarket", "event": "example" }
}
```

| Field | Meaning |
|---|---|
| `id` | Unique, lowercase. Prefix with the platform: `mc-`, `mf-`, `pm-`, `ks-`. Also the CSV filename. |
| `src` | `metaculus`, `manifold`, `polymarket`, `kalshi` or `derived` |
| `cat` | `catastrophe`, `misuse`, `governance` or `context` |
| `q` | The question, phrased as a yes/no question |
| `h` | Horizon label, such as `by 2030` |
| `url` | Link to the question on the platform |
| `unit` | `forecasters`, `traders` or `volume` (dollars) |
| `conditional` | `true` if the question is conditional on another event |
| `retired` | `true` to stop fetching but keep showing the history |

Source specs by platform:

| Platform | `source` |
|---|---|
| Metaculus | `{"type": "metaculus", "id": 1495}` (binary questions only) |
| Manifold | `{"type": "manifold", "slug": "will-ai-wipe-out-humanity-before-th"}` (the last part of the market URL) |
| Polymarket | `{"type": "polymarket", "event": "<event slug>", "market": "<text in the market question>"}`; `market` only for multi-market events; `token` is optional and speeds things up |
| Kalshi | `{"type": "kalshi", "ticker": "OAIAGI-26", "series": "KXOAIAGI"}` |
| Implied | `{"type": "derived", "of": ["mc-1493", "mc-1495"]}` (product of the listed probabilities) |

Then:

```bash
python -m ledger check
python -m ledger update --id pm-example
```

After merging, run **Actions → Backfill history** with the new id to pull its full history.

## What belongs here

A question belongs if it bears on AI catastrophe, misuse, loss of control, or the governance and lab behavior that affects those risks. AGI-timing markets go under `context`. Prefer questions with clear resolution criteria and real participation. Low-participation markets are fine if the `note` says so.

## Expert estimates

Edit `data/experts.json`. Each individual estimate needs a public source. Give a range with `lo` and `hi` when the person stated one. Record the estimate as the person stated it, without converting their definition of "doom" into anyone else's.
