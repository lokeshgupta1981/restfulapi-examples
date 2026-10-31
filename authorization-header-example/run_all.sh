#!/usr/bin/env bash
# Starts all demo servers, runs every demo, prints the output and stops the servers.
# Prepare once (see README.md): pip install -r requirements.txt, playwright install chromium,
# npm install in express/, mvn package in spring/.
cd "$(dirname "$0")"
ROOT=$(pwd)
TOKEN=$(cat demo-token.txt)
LOGS=$(mktemp -d)

(cd express && exec node server.js > "$LOGS/express.log" 2>&1) &
(cd fastapi && exec python3 -m uvicorn main:app --host 127.0.0.1 --port 9762 --no-access-log > "$LOGS/fastapi.log" 2>&1) &
(cd spring && exec java -jar target/auth-header-spring-1.0.0.jar > "$LOGS/spring.log" 2>&1) &
python3 clients/echo_server.py 9771 &
python3 clients/echo_server.py 9772 &
(cd cors && exec python3 cors_server.py > "$LOGS/cors.log" 2>&1) &
trap 'kill $(jobs -p) 2>/dev/null; wait 2>/dev/null; rm -rf "$LOGS"' EXIT

for port in 9761 9762 9763 9771 9772 9781; do
  until curl -s -o /dev/null "http://127.0.0.1:$port/"; do sleep 0.5; done
done

echo '=== 1. FastAPI: request without credentials, then with Basic credentials'
curl -s -i http://127.0.0.1:9762/basic/orders
echo; echo '---'
curl -s -v -u reports-app:demo-pass-123 http://127.0.0.1:9762/basic/orders 2>&1 \
  | grep -E '^> (GET|Host|Authorization)|^< (HTTP|content-type)|^\{'
echo; echo '=== 1b. FastAPI: Bearer token'
curl -s -i -H "Authorization: Bearer $TOKEN" http://127.0.0.1:9762/bearer/orders
echo; echo '---'
curl -s -i http://127.0.0.1:9762/bearer/orders

echo; echo '=== 2. Basic header bytes'
printf '%s' 'reports-app:demo-pass-123' | od -An -c
printf '%s' 'reports-app:demo-pass-123' | base64
echo 'reports-app:demo-pass-123' | base64
printf '%s' 'reports-app:demo-pass-123' | wc -c
printf 'echo value sent to FastAPI -> '
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Basic $(echo 'reports-app:demo-pass-123' | base64)" http://127.0.0.1:9762/basic/orders

echo; echo '=== 3. Decoding the demo JWT claims'
python3 -c "import base64,json,sys; p=sys.argv[1].split('.'); print([json.loads(base64.urlsafe_b64decode(x+'='*(-len(x)%4))) for x in p[:2]])" "$TOKEN"

echo; echo '=== 4. Parsing by hand (fastapi/parse_header.py)'
(cd fastapi && python3 parse_header.py)

echo; echo '=== 5. Express parsing helpers (express/parse_demo.mjs)'
(cd express && exec node parse_demo.mjs)

echo; echo '=== 6. Probe grid (Express 9761, FastAPI 9762, Spring Boot 9763)'
./probe.sh

echo; echo '=== 7. Express 401 response without credentials'
curl -s -i http://127.0.0.1:9761/basic/orders
echo; echo '=== 8. Spring Boot response to Bearer with two spaces'
curl -s -i -H "Authorization: Bearer  $TOKEN" http://127.0.0.1:9763/bearer/orders | grep -i -E '^HTTP|^WWW-Authenticate'
echo '=== 9. FastAPI response to Basic without padding'
curl -s -i -H 'Authorization: Basic cmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw' http://127.0.0.1:9762/basic/orders

echo; echo '=== 10. curl'
clients/clients.sh
echo; echo '=== 11. Python requests'
python3 clients/requests_client.py
echo; echo '=== 12. Node.js fetch'
node clients/fetch_client.mjs
echo; echo '=== 13. Browser-style Basic encoding (btoa and TextEncoder)'
node clients/browser_basic.mjs
echo; echo '=== 14. Java HttpClient'
java clients/HttpClientDemo.java 2>&1 | grep -v JAVA_TOOL_OPTIONS
echo; echo '=== 15. Non-ASCII password in Basic'
python3 clients/charset_check.py
echo '--- FastAPI with the wrong ASCII password, then with the UTF-8 value'
curl -s -w ' %{http_code}\n' -u reports-app:wrong-pass http://127.0.0.1:9762/basic/orders
curl -s -w ' %{http_code}\n' -H 'Authorization: Basic cmVwb3J0cy1hcHA6ZGVtby1jYWbDqS0xMjM=' http://127.0.0.1:9762/basic/orders

echo; echo '=== 16. Chromium CORS and redirect check'
python3 cors/cors_check.py

sleep 1
echo; echo '=== Express server log'; grep -v '^GET / ' "$LOGS/express.log"
echo; echo '=== FastAPI server log'; grep -E '^GET /[a-z]' "$LOGS/fastapi.log"
echo; echo '=== CORS demo server log'; grep -v '9781/ Authorization' "$LOGS/cors.log"
