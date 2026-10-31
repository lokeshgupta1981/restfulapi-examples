#!/usr/bin/env bash
# The raw HTTP exchanges from the article, with curl.
# Start the two servers first (see README.md), then run ./demo.sh
set -u
V20=${V20:-http://127.0.0.1:8000}   # OAUTH_PROFILE=2.0
V21=${V21:-http://127.0.0.1:8001}   # OAUTH_PROFILE=2.1
CB=https://bookstore.example/callback
AUTHZ="client_id=bookstore-spa&redirect_uri=$CB&state=s1"

# Authorization code + PKCE (S256); prints the token response.
pkce_tokens() {
  local base=$1 verifier challenge code
  verifier=$(openssl rand -base64 48 | tr '+/' '-_' | tr -d '=\n')
  challenge=$(printf '%s' "$verifier" | openssl dgst -sha256 -binary | basenc --base64url | tr -d '=')
  code=$(curl -s -i "$base/authorize?response_type=code&$AUTHZ&code_challenge=$challenge&code_challenge_method=S256" \
         | grep -i '^location' | sed -E 's/.*[?&]code=([^&]+).*/\1/' | tr -d '\r')
  curl -s -X POST "$base/token" -d grant_type=authorization_code -d client_id=bookstore-spa \
       -d code="$code" -d code_verifier="$verifier"
}

echo "### 1. Implicit grant (response_type=token)"
for base in "$V20" "$V21"; do
  echo "--- $base"
  curl -s -i "$base/authorize?response_type=token&$AUTHZ" | grep -i -E '^HTTP|^location'
done

echo; echo "### 2. Password grant"
for base in "$V20" "$V21"; do
  echo "--- $base"
  curl -s -X POST "$base/token" -d grant_type=password -d client_id=bookstore-spa \
       -d username=asha -d password=demo-password-asha | jq -c '{access_token, error, error_description}'
done

echo; echo "### 3. Authorization code without PKCE"
for base in "$V20" "$V21"; do
  echo "--- $base"
  curl -s -i "$base/authorize?response_type=code&$AUTHZ" | grep -i -E '^HTTP|^location'
done

echo; echo "### 4. Look-alike redirect URI"
for base in "$V20" "$V21"; do
  echo "--- $base"
  curl -s -i "$base/authorize?response_type=code&client_id=bookstore-spa&redirect_uri=https://bookstore.example.attacker.example/steal" \
    | grep -i -E '^HTTP|^location|error'
done

echo; echo "### 5. Bearer token in the query string"
for base in "$V20" "$V21"; do
  echo "--- $base"
  TOKEN=$(curl -s -X POST "$base/token" -d grant_type=password -d client_id=bookstore-spa \
          -d username=asha -d password=demo-password-asha | jq -r '.access_token // empty')
  [ -z "$TOKEN" ] && TOKEN=$(pkce_tokens "$base" | jq -r .access_token)   # 2.1: no password grant
  echo -n "query string : "; curl -s -o /dev/null -w '%{http_code}\n' "$base/books?access_token=$TOKEN"
  echo -n "header       : "; curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" "$base/books"
done

echo; echo "### 6. Refresh token used twice (2.1 rotates it)"
RT=$(pkce_tokens "$V21" | jq -r .refresh_token)
for i in 1 2; do
  echo "--- use $i of the same refresh token"
  curl -s -X POST "$V21/token" -d grant_type=refresh_token -d client_id=bookstore-spa -d refresh_token="$RT" \
    | jq -c 'if .access_token then {access_token: (.access_token[0:8]+"..."), refresh_token: (.refresh_token[0:8]+"...")} else . end'
done
