"""
SAP Transformation Platform — Multi-Tenant Engine (DB-per-Tenant).

Strategy: Each pilot customer gets an isolated SQLite (dev) or PostgreSQL (prod) database.
Tenant selection happens via:
    1. X-Tenant-ID HTTP header (API calls)
    2. TENANT_ID environment variable (CLI scripts / single-tenant mode)
    3. Falls back to "default" tenant

Architecture:
    ┌─────────────┐   ┌──────────────────────────┐
    │  Request     │──▶│  resolve_tenant()        │
    │  X-Tenant-ID │   │  → "acme", "globex", ... │
    └─────────────┘   └──────┬───────────────────┘
                             │
                    ┌────────▼────────────┐
                    │  get_tenant_db_uri()│
                    │  → sqlite / pg URI  │
                    └─────────────────────┘

Usage:
    # In config — override SQLALCHEMY_DATABASE_URI per request:
    app.config["SQLALCHEMY_BINDS"] is NOT used; instead we use
    a single DB that's resolved at app-init or per-request.

    # For CLI/scripts — set env var:
    TENANT_ID=acme python scripts/seed_demo_data.py

Tenant Registry (tenants.json):
    {
      "default": {"db_name": "sap_platform_dev", "display_name": "Development"},
      "acme":    {"db_name": "sap_tenant_acme",  "display_name": "Acme Corp"},
      ...
    }
"""

import json
import os
from pathlib import Path

_basedir = Path(__file__).resolve().parent.parent

# ── Tenant Registry ─────────────────────────────────────────────────────

_TENANT_REGISTRY_PATH = _basedir / "tenants.json"

_DEFAULT_REGISTRY = {
    "default": {
        "db_name": "sap_platform_dev",
        "display_name": "Development (Default)",
    },
}


def _load_registry() -> dict:
    """Load tenant registry from tenants.json, or return default."""
    if _TENANT_REGISTRY_PATH.exists():
        with open(_TENANT_REGISTRY_PATH) as f:
            return json.load(f)
    return _DEFAULT_REGISTRY.copy()


def list_tenants() -> dict:
    """Return all registered tenants."""
    return _load_registry()


def get_tenant_config(tenant_id: str) -> dict | None:
    """Get config for a specific tenant, or None if not found."""
    registry = _load_registry()
    return registry.get(tenant_id)


def register_tenant(tenant_id: str, db_name: str, display_name: str = "") -> dict:
    """
    Register a new tenant in tenants.json.

    Args:
        tenant_id: Unique slug (lowercase, no spaces) e.g. "acme"
        db_name: Database name e.g. "sap_tenant_acme"
        display_name: Human-readable name e.g. "Acme Corp"

    Returns:
        The full tenant config dict.
    """
    registry = _load_registry()
    config = {
        "db_name": db_name,
        "display_name": display_name or tenant_id.title(),
    }
    registry[tenant_id] = config
    with open(_TENANT_REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    return config


def remove_tenant(tenant_id: str) -> bool:
    """Remove a tenant from registry. Returns True if removed."""
    if tenant_id == "default":
        return False
    registry = _load_registry()
    if tenant_id in registry:
        del registry[tenant_id]
        with open(_TENANT_REGISTRY_PATH, "w") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        return True
    return False


# ── Tenant Resolution ────────────────────────────────────────────────────

def resolve_tenant() -> str:
    """
    Resolve current tenant ID from (in priority order):
        1. Flask request header X-Tenant-ID
        2. Environment variable TENANT_ID
        3. "default"
    """
    # Try Flask request context first
    try:
        from flask import request, has_request_context
        if has_request_context():
            header = request.headers.get("X-Tenant-ID", "").strip().lower()
            if header:
                return header
    except ImportError:
        pass

    # Fall back to env var
    env_tenant = os.getenv("TENANT_ID", "").strip().lower()
    if env_tenant:
        return env_tenant

    return "default"


def get_tenant_db_uri(tenant_id: str | None = None) -> str:
    """
    Build the database URI for a tenant.

    SQLite (dev):   sqlite:///instance/sap_tenant_{id}.db
    PostgreSQL:     postgresql://user:pass@host:port/{db_name}

    Falls back to DATABASE_URL env var for unknown tenants.
    """
    if tenant_id is None:
        tenant_id = resolve_tenant()

    config = get_tenant_config(tenant_id)
    db_name = config["db_name"] if config else f"sap_tenant_{tenant_id}"

    # Check if a PostgreSQL connection is configured
    base_url = os.getenv("DATABASE_URL", "")
    # Railway/Heroku use postgres:// but SQLAlchemy 2.0 requires postgresql://
    if base_url.startswith("postgres://"):
        base_url = base_url.replace("postgres://", "postgresql://", 1)
    if base_url.startswith("postgresql"):
        # Replace database name in pg URI:  postgresql://user:pass@host:port/OLD_DB → .../NEW_DB
        parts = base_url.rsplit("/", 1)
        if len(parts) == 2:
            return f"{parts[0]}/{db_name}"
        return base_url

    # SQLite mode
    instance_dir = _basedir / "instance"
    instance_dir.mkdir(exist_ok=True)
    return f"sqlite:///{instance_dir / (db_name + '.db')}"


# ── Flask Integration ────────────────────────────────────────────────────

def init_tenant_support(app):
    """
    Initialize tenant-aware database selection.

    Call this AFTER db.init_app(app) in create_app().
    In single-tenant mode (no tenants.json), this is a no-op.
    """
    if not _TENANT_REGISTRY_PATH.exists():
        # Single-tenant mode — no tenant resolution needed
        return

    @app.before_request
    def _resolve_tenant_db():
        """Set the database URI based on the current tenant."""
        from flask import g
        tenant_id = resolve_tenant()
        tenant_config = get_tenant_config(tenant_id)

        if not tenant_config:
            from flask import abort
            abort(400, description=f"Unknown tenant: {tenant_id}")

        g.tenant_id = tenant_id
        g.tenant_name = tenant_config.get("display_name", tenant_id)

    app.logger.info(
        "Tenant support enabled — %d tenants registered",
        len(_load_registry()),
    )
