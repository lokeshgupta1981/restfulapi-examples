"""Helpdesk REST API that implements openapi.yaml.

Run: uvicorn helpdesk_api:app --port 8080
"""
import base64
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

API_TOKEN = os.environ.get("HELPDESK_API_TOKEN", "dev-token-123")
SPEC = yaml.safe_load((Path(__file__).parent / "openapi.yaml").read_text())

app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

CUSTOMERS = {
    "C-201": {"id": "C-201", "name": "Northwind Traders", "email": "it@northwind.example", "plan": "enterprise"},
    "C-202": {"id": "C-202", "name": "Blue Fern Studio", "email": "hello@bluefern.example", "plan": "pro"},
    "C-203": {"id": "C-203", "name": "Kumar Bakery", "email": "owner@kumarbakery.example", "plan": "free"},
    "C-204": {"id": "C-204", "name": "Atlas Logistics", "email": "ops@atlas.example", "plan": "enterprise"},
}
AGENTS = [
    {"id": "A-1", "name": "Priya", "team": "billing"},
    {"id": "A-2", "name": "Marco", "team": "technical"},
    {"id": "A-3", "name": "Lena", "team": "technical"},
]
SUBJECTS = [
    "Invoice shows the wrong VAT number", "Cannot reset password", "Export to CSV times out",
    "Charged twice this month", "Webhook calls stopped", "Add a second admin user",
    "API returns HTTP 500 on large uploads", "Change billing email", "SSO login loops back to start",
    "Request a refund for unused seats", "Dashboard is slow in the morning", "Delete old test project",
]
STATUSES = ["open", "pending", "open", "closed", "open", "pending"]
PRIORITIES = ["normal", "high", "low", "urgent", "normal", "normal", "high"]
START = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


TICKETS: dict[str, dict] = {}
COMMENTS: dict[str, list[dict]] = {}
AUDIT: list[dict] = []
for i in range(24):
    tid = f"T-{1001 + i}"
    created = START + timedelta(days=i, hours=i % 5)
    TICKETS[tid] = {
        "id": tid,
        "subject": SUBJECTS[i % len(SUBJECTS)],
        "description": f"Customer report for {SUBJECTS[i % len(SUBJECTS)].lower()}.",
        "status": STATUSES[i % len(STATUSES)],
        "priority": PRIORITIES[i % len(PRIORITIES)],
        "assignee": AGENTS[i % 3]["id"] if i % 4 else None,
        "customer_id": list(CUSTOMERS)[i % len(CUSTOMERS)],
        "tags": ["billing"] if "charg" in SUBJECTS[i % len(SUBJECTS)].lower() else [],
        "created_at": iso(created),
        "updated_at": iso(created + timedelta(hours=3)),
    }
    COMMENTS[tid] = [{
        "id": f"{tid}-c1", "ticket_id": tid, "kind": "customer_message",
        "body": TICKETS[tid]["description"], "author": TICKETS[tid]["customer_id"],
        "created_at": iso(created),
    }]


def problem(status: int, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        {"type": "about:blank", "title": title, "status": status, "detail": detail},
        status_code=status, media_type="application/problem+json",
    )


@app.middleware("http")
async def check_token(request: Request, call_next):
    if request.url.path == "/openapi.json":
        return await call_next(request)
    if request.headers.get("authorization") != f"Bearer {API_TOKEN}":
        return problem(401, "Unauthorized", "Send Authorization: Bearer <token>.")
    if request.method in ("POST", "PATCH", "DELETE"):
        AUDIT.append({"at": iso(datetime.now(timezone.utc)), "method": request.method,
                      "path": request.url.path, "caller": "token"})
    return await call_next(request)


@app.get("/openapi.json")
def openapi_document():
    return SPEC


@app.get("/tickets")
def list_tickets(status: str | None = None, priority: str | None = None, assignee: str | None = None,
                 customer_id: str | None = None, cursor: str | None = None, limit: int = 10):
    rows = sorted(TICKETS.values(), key=lambda t: t["created_at"], reverse=True)
    for field, value in (("status", status), ("priority", priority),
                         ("assignee", assignee), ("customer_id", customer_id)):
        if value:
            rows = [t for t in rows if t[field] == value]
    start = int(base64.urlsafe_b64decode(cursor).decode()) if cursor else 0
    limit = max(1, min(limit, 50))
    page = rows[start:start + limit]
    more = start + limit < len(rows)
    next_cursor = base64.urlsafe_b64encode(str(start + limit).encode()).decode() if more else None
    return {"items": page, "next_cursor": next_cursor}


@app.post("/tickets", status_code=201)
async def create_ticket(request: Request):
    body = await request.json()
    tid = f"T-{1001 + len(TICKETS)}"
    now = iso(datetime.now(timezone.utc))
    TICKETS[tid] = {"id": tid, "subject": body["subject"], "description": body.get("description", ""),
                    "status": "open", "priority": body.get("priority", "normal"), "assignee": None,
                    "customer_id": body["customer_id"], "tags": body.get("tags", []),
                    "created_at": now, "updated_at": now}
    COMMENTS[tid] = []
    return TICKETS[tid]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    if ticket_id not in TICKETS:
        return problem(404, "Not Found", f"Ticket {ticket_id} does not exist.")
    return TICKETS[ticket_id]


@app.patch("/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, request: Request):
    if ticket_id not in TICKETS:
        return problem(404, "Not Found", f"Ticket {ticket_id} does not exist.")
    body = await request.json()
    for field in ("status", "priority", "assignee"):
        if field in body:
            TICKETS[ticket_id][field] = body[field]
    TICKETS[ticket_id]["updated_at"] = iso(datetime.now(timezone.utc))
    return TICKETS[ticket_id]


@app.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(ticket_id: str):
    if ticket_id not in TICKETS:
        return problem(404, "Not Found", f"Ticket {ticket_id} does not exist.")
    del TICKETS[ticket_id]
    COMMENTS.pop(ticket_id, None)
    return Response(status_code=204)


@app.get("/tickets/{ticket_id}/comments")
def list_comments(ticket_id: str):
    if ticket_id not in TICKETS:
        return problem(404, "Not Found", f"Ticket {ticket_id} does not exist.")
    return COMMENTS[ticket_id]


@app.post("/tickets/{ticket_id}/comments", status_code=201)
async def add_comment(ticket_id: str, request: Request):
    if ticket_id not in TICKETS:
        return problem(404, "Not Found", f"Ticket {ticket_id} does not exist.")
    body = await request.json() if await request.body() else {}
    if body.get("kind") not in ("public_reply", "internal_note") or not body.get("body"):
        return problem(422, "Unprocessable Content",
                       "Send kind (public_reply or internal_note) and a non-empty body.")
    comment = {"id": f"{ticket_id}-c{len(COMMENTS[ticket_id]) + 1}", "ticket_id": ticket_id,
               "kind": body["kind"], "body": body["body"], "author": "A-2",
               "created_at": iso(datetime.now(timezone.utc))}
    COMMENTS[ticket_id].append(comment)
    return comment


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    if customer_id not in CUSTOMERS:
        return problem(404, "Not Found", f"Customer {customer_id} does not exist.")
    return CUSTOMERS[customer_id]


@app.get("/agents")
def list_agents():
    return AGENTS


@app.post("/admin/tickets/purge")
def purge_closed_tickets(older_than_days: int = 30):
    limit = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    doomed = [tid for tid, t in TICKETS.items()
              if t["status"] == "closed" and t["created_at"] < iso(limit)]
    for tid in doomed:
        del TICKETS[tid]
        COMMENTS.pop(tid, None)
    return {"deleted": len(doomed)}


@app.get("/admin/audit-log")
def get_audit_log():
    return AUDIT
