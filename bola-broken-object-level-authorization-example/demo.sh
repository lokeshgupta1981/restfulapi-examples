#!/usr/bin/env bash
# Sends the same requests to one version of the Orders API.
# Start an app first, e.g. uvicorn vulnerable_app:app --port 8000, then: BASE=http://localhost:8000 ./demo.sh
BASE=${BASE:-http://localhost:8000}
ALICE="Authorization: Bearer demo-token-alice"   # fake demo tokens
BOB="Authorization: Bearer demo-token-bob"

call() {
  echo "### $1"
  shift
  curl -s -i "$@" | grep -v -i -E '^(date|server|content-length):'
  echo
  echo
}

call "1. Alice reads her own order" -H "$ALICE" "$BASE/orders/1001"
call "2. Alice changes the ID to 1002 (Bob's order)" -H "$ALICE" "$BASE/orders/1002"
call "3. Alice asks for Bob's order list with a query parameter" -H "$ALICE" "$BASE/orders?customer_id=2"
call "4. Alice cancels Bob's order" -X DELETE -H "$ALICE" "$BASE/orders/1002"
call "5. Alice ships her order to Bob's saved address" -X PATCH -H "$ALICE" \
  -H "Content-Type: application/json" -d '{"address_id": 12}' "$BASE/orders/1004"
call "6. Alice reads an order that does not exist" -H "$ALICE" "$BASE/orders/1999"
call "7. No token" "$BASE/orders/1002"
