-- Run as the database owner (for example: psql -U postgres -f schema.sql)
DROP TABLE IF EXISTS invoices;
DROP ROLE IF EXISTS app_user;

-- The API connects as app_user: not a superuser, not the table owner, no BYPASSRLS.
CREATE ROLE app_user LOGIN;

CREATE TABLE invoices (
    id           int  PRIMARY KEY,
    tenant_id    text NOT NULL,
    customer     text NOT NULL,
    amount_cents int  NOT NULL
);
CREATE INDEX ix_invoices_tenant ON invoices (tenant_id, id);

INSERT INTO invoices VALUES
    (1001, 'acme',   'Wayne Hardware', 12000),
    (1002, 'globex', 'Initech',        990000),
    (1003, 'acme',   'Stark Supplies', 4500);

GRANT SELECT, INSERT, UPDATE, DELETE ON invoices TO app_user;

-- Row-level security: every query sees only the rows of the tenant
-- that the API stored in the app.tenant_id setting for this transaction.
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON invoices
    USING      (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
