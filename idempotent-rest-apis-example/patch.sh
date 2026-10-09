#!/usr/bin/env bash
# JSON Patch requests that are idempotent and one that is not.
BASE=${BASE:-http://localhost:8000}
show() { echo "\$ $*"; "$@" -s -i | grep -iE '^(HTTP/|etag)|^\{' ; echo; }
JP='Content-Type: application/json-patch+json'

curl -s -o /dev/null -X PUT "$BASE/orders/ord_7" -H 'Content-Type: application/json' -d '{"items":["book"],"status":"new"}'

echo "== replace status, sent twice: same result =="
show curl -X PATCH "$BASE/orders/ord_7" -H "$JP" -d '[{"op":"replace","path":"/status","value":"paid"}]'
show curl -X PATCH "$BASE/orders/ord_7" -H "$JP" -d '[{"op":"replace","path":"/status","value":"paid"}]'

echo "== add to the end of items, sent twice: a second pen =="
show curl -X PATCH "$BASE/orders/ord_7" -H "$JP" -d '[{"op":"add","path":"/items/-","value":"pen"}]'
show curl -X PATCH "$BASE/orders/ord_7" -H "$JP" -d '[{"op":"add","path":"/items/-","value":"pen"}]'

echo "== add with If-Match, sent twice: the retry gets 412 =="
show curl -X PATCH "$BASE/orders/ord_7" -H "$JP" -H 'If-Match: "v4"' -d '[{"op":"add","path":"/items/-","value":"lamp"}]'
show curl -X PATCH "$BASE/orders/ord_7" -H "$JP" -H 'If-Match: "v4"' -d '[{"op":"add","path":"/items/-","value":"lamp"}]'
