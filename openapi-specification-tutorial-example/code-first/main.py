"""Code-first: FastAPI builds the OpenAPI document from the Python code."""
import json
from typing import Literal

from fastapi import FastAPI, Header
from pydantic import BaseModel, Field

app = FastAPI(title="Orders API", version="1.0.0")


class OrderItem(BaseModel):
    sku: str
    quantity: int = Field(ge=1, le=99)


class NewOrder(BaseModel):
    currency: str = Field(pattern="^[A-Z]{3}$")
    items: list[OrderItem] = Field(min_length=1)


class Order(NewOrder):
    id: str
    status: Literal["pending", "paid", "shipped", "cancelled"]
    total: str


@app.post("/orders", status_code=201, tags=["orders"])
def create_order(order: NewOrder, idempotency_key: str = Header()) -> Order:
    return Order(id="ord_1002", status="pending", total="59.90", **order.model_dump())


@app.get("/orders/{order_id}", tags=["orders"])
def get_order(order_id: str) -> Order:
    return Order(id=order_id, status="pending", total="59.90", currency="USD",
                 items=[OrderItem(sku="BOOK-REST-101", quantity=2)])


if __name__ == "__main__":
    with open("generated-openapi.json", "w") as f:
        json.dump(app.openapi(), f, indent=2)
    spec = app.openapi()
    print("openapi:", spec["openapi"])
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            print(method.upper(), path, "operationId:", op["operationId"],
                  "responses:", ", ".join(op["responses"].keys()))
