#!/usr/bin/env bash
# Starts server.py, runs every example and prints the output. Usage: ./demo.sh > OUTPUTS.txt
set -u
cd "$(dirname "$0")"
start() { uvicorn server:app --port 8000 --log-level warning & PID=$!; sleep 2; }
stop() { kill "$PID"; wait "$PID" 2>/dev/null; }

start
echo "===== curl: a 503 without Retry-After, then the same call again"
curl -si "http://127.0.0.1:8000/orders/2001?fail=1"; echo
curl -si "http://127.0.0.1:8000/orders/2001?fail=1"; echo
echo
echo "===== curl: a 429 with Retry-After"
curl -si "http://127.0.0.1:8000/reports/books"; echo
for s in 503 429 404 post-naive post-no-key post; do
  echo; echo "===== python client.py $s"; python3 client.py "$s"
done
stop; start
echo; echo "===== python requests_retry.py (urllib3 Retry)"
python3 requests_retry.py 2>&1
echo; echo "===== node retry.mjs"
node retry.mjs
echo; echo "===== python test_retry.py"
python3 test_retry.py
stop
echo; echo "===== python herd_sim.py"
python3 herd_sim.py
