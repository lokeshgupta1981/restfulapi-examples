#!/usr/bin/env bash
# Starts the servers, runs curl and every client, then stops the servers.
set -u
cd "$(dirname "$0")"
PY=.venv/bin/python
# Call the local servers directly, not through a proxy set in the environment.
unset NO_PROXY no_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy ALL_PROXY all_proxy

PORT=9420 $PY -m uvicorn app:app --port 9420 --log-level warning &
P1=$!
PORT=9423 EXPOSE=0 $PY -m uvicorn app:app --port 9423 --log-level warning &
P2=$!
$PY -m http.server 9421 --bind 127.0.0.1 --directory web > /dev/null 2>&1 &
P3=$!
$PY proxy.py &
P4=$!
trap 'kill $P1 $P2 $P3 $P4 2>/dev/null' EXIT
for i in $(seq 1 40); do
  curl -s -o /dev/null http://127.0.0.1:9420/builtin && break
  $PY -c "import time; time.sleep (0.25)"
done

echo "### curl: no token"
curl -si http://127.0.0.1:9420/shipments
echo
echo "### curl: expired token"
curl -si http://127.0.0.1:9420/shipments -H "Authorization: Bearer demo-token-expired"
echo
echo "### curl: token without the write scope"
curl -si -X POST http://127.0.0.1:9420/shipments -H "Authorization: Bearer demo-token-read"
echo
echo "### curl: malformed Bearer credentials"
curl -si http://127.0.0.1:9420/shipments -H "Authorization: Bearer"
echo
echo "### curl: Basic credentials sent to the Bearer API"
curl -si http://127.0.0.1:9420/shipments -u ana:demo-pass-123
echo
echo "### curl: resource metadata"
curl -s http://127.0.0.1:9420/.well-known/oauth-protected-resource/shipments
echo
echo
echo "### curl: two challenges on two lines"
curl -si http://127.0.0.1:9420/v2/shipments
echo
echo "### curl: Basic challenge"
curl -si http://127.0.0.1:9420/legacy/reports
echo
echo "### curl: FastAPI HTTPBearer without a token"
curl -si http://127.0.0.1:9420/builtin
echo
echo "### curl: CORS preflight and expired token from another origin"
curl -si -X OPTIONS http://127.0.0.1:9420/shipments -H "Origin: http://127.0.0.1:9421" \
  -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: authorization"
echo
curl -si http://127.0.0.1:9420/shipments -H "Origin: http://127.0.0.1:9421" -H "Authorization: Bearer demo-token-expired"
echo
echo "### curl: proxy without credentials"
curl -si -x http://127.0.0.1:9424 http://127.0.0.1:9420/legacy/reports
echo
echo "### curl: proxy with credentials, origin without credentials"
curl -si -x http://127.0.0.1:9424 --proxy-user proxyuser:demo-proxy-pass http://127.0.0.1:9420/legacy/reports
echo
echo "### curl: proxy and origin credentials"
curl -s -x http://127.0.0.1:9424 --proxy-user proxyuser:demo-proxy-pass -u ana:demo-pass-123 http://127.0.0.1:9420/legacy/reports
echo
echo
echo "### curl: credentials in the URL"
curl -s http://ana:demo-pass-123@127.0.0.1:9420/legacy/reports
echo
echo
echo "### node url_credentials.mjs"
node url_credentials.mjs
echo
echo "### node parse-demo.mjs"
node parse-demo.mjs
echo
echo "### node client.mjs"
node client.mjs
echo
echo "### python basic_client.py"
$PY basic_client.py
echo
echo "### python browser_check.py"
$PY browser_check.py
echo
echo "### node --test"
node --test 2>&1 | tail -8
