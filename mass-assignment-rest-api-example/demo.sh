#!/usr/bin/env bash
# Sends the same requests to the vulnerable and the secure app.
# Start both apps first (see README.md). Needs curl.
VULN=${VULN:-http://localhost:8000}
SECURE=${SECURE:-http://localhost:8001}

call() {  # call METHOD URL USER_ID BODY
  local method=$1 url=$2 user=$3 body=$4
  echo "\$ curl -X $method $url -H 'Content-Type: application/json'${user:+ -H 'X-User-Id: $user'} -d '$body'"
  curl -s -i -X "$method" "$url" -H 'Content-Type: application/json' \
       ${user:+-H "X-User-Id: $user"} ${body:+-d "$body"} \
    | grep -v -i -E '^(date|server|content-length|content-type):' | tr -d '\r' | sed '/^$/d'
  echo; echo
}

echo "########## Vulnerable app ($VULN)"
call POST  "$VULN/users" "" '{"email":"alice@example.com","name":"Alice","password":"alice-pass-1"}'
call POST  "$VULN/users" "" '{"email":"mallory@example.com","name":"Mallory","password":"mallory-pass-1","role":"admin","store_credit":500,"email_verified":true}'
call PATCH "$VULN/users/me" 2 '{"name":"Alice B.","store_credit":1000}'

echo "########## Secure app ($SECURE)"
call POST  "$SECURE/users" "" '{"email":"alice@example.com","name":"Alice","password":"alice-pass-1"}'
call POST  "$SECURE/users" "" '{"email":"mallory@example.com","name":"Mallory","password":"mallory-pass-1","role":"admin","store_credit":500,"email_verified":true}'
call PATCH "$SECURE/users/me" 2 '{"name":"Alice B.","store_credit":1000}'
call PATCH "$SECURE/users/me" 2 '{"name":"Alice B."}'
call PATCH "$SECURE/users/me" 2 '{"id":2,"email":"alice@example.com","name":"Alice C.","role":"customer","store_credit":0,"email_verified":false}'
call PATCH "$SECURE/admin/users/2" 2 '{"role":"admin"}'
call PATCH "$SECURE/admin/users/2" 1 '{"role":"editor"}'
