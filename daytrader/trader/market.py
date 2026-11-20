"""Exchange access through ccxt: market data, and (in live mode) the authenticated client."""
from __future__ import annotations

import os
import time

import ccxt

from .config import Config

TIMEFRAMES = ("1m", "5m", "15m", "1h", "4h", "1d")


def make_exchange(cfg: Config) -> ccxt.Exchange:
    cls = getattr(ccxt, cfg.exchange, None)
    if cls is None:
        raise ValueError(f"Unknown ccxt exchange id: {cfg.exchange}")
    params: dict = {"enableRateLimit": True}
    if cfg.is_live:
        key, secret = os.environ.get("EXCHANGE_API_KEY"), os.environ.get("EXCHANGE_API_SECRET")
        if not key or not secret:
            raise RuntimeError("Live mode needs EXCHANGE_API_KEY and EXCHANGE_API_SECRET in .env")
        params.update(apiKey=key, secret=secret)
        if os.environ.get("EXCHANGE_API_PASSWORD"):
            params["password"] = os.environ["EXCHANGE_API_PASSWORD"]
    return cls(params)


class MarketData:
    """Thin wrapper with a short price cache so tools and the monitor don't hammer the API."""

    kind = "crypto"

    def __init__(self, exchange: ccxt.Exchange, cache_seconds: float = 5.0):
        self.ex = exchange
        self.cache_seconds = cache_seconds
        self._prices: dict[str, tuple[float, float]] = {}
        self._markets_loaded = False

    def _load(self) -> None:
        if not self._markets_loaded:
            self.ex.load_markets()
            self._markets_loaded = True

    def price(self, symbol: str) -> float:
        now = time.time()
        hit = self._prices.get(symbol)
        if hit and now - hit[1] < self.cache_seconds:
            return hit[0]
        self._load()
        t = self.ex.fetch_ticker(symbol)
        p = t.get("last") or t.get("close") or ((t.get("bid") or 0) + (t.get("ask") or 0)) / 2
        if not p:
            raise RuntimeError(f"No price for {symbol}")
        self._prices[symbol] = (float(p), now)
        return float(p)

    def ticker(self, symbol: str) -> dict:
        self._load()
        t = self.ex.fetch_ticker(symbol)
        return {
            "symbol": symbol,
            "last": t.get("last"),
            "bid": t.get("bid"),
            "ask": t.get("ask"),
            "change_24h_pct": t.get("percentage"),
            "high_24h": t.get("high"),
            "low_24h": t.get("low"),
            "quote_volume_24h": t.get("quoteVolume"),
        }

    def candles(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
        if timeframe not in TIMEFRAMES:
            raise ValueError(f"timeframe must be one of {TIMEFRAMES}")
        self._load()
        return self.ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    def order_book(self, symbol: str, depth: int = 20) -> dict:
        self._load()
        ob = self.ex.fetch_order_book(symbol, limit=depth)
        bids, asks = ob.get("bids") or [], ob.get("asks") or []
        if not bids or not asks:
            return {"symbol": symbol, "error": "empty order book"}
        best_bid, best_ask = bids[0][0], asks[0][0]
        mid = (best_bid + best_ask) / 2
        bid_val = sum(p * q for p, q, *_ in bids[:depth])
        ask_val = sum(p * q for p, q, *_ in asks[:depth])
        return {
            "symbol": symbol,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread_pct": round((best_ask - best_bid) / mid * 100, 4),
            f"bid_depth_top{depth}_quote": round(bid_val, 2),
            f"ask_depth_top{depth}_quote": round(ask_val, 2),
            "imbalance_bid_minus_ask_pct": round((bid_val - ask_val) / (bid_val + ask_val) * 100, 2)
            if bid_val + ask_val
            else None,
        }

    def session_start_ms(self) -> int | None:
        """Crypto has no session: VWAP uses the candles requested."""
        return None

    def top_gainers(self, top: int = 50) -> list[dict]:
        """24h top gainers among the exchange's pairs in the quote currency."""
        self._load()
        tickers = self.ex.fetch_tickers()
        rows = []
        for s, t in tickers.items():
            if t.get("percentage") is None or not t.get("last"):
                continue
            rows.append({"symbol": s, "percent_change": t["percentage"], "price": t["last"],
                         "quote_volume_24h": t.get("quoteVolume")})
        rows.sort(key=lambda r: r["percent_change"], reverse=True)
        return rows[:top]

    def avg_daily_volume(self, symbol: str, days: int = 30) -> float | None:
        bars = self.candles(symbol, "1d", days + 1)[:-1]
        return sum(b[5] for b in bars) / len(bars) if bars else None

    def news(self, symbol: str, limit: int = 5, hours: int = 36) -> list[dict]:
        return []  # no free crypto news feed wired in; Claude is told so
