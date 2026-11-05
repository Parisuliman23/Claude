#!/usr/bin/env bash
# Adds "One Take Studio" and "One Take – New reel" to your app launcher
# (Chromebook Linux and most Linux desktops). Run once: bash install-launcher.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APPS="$HOME/.local/share/applications"
mkdir -p "$APPS"
chmod +x "$DIR/studio.sh" "$DIR/new-reel.sh"
cat > "$APPS/onetake-studio.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=One Take Studio
Comment=Open your reels studio in the browser
Exec=$DIR/studio.sh
Icon=$DIR/assets/icon.png
Terminal=false
Categories=AudioVideo;Video;
DESK
cat > "$APPS/onetake-new-reel.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=One Take – New reel
Comment=Have Claude edit the clips in drop-in-order
Exec=$DIR/new-reel.sh
Icon=$DIR/assets/icon.png
Terminal=false
Categories=AudioVideo;Video;
DESK
echo "Added. Look for 'One Take Studio' and 'One Take – New reel' in your app launcher"
echo "(on a Chromebook: the Linux apps folder). Tip: right-click one and pin it to the shelf."
