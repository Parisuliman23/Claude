"""Ross Cameron's 5-pillar momentum scanner.

Stocks: price $2-$20, up >=10%, relative volume >=5x, fresh news, float <20M.
Crypto (adapted): up >=10% in 24h, relative volume >=3x, minimum liquidity.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from .config import Config

log = logging.getLogger("trader.scanner")


def _hours_since(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).total_seconds() / 3600
    except ValueError:
        return None


class Scanner:
    def __init__(self, cfg: Config, market):
        self.cfg = cfg
        self.s = cfg.scanner
        self.market = market
        self.last: list[dict] = []

    def _universe(self) -> list[dict]:
        if self.cfg.symbols:  # fixed allowlist: rank just those
            rows = []
            for sym in self.cfg.symbols:
                try:
                    t = self.market.ticker(sym)
                    chg = t.get("change_pct_vs_prev_close", t.get("change_24h_pct"))
                    rows.append({"symbol": sym, "percent_change": chg, "price": t.get("last")})
                except Exception as e:
                    log.warning("ticker %s failed: %s", sym, e)
            return rows
        rows = self.market.top_gainers(self.s.universe_size)
        if self.market.kind == "crypto":
            q = "/" + self.cfg.quote_currency
            rows = [r for r in rows if r["symbol"].endswith(q)
                    and (r.get("quote_volume_24h") or 0) >= self.s.crypto_min_quote_volume]
        return rows

    def scan(self) -> list[dict]:
        s = self.s
        stocks = self.market.kind == "stocks"
        out = []
        for row in self._universe():
            sym, chg, price = row["symbol"], row.get("percent_change"), row.get("price")
            if price is None or chg is None:
                continue
            # cheap filters first, so we only pay API calls for real candidates
            if chg < s.min_gain_pct:
                continue
            if stocks and not (s.price_min <= price <= s.price_max):
                continue
            c = {"symbol": sym, "price": price, "change_pct": round(chg, 2), "pillars": {}, "flags": []}
            p = c["pillars"]
            p["price"] = True if not stocks else s.price_min <= price <= s.price_max
            p["percent_change"] = True

            try:
                t = self.market.ticker(sym)
                day_vol = t.get("day_volume") or t.get("quote_volume_24h")
                avg = self.market.avg_daily_volume(sym)
                if stocks:
                    rvol = (t.get("day_volume") or 0) / avg if avg else None
                else:
                    base_vol = (t.get("quote_volume_24h") or 0) / price if price else 0
                    rvol = base_vol / avg if avg else None
                c["relative_volume"] = round(rvol, 2) if rvol else None
                c["day_volume"] = day_vol
                min_rvol = s.min_rvol if stocks else s.crypto_min_rvol
                p["relative_volume"] = bool(rvol and rvol >= min_rvol)
            except Exception as e:
                c["relative_volume"] = None
                p["relative_volume"] = False
                c["flags"].append(f"volume data error: {e}")

            if stocks:
                news = self.market.news(sym, limit=3, hours=s.news_max_age_hours)
                c["news"] = news
                p["news_catalyst"] = bool(news)
                if news:
                    age = _hours_since(news[0].get("time"))
                    c["latest_news_hours_ago"] = round(age, 1) if age is not None else None

                flt = self.market.floats.get(sym)
                c["float_shares"] = flt
                if flt is None:
                    p["float"] = None  # unknown
                    c["flags"].append("float unknown (set FMP_API_KEY to check it)")
                else:
                    p["float"] = flt <= s.max_float
                    if c.get("day_volume") and flt:
                        c["float_rotation_x"] = round(c["day_volume"] / flt, 2)
                    if flt <= 5_000_000:
                        c["flags"].append("sub-5M float: 'rocket fuel' but extremely volatile")

                asset = self.market.asset(sym)
                if asset and (asset.get("exchange") == "OTC" or not asset.get("tradable", True)):
                    c["flags"].append("OTC or not tradable")
                    p["exchange_listed"] = False
            else:
                p["news_catalyst"] = None
                p["float"] = None

            required = ["price", "percent_change", "relative_volume"]
            if stocks and s.require_news:
                required.append("news_catalyst")
            if stocks and s.require_float_known:
                required.append("float")
            failed = [k for k in required if not p.get(k)]
            if stocks and p.get("float") is False:
                failed.append("float")
            if p.get("exchange_listed") is False:
                failed.append("exchange_listed")
            c["passes"] = not failed
            c["failed_pillars"] = sorted(set(failed))
            c["score"] = (len(required) - len(set(failed))) * 100 + (c.get("relative_volume") or 0) + chg / 10
            out.append(c)

        out.sort(key=lambda c: (c["passes"], c["score"]), reverse=True)
        self.last = out[: s.max_candidates]
        return self.last

    def approved_symbols(self) -> set[str]:
        return {c["symbol"] for c in self.last if c["passes"]}
