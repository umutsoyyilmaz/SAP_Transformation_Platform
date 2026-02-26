"""
SAP Transformation Management Platform
Cutover Hub domain models — Sprint 13 + Hypercare extension.

Models:
    - CutoverPlan:               top-level cutover plan for a program (one active plan per go-live)
    - CutoverScopeItem:          category-based grouping of runbook tasks
    - RunbookTask:               individual executable step within a scope item
    - TaskDependency:            predecessor → successor relationship between runbook tasks
    - Rehearsal:                 dry-run execution record with findings and timing comparison
    - GoNoGoItem:                readiness checklist item for go/no-go decision
    - HypercareIncident:         post-go-live incident tracker with SLA deadline tracking (FDD-B03)
    - HypercareSLA:              SLA response / resolution targets per severity level
    - PostGoliveChangeRequest:   change requests raised during hypercare window (FDD-B03)
    - IncidentComment:           audit-log comments on hypercare incidents (FDD-B03)
    - HypercareWarRoom:          war room session grouping incidents and CRs (FDD-B03-Phase-3)

Architecture:
    Program ──1:N──▶ CutoverPlan ──1:N──▶ CutoverScopeItem ──1:N──▶ RunbookTask
    RunbookTask ──N:M──▶ RunbookTask  (via TaskDependency)
    CutoverPlan ──1:N──▶ Rehearsal
    CutoverPlan ──1:N──▶ GoNoGoItem
    CutoverPlan ──1:N──▶ HypercareIncident
    CutoverPlan ──1:N──▶ HypercareSLA

Lifecycle states:
    CutoverPlan:        draft → approved → rehearsal → ready → executing → completed
                        → hypercare → closed  |  executing → rolled_back
    RunbookTask:        not_started → in_progress → completed → failed → skipped → rolled_back
    Rehearsal:          planned → in_progress → completed → cancelled
    GoNoGoItem:         pending → go → no_go → waived
    HypercareIncident:  open → investigating → resolved → closed
"""

from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

CUTOVER_PLAN_STATUSES = {
    "draft", "approved", "rehearsal", "ready",
    "executing", "completed", "rolled_back",
    "hypercare", "closed",
}

SCOPE_CATEGORIES = {
    "data_load", "interface", "authorization",
    "job_scheduling", "reconciliation", "custom",
}

RUNBOOK_TASK_STATUSES = {
    "not_started", "in_progress", "completed",
    "failed", "skipped", "rolled_back",
}

REHEARSAL_STATUSES = {
    "planned", "in_progress", "completed", "cancelled",
}

GO_NO_GO_VERDICTS = {"pending", "go", "no_go", "waived"}

GO_NO_GO_SOURCES = {
    "test_management", "data_factory", "integration_factory",
    "security", "training", "cutover_rehearsal",
    "steering_signoff", "custom",
}

LINKED_ENTITY_TYPES = {
    "backlog_item", "interface", "data_object",
    "config_item", "test_case",
}

# ── Hypercare Incident Constants ─────────────────────────────────────────────

INCIDENT_SEVERITIES = {"P1", "P2", "P3", "P4"}

INCIDENT_STATUSES = {"open", "investigating", "resolved", "closed"}

INCIDENT_CATEGORIES = {
    "functional", "technical", "data",
    "authorization", "performance", "other",
}

INCIDENT_TRANSITIONS = {
    "open":          ["investigating", "resolved", "closed"],
    "investigating": ["resolved", "closed"],
    "resolved":      ["closed", "open"],   # re-open if regression found
    "closed":        ["open"],             # re-open edge case
}

# ── FDD-B03-Phase-2: Escalation constants ──────────────────────────────────

ESCALATION_LEVELS = {"L1", "L2", "L3", "vendor", "management"}

ESCALATION_LEVEL_ORDER = ["L1", "L2", "L3", "vendor", "management"]

ESCALATION_TRIGGER_TYPES = {
    "no_response",          # first_response_at still None after threshold
    "no_update",            # no IncidentComment within threshold since last activity
    "no_resolution",        # approaching/exceeding resolution SLA deadline
    "severity_escalation",  # severity upgraded (e.g. P2 -> P1)
    "manual",               # manually triggered by operator
}


# ── Lifecycle Transition Guards ──────────────────────────────────────────────

PLAN_TRANSITIONS = {
    "draft":       ["approved"],
    "approved":    ["rehearsal", "ready"],
    "rehearsal":   ["approved", "ready"],
    "ready":       ["executing", "approved"],
    "executing":   ["completed", "rolled_back"],
    "completed":   ["hypercare"],
    "hypercare":   ["closed"],
    "closed":      [],
    "rolled_back": ["draft"],
}

TASK_TRANSITIONS = {
    "not_started":  ["in_progress", "skipped"],
    "in_progress":  ["completed", "failed", "rolled_back"],
    "completed":    ["rolled_back"],
    "failed":       ["in_progress", "rolled_back", "skipped"],
    "skipped":      ["not_started"],
    "rolled_back":  ["not_started"],
}

REHEARSAL_TRANSITIONS = {
    "planned":     ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed":   [],
    "cancelled":   ["planned"],
}


def validate_plan_transition(old_status, new_status):
    """Return True if CutoverPlan status transition is valid."""
    return new_status in PLAN_TRANSITIONS.get(old_status, [])


def validate_task_transition(old_status, new_status):
    """Return True if RunbookTask status transition is valid."""
    return new_status in TASK_TRANSITIONS.get(old_status, [])


def validate_rehearsal_transition(old_status, new_status):
    """Return True if Rehearsal status transition is valid."""
    return new_status in REHEARSAL_TRANSITIONS.get(old_status, [])


def validate_incident_transition(old_status, new_status):
    """Return True if HypercareIncident status transition is valid."""
    return new_status in INCIDENT_TRANSITIONS.get(old_status, [])


# ── Cycle Detection ──────────────────────────────────────────────────────────


def validate_no_cycle(session, task_id, new_predecessor_id):
    """
    Check that adding new_predecessor_id → task_id does not create a cycle.

    Uses iterative DFS from new_predecessor_id, walking backwards through
    existing predecessor chains.  Returns True if safe, False if cycle found.
    """
    if task_id == new_predecessor_id:
        return False

    visited = set()
    stack = [new_predecessor_id]

    while stack:
        current = stack.pop()
        if current == task_id:
            return False
        if current in visited:
            continue
        visited.add(current)

        deps = (
            session.query(TaskDependency.predecessor_id)
            .filter(TaskDependency.successor_id == current)
            .all()
        )
        for (pred_id,) in deps:
            stack.append(pred_id)

    return True


# ═════════════════════════════════════════════════════════════════════════════
# 1. CutoverPlan
# ═════════════════════════════════════════════════════════════════════════════


class CutoverPlan(db.Model):
    """
    Top-level cutover plan for a program.
    One program may have multiple plans (e.g. per wave / go-live event).
    Code format: CUT-001 (program-scoped, auto-generated in service layer).
    """

    __tablename__ = "cutover_plans"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    code = db.Column(
        db.String(30), unique=True, nullable=True,
        comment="Auto-generated: CUT-001 (program-scoped)",
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(
        db.String(30), default="draft",
        comment="draft | approved | rehearsal | ready | executing | completed | rolled_back",
    )
    version = db.Column(
        db.Integer, default=1,
        comment="Plan version — increments after each rehearsal revision",
    )

    # Timeline
    planned_start = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="Cutover window start (e.g. Friday 22:00)",
    )
    planned_end = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="Cutover window end (e.g. Monday 06:00)",
    )
    actual_start = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_end = db.Column(db.DateTime(timezone=True), nullable=True)

    # Ownership
    cutover_manager = db.Column(db.String(100), default="")
    cutover_manager_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True, comment="FK → team_members",
    )
    environment = db.Column(
        db.String(30), default="PRD",
        comment="Target environment: PRD | QAS | Sandbox",
    )

    # Rollback
    rollback_deadline = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="Point-of-no-return — after this, rollback is no longer feasible",
    )
    rollback_decision_by = db.Column(
        db.String(100), default="",
        comment="Person authorized to trigger rollback",
    )

    # Hypercare
    hypercare_start = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="Hypercare period start — usually = actual_end (go-live date)",
    )
    hypercare_end = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="Hypercare period end",
    )
    hypercare_duration_weeks = db.Column(
        db.Integer, default=4,
        comment="SAP standard 4-6 weeks hypercare window",
    )
    hypercare_manager = db.Column(
        db.String(100), default="",
        comment="Hypercare period manager / support lead",
    )

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('draft','approved','rehearsal','ready',"
            "'executing','completed','rolled_back','hypercare','closed')",
            name="ck_cutover_plan_status",
        ),
    )

    # ── Relationships ────────────────────────────────────────────────────
    scope_items = db.relationship(
        "CutoverScopeItem", backref="cutover_plan", lazy="dynamic",
        cascade="all, delete-orphan", order_by="CutoverScopeItem.order",
    )
    rehearsals = db.relationship(
        "Rehearsal", backref="cutover_plan", lazy="dynamic",
        cascade="all, delete-orphan", order_by="Rehearsal.rehearsal_number",
    )
    go_no_go_items = db.relationship(
        "GoNoGoItem", backref="cutover_plan", lazy="dynamic",
        cascade="all, delete-orphan", order_by="GoNoGoItem.source_domain",
    )
    incidents = db.relationship(
        "HypercareIncident", backref="cutover_plan", lazy="dynamic",
        cascade="all, delete-orphan", order_by="HypercareIncident.reported_at.desc()",
    )
    sla_targets = db.relationship(
        "HypercareSLA", backref="cutover_plan", lazy="dynamic",
        cascade="all, delete-orphan", order_by="HypercareSLA.severity",
    )
    cutover_manager_member = db.relationship("TeamMember", foreign_keys=[cutover_manager_id])

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "version": self.version,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "cutover_manager": self.cutover_manager,
            "cutover_manager_id": self.cutover_manager_id,
            "cutover_manager_member": self.cutover_manager_member.to_dict() if self.cutover_manager_id and self.cutover_manager_member else None,
            "environment": self.environment,
            "rollback_deadline": (
                self.rollback_deadline.isoformat() if self.rollback_deadline else None
            ),
            "rollback_decision_by": self.rollback_decision_by,
            "hypercare_start": self.hypercare_start.isoformat() if self.hypercare_start else None,
            "hypercare_end": self.hypercare_end.isoformat() if self.hypercare_end else None,
            "hypercare_duration_weeks": self.hypercare_duration_weeks,
            "hypercare_manager": self.hypercare_manager,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            # Aggregated stats
            "scope_item_count": self.scope_items.count(),
            "rehearsal_count": self.rehearsals.count(),
            "go_no_go_count": self.go_no_go_items.count(),
            "incident_count": self.incidents.count(),
            "sla_target_count": self.sla_targets.count(),
        }
        if include_children:
            result["scope_items"] = [si.to_dict(include_children=True) for si in self.scope_items]
            result["rehearsals"] = [r.to_dict() for r in self.rehearsals]
            result["go_no_go_items"] = [g.to_dict() for g in self.go_no_go_items]
        return result

    def __repr__(self):
        return f"<CutoverPlan {self.id}: {self.name} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# 2. CutoverScopeItem
# ═════════════════════════════════════════════════════════════════════════════


class CutoverScopeItem(db.Model):
    """
    Category-based grouping of runbook tasks within a cutover plan.
    Categories: data_load, interface, authorization, job_scheduling, reconciliation, custom.
    Status is computed from child task statuses (not stored).
    """

    __tablename__ = "cutover_scope_items"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    name = db.Column(db.String(200), nullable=False)
    category = db.Column(
        db.String(30), default="custom",
        comment="data_load | interface | authorization | job_scheduling | reconciliation | custom",
    )
    description = db.Column(db.Text, default="")
    owner = db.Column(db.String(100), default="")
    owner_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True, comment="FK → team_members",
    )
    order = db.Column(
        db.Integer, default=0,
        comment="Display order within the plan",
    )

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "category IN ('data_load','interface','authorization',"
            "'job_scheduling','reconciliation','custom')",
            name="ck_scope_item_category",
        ),
    )

    # ── Relationships ────────────────────────────────────────────────────
    runbook_tasks = db.relationship(
        "RunbookTask", backref="scope_item", lazy="dynamic",
        cascade="all, delete-orphan", order_by="RunbookTask.sequence",
    )
    owner_member = db.relationship("TeamMember", foreign_keys=[owner_id])

    def _compute_status(self):
        """Derive status from child task statuses."""
        tasks = self.runbook_tasks.all()
        if not tasks:
            return "not_started"
        statuses = {t.status for t in tasks}
        if statuses == {"completed"}:
            return "completed"
        if "failed" in statuses:
            return "failed"
        if statuses & {"in_progress", "completed"}:
            return "in_progress"
        return "not_started"

    def to_dict(self, include_children=False):
        task_count = self.runbook_tasks.count()
        result = {
            "id": self.id,
            "cutover_plan_id": self.cutover_plan_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "owner": self.owner,
            "owner_id": self.owner_id,
            "owner_member": self.owner_member.to_dict() if self.owner_id and self.owner_member else None,
            "order": self.order,
            "status": self._compute_status(),
            "task_count": task_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["runbook_tasks"] = [t.to_dict() for t in self.runbook_tasks]
        return result

    def __repr__(self):
        return f"<CutoverScopeItem {self.id}: {self.name} [{self.category}]>"


# ═════════════════════════════════════════════════════════════════════════════
# 3. RunbookTask
# ═════════════════════════════════════════════════════════════════════════════


class RunbookTask(db.Model):
    """
    Individual executable step within a cutover scope item.
    Code format: CUT-001-T047 (plan-scoped, auto-generated in service layer).
    """

    __tablename__ = "runbook_tasks"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scope_item_id = db.Column(
        db.Integer, db.ForeignKey("cutover_scope_items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    code = db.Column(
        db.String(30), nullable=True,
        comment="Auto-generated: CUT-001-T047 (plan-scoped)",
    )
    sequence = db.Column(
        db.Integer, default=0,
        comment="Execution order — plan-wide",
    )
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")

    # Timing
    planned_start = db.Column(db.DateTime(timezone=True), nullable=True)
    planned_end = db.Column(db.DateTime(timezone=True), nullable=True)
    planned_duration_min = db.Column(db.Integer, nullable=True)
    actual_start = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_end = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_duration_min = db.Column(db.Integer, nullable=True)

    # Responsibility (RACI)
    responsible = db.Column(db.String(100), default="", comment="R — does the work")
    responsible_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True, comment="FK → team_members (responsible)",
    )
    accountable = db.Column(db.String(100), default="", comment="A — signs off")

    # Execution
    status = db.Column(
        db.String(30), default="not_started",
        comment="not_started | in_progress | completed | failed | skipped | rolled_back",
    )
    environment = db.Column(db.String(30), default="PRD")
    executed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    executed_by = db.Column(db.String(100), default="")

    # Rollback
    rollback_action = db.Column(db.Text, default="")
    rollback_decision_point = db.Column(db.String(300), default="")

    # Cross-domain linkage
    linked_entity_type = db.Column(
        db.String(30), nullable=True,
        comment="backlog_item | interface | data_object | config_item | test_case",
    )
    linked_entity_id = db.Column(db.Integer, nullable=True)

    notes = db.Column(db.Text, default="")

    # ── War Room fields (FDD-I03 / S5-03) ────────────────────────────────
    workstream = db.Column(
        db.String(50),
        nullable=True,
        comment="technical | basis | functional | data | interface | communication",
    )
    delay_minutes = db.Column(
        db.Integer,
        nullable=True,
        comment="Auto-calculated: actual_end - planned_end in minutes. Negative = early.",
    )
    is_critical_path = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        comment="Set by calculate_critical_path() in cutover_service.",
    )
    parallel_group = db.Column(
        db.String(20),
        nullable=True,
        comment="A | B | C — parallel execution lanes within a workstream.",
    )
    issue_note = db.Column(
        db.Text,
        nullable=True,
        comment="War-room issue flag. Set via flag_issue() endpoint.",
    )

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('not_started','in_progress','completed',"
            "'failed','skipped','rolled_back')",
            name="ck_runbook_task_status",
        ),
        db.CheckConstraint(
            "workstream IS NULL OR workstream IN ("
            "'technical','basis','functional','data','interface','communication')",
            name="ck_runbook_task_workstream",
        ),
    )

    # ── Relationships ────────────────────────────────────────────────────
    predecessors = db.relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.successor_id",
        backref="successor_task",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    successors = db.relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.predecessor_id",
        backref="predecessor_task",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    responsible_member = db.relationship("TeamMember", foreign_keys=[responsible_id])

    def to_dict(self, include_dependencies=False):
        result = {
            "id": self.id,
            "scope_item_id": self.scope_item_id,
            "code": self.code,
            "sequence": self.sequence,
            "title": self.title,
            "description": self.description,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "planned_duration_min": self.planned_duration_min,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "actual_duration_min": self.actual_duration_min,
            "responsible": self.responsible,
            "responsible_id": self.responsible_id,
            "responsible_member": self.responsible_member.to_dict() if self.responsible_id and self.responsible_member else None,
            "accountable": self.accountable,
            "status": self.status,
            "environment": self.environment,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "executed_by": self.executed_by,
            "rollback_action": self.rollback_action,
            "rollback_decision_point": self.rollback_decision_point,
            "linked_entity_type": self.linked_entity_type,
            "linked_entity_id": self.linked_entity_id,
            "notes": self.notes,
            # War Room fields (FDD-I03)
            "workstream": self.workstream,
            "delay_minutes": self.delay_minutes,
            "is_critical_path": self.is_critical_path,
            "parallel_group": self.parallel_group,
            "issue_note": self.issue_note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_dependencies:
            result["predecessor_ids"] = [
                d.predecessor_id for d in self.predecessors
            ]
            result["successor_ids"] = [
                d.successor_id for d in self.successors
            ]
        return result

    def __repr__(self):
        return f"<RunbookTask {self.id}: {self.code or '#'}{self.sequence} {self.title[:40]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 4. TaskDependency
# ═════════════════════════════════════════════════════════════════════════════


class TaskDependency(db.Model):
    """
    Predecessor → Successor dependency between runbook tasks.
    Dependency types: finish_to_start (default), start_to_start, finish_to_finish.
    Supports optional lag time.
    """

    __tablename__ = "task_dependencies"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    predecessor_id = db.Column(
        db.Integer, db.ForeignKey("runbook_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    successor_id = db.Column(
        db.Integer, db.ForeignKey("runbook_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    dependency_type = db.Column(
        db.String(30), default="finish_to_start",
        comment="finish_to_start | start_to_start | finish_to_finish",
    )
    lag_minutes = db.Column(db.Integer, default=0)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.UniqueConstraint(
            "predecessor_id", "successor_id",
            name="uq_task_dep",
        ),
        db.CheckConstraint(
            "predecessor_id != successor_id",
            name="ck_dep_no_self_loop",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "predecessor_id": self.predecessor_id,
            "successor_id": self.successor_id,
            "dependency_type": self.dependency_type,
            "lag_minutes": self.lag_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<TaskDependency {self.predecessor_id} → {self.successor_id}>"


# ═════════════════════════════════════════════════════════════════════════════
# 5. Rehearsal
# ═════════════════════════════════════════════════════════════════════════════


class Rehearsal(db.Model):
    """
    Cutover rehearsal (dry-run) execution record.
    SAP best practice: at least 2-3 rehearsals before go-live.
    """

    __tablename__ = "rehearsals"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    rehearsal_number = db.Column(
        db.Integer, nullable=False,
        comment="Sequential within plan: 1, 2, 3, ...",
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(
        db.String(30), default="planned",
        comment="planned | in_progress | completed | cancelled",
    )
    environment = db.Column(db.String(30), default="QAS")

    # Timing
    planned_start = db.Column(db.DateTime(timezone=True), nullable=True)
    planned_end = db.Column(db.DateTime(timezone=True), nullable=True)
    planned_duration_min = db.Column(db.Integer, nullable=True)
    actual_start = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_end = db.Column(db.DateTime(timezone=True), nullable=True)
    actual_duration_min = db.Column(db.Integer, nullable=True)

    # Outcome
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    failed_tasks = db.Column(db.Integer, default=0)
    skipped_tasks = db.Column(db.Integer, default=0)
    duration_variance_pct = db.Column(
        db.Float, nullable=True,
        comment="(actual - planned) / planned × 100",
    )
    runbook_revision_needed = db.Column(db.Boolean, default=False)

    # Findings
    findings_summary = db.Column(db.Text, default="")

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.UniqueConstraint(
            "cutover_plan_id", "rehearsal_number",
            name="uq_plan_rehearsal_no",
        ),
        db.CheckConstraint(
            "status IN ('planned','in_progress','completed','cancelled')",
            name="ck_rehearsal_status",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "cutover_plan_id": self.cutover_plan_id,
            "rehearsal_number": self.rehearsal_number,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "environment": self.environment,
            "planned_start": self.planned_start.isoformat() if self.planned_start else None,
            "planned_end": self.planned_end.isoformat() if self.planned_end else None,
            "planned_duration_min": self.planned_duration_min,
            "actual_start": self.actual_start.isoformat() if self.actual_start else None,
            "actual_end": self.actual_end.isoformat() if self.actual_end else None,
            "actual_duration_min": self.actual_duration_min,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "duration_variance_pct": self.duration_variance_pct,
            "runbook_revision_needed": self.runbook_revision_needed,
            "findings_summary": self.findings_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Rehearsal {self.id}: #{self.rehearsal_number} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# 6. GoNoGoItem
# ═════════════════════════════════════════════════════════════════════════════


class GoNoGoItem(db.Model):
    """
    Readiness checklist item for the Go/No-Go decision pack.
    Aggregated from all platform domains — each row is one readiness criterion.
    """

    __tablename__ = "go_no_go_items"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    source_domain = db.Column(
        db.String(30), default="custom",
        comment="test_management | data_factory | integration_factory | "
                "security | training | cutover_rehearsal | steering_signoff | custom",
    )
    criterion = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    verdict = db.Column(
        db.String(20), default="pending",
        comment="pending | go | no_go | waived",
    )
    evidence = db.Column(db.Text, default="")
    evaluated_by = db.Column(db.String(100), default="")
    evaluated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.Text, default="")

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "verdict IN ('pending','go','no_go','waived')",
            name="ck_go_no_go_verdict",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "cutover_plan_id": self.cutover_plan_id,
            "source_domain": self.source_domain,
            "criterion": self.criterion,
            "description": self.description,
            "verdict": self.verdict,
            "evidence": self.evidence,
            "evaluated_by": self.evaluated_by,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<GoNoGoItem {self.id}: {self.criterion[:40]} [{self.verdict}]>"


# ── Seed Helpers ─────────────────────────────────────────────────────────────


def seed_default_go_no_go(cutover_plan_id):
    """
    Create the standard 7-item Go/No-Go checklist for a new cutover plan.
    """
    defaults = [
        {
            "source_domain": "test_management",
            "criterion": "Open P1/P2 Defects = 0",
            "description": "No critical or high-severity defects remain open in Test Management",
        },
        {
            "source_domain": "data_factory",
            "criterion": "Data Load Reconciliation Passed",
            "description": "All data objects reconciled — loaded count matches source with <0.1% variance",
        },
        {
            "source_domain": "integration_factory",
            "criterion": "Interface Connectivity Verified",
            "description": "All production interfaces tested end-to-end with successful connectivity",
        },
        {
            "source_domain": "security",
            "criterion": "Authorization Readiness Complete",
            "description": "All roles provisioned, SOD conflicts resolved, UAM sign-off obtained",
        },
        {
            "source_domain": "training",
            "criterion": "Training Completion ≥ 90%",
            "description": "End-user training completion rate meets minimum threshold",
        },
        {
            "source_domain": "cutover_rehearsal",
            "criterion": "Cutover Rehearsal Within Tolerance",
            "description": "Latest rehearsal completed within ±15% of planned duration, no P1 issues",
        },
        {
            "source_domain": "steering_signoff",
            "criterion": "Steering Committee Sign-off",
            "description": "Formal go-live approval from steering committee / project sponsor",
        },
    ]

    items = []
    for d in defaults:
        items.append(GoNoGoItem(cutover_plan_id=cutover_plan_id, **d))
    db.session.add_all(items)
    db.session.flush()
    return items


# ═════════════════════════════════════════════════════════════════════════════
# 7. HypercareIncident
# ═════════════════════════════════════════════════════════════════════════════


class HypercareIncident(db.Model):
    """
    Post-go-live incident tracker within the hypercare window.
    Code format: INC-001 (plan-scoped, auto-generated in service layer).
    Tracks severity, SLA response / resolution times, and cross-domain linkage.
    """

    __tablename__ = "hypercare_incidents"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,  # security audit fix A2 (S4-01): tenant isolation enforced
        index=True,
    )
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    code = db.Column(
        db.String(30), nullable=True,
        comment="Auto-generated: INC-001 (plan-scoped)",
    )
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    severity = db.Column(
        db.String(10), nullable=False, default="P3",
        comment="P1 | P2 | P3 | P4",
    )
    category = db.Column(
        db.String(30), default="other",
        comment="functional | technical | data | authorization | performance | other",
    )
    status = db.Column(
        db.String(20), default="open",
        comment="open | investigating | resolved | closed",
    )

    # People
    reported_by = db.Column(db.String(100), default="")
    reported_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    assigned_to = db.Column(db.String(100), default="")

    # Resolution
    resolution = db.Column(db.Text, default="")
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_by = db.Column(db.String(100), default="")

    # SLA tracking (minutes)
    response_time_min = db.Column(
        db.Integer, nullable=True,
        comment="Actual response time in minutes (first action after report)",
    )
    resolution_time_min = db.Column(
        db.Integer, nullable=True,
        comment="Actual resolution time in minutes (reported → resolved)",
    )

    # Cross-domain linkage
    linked_entity_type = db.Column(
        db.String(30), nullable=True,
        comment="backlog_item | interface | data_object | config_item | test_case",
    )
    linked_entity_id = db.Column(db.Integer, nullable=True)

    notes = db.Column(db.Text, default="")

    # ── FDD-B03 additions: classification, SLA deadlines, root cause, CR link ──

    # Incident classification
    incident_type = db.Column(
        db.String(30), nullable=True,
        comment="system_down | data_issue | performance | authorization | interface | other",
    )
    affected_module = db.Column(
        db.String(20), nullable=True, comment="SAP module: FI | MM | SD | HCM | PP | etc."
    )
    affected_users_count = db.Column(db.Integer, nullable=True)
    assigned_to_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        comment="Platform user assigned to resolve the incident",
    )

    # SLA deadline tracking — auto-calculated in hypercare_service on incident creation
    first_response_at = db.Column(db.DateTime(timezone=True), nullable=True)
    sla_response_breached = db.Column(db.Boolean, nullable=False, default=False)
    sla_resolution_breached = db.Column(db.Boolean, nullable=False, default=False)
    sla_response_deadline = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="Auto-calculated: created_at + HypercareSLA.response_target_min",
    )
    sla_resolution_deadline = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="Auto-calculated: created_at + HypercareSLA.resolution_target_min",
    )

    # Root cause analysis
    root_cause = db.Column(db.Text, nullable=True)
    root_cause_category = db.Column(
        db.String(30), nullable=True,
        comment="config | data | training | process | development | external",
    )
    linked_backlog_item_id = db.Column(
        db.Integer, db.ForeignKey("backlog_items.id", ondelete="SET NULL"), nullable=True,
        comment="If root cause is a WRICEF/backlog item, link here",
    )

    # Post-go-live change request link
    requires_change_request = db.Column(db.Boolean, nullable=False, default=False)
    change_request_id = db.Column(
        db.Integer,
        db.ForeignKey("post_golive_change_requests.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── FDD-B03-Phase-3: War Room assignment ─────────────────────────────
    war_room_id = db.Column(
        db.Integer, db.ForeignKey("hypercare_war_rooms.id", ondelete="SET NULL"),
        nullable=True,
        comment="Assigned war room session (nullable — incident may exist unassigned)",
    )

    # ── FDD-B03-Phase-2: Escalation tracking ──────────────────────────────
    current_escalation_level = db.Column(
        db.String(20), nullable=True,
        comment="Current highest escalation level: L1 | L2 | L3 | vendor | management",
    )
    escalation_count = db.Column(
        db.Integer, nullable=False, default=0,
        comment="Total number of times this incident has been escalated",
    )
    last_escalated_at = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="Timestamp of most recent escalation event",
    )
    last_activity_at = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="Timestamp of last comment, status change, or assignment — used by no_update trigger",
    )

    # Relationship to escalation events
    escalation_events = db.relationship(
        "EscalationEvent", backref="incident", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "severity IN ('P1','P2','P3','P4')",
            name="ck_incident_severity",
        ),
        db.CheckConstraint(
            "status IN ('open','investigating','resolved','closed')",
            name="ck_incident_status",
        ),
        db.CheckConstraint(
            "category IN ('functional','technical','data',"
            "'authorization','performance','other')",
            name="ck_incident_category",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "cutover_plan_id": self.cutover_plan_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "category": self.category,
            "status": self.status,
            "reported_by": self.reported_by,
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "assigned_to": self.assigned_to,
            "resolution": self.resolution,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "response_time_min": self.response_time_min,
            "resolution_time_min": self.resolution_time_min,
            "linked_entity_type": self.linked_entity_type,
            "linked_entity_id": self.linked_entity_id,
            "notes": self.notes,
            # FDD-B03 additions
            "incident_type": self.incident_type,
            "affected_module": self.affected_module,
            "affected_users_count": self.affected_users_count,
            "assigned_to_id": self.assigned_to_id,
            "first_response_at": self.first_response_at.isoformat() if self.first_response_at else None,
            "sla_response_breached": self.sla_response_breached,
            "sla_resolution_breached": self.sla_resolution_breached,
            "sla_response_deadline": self.sla_response_deadline.isoformat() if self.sla_response_deadline else None,
            "sla_resolution_deadline": self.sla_resolution_deadline.isoformat() if self.sla_resolution_deadline else None,
            "root_cause": self.root_cause,
            "root_cause_category": self.root_cause_category,
            "linked_backlog_item_id": self.linked_backlog_item_id,
            "requires_change_request": self.requires_change_request,
            "change_request_id": self.change_request_id,
            # FDD-B03-Phase-3: war room
            "war_room_id": self.war_room_id,
            # FDD-B03-Phase-2: escalation tracking
            "current_escalation_level": self.current_escalation_level,
            "escalation_count": self.escalation_count,
            "last_escalated_at": self.last_escalated_at.isoformat() if self.last_escalated_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<HypercareIncident {self.id}: {self.code or '#'} [{self.severity}] {self.title[:40]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 8. HypercareSLA
# ═════════════════════════════════════════════════════════════════════════════


class HypercareSLA(db.Model):
    """
    SLA targets per severity level for hypercare incidents.
    SAP standard: P1 = 15 min response / 4hr resolution, P4 = 8hr / 5 days.
    """

    __tablename__ = "hypercare_sla_targets"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    severity = db.Column(
        db.String(10), nullable=False,
        comment="P1 | P2 | P3 | P4",
    )
    response_target_min = db.Column(
        db.Integer, nullable=False,
        comment="Maximum response time in minutes",
    )
    resolution_target_min = db.Column(
        db.Integer, nullable=False,
        comment="Maximum resolution time in minutes",
    )
    escalation_after_min = db.Column(
        db.Integer, nullable=True,
        comment="Auto-escalation trigger after N minutes without response",
    )
    escalation_to = db.Column(
        db.String(100), default="",
        comment="Escalation contact (role or person)",
    )
    notes = db.Column(db.Text, default="")

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.UniqueConstraint(
            "cutover_plan_id", "severity",
            name="uq_sla_plan_severity",
        ),
        db.CheckConstraint(
            "severity IN ('P1','P2','P3','P4')",
            name="ck_sla_severity",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "cutover_plan_id": self.cutover_plan_id,
            "severity": self.severity,
            "response_target_min": self.response_target_min,
            "resolution_target_min": self.resolution_target_min,
            "escalation_after_min": self.escalation_after_min,
            "escalation_to": self.escalation_to,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<HypercareSLA {self.id}: {self.severity} resp={self.response_target_min}m res={self.resolution_target_min}m>"


# ── Hypercare Seed Helper ────────────────────────────────────────────────────


def seed_default_sla_targets(cutover_plan_id):
    """
    Create SAP-standard SLA targets for P1–P4 severity levels.
    P1: 15 min response, 4 hr resolution
    P2: 30 min response, 8 hr resolution
    P3: 4 hr response, 3 business-day resolution
    P4: 8 hr response, 5 business-day resolution
    """
    defaults = [
        {
            "severity": "P1",
            "response_target_min": 15,
            "resolution_target_min": 240,
            "escalation_after_min": 10,
            "escalation_to": "Hypercare Manager",
            "notes": "Critical — system down or data loss risk",
        },
        {
            "severity": "P2",
            "response_target_min": 30,
            "resolution_target_min": 480,
            "escalation_after_min": 20,
            "escalation_to": "Hypercare Manager",
            "notes": "High — major function impaired, workaround possible",
        },
        {
            "severity": "P3",
            "response_target_min": 240,
            "resolution_target_min": 1440,
            "escalation_after_min": 120,
            "escalation_to": "Module Lead",
            "notes": "Medium — minor function impaired",
        },
        {
            "severity": "P4",
            "response_target_min": 480,
            "resolution_target_min": 2400,
            "escalation_after_min": 240,
            "escalation_to": "Module Lead",
            "notes": "Low — cosmetic or enhancement request",
        },
    ]

    items = []
    for d in defaults:
        items.append(HypercareSLA(cutover_plan_id=cutover_plan_id, **d))
    db.session.add_all(items)
    db.session.flush()
    return items


# ═════════════════════════════════════════════════════════════════════════════
# 9. EscalationRule — FDD-B03-Phase-2
# ═════════════════════════════════════════════════════════════════════════════


class EscalationRule(db.Model):
    """Configurable escalation rule for hypercare incidents.

    Each rule defines when an incident at a given severity should be escalated
    to the next organizational level. Rules are evaluated in ascending
    level_order within each severity tier.

    Example chain for P1:
        level_order=1, L1, no_response, 10 min  -> Module Lead
        level_order=2, L2, no_response, 30 min  -> Hypercare Manager
        level_order=3, L3, no_resolution, 60 min -> Program Director
        level_order=4, vendor, no_resolution, 120 min -> SAP Support

    The escalation engine (evaluate_escalations in hypercare_service)
    processes rules in level_order. For each rule, if the trigger condition
    is met AND no EscalationEvent already exists at that level for the
    incident, a new event is created and a notification is sent.
    """

    __tablename__ = "escalation_rules"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    severity = db.Column(
        db.String(10), nullable=False,
        comment="P1 | P2 | P3 | P4 — which severity this rule applies to",
    )
    escalation_level = db.Column(
        db.String(20), nullable=False,
        comment="L1 | L2 | L3 | vendor | management — target escalation level",
    )
    level_order = db.Column(
        db.Integer, nullable=False, default=1,
        comment="Evaluation order within severity: 1 = first to fire, 2 = second, etc.",
    )

    # Trigger configuration
    trigger_type = db.Column(
        db.String(30), nullable=False, default="no_response",
        comment="no_response | no_update | no_resolution | severity_escalation",
    )
    trigger_after_min = db.Column(
        db.Integer, nullable=False,
        comment="Minutes after incident creation (or last activity) before escalation fires",
    )

    # Contact assignment
    escalate_to_role = db.Column(
        db.String(100), default="",
        comment="Role or team name: 'Hypercare Manager', 'SAP Basis Team', etc.",
    )
    escalate_to_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Specific platform user to notify (optional — role is primary)",
    )
    notification_channel = db.Column(
        db.String(30), default="platform",
        comment="platform | email — delivery channel for escalation alert",
    )

    is_active = db.Column(
        db.Boolean, nullable=False, default=True,
        comment="Inactive rules are skipped during evaluation",
    )

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "cutover_plan_id", "severity", "level_order",
            name="uq_escalation_severity_level",
        ),
        db.CheckConstraint(
            "severity IN ('P1','P2','P3','P4')",
            name="ck_esc_rule_severity",
        ),
        db.CheckConstraint(
            "escalation_level IN ('L1','L2','L3','vendor','management')",
            name="ck_esc_rule_level",
        ),
    )

    def to_dict(self) -> dict:
        """Serialize escalation rule to dict."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "cutover_plan_id": self.cutover_plan_id,
            "severity": self.severity,
            "escalation_level": self.escalation_level,
            "level_order": self.level_order,
            "trigger_type": self.trigger_type,
            "trigger_after_min": self.trigger_after_min,
            "escalate_to_role": self.escalate_to_role,
            "escalate_to_user_id": self.escalate_to_user_id,
            "notification_channel": self.notification_channel,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<EscalationRule {self.id}: {self.severity} L{self.level_order} "
            f"{self.trigger_type} after {self.trigger_after_min}m>"
        )


# ── Escalation Rule Seed Helper ─────────────────────────────────────────────


def seed_default_escalation_rules(cutover_plan_id, tenant_id=None):
    """Create SAP-standard escalation matrix for P1-P4 severity levels.

    Default escalation timings aligned with SAP Activate best practice:
        P1: L1 @10min, L2 @30min, L3 @60min, vendor @120min
        P2: L1 @20min, L2 @60min
        P3: L1 @120min
        P4: L1 @240min

    Idempotent: returns empty list if rules already exist for this plan.

    Args:
        cutover_plan_id: The CutoverPlan to seed rules for.
        tenant_id: Optional tenant scope.

    Returns:
        List of created EscalationRule instances.
    """
    existing = EscalationRule.query.filter_by(
        cutover_plan_id=cutover_plan_id
    ).first()
    if existing:
        return []

    defaults = [
        # P1: 4-level escalation chain
        {"severity": "P1", "escalation_level": "L1", "level_order": 1,
         "trigger_type": "no_response", "trigger_after_min": 10,
         "escalate_to_role": "Module Lead"},
        {"severity": "P1", "escalation_level": "L2", "level_order": 2,
         "trigger_type": "no_response", "trigger_after_min": 30,
         "escalate_to_role": "Hypercare Manager"},
        {"severity": "P1", "escalation_level": "L3", "level_order": 3,
         "trigger_type": "no_resolution", "trigger_after_min": 60,
         "escalate_to_role": "Program Director"},
        {"severity": "P1", "escalation_level": "vendor", "level_order": 4,
         "trigger_type": "no_resolution", "trigger_after_min": 120,
         "escalate_to_role": "SAP Support"},
        # P2: 2-level escalation chain
        {"severity": "P2", "escalation_level": "L1", "level_order": 1,
         "trigger_type": "no_response", "trigger_after_min": 20,
         "escalate_to_role": "Module Lead"},
        {"severity": "P2", "escalation_level": "L2", "level_order": 2,
         "trigger_type": "no_response", "trigger_after_min": 60,
         "escalate_to_role": "Hypercare Manager"},
        # P3: 1-level escalation
        {"severity": "P3", "escalation_level": "L1", "level_order": 1,
         "trigger_type": "no_response", "trigger_after_min": 120,
         "escalate_to_role": "Module Lead"},
        # P4: 1-level escalation
        {"severity": "P4", "escalation_level": "L1", "level_order": 1,
         "trigger_type": "no_response", "trigger_after_min": 240,
         "escalate_to_role": "Module Lead"},
    ]

    items = []
    for d in defaults:
        items.append(EscalationRule(
            cutover_plan_id=cutover_plan_id,
            tenant_id=tenant_id,
            **d,
        ))
    db.session.add_all(items)
    db.session.flush()
    return items


# ═════════════════════════════════════════════════════════════════════════════
# 10. EscalationEvent — FDD-B03-Phase-2
# ═════════════════════════════════════════════════════════════════════════════


class EscalationEvent(db.Model):
    """Immutable record of an escalation action on a hypercare incident.

    Append-only — events are never updated or deleted. This provides a
    complete audit trail of who was notified, when, and whether they
    acknowledged receipt.

    Events can be auto-generated by the escalation engine (is_auto=True) or
    created manually by a war room operator (is_auto=False).
    """

    __tablename__ = "escalation_events"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    incident_id = db.Column(
        db.Integer, db.ForeignKey("hypercare_incidents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    escalation_rule_id = db.Column(
        db.Integer, db.ForeignKey("escalation_rules.id", ondelete="SET NULL"),
        nullable=True,
        comment="Null for manual escalations; populated for auto-triggered",
    )

    escalation_level = db.Column(
        db.String(20), nullable=False,
        comment="L1 | L2 | L3 | vendor | management",
    )
    escalated_to = db.Column(
        db.String(150), nullable=False,
        comment="Role or person name that the incident was escalated to",
    )
    escalated_to_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Platform user notified (if resolvable from rule)",
    )

    trigger_type = db.Column(
        db.String(30), nullable=False,
        comment="no_response | no_update | no_resolution | severity_escalation | manual",
    )
    is_auto = db.Column(
        db.Boolean, nullable=False, default=True,
        comment="True = auto-triggered by rule engine; False = manual by operator",
    )

    notes = db.Column(db.Text, default="")

    # Acknowledgement tracking
    acknowledged_at = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="When the escalation recipient confirmed receipt",
    )
    acknowledged_by_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_esc_event_incident_time", "incident_id", "created_at"),
        db.Index("ix_esc_event_unack", "acknowledged_at"),
    )

    def to_dict(self) -> dict:
        """Serialize escalation event to dict."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "incident_id": self.incident_id,
            "escalation_rule_id": self.escalation_rule_id,
            "escalation_level": self.escalation_level,
            "escalated_to": self.escalated_to,
            "escalated_to_user_id": self.escalated_to_user_id,
            "trigger_type": self.trigger_type,
            "is_auto": self.is_auto,
            "notes": self.notes,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by_user_id": self.acknowledged_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<EscalationEvent {self.id}: incident={self.incident_id} "
            f"{self.escalation_level} -> {self.escalated_to}>"
        )


# ═════════════════════════════════════════════════════════════════════════════
# 11. PostGoliveChangeRequest — FDD-B03
# ═════════════════════════════════════════════════════════════════════════════


class PostGoliveChangeRequest(db.Model):
    """Change request raised during the hypercare window after go-live.

    Can originate from a hypercare incident or directly from a user.
    Unlike normal backlog items, production-system changes require Change
    Board approval before implementation.

    Lifecycle: draft → pending_approval → approved | rejected
                     → in_progress → implemented → closed

    Architecture note: program_id used (not project_id) — the platform uses
    'programs' not 'projects' as the top-level entity.
    """

    __tablename__ = "post_golive_change_requests"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tenant_id = db.Column(
        db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False, index=True,
    )

    cr_number = db.Column(
        db.String(20), nullable=False, unique=True, index=True,
        comment="Auto-generated sequential: CR-001, CR-002 …",
    )
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    change_type = db.Column(
        db.String(20), nullable=False,
        comment="config | development | data | authorization | emergency",
    )
    priority = db.Column(
        db.String(5), nullable=False, default="P3",
        comment="P1 | P2 | P3 | P4",
    )
    status = db.Column(
        db.String(30), nullable=False, default="draft",
        comment="draft | pending_approval | approved | rejected | in_progress | implemented | closed",
    )
    requested_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    approved_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    planned_implementation_date = db.Column(db.Date, nullable=True)
    actual_implementation_date = db.Column(db.Date, nullable=True)
    impact_assessment = db.Column(db.Text, nullable=True)
    test_required = db.Column(db.Boolean, nullable=False, default=True)
    rollback_plan = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # FDD-B03-Phase-3: War Room assignment
    war_room_id = db.Column(
        db.Integer, db.ForeignKey("hypercare_war_rooms.id", ondelete="SET NULL"),
        nullable=True,
        comment="Assigned war room session (nullable)",
    )

    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.Index("ix_pgcr_tenant_program", "tenant_id", "program_id"),
        db.CheckConstraint(
            "priority IN ('P1','P2','P3','P4')",
            name="ck_pgcr_priority",
        ),
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return f"<PostGoliveChangeRequest {self.cr_number} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# 10. IncidentComment — FDD-B03
# ═════════════════════════════════════════════════════════════════════════════


class IncidentComment(db.Model):
    """Audit-trail comment on a hypercare incident.

    Supports both internal consultant notes (is_internal=True, not shown to
    customer) and external update messages visible to the customer.
    is_internal prevents sensitive debugging info from reaching the customer.
    """

    __tablename__ = "incident_comments"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(
        db.Integer, db.ForeignKey("hypercare_incidents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    author_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(
        db.Boolean, nullable=False, default=False,
        comment="True = consultant-only note; False = visible to customer",
    )
    comment_type = db.Column(
        db.String(20), nullable=False, default="comment",
        comment="comment | escalation | status_change | assignment — enables filtering and audit",
    )
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return f"<IncidentComment {self.id} on incident={self.incident_id}>"


# ═════════════════════════════════════════════════════════════════════════════
# 12. HypercareWarRoom — FDD-B03-Phase-3
# ═════════════════════════════════════════════════════════════════════════════

WAR_ROOM_STATUSES = {"active", "monitoring", "resolved", "closed"}


class HypercareWarRoom(db.Model):
    """War room session for coordinating hypercare response.

    War rooms group related incidents and change requests under a single
    operational context.  Each war room has a lead, priority level, and
    lifecycle: active → monitoring → resolved → closed.

    Code format: WR-001 (plan-scoped, auto-generated in service layer).
    """

    __tablename__ = "hypercare_war_rooms"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    cutover_plan_id = db.Column(
        db.Integer, db.ForeignKey("cutover_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    code = db.Column(
        db.String(30), nullable=True,
        comment="Auto-generated: WR-001 (plan-scoped)",
    )
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(
        db.String(20), default="active",
        comment="active | monitoring | resolved | closed",
    )
    priority = db.Column(
        db.String(5), default="P2",
        comment="P1 | P2 | P3 | P4",
    )

    # Context
    affected_module = db.Column(
        db.String(20), nullable=True,
        comment="SAP module: FI | MM | SD | HCM | PP | etc.",
    )
    war_room_lead = db.Column(db.String(100), default="")
    war_room_lead_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Platform user leading this war room",
    )

    # Timeline
    opened_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    closed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Metadata
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('active','monitoring','resolved','closed')",
            name="ck_war_room_status",
        ),
        db.CheckConstraint(
            "priority IN ('P1','P2','P3','P4')",
            name="ck_war_room_priority",
        ),
    )

    # ── Relationships ────────────────────────────────────────────────────
    incidents = db.relationship(
        "HypercareIncident", backref="war_room", lazy="dynamic",
    )
    change_requests = db.relationship(
        "PostGoliveChangeRequest", backref="war_room", lazy="dynamic",
    )

    def to_dict(self) -> dict:
        """Serialize war room with aggregated counts."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "cutover_plan_id": self.cutover_plan_id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "affected_module": self.affected_module,
            "war_room_lead": self.war_room_lead,
            "war_room_lead_id": self.war_room_lead_id,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "incident_count": self.incidents.count(),
            "open_incident_count": self.incidents.filter_by(status="open").count()
                + self.incidents.filter_by(status="investigating").count(),
            "cr_count": self.change_requests.count(),
        }

    def __repr__(self) -> str:
        return f"<HypercareWarRoom {self.id}: {self.code or '#'} {self.name[:40]} [{self.status}]>"
