Source code for the article [REST API Interview Questions and Answers](https://restfulapi.net/rest-api-interview-questions/)

# REST API interview questions: example Orders API

A small FastAPI Orders API that shows, with real HTTP, the behavior behind the most common REST interview answers:

- `POST /orders` returns HTTP 201 with `Location` and `ETag`; an `Idempotency-Key` header makes a retried POST replay the first response (status, `Location`, `ETag` and body) instead of creating a second order.
- `GET /orders/{id}` returns an `ETag`; a request with `If-None-Match` gets HTTP 304 with no body.
- `PUT /orders/{id}` replaces the order (sending it twice gives the same result); a stale `If-Match` gets HTTP 412.
- `PATCH /orders/{id}` changes only the fields in the body.
- `DELETE /orders/{id}` returns HTTP 204, and HTTP 404 when sent again.
- No token gives HTTP 401 with `WWW-Authenticate: Bearer`; a token without the `orders:write` scope gives HTTP 403.
- An invalid value gives HTTP 422 and broken JSON gives HTTP 400, both as Problem Details (`application/problem+json`, RFC 9457).
- `PUT /orders` gives HTTP 405 with `Allow: GET, POST`.
- `GET /orders?limit=1` returns a `Link` header with `rel="next"`.

Demo tokens: `reader-token` (scope `orders:read`) and `writer-token` (scopes `orders:read` and `orders:write`). Data is kept in memory and resets when the app restarts.

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.142.2 (with starlette 1.7.0 and pydantic 2.13.5)
- uvicorn 0.54.0
- httpx2 2.13.1 (the HTTP client package that the Starlette 1.7 test client uses in place of httpx)
- pytest 9.1.1
- curl (for `demo.sh`)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/rest-api-interview-questions-example
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

pytest -q                              # 11 tests, no server needed
uvicorn app:app --port 9230            # terminal 1
./demo.sh                              # terminal 2, prints every request and response
```

`demo.sh` sends the article's requests in the order the article shows them, against `http://localhost:9230`. Run it against a freshly started app, because order IDs and ETags depend on that order (IDs start at 1001). It removes the `Date`, `Server` and `Content-Length` headers from the output. `OUTPUTS.txt` holds a captured run.
