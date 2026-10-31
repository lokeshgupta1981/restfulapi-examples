"""Shared client code: run the authorization code flow with PKCE."""
import base64
import hashlib
import os
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

ISSUER = os.environ.get("ISSUER", "http://127.0.0.1:8000")
REDIRECT_URI = "http://127.0.0.1:8099/callback"


def fetch_token(client_id, client_secret, user, scope, log=None):
    """Return the token response as a dict, or the error parameters from the redirect."""
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(8)
    query = urlencode({"response_type": "code", "client_id": client_id,
                       "redirect_uri": REDIRECT_URI, "scope": scope, "state": state,
                       "code_challenge": challenge, "code_challenge_method": "S256",
                       "login_hint": user})
    url = f"{ISSUER}/authorize?{query}"

    with httpx.Client() as http:
        redirect = http.get(url, follow_redirects=False)
        location = redirect.headers.get("location", "")
        if log:
            log(f"GET {url}")
            log(f"-> {redirect.status_code} Location: {location}")
        params = {k: v[0] for k, v in parse_qs(urlparse(location).query).items()}
        if params.get("state") != state:
            raise RuntimeError("state mismatch")
        if "code" not in params:
            params.pop("state")
            return params

        auth = (client_id, client_secret) if client_secret else None
        form = {"grant_type": "authorization_code", "code": params["code"],
                "redirect_uri": REDIRECT_URI, "code_verifier": verifier}
        if not client_secret:
            form["client_id"] = client_id
        return http.post(f"{ISSUER}/token", data=form, auth=auth).json()
