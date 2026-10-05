Source code for the article [HTTP 406 Not Acceptable](https://restfulapi.net/http-status-406-not-acceptable/)

# A reports API that answers HTTP 406, in FastAPI, Express and Spring Boot

`GET /reports/{month}` returns a monthly sales report as `application/json` or `text/csv`, chosen from the `Accept` header and its q-values. When no format matches, the FastAPI and Express apps answer with HTTP 406 and a Problem Details body (`application/problem+json`) that lists the available formats, plus `Vary: Accept`. The Spring Boot app shows the framework's built-in HTTP 406, and HTTP 415 for comparison.

## Versions

- Python 3.13: FastAPI 0.142.2 (Starlette 1.7.0), uvicorn 0.54.0, requests 2.34.2, httpx 0.28.1, pytest 9.1.1 (pinned in requirements.txt)
- Node.js 22 with Express 5.2.1 (pinned in express/package.json)
- JDK 21, Maven 3.9, Spring Boot 4.1.1 (spring-boot-starter-webmvc)
- curl 8.5.0

## Files

| File | What it does |
|---|---|
| fastapi/main.py | Reports API on port 9406: Accept parsing with q-values, HTTP 406 with Problem Details, and `/plain-reports/{month}`, which ignores Accept |
| fastapi/test_main.py | pytest checks for HTTP 406, q-values and a missing Accept header |
| express/server.js | Port 9407: `res.format()` with and without a `default` handler, and `res.json()`, which ignores Accept |
| spring/ | Port 9408: a `@RestController` that can only produce JSON (HTTP 406 for other Accept values), a `produces = application/xml` endpoint, a class without getters, and a JSON-only POST endpoint (HTTP 415) |
| spring/.../NotAcceptableHandler.java | `@ExceptionHandler` for `HttpMediaTypeNotAcceptableException` that sends the same `available` list as FastAPI (on with `--reports.custom-406=true`) |
| spring/pom-no-jackson.xml | Same app without Jackson, built into `target-no-jackson/`, to show the HTTP 406 a missing JSON library causes |
| clients/fetch_report.py | Client that reads the HTTP 406 body and retries once with a format from the list; stops with a message when the 406 body is not JSON. Usage: `.venv/bin/python clients/fetch_report.py URL` |
| run_all.sh | Starts all apps (Spring Boot four times: Problem Details on, off, without Jackson, with the custom handler; Express twice: development and production), runs the requests, the client and the tests, stops the apps |
| OUTPUTS.txt | Output of one run of run_all.sh |

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
(cd express && npm install)
(cd spring && mvn -q -DskipTests package && mvn -q -f pom-no-jackson.xml -DskipTests package)
./run_all.sh
```

Ports used: 9406 (FastAPI), 9407 and 9410 (Express), 9408, 9409, 9411 and 9412 (Spring Boot).

To run one app by hand:

```bash
cd fastapi && ../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 9406
curl -si -H 'Accept: application/xml' http://127.0.0.1:9406/reports/2026-09
```

## Results for `Accept: application/xml`

| App | Status | Body |
|---|---|---|
| FastAPI route that returns a dict | 200 | JSON report |
| FastAPI `/reports/{month}` | 406 | Problem Details with the available formats |
| Express `res.json()` | 200 | JSON report |
| Express `res.format()` without `default` | 406 | HTML error page |
| Express `res.format()` with `default` | 406 | Problem Details |
| Spring Boot, `spring.mvc.problemdetails.enabled=true` | 406 | `application/problem+json`, detail lists the JSON types |
| Spring Boot, Problem Details off | 406 | empty |

## Spring Boot 4.1.1 causes of HTTP 406 (tested)

| Case | Result |
|---|---|
| `Accept: application/xml`, only Jackson present | 406 |
| `produces = application/xml`, `Accept: application/json` | 406 (with `Accept: */*`: 500, no XML converter) |
| Jackson excluded (`pom-no-jackson.xml`) | 406 with an empty body for every request |
| Returned class without getters | 200 with `{}` (older Spring versions gave 406) |
