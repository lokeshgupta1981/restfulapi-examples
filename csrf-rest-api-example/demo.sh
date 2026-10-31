#!/usr/bin/env bash
# curl walkthrough of the bookstore account API (no browser involved).
# Usage: ./demo.sh            (API on http://localhost:8000)
#        BASE=http://localhost:9000 ./demo.sh
set -u
BASE=${BASE:-http://localhost:8000}
JAR=$(mktemp)
trap 'rm -f "$JAR"' EXIT

run() {  # print the command, then the status line and body
  local shown="$*"
  echo "\$ curl ${shown//$JAR/cookies.txt}"
  curl -s -i "$@" | grep -i -E '^(HTTP/|set-cookie:)|^\{'
  echo
}

curl -s -X POST "$BASE/reset" > /dev/null

echo "== 1. Log in: the API sets a session cookie and also returns a bearer token"
echo "\$ curl -X POST $BASE/login -H 'Content-Type: application/json' -d '{\"username\":\"alice\"}'"
LOGIN=$(curl -s -i -c "$JAR" -X POST "$BASE/login" -H 'Content-Type: application/json' -d '{"username":"alice"}')
echo "$LOGIN" | grep -i -E '^(HTTP/|set-cookie:)|^\{'
ACCESS_TOKEN=$(echo "$LOGIN" | tail -1 | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')
echo

echo "== 2. Protected endpoint with the cookie but without a CSRF token"
run -b "$JAR" -X POST "$BASE/protected/email" -H 'Content-Type: application/json' -d '{"email":"alice@new.example"}'

echo "== 3. Get a CSRF token, then send it in the X-CSRF-Token header"
CSRF=$(curl -s -b "$JAR" "$BASE/api/csrf-token" | python3 -c 'import json,sys;print(json.load(sys.stdin)["csrf_token"])')
echo "csrf_token=$CSRF"
run -b "$JAR" -X POST "$BASE/protected/email" -H 'Content-Type: application/json' -H "X-CSRF-Token: $CSRF" -d '{"email":"alice@new.example"}'

echo "== 4. A forged token (right shape, wrong signature)"
run -b "$JAR" -X POST "$BASE/protected/email" -H 'Content-Type: application/json' -H "X-CSRF-Token: 00000000000000000000000000000000.deadbeef" -d '{"email":"alice@new.example"}'

echo "== 5. The same request marked as cross-site, as a browser would mark it"
run -b "$JAR" -X POST "$BASE/protected/email" -H 'Content-Type: application/json' -H "X-CSRF-Token: $CSRF" -H 'Sec-Fetch-Site: cross-site' -d '{"email":"alice@new.example"}'

echo "== 6. An older browser without Sec-Fetch-Site, sending only Origin"
run -b "$JAR" -X POST "$BASE/protected/email" -H 'Content-Type: application/json' -H "X-CSRF-Token: $CSRF" -H 'Origin: https://evil.example' -d '{"email":"alice@new.example"}'

echo "== 7. The text/plain body an HTML form can send, against the unsafe and the JSON-only endpoints"
run -b "$JAR" -X POST "$BASE/unsafe/email" -H 'Content-Type: text/plain' --data-binary '{"email":"attacker@evil.example","ignore":"="}'
run -b "$JAR" -X POST "$BASE/json-only/email" -H 'Content-Type: text/plain' --data-binary '{"email":"attacker@evil.example","ignore":"="}'

echo "== 8. Bearer endpoint: the cookie alone is not enough, the Authorization header is"
run -b "$JAR" -X POST "$BASE/bearer/email" -H 'Content-Type: application/json' -d '{"email":"alice@new.example"}'
echo "\$ curl -X POST $BASE/bearer/email -H \"Authorization: Bearer \$ACCESS_TOKEN\" -H 'Content-Type: application/json' -d '{\"email\":\"alice@new.example\"}'"
curl -s -i -X POST "$BASE/bearer/email" -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d '{"email":"alice@new.example"}' | grep -i -E '^HTTP/|^\{'
echo
