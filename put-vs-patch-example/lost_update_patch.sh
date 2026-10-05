#!/usr/bin/env bash
# Section 6.2: the same edits as merge patches, without If-Match.
# Start a fresh server first: uvicorn app:app --port 9110
BASE=${BASE:-http://localhost:9110}

patch() {
  curl -s -X PATCH $BASE/tickets/TCK-1001 -H 'Content-Type: application/merge-patch+json' \
    -d "$1" -o /dev/null -w "$1 -> %{http_code}\n"
}

echo "### B. Two merge patches that touch different fields"
patch '{"status": "closed"}'
patch '{"priority": "high"}'
curl -s $BASE/tickets/TCK-1001; echo

echo "### C. Two merge patches that touch the same field"
patch '{"assignee": "li"}'
patch '{"assignee": "omar"}'
curl -s $BASE/tickets/TCK-1001; echo
