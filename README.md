# HI Portfolio

Personal Bloomberg-lite. Three curated watchlists with daily metrics, rendered as a static site.

**Live:** https://artemis-lgtm.github.io/hi-portfolio/

## Watchlists

1. **Energy** — oil majors, midstream, utilities, nuclear (incl. SMR), renewables. ~26 tickers.
2. **Tesla — Confirmed Suppliers** — companies named in Tesla 10-K, earnings calls, or supplier press releases. ~14 tickers.
3. **Tesla Optimus — Speculative Suppliers** — inferred from analyst notes (Morgan Stanley, Citi) + Chinese supply-chain reporting. ~10 tickers, each with a 1-10 confidence score. **Tesla has NOT disclosed an Optimus BOM** — these are educated guesses.

## How it works

- `data/watchlists.json` — curated universes + thesis + confidence (edit by hand)
- `scripts/refresh.py` — pulls daily metrics from yfinance (free, no key)
- `data/snapshot-latest.json` — today's data, served by GitHub Pages
- `data/snapshots/YYYY-MM-DD.json` — daily history
- `index.html` — Alpine.js + Tailwind, fetches snapshot JSON

## Refresh

```bash
cd hi-portfolio
python3 -m pip install yfinance
python3 scripts/refresh.py
git add data/ && git commit -m "Daily snapshot $(date +%F)" && git push
```

GitHub Pages republishes automatically.

## Daily automation

A launchd plist runs `refresh.py` at 06:00 ET every weekday and pushes the snapshot. See `~/Library/LaunchAgents/com.artemis.hi-portfolio-refresh.plist` (not in repo).

## Metrics per ticker

Price, market cap, P/E, forward P/E, EV/EBITDA, P/B, FCF yield, debt/equity, dividend yield, beta, 1Y/3Y/5Y return, 200-day MA distance, 52-week high/low, top 5 institutional holders, insider purchase summary (where available).

## Notes

- Non-US tickers (Tokyo `.T`, Shenzhen `.SZ`, Shanghai `.SS`, Korea `.KS`, Madrid `.MC`, Germany `.DE`) often have sparser fundamental data via yfinance — price + market cap usually work, deeper fundamentals may be missing.
- The MP Materials inclusion is deliberately contrarian: Tesla said Optimus uses zero rare-earth magnets (Investor Day 2023). It's on the list as a hedge against that decision being reversed. Confidence score: 3/10.
