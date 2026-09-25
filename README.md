# AI Risk Ledger

One page that tracks what forecasters and prediction markets expect from AI: catastrophe, misuse, governance and AGI timing. It pulls from Metaculus, Manifold, Polymarket and Kalshi every six hours, keeps the full price history, and shows it next to published expert estimates.

The site is static and hosted on Vercel. GitHub Actions does the fetching, rebuilds `site/data.json` and commits it; Vercel redeploys the `site` folder on every commit. There is no server and no database: the history lives in this repo as CSV files, so every change is auditable in git.

## What it tracks

| Category | Examples |
|---|---|
| Catastrophe & extinction | Metaculus Ragnarök series, Manifold "Will AI wipe out humanity" markets |
| Misuse & incidents | AI malfunction causing 100+ deaths, AI-enabled bioweapons, warning shots |
| Governance & labs | US AI safety bill, US–China limits, international pause, lab safety commitments |
| Capability context | OpenAI AGI announcement markets on Kalshi and Polymarket |

It also lists individual p(doom) statements, the XPT tournament, the AI Impacts survey and FRI's AIRO model ensemble. Those are edited by hand in `data/experts.json`.

## How it works

```
data/questions.json      the registry: every tracked question and where to fetch it
data/history/<id>.csv    one row per day: date, probability, participation
data/experts.json        hand-maintained expert estimates
ledger/                  Python package (standard library only)
  sources/               one adapter per platform
site/                    index.html, app.js, style.css, data.json (built by the update job)
vercel.json              serves site/ as a static site, no build step
.github/workflows/       update.yml (every 6h), backfill.yml (manual), test.yml
```

Every six hours `update.yml` runs `python -m ledger update`. It fetches each question's current value, writes today's row to its CSV, rebuilds `site/data.json` and commits both. Vercel sees the commit and publishes the `site` folder. There is no build step on Vercel.

Implied rows, such as "AI kills 10%+ of humanity by 2100", are computed at build time by multiplying Metaculus's conditional questions. They are labeled as our calculation, not a platform forecast.

### Source details

| Platform | Endpoint | Value used |
|---|---|---|
| Metaculus | `/api/posts/{id}/` with a token, otherwise `/api-proxy/posts/{id}/` | Recency-weighted community median |
| Manifold | `/v0/slug/{slug}`, history from `/v0/bets` | `probability` |
| Polymarket | CLOB `/prices-history` for the YES token | Last traded price, order-book midpoint if no recent trades |
| Kalshi | `/trade-api/v2/markets/{ticker}`, history from candlesticks | YES bid/ask midpoint |

Polymarket's Gamma search endpoints can return stale prices, so they are used only to look up token ids.

### Safeguards

- If a value moves more than 30 points since the previous reading, it is held back and flagged in the run summary instead of written. A real jump can be accepted by running the workflow by hand with **force** checked.
- One failing source never blocks the others. The job only fails if most sources fail.
- Backfills never overwrite existing rows.

## Setup

1. Create an empty **public** repository on GitHub, for example `ai-risk-ledger`.
2. Push this folder:
   ```bash
   git remote add origin https://github.com/<you>/ai-risk-ledger.git
   git push -u origin main
   ```
3. In Vercel, import the repository (or connect it to the existing `ai-risk-ledger` project under **Settings → Git**). `vercel.json` sets the output folder to `site` with no build step, so no other settings are needed.
4. Recommended: create a free Metaculus API token at <https://www.metaculus.com/accounts/settings/> and add it in GitHub under **Settings → Secrets and variables → Actions** as `METACULUS_TOKEN`. Without it the fetcher uses Metaculus's public web path, which may be rate-limited from GitHub's servers.
5. In GitHub, open **Actions → Backfill history → Run workflow** (leave the id blank). The repo ships with weekly history; this fills in daily points from every source.
6. Open **Actions → Update data → Run workflow** once to confirm every source responds. After that it runs every six hours and each run redeploys the site.

GitHub pauses scheduled workflows in repos with no activity for 60 days. The bot's own data commits normally count as activity, but if the schedule ever stops, re-enable it from the Actions tab.

## Local use

```bash
python -m ledger check          # validate the registry
python -m ledger update         # fetch today's values
python -m ledger backfill --id mf-wipe-2100
python -m ledger build          # write site/data.json
python -m http.server -d site   # preview at http://localhost:8000
pip install pytest && python -m pytest -q
```

Python 3.10+ with no third-party packages. `pytest` is only needed for the tests.

## Adding a question

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: add an entry to `data/questions.json`, run `python -m ledger check`, then run the **Backfill history** workflow with the new id.

## Reading the numbers

- **Extinction markets are biased low.** A market on human extinction can never pay out on YES. Treat those prices as a lower bound.
- **Definitions are not aligned.** "Catastrophe", "wipe out" and "p(doom)" mean different things on each platform and to each person.
- **Participation varies a lot.** Some governance markets have under $1,000 traded or fewer than 20 traders. The site shows participation next to every figure.
- **No real-money market covers AI mass casualties.** Polymarket and Kalshi list AI regulation and AGI markets but nothing on AI killing a share of humanity, even though such a market could pay out to survivors.

## License

Code is MIT licensed. Forecast data belongs to the platforms it comes from and is republished with links back to each source. Check each platform's terms before reusing the data commercially.
