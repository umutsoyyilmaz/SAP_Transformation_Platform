"""
TenantModel — Abstract base class for tenant-scoped models.

All models that need tenant isolation should inherit from TenantModel
instead of db.Model directly. This adds:
  - tenant_id FK column with index
  - query_for_tenant(tenant_id) classmethod
  - Composite index macro helper
"""

from app.models import db


class TenantModel(db.Model):
    """Abstract base for tenant-scoped tables."""
    __abstract__ = True

    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    @classmethod
    def query_for_tenant(cls, tenant_id):
        """Return a query filtered by tenant_id."""
        return cls.query.filter_by(tenant_id=tenant_id)

    @classmethod
    def tenant_composite_index(cls, *extra_cols):
        """Helper to build (tenant_id, ...) composite index name+tuple."""
        name = f"ix_{cls.__tablename__}_tenant_{'_'.join(extra_cols)}"
        cols = ("tenant_id",) + extra_cols
        return db.Index(name, *cols)
