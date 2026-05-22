#!/usr/bin/env python3
"""
Pull daily snapshot for every ticker in data/watchlists.json.
Writes:
  data/snapshot-latest.json
  data/snapshots/YYYY-MM-DD.json (also today's, for history)

Pulls from yfinance (free, no key). Fields per ticker:
  price, market_cap, pe, forward_pe, ev_to_ebitda, fcf_yield,
  debt_to_equity, dividend_yield, beta,
  return_1y, return_3y, return_5y,
  price_vs_200dma, fifty_two_week_high, fifty_two_week_low,
  top_5_holders (from major_holders / institutional_holders),
  insider_buys_90d (Form 4 net via insider_purchases when available)

Skipped fields gracefully fall back to None — non-US tickers especially.
"""
import json
import sys
import datetime as dt
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("yfinance not installed. pip install yfinance", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parent.parent
WATCHLISTS = REPO / "data" / "watchlists.json"
LATEST = REPO / "data" / "snapshot-latest.json"
HISTORY_DIR = REPO / "data" / "snapshots"


def safe(d, key, default=None):
    v = d.get(key) if isinstance(d, dict) else None
    return v if v is not None else default


def pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return round((a - b) / b * 100, 2)


def fetch_ticker(symbol):
    out = {"symbol": symbol, "error": None}
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        price = safe(info, "currentPrice") or safe(info, "regularMarketPrice")
        out["price"] = price
        out["currency"] = safe(info, "currency")
        out["market_cap"] = safe(info, "marketCap")
        out["pe"] = safe(info, "trailingPE")
        out["forward_pe"] = safe(info, "forwardPE")
        out["ev_to_ebitda"] = safe(info, "enterpriseToEbitda")
        out["price_to_book"] = safe(info, "priceToBook")
        out["debt_to_equity"] = safe(info, "debtToEquity")
        out["dividend_yield"] = safe(info, "dividendYield")
        out["beta"] = safe(info, "beta")
        out["fifty_two_week_high"] = safe(info, "fiftyTwoWeekHigh")
        out["fifty_two_week_low"] = safe(info, "fiftyTwoWeekLow")
        ma200 = safe(info, "twoHundredDayAverage")
        out["two_hundred_day_avg"] = ma200
        out["price_vs_200dma_pct"] = pct(price, ma200)

        # FCF yield = FCF / market cap
        fcf = safe(info, "freeCashflow")
        mc = out["market_cap"]
        if fcf and mc:
            out["fcf_yield_pct"] = round(fcf / mc * 100, 2)
        else:
            out["fcf_yield_pct"] = None

        # Returns (1y, 3y, 5y) from history
        try:
            hist = t.history(period="5y", auto_adjust=True)
            if not hist.empty and price:
                closes = hist["Close"]
                today = closes.iloc[-1]
                def ret_from(days):
                    if len(closes) <= days:
                        return None
                    past = closes.iloc[-days]
                    return pct(today, past)
                out["return_1y_pct"] = ret_from(252)
                out["return_3y_pct"] = ret_from(252 * 3)
                out["return_5y_pct"] = ret_from(252 * 5 - 1)
        except Exception as e:
            out["history_error"] = str(e)[:200]

        # Top institutional holders
        try:
            ih = t.institutional_holders
            if ih is not None and len(ih) > 0:
                top = ih.head(5)
                out["top_5_holders"] = [
                    {
                        "holder": str(row.get("Holder", "")),
                        "pct_held": float(row["pctHeld"]) if "pctHeld" in row and row["pctHeld"] == row["pctHeld"] else None,
                        "shares": int(row["Shares"]) if "Shares" in row and row["Shares"] == row["Shares"] else None,
                    }
                    for _, row in top.iterrows()
                ]
        except Exception as e:
            out["holders_error"] = str(e)[:200]

        # Insider transactions (90-day net via insider_purchases)
        try:
            ip = t.insider_purchases
            if ip is not None and len(ip) > 0:
                out["insider_purchases_summary"] = ip.to_dict(orient="records")
        except Exception:
            pass

    except Exception as e:
        out["error"] = str(e)[:300]
    return out


def main():
    watchlists = json.loads(WATCHLISTS.read_text())
    today = dt.date.today().isoformat()
    snapshot = {
        "generated_at_utc": dt.datetime.utcnow().isoformat() + "Z",
        "as_of_date": today,
        "watchlists": [],
    }

    for wl in watchlists["watchlists"]:
        wl_out = {
            "id": wl["id"],
            "name": wl["name"],
            "description": wl["description"],
            "tickers": [],
        }
        for t in wl["tickers"]:
            sym = t["symbol"]
            print(f"  {wl['id']:20s} {sym}", flush=True)
            data = fetch_ticker(sym)
            # merge curated meta + fetched data
            merged = {**t, **{k: v for k, v in data.items() if k != "symbol"}}
            wl_out["tickers"].append(merged)
        snapshot["watchlists"].append(wl_out)

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    def _clean(obj):
        # yfinance returns numpy NaN / Inf which Python's json writes as bare
        # tokens (invalid per RFC 8259). Coerce to None so browsers can parse.
        import math
        if isinstance(obj, float):
            return None if (math.isnan(obj) or math.isinf(obj)) else obj
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(v) for v in obj]
        return obj
    cleaned = _clean(snapshot)
    LATEST.write_text(json.dumps(cleaned, indent=2, default=str, allow_nan=False))
    (HISTORY_DIR / f"{today}.json").write_text(json.dumps(cleaned, indent=2, default=str, allow_nan=False))
    print(f"\nWrote {LATEST}")
    print(f"Wrote {HISTORY_DIR / (today + '.json')}")


if __name__ == "__main__":
    main()
