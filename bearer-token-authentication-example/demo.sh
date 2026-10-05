#!/usr/bin/env bash
# Calls the Orders API with different Authorization headers.
# Start the issuer (node issuer.js) and the API (node api.js) first. Needs curl and jq.
set -u

echo "### Token response for orders-app"
curl -s -u orders-app:orders-app-secret \
  -d grant_type=client_credentials \
  -d scope=orders:read \
  --data-urlencode resource=http://localhost:3000/orders \
  http://localhost:4000/token
echo; echo

# Four tokens: a normal one, one for another API, one without the scope, one that lives 2 seconds.
ORDERS_TOKEN=$(curl -s -u orders-app:orders-app-secret -d grant_type=client_credentials \
  -d scope=orders:read --data-urlencode resource=http://localhost:3000/orders \
  http://localhost:4000/token | jq -r .access_token)
BILLING_TOKEN=$(curl -s -u orders-app:orders-app-secret -d grant_type=client_credentials \
  -d scope=orders:read --data-urlencode resource=http://localhost:3000/billing \
  http://localhost:4000/token | jq -r .access_token)
REPORTS_TOKEN=$(curl -s -u reports-app:reports-app-secret -d grant_type=client_credentials \
  -d scope=reports:read --data-urlencode resource=http://localhost:3000/orders \
  http://localhost:4000/token | jq -r .access_token)
SHORT_TOKEN=$(curl -s -u short-lived-app:short-lived-app-secret -d grant_type=client_credentials \
  -d scope=orders:read --data-urlencode resource=http://localhost:3000/orders \
  http://localhost:4000/token | jq -r .access_token)

echo "### 1. No token"
curl -s -i http://localhost:3000/orders; echo; echo

echo "### 2. Basic credentials instead of a bearer token"
curl -s -i -u alice:secret http://localhost:3000/orders; echo; echo

echo "### 3. Malformed header (Bearer with no token)"
curl -s -i -H "Authorization: Bearer" http://localhost:3000/orders; echo; echo

echo "### 4. Token that is not a JWT"
curl -s -i -H "Authorization: Bearer abc123" http://localhost:3000/orders; echo; echo

echo "### 5. Token in the query string"
curl -s -i "http://localhost:3000/orders?access_token=$ORDERS_TOKEN"; echo; echo

echo "### 6. Wrong audience (token issued for the billing API)"
curl -s -i -H "Authorization: Bearer $BILLING_TOKEN" http://localhost:3000/orders; echo; echo

echo "### 7. Missing scope (token has reports:read only)"
curl -s -i -H "Authorization: Bearer $REPORTS_TOKEN" http://localhost:3000/orders; echo; echo

echo "### 8. Valid token"
curl -s -i -H "Authorization: Bearer $ORDERS_TOKEN" http://localhost:3000/orders; echo; echo

echo "### 9. Valid token, lowercase scheme name"
curl -s -i -H "Authorization: bearer $ORDERS_TOKEN" http://localhost:3000/orders; echo; echo

echo "### 10. Expired token (2-second lifetime, 5 seconds clock leeway, wait 8 seconds)"
sleep 8
curl -s -i -H "Authorization: Bearer $SHORT_TOKEN" http://localhost:3000/orders; echo; echo

echo "### 11. Issuer keys unreachable (second API on port 3001 points to an issuer that is down)"
API_PORT=3001 ISSUER_URL=http://localhost:4999 node api.js > api-3001.log 2>&1 &
API_3001_PID=$!
sleep 1
curl -s -i -H "Authorization: Bearer $ORDERS_TOKEN" http://localhost:3001/orders; echo; echo
kill $API_3001_PID
echo "### api.js on port 3001 console"
cat api-3001.log; rm -f api-3001.log
echo

echo "### Decoded header of ORDERS_TOKEN"
echo "$ORDERS_TOKEN" | cut -d. -f1 | jq -R 'gsub("-";"+") | gsub("_";"/") | @base64d | fromjson'
echo "### Decoded payload of ORDERS_TOKEN"
echo "$ORDERS_TOKEN" | cut -d. -f2 | jq -R 'gsub("-";"+") | gsub("_";"/") | @base64d | fromjson'
