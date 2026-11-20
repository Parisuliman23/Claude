"""The tools Claude can call, and the code that runs them.

Every order goes through RiskManager first. Errors come back to Claude as
tool_result errors so it can adjust instead of crashing the cycle.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .broker import BaseBroker
from .config import Config
from .indicators import analyze_setup, macd, session_vwap, summarize
from .market import TIMEFRAMES
from .risk import RiskManager
from .scanner import Scanner

TF_MS = {"1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000,
         "1d": 86_400_000}


def closed_candles(candles: list[list[float]], timeframe: str, now_ms: float | None = None) -> list:
    """Drop the still-forming last candle (Ross reads patterns on completed candles)."""
    now_ms = now_ms or time.time() * 1000
    if candles and candles[-1][0] + TF_MS.get(timeframe, 60_000) > now_ms:
        return candles[:-1]
    return candles


class Journal:
    """Append-only JSONL log of everything the agent does."""

    def __init__(self, path: Path):
        self.path = path

    def log(self, event: str, **data) -> None:
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **data}
        with self.path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    def tail(self, n: int, events: set[str] | None = None) -> list[dict]:
        if not self.path.exists():
            return []
        rows = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]
        if events:
            rows = [r for r in rows if r["event"] in events]
        return rows[-n:]


def _num(schema_desc: str) -> dict:
    return {"type": "number", "description": schema_desc}


TOOL_DEFS = [
    {
        "name": "get_account",
        "description": "Cash, equity, open positions with unrealized P&L and their stop/target levels, "
                       "today's P&L, trades left today, and the hard risk limits.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_market_data",
        "description": "Chart read for one symbol and timeframe: last price, EMA 9/20/200, MACD "
                       "(open = above signal), VWAP (session VWAP for stocks), RSI, ATR, volume vs "
                       "average, recent candles [open, high, low, close, volume], the ticker, and on "
                       "1m/5m a 'setup' block that detects the first-pullback/bull-flag: pole, "
                       "pullback low (stop), entry trigger (first candle to make a new high), "
                       "risk per share, 2R target and any problems. Use 1m/5m for entries and 1d for "
                       "daily levels/resistance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "e.g. BTC/USD"},
                "timeframe": {"type": "string", "enum": list(TIMEFRAMES)},
                "limit": {"type": "integer", "description": "Candles to analyze, 30-300. Default 100."},
            },
            "required": ["symbol", "timeframe"],
            "additionalProperties": False,
        },
    },
    {
        "name": "scan_momentum",
        "description": "Run the 5-pillar momentum scanner (Ross Cameron): price $1-$20, up >=10% on "
                       "the day, relative volume >=5x vs the 50-day average, news catalyst (preferred), "
                       "float <20M; buyouts/mergers excluded. Returns candidates ranked by % gain (the "
                       "leader is #1) with each pillar, headlines, float rotation, size factor, flags, "
                       "and a market temperature (hot/normal/cold). Only symbols that PASS can be traded.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_news",
        "description": "Recent headlines for a symbol (catalyst check: earnings, FDA, trial results, "
                       "contracts; watch for offerings/dilution).",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "set_watchlist",
        "description": "Choose up to 5 symbols for code to watch on the 1-minute chart between your "
                       "cycles. When one forms a first-pullback trigger (first candle to make a new "
                       "high, above VWAP, MACD open), you are woken immediately to decide.",
        "input_schema": {
            "type": "object",
            "properties": {"symbols": {"type": "array", "items": {"type": "string"}}},
            "required": ["symbols"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_order_book",
        "description": "Best bid/ask, spread, and buy-vs-sell depth imbalance for a symbol.",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "open_long",
        "description": "Buy a coin with a market order. Spot, long-only. Requires a stop_loss below "
                       "the current price. The risk manager may shrink usd_amount to fit the limits "
                       "and will reject the order if it breaks a rule; the result tells you what "
                       "actually happened. One position per symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "usd_amount": _num("How much quote currency to spend."),
                "stop_loss": _num("Price at which code will sell to cut the loss."),
                "take_profit": _num("Optional price at which code will sell to take profit."),
                "reason": {"type": "string", "description": "Your thesis for this trade, 1-3 sentences."},
            },
            "required": ["symbol", "usd_amount", "stop_loss", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "close_position",
        "description": "Sell an entire open position at market now.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["symbol", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "sell_partial",
        "description": "Sell part of a position (e.g. 0.5 = half into strength). Ross scales out half "
                       "on the first push and lets the rest ride with a break-even stop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "fraction": {"type": "number", "description": "0-1 portion of the shares held"},
                "reason": {"type": "string"},
            },
            "required": ["symbol", "fraction", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_stops",
        "description": "Move the stop-loss and/or take-profit of an open position. Stops can only be "
                       "raised (tightened), never lowered.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "stop_loss": _num("New stop price (must be >= the current stop)."),
                "take_profit": _num("New take-profit price."),
                "reason": {"type": "string"},
            },
            "required": ["symbol", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_trade_history",
        "description": "Your recent closed trades with P&L, and your own notes from recent decision "
                       "cycles. Use it to learn from what worked and what didn't.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Default 20."}},
            "additionalProperties": False,
        },
    },
]


class ToolError(Exception):
    pass


class Toolbox:
    def __init__(self, cfg: Config, broker: BaseBroker, risk: RiskManager, journal: Journal):
        self.cfg = cfg
        self.broker = broker
        self.risk = risk
        self.journal = journal
        self.market = broker.market
        self.scanner = Scanner(cfg, self.market)
        self.watchlist: list[str] = []

    def run(self, name: str, args: dict) -> str:
        fn = getattr(self, f"t_{name}", None)
        if fn is None:
            raise ToolError(f"Unknown tool {name}")
        return json.dumps(fn(**args), default=str)

    # -- read-only ---------------------------------------------------------
    def t_get_account(self) -> dict:
        positions = []
        for s, p in self.broker.positions.items():
            price = self.market.price(s)
            value = p.qty * price
            positions.append({
                "symbol": s,
                "qty": p.qty,
                "entry_price": p.entry_price,
                "current_price": price,
                "value_usd": round(value, 2),
                "unrealized_pnl_usd": round(value - p.cost_usd, 2),
                "unrealized_pnl_pct": round((value / p.cost_usd - 1) * 100, 3) if p.cost_usd else 0,
                "stop_loss": p.stop_loss,
                "take_profit": p.take_profit,
                "held_minutes": round((time.time() - p.opened_at) / 60, 1),
                "r_multiple": round((price - p.entry_price) / (p.entry_price - p.initial_stop), 2)
                if p.initial_stop and p.entry_price > p.initial_stop else None,
                "already_scaled_out": p.scaled_out,
                "partial_profit_banked_usd": round(p.realized_usd, 2),
            })
        return {
            "mode": self.cfg.mode,
            "cash": round(self.broker.cash(), 2),
            "equity": round(self.broker.equity(), 2),
            "positions": positions,
            "market": self.cfg.market,
            "tradable_symbols": self.cfg.symbols or sorted(self.scanner.approved_symbols()),
            "watchlist": self.watchlist,
            **self.risk.snapshot(),
        }

    def _symbol(self, symbol: str) -> str:
        symbol = symbol.upper().strip()
        if self.cfg.symbols and symbol not in self.cfg.symbols and symbol not in self.broker.positions:
            raise ToolError(f"{symbol} is not an allowed symbol. Allowed: {self.cfg.symbols}")
        return symbol

    def t_get_market_data(self, symbol: str, timeframe: str, limit: int = 100) -> dict:
        symbol = self._symbol(symbol)
        limit = max(30, min(int(limit), 300))
        candles = closed_candles(self.market.candles(symbol, timeframe, limit), timeframe)
        out = {"symbol": symbol, "timeframe": timeframe, "ticker": self.market.ticker(symbol),
               **summarize(candles)}
        closes = [c[4] for c in candles]
        m = macd(closes)
        out["macd_12_26_9"] = {k: (round(v, 6) if isinstance(v, float) else v)
                               for k, v in m.items()} if m else None
        if timeframe in ("1m", "5m"):
            out["setup"] = self.setup(symbol, timeframe, candles)
        return out

    def setup(self, symbol: str, timeframe: str = "1m", candles: list | None = None) -> dict:
        if candles is None:
            candles = closed_candles(self.market.candles(symbol, timeframe, 120), timeframe)
        vw = session_vwap(candles, self.market.session_start_ms())
        return analyze_setup(candles, live_price=self.market.price(symbol), vwap_value=vw)

    def t_scan_momentum(self) -> dict:
        cands = self.scanner.scan()
        self.journal.log("scan", passing=[c["symbol"] for c in cands if c["passes"]],
                         candidates=len(cands))
        note = None
        if not cands:
            note = "Nothing meets the criteria right now. Ross: no stock, no trade."
        elif self.market.kind == "crypto":
            note = "Crypto adaptation: no float or news data; relative volume uses 24h vs 30-day average."
        return {"market_temperature": self.scanner.market_temperature,
                "candidates": cands, "note": note}

    def t_get_news(self, symbol: str) -> dict:
        symbol = self._symbol(symbol)
        news = self.market.news(symbol, limit=8, hours=72)
        return {"symbol": symbol, "news": news,
                "note": None if news or self.market.kind == "stocks"
                else "No crypto news feed is connected; judge the catalyst from price/volume."}

    def t_set_watchlist(self, symbols: list[str]) -> dict:
        self.watchlist = [self._symbol(s) for s in symbols][:5]
        self.journal.log("watchlist", symbols=self.watchlist)
        return {"watchlist": self.watchlist}

    def t_get_order_book(self, symbol: str) -> dict:
        return self.market.order_book(self._symbol(symbol))

    def t_get_trade_history(self, limit: int = 20) -> dict:
        limit = max(1, min(int(limit), 100))
        notes = self.journal.tail(min(limit, 10), {"cycle_summary"})
        return {
            "closed_trades": self.broker.realized[-limit:],
            "win_rate_pct": self._win_rate(),
            "recent_cycle_notes": [{"ts": n["ts"], "summary": n.get("summary")} for n in notes],
        }

    def _win_rate(self) -> float | None:
        done = self.broker.completed_trades()
        if not done:
            return None
        wins = [t for t in done if t.get("trade_total_pnl_usd", t["pnl_usd"]) > 0]
        return round(len(wins) / len(done) * 100, 1)

    # -- trading -----------------------------------------------------------
    def t_open_long(self, symbol: str, usd_amount: float, stop_loss: float,
                    reason: str, take_profit: float | None = None) -> dict:
        symbol = self._symbol(symbol)
        d = self.risk.check_open(symbol, float(usd_amount), stop_loss, take_profit,
                                 allowed=self.scanner.approved_symbols(),
                                 size_factor=self.scanner.size_factor(symbol),
                                 day_volume=self.scanner.day_volume(symbol))
        if not d.ok:
            self.journal.log("order_rejected", symbol=symbol, usd=usd_amount, why=d.reason)
            return {"status": "rejected", "reason": d.reason}
        fill = self.broker.open_long(symbol, d.usd, stop_loss, take_profit)
        self.risk.record_trade()
        self.journal.log("open", symbol=symbol, usd=d.usd, qty=fill.qty, price=fill.price,
                         stop=stop_loss, tp=take_profit, reason=reason, mode=self.cfg.mode)
        return {"status": "filled", "symbol": symbol, "qty": fill.qty, "avg_price": fill.price,
                "spent_usd": round(fill.value_usd + fill.fee_usd, 2), "fee_usd": round(fill.fee_usd, 2),
                "size_adjustments": d.adjustments or [], "stop_loss": stop_loss,
                "take_profit": take_profit}

    def t_close_position(self, symbol: str, reason: str) -> dict:
        symbol = self._symbol(symbol)
        if symbol not in self.broker.positions:
            return {"status": "rejected", "reason": f"No open position in {symbol}"}
        rec = self.broker.close(symbol, f"agent: {reason}")
        self.journal.log("close", **rec)
        return {"status": "closed", **rec}

    def t_sell_partial(self, symbol: str, fraction: float, reason: str) -> dict:
        symbol = self._symbol(symbol)
        if symbol not in self.broker.positions:
            return {"status": "rejected", "reason": f"No open position in {symbol}"}
        rec = self.broker.reduce(symbol, float(fraction), f"agent: {reason}")
        self.journal.log("sell_partial", **rec)
        return {"status": "sold", **rec}

    def t_update_stops(self, symbol: str, reason: str, stop_loss: float | None = None,
                       take_profit: float | None = None) -> dict:
        symbol = self._symbol(symbol)
        d = self.risk.check_stop_update(symbol, stop_loss, take_profit)
        if not d.ok:
            return {"status": "rejected", "reason": d.reason}
        pos = self.broker.positions[symbol]
        if stop_loss is not None:
            pos.stop_loss = stop_loss
        if take_profit is not None:
            pos.take_profit = take_profit
        self.broker.save()
        self.journal.log("update_stops", symbol=symbol, stop=pos.stop_loss, tp=pos.take_profit,
                         reason=reason)
        return {"status": "updated", "symbol": symbol, "stop_loss": pos.stop_loss,
                "take_profit": pos.take_profit}
