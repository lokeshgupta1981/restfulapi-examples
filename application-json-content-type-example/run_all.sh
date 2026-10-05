#!/usr/bin/env bash
# Runs every demo against servers that are already started (see README) and
# writes the combined output to OUTPUTS.txt.
cd "$(dirname "$0")"
{
  echo "##### probe.sh (Express 9301, FastAPI 9302, Spring Boot 9303)"
  bash probe.sh
  echo
  echo "##### 415 responses with headers"
  curl -s -i http://127.0.0.1:9301/orders -H 'Content-Type: text/plain' --data-raw '{"item":"keyboard","quantity":2}' | tr -d '\r'; echo
  curl -s -i http://127.0.0.1:9303/orders -H 'Content-Type: text/plain' --data-raw '{"item":"keyboard","quantity":2}' | tr -d '\r'; echo
  echo
  echo "##### express/plus_json.mjs (port 9399)"
  node express/plus_json.mjs
  echo
  echo "##### clients/clients.sh (echo server 9300)"
  bash clients/clients.sh
  echo
  echo "##### cors/cors_check.py (page 9310, API 9311)"
  python3 cors/cors_check.py
  sleep 1
  echo "--- API log (cors/api.log)"
  cat cors/api.log
} > OUTPUTS.txt 2>&1
