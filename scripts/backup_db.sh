#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# SAP Transformation Platform — Database Backup Script
# Sprint 24: Automated backup via pg_dump
#
# Usage:
#   ./scripts/backup_db.sh                    # backup to default dir
#   ./scripts/backup_db.sh /path/to/backups   # custom backup dir
#   PGPASSWORD=xxx ./scripts/backup_db.sh     # with password
#
# Requires: pg_dump, gzip
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_URL="${DATABASE_URL:-postgresql://sap_user:sap_pass@localhost:5432/sap_platform_dev}"

# Parse DB URL
DB_HOST=$(echo "$DB_URL" | sed -n 's|.*@\(.*\):\([0-9]*\)/.*|\1|p')
DB_PORT=$(echo "$DB_URL" | sed -n 's|.*@\(.*\):\([0-9]*\)/.*|\2|p')
DB_NAME=$(echo "$DB_URL" | sed -n 's|.*/\(.*\)$|\1|p')
DB_USER=$(echo "$DB_URL" | sed -n 's|.*://\(.*\):.*@.*|\1|p')

BACKUP_FILE="${BACKUP_DIR}/sap_platform_${TIMESTAMP}.sql.gz"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  SAP Transformation Platform — Database Backup          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Database:  ${DB_NAME}"
echo "  Host:      ${DB_HOST}:${DB_PORT}"
echo "  Backup to: ${BACKUP_FILE}"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Perform backup
echo "→ Running pg_dump..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --format=plain --no-owner --no-acl \
    | gzip > "$BACKUP_FILE"

FILESIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
echo "✓ Backup complete: ${BACKUP_FILE} (${FILESIZE})"

# Cleanup old backups (keep last 10)
echo "→ Cleaning up old backups (keeping last 10)..."
ls -t "${BACKUP_DIR}"/sap_platform_*.sql.gz 2>/dev/null | tail -n +11 | xargs -r rm -f
echo "✓ Cleanup done."

echo ""
echo "To restore: gunzip -c ${BACKUP_FILE} | psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME}"
