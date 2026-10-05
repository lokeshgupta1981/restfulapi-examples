"""Orders service: REST API (openapi.yaml) plus MQTT events (asyncapi.yaml)."""
import asyncio
import json
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal

import aiomqtt
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

BROKER_HOST = "localhost"
BROKER_PORT = 9211

orders = {}
mqtt = None


class OrderItem(BaseModel):
    sku: str
    quantity: int = Field(ge=1)
    unitPrice: str = Field(pattern=r"^[0-9]+\.[0-9]{2}$")


class NewOrder(BaseModel):
    customerId: str
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    items: list[OrderItem] = Field(min_length=1)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


async def send(topic, payload):
    await mqtt.publish(topic, json.dumps(payload), qos=1)
    print(f"[orders] sent {topic}", flush=True)


async def receive_payments():
    """Operation receivePaymentCompleted: payments/{orderId}/completed."""
    await mqtt.subscribe("payments/+/completed", qos=1)
    async for message in mqtt.messages:
        payment = json.loads(message.payload)
        order = orders.get(payment["orderId"])
        if order is None:
            continue
        order["status"] = "paid"
        await send(f"orders/{order['id']}/status", {
            "eventId": str(uuid.uuid4()),
            "occurredAt": now(),
            "orderId": order["id"],
            "status": "paid",
        })


@asynccontextmanager
async def lifespan(app):
    global mqtt
    async with aiomqtt.Client(BROKER_HOST, BROKER_PORT, identifier="orders-service") as client:
        mqtt = client
        task = asyncio.create_task(receive_payments())
        yield
        task.cancel()


app = FastAPI(title="Orders API", lifespan=lifespan)


@app.post("/orders", status_code=201)
async def create_order(new_order: NewOrder, response: Response):
    total = sum(Decimal(i.unitPrice) * i.quantity for i in new_order.items)
    order = {
        "id": "ord_" + secrets.token_hex(4),
        "customerId": new_order.customerId,
        "items": [i.model_dump() for i in new_order.items],
        "total": f"{total:.2f}",
        "currency": new_order.currency,
        "status": "pending",
        "createdAt": now(),
    }
    orders[order["id"]] = order
    # Operation sendOrderPlaced: orders/placed
    await send("orders/placed", {"eventId": str(uuid.uuid4()), "occurredAt": now(), "order": order})
    response.headers["Location"] = f"/orders/{order['id']}"
    return order


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")
    return orders[order_id]
