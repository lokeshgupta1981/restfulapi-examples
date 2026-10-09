#!/usr/bin/env bash
# Sends each request twice and shows the status line, the ETag and the body.
BASE=${BASE:-http://localhost:8000}
show() { echo "\$ $*"; "$@" -s -i | grep -iE '^(HTTP/|etag|location|idempotent-replayed)|^\{' ; echo; }

echo "== PUT twice: same final state, same ETag =="
show curl -X PUT "$BASE/orders/ord_42" -H 'Content-Type: application/json' -d '{"items":["book"],"status":"new"}'
show curl -X PUT "$BASE/orders/ord_42" -H 'Content-Type: application/json' -d '{"items":["book"],"status":"new"}'

echo "== DELETE twice: the order is gone after both calls =="
show curl -X DELETE "$BASE/orders/ord_42"
show curl -X DELETE "$BASE/orders/ord_42"

echo "== POST twice without a key: two orders =="
show curl -X POST "$BASE/orders" -H 'Content-Type: application/json' -d '{"items":["pen"]}'
show curl -X POST "$BASE/orders" -H 'Content-Type: application/json' -d '{"items":["pen"]}'

echo "== POST twice with the same Idempotency-Key: one order =="
show curl -X POST "$BASE/orders" -H 'Content-Type: application/json' -H 'Idempotency-Key: "9b2f6a1e-4c1d-4f7a-9a51-2f3c8e0d7b11"' -d '{"items":["lamp"]}'
show curl -X POST "$BASE/orders" -H 'Content-Type: application/json' -H 'Idempotency-Key: "9b2f6a1e-4c1d-4f7a-9a51-2f3c8e0d7b11"' -d '{"items":["lamp"]}'

echo "== Same key, different body =="
show curl -X POST "$BASE/orders" -H 'Content-Type: application/json' -H 'Idempotency-Key: "9b2f6a1e-4c1d-4f7a-9a51-2f3c8e0d7b11"' -d '{"items":["desk"]}'

echo "== All orders =="
curl -s "$BASE/orders"; echo
