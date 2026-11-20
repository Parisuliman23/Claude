"""Live viewing screen: a small web server inside the agent process.

Open  http://<server-ip>:8080/?token=<DASHBOARD_TOKEN>  in a phone browser.
Shows a live 1-minute chart (EMA 9/20, VWAP, volume) of the watched/held stocks with the
agent's buys/sells as arrows and entry/stop/target lines, plus the account and an activity feed.
Read-only: nothing on this page can place or cancel trades.
"""
from __future__ import annotations

import json
import logging
import secrets
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from .indicators import ema_series

log = logging.getLogger("trader.dashboard")
ET = ZoneInfo("America/New_York")


def et_seconds(ms: float) -> int:
    """Chart time: UTC seconds shifted so the chart's clock reads US/Eastern."""
    dt = datetime.fromtimestamp(ms / 1000, timezone.utc)
    return int(ms / 1000 + dt.astimezone(ET).utcoffset().total_seconds())


def ensure_token(env_path: Path) -> str:
    """DASHBOARD_TOKEN from .env, created (and saved) on first use."""
    import os
    tok = os.environ.get("DASHBOARD_TOKEN")
    if tok:
        return tok
    tok = secrets.token_urlsafe(18)
    try:
        with env_path.open("a") as f:
            f.write(f"\nDASHBOARD_TOKEN={tok}\n")
    except OSError:
        pass
    os.environ["DASHBOARD_TOKEN"] = tok
    return tok


class Dashboard:
    def __init__(self, toolbox, market_factory, token: str, port: int = 8080):
        self.tb = toolbox
        self.market_factory = market_factory  # own market client: no sharing with the trading thread
        self._market = None
        self.token = token
        self.port = port
        self._lock = threading.Lock()

    @property
    def market(self):
        if self._market is None:
            self._market = self.market_factory()
        return self._market

    # -- data -----------------------------------------------------------------
    def state(self) -> dict:
        tb = self.tb
        positions = []
        for sym, p in list(tb.broker.positions.items()):
            try:
                px = self.market.price(sym)
            except Exception:
                px = None
            positions.append({"symbol": sym, "qty": p.qty, "entry": p.entry_price, "stop": p.stop_loss,
                              "target": p.take_profit, "price": px,
                              "pnl": round(px * p.qty - p.cost_usd + p.realized_usd, 2) if px else None,
                              "scaled_out": p.scaled_out})
        try:
            pnl, pct = tb.risk.day_pnl()
            equity = tb.broker.equity()
        except Exception:
            pnl = pct = equity = None
        events = []
        for e in tb.journal.tail(60):
            if e["event"] in ("cycle_start",):
                continue
            events.append(_describe(e))
        cands = [{"symbol": c["symbol"], "change_pct": c["change_pct"], "price": c["price"],
                  "rvol": c.get("relative_volume"), "passes": c["passes"]}
                 for c in (tb.scanner.last or [])[:10]]
        return {
            "now_et": datetime.now(ET).strftime("%a %b %d %H:%M:%S ET"),
            "mode": f"{tb.cfg.mode.upper()} · {tb.cfg.decision_mode}",
            "equity": equity, "day_pnl": pnl, "day_pnl_pct": round(pct * 100, 2) if pct is not None else None,
            "trades_today": tb.risk.state.get("trades_today"),
            "blocked": tb.risk.new_trade_block(),
            "in_window": tb.risk.in_window(),
            "positions": positions,
            "watchlist": list(tb.watchlist),
            "temperature": getattr(tb.scanner, "market_temperature", None),
            "candidates": cands,
            "events": events[::-1][:40],
            "symbols": list(dict.fromkeys([p["symbol"] for p in positions] + list(tb.watchlist)
                                          + [c["symbol"] for c in cands if c["passes"]])),
        }

    def candles(self, symbol: str) -> dict:
        m = self.market
        rows = m.candles(symbol, "1m", 390)
        start = m.session_start_ms() if hasattr(m, "session_start_ms") else None
        if start:
            today = [r for r in rows if r[0] >= start]
            rows = today if len(today) >= 20 else rows[-120:]
        closes = [r[4] for r in rows]
        e9, e20 = ema_series(closes, 9), ema_series(closes, 20)
        vw, pv, vv = [], 0.0, 0.0
        for r in rows:
            pv += (r[2] + r[3] + r[4]) / 3 * r[5]
            vv += r[5]
            vw.append(pv / vv if vv else None)
        t = [et_seconds(r[0]) for r in rows]
        markers = []
        for e in self.tb.journal.tail(400, {"open", "close", "sell_partial"}):
            if e.get("symbol") != symbol:
                continue
            ms = datetime.fromisoformat(e["ts"].replace("Z", "+00:00")).timestamp() * 1000
            mt = et_seconds(ms // 60000 * 60000)
            if e["event"] == "open":
                markers.append({"time": mt, "position": "belowBar", "color": "#22c55e", "shape": "arrowUp",
                                "text": f"BUY {e.get('price', 0):.2f}"})
            else:
                pnl = e.get("pnl_usd", 0) or 0
                markers.append({"time": mt, "position": "aboveBar",
                                "color": "#f59e0b" if e["event"] == "sell_partial" else "#ef4444",
                                "shape": "arrowDown",
                                "text": f"{'HALF' if e['event'] == 'sell_partial' else 'SELL'} "
                                        f"{e.get('exit_price', 0):.2f} {pnl:+.0f}"})
        markers.sort(key=lambda x: x["time"])
        pos = self.tb.broker.positions.get(symbol)
        lines = []
        if pos:
            lines.append({"price": pos.entry_price, "color": "#60a5fa", "title": "entry"})
            if pos.stop_loss:
                lines.append({"price": pos.stop_loss, "color": "#ef4444", "title": "stop"})
            if pos.take_profit:
                lines.append({"price": pos.take_profit, "color": "#22c55e", "title": "target"})
        return {
            "symbol": symbol,
            "candles": [{"time": t[i], "open": r[1], "high": r[2], "low": r[3], "close": r[4]}
                        for i, r in enumerate(rows)],
            "volume": [{"time": t[i], "value": r[5], "color": "#22c55e55" if r[4] >= r[1] else "#ef444455"}
                       for i, r in enumerate(rows)],
            "ema9": [{"time": t[i], "value": v} for i, v in enumerate(e9) if v is not None],
            "ema20": [{"time": t[i], "value": v} for i, v in enumerate(e20) if v is not None],
            "vwap": [{"time": t[i], "value": v} for i, v in enumerate(vw) if v is not None],
            "markers": markers,
            "lines": lines,
        }

    # -- server ---------------------------------------------------------------
    def start(self) -> None:
        dash = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):  # keep the trading log clean
                pass

            def _send(self, code, body, ctype="application/json"):
                data = body if isinstance(body, bytes) else body.encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                u = urlparse(self.path)
                q = parse_qs(u.query)
                if not secrets.compare_digest((q.get("token") or [""])[0], dash.token):
                    return self._send(403, "Forbidden: open the link with ?token=…", "text/plain")
                try:
                    if u.path == "/":
                        return self._send(200, PAGE, "text/html; charset=utf-8")
                    if u.path == "/api/state":
                        with dash._lock:
                            return self._send(200, json.dumps(dash.state(), default=str))
                    if u.path == "/api/candles":
                        sym = (q.get("symbol") or [""])[0].upper()
                        with dash._lock:
                            return self._send(200, json.dumps(dash.candles(sym), default=str))
                    return self._send(404, "not found", "text/plain")
                except Exception as e:
                    log.debug("dashboard error: %s", e)
                    return self._send(500, json.dumps({"error": str(e)}))

        srv = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True, name="dashboard").start()
        log.info("Dashboard on port %s", self.port)


def _describe(e: dict) -> dict:
    ev, t = e["event"], e["ts"][11:16]
    try:
        hhmm = datetime.fromisoformat(e["ts"].replace("Z", "+00:00")).astimezone(ET).strftime("%H:%M")
    except Exception:
        hhmm = t
    text, kind = ev, "info"
    if ev == "open":
        text, kind = f"BUY {e['symbol']} {e.get('qty', 0):.0f} @ {e.get('price', 0):.2f} · stop {e.get('stop')}", "buy"
    elif ev in ("close", "sell_partial"):
        pnl = e.get("trade_total_pnl_usd", e.get("pnl_usd", 0)) or 0
        text = (f"{'SOLD HALF' if ev == 'sell_partial' else 'SOLD'} {e['symbol']} @ {e.get('exit_price', 0):.2f} "
                f"({pnl:+.2f}) · {e.get('reason', '')}")
        kind = "win" if pnl >= 0 else "loss"
    elif ev == "watchlist":
        text = "watching " + (", ".join(e.get("symbols") or []) or "nothing")
    elif ev == "scan":
        text = f"scan: {len(e.get('passing') or [])} passing ({', '.join((e.get('passing') or [])[:5])})"
    elif ev == "setup_alert":
        text, kind = f"setup triggered on {e['symbol']}", "alert"
    elif ev == "order_rejected":
        text, kind = f"order refused {e.get('symbol')}: {e.get('why')}", "warn"
    elif ev == "halt":
        text, kind = f"done for the day: {e.get('reason')}", "warn"
    elif ev == "cycle_summary":
        text = e.get("summary") or ""
    elif ev == "update_stops":
        text = f"{e['symbol']} stop → {e.get('stop')} ({e.get('reason', '')})"
    elif ev == "error":
        text, kind = e.get("message", "error"), "warn"
    return {"t": hhmm, "text": text, "kind": kind}


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trading Agent Live</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{--bg:#0b0f14;--panel:#121821;--line:#1f2a37;--text:#e5e7eb;--mute:#8b98a9;--green:#22c55e;--red:#ef4444;--amber:#f59e0b;--blue:#60a5fa}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.4 -apple-system,system-ui,Segoe UI,Roboto,sans-serif}
header{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline;padding:12px 16px;border-bottom:1px solid var(--line)}
header h1{font-size:16px;margin:0}.mute{color:var(--mute)}.big{font-size:20px;font-weight:600}
.pos{color:var(--green)}.neg{color:var(--red)}
.tabs{display:flex;gap:6px;overflow-x:auto;padding:10px 16px}
.tab{padding:6px 12px;border-radius:999px;background:var(--panel);border:1px solid var(--line);color:var(--text);white-space:nowrap;cursor:pointer}
.tab.on{background:var(--blue);color:#06101f;border-color:var(--blue);font-weight:600}
#chart{height:52vh;min-height:300px;margin:0 8px}
.legend{padding:4px 16px;font-size:12px}.legend span{margin-right:12px}
.grid{display:grid;grid-template-columns:1fr;gap:12px;padding:12px 16px}
@media(min-width:900px){.grid{grid-template-columns:1fr 1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px}
.card h2{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);margin:0 0 8px}
.row{display:flex;justify-content:space-between;gap:8px;padding:4px 0;border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:0}
.ev{display:flex;gap:8px;padding:3px 0}.ev .t{color:var(--mute);min-width:42px}
.ev.buy .x{color:var(--blue)}.ev.win .x{color:var(--green)}.ev.loss .x{color:var(--red)}.ev.warn .x{color:var(--amber)}.ev.alert .x{color:#c084fc}
.badge{font-size:12px;padding:2px 8px;border-radius:999px;background:var(--line)}
#empty{padding:40px 16px;text-align:center}
</style></head><body>
<header>
  <h1>Trading Agent</h1><span class="mute" id="mode"></span><span class="mute" id="now"></span>
  <span style="flex:1"></span>
  <span>Equity <span class="big" id="eq">–</span></span>
  <span>Today <span class="big" id="pnl">–</span></span>
  <span class="badge" id="status"></span>
</header>
<div class="tabs" id="tabs"></div>
<div id="empty" class="mute" hidden>Nothing to show yet. The agent picks stocks from 7:00 AM ET.</div>
<div id="chart"></div>
<div class="legend mute"><span style="color:#e5e7eb">━ 9 EMA</span><span style="color:#60a5fa">━ 20 EMA</span><span style="color:#f59e0b">┅ VWAP</span><span style="color:var(--green)">▲ buy</span><span style="color:var(--red)">▼ sell</span></div>
<div class="grid">
  <div class="card"><h2>Positions</h2><div id="positions" class="mute">none</div></div>
  <div class="card"><h2>Scanner <span id="temp" class="badge"></span></h2><div id="cands" class="mute">–</div></div>
  <div class="card" style="grid-column:1/-1"><h2>Activity</h2><div id="events" class="mute">–</div></div>
</div>
<script>
const token=new URLSearchParams(location.search).get('token');
const api=(p)=>fetch(p+(p.includes('?')?'&':'?')+'token='+encodeURIComponent(token)).then(r=>r.json());
const fmt=(n,d=2)=>n==null?'–':Number(n).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d});
let sym=null,chart,cs,vs,e9,e20,vw,plines=[];
function initChart(){
  const el=document.getElementById('chart');
  chart=LightweightCharts.createChart(el,{layout:{background:{color:'#0b0f14'},textColor:'#8b98a9'},
    grid:{vertLines:{color:'#111821'},horzLines:{color:'#111821'}},timeScale:{timeVisible:true,secondsVisible:false,borderColor:'#1f2a37'},
    rightPriceScale:{borderColor:'#1f2a37'},crosshair:{mode:0},width:el.clientWidth,height:el.clientHeight});
  cs=chart.addCandlestickSeries({upColor:'#22c55e',downColor:'#ef4444',borderVisible:false,wickUpColor:'#22c55e',wickDownColor:'#ef4444'});
  vs=chart.addHistogramSeries({priceScaleId:'',priceFormat:{type:'volume'}});
  chart.priceScale('').applyOptions({scaleMargins:{top:0.8,bottom:0}});
  e9=chart.addLineSeries({color:'#e5e7eb',lineWidth:1,priceLineVisible:false,lastValueVisible:false});
  e20=chart.addLineSeries({color:'#60a5fa',lineWidth:1,priceLineVisible:false,lastValueVisible:false});
  vw=chart.addLineSeries({color:'#f59e0b',lineWidth:2,lineStyle:2,priceLineVisible:false,lastValueVisible:false});
  new ResizeObserver(()=>chart.applyOptions({width:el.clientWidth,height:el.clientHeight})).observe(el);
}
let firstLoad=true;
async function loadChart(){
  if(!sym)return;
  const d=await api('/api/candles?symbol='+encodeURIComponent(sym));
  if(d.error||!d.candles)return;
  cs.setData(d.candles);vs.setData(d.volume);e9.setData(d.ema9);e20.setData(d.ema20);vw.setData(d.vwap);
  cs.setMarkers(d.markers);
  plines.forEach(l=>cs.removePriceLine(l));
  plines=d.lines.map(l=>cs.createPriceLine({price:l.price,color:l.color,lineWidth:1,lineStyle:2,axisLabelVisible:true,title:l.title}));
  if(firstLoad){chart.timeScale().fitContent();firstLoad=false;}
}
function pick(s){sym=s;firstLoad=true;renderTabs(lastSymbols);loadChart();}
let lastSymbols=[];
function renderTabs(list){
  lastSymbols=list;const t=document.getElementById('tabs');t.innerHTML='';
  list.forEach(s=>{const b=document.createElement('button');b.className='tab'+(s===sym?' on':'');b.textContent=s;b.onclick=()=>pick(s);t.appendChild(b);});
  document.getElementById('empty').hidden=list.length>0;
}
async function loadState(){
  const s=await api('/api/state');
  document.getElementById('mode').textContent=s.mode;document.getElementById('now').textContent=s.now_et;
  document.getElementById('eq').textContent='$'+fmt(s.equity);
  const p=document.getElementById('pnl');p.textContent=(s.day_pnl>=0?'+$':'-$')+fmt(Math.abs(s.day_pnl||0))+' ('+fmt(s.day_pnl_pct)+'%)';
  p.className='big '+(s.day_pnl>0?'pos':s.day_pnl<0?'neg':'');
  document.getElementById('status').textContent=s.blocked?('paused: '+s.blocked.slice(0,60)):(s.in_window?'trading window open':'waiting');
  if(!sym&&s.symbols.length)sym=s.symbols[0];
  if(JSON.stringify(s.symbols)!==JSON.stringify(lastSymbols))renderTabs(s.symbols);
  document.getElementById('positions').innerHTML=s.positions.length?s.positions.map(x=>
    `<div class="row"><b>${x.symbol}</b><span>${fmt(x.qty,0)} @ ${fmt(x.entry)} → ${fmt(x.price)}</span><span class="${x.pnl>=0?'pos':'neg'}">${x.pnl>=0?'+':''}${fmt(x.pnl)}</span></div>`+
    `<div class="row mute"><span>stop ${fmt(x.stop)}</span><span>target ${x.target?fmt(x.target):'riding'}</span></div>`).join(''):'<span class="mute">none</span>';
  document.getElementById('temp').textContent=s.temperature||'';
  document.getElementById('cands').innerHTML=s.candidates.length?s.candidates.map(c=>
    `<div class="row"><b style="color:${c.passes?'var(--text)':'var(--mute)'}">${c.symbol}</b><span>$${fmt(c.price)}</span><span class="pos">+${fmt(c.change_pct,1)}%</span><span class="mute">rvol ${c.rvol??'–'}</span></div>`).join(''):'<span class="mute">no scan yet</span>';
  document.getElementById('events').innerHTML=s.events.length?s.events.map(e=>
    `<div class="ev ${e.kind}"><span class="t">${e.t}</span><span class="x">${e.text.replace(/</g,'&lt;')}</span></div>`).join(''):'<span class="mute">quiet so far</span>';
}
initChart();
async function tick(){try{await loadState();await loadChart();}catch(e){console.log(e)}}
tick();setInterval(tick,5000);
</script></body></html>"""
