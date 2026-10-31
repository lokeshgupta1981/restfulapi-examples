#!/usr/bin/env bash
# Runs matrix.py, the curl demo against each model, the AuthZEN demo and the tests.
# Ports are configurable: API_PORT (default 8000) and PDP_PORT (default 8001).
set -u
cd "$(dirname "$0")"
API_PORT=${API_PORT:-8000}
PDP_PORT=${PDP_PORT:-8001}

wait_for() { for _ in $(seq 50); do curl -s -o /dev/null "$1" && return 0; sleep 0.1; done; }

echo "## python matrix.py"
python matrix.py
echo

PDP_MODEL=hybrid uvicorn pdp:app --port "$PDP_PORT" --log-level warning & PDP_PID=$!
wait_for "http://127.0.0.1:$PDP_PORT/.well-known/authzen-configuration"

for model in rbac abac rebac authzen; do
  echo "## ./demo.sh with AUTHZ_MODEL=$model"
  AUTHZ_MODEL=$model PDP_URL="http://127.0.0.1:$PDP_PORT" \
    uvicorn app:app --port "$API_PORT" --log-level warning & API_PID=$!
  wait_for "http://127.0.0.1:$API_PORT/docs"
  BASE="http://127.0.0.1:$API_PORT" ./demo.sh
  kill "$API_PID"; wait "$API_PID" 2>/dev/null
done

echo "## ./pdp_demo.sh (PDP_MODEL=hybrid)"
PDP="http://127.0.0.1:$PDP_PORT" ./pdp_demo.sh
kill "$PDP_PID"; wait "$PDP_PID" 2>/dev/null

echo "## pytest -q"
python -m pytest -q
