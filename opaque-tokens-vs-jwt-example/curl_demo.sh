#!/usr/bin/env bash
# Shows the raw HTTP exchanges: token request, introspection, JWKS.
# Needs the servers from run_all.sh. Credentials are demo values.
AS=http://127.0.0.1:9400

echo "== Token request (opaque)"
RESPONSE=$(curl -s -u orders-app:demo-secret-key-123 \
  -d grant_type=client_credentials -d scope=orders:read -d token_format=opaque \
  $AS/token)
echo "$RESPONSE"
OPAQUE=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "== Token request (jwt), first 60 characters of the response"
curl -s -u orders-app:demo-secret-key-123 \
  -d grant_type=client_credentials -d scope=orders:read -d token_format=jwt \
  $AS/token | cut -c1-60
echo "..."

echo "== Introspection of an active token"
curl -si -u orders-api:demo-introspect-secret-456 -d "token=$OPAQUE" $AS/introspect
echo

echo "== Introspection of an unknown token"
curl -si -u orders-api:demo-introspect-secret-456 -d "token=not-a-real-token" $AS/introspect
echo

echo "== Introspection without API credentials"
curl -si -d "token=$OPAQUE" $AS/introspect
echo

echo "== Introspection asking for the JWT form (phantom token)"
curl -s -u orders-api:demo-introspect-secret-456 -H "Accept: application/jwt" \
  -d "token=$OPAQUE" $AS/introspect | cut -c1-60
echo "..."

echo "== JWKS"
curl -s $AS/jwks | python3 -m json.tool | cut -c1-70

echo "== Authorization server metadata"
curl -s $AS/.well-known/oauth-authorization-server | python3 -m json.tool

echo "== Orders API call with a token that lacks orders:read"
WRITE_TOKEN=$(curl -s -u orders-app:demo-secret-key-123 \
  -d grant_type=client_credentials -d scope=orders:write -d token_format=opaque \
  $AS/token | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -si -H "Authorization: Bearer $WRITE_TOKEN" http://127.0.0.1:9401/introspect/orders
echo
