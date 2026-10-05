#!/usr/bin/env bash
# Starts one provider with 2 events, captures its first raw webhook request on
# port 9142, and polls the change feed by hand: HTTP 200, then HTTP 304.
set -e
cd "$(dirname "$0")"
CAPTURE_FILE=$(mktemp)

python3 - "$CAPTURE_FILE" <<'PY' &
import socket, sys
server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("127.0.0.1", 9142))
server.listen(2)
for number in range(2):
    connection, _ = server.accept()
    data = connection.recv(65536)
    if number == 0:
        open(sys.argv[1], "w").write(data.decode())
    connection.sendall(b"HTTP/1.1 204 No Content\r\nContent-Length: 0\r\n\r\n")
    connection.close()
PY
CAPTURE_PID=$!
sleep 1

python3 provider.py --events 2 --mean-gap 0.5 --webhook-url http://127.0.0.1:9142/webhooks/orders > /dev/null &
PROVIDER_PID=$!
trap 'kill $PROVIDER_PID' EXIT
wait $CAPTURE_PID

echo "# First webhook request, as the receiver on port 9142 sees it"
cat "$CAPTURE_FILE"
rm -f "$CAPTURE_FILE"
echo; echo

echo '$ curl -i "http://127.0.0.1:9140/events?after=0"'
curl -s -i "http://127.0.0.1:9140/events?after=0"
echo; echo
echo '$ curl -i -H '"'"'If-None-Match: "feed-2"'"'"' "http://127.0.0.1:9140/events?after=2"'
curl -s -i -H 'If-None-Match: "feed-2"' "http://127.0.0.1:9140/events?after=2"
