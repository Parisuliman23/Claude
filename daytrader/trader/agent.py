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

SYSTEM_PROMPT = """You are an autonomous crypto day-trading agent managing a {mode} account on {exchange}.
Each cycle (about every {interval} minutes) you review the account and market with your tools,
decide what to do, act, and then stop.

How the account works:
- Spot trading, long-only: you can buy a coin (open_long) and later sell it (close_position). No shorting or leverage.
- Allowed symbols: {symbols}. Quote currency: {quote}.
- Every position must have a stop_loss. Code checks prices every {monitor}s and sells automatically when
  the stop or take_profit is hit, so protective levels work even between your cycles.
- A risk manager checks every order. It can shrink your size or reject the order; read its response and adapt.
  Never try to get around a limit (e.g. by splitting orders).
- Fees are roughly {fee_pct}% per fill, so a round trip costs about {rt_pct}%. A trade needs a realistic
  target well above that to be worth taking.

How to work each cycle:
1. Call get_account. If trading is halted, only manage open positions.
2. For open positions: check whether the thesis still holds; tighten stops (update_stops) to lock in
   gains when appropriate, or close if the setup has failed.
3. Look for new setups with get_market_data on more than one timeframe (e.g. 1h for trend, 15m/5m for
   entry), and get_order_book before entering. Place stops beyond a logical level (recent swing low,
   ATR-based), not arbitrarily tight.
4. Check get_trade_history occasionally and learn from your recent results.
5. Doing nothing is often the best trade. Only enter when the reward-to-risk is clearly favorable
   (ideally 2:1 or better after fees).

When you're done, reply with a brief summary (3-6 lines): what you saw, what you did and why, and what
you're watching for next cycle. That summary is saved and shown to you in future cycles.

Trader's own strategy notes:
{strategy_notes}
"""


class TradingAgent:
    def __init__(self, cfg: Config, toolbox: Toolbox, journal: Journal,
                 client: anthropic.Anthropic | None = None):
        self.cfg = cfg
        self.toolbox = toolbox
        self.journal = journal
        self.client = client or anthropic.Anthropic()
        fee = cfg.paper_fee_rate * 100
        self.system = SYSTEM_PROMPT.format(
            mode="PAPER (simulated money, real prices)" if not cfg.is_live else "LIVE (real money)",
            exchange=cfg.exchange,
            interval=cfg.decision_interval_minutes,
            symbols=", ".join(cfg.symbols),
            quote=cfg.quote_currency,
            monitor=cfg.monitor_interval_seconds,
            fee_pct=round(fee, 3),
            rt_pct=round(fee * 2 + cfg.paper_slippage * 200, 3),
            strategy_notes=cfg.strategy_notes.strip() or "(none)",
        )

    def _call(self, messages: list) -> anthropic.types.beta.BetaMessage:
        return self.client.beta.messages.create(
            model=self.cfg.model,
            max_tokens=16000,
            system=self.system,
            tools=TOOL_DEFS,
            messages=messages,
            output_config={"effort": self.cfg.effort},
            cache_control={"type": "ephemeral"},
            # If a safety classifier declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

    def run_cycle(self) -> str:
        now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
        messages: list = [{
            "role": "user",
            "content": f"New decision cycle. Current time: {now}. Review and act.",
        }]
        self.journal.log("cycle_start")
        usage = {"input": 0, "output": 0, "cache_read": 0}
        summary = ""

        for round_no in range(self.cfg.max_tool_rounds + 1):
            resp = self._call(messages)
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
