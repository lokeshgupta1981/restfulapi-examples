"""Demo data and authentication shared by both versions of the Bookstore Orders API."""
import sqlite3

from fastapi import Header, HTTPException

# Fake demo tokens. A real API reads the user from a validated JWT or session.
TOKENS = {
    "demo-token-alice": {"customer_id": 1, "name": "alice", "role": "customer"},
    "demo-token-bob": {"customer_id": 2, "name": "bob", "role": "customer"},
    "demo-token-sam": {"customer_id": 90, "name": "sam", "role": "support"},
}


def new_db():
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE addresses (id INTEGER PRIMARY KEY, customer_id INTEGER, line TEXT);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, book TEXT,
                             total REAL, address_id INTEGER, status TEXT);
        CREATE TABLE reviews (isbn TEXT, author TEXT, stars INTEGER, order_id INTEGER);
        INSERT INTO addresses VALUES (11, 1, '12 Elm Street, Springfield'),
                                     (12, 2, '7 Harbour Road, Shelbyville'),
                                     (13, 3, '99 Hill Lane, Ogdenville');
        INSERT INTO orders VALUES (1001, 1, 'Dune', 18.50, 11, 'shipped'),
                                  (1002, 2, 'Emma', 9.99, 12, 'paid'),
                                  (1003, 3, 'Ulysses', 14.25, 13, 'paid'),
                                  (1004, 1, 'Beloved', 12.00, 11, 'paid');
        INSERT INTO reviews VALUES ('978-0141439587', 'bob', 5, 1002);
    """)
    return db


def order_json(db, row):
    address = db.execute("SELECT line FROM addresses WHERE id = ?", (row["address_id"],)).fetchone()
    return {"id": row["id"], "customer_id": row["customer_id"], "book": row["book"],
            "total": row["total"], "status": row["status"], "ship_to": address["line"]}


def current_caller(authorization: str = Header(default="")):
    """Authentication only: who is calling. It says nothing about which orders they may touch."""
    caller = TOKENS.get(authorization.removeprefix("Bearer ").strip())
    if caller is None:
        raise HTTPException(401, "Missing or unknown token",
                            headers={"WWW-Authenticate": 'Bearer realm="orders"'})
    return caller
