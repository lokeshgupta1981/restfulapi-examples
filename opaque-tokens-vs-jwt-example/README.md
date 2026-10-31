Source code for the article [Opaque Tokens vs JWT: Which Access Token to Use](https://restfulapi.net/opaque-tokens-vs-jwt/)

# Opaque tokens vs JWT example

A demo authorization server, an Orders API that checks access tokens in three ways, and an API gateway that implements the phantom token pattern. A benchmark script compares token size, what a JWT reveals, latency and revocation.

- The Orders API checks a JWT on its own with the public key from the JWKS (RFC 9068).
- It checks an opaque token by calling the introspection endpoint (RFC 7662), on every request or with a 10-second cache.
- When the authorization server is down, the JWT route keeps working and the introspection route answers HTTP 503 with `Retry-After`.
- A revoked JWT keeps working on the signature-only route until it expires; introspection sees the revocation at once.

## Files

| File | Port | What it does |
|---|---|---|
| auth_server.py | 9400 | Token endpoint (client credentials, demo field token_format=jwt or opaque), JWKS, introspection, revocation, metadata |
| orders_api.py | 9401 | GET /jwt/orders, /introspect/orders, /cached/orders |
| gateway.py | 9402 | GET /orders: opaque token in, JWT forwarded to the Orders API |
| bench.py | - | Token sizes, decoded JWT payload, latency per mode, revocation test |
| curl_demo.sh | - | Raw HTTP exchanges with curl |
| run_all.sh | - | Starts the servers, runs curl_demo.sh and bench.py, then stops the authorization server to show what each route does |
| header_size_check.mjs | 9499 | Sends a 17,000-character Authorization header to a Node.js server |

## Versions

- Python 3.13
- fastapi 0.142.2, uvicorn 0.54.0, PyJWT 2.15.1, cryptography 50.0.2, httpx 0.28.1, python-multipart 0.0.32
- Node.js 22 (only for header_size_check.mjs)
- curl

## How to run

```
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/opaque-tokens-vs-jwt-example
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run_all.sh
node header_size_check.mjs
```

The revocation test waits 11 seconds for the 10-second caches to expire.
Set CACHE_TTL or REQUESTS_PER_MODE to change the defaults. Set PY to use another Python interpreter than .venv/bin/python.

All keys and secrets (for example demo-secret-key-123) are demo values. Never use them in production.

OUTPUTS.txt holds the output of two runs on Linux (2026-10-05 and 2026-10-31).
