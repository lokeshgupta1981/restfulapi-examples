"""An orders API with the mistakes that generated code often contains. Do not deploy.

Run: uvicorn vulnerable_app:app --port 8001
"""
import secrets
import traceback

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from common import make_db

SECRET_KEY = "supersecretkey"  # checklist item 8: secret in the source code
db = make_db()
tokens = {}
app = FastAPI()

# checklist item 9: any website may call the API with the user's cookies
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(Exception)
async def show_errors(request: Request, exc: Exception):
    # checklist item 10: the stack trace goes to the client
    return JSONResponse(status_code=500, content={"error": str(exc), "trace": traceback.format_exc()})


def current_user(authorization: str | None):
    if not authorization or authorization.removeprefix("Bearer ") not in tokens:
        raise HTTPException(401, "missing or invalid token")
    return tokens[authorization.removeprefix("Bearer ")]


@app.post("/login")
def login(body: dict):
    # checklist item 7: no limit on login attempts
    row = db.execute("SELECT id FROM users WHERE name = ? AND password = ?",
                     (body.get("name"), body.get("password"))).fetchone()
    if not row:
        raise HTTPException(401, "wrong name or password")
    token = secrets.token_hex(16)
    tokens[token] = row[0]
    return {"token": token}


@app.get("/orders/{order_id}")
def get_order(order_id: int, authorization: str | None = Header(None)):
    current_user(authorization)
    # checklist item 2: no check that the order belongs to the caller (BOLA)
    row = db.execute("SELECT id, user_id, item, total FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row:
        raise HTTPException(404, "order not found")
    return dict(zip(["id", "user_id", "item", "total"], row))


@app.get("/orders")
def search_orders(item: str, authorization: str | None = Header(None)):
    user_id = current_user(authorization)
    # checklist item 6: SQL built with an f-string
    rows = db.execute(f"SELECT id, item, total FROM orders WHERE user_id = {user_id} AND item = '{item}'").fetchall()
    return [dict(zip(["id", "item", "total"], r)) for r in rows]


@app.patch("/users/me")
def update_me(body: dict, authorization: str | None = Header(None)):
    user_id = current_user(authorization)
    # checklist item 4: every field from the request is written, including role (mass assignment)
    for field, value in body.items():
        db.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
    row = db.execute("SELECT id, name, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(zip(["id", "name", "email", "role"], row))


@app.get("/admin/users")
def list_users(authorization: str | None = Header(None)):
    current_user(authorization)
    # checklist item 3: any logged-in user reaches an admin route (BFLA)
    rows = db.execute("SELECT id, name, email, role FROM users").fetchall()
    return [dict(zip(["id", "name", "email", "role"], r)) for r in rows]
