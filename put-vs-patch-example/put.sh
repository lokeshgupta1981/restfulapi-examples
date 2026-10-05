#!/usr/bin/env bash
# Section 3 and 5.1 of the article: PUT cases. Start a fresh server first:
#   uvicorn app:app --port 9110
BASE=${BASE:-http://localhost:9110}

show() { echo; echo "### $1"; }

show "1. GET the ticket"
curl -si $BASE/tickets/TCK-1001

show "2. PUT the full ticket (change priority to high)"
curl -si -X PUT $BASE/tickets/TCK-1001 -H 'Content-Type: application/json' -d '{
  "title": "Checkout page times out",
  "status": "open",
  "priority": "high",
  "assignee": "maria",
  "labels": ["checkout"]
}'

show "3. PUT the same body again (retry)"
curl -si -X PUT $BASE/tickets/TCK-1001 -H 'Content-Type: application/json' -d '{
  "title": "Checkout page times out",
  "status": "open",
  "priority": "high",
  "assignee": "maria",
  "labels": ["checkout"]
}'

show "4. PUT with only one field"
curl -si -X PUT $BASE/tickets/TCK-1001 -H 'Content-Type: application/json' \
  -d '{"status": "closed"}'

show "5. PUT a new ticket at a URL the client chose"
curl -si -X PUT $BASE/tickets/TCK-1002 -H 'Content-Type: application/json' -d '{
  "title": "Refund email has wrong amount",
  "status": "open",
  "priority": "normal",
  "assignee": "li",
  "labels": []
}'

show "6. PUT from a client that does not know the assignee field"
curl -si -X PUT $BASE/tickets/TCK-1002 -H 'Content-Type: application/json' -d '{
  "title": "Refund email has wrong amount",
  "status": "in_progress",
  "priority": "normal",
  "labels": []
}'
