Source code for the article [Idempotent REST API](https://restfulapi.net/idempotent-rest-apis/)

# Idempotent REST API example

A small orders API in Python (FastAPI) with SQLite that shows which HTTP methods are idempotent and how to make POST requests safe to retry:

- `PUT /orders/{id}` creates or replaces an order. The same PUT sent twice gives HTTP 201 and then HTTP 200 with the same `ETag`.
- `DELETE /orders/{id}` gives HTTP 204 and then HTTP 404. The order stays deleted.
- `POST /orders` creates a new order with a server-generated id on every call. With an `Idempotency-Key` header, the server stores the first response and replays it for every retry with the same key (`Idempotent-Replayed: true`). A key reused with a different body gets HTTP 422. A retry while the first request is still running gets HTTP 409. A key stuck in "processing" for more than `PROCESSING_TIMEOUT_SECONDS` (default 30) can be taken over by a retry.
- `PATCH /orders/{id}` accepts JSON Patch (`application/json-patch+json`, RFC 6902) and an optional `If-Match` header. A stale `If-Match` gets HTTP 412.
- Errors use Problem Details (`application/problem+json`, RFC 9457).

The idempotency keys are claimed with `INSERT ... ON CONFLICT(idem_key) DO NOTHING`, which also works in PostgreSQL. The example never deletes old keys. In production, add a job that deletes keys older than your documented retention period.

## Files

- `app.py`: the API.
- `methods.sh`: PUT, DELETE and POST sent twice each, POST with the same key twice, and the same key with a different body.
- `patch.sh`: JSON Patch `replace` and `add` sent twice each, and `add` with `If-Match` sent twice.
- `test_idempotency.sh`: sends one POST twice with the same key and checks that the order count grows by one.
- `retry_client.py`: a client with a 1-second timeout that retries a POST request with exponential backoff and jitter, with or without an idempotency key (standard library only).
- `OUTPUTS.txt`: output of all scripts from a real run.

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.14.0, jsonpatch 1.34 (pinned in `requirements.txt`)
- curl and bash for the shell scripts (on Windows, use Git Bash or WSL)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/idempotent-rest-apis-example
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app:app --port 8000        # terminal 1
./methods.sh                       # terminal 2
```

The scripts expect an empty database. Stop the server, delete `orders.db` and start the server again before each of `patch.sh` and `test_idempotency.sh`.

To see a timeout and a retry, start the server with a slow create step:

```bash
SLOW_CREATE_SECONDS=2 uvicorn app:app --port 8000   # terminal 1
python retry_client.py                              # terminal 2: every retry creates one more order
curl -s http://localhost:8000/orders
```

Then delete `orders.db`, restart the server the same way and run `python retry_client.py --key`. The client sends the same key with every attempt, gets HTTP 409 while the first request runs, then the replayed HTTP 201, and the server holds one order. The number of attempts can differ between runs because the waits are random.

To use another port, start uvicorn with `--port 9000` and run the scripts with `BASE=http://localhost:9000`.
