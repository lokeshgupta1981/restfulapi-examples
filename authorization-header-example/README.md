Source code for the article [Authorization Header: Basic, Bearer and Other Schemes](https://restfulapi.net/authorization-header/)

The same protected `GET /basic/orders` and `GET /bearer/orders` endpoints in Express, FastAPI and Spring Boot (Spring Security), a probe script that sends them correct and malformed `Authorization` headers, client demos that show how curl, Python requests, Node.js `fetch()` and Java `HttpClient` set the header and what they do with it on redirects, and a headless Chromium check of the CORS preflight and of a cross-origin redirect.

All credentials in this folder are demo values for local tests: user `reports-app`, password `demo-pass-123`, and the HS256 token in `demo-token.txt`, signed with the demo key `demo-secret-key-123-only-for-local-tests` (`make_token.py` rebuilds it). Never reuse them anywhere else.

## Versions

- Node.js 22, Express 5.2.1, basic-auth 3.0.0
- Python 3.13, FastAPI 0.142.2 (Starlette 1.7.0, Pydantic 2.13.5), uvicorn 0.54.0
- requests 2.34.2 (client demos)
- JDK 21, Maven 3.9, Spring Boot 4.1.1 (Spring Security 7.1.1)
- curl 8.5.0
- Playwright for Python 1.56.0 with its Chromium build (Chromium 141), CORS demo only

## Ports

| Port | What |
|---|---|
| 9761 | Express app (`express/server.js`) |
| 9762 | FastAPI app (`fastapi/main.py`) |
| 9763 | Spring Boot app (`spring/`) |
| 9771, 9772 | Echo servers for the client demos (`clients/echo_server.py`) |
| 9780, 9781, 9782 | CORS demo: page origin, API origin, and a second API port for the redirect test (`cors/cors_server.py`) |

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/authorization-header-example

# Express (terminal 1)
cd express && npm install && node server.js

# FastAPI (terminal 2)
cd fastapi
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --host 127.0.0.1 --port 9762

# Spring Boot (terminal 3)
cd spring && mvn -q -DskipTests package && java -jar target/auth-header-spring-1.0.0.jar

# Echo servers for the client demos (terminal 4)
cd clients
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
python3 echo_server.py 9771 &
python3 echo_server.py 9772 &

# CORS demo server (terminal 5)
cd cors
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/python cors_server.py
```

Then run everything from the folder root:

```bash
./probe.sh      # status code grid for 18 Authorization headers
./run_all.sh    # probe grid, 401 responses, client demos, Chromium check
```

`OUTPUTS.txt` holds the output of one full run, plus the Express server log.

## Files

- `express/auth.js`: `parseBasic()` from `basic-auth`, `bearerToken()`, `safeEqual()` and `schemeForLog()`; `express/server.js` uses them; `express/parse_demo.mjs` prints what they return
- `fastapi/main.py`: `HTTPBasic` and `HTTPBearer` dependencies
- `spring/`: two `SecurityFilterChain` beans, `httpBasic()` and `oauth2ResourceServer().jwt()`
- `probe.sh`: sends correct and malformed headers to all three apps
- `clients/`: curl, requests, `fetch()`, browser-style `btoa()` and `HttpClient` demos, redirect tests, non-ASCII password check
- `cors/`: preflight with `Authorization`, the `*` wildcard, and a cross-origin redirect in Chromium
