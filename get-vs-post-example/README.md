Source code for the article [GET vs POST: Differences for REST APIs](https://restfulapi.net/get-vs-post/)

# GET vs POST example

A small Orders API (FastAPI) behind nginx, plus scripts that show where GET and POST behave differently in practice.

- `app.py`: Orders API on port 9120. `GET /orders` lists orders with query filters and `Cache-Control: public, max-age=60`, and `GET /orders/{id}` returns one order. `POST /orders` creates an order (HTTP 201 with `Location`). `POST /orders/search` takes the same filters in a JSON body. `/unstable` always answers HTTP 503. `/login` sets a `SameSite=Lax` session cookie, and `/orders/{id}/cancel` exists as GET (the wrong design) and as POST. `/stats` counts the requests that reached the app, `/cancel-log` lists every cancel attempt with its status. Both count from app start.
- `nginx/nginx.conf`: nginx on port 9121. `/orders` goes through a proxy cache and adds `X-Cache-Status`. `/pool/` goes to an upstream pool whose first server drops every connection and whose backup server is the app.
- `dropper.py`: the broken upstream server on port 9122. It reads the request and closes the connection without a response.
- `attacker/`: three pages served from `http://127.0.0.1:9123`, a different site from `http://localhost:9120`: a link (GET), an image (GET) and a form (POST) that all try to cancel an order.
- `demo.sh`: curl calls for caching, logging, repeated POST and proxy retries.
- `retry_client.py`: a `requests` session with urllib3 `Retry` on HTTP 503; counts how many attempts reach the app for GET and POST.
- `get_body.mjs`: `fetch()` with a GET body, then the same filter as a POST search.
- `csrf_demo.py`: logs in with Chromium (Playwright), opens the three attacker pages and prints which cancel requests carried the cookie.
- `start.sh` and `stop.sh`: start and stop the app, nginx, the broken upstream and the attacker pages.
- `run_all.sh`: starts all servers, runs every demo and stops the servers. `OUTPUTS.txt` holds a captured run.

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.142.2, uvicorn 0.54.0, requests 2.34.2, urllib3 2.8.0, playwright 1.63.0 (Chromium 153)
- nginx 1.24.0 (any version from 1.9.13 has the retry rule shown here)
- Node.js 22 (for `get_body.mjs`, no packages)
- curl

## Run

Needs Python 3.10 or later, Node.js 22, nginx and curl.

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/get-vs-post-example
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
./run_all.sh
```

To repeat single calls, start the servers, run any command from `demo.sh` or any script, and stop them:

```bash
./start.sh
curl -s -i "http://localhost:9121/orders?status=paid"
.venv/bin/python retry_client.py
./stop.sh
```

The app keeps its data in memory, so restart it to reset orders, counters and the cancel log.
