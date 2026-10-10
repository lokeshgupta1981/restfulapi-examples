#!/usr/bin/env bash
# Runs every case of the article against the stub on http://localhost:8000.
# Start the stub first: uvicorn stub_server:app --port 8000
set -u
PY=${PYTHON:-python3}
run() { echo "\$ python client.py $*"; $PY client.py "$@"; echo "(exit code $?)"; echo; }

echo "== 1. A finished answer from each vendor format =="
run openai --show-response
run anthropic --show-response
run gemini --show-response

echo "== 2. Truncated answer: the token limit cuts the JSON off =="
run openai --max-tokens 30
run anthropic --max-tokens 30
run gemini --max-tokens 30

echo "== 3. Refusal =="
run openai --scenario refusal --show-response
run anthropic --scenario refusal --show-response

echo "== 4. JSON that ignores the schema (a server without strict mode) =="
run openai --scenario drift

echo "== 5. Schema-valid JSON with a date that is not in the email =="
run anthropic --scenario wrong-date
