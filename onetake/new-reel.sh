#!/usr/bin/env bash
# Starts Claude and asks it to edit the clips in drop-in-order/.
cd "$(dirname "$0")"
[ -f .venv/bin/activate ] && source .venv/bin/activate
export PATH="$HOME/.local/bin:$PATH"
exec claude "I have a new reel to edit"
