#!/usr/bin/env bash
# Runs every step of the tutorial and prints the output.
# Usage: npm ci && ./run-all.sh | tee OUTPUTS.txt
set -u
export NO_COLOR=1
AUTH="Authorization: Bearer demo-token"

step() { printf '\n========== %s ==========\n' "$1"; }

step "versions"
node --version
npx redocly --version
npx prism --version
npx openapi-generator-cli version 2>/dev/null | tail -1

step "redocly lint openapi.yaml"
npx redocly lint openapi.yaml 2>&1

step "redocly lint openapi-broken.yaml --format=stylish"
npx redocly lint openapi-broken.yaml --format=stylish 2>&1

step "redocly build-docs"
npx redocly build-docs openapi.yaml --output docs/index.html 2>&1 | tail -2

step "prism mock"
npx prism mock openapi.yaml > prism.log 2>&1 &
PRISM_PID=$!
sleep 8
cat prism.log

step "GET /orders?status=pending"
curl -s -i "http://127.0.0.1:4010/orders?status=pending" -H "$AUTH"; echo

step "GET /orders without a token"
curl -s -i "http://127.0.0.1:4010/orders"; echo

step "GET /orders?limit=500"
curl -s -i "http://127.0.0.1:4010/orders?limit=500" -H "$AUTH"; echo

step "POST /orders valid"
curl -s -i -X POST "http://127.0.0.1:4010/orders" -H "$AUTH" \
  -H "Idempotency-Key: 5f2b7c1e-9a4d-4c55-8f0e-2d6b1a7e3c90" \
  -H "Content-Type: application/json" \
  -d '{"currency":"USD","items":[{"sku":"BOOK-REST-101","quantity":2}]}'; echo

step "POST /orders quantity 0"
curl -s -i -X POST "http://127.0.0.1:4010/orders" -H "$AUTH" \
  -H "Idempotency-Key: 5f2b7c1e-9a4d-4c55-8f0e-2d6b1a7e3c90" \
  -H "Content-Type: application/json" \
  -d '{"currency":"USD","items":[{"sku":"BOOK-REST-101","quantity":0}]}'; echo

step "POST /orders without Idempotency-Key"
curl -s -i -X POST "http://127.0.0.1:4010/orders" -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"currency":"USD","items":[{"sku":"BOOK-REST-101","quantity":2}]}'; echo

step "GET /orders/ord_9999 with Prefer: code=404"
curl -s -i "http://127.0.0.1:4010/orders/ord_9999" -H "$AUTH" -H "Prefer: code=404"; echo

step "generate typescript-fetch client"
rm -rf client
npx openapi-generator-cli generate -i openapi.yaml -g typescript-fetch -o client 2>&1 | grep -E "WARN|ERROR|Exception" || true
find client -name "*.ts" | sort

step "run generated client against the mock"
npx tsx use-client.ts 2>&1

kill "$PRISM_PID" 2>/dev/null; wait "$PRISM_PID" 2>/dev/null

step "OpenAPI 3.2 copy: redocly lint"
npx redocly lint openapi-3.2.yaml 2>&1 | tail -3

step "OpenAPI 3.2 copy: openapi-generator"
npx openapi-generator-cli generate -i openapi-3.2.yaml -g typescript-fetch -o /tmp/client-32 2>&1 \
  | grep -vE "^\s+at |JsonParseException|Source: REDACTED|JAVA_TOOL_OPTIONS" | head -12

step "code-first: FastAPI"
(cd code-first && .venv/bin/python main.py && .venv/bin/pip freeze | grep -iE "^(fastapi|pydantic|starlette)==")
npx redocly lint code-first/generated-openapi.json --format=stylish 2>&1
