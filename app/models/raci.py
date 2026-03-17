"""
RACI Matrix models — RaciActivity and RaciEntry.

Split from program.py (B1 refactor) — S3-03 / FDD-F06.
"""

from datetime import datetime, timezone

from app.models import db


# ── RaciActivity ─────────────────────────────────────────────────────────────


class RaciActivity(db.Model):
    """A row in the RACI matrix: a named activity within a program.

    Activities are the *rows* of the matrix.  They may be created manually or
    bulk-imported from the SAP Activate template.  `is_template` marks imported
    rows so they can be distinguished from user-defined ones.

    Lifecycle: activities belong to a specific program+tenant scope.
    They are filtered by `sap_activate_phase` or `workstream_id` on the UI.
    """

    __tablename__ = "raci_activities"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Sprint 7 secondary slice: project scope is mandatory",
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(
        db.String(50),
        nullable=True,
        comment="governance | technical | testing | data | training | cutover",
    )
    sap_activate_phase = db.Column(
        db.String(20),
        nullable=True,
        comment="discover | prepare | explore | realize | deploy | run",
    )
    workstream_id = db.Column(
        db.Integer,
        db.ForeignKey("workstreams.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_template = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="True for rows imported from the SAP Activate template",
    )
    sort_order = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.Index("ix_raci_activity_tenant_program", "tenant_id", "program_id"),
        db.Index("ix_raci_activity_tenant_project", "tenant_id", "project_id"),
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return f"<RaciActivity id={self.id} name={self.name!r} program={self.program_id}>"


# ── RaciEntry ────────────────────────────────────────────────────────────────


class RaciEntry(db.Model):
    """A single cell in the RACI matrix: one team-member's role for one activity.

    The four RACI roles are:
      R (Responsible)  — does the work.
      A (Accountable)  — ultimately answerable; only ONE per activity enforced
                         at the service layer.
      C (Consulted)    — provides input; two-way communication.
      I (Informed)     — kept up to date; one-way communication.

    A null/absent row means no assignment for that (activity, member) pair.
    Deleting is handled by the service when `raci_role=None` is passed to
    `upsert_raci_entry`.

    Security: `tenant_id` is nullable=False — a missing tenant scope would allow
    cross-tenant data exposure, which is a GDPR/KVKK violation.
    """

    __tablename__ = "raci_entries"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Sprint 7 secondary slice: project scope is mandatory",
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,  # CRITICAL: must never be NULL — tenant isolation boundary
        index=True,
    )
    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("raci_activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    team_member_id = db.Column(
        db.Integer,
        db.ForeignKey("team_members.id", ondelete="CASCADE"),
        nullable=False,
    )
    raci_role = db.Column(
        db.String(1),
        nullable=False,
        comment="R | A | C | I",
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        db.Index("ix_raci_entry_program_activity", "program_id", "activity_id"),
        db.Index("ix_raci_entry_tenant_program", "tenant_id", "program_id"),
        db.Index("ix_raci_entry_project_activity", "project_id", "activity_id"),
        db.Index("ix_raci_entry_tenant_project", "tenant_id", "project_id"),
        # Unique constraint: one entry per (activity, team_member) pair
        db.UniqueConstraint(
            "activity_id",
            "team_member_id",
            name="uq_raci_entry_activity_member",
        ),
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return (
            f"<RaciEntry id={self.id} activity={self.activity_id}"
            f" member={self.team_member_id} role={self.raci_role}>"
        )
