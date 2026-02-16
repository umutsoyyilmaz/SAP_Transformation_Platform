"""
SAP Transformation Management Platform
Process domain models -- refactored hierarchy.

Hierarchy (SAP Signavio L1-L4):
    Program -> Scenario (=L1 Value Chain) -> Process L2 -> Process L3 -> Process L4
    Scenario replaces the old "L1 Process" wrapper.
    L3/L4 carry scope & fit-gap attributes.
    L4 is where Requirement / WRICEF / Test Case are born (SAP Activate).

Models:
    - Process:  L2 (Process Area) | L3 (E2E Process) | L4 (Sub Process)
    - RequirementProcessMapping:  N:M junction between Requirement <-> L3/L4 Process
    - Analysis: Fit-Gap assessment linked to an L3/L4 Process
"""

from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

PROCESS_LEVELS = {"L2", "L3", "L4"}

# L3/L4-specific enums
SCOPE_DECISIONS = {"in_scope", "out_of_scope", "deferred"}
FIT_GAP_RESULTS = {"fit", "gap", "partial_fit", "standard", ""}
L3_PRIORITIES = {"low", "medium", "high", "critical"}

# L2 scope confirmation
SCOPE_CONFIRMATIONS = {"confirmed", "pending", "excluded", ""}

# L4 Activate output types
ACTIVATE_OUTPUTS = {
    "configuration", "wricef", "std_process", "workflow_config",
    "custom_logic", "enhancement", "report", "form", "interface", "",
}

# WRICEF sub-types (when activate_output = wricef)
WRICEF_TYPES = {
    "workflow", "report", "interface", "conversion", "enhancement", "form", "",
}

# Test level values
TEST_LEVELS = {"unit", "sit", "uat", "unit,sit", "sit,uat", "unit,sit,uat", ""}

# Analysis
ANALYSIS_STATUSES = {"planned", "in_progress", "completed", "cancelled"}
ANALYSIS_TYPES = {"workshop", "fit_gap", "demo", "prototype", "review", "workshop_note"}

# Coverage types for Requirement ↔ L3 mapping
COVERAGE_TYPES = {"full", "partial", "none"}


class Process(db.Model):
    """
    SAP process hierarchy node -- Signavio L2/L3/L4.

    L1 = Scenario (separate table, Value Chain level).
    L2 = Process Area (e.g. Procure-to-Pay, Order-to-Cash)
    L3 = E2E Process (e.g. Direct Material Procurement) -- Fit-to-Standard workshop subject
    L4 = Sub Process (e.g. PR Approval, 3-Way Match) -- Requirement/WRICEF/Test birth point

    L3 & L4 carry scope & fit-gap attributes.
    L4 additionally carries activate_output, wricef_type, and test_levels.
    """

    __tablename__ = "processes"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scenario_id = db.Column(
        db.Integer, db.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    parent_id = db.Column(
        db.Integer, db.ForeignKey("processes.id", ondelete="CASCADE"),
        nullable=True, comment="L3->parent L2, L4->parent L3, L2->NULL",
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    level = db.Column(
        db.String(5), default="L2",
        comment="L2 (Process Area) | L3 (E2E Process) | L4 (Sub Process)",
    )
    process_id_code = db.Column(
        db.String(50), default="",
        comment="SAP process ID, e.g. O2C, P2P, RTR",
    )
    module = db.Column(
        db.String(50), default="",
        comment="SAP module: FI, CO, MM, SD, PP, etc.",
    )
    order = db.Column(db.Integer, default=0)

    # ── L2 scope confirmation ─────────────────────────────────────────────
    scope_confirmation = db.Column(
        db.String(30), default="",
        comment="confirmed | pending | excluded  (L2 only)",
    )

    # ── L3/L4 fields (scope & fit-gap) ───────────────────────────────────
    code = db.Column(
        db.String(50), default="",
        comment="Short code, e.g. 1OC, L4.3.1.1",
    )
    scope_decision = db.Column(
        db.String(30), default="",
        comment="in_scope | out_of_scope | deferred  (L3 only)",
    )
    fit_gap = db.Column(
        db.String(20), default="",
        comment="fit | gap | partial_fit | standard  (L3 only)",
    )
    sap_tcode = db.Column(
        db.String(50), default="",
        comment="SAP transaction code: VA01, ME21N, FB01  (L3 only)",
    )
    sap_reference = db.Column(
        db.String(100), default="",
        comment="SAP Best Practice reference ID  (L3 only)",
    )
    priority = db.Column(
        db.String(20), default="",
        comment="low | medium | high | critical  (L3/L4)",
    )

    # ── L3-specific ────────────────────────────────────────────────────────
    cloud_alm_ref = db.Column(
        db.String(100), default="",
        comment="Cloud ALM Solution Process reference  (L3)",
    )
    test_scope = db.Column(
        db.String(50), default="",
        comment="sit | uat | sit,uat  (L3 test scope)",
    )

    # ── L4-specific (SAP Activate output) ────────────────────────────────
    activate_output = db.Column(
        db.String(100), default="",
        comment="configuration | wricef | std_process | workflow_config | custom_logic  (L4)",
    )
    wricef_type = db.Column(
        db.String(50), default="",
        comment="workflow | report | interface | conversion | enhancement | form  (L4, when gap)",
    )
    test_levels = db.Column(
        db.String(100), default="",
        comment="unit | sit | uat | unit,sit | sit,uat | unit,sit,uat  (L4)",
    )

    notes = db.Column(db.Text, default="")

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    children = db.relationship(
        "Process", backref=db.backref("parent", remote_side="Process.id"),
        lazy="dynamic", cascade="all, delete-orphan",
    )
    analyses = db.relationship(
        "Analysis", backref="process", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    requirement_mappings = db.relationship(
        "RequirementProcessMapping", backref="process", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    # NOTE: backlog_items relationship removed — WRICEF traces via Requirement,
    # not directly via Process. BacklogItem.process_id column was removed (ADR).

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "process_id_code": self.process_id_code,
            "module": self.module,
            "order": self.order,
            # L2
            "scope_confirmation": self.scope_confirmation,
            # L3/L4
            "code": self.code,
            "scope_decision": self.scope_decision,
            "fit_gap": self.fit_gap,
            "sap_tcode": self.sap_tcode,
            "sap_reference": self.sap_reference,
            "priority": self.priority,
            # L3
            "cloud_alm_ref": self.cloud_alm_ref,
            "test_scope": self.test_scope,
            # L4
            "activate_output": self.activate_output,
            "wricef_type": self.wricef_type,
            "test_levels": self.test_levels,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["children"] = [
                c.to_dict(include_children=True)
                for c in self.children.order_by(Process.order)
            ]
        return result

    def __repr__(self):
        return f"<Process {self.id}: [{self.level}] {self.name}>"


class RequirementProcessMapping(db.Model):
    """
    N:M junction -- which Requirements are addressed by which L3 Process Steps.

    One requirement can be addressed by multiple L3s.
    One L3 can address multiple requirements.
    """

    __tablename__ = "requirement_process_mappings"
    __table_args__ = (
        db.UniqueConstraint("requirement_id", "process_id", name="uq_req_process_mapping"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requirement_id = db.Column(
        db.Integer, db.ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    process_id = db.Column(
        db.Integer, db.ForeignKey("processes.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="L3 process step",
    )
    coverage_type = db.Column(
        db.String(20), default="full",
        comment="full | partial | none",
    )
    notes = db.Column(db.Text, default="")
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "requirement_id": self.requirement_id,
            "process_id": self.process_id,
            "coverage_type": self.coverage_type,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ReqProcMap {self.id}: REQ#{self.requirement_id} ↔ PROC#{self.process_id}>"


class Analysis(db.Model):
    """
    Fit-Gap assessment / workshop note linked to an L3 Process Step.

    Records the outcome of a Fit-Gap analysis including decision,
    attendees, and justification.
    """

    __tablename__ = "analyses"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    process_id = db.Column(
        db.Integer, db.ForeignKey("processes.id", ondelete="CASCADE"),
        nullable=False, comment="L3 process step being analyzed",
    )
    workshop_id = db.Column(
        db.Integer, db.ForeignKey("workshops.id", ondelete="SET NULL"),
        nullable=True,
        comment="Workshop session where this analysis was performed",
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    analysis_type = db.Column(
        db.String(30), default="fit_gap",
        comment="workshop | fit_gap | demo | prototype | review | workshop_note",
    )
    status = db.Column(
        db.String(30), default="planned",
        comment="planned | in_progress | completed | cancelled",
    )
    fit_gap_result = db.Column(
        db.String(20), default="",
        comment="fit | partial_fit | gap",
    )
    decision = db.Column(db.Text, default="", comment="Workshop outcome / decision")
    attendees = db.Column(db.Text, default="", comment="Comma-separated names")
    date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, default="")

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
            "process_id": self.process_id,
            "workshop_id": self.workshop_id,
            "name": self.name,
            "description": self.description,
            "analysis_type": self.analysis_type,
            "status": self.status,
            "fit_gap_result": self.fit_gap_result,
            "decision": self.decision,
            "attendees": self.attendees,
            "date": self.date.isoformat() if self.date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Analysis {self.id}: {self.name[:40]}>"
