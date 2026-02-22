"""
Explore Phase — Requirement & Open Item Models

ExploreDecision, ExploreOpenItem, ExploreRequirement,
RequirementOpenItemLink, RequirementDependency, OpenItemComment.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import synonym

from app.models import db


__all__ = [
    "REQUIREMENT_TRANSITIONS",
    "ExploreDecision",
    "ExploreOpenItem",
    "ExploreRequirement",
    "RequirementOpenItemLink",
    "RequirementDependency",
    "OpenItemComment",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════════
# 7. ExploreDecision — Workshop step decisions (T-007)
# ═════════════════════════════════════════════════════════════════════════════

class ExploreDecision(db.Model):
    """
    Decision captured during a workshop process step review.
    Separate from RAID Decision (raid.py) — this is Explore-specific.
    Code auto-generated: DEC-{seq} (3-digit, project-wide).
    """

    __tablename__ = "explore_decisions"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    process_step_id = db.Column(
        db.String(36), db.ForeignKey("process_steps.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    code = db.Column(
        db.String(10), nullable=False,
        comment="Auto: DEC-{seq}. Project-wide.",
    )
    text = db.Column(db.Text, nullable=False, comment="Decision statement")
    decided_by = db.Column(db.String(100), nullable=False, comment="Name of decider")
    decided_by_user_id = db.Column(db.String(36), nullable=True, comment="FK → user")
    category = db.Column(
        db.String(20), nullable=False, default="process",
        comment="process | technical | scope | organizational | data",
    )
    status = db.Column(
        db.String(20), nullable=False, default="active",
        comment="active | superseded | revoked",
    )
    rationale = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "process_step_id": self.process_step_id,
            "code": self.code,
            "text": self.text,
            "decision_text": self.text,  # compat alias
            "decided_by": self.decided_by,
            "decided_by_user_id": self.decided_by_user_id,
            "category": self.category,
            "status": self.status,
            "rationale": self.rationale,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ExploreDecision {self.code}: {self.text[:40]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 8. ExploreOpenItem — Independent action items (T-008)
# ═════════════════════════════════════════════════════════════════════════════

class ExploreOpenItem(db.Model):
    """
    Action items and investigation tasks. Born in workshops but live independently.
    Code auto-generated: OI-{seq} (3-digit, project-wide).

    Replaces legacy OpenItem (requirement.py) which was dependent on Requirement FK.
    This entity is fully independent with optional workshop/step context.
    """

    __tablename__ = "explore_open_items"
    __table_args__ = (
        db.UniqueConstraint("project_id", "code", name="uq_eoi_project_code"),
        db.Index("idx_eoi_project_status", "project_id", "status"),
        db.Index("idx_eoi_assignee_status", "assignee_id", "status"),
        db.Index("idx_eoi_workshop", "workshop_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    process_step_id = db.Column(
        db.String(36), db.ForeignKey("process_steps.id", ondelete="SET NULL"),
        nullable=True, comment="Origin process step",
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="SET NULL"),
        nullable=True, comment="Origin workshop",
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True, comment="Scope item context",
    )
    code = db.Column(
        db.String(10), nullable=False,
        comment="Auto: OI-{seq}. Project-wide.",
    )
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)

    status = db.Column(
        db.String(20), nullable=False, default="open",
        comment="open | in_progress | blocked | closed | cancelled",
    )
    priority = db.Column(
        db.String(5), nullable=False, default="P2",
        comment="P1 | P2 | P3 | P4",
    )
    category = db.Column(
        db.String(20), nullable=False, default="clarification",
        comment="clarification | technical | scope | data | process | organizational",
    )

    # Assignment
    assignee_id = db.Column(db.String(36), nullable=True, comment="FK → user")
    assignee_name = db.Column(db.String(100), nullable=True)
    created_by_id = db.Column(db.String(36), nullable=False, comment="FK → user")

    # Dates
    due_date = db.Column(db.Date, nullable=True)
    resolved_date = db.Column(db.Date, nullable=True)

    # Resolution
    resolution = db.Column(db.Text, nullable=True)
    blocked_reason = db.Column(db.Text, nullable=True)

    # Denormalized
    process_area = db.Column(db.String(5), nullable=True)
    wave = db.Column(db.Integer, nullable=True)
    module = synonym("process_area")

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=_utcnow, onupdate=_utcnow,
    )

    # ── Relationships ────────────────────────────────────────────────────
    workshop = db.relationship(
        "ExploreWorkshop", foreign_keys=[workshop_id], uselist=False,
    )
    comments = db.relationship(
        "OpenItemComment", backref="open_item", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    requirement_links = db.relationship(
        "RequirementOpenItemLink", backref="open_item", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # ── Computed properties ──────────────────────────────────────────────
    @property
    def is_overdue(self):
        if self.status in ("open", "in_progress") and self.due_date:
            return self.due_date < date.today()
        return False

    @property
    def days_overdue(self):
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

    def to_dict(self):
        # Resolve workshop code
        ws = self.workshop
        workshop_code = ws.code if ws else None

        # Resolve L4 code via process_step → process_level
        ps = self.process_step
        l4_code = None
        if ps and ps.process_level:
            l4_code = ps.process_level.code

        # Linked requirements (via N:M bridge)
        linked_reqs = [
            {"id": link.requirement_id, "link_type": link.link_type}
            for link in self.requirement_links
        ]

        return {
            "id": self.id,
            "project_id": self.project_id,
            "process_step_id": self.process_step_id,
            "workshop_id": self.workshop_id,
            "process_level_id": self.process_level_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "category": self.category,
            "assignee_id": self.assignee_id,
            "assignee_name": self.assignee_name,
            "created_by_id": self.created_by_id,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "resolved_date": self.resolved_date.isoformat() if self.resolved_date else None,
            "resolution": self.resolution,
            "blocked_reason": self.blocked_reason,
            "process_area": self.process_area,
            "wave": self.wave,
            "is_overdue": self.is_overdue,
            "days_overdue": self.days_overdue,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Resolved detail fields
            "workshop_code": workshop_code,
            "l4_code": l4_code,
            "linked_requirements": linked_reqs,
        }

    def __repr__(self):
        return f"<ExploreOpenItem {self.code}: {self.title[:40]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 9. ExploreRequirement — Delta requirements (T-009)
# ═════════════════════════════════════════════════════════════════════════════

# Valid status transitions for requirement lifecycle
REQUIREMENT_TRANSITIONS = {
    "submit_for_review": {"from": ["draft"], "to": "under_review"},
    "approve": {"from": ["under_review"], "to": "approved"},
    "reject": {"from": ["under_review"], "to": "rejected"},
    "return_to_draft": {"from": ["under_review"], "to": "draft"},
    "defer": {"from": ["draft", "approved"], "to": "deferred"},
    "push_to_alm": {"from": ["approved"], "to": "in_backlog"},
    "mark_realized": {"from": ["in_backlog"], "to": "realized"},
    "verify": {"from": ["realized"], "to": "verified"},
    "reactivate": {"from": ["deferred"], "to": "draft"},
    "unconvert": {"from": ["approved", "in_backlog", "realized"], "to": "approved"},
}


class ExploreRequirement(db.Model):
    """
    Delta requirements from Fit-to-Standard analysis.
    Full lifecycle: draft → under_review → approved → in_backlog → realized → verified.

    Code auto-generated: REQ-{seq} (3-digit, project-wide).
    Replaces legacy Requirement for Explore Phase context.
    """

    __tablename__ = "explore_requirements"
    __table_args__ = (
        db.UniqueConstraint("project_id", "code", name="uq_ereq_project_code"),
        db.Index("idx_ereq_project_status", "project_id", "status"),
        db.Index("idx_ereq_project_priority", "project_id", "priority"),
        db.Index("idx_ereq_project_area", "project_id", "process_area"),
        db.Index("idx_ereq_workshop", "workshop_id"),
        db.Index("idx_ereq_scope_item", "scope_item_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    process_step_id = db.Column(
        db.String(36), db.ForeignKey("process_steps.id", ondelete="SET NULL"),
        nullable=True, comment="Origin process step",
    )
    workshop_id = db.Column(
        db.String(36), db.ForeignKey("explore_workshops.id", ondelete="SET NULL"),
        nullable=True, comment="Origin workshop",
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True, comment="L4 where gap identified",
    )
    scope_item_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True, comment="L3 scope item (denormalized)",
    )

    code = db.Column(
        db.String(10), nullable=False,
        comment="Auto: REQ-{seq}. Project-wide.",
    )
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)

    priority = db.Column(
        db.String(5), nullable=False, default="P2",
        comment="P1 | P2 | P3 | P4",
    )
    type = db.Column(
        db.String(20), nullable=False, default="configuration",
        comment="development | configuration | integration | migration | enhancement | workaround",
    )
    fit_status = db.Column(
        db.String(20), nullable=False, default="gap",
        comment="gap | partial_fit — what triggered this requirement",
    )
    status = db.Column(
        db.String(20), nullable=False, default="draft",
        comment="draft | under_review | approved | in_backlog | realized | verified | deferred | rejected",
    )

    # Effort
    effort_hours = db.Column(db.Integer, nullable=True, comment="Estimated person-hours")
    effort_story_points = db.Column(db.Integer, nullable=True, comment="Agile alternative")
    complexity = db.Column(
        db.String(10), nullable=True,
        comment="low | medium | high | very_high",
    )

    # ── Analytical fields (W-2: Operational Model enrichment) ────────
    impact = db.Column(
        db.String(10), nullable=True,
        comment="high | medium | low — business impact assessment",
    )
    sap_module = db.Column(
        db.String(10), nullable=True,
        comment="SD | MM | FI | CO | PP | WM | QM | PM | PS | HR | etc.",
    )
    integration_ref = db.Column(
        db.String(200), nullable=True,
        comment="Cross-module integration reference (e.g. SD↔FI, MM↔WM)",
    )
    data_dependency = db.Column(
        db.Text, nullable=True,
        comment="Master data / migration dependency description",
    )
    business_criticality = db.Column(
        db.String(20), nullable=True,
        comment="business_critical | important | nice_to_have — KPI impact level",
    )
    wricef_candidate = db.Column(
        db.Boolean, nullable=False, default=False,
        comment="Flag: should this become a WRICEF backlog item?",
    )

    # Ownership
    created_by_id = db.Column(db.String(36), nullable=False, comment="FK → user")
    created_by_name = db.Column(db.String(100), nullable=True)
    approved_by_id = db.Column(db.String(36), nullable=True, comment="FK → user")
    approved_by_name = db.Column(db.String(100), nullable=True)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Denormalized
    process_area = db.Column(db.String(5), nullable=True)
    wave = db.Column(db.Integer, nullable=True)

    # Cloud ALM sync
    alm_id = db.Column(db.String(50), nullable=True, comment="Cloud ALM item ID")
    alm_synced = db.Column(db.Boolean, nullable=False, default=False)
    alm_synced_at = db.Column(db.DateTime(timezone=True), nullable=True)
    alm_sync_status = db.Column(
        db.String(20), nullable=True,
        comment="pending | synced | sync_error | out_of_sync",
    )

    # ── B-01 Consolidation fields (S1-05) ────────────────────────────────
    # All nullable=True: reviewer audit A3 — existing rows have no values;
    # constraints tighten in a later migration once data is populated.

    requirement_type = db.Column(
        db.String(32),
        nullable=True,
        default="functional",
        comment="business | functional | technical | non_functional | integration",
    )
    moscow_priority = db.Column(
        db.String(20),
        nullable=True,
        comment="must_have | should_have | could_have | wont_have (MoSCoW)",
    )
    source = db.Column(
        db.String(32),
        nullable=True,
        default="workshop",
        comment="workshop | stakeholder | regulation | gap_analysis | standard_process",
    )
    # Self-referential FK: Epic → Feature → User Story hierarchy.
    # String(36) to match the UUID primary key (FDD draft incorrectly listed Integer).
    parent_id = db.Column(
        db.String(36),
        db.ForeignKey("explore_requirements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Epic → Feature → User Story hierarchy; self-referential",
    )
    external_id = db.Column(
        db.String(100),
        nullable=True,
        index=True,
        comment="SAP Cloud ALM / Jira / ServiceNow external ID",
    )
    legacy_requirement_id = db.Column(
        db.Integer,
        nullable=True,
        index=True,
        comment="requirements.id of the migrated legacy row — for backward trace",
    )

    # Backlog linkage — REMOVED (ADR: WRICEF traces via BacklogItem.explore_requirement_id)
    # Canonical direction: BacklogItem.explore_requirement_id → ExploreRequirement.id (N:1)
    # Previously: backlog_item_id, config_item_id columns here (bidirectional 1:1). Removed
    # to enforce Requirement 1→N WRICEF architecture.

    # Deferred / Rejected
    deferred_to_phase = db.Column(db.String(50), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=_utcnow, onupdate=_utcnow,
    )

    # ── Relationships ────────────────────────────────────────────────────
    open_item_links = db.relationship(
        "RequirementOpenItemLink", backref="requirement", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    dependencies_from = db.relationship(
        "RequirementDependency",
        foreign_keys="RequirementDependency.requirement_id",
        backref="requirement", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    dependencies_to = db.relationship(
        "RequirementDependency",
        foreign_keys="RequirementDependency.depends_on_id",
        backref="dependency", lazy="dynamic",
    )
    alm_sync_logs = db.relationship(
        "CloudALMSyncLog", backref="requirement", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # Scope item relationship (L3)
    scope_item = db.relationship(
        "ProcessLevel", foreign_keys=[scope_item_id], uselist=False,
    )
    # L4 process level
    process_level = db.relationship(
        "ProcessLevel", foreign_keys=[process_level_id], uselist=False,
    )
    # Workshop relationship
    workshop = db.relationship(
        "ExploreWorkshop", foreign_keys=[workshop_id], uselist=False,
    )

    # Self-referential parent/children for Epic → Feature → User Story hierarchy.
    # parent_id FK defined above; this relationship provides ORM traversal.
    children = db.relationship(
        "ExploreRequirement",
        foreign_keys="ExploreRequirement.parent_id",
        backref=db.backref("parent", remote_side="ExploreRequirement.id"),
        lazy="select",
    )

    # ── 1:N Backlog/Config relationships (canonical direction) ────────
    # N WRICEFs can point to 1 Requirement via BacklogItem.explore_requirement_id
    linked_backlog_items = db.relationship(
        "BacklogItem",
        foreign_keys="BacklogItem.explore_requirement_id",
        lazy="select",
    )
    linked_config_items = db.relationship(
        "ConfigItem",
        foreign_keys="ConfigItem.explore_requirement_id",
        lazy="select",
    )

    # ── Computed properties for backward compatibility ─────────────────
    @property
    def is_converted(self):
        """Check if this requirement has been converted to backlog/config items."""
        return bool(self.linked_backlog_items or self.linked_config_items)

    @property
    def backlog_item_id(self):
        """Backward compat: returns first linked backlog item ID."""
        items = self.linked_backlog_items
        return items[0].id if items else None

    @property
    def config_item_id(self):
        """Backward compat: returns first linked config item ID."""
        items = self.linked_config_items
        return items[0].id if items else None

    def to_dict(self, include_links=False):
        # Resolve workshop code
        ws = self.workshop
        workshop_code = ws.code if ws else None

        # Resolve scope item (L3) name/code
        si = self.scope_item
        scope_item_name = si.name if si else None
        scope_item_code = si.code if si else None

        # Resolve L4 code via process_level
        pl = self.process_level
        l4_code = pl.code if pl else None

        # Linked open items (via N:M bridge) — always include
        linked_ois = [
            {"id": link.open_item_id, "link_type": link.link_type}
            for link in self.open_item_links
        ]
        # Dependencies — always include
        deps = [
            {"id": dep.depends_on_id, "type": dep.dependency_type}
            for dep in self.dependencies_from
        ]

        d = {
            "id": self.id,
            "project_id": self.project_id,
            "process_step_id": self.process_step_id,
            "workshop_id": self.workshop_id,
            "process_level_id": self.process_level_id,
            "scope_item_id": self.scope_item_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "type": self.type,
            "requirement_type": self.type,  # compat alias
            "fit_status": self.fit_status,
            "status": self.status,
            "effort_hours": self.effort_hours,
            "effort_story_points": self.effort_story_points,
            "complexity": self.complexity,
            "impact": self.impact,
            "sap_module": self.sap_module,
            "integration_ref": self.integration_ref,
            "data_dependency": self.data_dependency,
            "business_criticality": self.business_criticality,
            "wricef_candidate": self.wricef_candidate,
            "created_by_id": self.created_by_id,
            "created_by_name": self.created_by_name,
            "approved_by_id": self.approved_by_id,
            "approved_by_name": self.approved_by_name,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "process_area": self.process_area,
            "wave": self.wave,
            "alm_id": self.alm_id,
            "alm_synced": self.alm_synced,
            "alm_sync_status": self.alm_sync_status,
            "backlog_item_id": self.backlog_item_id,
            "config_item_id": self.config_item_id,
            "backlog_item_ids": [bi.id for bi in self.linked_backlog_items],
            "config_item_ids": [ci.id for ci in self.linked_config_items],
            "deferred_to_phase": self.deferred_to_phase,
            "rejection_reason": self.rejection_reason,
            # B-01 consolidation fields (S1-05)
            "requirement_type": self.requirement_type,
            "moscow_priority": self.moscow_priority,
            "source": self.source,
            "parent_id": self.parent_id,
            "external_id": self.external_id,
            "legacy_requirement_id": self.legacy_requirement_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Resolved detail fields
            "workshop_code": workshop_code,
            "scope_item_name": scope_item_name,
            "scope_item_code": scope_item_code,
            "l4_code": l4_code,
            "linked_open_items": linked_ois,
            "dependencies": deps,
        }
        if include_links:
            d["open_item_links"] = [l.to_dict() for l in self.open_item_links]
        return d

    def __repr__(self):
        return f"<ExploreRequirement {self.code}: {self.title[:40]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 10. RequirementOpenItemLink — N:M REQ ↔ OI (T-010)
# ═════════════════════════════════════════════════════════════════════════════

class RequirementOpenItemLink(db.Model):
    """
    N:M link between requirements and open items.
    link_type 'blocks' means the OI blocks the REQ transition.
    """

    __tablename__ = "requirement_open_item_links"
    __table_args__ = (
        db.UniqueConstraint("requirement_id", "open_item_id", name="uq_roil_req_oi"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requirement_id = db.Column(
        db.String(36), db.ForeignKey("explore_requirements.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    open_item_id = db.Column(
        db.String(36), db.ForeignKey("explore_open_items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    link_type = db.Column(
        db.String(10), nullable=False, default="related",
        comment="blocks | related | triggers",
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "requirement_id": self.requirement_id,
            "open_item_id": self.open_item_id,
            "link_type": self.link_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ReqOILink REQ:{self.requirement_id[:8]} ↔ OI:{self.open_item_id[:8]} ({self.link_type})>"


# ═════════════════════════════════════════════════════════════════════════════
# 11. RequirementDependency — REQ ↔ REQ self-ref (T-011)
# ═════════════════════════════════════════════════════════════════════════════

class RequirementDependency(db.Model):
    """Self-referential N:M for requirement-to-requirement dependencies."""

    __tablename__ = "requirement_dependencies"
    __table_args__ = (
        db.UniqueConstraint("requirement_id", "depends_on_id", name="uq_rdep_req_dep"),
        db.CheckConstraint(
            "requirement_id != depends_on_id", name="ck_rdep_no_self_ref",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requirement_id = db.Column(
        db.String(36), db.ForeignKey("explore_requirements.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="Dependent requirement",
    )
    depends_on_id = db.Column(
        db.String(36), db.ForeignKey("explore_requirements.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="Dependency (upstream)",
    )
    dependency_type = db.Column(
        db.String(10), nullable=False, default="related",
        comment="blocks | related | extends",
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "requirement_id": self.requirement_id,
            "depends_on_id": self.depends_on_id,
            "dependency_type": self.dependency_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<ReqDep {self.requirement_id[:8]} → {self.depends_on_id[:8]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 12. OpenItemComment — Activity log (T-012)
# ═════════════════════════════════════════════════════════════════════════════

class OpenItemComment(db.Model):
    """Activity log entry for an open item — comments, status changes, etc."""

    __tablename__ = "open_item_comments"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    open_item_id = db.Column(
        db.String(36), db.ForeignKey("explore_open_items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = db.Column(db.String(36), nullable=False, comment="FK → user")
    type = db.Column(
        db.String(20), nullable=False, default="comment",
        comment="comment | status_change | reassignment | due_date_change",
    )
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "open_item_id": self.open_item_id,
            "user_id": self.user_id,
            "type": self.type,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<OpenItemComment {self.id[:8]} on OI:{self.open_item_id[:8]}>"
