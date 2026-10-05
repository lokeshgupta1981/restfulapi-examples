#!/usr/bin/env bash
# Runs the demo prompts against the local stub model. Start both servers first (see README.md).
set -u

run() {
  echo "\$ $*"
  "$@"
  echo
}

run python agent.py --trace "What is the status of order 1001?"
run python agent.py "What is the status of order 9999?"
run python agent.py "Show me order twelve"
run python agent.py --trace "Where are the parcels for orders 1001, 1002 and 1003?"
run curl -s -i http://127.0.0.1:8780/orders/1003/shipment
echo "\$ echo y | python agent.py \"Cancel order 1002, wrong size\""
echo y | python agent.py "Cancel order 1002, wrong size"
echo
echo "\$ echo n | python agent.py \"Cancel order 1001, wrong size\""
echo n | python agent.py "Cancel order 1001, wrong size"
echo
echo "\$ echo y | python agent.py \"Cancel order 1001, wrong size\""
echo y | python agent.py "Cancel order 1001, wrong size"
echo
echo "\$ echo y | python agent.py \"Cancel order 1005, wrong size\""
echo y | python agent.py "Cancel order 1005, wrong size"
echo
for attempt in 1 2; do
  run curl -s -i -X POST http://127.0.0.1:8780/orders/1004/cancel -H "Content-Type: application/json" -H "Idempotency-Key: 7d4c1f0e-2b8a-4c55-9a51-0f3e6b2d9c11" -d '{"reason": "Duplicate order"}'
done
run python openapi_tools.py cancelOrder
