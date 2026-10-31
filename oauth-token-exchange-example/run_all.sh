#!/usr/bin/env bash
# Starts the three servers, runs demo.py and curl_demo.sh, then stops the servers.
# Ports: BASE_PORT (default 8000) for the authorization server, +1 Orders API, +2 Payments API.
set -euo pipefail
cd "$(dirname "$0")"
BASE_PORT=${BASE_PORT:-8000}
export AUTH_URL="http://127.0.0.1:$BASE_PORT"
export ORDERS_URL="http://127.0.0.1:$((BASE_PORT + 1))"
export PAYMENTS_URL="http://127.0.0.1:$((BASE_PORT + 2))"
PY=${PYTHON:-python3}

$PY -m uvicorn auth_server:app --port "$BASE_PORT" --log-level warning & P1=$!
$PY -m uvicorn orders_api:app --port "$((BASE_PORT + 1))" --log-level warning & P2=$!
$PY -m uvicorn payments_api:app --port "$((BASE_PORT + 2))" --log-level warning & P3=$!
trap 'kill $P1 $P2 $P3 2>/dev/null' EXIT
sleep 3

$PY demo.py
./curl_demo.sh
