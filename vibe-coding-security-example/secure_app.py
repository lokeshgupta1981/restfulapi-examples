"""The same orders API with the checklist applied.

Run: ORDERS_SECRET_KEY=change-me uvicorn secure_app:app --port 8002
"""
import logging
import os
import secrets
import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from common import make_db

SECRET_KEY = os.environ["ORDERS_SECRET_KEY"]  # checklist item 8: secret from the environment
log = logging.getLogger("orders")
db = make_db()
tokens = {}
app = FastAPI()

# checklist item 9: only the known front end may call the API with credentials
app.add_middleware(CORSMiddleware, allow_origins=["https://shop.example.com"], allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH"], allow_headers=["Authorization", "Content-Type"])


@app.exception_handler(Exception)
async def hide_errors(request: Request, exc: Exception):
    # checklist item 10: log the details, return a generic Problem Details body
    log.exception("unhandled error")
    return JSONResponse(status_code=500, media_type="application/problem+json",
                        content={"type": "about:blank", "title": "Internal Server Error", "status": 500})


def current_user(authorization: str | None = Header(None)):
    token = (authorization or "").removeprefix("Bearer ")
    if token not in tokens:
        raise HTTPException(401, "missing or invalid token")
    return tokens[token]


def require_admin(user_id: int = Depends(current_user)):
    role = db.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()[0]
    if role != "admin":
        raise HTTPException(403, "admin role required")  # checklist item 3: check the role on admin routes
    return user_id


failed_logins = defaultdict(deque)


def recent_failures(key):
    window, now = failed_logins[key], time.monotonic()
    while window and now - window[0] > 60:
        window.popleft()
    return window


class Login(BaseModel):
    name: str = Field(max_length=50)
    password: str = Field(max_length=200)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # checklist item 4: unknown fields such as role are rejected
    name: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None


@app.post("/login")
def login(body: Login, request: Request):
    # checklist item 7: after 5 failed attempts for one name from one client, answer 429 for a minute
    failures = recent_failures(f"{request.client.host}:{body.name}")
    if len(failures) >= 5:
        raise HTTPException(429, "too many failed logins", headers={"Retry-After": "60"})
    row = db.execute("SELECT id FROM users WHERE name = ? AND password = ?", (body.name, body.password)).fetchone()
    if not row:
        failures.append(time.monotonic())
        raise HTTPException(401, "wrong name or password")
    token = secrets.token_hex(16)
    tokens[token] = row[0]
    return {"token": token}


@app.get("/orders/{order_id}")
def get_order(order_id: int, user_id: int = Depends(current_user)):
    # checklist item 2: filter by owner, and answer 404 for other users' orders
    row = db.execute("SELECT id, user_id, item, total FROM orders WHERE id = ? AND user_id = ?",
                     (order_id, user_id)).fetchone()
    if not row:
        raise HTTPException(404, "order not found")
    return dict(zip(["id", "user_id", "item", "total"], row))


@app.get("/orders")
def search_orders(item: str = Query(max_length=100), user_id: int = Depends(current_user)):
    # checklist item 6: parameters instead of string formatting
    rows = db.execute("SELECT id, item, total FROM orders WHERE user_id = ? AND item = ?", (user_id, item)).fetchall()
    return [dict(zip(["id", "item", "total"], r)) for r in rows]


@app.patch("/users/me")
def update_me(body: ProfileUpdate, user_id: int = Depends(current_user)):
    if body.name is not None:
        db.execute("UPDATE users SET name = ? WHERE id = ?", (body.name, user_id))
    if body.email is not None:
        db.execute("UPDATE users SET email = ? WHERE id = ?", (body.email, user_id))
    row = db.execute("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(zip(["id", "name", "email", "role"], row))


@app.get("/admin/users")
def list_users(admin_id: int = Depends(require_admin)):
    rows = db.execute("SELECT id, name, email, role FROM users").fetchall()
    return [dict(zip(["id", "name", "email", "role"], r)) for r in rows]
