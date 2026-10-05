"""Demo API gateway that implements the phantom token pattern.

Clients send an opaque token. The gateway introspects it, asks for the
JWT form (Accept: application/jwt), caches that JWT for a short time
and forwards the request to the Orders API with the JWT.
"""
import hashlib
import os
import time

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

INTROSPECTION_URL = "http://127.0.0.1:9400/introspect"
UPSTREAM = "http://127.0.0.1:9401/jwt/orders"
GATEWAY_CREDENTIALS = ("orders-api", "demo-introspect-secret-456")  # demo values
CACHE_TTL = int(os.environ.get("CACHE_TTL", "10"))  # seconds, our example value

introspection_client = httpx.Client(auth=GATEWAY_CREDENTIALS, timeout=2.0)
upstream_client = httpx.Client(timeout=5.0)
jwt_cache = {}  # sha256(opaque token) -> (cached_until, jwt)

app = FastAPI()


def unauthorized():
    return JSONResponse(
        {"error": "invalid_token"},
        status_code=401,
        headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
    )


def jwt_for(opaque_token: str):
    key = hashlib.sha256(opaque_token.encode()).hexdigest()
    entry = jwt_cache.get(key)
    now = time.time()
    if entry and entry[0] > now:
        return entry[1]
    response = introspection_client.post(
        INTROSPECTION_URL,
        data={"token": opaque_token},
        headers={"Accept": "application/jwt"},
    )
    if response.headers.get("content-type", "").startswith("application/jwt"):
        jwt_cache[key] = (now + CACHE_TTL, response.text)
        return response.text
    return None  # {"active": false}


@app.get("/orders")
def orders(request: Request):
    started = time.perf_counter()
    scheme, _, opaque_token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not opaque_token:
        return unauthorized()
    access_jwt = jwt_for(opaque_token)
    if access_jwt is None:
        return unauthorized()
    gateway_ms = (time.perf_counter() - started) * 1000
    upstream = upstream_client.get(UPSTREAM, headers={"Authorization": "Bearer " + access_jwt})
    timing = upstream.headers.get("server-timing", "")
    return Response(
        upstream.content,
        status_code=upstream.status_code,
        media_type="application/json",
        headers={"Server-Timing": f"gateway;dur={gateway_ms:.3f}, {timing}"},
    )
