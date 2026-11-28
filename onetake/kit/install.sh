#!/usr/bin/env bash
# One Take Studio installer for Mac and Linux. Run it once from this folder:  bash install.sh
# It installs what's missing (Python 3, FFmpeg), sets up One Take's own Python packages in .venv (nothing system-wide),
# makes the built-in sounds and offers to install Claude Code. Safe to run again.
set -e
cd "$(dirname "$0")"
say() { printf "\n\033[1m%s\033[0m\n" "$1"; }
OS="$(uname -s)"

say "1/5  Checking Python 3.10+"
PY=""
for c in python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  if [ "$OS" = "Darwin" ]; then
    command -v brew >/dev/null || { echo "Please install Homebrew first (https://brew.sh), then run this again."; exit 1; }
    brew install python@3.12; PY=python3.12
  else
    sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip; PY=python3
  fi
fi
echo "Using $($PY --version)"

say "2/5  Checking FFmpeg (video engine)"
if ! command -v ffmpeg >/dev/null 2>&1; then
  if [ "$OS" = "Darwin" ]; then
    command -v brew >/dev/null || { echo "Please install Homebrew first (https://brew.sh), then run this again."; exit 1; }
    brew install ffmpeg
  else
    sudo apt-get install -y ffmpeg
  fi
fi
ffmpeg -version | head -1

say "3/5  Installing One Take's packages (in this folder only, a few minutes)"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt

say "4/5  Setting up"
mkdir -p drop-in-order projects library/broll library/images library/gifs library/sounds lookbook/looks/custom
.venv/bin/python -m engine setup

say "5/5  Claude Code (the editor)"
if command -v claude >/dev/null 2>&1 || [ -x "$HOME/.local/bin/claude" ]; then
  echo "Claude Code is installed."
else
  printf "Claude Code isn't installed. Install it now? (needs a Claude subscription) [Y/n] "
  read -r ans
  if [ -z "$ans" ] || [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    curl -fsSL https://claude.ai/install.sh | bash
  else
    echo "Skipped. Install it later from https://claude.com/claude-code"
  fi
fi
chmod +x "Start One Take.command" studio.sh 2>/dev/null || true

say "All set!"
echo "Start the studio:  double-click 'Start One Take.command' (Mac)  or run  bash studio.sh"
echo "Edit a reel:       put your clips in drop-in-order/, open a Terminal here, run  claude"
echo "                   and say: I have a new reel to edit"
