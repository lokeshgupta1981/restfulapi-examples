"""Orders API that uses UUIDv4, UUIDv7 or ULID as its order IDs.

ID_KIND=uuid7 (default), uuid4 or ulid. PORT defaults to 8000.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import uvicorn
from fastapi import Body, FastAPI, Response
from fastapi.responses import JSONResponse

from ids import created_at, new_id, parse_id
from store import OrderStore

ID_KIND = os.environ.get("ID_KIND", "uuid7")
MAX_CLOCK_SKEW = timedelta(minutes=1)

app = FastAPI()
store = OrderStore()


def problem(status: int, title: str, detail: str) -> JSONResponse:
    """An RFC 9457 problem details response."""
    return JSONResponse({"type": "about:blank", "title": title, "status": status, "detail": detail},
                        status_code=status, media_type="application/problem+json")


@app.post("/orders", status_code=201)
def create_order(response: Response, body: dict = Body(...)):
    """The server creates the ID."""
    order = store.insert(new_id(ID_KIND), body)
    response.headers["Location"] = f"/orders/{order['id']}"
    return order


@app.put("/orders/{order_id}")
def put_order(order_id: str, body: dict = Body(...)):
    """The client creates the ID. Repeating the same PUT is safe."""
    try:
        order_id = parse_id(ID_KIND, order_id)
    except ValueError as e:
        return problem(400, "Invalid order ID", f"'{order_id}' is not a valid {ID_KIND}: {e}")

    ts = created_at(order_id)
    if ts is not None and ts > datetime.now(timezone.utc) + MAX_CLOCK_SKEW:
        return problem(422, "Order ID from the future", f"The ID's timestamp {ts.isoformat()} is in the future.")

    existing = store.get(order_id)
    if existing is None:
        order = store.insert(order_id, body)
        return JSONResponse(order, status_code=201, headers={"Location": f"/orders/{order_id}"})
    same = {k: v for k, v in existing.items() if k not in ("id", "created_at")} == body
    if same:
        return existing                                   # a retry of the same request: 200
    return problem(409, "Order ID already used", f"Order {order_id} exists with a different body.")


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    try:
        order_id = parse_id(ID_KIND, order_id)            # also normalizes upper/lower case
    except ValueError:
        return problem(404, "Not Found", "No such order.")
    order = store.get(order_id)
    return order if order else problem(404, "Not Found", "No such order.")


@app.get("/orders")
def list_orders(limit: int = 3, after: str | None = None):
    items = store.page(after, limit)
    next_cursor = items[-1]["id"] if len(items) == limit else None
    return {"items": items, "next_cursor": next_cursor}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")), log_level="warning")
