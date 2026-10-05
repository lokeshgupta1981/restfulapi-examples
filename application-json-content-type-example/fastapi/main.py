from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class OrderIn(BaseModel):
    item: str
    quantity: int


@app.post("/orders", status_code=201)
def create_order(order: OrderIn):
    return {"id": 1001, "item": order.item, "quantity": order.quantity}
