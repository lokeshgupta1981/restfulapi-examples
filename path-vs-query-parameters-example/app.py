"""Orders and Products API that shows path parameters and query parameters side by side."""

from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Path, Query, Response
from pydantic import BaseModel, Field

app = FastAPI(title="Orders and Products API")

Status = Literal["pending", "paid", "shipped", "cancelled"]
SortKey = Literal["created", "-created", "total", "-total"]
Currency = Literal["USD", "EUR", "INR"]

RATES = {"USD": 1.0, "EUR": 0.86, "INR": 88.7}

PRODUCTS = {
    "KB-101": {"sku": "KB-101", "name": "C++ Primer", "category": "books", "price_usd": 49.0},
    "KB-102": {"sku": "KB-102", "name": "Rust in Action", "category": "books", "price_usd": 39.0},
    "HW-201": {"sku": "HW-201", "name": "USB-C Hub", "category": "hardware", "price_usd": 25.0},
    "HW-202": {"sku": "HW-202", "name": "AT&T Modem", "category": "hardware", "price_usd": 80.0},
}

CUSTOMERS = {7: {"id": 7, "name": "Asha"}, 8: {"id": 8, "name": "Ben"}, 9: {"id": 9, "name": "Chen"}}

ORDERS = [
    {"id": 1001, "customer_id": 7, "status": "paid", "total": 49.0, "created": "2026-10-01",
     "items": [{"sku": "KB-101", "qty": 1}]},
    {"id": 1002, "customer_id": 8, "status": "shipped", "total": 64.0, "created": "2026-10-02",
     "items": [{"sku": "KB-102", "qty": 1}, {"sku": "HW-201", "qty": 1}]},
    {"id": 1003, "customer_id": 7, "status": "pending", "total": 80.0, "created": "2026-10-03",
     "items": [{"sku": "HW-202", "qty": 1}]},
    {"id": 1004, "customer_id": 8, "status": "paid", "total": 25.0, "created": "2026-10-04",
     "items": [{"sku": "HW-201", "qty": 1}]},
]


def summary(order: dict) -> dict:
    """Return an order without its line items."""
    return {key: value for key, value in order.items() if key != "items"}


def sort_orders(orders: list[dict], sort: str) -> list[dict]:
    field = sort.lstrip("-")
    return sorted(orders, key=lambda order: order[field], reverse=sort.startswith("-"))


# Collection: every parameter is optional and shapes the same /orders resource.
@app.get("/orders")
def list_orders(
    status: Annotated[list[Status] | None, Query()] = None,
    sort: SortKey = "-created",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    matches = [order for order in ORDERS if status is None or order["status"] in status]
    page = sort_orders(matches, sort)[offset:offset + limit]
    return {"status": status, "sort": sort, "limit": limit, "offset": offset,
            "data": [summary(order) for order in page]}


# One resource: the path identifies it, the query only changes what we get back.
@app.get("/orders/{order_id}")
def get_order(
    order_id: Annotated[int, Path(ge=1)],
    include_items: bool = False,
):
    for order in ORDERS:
        if order["id"] == order_id:
            return order if include_items else summary(order)
    raise HTTPException(status_code=404, detail=f"Order {order_id} not found")


# Sub-collection: the customer id is part of the identity of the list.
@app.get("/customers/{customer_id}/orders")
def list_customer_orders(customer_id: Annotated[int, Path(ge=1)]):
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    orders = [summary(order) for order in ORDERS if order["customer_id"] == customer_id]
    return {"customer_id": customer_id, "data": orders}


# Search on the collection: q is echoed back so we can see how the server decoded it.
@app.get("/products")
def list_products(
    response: Response,
    q: Annotated[str | None, Query(max_length=50)] = None,
    category: Literal["books", "hardware"] | None = None,
):
    response.headers["Cache-Control"] = "public, max-age=60"
    matches = [
        product for product in PRODUCTS.values()
        if (q is None or q.lower() in product["name"].lower())
        and (category is None or product["category"] == category)
    ]
    return {"q": q, "category": category, "data": matches}


@app.get("/products/{sku}")
def get_product(sku: str):
    product = PRODUCTS.get(sku)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {sku!r} not found")
    return product


# A required query parameter: the price has no meaning without a currency.
@app.get("/products/{sku}/price")
def get_price(sku: str, currency: Currency):
    product = PRODUCTS.get(sku)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {sku!r} not found")
    amount = round(product["price_usd"] * RATES[currency], 2)
    return {"sku": sku, "currency": currency, "amount": amount}


class OrderQuery(BaseModel):
    status: list[Status] = Field(default_factory=list)
    customer_ids: list[int] = Field(default_factory=list, max_length=500)
    sort: SortKey = "-created"
    limit: int = Field(default=20, ge=1, le=100)


# HTTP QUERY (RFC 10008): the same search as GET /orders, with the input in the body.
@app.api_route("/orders", methods=["QUERY"])
def query_orders(body: OrderQuery):
    matches = [
        order for order in ORDERS
        if (not body.status or order["status"] in body.status)
        and (not body.customer_ids or order["customer_id"] in body.customer_ids)
    ]
    page = sort_orders(matches, body.sort)[:body.limit]
    return {"data": [summary(order) for order in page]}
