#!/usr/bin/env bash
# Sends the same requests to both servers with curl and runs the clients.
# Start both servers first (see README). Override the ports with REST_PORT / TRPC_PORT.
REST="http://localhost:${REST_PORT:-8000}"
TRPC="http://localhost:${TRPC_PORT:-8001}/trpc"
export REST_URL="$REST" TRPC_URL="$TRPC"

step() { echo; echo "### $*"; }

step "REST: GET /books/1"
curl -s -i "$REST/books/1"; echo

step "tRPC: query book.byId"
curl -s -i -G "$TRPC/book.byId" --data-urlencode 'input={"id":"1"}'; echo

step "REST: POST /books with a bad price"
curl -s -i -X POST "$REST/books" -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","priceCents":-5}'; echo

step "tRPC: mutation book.create with a bad price"
curl -s -i -X POST "$TRPC/book.create" -H 'Content-Type: application/json' \
  -d '{"title":"Dune","author":"Frank Herbert","priceCents":-5}'; echo

step "REST: conditional GET (does the server support ETag / 304?)"
ETAG=$(curl -s -D - -o /dev/null "$REST/books/1" | tr -d '\r' | awk -F': ' 'tolower($1)=="etag"{print $2}')
echo "ETag: $ETAG"
curl -s -o /dev/null -w "status with If-None-Match: %{http_code}\n" -H "If-None-Match: $ETAG" "$REST/books/1"

step "tRPC: conditional GET (any ETag?)"
curl -s -D - -o /dev/null -G "$TRPC/book.byId" --data-urlencode 'input={"id":"1"}' | tr -d '\r' | grep -iE '^(etag|cache-control):' || echo "no ETag or Cache-Control header"

step "tRPC: batched request (list + byId in one HTTP call)"
curl -s -G "$TRPC/book.list,book.byId" --data-urlencode 'batch=1' \
  --data-urlencode 'input={"1":{"id":"2"}}'; echo

step "tRPC: batch where one call fails"
curl -s -w "\nHTTP status: %{http_code}\n" -G "$TRPC/book.byId,book.byId" --data-urlencode 'batch=1' \
  --data-urlencode 'input={"0":{"id":"1"},"1":{"id":"99"}}'

step "tRPC client"
npx tsx src/trpc-client.ts

step "REST client (hand-written type)"
npx tsx src/rest-client.ts

step "REST client (types generated from openapi.yaml)"
npx tsx src/rest-typed-client.ts

step "Type check of the normal code"
npx tsc --noEmit -p tsconfig.json && echo "OK, no errors"

step "Type check of the mistakes"
npx tsc --noEmit -p tsconfig.mistakes.json

step "Running the REST mistake anyway"
npx tsx src/mistakes/rest-mistakes.ts
