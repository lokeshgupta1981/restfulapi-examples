"""Keyset pagination on created_at alone loses rows that share a timestamp.

Uses the same 10 sample orders as app.py, in an in-memory SQLite database.
Run: python tie_breaker.py
"""
import sqlite3

ROWS = [(101, "2026-10-01T09:00:00Z"), (102, "2026-10-01T09:05:00Z"),
        (103, "2026-10-01T09:05:00Z"), (104, "2026-10-01T09:12:00Z"),
        (105, "2026-10-01T09:20:00Z"), (106, "2026-10-01T09:31:00Z"),
        (107, "2026-10-01T09:44:00Z"), (108, "2026-10-01T09:44:00Z"),
        (109, "2026-10-01T09:58:00Z"), (110, "2026-10-01T10:03:00Z")]

con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL)")
con.executemany("INSERT INTO orders VALUES (?, ?)", ROWS)


def walk(first_sql, next_sql, key):
    seen, rows = [], con.execute(first_sql).fetchall()
    while rows:
        print("  page:", [r[0] for r in rows])
        seen += [r[0] for r in rows]
        rows = con.execute(next_sql, key(rows[-1])).fetchall()
    missing = sorted(set(r[0] for r in ROWS) - set(seen))
    print("  rows seen:", len(seen), " missing:", missing or "none")


print("Sort by created_at only, WHERE created_at < last created_at")
walk("SELECT id, created_at FROM orders ORDER BY created_at DESC LIMIT 3",
     "SELECT id, created_at FROM orders WHERE created_at < ? "
     "ORDER BY created_at DESC LIMIT 3",
     lambda last: (last[1],))

print("Sort by created_at, id; WHERE (created_at, id) < (last created_at, last id)")
walk("SELECT id, created_at FROM orders ORDER BY created_at DESC, id DESC LIMIT 3",
     "SELECT id, created_at FROM orders WHERE (created_at, id) < (?, ?) "
     "ORDER BY created_at DESC, id DESC LIMIT 3",
     lambda last: (last[1], last[0]))
