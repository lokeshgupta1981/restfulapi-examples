#!/usr/bin/env bash
# PUT vs POST on the same orders API. Start the server first: uvicorn app:app --port 8000
BASE=${BASE:-http://localhost:8000}
JSON='Content-Type: application/json'
show() { echo "\$ curl $*"; curl -s -i "$@" | grep -iE '^(HTTP/|etag|location)|^\{' ; echo; }

echo "== 1. POST to the collection, sent twice: two orders with server-chosen ids =="
show -X POST "$BASE/orders" -H "$JSON" -d '{"customer":"c-7","items":["book"]}'
show -X POST "$BASE/orders" -H "$JSON" -d '{"customer":"c-7","items":["book"]}'

echo "== 2. PUT to a client-chosen URI, sent twice: created once, then replaced with the same state =="
show -X PUT "$BASE/orders/ord_42" -H "$JSON" -d '{"customer":"c-9","items":["lamp"],"status":"new","note":"gift wrap"}'
show -X PUT "$BASE/orders/ord_42" -H "$JSON" -d '{"customer":"c-9","items":["lamp"],"status":"new","note":"gift wrap"}'

echo "== 3. PUT without the note field: the note is gone, because PUT replaces the whole order =="
show -X PUT "$BASE/orders/ord_42" -H "$JSON" -d '{"customer":"c-9","items":["lamp","pen"],"status":"new"}'
show "$BASE/orders/ord_42"

echo "== 4. PUT with only one field: rejected, PUT needs the full order =="
show -X PUT "$BASE/orders/ord_42" -H "$JSON" -d '{"items":["lamp"]}'

echo "== 5. Create-only PUT with If-None-Match: * =="
show -X PUT "$BASE/orders/ord_43" -H "$JSON" -H 'If-None-Match: *' -d '{"customer":"c-1","items":["desk"],"status":"new"}'
show -X PUT "$BASE/orders/ord_43" -H "$JSON" -H 'If-None-Match: *' -d '{"customer":"c-2","items":["chair"],"status":"new"}'

echo "== 6. Update with If-Match, sent twice: the second request has a stale ETag and gets 412 =="
show -X PUT "$BASE/orders/ord_42" -H "$JSON" -H 'If-Match: "v2"' -d '{"customer":"c-9","items":["lamp"],"status":"paid"}'
show -X PUT "$BASE/orders/ord_42" -H "$JSON" -H 'If-Match: "v2"' -d '{"customer":"c-9","items":["lamp"],"status":"paid"}'

echo "== 7. If-Match: * (any current version) and If-None-Match with the current ETag =="
show -X PUT "$BASE/orders/ord_42" -H "$JSON" -H 'If-Match: *' -d '{"customer":"c-9","items":["lamp"],"status":"paid"}'
show -X PUT "$BASE/orders/ord_42" -H "$JSON" -H 'If-None-Match: "v3"' -d '{"customer":"c-9","items":["desk"],"status":"paid"}'

echo "== 8. POST for an action =="
show -X POST "$BASE/orders/ord_42/cancel"
