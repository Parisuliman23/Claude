"""Phone alerts and remote control through ntfy (https://ntfy.sh, free app for Android/iPhone).

Setup: install the ntfy app, subscribe to two topics with long random names (anyone who knows
a topic name can read/post to it, so treat the names like passwords):
  NTFY_TOPIC      alerts from the agent (trades, stops, daily summary)
  NTFY_TOPIC-cmd  commands you send from the app: status, stop, resume, flatten, help
"""
from __future__ import annotations

import json
import logging
import os
import time

import httpx

log = logging.getLogger("trader.notify")

COMMANDS = {
    "status": "account, positions and today's P&L",
    "stop": "block new trades (open positions keep their stops)",
    "resume": "allow new trades again",
    "flatten": "sell everything now and block new trades",
    "help": "list commands",
}


class Notifier:
    def __init__(self, topic: str | None = None, server: str | None = None,
                 http: httpx.Client | None = None):
        self.topic = topic or os.environ.get("NTFY_TOPIC")
        self.server = (server or os.environ.get("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
        self.http = http or httpx.Client(timeout=10)
        self.since: str | None = None  # last seen message id (set on the first poll)

    @property
    def enabled(self) -> bool:
        return bool(self.topic)

    def send(self, title: str, message: str, priority: str = "default", tags: str = "") -> None:
        if not self.enabled:
            return
        try:
            # ntfy headers must be latin-1; keep titles plain
            headers = {"Title": title.encode("ascii", "replace").decode(), "Priority": priority}
            if tags:
                headers["Tags"] = tags
            self.http.post(f"{self.server}/{self.topic}", content=message.encode(), headers=headers)
        except Exception as e:  # alerts must never break trading
            log.warning("ntfy send failed: %s", e)

    def poll_commands(self) -> list[str]:
        """New commands posted to <topic>-cmd since the last poll."""
        if not self.enabled:
            return []
        try:
            first = self.since is None
            # First poll: only find the newest existing message so old commands are ignored.
            # Using message ids (not timestamps) avoids problems with clock differences.
            r = self.http.get(f"{self.server}/{self.topic}-cmd/json",
                              params={"poll": "1", "since": "all" if first else self.since})
            if first:
                self.since = "all"
                for line in r.text.splitlines():
                    if line.strip():
                        self.since = json.loads(line).get("id") or self.since
                return []  # if the topic was empty, "all" is right: every later message is new
            cmds = []
            for line in r.text.splitlines():
                if not line.strip():
                    continue
                msg = json.loads(line)
                if msg.get("event") != "message":
                    continue
                self.since = msg.get("id") or self.since
                cmds.append((msg.get("message") or "").strip().lower())
            return cmds
        except Exception as e:
            log.debug("ntfy poll failed: %s", e)
            return []


def describe_event(event: str, d: dict) -> tuple[str, str, str, str] | None:
    """Turn a journal event into (title, message, priority, tags), or None to stay quiet."""
    if event == "open":
        return (f"BUY {d['symbol']} @ {d['price']:.2f}",
                f"${d['usd']:,.0f} ({d['qty']:.0f} sh). Stop {d['stop']}, target {d.get('tp')}.\n{d.get('reason','')}",
                "high", "chart_with_upwards_trend")
    if event in ("close", "sell_partial"):
        pnl = d.get("trade_total_pnl_usd", d.get("pnl_usd", 0))
        verb = "SOLD HALF" if d.get("partial") else "SOLD"
        return (f"{verb} {d['symbol']} @ {d['exit_price']:.2f}  {'+' if pnl >= 0 else ''}${pnl:,.2f}",
                d.get("reason", ""), "high", "white_check_mark" if pnl >= 0 else "x")
    if event == "halt":
        return ("Done for the day", d.get("reason", ""), "high", "stop_sign")
    if event == "error":
        return ("Agent error", d.get("message", ""), "urgent", "warning")
    if event == "day_summary":
        return ("Day summary", d.get("text", ""), "default", "memo")
    return None
