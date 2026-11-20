"""Offline tests: fake exchange + scripted fake Claude client. No network, no API cost."""
from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from trader.agent import TradingAgent
from trader.broker import PaperBroker
from trader.config import Config, RiskConfig
from trader.indicators import rsi, summarize
from trader.main import guard
from trader.market import MarketData
from trader.risk import RiskManager
from trader.tools import Journal, Toolbox


class FakeExchange:
    has = {}

    def __init__(self):
        self.prices = {"BTC/USD": 50_000.0, "ETH/USD": 3_000.0}

    def load_markets(self):
        pass

    def fetch_ticker(self, s):
        p = self.prices[s]
        return {"last": p, "bid": p - 1, "ask": p + 1, "percentage": 1.2, "high": p * 1.02,
                "low": p * 0.98, "quoteVolume": 1e9}

    def fetch_ohlcv(self, s, timeframe, limit):
        base = self.prices[s]
        out = []
        for i in range(limit):
            c = base * (1 + 0.01 * math.sin(i / 5))
            out.append([i * 60_000, c * 0.999, c * 1.002, c * 0.998, c, 100 + i])
        return out

    def fetch_order_book(self, s, limit):
        p = self.prices[s]
        return {"bids": [[p - 1, 2]] * 5, "asks": [[p + 1, 1]] * 5}


@pytest.fixture
def setup(tmp_path: Path):
    risk_cfg = RiskConfig(starter_size_fraction=1.0, max_position_pct=0.20, max_stop_distance_pct=0.08,
                          breakout_or_bailout_minutes=None, giveback_pct_of_peak=0)
    cfg = Config(symbols=["BTC/USD", "ETH/USD"], state_dir=tmp_path, risk=risk_cfg,
                 paper_starting_cash=10_000, paper_fee_rate=0.006, paper_slippage=0.0)
    ex = FakeExchange()
    market = MarketData(ex, cache_seconds=0)
    broker = PaperBroker(market, tmp_path / "paper.json", 10_000, 0.006, 0.0)
    journal = Journal(tmp_path / "j.jsonl")
    risk = RiskManager(cfg, broker)
    return cfg, ex, broker, risk, journal, Toolbox(cfg, broker, risk, journal)


def test_indicators():
    assert rsi([float(i) for i in range(1, 40)]) == 100.0
    s = summarize(FakeExchange().fetch_ohlcv("BTC/USD", "1h", 100))
    assert s["ema_50"] and s["atr_14"] and len(s["recent_candles_ohlcv"]) == 12


def test_requires_stop_and_rejects_bad_symbol(setup):
    *_, tb = setup
    r = tb.t_open_long("BTC/USD", 1000, stop_loss=None, reason="x")
    assert r["status"] == "rejected" and "stop_loss" in r["reason"]
    with pytest.raises(Exception):
        tb.t_open_long("DOGE/USD", 100, stop_loss=0.1, reason="x")


def test_size_capped_by_risk_per_trade(setup):
    cfg, ex, broker, risk, journal, tb = setup
    # 2% stop distance -> max size = 1% * 10k / (0.02+0.01) = ~3333, but position cap 20% = 2000
    r = tb.t_open_long("BTC/USD", 9000, stop_loss=49_000, reason="test")
    assert r["status"] == "filled"
    assert 1990 < r["spent_usd"] <= 2012
    assert r["size_adjustments"]
    # second buy of same symbol rejected
    assert tb.t_open_long("BTC/USD", 100, stop_loss=49_000, reason="x")["status"] == "rejected"


def test_stop_only_tightens_and_guard_closes(setup):
    cfg, ex, broker, risk, journal, tb = setup
    tb.t_open_long("ETH/USD", 1000, stop_loss=2_900, take_profit=3_300, reason="t")
    assert tb.t_update_stops("ETH/USD", "x", stop_loss=2_800)["status"] == "rejected"
    assert tb.t_update_stops("ETH/USD", "x", stop_loss=2_950)["status"] == "updated"
    ex.prices["ETH/USD"] = 2_940.0
    guard(broker, risk, journal)
    assert "ETH/USD" not in broker.positions
    assert broker.realized[-1]["reason"].startswith("auto: stop hit")
    assert broker.realized[-1]["pnl_usd"] < 0


def test_daily_loss_halts_trading(setup):
    cfg, ex, broker, risk, journal, tb = setup
    tb.t_open_long("BTC/USD", 2000, stop_loss=47_000, reason="t")
    ex.prices["BTC/USD"] = 30_000.0  # crash past stop: big loss
    guard(broker, risk, journal)
    assert risk.halted() and "Daily loss" in risk.halted()
    r = tb.t_open_long("ETH/USD", 100, stop_loss=2_900, reason="t")
    assert r["status"] == "rejected" and "Daily loss" in r["reason"]


def test_kill_switch(setup):
    cfg, ex, broker, risk, journal, tb = setup
    (cfg.state_dir / "KILL").write_text("")
    assert tb.t_open_long("BTC/USD", 100, stop_loss=49_000, reason="t")["status"] == "rejected"


class FakeClient:
    """Scripted Claude: get_account, then open_long, then a final summary."""

    def __init__(self):
        self.calls = []
        script = [
            [NS(type="tool_use", id="t1", name="get_account", input={}),
             NS(type="tool_use", id="t2", name="get_market_data",
                input={"symbol": "BTC/USD", "timeframe": "1h"})],
            [NS(type="tool_use", id="t3", name="open_long",
                input={"symbol": "BTC/USD", "usd_amount": 500, "stop_loss": 48_500,
                       "take_profit": 54_000, "reason": "trend up"})],
            [NS(type="text", text="Bought BTC on 1h uptrend. Watching 52k.")],
        ]
        self.script = iter(script)
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        content = next(self.script)
        stop = "tool_use" if any(b.type == "tool_use" for b in content) else "end_turn"
        return NS(content=content, stop_reason=stop, stop_details=None,
                  usage=NS(input_tokens=100, output_tokens=50, cache_read_input_tokens=0))


def test_agent_cycle_end_to_end(setup):
    cfg, ex, broker, risk, journal, tb = setup
    client = FakeClient()
    agent = TradingAgent(cfg, tb, journal, client=client)
    summary = agent.run_cycle()
    assert "Bought BTC" in summary
    assert "BTC/USD" in broker.positions
    assert len(client.calls) == 3
    # tool results for parallel calls are returned together in one user message
    msgs = client.calls[-1]["messages"]  # same list, final state
    assert msgs[2]["role"] == "user" and len(msgs[2]["content"]) == 2
    assert client.calls[0]["model"] == "claude-opus-5-5"
    events = [r["event"] for r in journal.tail(50)]
    assert "open" in events and "cycle_summary" in events


# ---------------------------------------------------------------------------
# Ross Cameron strategy pieces
# ---------------------------------------------------------------------------
from trader.indicators import analyze_setup
from trader.main import SetupWatcher
from trader.scanner import Scanner
from trader.config import ScannerConfig


def bull_flag(trigger_now: bool = True):
    """Flat base, strong pole on heavy volume, 3-candle light-volume pullback."""
    c, t = [], 0
    p = 5.00
    for _ in range(40):  # base
        c.append([t, p, p + 0.02, p - 0.02, p + 0.005, 1000]); t += 60_000
    for _ in range(8):   # pole: +~0.15/candle, heavy volume
        c.append([t, p, p + 0.17, p - 0.01, p + 0.15, 20000]); p += 0.15; t += 60_000
    # pullback: red candles on light volume, last one with a bottoming tail
    for o, h, l, cl in ([6.20, 6.21, 6.08, 6.10], [6.10, 6.11, 5.98, 6.00], [6.00, 6.01, 5.92, 5.98]):
        c.append([t, o, h, l, cl, 4000]); t += 60_000
    return c


def test_analyze_setup_detects_first_pullback():
    candles = bull_flag()
    trigger = candles[-1][2]
    st = analyze_setup(candles, live_price=trigger + 0.02, vwap_value=5.3)
    assert st["state"] == "triggered", st
    assert st["stop"] == min(x[3] for x in candles[-3:])
    assert st["pullback_vol_vs_pole"] < 1
    assert st["target_2r"] > st["entry_trigger"]
    assert st["room_to_swing_high_r"] >= 2
    # a shallow setup with less than 2:1 room back to the high is refused
    shallow = analyze_setup(candles, live_price=candles[-1][2] + 0.01, vwap_value=5.3, min_room_r=3.0)
    assert any("room" in p for p in shallow["problems"])
    # below the trigger it is only forming
    assert analyze_setup(candles, live_price=trigger - 0.05, vwap_value=5.3)["state"] == "setup_forming"
    # below VWAP: rejected
    st2 = analyze_setup(candles, live_price=trigger + 0.02, vwap_value=9.0)
    assert st2["state"] == "no_setup" and any("VWAP" in p for p in st2["problems"])


def test_starter_size_until_cushion(setup):
    cfg, ex, broker, risk, journal, tb = setup
    cfg.risk.starter_size_fraction = 0.25
    r = tb.t_open_long("BTC/USD", 9000, stop_loss=49_000, reason="t")
    assert r["status"] == "filled"
    assert r["spent_usd"] <= 0.25 * 0.20 * 10_000 * 1.01
    assert any("starter size" in n for n in r["size_adjustments"])


def test_three_losers_in_a_row_stops_trading(setup):
    cfg, ex, broker, risk, journal, tb = setup
    for _ in range(3):
        tb.t_open_long("ETH/USD", 500, stop_loss=2_900, reason="t")
        ex.prices["ETH/USD"] = 2_990.0
        tb.t_close_position("ETH/USD", "test loss")
        ex.prices["ETH/USD"] = 3_000.0
    r = tb.t_open_long("ETH/USD", 500, stop_loss=2_900, reason="t")
    assert r["status"] == "rejected" and "in a row" in r["reason"]


def test_giveback_half_of_peak_stops_trading(setup):
    cfg, ex, broker, risk, journal, tb = setup
    cfg.risk.giveback_pct_of_peak = 0.5
    tb.t_open_long("BTC/USD", 2000, stop_loss=47_000, reason="t")
    ex.prices["BTC/USD"] = 60_000.0
    risk.update_peak()                      # peak ~ +$370
    ex.prices["BTC/USD"] = 51_000.0         # most of it given back
    assert "peak profit" in (risk.halted() or "")


def test_trade_window(setup):
    from datetime import datetime, timezone
    cfg, *_ , risk, journal, tb = setup
    cfg.risk.trade_window = "07:00-11:00"
    # 2026-11-18 is a Wednesday; 13:00 UTC = 08:00 ET, 17:00 UTC = 12:00 ET
    assert risk.in_window(datetime(2026, 11, 18, 13, 0, tzinfo=timezone.utc))
    assert not risk.in_window(datetime(2026, 11, 18, 17, 0, tzinfo=timezone.utc))


def test_guard_scales_out_half_and_moves_stop_to_breakeven(setup):
    cfg, ex, broker, risk, journal, tb = setup
    tb.t_open_long("ETH/USD", 1000, stop_loss=2_900, take_profit=3_200, reason="t")
    qty0 = broker.positions["ETH/USD"].qty
    ex.prices["ETH/USD"] = 3_210.0
    guard(broker, risk, journal)
    p = broker.positions["ETH/USD"]
    assert p.scaled_out and abs(p.qty - qty0 / 2) < 1e-9
    assert p.stop_loss == p.entry_price and p.take_profit is None
    ex.prices["ETH/USD"] = 2_990.0          # back to break-even stop: rest closes
    guard(broker, risk, journal)
    assert "ETH/USD" not in broker.positions
    final = broker.completed_trades()[-1]
    assert final["trade_total_pnl_usd"] > 0   # half banked at target, rest ~flat


def test_breakout_or_bailout(setup):
    cfg, ex, broker, risk, journal, tb = setup
    cfg.risk.breakout_or_bailout_minutes = 5
    tb.t_open_long("ETH/USD", 1000, stop_loss=2_900, reason="t")
    broker.positions["ETH/USD"].opened_at -= 6 * 60
    ex.prices["ETH/USD"] = 2_995.0
    guard(broker, risk, journal)
    assert "ETH/USD" not in broker.positions
    assert "bailout" in broker.realized[-1]["reason"]


class FakeStockMarket:
    """Minimal stand-in for AlpacaMarket."""
    kind = "stocks"

    def __init__(self):
        self.floats = type("F", (), {"get": lambda self, s: {"WISA": 3e6, "BIG": 90e6}.get(s)})()
        self.data = {
            "WISA": dict(price=9.59, chg=45.0, vol=12e6, avg=1e6, news=[{"time": None, "headline": "FDA approval"}]),
            "BIG": dict(price=8.0, chg=30.0, vol=50e6, avg=5e6, news=[{"time": None, "headline": "Earnings"}]),
            "NONEWS": dict(price=4.0, chg=25.0, vol=9e6, avg=1e6, news=[]),
            "PRICEY": dict(price=55.0, chg=20.0, vol=9e6, avg=1e6, news=[{"headline": "x"}]),
            "SLOW": dict(price=6.0, chg=12.0, vol=2e6, avg=1e6, news=[{"headline": "x"}]),
            "THIRTEEND": dict(price=4.45, chg=48.0, vol=8e6, avg=0.5e6,
                              news=[{"headline": "Schedule 13D: investor reports acquisition of 2.69 million shares"}]),
            "BUYOUT": dict(price=7.9, chg=60.0, vol=20e6, avg=1e6,
                           news=[{"headline": "XYZ to be acquired by MegaCorp for $8.00 per share"}]),
        }

    def top_gainers(self, top):
        return [{"symbol": s, "percent_change": d["chg"], "price": d["price"]} for s, d in self.data.items()]

    def ticker(self, s):
        return {"last": self.data[s]["price"], "day_volume": self.data[s]["vol"]}

    def avg_daily_volume(self, s):
        return self.data[s]["avg"]

    def news(self, s, limit, hours):
        return self.data[s]["news"]

    def asset(self, s):
        return {"exchange": "NASDAQ", "tradable": True}


def test_scanner_five_pillars(tmp_path):
    cfg = Config(market="stocks", stocks_data_feed="sip", symbols=[], state_dir=tmp_path, scanner=ScannerConfig())
    sc = Scanner(cfg, FakeStockMarket())
    res = {c["symbol"]: c for c in sc.scan()}
    assert res["WISA"]["passes"] and res["WISA"]["float_rotation_x"] == 4.0
    assert not res["BIG"]["passes"] and "float" in res["BIG"]["failed_pillars"]
    # Ross: catalyst preferred, not required -> passes at half size, flagged
    assert res["NONEWS"]["passes"] and res["NONEWS"]["size_factor"] == 0.5
    assert any("no news" in f for f in res["NONEWS"]["flags"])
    assert not res["BUYOUT"]["passes"] and "not_buyout_or_merger" in res["BUYOUT"]["failed_pillars"]
    assert not res["SLOW"]["passes"] and "relative_volume" in res["SLOW"]["failed_pillars"]
    assert "PRICEY" not in res                      # filtered out by price band
    assert res["THIRTEEND"]["passes"]                # 13D stake = catalyst, not a buyout
    assert sc.approved_symbols() == {"WISA", "NONEWS", "THIRTEEND"}
    assert list(res)[0] == "THIRTEEND"               # passing names rank first, by % gain (leader = #1)


def test_watcher_wakes_on_trigger(setup):
    cfg, ex, broker, risk, journal, tb = setup
    candles = bull_flag()
    trig = candles[-1][2]
    ex.prices["BTC/USD"] = trig + 0.02
    ex.fetch_ohlcv = lambda s, timeframe, limit: [list(c) for c in candles]
    tb.market.session_start_ms = lambda: None
    tb.watchlist = ["BTC/USD"]
    alert = SetupWatcher(tb).check()
    assert alert and alert["symbol"] == "BTC/USD" and alert["setup"]["state"] == "triggered"


def test_exit_on_first_candle_making_new_low(setup):
    import time as _t
    cfg, ex, broker, risk, journal, tb = setup
    cfg.risk.exit_on_new_low_candle = True
    tb.t_open_long("ETH/USD", 1000, stop_loss=2_900, reason="t")
    t0 = int(broker.positions["ETH/USD"].opened_at * 1000) // 60_000 * 60_000
    rows = [[t0 - 60_000, 2990, 3005, 2985, 3000, 10],   # entry candle
            [t0, 3000, 3010, 2995, 3008, 10],             # higher low: hold
            [t0 + 60_000, 3008, 3009, 2990, 2992, 10]]    # breaks prior low: exit
    ex.fetch_ohlcv = lambda s, timeframe, limit: rows
    import trader.tools as tools_mod
    real = tools_mod.time.time
    tools_mod.time.time = lambda: (t0 + 3 * 60_000) / 1000
    try:
        guard(broker, risk, journal)
    finally:
        tools_mod.time.time = real
    assert "ETH/USD" not in broker.positions
    assert "new low" in broker.realized[-1]["reason"]


def test_scanner_uses_sec_shares_outstanding_when_float_missing(tmp_path):
    m = FakeStockMarket()
    sec = {"WISA": 3e6, "BIG": 90e6, "NONEWS": 30e6}
    m.floats = type("F", (), {"info": lambda self, s: {"float": None, "outstanding": sec.get(s)}})()
    cfg = Config(market="stocks", stocks_data_feed="sip", symbols=[], state_dir=tmp_path, scanner=ScannerConfig())
    res = {c["symbol"]: c for c in Scanner(cfg, m).scan()}
    assert res["WISA"]["pillars"]["float"] is True          # 3M outstanding -> float < 20M
    assert res["BIG"]["pillars"]["float"] is False          # 90M outstanding -> too big
    assert res["NONEWS"]["pillars"]["float"] is None        # 30M: near the line, flagged not blocked
    assert any("check it" in f for f in res["NONEWS"]["flags"])


class FakeNotifier:
    enabled = True

    def __init__(self, cmds):
        self.cmds, self.sent = list(cmds), []

    def poll_commands(self):
        out, self.cmds = self.cmds, []
        return out

    def send(self, title, message, priority="default", tags=""):
        self.sent.append((title, message))


def test_phone_commands_stop_resume_flatten_status(setup):
    from trader.main import handle_commands
    cfg, ex, broker, risk, journal, tb = setup
    tb.t_open_long("ETH/USD", 500, stop_loss=2_900, reason="t")
    n = FakeNotifier(["status", "stop"])
    handle_commands(n, broker, risk, journal, tb)
    assert n.sent[0][0].startswith("Equity") and "ETH/USD" in n.sent[0][1]
    assert risk.kill_file.exists()
    assert tb.t_open_long("BTC/USD", 500, stop_loss=49_000, reason="t")["status"] == "rejected"
    n.cmds = ["resume"]; handle_commands(n, broker, risk, journal, tb)
    assert not risk.kill_file.exists()
    n.cmds = ["flatten"]; handle_commands(n, broker, risk, journal, tb)
    assert not broker.positions and risk.kill_file.exists()


def test_trade_events_become_phone_alerts(tmp_path):
    n = FakeNotifier([])
    j = Journal(tmp_path / "j.jsonl", notifier=n)
    j.log("open", symbol="WISA", price=9.59, usd=2400, qty=250, stop=9.39, tp=9.99, reason="pullback")
    j.log("close", symbol="WISA", exit_price=9.99, pnl_usd=100.0, trade_total_pnl_usd=100.0, reason="target")
    j.log("cycle_start")  # not alert-worthy
    assert [t for t, _ in n.sent] == ["BUY WISA @ 9.59", "SOLD WISA @ 9.99  +$100.00"]


def test_rules_mode_scans_watches_and_enters(setup):
    from trader.rules import RulesAgent
    cfg, ex, broker, risk, journal, tb = setup
    agent = RulesAgent(tb)
    # scan: crypto allowlist mode; both symbols pass price/gain? give them a +12% day
    ex.fetch_ticker = lambda s: {"last": ex.prices[s], "percentage": 12.0, "quoteVolume": 5e9,
                                 "bid": ex.prices[s] - 1, "ask": ex.prices[s] + 1}
    tb.scanner.last = [{"symbol": "BTC/USD", "passes": True, "change_pct": 12.0,
                        "pillars": {"float": None}, "size_factor": 1.0}]
    tb.scanner.scan = lambda: tb.scanner.last
    tb.scanner.market_temperature = "normal"
    assert "watching BTC/USD" in agent.run_cycle()
    assert tb.watchlist == ["BTC/USD"]
    # a triggered setup -> rules buy with stop at the pullback low and target >= 2R
    st = {"state": "triggered", "problems": [], "stop": 49_000.0, "entry_trigger": 49_900.0,
          "swing_high": 52_500.0, "target_2r": 51_700.0, "pole_gain_pct": 8, "pullback_vol_vs_pole": 0.4}
    msg = agent.run_cycle({"symbol": "BTC/USD", "setup": st})
    assert "filled" in msg
    p = broker.positions["BTC/USD"]
    assert p.stop_loss == 49_000.0 and p.take_profit == 52_500.0
    # third entry on the same symbol in a day is refused (first/second pullback only)
    broker.close("BTC/USD", "t")
    agent.run_cycle({"symbol": "BTC/USD", "setup": st}); broker.close("BTC/USD", "t")
    assert "first/second pullback" in agent.run_cycle({"symbol": "BTC/USD", "setup": st})


def test_rules_mode_does_not_need_anthropic_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from trader.config import load_config
    cfg = load_config()
    assert cfg.decision_mode == "rules"


def test_account_size_makes_100k_paper_behave_like_10k(tmp_path):
    from trader.alpaca import AlpacaBroker

    class FakeClient:
        def __init__(self):
            self.eq, self.cash = 100_000.0, 100_000.0

        def trade(self, path, **kw):
            assert path == "/v2/account"
            return {"equity": str(self.eq), "cash": str(self.cash)}

    class FakeMkt:
        def __init__(self, c):
            self.client = c

    c = FakeClient()
    b = AlpacaBroker(FakeMkt(c), tmp_path / "s.json", account_size=10_000)
    assert b.equity() == 10_000 and b.cash() == 10_000
    c.eq += 450                                   # agent made $450 on the real account
    assert b.equity() == 10_450
    b2 = AlpacaBroker(FakeMkt(c), tmp_path / "s.json", account_size=10_000)  # restart keeps baseline
    assert b2.equity() == 10_450
    b3 = AlpacaBroker(FakeMkt(c), tmp_path / "x.json", account_size=None)
    assert b3.equity() == 100_450                 # no override = real balance


def test_monte_carlo_sessions_hold_all_invariants():
    """Quick version of tools/simulate.py: 60 randomized sessions through the real agent code."""
    import random, sys, time as _t
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import simulate as S
    real = _t.time
    try:
        rng = random.Random(42)
        problems = []
        for i in range(60):
            res = S.run_session(rng, 1 if i % 2 == 0 else rng.randint(2, 5), rng.choice([0.25, 1.0]))
            problems += res["violations"]
    finally:
        _t.time = real
    assert problems == [], problems[:5]


def test_halt_protection_exits_and_entry_blocks():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from trader.halts import entry_block, exit_signal, luld_bands, luld_pct
    from trader.broker import Position
    ET_ = ZoneInfo("America/New_York")
    assert luld_pct(5) == 0.10 and luld_pct(2) == 0.20
    c = [[0, 5, 5.1, 4.9, 5, 100]] * 5
    assert luld_bands(c, datetime(2026, 11, 18, 8, 0, tzinfo=ET_)) is None          # premarket: no bands
    b = luld_bands(c, datetime(2026, 11, 18, 10, 30, tzinfo=ET_))
    assert round(b["lower"], 2) == 4.5 and round(b["upper"], 2) == 5.5
    r = RiskConfig()

    class M:
        def __init__(self, price, bid, ask):
            self.p, self.b, self.a = price, bid, ask
        def price(self, s): return self.p
        def candles(self, s, tf, n): return c
        def order_book(self, s): return {"best_bid": self.b, "best_ask": self.a}

    import trader.halts as H
    real = H.luld_active
    H.luld_active = lambda now=None: (True, 1.0)
    try:
        pos = Position("X", 100, 5.0, 4.8, None, 0, 500, entry_spread_pct=0.4)
        assert exit_signal(M(4.55, 4.54, 4.56), "X", pos, r)[0] == "all"         # near limit-down
        assert exit_signal(M(5.45, 5.44, 5.46), "X", pos, r)[0] == "half"        # near limit-up: take half
        assert exit_signal(M(5.0, 4.90, 5.10), "X", pos, r)[0] == "all"          # spread blew out (4%)
        assert exit_signal(M(5.0, 4.99, 5.01), "X", pos, r) is None              # normal
        assert "spread" in entry_block(M(5.0, 4.94, 5.06), "X", r)               # 2.4% spread: don't buy
        assert "limit-up" in entry_block(M(5.4, 5.39, 5.41), "X", r)             # right under the band
        assert entry_block(M(5.0, 4.99, 5.01), "X", r) is None
    finally:
        H.luld_active = real
