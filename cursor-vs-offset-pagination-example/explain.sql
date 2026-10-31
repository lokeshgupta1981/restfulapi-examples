-- OFFSET vs keyset in PostgreSQL: how many index entries does each query read?
-- Run: psql -d <your test database> -f explain.sql
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
  id         bigint      PRIMARY KEY,
  created_at timestamptz NOT NULL,
  customer   text        NOT NULL,
  total      integer     NOT NULL
);
INSERT INTO orders
SELECT i, timestamptz '2026-01-01 00:00:00+00' + i * interval '15 seconds',
       'customer-' || (i % 5000), i % 300
FROM generate_series(1, 1000000) AS i;
CREATE INDEX idx_orders_created_id ON orders (created_at, id);
VACUUM ANALYZE orders;

-- Page 25,001 with OFFSET: skip 500,000 rows, return 20.
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT * FROM orders
ORDER BY created_at DESC, id DESC
LIMIT 20 OFFSET 500000;

-- The same page with keyset: start after the last row of page 25,000.
SELECT created_at, id FROM orders
ORDER BY created_at DESC, id DESC
LIMIT 1 OFFSET 499999;

EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT * FROM orders
WHERE (created_at, id) < ('2026-03-28 19:20:15+00', 500001)
ORDER BY created_at DESC, id DESC
LIMIT 20;
