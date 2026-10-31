#!/usr/bin/env bash
# Starts issuer.py and orders_api.py, runs every demo, stops the servers.
set -e
cd "$(dirname "$0")"
PY=${PY:-.venv/bin/python}
ISSUER_PORT=${ISSUER_PORT:-8000}
API_PORT=${API_PORT:-8001}
export PY ISSUER_URL="http://127.0.0.1:$ISSUER_PORT" API_URL="http://127.0.0.1:$API_PORT"
# A fresh 256-bit HS256 secret for this run, shared by the issuer and the Orders API.
export HS256_SECRET=$($PY -c 'import secrets;print(secrets.token_hex(32))')

$PY -m uvicorn issuer:app --port "$ISSUER_PORT" --no-access-log --log-level warning &
P1=$!
$PY -m uvicorn orders_api:app --port "$API_PORT" --no-access-log --log-level warning &
P2=$!
trap 'kill $P1 $P2' EXIT
for port in "$ISSUER_PORT" "$API_PORT"; do
  until curl -s -o /dev/null "http://127.0.0.1:$port/docs"; do sleep 0.5; done
done

echo "######## anatomy.py";    $PY anatomy.py
echo; echo "######## failures.py"; $PY failures.py 2>&1
echo; echo "######## confusion.py"; $PY confusion.py
echo; echo "######## curl_demo.sh"; ./curl_demo.sh
echo; echo "######## bench.py";     $PY bench.py
