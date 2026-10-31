Source code for the article [BOLA (Broken Object Level Authorization) in REST APIs](https://restfulapi.net/bola-broken-object-level-authorization/)

# BOLA example: a Bookstore Orders API, broken and fixed

Two versions of the same small orders API (FastAPI and SQLite in memory). Both authenticate every request. Only one checks that the order or address in the request belongs to the caller.

- `store.py`: demo data (three customers, four orders, saved addresses, one public review) and the bearer-token lookup.
- `vulnerable_app.py`: loads orders by ID alone, trusts a `customer_id` query parameter and accepts any `address_id` in the body. This is BOLA.
- `secure_app.py`: one `load_order()` helper with a small policy (`can()`) used by every order route, a scoped list query, and an ownership check for `address_id`. Another customer's order gets the same HTTP 404 as a missing one. Support staff may read any order but not change it.
- `attack.py`: logs in as Alice and walks order IDs 1000-1010.
- `demo.sh`: seven curl calls, the same for both versions.
- `test_bola.py`: two-user authorization tests. They pass on `secure_app` and fail on `vulnerable_app`.
- `random_ids.py`: replaces the order IDs with random 62-bit numbers. Guessing stops working, but an ID leaked by a public review still opens Bob's order in the vulnerable version.

## Demo tokens (fake, for this demo only)

| Token | User | customer_id | Role |
|---|---|---|---|
| demo-token-alice | alice | 1 | customer (orders 1001, 1004, address 11) |
| demo-token-bob | bob | 2 | customer (order 1002, address 12) |
| demo-token-sam | sam | 90 | support |

## Versions

- Python 3.13 (3.10 or later)
- fastapi 0.143.0
- uvicorn 0.54.0
- httpx 0.28.1 (attack.py and the FastAPI TestClient)
- pytest 9.1.1

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/bola-broken-object-level-authorization-example
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn vulnerable_app:app --port 8000     # terminal 1
uvicorn secure_app:app --port 8001         # terminal 2

BASE=http://localhost:8000 python attack.py   # terminal 3
BASE=http://localhost:8001 python attack.py
BASE=http://localhost:8000 ./demo.sh          # restart the app afterwards, demo.sh cancels and changes orders
BASE=http://localhost:8001 ./demo.sh

pytest -q                          # secure_app: all pass
APP=vulnerable_app pytest -q       # vulnerable_app: 6 tests fail
python random_ids.py
```

The data lives in memory, so restarting an app resets it. `OUTPUTS.txt` holds the output of one run.
