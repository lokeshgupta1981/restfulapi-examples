"""A tiny OAuth 2.0 authorization server, just enough for the demo.

- GET  /authorize  signs in the demo user 'alice' without a login form and
                   redirects back with an authorization code (PKCE S256 required)
- POST /token      authorization_code and refresh_token grants

It is NOT a real authorization server: no login page, no consent, keys are fake.
"""
import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

import jwt
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import RedirectResponse

import settings

app = FastAPI(title="demo-authorization-server")

CLIENTS = {
    # confidential client: has a secret, runs on the server (the web BFF)
    settings.WEB_BFF_CLIENT_ID: {"secret": settings.WEB_BFF_CLIENT_SECRET,
                                 "redirect": f"{settings.WEB_BFF_URL}/bff/callback"},
    # public client: native mobile app, no secret, PKCE only
    settings.MOBILE_CLIENT_ID: {"secret": None,
                                "redirect": "com.example.bookstore:/callback"},
}
CODES: dict[str, dict] = {}
REFRESH_TOKENS: dict[str, dict] = {}


def s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def issue_tokens(client_id: str, user: str) -> dict:
    now = int(time.time())
    access = jwt.encode({"sub": user, "aud": "bookstore-api", "client_id": client_id,
                         "iat": now, "exp": now + settings.ACCESS_TOKEN_TTL},
                        settings.TOKEN_SIGNING_KEY, algorithm="HS256")
    refresh = secrets.token_urlsafe(32)
    REFRESH_TOKENS[refresh] = {"client_id": client_id, "user": user}
    return {"access_token": access, "token_type": "Bearer",
            "expires_in": settings.ACCESS_TOKEN_TTL, "refresh_token": refresh}


@app.get("/authorize")
def authorize(response_type: str, client_id: str, redirect_uri: str, state: str,
              code_challenge: str, code_challenge_method: str):
    client = CLIENTS.get(client_id)
    if not client or redirect_uri != client["redirect"]:
        raise HTTPException(400, "unknown client or redirect_uri")
    if response_type != "code" or code_challenge_method != "S256":
        raise HTTPException(400, "only response_type=code with PKCE S256")
    code = secrets.token_urlsafe(16)
    CODES[code] = {"client_id": client_id, "user": "alice",
                   "challenge": code_challenge, "redirect": redirect_uri}
    return RedirectResponse(f"{redirect_uri}?{urlencode({'code': code, 'state': state})}",
                            status_code=302)


@app.post("/token")
def token(grant_type: str = Form(...), client_id: str = Form(...),
          client_secret: str | None = Form(None), code: str | None = Form(None),
          code_verifier: str | None = Form(None), redirect_uri: str | None = Form(None),
          refresh_token: str | None = Form(None)):
    client = CLIENTS.get(client_id)
    if not client or client["secret"] != client_secret:
        raise HTTPException(401, "invalid_client")
    if grant_type == "authorization_code":
        grant = CODES.pop(code or "", None)
        if (not grant or grant["client_id"] != client_id or grant["redirect"] != redirect_uri
                or s256(code_verifier or "") != grant["challenge"]):
            raise HTTPException(400, "invalid_grant")
        return issue_tokens(client_id, grant["user"])
    if grant_type == "refresh_token":
        grant = REFRESH_TOKENS.pop(refresh_token or "", None)
        if not grant or grant["client_id"] != client_id:
            raise HTTPException(400, "invalid_grant")
        return issue_tokens(client_id, grant["user"])
    raise HTTPException(400, "unsupported_grant_type")
