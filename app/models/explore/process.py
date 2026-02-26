"""
Explore Phase — Process Hierarchy Models

ProcessLevel (L1-L4), ProcessStep (L4 within workshop context),
L4SeedCatalog (SAP Best Practice reference), BPMNDiagram.
"""

import uuid
from datetime import datetime, timezone

from app.models import db


__all__ = [
    "ProcessLevel",
    "ProcessStep",
    "L1SeedCatalog",
    "L2SeedCatalog",
    "L3SeedCatalog",
    "L4SeedCatalog",
    "BPMNDiagram",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════════
# 1. ProcessLevel — L1-L4 SAP Signavio hierarchy (T-001)
# ═════════════════════════════════════════════════════════════════════════════

class ProcessLevel(db.Model):
    """
    L1-L4 SAP Signavio process hierarchy. Self-referential tree.

    L1 = Value Chain, L2 = Process Area, L3 = E2E Process, L4 = Sub-Process.
    Replaces legacy Scenario (L1) + Process (L2-L4) with unified tree.

    L3 nodes carry consolidated fit decisions (GAP-11) and sign-off status.
    L2 nodes carry scope confirmation milestones (GAP-12).
    """

    __tablename__ = "process_levels"
    __table_args__ = (
        db.UniqueConstraint("program_id", "code", name="uq_pl_program_code"),
        db.Index("idx_pl_program_parent", "program_id", "parent_id"),
        db.Index("idx_pl_program_level", "program_id", "level"),
        db.Index("idx_pl_program_scope_item", "program_id", "scope_item_code"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Correct FK to programs. Replaces legacy project_id -> programs.id naming.",
    )
    # Faz 1.4: Re-pointed from programs.id → projects.id (was naming bug).
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    parent_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="CASCADE"),
        nullable=True, comment="NULL for L1 roots",
    )
    level = db.Column(
        db.Integer, nullable=False,
        comment="1=Value Chain, 2=Process Area, 3=E2E Process, 4=Sub-Process",
    )
    code = db.Column(
        db.String(20), nullable=False,
        comment="Unique within project. L1: VC-001, L2: PA-FIN, L3: J58, L4: J58.01",
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Scope & Fit
    scope_status = db.Column(
        db.String(20), nullable=False, default="under_review",
        comment="in_scope | out_of_scope | under_review",
    )
    fit_status = db.Column(
        db.String(20), nullable=True,
        comment="fit | gap | partial_fit | pending. NULL for L1/L2 (calculated).",
    )
    scope_item_code = db.Column(
        db.String(10), nullable=True,
        comment="SAP scope item code (L3 only, e.g. J58, BD9)",
    )

    # BPMN
    bpmn_available = db.Column(db.Boolean, nullable=False, default=False)
    bpmn_reference = db.Column(db.String(500), nullable=True)

    # Classification
    process_area_code = db.Column(
        db.String(5), nullable=True,
        comment="Denormalized: FI, CO, SD, MM, PP, QM, PM, WM, HR, PS",
    )
    wave = db.Column(db.Integer, nullable=True, comment="Implementation wave (1-4+)")
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    # ── GAP-11: L3 Consolidated Fit Decision ─────────────────────────────
    consolidated_fit_decision = db.Column(
        db.String(20), nullable=True,
        comment="Business-level: fit | gap | partial_fit. NULL = not decided yet.",
    )
    system_suggested_fit = db.Column(
        db.String(20), nullable=True,
        comment="Auto-calculated from L4 children: fit | gap | partial_fit",
    )
    consolidated_decision_override = db.Column(
        db.Boolean, nullable=False, default=False,
        comment="True = business overrode system suggestion",
    )
    consolidated_decision_rationale = db.Column(db.Text, nullable=True)
    consolidated_decided_by = db.Column(db.String(36), nullable=True)
    consolidated_decided_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── GAP-12: L2 Scope Confirmation Milestone ─────────────────────────
    confirmation_status = db.Column(
        db.String(30), nullable=True,
        comment="L2 only: not_ready | ready | confirmed | confirmed_with_risks",
    )
    confirmation_note = db.Column(db.Text, nullable=True)
    confirmed_by = db.Column(db.String(36), nullable=True)
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    readiness_pct = db.Column(
        db.Numeric(5, 2), nullable=True,
        comment="L2: (assessed L3 / total in-scope L3) * 100",
    )

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=_utcnow, onupdate=_utcnow,
    )

    # ── Relationships ────────────────────────────────────────────────────
    children = db.relationship(
        "ProcessLevel",
        backref=db.backref("parent", remote_side="ProcessLevel.id"),
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    workshop_scope_items = db.relationship(
        "WorkshopScopeItem", backref="process_level", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    process_steps = db.relationship(
        "ProcessStep", backref="process_level", lazy="dynamic",
    )

    def to_dict(self, include_children=False):
        d = {
            "id": self.id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "parent_id": self.parent_id,
            "level": self.level,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "scope_status": self.scope_status,
            "fit_status": self.fit_status,
            "scope_item_code": self.scope_item_code,
            "bpmn_available": self.bpmn_available,
            "bpmn_reference": self.bpmn_reference,
            "process_area_code": self.process_area_code,
            "wave": self.wave,
            "sort_order": self.sort_order,
            # GAP-11
            "consolidated_fit_decision": self.consolidated_fit_decision,
            "system_suggested_fit": self.system_suggested_fit,
            "consolidated_decision_override": self.consolidated_decision_override,
            "consolidated_decision_rationale": self.consolidated_decision_rationale,
            # GAP-12
            "confirmation_status": self.confirmation_status,
            "readiness_pct": float(self.readiness_pct) if self.readiness_pct else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            d["children"] = [
                c.to_dict(include_children=True)
                for c in self.children.order_by(ProcessLevel.sort_order)
            ]
        return d

    def __repr__(self):
        return f"<ProcessLevel L{self.level} {self.code}: {self.name}>"


# ═════════════════════════════════════════════════════════════════════════════
# 6. ProcessStep — L4 within workshop context (T-006)
# ═════════════════════════════════════════════════════════════════════════════

class ProcessStep(db.Model):
    """
    Workshop-scoped execution record for each L4 sub-process discussed.
    Created when workshop starts. Links L4 process definition to workshop outcomes.

    Business Rule: When fit_decision is set, propagate to process_level.fit_status.
    GAP-10: previous_session_step_id links to same L4 in a previous session.
    """

    __tablename__ = "process_steps"
    __table_args__ = (
        db.UniqueConstraint("workshop_id", "process_level_id", name="uq_ps_ws_pl"),
        db.Index("ix_ps_tenant_program_project", "tenant_id", "program_id", "project_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="Must be level=4",
    )
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    fit_decision = db.Column(
        db.String(20), nullable=True,
        comment="fit | gap | partial_fit. NULL = not assessed",
    )
    notes = db.Column(db.Text, nullable=True)
    demo_shown = db.Column(db.Boolean, nullable=False, default=False)
    bpmn_reviewed = db.Column(db.Boolean, nullable=False, default=False)
    assessed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    assessed_by = db.Column(db.String(36), nullable=True, comment="FK → user")

    # GAP-10: Multi-session continuity
    previous_session_step_id = db.Column(
        db.String(36), db.ForeignKey("process_steps.id", ondelete="SET NULL"),
        nullable=True, comment="Same L4 in previous session",
    )
    carried_from_session = db.Column(
        db.Integer, nullable=True,
        comment="Which session number this was carried from",
    )

    # ── Relationships ────────────────────────────────────────────────────
    decisions = db.relationship(
        "ExploreDecision", backref="process_step", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    open_items = db.relationship(
        "ExploreOpenItem", backref="process_step", lazy="dynamic",
    )
    requirements = db.relationship(
        "ExploreRequirement", backref="process_step", lazy="dynamic",
    )
    previous_session_step = db.relationship(
        "ProcessStep", remote_side="ProcessStep.id", uselist=False,
        foreign_keys=[previous_session_step_id],
    )

    def to_dict(self, include_children=False):
        pl = self.process_level  # L4 ProcessLevel
        l3 = pl.parent if pl else None  # L3 parent ProcessLevel
        d = {
            "id": self.id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "workshop_id": self.workshop_id,
            "process_level_id": self.process_level_id,
            "sort_order": self.sort_order,
            "order_index": self.sort_order,  # compat alias
            "fit_decision": self.fit_decision,
            "notes": self.notes,
            "demo_shown": self.demo_shown,
            "bpmn_reviewed": self.bpmn_reviewed,
            "assessed_at": self.assessed_at.isoformat() if self.assessed_at else None,
            "assessed_by": self.assessed_by,
            "previous_session_step_id": self.previous_session_step_id,
            "carried_from_session": self.carried_from_session,
            # L4 ProcessLevel fields for display
            "name": pl.name if pl else None,
            "code": pl.code if pl else None,
            "level": pl.level if pl else None,
            "process_area_code": pl.process_area_code if pl else None,
            "parent_id": pl.parent_id if pl else None,
            "scope_status": pl.scope_status if pl else None,
            "description": pl.description if pl else None,
            # L3 parent ProcessLevel fields for grouping headers
            "l3_parent_name": l3.name if l3 else None,
            "l3_parent_code": l3.code if l3 else None,
            "l3_parent_process_area_code": l3.process_area_code if l3 else None,
        }
        if include_children:
            d["decisions"] = [dec.to_dict() for dec in self.decisions]
            d["open_items"] = [oi.to_dict() for oi in self.open_items]
            d["requirements"] = [req.to_dict() for req in self.requirements]
        return d

    def __repr__(self):
        return f"<ProcessStep {self.id[:8]} WS:{self.workshop_id[:8]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 15. L1SeedCatalog — SAP Process Hierarchy Level 1 (Business Area)
# ═════════════════════════════════════════════════════════════════════════════

class L1SeedCatalog(db.Model):
    """SAP S/4HANA Process Catalog — Level 1 (Business Area).

    Global data shared across all tenants — no tenant_id.
    Examples: Financial Management, Procurement, Sales Management.

    Source: SAP Activate Best Practices conceptual structure (re-written for licensing).
    """

    __tablename__ = "l1_seed_catalog"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(
        db.String(10), nullable=False, unique=True,
        comment="E.g.: L1-FI, L1-MM, L1-SD",
    )
    name = db.Column(db.String(200), nullable=False)
    sap_module_group = db.Column(
        db.String(50), nullable=False,
        comment="FI_CO | MM_WM | SD_CS | HR | BASIS | PP_QM | PM",
    )
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    children = db.relationship(
        "L2SeedCatalog",
        back_populates="parent_l1",
        lazy="select",
        order_by="L2SeedCatalog.sort_order",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return f"<L1SeedCatalog {self.code}: {self.name}>"


# ═════════════════════════════════════════════════════════════════════════════
# 16. L2SeedCatalog — SAP Process Hierarchy Level 2 (Process Group)
# ═════════════════════════════════════════════════════════════════════════════

class L2SeedCatalog(db.Model):
    """SAP S/4HANA Process Catalog — Level 2 (Process Group).

    Global data shared across all tenants — no tenant_id.
    Examples: Accounts Payable, Accounts Receivable, Purchasing.
    """

    __tablename__ = "l2_seed_catalog"

    id = db.Column(db.Integer, primary_key=True)
    parent_l1_id = db.Column(
        db.Integer,
        db.ForeignKey("l1_seed_catalog.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = db.Column(
        db.String(15), nullable=False, unique=True,
        comment="E.g.: L2-FI-AP, L2-MM-PUR",
    )
    name = db.Column(db.String(200), nullable=False)
    sap_module = db.Column(
        db.String(10), nullable=False,
        comment="FI, MM, SD, CO, PP, PM, ...",
    )
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_s4_mandatory = db.Column(
        db.Boolean, nullable=False, default=False,
        comment="True = required for every S/4HANA migration (e.g. GL, New AP)",
    )

    parent_l1 = db.relationship("L1SeedCatalog", back_populates="children")
    children = db.relationship(
        "L3SeedCatalog",
        back_populates="parent_l2",
        lazy="select",
        order_by="L3SeedCatalog.sort_order",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return f"<L2SeedCatalog {self.code}: {self.name}>"


# ═════════════════════════════════════════════════════════════════════════════
# 17. L3SeedCatalog — SAP Process Hierarchy Level 3 (End-to-End Process)
# ═════════════════════════════════════════════════════════════════════════════

class L3SeedCatalog(db.Model):
    """SAP S/4HANA Process Catalog — Level 3 (End-to-End Process).

    Global data shared across all tenants — no tenant_id.
    Examples: Vendor Invoice Processing, Payment Run, Period-End Closing.

    Bridges L2 → L4 and optionally maps to a SAP Activate Scope Item code.
    """

    __tablename__ = "l3_seed_catalog"

    id = db.Column(db.Integer, primary_key=True)
    parent_l2_id = db.Column(
        db.Integer,
        db.ForeignKey("l2_seed_catalog.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code = db.Column(
        db.String(20), nullable=False, unique=True,
        comment="E.g.: L3-FI-AP-01, L3-MM-PUR-02",
    )
    name = db.Column(db.String(200), nullable=False)
    sap_scope_item_id = db.Column(
        db.String(20), nullable=True,
        comment="SAP Activate Scope Item reference: J45, BKC, BD9, ...",
    )
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    typical_complexity = db.Column(
        db.String(10), nullable=True,
        comment="low | medium | high",
    )

    parent_l2 = db.relationship("L2SeedCatalog", back_populates="children")
    l4_steps = db.relationship(
        "L4SeedCatalog",
        back_populates="parent_l3",
        lazy="select",
        order_by="L4SeedCatalog.standard_sequence",
        cascade="all, delete-orphan",
        foreign_keys="L4SeedCatalog.parent_l3_id",
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return f"<L3SeedCatalog {self.code}: {self.name}>"


# ═════════════════════════════════════════════════════════════════════════════
# 14. L4SeedCatalog — SAP Best Practice reference catalog (T-014, GAP-01)
# ═════════════════════════════════════════════════════════════════════════════

class L4SeedCatalog(db.Model):
    """
    SAP Best Practice L4 sub-process reference catalog.
    Project-independent global data — used to seed L4 process levels.
    """

    __tablename__ = "l4_seed_catalog"
    __table_args__ = (
        db.UniqueConstraint(
            "scope_item_code", "sub_process_code", name="uq_l4cat_scope_sub",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    scope_item_code = db.Column(
        db.String(10), nullable=False, index=True,
        comment="L3 scope item code (J58, BD9, etc.)",
    )
    sub_process_code = db.Column(
        db.String(20), nullable=False,
        comment="Standard L4 code (J58.01, BD9.03)",
    )
    sub_process_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    standard_sequence = db.Column(db.Integer, nullable=False, default=0)
    bpmn_activity_id = db.Column(
        db.String(100), nullable=True,
        comment="Signavio activity reference",
    )
    sap_release = db.Column(
        db.String(20), nullable=True,
        comment='SAP release version, e.g. "2402", "2311"',
    )

    # S7-01 FDD-I07 additions — link to L3 seed catalog hierarchy
    parent_l3_id = db.Column(
        db.Integer,
        db.ForeignKey("l3_seed_catalog.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to L3SeedCatalog. nullable: existing records without hierarchy still valid.",
    )
    is_customer_facing = db.Column(
        db.Boolean, nullable=False, default=False,
        comment="True = end-user facing L4 step (relevant for UAT scope).",
    )
    typical_fit_decision = db.Column(
        db.String(20), nullable=True,
        comment="fit | partial_fit | gap — SAP best practice baseline estimate.",
    )

    # Relationship back to L3
    parent_l3 = db.relationship(
        "L3SeedCatalog",
        back_populates="l4_steps",
        foreign_keys=[parent_l3_id],
    )

    def to_dict(self):
        return {
            "id": self.id,
            "scope_item_code": self.scope_item_code,
            "sub_process_code": self.sub_process_code,
            "sub_process_name": self.sub_process_name,
            "description": self.description,
            "standard_sequence": self.standard_sequence,
            "bpmn_activity_id": self.bpmn_activity_id,
            "sap_release": self.sap_release,
            "parent_l3_id": self.parent_l3_id,
            "is_customer_facing": self.is_customer_facing,
            "typical_fit_decision": self.typical_fit_decision,
        }

    def __repr__(self):
        return f"<L4SeedCatalog {self.sub_process_code}: {self.sub_process_name}>"


# ═════════════════════════════════════════════════════════════════════════════
# 23. BPMNDiagram — Process-level BPMN diagrams [GAP-02] (T-020)
# ═════════════════════════════════════════════════════════════════════════════

class BPMNDiagram(db.Model):
    """Stores BPMN diagrams (Signavio embed, raw XML, or uploaded images)."""
    __tablename__ = "bpmn_diagrams"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    type = db.Column(
        db.String(30), nullable=False, default="bpmn_xml",
        comment="signavio_embed | bpmn_xml | image",
    )
    source_url = db.Column(db.Text, nullable=True, comment="Signavio collaboration hub URL")
    bpmn_xml = db.Column(db.Text, nullable=True, comment="Raw BPMN 2.0 XML")
    image_path = db.Column(db.String(500), nullable=True, comment="Uploaded diagram image path")
    version = db.Column(db.Integer, nullable=False, default=1)
    uploaded_by = db.Column(db.String(36), nullable=True, comment="FK → user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    # ── Relationships ────────────────────────────────────────────────────
    process_level = db.relationship("ProcessLevel", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "process_level_id": self.process_level_id,
            "type": self.type,
            "source_url": self.source_url,
            "bpmn_xml": self.bpmn_xml,
            "image_path": self.image_path,
            "version": self.version,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<BPMNDiagram {self.id} type={self.type} v{self.version}>"
