"""Bookstore Orders API with object level authorization on every route."""
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from store import current_caller, new_db, order_json

app = FastAPI(title="Orders API (secure)")
db = new_db()


class NewOrder(BaseModel):
    book: str
    total: float
    address_id: int


class OrderChange(BaseModel):
    address_id: int


def can(caller, action, order):
    """The policy: owners may do anything with their order, support staff may only read."""
    if order["customer_id"] == caller["customer_id"]:
        return True
    return caller["role"] == "support" and action == "read"


def load_order(order_id, caller, action):
    row = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None or not can(caller, action, row):
        # Same answer for "does not exist" and "not yours"
        raise HTTPException(404, "Order not found")
    return row


def own_address(address_id, caller):
    row = db.execute("SELECT id FROM addresses WHERE id = ? AND customer_id = ?",
                     (address_id, caller["customer_id"])).fetchone()
    if row is None:
        raise HTTPException(422, "Unknown address_id")
    return row["id"]


@app.get("/orders")
def list_orders(caller=Depends(current_caller)):
    rows = db.execute("SELECT * FROM orders WHERE customer_id = ?",
                      (caller["customer_id"],)).fetchall()
    return [order_json(db, r) for r in rows]


@app.get("/orders/{order_id}")
def get_order(order_id: int, caller=Depends(current_caller)):
    return order_json(db, load_order(order_id, caller, "read"))


@app.patch("/orders/{order_id}")
def change_address(order_id: int, change: OrderChange, caller=Depends(current_caller)):
    order = load_order(order_id, caller, "update")
    address_id = own_address(change.address_id, caller)
    db.execute("UPDATE orders SET address_id = ? WHERE id = ?", (address_id, order["id"]))
    return order_json(db, load_order(order_id, caller, "read"))


@app.delete("/orders/{order_id}", status_code=204)
def cancel_order(order_id: int, caller=Depends(current_caller)):
    order = load_order(order_id, caller, "cancel")
    db.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order["id"],))


@app.post("/orders", status_code=201)
def create_order(order: NewOrder, caller=Depends(current_caller)):
    address_id = own_address(order.address_id, caller)
    cur = db.execute("INSERT INTO orders (customer_id, book, total, address_id, status) "
                     "VALUES (?, ?, ?, ?, 'paid')",
                     (caller["customer_id"], order.book, order.total, address_id))
    return order_json(db, load_order(cur.lastrowid, caller, "read"))


@app.get("/books/{isbn}/reviews")
def reviews(isbn: str):
    rows = db.execute("SELECT * FROM reviews WHERE isbn = ?", (isbn,)).fetchall()
    return [dict(r) for r in rows]
