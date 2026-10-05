"""A small Orders REST API used as the target of the tool calls."""
import math
import time

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Orders API", version="1.0.0")

ORDERS = {
    1001: {"id": 1001, "customer": "Alice", "status": "shipped", "total": "59.90", "currency": "EUR"},
    1002: {"id": 1002, "customer": "Bob", "status": "processing", "total": "120.00", "currency": "EUR"},
    1003: {"id": 1003, "customer": "Alice", "status": "delivered", "total": "15.50", "currency": "EUR"},
    1004: {"id": 1004, "customer": "Carol", "status": "processing", "total": "42.00", "currency": "EUR"},
    1005: {"id": 1005, "customer": "Dan", "status": "processing", "total": "18.00", "currency": "EUR"},
}

SHIPMENTS = {
    1001: {"order_id": 1001, "carrier": "DHL", "tracking_number": "JD014600006281", "eta": "2026-10-07"},
    1002: {"order_id": 1002, "carrier": None, "tracking_number": None, "eta": None},
    1003: {"order_id": 1003, "carrier": "UPS", "tracking_number": "1Z999AA10123456784", "eta": "2026-10-01"},
    1004: {"order_id": 1004, "carrier": None, "tracking_number": None, "eta": None},
    1005: {"order_id": 1005, "carrier": None, "tracking_number": None, "eta": None},
}

# Demo rate limit for the shipment endpoint: 2 lookups per 30 seconds.
SHIPMENT_LIMIT = 2
SHIPMENT_WINDOW_SECONDS = 30
shipment_calls: list[float] = []

# Demo of a lost response: the first cancel of these orders is applied, but the
# response comes back after 6 seconds, later than the client's 5 second timeout.
SLOW_FIRST_CANCEL = {1005}

# Idempotency-Key value -> (status code, body) of the first cancel request.
idempotency_store: dict[str, tuple[int, dict]] = {}


class CancelRequest(BaseModel):
    reason: str = Field(description="Why the customer wants to cancel", max_length=200)


def problem(status: int, title: str, detail: str, headers: dict | None = None) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return JSONResponse(body, status_code=status, headers=headers,
                        media_type="application/problem+json")


@app.get("/orders/{order_id}", operation_id="getOrder",
         summary="Get one order by its numeric ID")
def get_order(order_id: int):
    order = ORDERS.get(order_id)
    if order is None:
        return problem(404, "Not Found", f"Order {order_id} does not exist.")
    return order


@app.get("/orders/{order_id}/shipment", operation_id="getShipment",
         summary="Get the carrier, tracking number and ETA of an order")
def get_shipment(order_id: int):
    now = time.time()
    while shipment_calls and now - shipment_calls[0] >= SHIPMENT_WINDOW_SECONDS:
        shipment_calls.pop(0)
    if len(shipment_calls) >= SHIPMENT_LIMIT:
        retry_after = math.ceil(SHIPMENT_WINDOW_SECONDS - (now - shipment_calls[0]))
        return problem(429, "Too Many Requests",
                       f"Shipment lookups are limited to {SHIPMENT_LIMIT} per {SHIPMENT_WINDOW_SECONDS} seconds.",
                       headers={"Retry-After": str(retry_after)})
    shipment_calls.append(now)
    shipment = SHIPMENTS.get(order_id)
    if shipment is None:
        return problem(404, "Not Found", f"Order {order_id} does not exist.")
    return shipment


@app.post("/orders/{order_id}/cancel", operation_id="cancelOrder",
          summary="Cancel an order that has not shipped yet")
def cancel_order(order_id: int, body: CancelRequest,
                 idempotency_key: str | None = Header(default=None)):
    if idempotency_key is None:
        return problem(400, "Bad Request", "The Idempotency-Key header is required.")
    if idempotency_key in idempotency_store:
        status, saved = idempotency_store[idempotency_key]
        return JSONResponse(saved, status_code=status, headers={"Idempotent-Replayed": "true"})

    order = ORDERS.get(order_id)
    if order is None:
        return problem(404, "Not Found", f"Order {order_id} does not exist.")
    if order["status"] != "processing":
        return problem(409, "Conflict",
                       f"Order {order_id} is {order['status']} and can no longer be cancelled.")
    order["status"] = "cancelled"
    result = {"id": order_id, "status": "cancelled", "reason": body.reason}
    idempotency_store[idempotency_key] = (200, result)
    if order_id in SLOW_FIRST_CANCEL:
        SLOW_FIRST_CANCEL.discard(order_id)
        time.sleep (6)
    return result
