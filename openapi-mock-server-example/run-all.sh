#!/usr/bin/env bash
# Runs every demo from the article in order and prints the output.
# Ports: 9220 Prism mock, 9221 Mockoon, 9222 stateful mock, 9223 real API, 9224 Prism proxy.
set -u
cd "$(dirname "$0")"
BIN=./node_modules/.bin
PIDS=()

cleanup() {
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null; done
  wait 2>/dev/null
}
trap cleanup EXIT

start() { # start <port> <command...>
  local port=$1; shift
  "$@" > "logs/$port.log" 2>&1 &
  PIDS+=($!)
  for _ in $(seq 1 60); do
    curl -s -o /dev/null "http://127.0.0.1:$port/" && return 0
    sleep 0.5
  done
  echo "server on port $port did not start"; cat "logs/$port.log"; exit 1
}

stop_all() { cleanup; PIDS=(); }

step() { echo; echo "===== $*"; }
run() { echo "\$ $*"; eval "$@"; echo; }

mkdir -p logs
JSON='Content-Type: application/json'
GOOD='{"currency":"EUR","items":[{"sku":"PEN-BLUE-7","quantity":3}]}'
BAD='{"currency":"usd","items":[{"sku":"PEN-BLUE-7","quantity":0}],"coupon":"X"}'

step "1. Prism static mock"
start 9220 $BIN/prism mock openapi.yaml --port 9220
run "curl -s http://127.0.0.1:9220/orders/ord_1001"
run "curl -s http://127.0.0.1:9220/orders/ord_7777"
run "curl -s http://127.0.0.1:9220/orders/ord_1001 -H 'Prefer: example=shipped'"
run "curl -s -i -X POST http://127.0.0.1:9220/orders -H '$JSON' -d '$GOOD'"
run "curl -s -i -X POST http://127.0.0.1:9220/orders -H '$JSON' -d '$BAD'"
run "curl -s http://127.0.0.1:9220/orders/abc"
run "curl -s http://127.0.0.1:9220/customers"
run "curl -s http://127.0.0.1:9220/orders/ord_1001 -H 'Prefer: dynamic=true'"
stop_all

step "2. Prism dynamic mock with a seed, before and after a restart"
start 9220 $BIN/prism mock openapi.yaml --port 9220 --dynamic --seed orders
run "curl -s http://127.0.0.1:9220/orders/ord_1001"
stop_all
echo "(Prism restarted with the same command)"
start 9220 $BIN/prism mock openapi.yaml --port 9220 --dynamic --seed orders
run "curl -s http://127.0.0.1:9220/orders/ord_1001"
stop_all

step "3. Mockoon CLI started from the OpenAPI file"
start 9221 $BIN/mockoon-cli start --data openapi.yaml --port 9221 -X
run "curl -s http://127.0.0.1:9221/orders/ord_1001"
run "curl -s -i -X POST http://127.0.0.1:9221/orders -H '$JSON' -d '$BAD'"
stop_all
run "$BIN/mockoon-cli import --input openapi.yaml --output logs/mockoon-orders.json > /dev/null"
run "node list-mockoon-routes.js logs/mockoon-orders.json"

step "4. Stateful mock (openapi-backend)"
start 9222 node stateful-mock.js
run "curl -s -i -X POST http://127.0.0.1:9222/orders -H '$JSON' -d '$GOOD'"
run "curl -s http://127.0.0.1:9222/orders/ord_1003"
run "curl -s http://127.0.0.1:9222/orders/ord_1004"
run "curl -s 'http://127.0.0.1:9222/orders?status=pending'"
run "curl -s -X POST http://127.0.0.1:9222/orders -H '$JSON' -d '$BAD'"
run "curl -s -i -X DELETE http://127.0.0.1:9222/orders"
stop_all

step "5. Consumer tests against the stateful mock and against Prism"
start 9222 node stateful-mock.js
start 9220 $BIN/prism mock openapi.yaml --port 9220
run "BASE_URL=http://127.0.0.1:9222 node --test --test-reporter=tap consumer.test.js"
run "BASE_URL=http://127.0.0.1:9220 node --test --test-reporter=tap consumer.test.js"
stop_all

step "6. Prism validation proxy in front of the real API (with bugs)"
start 9223 node real-api.js
start 9224 $BIN/prism proxy openapi.yaml http://127.0.0.1:9223 --port 9224
run "curl -s -i http://127.0.0.1:9224/orders/ord_1001"
run "node contract-check.js; echo \"exit code: \$?\""
stop_all

step "7. Prism proxy with --errors"
start 9223 node real-api.js
start 9224 $BIN/prism proxy openapi.yaml http://127.0.0.1:9223 --port 9224 --errors
run "curl -s -i http://127.0.0.1:9224/orders/ord_1001"
stop_all

step "8. Contract check after the fix (real API started with FIXED=1)"
start 9223 env FIXED=1 node real-api.js
start 9224 $BIN/prism proxy openapi.yaml http://127.0.0.1:9223 --port 9224
run "node contract-check.js; echo \"exit code: \$?\""
stop_all
