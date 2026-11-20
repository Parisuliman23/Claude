"""US stocks through Alpaca (free paper-trading account + market data API).

Docs: https://docs.alpaca.markets  — keys: APCA_API_KEY_ID / APCA_API_SECRET_KEY.
Float data is optional, from Financial Modeling Prep (FMP_API_KEY), because
Alpaca does not publish share float.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

from .broker import BaseBroker, Fill

ET = ZoneInfo("America/New_York")
DATA_URL = "https://data.alpaca.markets"
PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"

_TF = {"1m": "1Min", "5m": "5Min", "15m": "15Min", "1h": "1Hour", "4h": "4Hour", "1d": "1Day"}
_TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}


class AlpacaClient:
    def __init__(self, live: bool, feed: str = "iex", http: httpx.Client | None = None):
        key, secret = os.environ.get("APCA_API_KEY_ID"), os.environ.get("APCA_API_SECRET_KEY")
        if not key or not secret:
            raise RuntimeError("Stocks mode needs APCA_API_KEY_ID and APCA_API_SECRET_KEY in .env "
                               "(free at alpaca.markets; use the PAPER keys first).")
        self.trade_url = LIVE_URL if live else PAPER_URL
        self.feed = feed
        self.http = http or httpx.Client(
            timeout=15, headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})

    def _get(self, base: str, path: str, **params) -> dict | list:
        r = self.http.get(f"{base}{path}", params={k: v for k, v in params.items() if v is not None})
        r.raise_for_status()
        return r.json()

    def data(self, path: str, **params):
        return self._get(DATA_URL, path, **params)

    def trade(self, path: str, **params):
        return self._get(self.trade_url, path, **params)

    def post_order(self, body: dict) -> dict:
        r = self.http.post(f"{self.trade_url}/v2/orders", json=body)
        if r.status_code >= 400:
            raise RuntimeError(f"Alpaca rejected order: {r.status_code} {r.text[:300]}")
        return r.json()

    def cancel_order(self, oid: str) -> None:
        self.http.delete(f"{self.trade_url}/v2/orders/{oid}")


SEC_UA = "daytrader-agent research-bot"  # SEC rejects some formats (e.g. with parentheses)


class FloatLookup:
    """Share float for pillar 5. Cached per run.

    1. Financial Modeling Prep float (FMP_API_KEY). The free plan only covers large
       companies, so small caps usually fall through to step 2.
    2. SEC EDGAR shares outstanding (free, no key). Outstanding >= float, so it is an
       upper bound: outstanding under the limit means the float is too.
    """

    def __init__(self, http: httpx.Client | None = None):
        self.key = os.environ.get("FMP_API_KEY")
        self.http = http or httpx.Client(timeout=10)
        self.cache: dict[str, dict] = {}
        self._ciks: dict[str, int] | None = None

    def _fmp(self, symbol: str) -> float | None:
        if not self.key:
            return None
        try:
            r = self.http.get("https://financialmodelingprep.com/stable/shares-float",
                              params={"symbol": symbol, "apikey": self.key})
            rows = r.json() if r.status_code == 200 else []
            if rows and isinstance(rows, list):
                return rows[0].get("floatShares")
        except Exception:
            pass
        return None

    def _sec_outstanding(self, symbol: str) -> float | None:
        try:
            if self._ciks is None:
                r = self.http.get("https://www.sec.gov/files/company_tickers.json",
                                  headers={"User-Agent": SEC_UA})
                self._ciks = {v["ticker"].upper(): v["cik_str"] for v in r.json().values()}
            cik = self._ciks.get(symbol.upper())
            if not cik:
                return None
            r = self.http.get(
                f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/dei/"
                "EntityCommonStockSharesOutstanding.json", headers={"User-Agent": SEC_UA})
            if r.status_code != 200:
                return None
            rows = (r.json().get("units") or {}).get("shares") or []
            if not rows:
                return None
            latest = max(rows, key=lambda x: (x.get("filed", ""), x.get("end", "")))
            return float(latest["val"])
        except Exception:
            return None

    def info(self, symbol: str) -> dict:
        if symbol not in self.cache:
            flt = self._fmp(symbol)
            out = None if flt else self._sec_outstanding(symbol)
            self.cache[symbol] = {"float": flt, "outstanding": out,
                                  "source": "fmp" if flt else ("sec_outstanding" if out else None)}
        return self.cache[symbol]

    def get(self, symbol: str) -> float | None:
        return self.info(symbol)["float"]


def session_start_ms(now: datetime | None = None) -> int:
    """04:00 ET today (premarket open): VWAP and the day's move are measured from here."""
    now = (now or datetime.now(timezone.utc)).astimezone(ET)
    start = now.replace(hour=4, minute=0, second=0, microsecond=0)
    return int(start.timestamp() * 1000)


class AlpacaMarket:
    """Same interface as MarketData (crypto), plus scan/news for stocks."""

    kind = "stocks"

    def __init__(self, client: AlpacaClient, floats: FloatLookup | None = None,
                 cache_seconds: float = 3.0):
        self.client = client
        self.floats = floats or FloatLookup()
        self.cache_seconds = cache_seconds
        self._snap: dict[str, tuple[dict, float]] = {}
        self._assets: dict[str, dict] = {}

    # -- prices ----------------------------------------------------------------
    def snapshots(self, symbols: list[str]) -> dict[str, dict]:
        now = time.time()
        need = [s for s in symbols if not (s in self._snap and now - self._snap[s][1] < self.cache_seconds)]
        if need:
            for i in range(0, len(need), 100):
                chunk = need[i:i + 100]
                data = self.client.data("/v2/stocks/snapshots", symbols=",".join(chunk),
                                        feed=self.client.feed)
                for s, snap in (data or {}).items():
                    if snap:
                        self._snap[s] = (snap, now)
        return {s: self._snap[s][0] for s in symbols if s in self._snap}

    def price(self, symbol: str) -> float:
        snap = self.snapshots([symbol]).get(symbol)
        if not snap:
            raise RuntimeError(f"No snapshot for {symbol}")
        trade = (snap.get("latestTrade") or {}).get("p")
        quote = snap.get("latestQuote") or {}
        p = trade or ((quote.get("ap") or 0) + (quote.get("bp") or 0)) / 2
        if not p:
            raise RuntimeError(f"No price for {symbol}")
        return float(p)

    def last_trade_age_s(self, symbol: str) -> float | None:
        """Seconds since the last trade print (a long gap on an active stock suggests a halt)."""
        t = ((self.snapshots([symbol]).get(symbol) or {}).get("latestTrade") or {}).get("t")
        if not t:
            return None
        import re
        m = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?", t)
        if not m:
            return None
        frac = (m.group(2) or "0")[:6].ljust(6, "0")
        ts = datetime.fromisoformat(f"{m.group(1)}.{frac}+00:00")
        return (datetime.now(timezone.utc) - ts).total_seconds()

    def ticker(self, symbol: str) -> dict:
        snap = self.snapshots([symbol]).get(symbol) or {}
        day, prev = snap.get("dailyBar") or {}, snap.get("prevDailyBar") or {}
        last = self.price(symbol)
        prev_close = prev.get("c")
        return {
            "symbol": symbol,
            "last": last,
            "bid": (snap.get("latestQuote") or {}).get("bp"),
            "ask": (snap.get("latestQuote") or {}).get("ap"),
            "change_pct_vs_prev_close": round((last / prev_close - 1) * 100, 2) if prev_close else None,
            "day_high": day.get("h"),
            "day_low": day.get("l"),
            "day_volume": day.get("v"),
            "prev_close": prev_close,
        }

    def candles(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
        if timeframe not in _TF:
            raise ValueError(f"timeframe must be one of {list(_TF)}")
        # look back far enough to cover nights/weekends
        minutes = _TF_MINUTES[timeframe] * limit
        days = max(4, int(minutes / (60 * 6.5)) + 4) if timeframe != "1d" else limit * 2 + 10
        start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        data = self.client.data(f"/v2/stocks/{symbol}/bars", timeframe=_TF[timeframe],
                                start=start, limit=limit, sort="desc", feed=self.client.feed,
                                adjustment="split")
        bars = list(reversed((data or {}).get("bars") or []))
        out = []
        for b in bars:
            ts = datetime.fromisoformat(b["t"].replace("Z", "+00:00"))
            out.append([int(ts.timestamp() * 1000), b["o"], b["h"], b["l"], b["c"], b["v"]])
        return out

    def order_book(self, symbol: str, depth: int = 20) -> dict:
        q = (self.snapshots([symbol]).get(symbol) or {}).get("latestQuote") or {}
        bid, ask = q.get("bp"), q.get("ap")
        if not bid or not ask:
            return {"symbol": symbol, "error": "no quote"}
        mid = (bid + ask) / 2
        return {"symbol": symbol, "best_bid": bid, "best_ask": ask, "bid_size": q.get("bs"),
                "ask_size": q.get("as"), "spread_pct": round((ask - bid) / mid * 100, 3),
                "note": "Top of book only (Alpaca has no full Level 2)."}

    def session_start_ms(self) -> int:
        return session_start_ms()

    # -- stock-specific ------------------------------------------------------
    def asset(self, symbol: str) -> dict:
        if symbol not in self._assets:
            try:
                self._assets[symbol] = self.client.trade(f"/v2/assets/{symbol}")
            except Exception:
                self._assets[symbol] = {}
        return self._assets[symbol]

    def sip_volume(self, symbol: str, days: int = 50) -> dict | None:
        """Full-market (SIP) daily volume: today so far, previous day, 50-day average.
        The free plan allows SIP data older than 15 minutes, which is fine for volume. The free
        IEX feed only sees a small, very uneven slice of small-cap volume, so it can't be used
        for Ross's relative-volume rule."""
        from datetime import timedelta as _td
        try:
            end = (datetime.now(timezone.utc) - _td(minutes=16)).isoformat()
            start = (datetime.now(timezone.utc) - _td(days=days * 2 + 10)).isoformat()
            data = self.client.data(f"/v2/stocks/{symbol}/bars", timeframe="1Day", start=start, end=end,
                                    limit=days + 5, feed="sip", adjustment="split", sort="desc")
        except Exception:
            return None
        bars = list(reversed((data or {}).get("bars") or []))  # newest first from the API -> oldest first
        if not bars:
            return None
        today = datetime.now(ET).date()
        def day(b):
            return datetime.fromisoformat(b["t"].replace("Z", "+00:00")).astimezone(ET).date()
        past = [b for b in bars if day(b) < today][-days:]
        today_v = sum(b["v"] for b in bars if day(b) == today)
        if not past:
            return None
        return {"today": float(today_v), "prev": float(past[-1]["v"]),
                "avg": sum(b["v"] for b in past) / len(past), "days": len(past)}

    def avg_daily_volume(self, symbol: str, days: int = 50) -> float | None:
        bars = self.candles(symbol, "1d", days + 1)
        today = datetime.now(ET).date()
        past = [b for b in bars
                if datetime.fromtimestamp(b[0] / 1000, ET).date() < today][-days:]
        return sum(b[5] for b in past) / len(past) if past else None

    def top_gainers(self, top: int = 50) -> list[dict]:
        data = self.client.data("/v1beta1/screener/stocks/movers", top=top)
        return (data or {}).get("gainers") or []

    def news(self, symbol: str, limit: int = 5, hours: int = 36) -> list[dict]:
        start = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        data = self.client.data("/v1beta1/news", symbols=symbol, limit=limit, start=start,
                                sort="desc")
        return [{"time": n.get("created_at"), "headline": n.get("headline"),
                 "summary": (n.get("summary") or "")[:300], "source": n.get("source")}
                for n in (data or {}).get("news") or []]

    def clock(self) -> dict:
        return self.client.trade("/v2/clock")


class AlpacaBroker(BaseBroker):
    """Long-only stock orders. Marketable limit orders so they also work premarket
    (Alpaca only accepts limit orders with extended_hours)."""

    def __init__(self, market: AlpacaMarket, state_path, limit_buffer: float = 0.003,
                 account_size: float | None = None):
        super().__init__(market, state_path)
        self.client = market.client
        self.limit_buffer = limit_buffer
        # account_size: trade as if the account held exactly this much (plus/minus the
        # agent's own P&L since then). Lets a $100k paper account behave like $10k, and
        # caps how much of a real account the agent can ever use.
        self.account_size = account_size
        self.baseline_equity: float | None = None
        self.baseline_size: float | None = None
        self.load()
        if account_size and (self.baseline_equity is None or self.baseline_size != account_size):
            self.baseline_equity = self._real_equity()
            self.baseline_size = account_size
            self.save()

    def _extra_state(self) -> dict:
        return {"baseline_equity": self.baseline_equity, "baseline_size": self.baseline_size}

    def _load_extra(self, data: dict) -> None:
        self.baseline_equity = data.get("baseline_equity")
        self.baseline_size = data.get("baseline_size")

    def account(self) -> dict:
        return self.client.trade("/v2/account")

    def _real_equity(self) -> float:
        return float(self.account().get("equity") or 0)

    def cash(self) -> float:
        real_cash = float(self.account().get("cash") or 0)
        if self.account_size and self.baseline_equity is not None:
            return max(0.0, min(real_cash, self.equity() - self.exposure()))
        return real_cash

    def equity(self) -> float:
        real = self._real_equity()
        if self.account_size and self.baseline_equity is not None:
            return self.account_size + (real - self.baseline_equity)
        return real

    def _qty_held(self, symbol: str) -> float:
        try:
            return float(self.client.trade(f"/v2/positions/{symbol}").get("qty") or 0)
        except httpx.HTTPStatusError:
            return 0.0

    def _submit(self, symbol: str, side: str, qty: int) -> Fill:
        q = self.market.order_book(symbol)
        ref = q.get("best_ask" if side == "buy" else "best_bid") or self.market.price(symbol)
        px = ref * (1 + self.limit_buffer) if side == "buy" else ref * (1 - self.limit_buffer)
        px = round(px, 2 if px >= 1 else 4)
        order = self.client.post_order({
            "symbol": symbol, "qty": str(qty), "side": side, "type": "limit",
            "limit_price": str(px), "time_in_force": "day", "extended_hours": True,
        })
        oid = order["id"]
        for _ in range(20):
            if order.get("status") in ("filled", "canceled", "rejected", "expired"):
                break
            time.sleep(0.5)
            order = self.client.trade(f"/v2/orders/{oid}")
        filled = float(order.get("filled_qty") or 0)
        if order.get("status") != "filled":
            self.client.cancel_order(oid)  # don't leave a stale order chasing price
            time.sleep(0.5)
            order = self.client.trade(f"/v2/orders/{oid}")
            filled = float(order.get("filled_qty") or 0)
        if filled <= 0:
            raise RuntimeError(f"{side} {symbol} did not fill (status {order.get('status')})")
        avg = float(order.get("filled_avg_price") or px)
        return Fill(symbol, side, filled, avg, 0.0, filled * avg, time.time(), oid)

    def _buy(self, symbol: str, usd: float) -> Fill:
        qty = int(usd // (self.market.price(symbol) * (1 + self.limit_buffer)))
        if qty < 1:
            raise ValueError(f"${usd:.2f} buys less than 1 share of {symbol}")
        return self._submit(symbol, "buy", qty)

    def _sell(self, symbol: str, qty: float) -> Fill:
        qty = int(min(qty, self._qty_held(symbol)))
        if qty < 1:
            raise RuntimeError(f"No shares of {symbol} held at the broker")
        return self._submit(symbol, "sell", qty)
