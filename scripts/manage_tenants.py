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
    print(f"\n  Kayıtlı Tenant'lar ({len(tenants)})")
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
        print(f"  ❌ Geçersiz tenant ID: '{tid}' (sadece harf, rakam, alt çizgi)")
        sys.exit(1)

    existing = get_tenant_config(tid)
    if existing:
        print(f"  ⚠️  Tenant '{tid}' zaten kayıtlı: {existing['display_name']}")
        sys.exit(1)

    db_name = f"sap_tenant_{tid}"
    display = args.name or tid.replace("_", " ").title()

    register_tenant(tid, db_name, display)
    print(f"  ✅ Tenant oluşturuldu: {tid}")
    print(f"     DB: {db_name}")
    print(f"     Ad: {display}")
    print(f"\n  Sonraki adım: python scripts/manage_tenants.py init {tid}")


def cmd_remove(args):
    """Remove a tenant from registry."""
    from app.tenant import remove_tenant

    tid = args.tenant_id.strip().lower()
    if tid == "default":
        print("  ❌ 'default' tenant silinemez")
        sys.exit(1)

    ok = remove_tenant(tid)
    if ok:
        print(f"  ✅ Tenant '{tid}' registry'den silindi")
        print(f"  ⚠️  Veritabanı dosyası silinmedi — elle temizleyin")
    else:
        print(f"  ❌ Tenant '{tid}' bulunamadı")


def cmd_init(args):
    """Initialize database for a tenant (create tables via migration)."""
    from app.tenant import get_tenant_config, get_tenant_db_uri

    tid = args.tenant_id.strip().lower()
    cfg = get_tenant_config(tid)
    if not cfg:
        print(f"  ❌ Tenant '{tid}' bulunamadı. Önce 'create' ile oluşturun.")
        sys.exit(1)

    db_uri = get_tenant_db_uri(tid)
    print(f"  🗄️  Tenant '{tid}' DB başlatılıyor...")
    print(f"     URI: {db_uri}")

    # Set env for Flask to pick up
    os.environ["DATABASE_URL"] = db_uri
    os.environ["TENANT_ID"] = tid

    from app import create_app
    from app.models import db as _db

    app = create_app("development")
    with app.app_context():
        _db.create_all()
        print(f"  ✅ Tablolar oluşturuldu ({tid})")

    # For PostgreSQL, also run Alembic migrations
    if db_uri.startswith("postgresql"):
        print(f"  ⬆️  Alembic migration'ları uygulanıyor...")
        os.system(f'FLASK_APP=wsgi.py DATABASE_URL="{db_uri}" flask db upgrade')
        print(f"  ✅ Migration'lar tamamlandı ({tid})")


def cmd_init_all(args):
    """Initialize databases for ALL registered tenants."""
    from app.tenant import list_tenants

    tenants = list_tenants()
    print(f"\n  {len(tenants)} tenant DB başlatılıyor...")
    for tid in tenants:
        args.tenant_id = tid
        cmd_init(args)
    print(f"\n  ✅ Tüm tenant DB'leri hazır!")


def cmd_seed(args):
    """Seed demo data for a specific tenant."""
    from app.tenant import get_tenant_config, get_tenant_db_uri

    tid = args.tenant_id.strip().lower()
    cfg = get_tenant_config(tid)
    if not cfg:
        print(f"  ❌ Tenant '{tid}' bulunamadı")
        sys.exit(1)

    db_uri = get_tenant_db_uri(tid)
    os.environ["DATABASE_URL"] = db_uri
    os.environ["TENANT_ID"] = tid

    print(f"  🌱 Tenant '{tid}' için demo veri yükleniyor...")

    # Import and run the seed script
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/seed_demo_data.py"],
        env={**os.environ, "DATABASE_URL": db_uri},
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    if result.returncode == 0:
        print(f"  ✅ Demo veri yüklendi ({tid})")
    else:
        print(f"  ❌ Seed başarısız ({tid})")
        sys.exit(1)


def cmd_status(args):
    """Show status of all tenant databases."""
    from app.tenant import list_tenants, get_tenant_db_uri
    from pathlib import Path

    tenants = list_tenants()
    print(f"\n  Tenant Veritabanı Durumu")
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
                status = "❌ DB mevcut değil"
        elif uri.startswith("postgresql"):
            status = "🐘 PostgreSQL (bağlantı kontrolü yapılmadı)"

        print(f"  {tid:<20} {cfg.get('display_name', ''):<25} {status}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="SAP Platform — Tenant Yönetim Aracı",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Komut")

    # list
    sub.add_parser("list", help="Tüm tenant'ları listele")

    # create
    p_create = sub.add_parser("create", help="Yeni tenant oluştur")
    p_create.add_argument("tenant_id", help="Tenant slug (ör: acme)")
    p_create.add_argument("--name", help="Görünen ad (ör: 'Acme Corp')")

    # remove
    p_remove = sub.add_parser("remove", help="Tenant'ı sil")
    p_remove.add_argument("tenant_id", help="Silinecek tenant ID")

    # init
    p_init = sub.add_parser("init", help="Tenant DB oluştur (tablo + migration)")
    p_init.add_argument("tenant_id", help="Başlatılacak tenant ID")

    # init-all
    sub.add_parser("init-all", help="Tüm tenant DB'lerini oluştur")

    # seed
    p_seed = sub.add_parser("seed", help="Tenant'a demo veri yükle")
    p_seed.add_argument("tenant_id", help="Seed yapılacak tenant ID")

    # status
    sub.add_parser("status", help="Tenant DB durumlarını göster")

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
