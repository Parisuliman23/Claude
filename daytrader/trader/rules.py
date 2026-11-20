"""Rules-only mode: trades Ross Cameron's rules mechanically, no Claude / no API cost.

Scan → watch the top passing gainers → buy the first candle to make a new high after a
pullback (setup detector) → stop at the pullback low, target the high → the guard handles
every exit (stop, breakout-or-bailout, first new-low candle, half at target + break-even,
end of window). The risk manager sizes and can veto every order, same as in Claude mode.
"""
from __future__ import annotations

import logging

from .tools import Toolbox

log = logging.getLogger("trader.rules")


class RulesTrader:
    def __init__(self, toolbox: Toolbox, watch_top: int = 3, max_entries_per_symbol: int = 2):
        self.tb = toolbox
        self.watch_top = watch_top  # Ross: biggest winners come from the top 3-4 gainers
        # Ross: "I like buying the first pullback and… the second pullback… after the second
        # pullback I start to get a little more cautious"
        self.max_entries_per_symbol = max_entries_per_symbol

    def _entries_today(self, symbol: str) -> int:
        day = self.tb.risk.state.get("day") or ""
        return sum(1 for r in self.tb.journal.tail(500, {"open"})
                   if r.get("symbol") == symbol and r["ts"][:10] >= day[:10])

    def scan_cycle(self) -> str:
        """Scheduled cycle: rescan and pick the watchlist."""
        tb = self.tb
        res = tb.t_scan_momentum()
        passing = [c for c in res["candidates"] if c["passes"]]
        # Prefer names without an open question on float; keep % gain order (the leader first)
        passing.sort(key=lambda c: (c["pillars"].get("float") is None, -c["change_pct"]))
        picks = [c["symbol"] for c in passing[: self.watch_top]]
        tb.watchlist = picks
        tb.journal.log("watchlist", symbols=picks, mode="rules")
        summary = (f"rules: market {res['market_temperature']}, {len(passing)} passing, "
                   f"watching {', '.join(picks) or 'nothing'}")
        tb.journal.log("cycle_summary", summary=summary)
        return summary

    def on_setup(self, alert: dict) -> dict:
        """A watched stock triggered: buy it if the rules and risk manager agree."""
        tb = self.tb
        sym, st = alert["symbol"], alert["setup"]
        if st.get("state") != "triggered" or st.get("problems"):
            return {"status": "skipped", "reason": "setup not clean"}
        if self._entries_today(sym) >= self.max_entries_per_symbol:
            return {"status": "skipped",
                    "reason": f"already traded {sym} {self.max_entries_per_symbol}x today (first/second pullback only)"}
        stop = st["stop"]
        # Target: back to the high (Ross), at least 2R (the detector already requires 2:1 room)
        target = max(st.get("swing_high") or 0, st.get("target_2r") or 0)
        equity = tb.broker.equity()
        want = equity * tb.cfg.risk.max_position_pct  # ask for full size; risk rules shrink it
        reason = (f"rules: first pullback, new-high candle over {st['entry_trigger']}, "
                  f"stop {stop} (pullback low), target {target}; pole +{st.get('pole_gain_pct')}%, "
                  f"pullback vol {st.get('pullback_vol_vs_pole')}x pole")
        r = tb.t_open_long(sym, want, stop_loss=stop, take_profit=target, reason=reason)
        log.info("RULES ENTRY %s -> %s", sym, r.get("status"), )
        return r


class RulesAgent:
    """Drop-in for TradingAgent: same run_cycle(alert) interface, no Claude."""

    def __init__(self, toolbox: Toolbox):
        self.trader = RulesTrader(toolbox)
        self.journal = toolbox.journal

    def run_cycle(self, alert: dict | None = None) -> str:
        if alert:
            r = self.trader.on_setup(alert)
            return f"rules: setup on {alert['symbol']} -> {r.get('status')} {r.get('reason', '')}".strip()
        return self.trader.scan_cycle()
