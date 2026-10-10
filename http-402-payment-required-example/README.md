Source code for the article [HTTP 402 Payment Required and the x402 Protocol](https://restfulapi.net/http-status-402-payment-required/)

# HTTP 402 Payment Required example

Two forms of HTTP 402 in one FastAPI app.

- `server.py` (port 8000) sells reports for prepaid credits. It returns HTTP 402 with a Problem Details body (RFC 9457) when the balance is 0, HTTP 403 for a feature outside the plan, and HTTP 429 with `Retry-After` for a burst. The endpoint `/v1/premium/forecast` runs an x402 version 2 handshake with the `PAYMENT-REQUIRED`, `PAYMENT-SIGNATURE` and `PAYMENT-RESPONSE` headers.
- `facilitator.py` (port 8001) is a demo facilitator with `/verify` and `/settle`.
- `demo_wallets.py` holds two demo wallets with fixed Ed25519 keys.
- `client.py` calls every case and prints what a client does next.

The x402 part uses a simulated payment rail: the network `demo:local`, the asset `DEMO-USD` and Ed25519 signatures stand in for a blockchain, so no money moves. For real payments, use an x402 SDK and a hosted facilitator (see docs.x402.org).

## Versions

Python 3.13, FastAPI 0.143.0, Uvicorn 0.54.0, cryptography 50.0.2.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: run the script in Git Bash or WSL
pip install -r requirements.txt
./run_demo.sh
```

`OUTPUTS.txt` holds the output of a real run.
