Source code for the article [application/json: The JSON Content-Type](https://restfulapi.net/application-json-content-type/)

The same `POST /orders` endpoint in Express, FastAPI and Spring Boot, a probe script that sends it different `Content-Type` headers, client scripts that show which `Content-Type` curl, Python requests, Node.js fetch and Java HttpClient send by default, and a headless-browser check of the CORS preflight that `application/json` triggers.

## Versions

- Node.js 22, Express 5.2.1
- Python 3.13, FastAPI 0.142.2 (Starlette 1.7.0, Pydantic 2.13.5), uvicorn 0.54.0, requests 2.34.2
- JDK 21, Maven 3.9, Spring Boot 4.1.1 (spring-boot-starter-webmvc)
- curl 8.5.0 (`--json` needs curl 7.82.0 or later)
- Playwright for Python 1.56.0 with its Chromium build (CORS demo only)

## Ports

| Port | What |
|---|---|
| 9300 | Echo server for the client demos (`clients/echo_server.py`) |
| 9301 | Express app (`express/server.js`) |
| 9302 | FastAPI app (`fastapi/main.py`) |
| 9303 | Spring Boot app (`spring/`) |
| 9310, 9311 | CORS demo: page origin and API origin (`cors/cors_server.py`) |

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/application-json-content-type-example

# Express (terminal 1)
cd express && npm install && node server.js

# FastAPI (terminal 2)
cd fastapi
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 9302

# Spring Boot (terminal 3)
cd spring && mvn -q -DskipTests package && java -jar target/orders-spring-1.0.0.jar

# Echo server for the client demos (terminal 4)
cd clients && python3 echo_server.py

# CORS demo servers (terminal 5)
cd cors
pip install -r requirements.txt && python -m playwright install chromium
python3 -u cors_server.py > api.log

# Run every demo and write OUTPUTS.txt (terminal 6)
bash run_all.sh
```

The client demos use the FastAPI virtual environment for Python requests (`fastapi/.venv`). `java HttpClientDemo.java` runs as a single-file program, so it needs no build.

## Files

- `express/plus_json.mjs` starts a second Express app on port 9399 whose `express.json()` parser also accepts `application/*+json` types (`node express/plus_json.mjs`).
- `probe.sh` sends the same order in 13 cases (mostly different headers) to the three servers and prints the status, the response `Content-Type` and the body.
- `clients/clients.sh` prints the `Content-Type` and `Accept` headers that each HTTP client sends, then runs `parse_check.mjs`, which shows the `SyntaxError` that `res.json()` throws on an HTML error page.
- `cors/cors_check.py` opens a page on one origin in headless Chromium and calls the API on another origin with `text/plain` and `application/json`; `cors/api.log` shows which calls caused an `OPTIONS` preflight.
