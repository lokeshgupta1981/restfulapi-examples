#!/usr/bin/env bash
# Runs every demo and prints the output used in the article.
set -e
cd "$(dirname "$0")"
echo "## Canonical request and signature in Python, Node.js and Java"
python signing.py
node compare.mjs
node client.mjs show
java Sign.java
echo
echo "## Orders API scenarios"
uvicorn server:app --port 9410 > server.log 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID' EXIT
for i in 1 2 3 4 5 6 7 8 9 10; do curl -s -o /dev/null http://localhost:9410/docs && break; sleep 0.5; done
echo "## Request without a signature"
curl -s -i -X POST http://localhost:9410/orders -H 'Content-Type: application/json' -d '{"item":"keyboard","quantity":2}'
echo
node client.mjs
echo
echo "## Server log"
cat server.log
echo
echo "## RFC 9421 HTTP Message Signatures"
python rfc9421_demo.py
echo
echo "## GitHub webhook test vector and re-serialized JSON"
python webhook_vector.py
