"""An AI agent's HTTP side: discover the authorization server, get tokens the
right way and call the Orders API. The "AI" part is left out on purpose.

python agent.py            -> stops when a risky action needs approval
python agent.py --approve  -> a human approved the cancel, so it goes ahead
"""
import base64
import hashlib
import json
import re
import secrets
import sys
from urllib.parse import parse_qs, urlparse

import httpx
import jwt

API = "http://127.0.0.1:9201"
# The agent sends its secrets only to an authorization server it was set up
# with. Discovery may point anywhere; trust comes from this configuration.
TRUSTED_ISSUER = "http://127.0.0.1:9200"
TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"
http = httpx.Client(timeout=10)


def show_claims(label, token):
    # Decoding without verification is fine for printing. Never for trusting.
    claims = jwt.decode(token, options={"verify_signature": False})
    keep = ["sub", "client_id", "aud", "scope", "act", "may_act"]
    lifetime = claims["exp"] - claims["iat"]
    print(f"  {label}:", json.dumps({k: claims[k] for k in keep if k in claims}),
          f"(valid {lifetime} s)")


def discover():
    """Find the authorization server from the API's 401 response (RFC 9728)."""
    r = http.get(API + "/orders")
    challenge = r.headers["WWW-Authenticate"]
    print("1. GET /orders without a token ->", r.status_code)
    print("  WWW-Authenticate:", challenge)
    metadata_url = re.search(r'resource_metadata="([^"]+)"', challenge).group(1)
    resource = http.get(metadata_url).json()
    if resource["resource"] != API:  # RFC 9728 section 3.3 check
        sys.exit("metadata is for a different resource, stopping")
    issuer = resource["authorization_servers"][0]
    if issuer != TRUSTED_ISSUER:
        sys.exit(f"{issuer} is not a trusted authorization server, stopping")
    as_meta = http.get(issuer + "/.well-known/oauth-authorization-server").json()
    if as_meta["issuer"] != issuer or not as_meta["token_endpoint"].startswith(issuer + "/"):
        sys.exit("issuer metadata mismatch, stopping")
    print("  authorization server:", issuer, "token endpoint:", as_meta["token_endpoint"])
    return as_meta


def call(method, path, token):
    r = http.request(method, API + path, headers={"Authorization": "Bearer " + token})
    print(f"  {method} {path} -> {r.status_code}")
    if r.status_code in (401, 403):
        print("  WWW-Authenticate:", r.headers["WWW-Authenticate"])
    return r


def acting_for_itself(as_meta):
    print("\n2. report-bot acts for itself (client credentials)")
    r = http.post(as_meta["token_endpoint"], data={
        "grant_type": "client_credentials", "client_id": "report-bot",
        "client_secret": "demo-secret-report-bot", "scope": "orders:read orders:read:all",
        "resource": API})
    token = r.json()["access_token"]
    show_claims("token", token)
    print("  orders seen:", [o["id"] for o in call("GET", "/orders", token).json()])
    call("POST", "/orders/ord_1003/cancel", token)


def sign_in_user(as_meta):
    print("\n3. Asha signs in to chat-app (authorization code + PKCE)")
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    redirect_uri = "http://127.0.0.1:9299/callback"
    # A real app opens this URL in the browser. The demo server approves at once.
    r = http.get(as_meta["authorization_endpoint"], params={
        "response_type": "code", "client_id": "chat-app", "redirect_uri": redirect_uri,
        "scope": "orders:read orders:write", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    query = parse_qs(urlparse(r.headers["Location"]).query)
    if query["state"][0] != state or query["iss"][0] != as_meta["issuer"]:
        sys.exit("state or issuer mismatch, stopping")
    r = http.post(as_meta["token_endpoint"], data={
        "grant_type": "authorization_code", "client_id": "chat-app",
        "code": query["code"][0], "redirect_uri": redirect_uri,
        "code_verifier": verifier})
    user_token = r.json()["access_token"]
    show_claims("user token", user_token)
    print("  The user token is not for the Orders API:")
    call("GET", "/orders", user_token)
    return user_token


def exchange(as_meta, user_token, scope):
    r = http.post(as_meta["token_endpoint"], data={
        "grant_type": TOKEN_EXCHANGE, "client_id": "shop-assistant",
        "client_secret": "demo-secret-shop-assistant",
        "subject_token": user_token, "subject_token_type": ACCESS_TOKEN_TYPE,
        "resource": API, "scope": scope})
    body = r.json()
    if r.status_code != 200:
        sys.exit(f"token exchange failed: {body}")
    show_claims("agent token", body["access_token"])
    return body["access_token"]


def acting_for_user(as_meta, user_token, approved):
    print("\n4. shop-assistant acts for Asha (token exchange, read only)")
    token = exchange(as_meta, user_token, "orders:read")
    print("  orders seen:", [o["id"] for o in call("GET", "/orders", token).json()])
    r = call("POST", "/orders/ord_1003/cancel", token)
    if r.status_code != 403:
        return
    needed = re.search(r'scope="([^"]+)"', r.headers["WWW-Authenticate"]).group(1)
    print(f"\n5. Cancel needs {needed}. Asking the human first.")
    if not approved:
        print("  Not approved. The agent stops here.")
        return
    print("  Approved. Getting a write token for this one action.")
    token = exchange(as_meta, user_token, needed)
    print("  result:", call("POST", "/orders/ord_1003/cancel", token).json())


if __name__ == "__main__":
    metadata = discover()
    acting_for_itself(metadata)
    asha_token = sign_in_user(metadata)
    acting_for_user(metadata, asha_token, approved="--approve" in sys.argv)
