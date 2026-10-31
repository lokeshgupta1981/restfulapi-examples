Source code for the article [Multi-Tenant API Design: Identify Tenants and Isolate Data](https://restfulapi.net/multi-tenant-rest-api-design/)

# Multi-tenant REST API example

A small invoices API for a SaaS app (FastAPI and SQLite) that two customer companies, the tenants `acme` and `globex`, share. It shows:

- The tenant comes from a signed claim (`tenant_id`) in the access token, not from the URL, a header or the body.
- All tenants share one `invoices` table with a `tenant_id` column. Every query goes through `TenantInvoices`, which always adds `WHERE tenant_id = ?`.
- Another tenant's invoice returns the same HTTP 404 as a missing one.
- A `tenant_id` field in the request body is rejected with HTTP 422; the server sets the tenant.
- Each tenant has its own rate limit from its plan (free: 5 requests per minute, pro: 20), with HTTP 429, `Retry-After` and the `RateLimit-Policy` / `RateLimit` headers from the IETF draft (draft-ietf-httpapi-ratelimit-headers-11).
- Two deliberately wrong routes under `/unsafe/`: one loads an invoice by ID alone (BOLA), one trusts an `X-Tenant-ID` header. They exist only for the demo.
- `rls/`: the same table in PostgreSQL with row-level security, so the database itself filters by tenant.

## Files

- `app.py`: the API.
- `tokens.py`: creates demo access tokens for `alice` (tenant acme) and `bob` (tenant globex), as an identity provider would.
- `demo.sh`: the curl requests shown in the article.
- `test_tenancy.py`: pytest tests for cross-tenant access, the body tenant field, a forged token and per-tenant rate limits.
- `rls/schema.sql`, `rls/demo.sql`, `rls/run.sh`: the PostgreSQL row-level security demo.
- `OUTPUTS.txt`: output of all scripts from a real run.

The signing key `demo-only-signing-key-not-a-secret` is a fake demo key. Set `JWT_SECRET` to change it, and use a key from a secret store in a real API.

## Versions

- Python 3.13 (3.10 or later works)
- fastapi 0.143.0, uvicorn 0.54.0, PyJWT 2.15.1, pytest 9.1.1, httpx2 2.13.1 (for the FastAPI TestClient), pinned in `requirements.txt`
- PostgreSQL 16.15 for `rls/` (row-level security works the same way in PostgreSQL 9.5 and later)
- curl and bash for the shell scripts (on Windows, use Git Bash or WSL)

## Run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/multi-tenant-rest-api-design-example
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

rm -f invoices.db
uvicorn app:app --port 8000        # terminal 1
./demo.sh                          # terminal 2
pytest -q
```

`demo.sh` expects an empty database and a fresh rate limit, so restart the server (and delete `invoices.db`) before running it again. To use another port, start uvicorn with `--port 9000` and run `BASE=http://localhost:9000 ./demo.sh`.

The row-level security demo needs a PostgreSQL server where you can connect as a superuser and create a role:

```bash
PGHOST=localhost PGPORT=5432 ./rls/run.sh
```

It drops and recreates a table named `invoices` and a role named `app_user`, so run it on a scratch database (set `PGDATABASE`). The script connects as `postgres` (or `PGADMIN`) to create the table, then as `app_user` to run the queries; adjust `pg_hba.conf` or set `PGPASSWORD` if your server asks for passwords.
