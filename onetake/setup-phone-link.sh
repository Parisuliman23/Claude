#!/usr/bin/env bash
# One-time setup of a PERMANENT phone link for One Take (same address every time; add it to your phone's home screen).
# Uses Tailscale Funnel (free, no upload limit). Run in the Linux terminal:  bash setup-phone-link.sh
# You'll be asked to sign in to Tailscale once (with Google is fine) and, the first time, to allow "Funnel".
set -e
cd "$(dirname "$0")"
if ! command -v tailscale >/dev/null; then
  echo "== Installing Tailscale (needs your Linux password if it asks)"
  curl -fsSL https://tailscale.com/install.sh | sh
fi
sudo systemctl enable --now tailscaled >/dev/null 2>&1 || true
if ! tailscale status >/dev/null 2>&1; then
  echo "== Sign in to Tailscale: open the link below, sign in, then come back here"
  sudo tailscale up
fi
sudo tailscale set --operator="$USER"          # lets the studio turn the link on/off without sudo
python3 -m engine phone-link permanent
echo "== Allowing Funnel (if a link appears, open it and press Enable, then run this script again)"
tailscale funnel --bg "http://127.0.0.1:$(python3 -c 'from engine import tunnel; print(tunnel.remote_port())')"
HOST=$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')
pkill -f "engine open" 2>/dev/null || true; sleep 2   # restart the studio with the permanent link
if ! python3 -m engine autostart on | grep -q "now starts"; then  # also starts it now
  nohup python3 -m engine open --no-browser > projects/.studio.log 2>&1 &
fi
echo
echo "Your permanent phone link:  https://$HOST/phone"
echo "Open it on your phone, enter your PIN once, then browser menu -> Add to Home screen."
python3 -m engine phone-link
