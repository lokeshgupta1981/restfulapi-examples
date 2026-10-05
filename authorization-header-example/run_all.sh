#!/usr/bin/env bash
# Runs every demo against the running servers and prints the output.
# Start the servers first (see README.md).
cd "$(dirname "$0")"
TOKEN=$(cat demo-token.txt)

echo '=== Basic header bytes'
printf '%s' 'reports-app:demo-pass-123' | od -An -c
printf '%s' 'reports-app:demo-pass-123' | base64

echo; echo '=== Express parsing helpers (express/parse_demo.mjs)'
(cd express && node parse_demo.mjs)

echo; echo '=== Probe grid (Express 9761, FastAPI 9762, Spring Boot 9763)'
./probe.sh

echo; echo '=== Express 401 response without credentials'
curl -s -i http://127.0.0.1:9761/basic/orders
echo; echo '=== Spring Boot response to Bearer with two spaces'
curl -s -i -H "Authorization: Bearer  $TOKEN" http://127.0.0.1:9763/bearer/orders | grep -i -E '^HTTP|^WWW-Authenticate'
echo '=== FastAPI response to Basic without padding'
curl -s -i -H 'Authorization: Basic cmVwb3J0cy1hcHA6ZGVtby1wYXNzLTEyMw' http://127.0.0.1:9762/basic/orders
echo; echo '=== FastAPI response with no header on /bearer/orders'
curl -s -i http://127.0.0.1:9762/bearer/orders

echo; echo '=== curl'
clients/clients.sh
echo; echo '=== Python requests'
clients/.venv/bin/python clients/requests_client.py
echo; echo '=== Node.js fetch'
node clients/fetch_client.mjs
echo; echo '=== Browser-style Basic encoding (btoa and TextEncoder)'
node clients/browser_basic.mjs
echo; echo '=== Java HttpClient'
java clients/HttpClientDemo.java 2>&1 | grep -v JAVA_TOOL_OPTIONS
echo; echo '=== Non-ASCII password in Basic'
clients/.venv/bin/python clients/charset_check.py

echo; echo '=== Chromium CORS and redirect check'
cors/.venv/bin/python cors/cors_check.py
