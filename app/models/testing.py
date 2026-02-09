"""
SAP Transformation Management Platform
Testing domain models — Sprint 5 scope (Test Hub).

Models:
    - TestPlan:       top-level test planning container per program
    - TestCycle:      execution cycle within a plan (e.g. SIT Cycle 1, UAT Cycle 2)
    - TestCase:       individual test case in the catalog (linked to requirements)
    - TestExecution:  execution record of a test case within a cycle
    - Defect:         defect/bug raised during testing (linked to WRICEF/Config + test case)

Architecture ref:
    Test Plan ──1:N──▶ Test Cycle ──1:N──▶ Test Execution
    Test Catalog ──1:N──▶ Test Case
                           ├── linked_requirements[]
                           ├── test_layer (Unit/SIT/UAT/Regression/Perf)
                           ├── test_data_set
                           └──1:N──▶ Defect

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

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "requirement_id": self.requirement_id,
            "backlog_item_id": self.backlog_item_id,
            "config_item_id": self.config_item_id,
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

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "test_case_id": self.test_case_id,
            "backlog_item_id": self.backlog_item_id,
            "config_item_id": self.config_item_id,
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Defect {self.id}: [{self.severity}] {self.code or self.title[:30]}>"
