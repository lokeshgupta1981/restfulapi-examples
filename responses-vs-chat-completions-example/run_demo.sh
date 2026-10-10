#!/usr/bin/env bash
# Starts the stub server, runs both demos and the raw HTTP calls, then stops the server.
PY=${PYTHON:-python3}
$PY -m uvicorn stub_server:app --host 127.0.0.1 --port 8000 --log-level warning &
SERVER=$!
trap "kill $SERVER" EXIT
for i in 1 2 3 4 5 6 7 8 9 10; do curl -s -o /dev/null http://127.0.0.1:8000/docs && break; sleep 0.5; done
echo "######## chat_demo.py"; $PY chat_demo.py
echo; echo "######## responses_demo.py"; $PY responses_demo.py
echo; echo "######## wire.sh"; ./wire.sh
