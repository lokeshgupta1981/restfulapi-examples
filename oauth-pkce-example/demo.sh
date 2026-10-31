#!/usr/bin/env bash
# The whole PKCE flow with curl and openssl. Start the server first:
#   uvicorn server:app --port 8000
# Set AUTH_URL if you use another port.
set -euo pipefail
AUTH_URL="${AUTH_URL:-http://127.0.0.1:8000}"
CLIENT_ID="bookstore-app"
REDIRECT_URI="com.example.bookstore:/oauth/callback"
REDIRECT_ENC="com.example.bookstore%3A%2Foauth%2Fcallback"

b64url() { basenc --base64url -w0 | tr -d '='; }

echo "== 1. Create the code_verifier and the S256 code_challenge"
VERIFIER=$(openssl rand 32 | b64url)
CHALLENGE=$(printf '%s' "$VERIFIER" | openssl dgst -sha256 -binary | b64url)
echo "code_verifier  = $VERIFIER"
echo "code_challenge = $CHALLENGE"

echo
echo "== 2. Authorization request (the app opens this URL in the browser)"
URL="$AUTH_URL/authorize?response_type=code&client_id=$CLIENT_ID&redirect_uri=$REDIRECT_ENC&state=af0ifjsldkj&code_challenge=$CHALLENGE&code_challenge_method=S256"
echo "GET $URL"
curl -s -i "$URL" | grep -iE '^(HTTP|location)'
CODE=$(curl -s -o /dev/null -w '%{redirect_url}' "$URL" | sed -E 's/.*[?&]code=([^&]+).*/\1/')

echo
echo "== 3. Token request with the code_verifier"
curl -s -i -X POST "$AUTH_URL/token" \
  -d grant_type=authorization_code \
  -d "code=$CODE" \
  --data-urlencode "redirect_uri=$REDIRECT_URI" \
  -d "client_id=$CLIENT_ID" \
  -d "code_verifier=$VERIFIER" | tr -d '\r' | grep -vE '^(date|server|content-length):'
echo

echo
echo "== 4. Redeeming the same code a second time"
curl -s -X POST "$AUTH_URL/token" \
  -d grant_type=authorization_code -d "code=$CODE" \
  --data-urlencode "redirect_uri=$REDIRECT_URI" \
  -d "client_id=$CLIENT_ID" -d "code_verifier=$VERIFIER"
echo

echo
echo "== 5. Asking for the plain method"
curl -s -i \
  "$AUTH_URL/authorize?response_type=code&client_id=$CLIENT_ID&redirect_uri=$REDIRECT_ENC&state=xyz&code_challenge=$VERIFIER&code_challenge_method=plain" | grep -iE '^(HTTP|location)'
