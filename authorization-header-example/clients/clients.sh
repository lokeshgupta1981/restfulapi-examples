#!/usr/bin/env bash
# curl: how it builds the Authorization header and what it does on redirects.
# Needs the echo servers on ports 9771 and 9772 (echo_server.py).
BASE=http://127.0.0.1:9771

echo '--- curl -u (Basic built by curl)'
curl -s -u reports-app:demo-pass-123 "$BASE/echo"; echo

echo '--- curl -H with a Bearer token'
curl -s -H 'Authorization: Bearer demo-token-123' "$BASE/echo"; echo

for target in to-same to-port to-host; do
  echo "--- curl -L -H, redirect $target"
  curl -s -L -H 'Authorization: Bearer demo-token-123' "$BASE/$target"; echo
done

for target in to-same to-port to-host; do
  echo "--- curl -L -u, redirect $target"
  curl -s -L -u reports-app:demo-pass-123 "$BASE/$target"; echo
done

echo '--- curl --location-trusted -u, redirect to-host'
curl -s --location-trusted -u reports-app:demo-pass-123 "$BASE/to-host"; echo

echo '--- curl through a proxy: -U sends Proxy-Authorization, -u sends Authorization'
curl -s -x http://127.0.0.1:9772 -U proxy-user:demo-proxy-pass -u reports-app:demo-pass-123 http://orders.example/echo; echo
