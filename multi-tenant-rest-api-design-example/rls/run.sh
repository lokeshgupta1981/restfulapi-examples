#!/usr/bin/env bash
# Creates the table and policy, then runs the demo as app_user.
# PGHOST/PGPORT select the server (defaults: local socket, port 5432).
set -e
cd "$(dirname "$0")"
psql -X -q -U "${PGADMIN:-postgres}" -d "${PGDATABASE:-postgres}" -f schema.sql
psql -X -a -U app_user -d "${PGDATABASE:-postgres}" -f demo.sql
echo '--- 6. The superuser bypasses row-level security: it sees every row.'
psql -X -U "${PGADMIN:-postgres}" -d "${PGDATABASE:-postgres}" -c "SELECT count(*) AS rows_seen FROM invoices;"
