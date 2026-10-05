#!/usr/bin/env bash
# Starts the broker, the Orders API and the shipping consumer, sends requests and events, then stops everything.
set -u
cd "$(dirname "$0")"
PY=.venv/bin/python

.venv/bin/amqtt -c broker.yaml > broker.log 2>&1 &
BROKER=$!
sleep 2
$PY shipping.py > shipping.log 2>&1 &
SHIPPING=$!
.venv/bin/uvicorn app:app --port 9210 --log-level warning > app.log 2>&1 &
API=$!
sleep 3

echo "== POST /orders"
curl -s -i -X POST http://localhost:9210/orders \
  -H "Content-Type: application/json" \
  -d '{"customerId":"cus_42","currency":"EUR","items":[{"sku":"BOOK-1","quantity":2,"unitPrice":"24.95"}]}' | tr -d '\r' > post.txt
cat post.txt; echo
ORDER_ID=$(tail -n 1 post.txt | $PY -c 'import json,sys; print(json.load(sys.stdin)["id"])')

echo "== POST /orders with an empty items array"
curl -s -i -X POST http://localhost:9210/orders \
  -H "Content-Type: application/json" \
  -d '{"customerId":"cus_42","currency":"EUR","items":[]}' | tr -d '\r' | grep -v -E '^(date|server):'; echo

echo "== payment event for $ORDER_ID"
$PY publish.py "payments/$ORDER_ID/completed" "{\"paymentId\":\"pay_7\",\"orderId\":\"$ORDER_ID\",\"amount\":\"49.90\"}"
sleep 1

echo "== GET /orders/$ORDER_ID"
curl -s http://localhost:9210/orders/$ORDER_ID; echo

echo "== a bad OrderPlaced event from another producer"
$PY publish.py orders/placed '{"eventId":"3f0c9a2e-5b1d-4c8e-9a7f-2d6e1b0c4a11","occurredAt":"2026-10-05T09:00:00Z","order":{"id":"ord_1a2b3c4d","customerId":"cus_42","items":[{"sku":"BOOK-1","quantity":2,"unitPrice":"24.95"}],"total":49.9,"currency":"EUR","status":"new","createdAt":"2026-10-05T09:00:00Z"}}'
sleep 1

echo "== app log"; cat app.log
echo "== shipping log"; cat shipping.log
kill $API $SHIPPING $BROKER 2>/dev/null
wait 2>/dev/null
rm -f post.txt
