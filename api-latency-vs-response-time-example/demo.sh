#!/usr/bin/env bash
# Starts the Orders API (HTTPS, port 9200) and the delay proxy (port 9201),
# runs every measurement from the article, and stops both processes.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f cert.pem ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem \
    -days 365 -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost" 2>/dev/null
fi

python3 server.py --tls &
SERVER_PID=$!
python3 delay_proxy.py --listen 9201 --target 9200 --delay-ms 25 &
PROXY_PID=$!
trap 'kill $SERVER_PID $PROXY_PID' EXIT
sleep 1

echo "== One request with headers, through the proxy"
curl -s -i --cacert cert.pem https://localhost:9201/orders/7
echo

echo "== curl timings, straight to the API (no added delay)"
curl -s -o /dev/null -D - --cacert cert.pem -w @curl-timing.txt https://localhost:9200/orders/7

echo "== curl timings through the proxy (25 ms each way)"
curl -s -o /dev/null -D - --cacert cert.pem -w @curl-timing.txt https://localhost:9201/orders/7

echo "== Large export through the proxy: first byte vs last byte"
curl -s -o /dev/null -D - --cacert cert.pem -w @curl-timing.txt https://localhost:9201/orders/export

echo "== 500 requests on one reused connection"
python3 measure.py --url https://localhost:9201/orders/42 -n 500 --csv results-keepalive.csv

echo "== 200 requests with a new connection each time"
python3 measure.py --url https://localhost:9201/orders/42 -n 200 --new-connection
