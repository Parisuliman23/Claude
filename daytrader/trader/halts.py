"""Halt-risk protection from Level 1 data (no Level 2 / halt feed needed).

1. LULD bands (Limit Up-Limit Down, SEC/FINRA plan): during regular hours a stock is halted
   when its price leaves a band around its 5-minute average price. For Tier 2 stocks (the
   small caps Ross trades):  price > $3: ±10%,  $0.75-$3: ±20%,  < $0.75: lesser of $0.15/75%.
   Bands double 9:30-9:45 and 15:35-16:00 ET. No LULD bands premarket/after-hours.
2. Spread spike: market makers pulling bids before a drop widen the spread suddenly.
3. Halt suspicion: no new trade prints on a fast-moving stock for a while during regular hours.
"""
from __future__ import annotations

from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def luld_pct(price: float) -> float:
    if price > 3.0:
        return 0.10
    if price >= 0.75:
        return 0.20
    return min(0.15 / price, 0.75) if price > 0 else 0.75


def luld_active(now: datetime | None = None) -> tuple[bool, float]:
    """(bands active?, multiplier). Bands apply 9:30-16:00 ET on weekdays, doubled near open/close."""
    now = (now or datetime.now(timezone.utc)).astimezone(ET)
    if now.weekday() >= 5:
        return False, 1.0
    t = now.time()
    if not (dtime(9, 30) <= t < dtime(16, 0)):
        return False, 1.0
    if t < dtime(9, 45) or t >= dtime(15, 35):
        return True, 2.0
    return True, 1.0


def luld_bands(candles_1m: list[list[float]], now: datetime | None = None) -> dict | None:
    """Estimated bands from the last 5 one-minute candles (reference = 5-min average price)."""
    active, mult = luld_active(now)
    if not active or len(candles_1m) < 2:
        return None
    last5 = candles_1m[-5:]
    ref = sum((c[2] + c[3] + c[4]) / 3 for c in last5) / len(last5)
    pct = luld_pct(ref) * mult
    return {"reference": ref, "pct": pct, "lower": ref * (1 - pct), "upper": ref * (1 + pct)}


def spread_pct(book: dict) -> float | None:
    bid, ask = book.get("best_bid"), book.get("best_ask")
    if not bid or not ask or ask <= bid:
        return None
    return (ask - bid) / ((ask + bid) / 2) * 100


def entry_block(market, symbol: str, r) -> str | None:
    """Reason not to buy right now (wide spread, or right next to a LULD halt band)."""
    if not r.halt_protection:
        return None
    try:
        sp = spread_pct(market.order_book(symbol))
    except Exception:
        sp = None
    if sp is not None and sp > r.max_entry_spread_pct:
        return (f"spread {sp:.2f}% is over {r.max_entry_spread_pct}% (illiquid / bids pulled); "
                "can't get out cleanly")
    try:
        bands = luld_bands(market.candles(symbol, "1m", 6))
        price = market.price(symbol)
    except Exception:
        bands = None
    if bands:
        buf = r.luld_entry_buffer_pct / 100
        if price <= bands["lower"] * (1 + buf):
            return f"price {price:.2f} is near the limit-down halt band {bands['lower']:.2f}"
        if price >= bands["upper"] * (1 - buf):
            return (f"price {price:.2f} is near the limit-up halt band {bands['upper']:.2f}: a halt here "
                    "could trap the position")
    return None


def exit_signal(market, symbol: str, pos, r, candles=None) -> tuple[str, str] | None:
    """('all'|'half', reason) if halt risk says get out, else None."""
    if not r.halt_protection:
        return None
    try:
        price = market.price(symbol)
        candles = candles if candles is not None else market.candles(symbol, "1m", 6)
        bands = luld_bands(candles)
    except Exception:
        bands = None
    if bands:
        if price <= bands["lower"] * (1 + r.luld_exit_buffer_pct / 100):
            return "all", f"approaching the limit-down halt band ({price:.2f} vs {bands['lower']:.2f})"
        if not pos.scaled_out and price >= bands["upper"] * (1 - r.luld_upper_scale_pct / 100):
            return "half", f"approaching the limit-up halt band ({price:.2f} vs {bands['upper']:.2f}): taking half"
    try:
        sp = spread_pct(market.order_book(symbol))
    except Exception:
        sp = None
    base = pos.entry_spread_pct
    if sp is not None and base is not None and sp >= max(r.spread_spike_min_pct, base * r.spread_spike_mult):
        return "all", f"spread blew out to {sp:.2f}% (was {base:.2f}% at entry): bids pulled"
    return None


_real_active = luld_active
