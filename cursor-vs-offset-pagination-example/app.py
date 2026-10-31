"""Orders API with three kinds of pagination: offset, keyset and cursor.

Run: uvicorn app:app --port 8000
The database (orders.db) is recreated with 10 sample orders on every start.
"""
import base64
import binascii
import json
import os
import sqlite3
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel

DB = os.environ.get("ORDERS_DB", "orders.db")
MAX_LIMIT = 100

app = FastAPI(title="Orders API - pagination demo")


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def seed():
    if os.path.exists(DB):
        os.remove(DB)
    with connect() as con:
        con.execute("""CREATE TABLE orders (
                         id         INTEGER PRIMARY KEY,
                         created_at TEXT    NOT NULL,
                         customer   TEXT    NOT NULL,
                         total      INTEGER NOT NULL)""")
        # The index matches the sort order: newest first, id breaks ties.
        con.execute("CREATE INDEX idx_orders_created_id ON orders (created_at, id)")
        rows = [
            (101, "2026-10-01T09:00:00Z", "alice", 40),
            (102, "2026-10-01T09:05:00Z", "bob", 15),
            (103, "2026-10-01T09:05:00Z", "carol", 22),   # same time as 102
            (104, "2026-10-01T09:12:00Z", "dave", 31),
            (105, "2026-10-01T09:20:00Z", "erin", 9),
            (106, "2026-10-01T09:31:00Z", "frank", 54),
            (107, "2026-10-01T09:44:00Z", "grace", 18),
            (108, "2026-10-01T09:44:00Z", "heidi", 27),   # same time as 107
            (109, "2026-10-01T09:58:00Z", "ivan", 66),
            (110, "2026-10-01T10:03:00Z", "judy", 12),
        ]
        con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", rows)


seed()


def as_dict(row):
    return {"id": row["id"], "created_at": row["created_at"], "customer": row["customer"]}


# ---------- 1. Offset pagination ----------

@app.get("/orders/offset")
def list_offset(limit: int = Query(3, ge=1, le=MAX_LIMIT), offset: int = Query(0, ge=0)):
    with connect() as con:
        rows = con.execute(
            "SELECT * FROM orders ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (limit, offset)).fetchall()
        total = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    return {"data": [as_dict(r) for r in rows],
            "offset": offset, "limit": limit, "total": total}


# ---------- 2. Keyset pagination (sort values visible in the URL) ----------

@app.get("/orders/keyset")
def list_keyset(limit: int = Query(3, ge=1, le=MAX_LIMIT),
                before_created_at: str | None = None, before_id: int | None = None):
    sql = "SELECT * FROM orders"
    args: list = []
    if before_created_at is not None and before_id is not None:
        sql += " WHERE (created_at, id) < (?, ?)"
        args += [before_created_at, before_id]
    sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
    args.append(limit)
    with connect() as con:
        rows = con.execute(sql, args).fetchall()
    return {"data": [as_dict(r) for r in rows]}


# ---------- 3. Cursor pagination (opaque token, keyset underneath) ----------

def encode_cursor(row) -> str:
    raw = json.dumps({"created_at": row["created_at"], "id": row["id"]},
                     separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[str, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        data = json.loads(raw)
        created_at, row_id = data["created_at"], data["id"]
        datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        if not isinstance(row_id, int):
            raise ValueError("id must be an integer")
        return created_at, row_id
    except (binascii.Error, ValueError, KeyError, TypeError, UnicodeDecodeError):
        raise HTTPException(400, detail="Invalid cursor. Start again without a cursor.")


@app.get("/orders")
def list_cursor(response: Response,
                limit: int = Query(3, ge=1, le=MAX_LIMIT), cursor: str | None = None):
    sql = "SELECT * FROM orders"
    args: list = []
    if cursor:
        sql += " WHERE (created_at, id) < (?, ?)"
        args += list(decode_cursor(cursor))
    sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
    args.append(limit + 1)            # one extra row tells us if there is a next page
    with connect() as con:
        rows = con.execute(sql, args).fetchall()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = encode_cursor(rows[-1]) if has_more else None
    if next_cursor:
        response.headers["Link"] = f'</orders?limit={limit}&cursor={next_cursor}>; rel="next"'
    return {"data": [as_dict(r) for r in rows],
            "next_cursor": next_cursor, "has_more": has_more}


# ---------- Writes, to change the data between two page requests ----------

class NewOrder(BaseModel):
    customer: str
    total: int


@app.post("/orders", status_code=201)
def create_order(order: NewOrder):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with connect() as con:
        cur = con.execute(
            "INSERT INTO orders (created_at, customer, total) VALUES (?, ?, ?)",
            (now, order.customer, order.total))
        row = con.execute("SELECT * FROM orders WHERE id = ?", (cur.lastrowid,)).fetchone()
    return as_dict(row)


@app.post("/_reset", status_code=204)
def reset():
    """Demo only: put the 10 sample orders back."""
    seed()
    return Response(status_code=204)


@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: int):
    with connect() as con:
        con.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    return Response(status_code=204)
