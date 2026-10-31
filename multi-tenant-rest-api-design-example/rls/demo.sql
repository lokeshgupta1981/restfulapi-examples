-- Run as the API's role: psql -U app_user -f demo.sql

\echo '--- 1. A request for tenant acme. The query has no WHERE clause.'
BEGIN;
SELECT set_config('app.tenant_id', 'acme', true);
SELECT id, tenant_id, customer FROM invoices ORDER BY id;
COMMIT;

\echo '--- 2. After the transaction, no tenant is set: no rows.'
SELECT count(*) FROM invoices;

\echo '--- 3. Acme tries to write a row for globex.'
BEGIN;
SELECT set_config('app.tenant_id', 'acme', true);
INSERT INTO invoices VALUES (1004, 'globex', 'Umbrella', 500);
ROLLBACK;

\echo '--- 4. Acme tries to read invoice 1002 (globex) by ID.'
BEGIN;
SELECT set_config('app.tenant_id', 'acme', true);
SELECT id, tenant_id FROM invoices WHERE id = 1002;
COMMIT;

\echo '--- 5. The pooling mistake: a session-level setting (is_local = false) ...'
SELECT set_config('app.tenant_id', 'acme', false);
\echo '--- ... and the next request on the same connection forgets to set its tenant.'
SELECT id, tenant_id FROM invoices ORDER BY id;
