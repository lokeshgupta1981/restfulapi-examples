Source code for the article [HTTP 401 vs 403 vs 404: Which Status Code to Return](https://restfulapi.net/401-vs-403-vs-404/)

# HTTP 401 vs 403 vs 404 example

A small multi-tenant Projects API (FastAPI) that returns HTTP 401, HTTP 403 or HTTP 404 for each case, plus a client that reacts to each code.

- `app.py`: the API. A middleware authenticates every request except `/health` and `/token` (HTTP 401 with `WWW-Authenticate: Bearer ...`, or HTTP 400 for a malformed header). Project lookups are scoped to the caller's tenant and to private projects the caller owns, so a project the caller may not know about returns the same HTTP 404 as a missing one. HTTP 403 is used for a missing scope, a suspended account, a project the caller can see but not delete, and the documented admin route.
- `demo.sh`: 16 curl calls, one per case. Needs curl.
- `client.py`: an httpx2 client that refreshes its token once on HTTP 401 `invalid_token`, does not retry HTTP 403 and drops the item on HTTP 404.
- `test_status_codes.py`: pytest tests for the rules.
- `leaky_lookup.py`: the wrong pattern (load by ID, then compare the tenant), which returns HTTP 404 for a missing project and HTTP 403 for another tenant's project.
- `matrix.py`: prints the status code each demo caller gets for six requests (uses the TestClient, no server needed).

## Demo tokens

| Token | User | Tenant | Scopes | Note |
|---|---|---|---|---|
| tok-alice | alice | acme | projects:read projects:write | owns p-100 and private p-101 |
| tok-carol | carol | acme | projects:read | read-only |
| tok-bob | bob | globex | projects:read projects:write | admin of globex, owns p-200 |
| tok-dave | dave | acme | projects:read | suspended account |
| tok-alice-old | alice | acme | projects:read projects:write | expired |

Refresh token `rt-alice` returns `tok-alice` from `POST /token`. Tokens and data are for the demo only and live in memory.

## Versions

- Python 3.13 (3.10 or later)
- fastapi 0.142.2
- uvicorn 0.54.0
- httpx2 2.13.1 (HTTP client for client.py and the FastAPI TestClient)
- pytest 9.1.1

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/401-vs-403-vs-404-example
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --port 9130     # terminal 1
./demo.sh                       # terminal 2
python client.py                # terminal 2 (restart the API first, demo.sh deletes p-100)
pytest -q
python matrix.py
python leaky_lookup.py
```
