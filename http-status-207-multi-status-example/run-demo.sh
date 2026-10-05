#!/usr/bin/env bash
# Starts the Express orders API (port 9207) and a WsgiDAV server (port 9208),
# runs every curl call and client from the article, then stops both servers.
set -u
cd "$(dirname "$0")"

rm -rf webdav-data && mkdir -p webdav-data/reports
printf 'Q3 sales summary\n' > webdav-data/reports/q3.txt
printf 'Q4 sales summary\n' > webdav-data/reports/q4.txt

node server.js > /dev/null &
NODE_PID=$!
.venv/bin/wsgidav --host 127.0.0.1 --port 9208 --root ./webdav-data --auth anonymous > /dev/null 2>&1 &
DAV_PID=$!
trap 'kill $NODE_PID $DAV_PID 2> /dev/null' EXIT
sleep 3

run() { echo "\$ $*"; "$@"; echo; echo; }

echo "=== Express: bulk cancel with mixed results ==="
run curl -si -H 'Content-Type: application/json' \
  -d '{"items":[{"orderId":"ord-1001"},{"orderId":"ord-1002"},{"orderId":"ord-9999"}]}' \
  http://127.0.0.1:9207/orders/bulk-cancel

echo "=== Express: malformed JSON fails the whole request ==="
run curl -si -H 'Content-Type: application/json' -d '{"items": [' http://127.0.0.1:9207/orders/bulk-cancel

echo "=== Express: empty items array ==="
run curl -si -H 'Content-Type: application/json' -d '{"items": []}' http://127.0.0.1:9207/orders/bulk-cancel

echo "=== Node.js fetch() client ==="
node client.mjs
echo
echo "=== Python requests client ==="
.venv/bin/python client.py
echo

echo "=== WebDAV: PROPFIND with Depth 1 ==="
run curl -si -X PROPFIND -H 'Depth: 1' -H 'Content-Type: application/xml' \
  --data '<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:getcontentlength/></d:prop></d:propfind>' \
  http://127.0.0.1:9208/reports/

echo "=== WebDAV: LOCK q3.txt, then DELETE the folder ==="
curl -s -o /dev/null -w 'LOCK status: %{http_code}\n' -X LOCK -H 'Content-Type: application/xml' \
  --data '<?xml version="1.0"?><d:lockinfo xmlns:d="DAV:"><d:lockscope><d:exclusive/></d:lockscope><d:locktype><d:write/></d:locktype><d:owner>demo</d:owner></d:lockinfo>' \
  http://127.0.0.1:9208/reports/q3.txt
run curl -si -X DELETE http://127.0.0.1:9208/reports/
echo "files left in reports/: $(ls webdav-data/reports)"
echo

if [ -f spring-boot/target/orders-bulk-cancel-1.0.0.jar ]; then
  echo "=== Spring Boot: bulk cancel with mixed results ==="
  java -jar spring-boot/target/orders-bulk-cancel-1.0.0.jar > /dev/null 2>&1 &
  SPRING_PID=$!
  trap 'kill $NODE_PID $DAV_PID $SPRING_PID 2> /dev/null' EXIT
  for i in $(seq 1 30); do curl -s -o /dev/null http://127.0.0.1:9209/ && break; sleep 1; done
  run curl -si -H 'Content-Type: application/json' \
    -d '{"items":[{"orderId":"ord-1001"},{"orderId":"ord-1002"},{"orderId":"ord-9999"}]}' \
    http://127.0.0.1:9209/orders/bulk-cancel
fi
