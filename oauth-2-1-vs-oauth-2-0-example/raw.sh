#!/usr/bin/env bash
# Full HTTP responses (curl -i) quoted in the article. Start both servers first.
V20=${V20:-http://127.0.0.1:8000}
B=${V21:-http://127.0.0.1:8001}
TOK=$(mktemp)
V=$(openssl rand -base64 48 | tr '+/' '-_' | tr -d '=\n'); C=$(printf '%s' "$V" | openssl dgst -sha256 -binary | basenc --base64url | tr -d '=')
echo "### Authorization code + PKCE on 2.1 (code_challenge=$C)"
L=$(curl -s -i "$B/authorize?response_type=code&client_id=bookstore-spa&redirect_uri=https://bookstore.example/callback&state=s1&code_challenge=$C&code_challenge_method=S256" | grep -i '^location' | tr -d '\r'); echo "$L"
CODE=$(echo "$L" | sed -E 's/.*[?&]code=([^&]+).*/\1/')
curl -s -X POST $B/token -d grant_type=authorization_code -d client_id=bookstore-spa -d code=$CODE -d code_verifier=$V | tee "$TOK"; echo
echo "### Token in the query string on 2.1"
curl -s -i "$B/books?access_token=$(jq -r .access_token "$TOK")" | grep -v -i '^date\|^server'; echo
echo "### Password grant on 2.0, then on 2.1"
curl -s -i -X POST $V20/token -d grant_type=password -d client_id=bookstore-spa -d username=asha -d password=demo-password-asha | grep -v -i '^date\|^server'; echo
curl -s -i -X POST $B/token -d grant_type=password -d client_id=bookstore-spa -d username=asha -d password=demo-password-asha | grep -v -i '^date\|^server'; echo
echo "### Same refresh token twice on 2.1"
RT=$(jq -r .refresh_token "$TOK")
for i in 1 2; do curl -s -i -X POST $B/token -d grant_type=refresh_token -d client_id=bookstore-spa -d refresh_token=$RT | grep -v -i '^date\|^server'; echo; done
rm -f "$TOK"
