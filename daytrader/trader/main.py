"""Command-line entry point.

  python -m trader.main run        # run all day: scans, setup alerts, stop/target guard
  python -m trader.main once       # one scheduled cycle, then exit
  python -m trader.main scan       # print today's 5-pillar scanner results (no Claude, no trades)
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
from .broker import BaseBroker, PaperBroker
from .config import Config, load_config
from .risk import RiskManager
from .tools import Journal, Toolbox

log = logging.getLogger("trader")


def build(cfg: Config):
    if cfg.market == "stocks":
        from .alpaca import AlpacaBroker, AlpacaClient, AlpacaMarket
        market = AlpacaMarket(AlpacaClient(live=cfg.is_live, feed=cfg.stocks_data_feed))
        broker: BaseBroker = AlpacaBroker(market, cfg.state_dir / f"stocks_{cfg.mode}_positions.json")
    else:
        from .broker import LiveBroker
        from .market import MarketData, make_exchange
        market = MarketData(make_exchange(cfg))
        if cfg.is_live:
            broker = LiveBroker(market, cfg.state_dir / "live_account.json", cfg.quote_currency)
        else:
            broker = PaperBroker(market, cfg.state_dir / "paper_account.json", cfg.paper_starting_cash,
                                 cfg.paper_fee_rate, cfg.paper_slippage)
    journal = Journal(cfg.state_dir / f"journal_{cfg.market}_{cfg.mode}.jsonl")
    risk = RiskManager(cfg, broker)
    return broker, risk, journal, Toolbox(cfg, broker, risk, journal)


def _min_move(cfg_r, market_kind: str, entry: float) -> float:
    # stocks: dollars per share (Ross's "10 cents"); crypto: 0.3% of price
    return cfg_r.bailout_min_move if market_kind == "stocks" else entry * 0.003


def new_low_candle(broker: BaseBroker, symbol: str, since_ts: float, timeframe: str) -> bool:
    """True if a completed candle after entry broke the previous candle's low."""
    from .tools import closed_candles
    candles = closed_candles(broker.market.candles(symbol, timeframe, 6), timeframe)
    since_ms = since_ts * 1000
    for prev, cur in zip(candles, candles[1:]):
        if cur[0] >= since_ms - 1 and cur[3] < prev[3]:
            return True
    return False


def guard(broker: BaseBroker, risk: RiskManager, journal: Journal, check_candles: bool = True) -> None:
    """Runs every few seconds, no AI. Ross's exit rules:
    stop at the pullback low · breakout or bailout (no ~10c move within ~1 min) ·
    first candle to make a new low · sell half at the target and move stop to break-even ·
    daily-loss / end-of-window flatten."""
    r = risk.r
    kind = getattr(broker.market, "kind", "crypto")
    flatten_reason = None
    if risk.flatten_due():
        flatten_reason = "end of trade window / flatten time"
    elif (h := risk.halted()) and "Daily loss" in h:
        flatten_reason = "daily loss limit"

    for symbol, pos in list(broker.positions.items()):
        try:
            price = broker.market.price(symbol)
        except Exception as e:
            log.warning("price fetch failed for %s: %s", symbol, e)
            continue
        try:
            if price > pos.max_price:
                pos.max_price = price
            reason = flatten_reason
            if not reason and pos.stop_loss is not None and price <= pos.stop_loss:
                reason = f"stop hit ({price} <= {pos.stop_loss})"
            held_min = (time.time() - pos.opened_at) / 60
            if (not reason and r.breakout_or_bailout_minutes and not pos.scaled_out
                    and held_min >= r.breakout_or_bailout_minutes
                    and pos.max_price < pos.entry_price + _min_move(r, kind, pos.entry_price)):
                reason = (f"breakout or bailout: no follow-through within {held_min:.1f} min "
                          f"(high since entry {pos.max_price}, entry {pos.entry_price})")
            if not reason and check_candles and r.exit_on_new_low_candle:
                try:
                    if new_low_candle(broker, symbol, pos.opened_at, r.exit_candle_timeframe):
                        reason = "exit indicator: first candle to make a new low"
                except Exception as e:
                    log.debug("candle check %s failed: %s", symbol, e)
            if reason:
                rec = broker.close(symbol, f"auto: {reason}")
                journal.log("close", **rec)
                log.info("AUTO CLOSE %s: %s  pnl=$%.2f", symbol, reason, rec["pnl_usd"])
                continue
            if pos.take_profit is not None and price >= pos.take_profit:
                if r.scale_out_fraction and not pos.scaled_out and r.scale_out_fraction < 1:
                    rec = broker.reduce(symbol, r.scale_out_fraction,
                                        f"auto: first target {pos.take_profit} hit, scaling out")
                    journal.log("sell_partial", **rec)
                    if symbol in broker.positions:
                        p = broker.positions[symbol]
                        p.scaled_out = True
                        p.take_profit = None  # the rest rides until an exit indicator
                        if r.move_stop_to_breakeven:
                            p.stop_loss = max(p.stop_loss or 0, p.entry_price)
                        broker.save()
                        journal.log("update_stops", symbol=symbol, stop=p.stop_loss, tp=None,
                                    reason="auto: break-even after scale-out")
                    log.info("SCALE OUT %s at %s pnl=$%.2f, stop to break-even", symbol, price,
                             rec["pnl_usd"])
                else:
                    rec = broker.close(symbol, f"auto: take-profit hit ({price})")
                    journal.log("close", **rec)
                    log.info("AUTO CLOSE %s at target pnl=$%.2f", symbol, rec["pnl_usd"])
            else:
                broker.save()
        except Exception:
            log.exception("guard action failed for %s", symbol)
    risk.update_peak()


class SetupWatcher:
    """Checks the watchlist's 1-minute charts and returns a triggered setup, if any."""

    def __init__(self, toolbox: Toolbox, cooldown_s: float = 180):
        self.toolbox = toolbox
        self.cooldown_s = cooldown_s
        self.last_alert: dict[str, float] = {}

    def check(self) -> dict | None:
        tb = self.toolbox
        if tb.risk.new_trade_block():
            return None
        approved = tb.cfg.symbols or tb.scanner.approved_symbols()
        for sym in tb.watchlist:
            if sym in tb.broker.positions or sym not in approved:
                continue
            if time.time() - self.last_alert.get(sym, 0) < self.cooldown_s:
                continue
            try:
                st = tb.setup(sym, tb.cfg.setup_timeframe)
            except Exception as e:
                log.debug("setup check %s failed: %s", sym, e)
                continue
            if st.get("state") == "triggered":
                self.last_alert[sym] = time.time()
                tb.journal.log("setup_alert", symbol=sym, setup=st)
                return {"symbol": sym, "timeframe": tb.cfg.setup_timeframe, "setup": st}
        return None


def run_cycle_safely(agent: TradingAgent, alert: dict | None = None) -> None:
    try:
        summary = agent.run_cycle(alert)
        log.info("CYCLE SUMMARY:\n%s", summary)
    except anthropic.RateLimitError as e:
        log.warning("Rate limited by Claude API; skipping this cycle (%s)", e)
    except anthropic.APIConnectionError as e:
        log.warning("Network error talking to Claude API; skipping this cycle (%s)", e)
    except anthropic.APIStatusError as e:
        log.error("Claude API error %s: %s", e.status_code, e.message)
    except Exception:
        log.exception("Decision cycle crashed; continuing")


def cmd_status(cfg: Config) -> None:
    broker, risk, journal, toolbox = build(cfg)
    print(json.dumps(toolbox.t_get_account(), indent=2, default=str))
    done = broker.completed_trades()
    if done:
        pnl = [t.get("trade_total_pnl_usd", t["pnl_usd"]) for t in done]
        wins = [p for p in pnl if p > 0]
        losses = [p for p in pnl if p <= 0]
        avg_w = sum(wins) / len(wins) if wins else 0
        avg_l = -sum(losses) / len(losses) if losses else 0
        print(f"\nTrades: {len(done)}  accuracy: {len(wins)/len(done)*100:.0f}%  "
              f"avg win ${avg_w:,.2f} / avg loss ${avg_l:,.2f}"
              f"{f'  (P/L ratio {avg_w/avg_l:.2f})' if avg_l else ''}  total ${sum(pnl):,.2f}")
        acc = len(wins) / len(done)
        plr = (avg_w / avg_l) if avg_l else float("inf")
        ok = sum(pnl) > 0 and acc >= 0.60 and plr > 1
        print("Ross's bar for going live (after 10+ days of one trade a day): net profit > 0, "
              "accuracy >= 60%, P/L ratio > 1:1 -> " + ("MET" if ok else "not met yet"))
    if isinstance(broker, PaperBroker):
        print(f"Paper return since start: {(broker.equity()/broker.starting_cash-1)*100:+.2f}%")


def cmd_scan(cfg: Config) -> None:
    _, _, _, toolbox = build(cfg)
    for c in toolbox.scanner.scan():
        mark = "PASS" if c["passes"] else "fail"
        print(f"[{mark}] {c['symbol']:<8} ${c['price']:<8} {c['change_pct']:+.1f}%  "
              f"rvol {c.get('relative_volume')}  float {c.get('float_shares')}  "
              f"failed: {', '.join(c['failed_pillars']) or '-'}")
        for n in (c.get("news") or [])[:2]:
            print(f"           news: {n['headline']}")


def cmd_flatten(cfg: Config) -> None:
    broker, risk, journal, _ = build(cfg)
    for s in list(broker.positions):
        rec = broker.close(s, "manual flatten")
        journal.log("close", **rec)
        print(f"Closed {s}: pnl ${rec['pnl_usd']:.2f}")
    print("Flat.")


def cmd_run(cfg: Config, once: bool) -> None:
    broker, risk, journal, toolbox = build(cfg)
    agent = TradingAgent(cfg, toolbox, journal)
    watcher = SetupWatcher(toolbox)
    if cfg.is_live:
        log.warning("LIVE MODE: real orders. Ctrl-C to stop, or create state/KILL to block new trades.")
    else:
        log.info("PAPER mode (%s), equity $%.2f", cfg.market, broker.equity())

    if once:
        guard(broker, risk, journal)
        run_cycle_safely(agent)
        return

    next_cycle = next_watch = next_candle_check = last_mark_cycle = 0.0
    idle_logged = False
    while True:
        try:
            do_candles = time.time() >= next_candle_check
            if do_candles:
                next_candle_check = time.time() + cfg.watch_interval_seconds
            guard(broker, risk, journal, check_candles=do_candles)
        except Exception:
            log.exception("guard failed")
        now = time.time()
        active = risk.in_window() or bool(broker.positions)
        if not active:
            if not idle_logged:
                log.info("Outside the trade window (%s); waiting.", cfg.risk.trade_window)
                idle_logged = True
            time.sleep(30)
            continue
        idle_logged = False

        # extra cycle ~1 minute after each :00 / :30 (Ross: headlines drop at the top/bottom of the hour)
        lt = time.localtime(now)
        half_hour_mark = lt.tm_min in (1, 31) and now - last_mark_cycle > 120
        if now >= next_cycle or half_hour_mark:
            if half_hour_mark:
                last_mark_cycle = now
            run_cycle_safely(agent)
            next_cycle = time.time() + cfg.decision_interval_minutes * 60
        elif now >= next_watch and toolbox.watchlist:
            next_watch = now + cfg.watch_interval_seconds
            alert = watcher.check()
            if alert:
                log.info("SETUP TRIGGER %s: waking Claude", alert["symbol"])
                run_cycle_safely(agent, alert)
        time.sleep(cfg.monitor_interval_seconds)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="trader", description="Claude momentum day-trading agent")
    p.add_argument("command", choices=["run", "once", "scan", "status", "flatten"])
    p.add_argument("--config", default=None, help="path to config.yaml")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    cfg = load_config(a.config) if a.config else load_config()

    if a.command == "status":
        cmd_status(cfg)
    elif a.command == "scan":
        cmd_scan(cfg)
    elif a.command == "flatten":
        cmd_flatten(cfg)
    else:
        try:
            cmd_run(cfg, once=a.command == "once")
        except KeyboardInterrupt:
            log.info("Stopped. Open positions are kept; run `flatten` to close them.")


if __name__ == "__main__":
    main()
