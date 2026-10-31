Source code for the article [JWT Claims Explained (Registered, Public and Private)](https://restfulapi.net/jwt-claims/)

A small Orders API for a bookstore that accepts JWT access tokens and validates their claims:
the signature with a fixed algorithm, the *typ* header, *iss*, *aud*, *exp*, *nbf*, the required
registered claims, and finally the *scope* claim for authorization. A token script creates one valid
token and ten broken ones, and *demo.sh* sends each of them to the API with curl.

## Versions

- Python 3.13
- fastapi 0.143.0, uvicorn 0.54.0, PyJWT 2.15.1, cryptography 50.0.2, httpx 0.28.1
- curl

## Files

| File | What it does |
|---|---|
| tokens.py | Demo issuer: creates an RSA demo key pair in demo-keys/ and signs RS256 tokens with registered, public and private claims |
| orders_api.py | FastAPI Orders API: GET /orders (needs orders:read), POST /orders/{id}/refund (needs orders:refund) |
| make_tokens.py | Writes a valid token and ten broken ones to tokens/ |
| decode_token.py | Decodes a token with plain Base64URL, no key, to show that claims are readable by anyone |
| demo.sh | Starts the API and calls it with every token using curl |
| pitfalls.py | Shows which claims PyJWT checks only when we ask for them |
| size.py | Compares token sizes for small and large claim sets |
| run_all.sh | Runs everything; its output is in OUTPUTS.txt |

## How to run

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
source .venv/bin/activate
./run_all.sh            # or: PORT=9000 ./run_all.sh
```

The API listens on port 8000 by default; set PORT to change it.

The RSA key in demo-keys/ is created on first run and is a demo key only. Never commit it and never use it in production.

OUTPUTS.txt holds the output of one run on Linux (2026-10-31). Tokens, *jti* values and times differ on every run.
