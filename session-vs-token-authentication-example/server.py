"""Bookstore orders API with two login styles: server sessions and JWT access tokens.

Demo only. The users, passwords and the JWT secret below are fake demo values.

Environment variables:
  PORT           port for uvicorn (see run commands in README), default 8000
  INSTANCE       a name shown in every response, default "A"
  SESSION_STORE  "memory" (one dict per process) or "shared" (SQLite file), default memory
  DENYLIST       "1" to check a shared denylist of revoked JWT IDs on every request
  DATA_DIR       folder for users.db and shared.db, default ./data
"""
import os
import secrets
import sqlite3
import time
import uuid

import jwt
from fastapi import Cookie, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel

INSTANCE = os.getenv("INSTANCE", "A")
SESSION_STORE = os.getenv("SESSION_STORE", "memory")
DENYLIST = os.getenv("DENYLIST", "0") == "1"
DATA_DIR = os.getenv("DATA_DIR", "data")
JWT_SECRET = "demo-only-secret-do-not-use-in-production-0123456789"  # fake demo key
TOKEN_TTL = 15 * 60      # access token lifetime: 15 minutes
SESSION_TTL = 30 * 60    # session idle timeout: 30 minutes

os.makedirs(DATA_DIR, exist_ok=True)
app = FastAPI()


def db(name):
    con = sqlite3.connect(os.path.join(DATA_DIR, name), isolation_level=None)
    con.execute("PRAGMA busy_timeout=2000")
    return con


# The users table is the application database. Every instance shares it.
with db("users.db") as con:
    con.execute("CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, password TEXT, role TEXT)")
    con.execute("INSERT OR IGNORE INTO users VALUES ('alice', 'alice-demo-pass', 'admin')")


# ---------- session store: in-process dict or a shared SQLite file ----------
memory_sessions = {}


def shared():
    con = db("shared.db")
    con.execute("CREATE TABLE IF NOT EXISTS sessions (sid TEXT PRIMARY KEY, user TEXT, expires REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS denylist (jti TEXT PRIMARY KEY, expires REAL)")
    return con


def save_session(sid, user):
    expires = time.time() + SESSION_TTL
    if SESSION_STORE == "shared":
        with shared() as con:
            con.execute("INSERT INTO sessions VALUES (?, ?, ?)", (sid, user, expires))
    else:
        memory_sessions[sid] = (user, expires)


def load_session(sid):
    if SESSION_STORE == "shared":
        with shared() as con:
            row = con.execute("SELECT user, expires FROM sessions WHERE sid = ?", (sid,)).fetchone()
    else:
        row = memory_sessions.get(sid)
    if row is None or row[1] < time.time():
        return None
    return row[0]


def delete_session(sid):
    if SESSION_STORE == "shared":
        with shared() as con:
            con.execute("DELETE FROM sessions WHERE sid = ?", (sid,))
    else:
        memory_sessions.pop(sid, None)


# ---------- helpers ----------
class Login(BaseModel):
    username: str
    password: str


def check_password(body: Login):
    with db("users.db") as con:
        row = con.execute("SELECT password FROM users WHERE name = ?", (body.username,)).fetchone()
    if row is None or not secrets.compare_digest(row[0], body.password):
        raise HTTPException(401, "invalid username or password")


def current_role(user):
    with db("users.db") as con:
        return con.execute("SELECT role FROM users WHERE name = ?", (user,)).fetchone()[0]


def orders_for(user):
    return [{"id": 1001, "book": "REST in Practice", "status": "shipped"}]


# ---------- 1. session authentication ----------
@app.post("/session/login")
def session_login(body: Login, response: Response):
    check_password(body)
    sid = secrets.token_urlsafe(32)          # 256 random bits, means nothing by itself
    save_session(sid, body.username)
    response.set_cookie("sid", sid, max_age=SESSION_TTL, path="/",
                        httponly=True, secure=True, samesite="lax")
    return {"user": body.username, "instance": INSTANCE}


def session_user(sid):
    user = load_session(sid) if sid else None
    if user is None:
        raise HTTPException(401, "no valid session", headers={"WWW-Authenticate": "Cookie"})
    return user


@app.get("/session/orders")
def session_orders(sid: str | None = Cookie(default=None)):
    user = session_user(sid)
    return {"user": user, "role": current_role(user), "orders": orders_for(user), "instance": INSTANCE}


@app.get("/session/admin/report")
def session_admin(sid: str | None = Cookie(default=None)):
    user = session_user(sid)
    role = current_role(user)                # read fresh on every request
    if role != "admin":
        raise HTTPException(403, f"role is {role}, admin required")
    return {"report": "daily sales", "user": user, "instance": INSTANCE}


@app.post("/session/logout", status_code=204)
def session_logout(response: Response, sid: str | None = Cookie(default=None)):
    if sid:
        delete_session(sid)                  # the server forgets the session
    response.delete_cookie("sid", path="/", httponly=True, secure=True, samesite="lax")


# ---------- 2. token authentication (JWT) ----------
@app.post("/token/login")
def token_login(body: Login):
    check_password(body)
    now = int(time.time())
    claims = {"sub": body.username, "role": current_role(body.username),
              "iat": now, "exp": now + TOKEN_TTL, "jti": str(uuid.uuid4())}
    token = jwt.encode(claims, JWT_SECRET, algorithm="HS256")
    return {"access_token": token, "token_type": "Bearer", "expires_in": TOKEN_TTL}


def token_claims(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = jwt.decode(authorization[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "token expired", headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    except jwt.InvalidTokenError:
        raise HTTPException(401, "invalid token", headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    if DENYLIST:
        with shared() as con:
            if con.execute("SELECT 1 FROM denylist WHERE jti = ?", (claims["jti"],)).fetchone():
                raise HTTPException(401, "token revoked", headers={"WWW-Authenticate": 'Bearer error="invalid_token"'})
    return claims


@app.get("/token/orders")
def token_orders(authorization: str | None = Header(default=None)):
    claims = token_claims(authorization)
    return {"user": claims["sub"], "role": claims["role"], "orders": orders_for(claims["sub"]), "instance": INSTANCE}


@app.get("/token/admin/report")
def token_admin(authorization: str | None = Header(default=None)):
    claims = token_claims(authorization)
    if claims["role"] != "admin":            # trusts the role written into the token
        raise HTTPException(403, f"role is {claims['role']}, admin required")
    return {"report": "daily sales", "user": claims["sub"], "instance": INSTANCE}


@app.post("/token/logout", status_code=204)
def token_logout(authorization: str | None = Header(default=None)):
    claims = token_claims(authorization)
    if DENYLIST:
        with shared() as con:
            con.execute("INSERT OR IGNORE INTO denylist VALUES (?, ?)", (claims["jti"], claims["exp"]))
    # Without a denylist there is nothing to delete: the token stays valid until exp.


# ---------- demo-only admin action ----------
@app.post("/demo/users/{name}/role/{role}", status_code=204)
def set_role(name: str, role: str):
    with db("users.db") as con:
        con.execute("UPDATE users SET role = ? WHERE name = ?", (role, name))
