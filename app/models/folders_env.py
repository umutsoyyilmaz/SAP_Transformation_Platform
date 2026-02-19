"""
FAZ 6 — Hierarchical Folders, Bulk Operations & Environment Matrix

Models:
  - TestEnvironment: Test execution environment/platform definition
  - ExecutionEnvironmentResult: Per-environment execution result
  - SavedSearch: Saved search/filter configuration
"""

from datetime import datetime, timezone

from app.models import db


class TestEnvironment(db.Model):
    """Test execution environment/platform definition (QMetry-parity)."""

    __tablename__ = "test_environments"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(
        db.String(100),
        nullable=False,
        comment="e.g. 'Chrome 120 / Windows 11', 'SAP QAS'",
    )
    env_type = db.Column(
        db.String(30),
        default="sap_system",
        comment="browser | os | device | sap_system | custom",
    )
    properties = db.Column(
        db.JSON,
        default=dict,
        comment='{"browser": "chrome", "version": "120", "os": "win11"}',
    )
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    execution_results = db.relationship(
        "ExecutionEnvironmentResult",
        backref="environment",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "env_type": self.env_type,
            "properties": self.properties or {},
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ExecutionEnvironmentResult(db.Model):
    """Execution result per environment — enables TC × Environment matrix."""

    __tablename__ = "execution_environment_results"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    execution_id = db.Column(
        db.Integer,
        db.ForeignKey("test_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    environment_id = db.Column(
        db.Integer,
        db.ForeignKey("test_environments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = db.Column(
        db.String(20),
        default="not_run",
        comment="pass | fail | blocked | not_run",
    )
    executed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    executed_by = db.Column(
        db.Integer,
        db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes = db.Column(db.Text, default="")
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    execution = db.relationship("TestExecution", backref="environment_results")
    executor = db.relationship("TeamMember", foreign_keys=[executed_by])

    def to_dict(self):
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "environment_id": self.environment_id,
            "environment_name": self.environment.name if self.environment else None,
            "status": self.status,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "executed_by": self.executed_by,
            "notes": self.notes,
        }


class SavedSearch(db.Model):
    """Saved search/filter configuration — shareable with team."""

    __tablename__ = "saved_searches"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = db.Column(
        db.Integer,
        db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    name = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(
        db.String(30),
        nullable=False,
        comment="test_case | defect | execution | test_plan | test_cycle",
    )
    filters = db.Column(
        db.JSON,
        default=dict,
        comment='{"status": ["fail"], "module": "FI", "date_range": "7d"}',
    )
    columns = db.Column(
        db.JSON,
        default=list,
        comment="Visible column configuration",
    )
    sort_by = db.Column(db.String(50), default="")
    is_public = db.Column(db.Boolean, default=False, comment="Share with team")
    is_pinned = db.Column(db.Boolean, default=False, comment="Show in sidebar")
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    creator = db.relationship("TeamMember", foreign_keys=[created_by])

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "created_by": self.created_by,
            "name": self.name,
            "entity_type": self.entity_type,
            "filters": self.filters or {},
            "columns": self.columns or [],
            "sort_by": self.sort_by,
            "is_public": self.is_public,
            "is_pinned": self.is_pinned,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
