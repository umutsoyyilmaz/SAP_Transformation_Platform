"""
Discover-phase governance document models.

Split from program.py (B1 refactor) — ProjectCharter, SystemLandscape, ScopeAssessment.
"""

from datetime import datetime, timezone

from app.models import db


# ── ProjectCharter ───────────────────────────────────────────────────────────


class ProjectCharter(db.Model):
    """SAP Activate Discover phase output: project justification and key decisions.

    At most one charter is created per Program. The charter must have
    status='approved' to pass the Discover Gate.

    Lifecycle: draft → in_review → approved | rejected
    """

    __tablename__ = "project_charters"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="At most one charter per program — unique constraint",
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Project justification
    project_objective = db.Column(db.Text, nullable=True, comment="Project business objective")
    business_drivers = db.Column(db.Text, nullable=True, comment="Why now? Triggering factors")
    expected_benefits = db.Column(db.Text, nullable=True, comment="Expected business benefits")
    key_risks = db.Column(db.Text, nullable=True, comment="Known initial risks")

    # Scope summary
    in_scope_summary = db.Column(db.Text, nullable=True, comment="Areas included in scope")
    out_of_scope_summary = db.Column(db.Text, nullable=True, comment="Areas excluded from scope")
    affected_countries = db.Column(db.String(500), nullable=True, comment="CSV country codes: TR,DE,NL")
    affected_sap_modules = db.Column(db.String(500), nullable=True, comment="CSV module codes: FI,MM,SD")

    # Project type and timeline
    project_type = db.Column(
        db.String(30),
        nullable=False,
        default="greenfield",
        comment="greenfield | brownfield | bluefield | selective_data_transition",
    )
    target_go_live_date = db.Column(db.Date, nullable=True)
    estimated_duration_months = db.Column(db.Integer, nullable=True)

    # Approval status
    status = db.Column(
        db.String(20),
        nullable=False,
        default="draft",
        comment="draft | in_review | approved | rejected",
    )
    approved_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    approval_notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        """Serialize charter excluding no sensitive fields; dates as ISO strings."""
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "project_objective": self.project_objective,
            "business_drivers": self.business_drivers,
            "expected_benefits": self.expected_benefits,
            "key_risks": self.key_risks,
            "in_scope_summary": self.in_scope_summary,
            "out_of_scope_summary": self.out_of_scope_summary,
            "affected_countries": self.affected_countries,
            "affected_sap_modules": self.affected_sap_modules,
            "project_type": self.project_type,
            "target_go_live_date": self.target_go_live_date.isoformat() if self.target_go_live_date else None,
            "estimated_duration_months": self.estimated_duration_months,
            "status": self.status,
            "approved_by_id": self.approved_by_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approval_notes": self.approval_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<ProjectCharter program={self.program_id} status={self.status}>"


# ── SystemLandscape ──────────────────────────────────────────────────────────


class SystemLandscape(db.Model):
    """AS-IS system landscape record.

    Multiple systems can be registered per program. Which SAP/non-SAP
    systems exist, which will be decommissioned or remain integrated after go-live?

    Scoped by tenant_id — WHERE tenant_id = :tid is required in all queries.
    """

    __tablename__ = "system_landscapes"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    system_name = db.Column(db.String(100), nullable=False)
    system_type = db.Column(
        db.String(30),
        nullable=False,
        default="non_sap",
        comment="sap_erp | s4hana | non_sap | middleware | cloud | legacy",
    )
    role = db.Column(
        db.String(20),
        nullable=False,
        default="source",
        comment="source | target | interface | decommission | keep",
    )
    vendor = db.Column(db.String(100), nullable=True)
    version = db.Column(db.String(50), nullable=True)
    environment = db.Column(
        db.String(20),
        nullable=False,
        default="prod",
        comment="dev | test | q | prod",
    )
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Composite index — most queries will filter by tenant + program
    __table_args__ = (
        db.Index("ix_system_landscape_tenant_program", "tenant_id", "program_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "system_name": self.system_name,
            "system_type": self.system_type,
            "role": self.role,
            "vendor": self.vendor,
            "version": self.version,
            "environment": self.environment,
            "description": self.description,
            "notes": self.notes,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<SystemLandscape {self.system_name} role={self.role}>"


# ── ScopeAssessment ──────────────────────────────────────────────────────────


class ScopeAssessment(db.Model):
    """Initial scope assessment per SAP module (Discover phase).

    Which modules are in scope, what is the complexity and estimated effort?
    At most one record per program + module combination — upsert logic
    is implemented in discover_service.save_scope_assessment().

    Scoped by tenant_id — WHERE tenant_id = :tid is required in all queries.
    """

    __tablename__ = "scope_assessments"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    sap_module = db.Column(db.String(10), nullable=False, comment="FI, MM, SD, PP, CO, HR, etc.")
    is_in_scope = db.Column(db.Boolean, nullable=False, default=True)
    complexity = db.Column(
        db.String(10),
        nullable=True,
        comment="low | medium | high | very_high",
    )
    estimated_requirements = db.Column(db.Integer, nullable=True, comment="Estimated number of requirements")
    estimated_gaps = db.Column(db.Integer, nullable=True, comment="Estimated number of gaps (WRICEF)")
    notes = db.Column(db.Text, nullable=True)
    assessment_basis = db.Column(
        db.String(30),
        nullable=True,
        comment="workshop | document_review | interview | expert_estimate",
    )
    assessed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assessed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Composite unique: one assessment per module per program per tenant
    __table_args__ = (
        db.UniqueConstraint("program_id", "tenant_id", "sap_module", name="uq_scope_program_tenant_module"),
        db.Index("ix_scope_assessment_tenant_program", "tenant_id", "program_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "program_id": self.program_id,
            "tenant_id": self.tenant_id,
            "sap_module": self.sap_module,
            "is_in_scope": self.is_in_scope,
            "complexity": self.complexity,
            "estimated_requirements": self.estimated_requirements,
            "estimated_gaps": self.estimated_gaps,
            "notes": self.notes,
            "assessment_basis": self.assessment_basis,
            "assessed_by_id": self.assessed_by_id,
            "assessed_at": self.assessed_at.isoformat() if self.assessed_at else None,
        }

    def __repr__(self) -> str:
        return f"<ScopeAssessment program={self.program_id} module={self.sap_module}>"
