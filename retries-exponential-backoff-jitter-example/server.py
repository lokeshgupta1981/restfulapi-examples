"""A small orders API that fails on purpose, so we can watch a client retry.

Run: uvicorn server:app --port 8000
"""
import asyncio
import itertools

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Flaky orders API")

failures_left: dict[int, int] = {}          # order id -> 503 responses still to send
rate_limited: set[str] = set()              # report names that already sent one 429
orders: dict[int, dict] = {}                # created orders
by_key: dict[str, asyncio.Task] = {}        # Idempotency-Key -> task that creates the order
next_id = itertools.count(5001)


def problem(status: int, title: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"title": title, "status": status}, status_code=status,
                        headers=headers, media_type="application/problem+json")


@app.get("/orders/{order_id}")
async def get_order(order_id: int, fail: int = 0):
    """Answers 503 for the first `fail` calls for this order id, then 200."""
    if order_id >= 9000:
        return problem(404, "Order not found")
    left = failures_left.setdefault(order_id, fail)
    if left > 0:
        failures_left[order_id] = left - 1
        return problem(503, "Service Unavailable")
    return {"id": order_id, "status": "SHIPPED", "total": 42.5}


@app.get("/reports/{name}")
async def get_report(name: str, retry_after: str = "2"):
    """Answers 429 with a Retry-After header the first time, then 200."""
    if name not in rate_limited:
        rate_limited.add(name)
        return problem(429, "Too Many Requests", {"Retry-After": retry_after})
    return {"report": name, "rows": 42}


@app.post("/orders", status_code=201)
async def create_order(request: Request, idempotency_key: str | None = Header(default=None),
                       slow: float = 0):
    """Creates an order. The first call can be slow (`slow` seconds) to force a client timeout.
    With an Idempotency-Key, a retry gets the same order instead of a new one."""
    body = await request.json()

    async def create() -> dict:
        await asyncio.sleep(slow)
        order = {"id": next(next_id), **body}
        orders[order["id"]] = order
        return order

    if idempotency_key is None:
        return await create()
    if idempotency_key in by_key:                      # a retry: wait for the first call, replay it
        order = await asyncio.shield(by_key[idempotency_key])
        return JSONResponse(order, status_code=201, headers={"Idempotent-Replayed": "true"})
    by_key[idempotency_key] = asyncio.ensure_future(create())   # keeps running if the client leaves
    return await asyncio.shield(by_key[idempotency_key])


@app.get("/orders")
async def list_orders():
    return list(orders.values())
