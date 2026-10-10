#!/usr/bin/env bash
# Starts the facilitator (port 8001) and the API server (port 8000), runs the client, stops both.
PY=${PYTHON:-python3}
$PY -m uvicorn facilitator:app --host 127.0.0.1 --port 8001 --log-level warning &
FAC=$!
$PY -m uvicorn server:app --host 127.0.0.1 --port 8000 --log-level warning &
API=$!
trap "kill $FAC $API" EXIT
for i in $(seq 1 20); do curl -s -o /dev/null http://127.0.0.1:8000/docs && curl -s -o /dev/null http://127.0.0.1:8001/docs && break; sleep 0.5; done
$PY client.py
echo; echo "== raw 402 responses"
curl -s -i http://127.0.0.1:8000/v1/premium/forecast | grep -v -i '^date:\|^server:' | cut -c1-120
echo
