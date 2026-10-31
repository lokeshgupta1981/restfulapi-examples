"""The bookstore API (port 9600). It calls the inventory API for every book page and order.

Settings (environment variables):
  BREAKER=on|off        use the circuit breaker or call the inventory API directly (default on)
  FAILURE_THRESHOLD=5   consecutive failures that open the breaker
  OPEN_SECONDS=10       how long the breaker stays open before a trial call
  INVENTORY_TIMEOUT=2   seconds to wait for the inventory API
"""
import math
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from breaker import CircuitBreaker, CircuitOpenError

INVENTORY_URL = "http://127.0.0.1:9601"
USE_BREAKER = os.getenv("BREAKER", "on") == "on"
TIMEOUT = float(os.getenv("INVENTORY_TIMEOUT", "2"))

BOOKS = {1: "REST API Design Rulebook", 2: "Release It!", 3: "Designing Data-Intensive Applications"}


class InventoryError(Exception):
    """The inventory API answered with a 5xx status."""


breaker = CircuitBreaker(
    "inventory",
    failure_threshold=int(os.getenv("FAILURE_THRESHOLD", "5")),
    open_seconds=float(os.getenv("OPEN_SECONDS", "10")),
    # Only problems of the remote service count: timeouts, connection errors, 5xx.
    # A 404 for an unknown book is a normal answer and never trips the breaker.
    failure_exceptions=(httpx.TransportError, InventoryError),
)


@asynccontextmanager
async def lifespan(app):
    app.state.http = httpx.AsyncClient(base_url=INVENTORY_URL, timeout=TIMEOUT)
    print(f"store: breaker={'on' if USE_BREAKER else 'off'}, timeout={TIMEOUT:g} s", flush=True)
    yield
    await app.state.http.aclose()


app = FastAPI(lifespan=lifespan)


async def fetch_stock(book_id: int):
    response = await app.state.http.get(f"/stock/{book_id}")
    if response.status_code >= 500:
        raise InventoryError(f"inventory answered {response.status_code}")
    if response.status_code == 404:
        return None
    return response.json()["in_stock"]


async def get_stock(book_id: int):
    if USE_BREAKER:
        return await breaker.call(fetch_stock, book_id)
    return await fetch_stock(book_id)


@app.get("/books/{book_id}")
async def get_book(book_id: int):
    if book_id not in BOOKS:
        raise HTTPException(404, "unknown book")
    try:
        in_stock = await get_stock(book_id)
        return {"id": book_id, "title": BOOKS[book_id], "in_stock": in_stock}
    except (CircuitOpenError, httpx.TransportError, InventoryError) as error:
        # Fallback: the page still works, it just can't show the stock right now.
        return {"id": book_id, "title": BOOKS[book_id], "in_stock": None,
                "stock_note": "Stock information is temporarily unavailable",
                "reason": type(error).__name__}


@app.post("/orders")
async def create_order(book_id: int):
    try:
        in_stock = await get_stock(book_id)
    except CircuitOpenError as error:
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": str(math.ceil(error.retry_after))},
            media_type="application/problem+json",
            content={"type": "https://example.com/problems/inventory-unavailable",
                     "title": "Inventory service unavailable",
                     "status": 503,
                     "detail": "We can't check stock right now. Please try again shortly."})
    except (httpx.TransportError, InventoryError):
        return JSONResponse(status_code=503, media_type="application/problem+json",
                            content={"title": "Inventory service unavailable", "status": 503})
    if not in_stock:
        raise HTTPException(409, "out of stock")
    return JSONResponse(status_code=201, content={"order": "created", "book_id": book_id})


@app.get("/admin/breaker")
async def breaker_state():
    return breaker.snapshot()
