"""
SAP Transformation Management Platform
Reporting & Dashboard Models — F5 Advanced Reporting.

Models:
    - ReportDefinition: Saved report configuration (preset / custom)
    - DashboardLayout: Per-user dashboard gadget arrangement
"""

from datetime import datetime, timezone

from app.models import db


class ReportDefinition(db.Model):
    """Saved report configuration — preset or custom."""

    __tablename__ = "report_definitions"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True, index=True,
        comment="NULL → system-wide preset; non-NULL → program-specific",
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(
        db.String(50), default="custom", index=True,
        comment="coverage | execution | defect | traceability | ai_insights | plan | custom",
    )
    query_type = db.Column(
        db.String(20), default="preset",
        comment="preset | builder",
    )
    query_config = db.Column(
        db.JSON, nullable=True,
        comment="Filters, grouping, sorts — depends on query_type",
    )
    chart_type = db.Column(
        db.String(30), default="table",
        comment="table | bar | line | pie | donut | gauge | heatmap | kpi | treemap",
    )
    chart_config = db.Column(
        db.JSON, nullable=True,
        comment="Chart-specific options: colors, axes, thresholds",
    )
    is_preset = db.Column(
        db.Boolean, default=False,
        comment="True → system preset, cannot be deleted by user",
    )
    is_public = db.Column(
        db.Boolean, default=False,
        comment="True → visible to all users in the program",
    )
    created_by = db.Column(db.String(100), default="")
    schedule = db.Column(
        db.JSON, nullable=True,
        comment="Optional: {cron: '0 8 * * 1', recipients: ['a@b.c']}",
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "query_type": self.query_type,
            "query_config": self.query_config,
            "chart_type": self.chart_type,
            "chart_config": self.chart_config,
            "is_preset": self.is_preset,
            "is_public": self.is_public,
            "created_by": self.created_by,
            "schedule": self.schedule,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<ReportDefinition {self.id}: {self.name}>"


class DashboardLayout(db.Model):
    """Per-user dashboard gadget arrangement."""

    __tablename__ = "dashboard_layouts"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="CASCADE"),
        nullable=True, index=True,
        comment="NULL → program default layout",
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    layout = db.Column(
        db.JSON, nullable=True,
        comment='[{"gadget_id": "pass_rate_gauge", "x":0, "y":0, "w":4, "h":3, "config":{}}]',
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "program_id": self.program_id,
            "layout": self.layout or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<DashboardLayout {self.id}: user={self.user_id} program={self.program_id}>"
