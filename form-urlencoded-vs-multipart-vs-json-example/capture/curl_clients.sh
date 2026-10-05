#!/usr/bin/env bash
# Sends the same ticket three ways with curl. Start wire_server.py first.
# Run from the example root folder (error.log is there).
URL=http://127.0.0.1:9170/tickets

echo '$ curl -d (x-www-form-urlencoded)'
curl -s "$URL" --data-urlencode "subject=Login fails & shows 500" \
  -d priority=high -d tags=auth -d tags=web
echo

echo '$ curl -F (multipart/form-data)'
curl -s "$URL" -F "subject=Login fails & shows 500" -F priority=high \
  -F "attachment=@error.log;type=text/plain"
echo

echo '$ curl --json (application/json)'
curl -s "$URL" --json '{"subject":"Login fails & shows 500","priority":"high","tags":["auth","web"]}'
echo

echo '$ curl OAuth 2.0 token request (x-www-form-urlencoded)'
curl -s http://127.0.0.1:9170/oauth/token -u ticket-cli:s3cret \
  -d grant_type=client_credentials --data-urlencode "scope=tickets:read tickets:write"
echo
