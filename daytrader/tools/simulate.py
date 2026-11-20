"""Monte-Carlo bug hunt: runs the REAL agent code (setup detector, rules entries, risk
manager, guard exits, P&L accounting) through randomized synthetic trading scenarios and
checks invariants after every tick.

  python tools/simulate.py --runs 1000 --seed 1

No network, no API. Prints a summary of outcomes and every invariant violation found.
"""
from __future__ import annotations

import argparse
import math
import random
import sys
import tempfile
import time as _time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trader.broker import PaperBroker  # noqa: E402
from trader.config import Config, RiskConfig, ScannerConfig  # noqa: E402
from trader.main import SetupWatcher, guard  # noqa: E402
from trader.risk import RiskManager  # noqa: E402
from trader.rules import RulesAgent  # noqa: E402
from trader.tools import Journal, Toolbox  # noqa: E402

BIG_LOSSES: list = []
TICK = 15  # seconds between checks (the agent's watch interval)


class Clock:
    def __init__(self, t0: float):
        self.t = t0

    def __call__(self) -> float:
        return self.t


# ---------------------------------------------------------------------------
# Synthetic market
# ---------------------------------------------------------------------------
class SimMarket:
    """1-minute candles built from a 15-second price path, revealed as the clock advances."""

    kind = "stocks"

    def __init__(self, clock: Clock):
        self.clock = clock
        self.paths: dict[str, list[tuple[float, float, float]]] = {}  # sym -> [(t, price, vol)]

    def add(self, sym: str, path):
        self.paths[sym] = path

    def _upto(self, sym):
        return [p for p in self.paths[sym] if p[0] <= self.clock.t]

    def price(self, sym):
        pts = self._upto(sym)
        if not pts:
            raise RuntimeError("no price yet")
        return pts[-1][1]

    def candles(self, sym, tf, limit):
        pts = self._upto(sym)
        out, cur = [], None
        for t, p, v in pts:
            m = int(t // 60 * 60 * 1000)
            if cur is None or cur[0] != m:
                if cur:
                    out.append(cur)
                cur = [m, p, p, p, p, v]
            else:
                cur[2] = max(cur[2], p); cur[3] = min(cur[3], p); cur[4] = p; cur[5] += v
        if cur:
            out.append(cur)
        return out[-limit:]

    def ticker(self, sym):
        return {"last": self.price(sym)}

    def order_book(self, sym, depth=20):
        p = self.price(sym)
        return {"best_bid": p - 0.01, "best_ask": p + 0.01}

    def session_start_ms(self):
        return None

    def news(self, *a, **k):
        return []


SCENARIOS = ["continuation", "stall", "fail", "gap_down", "whipsaw", "spike_dump", "grind_up",
             "heavy_pullback", "halt_up", "chop"]


def make_path(rng: random.Random, t0: float, scenario: str):
    """Base → pole (heavy volume) → light-volume pullback → outcome. 15s points."""
    p = rng.uniform(1.5, 18.0)
    pts, t = [], t0

    def step(n, drift, vol, noise=0.002):
        nonlocal p, t
        for _ in range(n):
            p = max(0.05, p * (1 + drift + rng.gauss(0, noise)))
            pts.append((t, round(p, 4), vol * rng.uniform(0.7, 1.3)))
            t += TICK

    step(4 * 35, 0.0, 500, 0.0008)                               # quiet base (35 min)
    step(4 * rng.randint(6, 12), rng.uniform(0.003, 0.009), 9000)  # pole: +1-4%/min, heavy vol
    pb_vol = 6000 if scenario == "heavy_pullback" else 1200
    step(4 * rng.randint(2, 4), -rng.uniform(0.0015, 0.004), pb_vol, 0.001)  # pullback
    if scenario == "continuation":
        step(4 * 20, rng.uniform(0.002, 0.006), 7000)
    elif scenario == "grind_up":
        step(4 * 40, rng.uniform(0.0005, 0.0015), 3000, 0.001)
    elif scenario == "stall":
        step(4 * 2, 0.002, 4000); step(4 * 25, 0.0, 1500, 0.0006)
    elif scenario == "fail":
        step(4 * 1, 0.002, 4000); step(4 * 15, -rng.uniform(0.002, 0.005), 5000)
    elif scenario == "gap_down":
        step(4 * 1, 0.002, 4000)
        p *= rng.uniform(0.70, 0.88)                              # halt / gap straight through the stop
        step(4 * 15, -0.001, 8000)
    elif scenario == "whipsaw":
        step(4 * 3, 0.003, 5000); step(4 * 3, -0.004, 6000); step(4 * 3, 0.003, 5000); step(4 * 10, -0.003, 6000)
    elif scenario == "spike_dump":
        step(4 * 5, 0.008, 9000); step(4 * 10, -0.01, 12000)
    elif scenario == "halt_up":
        step(4 * 1, 0.002, 4000); p *= rng.uniform(1.10, 1.30); step(4 * 15, 0.0, 6000, 0.003)
    elif scenario == "heavy_pullback":
        step(4 * 20, rng.uniform(-0.002, 0.004), 4000)
    elif scenario == "chop":
        for _ in range(8):
            step(4 * 2, rng.choice([0.004, -0.004]), 4000)
    return pts


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------
class Checker:
    def __init__(self, tb: Toolbox, start_equity: float):
        self.tb = tb
        self.start = start_equity
        self.violations: list[str] = []
        self.last_stops: dict[str, float] = {}
        self.max_seen_entries = Counter()

    def fail(self, msg):
        self.violations.append(msg)

    def tick(self, clock_t):
        b, r = self.tb.broker, self.tb.risk
        for sym in list(self.last_stops):          # a new position on the same symbol starts fresh
            if sym not in b.positions:
                del self.last_stops[sym]
        eq = b.equity()
        if eq <= 0 or math.isnan(eq):
            self.fail(f"equity invalid {eq}")
        if b.cash() < -1e-6:
            self.fail(f"negative cash {b.cash():.2f}")
        for sym, p in b.positions.items():
            if p.qty <= 0:
                self.fail(f"{sym} non-positive qty {p.qty}")
            prev = self.last_stops.get(sym)
            if prev is not None and p.stop_loss is not None and p.stop_loss < prev - 1e-9:
                self.fail(f"{sym} stop LOWERED {prev} -> {p.stop_loss}")
            if p.stop_loss is not None:
                self.last_stops[sym] = p.stop_loss
            value = p.qty * b.market.price(sym)
            if value > r.r.max_position_pct * eq * 1.6 + 1:  # price can run up after entry
                self.fail(f"{sym} position ${value:,.0f} way over cap ({r.r.max_position_pct*eq:,.0f})")
            if p.scaled_out and p.stop_loss is not None and p.stop_loss < p.entry_price - 1e-9:
                self.fail(f"{sym} scaled out but stop {p.stop_loss} below entry {p.entry_price}")
        if b.exposure() > r.r.max_total_exposure_pct * eq * 1.6 + 1:
            self.fail(f"total exposure ${b.exposure():,.0f} over cap")
        # accounting: equity change == realized + unrealized
        realized = sum(t["pnl_usd"] for t in b.realized)
        unreal = sum(p.qty * b.market.price(s) - p.cost_usd for s, p in b.positions.items())
        if abs((eq - self.start) - (realized + unreal)) > 0.05:
            self.fail(f"accounting mismatch: equity Δ {eq-self.start:.2f} vs realized+unrealized "
                      f"{realized+unreal:.2f}")

    def trade_closed(self, rec, entry_ev):
        """Loss per trade must respect risk-per-trade unless the price gapped through the stop."""
        if rec.get("partial"):
            return
        total = rec.get("trade_total_pnl_usd", rec["pnl_usd"])
        budget = self.tb.risk.r.risk_per_trade_pct * self.start
        gap = "gap" in (rec.get("_scenario") or "")
        if total < -budget * 1.35 and not gap:
            self.fail(f"loss {total:.2f} exceeded 1% risk budget {budget:.2f} "
                      f"(reason: {rec['reason']}, scenario {rec.get('_scenario')})")


# ---------------------------------------------------------------------------
# One simulated trading session
# ---------------------------------------------------------------------------
def run_session(rng: random.Random, n_symbols: int, starter_fraction: float):
    tmp = Path(tempfile.mkdtemp(prefix="sim_"))
    today = datetime.now(timezone.utc).replace(hour=13, minute=0, second=0, microsecond=0)
    clock = Clock(today.timestamp())
    _time.time = clock  # every module calls time.time(); drive them all from the sim clock

    cfg = Config(market="stocks", symbols=[], state_dir=tmp, decision_mode="rules",
                 scanner=ScannerConfig(price_min=1, price_max=20),
                 risk=RiskConfig(trade_window=None, starter_size_fraction=starter_fraction,
                                 max_position_pct=0.25, max_total_exposure_pct=0.5,
                                 risk_per_trade_pct=0.01, max_daily_loss_pct=0.02,
                                 max_trades_per_day=6, max_stop_distance_pct=0.10,
                                 breakout_or_bailout_minutes=1.5, bailout_min_move=0.10,
                                 exit_on_new_low_candle=True, min_order_usd=50),
                 paper_fee_rate=0.0, paper_slippage=0.0)
    market = SimMarket(clock)
    syms, scen = [], {}
    t_start = clock.t
    for i in range(n_symbols):
        sym = f"S{i}{rng.randint(100, 999)}"
        sc = rng.choice(SCENARIOS)
        offset = i * rng.randint(8, 25) * 60  # stagger setups through the morning
        market.add(sym, make_path(rng, t_start + offset, sc))
        syms.append(sym); scen[sym] = sc
    broker = PaperBroker(market, tmp / "acct.json", 10_000, 0.0, 0.0)
    journal = Journal(tmp / "j.jsonl")
    risk = RiskManager(cfg, broker)
    tb = Toolbox(cfg, broker, risk, journal)
    tb.scanner.last = [{"symbol": s, "passes": True, "change_pct": 30, "pillars": {"float": True},
                        "size_factor": 1.0, "day_volume": 5e6} for s in syms]
    tb.watchlist = list(syms)
    agent = RulesAgent(tb)
    watcher = SetupWatcher(tb, cooldown_s=60)
    chk = Checker(tb, broker.equity())
    end_t = max(p[-1][0] for p in market.paths.values())
    risk.flatten_due = lambda now=None: clock.t >= end_t  # "11:00": everything must be flat
    events = Counter()
    entries_after_halt = 0
    while clock.t <= end_t + TICK:
        halted_before = risk.halted()
        try:
            alert = watcher.check()
            if alert:
                n_open = len(broker.realized), len(broker.positions)
                agent.run_cycle(alert)
                if halted_before and len(broker.positions) > n_open[1]:
                    entries_after_halt += 1
            n_closed = len(broker.realized)
            guard(broker, risk, journal, check_candles=True)
            for rec in broker.realized[n_closed:]:
                rec["_scenario"] = scen.get(rec["symbol"], "") + (" gap" if scen.get(rec["symbol"]) in
                                                                   ("gap_down", "spike_dump") else "")
                chk.trade_closed(rec, None)
            chk.tick(clock.t)
        except Exception:
            chk.fail("EXCEPTION:\n" + traceback.format_exc())
            break
        clock.t += TICK
    if broker.positions:
        chk.fail(f"positions left open after flatten: {list(broker.positions)}")
    if entries_after_halt:
        chk.fail(f"{entries_after_halt} entries after the day was halted")
    opens = Counter(e["symbol"] for e in journal.tail(10_000, {"open"}))
    for s, n in opens.items():
        if n > 2:
            chk.fail(f"{s} entered {n} times (max 2)")
    if risk.state["trades_today"] > cfg.risk.max_trades_per_day:
        chk.fail(f"{risk.state['trades_today']} trades > max {cfg.risk.max_trades_per_day}")
    # consecutive-loss rule: never a 4th consecutive losing trade
    streak, worst = 0, 0
    for t in broker.completed_trades():
        streak = streak + 1 if t.get("trade_total_pnl_usd", t["pnl_usd"]) < 0 else 0
        worst = max(worst, streak)
    if worst > cfg.risk.max_consecutive_losses:
        chk.fail(f"{worst} losses in a row (limit {cfg.risk.max_consecutive_losses})")
    for t in broker.completed_trades():
        reason = t["reason"].split(":")[1].strip().split(" (")[0] if ":" in t["reason"] else t["reason"]
        events[reason[:40]] += 1
    pnl = broker.equity() - 10_000
    if pnl < -0.025 * 10_000:  # worse than the 2% daily limit (+ slack): explain it
        lines = [f"{t['symbol']}[{scen.get(t['symbol'])}] {t.get('trade_total_pnl_usd', t['pnl_usd']):+.2f} "
                 f"entry {t['entry_price']:.3f} exit {t['exit_price']:.3f} :: {t['reason'][:70]}"
                 for t in broker.completed_trades()]
        BIG_LOSSES.append((pnl, lines))
    return {"violations": chk.violations, "trades": len(broker.completed_trades()), "pnl": pnl,
            "exits": events, "scenarios": Counter(scen.values()), "halt": risk.state.get("halted_reason")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    real_time = _time.time
    totals, exits, viol, trades, pnls, halts = Counter(), Counter(), [], 0, [], Counter()
    for i in range(a.runs):
        n = 1 if i % 2 == 0 else rng.randint(2, 6)        # half single trades, half full days
        starter = rng.choice([0.25, 1.0])
        res = run_session(rng, n, starter)
        trades += res["trades"]; pnls.append(res["pnl"]); exits.update(res["exits"])
        totals.update(res["scenarios"])
        if res["halt"]:
            halts[res["halt"].split(".")[0][:50]] += 1
        for v in res["violations"]:
            viol.append((i, v))
    _time.time = real_time
    print(f"Sessions: {a.runs}   symbols simulated: {sum(totals.values())}   trades: {trades}")
    print("Scenarios:", dict(totals))
    print("Exit reasons:", dict(exits.most_common()))
    print("Day halts:", dict(halts))
    wins = sum(1 for p in pnls if p > 0); losses = sum(1 for p in pnls if p < 0)
    print(f"Session P&L: {wins} green / {losses} red / {a.runs-wins-losses} flat; "
          f"worst ${min(pnls):,.2f}, best ${max(pnls):,.2f}")
    print(f"\nINVARIANT VIOLATIONS: {len(viol)}")
    kinds = Counter(v.split('\n')[0].split(' ')[0] if v.startswith('EXCEPTION') else
                    ' '.join(v.split()[1:4]) for _, v in viol)
    for k, n in kinds.most_common(15):
        print(f"  {n:5d} × {k}")
    print(f"\nDays worse than -2.5%: {len(BIG_LOSSES)}")
    for pnl, lines in sorted(BIG_LOSSES)[:6]:
        print(f"  day {pnl:+.2f}:"); [print("     ", l) for l in lines]
    for i, v in viol[:12]:
        print(f"\n--- session {i}: {v[:1500]}")
    return 1 if viol else 0


if __name__ == "__main__":
    sys.exit(main())
