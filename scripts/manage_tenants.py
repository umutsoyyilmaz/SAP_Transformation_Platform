#!/usr/bin/env python3
"""
SAP Transformation Platform — Tenant Management CLI.

Commands:
    python scripts/manage_tenants.py list
    python scripts/manage_tenants.py create <id> --name "Acme Corp"
    python scripts/manage_tenants.py init <id>          # Create DB + run migrations
    python scripts/manage_tenants.py init-all            # Init all tenant DBs
    python scripts/manage_tenants.py remove <id>
    python scripts/manage_tenants.py seed <id>           # Seed demo data for tenant
    python scripts/manage_tenants.py status              # Show all tenant DB status

Usage in docker:
    docker compose exec app python scripts/manage_tenants.py list
"""

import argparse
import os
import sys

sys.path.insert(0, ".")


def cmd_list(args):
    """List all registered tenants."""
    from app.tenant import list_tenants, get_tenant_db_uri

    tenants = list_tenants()
    print(f"\n  Registered Tenants ({len(tenants)})")
    print("  " + "═" * 60)
    for tid, cfg in tenants.items():
        uri = get_tenant_db_uri(tid)
        # Mask password in URI
        display_uri = uri
        if "@" in uri:
            pre, post = uri.split("@", 1)
            display_uri = pre.rsplit(":", 1)[0] + ":***@" + post
        print(f"  {tid:<20} {cfg.get('display_name', ''):<25} {display_uri}")
    print()


def cmd_create(args):
    """Register a new tenant."""
    from app.tenant import register_tenant, get_tenant_config

    tid = args.tenant_id.strip().lower()
    if not tid.isidentifier():
        print(f"  ❌ Invalid tenant ID: '{tid}' (only letters, digits, underscores)")
        sys.exit(1)

    existing = get_tenant_config(tid)
    if existing:
        print(f"  ⚠️  Tenant '{tid}' is already registered: {existing['display_name']}")
        sys.exit(1)

    db_name = f"sap_tenant_{tid}"
    display = args.name or tid.replace("_", " ").title()

    register_tenant(tid, db_name, display)
    print(f"  ✅ Tenant created: {tid}")
    print(f"     DB: {db_name}")
    print(f"     Name: {display}")
    print(f"\n  Next step: python scripts/manage_tenants.py init {tid}")


def cmd_remove(args):
    """Remove a tenant from registry."""
    from app.tenant import remove_tenant

    tid = args.tenant_id.strip().lower()
    if tid == "default":
        print("  ❌ 'default' tenant cannot be deleted")
        sys.exit(1)

    ok = remove_tenant(tid)
    if ok:
        print(f"  ✅ Tenant '{tid}' removed from registry")
        print(f"  ⚠️  Database file was not deleted — clean up manually")
    else:
        print(f"  ❌ Tenant '{tid}' not found")


def cmd_init(args):
    """Initialize database for a tenant (create tables via migration)."""
    from app.tenant import get_tenant_config, get_tenant_db_uri

    tid = args.tenant_id.strip().lower()
    cfg = get_tenant_config(tid)
    if not cfg:
        print(f"  ❌ Tenant '{tid}' not found. Create it first with 'create'.")
        sys.exit(1)

    db_uri = get_tenant_db_uri(tid)
    print(f"  🗄️  Initializing tenant '{tid}' DB...")
    print(f"     URI: {db_uri}")

    # Set env for Flask to pick up
    os.environ["DATABASE_URL"] = db_uri
    os.environ["TENANT_ID"] = tid

    from app import create_app
    from app.models import db as _db

    app = create_app("development")
    with app.app_context():
        _db.create_all()
        print(f"  ✅ Tables created ({tid})")

    # For PostgreSQL, also run Alembic migrations
    if db_uri.startswith("postgresql"):
        print(f"  ⬆️  Applying Alembic migrations...")
        os.system(f'FLASK_APP=wsgi.py DATABASE_URL="{db_uri}" flask db upgrade')
        print(f"  ✅ Migrations completed ({tid})")


def cmd_init_all(args):
    """Initialize databases for ALL registered tenants."""
    from app.tenant import list_tenants

    tenants = list_tenants()
    print(f"\n  Initializing {len(tenants)} tenant DBs...")
    for tid in tenants:
        args.tenant_id = tid
        cmd_init(args)
    print(f"\n  ✅ All tenant DBs are ready!")


def cmd_seed(args):
    """Seed demo data for a specific tenant."""
    from app.tenant import get_tenant_config, get_tenant_db_uri

    tid = args.tenant_id.strip().lower()
    cfg = get_tenant_config(tid)
    if not cfg:
        print(f"  ❌ Tenant '{tid}' not found")
        sys.exit(1)

    db_uri = get_tenant_db_uri(tid)
    os.environ["DATABASE_URL"] = db_uri
    os.environ["TENANT_ID"] = tid

    print(f"  🌱 Loading demo data for tenant '{tid}'...")

    # Import and run the seed script
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/seed_demo_data.py"],
        env={**os.environ, "DATABASE_URL": db_uri},
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    if result.returncode == 0:
        print(f"  ✅ Demo data loaded ({tid})")
    else:
        print(f"  ❌ Seed failed ({tid})")
        sys.exit(1)


def cmd_status(args):
    """Show status of all tenant databases."""
    from app.tenant import list_tenants, get_tenant_db_uri
    from pathlib import Path

    tenants = list_tenants()
    print(f"\n  Tenant Database Status")
    print("  " + "═" * 60)

    for tid, cfg in tenants.items():
        uri = get_tenant_db_uri(tid)
        status = "?"

        if uri.startswith("sqlite"):
            db_path = uri.replace("sqlite:///", "")
            p = Path(db_path)
            if p.exists():
                size_mb = p.stat().st_size / (1024 * 1024)
                status = f"✅ {size_mb:.1f} MB"
            else:
                status = "❌ DB does not exist"
        elif uri.startswith("postgresql"):
            status = "🐘 PostgreSQL (connection check not performed)"

        print(f"  {tid:<20} {cfg.get('display_name', ''):<25} {status}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="SAP Platform — Tenant Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Command")

    # list
    sub.add_parser("list", help="List all tenants")

    # create
    p_create = sub.add_parser("create", help="Create a new tenant")
    p_create.add_argument("tenant_id", help="Tenant slug (e.g.: acme)")
    p_create.add_argument("--name", help="Display name (e.g.: 'Acme Corp')")

    # remove
    p_remove = sub.add_parser("remove", help="Remove a tenant")
    p_remove.add_argument("tenant_id", help="Tenant ID to remove")

    # init
    p_init = sub.add_parser("init", help="Create tenant DB (tables + migrations)")
    p_init.add_argument("tenant_id", help="Tenant ID to initialize")

    # init-all
    sub.add_parser("init-all", help="Create all tenant DBs")

    # seed
    p_seed = sub.add_parser("seed", help="Load demo data for a tenant")
    p_seed.add_argument("tenant_id", help="Tenant ID to seed")

    # status
    sub.add_parser("status", help="Show tenant DB statuses")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "create": cmd_create,
        "remove": cmd_remove,
        "init": cmd_init,
        "init-all": cmd_init_all,
        "seed": cmd_seed,
        "status": cmd_status,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
