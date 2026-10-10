#!/usr/bin/env bash
# Starts the agent on port 9999, runs the plain HTTP client and the SDK client, then stops the agent.
PY=${PYTHON:-python3}
$PY -m uvicorn expense_agent:app --host 127.0.0.1 --port 9999 --log-level warning &
AGENT=$!
trap "kill $AGENT" EXIT
for i in $(seq 1 20); do curl -s -o /dev/null http://127.0.0.1:9999/.well-known/agent-card.json && break; sleep 0.5; done
echo "######## client.py (plain HTTP)"
$PY client.py
echo; echo "######## sdk_client.py (a2a-sdk)"
$PY sdk_client.py
