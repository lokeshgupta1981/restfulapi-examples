#!/usr/bin/env bash
# Starts the FastAPI app (port 9182) and the Express app (port 9183),
# runs every client against them and stops both servers.
set -u
cd "$(dirname "$0")"

.venv/bin/uvicorn app:app --host 127.0.0.1 --port 9182 --log-level warning &
API_PID=$!
node express-app.js &
EXPRESS_PID=$!
trap 'kill $API_PID $EXPRESS_PID 2>/dev/null' EXIT
sleep 2

echo "== 1. GET the invoice PDF without following the redirect"
curl -si http://127.0.0.1:9182/invoices/1001/pdf

echo
echo "== 2. Follow the redirect with curl -L"
echo "$ curl -sL -o invoice-1001.pdf -w 'status: %{http_code}, type: %{content_type}, redirects: %{num_redirects}\\nfinal URL: %{url_effective}\\n' http://127.0.0.1:9182/invoices/1001/pdf"
curl -sL -o invoice-1001.pdf -w 'status: %{http_code}, type: %{content_type}, redirects: %{num_redirects}\nfinal URL: %{url_effective}\n' http://127.0.0.1:9182/invoices/1001/pdf
rm -f invoice-1001.pdf

echo
echo "== 3. Express res.redirect() default"
curl -si http://127.0.0.1:9183/invoices/1001/pdf | head -n 6

echo
echo "== 4. curl -L with POST, PUT and DELETE (same host, with an Authorization header)"
echo "$ curl -sL -H 'Authorization: Bearer demo-token' -H 'Content-Type: application/json' -d '{\"amount\":\"49.90\"}' http://127.0.0.1:9182/redirect/302"
curl -sL -H 'Authorization: Bearer demo-token' -H 'Content-Type: application/json' -d '{"amount":"49.90"}' http://127.0.0.1:9182/redirect/302
echo
for method in PUT DELETE; do
  echo "$ curl -sL -X $method -H 'Authorization: Bearer demo-token' -H 'Content-Type: application/json' -d '{\"amount\":\"49.90\"}' http://127.0.0.1:9182/redirect/302"
  curl -sL -X "$method" -H 'Authorization: Bearer demo-token' -H 'Content-Type: application/json' -d '{"amount":"49.90"}' http://127.0.0.1:9182/redirect/302
  echo
done
echo "-- the same with HTTP 303 and HTTP 307"
for code in 303 307; do
  for method in POST PUT DELETE; do
    if [ "$method" = POST ]; then
      result=$(curl -sL -H 'Content-Type: application/json' -d '{"amount":"49.90"}' "http://127.0.0.1:9182/redirect/$code")
    else
      result=$(curl -sL -X "$method" -H 'Content-Type: application/json' -d '{"amount":"49.90"}' "http://127.0.0.1:9182/redirect/$code")
    fi
    echo "$method $code $result"
  done
done
echo "-- POST with --post302"
curl -sL --post302 -H 'Content-Type: application/json' -d '{"amount":"49.90"}' http://127.0.0.1:9182/redirect/302
echo
echo "-- verbose POST to 302"
curl -sL -v -H 'Content-Type: application/json' -d '{"amount":"49.90"}' http://127.0.0.1:9182/redirect/302 2>&1 | grep -E '^(> (POST|GET|PUT)|< HTTP|\* Switch)'

echo
echo "== 5. Python requests and httpx"
.venv/bin/python matrix.py

echo
echo "== 6. Node.js fetch()"
node matrix.mjs

echo
echo "== 7. Java HttpClient"
java Matrix.java 2>&1 | grep -v JAVA_TOOL_OPTIONS

echo
echo "== 8. Redirect following turned off"
.venv/bin/python no_follow.py
node no_follow.mjs
