"""The Bookstore app: a public client that signs in with authorization code + PKCE.

Run: python client.py              (server on http://127.0.0.1:8000)
     AUTH_URL=http://127.0.0.1:9000 python client.py
"""
import os
import secrets
import sys
from urllib.parse import parse_qs, urlsplit

import httpx

from pkce import make_challenge, make_verifier

AUTH_URL = os.environ.get("AUTH_URL", "http://127.0.0.1:8000")
CLIENT_ID = "bookstore-app"
REDIRECT_URI = "com.example.bookstore:/oauth/callback"


def start_login(http, use_pkce=True):
    """Send the authorization request. Returns (location, state, verifier)."""
    state = secrets.token_urlsafe(16)
    params = {"response_type": "code", "client_id": CLIENT_ID,
              "redirect_uri": REDIRECT_URI, "state": state}
    verifier = None
    if use_pkce:
        verifier = make_verifier()
        params["code_challenge"] = make_challenge(verifier)
        params["code_challenge_method"] = "S256"
    # The real app opens this URL in the system browser. The demo server signs
    # the user in automatically and answers with a 302 to the redirect URI.
    r = http.get(AUTH_URL + "/authorize", params=params)
    return r, state, verifier


def code_from(location, expected_state):
    query = parse_qs(urlsplit(location).query)
    if query.get("state", [None])[0] != expected_state:
        sys.exit("state mismatch, stopping")
    if "error" in query:
        sys.exit(f"authorization error: {query}")
    return query["code"][0]


def redeem(http, code, verifier):
    form = {"grant_type": "authorization_code", "code": code,
            "redirect_uri": REDIRECT_URI, "client_id": CLIENT_ID}
    if verifier is not None:
        form["code_verifier"] = verifier
    return http.post(AUTH_URL + "/token", data=form)


def main():
    with httpx.Client(follow_redirects=False) as http:
        meta = http.get(AUTH_URL + "/.well-known/oauth-authorization-server").json()
        methods = meta.get("code_challenge_methods_supported", [])
        print("1. Server metadata: code_challenge_methods_supported =",
              methods or "(absent)")
        if "S256" not in methods:
            sys.exit("   The server does not advertise S256 PKCE, refusing to continue.")

        r, state, verifier = start_login(http)
        print("2. GET", r.request.url)
        print("   ->", r.status_code, "Location:", r.headers["location"])
        code = code_from(r.headers["location"], state)

        r = redeem(http, code, verifier)
        print("3. POST /token with code_verifier =", verifier)
        print("   ->", r.status_code, r.text)
        token = r.json()["access_token"]

        r = http.get(AUTH_URL + "/orders", headers={"Authorization": "Bearer " + token})
        print("4. GET /orders ->", r.status_code, r.text)


if __name__ == "__main__":
    main()
