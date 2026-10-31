#!/usr/bin/env bash
# Shows what happens to offset and cursor pages when the data changes between two requests.
# Start the server first: uvicorn app:app --port 8000
BASE=${BASE:-http://localhost:8000}

ids() {   # print the request and the ids on the page
  echo "\$ curl -s \"$BASE$1\" | jq -c '[.data[].id]'"
  curl -s "$BASE$1" | jq -c '[.data[].id]'
}
reset() { curl -s -X POST "$BASE/_reset"; }

echo "== 1. Offset: a new order arrives between page 1 and page 2 =="
reset
ids "/orders/offset?limit=3&offset=0"
echo '$ curl -s -X POST '"$BASE"'/orders -H "Content-Type: application/json" -d '"'"'{"customer":"kim","total":25}'"'"
curl -s -X POST "$BASE/orders" -H "Content-Type: application/json" -d '{"customer":"kim","total":25}'; echo
ids "/orders/offset?limit=3&offset=3"
echo

echo "== 2. Offset: an order on page 1 is deleted before page 2 =="
reset
ids "/orders/offset?limit=3&offset=0"
echo "\$ curl -s -X DELETE $BASE/orders/109"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X DELETE "$BASE/orders/109"
ids "/orders/offset?limit=3&offset=3"
echo

echo "== 3. Cursor: the same two changes =="
reset
echo "\$ curl -s \"$BASE/orders?limit=3\""
PAGE1=$(curl -s "$BASE/orders?limit=3"); echo "$PAGE1"
NEXT=$(echo "$PAGE1" | jq -r .next_cursor)
curl -s -o /dev/null -X POST "$BASE/orders" -H "Content-Type: application/json" -d '{"customer":"kim","total":25}'
curl -s -o /dev/null -X DELETE "$BASE/orders/109"
echo "(created order 111 and deleted order 109)"
ids "/orders?limit=3&cursor=$NEXT"
echo

echo "== 4. Keyset with the sort values in the URL =="
reset
ids "/orders/keyset?limit=3"
ids "/orders/keyset?limit=3&before_created_at=2026-10-01T09:44:00Z&before_id=108"
echo

echo "== 5. A broken cursor =="
echo "\$ curl -s -i \"$BASE/orders?cursor=not-a-real-cursor\""
curl -s -i "$BASE/orders?cursor=not-a-real-cursor" | grep -v -i -E '^(date|server|content-length):'
echo
BAD=$(printf '{"created_at":"2026-10-01T09:44:00Z","id":"108"}' | base64 | tr '+/' '-_' | tr -d '=\n')
echo "\$ curl -s \"$BASE/orders?cursor=$BAD\"   # id is a string"
curl -s -w "  (HTTP %{http_code})" "$BASE/orders?cursor=$BAD"; echo
echo

echo "== 6. A page size above the maximum (100) =="
echo "\$ curl -s \"$BASE/orders?limit=500\""
curl -s -w "  (HTTP %{http_code})" "$BASE/orders?limit=500"; echo
