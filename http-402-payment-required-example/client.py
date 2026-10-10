"""Calls both forms of HTTP 402 and handles each status the way a client should."""

import base64
import json
import time
import urllib.error
import urllib.request

from demo_wallets import PRIVATE_KEYS

BASE = "http://127.0.0.1:8000"
KEY = {"Authorization": "Bearer key-basic"}
AGENT_BUDGET = 5000  # the most this client pays for one request, in atomic units


def call(method: str, path: str, headers: dict | None = None, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method,
                                     headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, dict(response.headers), json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), json.load(error)


def decode(header_value: str) -> dict:
    return json.loads(base64.b64decode(header_value))


print("== 1. Prepaid credits")
for attempt in range(1, 4):
    status, headers, body = call("GET", "/v1/reports/r-77", KEY)
    print(f"report call {attempt}: HTTP {status}", body if status == 200 else "")
print("problem:", json.dumps(body))
print("content-type:", headers.get("content-type"))
print("client action: do not retry, show the top-up link", body["top_up"])

status, _, body = call("POST", "/v1/credits", KEY, {"amount": 5})
print(f"top up: HTTP {status}", body)
status, _, body = call("GET", "/v1/reports/r-77", KEY)
print(f"report after top-up: HTTP {status}", body)

status, _, body = call("GET", "/v1/exports", KEY)
print(f"\nexports: HTTP {status} {body['title']}. client action: upgrade the plan, paying per call does not help")

for _ in range(10):
    status, headers, body = call("GET", "/v1/reports/r-77", KEY)
    if status == 429:
        print(f"burst: HTTP 429, Retry-After={headers.get('retry-after')}. client action: wait, then retry")
        break

print("\n== 2. x402 handshake (simulated payment rail)")
status, headers, body = call("GET", "/v1/premium/forecast")
required = decode(headers["payment-required"])
print(f"first call: HTTP {status}, body={body}")
print("PAYMENT-REQUIRED decoded:", json.dumps(required, indent=2))

offer = next(o for o in required["accepts"] if o["network"] == "demo:local" and o["scheme"] == "exact")
if int(offer["amount"]) > AGENT_BUDGET:
    raise SystemExit("price is above the budget, stop instead of paying")


def payment_header(wallet: str, nonce: str) -> str:
    now = int(time.time())
    authorization = {"from": wallet, "to": offer["payTo"], "value": offer["amount"],
                     "validAfter": str(now - 5), "validBefore": str(now + offer["maxTimeoutSeconds"]), "nonce": nonce}
    signature = PRIVATE_KEYS[wallet].sign(json.dumps(authorization, sort_keys=True).encode()).hex()
    payload = {"x402Version": 2, "resource": required["resource"], "accepted": offer,
               "payload": {"signature": signature, "authorization": authorization}}
    return base64.b64encode(json.dumps(payload).encode()).decode()


paid = payment_header("demo-buyer-wallet", "7f3a9c2e5b1d4f60a8e2")
status, headers, body = call("GET", "/v1/premium/forecast", {"PAYMENT-SIGNATURE": paid})
print(f"\npaid call: HTTP {status}, body={body}")
print("PAYMENT-RESPONSE decoded:", decode(headers["payment-response"]))

status, headers, _ = call("GET", "/v1/premium/forecast", {"PAYMENT-SIGNATURE": paid})
print(f"\nsame PAYMENT-SIGNATURE again: HTTP {status},", decode(headers["payment-response"]))

poor = payment_header("demo-poor-wallet", "1b8e6d0c4a2f9e7d5c3b")
status, headers, _ = call("GET", "/v1/premium/forecast", {"PAYMENT-SIGNATURE": poor})
print(f"wallet with 1000 units: HTTP {status},", decode(headers["payment-response"]))
