"""Payments API: accepts only tokens issued for "payments-api".

Run: uvicorn payments_api:app --port 8002
"""
import uuid

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from token_check import require_token

# Services that may charge a customer on the customer's behalf.
ALLOWED_ACTORS = {"orders-api"}

app = FastAPI(title="Payments API")


class Charge(BaseModel):
    order_id: str
    amount: float


@app.post("/charges", status_code=201)
def create_charge(charge: Charge, request: Request):
    claims = require_token(request, audience="payments-api", scope="payments:charge")
    # Access control uses the top-level claims and the current actor only
    # (RFC 8693, section 4.1). Nested act claims are history.
    actor = claims.get("act", {}).get("sub")
    if actor is not None and actor not in ALLOWED_ACTORS:
        raise HTTPException(403, f"{actor} may not charge customers")
    print(f"charge {charge.order_id}: customer={claims['sub']} acting_service={actor}",
          flush=True)
    return {"charge_id": "ch_" + uuid.uuid4().hex[:8], "order_id": charge.order_id,
            "amount": charge.amount, "customer": claims["sub"], "acting_service": actor}
