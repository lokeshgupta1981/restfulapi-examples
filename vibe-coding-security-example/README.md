Source code for the article [Vibe Coding Security Checklist for AI-Generated API Code](https://restfulapi.net/vibe-coding-api-security-checklist/)

# Vibe Coding Security Checklist Example

Two versions of the same small orders API (FastAPI and SQLite), plus a curl demo, an attack script and a two-user pytest suite that show the difference between them.

- `vulnerable_app.py`: the kind of code we get when we ask an assistant only for features. Every feature works, but it has no ownership check (BOLA), mass assignment, a missing admin role check, SQL built with an f-string, no login limit, stack traces in error responses, CORS that trusts every origin with credentials, and a secret key in the source. Do not deploy it.
- `secure_app.py`: the same API with the checklist applied. It refuses to start without the `ORDERS_SECRET_KEY` environment variable.
- `common.py`: creates the demo users (alice, bob, admin) and orders (101 and 102 belong to alice, 201 to bob) in an in-memory SQLite database.
- `demo.sh`: sends the same nine requests to one version with curl and prints the status line, the relevant headers and the body.
- `security_check.py`: logs in as different users, runs one attack per checklist item and prints PASS or FAIL. The number in brackets is the item number in the article's checklist. It exits with code 1 when a check fails, so it can run as a CI step against a running server.
- `test_ownership.py`: pytest tests where one user tries another user's data (checklist item 13). They use the FastAPI TestClient, so no server is needed. `APP=vulnerable_app pytest` runs them against the vulnerable version, where they fail.
- `SECURITY_RULES.md`: rules to copy into the instruction file of a coding agent.
- `OUTPUTS.txt`: the captured output of every command below.

## Demo users

| User | Password | Role | Orders |
|---|---|---|---|
| alice | alice-pass | customer | 101, 102 |
| bob | bob-pass | customer | 201 |
| admin | admin-pass | admin | none |

The passwords and the key `demo-only-not-a-real-key` are demo values only.

## Versions

- Python 3.13 (3.10 or later)
- fastapi 0.143.0
- uvicorn 0.54.0
- pydantic 2.14.0 with email-validator
- httpx2 2.16.0 (used by the FastAPI TestClient)
- pytest 9.2.0

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/vibe-coding-security-example
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn vulnerable_app:app --port 8001                                          # terminal 1
ORDERS_SECRET_KEY=demo-only-not-a-real-key uvicorn secure_app:app --port 8002   # terminal 2 (PowerShell: $env:ORDERS_SECRET_KEY="demo-only-not-a-real-key")

./demo.sh http://127.0.0.1:8001
./demo.sh http://127.0.0.1:8002
python security_check.py http://127.0.0.1:8001
python security_check.py http://127.0.0.1:8002

pytest -q
APP=vulnerable_app pytest -q
```

Restart both servers before running `demo.sh` or `security_check.py` again, because the data lives in memory and the login limit keeps counting.
