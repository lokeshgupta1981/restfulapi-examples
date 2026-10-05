#!/usr/bin/env bash
# Runs every demo in order. Install the dependencies first (see README.md).
set -u
cd "$(dirname "$0")"

echo "## Python strict json module"; python python/strict_parse.py
echo; echo "## Python json5 package"; python python/load_with_json5.py
echo; echo "## Python naive regex strip"; python python/naive_strip.py
echo; echo "## Python comment keys"; python python/comment_keys.py
echo; echo "## Node.js JSON.parse()"; (cd node && node strict-parse.mjs)
echo; echo "## Node.js jsonc-parser, strip-json-comments, json5"; (cd node && node load-config.mjs)
echo; echo "## Node.js jsonc-parser format()"; (cd node && node format.mjs)
echo; echo "## Go encoding/json"; (cd go && go run .)
echo; echo "## Java Jackson 3"; (cd java && mvn -q -B compile exec:java 2>&1 | grep -v JAVA_TOOL_OPTIONS)
echo; echo "## jq"; (cd config && jq . orders-service.jsonc; jq . trailing-comma.jsonc)
echo; echo "## python -m json.tool"; (cd config && python -m json.tool orders-service.jsonc)
echo; echo "## tsc --showConfig"; (cd tsconfig-demo && npx tsc --version && npx tsc --showConfig | grep -v '"/')

echo; echo "## Orders API"
PORT=9185 python api/server.py > /dev/null &
SERVER_PID=$!
until curl -s -o /dev/null http://127.0.0.1:9185/orders/42; do sleep 0.2; done
echo "### POST with a comment"
curl -s -i -X POST http://127.0.0.1:9185/orders -H 'Content-Type: application/json' \
  --data-binary $'{\n  "items": [ { "sku": "BOOK-1", "qty": 2 } ] // gift wrap\n}' | grep -v -E '^(Server|Date):'
echo; echo "### POST without a comment"
curl -s -i -X POST http://127.0.0.1:9185/orders -H 'Content-Type: application/json' \
  -d '{"items":[{"sku":"BOOK-1","qty":2}]}' | grep -v -E '^(Server|Date):'
echo; echo "### fetch() client"
BASE_URL=http://127.0.0.1:9185 node api/client.mjs
kill $SERVER_PID
