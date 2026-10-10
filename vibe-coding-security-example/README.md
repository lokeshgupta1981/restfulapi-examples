# Vibe Coding Security Checklist Example

Source code for the article [API Security Checklist for AI-Generated Code](https://restfulapi.net/vibe-coding-api-security-checklist/).

The example has two versions of the same small orders API and a script that tests both.

- `vulnerable_app.py` contains seven mistakes that generated API code often has: no ownership check (BOLA), mass assignment, a missing admin role check, SQL built with an f-string, no login limit, stack traces in errors, and CORS that trusts every origin with credentials. It also keeps its secret key in the source. Do not deploy it.
- `secure_app.py` is the same API with the checklist applied.
- `security_check.py` logs in as different users and runs one attack per checklist item, then prints PASS or FAIL. The number in brackets is the item number in the article's checklist. The script exits with code 1 when a check fails, so it can run as a CI step.
- `SECURITY_RULES.md` holds rules to copy into the instruction file of a coding agent.
- `common.py` creates the sample users (alice, bob, admin) and orders in SQLite.

## Versions

- Python 3.10 or later
- FastAPI 0.143.0, Uvicorn 0.54.0, Pydantic 2.14.0 with email-validator

## Run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn vulnerable_app:app --port 8001                          # terminal 1
ORDERS_SECRET_KEY=change-me uvicorn secure_app:app --port 8002  # terminal 2 (PowerShell: $env:ORDERS_SECRET_KEY="change-me")

python security_check.py http://127.0.0.1:8001
python security_check.py http://127.0.0.1:8002
```

Restart the servers before running the checks again, because the data lives in memory and the login limit keeps counting.

## Expected output

```text
FAIL  [2] Object-level authorization (BOLA)   alice reads bob's order 201 -> HTTP 200
...
0/7 checks passed

PASS  [2] Object-level authorization (BOLA)   alice reads bob's order 201 -> HTTP 404
...
7/7 checks passed
```
