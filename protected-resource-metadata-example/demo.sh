#!/usr/bin/env bash
# Shows the raw HTTP exchanges with curl. Start both servers first (see README).
API=http://127.0.0.1:8000
AS=http://127.0.0.1:9000

token() {  # $1 = scope, $2 = resource
  curl -s -X POST $AS/token -d grant_type=client_credentials \
    -d client_id=orders-cli -d client_secret=orders-cli-secret \
    -d scope="$1" -d resource="$2" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])"
}

echo "== 1. Call the API without a token"
curl -si $API/orders; echo
echo
echo "== 2. Read the protected resource metadata"
curl -si $API/.well-known/oauth-protected-resource/orders; echo
echo
echo "== 3. The well-known part appended at the end (wrong place)"
curl -si $API/orders/.well-known/oauth-protected-resource; echo
echo
echo "== 4. Read the authorization server metadata (RFC 8414)"
curl -si $AS/.well-known/oauth-authorization-server; echo
echo
echo "== 5. Ask for a token for this resource (RFC 8707 resource parameter)"
curl -si -X POST $AS/token -d grant_type=client_credentials \
  -d client_id=orders-cli -d client_secret=orders-cli-secret \
  -d scope=orders:read -d resource=$API/orders; echo
echo
echo "== 6. Token with the wrong scope (orders:write only)"
curl -si -H "Authorization: Bearer $(token orders:write $API/orders)" $API/orders; echo
echo
echo "== 7. Token issued for another resource"
curl -si -H "Authorization: Bearer $(token orders:read https://other.example/api)" $API/orders; echo
echo
echo "== 8. Token with the right scope and resource"
curl -si -H "Authorization: Bearer $(token orders:read $API/orders)" $API/orders; echo
