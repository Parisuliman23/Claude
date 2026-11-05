#!/usr/bin/env bash
# Opens the One Take Studio in your browser (starts it if it isn't running).
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
export PATH="$HOME/.local/bin:/usr/bin:$PATH"  # Claude + the Chromebook link opener
mkdir -p projects
PORT=$(python3 -c "from engine import config; print(config.settings()['port'])" 2>/dev/null || echo 5178)
URL="http://localhost:$PORT/"
if ! python3 -c "import urllib.request; urllib.request.urlopen('$URL'+'api/status', timeout=1)" 2>/dev/null; then
  nohup python3 -m engine open --no-browser > projects/.studio.log 2>&1 &
  for i in $(seq 1 30); do  # wait until it answers (up to ~15 s)
    python3 -c "import urllib.request; urllib.request.urlopen('$URL'+'api/status', timeout=1)" 2>/dev/null && break
    sleep 0.5
  done
fi
bash ./open-url.sh "$URL"
