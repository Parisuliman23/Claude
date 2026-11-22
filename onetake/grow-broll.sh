#!/usr/bin/env bash
# Weekly: Claude grows the checked B-roll library in Google Drive (One Take/B-roll Library) on its own.
# Run by the systemd user timer onetake-broll.timer (Sunday evenings); safe to run by hand too.
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
export PATH="$HOME/.local/bin:/usr/bin:$PATH"
LOG=projects/.grow-broll.log
# don't compete with a reel being edited or rendered (the Chromebook has little memory)
if grep -q '"running"' projects/.newreel.json 2>/dev/null; then echo "$(date) skipped: a reel is being edited" >> "$LOG"; exit 0; fi
FREE_MB=$(df -Pm "$HOME" | awk 'NR==2{print $4}')
if [ "${FREE_MB:-0}" -lt 2500 ]; then echo "$(date) skipped: only ${FREE_MB} MB free" >> "$LOG"; exit 0; fi
PROMPT="Grow the user's B-roll library (One Take, see CLAUDE.md and lookbook/style/09-broll-relevance.md). Nobody is here to
answer questions; decide yourself. Work in this order and keep it small (the Chromebook has little disk and memory):
1. Run 'python3 -m engine broll-cloud status' and 'python3 -m engine broll-index' to see what exists.
2. Pick 4 topics the library is weakest on from this list (finance creator: stocks, AI, chips): stock market / trading
   floor; red market crash screen; green rising stock chart screen; AI data center / GPU racks; chip clean room / wafer;
   bank / Federal Reserve; cash / paying bills / debt; real estate / houses; inflation / grocery prices; big tech HQs
   (Apple, Microsoft, Amazon, Google, Tesla, NVIDIA); famous CEOs and investors (Jensen Huang, Elon Musk, Tim Cook,
   Satya Nadella, Warren Buffett, Jerome Powell); oil / energy; crypto / bitcoin; electric cars; smartphones.
3. For each topic: 'python3 -m engine broll-find \"<what is literally on screen>\" --n 2' for footage and/or
   'python3 -m engine commons-find \"<exact company / person / place>\" --n 2' for real photos.
4. Look at EVERY new file: 'python3 -m engine broll-check <files>' then Read the sheet (photos: Read the image).
   Keep only files that clearly show the topic. Delete the rest with rm (only files you downloaded in this run).
5. Describe each kept file: 'python3 -m engine broll-describe <file> --json {\"shows\":...,\"use_for\":[...],\"not_for\":[...]}'
   (photos: add it to library/images/index.json the same way, same fields).
6. Move them to the cloud: 'python3 -m engine broll-cloud push <files>'.
7. Finish with one line per topic: what you added."
if command -v claude >/dev/null 2>&1; then
  echo "=== $(date)" >> "$LOG"
  CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 timeout 45m claude -p "$PROMPT" --model sonnet --permission-mode acceptEdits \
    --allowedTools "Bash(python3 -m engine:*)" "Bash(rm library/broll/pixabay-*)" "Bash(rm library/images/commons-*)" "Bash(ls:*)" Read Edit >> "$LOG" 2>&1
fi
