#!/usr/bin/env bash
# Starts the authorization server and two Orders API instances, runs the demos, stops them.
# Ports: AUTH_PORT (default 8000), API_PORT (8001), NONCE_API_PORT (8002).
set -e
cd "$(dirname "$0")"
AUTH_PORT=${AUTH_PORT:-8000}; API_PORT=${API_PORT:-8001}; NONCE_API_PORT=${NONCE_API_PORT:-8002}
export ISSUER="http://localhost:$AUTH_PORT"
export AUTH_URL="$ISSUER" API_URL="http://localhost:$API_PORT" NONCE_API_URL="http://localhost:$NONCE_API_PORT"
PY=${PYTHON:-python3}
$PY -m uvicorn auth_server:app --port "$AUTH_PORT" --log-level warning & P1=$!
$PY -m uvicorn orders_api:app --port "$API_PORT" --log-level warning & P2=$!
REQUIRE_NONCE=1 $PY -m uvicorn orders_api:app --port "$NONCE_API_PORT" --log-level warning & P3=$!
trap 'kill $P1 $P2 $P3 2>/dev/null' EXIT
sleep 2
$PY test_rfc_examples.py
$PY client.py
./demo.sh
$PY bench.py
