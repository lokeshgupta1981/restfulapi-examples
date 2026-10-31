"""Time one page of 20 rows at different depths: OFFSET vs keyset.

Builds bench.db (SQLite) with 1,000,000 orders and an index on (created_at, id).
Run: python bench.py
"""
import os
import sqlite3
import statistics
import time
from datetime import datetime, timedelta

DB, N, LIMIT, REPEAT = "bench.db", 1_000_000, 20, 15
DEPTHS = [0, 1_000, 10_000, 100_000, 500_000, 999_000]

if os.path.exists(DB):
    os.remove(DB)
con = sqlite3.connect(DB)
con.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, "
            "customer TEXT NOT NULL, total INTEGER NOT NULL)")
start = datetime(2026, 1, 1)
con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)",
                ((i, (start + timedelta(seconds=i * 15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  f"customer-{i % 5000}", i % 300) for i in range(1, N + 1)))
con.execute("CREATE INDEX idx_orders_created_id ON orders (created_at, id)")
con.commit()

OFFSET_SQL = ("SELECT * FROM orders ORDER BY created_at DESC, id DESC "
              "LIMIT ? OFFSET ?")
KEYSET_SQL = ("SELECT * FROM orders WHERE (created_at, id) < (?, ?) "
              "ORDER BY created_at DESC, id DESC LIMIT ?")
FIRST_SQL = "SELECT * FROM orders ORDER BY created_at DESC, id DESC LIMIT ?"

print("Query plans:")
for sql, args in [(OFFSET_SQL, (LIMIT, 500_000)), (KEYSET_SQL, ("2026-01-01", 1, LIMIT))]:
    plan = con.execute("EXPLAIN QUERY PLAN " + sql, args).fetchall()
    print(" ", sql.split(" ORDER")[0][:60], "->", "; ".join(p[3] for p in plan))


def median_ms(sql, args):
    times = []
    for _ in range(REPEAT):
        t = time.perf_counter()
        rows = con.execute(sql, args).fetchall()
        times.append((time.perf_counter() - t) * 1000)
    return statistics.median(times), rows


print(f"\n{N:,} rows, page size {LIMIT}, median of {REPEAT} runs")
print(f"{'rows skipped':>12} | {'OFFSET ms':>9} | {'keyset ms':>9} | same rows")
for depth in DEPTHS:
    off_ms, off_rows = median_ms(OFFSET_SQL, (LIMIT, depth))
    if depth == 0:
        key_ms, key_rows = median_ms(FIRST_SQL, (LIMIT,))
    else:
        # The cursor holds the sort values of the last row on the previous page.
        last = con.execute(OFFSET_SQL, (1, depth - 1)).fetchone()
        key_ms, key_rows = median_ms(KEYSET_SQL, (last[1], last[0], LIMIT))
    print(f"{depth:>12,} | {off_ms:>9.3f} | {key_ms:>9.3f} | {off_rows == key_rows}")
con.close()
