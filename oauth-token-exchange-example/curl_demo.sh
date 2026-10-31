#!/usr/bin/env bash
# The raw token exchange request and response, with curl.
set -euo pipefail
AUTH_URL=${AUTH_URL:-http://127.0.0.1:8000}

echo "== curl: user token"
USER_TOKEN=$(curl -s -X POST "$AUTH_URL/demo/login" -d user=asha \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
echo "${USER_TOKEN:0:24}..."

echo "== curl: the user token sent straight to the Payments API"
curl -s -i -X POST "${PAYMENTS_URL:-http://127.0.0.1:8002}/charges" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ord_1","amount":39.0}'
echo

echo "== curl: token exchange request (orders-api, demo secret)"
curl -s -i -X POST "$AUTH_URL/token" \
  -u orders-api:demo-secret-orders-api \
  -d grant_type=urn:ietf:params:oauth:grant-type:token-exchange \
  -d subject_token="$USER_TOKEN" \
  -d subject_token_type=urn:ietf:params:oauth:token-type:access_token \
  -d audience=payments-api \
  -d scope=payments:charge \
  | sed -E 's/("access_token":")([^"]{24})[^"]*/\1\2.../'
echo

echo "== curl: same request with a resource URL instead of an audience name"
curl -s -X POST "$AUTH_URL/token" \
  -u orders-api:demo-secret-orders-api \
  -d grant_type=urn:ietf:params:oauth:grant-type:token-exchange \
  -d subject_token="$USER_TOKEN" \
  -d subject_token_type=urn:ietf:params:oauth:token-type:access_token \
  --data-urlencode resource="${PAYMENTS_URL:-http://127.0.0.1:8002}" \
  -d scope=payments:charge \
  | sed -E 's/("access_token":")([^"]{24})[^"]*/\1\2.../'
echo

echo "== curl: token exchange without client authentication"
curl -s -i -X POST "$AUTH_URL/token" \
  -d grant_type=urn:ietf:params:oauth:grant-type:token-exchange \
  -d subject_token="$USER_TOKEN" \
  -d subject_token_type=urn:ietf:params:oauth:token-type:access_token \
  -d audience=payments-api
echo
