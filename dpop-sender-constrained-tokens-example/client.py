"""Walks through bearer tokens, DPoP-bound tokens and the attacks DPoP stops.

Run the authorization server and the Orders API first (see README.md).
"""
import base64
import json
import os
import time

import httpx

import dpop

AUTH = os.environ.get("AUTH_URL", "http://localhost:8000")
API = os.environ.get("API_URL", "http://localhost:8001")
NONCE_API = os.environ.get("NONCE_API_URL", "http://localhost:8002")
CLIENT = ("orders-app", "demo-secret-not-for-production")       # fake demo credentials


def show(title, r):
    print(f"\n--- {title}")
    print(r.status_code, r.reason_phrase)
    for h in ("www-authenticate", "dpop-nonce"):
        if h in r.headers:
            print(f"{h}: {r.headers[h]}")
    print(r.text[:300])


def payload(token):
    part = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def get_token(key=None):
    headers = {"DPoP": dpop.make_proof(key, "POST", f"{AUTH}/token")} if key else {}
    r = httpx.post(f"{AUTH}/token", auth=CLIENT, headers=headers,
                   data={"grant_type": "client_credentials", "scope": "orders:read"})
    r.raise_for_status()
    return r.json()


print("=== 1. A plain bearer token works for anyone who has it")
bearer = get_token()["access_token"]
show("legitimate client, Bearer", httpx.get(f"{API}/orders", headers={"Authorization": f"Bearer {bearer}"}))
show("attacker replays the stolen token", httpx.get(f"{API}/orders", headers={"Authorization": f"Bearer {bearer}"}))

print("\n=== 2. A DPoP-bound token")
key = dpop.new_key()
print("client public key thumbprint (jkt):", dpop.jwk_thumbprint(dpop.public_jwk(key)))
resp = get_token(key)
token = resp["access_token"]
print("token_type:", resp["token_type"])
print("cnf claim in the token:", payload(token)["cnf"])
proof = dpop.make_proof(key, "GET", f"{API}/orders", access_token=token)
print("proof header:", json.dumps(dpop.jwt.get_unverified_header(proof)))
print("proof claims:", json.dumps(payload(proof)))
show("legitimate client, DPoP",
     httpx.get(f"{API}/orders", headers={"Authorization": f"DPoP {token}", "DPoP": proof}))

print("\n=== 3. What an attacker can do with the stolen DPoP token")
show("stolen token sent as Bearer", httpx.get(f"{API}/orders", headers={"Authorization": f"Bearer {token}"}))
show("stolen token sent as DPoP without a proof", httpx.get(f"{API}/orders", headers={"Authorization": f"DPoP {token}"}))
attacker_key = dpop.new_key()
own_proof = dpop.make_proof(attacker_key, "GET", f"{API}/orders", access_token=token)
show("stolen token + proof signed with the attacker's own key",
     httpx.get(f"{API}/orders", headers={"Authorization": f"DPoP {token}", "DPoP": own_proof}))
show("captured token + proof replayed unchanged",
     httpx.get(f"{API}/orders", headers={"Authorization": f"DPoP {token}", "DPoP": proof}))
show("captured GET proof reused for POST /orders",
     httpx.post(f"{API}/orders", json={"item": "free stuff", "total": 0},
                headers={"Authorization": f"DPoP {token}", "DPoP": proof}))
old = dpop.make_proof(key, "GET", f"{API}/orders", access_token=token, iat=int(time.time()) - 300)
show("proof created 5 minutes ago",
     httpx.get(f"{API}/orders", headers={"Authorization": f"DPoP {token}", "DPoP": old}))
other = dpop.make_proof(key, "GET", f"{API}/orders", access_token=bearer)
show("proof made for a different access token (ath mismatch)",
     httpx.get(f"{API}/orders", headers={"Authorization": f"DPoP {token}", "DPoP": other}))

print("\n=== 4. A server nonce (API started with REQUIRE_NONCE=1)")
first = httpx.get(f"{NONCE_API}/orders", headers={
    "Authorization": f"DPoP {token}",
    "DPoP": dpop.make_proof(key, "GET", f"{NONCE_API}/orders", access_token=token)})
show("first call without a nonce", first)
nonce = first.headers["dpop-nonce"]
retry = httpx.get(f"{NONCE_API}/orders", headers={
    "Authorization": f"DPoP {token}",
    "DPoP": dpop.make_proof(key, "GET", f"{NONCE_API}/orders", access_token=token, nonce=nonce)})
show("retry with the nonce in the proof", retry)
