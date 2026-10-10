#!/usr/bin/env bash
# Starts the server twice (strict on port 8000, lenient on port 8001), runs the checks and the raw calls.
PY=${PYTHON:-python3}
$PY -m uvicorn server:app --host 127.0.0.1 --port 8000 --log-level warning &
STRICT=$!
LENIENT=1 $PY -m uvicorn server:app --host 127.0.0.1 --port 8001 --log-level warning &
LOOSE=$!
trap "kill $STRICT $LOOSE" EXIT
for i in $(seq 1 20); do curl -s -o /dev/null http://127.0.0.1:8001/docs && break; sleep 0.5; done

echo "######## switch_demo.py"
OPENAI_API_KEY=${OPENAI_API_KEY:-placeholder} $PY switch_demo.py
echo; echo "######## strict server"
OPENAI_BASE_URL=http://127.0.0.1:8000/v1 BURST_KEY=burst-key $PY check_compat.py
echo; echo "######## lenient server (LENIENT=1)"
OPENAI_BASE_URL=http://127.0.0.1:8001/v1 BURST_KEY=burst-key $PY check_compat.py
echo; echo "######## wire.sh"
./wire.sh
