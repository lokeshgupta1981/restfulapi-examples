"""Sends the same OAuth requests to the 2.0 server and the 2.1 server and
prints what each one answers.

Run: python client.py http://127.0.0.1:8000 http://127.0.0.1:8001
"""
import base64
import hashlib
import secrets
import sys
from urllib.parse import parse_qs, urlsplit

import httpx

CLIENT_ID = "bookstore-spa"
CALLBACK = "https://bookstore.example/callback"


def location(r):
    """The redirect the browser would follow, split into query and fragment."""
    loc = urlsplit(r.headers.get("location", ""))
    params = parse_qs(loc.query) or parse_qs(loc.fragment)
    return {k: v[0] for k, v in params.items()}


def pkce_pair():
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def authorize(c, **params):
    return c.get("/authorize", params={"client_id": CLIENT_ID, "state": "s1", **params})


def implicit(c):
    r = authorize(c, response_type="token", redirect_uri=CALLBACK)
    p = location(r)
    if "access_token" in p:
        return "token in the URL fragment: #access_token=" + p["access_token"][:8] + "..."
    return f"{r.status_code} -> error={p.get('error')}"


def password(c):
    r = c.post("/token", data={"grant_type": "password", "client_id": CLIENT_ID,
                               "username": "asha", "password": "demo-password-asha"})
    return f"{r.status_code} " + ("access_token issued" if r.status_code == 200
                                  else "error=" + r.json()["error"])


def code_without_pkce(c):
    r = authorize(c, response_type="code", redirect_uri=CALLBACK)
    p = location(r)
    if "code" not in p:
        return f"{r.status_code} -> error={p.get('error')} ({p.get('error_description')})"
    t = c.post("/token", data={"grant_type": "authorization_code", "client_id": CLIENT_ID,
                               "code": p["code"], "redirect_uri": CALLBACK})
    return f"code issued, token {t.status_code}"


def plain_pkce(c):
    r = authorize(c, response_type="code", redirect_uri=CALLBACK,
                  code_challenge="the-verifier-in-clear-text-1234567890-abcdefgh",
                  code_challenge_method="plain")
    p = location(r)
    return "code issued" if "code" in p else f"error={p.get('error')} ({p.get('error_description')})"


def lookalike_redirect(c):
    evil = "https://bookstore.example.attacker.example/steal"
    r = authorize(c, response_type="code", redirect_uri=evil)
    if r.status_code == 302:
        return "302 -> code sent to " + urlsplit(r.headers["location"]).hostname
    return f"{r.status_code} -> {r.json()['error_description']}"


def code_with_pkce(c):
    """The flow both versions accept. Returns the tokens for the next checks."""
    verifier, challenge = pkce_pair()
    r = authorize(c, response_type="code", redirect_uri=CALLBACK,
                  code_challenge=challenge, code_challenge_method="S256")
    p = location(r)
    # No redirect_uri in the token request: OAuth 2.1 dropped it.
    t = c.post("/token", data={"grant_type": "authorization_code", "client_id": CLIENT_ID,
                               "code": p["code"], "code_verifier": verifier})
    iss = f"iss={p['iss']}" if "iss" in p else "no iss"
    summary = f"{iss}, token {t.status_code}"
    if t.status_code != 200:
        summary += " (" + t.json()["error_description"] + ")"
        # A 2.0 client sends redirect_uri again; retry the way it would.
        r = authorize(c, response_type="code", redirect_uri=CALLBACK,
                      code_challenge=challenge, code_challenge_method="S256")
        t = c.post("/token", data={"grant_type": "authorization_code", "client_id": CLIENT_ID,
                                   "code": location(r)["code"], "code_verifier": verifier,
                                   "redirect_uri": CALLBACK})
        summary += f"; with redirect_uri: token {t.status_code}"
    return summary, t.json()


def token_in_query(c, tokens):
    r = c.get("/books", params={"access_token": tokens["access_token"]})
    h = c.get("/books", headers={"Authorization": "Bearer " + tokens["access_token"]})
    return f"?access_token= -> {r.status_code}, Authorization header -> {h.status_code}"


def refresh_reuse(c, tokens):
    old = tokens["refresh_token"]
    data = {"grant_type": "refresh_token", "client_id": CLIENT_ID, "refresh_token": old}
    first = c.post("/token", data=data)
    second = c.post("/token", data=data)          # the same refresh token again
    rotated = "new refresh token" if "refresh_token" in first.json() else "same refresh token"
    out = f"1st use {first.status_code} ({rotated}), 2nd use {second.status_code}"
    if second.status_code != 200:
        out += " " + second.json()["error_description"]
        nxt = c.post("/token", data={**data, "refresh_token": first.json()["refresh_token"]})
        out += f"; new token afterwards {nxt.status_code}"
    return out


def run(base):
    with httpx.Client(base_url=base) as c:
        print(f"== {base} ({c.get('/openapi.json').json()['info']['title']})")
        print("1. implicit grant          :", implicit(c))
        print("2. password grant          :", password(c))
        print("3. code without PKCE       :", code_without_pkce(c))
        print("4. PKCE method plain       :", plain_pkce(c))
        print("5. look-alike redirect_uri :", lookalike_redirect(c))
        summary, tokens = code_with_pkce(c)
        print("6. code + PKCE (S256)      :", summary)
        print("7. bearer token in the URL :", token_in_query(c, tokens))
        print("8. refresh token used twice:", refresh_reuse(c, tokens))
        print()


if __name__ == "__main__":
    for url in sys.argv[1:] or ["http://127.0.0.1:8000", "http://127.0.0.1:8001"]:
        run(url)
