#!/usr/bin/env bash
# CI checks: consumer tests against the stateful mock, then a contract check
# of the API through a Prism validation proxy. Any failure stops the build.
set -euo pipefail
cd "$(dirname "$0")"
trap 'kill $(jobs -p) 2>/dev/null || true' EXIT

wait_for() {
  curl -s -o /dev/null --retry 30 --retry-connrefused --retry-delay 1 "$1"
}

# 1. Consumer tests against the stateful mock
node stateful-mock.js > /dev/null &
wait_for http://127.0.0.1:9222/
BASE_URL=http://127.0.0.1:9222 node --test --test-reporter=dot consumer.test.js

# 2. Contract check of the API (here the local real-api.js) through Prism
node real-api.js > /dev/null &
./node_modules/.bin/prism proxy openapi.yaml http://127.0.0.1:9223 --port 9224 > /dev/null &
wait_for http://127.0.0.1:9223/
wait_for http://127.0.0.1:9224/
node contract-check.js
