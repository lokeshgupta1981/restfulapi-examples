#!/usr/bin/env bash
# Runs every scenario from the article against two instances (A and B) of server.py.
# Usage: ./demo.sh            (ports 8000 and 8001)
#        BASE_PORT=9000 ./demo.sh
set -e
cd "$(dirname "$0")"
PY=${PY:-python3}
BASE_PORT=${BASE_PORT:-8000}
A=http://127.0.0.1:$BASE_PORT
B=http://127.0.0.1:$((BASE_PORT + 1))
PIDS=()

start() {   # start <session-store> <denylist>
  rm -rf data
  for i in 0 1; do
    name=$([ $i = 0 ] && echo A || echo B)
    INSTANCE=$name SESSION_STORE=$1 DENYLIST=$2 $PY -m uvicorn server:app \
      --port $((BASE_PORT + i)) --no-access-log --log-level warning &
    PIDS+=($!)
    sleep 0.3   # let A create users.db before B starts
  done
  for url in $A $B; do until curl -s -o /dev/null $url/docs; do sleep 0.2; done; done
}
stop() { kill "${PIDS[@]}" 2>/dev/null || true; wait "${PIDS[@]}" 2>/dev/null || true; PIDS=(); }
trap stop EXIT
json() { $PY -c "import json,sys; print(json.load(sys.stdin)$1)"; }
LOGIN='{"username":"alice","password":"alice-demo-pass"}'
show() { echo; echo "== $*"; }

start memory 0
echo "Two instances, SESSION_STORE=memory, DENYLIST=0"

show "1. Session login on A (response headers)"
curl -s -i -X POST $A/session/login -H 'Content-Type: application/json' -d "$LOGIN" | grep -v '^date:'
SID=$(curl -s -i -X POST $A/session/login -H 'Content-Type: application/json' -d "$LOGIN" \
      | sed -n 's/^set-cookie: sid=\([^;]*\);.*/\1/p')

show "2. Orders on A with the session cookie"
curl -s -w '  -> HTTP %{http_code}\n' $A/session/orders -H "Cookie: sid=$SID"

show "3. Same cookie sent to instance B"
curl -s -w '  -> HTTP %{http_code}\n' $B/session/orders -H "Cookie: sid=$SID"

show "4. Token login on A"
TOKEN=$(curl -s -X POST $A/token/login -H 'Content-Type: application/json' -d "$LOGIN" | json "['access_token']")
curl -s -X POST $A/token/login -H 'Content-Type: application/json' -d "$LOGIN" \
  | $PY -c "import json,sys; d=json.load(sys.stdin); d['access_token']=d['access_token'][:24]+'...'; print(json.dumps(d))"
echo "token: $TOKEN"

show "5. Anyone can read the token payload (base64url, not encrypted)"
echo "$TOKEN" | cut -d. -f2 | $PY -c "import sys,base64,json; s=sys.stdin.read().strip(); print(json.dumps(json.loads(base64.urlsafe_b64decode(s+'='*(-len(s)%4)))))"

show "6. Orders on A and on B with the same token"
curl -s -w '  -> HTTP %{http_code}\n' $A/token/orders -H "Authorization: Bearer $TOKEN"
curl -s -w '  -> HTTP %{http_code}\n' $B/token/orders -H "Authorization: Bearer $TOKEN"

show "7. Tampered token (role changed to superadmin in the payload)"
FORGED_PAYLOAD=$(echo "$TOKEN" | cut -d. -f2 | $PY -c "
import sys,base64,json
s=sys.stdin.read().strip(); c=json.loads(base64.urlsafe_b64decode(s+'='*(-len(s)%4)))
c['role']='superadmin'
print(base64.urlsafe_b64encode(json.dumps(c,separators=(',',':')).encode()).decode().rstrip('='))")
FORGED="$(echo "$TOKEN" | cut -d. -f1).$FORGED_PAYLOAD.$(echo "$TOKEN" | cut -d. -f3)"
curl -s -i $A/token/orders -H "Authorization: Bearer $FORGED" | grep -v '^date:'

show "8. Header sizes on every request"
echo "Cookie: sid=$SID" | tr -d '\n' | wc -c | xargs echo "Cookie header bytes:"
echo "Authorization: Bearer $TOKEN" | tr -d '\n' | wc -c | xargs echo "Authorization header bytes:"

show "9. Logout, then reuse the old credential"
curl -s -o /dev/null -w 'session logout -> HTTP %{http_code}\n' -X POST $A/session/logout -H "Cookie: sid=$SID"
curl -s -w '  -> HTTP %{http_code}\n' $A/session/orders -H "Cookie: sid=$SID"
curl -s -o /dev/null -w 'token logout -> HTTP %{http_code}\n' -X POST $A/token/logout -H "Authorization: Bearer $TOKEN"
curl -s -w '  -> HTTP %{http_code}\n' $A/token/orders -H "Authorization: Bearer $TOKEN"

show "10. Alice is demoted from admin to customer while logged in"
SID=$(curl -s -i -X POST $A/session/login -H 'Content-Type: application/json' -d "$LOGIN" \
      | sed -n 's/^set-cookie: sid=\([^;]*\);.*/\1/p')
TOKEN=$(curl -s -X POST $A/token/login -H 'Content-Type: application/json' -d "$LOGIN" | json "['access_token']")
curl -s -w '  -> HTTP %{http_code}\n' $A/session/admin/report -H "Cookie: sid=$SID"
curl -s -w '  -> HTTP %{http_code}\n' $A/token/admin/report -H "Authorization: Bearer $TOKEN"
curl -s -o /dev/null -w 'demote -> HTTP %{http_code}\n' -X POST $A/demo/users/alice/role/customer
curl -s -w '  -> HTTP %{http_code}\n' $A/session/admin/report -H "Cookie: sid=$SID"
curl -s -w '  -> HTTP %{http_code}\n' $A/token/admin/report -H "Authorization: Bearer $TOKEN"

stop
start shared 1
echo; echo "Restarted: two instances, SESSION_STORE=shared, DENYLIST=1"

show "11. Session created on A, used on B (shared store)"
SID=$(curl -s -i -X POST $A/session/login -H 'Content-Type: application/json' -d "$LOGIN" \
      | sed -n 's/^set-cookie: sid=\([^;]*\);.*/\1/p')
curl -s -w '  -> HTTP %{http_code}\n' $B/session/orders -H "Cookie: sid=$SID"

show "12. Token logout on A with a denylist, then reuse on B"
TOKEN=$(curl -s -X POST $A/token/login -H 'Content-Type: application/json' -d "$LOGIN" | json "['access_token']")
curl -s -w '  -> HTTP %{http_code}\n' $B/token/orders -H "Authorization: Bearer $TOKEN"
curl -s -o /dev/null -w 'token logout -> HTTP %{http_code}\n' -X POST $A/token/logout -H "Authorization: Bearer $TOKEN"
curl -s -i $B/token/orders -H "Authorization: Bearer $TOKEN" | grep -v '^date:'
echo
