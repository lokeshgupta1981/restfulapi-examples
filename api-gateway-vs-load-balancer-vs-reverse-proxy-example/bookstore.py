"""A tiny bookstore service. Run several copies to see what each component in front of it does.

SERVICE=books  INSTANCE=books-1 uvicorn bookstore:app --port 9001
SERVICE=orders INSTANCE=orders-1 uvicorn bookstore:app --port 9004
"""
import os

from fastapi import FastAPI, HTTPException, Request

SERVICE = os.getenv("SERVICE", "books")
INSTANCE = os.getenv("INSTANCE", f"{SERVICE}-1")

BOOKS = {
    "1": {"id": "1", "title": "RESTful Web APIs", "price": 39.99},
    "2": {"id": "2", "title": "Designing Web APIs", "price": 44.50},
}
ORDERS = {"1042": {"id": "1042", "bookId": "1", "quantity": 2, "status": "SHIPPED"}}

app = FastAPI()


@app.middleware("http")
async def add_instance_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Instance"] = INSTANCE
    return response


@app.get("/health")
def health():
    return {"status": "UP", "instance": INSTANCE}


@app.get("/whoami")
def whoami(request: Request):
    """Shows what this service can see about the request it received."""
    return {
        "instance": INSTANCE,
        "path": request.url.path,
        "tcp_peer": request.client.host,
        "host": request.headers.get("host"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "x_forwarded_proto": request.headers.get("x-forwarded-proto"),
        "x_client_id": request.headers.get("x-client-id"),
        "x_api_key": request.headers.get("x-api-key"),
    }


if SERVICE == "books":

    @app.get("/books")
    def list_books():
        return list(BOOKS.values())

    @app.get("/books/{book_id}")
    def get_book(book_id: str):
        if book_id not in BOOKS:
            raise HTTPException(status_code=404, detail="Book not found")
        return BOOKS[book_id]

else:

    @app.get("/orders/{order_id}")
    def get_order(order_id: str):
        if order_id not in ORDERS:
            raise HTTPException(status_code=404, detail="Order not found")
        return ORDERS[order_id]
