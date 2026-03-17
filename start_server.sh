#!/usr/bin/env bash
cd "$(dirname "$0")"
WORKDIR=$(pwd)
cd "$WORKDIR"
echo "Activate a Python venv and run:"
if [ -f "./venv_new/bin/python3" ]; then
  echo "Using optimized venv_new..."
  ./venv_new/bin/python3 -m uvicorn server.api:app --reload --host 0.0.0.0 --port 8000
else
  python3 -m uvicorn server.api:app --reload --host 0.0.0.0 --port 8000
fi
