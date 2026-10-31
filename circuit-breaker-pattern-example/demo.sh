#!/usr/bin/env bash
# Starts the inventory API and the bookstore API, then walks through every circuit breaker state.
set -u
cd "$(dirname "$0")"
PY=${PY:-.venv/bin/python}
mkdir -p logs
STORE=http://127.0.0.1:9600
INV=http://127.0.0.1:9601

section() { echo; echo "===== $1"; }
mode() { curl -s -X POST "$INV/admin/mode?mode=$1" > /dev/null; echo "[inventory mode: $1]"; }
timed() { curl -sS -w "  [%{http_code}, %{time_total} s]\n" "$@"; }
store_log() { echo "--- store log:"; grep -E "^(breaker|store:)" logs/store.log | tail -n "${1:-20}"; }

start_store() {
  pkill -f "uvicorn store_api:app" 2>/dev/null; sleep 1
  env "$@" "$PY" -m uvicorn store_api:app --host 127.0.0.1 --port 9600 > logs/store.log 2>&1 &
  sleep 2
}

pkill -f "uvicorn inventory_service:app" 2>/dev/null
"$PY" -m uvicorn inventory_service:app --host 127.0.0.1 --port 9601 > logs/inventory.log 2>&1 &
sleep 2
start_store BREAKER=on OPEN_SECONDS=10

section "1. Inventory healthy: the breaker is CLOSED and calls go through"
curl -sS -i "$STORE/books/1"; echo
timed "$STORE/admin/breaker"

section "2. Inventory down: 5 failures open the breaker, then calls are rejected at once"
curl -s -X POST "$INV/admin/reset" > /dev/null
mode down
for i in 1 2 3 4 5 6 7 8; do
  printf "request %s: " "$i"; timed "$STORE/books/1"
done
echo "inventory API received: $(curl -s "$INV/admin/stats")"
timed "$STORE/admin/breaker"
store_log 1

section "3. POST /orders while the breaker is OPEN"
curl -sS -i -X POST "$STORE/orders?book_id=1"; echo

section "4. Trial call fails: HALF_OPEN goes back to OPEN"
echo "waiting for the 10 s open period to end..."; sleep 10
timed "$STORE/books/1"
timed "$STORE/admin/breaker"
store_log 2

section "5. Inventory recovers: the trial call succeeds and the breaker closes"
mode healthy
timed "$STORE/books/1"
echo "waiting for the 10 s open period to end..."; sleep 10
timed "$STORE/books/1"
timed "$STORE/admin/breaker"
store_log 2

section "6. Inventory slow (5 s), store timeout 2 s, 50 requests 10 at a time, NO breaker"
start_store BREAKER=off
mode slow
"$PY" load_test.py 50 10

section "7. Same load WITH the breaker (threshold 5, open 10 s)"
start_store BREAKER=on OPEN_SECONDS=10
"$PY" load_test.py 50 10
store_log 2

section "8. The same inventory call with the opossum library (Node.js)"
if [ -d node/node_modules ]; then
  (cd node && node opossum_demo.js)
else
  echo "skipped: run 'npm install' in node/ first"
fi

mode healthy
pkill -f "uvicorn store_api:app"; pkill -f "uvicorn inventory_service:app"
