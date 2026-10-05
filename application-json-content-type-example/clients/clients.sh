#!/usr/bin/env bash
# Sends the same order from curl, Python requests, Node.js fetch and Java HttpClient
# to the echo server and prints the headers each one sent.
cd "$(dirname "$0")"
URL=http://127.0.0.1:9300/orders
BODY='{"item":"keyboard","quantity":2}'
echo "--- curl"
curl -s -H 'X-Client: curl -d' -d "$BODY" $URL; echo
curl -s -H 'X-Client: curl --json' --json "$BODY" $URL; echo
echo "--- Python requests"
../fastapi/.venv/bin/python requests_client.py
echo "--- Node.js fetch"
node fetch_client.mjs
echo "--- Java HttpClient"
java HttpClientDemo.java 2>/dev/null
echo "--- Node.js: parsing a non-JSON response"
node parse_check.mjs
