#!/usr/bin/env bash
# Compares DCR and CIMD with curl. Start auth_server.py and client_site.py first.
AS=${AS:-http://127.0.0.1:9000}
SITE=${SITE:-https://localhost:8443}
CB=${CB:-http://127.0.0.1:8765/callback}
CHALLENGE=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGjSstw-cM   # PKCE example value from RFC 7636

enc() { python3 -c "import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=''))" "$1"; }

authorize() {   # $1 = client_id, $2 = redirect_uri
  curl -s -i "$AS/authorize?response_type=code&client_id=$(enc "$1")&redirect_uri=$(enc "$2")&code_challenge=$CHALLENGE&code_challenge_method=S256&state=xyz" \
    | grep -iE '^(HTTP|location|x-demo-consent-screen)|error'
}

echo "== 1. Authorization server metadata"
curl -s "$AS/.well-known/oauth-authorization-server" | python3 -m json.tool
echo

echo "== 2. DCR: register Orders Desktop"
curl -s -i -X POST "$AS/register" -H "Content-Type: application/json" \
  -d "{\"client_name\":\"Orders Desktop\",\"redirect_uris\":[\"$CB\"],\"token_endpoint_auth_method\":\"none\",\"application_type\":\"native\"}" \
  | grep -vE '^(date|server|content-length):'
echo; echo

echo "== 3. DCR: four more installs of the same app register again"
for i in 1 2 3 4; do
  curl -s -X POST "$AS/register" -H "Content-Type: application/json" \
    -d "{\"client_name\":\"Orders Desktop\",\"redirect_uris\":[\"$CB\"],\"token_endpoint_auth_method\":\"none\"}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['client_id'])"
done
echo

echo "== 4. DCR: anyone can register any name"
curl -s -X POST "$AS/register" -H "Content-Type: application/json" \
  -d '{"client_name":"Orders Desktop","redirect_uris":["https://attacker.example/cb"],"token_endpoint_auth_method":"none"}' \
  | python3 -m json.tool
echo

echo "== 5. CIMD: the client's metadata document"
curl -s -i --cacert certs/localhost.pem "$SITE/oauth/client-metadata.json" | grep -vE '^(date|server|content-length):'
echo; echo

echo "== 6. CIMD: five authorization requests with the URL as client_id"
for i in 1 2 3 4; do authorize "$SITE/oauth/client-metadata.json" "$CB" | head -1; done
authorize "$SITE/oauth/client-metadata.json" "$CB" | sed 's/code=[^&]*/code=.../'
echo

echo "== 7. What the server stored"
curl -s "$AS/demo/stats" | python3 -m json.tool
echo

echo "== 8. CIMD: redirect_uri not in the document"
authorize "$SITE/oauth/client-metadata.json" "https://attacker.example/cb"
echo; echo "== 9. CIMD: document copied to another URL"
authorize "$SITE/oauth/copied.json" "$CB"
echo; echo "== 10. CIMD: document with a client secret"
authorize "$SITE/oauth/with-secret.json" "$CB"
echo; echo "== 11. CIMD: document behind a redirect"
authorize "$SITE/oauth/moved.json" "$CB"
echo; echo "== 12. CIMD: document larger than 5 KB"
authorize "$SITE/oauth/huge.json" "$CB"
echo; echo "== 13. CIMD: client_id pointing at a cloud metadata address"
authorize "https://169.254.169.254/latest/meta-data.json" "$CB"
echo; echo "== 14. CIMD: client_id with http"
authorize "http://orders.example/oauth/client-metadata.json" "$CB"
echo
