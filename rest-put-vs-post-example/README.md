Source code for the article [HTTP PUT vs. POST](https://restfulapi.net/rest-put-vs-post/)

# PUT vs POST example

A small orders API in Python (FastAPI) that keeps orders in memory and shows the difference between PUT and POST (RFC 9110, sections 9.3.3 and 9.3.4):

- `POST /orders` creates an order with a server-chosen id (`ord_1001`, `ord_1002`, ...) and returns HTTP 201 with `Location`. Sending the same POST twice creates two orders.
- `PUT /orders/{id}` creates (HTTP 201) or replaces (HTTP 200) the order at a client-chosen id. The body must be the full order (`customer` and `items` are required, HTTP 422 otherwise). Fields left out of the body are gone after the PUT. The body is stored byte for byte, so the PUT response may carry an `ETag`.
- `If-None-Match: *` makes a PUT create-only (HTTP 412 when the order exists). `If-Match` with the current `ETag` (or `*`) protects updates against lost updates (HTTP 412 when the `ETag` is stale). `If-Match` uses the strong comparison, `If-None-Match` the weak one.
- `POST /orders/{id}/cancel` is an action that runs server logic instead of replacing the order.
- Errors use Problem Details (`application/problem+json`, RFC 9457).

## Files

- `app.py`: the API.
- `demo.sh`: every request from the article, printed with status line, `Location`, `ETag` and body.
- `OUTPUTS.txt`: output of `demo.sh` from a real run.

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.14.0 (pinned in `requirements.txt`)
- curl and bash for `demo.sh` (on Windows, use Git Bash or WSL)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/rest-put-vs-post-example
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app:app --port 8000        # terminal 1
./demo.sh                          # terminal 2
```

Data lives in memory, so restart the server before running `demo.sh` again. To use another port, start uvicorn with `--port 9000` and run `BASE=http://localhost:9000 ./demo.sh`.
