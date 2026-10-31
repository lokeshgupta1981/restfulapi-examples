#!/usr/bin/env bash
# The DPoP exchange on the wire, with curl. Needs the servers running and jq.
cd "$(dirname "$0")"
AUTH=${AUTH_URL:-http://localhost:8000}; API=${API_URL:-http://localhost:8001}
PY=${PYTHON:-python3}
rm -f demo-key.pem

echo "### Token request with a proof made for another URL"
PROOF=$($PY make_proof.py POST "$AUTH/other")
curl -s -i -u orders-app:demo-secret-not-for-production -H "DPoP: $PROOF" \
  -d grant_type=client_credentials -d scope=orders:read "$AUTH/token"; echo

echo; echo "### Token request with a DPoP proof"
PROOF=$($PY make_proof.py POST "$AUTH/token")
RESP=$(curl -s -D headers.txt -u orders-app:demo-secret-not-for-production -H "DPoP: $PROOF" \
  -d grant_type=client_credentials -d scope=orders:read "$AUTH/token")
grep -iE "^(HTTP|cache-control)" headers.txt; rm -f headers.txt
echo "$RESP" | jq '{access_token: (.access_token[:24] + "..."), token_type, expires_in, scope}'
TOKEN=$(echo "$RESP" | jq -r .access_token)

echo; echo "### API call with Authorization: DPoP and a fresh proof"
PROOF=$($PY make_proof.py GET "$API/orders" "$TOKEN")
curl -s -i -H "Authorization: DPoP $TOKEN" -H "DPoP: $PROOF" "$API/orders"; echo

echo; echo "### The same request replayed"
curl -s -i -H "Authorization: DPoP $TOKEN" -H "DPoP: $PROOF" "$API/orders"; echo

echo; echo "### The token without a proof"
curl -s -i -H "Authorization: DPoP $TOKEN" "$API/orders"; echo
rm -f demo-key.pem
