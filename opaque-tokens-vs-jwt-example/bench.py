"""Compares opaque tokens and JWT access tokens against the demo servers:
token size, what a JWT reveals, validation latency and revocation.
Start auth_server.py, orders_api.py and gateway.py first (see run_all.sh).
"""
import base64
import json
import os
import statistics
import time

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec

AUTH = "http://127.0.0.1:9400"
API = "http://127.0.0.1:9401"
GATEWAY = "http://127.0.0.1:9402"
CLIENT = ("orders-app", "demo-secret-key-123")  # demo credentials
REQUESTS_PER_MODE = int(os.environ.get("REQUESTS_PER_MODE", "1000"))
CACHE_TTL = int(os.environ.get("CACHE_TTL", "10"))

http = httpx.Client(timeout=5.0)


def get_token(token_format: str) -> str:
    response = http.post(
        AUTH + "/token",
        auth=CLIENT,
        data={"grant_type": "client_credentials", "scope": "orders:read", "token_format": token_format},
    )
    return response.json()["access_token"]


def call(url: str, token_value: str):
    return http.get(url, headers={"Authorization": "Bearer " + token_value})


def section(title: str):
    print()
    print("== " + title)


# 1. Size on the wire
section("1. Token sizes")
opaque = get_token("opaque")
signed_jwt = get_token("jwt")
print("opaque token :", opaque)
print("opaque length:", len(opaque), "characters")
print("JWT length   :", len(signed_jwt), "characters")
header_b64, payload_b64, signature_b64 = signed_jwt.split(".")
print("JWT parts    : header", len(header_b64), "+ payload", len(payload_b64), "+ signature", len(signature_b64))
claims = jwt.decode(signed_jwt, options={"verify_signature": False})
es256_token = jwt.encode(claims, ec.generate_private_key(ec.SECP256R1()), algorithm="ES256",
                         headers={"typ": "at+jwt", "kid": "demo-key-2"})
print("same claims signed with ES256:", len(es256_token), "characters")

# 2. What anyone holding the JWT can read
section("2. Decoding the JWT payload without any key")
padded = payload_b64 + "=" * (-len(payload_b64) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(padded)), indent=2))

# 3. Latency per validation mode
section(f"3. Latency, {REQUESTS_PER_MODE} sequential requests per mode")
modes = [
    ("JWT, local signature check", API + "/jwt/orders", signed_jwt),
    ("Opaque, introspection every call", API + "/introspect/orders", opaque),
    (f"Opaque, introspection + {CACHE_TTL} s cache", API + "/cached/orders", opaque),
    ("Phantom token via gateway", GATEWAY + "/orders", opaque),
]
print(f"{'mode':<38}{'p50 ms':>8}{'p95 ms':>8}{'p99 ms':>8}{'check p50':>11}{'introspections':>16}")
print(f"{'(introspections include 50 warm-up calls)':<38}")
for name, url, token_value in modes:
    http.post(AUTH + "/stats/reset")
    for _ in range(50):  # warm-up: connections, JWKS download, caches
        call(url, token_value)
    totals, auth_times = [], []
    for _ in range(REQUESTS_PER_MODE):
        started = time.perf_counter()
        response = call(url, token_value)
        totals.append((time.perf_counter() - started) * 1000)
        assert response.status_code == 200, response.text
        timings = dict(
            part.strip().split(";dur=") for part in response.headers["server-timing"].split(",")
        )
        # Token check time: the API's own check, plus the gateway's time for the phantom route.
        auth_times.append(sum(float(value) for value in timings.values()))
    calls = http.get(AUTH + "/stats").json()["introspect"]
    q = statistics.quantiles(totals, n=100)
    print(f"{name:<38}{q[49]:>8.2f}{q[94]:>8.2f}{q[98]:>8.2f}{statistics.median(auth_times):>11.3f}{calls:>16}")

# 4. Revocation
section("4. Revocation")
opaque = get_token("opaque")
signed_jwt = get_token("jwt")
print("before revoke: JWT local       ->", call(API + "/jwt/orders", signed_jwt).status_code)
print("before revoke: opaque cached   ->", call(API + "/cached/orders", opaque).status_code)
print("before revoke: phantom gateway ->", call(GATEWAY + "/orders", opaque).status_code)
for token_value in (opaque, signed_jwt):
    http.post(AUTH + "/revoke", auth=CLIENT, data={"token": token_value})
print("revoked both tokens at the authorization server (POST /revoke)")
print("after revoke : JWT local       ->", call(API + "/jwt/orders", signed_jwt).status_code)
print("after revoke : JWT introspected->", call(API + "/introspect/orders", signed_jwt).status_code)
print("after revoke : opaque introsp. ->", call(API + "/introspect/orders", opaque).status_code)
print("after revoke : opaque cached   ->", call(API + "/cached/orders", opaque).status_code)
print("after revoke : phantom gateway ->", call(GATEWAY + "/orders", opaque).status_code)
time.sleep (CACHE_TTL + 1)
print(f"{CACHE_TTL + 1} s later  : opaque cached   ->", call(API + "/cached/orders", opaque).status_code)
print(f"{CACHE_TTL + 1} s later  : phantom gateway ->", call(GATEWAY + "/orders", opaque).status_code)
response = call(API + "/introspect/orders", opaque)
print("401 challenge:", response.headers["www-authenticate"])
