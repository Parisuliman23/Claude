"""Hard risk limits. Every order Claude asks for passes through here first.

Includes Ross Cameron's discipline rules: max daily loss, 3 losers in a row and
you're done, don't give back more than half the day's peak profit, trade 1/4
size until you have a cushion, and only trade inside the morning window.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

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
        self.tz = ZoneInfo(self.r.trade_window_tz)
        self.path = cfg.state_dir / f"risk_{cfg.market}_{cfg.mode}.json"
        self.kill_file = cfg.state_dir / "KILL"
        self.state = {"day": None, "day_start_equity": None, "trades_today": 0,
                      "halted_reason": None, "peak_day_pnl": 0.0}
        if self.path.exists():
            self.state.update(json.loads(self.path.read_text()))

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.state, indent=2))

    def _day(self) -> str:
        # stocks: the trading day is the US/Eastern date; crypto: UTC
        if self.cfg.market == "stocks":
            return datetime.now(self.tz).strftime("%Y-%m-%d")
        return utc_day()

    # -- daily bookkeeping -------------------------------------------------
    def roll_day(self) -> None:
        today = self._day()
        if self.state["day"] != today:
            self.state.update(day=today, day_start_equity=self.broker.equity(),
                              trades_today=0, halted_reason=None, peak_day_pnl=0.0)
            self._save()

    def day_pnl(self) -> tuple[float, float]:
        self.roll_day()
        start = self.state["day_start_equity"] or self.broker.equity()
        pnl = self.broker.equity() - start
        return pnl, (pnl / start if start else 0.0)

    def update_peak(self) -> None:
        pnl, _ = self.day_pnl()
        if pnl > self.state["peak_day_pnl"]:
            self.state["peak_day_pnl"] = pnl
            self._save()

    def todays_trades(self) -> list[dict]:
        day = self.state["day"]
        out = []
        for t in self.broker.completed_trades():
            ts = datetime.fromtimestamp(t["closed_at"], timezone.utc)
            d = ts.astimezone(self.tz) if self.cfg.market == "stocks" else ts
            if d.strftime("%Y-%m-%d") == day:
                out.append(t)
        return out

    def consecutive_losses(self) -> int:
        n = 0
        for t in reversed(self.todays_trades()):
            if t.get("trade_total_pnl_usd", t["pnl_usd"]) < 0:
                n += 1
            else:
                break
        return n

    def in_window(self, now: datetime | None = None) -> bool:
        if not self.r.trade_window:
            return True
        now = (now or datetime.now(timezone.utc)).astimezone(self.tz)
        if self.cfg.market == "stocks" and now.weekday() >= 5:
            return False
        a, b = self.r.trade_window.split("-")
        start = tuple(map(int, a.split(":")))
        end = tuple(map(int, b.split(":")))
        return start <= (now.hour, now.minute) < end

    def _halt(self, reason: str) -> str:
        self.state["halted_reason"] = reason
        self._save()
        return reason

    def halted(self) -> str | None:
        """Reason no NEW trades are allowed for the rest of the day (None = OK)."""
        if self.kill_file.exists():
            return "Kill switch file state/KILL exists. Delete it to resume trading."
        self.roll_day()
        if self.state["halted_reason"]:
            return self.state["halted_reason"]
        pnl, pct = self.day_pnl()
        if pct <= -self.r.max_daily_loss_pct:
            return self._halt(f"Daily loss limit hit ({pct*100:.2f}%). Done for the day.")
        if self.r.max_consecutive_losses and self.consecutive_losses() >= self.r.max_consecutive_losses:
            return self._halt(f"{self.r.max_consecutive_losses} losing trades in a row. Done for the day "
                              "(Ross: stop before the trading spiral).")
        peak = self.state["peak_day_pnl"]
        start = self.state["day_start_equity"] or 1
        if (self.r.giveback_pct_of_peak and peak >= self.r.giveback_min_peak_pct * start
                and pnl <= peak * (1 - self.r.giveback_pct_of_peak)):
            return self._halt(f"Gave back {self.r.giveback_pct_of_peak*100:.0f}% of today's peak profit "
                              f"(peak ${peak:,.2f}, now ${pnl:,.2f}). Protecting the green day.")
        return None

    def new_trade_block(self) -> str | None:
        if (h := self.halted()):
            return h
        if not self.in_window():
            return f"Outside the trade window ({self.r.trade_window} {self.r.trade_window_tz})."
        return None

    def record_trade(self) -> None:
        self.roll_day()
        self.state["trades_today"] += 1
        self._save()

    def trades_left(self) -> int:
        self.roll_day()
        return max(self.r.max_trades_per_day - self.state["trades_today"], 0)

    def has_cushion(self) -> bool:
        pnl, _ = self.day_pnl()
        start = self.state["day_start_equity"] or self.broker.equity()
        return pnl >= self.r.cushion_pct * start

    # -- order checks ------------------------------------------------------
    def check_open(self, symbol: str, usd: float, stop: float | None, tp: float | None,
                   allowed: set[str] | None = None, size_factor: float = 1.0,
                   day_volume: float | None = None) -> Decision:
        if (h := self.new_trade_block()):
            return Decision(False, reason=h)
        allowed_set = set(self.cfg.symbols) if self.cfg.symbols else (allowed or set())
        if symbol not in allowed_set:
            why = (f"{symbol} is not in the allowed list {sorted(allowed_set)}" if self.cfg.symbols
                   else f"{symbol} has not passed the momentum scanner (5 pillars) this session. "
                        "Run scan_momentum; only stocks that pass can be traded.")
            return Decision(False, reason=why)
        if symbol in self.broker.positions:
            return Decision(False, reason=f"Already holding {symbol}. Manage it instead of adding.")
        if self.trades_left() <= 0:
            return Decision(False, reason=f"Max trades per day ({self.r.max_trades_per_day}) reached.")
        if usd <= 0:
            return Decision(False, reason="usd_amount must be positive.")

        price = self.broker.market.price(symbol)
        if self.cfg.market == "stocks":
            s = self.cfg.scanner
            if not (s.price_min <= price <= s.price_max):
                return Decision(False, reason=f"Price ${price} outside ${s.price_min}-${s.price_max}.")
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
        size_mult = 1.0
        if self.r.starter_size_fraction < 1 and not self.has_cushion():
            size_mult = self.r.starter_size_fraction
            notes.append(f"starter size x{size_mult} until the day is up "
                         f"{self.r.cushion_pct*100:.2f}% (Ross: 1/4 size until you have a cushion)")
        if size_factor < 1:
            size_mult *= size_factor
            notes.append(f"size x{size_factor} (no news catalyst and/or thin volume)")
        fee_buf = 2 * self.cfg.paper_fee_rate if self.cfg.market == "crypto" else 0.002
        caps = {
            "max_position_pct": self.r.max_position_pct * equity * size_mult,
            "max_total_exposure_pct": self.r.max_total_exposure_pct * equity - self.broker.exposure(),
            "available_cash": self.broker.cash() * 0.99,
        }
        if self.cfg.market == "stocks" and day_volume:
            caps["max_pct_of_day_volume"] = self.cfg.scanner.max_pct_of_day_volume * day_volume * price
        if stop_dist:
            caps["risk_per_trade_pct"] = (self.r.risk_per_trade_pct * equity * size_mult
                                          / (stop_dist + fee_buf))
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
        now = now or datetime.now(timezone.utc)
        if self.r.flatten_at_utc:
            hh, mm = map(int, self.r.flatten_at_utc.split(":"))
            if (now.hour, now.minute) >= (hh, mm):
                return True
        # stocks: day trades don't go home - flatten when the window closes
        if self.cfg.market == "stocks" and self.r.trade_window:
            local = now.astimezone(self.tz)
            end = tuple(map(int, self.r.trade_window.split("-")[1].split(":")))
            if (local.hour, local.minute) >= end and local.weekday() < 5:
                return True
        return False

    def snapshot(self) -> dict:
        pnl, pct = self.day_pnl()
        return {
            "day": self.state["day"],
            "day_pnl_usd": round(pnl, 2),
            "day_pnl_pct": round(pct * 100, 3),
            "peak_day_pnl_usd": round(self.state["peak_day_pnl"], 2),
            "trades_today": self.state["trades_today"],
            "trades_left_today": self.trades_left(),
            "consecutive_losses_today": self.consecutive_losses(),
            "has_cushion_full_size_allowed": self.has_cushion(),
            "in_trade_window": self.in_window(),
            "new_trades_blocked": self.new_trade_block(),
            "limits": {
                "trade_window": f"{self.r.trade_window} {self.r.trade_window_tz}" if self.r.trade_window else None,
                "max_position_pct_of_equity": self.r.max_position_pct * 100,
                "max_total_exposure_pct": self.r.max_total_exposure_pct * 100,
                "risk_per_trade_pct": self.r.risk_per_trade_pct * 100,
                "starter_size_fraction": self.r.starter_size_fraction,
                "max_daily_loss_pct": self.r.max_daily_loss_pct * 100,
                "max_consecutive_losses": self.r.max_consecutive_losses,
                "giveback_pct_of_peak": self.r.giveback_pct_of_peak * 100,
                "max_stop_distance_pct": self.r.max_stop_distance_pct * 100,
                "auto_scale_out": f"sell {self.r.scale_out_fraction*100:.0f}% at take_profit, "
                                  f"stop to break-even" if self.r.scale_out_fraction else None,
                "breakout_or_bailout_minutes": self.r.breakout_or_bailout_minutes,
            },
        }
