#!/usr/bin/env bash
# Send POST (--data) and PUT (-X PUT --data) to /lab/<code> with curl -L
# and print the summary that /echo returns.
BASE=http://127.0.0.1:9190
ORDER='{"sku": "BOOK-42", "qty": 2}'
summary() { python3 -c 'import json,sys; print(json.load(sys.stdin)["summary"])'; }
send() {
  curl -s -L -H 'Content-Type: application/json' -H 'Authorization: Bearer demo-token' \
    --data "$ORDER" "$@" | summary
}
for code in 301 302 303 307 308; do printf 'POST %s -> ' "$code"; send "$BASE/lab/$code"; done
for code in 301 302 303 307 308; do printf 'PUT  %s -> ' "$code"; send -X PUT "$BASE/lab/$code"; done
printf 'POST 308 to another host -> '; send "$BASE/lab/308?cross=1"
printf 'POST 301 with -X POST -> '; send -X POST "$BASE/lab/301"
printf 'POST 301 with --post301 -> '; send --post301 "$BASE/lab/301"
