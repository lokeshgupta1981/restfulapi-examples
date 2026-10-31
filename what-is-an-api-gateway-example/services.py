"""Two small backend services for the bookstore: books and orders.

Run them on separate ports, for example:
    SERVICE=books  uvicorn services:app --port 8001
    SERVICE=orders uvicorn services:app --port 8002
"""
import asyncio
import os

from fastapi import FastAPI, Header, HTTPException

SERVICE = os.environ.get("SERVICE", "books")
app = FastAPI(title=f"{SERVICE} service")

BOOKS = {
    "1": {"id": "1", "title": "RESTful Web APIs", "price": 39.99},
    "2": {"id": "2", "title": "Designing Web APIs", "price": 44.50},
}
ORDERS = {
    "1042": {"id": "1042", "client": "mobile-app", "bookId": "2", "quantity": 1},
}
calls = {"count": 0}  # how many requests reached this service


@app.middleware("http")
async def count_calls(request, call_next):
    if request.url.path.startswith(("/books", "/orders")):
        calls["count"] += 1
    return await call_next(request)


@app.get("/stats")
def stats():
    return {"service": SERVICE, "requestsReceived": calls["count"]}


if SERVICE == "books":

    @app.get("/books")
    def list_books():
        return list(BOOKS.values())

    @app.get("/books/{book_id}")
    def get_book(book_id: str):
        if book_id not in BOOKS:
            raise HTTPException(404, "book not found")
        return BOOKS[book_id]

    @app.get("/books/{book_id}/slow")
    async def slow_book(book_id: str):
        await asyncio.sleep(5)  # simulates a stuck dependency
        return BOOKS.get(book_id, {})

else:

    @app.get("/orders/{order_id}")
    def get_order(
        order_id: str,
        x_client_id: str | None = Header(default=None),
        x_request_id: str | None = Header(default=None),
        x_api_key: str | None = Header(default=None),
    ):
        if order_id not in ORDERS:
            raise HTTPException(404, "order not found")
        # Echo what the gateway passed on, so the demo can show it.
        return ORDERS[order_id] | {
            "seenByService": {
                "X-Client-Id": x_client_id,
                "X-Request-Id": x_request_id,
                "X-Api-Key": x_api_key,
            }
        }
