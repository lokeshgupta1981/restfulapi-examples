"""A small REST API for orders. Run: uvicorn orders_api:app --port 8080"""
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="Orders API", version="1.0.0")


class Order(BaseModel):
    id: str
    customer: str
    status: str
    total: float


ORDERS = {
    "ord_1001": Order(id="ord_1001", customer="Asha", status="shipped", total=59.90),
    "ord_1002": Order(id="ord_1002", customer="Ben", status="pending", total=120.00),
    "ord_1003": Order(id="ord_1003", customer="Asha", status="pending", total=18.50),
}


@app.get("/orders", response_model=list[Order])
def list_orders(status: str | None = Query(None), customer: str | None = Query(None)):
    result = list(ORDERS.values())
    if status:
        result = [o for o in result if o.status == status]
    if customer:
        result = [o for o in result if o.customer.lower() == customer.lower()]
    return result


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    if order_id not in ORDERS:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return ORDERS[order_id]


@app.post("/orders/{order_id}/cancel", response_model=Order)
def cancel_order(order_id: str):
    order = get_order(order_id)
    if order.status != "pending":
        raise HTTPException(status_code=409, detail=f"Only pending orders can be cancelled; {order_id} is {order.status}")
    order.status = "cancelled"
    return order
