#!/usr/bin/env bash
# Starts the server, runs the client, stops the server.
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
$PY -m uvicorn server:app --host 127.0.0.1 --port 8000 --log-level warning &
SERVER_PID=$!
for i in $(seq 1 50); do
  curl -s -o /dev/null http://127.0.0.1:8000/docs && break
  sleep 0.2
done
$PY client.py
kill $SERVER_PID
