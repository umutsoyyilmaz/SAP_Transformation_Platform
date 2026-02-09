"""
SAP Transformation Management Platform
RAID domain models — Sprint 6.

Models:
    - RaidItem: base model for all RAID entities
    - Risk: Risks with probability × impact scoring, mitigation & contingency
    - Action: Tracked action items with due dates and linked entities
    - Issue: Current problems requiring resolution
    - Decision: Architecture / design decisions with rationale

Architecture chain: Program → Risk / Action / Issue / Decision
"""

from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

RAID_TYPES = {"risk", "action", "issue", "decision"}

RISK_STATUSES = {"identified", "analysed", "mitigating", "accepted", "closed", "expired"}
ACTION_STATUSES = {"open", "in_progress", "completed", "cancelled", "overdue"}
ISSUE_STATUSES = {"open", "investigating", "escalated", "resolved", "closed"}
DECISION_STATUSES = {"proposed", "pending_approval", "approved", "rejected", "superseded"}

RISK_CATEGORIES = {"technical", "organisational", "commercial", "external", "schedule", "resource", "scope"}
RISK_RESPONSES = {"avoid", "transfer", "mitigate", "accept", "escalate"}

PRIORITY_LEVELS = {"critical", "high", "medium", "low"}
SEVERITY_LEVELS = {"critical", "major", "moderate", "minor"}

ACTION_TYPES = {"preventive", "corrective", "detective", "improvement", "follow_up"}


# ── Risk Scoring Matrix ─────────────────────────────────────────────────────

def calculate_risk_score(probability: int, impact: int) -> int:
    """
    Calculate risk score: probability (1-5) × impact (1-5).
    Range: 1–25.
    """
    p = max(1, min(5, int(probability or 1)))
    i = max(1, min(5, int(impact or 1)))
    return p * i


def risk_rag_status(score: int) -> str:
    """
    RAG classification based on risk score.
      1-4  → green  (Low)
      5-9  → amber  (Medium)
      10-15 → orange (High)
      16-25 → red    (Critical)
    """
    if score <= 4:
        return "green"
    elif score <= 9:
        return "amber"
    elif score <= 15:
        return "orange"
    return "red"


# ═══════════════════════════════════════════════════════════════════════════
#  RISK
# ═══════════════════════════════════════════════════════════════════════════

class Risk(db.Model):
    """
    A risk identified and tracked for a programme.

    Risk score = probability × impact (1-25) with RAG classification.
    """

    __tablename__ = "risks"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    code = db.Column(db.String(30), unique=True, nullable=False, comment="Auto-generated: RSK-001")
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(30), default="identified", index=True)
    owner = db.Column(db.String(150), default="")
    priority = db.Column(db.String(20), default="medium")

    # Risk-specific
    probability = db.Column(db.Integer, default=3, comment="1-5 scale")
    impact = db.Column(db.Integer, default=3, comment="1-5 scale")
    risk_score = db.Column(db.Integer, default=9, comment="probability × impact")
    rag_status = db.Column(db.String(10), default="amber", comment="green/amber/orange/red")
    risk_category = db.Column(db.String(30), default="technical")
    risk_response = db.Column(db.String(20), default="mitigate")
    mitigation_plan = db.Column(db.Text, default="")
    contingency_plan = db.Column(db.Text, default="")
    trigger_event = db.Column(db.String(300), default="")

    # References
    workstream_id = db.Column(db.Integer, db.ForeignKey("workstreams.id", ondelete="SET NULL"), nullable=True, index=True)
    phase_id = db.Column(db.Integer, db.ForeignKey("phases.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def recalculate_score(self):
        """Recalculate risk_score and rag_status from probability & impact."""
        self.risk_score = calculate_risk_score(self.probability, self.impact)
        self.rag_status = risk_rag_status(self.risk_score)

    def to_dict(self):
        return {
            "id": self.id,
            "raid_type": "risk",
            "program_id": self.program_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "owner": self.owner,
            "priority": self.priority,
            "probability": self.probability,
            "impact": self.impact,
            "risk_score": self.risk_score,
            "rag_status": self.rag_status,
            "risk_category": self.risk_category,
            "risk_response": self.risk_response,
            "mitigation_plan": self.mitigation_plan,
            "contingency_plan": self.contingency_plan,
            "trigger_event": self.trigger_event,
            "workstream_id": self.workstream_id,
            "phase_id": self.phase_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Risk {self.code}: {self.title[:40]}>"


# ═══════════════════════════════════════════════════════════════════════════
#  ACTION
# ═══════════════════════════════════════════════════════════════════════════

class Action(db.Model):
    """
    A tracked action item linked to a programme.
    Can reference another RAID entity or any project entity.
    """

    __tablename__ = "actions"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    code = db.Column(db.String(30), unique=True, nullable=False, comment="Auto-generated: ACT-001")
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(30), default="open", index=True)
    owner = db.Column(db.String(150), default="")
    priority = db.Column(db.String(20), default="medium")
    action_type = db.Column(db.String(30), default="corrective")

    # Dates
    due_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.Date, nullable=True)

    # Linked entity
    linked_entity_type = db.Column(db.String(30), default="", comment="risk/issue/requirement/...")
    linked_entity_id = db.Column(db.Integer, nullable=True)

    # References
    workstream_id = db.Column(db.Integer, db.ForeignKey("workstreams.id", ondelete="SET NULL"), nullable=True, index=True)
    phase_id = db.Column(db.Integer, db.ForeignKey("phases.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "raid_type": "action",
            "program_id": self.program_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "owner": self.owner,
            "priority": self.priority,
            "action_type": self.action_type,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
            "linked_entity_type": self.linked_entity_type,
            "linked_entity_id": self.linked_entity_id,
            "workstream_id": self.workstream_id,
            "phase_id": self.phase_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Action {self.code}: {self.title[:40]}>"


# ═══════════════════════════════════════════════════════════════════════════
#  ISSUE
# ═══════════════════════════════════════════════════════════════════════════

class Issue(db.Model):
    """
    A current problem / impediment affecting the programme.
    """

    __tablename__ = "issues"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    code = db.Column(db.String(30), unique=True, nullable=False, comment="Auto-generated: ISS-001")
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(30), default="open", index=True)
    owner = db.Column(db.String(150), default="")
    priority = db.Column(db.String(20), default="medium")

    # Issue-specific
    severity = db.Column(db.String(20), default="moderate")
    escalation_path = db.Column(db.String(300), default="")
    root_cause = db.Column(db.Text, default="")
    resolution = db.Column(db.Text, default="")
    resolution_date = db.Column(db.Date, nullable=True)

    # References
    workstream_id = db.Column(db.Integer, db.ForeignKey("workstreams.id", ondelete="SET NULL"), nullable=True, index=True)
    phase_id = db.Column(db.Integer, db.ForeignKey("phases.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "raid_type": "issue",
            "program_id": self.program_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "owner": self.owner,
            "priority": self.priority,
            "severity": self.severity,
            "escalation_path": self.escalation_path,
            "root_cause": self.root_cause,
            "resolution": self.resolution,
            "resolution_date": self.resolution_date.isoformat() if self.resolution_date else None,
            "workstream_id": self.workstream_id,
            "phase_id": self.phase_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Issue {self.code}: {self.title[:40]}>"


# ═══════════════════════════════════════════════════════════════════════════
#  DECISION
# ═══════════════════════════════════════════════════════════════════════════

class Decision(db.Model):
    """
    A design / architecture / process decision record (Decision Log).
    """

    __tablename__ = "decisions"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    code = db.Column(db.String(30), unique=True, nullable=False, comment="Auto-generated: DEC-001")
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(30), default="proposed", index=True)
    owner = db.Column(db.String(150), default="")
    priority = db.Column(db.String(20), default="medium")

    # Decision-specific
    decision_date = db.Column(db.Date, nullable=True)
    decision_owner = db.Column(db.String(150), default="", comment="Final approver / decision maker")
    alternatives = db.Column(db.Text, default="", comment="JSON or freetext list of alternatives")
    rationale = db.Column(db.Text, default="")
    impact_description = db.Column(db.Text, default="")
    reversible = db.Column(db.Boolean, default=True)

    # References
    workstream_id = db.Column(db.Integer, db.ForeignKey("workstreams.id", ondelete="SET NULL"), nullable=True, index=True)
    phase_id = db.Column(db.Integer, db.ForeignKey("phases.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "raid_type": "decision",
            "program_id": self.program_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "owner": self.owner,
            "priority": self.priority,
            "decision_date": self.decision_date.isoformat() if self.decision_date else None,
            "decision_owner": self.decision_owner,
            "alternatives": self.alternatives,
            "rationale": self.rationale,
            "impact_description": self.impact_description,
            "reversible": self.reversible,
            "workstream_id": self.workstream_id,
            "phase_id": self.phase_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Decision {self.code}: {self.title[:40]}>"


# ═══════════════════════════════════════════════════════════════════════════
#  AUTO-CODE GENERATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _next_code(model_class, prefix: str) -> str:
    """
    Generate the next sequential code for a RAID entity.
    E.g. RSK-001, RSK-002, ...

    Race-safe: uses MAX(id) ordering and SELECT ... FOR UPDATE where supported.
    Callers should handle IntegrityError and retry if a unique constraint exists.
    """
    full_prefix = prefix + "-"
    last = (
        model_class.query
        .filter(model_class.code.like(f"{full_prefix}%"))
        .order_by(model_class.id.desc())
        .with_for_update(skip_locked=True)
        .first()
    )
    if last and last.code.startswith(full_prefix):
        try:
            num = int(last.code.split("-")[1]) + 1
        except (IndexError, ValueError):
            num = 1
    else:
        num = 1
    return f"{prefix}-{num:03d}"


def next_risk_code() -> str:
    return _next_code(Risk, "RSK")


def next_action_code() -> str:
    return _next_code(Action, "ACT")


def next_issue_code() -> str:
    return _next_code(Issue, "ISS")


def next_decision_code() -> str:
    return _next_code(Decision, "DEC")
