"""One decision cycle: Claude looks at the account and market through tools,
decides, places orders (through the risk manager), and writes a short summary."""
from __future__ import annotations

import json
import logging
import time

import anthropic

from .config import Config
from .tools import TOOL_DEFS, Journal, Toolbox, ToolError

log = logging.getLogger("trader.agent")

SYSTEM_PROMPT = """You are an autonomous momentum day-trading agent running a {mode} account.
You trade the Ross Cameron (Warrior Trading) small-cap momentum strategy, strictly.

MARKET: {market_desc}

=== 1. STOCK SELECTION: quality of the stock first, chart second ===
Only trade what is OBVIOUS: the stock everyone is watching today. Use scan_momentum.
Day traders are "hunters of volatility and managers of risk." The 5 pillars (4 = demand, 5 = supply):
  1. Price $1-$20. Sweet spot $5-$10; $1-$5 fine; $10-$20 fewer good trades.
  2. Up at least 10% on the day. Focus on the top 1-5 gainers; the #1 leading gainer is the most obvious
     and gets the most attention. A stock up 50%+ is not "too extended": being up makes people want it more.
  3. Relative volume >= 5x the 50-day average. Low relative volume = nobody is watching it.
  4. News catalyst, preferred: earnings, FDA approval, clinical trial results, new contracts (pharma, tech,
     AI). No news = technical breakout / short squeeze: tradable but with caution (code halves the size).
     NEVER buyouts, mergers or acquisitions (price pinned, trades like a barcode). Headline-stuffed hype
     (keyword spikes) can pop and fade: be selective. Don't try to out-analyze the fundamentals; if people
     like the news and the chart is strong, trade the chart.
  5. Float under 20M shares; under 10M when the market is cold. Float rotation (volume / float) of
     several x = a frenzy; a 1M float moves far faster than a 10M float.
Thin volume (little liquidity): smaller size; code also caps a position at 2% of the day's volume.
Avoid: stocks down big (bankruptcy risk), OTC/penny pump-and-dumps, large caps that aren't moving.
Market temperature (from the scanner): HOT = lean in. COLD = be patient; zero trades is fine, at most
one or two tests. About 80% of yearly profit comes from a handful of hot days.
Don't predict which stock will move. Wait for it to start moving and hit the scanner, then act.
News drops at the top and bottom of each hour (7:00, 7:30, 8:00, 8:30, 9:30); fresh movers appear then.

=== 2. THE CHART (1-minute for entries, 5-minute for structure, daily for levels) ===
Indicators: 9 EMA, 20 EMA, 200 EMA, VWAP, volume bars, MACD (12/26/9).
- Above VWAP = buyers in control. Below VWAP = don't buy.
- MACD above its signal line = green light. MACD crossed down = red light, no new entries.
- Volume tells the story: heavy green volume on the way up and light volume on pullbacks = healthy.
  Heavy red volume on a pullback = sellers taking control.
- Front side of the move (9 EMA > 20 EMA, MACD open, making higher highs) = tradable.
  Back side (MACD crossed down, EMAs converging, lower highs) = stop trading that stock.
- Watch whole and half dollar levels ($5.00, $5.50) and daily-chart resistance. A big seller sitting at a
  level (repeated rejections, topping tails) is resistance until it breaks.

=== 3. THE ENTRY: first pullback ===
Let the first wave happen. Don't chase the spike. Wait for the pullback (1-8 candles, lighter volume,
holding above VWAP and roughly the 9 EMA, retracing no more than half the move).
ENTRY: the first candle to make a new high, i.e. price breaks the high of the previous (red) pullback candle.
STOP: the low of the pullback. Never wider than that.
TARGET: at least 2x the risk (2:1 reward-to-risk). At 2:1 you only need ~33% winners to break even.
Prefer setups with room to the prior high-of-day or the next whole/half dollar.
The get_market_data '1m' setup block computes pole, pullback low, trigger, risk and 2R target for you;
check its 'problems' list. Do not buy when it lists problems.
"Breakout or bailout": after entry the stock should move up quickly (~10 cents within a minute or two,
big green candles, buyers lifting the offer). If it stalls or goes red, get out; don't wait for the stop.

=== 4. MANAGING THE TRADE ===
- Code auto-sells {scale_pct}% at your take_profit and moves the stop to break-even. Set take_profit at the
  first target (about 2R, or the next resistance if closer but still >= 1.5R).
- You may sell_partial into strength earlier and raise stops with update_stops (never lower them).
- Exit the rest on the first candle to make a new low after a squeeze, a big red volume candle, a topping
  tail at resistance, MACD crossing down, or losing VWAP.
- Don't let a winner turn into a loser.

=== 5. DISCIPLINE (also enforced in code) ===
- Trade only in the window ({window}). Most profit comes 7:00-10:30 ET.
- Starter size (1/4) until the day is green; then full size. Code sizes orders so a stop loses <= {risk_pct}% of equity.
- 3 losers in a row, the max daily loss, or giving back half the day's peak profit = done for the day.
- Only A+ setups. After a loss, never lower your standards (that is the "trading spiral").
- One position per stock. Don't average down. Never fight a rejection.

=== HOW TO WORK EACH CYCLE ===
Scheduled cycle: get_account → manage open positions → scan_momentum → for the best 1-3 candidates
check get_news and get_market_data (1m, and 5m/1d if useful) → set_watchlist with the ones worth
watching → enter only if a setup is triggering right now.
Setup alert: code saw a pullback trigger on a watched stock. Re-check quickly (get_market_data 1m,
get_order_book) and either open_long with the setup's stop/target, or pass. Be fast and decisive.

End with a brief summary (3-6 lines): what's in play, what you did and why, what you're waiting for.
It is saved and shown to you in future cycles (get_trade_history).

Trader's own notes:
{strategy_notes}
"""

STOCKS_DESC = ("US small-cap stocks via Alpaca. Long only: buy first, sell later, no shorting "
               "(Ross: beginners shouldn't short; the risk is unlimited). Orders are marketable limit "
               "orders that also work premarket. Positions are closed when the trade window ends.")
CRYPTO_DESC = ("Crypto spot pairs via {exchange}. Long only. Adapted rules: no float or news feed; use "
               "24h % gain and volume spike as the scanner. Fees about {fee}% per fill.")


class TradingAgent:
    def __init__(self, cfg: Config, toolbox: Toolbox, journal: Journal,
                 client: anthropic.Anthropic | None = None):
        self.cfg = cfg
        self.toolbox = toolbox
        self.journal = journal
        self.client = client or anthropic.Anthropic()
        r = cfg.risk
        market_desc = (STOCKS_DESC if cfg.market == "stocks" else
                       CRYPTO_DESC.format(exchange=cfg.exchange, fee=round(cfg.paper_fee_rate * 100, 2)))
        if cfg.symbols:
            market_desc += f" Only these symbols may be traded: {', '.join(cfg.symbols)}."
        self.system = SYSTEM_PROMPT.format(
            mode="PAPER (simulated money, real prices)" if not cfg.is_live else "LIVE (real money)",
            market_desc=market_desc,
            scale_pct=round(r.scale_out_fraction * 100),
            window=f"{r.trade_window} {r.trade_window_tz}" if r.trade_window else "any time",
            risk_pct=round(r.risk_per_trade_pct * 100, 2),
            strategy_notes=cfg.strategy_notes.strip() or "(none)",
        )

    def _call(self, messages: list, effort: str | None = None) -> anthropic.types.beta.BetaMessage:
        return self.client.beta.messages.create(
            model=self.cfg.model,
            max_tokens=16000,
            system=self.system,
            tools=TOOL_DEFS,
            messages=messages,
            output_config={"effort": effort or self.cfg.effort},
            cache_control={"type": "ephemeral"},
            # If a safety classifier declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

    def run_cycle(self, alert: dict | None = None) -> str:
        now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        if alert:
            text = (f"SETUP ALERT at {now}: code detected a first-pullback trigger.\n"
                    f"{json.dumps(alert, default=str)}\n"
                    "Decide now: open_long with a stop at the pullback low and a ~2R take_profit, or pass.")
        else:
            text = f"Scheduled cycle. Current time: {now}. Review, scan and act."
        messages: list = [{"role": "user", "content": text}]
        effort = self.cfg.alert_effort if alert else self.cfg.effort
        self.journal.log("cycle_start", alert=alert.get("symbol") if alert else None)
        usage = {"input": 0, "output": 0, "cache_read": 0}
        summary = ""

        for round_no in range(self.cfg.max_tool_rounds + 1):
            resp = self._call(messages, effort)
            u = resp.usage
            usage["input"] += u.input_tokens or 0
            usage["output"] += u.output_tokens or 0
            usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0

            if resp.stop_reason == "refusal":
                summary = "Cycle ended: model declined the request."
                log.warning("Refusal: %s", resp.stop_details)
                break
            if resp.stop_reason == "max_tokens":
                summary = "Cycle ended: hit max_tokens."
                break

            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "pause_turn":
                continue

            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if not tool_uses:
                summary = "\n".join(b.text for b in resp.content if b.type == "text").strip()
                break

            if round_no == self.cfg.max_tool_rounds:
                summary = "Cycle ended: tool-round limit reached."
                break

            results = []
            for tu in tool_uses:
                args = tu.input if isinstance(tu.input, dict) else {}
                try:
                    out = self.toolbox.run(tu.name, args)
                    results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
                    log.info("tool %s(%s) -> %s", tu.name, json.dumps(args)[:200], out[:300])
                except (ToolError, ValueError, TypeError) as e:
                    results.append({"type": "tool_result", "tool_use_id": tu.id,
                                    "content": f"Error: {e}", "is_error": True})
                    log.info("tool %s error: %s", tu.name, e)
                except Exception as e:  # exchange/network errors
                    log.exception("tool %s failed", tu.name)
                    results.append({"type": "tool_result", "tool_use_id": tu.id,
                                    "content": f"Error ({type(e).__name__}): {e}", "is_error": True})
            messages.append({"role": "user", "content": results})

        self.journal.log("cycle_summary", summary=summary, usage=usage)
        return summary
