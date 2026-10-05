#!/usr/bin/env bash
# curl calls that compare GET and POST through nginx (port 9121) and the app (port 9120).
set -u

# Prints a command, runs it, prints a blank line.
run() { echo "\$ $1"; eval "$1"; echo; echo; }

echo "### 1. Caching: the same GET twice, then the same POST search twice"
run 'curl -s -i "http://localhost:9121/orders?status=paid"'
run 'curl -s -i "http://localhost:9121/orders?status=paid"'
run 'curl -s -i -X POST http://localhost:9121/orders/search -H "Content-Type: application/json" -d '"'"'{"status": ["paid"]}'"'"
run 'curl -s -i -X POST http://localhost:9121/orders/search -H "Content-Type: application/json" -d '"'"'{"status": ["paid"]}'"'"
run 'curl -s http://localhost:9120/stats'

echo "### 2. Logging: a filter in the URL and the same filter in a POST body"
run 'curl -s -o /dev/null "http://localhost:9121/orders?customer_email=ana@example.com"'
run 'curl -s -o /dev/null -X POST http://localhost:9121/orders/search -H "Content-Type: application/json" -d '"'"'{"customer_email": "ana@example.com"}'"'"
run 'tail -2 nginx/logs/access.log'

echo "### 3. Idempotency: the same POST twice creates two orders"
run 'curl -s -i -X POST http://localhost:9120/orders -H "Content-Type: application/json" -d '"'"'{"customer_email": "kim@example.com", "total": 30}'"'"
run 'curl -s -i -X POST http://localhost:9120/orders -H "Content-Type: application/json" -d '"'"'{"customer_email": "kim@example.com", "total": 30}'"'"

echo "### 4. Proxy retry: the first upstream server drops the connection"
run 'curl -s -i "http://localhost:9121/pool/orders?status=paid"'
run 'curl -s -i -X POST http://localhost:9121/pool/orders -H "Content-Type: application/json" -d '"'"'{"customer_email": "kim@example.com", "total": 30}'"'"
run 'tail -2 nginx/logs/error.log'
run 'curl -s http://localhost:9120/stats'
