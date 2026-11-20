"""Ross Cameron's 5-pillar momentum scanner.

Stocks: price $1-$20 (sweet spot $5-$10), up >=10% (leading gainers), relative
volume >=5x, a news catalyst (preferred), float <20M (10M in a cold market).
Buyouts / mergers / acquisitions are skipped ("the value is now fixed").
Crypto (adapted): up >=10% in 24h, relative volume >=3x, minimum liquidity.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from .config import Config

log = logging.getLogger("trader.scanner")

# Ross: "no to catalysts such as mergers, buyouts, or acquisitions"
# (A 13D "acquisition of X shares" by an investor is NOT a buyout: Ross treats it as a positive catalyst.)
REJECT_WORDS = ("merger", "to merge", "merge with", "to be acquired", "acquired by", "agreement to acquire",
                "will acquire all", "buyout", "buy-out", "take private", "take-private", "go-private",
                "going private", "tender offer", "per share in cash")
# Dilution red flags: allowed, but Claude is warned
DILUTION_WORDS = ("offering", "priced", "warrants", "registered direct", "private placement",
                  "shelf", "atm program", "at-the-market", "reverse split")


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
        self.market_temperature = "unknown"

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
                self._bonus(sym, price, c)
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
                news = self.market.news(sym, limit=5, hours=s.news_max_age_hours)
                c["news"] = news[:3]
                p["news_catalyst"] = bool(news)
                text = " ".join(((n.get("headline") or "") + " " + (n.get("summary") or "")).lower()
                                for n in news)
                if any(w in text for w in REJECT_WORDS):
                    p["not_buyout_or_merger"] = False
                    c["flags"].append("buyout/merger/acquisition news: price pinned, Ross avoids")
                if any(w in text for w in DILUTION_WORDS):
                    c["flags"].append("possible dilution (offering/warrants/reverse split) in the news")
                if not news:
                    c["flags"].append("no news catalyst: technical breakout/short squeeze at best, trade "
                                      "with caution (half size)")
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
            if p.get("not_buyout_or_merger") is False:
                failed.append("not_buyout_or_merger")
            # size factor: Ross reduces size on no-news and thin-volume names
            sf = 1.0
            if stocks and not p.get("news_catalyst"):
                sf *= s.no_news_size_factor
            if stocks and (c.get("day_volume") or 0) < s.thin_volume_shares:
                sf *= s.thin_volume_size_factor
                c["flags"].append(f"thin volume (<{s.thin_volume_shares:,.0f} shares): reduced size")
            c["size_factor"] = sf
            if stocks and price < 2:
                sf *= 0.5
                c["flags"].append("under $2: under 4% of Ross's profit came from these; half size")
            c["size_factor"] = sf
            if stocks and 5 <= price <= 10:
                c["flags"].append("$5-$10: Ross's sweet spot")
            if stocks and price > 10:
                c["flags"].append("over $10: Ross's metrics are weaker here; be pickier")
            c["passes"] = not failed
            c["failed_pillars"] = sorted(set(failed))
            c["score"] = (len(required) - len(set(failed))) * 100 + (c.get("relative_volume") or 0) + chg / 10
            out.append(c)

        # Ross focuses on the leading gainers: rank passing names by % gain
        out.sort(key=lambda c: (c["passes"], c["change_pct"]), reverse=True)
        for i, c in enumerate(out, 1):
            c["rank"] = i
        self.last = out[: s.max_candidates]
        n_pass = sum(c["passes"] for c in self.last)
        self.market_temperature = "hot" if n_pass >= 3 else "normal" if n_pass >= 1 else "cold"
        return self.last

    def _bonus(self, sym: str, price: float, c: dict) -> None:
        """Ross's bonus criteria: yesterday's volume <100k, at/near 52-week (≈all-time) highs.
        (Recent IPO / reverse split show up in the news and daily chart; Claude checks.)"""
        try:
            daily = self.market.candles(sym, "1d", 260)
        except Exception:
            return
        if len(daily) < 2:
            c["flags"].append("bonus: very little trading history (recent IPO?)")
            return
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()
        past = [b for b in daily if datetime.fromtimestamp(b[0] / 1000, timezone.utc).date() < today]
        if past:
            prev_vol = past[-1][5]
            c["prev_day_volume"] = prev_vol
            if prev_vol < 100_000:
                c["flags"].append("bonus: yesterday's volume <100k (surprise demand)")
            hi = max(b[2] for b in past)
            if price >= hi * 0.98:
                c["flags"].append("bonus: at/near 52-week high: blue sky, no overhead resistance")
            if len(past) < 60:
                c["flags"].append("bonus: under ~3 months of trading history (recent IPO?)")

    def size_factor(self, symbol: str) -> float:
        for c in self.last:
            if c["symbol"] == symbol:
                return c.get("size_factor", 1.0)
        return 1.0

    def day_volume(self, symbol: str) -> float | None:
        for c in self.last:
            if c["symbol"] == symbol:
                return c.get("day_volume")
        return None

    def approved_symbols(self) -> set[str]:
        return {c["symbol"] for c in self.last if c["passes"]}
