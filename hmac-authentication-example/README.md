Source code for the article [HMAC Authentication: Signing API Requests and Webhooks](https://restfulapi.net/hmac-authentication/)

An Orders API (FastAPI) that accepts only HMAC-SHA256 signed requests, a Python client that sends ten signed test requests (valid, replayed, tampered, expired, rotated keys, and a server bug), the same signing code in Node.js and Java, an HTTP Message Signatures (RFC 9421) demo, and webhook signature checks for GitHub and Stripe.

All keys in this folder are example values such as `demo-secret-key-2026-10`. Never use them for a real API.

## Versions

- Python 3.13, FastAPI 0.162.0 (Starlette 1.10.0), uvicorn 0.54.0, httpx 0.28.1, requests 2.34.2, http-message-signatures 3.0.0, stripe 16.1.0
- Node.js 22 (built-in `node:crypto`, no packages)
- JDK 25 (single-file `java Sign.java`, no dependencies)
- curl 8.5.0

## Files

| File | What it does |
|---|---|
| `hmac_basics.py` | Shows that an HMAC changes with the message and with the key |
| `signing.py` | Canonical request, HMAC-SHA256 signature and constant-time compare in Python |
| `server.py` | Orders API on port 9410: checks keyId, timestamp window (300 s), signature and nonce; `/buggy/orders` shows the re-serialized JSON bug |
| `client.py` | Python client (httpx) that signs requests and sends the ten test requests |
| `sign.mjs` | The same canonical request, signature and constant-time compare in Node.js |
| `Sign.java` | The same canonical request and signature in Java |
| `rfc9421_demo.py` | RFC 9421 signature base, test case B.2.5, `Signature-Input` and `Signature` for an order, verification with the http-message-signatures library |
| `webhooks.py` | GitHub `X-Hub-Signature-256` test vector, a Stripe-format signature verified by the stripe library, raw vs re-serialized JSON |
| `run_all.sh` | Runs everything; its output is in `OUTPUTS.txt` |

## How to run

```bash
git clone https://github.com/lokeshgupta1981/restfulapi-examples.git
cd restfulapi-examples/hmac-authentication-example

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Everything at once (starts and stops the server)
./run_all.sh
```

Or step by step:

```bash
python hmac_basics.py            # what an HMAC is
python signing.py                # canonical request and signature in Python
node sign.mjs                    # same values in Node.js
java Sign.java                   # same values in Java

uvicorn server:app --port 9410   # terminal 1
python client.py                 # terminal 2: ten test requests

python rfc9421_demo.py
python webhooks.py
```

The timestamps and nonces in your output differ from `OUTPUTS.txt` because the client uses the current time and random nonces. The fixed test values (`1791200000`, `n-0001`) always give signature `9140e96dca095dfa3f4f13b237c07bb7cb5b116fcbf7c52d69665d12c40d066f`.
