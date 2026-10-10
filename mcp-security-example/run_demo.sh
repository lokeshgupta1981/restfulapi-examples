#!/usr/bin/env bash
# Runs every case of the article. The script starts the MCP server itself on
# http://127.0.0.1:8000, first with the approved tools, then with RUG_PULL=1.
set -u
PY=${PYTHON:-python3}
# run TOKEN_VARIABLE args...: prints the command with the variable name instead of the token
run() { local var=$1; shift; echo "\$ python client_guard.py $* --token \$$var"; $PY client_guard.py "$@" --token "${!var}"; echo "(exit code $?)"; echo; }
start_server() {
  "$@" $PY -m uvicorn server:app --host 127.0.0.1 --port 8000 --log-level warning &
  SERVER_PID=$!
  for i in $(seq 1 50); do curl -s -o /dev/null http://127.0.0.1:8000/docs && return; sleep 0.2; done
}
stop_server() { kill "$SERVER_PID"; wait "$SERVER_PID" 2>/dev/null; }

ALICE=$($PY tokens.py --sub alice --scope "cart:write")
ALICE_ORDERS=$($PY tokens.py --sub alice --scope "cart:write orders:write")
BOB=$($PY tokens.py --sub bob --scope "cart:write")
OTHER_AUD=$($PY tokens.py --sub alice --scope "cart:write" --aud https://api.example.com)

start_server env
echo "== 1. The user approves the tools, the client pins their hashes =="
run ALICE pin
run ALICE check

echo "== 2. Token issued for another API (audience check) =="
run OTHER_AUD call create_cart

echo "== 3. Token without the scope that checkout needs =="
CART=$($PY client_guard.py call create_cart --token "$ALICE" | sed -n 's/.*text=//p')
echo "alice created a cart (cart_id hidden)"
$PY client_guard.py call add_item "{\"cart_id\": \"$CART\", \"sku\": \"SKU-1\"}" --token "$ALICE" >/dev/null
echo "\$ python client_guard.py call checkout '{\"cart_id\": \"<alice's cart_id>\"}' --token \$ALICE"
$PY client_guard.py call checkout "{\"cart_id\": \"$CART\"}" --token "$ALICE"
echo

echo "== 4. Bob sends Alice's cart_id (state handle hijacking) =="
echo "\$ python client_guard.py call add_item '{\"cart_id\": \"<alice's cart_id>\", \"sku\": \"SKU-9\"}' --token \$BOB"
$PY client_guard.py call add_item "{\"cart_id\": \"$CART\", \"sku\": \"SKU-9\"}" --token "$BOB"
echo

echo "== 5. Alice gets orders:write and checks out =="
echo "\$ python client_guard.py call checkout '{\"cart_id\": \"<alice's cart_id>\"}' --token \$ALICE_ORDERS"
$PY client_guard.py call checkout "{\"cart_id\": \"$CART\"}" --token "$ALICE_ORDERS"
echo

echo "== 6. A web page on another origin calls the local server (DNS rebinding) =="
run ALICE call create_cart --origin http://evil.example
stop_server

echo "== 7. The server changes a tool description after approval (rug pull) =="
start_server env RUG_PULL=1
run ALICE check
stop_server
