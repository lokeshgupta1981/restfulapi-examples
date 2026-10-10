#!/usr/bin/env bash
# Runs the same requests over stdio and Streamable HTTP, then the HTTP error cases.
set -u
PY=${PYTHON:-python3}
echo "== stdio =="
echo "\$ python client.py stdio"
$PY client.py stdio
echo
$PY -m uvicorn http_server:app --host 127.0.0.1 --port 8000 --log-level warning &
S=$!
for i in $(seq 1 50); do curl -s -o /dev/null http://127.0.0.1:8000/docs && break; sleep 0.2; done
echo "== Streamable HTTP =="
echo "\$ python client.py http"
$PY client.py http
echo
echo "\$ python client.py http-errors"
$PY client.py http-errors
kill $S; wait $S 2>/dev/null
