#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# SAP Transformation Platform — PostgreSQL Tenant DB Initializer
# ═══════════════════════════════════════════════════════════════════
#
# This script runs inside the PostgreSQL container on first startup.
# It reads tenants.json and creates a database for each tenant.
# The default database (sap_platform_dev) is already created by POSTGRES_DB.
#
# Location: docker/init-tenant-dbs.sh
# Mounted: /docker-entrypoint-initdb.d/init-tenant-dbs.sh

set -e

echo "════════════════════════════════════════════════"
echo "  SAP Platform — Tenant DB Initialization"
echo "════════════════════════════════════════════════"

# tenants.json is mounted at /app/tenants.json
TENANTS_FILE="/app/tenants.json"

if [ ! -f "$TENANTS_FILE" ]; then
    echo "  ℹ️  tenants.json not found — skipping tenant DB creation"
    exit 0
fi

# Parse tenant db_names from JSON (simple jq-free parsing)
# Format: "db_name": "sap_tenant_acme"
DB_NAMES=$(python3 -c "
import json, sys
try:
    with open('$TENANTS_FILE') as f:
        data = json.load(f)
    for tid, cfg in data.items():
        db_name = cfg.get('db_name', '')
        if db_name and db_name != '${POSTGRES_DB}':
            print(db_name)
except Exception as e:
    print(f'WARNING: Could not parse tenants.json: {e}', file=sys.stderr)
" 2>/dev/null || true)

if [ -z "$DB_NAMES" ]; then
    echo "  ℹ️  No additional tenant databases to create"
    exit 0
fi

for DB in $DB_NAMES; do
    echo -n "  Creating database: $DB ... "
    psql -v ON_ERROR_STOP=0 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $DB OWNER $POSTGRES_USER'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB');\gexec
EOSQL
    echo "✅"
done

echo "════════════════════════════════════════════════"
echo "  Tenant DB initialization complete"
echo "════════════════════════════════════════════════"
