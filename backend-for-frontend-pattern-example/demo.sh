#!/usr/bin/env bash
# Starts the authorization server, the three services and both BFFs, then runs
# every step shown in the article. Ports default to 8000-8005; override with
# BASE_PORT, e.g. BASE_PORT=20480 ./demo.sh
set -u
cd "$(dirname "$0")"
PY=${PY:-.venv/bin/python}
UV=${UV:-"$PY -m uvicorn"}
BASE=${BASE_PORT:-8000}
export AUTH_PORT=$BASE ORDERS_PORT=$((BASE+1)) CATALOG_PORT=$((BASE+2)) \
       SHIPPING_PORT=$((BASE+3)) MOBILE_BFF_PORT=$((BASE+4)) WEB_BFF_PORT=$((BASE+5))
export ACCESS_TOKEN_TTL=60          # short-lived access tokens for the refresh step
mkdir -p logs
PIDS=()

start() {  # start <module:app> <port> [ENV=value ...]
  local target=$1 port=$2; shift 2
  env "$@" $UV "$target" --host 127.0.0.1 --port "$port" --log-level warning \
      >> "logs/${target%%:*}.log" 2>&1 &
  PIDS+=($!)
  eval "PID_${target//:/_}=$!"   # e.g. PID_services_shipping_app
}
cleanup() { for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done; }
trap cleanup EXIT
section() { echo; echo "===== $1"; }
wait_ready() {  # wait until every given port accepts connections
  for port in "$@"; do
    for _ in $(seq 100); do curl -s -o /dev/null "http://127.0.0.1:$port/docs" && break; sleep 0.2; done
  done
}

start auth_server:app "$AUTH_PORT"
start services:orders_app "$ORDERS_PORT"
start services:catalog_app "$CATALOG_PORT"
start services:shipping_app "$SHIPPING_PORT"
start mobile_bff:app "$MOBILE_BFF_PORT"
start web_bff:app "$WEB_BFF_PORT" REFRESH_MARGIN=55
wait_ready $(seq "$BASE" $((BASE+5)))

section "1. Mobile order screen without and with the BFF"
$PY mobile_client.py 1001

WEB=http://127.0.0.1:$WEB_BFF_PORT
section "2. Browser sign-in through the web BFF"
echo "--- 2a. GET /bff/login"
login=$(curl -sS -i "$WEB/bff/login")
echo "$login" | grep -iE '^(HTTP|location|set-cookie)'
auth_url=$(echo "$login" | grep -i '^location:' | cut -d' ' -f2 | tr -d '\r')
state=$(echo "$auth_url" | sed -E 's/.*state=([^&]*).*/\1/')
echo "--- 2b. the browser follows the redirect to the authorization server"
authz=$(curl -sS -i "$auth_url")
echo "$authz" | grep -iE '^(HTTP|location)'
cb_url=$(echo "$authz" | grep -i '^location:' | cut -d' ' -f2 | tr -d '\r')
echo "--- 2c. the browser comes back to the BFF callback"
cb=$(curl -sS -i -H "Cookie: __Host-Http-login=$state" "$cb_url")
echo "$cb" | grep -iE '^(HTTP|location|set-cookie)'
sid=$(echo "$cb" | grep -i 'set-cookie: __Host-Http-session=' | sed -E 's/.*session=([^;]*).*/\1/')
COOKIE="Cookie: __Host-Http-session=$sid"

section "3. The SPA calls the web BFF with the cookie and the X-CSRF header"
curl -sS -i -H "$COOKIE" -H "X-CSRF: 1" "$WEB/api/order-page/1001"; echo
echo "--- does the response contain a token? (grep for eyJ, the start of a JWT)"
curl -sS -H "$COOKIE" -H "X-CSRF: 1" "$WEB/api/order-page/1001" | grep -c 'eyJ'

section "4. CSRF defense and missing session"
echo "--- 4a. cookie but no X-CSRF header (what a cross-site form post would send)"
curl -sS -i -H "$COOKIE" "$WEB/api/order-page/1001"; echo
echo "--- 4b. X-CSRF header but no cookie"
curl -sS -i -H "X-CSRF: 1" "$WEB/api/order-page/1001"; echo

section "5. Token refresh inside the BFF (access token TTL 60 s, refresh 55 s before expiry)"
sleep 6
curl -sS -o /dev/null -w "HTTP %{http_code}\n" -H "$COOKIE" -H "X-CSRF: 1" "$WEB/api/order-page/1001"
sleep 1
echo "--- logs/web_bff.log:"; grep refreshed logs/web_bff.log

section "6. Shipping service down: the mobile BFF degrades the screen"
kill "$PID_services_shipping_app"
sleep 1
token=$($PY -c "import httpx,mobile_client as m; print(m.sign_in(httpx.Client()))")
curl -sS -i -H "Authorization: Bearer $token" "http://127.0.0.1:$MOBILE_BFF_PORT/mobile/v1/order-screen/1001"; echo
start services:shipping_app "$SHIPPING_PORT"
wait_ready "$SHIPPING_PORT"

section "7. Latency: direct calls vs the BFF (parallel fan-out inside the BFF)"
$PY bench.py 50

section "8. Latency: the same BFF with sequential fan-out"
kill "$PID_mobile_bff_app"; sleep 1
start mobile_bff:app "$MOBILE_BFF_PORT" FANOUT=sequential
wait_ready "$MOBILE_BFF_PORT"
$PY bench.py 50
