#!/usr/bin/env bash
# Mac: double-click to open One Take Studio (starts it if it isn't running).
cd "$(dirname "$0")"
PY=.venv/bin/python; [ -x "$PY" ] || PY=python3
PORT=$("$PY" -c "from engine import config; print(config.settings()['port'])" 2>/dev/null || echo 5178)
if ! "$PY" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$PORT/api/status', timeout=1)" 2>/dev/null; then
  mkdir -p projects
  nohup "$PY" -m engine open --no-browser > projects/.studio.log 2>&1 &
  for i in $(seq 1 30); do "$PY" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$PORT/api/status', timeout=1)" 2>/dev/null && break; sleep 0.5; done
fi
open "http://localhost:$PORT/"
