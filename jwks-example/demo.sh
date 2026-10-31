#!/usr/bin/env bash
# Runs the whole JWKS story: discovery, verification, caching, forged tokens,
# a rotation done too fast, a rotation done right, and removing an old key.
# Takes about 160 seconds because it waits for the cooldown and the cache.
set -u
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
AUTH_PORT=${AUTH_PORT:-8000}
API_PORT=${API_PORT:-8001}
export ISSUER="http://127.0.0.1:$AUTH_PORT"
export JWKS_CACHE_SECONDS=${JWKS_CACHE_SECONDS:-60}
AUTH="$ISSUER"
API="http://127.0.0.1:$API_PORT"
CLIENT="orders-app:demo-secret-not-real"   # demo credentials, not real

AUTH_PORT=$AUTH_PORT $PY auth_server.py & AUTH_PID=$!
trap 'kill $AUTH_PID ${API_PID:-} 2>/dev/null' EXIT
until curl -s "$AUTH/.well-known/jwks.json" >/dev/null; do sleep 0.2; done
API_PORT=$API_PORT $PY orders_api.py > api.log 2>&1 & API_PID=$!
until curl -s "$API/debug/jwks-fetches" >/dev/null; do sleep 0.2; done

LOG_LINES=0
api_log() { local n; n=$(wc -l < api.log); if [ "$n" -gt "$LOG_LINES" ]; then sed -n "$((LOG_LINES+1)),${n}p" api.log; fi; LOG_LINES=$n; }
token() { curl -s -u "$CLIENT" -d grant_type=client_credentials "$AUTH/token" | $PY -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'; }
header() { $PY -c 'import sys,base64,json;h=sys.argv[1].split(".")[0];print(json.loads(base64.urlsafe_b64decode(h+"="*(-len(h)%4))))' "$1"; }
call() { echo "\$ curl -H 'Authorization: Bearer <$1>' $API/orders"; curl -s -w '  -> HTTP %{http_code}\n' -H "Authorization: Bearer $2" "$API/orders"; api_log; }
admin() { curl -s -X "$1" -H 'Content-Type: application/json' ${3:+-d "$3"} "$AUTH$2"; echo; }

echo "== 1. Discovery: where are the keys?"
echo "\$ curl $AUTH/.well-known/oauth-authorization-server"
curl -s "$AUTH/.well-known/oauth-authorization-server" | $PY -m json.tool
echo
echo "== 2. The JWKS endpoint"
echo "\$ curl -i $AUTH/.well-known/jwks.json"
curl -s -i "$AUTH/.well-known/jwks.json" | sed 's/\r$//' | $PY -c '
import sys,json
head,body=sys.stdin.read().split("\n\n",1)
print("\n".join(l for l in head.split("\n") if not l.lower().startswith("date:")))
print()
print(json.dumps(json.loads(body),indent=2))'
echo
echo "== 3. Get a token and look at its header"
echo "\$ curl -u $CLIENT -d grant_type=client_credentials $AUTH/token"
curl -s -u "$CLIENT" -d grant_type=client_credentials "$AUTH/token" | cut -c1-90; echo "..."
TOKEN_A=$(token)
echo "Header of token A:"; header "$TOKEN_A"
echo
echo "== 4. Verify by hand (no JWT library)"
$PY verify_by_hand.py "$AUTH" "$TOKEN_A"
echo
echo "== 5. The Orders API verifies token A (first call fetches the JWKS)"
call "token A" "$TOKEN_A"
echo "Second call with the same token, no fetch:"
call "token A" "$TOKEN_A"
for i in 1 2 3 4 5 6 7 8; do curl -s -o /dev/null -H "Authorization: Bearer $TOKEN_A" "$API/orders"; done
echo "After 8 more calls:"; curl -s "$API/debug/jwks-fetches"; echo
echo
echo "== 6. Forged tokens"
FORGED_UNKNOWN=$($PY forge_token.py "$AUTH" attacker-key)
FORGED_REAL_KID=$($PY forge_token.py "$AUTH" 2026-10-a)
call "forged, kid=attacker-key" "$FORGED_UNKNOWN"
call "forged, kid=2026-10-a" "$FORGED_REAL_KID"
for i in $(seq 1 20); do T=$($PY forge_token.py "$AUTH" "random-$i"); curl -s -o /dev/null -H "Authorization: Bearer $T" "$API/orders"; done
echo "After 20 forged tokens with random kids:"; curl -s "$API/debug/jwks-fetches"; echo
echo
echo "== 7. Rotation done too fast: new EC key signs immediately"
admin POST /admin/keys '{"kid":"2026-10-b","kty":"EC","status":"active"}'
echo "The new key in the JWKS:"
curl -s "$AUTH/.well-known/jwks.json" | $PY -c 'import sys,json;print(json.dumps([k for k in json.load(sys.stdin)["keys"] if k["kid"]=="2026-10-b"][0],indent=2))'
TOKEN_B=$(token)
echo "Header of token B:"; header "$TOKEN_B"
call "token B" "$TOKEN_B"
echo "Waiting 31 seconds for the refresh cooldown to pass..."
sleep 31
call "token B" "$TOKEN_B"
echo
echo "== 8. Rotation done right: publish first, sign later"
admin POST /admin/keys '{"kid":"2026-10-c","kty":"RSA","status":"next"}'
echo "Key 2026-10-c is published but not used. Waiting $((${JWKS_CACHE_SECONDS%.*}+1)) seconds for the API cache to expire..."
sleep $((${JWKS_CACHE_SECONDS%.*}+1))
call "token B" "$TOKEN_B"
admin POST /admin/keys/2026-10-c/activate
TOKEN_C=$(token)
echo "Header of token C:"; header "$TOKEN_C"
call "token C" "$TOKEN_C"
echo
echo "== 9. Remove the first key from the JWKS"
admin DELETE /admin/keys/2026-10-a
echo "\$ curl $AUTH/.well-known/jwks.json  (kids only)"
curl -s "$AUTH/.well-known/jwks.json" | $PY -c 'import sys,json;print([k["kid"] for k in json.load(sys.stdin)["keys"]])'
echo "Token A is still accepted while the API's cached copy has key 2026-10-a:"
call "token A" "$TOKEN_A"
echo "Waiting $((${JWKS_CACHE_SECONDS%.*}+1)) seconds for the API cache to expire..."
sleep $((${JWKS_CACHE_SECONDS%.*}+1))
call "token A" "$TOKEN_A"
echo "Total JWKS fetches by the Orders API:"; curl -s "$API/debug/jwks-fetches"; echo
rm -f api.log
