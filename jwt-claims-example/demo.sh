#!/usr/bin/env bash
# Starts the Orders API, sends every demo token to it with curl and prints the responses.
# PORT defaults to 8000.
set -euo pipefail
cd "$(dirname "$0")"
PORT="${PORT:-8000}"
BASE="http://127.0.0.1:$PORT"

python3 make_tokens.py
python3 -m uvicorn orders_api:app --port "$PORT" --log-level warning &
API_PID=$!
trap 'kill $API_PID' EXIT
for _ in $(seq 1 50); do curl -s -o /dev/null "$BASE/docs" && break; sleep 0.1; done

call() {  # call <token-name> [METHOD] [PATH]
  local name=$1 method=${2:-GET} path=${3:-/orders}
  echo "== $name: $method $path"
  curl -s -i -X "$method" "$BASE$path" -H "Authorization: Bearer $(cat "tokens/$name.jwt")" \
    | grep -v -i -E '^(date|server|content-length):' | tr -d '\r'
  echo; echo
}

for t in valid expired expired-within-leeway not-yet-valid wrong-audience audience-list \
         wrong-issuer no-exp id-token-type forged-signature; do
  call "$t"
done
call read-only-scope POST /orders/ord-1001/refund
