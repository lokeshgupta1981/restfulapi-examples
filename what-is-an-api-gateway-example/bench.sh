#!/usr/bin/env bash
# Starts the books service, the gateway (with a high partner limit) and, if installed,
# a plain nginx reverse proxy, then runs bench.py.
set -u
cd "$(dirname "$0")"
GW=${GATEWAY_PORT:-8000}; BP=${BOOKS_PORT:-8001}; NP=${NGINX_PORT:-8080}; PY=${PYTHON:-python3}
mkdir -p logs
SERVICE=books $PY -m uvicorn services:app --port "$BP" --log-level warning & P1=$!
PARTNER_LIMIT=1000000 BOOKS_URL=http://127.0.0.1:$BP \
  $PY -m uvicorn gateway:app --port "$GW" --log-level warning > /dev/null & P2=$!
trap 'kill $P1 $P2 2>/dev/null; wait $P1 $P2 2>/dev/null; [ -f logs/nginx.conf ] && nginx -p "$PWD" -c "$PWD/logs/nginx.conf" -s stop 2>/dev/null' EXIT
if command -v nginx > /dev/null; then
  sed "s/BOOKS_PORT/$BP/; s/NGINX_PORT/$NP/" nginx-bench.conf.template > logs/nginx.conf
  sed -i "s#^pid nginx.pid;#pid $PWD/logs/nginx.pid;#" logs/nginx.conf
  nginx -p "$PWD" -c "$PWD/logs/nginx.conf" && export NGINX_PORT=$NP
fi
for p in $BP $GW; do until curl -s -o /dev/null "http://127.0.0.1:$p/docs"; do sleep 0.2; done; done
GATEWAY_PORT=$GW BOOKS_PORT=$BP $PY bench.py "${1:-2000}"
