#!/usr/bin/env bash
# curl requests against the FastAPI app (start it first: uvicorn fastapi_app:app --port 9161)
BASE=http://127.0.0.1:9161

run() {
  echo "\$ $*"
  "$@"
  echo
  echo
}

run curl -s "$BASE/docs/report?tag=C%2B%2B+%26+Java%2FGo"
run curl -s "$BASE/docs/caf%C3%A9"
run curl -s -i "$BASE/docs/AB%2F12"
run curl -s "$BASE/files/AB%2F12"
run curl -s "$BASE/files/AB/12"
run curl -s "$BASE/docs/caf%E9"
run curl -s "$BASE/docs/50%zz"
