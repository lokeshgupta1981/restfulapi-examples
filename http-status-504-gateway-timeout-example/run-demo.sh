#!/usr/bin/env bash
# Runs every HTTP 504 case against nginx and the orders API and prints the results.
set -u
cd "$(dirname "$0")"
mkdir -p logs tmp
: > logs/error.log
: > logs/access.log
: > logs/app.log

seen=0
new_error_log_lines() {
  echo "--- new lines in logs/error.log:"
  tail -n +"$((seen + 1))" logs/error.log
  seen=$(wc -l < logs/error.log)
}
section() { echo; echo "===== $1"; }
timed_curl() { curl -sS -i -w "\n[curl time_total: %{time_total} s]\n" "$@"; }

nginx -s stop -p "$PWD" -c "$PWD/nginx.conf" 2>/dev/null
pkill -f "uvicorn app:app --host 127.0.0.1 --port 9504" 2>/dev/null
pkill -f "stuck_listener.py" 2>/dev/null
sleep 1

.venv/bin/uvicorn app:app --host 127.0.0.1 --port 9504 > logs/app.log 2>&1 &
.venv/bin/python stuck_listener.py > logs/stuck.log 2>&1 &
nginx -p "$PWD" -c "$PWD/nginx.conf"
sleep 2

section "Case 0: the report takes 1 s, proxy_read_timeout is 3 s"
timed_curl "http://127.0.0.1:8504/reports/sales?seconds=1"

section "Case 1: the report takes 5 s, proxy_read_timeout is 3 s"
timed_curl "http://127.0.0.1:8504/reports/sales?seconds=5"
new_error_log_lines
sleep 3
echo "--- app log (the app kept working after nginx gave up):"
cat logs/app.log

section "Case 2: POST /orders takes 5 s, the client gets HTTP 504, but the order exists"
timed_curl -X POST "http://127.0.0.1:8504/orders?seconds=5"
new_error_log_lines
sleep 3
timed_curl "http://127.0.0.1:8504/orders"

section "Case 3: the upstream never accepts the TCP connection (proxy_connect_timeout 2 s)"
timed_curl "http://127.0.0.1:8504/legacy/status"
new_error_log_lines

section "Case 4: a streaming export sends a line every 2 s for 8 s, no HTTP 504"
timed_curl "http://127.0.0.1:8504/reports/export"
new_error_log_lines

section "Case 5: the app enforces its own 2 s budget and returns HTTP 503"
timed_curl "http://127.0.0.1:8504/inventory"
new_error_log_lines

section "Case 6: /reports/yearly takes 5 s, its location sets proxy_read_timeout 10s"
timed_curl "http://127.0.0.1:8504/reports/yearly"
new_error_log_lines

section "Case 7: slow work as a background job: HTTP 202 plus a status URL"
timed_curl -X POST "http://127.0.0.1:8504/exports" | tee logs/export-response.txt
location=$(tr -d '\r' < logs/export-response.txt | awk -F': ' 'tolower($1)=="location" {print $2}')
timed_curl "http://127.0.0.1:8504$location"
sleep 7
timed_curl "http://127.0.0.1:8504$location"

section "Access log with timing variables"
cat logs/access.log

section "Full app log"
cat logs/app.log

nginx -s stop -p "$PWD" -c "$PWD/nginx.conf"
pkill -f "uvicorn app:app --host 127.0.0.1 --port 9504"
pkill -f "stuck_listener.py"
