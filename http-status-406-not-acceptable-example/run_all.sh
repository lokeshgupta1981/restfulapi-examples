#!/usr/bin/env bash
# Starts the FastAPI, Express and Spring Boot apps, sends the requests used in
# the article, runs the client and the tests, stops the apps and writes OUTPUTS.txt.
#
# Ports:
#   9406 FastAPI
#   9407 Express (development)        9410 Express (NODE_ENV=production)
#   9408 Spring Boot (Problem Details on, built-in 406 body)
#   9409 Spring Boot (Problem Details off)
#   9411 Spring Boot without Jackson (pom-no-jackson.xml)
#   9412 Spring Boot with the custom 406 handler (reports.custom-406=true)
set -u
cd "$(dirname "$0")"
OUT=OUTPUTS.txt
: > "$OUT"
SPRING_JAR=target/reports-spring-1.0.0.jar
PIDS=()


(cd fastapi && exec ../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 9406 > /dev/null 2>&1) & PIDS+=($!)
(cd express && exec node server.js > /dev/null 2>&1) & PIDS+=($!)
(cd express && NODE_ENV=production PORT=9410 exec node server.js > /dev/null 2>&1) & PIDS+=($!)
(cd spring && exec java -jar $SPRING_JAR > /dev/null 2>&1) & PIDS+=($!)
(cd spring && exec java -jar $SPRING_JAR --server.port=9409 --spring.mvc.problemdetails.enabled=false > /dev/null 2>&1) & PIDS+=($!)
(cd spring && exec java -jar target-no-jackson/reports-spring-no-jackson-1.0.0.jar --server.port=9411 > /dev/null 2>&1) & PIDS+=($!)
(cd spring && exec java -jar $SPRING_JAR --server.port=9412 --reports.custom-406=true > /dev/null 2>&1) & PIDS+=($!)

for port in 9406 9407 9408 9409 9410 9411 9412; do
  for attempt in $(seq 1 60); do
    curl -s -o /dev/null "http://127.0.0.1:$port/" && break
    sleep 1
  done
done

run() {
  echo "\$ $*" >> "$OUT"
  "$@" >> "$OUT" 2>&1
  echo >> "$OUT"
  echo >> "$OUT"
}

echo "### FastAPI (port 9406)" >> "$OUT"
run curl -si -H 'Accept: application/json' http://127.0.0.1:9406/reports/2026-09
run curl -si -H 'Accept: text/csv' http://127.0.0.1:9406/reports/2026-09
run curl -si -H 'Accept: text/csv;q=0.5, application/json;q=0.4' http://127.0.0.1:9406/reports/2026-09
run curl -si -H 'Accept: application/xml' http://127.0.0.1:9406/reports/2026-09
run curl -si -H 'Accept: application/xml, */*;q=0.1' http://127.0.0.1:9406/reports/2026-09
run curl -si -H 'Accept: */*;q=0' http://127.0.0.1:9406/reports/2026-09
run curl -si -H 'Accept: application/xml' http://127.0.0.1:9406/plain-reports/2026-09

echo "### Express (port 9407)" >> "$OUT"
run curl -si -H 'Accept: text/csv' http://127.0.0.1:9407/reports/2026-09
run curl -si -H 'Accept: application/xml' http://127.0.0.1:9407/reports/2026-09
run curl -s -o /dev/null -w '%{http_code} %{content_type}\n' -H 'Accept: application/xml' http://127.0.0.1:9407/bare-reports/2026-09
run curl -si -H 'Accept: application/xml' http://127.0.0.1:9407/plain-reports/2026-09

echo "### Express with NODE_ENV=production (port 9410)" >> "$OUT"
run curl -si -H 'Accept: application/xml' http://127.0.0.1:9410/bare-reports/2026-09

echo "### Spring Boot (port 9408)" >> "$OUT"
run curl -si -H 'Accept: application/xml' http://127.0.0.1:9408/reports/2026-09
run curl -si -H 'Accept: application/json' http://127.0.0.1:9408/xml-reports/2026-09
run curl -si http://127.0.0.1:9408/xml-reports/2026-09
run curl -si http://127.0.0.1:9408/hidden-reports/2026-09

echo "### Spring Boot with Problem Details turned off (port 9409)" >> "$OUT"
run curl -si -H 'Accept: application/xml' http://127.0.0.1:9409/reports/2026-09

echo "### Spring Boot without Jackson (port 9411)" >> "$OUT"
run curl -si http://127.0.0.1:9411/reports/2026-09

echo "### Spring Boot with the custom 406 handler (port 9412)" >> "$OUT"
run curl -si -H 'Accept: application/xml' http://127.0.0.1:9412/reports/2026-09

echo "### Spring Boot: HTTP 415 for comparison (port 9408)" >> "$OUT"
run curl -si -H 'Content-Type: text/plain' -d 'call the north team' http://127.0.0.1:9408/reports/2026-09/notes
run curl -si -H 'Content-Type: text/plain' -H 'Accept: application/xml' -d 'call the north team' http://127.0.0.1:9408/reports/2026-09/notes

echo "### Client that handles HTTP 406" >> "$OUT"
run .venv/bin/python clients/fetch_report.py http://127.0.0.1:9406/reports/2026-09
run .venv/bin/python clients/fetch_report.py http://127.0.0.1:9407/reports/2026-09
run .venv/bin/python clients/fetch_report.py http://127.0.0.1:9412/reports/2026-09
run .venv/bin/python clients/fetch_report.py http://127.0.0.1:9407/bare-reports/2026-09
run .venv/bin/python clients/fetch_report.py http://127.0.0.1:9409/reports/2026-09

echo "### Tests" >> "$OUT"
(cd fastapi && exec ../.venv/bin/pytest -q -p no:warnings) >> "$OUT" 2>&1

kill "${PIDS[@]}" 2>/dev/null
echo "Wrote $OUT"
