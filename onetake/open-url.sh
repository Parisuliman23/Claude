#!/usr/bin/env bash
# Opens a link in your normal browser. On a Chromebook, Linux apps hand links to Chrome through
# "garcon-url-handler"; elsewhere xdg-open (Linux) or open (Mac) does it.
URL="$1"
for c in garcon-url-handler /usr/bin/garcon-url-handler xdg-open sensible-browser x-www-browser open; do
  if command -v "$c" >/dev/null 2>&1; then "$c" "$URL" >/dev/null 2>&1 && exit 0; fi
done
python3 -m webbrowser -t "$URL" >/dev/null 2>&1
