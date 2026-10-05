"""Orders API that accepts only HMAC-signed requests.

Run: uvicorn server:app --port 9410
"""
import json
import re
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from signing import canonical_request, sign, signatures_match

# Two active keys during a rotation: the client may sign with either one.
# Example values only, never real secrets.
KEYS = {
    "client-1-2026-10": b"demo-secret-key-2026-10",
    "client-1-2026-07": b"demo-secret-key-2026-07",
}
MAX_SKEW_SECONDS = 300
seen_nonces = {}  # nonce -> expiry time; use Redis with a TTL in production

AUTH_PATTERN = re.compile(r'(\w+)="([^"]*)"')

app = FastAPI()


def problem(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        media_type="application/problem+json",
        headers={"WWW-Authenticate": 'HMAC-SHA256 realm="orders-api"'},
        content={"type": "about:blank", "title": "Unauthorized",
                 "status": 401, "detail": detail},
    )


async def verify(request: Request, body: bytes):
    header = request.headers.get("authorization", "")
    scheme, _, params_text = header.partition(" ")
    if scheme.lower() != "hmac-sha256":
        return problem("Missing HMAC-SHA256 Authorization header.")
    params = dict(AUTH_PATTERN.findall(params_text))
    secret = KEYS.get(params.get("keyId", ""))
    if secret is None:
        return problem("Unknown keyId.")

    ts = params.get("ts", "")
    if not ts.isdigit() or abs(time.time() - int(ts)) > MAX_SKEW_SECONDS:
        return problem("Timestamp outside the 300 second window.")

    canonical = canonical_request(
        request.method, request.headers.get("host", ""), request.url.path,
        request.url.query, ts, params.get("nonce", ""), body)
    expected = sign(secret, canonical)
    if not signatures_match(expected, params.get("sig", "")):
        print("canonical request on the server:\n" + canonical)
        return problem("Signature does not match.")

    now = time.time()
    for nonce, expiry in list(seen_nonces.items()):
        if expiry < now:
            del seen_nonces[nonce]
    nonce = params.get("nonce", "")
    if nonce in seen_nonces:
        return problem("Nonce already used.")
    seen_nonces[nonce] = now + 2 * MAX_SKEW_SECONDS
    return None


@app.post("/orders")
async def create_order(request: Request):
    body = await request.body()  # raw bytes, exactly as sent
    error = await verify(request, body)
    if error:
        return error
    order = json.loads(body)
    return JSONResponse(status_code=201, content={"id": 1001, **order})


@app.get("/orders/{order_id}")
async def get_order(order_id: int, request: Request):
    error = await verify(request, b"")
    if error:
        return error
    return {"id": order_id, "item": "keyboard", "quantity": 2}


@app.post("/buggy/orders")
async def create_order_buggy(request: Request):
    # BUG: hashes a re-serialized copy of the JSON instead of the raw bytes
    body = await request.body()
    reserialized = json.dumps(json.loads(body)).encode("utf-8")
    error = await verify(request, reserialized)
    if error:
        return error
    return JSONResponse(status_code=201, content={"id": 1002})
