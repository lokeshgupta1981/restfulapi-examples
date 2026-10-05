#!/usr/bin/env bash
# Shows the wire format of all three techniques with curl.
# Start a fresh server first: uvicorn server:app --port 9150
BASE=http://127.0.0.1:9150
publish() {
  curl -s -o /dev/null -X POST "$BASE/orders/1042/events" \
    -H "Content-Type: application/json" -d "{\"status\":\"$1\"}"
}

echo "### 1. Publish an event"
curl -s -i -X POST "$BASE/orders/1042/events" \
  -H "Content-Type: application/json" -d '{"status":"packed"}'
echo; echo

echo "### 2. Long poll: an event newer than id 0 exists, so the answer comes at once"
curl -s -w '\n(%{time_total} s)\n' "$BASE/orders/1042/updates?after=0"
echo

echo "### 3. Long poll: nothing newer than id 1, the server holds the request"
(sleep 2; publish shipped) &
curl -s -w '\n(%{time_total} s)\n' "$BASE/orders/1042/updates?after=1"
wait
echo

echo "### 4. Long poll: nothing arrives, the server answers after LONG_POLL_WAIT (25 s)"
curl -s -i -w '\n(%{time_total} s)\n' "$BASE/orders/1042/updates?after=2"
echo

echo "### 5. SSE: one response that stays open, starting after id 2 (curl stops after 4 s)"
(sleep 2; publish out_for_delivery) &
curl -s -i -N --max-time 4 "$BASE/orders/1042/stream?after=2"
wait
echo

echo "### 6. SSE: reconnect with Last-Event-ID: 2"
curl -s -N --max-time 2 -H "Last-Event-ID: 2" "$BASE/orders/1042/stream"
echo

echo "### 7. WebSocket opening handshake (curl prints the HTTP 101 and stops)"
curl -s -i -N --max-time 1 "$BASE/orders/1042/socket?after=2" \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  | sed -n '/^\r$/q;p'
echo

echo "### 8. WebSocket: messages in both directions on one connection"
python ws_client.py 2
