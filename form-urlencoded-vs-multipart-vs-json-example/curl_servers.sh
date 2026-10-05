#!/usr/bin/env bash
# Sends the same requests (correct and wrong) to the Express (9171),
# FastAPI (9172) and Spring Boot (9173) servers. Run from the example root folder.
run() {
  echo "\$ $*"
  "$@"
  echo
  echo
}

TICKET='{"subject":"Login fails & shows 500","priority":"high","tags":["auth","web"],"customer":{"id":"c-1042","plan":"pro"}}'

for BASE in http://127.0.0.1:9171 http://127.0.0.1:9172 http://127.0.0.1:9173; do
  FORM_URL=$BASE/tickets
  UPLOAD_URL=$BASE/tickets
  if [ "$BASE" = http://127.0.0.1:9172 ]; then
    FORM_URL=$BASE/tickets/form
    UPLOAD_URL=$BASE/tickets/upload
  fi
  echo "########## $BASE"
  run curl -s "$BASE/tickets" --json "$TICKET"
  run curl -s "$FORM_URL" --data-urlencode "subject=Login fails & shows 500" -d priority=high -d tags=auth -d tags=web
  run curl -s "$UPLOAD_URL" -F "subject=Login fails & shows 500" -F priority=high -F "attachment=@error.log;type=text/plain"
  run curl -s "$FORM_URL" -d "subject=Login" -d "customer[id]=c-1042" -d "customer[plan]=pro"
  echo "# mistakes"
  run curl -s -i "$FORM_URL" -d '{"subject":"Login fails & shows 500","priority":"high"}'
  run curl -s -i "$BASE/tickets" -d 'subject=Login&priority=high'
  run curl -s -i "$BASE/tickets" -H "Content-Type: text/plain" -d '{"subject":"Login"}'
  run curl -s -i "$UPLOAD_URL" -H "Content-Type: multipart/form-data" -d 'subject=Login'
  run curl -s -i "$BASE/tickets" --json '{"subject":"Login",}'
done

echo "########## OAuth token endpoint (Express)"
run curl -s -i http://127.0.0.1:9171/oauth/token -u ticket-cli:s3cret -d grant_type=client_credentials --data-urlencode "scope=tickets:read tickets:write"
run curl -s -i http://127.0.0.1:9171/oauth/token -u ticket-cli:s3cret --json '{"grant_type":"client_credentials"}'

echo "########## Nested JSON plus a file in one multipart request (Spring Boot, then Express)"
run curl -s http://127.0.0.1:9173/tickets/with-attachment \
  -F 'ticket={"subject":"Login fails & shows 500","tags":["auth"],"customer":{"id":"c-1042","plan":"pro"}};type=application/json' \
  -F "attachment=@error.log;type=text/plain"
run curl -s http://127.0.0.1:9171/tickets/with-attachment \
  -F 'ticket={"subject":"Login fails & shows 500","tags":["auth"],"customer":{"id":"c-1042","plan":"pro"}};type=application/json' \
  -F "attachment=@error.log;type=text/plain"
