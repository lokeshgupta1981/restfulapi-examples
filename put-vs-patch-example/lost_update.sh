#!/usr/bin/env bash
# Section 6.1: two clients send PUT from the same old copy, without If-Match.
# Start a fresh server first: uvicorn app:app --port 9110
BASE=${BASE:-http://localhost:9110}

echo "### Both clients GET the ticket (ETag \"1\")"
curl -s $BASE/tickets/TCK-1001; echo

echo "### Client A closes the ticket"
curl -s -X PUT $BASE/tickets/TCK-1001 -H 'Content-Type: application/json' -d '{
  "title": "Checkout page times out", "status": "closed",
  "priority": "normal", "assignee": "maria", "labels": ["checkout"]}' \
  -o /dev/null -w '%{http_code}\n'

echo "### Client B, still holding the old copy, raises the priority"
curl -s -X PUT $BASE/tickets/TCK-1001 -H 'Content-Type: application/json' -d '{
  "title": "Checkout page times out", "status": "open",
  "priority": "high", "assignee": "maria", "labels": ["checkout"]}' \
  -o /dev/null -w '%{http_code}\n'

echo "### Result"
curl -s $BASE/tickets/TCK-1001; echo
