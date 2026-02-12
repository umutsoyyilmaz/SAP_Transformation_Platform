#!/usr/bin/env python3
"""
SAP Transformation Platform — Tenant Migration Script.

Ensures all registered tenant databases have the latest schema.
Runs Flask-Migrate (Alembic) upgrade against each tenant DB.

Usage:
    python scripts/migrate_tenants.py                  # Migrate all tenants
    python scripts/migrate_tenants.py --tenant acme    # Migrate single tenant
    python scripts/migrate_tenants.py --check          # Dry-run: show pending
    python scripts/migrate_tenants.py --create-all     # create_all() fallback

For PostgreSQL tenants, this runs `flask db upgrade`.
For SQLite tenants, this uses db.create_all() as a safe fallback
(Alembic offline mode doesn't always handle SQLite well).
"""

import argparse
import os
import sys

sys.path.insert(0, ".")


def migrate_tenant(tenant_id: str, check_only: bool = False, use_create_all: bool = False):
    """Run migrations for a single tenant."""
    from app.tenant import get_tenant_config, get_tenant_db_uri

    cfg = get_tenant_config(tenant_id)
    if not cfg:
        print(f"  ❌ Tenant '{tenant_id}' bulunamadı")
        return False

    db_uri = get_tenant_db_uri(tenant_id)
    display = cfg.get("display_name", tenant_id)

    if check_only:
        print(f"  📋 {tenant_id} ({display}): {db_uri}")
        return True

    print(f"  ⬆️  Migrating: {tenant_id} ({display})")

    # Set env for this tenant
    os.environ["DATABASE_URL"] = db_uri
    os.environ["TENANT_ID"] = tenant_id

    if use_create_all or db_uri.startswith("sqlite"):
        # SQLite: use create_all() — simpler and more reliable
        from app import create_app
        from app.models import db as _db

        app = create_app("development")
        with app.app_context():
            _db.create_all()
        print(f"     ✅ create_all() tamamlandı ({tenant_id})")
    else:
        # PostgreSQL: use Alembic migrations
        result = os.system(
            f'FLASK_APP=wsgi.py DATABASE_URL="{db_uri}" flask db upgrade 2>&1'
        )
        if result == 0:
            print(f"     ✅ Alembic upgrade tamamlandı ({tenant_id})")
        else:
            print(f"     ❌ Migration başarısız ({tenant_id})")
            return False

    return True


def verify_tenant_schema(tenant_id: str) -> dict:
    """
    Verify a tenant DB has all expected tables.
    Returns: {"tenant_id": str, "ok": bool, "tables": int, "missing": [...]}
    """
    from app.tenant import get_tenant_db_uri
    from sqlalchemy import create_engine, inspect

    db_uri = get_tenant_db_uri(tenant_id)
    engine = create_engine(db_uri)

    try:
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
    except Exception as e:
        return {"tenant_id": tenant_id, "ok": False, "tables": 0, "missing": [], "error": str(e)}
    finally:
        engine.dispose()

    # Expected critical tables (subset — not exhaustive)
    critical_tables = {
        "programs", "phases", "gates", "workstreams", "team_members",
        "explore_workshops", "explore_requirements", "explore_open_items",
        "process_levels", "process_steps", "workshop_scope_items",
        "backlog_items", "config_items", "test_plans", "test_cases",
        "test_executions", "defects", "risks", "actions", "issues",
        "decisions", "audit_logs", "project_roles",
    }

    missing = critical_tables - existing
    return {
        "tenant_id": tenant_id,
        "ok": len(missing) == 0,
        "tables": len(existing),
        "missing": sorted(missing),
    }


def main():
    parser = argparse.ArgumentParser(description="Tenant Migration Tool")
    parser.add_argument("--tenant", help="Migrate specific tenant only")
    parser.add_argument("--check", action="store_true", help="Dry-run: show tenants and URIs")
    parser.add_argument("--create-all", action="store_true", help="Use db.create_all() instead of Alembic")
    parser.add_argument("--verify", action="store_true", help="Verify schema after migration")
    args = parser.parse_args()

    from app.tenant import list_tenants

    tenants = list_tenants()

    if args.tenant:
        if args.tenant not in tenants:
            print(f"  ❌ Tenant '{args.tenant}' kayıtlı değil")
            sys.exit(1)
        targets = {args.tenant: tenants[args.tenant]}
    else:
        targets = tenants

    print(f"\n  {'Schema Check' if args.check else 'Tenant Migration'}")
    print("  " + "═" * 50)

    all_ok = True
    for tid in targets:
        ok = migrate_tenant(tid, check_only=args.check, use_create_all=args.create_all)
        if not ok:
            all_ok = False

    if args.verify and not args.check:
        print(f"\n  Schema Doğrulama")
        print("  " + "─" * 50)
        for tid in targets:
            result = verify_tenant_schema(tid)
            if result["ok"]:
                print(f"  ✅ {tid}: {result['tables']} tablo — OK")
            else:
                print(f"  ❌ {tid}: {result['tables']} tablo — Eksik: {result['missing']}")
                all_ok = False

    print()
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
