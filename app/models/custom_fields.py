"""F9 — Custom Fields & Layout Engine models."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models import db

try:
    from sqlalchemy import JSON
except ImportError:
    from sqlalchemy.types import JSON


def _utcnow():
    return datetime.now(timezone.utc)


# ── 9.1 Custom Field Definition ──────────────────────────────────

class CustomFieldDefinition(db.Model):
    """Dynamic field definition per entity type within a program."""

    __tablename__ = "custom_field_definitions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"))
    entity_type = Column(
        String(30), default="test_case"
    )  # test_case | defect | test_plan | test_cycle | ...
    field_name = Column(String(100), nullable=False)
    field_label = Column(String(200), default="")
    field_type = Column(
        String(30), default="text"
    )  # text | number | date | select | multiselect | checkbox | url | textarea
    options = Column(JSON, default=list)  # For select: [{"value":"v","label":"l"},...]
    is_required = Column(Boolean, default=False)
    is_filterable = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    default_value = Column(String(500), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    values = relationship(
        "CustomFieldValue",
        backref="field_definition",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        Index("ix_cfd_program_entity", "program_id", "entity_type"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "entity_type": self.entity_type,
            "field_name": self.field_name,
            "field_label": self.field_label,
            "field_type": self.field_type,
            "options": self.options or [],
            "is_required": self.is_required,
            "is_filterable": self.is_filterable,
            "sort_order": self.sort_order,
            "default_value": self.default_value,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── 9.1b Custom Field Value ──────────────────────────────────────

class CustomFieldValue(db.Model):
    """Stored value for a custom field on a specific entity."""

    __tablename__ = "custom_field_values"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=True)
    field_id = Column(
        Integer,
        ForeignKey("custom_field_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type = Column(String(30), default="test_case")
    entity_id = Column(Integer, nullable=False)
    value = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("ix_cfv_entity", "entity_type", "entity_id"),
        Index("ix_cfv_field_entity", "field_id", "entity_type", "entity_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "field_id": self.field_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "value": self.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── 9.2 Layout Configuration ─────────────────────────────────────

class LayoutConfig(db.Model):
    """JSON-driven layout configuration for entity detail views."""

    __tablename__ = "layout_configs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"))
    entity_type = Column(String(30), default="test_case")
    name = Column(String(200), default="Default")
    is_default = Column(Boolean, default=False)
    sections = Column(JSON, default=list)
    """
    sections: [
        {
            "id": "basic",
            "title": "Basic Info",
            "visible": true,
            "sort_order": 0,
            "fields": ["title", "description", "cf_12", "cf_13"]
        },
        ...
    ]
    """
    created_by = Column(String(200), default="system")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("ix_lc_program_entity", "program_id", "entity_type"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "is_default": self.is_default,
            "sections": self.sections or [],
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
