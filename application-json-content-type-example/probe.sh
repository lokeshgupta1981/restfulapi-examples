#!/usr/bin/env bash
# Sends the same order with different Content-Type headers to the three servers
# and prints the status code, the response Content-Type and the body.
BODY='{"item":"keyboard","quantity":2}'

send() {
  local name="$1" port="$2"; shift 2
  local out
  out=$(curl -s -i -X POST "http://127.0.0.1:$port/orders" "$@")
  local status ctype body
  status=$(printf '%s' "$out" | head -1 | tr -d '\r')
  ctype=$(printf '%s' "$out" | grep -i '^content-type:' | tr -d '\r')
  body=$(printf '%s' "$out" | sed '1,/^\r$/d' | head -c 300)
  printf '%-8s %s | %s\n         %s\n' "$name" "$status" "$ctype" "$body"
}

run_case() {
  local title="$1"; shift
  echo "=== $title"
  send express 9301 "$@"
  send fastapi 9302 "$@"
  send spring  9303 "$@"
  echo
}

run_case "1. Content-Type: application/json" -H 'Content-Type: application/json' --data-raw "$BODY"
run_case "2. Content-Type: application/json; charset=utf-8" -H 'Content-Type: application/json; charset=utf-8' --data-raw "$BODY"
run_case "3. No Content-Type header" -H 'Content-Type:' --data-raw "$BODY"
run_case "4. Content-Type: text/plain" -H 'Content-Type: text/plain' --data-raw "$BODY"
run_case "5. Content-Type: application/x-www-form-urlencoded (curl -d default)" -d "$BODY"
run_case "6. Content-Type: application/vnd.acme.order+json" -H 'Content-Type: application/vnd.acme.order+json' --data-raw "$BODY"
run_case "7. Content-Type: application/json with invalid JSON" -H 'Content-Type: application/json' --data-raw '{"item":"keyboard",}'
run_case "8. Content-Type: application/json; charset=iso-8859-1" -H 'Content-Type: application/json; charset=iso-8859-1' --data-raw "$BODY"
run_case "9. Content-Type: Application/JSON (uppercase)" -H 'Content-Type: Application/JSON' --data-raw "$BODY"
run_case "10. Valid JSON request with Accept: application/xml" -H 'Content-Type: application/json' -H 'Accept: application/xml' --data-raw "$BODY"

echo "=== 11. Express route without a Content-Type check, Content-Type: text/plain"
curl -s -X POST http://127.0.0.1:9301/orders-unchecked -H 'Content-Type: text/plain' --data-raw "$BODY"; echo
echo
echo "=== 12. Full response from the Spring Boot app (curl -i --json)"
curl -s -i http://127.0.0.1:9303/orders --json "$BODY" | tr -d '\r'; echo
echo
echo "=== 13. Request and response headers (curl -v --json, Spring Boot app)"
curl -s -v http://127.0.0.1:9303/orders --json "$BODY" 2>&1 | grep -E '^[<>] |^\{' | tr -d '\r'; echo
