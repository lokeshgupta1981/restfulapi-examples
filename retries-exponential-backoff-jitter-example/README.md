Source code for the article [API Retries with Exponential Backoff and Jitter](https://restfulapi.net/retries-exponential-backoff-jitter/)

# Retries with exponential backoff and jitter

A small orders API in Python (FastAPI) that fails on purpose, and clients that retry it safely:

- `retry.py`: a retry helper for httpx. It retries 408, 429, 500, 502, 503 and 504 responses, connection errors and timeouts. It waits a random time between 0 and `min(cap, base * 2 ** attempt)` (exponential backoff with full jitter), or the time in the `Retry-After` header when the server sends one. It only retries idempotent methods (GET, HEAD, OPTIONS, PUT, DELETE) and POST requests that carry an `Idempotency-Key` header.
- `server.py`: the API. `GET /orders/{id}?fail=N` answers 503 for the first N calls for that id. `GET /reports/{name}` answers 429 with `Retry-After: 2` the first time. `GET /orders/9000` and higher answer 404. `POST /orders?slow=S` takes S seconds; with an `Idempotency-Key`, a retry gets the first order back instead of a new one.
- `client.py`: runs the helper against the API (scenarios `503`, `429`, `404`, `post-naive`, `post-no-key`, `post`). `post-naive` shows the mistake: retrying a POST without a key creates five orders.
- `requests_retry.py`: the same retries with `requests` and urllib3's built-in `Retry` class.
- `retry.mjs`: the same helper in JavaScript with `fetch` (Node 18 or later).
- `test_retry.py`: checks the backoff range and the `Retry-After` parsing (seconds and HTTP date).
- `herd_sim.py`: a seeded simulation of 100 clients retrying against a server that is down for 1 s and then serves 10 requests per 100 ms. It compares a fixed 100 ms delay, exponential backoff without jitter, and exponential backoff with full jitter. It writes the per-100 ms request counts of one run to `herd-timeline.json`.
- `demo.sh`: starts the server and runs everything.
- `OUTPUTS.txt`: the output of `./demo.sh` from a real run. The retry waits are random, so your numbers will differ; `herd_sim.py` uses fixed seeds and prints the same table every time.

## Versions

- Python 3.13 (3.10 or later works), Node.js 22 (18 or later works)
- fastapi 0.143.0, uvicorn 0.54.0, httpx 0.28.1, requests 2.34.2, urllib3 2.8.0 (pinned in `requirements.txt`)
- curl and bash for `demo.sh` (on Windows, use Git Bash or WSL)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/retries-exponential-backoff-jitter-example
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

./demo.sh                          # everything, about 40 seconds
```

Or step by step:

```bash
uvicorn server:app --port 8000     # terminal 1
python client.py 503               # terminal 2; also 429, 404, post-naive, post-no-key, post
python requests_retry.py
node retry.mjs
python test_retry.py
python herd_sim.py                 # no server needed
```

The server keeps its state in memory. Restart it to reset the failure counters (each order id fails only for its first N calls).
