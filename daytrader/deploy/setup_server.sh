#!/usr/bin/env bash
# One-time setup on a fresh Ubuntu cloud server (e.g. a DigitalOcean droplet in New York).
#   curl -fsSL https://raw.githubusercontent.com/Parisuliman23/Claude/ccr-8b9f8b8a-b5qdme/daytrader/deploy/setup_server.sh | bash
set -euo pipefail
BRANCH=ccr-8b9f8b8a-b5qdme
APP=/opt/daytrader

echo "== Installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3-venv python3-pip nano unattended-upgrades

echo "== Downloading the agent"
if [ -d "$APP/.git" ]; then git -C "$APP" pull --ff-only; else git clone -b "$BRANCH" https://github.com/Parisuliman23/Claude.git "$APP"; fi

echo "== Python packages"
cd "$APP/daytrader"
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
chmod 600 .env

echo "== Running the offline tests"
.venv/bin/python -m pytest -q tests

echo "== Installing the always-on service"
cat > /etc/systemd/system/daytrader.service <<UNIT
[Unit]
Description=Claude day-trading agent
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$APP/daytrader
ExecStart=$APP/daytrader/.venv/bin/python -m trader.main run
Restart=always
RestartSec=15
# On stop (e.g. 'systemctl stop'), give it time to finish an order
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable daytrader >/dev/null

echo
echo "Done. Next:"
echo "  1. nano $APP/daytrader/.env      (add your keys, Ctrl+O Enter Ctrl+X)"
echo "  2. cd $APP/daytrader && .venv/bin/python -m trader.main scan     (check it works)"
echo "  3. systemctl start daytrader     (runs every trading morning from now on)"
echo "  Logs:  journalctl -u daytrader -f      Stop:  systemctl stop daytrader"
