#!/usr/bin/env bash
# Phone-friendly: asks for each key and saves it into .env.
# Input is shown so pasting works in phone web consoles; the screen is cleared at the end.
# Press Enter on a question to keep what is already there.
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
ask() {
  local name="$1" prompt="$2" val
  # -e = same line editing as the normal prompt, so paste works the same way
  read -e -r -p "$prompt (Enter = keep current): " val
  [ -z "$val" ] && return
  val="$(printf '%s' "$val" | tr -d '[:space:]')"
  .venv/bin/python - "$name" "$val" <<'PY'
import sys, re, pathlib
name, val = sys.argv[1], sys.argv[2]
p = pathlib.Path(".env"); lines = p.read_text().splitlines()
for i, l in enumerate(lines):
    if re.match(rf"^{name}=", l):
        lines[i] = f"{name}={val}"; break
else:
    lines.append(f"{name}={val}")
p.write_text("\n".join(lines) + "\n")
PY
  echo "  saved $name (${val:0:4}...)"
}
# Backup mode, no questions:  set_keys.sh NAME VALUE   (e.g. set_keys.sh APCA_API_KEY_ID PK123...)
if [ $# -eq 2 ]; then
  ask_direct() { printf '%s\n' "$2" | ask "$1" "$1" >/dev/null; }
  ask_direct "$1" "$2"
  history -c 2>/dev/null || true
  clear
  echo "Saved $1=$(printf '%s' "$2" | tr -d '[:space:]' | cut -c1-4)..."
  exit 0
fi
ask ANTHROPIC_API_KEY  "Anthropic API key (sk-ant-...)"
ask APCA_API_KEY_ID    "Alpaca PAPER API Key ID (PK...)"
ask APCA_API_SECRET_KEY "Alpaca PAPER Secret Key"
ask FMP_API_KEY        "FMP API key (optional)"
ask NTFY_TOPIC         "ntfy topic name (WITHOUT -cmd)"
chmod 600 .env
clear
history -c 2>/dev/null || true
echo "Saved (only the first 4 characters shown):"
grep -E "^(ANTHROPIC_API_KEY|APCA_API_KEY_ID|APCA_API_SECRET_KEY|FMP_API_KEY|NTFY_TOPIC)=" .env | sed -E 's/=(.{0,4}).*/=\1.../'
echo "Done. Keys are in $(pwd)/.env (only root can read it)."
