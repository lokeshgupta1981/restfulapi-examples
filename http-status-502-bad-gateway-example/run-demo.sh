#!/usr/bin/env bash
# Runs every HTTP 502 case against nginx and the orders API and prints the results.
set -u
cd "$(dirname "$0")"
mkdir -p logs tmp
: > logs/error.log
: > logs/access.log

start_app() {
  .venv/bin/uvicorn app:app --host 127.0.0.1 --port 9502 --log-level warning >> logs/app.log 2>&1 &
  sleep 2
}
stop_app() {
  pkill -f "uvicorn app:app --host 127.0.0.1 --port 9502" 2>/dev/null
  sleep 1
}
seen=0
new_error_log_lines() {
  echo "--- new lines in logs/error.log:"
  tail -n +"$((seen + 1))" logs/error.log
  seen=$(wc -l < logs/error.log)
}
section() { echo; echo "===== $1"; }

stop_app
nginx -s stop -p "$PWD" -c "$PWD/nginx.conf" 2>/dev/null
nginx -p "$PWD" -c "$PWD/nginx.conf"
sleep 1

section "Case 0: app running, normal request"
start_app
curl -sS -i http://127.0.0.1:8502/orders/1001; echo

section "Case 1: app down (connection refused), default nginx page"
stop_app
curl -sS -i http://127.0.0.1:8502/orders/1001
new_error_log_lines

section "Case 1b: app down, Problem Details body from nginx"
curl -sS -i http://127.0.0.1:8503/orders/1001
new_error_log_lines

section "Case 2: app process dies before it sends the response"
start_app
curl -sS -i http://127.0.0.1:8503/fail/crash-before-response
new_error_log_lines

section "Case 3: app process dies in the middle of the response body"
start_app
curl -sS -D - -o logs/partial-body.txt http://127.0.0.1:8502/fail/crash-mid-body
echo "curl exit code: $?"
echo "body bytes received: $(wc -c < logs/partial-body.txt)"
new_error_log_lines

section "Case 4: app sends a response header that is too big for proxy_buffer_size"
start_app
curl -sS -i http://127.0.0.1:8503/fail/huge-header
new_error_log_lines

section "Case 4b: the same request on port 8502, where proxy_buffer_size is 32k"
curl -sS -o /dev/null -w "status=%{http_code} header_bytes=%{size_header}\n" http://127.0.0.1:8502/fail/huge-header
new_error_log_lines

section "Case 5: app exits without reading a 900 KB request body (TCP reset)"
start_app
head -c 900000 /dev/zero > logs/upload.bin
curl -sS -i -X POST --data-binary @logs/upload.bin -H "Content-Type: application/octet-stream" http://127.0.0.1:8503/fail/reset
new_error_log_lines

section "Access log (upstream_status shows what nginx saw from the app)"
cat logs/access.log

section "Client retry demo: app down, it starts 3 seconds after the client"
stop_app
.venv/bin/python client.py http://127.0.0.1:8503 &
client_pid=$!
sleep 3
start_app
wait "$client_pid"

stop_app
nginx -s stop -p "$PWD" -c "$PWD/nginx.conf"
