Source code for the article [Opaque Tokens vs JWT: Which Access Token to Use](https://restfulapi.net/opaque-tokens-vs-jwt/)

A demo authorization server, an Orders API that validates access tokens in three ways
(JWT signature check with a JWKS, RFC 7662 introspection, introspection with a cache)
and an API gateway that implements the phantom token pattern. A benchmark script compares
token size, claim privacy, latency and revocation.

## Versions

- Python 3.13
- fastapi 0.142.2, uvicorn 0.54.0, PyJWT 2.15.1, cryptography 50.0.2, httpx 0.28.1, python-multipart 0.0.32
- Node.js 22 (only for header_size_check.mjs)
- curl

## Files

| File | Port | What it does |
|---|---|---|
| auth_server.py | 9400 | Token endpoint (client credentials, demo field token_format=jwt or opaque), JWKS, introspection, revocation, metadata |
| orders_api.py | 9401 | GET /jwt/orders, /introspect/orders, /cached/orders |
| gateway.py | 9402 | GET /orders: opaque token in, JWT forwarded to the Orders API |
| bench.py | - | Token sizes, decoded JWT payload, latency per mode, revocation test |
| curl_demo.sh | - | Raw HTTP exchanges with curl |
| header_size_check.mjs | 9499 | Sends a 17,000-character Authorization header to a Node.js server |

## Run

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run_all.sh
node header_size_check.mjs
```

The revocation test waits 11 seconds for the 10-second caches to expire.
Set CACHE_TTL or REQUESTS_PER_MODE to change the defaults.

All keys and secrets (for example demo-secret-key-123) are demo values. Never use them in production.

OUTPUTS.txt holds the output of one run on Linux (2026-10-05).
