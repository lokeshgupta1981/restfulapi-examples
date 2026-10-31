#!/usr/bin/env bash
# Starts the two services and the gateway, then runs every case with curl.
# Ports are configurable: GATEWAY_PORT, BOOKS_PORT, ORDERS_PORT (defaults 8000, 8001, 8002).
set -u
cd "$(dirname "$0")"
GW=${GATEWAY_PORT:-8000}; BP=${BOOKS_PORT:-8001}; OP=${ORDERS_PORT:-8002}
PY=${PYTHON:-python3}
mkdir -p logs
SERVICE=books  $PY -m uvicorn services:app --port "$BP" --log-level warning > logs/books.log 2>&1 &  P1=$!
SERVICE=orders $PY -m uvicorn services:app --port "$OP" --log-level warning > logs/orders.log 2>&1 & P2=$!
BOOKS_URL=http://127.0.0.1:$BP ORDERS_URL=http://127.0.0.1:$OP \
  $PY -m uvicorn gateway:app --port "$GW" --log-level warning > logs/gateway.log 2>&1 & P3=$!
trap 'kill $P1 $P2 $P3 2>/dev/null; wait 2>/dev/null' EXIT
for p in $BP $OP $GW; do until curl -s -o /dev/null "http://127.0.0.1:$p/docs"; do sleep 0.2; done; done

G=http://127.0.0.1:$GW
MOBILE='X-API-Key: demo-key-mobile-123'
PARTNER='X-API-Key: demo-key-partner-456'
quote() { for a in "$@"; do case $a in *" "*) printf " '%s'" "$a";; *) printf ' %s' "$a";; esac; done; }
show() { echo; echo "== $1 =="; shift; echo "\$ curl -i$(quote "$@")" | sed "s#$G#http://localhost:8000#"; curl -s -i "$@" | tr -d '\r' | grep -iv '^date:\|^server:'; echo; }

show "1. Without the gateway the client must know every service" "http://127.0.0.1:$BP/books/1"
show "2. No API key" "$G/api/orders/1042"
show "3. Valid key, routed to the orders service" -H "$MOBILE" "$G/api/orders/1042"
echo; echo "== 4. Requests that reached the books service so far (case 1 called it directly) =="
curl -s "http://127.0.0.1:$BP/stats"; echo
show "4a. Book list, first call (cache miss)" -H "$PARTNER" "$G/api/books"
show "4b. Book list, second call (cache hit)" -H "$PARTNER" "$G/api/books"
echo; echo "== 4c. Requests that reached the books service after 4a and 4b =="
curl -s "http://127.0.0.1:$BP/stats"; echo
echo; echo "== 5. Rate limit: mobile-app may send 5 requests per 10 seconds (case 3 was number 1) =="
for i in 2 3 4 5; do
  curl -s -o /dev/null -w "request $i -> %{http_code}\n" -H "$MOBILE" "$G/api/books/1"
done
show "5b. The next request is rejected" -H "$MOBILE" "$G/api/books/1"
show "6. Composition: one call, two services" -H "$PARTNER" "$G/api/order-summary/1042"
show "7. Unknown route" -H "$PARTNER" "$G/api/customers/7"
show "8. Slow service, the gateway gives up after 2 seconds" -H "$PARTNER" "$G/api/books/1/slow"
kill $P2; sleep 0.5
show "9. Orders service is down" -H "$PARTNER" "$G/api/orders/1042"
echo; echo "== Gateway access log =="
grep -v " /docs " logs/gateway.log
