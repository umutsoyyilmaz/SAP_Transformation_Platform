"""
SAP Transformation Management Platform
Testing domain models — Sprint 5 (Test Hub) + TS-Sprint 1 (Suite & Step) + TS-Sprint 2 (Run & Defect).

Models (Sprint 5 — existing):
    - TestPlan:           top-level test planning container per program
    - TestCycle:          execution cycle within a plan
    - TestCase:           individual test case in the catalog
    - TestExecution:      execution record of a test case within a cycle
    - Defect:             defect/bug raised during testing

Models (TS-Sprint 1):
    - TestSuite:          grouping of test cases (SIT/UAT/Regression suites)
    - TestStep:           atomic step within a test case
    - TestCaseDependency: predecessor/successor dependency between test cases
    - TestCycleSuite:     junction table for cycle ↔ suite N:M relationship

Models (TS-Sprint 2 — new):
    - TestRun:            execution-independent run (manual/automated), environment, timing
    - TestStepResult:     step-level result within a run (pass/fail/blocked per step)
    - DefectComment:      threaded comments on a defect
    - DefectHistory:      field-level change audit trail for defects
    - DefectLink:         inter-defect linking (duplicate/related/blocks)

Architecture ref:
    Test Plan ──1:N──▶ Test Cycle ──N:M──▶ Test Suite ──1:N──▶ Test Case
    Test Case ──1:N──▶ Test Step
    Test Case ──N:M──▶ Test Case (dependencies)
    Test Cycle ──1:N──▶ Test Execution  (legacy, kept for backward compat)
    Test Cycle ──1:N──▶ Test Run ──1:N──▶ Test Step Result
    Test Case  ──1:N──▶ Defect ──1:N──▶ DefectComment / DefectHistory / DefectLink

Traceability: Requirement ↔ Test Case ↔ Defect (auto-built)
"""

from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────

TEST_LAYERS = {
    "unit", "sit", "uat", "regression", "performance", "cutover_rehearsal",
}

TEST_CASE_STATUSES = {
    "draft", "ready", "approved", "deprecated",
}

EXECUTION_RESULTS = {
    "not_run", "pass", "fail", "blocked", "deferred",
}

DEFECT_SEVERITIES = {"S1", "S2", "S3", "S4"}

DEFECT_PRIORITIES = {"P1", "P2", "P3", "P4"}

DEFECT_STATUSES = {
    "new", "assigned", "in_progress", "resolved", "retest",
    "closed", "rejected", "reopened", "deferred",
}

# ── 9-status lifecycle transition guard ──────────────────────────────────
VALID_TRANSITIONS = {
    "new":         ["assigned", "rejected", "deferred"],
    "assigned":    ["in_progress", "deferred"],
    "in_progress": ["resolved", "deferred"],
    "resolved":    ["retest"],
    "retest":      ["closed", "reopened"],
    "reopened":    ["assigned"],
    "closed":      ["reopened"],
    "deferred":    ["assigned"],
    "rejected":    [],
}


def validate_defect_transition(old_status, new_status):
    """Return True if transition is valid, False otherwise."""
    allowed = VALID_TRANSITIONS.get(old_status, [])
    return new_status in allowed


# ── SLA Matrix ───────────────────────────────────────────────────────────
SLA_MATRIX = {
    ("S1", "P1"): {"first_response_hours": 1,  "resolution_hours": 4,    "calendar": True},
    ("S1", "P2"): {"first_response_hours": 2,  "resolution_hours": 8,    "calendar": True},
    ("S2", "P1"): {"first_response_hours": 2,  "resolution_hours": 12,   "calendar": True},
    ("S2", "P2"): {"first_response_hours": 4,  "resolution_hours": 24,   "calendar": False},
    ("S3", "P3"): {"first_response_hours": 24, "resolution_hours": 72,   "calendar": False},
    ("S3", "P4"): {"first_response_hours": 48, "resolution_hours": 120,  "calendar": False},
    ("S4", "P3"): {"first_response_hours": 48, "resolution_hours": None, "calendar": False},
    ("S4", "P4"): {"first_response_hours": 48, "resolution_hours": None, "calendar": False},
}


UAT_SIGNOFF_STATUSES = {"pending", "approved", "rejected"}

CYCLE_STATUSES = {
    "planning", "in_progress", "completed", "cancelled",
}

PLAN_STATUSES = {
    "draft", "active", "completed", "cancelled",
}

SUITE_TYPES = {"SIT", "UAT", "Regression", "E2E", "Performance", "Custom"}

SUITE_STATUSES = {
    "draft", "active", "locked", "archived",
}

DEPENDENCY_TYPES = {
    "blocks",        # predecessor must pass before successor can run
    "related",       # informational link
    "data_feeds",    # predecessor produces test data for successor
}

# ── TS-Sprint 2 constants ────────────────────────────────────────────────

RUN_TYPES = {"manual", "automated", "exploratory"}

RUN_STATUSES = {
    "not_started", "in_progress", "completed", "aborted",
}

STEP_RESULTS = {
    "not_run", "pass", "fail", "blocked", "skipped",
}

DEFECT_LINK_TYPES = {
    "duplicate",   # this defect duplicates target
    "related",     # informational relationship
    "blocks",      # this defect blocks fixing target
}

# ── Test Data Bridge constants ─────────────────────────────────────────────
PLAN_TYPES = {
    "sit", "uat", "regression", "e2e",
    "cutover_rehearsal", "performance",
}

CYCLE_DATA_STATUSES = {
    "not_checked", "ready", "stale", "refresh_needed",
}

SCOPE_TYPES = {
    "l3_process", "scenario", "requirement",
}

TC_ADDED_METHODS = {
    "manual", "scope_suggest", "suite_import", "ai_suggest",
}

COVERAGE_STATUSES = {
    "not_covered", "partial", "covered",
}


# ═════════════════════════════════════════════════════════════════════════════
# TEST PLAN
# ═════════════════════════════════════════════════════════════════════════════

class TestPlan(db.Model):
    """
    Top-level test planning container for a program.

    Groups test cycles (SIT, UAT, Regression, etc.) and provides
    overall test strategy metadata.
    """

    __tablename__ = "test_plans"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name = db.Column(db.String(200), nullable=False, comment="e.g. SIT Master Plan, UAT Plan v2")
    description = db.Column(db.Text, default="")
    status = db.Column(
        db.String(30), default="draft", index=True,
        comment="draft | active | completed | cancelled",
    )
    test_strategy = db.Column(db.Text, default="", comment="High-level test approach / strategy notes")
    entry_criteria = db.Column(db.Text, default="", comment="Conditions to start this plan")
    exit_criteria = db.Column(db.Text, default="", comment="Conditions to close this plan")
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    plan_type = db.Column(
        db.String(30), default="sit",
        comment="sit | uat | regression | e2e | cutover_rehearsal | performance",
    )
    environment = db.Column(
        db.String(10), nullable=True,
        comment="DEV | QAS | PRE | PRD",
    )

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    cycles = db.relationship(
        "TestCycle", backref="plan", lazy="dynamic",
        cascade="all, delete-orphan", order_by="TestCycle.order",
    )
    plan_data_sets = db.relationship(
        "PlanDataSet", backref="plan", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    scopes = db.relationship(
        "PlanScope", backref="plan", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    plan_test_cases = db.relationship(
        "PlanTestCase", backref="plan", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_cycles=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "plan_type": self.plan_type,
            "environment": self.environment,
            "test_strategy": self.test_strategy,
            "entry_criteria": self.entry_criteria,
            "exit_criteria": self.exit_criteria,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_cycles:
            result["cycles"] = [c.to_dict() for c in self.cycles]
        return result

    def __repr__(self):
        return f"<TestPlan {self.id}: {self.name}>"


# ═════════════════════════════════════════════════════════════════════════════
# TEST CYCLE
# ═════════════════════════════════════════════════════════════════════════════

class TestCycle(db.Model):
    """
    Execution cycle within a test plan.

    e.g. "SIT Cycle 1", "UAT Cycle 2", "Regression Cycle 3"
    Contains test executions that link to test cases.
    """

    __tablename__ = "test_cycles"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    plan_id = db.Column(
        db.Integer, db.ForeignKey("test_plans.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name = db.Column(db.String(200), nullable=False, comment="e.g. SIT Cycle 1")
    description = db.Column(db.Text, default="")
    status = db.Column(
        db.String(30), default="planning", index=True,
        comment="planning | in_progress | completed | cancelled",
    )
    test_layer = db.Column(
        db.String(30), default="sit",
        comment="unit | sit | uat | regression | performance | cutover_rehearsal",
    )
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    order = db.Column(db.Integer, default=0, comment="Sort order within plan")
    environment = db.Column(
        db.String(10), nullable=True,
        comment="DEV | QAS | PRE | PRD",
    )
    build_tag = db.Column(
        db.String(50), default="",
        comment="Transport request or build label, e.g. TR-12345",
    )

    # ── Entry/Exit Criteria (TS-Sprint 3)
    entry_criteria = db.Column(
        db.JSON, nullable=True,
        comment='JSON list of entry criteria, e.g. [{"criterion": "...", "met": true}]',
    )
    exit_criteria = db.Column(
        db.JSON, nullable=True,
        comment='JSON list of exit criteria, e.g. [{"criterion": "...", "met": false}]',
    )

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    executions = db.relationship(
        "TestExecution", backref="cycle", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # ── Relationships
    cycle_data_sets = db.relationship(
        "CycleDataSet", backref="cycle", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self, include_executions=False):
        result = {
            "id": self.id,
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "test_layer": self.test_layer,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "order": self.order,
            "environment": self.environment,
            "build_tag": self.build_tag,
            "entry_criteria": self.entry_criteria,
            "exit_criteria": self.exit_criteria,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_executions:
            result["executions"] = [e.to_dict() for e in self.executions]
        return result

    def __repr__(self):
        return f"<TestCycle {self.id}: {self.name}>"


# ═════════════════════════════════════════════════════════════════════════════
# TEST CASE (Catalog)
# ═════════════════════════════════════════════════════════════════════════════

class TestCase(db.Model):
    """
    Individual test case in the test catalog.

    Linked to requirements for traceability.
    Test layers: Unit, SIT, UAT, Regression, Performance, Cutover Rehearsal.
    """

    __tablename__ = "test_cases"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    requirement_id = db.Column(
        db.Integer, db.ForeignKey("requirements.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="Linked requirement for traceability",
    )
    explore_requirement_id = db.Column(
        db.String(36),
        db.ForeignKey("explore_requirements.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Linked Explore phase requirement (new model)",
    )
    backlog_item_id = db.Column(
        db.Integer, db.ForeignKey("backlog_items.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="Linked WRICEF backlog item",
    )
    config_item_id = db.Column(
        db.Integer, db.ForeignKey("config_items.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="Linked config item",
    )
    process_level_id = db.Column(
        db.String(36), db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="ADR-FINAL: Direct FK to L3/L4 process for scope tracing",
    )
    suite_id = db.Column(
        db.Integer, db.ForeignKey("test_suites.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="Linked test suite",
    )

    # ── Identification
    code = db.Column(
        db.String(50), default="",
        comment="Auto or manual code, e.g. TC-FI-001, TC-SD-042",
    )
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")

    # ── Test details
    test_layer = db.Column(
        db.String(30), default="sit",
        comment="unit | sit | uat | regression | performance | cutover_rehearsal",
    )
    module = db.Column(db.String(50), default="", comment="SAP module: FI, MM, SD, etc.")
    preconditions = db.Column(db.Text, default="", comment="Setup / preconditions")
    test_steps = db.Column(db.Text, default="", comment="Step-by-step test procedure")
    expected_result = db.Column(db.Text, default="", comment="Expected outcome")
    test_data_set = db.Column(db.Text, default="", comment="Test data description or reference")
    transaction_code = db.Column(
        db.String(20), default="",
        comment="SAP transaction code, e.g. VA01, ME21N, FB01",
    )
    data_set_id = db.Column(
        db.Integer, db.ForeignKey("test_data_sets.id", ondelete="SET NULL"),
        nullable=True, comment="Linked test data set from Data Factory",
    )

    # ── Status
    status = db.Column(
        db.String(30), default="draft",
        comment="draft | ready | approved | deprecated",
    )
    priority = db.Column(
        db.String(20), default="medium",
        comment="low | medium | high | critical",
    )
    is_regression = db.Column(
        db.Boolean, default=False,
        comment="Flagged for regression set (re-run on upgrades/releases)",
    )
    assigned_to = db.Column(db.String(100), default="", comment="Tester name")
    assigned_to_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True, comment="FK → team_members",
    )

    # ── Clone tracking
    cloned_from_id = db.Column(
        db.Integer, db.ForeignKey("test_cases.id", ondelete="SET NULL"),
        nullable=True, comment="Source test case this was cloned from",
    )

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    cloned_from = db.relationship(
        "TestCase", remote_side="TestCase.id",
        foreign_keys=[cloned_from_id],
        uselist=False,
    )
    executions = db.relationship(
        "TestExecution", backref="test_case", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    defects = db.relationship(
        "Defect", backref="test_case", lazy="dynamic",
        cascade="save-update, merge",
    )
    steps = db.relationship(
        "TestStep", backref="test_case", lazy="select",
        cascade="all, delete-orphan", order_by="TestStep.step_no",
    )
    predecessor_deps = db.relationship(
        "TestCaseDependency",
        foreign_keys="TestCaseDependency.successor_id",
        backref="successor_case", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    successor_deps = db.relationship(
        "TestCaseDependency",
        foreign_keys="TestCaseDependency.predecessor_id",
        backref="predecessor_case", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    assigned_member = db.relationship("TeamMember", foreign_keys=[assigned_to_id])

    def to_dict(self, include_steps=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "requirement_id": self.requirement_id,
            "explore_requirement_id": self.explore_requirement_id,
            "backlog_item_id": self.backlog_item_id,
            "config_item_id": self.config_item_id,
            "process_level_id": self.process_level_id,
            "suite_id": self.suite_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "test_layer": self.test_layer,
            "module": self.module,
            "preconditions": self.preconditions,
            "test_steps": self.test_steps,
            "expected_result": self.expected_result,
            "test_data_set": self.test_data_set,
            "transaction_code": self.transaction_code,
            "data_set_id": self.data_set_id,
            "status": self.status,
            "priority": self.priority,
            "is_regression": self.is_regression,
            "assigned_to": self.assigned_to,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to_member": self.assigned_member.to_dict() if self.assigned_to_id and self.assigned_member else None,
            "cloned_from_id": self.cloned_from_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_steps:
            result["steps"] = [s.to_dict() for s in self.steps]
        return result

    def __repr__(self):
        return f"<TestCase {self.id}: {self.code or self.title[:30]}>"


# ═════════════════════════════════════════════════════════════════════════════
# TEST EXECUTION
# ═════════════════════════════════════════════════════════════════════════════

class TestExecution(db.Model):
    """
    Execution record of a test case within a test cycle.

    Records the result (pass/fail/blocked/deferred) plus execution metadata.
    """

    __tablename__ = "test_executions"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cycle_id = db.Column(
        db.Integer, db.ForeignKey("test_cycles.id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    test_case_id = db.Column(
        db.Integer, db.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False,
        index=True,
    )

    result = db.Column(
        db.String(20), default="not_run",
        comment="not_run | pass | fail | blocked | deferred",
    )
    assigned_to = db.Column(
        db.String(100), default="",
        comment="Pre-assigned tester name (before execution)",
    )
    assigned_to_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True,
        comment="Pre-assigned tester FK → team_members",
    )
    executed_by = db.Column(db.String(100), default="", comment="Tester name")
    executed_by_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True, comment="FK → team_members",
    )
    executed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True, comment="Execution time in minutes")
    notes = db.Column(db.Text, default="", comment="Execution notes / evidence")
    evidence_url = db.Column(db.String(500), default="", comment="Screenshot / log URL")

    # ── ADR-FINAL: Execution unification fields
    attempt_number = db.Column(
        db.Integer, default=1,
        comment="Attempt number — retest tracking (carry-forward increments)",
    )
    test_run_id = db.Column(
        db.Integer, db.ForeignKey("test_runs.id", ondelete="SET NULL"),
        nullable=True,
        comment="Optional link to TestRun metadata (who/when/environment)",
    )

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    assigned_member = db.relationship("TeamMember", foreign_keys=[assigned_to_id])
    executed_by_member = db.relationship("TeamMember", foreign_keys=[executed_by_id])

    # ── ADR-FINAL: Step results live under execution (SSOT)
    step_results = db.relationship(
        "TestStepResult", backref="execution", lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="TestStepResult.step_no",
    )

    def derive_result_from_steps(self):
        """Auto-derive execution result from step results.

        Rules:
        - All steps pass → execution pass
        - Any step fail → execution fail
        - Any step blocked (no fail) → execution blocked
        - Otherwise → not_run
        """
        steps = self.step_results.all()
        if not steps:
            return self.result  # No steps, keep current
        results = [s.result for s in steps]
        if all(r == "pass" for r in results):
            return "pass"
        if any(r == "fail" for r in results):
            return "fail"
        if any(r == "blocked" for r in results):
            return "blocked"
        if all(r == "not_run" for r in results):
            return "not_run"
        return self.result

    def to_dict(self, include_step_results=False):
        d = {
            "id": self.id,
            "cycle_id": self.cycle_id,
            "test_case_id": self.test_case_id,
            "result": self.result,
            "assigned_to": self.assigned_to,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to_member": self.assigned_member.to_dict() if self.assigned_to_id and self.assigned_member else None,
            "executed_by": self.executed_by,
            "executed_by_id": self.executed_by_id,
            "executed_by_member": self.executed_by_member.to_dict() if self.executed_by_id and self.executed_by_member else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "duration_minutes": self.duration_minutes,
            "notes": self.notes,
            "evidence_url": self.evidence_url,
            "attempt_number": self.attempt_number,
            "test_run_id": self.test_run_id,
            "step_result_count": self.step_results.count() if self.id else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_step_results:
            d["step_results"] = [sr.to_dict() for sr in self.step_results.all()]
        return d

    def __repr__(self):
        return f"<TestExecution {self.id}: case#{self.test_case_id} → {self.result}>"


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT
# ═════════════════════════════════════════════════════════════════════════════

class Defect(db.Model):
    """
    Defect / bug raised during testing.

    Linked to a test case (origin) and optionally to a WRICEF item or config item
    (root cause / fix target).

    Severity: P1 (blocker) → P4 (cosmetic)
    Lifecycle: new → open → in_progress → fixed → retest → closed
                                                   └──▶ reopened ──▶ in_progress
    """

    __tablename__ = "defects"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    test_case_id = db.Column(
        db.Integer, db.ForeignKey("test_cases.id", ondelete="SET NULL"),
        nullable=True, comment="Test case that found this defect",
        index=True,
    )
    backlog_item_id = db.Column(
        db.Integer, db.ForeignKey("backlog_items.id", ondelete="SET NULL"),
        nullable=True, comment="Linked WRICEF item (fix target)",
    )
    config_item_id = db.Column(
        db.Integer, db.ForeignKey("config_items.id", ondelete="SET NULL"),
        nullable=True, comment="Linked config item (fix target)",
    )
    linked_requirement_id = db.Column(
        db.Integer, db.ForeignKey("requirements.id", ondelete="SET NULL"),
        nullable=True, comment="Linked requirement (TS-Sprint 2)",
        index=True,
    )
    explore_requirement_id = db.Column(
        db.String(36),
        db.ForeignKey("explore_requirements.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Linked Explore phase requirement (new model)",
    )

    # ── Identification
    code = db.Column(
        db.String(50), default="",
        comment="Auto code, e.g. DEF-0001, DEF-FI-042",
    )
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    steps_to_reproduce = db.Column(db.Text, default="")

    # ── Classification
    severity = db.Column(
        db.String(10), default="S3",
        comment="S1 (showstopper) | S2 (critical) | S3 (major) | S4 (minor)",
    )
    priority = db.Column(
        db.String(10), default="P3",
        comment="P1 (immediate) | P2 (high) | P3 (medium) | P4 (low)",
    )
    status = db.Column(
        db.String(30), default="new",
        comment="new | assigned | in_progress | resolved | retest | closed | rejected | reopened | deferred",
    )
    module = db.Column(db.String(50), default="", comment="SAP module")
    environment = db.Column(db.String(50), default="", comment="DEV | QAS | PRD")

    # ── SLA
    sla_due_date = db.Column(
        db.DateTime(timezone=True), nullable=True,
        comment="SLA resolution deadline, auto-computed from severity+priority matrix",
    )

    # ── Assignment & tracking
    reported_by = db.Column(db.String(100), default="")
    assigned_to = db.Column(db.String(100), default="")
    found_in_cycle = db.Column(db.String(100), default="", comment="Which test cycle found it (legacy text)")
    found_in_cycle_id = db.Column(
        db.Integer, db.ForeignKey("test_cycles.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="FK to test cycle where defect was found",
    )

    # ── Aging & reopen tracking
    reported_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reopen_count = db.Column(db.Integer, default=0, comment="Number of times reopened")

    # ── Resolution
    resolution = db.Column(db.Text, default="", comment="Fix description")
    root_cause = db.Column(db.Text, default="", comment="Root cause analysis")
    transport_request = db.Column(db.String(30), default="", comment="SAP transport for the fix")
    notes = db.Column(db.Text, default="")

    # ── Relationships (TS-Sprint 2)
    comments = db.relationship(
        "DefectComment", backref="defect", lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="DefectComment.created_at",
    )
    history = db.relationship(
        "DefectHistory", backref="defect", lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="DefectHistory.changed_at.desc()",
    )
    source_links = db.relationship(
        "DefectLink", foreign_keys="DefectLink.source_defect_id",
        backref="source_defect", lazy="dynamic", cascade="all, delete-orphan",
    )
    target_links = db.relationship(
        "DefectLink", foreign_keys="DefectLink.target_defect_id",
        backref="target_defect", lazy="dynamic", cascade="all, delete-orphan",
    )

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def aging_days(self):
        """Calculate how many days since the defect was reported."""
        if self.status in ("closed", "rejected"):
            end = self.resolved_at or self.updated_at or datetime.now(timezone.utc)
        else:
            end = datetime.now(timezone.utc)
        start = self.reported_at or self.created_at
        if start and end:
            # Handle timezone-naive datetimes
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            return (end - start).days
        return 0

    @property
    def sla_status(self):
        """Compute SLA status: on_track / warning / breached."""
        if not self.sla_due_date:
            return None
        if self.status in ("closed", "rejected"):
            return "on_track"
        now = datetime.now(timezone.utc)
        due = self.sla_due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if now > due:
            return "breached"
        # Warning: >75% elapsed
        created = self.reported_at or self.created_at
        if created:
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            total = (due - created).total_seconds()
            elapsed = (now - created).total_seconds()
            if total > 0 and (elapsed / total) > 0.75:
                return "warning"
        return "on_track"

    def to_dict(self, include_comments=False):
        d = {
            "id": self.id,
            "program_id": self.program_id,
            "test_case_id": self.test_case_id,
            "backlog_item_id": self.backlog_item_id,
            "config_item_id": self.config_item_id,
            "linked_requirement_id": self.linked_requirement_id,
            "explore_requirement_id": self.explore_requirement_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "steps_to_reproduce": self.steps_to_reproduce,
            "severity": self.severity,
            "priority": self.priority,
            "status": self.status,
            "module": self.module,
            "environment": self.environment,
            "reported_by": self.reported_by,
            "assigned_to": self.assigned_to,
            "found_in_cycle": self.found_in_cycle,
            "found_in_cycle_id": self.found_in_cycle_id,
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "sla_due_date": self.sla_due_date.isoformat() if self.sla_due_date else None,
            "sla_status": self.sla_status,
            "reopen_count": self.reopen_count,
            "aging_days": self.aging_days,
            "resolution": self.resolution,
            "root_cause": self.root_cause,
            "transport_request": self.transport_request,
            "notes": self.notes,
            "comment_count": self.comments.count() if self.id else 0,
            "link_count": (
                (self.source_links.count() + self.target_links.count())
                if self.id else 0
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_comments:
            d["comments"] = [c.to_dict() for c in self.comments.all()]
        return d

    def __repr__(self):
        return f"<Defect {self.id}: [{self.severity}] {self.code or self.title[:30]}>"


# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITE  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

class TestSuite(db.Model):
    """
    Logical grouping of test cases by type (SIT, UAT, Regression, etc.).

    A suite owns test cases and can be assigned to multiple test cycles
    via the TestCycleSuite junction table.

    Status FSM: draft → active → locked → archived
    """

    __tablename__ = "test_suites"

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

    name = db.Column(db.String(200), nullable=False, comment="e.g. SIT Suite — Finance")
    description = db.Column(db.Text, default="")
    suite_type = db.Column(
        db.String(30), default="SIT",
        comment="SIT | UAT | Regression | E2E | Performance | Custom",
    )
    status = db.Column(
        db.String(30), default="draft",
        comment="draft | active | locked | archived",
    )
    module = db.Column(db.String(50), default="", comment="SAP module scope: FI, MM, SD, etc.")
    owner = db.Column(db.String(100), default="", comment="Suite owner / test lead")
    owner_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True, comment="FK → team_members",
    )
    tags = db.Column(db.Text, default="", comment="Comma-separated tags for filtering")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships
    test_cases = db.relationship(
        "TestCase", backref="suite", lazy="dynamic",
        cascade="save-update, merge",
        foreign_keys="TestCase.suite_id",
    )
    cycle_suites = db.relationship(
        "TestCycleSuite", backref="suite", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    owner_member = db.relationship("TeamMember", foreign_keys=[owner_id])

    def to_dict(self, include_cases=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "suite_type": self.suite_type,
            "status": self.status,
            "module": self.module,
            "owner": self.owner,
            "owner_id": self.owner_id,
            "owner_member": self.owner_member.to_dict() if self.owner_id and self.owner_member else None,
            "tags": self.tags,
            "case_count": self.test_cases.count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_cases:
            result["test_cases"] = [tc.to_dict() for tc in self.test_cases]
        return result

    def __repr__(self):
        return f"<TestSuite {self.id}: [{self.suite_type}] {self.name}>"


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEP  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

class TestStep(db.Model):
    """
    Atomic step within a test case.

    Provides structured step-by-step execution instructions
    replacing the free-text test_steps field on TestCase.
    """

    __tablename__ = "test_steps"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_case_id = db.Column(
        db.Integer, db.ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    step_no = db.Column(db.Integer, nullable=False, comment="Sequential step number")
    action = db.Column(db.Text, nullable=False, comment="Action to perform")
    expected_result = db.Column(db.Text, default="", comment="Expected outcome")
    test_data = db.Column(db.Text, default="", comment="Test data for this step")
    notes = db.Column(db.Text, default="", comment="Additional notes / hints")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "test_case_id": self.test_case_id,
            "step_no": self.step_no,
            "action": self.action,
            "expected_result": self.expected_result,
            "test_data": self.test_data,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<TestStep {self.id}: case#{self.test_case_id} step#{self.step_no}>"


# ═════════════════════════════════════════════════════════════════════════════
# TEST CASE DEPENDENCY  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

class TestCaseDependency(db.Model):
    """
    Dependency link between two test cases.

    Types:
        blocks     — predecessor must pass before successor can execute
        related    — informational link (no execution constraint)
        data_feeds — predecessor produces test data consumed by successor
    """

    __tablename__ = "test_case_dependencies"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    predecessor_id = db.Column(
        db.Integer, db.ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    successor_id = db.Column(
        db.Integer, db.ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    dependency_type = db.Column(
        db.String(30), default="blocks",
        comment="blocks | related | data_feeds",
    )
    notes = db.Column(db.Text, default="", comment="Dependency description")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # ── Unique constraint: no duplicate dependency between same pair
    __table_args__ = (
        db.UniqueConstraint("predecessor_id", "successor_id", name="uq_tc_dependency"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "predecessor_id": self.predecessor_id,
            "successor_id": self.successor_id,
            "dependency_type": self.dependency_type,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return (
            f"<TestCaseDependency {self.id}: "
            f"#{self.predecessor_id} → #{self.successor_id} ({self.dependency_type})>"
        )


# ═════════════════════════════════════════════════════════════════════════════
# TEST CYCLE ↔ SUITE JUNCTION  (TS-Sprint 1)
# ═════════════════════════════════════════════════════════════════════════════

class TestCycleSuite(db.Model):
    """
    Junction table linking test cycles and test suites (N:M).

    A test cycle can include multiple suites, and a suite can be
    assigned to multiple cycles across different plans.
    """

    __tablename__ = "test_cycle_suites"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cycle_id = db.Column(
        db.Integer, db.ForeignKey("test_cycles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    suite_id = db.Column(
        db.Integer, db.ForeignKey("test_suites.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    order = db.Column(db.Integer, default=0, comment="Execution order within cycle")
    notes = db.Column(db.Text, default="", comment="Assignment notes")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # ── Unique constraint: no duplicate assignment
    __table_args__ = (
        db.UniqueConstraint("cycle_id", "suite_id", name="uq_cycle_suite"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "cycle_id": self.cycle_id,
            "suite_id": self.suite_id,
            "order": self.order,
            "notes": self.notes,
            "suite_name": self.suite.name if self.suite else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<TestCycleSuite {self.id}: cycle#{self.cycle_id} ↔ suite#{self.suite_id}>"


# ═════════════════════════════════════════════════════════════════════════════
# TEST RUN  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class TestRun(db.Model):
    """
    Execution-independent test run.

    A run represents a single end-to-end execution of a test case within a
    test cycle.  Unlike TestExecution (legacy), TestRun captures run_type,
    environment, timing, and links to step-level results.

    Lifecycle: not_started → in_progress → completed / aborted
    """

    __tablename__ = "test_runs"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cycle_id = db.Column(
        db.Integer, db.ForeignKey("test_cycles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    test_case_id = db.Column(
        db.Integer, db.ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    run_type = db.Column(
        db.String(20), default="manual",
        comment="manual | automated | exploratory",
    )
    status = db.Column(
        db.String(20), default="not_started",
        comment="not_started | in_progress | completed | aborted",
    )
    result = db.Column(
        db.String(20), default="not_run",
        comment="not_run | pass | fail | blocked | deferred",
    )
    environment = db.Column(db.String(50), default="", comment="DEV | QAS | PRD")
    tester = db.Column(db.String(100), default="", comment="Tester name")
    notes = db.Column(db.Text, default="")
    evidence_url = db.Column(db.String(500), default="", comment="Screenshot / log URL")

    # ── Timing
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True, comment="Run duration in minutes")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships (TestRun is now optional metadata — step_results moved to TestExecution)

    @property
    def computed_duration(self):
        """Calculate duration from timestamps if not explicitly set."""
        if self.duration_minutes is not None:
            return self.duration_minutes
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None

    def to_dict(self):
        d = {
            "id": self.id,
            "cycle_id": self.cycle_id,
            "test_case_id": self.test_case_id,
            "run_type": self.run_type,
            "status": self.status,
            "result": self.result,
            "environment": self.environment,
            "tester": self.tester,
            "notes": self.notes,
            "evidence_url": self.evidence_url,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_minutes": self.computed_duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        return d

    def __repr__(self):
        return f"<TestRun {self.id}: case#{self.test_case_id} [{self.run_type}] → {self.result}>"


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEP RESULT  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class TestStepResult(db.Model):
    """
    Step-level result within a test execution (ADR-FINAL).

    Records pass/fail/blocked at individual step granularity, enabling
    precise failure pinpointing.  Linked to TestExecution (SSOT),
    not to TestRun (which is optional metadata).
    """

    __tablename__ = "test_step_results"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    execution_id = db.Column(
        db.Integer, db.ForeignKey("test_executions.id", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="Parent execution — SSOT (ADR-FINAL)",
    )
    step_id = db.Column(
        db.Integer, db.ForeignKey("test_steps.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="Optional FK to TestStep",
    )

    step_no = db.Column(db.Integer, nullable=False, comment="Step number (copied from TestStep or manual)")
    result = db.Column(
        db.String(20), default="not_run",
        comment="not_run | pass | fail | blocked | skipped",
    )
    actual_result = db.Column(db.Text, default="", comment="Actual observed result")
    notes = db.Column(db.Text, default="")
    screenshot_url = db.Column(db.String(500), default="", comment="Evidence screenshot")
    executed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "step_id": self.step_id,
            "step_no": self.step_no,
            "result": self.result,
            "actual_result": self.actual_result,
            "notes": self.notes,
            "screenshot_url": self.screenshot_url,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<TestStepResult {self.id}: exec#{self.execution_id} step#{self.step_no} → {self.result}>"


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT COMMENT  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class DefectComment(db.Model):
    """
    Threaded comment on a defect — supports discussion between testers,
    developers, and project leads.
    """

    __tablename__ = "defect_comments"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    defect_id = db.Column(
        db.Integer, db.ForeignKey("defects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    author = db.Column(db.String(100), nullable=False, comment="Comment author")
    body = db.Column(db.Text, nullable=False, comment="Comment body (Markdown supported)")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "defect_id": self.defect_id,
            "author": self.author,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<DefectComment {self.id}: defect#{self.defect_id} by {self.author}>"


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT HISTORY  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class DefectHistory(db.Model):
    """
    Field-level change audit trail for defects.

    Automatically populated when a defect is updated (via API hook).
    Enables full change replay and accountability.
    """

    __tablename__ = "defect_history"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    defect_id = db.Column(
        db.Integer, db.ForeignKey("defects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    field = db.Column(db.String(50), nullable=False, comment="Changed field name")
    old_value = db.Column(db.Text, default="", comment="Previous value")
    new_value = db.Column(db.Text, default="", comment="New value")
    changed_by = db.Column(db.String(100), default="", comment="Who made the change")
    changed_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "defect_id": self.defect_id,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }

    def __repr__(self):
        return f"<DefectHistory {self.id}: defect#{self.defect_id} {self.field}>"


# ═════════════════════════════════════════════════════════════════════════════
# DEFECT LINK  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class DefectLink(db.Model):
    """
    Inter-defect link: duplicate, related, or blocks relationship.

    source_defect → target_defect with a link_type.
    Unique constraint prevents duplicate links between the same pair.
    """

    __tablename__ = "defect_links"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_defect_id = db.Column(
        db.Integer, db.ForeignKey("defects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    target_defect_id = db.Column(
        db.Integer, db.ForeignKey("defects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    link_type = db.Column(
        db.String(20), default="related",
        comment="duplicate | related | blocks",
    )
    notes = db.Column(db.Text, default="")

    # ── Audit
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # ── Unique constraint
    __table_args__ = (
        db.UniqueConstraint(
            "source_defect_id", "target_defect_id",
            name="uq_defect_link",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "source_defect_id": self.source_defect_id,
            "target_defect_id": self.target_defect_id,
            "link_type": self.link_type,
            "notes": self.notes,
            "source_title": self.source_defect.title if self.source_defect else None,
            "target_title": self.target_defect.title if self.target_defect else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<DefectLink {self.id}: #{self.source_defect_id} —[{self.link_type}]→ #{self.target_defect_id}>"


# ═════════════════════════════════════════════════════════════════════════════
# UAT SIGN-OFF  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class UATSignOff(db.Model):
    """
    UAT sign-off record per process area / scope item.

    Business rule: Only BPO or PM roles can sign off.
    Linked to a test cycle (UAT cycle) for context.
    """

    __tablename__ = "uat_signoffs"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_cycle_id = db.Column(
        db.Integer, db.ForeignKey("test_cycles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    process_area = db.Column(
        db.String(100), nullable=False,
        comment="e.g. Finance, Logistics, HR",
    )
    scope_item_id = db.Column(
        db.String(36), nullable=True,
        comment="Reference to scope item / process level ID",
    )
    signed_off_by = db.Column(
        db.String(100), nullable=False,
        comment="BPO or PM who signed off",
    )
    sign_off_date = db.Column(
        db.DateTime(timezone=True), nullable=True,
    )
    status = db.Column(
        db.String(20), default="pending",
        comment="pending | approved | rejected",
    )
    role = db.Column(
        db.String(20), default="BPO",
        comment="BPO | PM — only these roles can sign off",
    )
    comments = db.Column(db.Text, default="")

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "test_cycle_id": self.test_cycle_id,
            "process_area": self.process_area,
            "scope_item_id": self.scope_item_id,
            "signed_off_by": self.signed_off_by,
            "sign_off_date": self.sign_off_date.isoformat() if self.sign_off_date else None,
            "status": self.status,
            "role": self.role,
            "comments": self.comments,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<UATSignOff {self.id}: [{self.status}] {self.process_area}>"


# ═════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TEST RESULT  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class PerfTestResult(db.Model):
    """
    Performance test result for a test case execution.

    Business rule: pass_fail is auto-computed from response_time_ms <= target_response_ms.
    Stores throughput, concurrent users, and environment info.
    """

    __tablename__ = "perf_test_results"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_case_id = db.Column(
        db.Integer, db.ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    test_run_id = db.Column(
        db.Integer, db.ForeignKey("test_runs.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    response_time_ms = db.Column(db.Float, nullable=False, comment="Actual response time in ms")
    throughput_rps = db.Column(db.Float, nullable=True, comment="Requests per second")
    concurrent_users = db.Column(db.Integer, nullable=True, comment="Number of concurrent users")
    target_response_ms = db.Column(db.Float, nullable=False, comment="Target response time in ms")
    target_throughput_rps = db.Column(db.Float, nullable=True, comment="Target throughput RPS")

    environment = db.Column(db.String(50), default="", comment="DEV | QAS | PRD | PERF")
    notes = db.Column(db.Text, default="")
    executed_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    @property
    def pass_fail(self):
        """Auto-compute pass/fail based on response time vs target."""
        return self.response_time_ms <= self.target_response_ms

    def to_dict(self):
        return {
            "id": self.id,
            "test_case_id": self.test_case_id,
            "test_run_id": self.test_run_id,
            "response_time_ms": self.response_time_ms,
            "throughput_rps": self.throughput_rps,
            "concurrent_users": self.concurrent_users,
            "target_response_ms": self.target_response_ms,
            "target_throughput_rps": self.target_throughput_rps,
            "pass_fail": self.pass_fail,
            "environment": self.environment,
            "notes": self.notes,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        pf = "PASS" if self.pass_fail else "FAIL"
        return f"<PerfTestResult {self.id}: {self.response_time_ms}ms [{pf}]>"


# ═════════════════════════════════════════════════════════════════════════════
# TEST DAILY SNAPSHOT  (TS-Sprint 3)
# ═════════════════════════════════════════════════════════════════════════════

class TestDailySnapshot(db.Model):
    """
    Daily test progress snapshot for trend reporting.

    Business rule: Created by daily cronjob or manual trigger.
    Captures point-in-time counts for test execution and defects.
    """

    __tablename__ = "test_daily_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    snapshot_date = db.Column(db.Date, nullable=False, index=True)
    test_cycle_id = db.Column(
        db.Integer, db.ForeignKey("test_cycles.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Nullable — snapshot can be program-wide",
    )
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    wave = db.Column(db.String(50), default="", comment="Implementation wave label")

    # ── Test execution counts
    total_cases = db.Column(db.Integer, default=0)
    passed = db.Column(db.Integer, default=0)
    failed = db.Column(db.Integer, default=0)
    blocked = db.Column(db.Integer, default=0)
    not_run = db.Column(db.Integer, default=0)

    # ── Defect counts by severity
    open_defects_s1 = db.Column(db.Integer, default=0)
    open_defects_s2 = db.Column(db.Integer, default=0)
    open_defects_s3 = db.Column(db.Integer, default=0)
    open_defects_s4 = db.Column(db.Integer, default=0)
    closed_defects = db.Column(db.Integer, default=0)

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    @property
    def pass_rate(self):
        """Compute pass rate as percentage."""
        executed = self.passed + self.failed + self.blocked
        if executed == 0:
            return 0.0
        return round(self.passed / executed * 100, 1)

    def to_dict(self):
        return {
            "id": self.id,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "test_cycle_id": self.test_cycle_id,
            "program_id": self.program_id,
            "wave": self.wave,
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "blocked": self.blocked,
            "not_run": self.not_run,
            "pass_rate": self.pass_rate,
            "open_defects_s1": self.open_defects_s1,
            "open_defects_s2": self.open_defects_s2,
            "open_defects_s3": self.open_defects_s3,
            "open_defects_s4": self.open_defects_s4,
            "closed_defects": self.closed_defects,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<TestDailySnapshot {self.id}: {self.snapshot_date}>"


# ═════════════════════════════════════════════════════════════════════════════
# PLAN DATA SET  (Data Bridge)
# ═════════════════════════════════════════════════════════════════════════════

class PlanDataSet(db.Model):
    """Bridge: TestPlan ↔ TestDataSet (N:M).

    Declares which data sets a test plan requires.
    is_mandatory = True means testing must not start without this data.
    """

    __tablename__ = "plan_data_sets"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    plan_id = db.Column(
        db.Integer, db.ForeignKey("test_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    data_set_id = db.Column(
        db.Integer, db.ForeignKey("test_data_sets.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    is_mandatory = db.Column(
        db.Boolean, default=True,
        comment="True = test must not start without this data set",
    )
    notes = db.Column(db.Text, default="")

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("plan_id", "data_set_id", name="uq_plan_dataset"),
    )

    data_set = db.relationship("TestDataSet", foreign_keys=[data_set_id])

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "data_set_id": self.data_set_id,
            "data_set_name": self.data_set.name if self.data_set else None,
            "data_set_status": self.data_set.status if self.data_set else None,
            "is_mandatory": self.is_mandatory,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<PlanDataSet {self.id}: plan#{self.plan_id} ↔ ds#{self.data_set_id}>"


# ═════════════════════════════════════════════════════════════════════════════
# CYCLE DATA SET  (Data Bridge)
# ═════════════════════════════════════════════════════════════════════════════

class CycleDataSet(db.Model):
    """Bridge: TestCycle ↔ TestDataSet (N:M).

    Tracks which data sets are active in a cycle and their
    readiness status.  Supports per-cycle data refresh tracking.
    """

    __tablename__ = "cycle_data_sets"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    cycle_id = db.Column(
        db.Integer, db.ForeignKey("test_cycles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    data_set_id = db.Column(
        db.Integer, db.ForeignKey("test_data_sets.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    data_status = db.Column(
        db.String(20), default="not_checked",
        comment="not_checked | ready | stale | refresh_needed",
    )
    data_refreshed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.Text, default="")

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("cycle_id", "data_set_id", name="uq_cycle_dataset"),
    )

    data_set = db.relationship("TestDataSet", foreign_keys=[data_set_id])

    def to_dict(self):
        return {
            "id": self.id,
            "cycle_id": self.cycle_id,
            "data_set_id": self.data_set_id,
            "data_set_name": self.data_set.name if self.data_set else None,
            "data_set_version": self.data_set.version if self.data_set else None,
            "data_status": self.data_status,
            "data_refreshed_at": self.data_refreshed_at.isoformat() if self.data_refreshed_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<CycleDataSet {self.id}: cycle#{self.cycle_id} ↔ ds#{self.data_set_id} [{self.data_status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# PLAN SCOPE  (Test Coverage)
# ═════════════════════════════════════════════════════════════════════════════

class PlanScope(db.Model):
    """Scope item within a test plan.

    Defines which L3 processes, scenarios, or requirements
    a plan covers.  Used for coverage reporting.
    """

    __tablename__ = "plan_scopes"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    plan_id = db.Column(
        db.Integer, db.ForeignKey("test_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    scope_type = db.Column(
        db.String(30), nullable=False,
        comment="l3_process | scenario | requirement",
    )
    scope_ref_id = db.Column(
        db.String(36), nullable=True,
        comment="Reference ID (explore_requirements.id, process ID, etc.)",
    )
    scope_label = db.Column(
        db.String(200), nullable=False,
        comment="Human-readable label, e.g. 'OTC-010 Sales Order Processing'",
    )
    priority = db.Column(
        db.String(20), default="medium",
        comment="low | medium | high | critical — scope item priority",
    )
    risk_level = db.Column(
        db.String(20), default="medium",
        comment="low | medium | high — risk classification for coverage weighting",
    )
    coverage_status = db.Column(
        db.String(20), default="not_covered",
        comment="not_covered | partial | covered — auto-computed by coverage service",
    )
    notes = db.Column(db.Text, default="")

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("plan_id", "scope_type", "scope_ref_id", name="uq_plan_scope"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "scope_type": self.scope_type,
            "scope_ref_id": self.scope_ref_id,
            "scope_label": self.scope_label,
            "priority": self.priority,
            "risk_level": self.risk_level,
            "coverage_status": self.coverage_status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<PlanScope {self.id}: [{self.scope_type}] {self.scope_label}>"


# ═════════════════════════════════════════════════════════════════════════════
# PLAN TEST CASE  (TC Pool)
# ═════════════════════════════════════════════════════════════════════════════

class PlanTestCase(db.Model):
    """Bridge: TestPlan ↔ TestCase (N:M) — the TC Pool.

    Tracks which test cases are assigned to a plan, how they
    were added, priority within the plan, tester assignment,
    and execution ordering.
    """

    __tablename__ = "plan_test_cases"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    plan_id = db.Column(
        db.Integer, db.ForeignKey("test_plans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    test_case_id = db.Column(
        db.Integer, db.ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    added_method = db.Column(
        db.String(30), default="manual",
        comment="manual | scope_suggest | suite_import | ai_suggest",
    )
    priority = db.Column(
        db.String(20), default="medium",
        comment="low | medium | high | critical — priority within this plan",
    )
    estimated_effort = db.Column(
        db.Integer, nullable=True,
        comment="Estimated execution effort in minutes",
    )
    planned_tester = db.Column(
        db.String(100), default="",
        comment="Planned tester name",
    )
    planned_tester_id = db.Column(
        db.Integer, db.ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True,
        comment="Planned tester FK → team_members",
    )
    execution_order = db.Column(
        db.Integer, default=0,
        comment="Execution sequence within the plan",
    )
    notes = db.Column(db.Text, default="")

    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint("plan_id", "test_case_id", name="uq_plan_testcase"),
    )

    test_case = db.relationship("TestCase", foreign_keys=[test_case_id])
    planned_member = db.relationship("TeamMember", foreign_keys=[planned_tester_id])

    def to_dict(self):
        tc = self.test_case
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "test_case_id": self.test_case_id,
            "test_case_code": tc.code if tc else None,
            "test_case_title": tc.title if tc else None,
            "test_case_layer": tc.test_layer if tc else None,
            "test_case_module": tc.module if tc else None,
            "test_case_status": tc.status if tc else None,
            "added_method": self.added_method,
            "priority": self.priority,
            "estimated_effort": self.estimated_effort,
            "planned_tester": self.planned_tester,
            "planned_tester_id": self.planned_tester_id,
            "planned_tester_name": self.planned_member.name if self.planned_tester_id and self.planned_member else None,
            "execution_order": self.execution_order,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<PlanTestCase {self.id}: plan#{self.plan_id} ↔ tc#{self.test_case_id}>"

