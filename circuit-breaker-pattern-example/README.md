Source code for the article [Circuit Breaker Pattern for API Calls](https://restfulapi.net/circuit-breaker-pattern/)

# A circuit breaker between a bookstore API and its inventory API

A bookstore API (FastAPI, port 9600) calls an inventory API (port 9601) for every book page and every order. The inventory API can be switched to healthy, slow (5-second answers) or down (HTTP 503). The bookstore protects the call with a small circuit breaker written from scratch in `breaker.py`, so every state change is easy to follow:

- CLOSED: calls go through; 5 consecutive failures (timeouts, connection errors, 5xx) open the breaker. A 404 does not count.
- OPEN: calls are rejected at once for 10 seconds. `GET /books/{id}` falls back to `"in_stock": null`; `POST /orders` answers HTTP 503 with `Retry-After` and Problem Details.
- HALF_OPEN: after 10 seconds, one trial call goes through. Success closes the breaker, failure opens it again.

A load test compares 50 requests against the slow inventory API with and without the breaker. The `node/` folder does the same with the [opossum](https://github.com/nodeshift/opossum) library.

## Files

| File | What it does |
|---|---|
| breaker.py | The circuit breaker: three states, consecutive-failure threshold, one trial call in HALF_OPEN |
| inventory_service.py | Inventory API with `POST /admin/mode?mode=healthy\|slow\|down` and a request counter |
| store_api.py | Bookstore API: `GET /books/{id}` with a fallback, `POST /orders` with HTTP 503 + Retry-After, `GET /admin/breaker` |
| load_test.py | Sends N requests, C at a time, and prints latency and how many calls reached the inventory API |
| test_breaker.py | pytest unit tests of every state change, with a fake clock |
| demo.sh | Starts both APIs and runs every case, including the load test and the opossum demo |
| node/opossum_demo.js | The same inventory call protected by opossum |
| OUTPUTS.txt | Output of one run of the tests and demo.sh |

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.143.0, uvicorn 0.54.0, httpx 0.28.1, pytest 9.1.1 (pinned in requirements.txt)
- Node.js 22 and opossum 10.0.0 (pinned in node/package.json)
- curl and bash for demo.sh (on Windows, use Git Bash or WSL)

## How to run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -v test_breaker.py
(cd node && npm install)      # optional, for section 8
./demo.sh
```

The demo uses ports 9600 and 9601 and takes about 45 seconds. Settings for the bookstore API are environment variables: `BREAKER=on|off`, `FAILURE_THRESHOLD` (default 5), `OPEN_SECONDS` (default 10) and `INVENTORY_TIMEOUT` (default 2 seconds).

The breaker keeps its state in memory, in one process. With several bookstore instances, each instance has its own breaker, which is what most libraries do as well.
