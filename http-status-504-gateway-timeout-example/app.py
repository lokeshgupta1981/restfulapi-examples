"""A small orders API with slow endpoints, so nginx returns HTTP 504."""
import asyncio
import logging
import time
import uuid

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse, StreamingResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s app %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("orders")

app = FastAPI(title="Orders API")
ORDERS = {}

# The app answers before nginx gives up: proxy_read_timeout is 3 s, this budget is 2 s.
INVENTORY_BUDGET_SECONDS = 2.0


@app.get("/reports/sales")
async def sales_report(seconds: float = 1.0):
    started = time.monotonic()
    await asyncio.sleep (seconds)  # stands in for a slow database query
    log.info("sales report finished after %.1f s", time.monotonic() - started)
    return {"report": "sales", "rows": 42}


@app.post("/orders", status_code=201)
async def create_order(seconds: float = 0.0):
    order_id = str(uuid.uuid4())[:8]
    ORDERS[order_id] = {"id": order_id, "status": "CREATED"}
    log.info("order %s saved", order_id)
    await asyncio.sleep (seconds)  # stands in for a slow payment provider call
    log.info("order %s response ready", order_id)
    return ORDERS[order_id]


@app.get("/orders")
async def list_orders():
    return {"count": len(ORDERS), "orders": list(ORDERS.values())}


@app.get("/reports/yearly")
async def yearly_report():
    await asyncio.sleep (5)  # known slow endpoint, nginx gives it a longer proxy_read_timeout
    return {"report": "yearly", "rows": 365}


EXPORTS = {}
BACKGROUND_TASKS = set()


async def run_export(export_id):
    await asyncio.sleep (6)  # stands in for a slow export job
    EXPORTS[export_id]["status"] = "DONE"


@app.post("/exports", status_code=202)
async def start_export(response: Response):
    export_id = str(uuid.uuid4())[:8]
    EXPORTS[export_id] = {"id": export_id, "status": "RUNNING"}
    task = asyncio.create_task(run_export(export_id))
    BACKGROUND_TASKS.add(task)
    task.add_done_callback(BACKGROUND_TASKS.discard)
    response.headers["Location"] = f"/exports/{export_id}"
    return EXPORTS[export_id]


@app.get("/exports/{export_id}")
async def export_status(export_id: str):
    return EXPORTS[export_id]


@app.get("/reports/export")
async def export_report():
    # Sends one line every 2 seconds: nginx resets proxy_read_timeout after each read.
    async def lines():
        for row in range(4):
            await asyncio.sleep (2)
            yield f'{{"row": {row}}}\n'.encode()

    return StreamingResponse(lines(), media_type="application/x-ndjson")


async def slow_inventory_query():
    await asyncio.sleep (10)
    return {"sku": "A-100", "available": 7}


@app.get("/inventory")
async def inventory():
    try:
        return await asyncio.wait_for(slow_inventory_query(), timeout=INVENTORY_BUDGET_SECONDS)
    except asyncio.TimeoutError:
        log.info("inventory query cancelled after %.1f s", INVENTORY_BUDGET_SECONDS)
        return JSONResponse(
            status_code=503,
            media_type="application/problem+json",
            headers={"Retry-After": "10"},
            content={
                "type": "https://example.com/problems/inventory-slow",
                "title": "Service Unavailable",
                "status": 503,
                "detail": "The inventory database did not answer within 2 seconds.",
            },
        )
