"""
Soft Delete Mixin — Sprint 10 (Item 4.7)

Adds `deleted_at` timestamp column and query helpers for soft delete.
Models that include this mixin will mark records as deleted rather
than physically removing them.

Usage:
    class MyModel(SoftDeleteMixin, db.Model):
        ...

    # Soft delete
    obj.soft_delete()
    db.session.commit()

    # Query only active records
    MyModel.query_active().all()

    # Include deleted
    MyModel.query.all()

    # Restore
    obj.restore()
    db.session.commit()
"""

from datetime import datetime, timezone

from app.models import db


class SoftDeleteMixin:
    """Mixin that adds soft delete support to any SQLAlchemy model."""

    deleted_at = db.Column(db.DateTime, nullable=True, default=None, index=True)

    def soft_delete(self):
        """Mark this record as deleted."""
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore a soft-deleted record."""
        self.deleted_at = None

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    @classmethod
    def query_active(cls):
        """Return a query that excludes soft-deleted records."""
        return cls.query.filter(cls.deleted_at.is_(None))

    @classmethod
    def query_deleted(cls):
        """Return only soft-deleted records."""
        return cls.query.filter(cls.deleted_at.isnot(None))
