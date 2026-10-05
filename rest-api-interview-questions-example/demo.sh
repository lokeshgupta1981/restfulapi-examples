#!/usr/bin/env bash
# Sends the requests from the article, in the order the article shows them.
# Start a fresh API first (IDs start at 1001): uvicorn app:app --port 9230
# The Date, Server and Content-Length headers are removed from the output.

run() {
  echo "### $1"
  echo "\$ $2"
  eval "$2" 2>/dev/null | grep -v -i -E '^(date|server|content-length):' | tr -d '\r'
  echo
  echo
}

run "1. Unsupported method on the collection (question 1.12)" \
  "curl -i -X PUT http://localhost:9230/orders -H \"Authorization: Bearer writer-token\" -H \"Content-Type: application/json\" -d '{}'"
run "2. POST creates order 1001 (question 2.2)" \
  "curl -i -X POST http://localhost:9230/orders -H \"Authorization: Bearer writer-token\" -H \"Content-Type: application/json\" -d '{\"product\":\"keyboard\",\"quantity\":2}'"
run "3. POST creates order 1002, status code only (question 2.3)" \
  "curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:9230/orders -H \"Authorization: Bearer writer-token\" -H \"Content-Type: application/json\" -d '{\"product\":\"cable\",\"quantity\":1}'"
run "4. DELETE order 1002 (question 2.3)" \
  "curl -i -X DELETE http://localhost:9230/orders/1002 -H \"Authorization: Bearer writer-token\""
run "5. Same DELETE again (question 2.3)" \
  "curl -i -X DELETE http://localhost:9230/orders/1002 -H \"Authorization: Bearer writer-token\""
run "6. POST without a token (question 2.5)" \
  "curl -i -X POST http://localhost:9230/orders -H \"Content-Type: application/json\" -d '{\"product\":\"keyboard\",\"quantity\":2}'"
run "7. POST with a read-only token (question 2.5)" \
  "curl -i -X POST http://localhost:9230/orders -H \"Authorization: Bearer reader-token\" -H \"Content-Type: application/json\" -d '{\"product\":\"keyboard\",\"quantity\":2}'"
run "8. POST with quantity 0 (question 2.6)" \
  "curl -i -X POST http://localhost:9230/orders -H \"Authorization: Bearer writer-token\" -H \"Content-Type: application/json\" -d '{\"product\":\"keyboard\",\"quantity\":0}'"
run "9. POST with broken JSON (question 2.6)" \
  "curl -i -X POST http://localhost:9230/orders -H \"Authorization: Bearer writer-token\" -H \"Content-Type: application/json\" -d '{\"product\": \"keyboard\",'"
run "10. Client A revalidates order 1001 (question 3.1)" \
  "curl -i http://localhost:9230/orders/1001 -H \"Authorization: Bearer reader-token\" -H 'If-None-Match: \"4b3954d2450d7a4b\"'"
run "11. Client B replaces order 1001 (question 3.2)" \
  "curl -i -X PUT http://localhost:9230/orders/1001 -H \"Authorization: Bearer writer-token\" -H \"Content-Type: application/json\" -d '{\"product\":\"keyboard\",\"quantity\":5}'"
run "12. Client A writes with its old ETag (question 3.2)" \
  "curl -i -X PUT http://localhost:9230/orders/1001 -H \"Authorization: Bearer writer-token\" -H \"Content-Type: application/json\" -H 'If-Match: \"4b3954d2450d7a4b\"' -d '{\"product\":\"keyboard\",\"quantity\":9}'"
run "13. POST with an Idempotency-Key (question 3.3)" \
  "curl -i -X POST http://localhost:9230/orders -H \"Authorization: Bearer writer-token\" -H \"Content-Type: application/json\" -H \"Idempotency-Key: 7f3c9a\" -d '{\"product\":\"mouse\",\"quantity\":1}'"
run "14. Same POST retried with the same key (question 3.3)" \
  "curl -i -X POST http://localhost:9230/orders -H \"Authorization: Bearer writer-token\" -H \"Content-Type: application/json\" -H \"Idempotency-Key: 7f3c9a\" -d '{\"product\":\"mouse\",\"quantity\":1}'"
run "15. First page of orders (question 3.4)" \
  "curl -i \"http://localhost:9230/orders?limit=1\" -H \"Authorization: Bearer reader-token\""
