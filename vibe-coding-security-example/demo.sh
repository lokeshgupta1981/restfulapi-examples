#!/usr/bin/env bash
# Sends the same requests to one version of the orders API and prints what goes over the wire.
# Usage: ./demo.sh http://127.0.0.1:8001   (vulnerable_app)
#        ./demo.sh http://127.0.0.1:8002   (secure_app)
# Restart the server before each run, because the data lives in memory.
BASE=${1:-http://127.0.0.1:8001}

show() {  # prints the status line, the interesting headers and the body
  echo "### $1"
  shift
  curl -s -i "$@" | tr -d '\r' | grep -iE '^(HTTP/|access-control-allow-|retry-after|content-type)|^[[{]' | cut -c1-200
  echo
}

token() {
  curl -s -X POST "$BASE/login" -H 'Content-Type: application/json' \
    -d "{\"name\":\"$1\",\"password\":\"$1-pass\"}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])'
}

ALICE=$(token alice)
BOB=$(token bob)

show "1. alice reads her own order 101" "$BASE/orders/101" -H "Authorization: Bearer $ALICE"
show "2. alice reads bob's order 201" "$BASE/orders/201" -H "Authorization: Bearer $ALICE"
show "3. alice changes her email and sends role=admin" -X PATCH "$BASE/users/me" \
  -H "Authorization: Bearer $ALICE" -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.org","role":"admin"}'
show "4. bob calls an admin route" "$BASE/admin/users" -H "Authorization: Bearer $BOB"
show "5. bob searches for item x' OR '1'='1" -G "$BASE/orders" -H "Authorization: Bearer $BOB" \
  --data-urlencode "item=x' OR '1'='1"
show "6. bob sends a field that does not exist" -X PATCH "$BASE/users/me" \
  -H "Authorization: Bearer $BOB" -H 'Content-Type: application/json' -d '{"no_such_column":1}'
show "7. a page on https://evil.example calls the API" "$BASE/orders/101" -H 'Origin: https://evil.example'
echo "### 8. eight wrong passwords for bob"
for i in 1 2 3 4 5 6 7 8; do
  curl -s -o /dev/null -w '%{http_code} ' -X POST "$BASE/login" -H 'Content-Type: application/json' \
    -d '{"name":"bob","password":"guess"}'
done
echo
echo
show "9. one more wrong password for bob" -X POST "$BASE/login" -H 'Content-Type: application/json' \
  -d '{"name":"bob","password":"guess"}'
