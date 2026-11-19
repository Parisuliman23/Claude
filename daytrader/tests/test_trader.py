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
    cfg = Config(symbols=["BTC/USD", "ETH/USD"], state_dir=tmp_path, risk=RiskConfig(),
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
    assert broker.realized[-1]["reason"].startswith("auto: stop-loss")
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
