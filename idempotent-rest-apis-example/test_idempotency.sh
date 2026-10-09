#!/usr/bin/env bash
# Checks idempotency by comparing the data on the server, not the responses.
BASE=${BASE:-http://localhost:8000}
KEY='"9b2f6a1e-4c1d-4f7a-9a51-2f3c8e0d7b11"'

before=$(curl -s "$BASE/orders"); echo "before: $before"

curl -s -o /dev/null -X POST "$BASE/orders" -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $KEY" -d '{"items":["lamp"]}'
curl -s -o /dev/null -X POST "$BASE/orders" -H 'Content-Type: application/json' \
  -H "Idempotency-Key: $KEY" -d '{"items":["lamp"]}'

after=$(curl -s "$BASE/orders"); echo "after:  $after"

count() { echo "$1" | python3 -c 'import json,sys; print(json.load(sys.stdin)["count"])'; }
if [ $(( $(count "$after") - $(count "$before") )) -eq 1 ]; then echo "PASS: one new order"; else echo "FAIL"; fi
