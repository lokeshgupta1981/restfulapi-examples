Source code for the article [REST API Response Format Best Practices](https://restfulapi.net/rest-api-response-format/)

# REST API response format example

A small Bookstore API in Python (FastAPI) that uses one response format for every endpoint:

- `GET /books/{id}` returns the book itself as a JSON object, with no wrapper.
- `GET /books?limit=&cursor=&author=` returns an object with an `items` array and a `next` link (`null` on the last page). A filter that matches nothing returns HTTP 200 with an empty `items` array.
- `POST /books` returns HTTP 201, a `Location` header and the created book. `DELETE /books/{id}` returns HTTP 204 with no body.
- Every error, including unknown URLs, wrong methods, malformed JSON, validation errors and unexpected crashes (HTTP 500 without a stack trace), is a Problem Details object (RFC 9457) with `Content-Type: application/problem+json`. Validation errors list each field in an `errors` array with a JSON Pointer.
- Field names are camelCase, IDs are strings, timestamps are RFC 3339 in UTC, dates are `YYYY-MM-DD`, money is a decimal string with a currency code, and an optional field with no value is sent as `null`.

For comparison, `GET /envelope/books/{id}` returns the `{"success", "data", "error"}` envelope with HTTP 200 even when the book does not exist, and `default_app.py` serves the same books with FastAPI's default error bodies.

Data lives in memory and resets when the server restarts.

## Files

- `app.py`: the API with the consistent format (port 9120).
- `default_app.py`: the same API with FastAPI's default error handling (port 9121).
- `demo.sh`: every curl exchange from the article (the `date` and `server` headers are left out).
- `client.py`: a `requests` client. It shows that `raise_for_status()` does not notice a failure inside a 200 envelope, reads every error through one Problem Details helper, and follows the `next` links.
- `big_ids.js`: shows why IDs and money go over the wire as strings (Node.js).
- `test_format.py`: pytest contract tests that check every endpoint against the format.
- `OUTPUTS.txt`: output of all of the above from a real run.

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.13.5, requests 2.34.2, httpx 0.28.1, pytest 9.1.1 (pinned in `requirements.txt`)
- Node.js 22 (for `big_ids.js`), curl (for `demo.sh`)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/rest-api-response-format-example
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app:app --port 9120                # terminal 1
uvicorn default_app:app --port 9121        # terminal 2
./demo.sh                                  # terminal 3
python3 client.py
node big_ids.js
pytest -v                                  # needs no running server
```

`demo.sh` creates and deletes book 1006, so restart `app.py` before running it again if you want the same IDs. To use other ports, set `BASE` and `DEFAULT`, for example `BASE=http://localhost:8000 ./demo.sh`.
