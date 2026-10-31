"""Invoices API for a small multi-tenant SaaS app (demo).

Every tenant (customer company) shares one database table. The tenant of a
request comes from the signed access token, never from the URL, a header or
the request body. Every query goes through TenantInvoices, which adds the
tenant filter, and every tenant has its own rate limit.

The /unsafe/... routes show the two classic mistakes. They exist only so the
demo can show what goes wrong. Do not copy them.
"""
import math
import os
import sqlite3
import time

import jwt
from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

# Demo signing key. Not a real secret: use a key from your secret store.
JWT_SECRET = os.environ.get("JWT_SECRET", "demo-only-signing-key-not-a-secret")
DB_PATH = os.environ.get("DB_PATH", "invoices.db")
WINDOW_SECONDS = 60
PLAN_LIMITS = {"free": 5, "pro": 20}  # requests per tenant per minute

app = FastAPI(title="Invoices API (multi-tenant demo)")


class ApiError(Exception):
    def __init__(self, status, title, detail, headers=None):
        self.status, self.title, self.detail = status, title, detail
        self.headers = headers or {}


@app.exception_handler(ApiError)
def api_error(request: Request, exc: ApiError):
    body = {"type": "about:blank", "title": exc.title,
            "status": exc.status, "detail": exc.detail}
    return JSONResponse(body, status_code=exc.status, headers=exc.headers,
                        media_type="application/problem+json")


# ---------------------------------------------------------------- database
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tenants (
            id    TEXT PRIMARY KEY,
            name  TEXT NOT NULL,
            plan  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id    TEXT NOT NULL REFERENCES tenants(id),
            customer     TEXT NOT NULL,
            amount_cents INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_invoices_tenant ON invoices(tenant_id, id);
    """)
    if conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0] == 0:
        conn.executemany("INSERT INTO tenants VALUES (?, ?, ?)", [
            ("acme", "Acme Corp", "free"),
            ("globex", "Globex Inc", "pro"),
        ])
        conn.executemany(
            "INSERT INTO invoices (id, tenant_id, customer, amount_cents) VALUES (?, ?, ?, ?)", [
                (1001, "acme", "Wayne Hardware", 12000),
                (1002, "globex", "Initech", 990000),
                (1003, "acme", "Stark Supplies", 4500),
            ])
    conn.commit()
    conn.close()


init_db()


# ---------------------------------------------------------------- tenant
class Tenant(BaseModel):
    id: str
    plan: str


def current_tenant(authorization: str | None = Header(default=None),
                   conn: sqlite3.Connection = Depends(db)) -> Tenant:
    """Authenticate the caller and read the tenant from the token claim."""
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "Unauthorized", "Missing bearer token",
                       {"WWW-Authenticate": 'Bearer realm="invoices"'})
    try:
        claims = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"],
                            audience="invoices-api",
                            options={"require": ["tenant_id", "sub", "exp"]})
    except jwt.PyJWTError as e:
        raise ApiError(401, "Unauthorized", f"Invalid token: {e}",
                       {"WWW-Authenticate": 'Bearer error="invalid_token"'})
    row = conn.execute("SELECT id, plan FROM tenants WHERE id = ?",
                       (claims["tenant_id"],)).fetchone()
    if row is None:
        raise ApiError(403, "Forbidden", "Unknown tenant")
    return Tenant(id=row["id"], plan=row["plan"])


# ---------------------------------------------------------------- rate limit
_recent: dict[str, list[float]] = {}  # tenant_id -> times of its requests in the window


def rate_limited_tenant(request: Request, tenant: Tenant = Depends(current_tenant)) -> Tenant:
    """Sliding-window limit per tenant: at most N requests in any 60 seconds."""
    limit = PLAN_LIMITS[tenant.plan]
    now = time.monotonic()
    times = [t for t in _recent.get(tenant.id, []) if t > now - WINDOW_SECONDS]
    policy = f'"tenant";q={limit};w={WINDOW_SECONDS}'
    if len(times) >= limit:
        wait = max(1, math.ceil(times[0] + WINDOW_SECONDS - now))
        _recent[tenant.id] = times
        raise ApiError(429, "Too Many Requests",
                       f"Tenant {tenant.id} used its {limit} requests per minute",
                       {"Retry-After": str(wait), "RateLimit-Policy": policy,
                        "RateLimit": f'"tenant";r=0;t={wait}'})
    times.append(now)
    _recent[tenant.id] = times
    reset = math.ceil(times[0] + WINDOW_SECONDS - now)
    request.state.ratelimit = {"RateLimit-Policy": policy,
                               "RateLimit": f'"tenant";r={limit - len(times)};t={reset}'}
    return tenant


@app.middleware("http")
async def add_ratelimit_headers(request: Request, call_next):
    response = await call_next(request)
    for name, value in getattr(request.state, "ratelimit", {}).items():
        response.headers[name] = value
    return response


# ---------------------------------------------------------------- data access
class TenantInvoices:
    """All invoice queries for ONE tenant. There is no method without the filter."""

    def __init__(self, conn: sqlite3.Connection, tenant_id: str):
        self.conn, self.tenant_id = conn, tenant_id

    def list(self):
        rows = self.conn.execute(
            "SELECT id, customer, amount_cents FROM invoices WHERE tenant_id = ? ORDER BY id",
            (self.tenant_id,))
        return [dict(r) for r in rows]

    def get(self, invoice_id: int):
        row = self.conn.execute(
            "SELECT id, customer, amount_cents FROM invoices WHERE tenant_id = ? AND id = ?",
            (self.tenant_id, invoice_id)).fetchone()
        return dict(row) if row else None

    def create(self, customer: str, amount_cents: int):
        cur = self.conn.execute(
            "INSERT INTO invoices (tenant_id, customer, amount_cents) VALUES (?, ?, ?)",
            (self.tenant_id, customer, amount_cents))
        self.conn.commit()
        return self.get(cur.lastrowid)


def invoices(tenant: Tenant = Depends(rate_limited_tenant),
             conn: sqlite3.Connection = Depends(db)) -> TenantInvoices:
    return TenantInvoices(conn, tenant.id)


# ---------------------------------------------------------------- routes
class NewInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a "tenant_id" field is rejected
    customer: str = Field(min_length=1)
    amount_cents: int = Field(gt=0)


@app.get("/invoices")
def list_invoices(repo: TenantInvoices = Depends(invoices)):
    return {"tenant": repo.tenant_id, "items": repo.list()}


@app.post("/invoices", status_code=201)
def create_invoice(body: NewInvoice, repo: TenantInvoices = Depends(invoices)):
    return repo.create(body.customer, body.amount_cents)


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, repo: TenantInvoices = Depends(invoices)):
    invoice = repo.get(invoice_id)
    if invoice is None:
        # Same answer for "does not exist" and "belongs to another tenant".
        raise ApiError(404, "Not Found", f"Invoice {invoice_id} not found")
    return invoice


# ---------------------------------------------------------------- the mistakes
@app.get("/unsafe/invoices/{invoice_id}")
def unsafe_get_invoice(invoice_id: int, tenant: Tenant = Depends(current_tenant),
                       conn: sqlite3.Connection = Depends(db)):
    """WRONG: authenticates the caller, then loads the invoice by ID alone (BOLA)."""
    row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if row is None:
        raise ApiError(404, "Not Found", f"Invoice {invoice_id} not found")
    return dict(row)


@app.get("/unsafe/invoices")
def unsafe_list_invoices(x_tenant_id: str = Header(),
                         tenant: Tenant = Depends(current_tenant),
                         conn: sqlite3.Connection = Depends(db)):
    """WRONG: trusts a tenant ID that the client can type into a header."""
    rows = conn.execute("SELECT id, customer, amount_cents FROM invoices WHERE tenant_id = ?",
                        (x_tenant_id,))
    return {"tenant": x_tenant_id, "items": [dict(r) for r in rows]}
