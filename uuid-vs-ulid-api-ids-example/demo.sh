#!/usr/bin/env bash
# Run against: ID_KIND=uuid7 python server.py   (API_URL defaults to http://127.0.0.1:8000)
# For a ULID server: ID_KIND=ulid python server.py, then ID_KIND=ulid ./demo.sh
set -u
API=${API_URL:-http://127.0.0.1:8000}
PY=${PYTHON:-python3}
KIND=${ID_KIND:-uuid7}
J='Content-Type: application/json'
JQ=" | jq -c '(.items[] | {id, item}), {next_cursor}'"

echo "### 1. The server creates the ID"
curl -s -i -X POST "$API/orders" -H "$J" -d '{"item":"Clean Code","qty":1}' | grep -v -i -E '^(date|server|content-length):'
echo
for b in "Refactoring" "Domain-Driven Design" "Release It!"; do
  curl -s -X POST "$API/orders" -H "$J" -d "{\"item\":\"$b\",\"qty\":1}" > /dev/null
  sleep 0.05
done

echo
echo "### 2. Pages with the last ID as the cursor"
PAGE1=$(curl -s "$API/orders?limit=2")
echo "\$ curl -s '$API/orders?limit=2'$JQ"; echo "$PAGE1" | jq -c '(.items[] | {id, item}), {next_cursor}'
CURSOR=$(echo "$PAGE1" | jq -r .next_cursor)
echo "\$ curl -s '$API/orders?limit=2&after=$CURSOR'$JQ"
curl -s "$API/orders?limit=2&after=$CURSOR" | jq -c '(.items[] | {id, item}), {next_cursor}'

FIRST=$(echo "$PAGE1" | jq -r '.items[0].id')
echo
echo "### 3. Anyone who sees the ID can read its creation time"
echo "\$ python id_tool.py when $FIRST"
$PY id_tool.py when "$FIRST"
echo "created_at stored by the server: $(echo "$PAGE1" | jq -r '.items[0].created_at')"

echo
echo "### 4. The same ID in the other letter case"
if [ "$KIND" = ulid ]; then UPPER=$(echo "$FIRST" | tr A-Z a-z); else UPPER=$(echo "$FIRST" | tr a-f A-F); fi
echo "\$ curl -s -o /dev/null -w '%{http_code}' $API/orders/$UPPER"
curl -s -o /dev/null -w '%{http_code}\n' "$API/orders/$UPPER"

echo
echo "### 5. The client creates the ID: PUT /orders/{id}"
CID=$($PY id_tool.py new "$KIND")
for attempt in 1 2; do
  echo "\$ curl -s -w ' -> %{http_code}' -X PUT $API/orders/$CID -H '$J' -d '{\"item\":\"Clean Architecture\",\"qty\":2}'   (attempt $attempt)"
  curl -s -w ' -> %{http_code}\n' -X PUT "$API/orders/$CID" -H "$J" -d '{"item":"Clean Architecture","qty":2}'
done
echo "\$ curl -s -w ' -> %{http_code}' -X PUT $API/orders/$CID -H '$J' -d '{\"item\":\"Clean Architecture\",\"qty\":5}'   (same ID, different body)"
curl -s -w ' -> %{http_code}\n' -X PUT "$API/orders/$CID" -H "$J" -d '{"item":"Clean Architecture","qty":5}'

[ "$KIND" = uuid7 ] || exit 0
echo
echo "### 6. IDs the server must reject"
V4=$($PY id_tool.py new uuid4)
echo "\$ a UUIDv4: PUT $API/orders/$V4"
curl -s -w ' -> %{http_code}\n' -X PUT "$API/orders/$V4" -H "$J" -d '{"item":"x","qty":1}'
FUT=$($PY id_tool.py future-uuid7)
echo "\$ a UUIDv7 dated next year: PUT $API/orders/$FUT"
curl -s -w ' -> %{http_code}\n' -X PUT "$API/orders/$FUT" -H "$J" -d '{"item":"x","qty":1}'
echo "\$ not an ID at all: PUT $API/orders/12345"
curl -s -w ' -> %{http_code}\n' -X PUT "$API/orders/12345" -H "$J" -d '{"item":"x","qty":1}'
