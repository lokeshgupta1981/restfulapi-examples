#!/usr/bin/env bash
# curl requests against server.py (start it first: python3 server.py)
BASE=http://127.0.0.1:9160

run() {
  echo "\$ $*"
  "$@"
  echo
  echo
}

run curl -s -G "$BASE/v2/docs/report" --data-urlencode "tag=C++ & Java/Go"
run curl -s "$BASE/v2/docs/report" --url-query "tag=C++ & Java/Go"
run curl -s "$BASE/v2/docs/report?tag=C++%20%26%20Java"
run curl -s "$BASE/v2/docs/AB%2F12"
run curl -s "$BASE/v2/docs/a+b?tag=a+b&tag=a%2Bb"
run curl -s "$BASE/v2/docs/caf%C3%A9?tag=50%25%20off"
run curl -s -i "$BASE/v2/docs/50%zz"
run curl -s -i "$BASE/v2/docs/caf%E9"
run curl -s -i "$BASE/v2/docs/report?tag=50%zz"
run curl -s "$BASE/v2/docs/100%2541"
run curl -s "$BASE/v1/docs/100%2541"
run curl -s -i "$BASE/v2/admin/stats"
run curl -s -i "$BASE/v2/%2561dmin/stats"
run curl -s -i "$BASE/v1/%2561dmin/stats"
run curl -s -i "$BASE/v2/notes" --data-urlencode "title=Q3 plan" --data-urlencode "body=a+b=c & 100%"
