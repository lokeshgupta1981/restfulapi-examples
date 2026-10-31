#!/usr/bin/env bash
# Starts all servers, runs every demo, stops the servers.
set -u
cd "$(dirname "$0")"

./start.sh
echo "### 0. On the wire: one GET and one POST, byte by byte"
echo "\$ python wire.py"; .venv/bin/python wire.py
# Restart so the demos below start from the four seed orders and zero counters.
./stop.sh
sleep 1
./start.sh

./demo.sh
echo "### 5. Client retry with urllib3"
echo "\$ python retry_client.py"; .venv/bin/python retry_client.py; echo
echo "### 6. fetch() and a GET body"
echo "\$ node get_body.mjs"; node get_body.mjs; echo
echo "\$ curl -s -X GET http://localhost:9120/orders -H \"Content-Type: application/json\" -d '{\"status\": [\"paid\"]}'"
curl -s -X GET http://localhost:9120/orders -H "Content-Type: application/json" -d '{"status": ["paid"]}'; echo; echo
echo "### 7. CSRF with a SameSite=Lax cookie"
echo "\$ python csrf_demo.py"; .venv/bin/python csrf_demo.py

./stop.sh
sleep 1
