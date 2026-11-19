"""Hard risk limits. Every order Claude asks for passes through here first.

Claude can be wrong; these rules are what keep a bad decision small.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .broker import BaseBroker
from .config import Config


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@dataclass
class Decision:
    ok: bool
    usd: float = 0.0
    reason: str = ""
    adjustments: list[str] | None = None


class RiskManager:
    def __init__(self, cfg: Config, broker: BaseBroker):
        self.cfg = cfg
        self.r = cfg.risk
        self.broker = broker
        self.path = cfg.state_dir / f"risk_{cfg.mode}.json"
        self.kill_file = cfg.state_dir / "KILL"
        self.state = {"day": None, "day_start_equity": None, "trades_today": 0,
                      "halted_reason": None}
        if self.path.exists():
            self.state.update(json.loads(self.path.read_text()))

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.state, indent=2))

    # -- daily bookkeeping -------------------------------------------------
    def roll_day(self) -> None:
        today = utc_day()
        if self.state["day"] != today:
            self.state.update(day=today, day_start_equity=self.broker.equity(),
                              trades_today=0, halted_reason=None)
            self._save()

    def day_pnl(self) -> tuple[float, float]:
        self.roll_day()
        start = self.state["day_start_equity"] or self.broker.equity()
        pnl = self.broker.equity() - start
        return pnl, (pnl / start if start else 0.0)

    def halted(self) -> str | None:
        if self.kill_file.exists():
            return "Kill switch file state/KILL exists. Delete it to resume trading."
        self.roll_day()
        if self.state["halted_reason"]:
            return self.state["halted_reason"]
        _, pct = self.day_pnl()
        if pct <= -self.r.max_daily_loss_pct:
            self.state["halted_reason"] = (
                f"Daily loss limit hit ({pct*100:.2f}% <= -{self.r.max_daily_loss_pct*100:.2f}%). "
                "No new trades until 00:00 UTC."
            )
            self._save()
            return self.state["halted_reason"]
        return None

    def record_trade(self) -> None:
        self.roll_day()
        self.state["trades_today"] += 1
        self._save()

    def trades_left(self) -> int:
        self.roll_day()
        return max(self.r.max_trades_per_day - self.state["trades_today"], 0)

    # -- order checks ------------------------------------------------------
    def check_open(self, symbol: str, usd: float, stop: float | None, tp: float | None) -> Decision:
        if (h := self.halted()):
            return Decision(False, reason=h)
        if symbol not in self.cfg.symbols:
            return Decision(False, reason=f"{symbol} is not in the allowed list {self.cfg.symbols}")
        if symbol in self.broker.positions:
            return Decision(False, reason=f"Already holding {symbol}. Close it or adjust its stops instead.")
        if self.trades_left() <= 0:
            return Decision(False, reason=f"Max trades per day ({self.r.max_trades_per_day}) reached.")
        if usd <= 0:
            return Decision(False, reason="usd_amount must be positive.")

        price = self.broker.market.price(symbol)
        stop_dist = None
        if stop is None:
            if self.r.require_stop_loss:
                return Decision(False, reason="A stop_loss is required for every trade.")
        else:
            if stop >= price:
                return Decision(False, reason=f"stop_loss {stop} must be below current price {price}.")
            stop_dist = (price - stop) / price
            if stop_dist > self.r.max_stop_distance_pct:
                return Decision(False, reason=(
                    f"stop_loss is {stop_dist*100:.2f}% away; max allowed is "
                    f"{self.r.max_stop_distance_pct*100:.2f}%."))
        if tp is not None and tp <= price:
            return Decision(False, reason=f"take_profit {tp} must be above current price {price}.")

        equity = self.broker.equity()
        notes = []
        caps = {
            "max_position_pct": self.r.max_position_pct * equity,
            "max_total_exposure_pct": self.r.max_total_exposure_pct * equity - self.broker.exposure(),
            "available_cash": self.broker.cash() * 0.99,  # leave room for fees
        }
        if stop_dist:
            # size so that hitting the stop loses at most risk_per_trade_pct of equity
            # (+ fee/slippage buffer)
            caps["risk_per_trade_pct"] = self.r.risk_per_trade_pct * equity / (stop_dist + 0.01)
        size = usd
        for name, cap in caps.items():
            if size > cap:
                notes.append(f"reduced from ${size:,.2f} to ${max(cap,0):,.2f} by {name}")
                size = cap
        if size < self.r.min_order_usd:
            return Decision(False, reason=(
                f"Allowed size ${max(size,0):,.2f} is below the minimum order "
                f"${self.r.min_order_usd}. ({'; '.join(notes)})"))
        return Decision(True, usd=round(size, 2), adjustments=notes)

    def check_stop_update(self, symbol: str, new_stop: float | None, new_tp: float | None) -> Decision:
        pos = self.broker.positions.get(symbol)
        if not pos:
            return Decision(False, reason=f"No open position in {symbol}.")
        price = self.broker.market.price(symbol)
        if new_stop is not None:
            if pos.stop_loss is not None and new_stop < pos.stop_loss:
                return Decision(False, reason=(
                    f"Stops can only be tightened (raised). Current {pos.stop_loss}, requested {new_stop}."))
            if new_stop >= price:
                return Decision(False, reason=f"New stop {new_stop} must be below price {price}. "
                                              "Use close_position to exit now.")
        if new_tp is not None and new_tp <= price:
            return Decision(False, reason=f"take_profit {new_tp} must be above price {price}.")
        return Decision(True)

    def flatten_due(self, now: datetime | None = None) -> bool:
        if not self.r.flatten_at_utc:
            return False
        now = now or datetime.now(timezone.utc)
        hh, mm = map(int, self.r.flatten_at_utc.split(":"))
        return (now.hour, now.minute) >= (hh, mm)

    def snapshot(self) -> dict:
        pnl, pct = self.day_pnl()
        return {
            "day_utc": self.state["day"],
            "day_pnl_usd": round(pnl, 2),
            "day_pnl_pct": round(pct * 100, 3),
            "trades_today": self.state["trades_today"],
            "trades_left_today": self.trades_left(),
            "trading_halted": self.halted(),
            "limits": {
                "max_position_pct_of_equity": self.r.max_position_pct * 100,
                "max_total_exposure_pct": self.r.max_total_exposure_pct * 100,
                "risk_per_trade_pct": self.r.risk_per_trade_pct * 100,
                "max_daily_loss_pct": self.r.max_daily_loss_pct * 100,
                "max_stop_distance_pct": self.r.max_stop_distance_pct * 100,
                "stop_loss_required": self.r.require_stop_loss,
                "flatten_at_utc": self.r.flatten_at_utc,
            },
        }
