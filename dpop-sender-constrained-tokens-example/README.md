Source code for the article [DPoP Token: Sender-Constrained OAuth Access Tokens](https://restfulapi.net/dpop-sender-constrained-tokens/)

# DPoP example

A demo authorization server and an Orders API that use DPoP (RFC 9449) to bind OAuth access tokens to the client's key pair. A client script shows that a stolen plain bearer token works for anyone, and that a stolen DPoP-bound token does not: sent as Bearer, without a proof, with a proof signed by another key, as a replayed proof, with a proof for another method, with an old proof, or with a proof for another token. It also shows the server nonce flow (`use_dpop_nonce` and the `DPoP-Nonce` header).

## Files

| File | What it does |
|---|---|
| `dpop.py` | Creates DPoP proofs (client side) and runs the RFC 9449 section 4.3 checks (server side): JWK thumbprint, `ath`, `htm`, `htu`, `iat` window, `jti` replay cache, nonce |
| `auth_server.py` | Demo authorization server: client credentials grant, issues a DPoP-bound JWT (`cnf.jkt`, `token_type: DPoP`) when the request has a valid `DPoP` header and a plain bearer token otherwise; JWKS and metadata with `dpop_signing_alg_values_supported` |
| `orders_api.py` | Orders API: `GET /orders` and `POST /orders`; accepts `Authorization: DPoP` with a proof, still accepts unbound bearer tokens for comparison, rejects a DPoP-bound token sent as Bearer. `REQUIRE_NONCE=1` turns on server nonces |
| `client.py` | The walkthrough: bearer token replay, DPoP token, seven attack attempts, nonce retry |
| `make_proof.py` | Prints a proof for curl (keeps a demo key in `demo-key.pem`, deleted by `demo.sh`) |
| `demo.sh` | The raw HTTP exchanges with curl |
| `test_rfc_examples.py` | Checks the thumbprint and `ath` code against the examples in RFC 9449 |
| `bench.py` | Measures the time to create and to check one proof |
| `run_all.sh` | Starts the servers, runs everything, stops the servers |

## Versions

- Python 3.13.18 (3.10 or newer works)
- fastapi 0.143.0, uvicorn 0.54.0, PyJWT 2.15.1, cryptography 50.0.2, httpx 0.28.1, python-multipart 0.0.32
- curl 8 and jq 1.7 (for `demo.sh`)

## How to run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/dpop-sender-constrained-tokens-example
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./run_all.sh
```

Or start the pieces by hand:

```bash
uvicorn auth_server:app --port 8000                     # terminal 1
uvicorn orders_api:app --port 8001                      # terminal 2
REQUIRE_NONCE=1 uvicorn orders_api:app --port 8002      # terminal 3
python client.py                                        # terminal 4
./demo.sh
```

Other ports: `AUTH_PORT=9000 API_PORT=9001 NONCE_API_PORT=9002 ./run_all.sh`. When starting by hand, set `ISSUER`, `AUTH_URL`, `API_URL` and `NONCE_API_URL` to match.

`OUTPUTS.txt` holds the output of one run. Keys, `jti` values and nonces differ on every run.

## Demo only

The client secret `demo-secret-not-for-production` is fake. The authorization server keeps its signing key in memory and the replay cache lives in one process. Use a real authorization server in production, run everything over HTTPS, and share the `jti` cache (or use nonces) when the API runs on more than one instance.
