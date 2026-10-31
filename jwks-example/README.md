Source code for the article [JWKS Explained: Verify JWTs with a JSON Web Key Set](https://restfulapi.net/jwks/)

A demo authorization server publishes its public signing keys as a JWKS (JSON Web Key Set)
and issues JWT access tokens. An Orders API finds the JWKS through the issuer's metadata,
verifies tokens with PyJWT's `PyJWKClient`, and logs every JWKS fetch. The demo shows
caching, forged tokens, a key rotation done too fast, a rotation done right, and what
happens when an old key is removed.

## Files

| File | What it does |
|---|---|
| auth_server.py | Authorization server: RFC 8414 metadata, `/.well-known/jwks.json`, `/token` (client credentials), demo-only `/admin/keys` endpoints to add, activate and remove keys |
| orders_api.py | Resource server: `GET /orders` verifies the Bearer token with the JWKS; `GET /debug/jwks-fetches` counts JWKS fetches |
| verify_by_hand.py | Verifies one token step by step with only `cryptography` and `httpx` (no JWT library) |
| forge_token.py | Signs a token with a made-up key and any `kid`, to show what the API rejects |
| demo.sh | Runs the whole story with curl (about 160 seconds, because it waits for the cooldown and the cache) |
| OUTPUTS.txt | Output of one run |

## Versions

- Python 3.13
- fastapi 0.162.0, uvicorn 0.54.0, PyJWT 2.15.1, cryptography 50.0.2, httpx 0.28.1
- curl

## How to run

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHON=.venv/bin/python ./demo.sh
```

The authorization server listens on port 8000 and the Orders API on 8001.
Change them with `AUTH_PORT` and `API_PORT`. The demo sets the API's JWKS cache
lifetime to 60 seconds (`JWKS_CACHE_SECONDS`); the code default is 300 seconds,
the same as PyJWT's default.

To run the servers by hand:

```
.venv/bin/python auth_server.py
.venv/bin/python orders_api.py
curl -u orders-app:demo-secret-not-real -d grant_type=client_credentials http://127.0.0.1:8000/token
```

All keys are generated in memory at start-up. The client secret `demo-secret-not-real`
is a demo value, and the `/admin` endpoints have no authentication. Never use any of
this in production.
