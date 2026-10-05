#!/usr/bin/env bash
# Sends the same request with different Authorization headers to the three apps
# and prints the status code each one returns.
# Demo credentials only: reports-app / demo-pass-123 and the token in demo-token.txt.
cd "$(dirname "$0")"
TOKEN=$(cat demo-token.txt)
B64='cmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw=='
NOPAD='cmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw'
WRONG='d3JvbmctYXBwOndyb25nLXBhc3M='   # wrong-app:wrong-pass

row() {
  local label="$1" path="$2"; shift 2
  local line
  line=$(printf '%-44s' "$label")
  for port in 9761 9762 9763; do
    line+=$(printf '%6s' "$(curl -s -o /dev/null -w '%{http_code}' "$@" "http://127.0.0.1:$port$path")")
  done
  echo "$line"
}

printf '%-44s%6s%6s%6s\n' 'Authorization header sent' 'Expr' 'Fast' 'Spr'
row 'Basic <base64>'                        /basic/orders  -H "Authorization: Basic $B64"
row 'basic <base64> (lowercase scheme)'     /basic/orders  -H "Authorization: basic $B64"
row 'BASIC <base64> (uppercase scheme)'     /basic/orders  -H "Authorization: BASIC $B64"
row 'Basic<base64> (no space)'              /basic/orders  -H "Authorization: Basic$B64"
row 'Basic  <base64> (two spaces)'          /basic/orders  -H "Authorization: Basic  $B64"
row 'Basic <base64 without padding>'        /basic/orders  -H "Authorization: Basic $NOPAD"
row 'Basic reports-app:demo-pass-123'       /basic/orders  -H "Authorization: Basic reports-app:demo-pass-123"
row 'two headers: valid, then wrong'        /basic/orders  -H "Authorization: Basic $B64" -H "Authorization: Basic $WRONG"
row 'two headers: wrong, then valid'        /basic/orders  -H "Authorization: Basic $WRONG" -H "Authorization: Basic $B64"
row 'no Authorization header'               /basic/orders
row 'Bearer <token>'                        /bearer/orders -H "Authorization: Bearer $TOKEN"
row 'bearer <token> (lowercase scheme)'     /bearer/orders -H "Authorization: bearer $TOKEN"
row 'Bearer<token> (no space)'              /bearer/orders -H "Authorization: Bearer$TOKEN"
row 'Bearer  <token> (two spaces)'          /bearer/orders -H "Authorization: Bearer  $TOKEN"
row 'Bearer "<token>" (quoted)'             /bearer/orders -H "Authorization: Bearer \"$TOKEN\""
row '<token> (no scheme)'                   /bearer/orders -H "Authorization: $TOKEN"
row 'Token <token> (wrong scheme)'          /bearer/orders -H "Authorization: Token $TOKEN"
row 'two headers: Bearer <token> twice'     /bearer/orders -H "Authorization: Bearer $TOKEN" -H "Authorization: Bearer $TOKEN"
