"""Bookstore account API used in the article "CSRF in REST APIs".

One user (alice) can change the email address of her account through four
versions of the same endpoint:

  POST /unsafe/email     cookie session, reads the body as JSON whatever the
                         Content-Type says (vulnerable to CSRF)
  POST /json-only/email  cookie session, accepts application/json only
  POST /protected/email  cookie session + Sec-Fetch-Site check + CSRF token
  POST /bearer/email     Authorization: Bearer token, no cookie at all

Demo only: no passwords, in-memory sessions, a fake secret.
Run: uvicorn api:app --port 8000
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Demo value. In production, load a long random secret from your secret store.
CSRF_SECRET = os.environ.get("CSRF_SECRET", "demo-secret-not-for-production").encode()
DEFAULT_EMAIL = "alice@example.com"

ACCOUNTS = {"alice": {"email": DEFAULT_EMAIL}}
SESSIONS: dict[str, str] = {}   # session id -> username
BEARER: dict[str, str] = {}     # access token -> username

log = logging.getLogger("api")
logging.basicConfig(level=logging.INFO, format="API  %(message)s")

app = FastAPI(title="Bookstore account API")


class Login(BaseModel):
    username: str


class EmailChange(BaseModel):
    email: str


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Print what the browser sent, so we can see which defences fire."""
    response = await call_next(request)
    log.info(
        "%s %s cookie=%s sec-fetch-site=%s origin=%s content-type=%s -> %s",
        request.method,
        request.url.path,
        "yes" if "session" in request.cookies else "no",
        request.headers.get("sec-fetch-site", "-"),
        request.headers.get("origin", "-"),
        request.headers.get("content-type", "-"),
        response.status_code,
    )
    return response


# ---------- login and helpers ----------

@app.post("/login")
def login(body: Login, response: Response, samesite: str = "lax"):
    """Log in (demo: no password) and set the session cookie.

    ?samesite=strict|lax|none|unset lets the demo compare cookie settings.
    """
    if body.username not in ACCOUNTS:
        raise HTTPException(401, "unknown user")
    sid = secrets.token_urlsafe(16)
    SESSIONS[sid] = body.username
    if samesite == "none":
        response.set_cookie("session", sid, httponly=True, secure=True, samesite="none")
    elif samesite == "unset":
        response.set_cookie("session", sid, httponly=True, samesite=None)
    else:
        response.set_cookie("session", sid, httponly=True, samesite=samesite)
    token = secrets.token_urlsafe(24)
    BEARER[token] = body.username
    return {"user": body.username, "access_token": token, "token_type": "Bearer"}


@app.post("/reset")
def reset():
    ACCOUNTS["alice"]["email"] = DEFAULT_EMAIL
    return ACCOUNTS["alice"]


def user_from_cookie(request: Request) -> str:
    sid = request.cookies.get("session")
    if sid not in SESSIONS:
        raise HTTPException(401, "not logged in")
    return SESSIONS[sid]


def user_from_bearer(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or token not in BEARER:
        raise HTTPException(401, "missing or invalid bearer token")
    return BEARER[token]


@app.get("/api/me")
def me(user: str = Depends(user_from_cookie)):
    return {"user": user, **ACCOUNTS[user]}


# ---------- CSRF token (signed, bound to the session) ----------

def make_csrf_token(session_id: str) -> str:
    nonce = secrets.token_hex(16)
    mac = hmac.new(CSRF_SECRET, f"{session_id}!{nonce}".encode(), hashlib.sha256).hexdigest()
    return f"{nonce}.{mac}"


def csrf_token_is_valid(token: str, session_id: str) -> bool:
    nonce, _, mac = token.partition(".")
    expected = hmac.new(CSRF_SECRET, f"{session_id}!{nonce}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, expected)


@app.get("/api/csrf-token")
def csrf_token(request: Request, user: str = Depends(user_from_cookie)):
    return {"csrf_token": make_csrf_token(request.cookies["session"])}


def check_csrf(request: Request, user: str = Depends(user_from_cookie)) -> str:
    # 1. Browsers since 2023 say where a request comes from.
    site = request.headers.get("sec-fetch-site")
    if site is not None and site not in ("same-origin", "none"):
        raise HTTPException(403, f"cross-origin request rejected (Sec-Fetch-Site: {site})")
    # 1b. Older browsers: compare Origin with the host the request was sent to.
    origin = request.headers.get("origin")
    if site is None and origin and urlsplit(origin).netloc != request.headers.get("host"):
        raise HTTPException(403, f"cross-origin request rejected (Origin: {origin})")
    # 2. The token proves the request came from our own page.
    token = request.headers.get("x-csrf-token", "")
    if not csrf_token_is_valid(token, request.cookies["session"]):
        raise HTTPException(403, "missing or invalid CSRF token")
    return user


# ---------- four versions of "change my email" ----------

@app.post("/unsafe/email")
async def change_email_unsafe(request: Request, user: str = Depends(user_from_cookie)):
    data = json.loads(await request.body())   # ignores Content-Type: the bug
    ACCOUNTS[user]["email"] = data["email"]
    return ACCOUNTS[user]


@app.post("/json-only/email")
def change_email_json_only(body: EmailChange, user: str = Depends(user_from_cookie)):
    # FastAPI parses a model body only when Content-Type is JSON (since 0.65.2);
    # text/plain or form bodies get HTTP 422 before this code runs.
    ACCOUNTS[user]["email"] = body.email
    return ACCOUNTS[user]


@app.post("/protected/email")
def change_email_protected(body: EmailChange, user: str = Depends(check_csrf)):
    ACCOUNTS[user]["email"] = body.email
    return ACCOUNTS[user]


@app.post("/bearer/email")
def change_email_bearer(body: EmailChange, user: str = Depends(user_from_bearer)):
    ACCOUNTS[user]["email"] = body.email
    return ACCOUNTS[user]


# ---------- our own front end (same origin as the API) ----------

@app.get("/", response_class=HTMLResponse)
def home():
    return (Path(__file__).parent / "app.html").read_text()
