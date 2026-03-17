"""
Stakeholder and CommunicationPlanEntry models.

Split from program.py (B1 refactor) — FDD-I08 / S5-05.
"""

from datetime import datetime, timezone

from app.models import db


# ═════════════════════════════════════════════════════════════════════════════
# Stakeholder (FDD-I08 / S5-05)
# ═════════════════════════════════════════════════════════════════════════════


class Stakeholder(db.Model):
    """
    A person or group with a stake in the SAP transformation program.

    Engagement strategy is auto-computed from influence × interest:
      - high/high   → manage_closely
      - high/low    → keep_satisfied
      - low/high    → keep_informed
      - low/low     → monitor

    Lifecycle tracking: current_sentiment helps the change manager monitor
    reaction shifts over time; last/next_contact_date drives contact cadence.
    """

    __tablename__ = "stakeholders"

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
        nullable=False,  # Audit requirement: always tenant-scoped
        index=True,
    )

    # ── Identity ──────────────────────────────────────────────────────────
    name = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    organization = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)

    # ── Classification ────────────────────────────────────────────────────
    stakeholder_type = db.Column(
        db.String(30),
        nullable=False,
        default="internal",
        comment="internal | external | vendor | sponsor | key_user | steering | regulator",
    )
    sap_module_interest = db.Column(
        db.String(200),
        nullable=True,
        comment="Comma-separated SAP module codes, e.g. 'FI,MM,SD'",
    )

    # ── Influence/Interest matrix ─────────────────────────────────────────
    influence_level = db.Column(
        db.String(10),
        nullable=False,
        default="medium",
        comment="high | medium | low",
    )
    interest_level = db.Column(
        db.String(10),
        nullable=False,
        default="medium",
        comment="high | medium | low",
    )
    engagement_strategy = db.Column(
        db.String(30),
        nullable=True,
        comment="Auto-computed: manage_closely | keep_satisfied | keep_informed | monitor",
    )

    # ── Sentiment tracking ────────────────────────────────────────────────
    current_sentiment = db.Column(
        db.String(20),
        nullable=True,
        comment="champion | supporter | neutral | resistant | blocker",
    )

    # ── Contact cadence ──────────────────────────────────────────────────
    last_contact_date = db.Column(db.Date, nullable=True)
    next_contact_date = db.Column(db.Date, nullable=True)
    contact_frequency = db.Column(
        db.String(30),
        nullable=True,
        comment="weekly | biweekly | monthly | quarterly | as_needed",
    )
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

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

    # ── Constraints & Indexes ─────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "influence_level IN ('high','medium','low')",
            name="ck_stakeholder_influence",
        ),
        db.CheckConstraint(
            "interest_level IN ('high','medium','low')",
            name="ck_stakeholder_interest",
        ),
        db.Index("ix_stakeholder_tenant_program", "tenant_id", "program_id"),
    )

    SENSITIVE_FIELDS: frozenset[str] = frozenset()

    def to_dict(self) -> dict:
        result = {}
        for c in self.__table__.columns:
            if c.name in self.SENSITIVE_FIELDS:
                continue
            val = getattr(self, c.name)
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            result[c.name] = val
        return result

    def __repr__(self) -> str:
        return f"<Stakeholder id={self.id} name={self.name!r} program={self.program_id}>"


# ═════════════════════════════════════════════════════════════════════════════
# CommunicationPlanEntry (FDD-I08 / S5-05)
# ═════════════════════════════════════════════════════════════════════════════


class CommunicationPlanEntry(db.Model):
    """
    A scheduled communication event in the program's change management plan.

    Entries may target a specific Stakeholder (stakeholder_id set) or a
    broader audience_group (e.g. 'All Key Users', 'Steering Committee').
    They follow a status lifecycle: planned → sent → completed | cancelled.

    SAP Activate phase alignment ensures communications are timed to the
    correct methodology phase (Discover → Explore → Realize → Deploy → Run).
    """

    __tablename__ = "communication_plan_entries"

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
        nullable=False,  # Audit requirement
        index=True,
    )
    stakeholder_id = db.Column(
        db.Integer,
        db.ForeignKey("stakeholders.id", ondelete="SET NULL"),
        nullable=True,
        comment="Null = group/audience communication, not individual-targeted",
    )

    # ── Communication content ─────────────────────────────────────────────
    audience_group = db.Column(
        db.String(200),
        nullable=True,
        comment="e.g. 'All Key Users', 'Finance Team', 'IT Department'",
    )
    communication_type = db.Column(
        db.String(50),
        nullable=True,
        comment="email | workshop | town_hall | newsletter | training | demo | status_update",
    )
    subject = db.Column(db.String(300), nullable=False)
    channel = db.Column(
        db.String(100),
        nullable=True,
        comment="Delivery channel: email | teams | sharepoint | in_person | video_call",
    )
    responsible_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Scheduling ────────────────────────────────────────────────────────
    frequency = db.Column(
        db.String(30),
        nullable=True,
        comment="one_time | weekly | biweekly | monthly | per_milestone",
    )
    sap_activate_phase = db.Column(
        db.String(20),
        nullable=True,
        comment="discover | explore | realize | deploy | run",
    )
    planned_date = db.Column(db.Date, nullable=True)
    actual_date = db.Column(db.Date, nullable=True)

    # ── Status ────────────────────────────────────────────────────────────
    status = db.Column(
        db.String(20),
        nullable=False,
        default="planned",
        comment="planned | sent | completed | cancelled",
    )
    notes = db.Column(db.Text, nullable=True)

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

    # ── Constraints & Indexes ─────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('planned','sent','completed','cancelled')",
            name="ck_comm_plan_entry_status",
        ),
        db.Index("ix_comm_plan_tenant_program", "tenant_id", "program_id"),
        db.Index("ix_comm_plan_stakeholder", "stakeholder_id"),
    )

    SENSITIVE_FIELDS: frozenset[str] = frozenset()

    def to_dict(self) -> dict:
        result = {}
        for c in self.__table__.columns:
            if c.name in self.SENSITIVE_FIELDS:
                continue
            val = getattr(self, c.name)
            if hasattr(val, "isoformat"):
                val = val.isoformat()
            result[c.name] = val
        return result

    def __repr__(self) -> str:
        return f"<CommunicationPlanEntry id={self.id} subject={self.subject!r} status={self.status}>"
