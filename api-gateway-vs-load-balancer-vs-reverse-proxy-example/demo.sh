#!/usr/bin/env bash
# Starts four bookstore services and nginx, then shows what the reverse proxy,
# the load balancer and the API gateway each do with real requests.
set -u
cd "$(dirname "$0")"

RP_PORT=${RP_PORT:-8080}          # reverse proxy, plain HTTP
RP_TLS_PORT=${RP_TLS_PORT:-8443}  # reverse proxy, HTTPS
LB_PORT=${LB_PORT:-8081}          # load balancer
GW_PORT=${GW_PORT:-8082}          # API gateway
EDGE_PORT=${EDGE_PORT:-9443}      # TLS edge in front of the gateway
BOOKS1_PORT=${BOOKS1_PORT:-9001}
BOOKS2_PORT=${BOOKS2_PORT:-9002}
BOOKS3_PORT=${BOOKS3_PORT:-9003}
ORDERS_PORT=${ORDERS_PORT:-9004}
CLIENT_IP=${CLIENT_IP:-127.0.0.2} # curl sends from this address (use 127.0.0.1 on macOS)
UVICORN=${UVICORN:-uvicorn}

mkdir -p logs tmp certs
: > logs/error.log; : > logs/access.log

# Self-signed demo certificate for 127.0.0.1, created on first run (never commit it).
if [ ! -f certs/demo.crt ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=127.0.0.1" \
    -addext "subjectAltName=IP:127.0.0.1" \
    -keyout certs/demo.key -out certs/demo.crt 2>/dev/null
fi

sed -e "s/__RP_PORT__/$RP_PORT/g" -e "s/__RP_TLS_PORT__/$RP_TLS_PORT/g" \
    -e "s/__LB_PORT__/$LB_PORT/g" -e "s/__GW_PORT__/$GW_PORT/g" -e "s/__EDGE_PORT__/$EDGE_PORT/g" \
    -e "s/__BOOKS1_PORT__/$BOOKS1_PORT/g" -e "s/__BOOKS2_PORT__/$BOOKS2_PORT/g" \
    -e "s/__BOOKS3_PORT__/$BOOKS3_PORT/g" -e "s/__ORDERS_PORT__/$ORDERS_PORT/g" \
    nginx.conf.template > nginx.conf

declare -A PIDS
start() { # name service port
  SERVICE=$2 INSTANCE=$1 $UVICORN bookstore:app --host 127.0.0.1 --port "$3" \
    --no-proxy-headers --log-level warning >> logs/services.log 2>&1 &
  PIDS[$1]=$!
}
stop() { kill "${PIDS[$1]}" 2>/dev/null; wait "${PIDS[$1]}" 2>/dev/null; }
cleanup() {
  for n in "${!PIDS[@]}"; do stop "$n"; done
  nginx -p "$PWD" -c "$PWD/nginx.conf" -s stop 2>/dev/null
}
trap cleanup EXIT

section() { echo; echo "===== $1"; }
c() { curl -sS --interface "$CLIENT_IP" "$@"; }

start books-1 books "$BOOKS1_PORT"; start books-2 books "$BOOKS2_PORT"
start books-3 books "$BOOKS3_PORT"; start orders-1 orders "$ORDERS_PORT"
nginx -p "$PWD" -c "$PWD/nginx.conf"
sleep 2

section "1. Direct call to books-1, no proxy"
c -i "http://127.0.0.1:$BOOKS1_PORT/books/1"; echo
c "http://127.0.0.1:$BOOKS1_PORT/whoami"; echo

section "2. The same call through the reverse proxy"
c -i "http://127.0.0.1:$RP_PORT/books/1"; echo

section "3. HTTPS at the reverse proxy: what books-1 sees"
c --cacert certs/demo.crt "https://127.0.0.1:$RP_TLS_PORT/whoami"; echo

section "4. Load balancer: six requests"
for i in 1 2 3 4 5 6; do
  c -o /dev/null -D - "http://127.0.0.1:$LB_PORT/books/1" | grep -iE '^(HTTP|x-upstream|x-instance)' | tr -d '\r' | paste -sd' '
done

section "5. books-2 stops; six more requests through the load balancer"
stop books-2
for i in 1 2 3 4 5 6; do
  c -o /dev/null -D - "http://127.0.0.1:$LB_PORT/books/1" | grep -iE '^(HTTP|x-upstream|x-instance)' | tr -d '\r' | paste -sd' '
done
echo "--- access.log lines for port $LB_PORT:"; grep "^$LB_PORT " logs/access.log | tail -n 6
echo "--- error.log:"; grep -o 'connect() failed.*upstream: "[^"]*"' logs/error.log

section "6. books-1 stops too: reverse proxy vs load balancer"
stop books-1
echo "reverse proxy:"; c -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:$RP_PORT/books/1"
echo "load balancer:"; c -o /dev/null -D - "http://127.0.0.1:$LB_PORT/books/1" | grep -iE '^(HTTP|x-instance)' | tr -d '\r' | paste -sd' '
start books-1 books "$BOOKS1_PORT"; start books-2 books "$BOOKS2_PORT"; sleep 11  # wait out fail_timeout

section "7. Gateway: no API key"
c -i "http://127.0.0.1:$GW_PORT/api/books/1"; echo
echo "--- the load balancer does not care:"
c -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:$LB_PORT/books/1"

section "8. Gateway: valid key, routing by path"
c -i -H 'X-API-Key: demo-key-mobile-123' "http://127.0.0.1:$GW_PORT/api/books/1"; echo
c -i -H 'X-API-Key: demo-key-mobile-123' "http://127.0.0.1:$GW_PORT/api/orders/1042"; echo
c -i -H 'X-API-Key: demo-key-mobile-123' "http://127.0.0.1:$GW_PORT/api/payments/7"

section "9. Gateway: what the service sees"
c -H 'X-API-Key: demo-key-mobile-123' "http://127.0.0.1:$GW_PORT/api/whoami"; echo

section "10. Gateway: rate limit per client (60/min, burst 2)"
sleep 3
for i in 1 2 3 4 5; do
  printf 'mobile  request %s: ' "$i"
  c -o /dev/null -w '%{http_code}\n' -H 'X-API-Key: demo-key-mobile-123' "http://127.0.0.1:$GW_PORT/api/books/1"
done
printf 'partner request 1: '
c -o /dev/null -w '%{http_code}\n' -H 'X-API-Key: demo-key-partner-456' "http://127.0.0.1:$GW_PORT/api/books/1"

section "11. Production path: HTTPS edge -> gateway -> books pool"
sleep 3
c --cacert certs/demo.crt -H 'X-API-Key: demo-key-partner-456' "https://127.0.0.1:$EDGE_PORT/api/whoami"; echo
echo "--- access.log, one line per hop:"; tail -n 2 logs/access.log

section "12. A client sends a fake X-Forwarded-For"
echo "reverse proxy (appends to it):"
c --cacert certs/demo.crt -H 'X-Forwarded-For: 203.0.113.9' "https://127.0.0.1:$RP_TLS_PORT/whoami"; echo
echo "edge (replaces it):"
sleep 2
c --cacert certs/demo.crt -H 'X-API-Key: demo-key-partner-456' -H 'X-Forwarded-For: 203.0.113.9' \
  "https://127.0.0.1:$EDGE_PORT/api/whoami"; echo
