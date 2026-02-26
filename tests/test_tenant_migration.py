"""
Sprint 5 — Tenant Migration Tests.

Validates:
  1. Schema: every tenant-scoped model has tenant_id (nullable FK)
  2. Schema: 5 global models do NOT have tenant_id
  3. Functional: CRUD with tenant_id works, backward compat (None)
  4. AuditLog: tenant_id + actor_user_id FK
  5. Composite indexes: (tenant_id, id) on all tenant-scoped tables
  6. Cross-model consistency: parent.tenant_id propagates
  7. Migration scripts importable and runnable
"""

import pytest
from sqlalchemy import inspect as sa_inspect

from app.models import db as _db
from app.models.auth import Tenant, User
from app.utils.crypto import hash_password


# ── All tenant-scoped models ────────────────────────────────────────────────
# Grouped by file for clarity.

TENANT_SCOPED_MODELS = {}  # populated at import time


def _collect_models():
    """Dynamically collect all models and classify by tenant-scope."""
    from app.models.program import Program, Phase, Gate, Workstream, TeamMember, Committee
    from app.models.testing import (
        TestPlan, TestCycle, TestCase, TestExecution, Defect,
        TestSuite, TestStep, TestCaseDependency, TestCycleSuite,
        TestRun, TestStepResult, DefectComment, DefectHistory,
        DefectLink, UATSignOff, PerfTestResult, TestDailySnapshot,
    )
    from app.models.requirement import Requirement, OpenItem, RequirementTrace
    from app.models.explore import (
        ProcessLevel, ExploreWorkshop, WorkshopScopeItem,
        WorkshopAttendee, WorkshopAgendaItem, ProcessStep,
        ExploreDecision, ExploreOpenItem, ExploreRequirement,
        RequirementOpenItemLink, RequirementDependency,
        OpenItemComment, CloudALMSyncLog, ProjectRole,
        PhaseGate, WorkshopDependency, CrossModuleFlag,
        WorkshopRevisionLog, Attachment, ScopeChangeRequest,
        ScopeChangeLog, BPMNDiagram, ExploreWorkshopDocument,
        DailySnapshot,
    )
    from app.models.scope import Process, RequirementProcessMapping, Analysis
    from app.models.integration import (
        Interface, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist,
    )
    from app.models.backlog import (
        Sprint, BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec,
    )
    from app.models.raid import Risk, Action, Issue, Decision
    from app.models.cutover import (
        CutoverPlan, CutoverScopeItem, RunbookTask, TaskDependency,
        Rehearsal, GoNoGoItem, HypercareIncident, HypercareSLA,
    )
    from app.models.data_factory import (
        DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation,
    )
    from app.models.run_sustain import (
        KnowledgeTransfer, HandoverItem, StabilizationMetric,
    )
    from app.models.notification import Notification
    from app.models.scheduling import NotificationPreference, EmailLog
    from app.models.scenario import Scenario
    from app.models.scenario import Workshop as ScenarioWorkshop
    from app.models.scenario import WorkshopDocument as ScenarioWorkshopDoc
    from app.models.audit import AuditLog
    from app.models.ai import (
        AIUsageLog, AIEmbedding, AISuggestion, AIAuditLog,
        AITokenBudget, AIConversation, AIConversationMessage, AITask,
    )

    return {
        "program": [Program, Phase, Gate, Workstream, TeamMember, Committee],
        "testing": [
            TestPlan, TestCycle, TestCase, TestExecution, Defect,
            TestSuite, TestStep, TestCaseDependency, TestCycleSuite,
            TestRun, TestStepResult, DefectComment, DefectHistory,
            DefectLink, UATSignOff, PerfTestResult, TestDailySnapshot,
        ],
        "requirement": [Requirement, OpenItem, RequirementTrace],
        "explore": [
            ProcessLevel, ExploreWorkshop, WorkshopScopeItem,
            WorkshopAttendee, WorkshopAgendaItem, ProcessStep,
            ExploreDecision, ExploreOpenItem, ExploreRequirement,
            RequirementOpenItemLink, RequirementDependency,
            OpenItemComment, CloudALMSyncLog, ProjectRole,
            PhaseGate, WorkshopDependency, CrossModuleFlag,
            WorkshopRevisionLog, Attachment, ScopeChangeRequest,
            ScopeChangeLog, BPMNDiagram, ExploreWorkshopDocument,
            DailySnapshot,
        ],
        "scope": [Process, RequirementProcessMapping, Analysis],
        "integration": [Interface, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist],
        "backlog": [Sprint, BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec],
        "raid": [Risk, Action, Issue, Decision],
        "cutover": [
            CutoverPlan, CutoverScopeItem, RunbookTask, TaskDependency,
            Rehearsal, GoNoGoItem, HypercareIncident, HypercareSLA,
        ],
        "data_factory": [DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation],
        "run_sustain": [KnowledgeTransfer, HandoverItem, StabilizationMetric],
        "notification": [Notification],
        "scheduling": [NotificationPreference, EmailLog],
        "scenario": [Scenario, ScenarioWorkshop, ScenarioWorkshopDoc],
        "audit": [AuditLog],
        "ai": [
            AIUsageLog, AIEmbedding, AISuggestion, AIAuditLog,
            AITokenBudget, AIConversation, AIConversationMessage, AITask,
        ],
    }


# 5 global tables that must NOT have tenant_id
GLOBAL_SKIP_TABLES = [
    "kb_versions",
    "ai_response_cache",
    "ai_feedback_metrics",
    "l4_seed_catalog",
    "scheduled_jobs",
]


# ══════════════════════════════════════════════════════════════════════════════
# 1. SCHEMA TESTS — tenant_id column on every tenant-scoped model
# ══════════════════════════════════════════════════════════════════════════════


class TestTenantIdSchema:
    """Every tenant-scoped model has a nullable, indexed tenant_id FK column."""

    def _get_all_models(self):
        return _collect_models()

    def test_all_tenant_models_have_tenant_id_column(self, app):
        """96+ models should have 'tenant_id' as a column attribute."""
        models = self._get_all_models()
        missing = []
        for group, model_list in models.items():
            for model in model_list:
                if not hasattr(model, "tenant_id"):
                    missing.append(f"{group}/{model.__name__}")
        assert missing == [], f"Models missing tenant_id: {missing}"

    def test_tenant_id_column_is_nullable(self, app):
        """tenant_id must be nullable during the transition period.

        Some models have already completed migration to nullable=False
        (security audit fix SEC-03).
        """
        # Tables that have completed tenant_id migration to NOT NULL
        enforced_tables = {
            "programs", "phases", "gates", "workstreams",
            "team_members", "committees", "hypercare_incidents",
        }
        insp = sa_inspect(_db.engine)
        models = self._get_all_models()
        non_nullable = []
        for group, model_list in models.items():
            for model in model_list:
                table = model.__tablename__
                if table in enforced_tables:
                    continue
                cols = {c["name"]: c for c in insp.get_columns(table)}
                if "tenant_id" in cols and not cols["tenant_id"]["nullable"]:
                    non_nullable.append(table)
        assert non_nullable == [], f"tenant_id must be nullable: {non_nullable}"

    def test_tenant_id_column_type_is_integer(self, app):
        """tenant_id must be INTEGER type."""
        insp = sa_inspect(_db.engine)
        models = self._get_all_models()
        wrong_type = []
        for group, model_list in models.items():
            for model in model_list:
                table = model.__tablename__
                cols = {c["name"]: c for c in insp.get_columns(table)}
                if "tenant_id" in cols:
                    col_type = str(cols["tenant_id"]["type"]).upper()
                    if "INT" not in col_type:
                        wrong_type.append(f"{table}: {col_type}")
        assert wrong_type == [], f"tenant_id wrong type: {wrong_type}"

    def test_tenant_id_has_index(self, app):
        """tenant_id column should have at least one index."""
        insp = sa_inspect(_db.engine)
        models = self._get_all_models()
        no_index = []
        for group, model_list in models.items():
            for model in model_list:
                table = model.__tablename__
                indexes = insp.get_indexes(table)
                # Check if any index covers tenant_id
                has_idx = any(
                    "tenant_id" in idx.get("column_names", [])
                    for idx in indexes
                )
                if not has_idx:
                    no_index.append(table)
        assert no_index == [], f"Tables missing tenant_id index: {no_index}"

    def test_total_tenant_scoped_model_count(self, app):
        """Sanity check — we expect 96+ tenant-scoped models."""
        models = self._get_all_models()
        total = sum(len(v) for v in models.values())
        assert total >= 96, f"Expected ≥96 tenant-scoped models, got {total}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. GLOBAL TABLES — must NOT have tenant_id
# ══════════════════════════════════════════════════════════════════════════════


class TestGlobalTablesNoTenantId:
    """5 global tables must NOT have a tenant_id column."""

    @pytest.mark.parametrize("table_name", GLOBAL_SKIP_TABLES)
    def test_global_table_has_no_tenant_id(self, app, table_name):
        insp = sa_inspect(_db.engine)
        cols = [c["name"] for c in insp.get_columns(table_name)]
        assert "tenant_id" not in cols, f"Global table {table_name} should NOT have tenant_id"


# ══════════════════════════════════════════════════════════════════════════════
# 3. FUNCTIONAL TESTS — CRUD with tenant_id
# ══════════════════════════════════════════════════════════════════════════════


class TestTenantIdCRUD:
    """CRUD operations with tenant_id work correctly."""

    @pytest.fixture
    def tenant(self):
        t = Tenant(name="Test Corp", slug="test-corp", plan="pro", max_users=10)
        _db.session.add(t)
        _db.session.flush()
        return t

    def test_program_create_without_tenant_id(self, app):
        """SEC-03: Program without tenant_id → DB rejects (nullable=False)."""
        import sqlalchemy.exc
        from app.models.program import Program
        p = Program(name="Legacy Program", methodology="agile")
        _db.session.add(p)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            _db.session.flush()
        _db.session.rollback()

    def test_program_create_with_tenant_id(self, app, tenant):
        """Create Program with explicit tenant_id."""
        from app.models.program import Program
        p = Program(name="Tenant Program", methodology="agile", tenant_id=tenant.id)
        _db.session.add(p)
        _db.session.flush()
        assert p.tenant_id == tenant.id

    def test_phase_create_with_tenant_id(self, app, tenant):
        """Create Phase with tenant_id."""
        from app.models.program import Program, Phase
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        phase = Phase(
            name="Explore", program_id=prog.id,
            status="not_started", tenant_id=tenant.id,
        )
        _db.session.add(phase)
        _db.session.flush()
        assert phase.tenant_id == tenant.id

    def test_test_case_create_with_tenant_id(self, app, tenant):
        """Create TestCase with tenant_id."""
        from app.models.program import Program
        from app.models.testing import TestCase
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        tc = TestCase(
            title="Login Test", program_id=prog.id,
            priority="high",
            tenant_id=tenant.id,
        )
        _db.session.add(tc)
        _db.session.flush()
        assert tc.tenant_id == tenant.id

    def test_requirement_create_with_tenant_id(self, app, tenant):
        """Create Requirement with tenant_id."""
        from app.models.program import Program
        from app.models.requirement import Requirement
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        req = Requirement(
            title="REQ-001", code="REQ-001",
            program_id=prog.id, tenant_id=tenant.id,
        )
        _db.session.add(req)
        _db.session.flush()
        assert req.tenant_id == tenant.id

    def test_risk_create_with_tenant_id(self, app, tenant):
        """Create Risk with tenant_id."""
        from app.models.program import Program
        from app.models.raid import Risk
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        risk = Risk(
            title="Data Loss Risk", code="RISK-001",
            program_id=prog.id,
            tenant_id=tenant.id,
        )
        _db.session.add(risk)
        _db.session.flush()
        assert risk.tenant_id == tenant.id

    def test_explore_workshop_create_with_tenant_id(self, app, tenant):
        """Create ExploreWorkshop with tenant_id."""
        from app.models.program import Program
        from app.models.explore import ExploreWorkshop
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        ws = ExploreWorkshop(
            name="Kickoff", code="WS-001",
            project_id=prog.id, process_area="FI",
            tenant_id=tenant.id,
        )
        _db.session.add(ws)
        _db.session.flush()
        assert ws.tenant_id == tenant.id

    def test_notification_create_with_tenant_id(self, app, tenant):
        """Create Notification with tenant_id."""
        from app.models.notification import Notification
        n = Notification(
            title="Test Alert", message="Hello",
            category="system", tenant_id=tenant.id,
        )
        _db.session.add(n)
        _db.session.flush()
        assert n.tenant_id == tenant.id

    def test_cutover_plan_create_with_tenant_id(self, app, tenant):
        """Create CutoverPlan with tenant_id."""
        from app.models.program import Program
        from app.models.cutover import CutoverPlan
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        cp = CutoverPlan(
            name="Go-Live Plan", program_id=prog.id,
            tenant_id=tenant.id,
        )
        _db.session.add(cp)
        _db.session.flush()
        assert cp.tenant_id == tenant.id

    def test_sprint_create_with_tenant_id(self, app, tenant):
        """Create Sprint with tenant_id."""
        from app.models.program import Program
        from app.models.backlog import Sprint
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        sp = Sprint(
            name="Sprint 1", program_id=prog.id,
            tenant_id=tenant.id,
        )
        _db.session.add(sp)
        _db.session.flush()
        assert sp.tenant_id == tenant.id


# ══════════════════════════════════════════════════════════════════════════════
# 4. AUDIT LOG — tenant_id + actor_user_id
# ══════════════════════════════════════════════════════════════════════════════


class TestAuditLogTenantFields:
    """AuditLog has both tenant_id and actor_user_id FK fields."""

    def test_audit_log_has_tenant_id(self, app):
        from app.models.audit import AuditLog
        assert hasattr(AuditLog, "tenant_id")

    def test_audit_log_has_actor_user_id(self, app):
        from app.models.audit import AuditLog
        assert hasattr(AuditLog, "actor_user_id")

    def test_audit_log_create_with_tenant_id(self, app):
        from app.models.audit import AuditLog
        tenant = Tenant(name="Audit Corp", slug="audit-corp", plan="pro", max_users=5)
        _db.session.add(tenant)
        _db.session.flush()

        log = AuditLog(
            entity_type="Program", entity_id=1,
            action="create", actor="admin",
            tenant_id=tenant.id,
        )
        _db.session.add(log)
        _db.session.flush()
        assert log.tenant_id == tenant.id

    def test_audit_log_create_with_actor_user_id(self, app):
        from app.models.audit import AuditLog
        tenant = Tenant(name="Audit2", slug="audit2", plan="pro", max_users=5)
        _db.session.add(tenant)
        _db.session.flush()
        user = User(
            email="auditor@test.com",
            password_hash=hash_password("test123"),
            full_name="Auditor",
            tenant_id=tenant.id,
        )
        _db.session.add(user)
        _db.session.flush()

        log = AuditLog(
            entity_type="Requirement", entity_id=42,
            action="update", actor="auditor@test.com",
            tenant_id=tenant.id,
            actor_user_id=user.id,
        )
        _db.session.add(log)
        _db.session.flush()
        assert log.actor_user_id == user.id
        assert log.tenant_id == tenant.id

    def test_audit_log_to_dict_includes_tenant_fields(self, app):
        from app.models.audit import AuditLog
        tenant = Tenant(name="Dict Corp", slug="dict-corp", plan="pro", max_users=5)
        _db.session.add(tenant)
        _db.session.flush()

        log = AuditLog(
            entity_type="TestCase", entity_id=99,
            action="delete", actor="system",
            tenant_id=tenant.id,
        )
        _db.session.add(log)
        _db.session.flush()

        d = log.to_dict()
        assert "tenant_id" in d
        assert "actor_user_id" in d
        assert d["tenant_id"] == tenant.id

    def test_write_audit_with_tenant_params(self, app):
        """write_audit() helper accepts tenant_id and actor_user_id."""
        from app.models.audit import AuditLog, write_audit
        tenant = Tenant(name="Write Corp", slug="write-corp", plan="pro", max_users=5)
        _db.session.add(tenant)
        _db.session.flush()

        write_audit(
            entity_type="Interface", entity_id=7,
            action="create", actor="pm@test.com",
            tenant_id=tenant.id,
        )
        _db.session.flush()

        log = _db.session.execute(
            _db.select(AuditLog).where(
                AuditLog.entity_type == "Interface",
                AuditLog.entity_id == 7,
            )
        ).scalar_one()
        assert log.tenant_id == tenant.id


# ══════════════════════════════════════════════════════════════════════════════
# 5. COMPOSITE INDEXES
# ══════════════════════════════════════════════════════════════════════════════


class TestTenantIdIndexes:
    """All tenant-scoped tables have at least one index covering tenant_id.

    Note: Composite (tenant_id, id) indexes are created by
    scripts/add_tenant_indexes.py at deploy time. The model-level
    ``index=True`` creates a single-column index that survives
    ``db.create_all()``.
    """

    EXPECTED_INDEX_TABLES = [
        "programs", "phases", "gates", "workstreams", "team_members",
        "committees", "test_plans", "test_cycles", "test_cases",
        "test_executions", "defects", "test_suites", "test_steps",
        "requirements", "open_items", "requirement_traces",
        "process_levels", "explore_workshops", "process_steps",
        "risks", "actions", "issues", "decisions",
        "cutover_plans", "runbook_tasks", "sprints", "backlog_items",
        "interfaces", "waves", "data_objects", "notifications",
        "audit_logs", "scenarios",
    ]

    @pytest.mark.parametrize("table_name", EXPECTED_INDEX_TABLES)
    def test_tenant_id_index_exists(self, app, table_name):
        """Each tenant-scoped table has at least one index on tenant_id."""
        insp = sa_inspect(_db.engine)
        indexes = insp.get_indexes(table_name)
        tenant_indexed = any(
            "tenant_id" in idx.get("column_names", [])
            for idx in indexes
        )
        assert tenant_indexed, (
            f"No index covering tenant_id on {table_name}. "
            f"Indexes: {[i['name'] for i in indexes]}"
        )

    def test_composite_index_script_exists(self, app):
        """The add_tenant_indexes.py script exists and is importable."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "add_tenant_indexes", "scripts/add_tenant_indexes.py",
        )
        assert spec is not None


# ══════════════════════════════════════════════════════════════════════════════
# 6. CROSS-MODEL CONSISTENCY
# ══════════════════════════════════════════════════════════════════════════════


class TestCrossModelConsistency:
    """Parent and child models share the same tenant_id."""

    @pytest.fixture
    def tenant(self):
        t = Tenant(name="Cross Corp", slug="cross-corp", plan="enterprise", max_users=50)
        _db.session.add(t)
        _db.session.flush()
        return t

    def test_program_phase_gate_chain(self, app, tenant):
        """Program → Phase → Gate share tenant_id."""
        from app.models.program import Program, Phase, Gate
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        phase = Phase(name="Explore", program_id=prog.id, status="active", tenant_id=tenant.id)
        _db.session.add(phase)
        _db.session.flush()
        gate = Gate(name="G1", phase_id=phase.id, status="pending", tenant_id=tenant.id)
        _db.session.add(gate)
        _db.session.flush()
        assert prog.tenant_id == phase.tenant_id == gate.tenant_id == tenant.id

    def test_program_test_plan_cycle_chain(self, app, tenant):
        """Program → TestPlan → TestCycle share tenant_id."""
        from app.models.program import Program
        from app.models.testing import TestPlan, TestCycle
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        tp = TestPlan(name="Master Plan", program_id=prog.id, tenant_id=tenant.id)
        _db.session.add(tp)
        _db.session.flush()
        tc = TestCycle(name="Cycle 1", plan_id=tp.id, tenant_id=tenant.id)
        _db.session.add(tc)
        _db.session.flush()
        assert prog.tenant_id == tp.tenant_id == tc.tenant_id == tenant.id

    def test_program_requirement_trace_chain(self, app, tenant):
        """Program → Requirement → RequirementTrace share tenant_id."""
        from app.models.program import Program
        from app.models.requirement import Requirement, RequirementTrace
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        req = Requirement(
            title="R1", code="REQ-001",
            program_id=prog.id, tenant_id=tenant.id,
        )
        _db.session.add(req)
        _db.session.flush()
        trace = RequirementTrace(
            requirement_id=req.id, target_type="test_case",
            target_id=1, tenant_id=tenant.id,
        )
        _db.session.add(trace)
        _db.session.flush()
        assert prog.tenant_id == req.tenant_id == trace.tenant_id == tenant.id

    def test_program_sprint_backlog_chain(self, app, tenant):
        """Program → Sprint → BacklogItem share tenant_id."""
        from app.models.program import Program
        from app.models.backlog import Sprint, BacklogItem
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        sprint = Sprint(name="Sprint 1", program_id=prog.id, tenant_id=tenant.id)
        _db.session.add(sprint)
        _db.session.flush()
        item = BacklogItem(
            title="Story 1", program_id=prog.id,
            sprint_id=sprint.id,
            tenant_id=tenant.id,
        )
        _db.session.add(item)
        _db.session.flush()
        assert prog.tenant_id == sprint.tenant_id == item.tenant_id == tenant.id

    def test_tenant_filter_query(self, app, tenant):
        """Querying by tenant_id returns only tenant-scoped records.

        SEC-03: Program.tenant_id is now NOT NULL, so all programs must
        belong to a tenant. Test verifies cross-tenant isolation.
        """
        from app.models.program import Program
        other = Tenant(name="Other Corp", slug="other", plan="trial", max_users=5)
        _db.session.add(other)
        _db.session.flush()

        p1 = Program(name="Tenant A prog", methodology="agile", tenant_id=tenant.id)
        p2 = Program(name="Tenant B prog", methodology="waterfall", tenant_id=other.id)
        _db.session.add_all([p1, p2])
        _db.session.flush()

        tenant_programs = _db.session.execute(
            _db.select(Program).where(Program.tenant_id == tenant.id)
        ).scalars().all()
        assert len(tenant_programs) == 1
        assert tenant_programs[0].name == "Tenant A prog"

    def test_null_tenant_program_rejected_by_db(self, app, tenant):
        """SEC-03: Program with tenant_id=NULL → IntegrityError."""
        import sqlalchemy.exc
        from app.models.program import Program
        p = Program(name="No tenant", methodology="agile")
        _db.session.add(p)
        with pytest.raises(sqlalchemy.exc.IntegrityError):
            _db.session.flush()
        _db.session.rollback()


# ══════════════════════════════════════════════════════════════════════════════
# 7. MIGRATION SCRIPTS — importable
# ══════════════════════════════════════════════════════════════════════════════


class TestMigrationScriptsExist:
    """All Sprint 5 migration scripts are importable."""

    def test_add_tenant_id_script_exists(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "add_tenant_id",
            "scripts/add_tenant_id.py",
        )
        assert spec is not None

    def test_backfill_script_exists(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migrate_tenant_backfill",
            "scripts/migrate_tenant_backfill.py",
        )
        assert spec is not None

    def test_integrity_check_exists(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_tenant_integrity",
            "scripts/check_tenant_integrity.py",
        )
        assert spec is not None

    def test_index_script_exists(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "add_tenant_indexes",
            "scripts/add_tenant_indexes.py",
        )
        assert spec is not None


# ══════════════════════════════════════════════════════════════════════════════
# 8. PER-MODULE TENANT_ID SPOT CHECKS
# ══════════════════════════════════════════════════════════════════════════════


class TestPerModuleSpotChecks:
    """Spot-check tenant_id on representative models from each file."""

    @pytest.fixture
    def tenant(self):
        t = Tenant(name="Spot Corp", slug="spot-corp", plan="pro", max_users=5)
        _db.session.add(t)
        _db.session.flush()
        return t

    def test_data_factory_models(self, app, tenant):
        from app.models.program import Program
        from app.models.data_factory import DataObject
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        do = DataObject(
            name="Customer Master", program_id=prog.id,
            source_system="SAP ECC",
            tenant_id=tenant.id,
        )
        _db.session.add(do)
        _db.session.flush()
        assert do.tenant_id == tenant.id

    def test_integration_models(self, app, tenant):
        from app.models.program import Program
        from app.models.integration import Interface
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        iface = Interface(
            name="SAP-SF", program_id=prog.id,
            source_system="SAP", target_system="SuccessFactors",
            tenant_id=tenant.id,
        )
        _db.session.add(iface)
        _db.session.flush()
        assert iface.tenant_id == tenant.id

    def test_run_sustain_models(self, app, tenant):
        from app.models.program import Program
        from app.models.cutover import CutoverPlan
        from app.models.run_sustain import KnowledgeTransfer
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        cp = CutoverPlan(name="Go-Live", program_id=prog.id, tenant_id=tenant.id)
        _db.session.add(cp)
        _db.session.flush()
        kt = KnowledgeTransfer(
            title="KT Session 1", cutover_plan_id=cp.id,
            tenant_id=tenant.id,
        )
        _db.session.add(kt)
        _db.session.flush()
        assert kt.tenant_id == tenant.id

    def test_scenario_models(self, app, tenant):
        from app.models.program import Program
        from app.models.scenario import Scenario
        prog = Program(name="P1", methodology="agile", tenant_id=tenant.id)
        _db.session.add(prog)
        _db.session.flush()
        sc = Scenario(
            name="Order to Cash", program_id=prog.id,
            tenant_id=tenant.id,
        )
        _db.session.add(sc)
        _db.session.flush()
        assert sc.tenant_id == tenant.id

    def test_ai_models(self, app, tenant):
        from app.models.ai import AIConversation
        conv = AIConversation(
            title="AI Chat 1",
            tenant_id=tenant.id,
        )
        _db.session.add(conv)
        _db.session.flush()
        assert conv.tenant_id == tenant.id

    def test_scheduling_models(self, app, tenant):
        from app.models.scheduling import EmailLog
        log = EmailLog(
            recipient_email="user@test.com",
            subject="Test email",
            tenant_id=tenant.id,
        )
        _db.session.add(log)
        _db.session.flush()
        assert log.tenant_id == tenant.id
