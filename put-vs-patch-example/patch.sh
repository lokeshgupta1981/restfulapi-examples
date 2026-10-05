#!/usr/bin/env bash
# Section 4 and 5.2 of the article: PATCH cases. Start a fresh server first:
#   uvicorn app:app --port 9110
BASE=${BASE:-http://localhost:9110}

show() { echo; echo "### $1"; }

show "1. PATCH with JSON Merge Patch (status only)"
curl -si -X PATCH $BASE/tickets/TCK-1001 -H 'Content-Type: application/merge-patch+json' \
  -d '{"status": "in_progress"}'

show "2. PATCH with null removes a field"
curl -si -X PATCH $BASE/tickets/TCK-1001 -H 'Content-Type: application/merge-patch+json' \
  -d '{"assignee": null}'

show "3. PATCH result that breaks validation"
curl -si -X PATCH $BASE/tickets/TCK-1001 -H 'Content-Type: application/merge-patch+json' \
  -d '{"priority": "urgent"}'

show "4. PATCH sent as application/json"
curl -si -X PATCH $BASE/tickets/TCK-1001 -H 'Content-Type: application/json' \
  -d '{"status": "closed"}'

show "5. OPTIONS"
curl -si -X OPTIONS $BASE/tickets/TCK-1001

show "6. PATCH a ticket that does not exist"
curl -si -X PATCH $BASE/tickets/TCK-9999 -H 'Content-Type: application/merge-patch+json' \
  -d '{"status": "closed"}'

show "7. JSON Patch that appends a label, sent twice without If-Match (retry)"
for attempt in 1 2; do
  curl -si -X PATCH $BASE/tickets/TCK-1001 -H 'Content-Type: application/json-patch+json' \
    -d '[{"op": "add", "path": "/labels/-", "value": "payments"}]'
  echo
done

show "8. JSON Patch that appends a label, sent twice with If-Match (retry)"
for attempt in 1 2; do
  curl -si -X PATCH $BASE/tickets/TCK-1001 -H 'Content-Type: application/json-patch+json' \
    -H 'If-Match: "5"' \
    -d '[{"op": "add", "path": "/labels/-", "value": "urgent"}]'
  echo
done
