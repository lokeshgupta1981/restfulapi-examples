#!/usr/bin/env bash
# Starts the three demo servers, runs the comparison, stops the servers.
set -e
cd "$(dirname "$0")"
PY=${PY:-.venv/bin/python}
export CACHE_TTL=10

$PY -m uvicorn auth_server:app --port 9400 --no-access-log --log-level warning &
P1=$!
$PY -m uvicorn orders_api:app --port 9401 --no-access-log --log-level warning &
P2=$!
$PY -m uvicorn gateway:app --port 9402 --no-access-log --log-level warning &
P3=$!
trap 'kill $P1 $P2 $P3 2>/dev/null' EXIT
# Wait until all three servers answer.
for port in 9400 9401 9402; do
  until curl -s -o /dev/null "http://127.0.0.1:$port/docs"; do sleep 0.5; done
done

./curl_demo.sh
$PY bench.py

echo
echo "== Authorization server down"
JWT=$(curl -s -u orders-app:demo-secret-key-123 -d grant_type=client_credentials \
  -d scope=orders:read -d token_format=jwt http://127.0.0.1:9400/token \
  | $PY -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s -o /dev/null -H "Authorization: Bearer $JWT" http://127.0.0.1:9401/jwt/orders  # caches the JWKS
kill $P1; wait $P1 2>/dev/null || true
echo "stopped auth_server.py"
echo "-- JWT route"
curl -si -H "Authorization: Bearer $JWT" http://127.0.0.1:9401/jwt/orders
echo
echo "-- introspection route"
curl -si -H "Authorization: Bearer $JWT" http://127.0.0.1:9401/introspect/orders
echo
