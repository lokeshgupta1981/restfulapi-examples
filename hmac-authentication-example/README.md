Source code for the article [HMAC Authentication: Signing API Requests and Webhooks](https://restfulapi.net/hmac-authentication/)

An Orders API (FastAPI) that accepts only HMAC-SHA256 signed requests, a Node.js client that signs requests and runs ten success and failure scenarios, the same signing code in Java, an HTTP Message Signatures (RFC 9421) demo with the `hmac-sha256` algorithm, and a check of the GitHub webhook test vector.

All keys in this folder are example values such as `demo-secret-key-2026-10`. Never use them for a real API.

## Versions

- Python 3.13, FastAPI 0.142.2 (Starlette 1.7.0), uvicorn 0.54.0, requests 2.34.2, http-message-signatures 2.0.1
- Node.js 22 (built-in `node:crypto` and `fetch`, no packages)
- JDK 21 (single-file `java Sign.java`, no dependencies)
- curl 8.5.0

## Files

| File | What it does |
|---|---|
| `signing.py` | Canonical request, HMAC-SHA256 signature and constant-time compare in Python |
| `server.py` | Orders API on port 9410: checks keyId, timestamp window (300 s), signature and nonce; `/buggy/orders` shows the re-serialized JSON bug |
| `client.mjs` | Node.js signer; `node client.mjs show` prints the fixed test signature, `node client.mjs` runs the scenarios |
| `compare.mjs` | Constant-time signature comparison for a Node.js server |
| `Sign.java` | The same canonical request and signature in Java |
| `rfc9421_demo.py` | RFC 9421 signature base, test case B.2.5, `Signature-Input` and `Signature` for an order, verification with the http-message-signatures library |
| `webhook_vector.py` | GitHub `X-Hub-Signature-256` test vector and raw vs re-serialized JSON bytes |
| `run_all.sh` | Runs everything and prints the output in `OUTPUTS.txt` |

## Run

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
python signing.py            # canonical request and signature in Python
node compare.mjs             # constant-time comparison in Node.js
node client.mjs show         # same values in Node.js
java Sign.java               # same values in Java

uvicorn server:app --port 9410   # terminal 1
node client.mjs                  # terminal 2: ten scenarios

python rfc9421_demo.py
python webhook_vector.py
```

The timestamps and nonces in your output differ from `OUTPUTS.txt` because the client uses the current time and random nonces. The fixed test values (`1791200000`, `n-0001`) always give signature `9140e96dca095dfa3f4f13b237c07bb7cb5b116fcbf7c52d69665d12c40d066f`.
