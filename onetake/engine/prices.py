"""Real share prices for the `stock_chart` look (Yahoo Finance's public chart data, no key).

`fetch("NVDA", "1y")` saves library/prices/NVDA-1y.json = {"ticker", "range", "currency", "t": [unix…], "c": [close…],
"fetched"} so a reel always renders the same numbers (prices from the day it was edited). Ranges: 5d 1mo 3mo 6mo ytd 1y
2y 5y 10y max.
"""
import json
import time
import urllib.parse
import urllib.request

from . import config

DIR = config.LIBRARY / "prices"
INTERVAL = {"5d": "1h", "1mo": "1d", "3mo": "1d", "6mo": "1d", "ytd": "1d", "1y": "1d", "2y": "1wk", "5y": "1wk",
            "10y": "1mo", "max": "1mo"}


def path(ticker, rng):
    return DIR / f"{ticker.upper().lstrip('$')}-{rng}.json"


def cached(ticker, rng):
    f = path(ticker, rng)
    try:
        return json.loads(f.read_text())
    except (OSError, ValueError):
        return None


def fetch(ticker, rng="1y"):
    t = ticker.upper().lstrip("$").replace(".", "-")
    if rng not in INTERVAL:
        raise SystemExit(f"Range must be one of: {', '.join(INTERVAL)}")
    q = urllib.parse.urlencode({"range": rng, "interval": INTERVAL[rng]})
    last = None
    for host in ("query1", "query2"):
        try:
            req = urllib.request.Request(f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(t)}?{q}",
                                         headers={"User-Agent": "Mozilla/5.0 (OneTakeStudio)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read())["chart"]["result"][0]
            break
        except Exception as e:  # noqa: BLE001
            last = e
    else:
        raise RuntimeError(f"Couldn't get prices for {t}: {last}")
    closes = res["indicators"]["quote"][0]["close"]
    pts = [(ts, c) for ts, c in zip(res.get("timestamp", []), closes) if c is not None]
    if len(pts) < 2:
        raise RuntimeError(f"No price history for {t}.")
    data = {"ticker": t, "range": rng, "currency": res["meta"].get("currency", "USD"),
            "name": res["meta"].get("longName") or res["meta"].get("shortName") or t,
            "t": [p[0] for p in pts], "c": [round(p[1], 4) for p in pts], "fetched": int(time.time())}
    DIR.mkdir(parents=True, exist_ok=True)
    path(t, rng).write_text(json.dumps(data))
    return data
