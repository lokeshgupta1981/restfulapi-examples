"""Bookstore Orders API WITH the BOLA bug. Every route authenticates, none checks ownership."""
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from store import current_caller, new_db, order_json

app = FastAPI(title="Orders API (vulnerable)")
db = new_db()


class NewOrder(BaseModel):
    book: str
    total: float
    address_id: int


class OrderChange(BaseModel):
    address_id: int


@app.get("/orders")
def list_orders(customer_id: int | None = None, caller=Depends(current_caller)):
    # BUG: trusts a customer_id from the query string
    cid = customer_id or caller["customer_id"]
    rows = db.execute("SELECT * FROM orders WHERE customer_id = ?", (cid,)).fetchall()
    return [order_json(db, r) for r in rows]


@app.get("/orders/{order_id}")
def get_order(order_id: int, caller=Depends(current_caller)):
    # BUG: loads the order by ID alone
    row = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Order not found")
    return order_json(db, row)


@app.patch("/orders/{order_id}")
def change_address(order_id: int, change: OrderChange, caller=Depends(current_caller)):
    # BUG: neither the order nor the address is checked
    cur = db.execute("UPDATE orders SET address_id = ? WHERE id = ?", (change.address_id, order_id))
    if cur.rowcount == 0:
        raise HTTPException(404, "Order not found")
    return order_json(db, db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone())


@app.delete("/orders/{order_id}", status_code=204)
def cancel_order(order_id: int, caller=Depends(current_caller)):
    # BUG: anyone with a token can cancel any order
    cur = db.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Order not found")


@app.post("/orders", status_code=201)
def create_order(order: NewOrder, caller=Depends(current_caller)):
    # BUG: the address ID in the body is not checked
    cur = db.execute("INSERT INTO orders (customer_id, book, total, address_id, status) "
                     "VALUES (?, ?, ?, ?, 'paid')",
                     (caller["customer_id"], order.book, order.total, order.address_id))
    return order_json(db, db.execute("SELECT * FROM orders WHERE id = ?", (cur.lastrowid,)).fetchone())


@app.get("/books/{isbn}/reviews")
def reviews(isbn: str):
    # Public endpoint. "Verified purchase" links show the order ID.
    rows = db.execute("SELECT * FROM reviews WHERE isbn = ?", (isbn,)).fetchall()
    return [dict(r) for r in rows]
