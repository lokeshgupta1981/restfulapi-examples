"""A tiny SQLite order store. The primary key is the ID text, so ORDER BY id sorts by the ID."""
import json
import sqlite3
import threading
from datetime import datetime, timezone


class OrderStore:
    def __init__(self):
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.execute("CREATE TABLE orders (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, body TEXT NOT NULL)")
        self.lock = threading.Lock()

    def insert(self, order_id: str, body: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self.lock:
            self.db.execute("INSERT INTO orders VALUES (?, ?, ?)", (order_id, now, json.dumps(body, sort_keys=True)))
        return {"id": order_id, "created_at": now, **body}

    def get(self, order_id: str) -> dict | None:
        row = self.db.execute("SELECT id, created_at, body FROM orders WHERE id = ?", (order_id,)).fetchone()
        return None if row is None else {"id": row[0], "created_at": row[1], **json.loads(row[2])}

    def page(self, after: str | None, limit: int) -> list[dict]:
        """Keyset pagination: the rows whose id is greater than the cursor, in id order."""
        rows = self.db.execute(
            "SELECT id, created_at, body FROM orders WHERE id > ? ORDER BY id LIMIT ?",
            (after or "", limit),
        ).fetchall()
        return [{"id": r[0], "created_at": r[1], **json.loads(r[2])} for r in rows]
