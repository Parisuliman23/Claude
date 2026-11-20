"""Small dependency-free indicator set used to summarize candles for Claude.

Candles are ccxt OHLCV rows: [timestamp_ms, open, high, low, close, volume].
"""
from __future__ import annotations


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    avg_g, avg_l = gains / period, losses / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_g = (avg_g * (period - 1) + max(d, 0)) / period
        avg_l = (avg_l * (period - 1) + max(-d, 0)) / period
    if avg_l == 0:
        return 100.0
    return 100 - 100 / (1 + avg_g / avg_l)


def atr(candles: list[list[float]], period: int = 14) -> float | None:
    if len(candles) <= period:
        return None
    trs = []
    for i in range(1, len(candles)):
        _, _, h, l, _, _ = candles[i][:6]
        prev_c = candles[i - 1][4]
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    a = sum(trs[:period]) / period
    for tr in trs[period:]:
        a = (a * (period - 1) + tr) / period
    return a


def vwap(candles: list[list[float]]) -> float | None:
    pv = sum(((c[2] + c[3] + c[4]) / 3) * c[5] for c in candles)
    vol = sum(c[5] for c in candles)
    return pv / vol if vol else None


def _r(x: float | None, nd: int = 4) -> float | None:
    return None if x is None else round(x, nd)


def summarize(candles: list[list[float]], recent: int = 12) -> dict:
    """Compact summary of a candle series for the model."""
    if not candles:
        return {"error": "no candles"}
    closes = [c[4] for c in candles]
    last = closes[-1]
    first = closes[0]
    hi = max(c[2] for c in candles)
    lo = min(c[3] for c in candles)
    vols = [c[5] for c in candles]
    avg_vol = sum(vols[:-1]) / max(len(vols) - 1, 1)
    a = atr(candles)
    return {
        "last_close": last,
        "change_pct_over_window": _r((last / first - 1) * 100, 2),
        "window_high": hi,
        "window_low": lo,
        "ema_9": _r(ema(closes, 9)),
        "ema_21": _r(ema(closes, 21)),
        "ema_50": _r(ema(closes, 50)),
        "rsi_14": _r(rsi(closes), 1),
        "atr_14": _r(a),
        "atr_pct": _r(a / last * 100, 2) if a else None,
        "vwap_window": _r(vwap(candles)),
        "last_volume_vs_avg": _r(vols[-1] / avg_vol, 2) if avg_vol else None,
        "recent_candles_ohlcv": [
            [round(x, 6) for x in c[1:6]] for c in candles[-recent:]
        ],
    }


# ---------------------------------------------------------------------------
# Ross Cameron-style tools: MACD, session VWAP, and pullback/bull-flag detection
# ---------------------------------------------------------------------------

def ema_series(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    k = 2 / (period + 1)
    e = sum(values[:period]) / period
    out[period - 1] = e
    for i in range(period, len(values)):
        e = values[i] * k + e * (1 - k)
        out[i] = e
    return out


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict | None:
    if len(closes) < slow + signal:
        return None
    f, s = ema_series(closes, fast), ema_series(closes, slow)
    line = [a - b for a, b in zip(f, s) if a is not None and b is not None]
    sig = ema_series(line, signal)
    if sig[-1] is None:
        return None
    hist = line[-1] - sig[-1]
    prev_hist = line[-2] - sig[-2] if len(line) > 1 and sig[-2] is not None else None
    return {
        "macd": line[-1],
        "signal": sig[-1],
        "histogram": hist,
        "open": hist > 0,  # Ross: "green light" when MACD is above its signal line
        "crossed_down_last_bar": prev_hist is not None and prev_hist > 0 >= hist,
    }


def session_vwap(candles: list[list[float]], session_start_ms: int | None) -> float | None:
    """VWAP from the session start (premarket included for stocks)."""
    rows = [c for c in candles if session_start_ms is None or c[0] >= session_start_ms]
    return vwap(rows) if rows else None


def analyze_setup(candles: list[list[float]], live_price: float | None = None,
                  vwap_value: float | None = None, lookback: int = 30) -> dict:
    """Detect the first-pullback / bull-flag structure on short-timeframe candles.

    Pole = run from the lowest low to the swing high in the lookback window.
    Pullback = closed candles after the swing high. Entry trigger (Ross) = the
    first candle to make a new high, i.e. price breaking the last pullback
    candle's high. Stop = pullback low.
    """
    if len(candles) < 30:
        return {"state": "not_enough_data"}
    closes = [c[4] for c in candles]
    win = candles[-lookback:]
    hi_rel = max(range(len(win)), key=lambda i: win[i][2])
    swing_high = win[hi_rel][2]
    pole_bars = win[: hi_rel + 1]
    pole_low_rel = min(range(len(pole_bars)), key=lambda i: pole_bars[i][3])
    pole_low = pole_bars[pole_low_rel][3]
    pole = win[pole_low_rel: hi_rel + 1]
    pullback = win[hi_rel + 1:]

    e9, e20 = ema(closes, 9), ema(closes, 20)
    e200 = ema(closes, 200)
    m = macd(closes)
    last = closes[-1]
    price = live_price or last
    vw = vwap_value if vwap_value is not None else vwap(candles)
    front_side = bool(e9 and e20 and e9 > e20 and m and m["open"] and vw and price > vw)

    out: dict = {
        "price": price,
        "swing_high": swing_high,
        "pole_low": pole_low,
        "pole_gain_pct": round((swing_high / pole_low - 1) * 100, 2) if pole_low else None,
        "ema9": _r(e9), "ema20": _r(e20), "ema200": _r(e200),
        "vwap": _r(vw),
        "above_vwap": bool(vw and price > vw),
        "macd_open": bool(m and m["open"]),
        "macd_crossed_down_last_bar": bool(m and m["crossed_down_last_bar"]),
        "front_side": front_side,
        "pullback_candles": len(pullback),
    }
    if not pullback:
        out["state"] = "extending" if front_side else "at_high_no_pullback"
        out["note"] = "No pullback yet. Ross waits for the first pullback instead of chasing."
        return out

    pb_low = min(c[3] for c in pullback)
    pole_range = swing_high - pole_low
    retrace = (swing_high - pb_low) / pole_range if pole_range > 0 else 1.0
    pole_vol = sum(c[5] for c in pole) / max(len(pole), 1)
    pb_vol = sum(c[5] for c in pullback) / len(pullback)
    trigger = pullback[-1][2]  # break of the last pullback candle's high
    risk = (trigger - pb_low) if trigger > pb_low else None
    out.update({
        "pullback_low": pb_low,
        "retrace_of_pole_pct": round(retrace * 100, 1),
        "pullback_vol_vs_pole": round(pb_vol / pole_vol, 2) if pole_vol else None,
        "entry_trigger": trigger,
        "stop": pb_low,
        "risk_per_unit": _r(risk, 6),
        "risk_pct": round(risk / trigger * 100, 2) if risk else None,
        "target_2r": _r(trigger + 2 * risk, 6) if risk else None,
        "room_to_swing_high_r": round((swing_high - trigger) / risk, 2) if risk else None,
    })

    problems = []
    if len(pullback) > 8:
        problems.append("pullback too long (>8 candles): momentum fading")
    if retrace > 0.5:
        problems.append("retraced >50% of the pole: weak")
    if pb_vol and pole_vol and pb_vol >= pole_vol:
        problems.append("pullback volume not lighter than the pole: sellers in control")
    if not out["above_vwap"]:
        problems.append("below VWAP")
    if not out["macd_open"]:
        problems.append("MACD below signal (red light)")
    if e9 and e20 and e9 <= e20:
        problems.append("9 EMA below 20 EMA (back side)")
    out["problems"] = problems

    if problems:
        out["state"] = "no_setup"
    elif price > trigger:
        out["state"] = "triggered"  # first candle making a new high
    else:
        out["state"] = "setup_forming"
    return out
