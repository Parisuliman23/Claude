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
