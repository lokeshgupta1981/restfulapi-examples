#!/usr/bin/env bash
# Measures the API straight on port 9200, first with Nagle's algorithm left on,
# then with it off (the default in server.py). Run ./demo.sh once first, so
# cert.pem exists.
set -euo pipefail
cd "$(dirname "$0")"

echo "== Nagle left on (python3 server.py --tls --keep-nagle), straight to the API, 200 requests"
python3 server.py --tls --keep-nagle &
SERVER_PID=$!
sleep 1
python3 measure.py --url https://localhost:9200/orders/42 -n 200
kill $SERVER_PID
sleep 0.5

echo "== Nagle off (python3 server.py --tls), straight to the API, 200 requests"
python3 server.py --tls &
SERVER_PID=$!
sleep 1
python3 measure.py --url https://localhost:9200/orders/42 -n 200
kill $SERVER_PID
