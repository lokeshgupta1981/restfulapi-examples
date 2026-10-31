Source code for the article [What Is an API Gateway](https://restfulapi.net/what-is-an-api-gateway/)

# A minimal API gateway in front of a bookstore API

A small API gateway written in Python, so that every step a gateway takes is visible in about 150 lines. It sits in front of two services, books and orders, and for each request it:

- gives the request an ID (`X-Request-Id`) and writes one access-log line,
- checks an API key (`X-API-Key`) and answers HTTP 401 without one,
- limits each client to a number of requests per 10-second window (HTTP 429 with `Retry-After`),
- caches `GET /api/books` for 30 seconds (`X-Cache: MISS` / `HIT`),
- routes `/api/books/...` and `/api/orders/...` to the right service, removing the API key and adding `X-Client-Id`,
- gives up on a slow service after 2 seconds (HTTP 504) and reports a service that is down (HTTP 502),
- composes one response from both services at `/api/order-summary/{id}`.

The gateway is for learning. For real traffic, use a real gateway (Kong, Apache APISIX, Envoy Gateway, Tyk, KrakenD, or your cloud's managed gateway).

The API keys in `gateway.py` are fake demo keys.

## Versions

- Python 3.13, fastapi 0.143.0, uvicorn 0.54.0, httpx 0.28.1 (pinned in requirements.txt)
- curl for the demo
- nginx 1.24.0 for the benchmark comparison (optional; `bench.sh` skips it if nginx is not installed)

## Files

| File | What it does |
|---|---|
| gateway.py | The gateway on port 8000: request ID, API key check, rate limit, cache, routing, timeouts, composition, access log |
| services.py | The books service (`SERVICE=books`, port 8001) and the orders service (`SERVICE=orders`, port 8002); `/stats` counts the requests each one received |
| demo.sh | Starts all three apps and runs every case with curl, then prints the gateway access log |
| bench.py | Sends the same GET 2,000 times directly to the books service, through the gateway and through plain nginx, and prints median and p95 latency |
| bench.sh | Starts the books service, the gateway and nginx, then runs bench.py |
| nginx-bench.conf.template | The plain nginx reverse proxy used by bench.sh |
| OUTPUTS.txt | Output of demo.sh and three runs of bench.sh |

## How to run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./demo.sh                        # Windows: run in Git Bash or WSL
./bench.sh 2000
```

The ports default to 8000 (gateway), 8001 (books), 8002 (orders) and 8080 (nginx). Change them with `GATEWAY_PORT`, `BOOKS_PORT`, `ORDERS_PORT` and `NGINX_PORT`, for example `GATEWAY_PORT=9000 ./demo.sh`.

To try requests by hand:

```bash
SERVICE=books  uvicorn services:app --port 8001 &
SERVICE=orders uvicorn services:app --port 8002 &
uvicorn gateway:app --port 8000 &
curl -i -H 'X-API-Key: demo-key-mobile-123' http://localhost:8000/api/orders/1042
```
