#!/bin/bash
# Saves the long-lasting Claude login (from `claude setup-token`) for One Take's background jobs:
# the Sunday B-roll routine and the studio's automatic requests. The token is typed in hidden and
# stored only in ~/.config/onetake/claude.env (private to you). It is never put in the onetake folder or on GitHub.
set -e
mkdir -p ~/.config/onetake && chmod 700 ~/.config/onetake
echo "Paste the token that 'claude setup-token' printed (it starts with sk-ant-oat), then press Enter."
echo "(Nothing shows while you paste. That's normal.)"
read -rs TOKEN
echo
case "$TOKEN" in
  sk-ant-*) ;;
  *) echo "That doesn't look like the token (it should start with sk-ant-). Nothing was saved."; exit 1 ;;
esac
umask 077
printf 'CLAUDE_CODE_OAUTH_TOKEN=%s\n' "$TOKEN" > ~/.config/onetake/claude.env
chmod 600 ~/.config/onetake/claude.env
echo "Saved. Testing it..."
if CLAUDE_CODE_OAUTH_TOKEN="$TOKEN" timeout 120 claude -p "Reply with just the word OK" 2>/dev/null | grep -qi ok; then
  echo "Works! Restarting the studio so it uses it."
  systemctl --user restart onetake-studio.service
  echo "All set. The Sunday B-roll routine and studio requests now use this login (good for 1 year)."
else
  echo "Saved, but the test didn't answer. Tell Claude in the One Take chat and it will check."
fi
