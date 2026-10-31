Source code for the article [Cursor Pagination vs Offset vs Keyset: Which to Use](https://restfulapi.net/cursor-vs-offset-pagination/)

# Cursor vs keyset vs offset pagination example

A small orders API in Python (FastAPI) with SQLite that lists the same 10 orders, newest first, in three ways:

- `GET /orders/offset?limit=3&offset=3`: offset pagination with `LIMIT ... OFFSET ...` and a total count.
- `GET /orders/keyset?limit=3&before_created_at=...&before_id=...`: keyset pagination. The client sends the sort values of the last row it saw, and the server uses `WHERE (created_at, id) < (?, ?)`.
- `GET /orders?limit=3&cursor=...`: cursor pagination. The same keyset query, but the last row's values travel as an opaque base64url cursor. The response has `next_cursor`, `has_more` and a `Link: <...>; rel="next"` header. A cursor that does not decode gets HTTP 400.

`POST /orders` and `DELETE /orders/{id}` change the data between two page requests. `POST /_reset` (demo only) puts the 10 sample orders back. The database file `orders.db` is recreated every time the server starts.

## Files

- `app.py`: the API.
- `demo.sh`: shows offset pages repeating a row after an insert and skipping a row after a delete, then the same changes with a cursor, keyset URLs and a broken cursor.
- `client.py`: reads all orders by following `next_cursor` until `has_more` is false (httpx).
- `tie_breaker.py`: keyset on `created_at` alone loses a row that shares its timestamp; adding `id` to the sort fixes it.
- `bench.py`: builds a 1,000,000-row SQLite database (`bench.db`, about 76 MB) and times one 20-row page at different depths with OFFSET and with keyset.
- `explain.sql`: the same comparison in PostgreSQL with `EXPLAIN (ANALYZE, BUFFERS)`. It drops and recreates a table named `orders`, so run it in an empty test database.
- `run_all.sh`: starts the server and runs everything above except `explain.sql`.
- `OUTPUTS.txt`: output of all scripts from a real run.

## Versions

- Python 3.13 (3.10 or later works); SQLite 3.15 or later (row values), included with Python
- fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.13.5, httpx 0.28.1 (pinned in `requirements.txt`)
- PostgreSQL 16 for `explain.sql` (any version with row comparisons works)
- curl, jq and bash for the shell scripts (on Windows, use Git Bash or WSL)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/cursor-vs-offset-pagination-example
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app:app --port 8000        # terminal 1
./demo.sh                          # terminal 2
python client.py
python tie_breaker.py
python bench.py
```

Or run everything at once with `./run_all.sh` (it starts and stops its own server on port 8000).

For PostgreSQL:

```bash
createdb pagination_test
psql -d pagination_test -f explain.sql
```

To use another port, start uvicorn with `--port 9000` and run the scripts with `BASE=http://localhost:9000`.
