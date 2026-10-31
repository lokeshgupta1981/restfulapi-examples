Source code for the article [OAuth Token Exchange (RFC 8693): Swap Tokens Between APIs](https://restfulapi.net/oauth-token-exchange/)

A bookstore with three services shows OAuth 2.0 Token Exchange (RFC 8693). A user signs in and gets an access token for the Orders API only. The Orders API needs to charge the user through the Payments API, so it exchanges the user's token at the authorization server for a new token that is valid only for the Payments API, with a smaller scope and a shorter lifetime. The demo shows impersonation (no `act` claim), delegation (an `act` claim from an `actor_token`), a delegation chain (nested `act`), the errors the authorization server returns, the Payments API checking the current actor, and caching of exchanged tokens.

`auth_server.py` is a DEMO authorization server for learning only. It signs in the demo user "asha" without a password and keeps keys and policies in memory. Use a real authorization server in production. All client secrets (for example demo-secret-orders-api) are fake demo values.

## Versions

- Python 3.13.18 (3.10 or newer works)
- fastapi 0.143.0, uvicorn 0.54.0, PyJWT 2.15.1, cryptography 50.0.2, httpx 0.28.1, python-multipart 0.0.32
- curl

## Files

| File | Default port | What it does |
|---|---|---|
| auth_server.py | 8000 | Token endpoint with client credentials and token exchange, JWKS, exchange policy, demo login |
| orders_api.py | 8001 | POST /orders; gets a Payments API token (forward=user-token, impersonate or delegate) and caches it |
| payments_api.py | 8002 | POST /charges; accepts only tokens with aud payments-api and checks the current actor |
| token_check.py | - | JWT validation shared by both APIs (signature, issuer, audience, scope) |
| demo.py | - | Walks through every step and prints decoded tokens and responses |
| curl_demo.sh | - | The raw token exchange request and response with curl |
| run_all.sh | - | Starts the three servers, runs demo.py and curl_demo.sh, stops the servers |

## How to run

```
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
./run_all.sh
```

To use other ports, set BASE_PORT (the authorization server uses BASE_PORT, the Orders API BASE_PORT+1, the Payments API BASE_PORT+2):

```
BASE_PORT=9000 ./run_all.sh
```

To run the servers yourself, start each in its own terminal with the same AUTH_URL, ORDERS_URL and PAYMENTS_URL environment variables, for example `uvicorn auth_server:app --port 8000`, then run `python demo.py`.

OUTPUTS.txt holds the output of one run on Linux (2026-10-31, BASE_PORT=20430). Tokens, IDs and timestamps differ on every run.
