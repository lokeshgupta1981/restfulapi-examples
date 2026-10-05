#!/usr/bin/env bash
# curl calls against python/api_server.py. Needs curl, jq and GNU coreutils base64.
# Start the server first: python3 python/api_server.py
set -u
API="${API_URL:-http://127.0.0.1:9170}"
cd "$(dirname "$0")"

step() { printf '\n### %s\n' "$1"; }

step "1. Base64URL cursor: first page, then the next page"
curl -s "$API/orders"
echo
CURSOR=$(curl -s "$API/orders" | jq -r .next_cursor)
curl -s "$API/orders?cursor=$CURSOR"
echo

step "2. Standard Base64 cursor pasted into the query string"
LEGACY=$(curl -s "$API/legacy/orders" | jq -r .next_cursor)
echo "next_cursor: $LEGACY"
curl -s "$API/legacy/orders?cursor=$LEGACY"
echo
echo "--- same cursor, percent-encoded with --data-urlencode:"
curl -s -G "$API/legacy/orders" --data-urlencode "cursor=$LEGACY"

step "3. File content in JSON: standard Base64 on one line"
jq -n --arg c "$(base64 -w 0 pixel.png)" '{file_name: "pixel.png", content_base64: $c}' \
  | curl -s -i -X POST "$API/attachments" -H "Content-Type: application/json" --data-binary @-
echo
echo "--- Base64URL text instead:"
jq -n --arg c "$(base64 -w 0 pixel.png | tr '+/' '-_')" '{file_name: "pixel.png", content_base64: $c}' \
  | curl -s -X POST "$API/attachments" -H "Content-Type: application/json" --data-binary @-
echo
echo "--- base64 without -w 0 (line break after 76 characters):"
jq -n --arg c "$(base64 pixel.png)" '{file_name: "pixel.png", content_base64: $c}' \
  | curl -s -X POST "$API/attachments" -H "Content-Type: application/json" --data-binary @-
echo
echo "--- sha256 of the file, in Base64, for comparison:"
openssl dgst -sha256 -binary pixel.png | base64

step "4. Basic authentication"
curl -s -u reports-app:s3cret-42 "$API/reports"
echo
echo "--- header built with echo (adds a newline):"
BAD=$(echo "reports-app:s3cret-42" | base64)
GOOD=$(printf '%s' "reports-app:s3cret-42" | base64)
echo "echo | base64       : $BAD"
echo "printf '%s' | base64: $GOOD"
curl -s -i -H "Authorization: Basic $BAD" "$API/reports"
echo
echo "$BAD" | base64 -d | od -c | head -2

step "5. Command line: base64url with GNU basenc"
printf '%s' '<<???>>' | basenc --base64url
printf '%s' 'PDw_Pz8-Pg' | basenc --base64url -d; echo " (exit code $?)"
printf '%s' 'PDw_Pz8-Pg==' | basenc --base64url -d; echo " (exit code $?)"
printf '%s' '<<???>>' | base64 | tr '+/' '-_' | tr -d '='
