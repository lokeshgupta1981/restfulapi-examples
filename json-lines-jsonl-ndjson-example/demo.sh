#!/usr/bin/env bash
# Runs every command shown in the article. Start the server first: node server.mjs
set -u
cd "$(dirname "$0")"

echo '$ python write_jsonl.py'; python write_jsonl.py
echo '$ cat data/orders.jsonl'; cat data/orders.jsonl
echo '$ python read_jsonl.py data/orders.jsonl'; python read_jsonl.py data/orders.jsonl
echo '$ python read_jsonl.py data/orders-bad.jsonl'; python read_jsonl.py data/orders-bad.jsonl; echo "exit code $?"
echo '$ python read_jsonl.py data/orders-bad.jsonl --skip-bad'; python read_jsonl.py data/orders-bad.jsonl --skip-bad 2>&1
echo '$ node read_jsonl.mjs data/orders-bad.jsonl'; node read_jsonl.mjs data/orders-bad.jsonl 2>&1
echo '$ python splitlines_bug.py'; python splitlines_bug.py
echo '$ python batch_requests.py'; python batch_requests.py
echo '$ head -n 1 data/batch-input.jsonl | jq .'; head -n 1 data/batch-input.jsonl | jq .
echo "\$ python -c \"import json; json.load(open('data/orders.jsonl'))\""; python -c "import json; json.load(open('data/orders.jsonl'))" 2>&1 | tail -n 1
echo "\$ node -e \"JSON.parse(require('fs').readFileSync('data/orders.jsonl', 'utf8'))\""; node -e "JSON.parse(require('fs').readFileSync('data/orders.jsonl', 'utf8'))" 2>&1 | grep SyntaxError

echo '$ wc -l data/orders.jsonl'; wc -l data/orders.jsonl
echo "\$ jq -c 'select(.status == \"paid\") | {id, total}' data/orders.jsonl"; jq -c 'select(.status == "paid") | {id, total}' data/orders.jsonl
echo "\$ jq -s 'map(.total) | add' data/orders.jsonl"; jq -s 'map(.total) | add' data/orders.jsonl
echo "\$ jq -s '.' data/orders.jsonl > data/orders.json"; jq -s '.' data/orders.jsonl > data/orders.json; head -c 80 data/orders.json; echo
echo "\$ jq -c '.[]' data/orders.json"; jq -c '.[]' data/orders.json
echo '$ gzip -kf data/orders.jsonl && zcat data/orders.jsonl.gz | jq -c .'; gzip -kf data/orders.jsonl && zcat data/orders.jsonl.gz | jq -c .
echo "\$ jq -c . data/orders-bad.jsonl"; NO_COLOR=1 script -qc "jq -c . data/orders-bad.jsonl" /dev/null | tr -d '\r'  # terminal order: stdout, then stderr
echo "\$ jq -cR 'fromjson? // empty' data/orders-bad.jsonl"; jq -cR 'fromjson? // empty' data/orders-bad.jsonl

echo '$ curl -sN -i http://127.0.0.1:9387/orders/export'; curl -sN -i http://127.0.0.1:9387/orders/export | grep -v -E '^(Date|Keep-Alive)'
echo '$ curl -sN http://127.0.0.1:9387/orders/export | jq -c "{id, status}"'; curl -sN http://127.0.0.1:9387/orders/export | jq -c '{id, status}'
echo '$ python client.py'; python client.py
echo '$ node client.mjs'; node client.mjs
echo '$ mvn -q compile exec:java -Dexec.args=http'; mvn -q -B compile exec:java -Dexec.args=http 2>&1 | grep -v JAVA_TOOL_OPTIONS
