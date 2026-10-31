Source code for the article [Authorization Header: Basic, Bearer and Other Schemes](https://restfulapi.net/authorization-header/)

A small orders API protects `GET /basic/orders` with Basic credentials and `GET /bearer/orders` with a Bearer token. The same two endpoints exist in FastAPI, Express and Spring Boot, so we can send all three the same correct and broken `Authorization` headers and compare the answers.

The project shows:

- the 401 challenge and the retry with credentials, as raw HTTP
- how a Basic value is built byte by byte, and how to parse the header by hand in Python (`fastapi/parse_header.py`)
- how curl, Python requests, Node.js `fetch()`, browser-style `btoa()` and Java `HttpClient` set the header
- which clients keep the header on a redirect, and the CORS preflight in headless Chromium
- a status code grid for 18 header variants against the three frameworks (`probe.sh`)
- logging only the scheme name, never the credentials

All credentials in this folder are FAKE demo values for local tests: user `reports-app`, password `demo-pass-123`, and the HS256 token in `demo-token.txt`, signed with the demo key `demo-secret-key-123-only-for-local-tests` (`make_token.py` rebuilds it). Never reuse them anywhere else.

## Files

- `fastapi/main.py`: the orders API with FastAPI's `HTTPBasic` and `HTTPBearer`, plus a middleware that logs the scheme only
- `fastapi/parse_header.py`: `parse_authorization()`, `decode_basic()` and `scheme_for_log()`, written by hand
- `express/auth.js`, `express/server.js`: the same API in Express with the basic-auth package and a Bearer regex; `express/parse_demo.mjs` prints what the helpers return
- `spring/`: the same API in Spring Boot with `httpBasic()` and `oauth2ResourceServer().jwt()`
- `probe.sh`: sends 18 correct and malformed headers to all three apps
- `clients/`: an echo server that prints the headers it receives and answers HTTP 302 for the redirect tests, plus the curl, requests, `fetch()`, `btoa()` and `HttpClient` demos and the non-ASCII password check
- `cors/`: a page origin and an API origin for the CORS preflight and cross-origin redirect check in Chromium
- `run_all.sh`: starts every server, runs every demo and stops the servers
- `OUTPUTS.txt`: the output of one full run

## Versions

- Python 3.13.18, FastAPI 0.142.2 (Starlette 1.7.0, Pydantic 2.13.5), uvicorn 0.54.0, requests 2.34.2
- Playwright for Python 1.63.0 with its Chromium 153 build (CORS demo only)
- Node.js 22.23.4, Express 5.2.1, basic-auth 3.0.0
- OpenJDK 25.0.4.1, Maven 3.9.11, Spring Boot 4.1.1 (Spring Security 7.1.1)
- curl 8.5.0

## Ports

| Port | What |
|---|---|
| 9761 | Express app |
| 9762 | FastAPI app |
| 9763 | Spring Boot app |
| 9771, 9772 | Echo servers for the client and redirect demos |
| 9780, 9781, 9782 | CORS demo: page origin, API origin, and a second API port |

## How to Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/authorization-header-example

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

(cd express && npm install)
(cd spring && mvn -q -DskipTests package)

./run_all.sh
```

To try only the FastAPI app:

```bash
cd fastapi
uvicorn main:app --host 127.0.0.1 --port 9762

# in a second terminal
curl -i http://127.0.0.1:9762/basic/orders
curl -i -u reports-app:demo-pass-123 http://127.0.0.1:9762/basic/orders
curl -i -H "Authorization: Bearer $(cat ../demo-token.txt)" http://127.0.0.1:9762/bearer/orders
```
