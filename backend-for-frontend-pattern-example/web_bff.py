"""Backend for Frontend of the browser app (single-page app).

Besides shaping data for the web order page, it is the OAuth client for the
browser, as described in RFC 10017, Section 6.1:
- it runs the authorization code flow with PKCE and a client secret,
- it keeps the access and refresh tokens on the server, in a session,
- the browser only gets an HttpOnly session cookie,
- every API call must carry the custom header 'X-CSRF: 1' (CSRF defense),
- it attaches the access token when it calls the services.

    uvicorn web_bff:app --port 8005
"""
import asyncio
import base64
import hashlib
import os
import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

import settings

app = FastAPI(title="web-bff")
client = httpx.AsyncClient(timeout=httpx.Timeout(1.0))

SESSION_COOKIE = "__Host-Http-session"
LOGIN_COOKIE = "__Host-Http-login"
REFRESH_MARGIN = int(os.getenv("REFRESH_MARGIN", "30"))  # refresh this many s before expiry
SESSIONS: dict[str, dict] = {}   # session id -> tokens; use Redis or a DB in production
PENDING_LOGINS: dict[str, str] = {}  # state -> PKCE code_verifier
REDIRECT_URI = f"{settings.WEB_BFF_URL}/bff/callback"


def set_host_cookie(response, name: str, value: str, max_age: int, samesite: str = "strict"):
    response.set_cookie(name, value, max_age=max_age, path="/", secure=True,
                        httponly=True, samesite=samesite)  # no Domain attribute


# ------------------------------------------------------------ CSRF defense
@app.middleware("http")
async def require_csrf_header(request: Request, call_next):
    protected = request.url.path.startswith("/api/") or request.url.path in ("/bff/user", "/bff/logout")
    if protected and request.headers.get("X-CSRF") != "1":
        return JSONResponse({"detail": "missing X-CSRF header"}, status_code=403)
    return await call_next(request)


# ------------------------------------------------------------ login flow
@app.get("/bff/login")
def login():
    state = secrets.token_urlsafe(16)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    PENDING_LOGINS[state] = verifier
    query = urlencode({"response_type": "code", "client_id": settings.WEB_BFF_CLIENT_ID,
                       "redirect_uri": REDIRECT_URI, "state": state,
                       "code_challenge": challenge, "code_challenge_method": "S256"})
    response = RedirectResponse(f"{settings.AUTH_URL}/authorize?{query}", status_code=302)
    # Binds the flow to this browser. Lax, not Strict: the browser must send it on the
    # cross-site redirect back from the authorization server to /bff/callback.
    set_host_cookie(response, LOGIN_COOKIE, state, max_age=300, samesite="lax")
    return response


@app.get("/bff/callback")
async def callback(code: str, state: str, request: Request):
    verifier = PENDING_LOGINS.pop(state, None)
    if not verifier or request.cookies.get(LOGIN_COOKIE) != state:
        raise HTTPException(400, "unknown or mismatched state")
    r = await client.post(f"{settings.AUTH_URL}/token", data={
        "grant_type": "authorization_code", "code": code, "code_verifier": verifier,
        "redirect_uri": REDIRECT_URI, "client_id": settings.WEB_BFF_CLIENT_ID,
        "client_secret": settings.WEB_BFF_CLIENT_SECRET})
    r.raise_for_status()
    tokens = r.json()
    session_id = secrets.token_urlsafe(32)
    SESSIONS[session_id] = {"user": "alice", "access_token": tokens["access_token"],
                            "refresh_token": tokens["refresh_token"],
                            "expires_at": time.time() + tokens["expires_in"]}
    response = RedirectResponse("/", status_code=302)
    set_host_cookie(response, SESSION_COOKIE, session_id, max_age=8 * 3600)
    response.delete_cookie(LOGIN_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
    return response


async def access_token_for(request: Request) -> str:
    """Find the session from the cookie and return a fresh access token."""
    session = SESSIONS.get(request.cookies.get(SESSION_COOKIE, ""))
    if not session:
        raise HTTPException(401, "not signed in")
    if session["expires_at"] - time.time() < REFRESH_MARGIN:
        r = await client.post(f"{settings.AUTH_URL}/token", data={
            "grant_type": "refresh_token", "refresh_token": session["refresh_token"],
            "client_id": settings.WEB_BFF_CLIENT_ID,
            "client_secret": settings.WEB_BFF_CLIENT_SECRET})
        if r.status_code != 200:
            raise HTTPException(401, "session expired, sign in again")
        tokens = r.json()
        session.update(access_token=tokens["access_token"], refresh_token=tokens["refresh_token"],
                       expires_at=time.time() + tokens["expires_in"])
        print("web-bff: access token refreshed for", session["user"], flush=True)
    return session["access_token"]


@app.get("/bff/user")
async def user(request: Request):
    session = SESSIONS.get(request.cookies.get(SESSION_COOKIE, ""))
    if not session:
        raise HTTPException(401, "not signed in")
    return {"user": session["user"]}  # no tokens, ever


@app.post("/bff/logout")
async def logout(request: Request):
    SESSIONS.pop(request.cookies.get(SESSION_COOKIE, ""), None)
    response = JSONResponse({"signedOut": True})
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    return response


# ------------------------------------------------------------ data for the web order page
async def fetch(url: str, token: str | None = None) -> dict:
    r = await client.get(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    r.raise_for_status()
    return r.json()


@app.get("/api/order-page/{order_id}")
async def order_page(order_id: str, request: Request):
    token = await access_token_for(request)
    try:
        order = await fetch(f"{settings.ORDERS_URL}/orders/{order_id}", token)
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, e.response.json()["detail"])
    calls = [fetch(f"{settings.CATALOG_URL}/books/{l['bookId']}") for l in order["lines"]]
    calls.append(fetch(f"{settings.SHIPPING_URL}/shipments/{order['shipmentId']}", token))
    *books, shipment = await asyncio.gather(*calls, return_exceptions=True)
    if any(isinstance(b, Exception) for b in books):
        raise HTTPException(502, "catalog service unavailable")

    # The desktop page has room for more: authors, rating, prices, the full tracking history.
    return {
        "orderId": order["id"], "status": order["status"], "placedAt": order["createdAt"],
        "lines": [{"title": b["title"], "authors": [a["name"] for a in b["authors"]],
                   "image": b["images"]["medium"], "rating": b["rating"]["average"],
                   "quantity": l["quantity"], "unitPrice": l["unitPrice"]}
                  for l, b in zip(order["lines"], books)],
        "totals": {k: order[k] for k in ("subtotal", "tax", "shippingFee", "total", "currency")},
        "shipTo": order["shippingAddress"],
        "tracking": None if isinstance(shipment, Exception) else
                    {"carrier": shipment["carrier"], "number": shipment["trackingNumber"],
                     "events": shipment["events"]},
    }
