#!/usr/bin/env bash
# Calls the Docs API with a few requests. Start the API first, for example:
#   AUTHZ_MODEL=rbac uvicorn app:app --port 8000
BASE=${BASE:-http://127.0.0.1:8000}

call() {
  echo "### $1"
  shift
  curl -s -i "$@" | grep -v -i -E '^(date|server|content-length):'
  echo
  echo
}

call "Bob (sales editor) edits Alice's launch plan" -X PUT -H "Authorization: Bearer tok-bob" \
  -H "Content-Type: application/json" -d '{"title":"Bob was here"}' "$BASE/documents/launch-plan"
call "Erin (agency) reads the launch plan in the shared folder" -H "Authorization: Bearer tok-erin" "$BASE/documents/launch-plan"
call "Carol (marketing viewer) edits the launch plan" -X PUT -H "Authorization: Bearer tok-carol" \
  -H "Content-Type: application/json" -d '{"title":"Carol was here"}' "$BASE/documents/launch-plan"
call "Erin lists the documents she can see" -H "Authorization: Bearer tok-erin" "$BASE/documents"
call "Alice lists the documents she can see" -H "Authorization: Bearer tok-alice" "$BASE/documents"
