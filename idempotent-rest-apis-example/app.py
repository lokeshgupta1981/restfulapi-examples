"""Orders API that shows which HTTP methods are idempotent and how to make POST safe to retry."""
import hashlib
import json
import os
import sqlite3
import time

import jsonpatch
from fastapi import Body, FastAPI, Header, Response
from fastapi.responses import JSONResponse

DB_PATH = os.environ.get("DB_PATH", "orders.db")
SLOW_CREATE_SECONDS = float(os.environ.get("SLOW_CREATE_SECONDS", "0"))
# A key that stays "processing" longer than this (for example after a crash) can be taken over by a retry.
PROCESSING_TIMEOUT_SECONDS = float(os.environ.get("PROCESSING_TIMEOUT_SECONDS", "30"))

app = FastAPI(title="Orders API")


def connect():
    connection = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                body TEXT NOT NULL,
                version INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                idem_key TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                status TEXT NOT NULL,
                response_status INTEGER,
                response_body TEXT,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
            INSERT INTO counters (name, value) VALUES ('order', 1000) ON CONFLICT(name) DO NOTHING;
            """
        )


init_db()


def problem(status, title, detail):
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def load_order(db, order_id):
    row = db.execute("SELECT body, version FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return None, None
    return json.loads(row["body"]), row["version"]


def order_response(order, version, status_code=200, headers=None):
    all_headers = {"ETag": f'"v{version}"'}
    all_headers.update(headers or {})
    return JSONResponse(order, status_code=status_code, headers=all_headers)


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    with connect() as db:
        order, version = load_order(db, order_id)
    if order is None:
        return problem(404, "Not Found", f"Order {order_id} does not exist.")
    return order_response(order, version)


@app.get("/orders")
def list_orders():
    with connect() as db:
        rows = db.execute("SELECT id FROM orders ORDER BY id").fetchall()
    return {"count": len(rows), "ids": [row["id"] for row in rows]}


def create_order(db, payload):
    """Create a new order with a server-generated id. Every call creates one more order."""
    if SLOW_CREATE_SECONDS:
        time.sleep (SLOW_CREATE_SECONDS)
    db.execute("BEGIN IMMEDIATE")
    number = db.execute("UPDATE counters SET value = value + 1 WHERE name = 'order' RETURNING value").fetchone()[0]
    order = {"id": f"ord_{number}", "items": payload.get("items", []), "status": "new"}
    db.execute("INSERT INTO orders (id, body, version) VALUES (?, ?, 1)", (order["id"], json.dumps(order)))
    db.execute("COMMIT")
    return order


@app.post("/orders")
def post_order(payload: dict = Body(default={}), idem_key: str | None = Header(default=None, alias="Idempotency-Key")):

    with connect() as db:
        if idem_key is None:
            order = create_order(db, payload)
            return order_response(order, 1, 201, {"Location": f"/orders/{order['id']}"})

        canonical_body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(("POST /orders\n" + canonical_body).encode()).hexdigest()
        claimed = db.execute(
            "INSERT INTO idempotency_keys (idem_key, fingerprint, status, created_at) "
            "VALUES (?, ?, 'processing', ?) ON CONFLICT(idem_key) DO NOTHING",
            (idem_key, fingerprint, time.time()),
        ).rowcount

        if claimed == 0:
            row = db.execute("SELECT * FROM idempotency_keys WHERE idem_key = ?", (idem_key,)).fetchone()
            if row["fingerprint"] != fingerprint:
                return problem(422, "Unprocessable Content", "This Idempotency-Key was already used with a different request body.")
            if row["status"] == "done":
                stored = json.loads(row["response_body"])
                return JSONResponse(stored, status_code=row["response_status"],
                                    headers={"Location": f"/orders/{stored['id']}", "Idempotent-Replayed": "true"})
            # The first request is still "processing". Take the key over only if it is older than the timeout.
            taken_over = db.execute(
                "UPDATE idempotency_keys SET created_at = ? "
                "WHERE idem_key = ? AND status = 'processing' AND created_at < ?",
                (time.time(), idem_key, time.time() - PROCESSING_TIMEOUT_SECONDS),
            ).rowcount
            if not taken_over:
                return problem(409, "Conflict", "A request with this Idempotency-Key is still being processed. Retry later.")

        try:
            order = create_order(db, payload)
        except Exception:
            # Free the key so that the client can retry the same request.
            db.execute("DELETE FROM idempotency_keys WHERE idem_key = ?", (idem_key,))
            raise
        db.execute(
            "UPDATE idempotency_keys SET status = 'done', response_status = 201, response_body = ? WHERE idem_key = ?",
            (json.dumps(order), idem_key),
        )
        return order_response(order, 1, 201, {"Location": f"/orders/{order['id']}"})


@app.put("/orders/{order_id}")
def put_order(order_id: str, new_order: dict = Body()):
    # The server stores the body as received, so the ETag in the response is allowed (RFC 9110, section 9.3.4).
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current, version = load_order(db, order_id)
        if current is None:
            db.execute("INSERT INTO orders (id, body, version) VALUES (?, ?, 1)", (order_id, json.dumps(new_order)))
            db.execute("COMMIT")
            return order_response(new_order, 1, 201, {"Location": f"/orders/{order_id}"})
        if current != new_order:
            version += 1
            db.execute("UPDATE orders SET body = ?, version = ? WHERE id = ?", (json.dumps(new_order), version, order_id))
        db.execute("COMMIT")
    return order_response(new_order, version)


@app.patch("/orders/{order_id}")
def patch_order(order_id: str, operations: list = Body(), if_match: str | None = Header(default=None)):
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        current, version = load_order(db, order_id)
        if current is None:
            db.execute("ROLLBACK")
            return problem(404, "Not Found", f"Order {order_id} does not exist.")
        if if_match is not None and if_match != f'"v{version}"':
            db.execute("ROLLBACK")
            return problem(412, "Precondition Failed", f"The order changed. Current ETag is \"v{version}\".")
        patched = jsonpatch.apply_patch(current, operations)
        if patched != current:
            version += 1
            db.execute("UPDATE orders SET body = ?, version = ? WHERE id = ?", (json.dumps(patched), version, order_id))
        db.execute("COMMIT")
    return order_response(patched, version)


@app.delete("/orders/{order_id}")
def delete_order(order_id: str):
    with connect() as db:
        deleted = db.execute("DELETE FROM orders WHERE id = ?", (order_id,)).rowcount
    if deleted == 0:
        return problem(404, "Not Found", f"Order {order_id} does not exist.")
    return Response(status_code=204)
