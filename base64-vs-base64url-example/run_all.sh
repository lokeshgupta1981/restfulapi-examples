#!/usr/bin/env bash
# Starts the Orders API, runs every demo, prints the exact commands used in the
# article with their output, and stops the server. Output: ./run_all.sh > OUTPUTS.txt
# Needs: Python 3.10+ with requirements.txt installed, curl, jq, GNU coreutils,
# Node.js 22 (Node.js 25+ for Uint8Array.fromBase64), Java 21+, Go 1.22+.
# Set NODE to a Node.js 25+ binary to run the fromBase64 parts.
set -u
cd "$(dirname "$0")"
NODE="${NODE:-node}"
API=http://127.0.0.1:9170

run() { printf '\n$ %s\n' "$*"; eval "$*"; echo; }

echo "# Captured $(date -u +%Y-%m-%dT%H:%MZ)"
echo "# Python $(python3 -c 'import platform;print(platform.python_version())'), $(python3 -c 'import fastapi,uvicorn,httpx;print("fastapi",fastapi.__version__,"uvicorn",uvicorn.__version__,"httpx",httpx.__version__)')"
echo "# Node.js $(node --version) and $($NODE --version), $(java -version 2>&1 | grep -m1 version), $(go version), $(curl --version | head -1 | cut -d' ' -f1-2)"

uvicorn server:app --host 127.0.0.1 --port 9170 --log-level warning &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
for _ in $(seq 1 40); do curl -s -o /dev/null "$API/orders" && break; sleep 0.25; done

echo; echo "################ encoders"
run python3 encoding_demo.py
run node node/demo.mjs
run "$NODE" node/demo.mjs
run java java/Base64Demo.java
run "(cd go && go run .)"

echo; echo "################ decoder matrix"
run python3 decoder-matrix/decoder_matrix.py
run "$NODE" decoder-matrix/decoder_matrix.mjs
run java decoder-matrix/DecoderMatrix.java
run "(cd decoder-matrix/go && go run .)"

echo; echo "################ Orders API: demo.sh and client.py"
run ./demo.sh
run python3 client.py

echo; echo "################ commands quoted in the article"
run "curl -s -i $API/legacy/orders"
run "curl -s \"$API/legacy/orders?cursor=eyJhZnRlciI6Im9yZF8xMDAxIn0u+sCjW+KiNWI=\""
run "curl -s -G $API/legacy/orders --data-urlencode \"cursor=eyJhZnRlciI6Im9yZF8xMDAxIn0u+sCjW+KiNWI=\" -v 2>&1 | grep '^> GET'"
run "curl -s $API/orders"
run "curl -s \"$API/orders?cursor=eyJhZnRlciI6Im9yZF8xMDAxIn0u-sCjW-KiNWI\""
run "curl -s \"$API/orders?cursor=eyJhZnRlciI6Im9yZF8xMDAxIn0u-sCjW-KiNWj\""
run "echo 'reports-app:s3cret-42' | base64"
run "printf '%s' 'reports-app:s3cret-42' | base64"
run "curl -s -i $API/reports -H 'Authorization: Basic cmVwb3J0cy1hcHA6czNjcmV0LTQyCg=='"
run "echo 'cmVwb3J0cy1hcHA6czNjcmV0LTQyCg==' | base64 -d | od -c"
run "curl -s -u reports-app:s3cret-42 -v $API/reports 2>&1 | grep -i '^> authorization'"
run "base64 pixel.png"
run "base64 pixel.png | jq -Rs '{file_name: \"pixel.png\", content_base64: .}' | curl -s $API/attachments -H 'Content-Type: application/json' --data-binary @-"
run "base64 -w 0 pixel.png | jq -R '{file_name: \"pixel.png\", content_base64: .}' | curl -s -i $API/attachments -H 'Content-Type: application/json' --data-binary @-"
run "python3 -c 'import secrets; print(secrets.token_urlsafe(16))'"
run "python3 -c \"from server import b64url_decode; print(b64url_decode('eyJhZnRlciI6Im9yZF8xMDAxIn0u-sCjW-KiNWI'))\""
