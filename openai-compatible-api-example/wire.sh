#!/usr/bin/env bash
# Raw HTTP against the server: a model list, an error body and a short stream.
BASE=${BASE:-http://127.0.0.1:8000/v1}

echo "== GET /v1/models"
curl -s $BASE/models -H "Authorization: Bearer demo-key" | python3 -m json.tool

echo; echo "== POST /v1/chat/completions with an unknown model"
curl -s -i $BASE/chat/completions -H "Authorization: Bearer demo-key" -H "Content-Type: application/json" \
  -d '{"model": "no-such-model", "messages": [{"role": "user", "content": "hi"}]}' | grep -v -i '^date:\|^server:'

echo; echo; echo "== POST /v1/chat/completions with stream and include_usage"
curl -s -N $BASE/chat/completions -H "Authorization: Bearer demo-key" -H "Content-Type: application/json" \
  -d '{"model": "echo-1", "stream": true, "stream_options": {"include_usage": true},
       "messages": [{"role": "user", "content": "hi"}]}'
