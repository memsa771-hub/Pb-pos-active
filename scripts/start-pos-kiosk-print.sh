#!/usr/bin/env bash
# Launch POS with silent kitchen printing (no print dialog).
# Set your kitchen thermal printer as the DEFAULT printer first.
#
# Usage:
#   ./scripts/start-pos-kiosk-print.sh
#   ./scripts/start-pos-kiosk-print.sh https://rev1.pbpos.online/pos/

POS_URL="${1:-https://rev1.pbpos.online/pos/}"

if command -v google-chrome >/dev/null 2>&1; then
  exec google-chrome --kiosk-printing --app="${POS_URL}"
fi

if command -v google-chrome-stable >/dev/null 2>&1; then
  exec google-chrome-stable --kiosk-printing --app="${POS_URL}"
fi

if command -v chromium-browser >/dev/null 2>&1; then
  exec chromium-browser --kiosk-printing --app="${POS_URL}"
fi

if command -v chromium >/dev/null 2>&1; then
  exec chromium --kiosk-printing --app="${POS_URL}"
fi

if command -v microsoft-edge >/dev/null 2>&1; then
  exec microsoft-edge --kiosk-printing --app="${POS_URL}"
fi

echo "Chrome/Chromium/Edge not found. Install Google Chrome, then run again."
exit 1
