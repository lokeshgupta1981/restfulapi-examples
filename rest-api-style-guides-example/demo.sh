#!/usr/bin/env bash
# Starts server.py, sends the same requests to the three styles, stops the server.
set -u
cd "$(dirname "$0")"
PORT=${PORT:-8000}
BASE=http://127.0.0.1:$PORT
PORT=$PORT python3 server.py > server.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT
for _ in $(seq 1 50); do curl -s -o /dev/null "$BASE/docs" && break; sleep 0.1; done

show() {  # print the request line, then status line, content-type, error-code header and body
  echo "== $1 $2"
  curl -s -i -X "$1" "$BASE$2" | grep -v -i -E '^(date|server|content-length):' | tr -d '\r'
  echo; echo
}

show GET "/azure/orders?api-version=2026-10-01&maxpagesize=2"
show GET "/azure/orders?maxpagesize=2"
show GET "/azure/orders/ord-9?api-version=2026-10-01"
show GET "/google/v1/orders?pageSize=2"
show GET "/google/v1/orders/ord-9"
show GET "/zalando/orders?limit=2"
show GET "/zalando/orders/ord-9"

# follow the next page in each style
next=$(curl -s "$BASE/azure/orders?api-version=2026-10-01&maxpagesize=2" | python3 -c 'import json,sys;print(json.load(sys.stdin)["nextLink"])')
echo "== GET nextLink (Azure, last page)"; curl -s "$next"; echo; echo
tok=$(curl -s "$BASE/google/v1/orders?pageSize=2" | python3 -c 'import json,sys;print(json.load(sys.stdin)["nextPageToken"])')
echo "== GET /google/v1/orders?pageSize=2&pageToken=$tok (last page)"; curl -s "$BASE/google/v1/orders?pageSize=2&pageToken=$tok"; echo; echo
nxt=$(curl -s "$BASE/zalando/orders?limit=2" | python3 -c 'import json,sys;print(json.load(sys.stdin)["next"])')
echo "== GET next (Zalando, last page)"; curl -s "$nxt"; echo
