#!/usr/bin/env bash
# Runs every script and prints the output (used to produce OUTPUTS.txt).
set -e
cd "$(dirname "$0")"
rm -f orders.db
uvicorn app:app --port 8000 > /dev/null 2>&1 &
SERVER=$!
trap 'kill $SERVER' EXIT
sleep 2

echo "########## ./demo.sh"; ./demo.sh
echo "########## first page with headers"
echo '$ curl -s -i "http://localhost:8000/orders?limit=3"'
curl -s -X POST http://localhost:8000/_reset
curl -s -i "http://localhost:8000/orders?limit=3" | grep -v -i -E '^(date|server):'
echo; echo
echo "########## python client.py"; python3 client.py; echo
echo "########## python tie_breaker.py"; python3 tie_breaker.py; echo
echo "########## python bench.py"; python3 bench.py
rm -f bench.db
