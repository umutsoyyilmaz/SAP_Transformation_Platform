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

DEFECT_SEVERITIES = {"P1", "P2", "P3", "P4"}

DEFECT_STATUSES = {
    "new", "open", "in_progress", "fixed", "retest", "closed", "rejected", "reopened",
}

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

    def to_dict(self, include_cycles=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
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
    program_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    requirement_id = db.Column(
        db.Integer, db.ForeignKey("requirements.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="Linked requirement for traceability",
    )
    backlog_item_id = db.Column(
        db.Integer, db.ForeignKey("backlog_items.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="Linked WRICEF backlog item",
    )
    config_item_id = db.Column(
        db.Integer, db.ForeignKey("config_items.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="Linked config item",
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

    def to_dict(self, include_steps=False):
        result = {
            "id": self.id,
            "program_id": self.program_id,
            "requirement_id": self.requirement_id,
            "backlog_item_id": self.backlog_item_id,
            "config_item_id": self.config_item_id,
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
            "status": self.status,
            "priority": self.priority,
            "is_regression": self.is_regression,
            "assigned_to": self.assigned_to,
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
    executed_by = db.Column(db.String(100), default="", comment="Tester name")
    executed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True, comment="Execution time in minutes")
    notes = db.Column(db.Text, default="", comment="Execution notes / evidence")
    evidence_url = db.Column(db.String(500), default="", comment="Screenshot / log URL")

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
            "cycle_id": self.cycle_id,
            "test_case_id": self.test_case_id,
            "result": self.result,
            "executed_by": self.executed_by,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "duration_minutes": self.duration_minutes,
            "notes": self.notes,
            "evidence_url": self.evidence_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

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
        db.String(10), default="P3",
        comment="P1 (blocker) | P2 (critical) | P3 (major) | P4 (minor/cosmetic)",
    )
    status = db.Column(
        db.String(30), default="new",
        comment="new | open | in_progress | fixed | retest | closed | rejected | reopened",
    )
    module = db.Column(db.String(50), default="", comment="SAP module")
    environment = db.Column(db.String(50), default="", comment="DEV | QAS | PRD")

    # ── Assignment & tracking
    reported_by = db.Column(db.String(100), default="")
    assigned_to = db.Column(db.String(100), default="")
    found_in_cycle = db.Column(db.String(100), default="", comment="Which test cycle found it")

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

    def to_dict(self, include_comments=False):
        d = {
            "id": self.id,
            "program_id": self.program_id,
            "test_case_id": self.test_case_id,
            "backlog_item_id": self.backlog_item_id,
            "config_item_id": self.config_item_id,
            "linked_requirement_id": self.linked_requirement_id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "steps_to_reproduce": self.steps_to_reproduce,
            "severity": self.severity,
            "status": self.status,
            "module": self.module,
            "environment": self.environment,
            "reported_by": self.reported_by,
            "assigned_to": self.assigned_to,
            "found_in_cycle": self.found_in_cycle,
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
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

    # ── Relationships
    step_results = db.relationship(
        "TestStepResult", backref="run", lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="TestStepResult.step_no",
    )

    @property
    def computed_duration(self):
        """Calculate duration from timestamps if not explicitly set."""
        if self.duration_minutes is not None:
            return self.duration_minutes
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None

    def to_dict(self, include_step_results=False):
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
            "step_result_count": self.step_results.count() if self.id else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_step_results:
            d["step_results"] = [sr.to_dict() for sr in self.step_results.all()]
        return d

    def __repr__(self):
        return f"<TestRun {self.id}: case#{self.test_case_id} [{self.run_type}] → {self.result}>"


# ═════════════════════════════════════════════════════════════════════════════
# TEST STEP RESULT  (TS-Sprint 2)
# ═════════════════════════════════════════════════════════════════════════════

class TestStepResult(db.Model):
    """
    Step-level result within a test run.

    Records pass/fail/blocked at individual step granularity, enabling
    precise failure pinpointing.
    """

    __tablename__ = "test_step_results"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(
        db.Integer, db.ForeignKey("test_runs.id", ondelete="CASCADE"),
        nullable=False, index=True,
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
            "run_id": self.run_id,
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
        return f"<TestStepResult {self.id}: run#{self.run_id} step#{self.step_no} → {self.result}>"


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
