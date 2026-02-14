"""
Schema-per-Tenant Service — Sprint 10 (Item 4.8)

PostgreSQL schema isolation for enterprise tenants.
Each enterprise tenant gets its own PG schema, while standard
tenants share the 'public' schema with tenant_id filtering.

Architecture:
  - Standard/trial tenants: shared tables in 'public' schema
  - Enterprise tenants: dedicated PG schema (e.g. 'tenant_42')
  - Schema created on tenant upgrade or new enterprise onboarding
  - Dynamic schema switching via session-level search_path
"""

import logging

import sqlalchemy as sa

from app.models import db
from app.models.auth import Tenant

logger = logging.getLogger(__name__)


def _is_postgres():
    """Check if the current database is PostgreSQL."""
    return "postgresql" in str(db.engine.url)


def create_tenant_schema(tenant_id):
    """Create a dedicated PostgreSQL schema for an enterprise tenant.

    Returns:
        (schema_name, error_str)
    """
    if not _is_postgres():
        return None, "Schema-per-tenant requires PostgreSQL"

    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return None, "Tenant not found"

    schema_name = f"tenant_{tenant_id}"

    try:
        with db.engine.connect() as conn:
            # Create schema if not exists
            conn.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
            conn.commit()

        # Update tenant settings to track schema
        settings = tenant.settings or {}
        settings["schema"] = schema_name
        tenant.settings = settings
        db.session.commit()

        logger.info("Created schema '%s' for tenant %d", schema_name, tenant_id)
        return schema_name, None

    except Exception as exc:
        logger.error("Failed to create schema for tenant %d: %s", tenant_id, exc)
        return None, str(exc)


def clone_tables_to_schema(tenant_id):
    """Clone all public tables into the tenant's schema.

    This creates empty copies of all tables in the tenant's dedicated schema.

    Returns:
        (table_count, error_str)
    """
    if not _is_postgres():
        return None, "Schema-per-tenant requires PostgreSQL"

    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return None, "Tenant not found"

    schema_name = (tenant.settings or {}).get("schema")
    if not schema_name:
        return None, "Tenant does not have a dedicated schema"

    try:
        count = 0
        with db.engine.connect() as conn:
            for table in db.metadata.sorted_tables:
                table_name = table.name
                # Skip auth tables — those stay in public
                if table_name in ("tenants", "sso_configs", "tenant_domains", "feature_flags", "tenant_feature_flags"):
                    continue
                try:
                    conn.execute(sa.text(
                        f'CREATE TABLE IF NOT EXISTS "{schema_name}"."{table_name}" '
                        f'(LIKE "public"."{table_name}" INCLUDING ALL)'
                    ))
                    count += 1
                except Exception as exc:
                    logger.warning("Could not clone table %s to %s: %s", table_name, schema_name, exc)
            conn.commit()

        logger.info("Cloned %d tables to schema '%s'", count, schema_name)
        return count, None

    except Exception as exc:
        logger.error("Failed to clone tables for tenant %d: %s", tenant_id, exc)
        return None, str(exc)


def drop_tenant_schema(tenant_id):
    """Drop a tenant's dedicated schema (DANGEROUS — use with caution).

    Returns:
        (success, error_str)
    """
    if not _is_postgres():
        return False, "Schema-per-tenant requires PostgreSQL"

    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return False, "Tenant not found"

    schema_name = (tenant.settings or {}).get("schema")
    if not schema_name:
        return False, "Tenant does not have a dedicated schema"

    try:
        with db.engine.connect() as conn:
            conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
            conn.commit()

        # Remove schema from tenant settings
        settings = tenant.settings or {}
        settings.pop("schema", None)
        tenant.settings = settings
        db.session.commit()

        logger.info("Dropped schema '%s' for tenant %d", schema_name, tenant_id)
        return True, None

    except Exception as exc:
        logger.error("Failed to drop schema for tenant %d: %s", tenant_id, exc)
        return False, str(exc)


def get_tenant_schema(tenant_id):
    """Get the schema name for a tenant (or 'public' for shared tenants)."""
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return "public"
    return (tenant.settings or {}).get("schema", "public")


def list_tenant_schemas():
    """List all tenants that have dedicated schemas."""
    tenants = Tenant.query.all()
    result = []
    for t in tenants:
        schema = (t.settings or {}).get("schema")
        if schema:
            result.append({
                "tenant_id": t.id,
                "tenant_name": t.name,
                "schema": schema,
                "plan": t.plan,
            })
    return result


def set_search_path(tenant_id):
    """Set the PostgreSQL search_path for the current connection to a tenant's schema.

    This should be called at the start of each request for enterprise tenants.

    Returns:
        (schema_name, error_str)
    """
    if not _is_postgres():
        return "public", None

    schema_name = get_tenant_schema(tenant_id)
    if schema_name != "public":
        try:
            db.session.execute(sa.text(f'SET search_path TO "{schema_name}", public'))
            return schema_name, None
        except Exception as exc:
            logger.error("Failed to set search_path for tenant %d: %s", tenant_id, exc)
            return None, str(exc)
    return "public", None
