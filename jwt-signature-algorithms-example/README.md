Source code for the article [JWT Signature Verification: HS256 vs RS256 vs ES256](https://restfulapi.net/jwt-signature-algorithms/)

A demo token issuer and an Orders API that verifies JWT signatures before it trusts any claim.
The scripts show what a JWT signature covers, reproduce the common "Signature verification failed"
errors, run the alg=none and algorithm confusion attacks against a naive verifier, rotate a signing
key with a `kid`, and compare HS256, RS256, PS256, ES256 and EdDSA (Ed25519) by size and speed.

## Versions

- Python 3.13
- fastapi 0.143.0, uvicorn 0.54.0, PyJWT 2.15.1, cryptography 50.0.2, httpx 0.28.1
- curl

## Files

| File | What it does |
|---|---|
| issuer.py | POST /token (HS256, RS256 or ES256), GET /.well-known/jwks.json, POST /rotate. Default port 8000 |
| orders_api.py | GET /orders. Picks the key by `kid`, takes the algorithm from its own key table, never from the token. Default port 8001 |
| anatomy.py | Builds an HS256 token, splits it, recomputes the signature by hand, then tampers with the payload |
| failures.py | Reproduces common PyJWT verification errors (wrong secret, wrong key, alg not allowed, short secret, ...) |
| confusion.py | A naive verifier that trusts the `alg` header accepts alg=none and HS256-with-public-key forgeries; a pinned one rejects both |
| forge.py | Builds tampered and forged tokens for curl_demo.sh |
| curl_demo.sh | Raw HTTP exchanges: valid tokens, forged tokens, key rotation |
| bench.py | Signature size, token size, determinism, sign and verify time per algorithm |
| run_all.sh | Starts both servers, runs everything above, stops the servers |

## Run

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run_all.sh
```

Set ISSUER_PORT and API_PORT to use other ports, and BENCH_OPS to change the benchmark size.
The rotation demo waits 31 seconds, because PyJWKClient fetches the JWKS again for an unknown
`kid` at most once every 30 seconds (its default `cooldown_duration`).

run_all.sh creates a fresh random HS256 secret for each run and passes it to both servers in
HS256_SECRET. The RSA and EC keys are created in memory when issuer.py starts. The fixed secret
in anatomy.py and failures.py is a demo value. Never use any of these keys in production.

OUTPUTS.txt holds the output of one run on Linux (2026-10-31, 2 vCPUs). Benchmark times vary
between runs by up to about 2x on this machine; compare the orders of magnitude, not exact values.
