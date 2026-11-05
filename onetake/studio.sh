#!/usr/bin/env bash
# Opens the One Take Studio in your browser (starts it if it isn't running).
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
export PATH="$HOME/.local/bin:$PATH"  # so the studio can hand requests to Claude
exec python3 -m engine open
