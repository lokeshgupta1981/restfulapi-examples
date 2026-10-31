#!/usr/bin/env bash
# Validates both templates, runs the tests, prices both API types and calls the
# handler through the local stand-in. Needs no AWS account and deploys nothing.
set -u
cd "$(dirname "$0")"
export SAM_CLI_TELEMETRY=0
PORT="${PORT:-8000}"
BASE="http://127.0.0.1:$PORT"
DEMO_KEY="demo-key-not-real"
DEMO_JWT="Bearer demo.jwt.not-real"

echo "### 1. Lint and validate the templates"
for t in template-rest.yaml template-http.yaml; do
  cfn-lint "$t" && echo "cfn-lint $t: no findings"
  sam validate --lint -t "$t" 2>&1 | tail -1
done

echo; echo "### 2. What each template turns into (offline SAM transform)"
python3 show_resources.py template-rest.yaml template-http.yaml 2>&1 | grep -v "unpublished metrics"

echo; echo "### 3. Unit tests"
python3 -m pytest -q -p no:cacheprovider tests 2>&1 | tail -1

echo; echo "### 4. Request charges (us-east-1 prices)"
python3 pricing.py

echo; echo "### 5. The same handler behind both front doors (local stand-in on port $PORT)"
PORT="$PORT" python3 local_gateway.py > stand-in.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT
for _ in $(seq 1 50); do curl -s -o /dev/null "$BASE/" && break; sleep 0.1; done

show() { for a in "$@"; do if [[ $a =~ [[:space:]{\"] ]]; then printf "'%s' " "$a"; else printf "%s " "$a"; fi; done; }
run() { echo; echo "\$ curl $(show "$@")"; curl -s -i "$@" | tr -d '\r' | grep -viE '^(server|date):'; echo; }

run "$BASE/rest/prod/orders/1001" -H "x-api-key: $DEMO_KEY"
run "$BASE/http/orders/1001" -H "Authorization: $DEMO_JWT"
run -X POST "$BASE/rest/prod/orders" -H "x-api-key: $DEMO_KEY" -H "Content-Type: application/json" -d '{"book":"RESTful Web APIs","quantity":2}'
run -X POST "$BASE/http/orders" -H "Authorization: $DEMO_JWT" -H "Content-Type: application/json" -d '{"book":"Designing Web APIs","quantity":1}'
run "$BASE/rest/prod/health"
run "$BASE/http/health"

echo "### Handler log (one JSON line per call)"
grep '^{' stand-in.log
rm -f stand-in.log
