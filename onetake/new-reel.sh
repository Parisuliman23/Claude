#!/usr/bin/env bash
# Edit the clips in drop-in-order/ with Claude.
# From a Terminal: starts Claude so you can watch and chat.
# From the app icon (no Terminal): Claude edits in the background and the studio
# opens in your browser, showing progress until the reel is ready.
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
export PATH="$HOME/.local/bin:/usr/bin:$PATH"

if [ -t 1 ] && [ -z "$ONETAKE_NO_BROWSER" ]; then
  exec claude "I have a new reel to edit"
fi

PORT=$(python3 -c "from engine import config; print(config.settings()['port'])")
URL="$(python3 -c "from engine import config; print(config.studio_url())" 2>/dev/null || echo "http://localhost:$PORT/")#newreel"
STATUS=projects/.newreel.json
LOG=projects/.newreel.log

# make sure the studio is running
if ! python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$PORT/api/status', timeout=1)" 2>/dev/null; then
  nohup python3 -m engine open --no-browser > projects/.studio.log 2>&1 &
  sleep 3
fi

if [ -z "$(ls -A drop-in-order | grep -v '^\.keep$')" ]; then
  echo "{\"status\": \"noclips\", \"started\": $(date +%s)}" > "$STATUS"
  [ -z "$ONETAKE_NO_BROWSER" ] && bash ./open-url.sh "$URL"
  exit 0
fi

if [ -z "$ONETAKE_NO_BROWSER" ] && [ -f "$STATUS" ] && grep -q '"running"' "$STATUS"; then  # already editing: just show it
  bash ./open-url.sh "$URL"
  exit 0
fi

AUTO=false; [ -n "$ONETAKE_AUTO_RENDER" ] && AUTO=true
echo "{\"status\": \"running\", \"started\": $(date +%s), \"step\": \"start\", \"step_at\": $(date +%s), \"auto_render\": $AUTO}" > "$STATUS"
[ -z "$ONETAKE_NO_BROWSER" ] && bash ./open-url.sh "$URL" &

PROMPT="I have a new reel to edit. You were started from the One Take app icon and are running in the background:
the studio is already running, so skip starting it, and there's nobody to answer questions, so make sensible
choices yourself. Finish with the short summary for the user (what you cut and styled)."
RESULT=failed
if command -v claude >/dev/null 2>&1 && claude -p "$PROMPT" --permission-mode acceptEdits \
     --allowedTools "Bash(python3 -m engine:*)" "Bash(ls:*)" Read Write Edit Glob Grep > "$LOG" 2>&1; then
  RESULT=done
fi
# Claude unavailable (not installed, usage limit…) and the clips are still waiting: do the automatic
# cut and styling without Claude so you still get a reel to work on.
if [ -n "$(ls -A drop-in-order | grep -v '^\.keep$')" ]; then
  if python3 -m engine new >> "$LOG" 2>&1; then
    NAME=$(python3 -c "from engine import project; print(project.list_projects()[0]['name'])")
    python3 -m engine sfx-auto "$NAME" >> "$LOG" 2>&1
    python3 -m engine edge-check "$NAME" --fix >> "$LOG" 2>&1
    printf "\n\n" >> "$LOG"
    echo "Claude wasn't available, so One Take made the automatic cut, captions, hook and sounds. Open it to review, or use Ask Claude later to style it further." >> "$LOG"
    RESULT=done
  fi
fi
# phone uploads: render it and put the MP4 in Google Drive "One Take/Ready"
if [ "$RESULT" = done ] && [ -n "$ONETAKE_AUTO_RENDER" ]; then
  NAME=$(python3 -c "from engine import project; print(project.list_projects()[0]['name'])")
  python3 -c "from engine import inbox; print(inbox.deliver('$NAME'))" >> "$LOG" 2>&1 || RESULT=failed
fi
echo "{\"status\": \"$RESULT\", \"ended\": $(date +%s)}" > "$STATUS"
