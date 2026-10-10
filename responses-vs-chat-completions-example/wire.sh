#!/usr/bin/env bash
# Raw HTTP for the same question in both API styles (the stub server must be running).
BASE=${BASE:-http://127.0.0.1:8000/v1}

echo "== POST /v1/chat/completions"
curl -s $BASE/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer stub-key" -d '{
  "model": "stub-model-1",
  "messages": [
    {"role": "developer", "content": "You answer questions about orders."},
    {"role": "user", "content": "Hi"}
  ]
}' | python3 -m json.tool

echo; echo "== POST /v1/responses"
curl -s $BASE/responses -H "Content-Type: application/json" -H "Authorization: Bearer stub-key" -d '{
  "model": "stub-model-1",
  "instructions": "You answer questions about orders.",
  "input": "Hi",
  "store": false
}' | python3 -m json.tool

echo; echo "== POST /v1/chat/completions with stream: true"
curl -sN $BASE/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer stub-key" -d '{
  "model": "stub-model-1", "stream": true,
  "messages": [{"role": "user", "content": "When will order A-1001 arrive?"}],
  "tools": [{"type": "function", "function": {"name": "get_order_status",
             "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}}}}]
}'

echo "== POST /v1/responses with stream: true"
curl -sN $BASE/responses -H "Content-Type: application/json" -H "Authorization: Bearer stub-key" -d '{
  "model": "stub-model-1", "stream": true, "store": false,
  "input": "When will order A-1001 arrive?",
  "tools": [{"type": "function", "name": "get_order_status",
             "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}}}]
}'
