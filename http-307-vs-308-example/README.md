Source code for the article [HTTP 307 vs 308 Redirects](https://restfulapi.net/http-307-vs-308/)

A small FastAPI Orders API that answers with HTTP 301, 302, 303, 307 and 308, plus HTTP clients (curl, Python requests, Node.js fetch(), Java HttpClient and HttpURLConnection) that show which method, body and Authorization header reach the redirect target.

## Versions

- Python 3.13, FastAPI 0.142.2 (Starlette 1.7.0), uvicorn 0.54.0, requests 2.34.2, httpx2 2.13.1 and pytest 9.1.1 for the tests
- curl 8.5.0, Node.js 22.22.0, OpenJDK 21.0.12
- Optional browser check: Playwright for Python 1.56.0 with Chromium 141
- OpenSSL (the run script creates a self-signed certificate for the HTTPS port)

## Ports

- 9190: the Orders API over HTTP
- 9191: an HTTP listener that redirects every request to HTTPS with 308
- 9192: the same Orders API over HTTPS

## Run

Prerequisites: Python 3.13, curl, OpenSSL, Node.js 22 and (optional) Java 21.

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/http-307-vs-308-example
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run-demo.sh
```

The script starts the three servers, runs every client, prints the results and stops the servers. `OUTPUTS.txt` holds the output of one run.

Optional browser cache check (step 10 of the script runs it when Playwright is installed):

```bash
.venv/bin/pip install playwright==1.56.0
.venv/bin/playwright install chromium
./run-demo.sh
```

## Files

- `app.py`: the Orders API. `POST /v1/orders` answers 308 to `/v2/orders`; `/lab/{code}` redirects any method to `/echo` with the given status code (`?cross=1` sends it to another host name); `/echo` reports the method, body size and Authorization header that arrived; `/loop/{hop}` never stops redirecting; `/cache/{code}` counts how often a browser asks for a redirect.
- `http_redirector.py`: the HTTP to HTTPS redirector on port 9191.
- `clients/curl_matrix.sh`, `clients/requests_matrix.py`, `clients/fetch_matrix.mjs`, `clients/RedirectMatrix.java`: the same POST and PUT tests for each client.
- `clients/follow_308.py`: follows a 307 or 308 by hand, only on the same host, and remembers the new URL after a 308.
- `clients/LoopCheck.java`: what Java HttpClient returns on an endless redirect chain.
- `clients/UrlConnectionCheck.java`: the older `java.net.HttpURLConnection`, which does not follow 308.
- `browser_cache_check.py`: calls the `/cache` URLs three times each from Chromium.
- `test_redirects.py`: pytest tests for the 308 and the followed request.
- `run-demo.sh`: runs everything.

Run a single client while the API is running on port 9190:

```bash
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 9190 &
./clients/curl_matrix.sh
.venv/bin/python clients/requests_matrix.py
node clients/fetch_matrix.mjs
java clients/RedirectMatrix.java
```

## Express snippet

The folder `snippets/` holds the Express 5.2.1 example from the article. It is not part of `run-demo.sh`:

```bash
cd snippets
npm install
node express-redirect.mjs &          # port 9193
curl -si -X POST http://127.0.0.1:9193/v1/orders
```
