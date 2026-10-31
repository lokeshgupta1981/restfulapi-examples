#!/usr/bin/env bash
# Sends the requests shown in the article. Start the API first on an empty database:
#   rm -f invoices.db && uvicorn app:app --port 8000
BASE="${BASE:-http://localhost:8000}"
PY="${PY:-python}"
ALICE=$($PY tokens.py alice)   # tenant acme (free plan)
BOB=$($PY tokens.py bob)       # tenant globex (pro plan)

show() {  # print the request line, then status, selected headers and body
  printf '$ curl'
  for a in "$@"; do
    if [[ $a == *[\ \"{]* ]]; then printf " '%s'" "$a"; else printf ' %s' "$a"; fi
  done
  echo
  curl -s -i "$@" | tr -d '\r' | grep -Ei '^(HTTP/|content-type|retry-after|ratelimit|www-authenticate|\{)'
  echo
}

echo "== 1. Alice lists invoices: only tenant acme =="
show "$BASE/invoices" -H "Authorization: Bearer $ALICE" | sed "s/$ALICE/\$ALICE/"

echo "== 2. Alice asks for globex's invoice 1002 through the safe route =="
show "$BASE/invoices/1002" -H "Authorization: Bearer $ALICE" | sed "s/$ALICE/\$ALICE/"

echo "== 3. The same request through the unsafe route (lookup by ID only) =="
show "$BASE/unsafe/invoices/1002" -H "Authorization: Bearer $ALICE" | sed "s/$ALICE/\$ALICE/"

echo "== 4. Unsafe route that trusts X-Tenant-ID =="
show "$BASE/unsafe/invoices" -H "Authorization: Bearer $ALICE" -H "X-Tenant-ID: globex" | sed "s/$ALICE/\$ALICE/"

echo "== 5. Alice tries to create an invoice for tenant globex =="
show -X POST "$BASE/invoices" -H "Authorization: Bearer $ALICE" -H "Content-Type: application/json" \
  -d '{"customer":"Umbrella","amount_cents":500,"tenant_id":"globex"}' | sed "s/$ALICE/\$ALICE/"

echo "== 6. Alice creates an invoice: the server sets the tenant =="
show -X POST "$BASE/invoices" -H "Authorization: Bearer $ALICE" -H "Content-Type: application/json" \
  -d '{"customer":"Umbrella","amount_cents":500}' | sed "s/$ALICE/\$ALICE/"

echo "== 7. Acme (free plan, 5 per minute) has used 4 requests: one more works, the 6th gets 429 =="
curl -s -o /dev/null -w "acme request 5: %{http_code}\n" "$BASE/invoices" -H "Authorization: Bearer $ALICE"
show "$BASE/invoices" -H "Authorization: Bearer $ALICE" | sed "s/$ALICE/\$ALICE/"

echo "== 8. Globex is not affected by acme's limit =="
show "$BASE/invoices" -H "Authorization: Bearer $BOB" | sed "s/$BOB/\$BOB/"

echo "== 9. No token =="
show "$BASE/invoices"
