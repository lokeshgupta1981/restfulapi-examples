"""Backend for Frontend of the mobile app.

One endpoint per mobile screen. It forwards the app's own access token, calls
the general-purpose services, runs independent calls in parallel, and returns
only the fields the order screen shows.

    uvicorn mobile_bff:app --port 8004
    FANOUT=sequential uvicorn mobile_bff:app --port 8004   # for the benchmark
"""
import asyncio
import os

import httpx
from fastapi import FastAPI, Header, HTTPException

import settings

app = FastAPI(title="mobile-bff")
SEQUENTIAL = os.getenv("FANOUT", "parallel") == "sequential"
client = httpx.AsyncClient(timeout=httpx.Timeout(1.0))  # one shared connection pool


async def fetch(url: str, token: str | None = None) -> dict:
    headers = {"Authorization": token} if token else {}
    r = await client.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


@app.get("/mobile/v1/order-screen/{order_id}")
async def order_screen(order_id: str, authorization: str | None = Header(None)):
    # 1. The order comes first: we need its book IDs and shipment ID.
    try:
        order = await fetch(f"{settings.ORDERS_URL}/orders/{order_id}", authorization)
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, e.response.json()["detail"])
    except httpx.HTTPError:
        raise HTTPException(502, "orders service unavailable")

    # 2. Books and shipment do not depend on each other: fetch them together.
    calls = [fetch(f"{settings.CATALOG_URL}/books/{line['bookId']}") for line in order["lines"]]
    calls.append(fetch(f"{settings.SHIPPING_URL}/shipments/{order['shipmentId']}", authorization))
    if SEQUENTIAL:
        results = []
        for c in calls:
            try:
                results.append(await c)
            except Exception as e:  # keep the same error handling as gather()
                results.append(e)
    else:
        results = await asyncio.gather(*calls, return_exceptions=True)
    *books, shipment = results

    # 3. Shape the response for the small screen.
    items = []
    for line, book in zip(order["lines"], books):
        ok = not isinstance(book, Exception)
        items.append({"title": book["title"] if ok else "Unknown book",
                      "thumbnail": book["images"]["thumb"] if ok else None,
                      "quantity": line["quantity"]})

    screen = {"orderId": order["id"], "status": order["status"],
              "total": f"{order['total']} {order['currency']}", "items": items}
    if isinstance(shipment, Exception):
        # Shipping is nice to have on this screen: degrade instead of failing.
        screen["delivery"] = None
        screen["warnings"] = ["Delivery details are unavailable right now."]
    else:
        screen["delivery"] = {"carrier": shipment["carrier"],
                              "eta": shipment["estimatedDelivery"],
                              "lastEvent": shipment["events"][-1]["what"]}
    return screen
