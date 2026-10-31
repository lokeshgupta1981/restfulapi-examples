Source code for the article [JWT vs JWE vs JWS: Signed vs Encrypted Tokens](https://restfulapi.net/jws-vs-jwe-vs-jwt/)

The same set of JWT claims protected three ways: signed (JWS), encrypted (JWE) and
signed, then encrypted (a nested JWT). The demo shows what each token reveals, what
happens when a token is changed or forged, how to tell a JWS from a JWE, and what the
encryption costs in size and time. A small Orders API accepts each kind of token on its
own route, including one deliberately naive route that only decrypts.

## Files

| File | What it does |
|---|---|
| keys.py | Creates the demo keys on first use in demo-keys/ (EC P-256 signing key of the auth server, RSA 2048 encryption key of the Orders API) |
| tokens.py | make_jws(), make_jwe(), make_nested(), kind_of(), verify_jws(), decrypt_only(), decrypt_and_verify() |
| demo.py | Walks through all cases and prints token parts, results, sizes and timings |
| server.py | Orders API: GET /jws/orders, GET /jwe-only/orders (naive, do not copy), GET /orders (nested JWT) |
| issue.py | Prints one token: jws, jwe, nested, forged-jwe or forged-nested |
| demo.sh | Starts server.py and calls each route with curl |
| OUTPUTS.txt | Output of one run |

## Versions

- Python 3.13
- jwcrypto 1.6.1, cryptography 50.0.2, fastapi 0.162.0, uvicorn 0.54.0
- curl

## How to run

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python demo.py
PY=.venv/bin/python ./demo.sh
```

The server listens on port 8000. Set PORT to change it, for example `PORT=9000 ./demo.sh`.
`python demo.py 500` runs the timing loop with 500 tokens per round instead of 2000.

The keys in demo-keys/ are generated on your machine and are demo keys only. Never use
them, or the naive /jwe-only/orders route, in production.

OUTPUTS.txt holds the output of one run on Linux (2026-10-31).
