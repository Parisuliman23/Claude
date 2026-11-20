#!/usr/bin/env bash
# Phone-friendly: asks for each key and saves it into .env (input is hidden).
# Press Enter on a question to keep what is already there.
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
ask() {
  local name="$1" prompt="$2" val
  read -r -s -p "$prompt (Enter = keep current): " val; echo
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
ask ANTHROPIC_API_KEY  "Anthropic API key (sk-ant-...)"
ask APCA_API_KEY_ID    "Alpaca PAPER API Key ID (PK...)"
ask APCA_API_SECRET_KEY "Alpaca PAPER Secret Key"
ask FMP_API_KEY        "FMP API key (optional)"
ask NTFY_TOPIC         "ntfy topic name (WITHOUT -cmd)"
chmod 600 .env
echo "Done. Keys are in $(pwd)/.env (only root can read it)."
