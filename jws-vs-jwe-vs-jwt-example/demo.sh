#!/usr/bin/env bash
# Starts the Orders API and sends it each kind of token with curl.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-python3}
PORT=${PORT:-8000}
BASE="http://127.0.0.1:$PORT"

PORT=$PORT $PY server.py > server.log 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID' EXIT
for _ in $(seq 50); do curl -s "$BASE/docs" > /dev/null && break; sleep 0.1; done

call() {  # call <title> <path> <token-kind>
  echo "== $1"
  TOKEN=$($PY issue.py "$3")
  echo "\$ curl -i $BASE$2 -H \"Authorization: Bearer ${TOKEN:0:24}...\""
  curl -s -i "$BASE$2" -H "Authorization: Bearer $TOKEN" | grep -v -i '^date:'
  echo; echo
}

call "JWS on /jws/orders" /jws/orders jws
call "JWE on the naive /jwe-only/orders" /jwe-only/orders jwe
call "Forged JWE on the naive /jwe-only/orders" /jwe-only/orders forged-jwe
call "Nested JWT on /orders" /orders nested
call "Forged JWE on /orders" /orders forged-jwe
call "Forged nested JWT (attacker's signing key) on /orders" /orders forged-nested
call "JWS on /orders (not encrypted)" /orders jws
