#!/usr/bin/env bash
# Starts the Orders API on ports 9190 (HTTP), 9191 (HTTP to HTTPS redirector) and
# 9192 (HTTPS), runs every client against it and stops the servers at the end.
set -u
cd "$(dirname "$0")"
PY=.venv/bin/python
UV=.venv/bin/uvicorn

if [ ! -f cert.pem ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 \
    -subj "/CN=127.0.0.1" -addext "subjectAltName=IP:127.0.0.1,DNS:localhost" 2>/dev/null
fi

$UV app:app --host 127.0.0.1 --port 9190 --log-level warning & P1=$!
$UV http_redirector:app --host 127.0.0.1 --port 9191 --log-level warning & P2=$!
$UV app:app --host 127.0.0.1 --port 9192 --ssl-keyfile key.pem --ssl-certfile cert.pem --log-level warning & P3=$!
trap 'kill $P1 $P2 $P3 2>/dev/null' EXIT
sleep 2

ORDER='{"sku": "BOOK-42", "qty": 2}'

echo "== 0. Tests"
.venv/bin/pytest -q test_redirects.py 2>&1 | tail -1
echo

echo "== 1. POST /v1/orders gets HTTP 308"
curl -si -H 'Content-Type: application/json' --data "$ORDER" http://127.0.0.1:9190/v1/orders
echo; echo
echo "== 2. curl -L follows the 308 with the same POST and body"
curl -si -L -H 'Content-Type: application/json' --data "$ORDER" http://127.0.0.1:9190/v1/orders
echo; echo
echo "== 3. Trailing slash: Starlette answers POST /orders/ with HTTP 307"
curl -si -H 'Content-Type: application/json' --data '{"sku": "PEN-7", "qty": 1}' http://127.0.0.1:9190/orders/
echo; echo
echo "== 4. HTTP to HTTPS with 308: what curl -v sends on each hop"
curl -sv -L --cacert cert.pem -H 'Content-Type: application/json' -H 'Authorization: Bearer demo-token' \
  --data "$ORDER" http://127.0.0.1:9191/v1/orders 2>&1 | grep -E '^[<>] (POST|Host|Authorization|HTTP|location)|^\{"'
echo; echo
echo "== 5. curl"; ./clients/curl_matrix.sh; echo
echo "== 6. Python requests"; $PY clients/requests_matrix.py; echo
echo "== 6b. Python requests: follow a 308 by hand"; $PY clients/follow_308.py; echo
echo "== 7. Node.js fetch()"; node clients/fetch_matrix.mjs; echo
if command -v java >/dev/null; then
  echo "== 8. Java HttpClient"; java clients/RedirectMatrix.java 2>&1 | grep -v JAVA_TOOL_OPTIONS; echo
  echo "== 8b. Java HttpURLConnection"; java clients/UrlConnectionCheck.java 2>&1 | grep -v JAVA_TOOL_OPTIONS; echo
fi
echo "== 9. Redirect loop: where each client stops"
curl -s -L -o /dev/null -w 'curl: stopped after %{num_redirects} redirects, ' http://127.0.0.1:9190/loop/0; echo "exit code $?"
$PY -c 'import requests
try: requests.get("http://127.0.0.1:9190/loop/0", timeout=5)
except requests.TooManyRedirects as e: print("requests:", type(e).__name__, e)'
node -e 'fetch("http://127.0.0.1:9190/loop/0").catch(e => console.log("fetch():", e.message + ":", e.cause.message))'
command -v java >/dev/null && java clients/LoopCheck.java 2>&1 | grep -v JAVA_TOOL_OPTIONS
echo
if $PY -c 'import playwright' 2>/dev/null || python3 -c 'import playwright' 2>/dev/null; then
  echo "== 10. Browser cache: does Chromium store the redirect?"
  ($PY browser_cache_check.py 2>/dev/null || python3 browser_cache_check.py)
fi
