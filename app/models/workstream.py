"""
Workstream, TeamMember, Committee models.

Split from program.py (B1 refactor) — team / organizational structure.
"""

from datetime import datetime, timezone

from app.models import db


# ── Workstream ───────────────────────────────────────────────────────────────


class Workstream(db.Model):
    """
    Functional or technical work stream within a program.
    E.g. FI/CO, MM/PP, SD, HCM, Basis/Tech, Data Migration, Testing, Change Mgmt.
    """

    __tablename__ = "workstreams"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Sprint 7 schema slice: project scope is mandatory",
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    ws_type = db.Column(
        db.String(30),
        default="functional",
        comment="functional | technical | cross_cutting",
    )
    lead_name = db.Column(db.String(100), default="")
    status = db.Column(
        db.String(30),
        default="active",
        comment="active | on_hold | completed",
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
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "ws_type": self.ws_type,
            "lead_name": self.lead_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Workstream {self.id}: {self.name}>"


# ── TeamMember ───────────────────────────────────────────────────────────────


class TeamMember(db.Model):
    """
    Person assigned to a program with role and RACI designation.
    """

    __tablename__ = "team_members"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Sprint 7 schema slice: project scope is mandatory",
    )
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), default="")
    role = db.Column(
        db.String(50),
        default="team_member",
        comment="program_manager | project_lead | stream_lead | consultant | developer | team_member",
    )
    raci = db.Column(
        db.String(20),
        default="informed",
        comment="responsible | accountable | consulted | informed",
    )
    workstream_id = db.Column(
        db.Integer, db.ForeignKey("workstreams.id", ondelete="SET NULL"), nullable=True,
    )
    organization = db.Column(db.String(100), default="", comment="Company / partner name")
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship to workstream (optional)
    workstream = db.relationship("Workstream", backref="team_members")

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "raci": self.raci,
            "workstream_id": self.workstream_id,
            "organization": self.organization,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<TeamMember {self.id}: {self.name} ({self.role})>"


# ── Committee ────────────────────────────────────────────────────────────────


class Committee(db.Model):
    """
    Governance / steering committee for a program.
    E.g. SteerCo, Change Advisory Board, Architecture Review Board.
    """

    __tablename__ = "committees"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Sprint 7 schema slice: project scope is mandatory",
    )
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default="")
    committee_type = db.Column(
        db.String(50),
        default="steering",
        comment="steering | advisory | review | working_group",
    )
    meeting_frequency = db.Column(
        db.String(30),
        default="weekly",
        comment="daily | weekly | biweekly | monthly | ad_hoc",
    )
    chair_name = db.Column(db.String(100), default="")

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
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "committee_type": self.committee_type,
            "meeting_frequency": self.meeting_frequency,
            "chair_name": self.chair_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Committee {self.id}: {self.name}>"
