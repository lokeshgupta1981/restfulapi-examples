#!/usr/bin/env bash
# Starts both servers, runs every demo and writes OUTPUTS.txt. Stops the servers at the end.
cd "$(dirname "$0")"
start_api() { uvicorn resource_server:app --port 8000 --log-level warning & API_PID=$!; sleep 2; }
uvicorn auth_server:app --port 9000 --log-level warning & AS_PID=$!
start_api
{
  echo "### python discover.py http://127.0.0.1:8000/orders"
  python3 discover.py http://127.0.0.1:8000/orders
  echo
  echo "### ./demo.sh"
  ./demo.sh
  kill $API_PID; wait $API_PID 2>/dev/null
  echo
  echo "### PRM_NO_HEADER=1: the 401 has no resource_metadata, the client builds the well-known URL"
  PRM_NO_HEADER=1 start_api
  python3 discover.py http://127.0.0.1:8000/orders
  kill $API_PID; wait $API_PID 2>/dev/null
  echo
  echo "### PRM_FAKE_RESOURCE=1: the metadata describes another resource"
  PRM_FAKE_RESOURCE=1 start_api
  python3 discover.py http://127.0.0.1:8000/orders; echo "exit code $?"
  kill $API_PID; wait $API_PID 2>/dev/null
} > OUTPUTS.txt 2>&1
kill $AS_PID
cat OUTPUTS.txt
