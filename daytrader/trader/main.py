"""Command-line entry point.

  python -m trader.main run        # run forever: Claude decides every N minutes, code guards stops
  python -m trader.main once       # one decision cycle, then exit
  python -m trader.main status     # print account, positions, P&L
  python -m trader.main flatten    # sell everything now
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time

import anthropic

from .agent import TradingAgent
from .broker import BaseBroker, LiveBroker, PaperBroker
from .config import Config, load_config
from .market import MarketData, make_exchange
from .risk import RiskManager
from .tools import Journal, Toolbox

log = logging.getLogger("trader")


def build(cfg: Config):
    market = MarketData(make_exchange(cfg))
    if cfg.is_live:
        broker: BaseBroker = LiveBroker(market, cfg.state_dir / "live_account.json", cfg.quote_currency)
    else:
        broker = PaperBroker(market, cfg.state_dir / "paper_account.json", cfg.paper_starting_cash,
                             cfg.paper_fee_rate, cfg.paper_slippage)
    journal = Journal(cfg.state_dir / f"journal_{cfg.mode}.jsonl")
    risk = RiskManager(cfg, broker)
    return broker, risk, journal, Toolbox(cfg, broker, risk, journal)


def guard(broker: BaseBroker, risk: RiskManager, journal: Journal) -> None:
    """Runs between decisions: enforce stops/targets, daily-loss halt, and end-of-day flatten."""
    flatten_reason = None
    if risk.flatten_due():
        flatten_reason = "end-of-day flatten"
    elif (h := risk.halted()) and "Daily loss" in h:
        flatten_reason = "daily loss limit"

    for symbol, pos in list(broker.positions.items()):
        try:
            price = broker.market.price(symbol)
        except Exception as e:
            log.warning("price fetch failed for %s: %s", symbol, e)
            continue
        reason = flatten_reason
        if not reason and pos.stop_loss is not None and price <= pos.stop_loss:
            reason = f"stop-loss hit ({price} <= {pos.stop_loss})"
        elif not reason and pos.take_profit is not None and price >= pos.take_profit:
            reason = f"take-profit hit ({price} >= {pos.take_profit})"
        if reason:
            try:
                rec = broker.close(symbol, f"auto: {reason}")
                journal.log("close", **rec)
                log.info("AUTO CLOSE %s: %s  pnl=$%.2f", symbol, reason, rec["pnl_usd"])
            except Exception:
                log.exception("auto close failed for %s", symbol)


def cmd_status(cfg: Config) -> None:
    broker, risk, journal, toolbox = build(cfg)
    print(json.dumps(toolbox.t_get_account(), indent=2, default=str))
    trades = broker.realized
    if trades:
        wins = [t for t in trades if t["pnl_usd"] > 0]
        print(f"\nClosed trades: {len(trades)}  win rate: {len(wins)/len(trades)*100:.0f}%  "
              f"total realized: ${sum(t['pnl_usd'] for t in trades):,.2f}")
    if isinstance(broker, PaperBroker):
        eq = broker.equity()
        print(f"Paper return since start: {(eq/broker.starting_cash-1)*100:+.2f}%")


def cmd_flatten(cfg: Config) -> None:
    broker, risk, journal, _ = build(cfg)
    for s in list(broker.positions):
        rec = broker.close(s, "manual flatten")
        journal.log("close", **rec)
        print(f"Closed {s}: pnl ${rec['pnl_usd']:.2f}")
    print("Flat.")


def run_cycle_safely(agent: TradingAgent) -> None:
    try:
        summary = agent.run_cycle()
        log.info("CYCLE SUMMARY:\n%s", summary)
    except anthropic.RateLimitError as e:
        log.warning("Rate limited by Claude API; skipping this cycle (%s)", e)
    except anthropic.APIConnectionError as e:
        log.warning("Network error talking to Claude API; skipping this cycle (%s)", e)
    except anthropic.APIStatusError as e:
        log.error("Claude API error %s: %s", e.status_code, e.message)
    except Exception:
        log.exception("Decision cycle crashed; continuing")


def cmd_run(cfg: Config, once: bool) -> None:
    broker, risk, journal, toolbox = build(cfg)
    agent = TradingAgent(cfg, toolbox, journal)
    if cfg.is_live:
        log.warning("LIVE MODE: real orders will be placed on %s. Ctrl-C to stop, "
                    "or create state/KILL to block new trades.", cfg.exchange)
    else:
        log.info("Paper mode on %s, equity $%.2f", cfg.exchange, broker.equity())

    if once:
        guard(broker, risk, journal)
        run_cycle_safely(agent)
        return

    next_decision = 0.0
    while True:
        try:
            guard(broker, risk, journal)
        except Exception:
            log.exception("guard failed")
        if time.time() >= next_decision:
            run_cycle_safely(agent)
            next_decision = time.time() + cfg.decision_interval_minutes * 60
        time.sleep(cfg.monitor_interval_seconds)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="trader", description="Claude crypto day-trading agent")
    p.add_argument("command", choices=["run", "once", "status", "flatten"])
    p.add_argument("--config", default=None, help="path to config.yaml")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    cfg = load_config(a.config) if a.config else load_config()

    if a.command == "status":
        cmd_status(cfg)
    elif a.command == "flatten":
        cmd_flatten(cfg)
    else:
        try:
            cmd_run(cfg, once=a.command == "once")
        except KeyboardInterrupt:
            log.info("Stopped. Open positions are kept; run `flatten` to close them.")


if __name__ == "__main__":
    main()
