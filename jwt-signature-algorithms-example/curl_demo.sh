#!/usr/bin/env bash
# Raw HTTP exchanges against issuer.py and orders_api.py (both must be running).
ISSUER=${ISSUER_URL:-http://127.0.0.1:8000}
API=${API_URL:-http://127.0.0.1:8001}
PY=${PY:-python3}
JWKS="$ISSUER/.well-known/jwks.json"

token() {  # token ALG -> prints an access token
  curl -s -X POST "$ISSUER/token" -H 'Content-Type: application/json' \
    -d "{\"sub\":\"alice\",\"alg\":\"$1\"}" | $PY -c 'import json,sys;print(json.load(sys.stdin)["access_token"])'
}
call() {   # call TOKEN -> status line, WWW-Authenticate header, body
  curl -s -i "$API/orders" -H "Authorization: Bearer $1" | grep -iE '^(HTTP/|www-authenticate)|^\{' | tr -d '\r'
}
header() { $PY -c 'import sys,jwt;print(jwt.get_unverified_header(sys.argv[1]))' "$1"; }

echo "== Token request (RS256)"
echo "\$ curl -s -X POST $ISSUER/token -H 'Content-Type: application/json' -d '{\"sub\":\"alice\",\"alg\":\"RS256\"}'"
curl -s -X POST "$ISSUER/token" -H 'Content-Type: application/json' -d '{"sub":"alice","alg":"RS256"}' | cut -c1-120; echo " ..."
RS=$(token RS256); ES=$(token ES256); HS=$(token HS256)
echo "== JWKS"
curl -s "$JWKS" | $PY -c '
import json,sys
for k in json.load(sys.stdin)["keys"]:
    print({n: (v[:20] + "...") if len(v) > 24 else v for n, v in k.items()})'

for alg in RS256 ES256 HS256; do
  eval "t=\$${alg:0:2}"
  echo "== GET /orders with an $alg token, header $(header "$t")"
  call "$t"
done

echo "== Tampered RS256 token (sub changed to mallory, old signature)"
call "$($PY forge.py tamper "$JWKS" "$RS")"
echo "== Forged alg=none token"
call "$($PY forge.py none "$JWKS")"
echo "== Forged HS256 token signed with the RSA public key (algorithm confusion)"
call "$($PY forge.py confused "$JWKS")"

echo "== Key rotation"
curl -s -X POST "$ISSUER/rotate"; echo
NEW=$(token RS256)
echo "-- kids in the JWKS now"
curl -s "$JWKS" | $PY -c 'import json,sys;print([k["kid"] for k in json.load(sys.stdin)["keys"]])'
echo "-- old RS256 token, header $(header "$RS")"
call "$RS"
echo "-- new RS256 token, header $(header "$NEW")"
call "$NEW"
echo "-- same new token again, 31 seconds later"
sleep 31
call "$NEW"
