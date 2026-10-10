"""HTTP 402 in two forms, on http://127.0.0.1:8000.

1. A prepaid-credit API (our own design, no protocol):
   GET /v1/reports/{id}      costs 1 credit, HTTP 402 with Problem Details when the balance is 0
   POST /v1/credits          adds credits (stands in for a real payment page)
   GET /v1/exports           not in the "basic" plan, HTTP 403 (paying per call does not help)
   Rate limit: 10 requests per 10 seconds per key, HTTP 429 with Retry-After

2. An x402 v2 handshake simulation:
   GET /v1/premium/forecast  HTTP 402 with a PAYMENT-REQUIRED header until the request carries a
                             valid PAYMENT-SIGNATURE header, then HTTP 200 with PAYMENT-RESPONSE.
   The server calls the facilitator in facilitator.py (/verify, /settle). The network "demo:local",
   the asset "DEMO-USD" and the Ed25519 signatures are stand-ins for a real blockchain payment.

Run: uvicorn server:app --host 127.0.0.1 --port 8000   (and facilitator.py on port 8001)
"""

import base64
import json
import math
import time
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()
FACILITATOR = "http://127.0.0.1:8001"
ACCOUNTS = {"key-basic": {"plan": "basic", "credits": 2}}  # demo key, a real API stores hashed keys
WINDOW_SECONDS, WINDOW_REQUESTS = 10, 10
windows: dict[str, tuple[float, int]] = {}


def problem(status: int, problem_type: str, title: str, detail: str, headers: dict | None = None, **extra):
    body = {"type": f"https://api.example.com/problems/{problem_type}", "title": title, "status": status,
            "detail": detail, **extra}
    return JSONResponse(body, status_code=status, headers=headers, media_type="application/problem+json")


def account_for(request: Request):
    key = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if key not in ACCOUNTS:
        return None, problem(401, "invalid-key", "Invalid API key", "Send a valid key in the Authorization header.",
                             headers={"WWW-Authenticate": 'Bearer realm="reports"'})
    now = time.time()
    start, used = windows.get(key, (now, 0))
    if now - start >= WINDOW_SECONDS:
        start, used = now, 0
    if used >= WINDOW_REQUESTS:
        retry_after = math.ceil(WINDOW_SECONDS - (now - start))
        return None, problem(429, "rate-limited", "Too many requests",
                             f"Wait {retry_after} seconds before the next request.",
                             headers={"Retry-After": str(retry_after)})
    windows[key] = (start, used + 1)
    return ACCOUNTS[key], None


# ------------------------------------------------------------ 1. prepaid credits

@app.get("/v1/reports/{report_id}")
async def get_report(report_id: str, request: Request):
    account, failure = account_for(request)
    if failure:
        return failure
    if account["credits"] < 1:
        return problem(402, "out-of-credit", "Not enough credit",
                       "This report costs 1 credit and the balance is 0.",
                       balance=0, cost=1, top_up="https://api.example.com/v1/credits")
    account["credits"] -= 1
    return {"report": report_id, "rows": 42, "credits_left": account["credits"]}


@app.post("/v1/credits")
async def add_credits(request: Request):
    account, failure = account_for(request)
    if failure:
        return failure
    account["credits"] += (await request.json())["amount"]
    return {"credits": account["credits"]}


@app.get("/v1/exports")
async def exports(request: Request):
    account, failure = account_for(request)
    if failure:
        return failure
    return problem(403, "plan-feature", "Not included in your plan",
                   f"Exports need the business plan, the current plan is {account['plan']}.")


# ------------------------------------------------------------ 2. x402 handshake (simulated rail)

PRICE = {"scheme": "exact", "network": "demo:local", "amount": "2500", "asset": "DEMO-USD",
         "payTo": "demo-seller-wallet", "maxTimeoutSeconds": 60, "extra": {"decimals": 6}}
RESOURCE = {"url": "http://127.0.0.1:8000/v1/premium/forecast", "description": "7-day forecast",
            "mimeType": "application/json"}


def b64json(value: dict) -> str:
    return base64.b64encode(json.dumps(value).encode()).decode()


def facilitator(path: str, body: dict) -> dict:
    request = urllib.request.Request(FACILITATOR + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


@app.get("/v1/premium/forecast")
async def forecast(request: Request):
    header = request.headers.get("PAYMENT-SIGNATURE")
    if header is None:
        required = {"x402Version": 2, "error": "PAYMENT-SIGNATURE header is required",
                    "resource": RESOURCE, "accepts": [PRICE]}
        return JSONResponse({}, status_code=402, headers={"PAYMENT-REQUIRED": b64json(required)})
    try:
        payload = json.loads(base64.b64decode(header))
    except ValueError:
        return JSONResponse({"error": "PAYMENT-SIGNATURE is not Base64-encoded JSON"}, status_code=400)

    check = {"paymentPayload": payload, "paymentRequirements": PRICE}
    verified = facilitator("/verify", check)
    if not verified["isValid"]:
        settlement = {"success": False, "errorReason": verified["invalidReason"], "transaction": "",
                      "network": PRICE["network"], "payer": verified.get("payer")}
        return JSONResponse({}, status_code=402, headers={"PAYMENT-RESPONSE": b64json(settlement)})

    result = {"city": "Lisbon", "days": [21, 22, 22, 20, 19, 21, 23]}  # the paid work
    settlement = facilitator("/settle", check)
    if not settlement["success"]:
        return JSONResponse({}, status_code=402, headers={"PAYMENT-RESPONSE": b64json(settlement)})
    return JSONResponse(result, headers={"PAYMENT-RESPONSE": b64json(settlement)})
