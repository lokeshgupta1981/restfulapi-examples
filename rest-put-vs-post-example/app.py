"""Orders API that shows the difference between PUT and POST (RFC 9110, sections 9.3.3 and 9.3.4)."""
import json

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="Orders API")

orders = {}        # order id -> stored representation as bytes
versions = {}      # order id -> version number, used for the ETag
next_number = 1000
REQUIRED_FIELDS = ("customer", "items")


def problem(status, title, detail):
    """Error response in the Problem Details format (RFC 9457)."""
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def etag(order_id):
    return f'"v{versions[order_id]}"'


def matches(header_value, order_id, weak):
    """True when an If-Match (strong) or If-None-Match (weak) value matches the current order (RFC 9110, 13.1)."""
    if order_id not in orders:
        return False
    if header_value.strip() == "*":
        return True
    tags = [tag.strip() for tag in header_value.split(",")]
    if weak:
        tags = [tag.removeprefix("W/") for tag in tags]
    return etag(order_id) in tags


def stored(order_id, status_code=200, extra_headers=None):
    headers = {"ETag": etag(order_id), **(extra_headers or {})}
    return Response(orders[order_id], status_code=status_code, media_type="application/json", headers=headers)


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    if order_id not in orders:
        return problem(404, "Not Found", f"Order {order_id} does not exist.")
    return stored(order_id)


@app.post("/orders")
async def create_order(request: Request):
    """POST to the collection: the server picks the id, so every call creates a new order."""
    global next_number
    order = json.loads(await request.body())
    missing = [field for field in REQUIRED_FIELDS if field not in order]
    if missing:
        return problem(422, "Unprocessable Content", f"Missing fields: {', '.join(missing)}.")
    next_number += 1
    order_id = f"ord_{next_number}"
    orders[order_id] = json.dumps({"id": order_id, **order, "status": "new"}, separators=(",", ":")).encode()
    versions[order_id] = 1
    # The server built this representation itself, so the client learns its URI from Location.
    return Response(orders[order_id], status_code=201, media_type="application/json",
                    headers={"Location": f"/orders/{order_id}"})


@app.put("/orders/{order_id}")
async def put_order(order_id: str, request: Request):
    """PUT to one order: the client picks the id and sends the complete new state."""
    body = await request.body()
    if_match = request.headers.get("If-Match")
    if_none_match = request.headers.get("If-None-Match")
    if if_match is not None and not matches(if_match, order_id, weak=False):
        return problem(412, "Precondition Failed", "The order changed since the client read it.")
    if if_none_match is not None and matches(if_none_match, order_id, weak=True):
        detail = f"Order {order_id} already exists." if if_none_match.strip() == "*" else "The current ETag matches If-None-Match."
        return problem(412, "Precondition Failed", detail)
    order = json.loads(body)
    missing = [field for field in REQUIRED_FIELDS if field not in order]
    if missing:
        return problem(422, "Unprocessable Content", f"PUT needs the full order. Missing fields: {', '.join(missing)}.")

    if order_id not in orders:
        orders[order_id] = body           # stored byte for byte, so the ETag may be sent
        versions[order_id] = 1
        return stored(order_id, 201, {"Location": f"/orders/{order_id}"})
    if orders[order_id] != body:
        orders[order_id] = body           # replace: fields missing from the body are gone
        versions[order_id] += 1
    return stored(order_id, 200)


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str):
    """POST for an action that runs server logic instead of replacing the order."""
    if order_id not in orders:
        return problem(404, "Not Found", f"Order {order_id} does not exist.")
    order = json.loads(orders[order_id])
    if order.get("status") != "cancelled":
        order["status"] = "cancelled"     # a real API would also release stock and refund here
        orders[order_id] = json.dumps(order, separators=(",", ":")).encode()
        versions[order_id] += 1
    return stored(order_id, 200)


@app.delete("/orders/{order_id}")
def delete_order(order_id: str):
    if orders.pop(order_id, None) is None:
        return problem(404, "Not Found", f"Order {order_id} does not exist.")
    versions.pop(order_id)
    return Response(status_code=204)
