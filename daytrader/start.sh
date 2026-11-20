#!/usr/bin/env bash
# Start the trading agent for the morning. Usage: ./start.sh   (or ./start.sh scan / status / flatten)
cd "$(dirname "$0")"
source .venv/bin/activate
python -m trader.main "${1:-run}"
