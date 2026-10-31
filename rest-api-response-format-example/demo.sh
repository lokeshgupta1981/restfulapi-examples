#!/usr/bin/env bash
# Every curl exchange shown in the article. Start both servers first:
#   uvicorn app:app --port 9120            (the consistent format)
#   uvicorn default_app:app --port 9121    (FastAPI's default errors, for comparison)
# The date and server headers are left out to keep the output short.
BASE=${BASE:-http://localhost:9120}
DEFAULT=${DEFAULT:-http://localhost:9121}
TMP=$(mktemp -d)

show() { echo; echo "### $1"; }
req() {
  curl -s -D "$TMP/h" -o "$TMP/b" "$@"
  grep -viE '^(date|server):' "$TMP/h" | tr -d '\r'
  if [ -s "$TMP/b" ]; then python3 -m json.tool --indent 2 "$TMP/b"; fi
}

show "1. Default FastAPI errors: missing book"
req $DEFAULT/books/9999
show "2. Default FastAPI errors: unknown URL"
req $DEFAULT/no-such-url
show "3. Default FastAPI errors: invalid body"
req -X POST $DEFAULT/books -H 'Content-Type: application/json' \
  -d '{"title": "API Design Patterns", "author": "JJ Geewax", "isbn": "9781617295850", "price": {"amount": "59.99", "currency": "usd"}}'

show "4. Envelope with 200 for everything: missing book"
req $BASE/envelope/books/9999

show "5. A single book"
req $BASE/books/1001

show "6. First page of books"
req "$BASE/books?limit=2"
show "7. Following the next link"
req "$BASE/books?limit=2&cursor=MTAwMg"
show "8. A filter that matches nothing"
req "$BASE/books?author=Nobody"

show "9. Create a book"
req -X POST $BASE/books -H 'Content-Type: application/json' \
  -d '{"title": "REST in Practice", "author": "Jim Webber", "isbn": "9780596805821", "price": {"amount": "34.99", "currency": "USD"}, "publishedOn": "2010-09-01"}'
show "10. Delete it"
req -X DELETE $BASE/books/1006

show "11. Missing book"
req $BASE/books/9999
show "12. Invalid body"
req -X POST $BASE/books -H 'Content-Type: application/json' \
  -d '{"title": "API Design Patterns", "author": "JJ Geewax", "isbn": "9781617295850", "price": {"amount": "59.99", "currency": "usd"}}'
show "13. Malformed JSON"
req -X POST $BASE/books -H 'Content-Type: application/json' -d '{"title": '
show "14. Wrong method"
req -X PUT $BASE/books/1001
show "15. Invalid page size"
req "$BASE/books?limit=500"

show "16. What curl --fail sees (exit code 22 means an HTTP error)"
curl -sf -o /dev/null $BASE/envelope/books/9999; echo "envelope:     exit code $?"
curl -sf -o /dev/null $BASE/books/9999; echo "status codes: exit code $?"

rm -r "$TMP"
