#!/usr/bin/env bash
# Section 6.3: the two PUTs from lost_update.sh, both with If-Match.
# Start a fresh server first: uvicorn app:app --port 9110
BASE=${BASE:-http://localhost:9110}

echo "### Both clients GET the ticket"
curl -si $BASE/tickets/TCK-1001 | grep -i '^etag'

echo "### Client A closes the ticket"
curl -s -X PUT $BASE/tickets/TCK-1001 -H 'Content-Type: application/json' \
  -H 'If-Match: "1"' -d '{
  "title": "Checkout page times out", "status": "closed",
  "priority": "normal", "assignee": "maria", "labels": ["checkout"]}' \
  -o /dev/null -w '%{http_code}\n'

echo "### Client B, still holding the old copy, raises the priority"
curl -si -X PUT $BASE/tickets/TCK-1001 -H 'Content-Type: application/json' \
  -H 'If-Match: "1"' -d '{
  "title": "Checkout page times out", "status": "open",
  "priority": "high", "assignee": "maria", "labels": ["checkout"]}'
echo

echo "### Result"
curl -s $BASE/tickets/TCK-1001; echo
