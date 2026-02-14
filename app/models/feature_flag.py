"""
Feature Flag Model — Sprint 9 (Item 4.1)

Tenant-level feature toggles. Each flag has a global default
and can be overridden per tenant.
"""

from datetime import datetime, timezone

from app.models import db


class FeatureFlag(db.Model):
    """Global feature flag definition."""
    __tablename__ = "feature_flags"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)  # e.g. "ai_assistant"
    display_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    default_enabled = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), default="general")  # general, ai, beta, experimental
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    overrides = db.relationship(
        "TenantFeatureFlag", back_populates="feature_flag",
        lazy="dynamic", cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "display_name": self.display_name,
            "description": self.description,
            "default_enabled": self.default_enabled,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TenantFeatureFlag(db.Model):
    """Per-tenant override for a feature flag."""
    __tablename__ = "tenant_feature_flags"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer, db.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    feature_flag_id = db.Column(
        db.Integer, db.ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False,
    )
    is_enabled = db.Column(db.Boolean, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("tenant_id", "feature_flag_id", name="uq_tenant_feature_flag"),
        db.Index("ix_tenant_feature_flags_tenant", "tenant_id"),
    )

    # Relationships
    feature_flag = db.relationship("FeatureFlag", back_populates="overrides")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "feature_flag_id": self.feature_flag_id,
            "key": self.feature_flag.key if self.feature_flag else None,
            "is_enabled": self.is_enabled,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
