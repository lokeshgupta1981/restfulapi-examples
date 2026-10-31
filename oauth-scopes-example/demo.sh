#!/usr/bin/env bash
# Runs every case from the article against the two running servers.
# Needs curl and jq. Set ISSUER and API_URL if you use other ports.
set -u
export ISSUER=${ISSUER:-http://127.0.0.1:8000}
export API_URL=${API_URL:-http://127.0.0.1:8001}
PY=${PY:-python3}

token() { $PY get_token.py "$@" | jq -r .access_token; }
payload() { $PY -c "import sys,base64;p=sys.stdin.read().split('.')[1];print(base64.urlsafe_b64decode(p+'='*(-len(p)%4)).decode())"; }

echo "### 1. Which scopes does the API use? (protected resource metadata)"
curl -s "$API_URL/.well-known/oauth-protected-resource" | jq .

echo; echo "### 2. reading-tracker asks for orders:read orders:write"
$PY get_token.py -v --client reading-tracker --secret demo-secret-reading-tracker \
  --user asha --scope "orders:read orders:write" | jq '.access_token |= .[0:20] + "..."'

echo; echo "### 3. An unknown scope"
$PY get_token.py -v --client bookshop-web --user asha --scope "orders:delete"

echo; echo "### 4. The scope inside the access token (JWT payload)"
READ_TOKEN=$(token --client reading-tracker --secret demo-secret-reading-tracker \
  --user asha --scope "orders:read orders:write")
echo "$READ_TOKEN" | payload | jq .

echo; echo "### 5. No token"
curl -s -i "$API_URL/orders"

echo; echo; echo "### 6. GET /orders with orders:read"
curl -s -i -H "Authorization: Bearer $READ_TOKEN" "$API_URL/orders"

echo; echo; echo "### 7. POST /orders with only orders:read"
curl -s -i -X POST -H "Authorization: Bearer $READ_TOKEN" \
  -H "Content-Type: application/json" -d '{"book":"b-2"}' "$API_URL/orders"

echo; echo; echo "### 8. Asha reads Meera's order with orders:read"
curl -s -i -H "Authorization: Bearer $READ_TOKEN" "$API_URL/orders/o-2001"

echo; echo; echo "### 9. A token that was tampered with"
curl -s -i -H "Authorization: Bearer ${READ_TOKEN}x" "$API_URL/orders"

echo; echo; echo "### 10. Asha (customer) asks for orders:refund"
$PY get_token.py --client bookshop-web --user asha --scope "orders:read orders:refund" \
  | jq '.access_token |= .[0:20] + "..."'

echo; echo "### 11. Ravi (staff) asks for orders:refund and refunds o-2001"
STAFF_TOKEN=$(token --client bookshop-web --user ravi --scope "orders:refund")
echo "$STAFF_TOKEN" | payload | jq -c '{sub, scope, roles}'
curl -s -i -X POST -H "Authorization: Bearer $STAFF_TOKEN" "$API_URL/orders/o-2001/refund"
echo
