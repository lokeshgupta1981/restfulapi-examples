#!/usr/bin/env bash
# Starts the three demo servers, runs the comparison, stops the servers.
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python
export CACHE_TTL=10

$PY -m uvicorn auth_server:app --port 9400 --no-access-log --log-level warning &
P1=$!
$PY -m uvicorn orders_api:app --port 9401 --no-access-log --log-level warning &
P2=$!
$PY -m uvicorn gateway:app --port 9402 --no-access-log --log-level warning &
P3=$!
trap 'kill $P1 $P2 $P3' EXIT
# Wait until all three servers answer.
for port in 9400 9401 9402; do
  until curl -s -o /dev/null "http://127.0.0.1:$port/docs"; do sleep 0.5; done
done

./curl_demo.sh
$PY bench.py
