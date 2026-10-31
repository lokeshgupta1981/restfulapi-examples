"""Orders API: takes the user's token and calls the Payments API.

The query parameter "forward" picks how it gets a token for the Payments API:
  user-token   forwards the user's own token (fails: wrong audience)
  impersonate  token exchange without an actor_token (no act claim)
  delegate     token exchange with an actor_token (act claim), the default

Run: uvicorn orders_api:app --port 8001
"""
import hashlib
import os
import time
import uuid

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from token_check import require_token

AUTH_URL = os.environ.get("AUTH_URL", "http://127.0.0.1:8000")
PAYMENTS_URL = os.environ.get("PAYMENTS_URL", "http://127.0.0.1:8002")
CLIENT = ("orders-api", "demo-secret-orders-api")  # fake demo secret
ACCESS_TOKEN = "urn:ietf:params:oauth:token-type:access_token"

http = httpx.Client(timeout=5)
# Exchanged tokens, reused until 30 seconds before they expire.
CACHE = {}

app = FastAPI(title="Orders API")


class Order(BaseModel):
    book_id: str
    amount: float


def own_token():
    """The Orders API's own token (client credentials), used as actor_token."""
    entry = CACHE.get("self")
    if entry and entry["expires_at"] > time.time() + 30:
        return entry["token"]
    body = http.post(AUTH_URL + "/token", auth=CLIENT,
                     data={"grant_type": "client_credentials"}).json()
    CACHE["self"] = {"token": body["access_token"],
                     "expires_at": time.time() + body["expires_in"]}
    return body["access_token"]


def exchange(user_token, delegate):
    key = (hashlib.sha256(user_token.encode()).hexdigest(), delegate)
    entry = CACHE.get(key)
    if entry and entry["expires_at"] > time.time() + 30:
        return entry["token"], "cached"
    form = {"grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": user_token,
            "subject_token_type": ACCESS_TOKEN,
            "audience": "payments-api",
            "scope": "payments:charge"}
    if delegate:
        form["actor_token"] = own_token()
        form["actor_token_type"] = ACCESS_TOKEN
    response = http.post(AUTH_URL + "/token", auth=CLIENT, data=form)
    if response.status_code != 200:
        raise HTTPException(502, f"token exchange failed: {response.text}")
    body = response.json()
    CACHE[key] = {"token": body["access_token"],
                  "expires_at": time.time() + body["expires_in"]}
    return body["access_token"], "new"


@app.post("/orders", status_code=201)
def place_order(order: Order, request: Request, forward: str = "delegate"):
    claims = require_token(request, audience="orders-api", scope="orders:write")
    user_token = request.headers["authorization"][7:]
    order_id = "ord_" + uuid.uuid4().hex[:8]

    if forward == "user-token":
        token, how = user_token, "forwarded"
    else:
        token, how = exchange(user_token, delegate=(forward == "delegate"))

    payment = http.post(PAYMENTS_URL + "/charges", json={"order_id": order_id,
                        "amount": order.amount},
                        headers={"Authorization": "Bearer " + token})
    if payment.status_code != 201:
        return JSONResponse({"order_id": order_id, "status": "payment_failed",
                             "payments_status": payment.status_code,
                             "payments_error": payment.json()["detail"]}, status_code=502)
    return {"order_id": order_id, "customer": claims["sub"], "status": "paid",
            "payment_token": how, "payment": payment.json()}
