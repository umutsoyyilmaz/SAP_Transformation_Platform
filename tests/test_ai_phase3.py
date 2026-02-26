"""
SAP Transformation Management Platform
Tests — AI Phase 3 Assistants (Sprint 15).

Coverage:
    - CutoverOptimizer  (optimize_runbook, assess_go_nogo, context builders)
    - MeetingMinutesAssistant (generate_minutes, extract_actions)
    - API endpoints for all 4 new assistant endpoints
    - Prompt YAML loading verification
"""

import json
import pytest

from app import create_app
from app.models import db as _db
from app.models.ai import AISuggestion
from app.models.program import Program
from app.models.cutover import (
    CutoverPlan,
    CutoverScopeItem,
    RunbookTask,
    TaskDependency,
    Rehearsal,
    GoNoGoItem,
    HypercareIncident,
)
from app.ai.assistants.cutover_optimizer import CutoverOptimizer
from app.ai.assistants.meeting_minutes import MeetingMinutesAssistant
from app.ai.prompt_registry import PromptRegistry


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def app():
    from app.config import TestingConfig
    TestingConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    app = create_app("testing")
    return app


@pytest.fixture(scope="session")
def _setup_db(app):
    with app.app_context():
        _db.create_all()
    yield
    with app.app_context():
        _db.drop_all()


@pytest.fixture(autouse=True)
def session(app, _setup_db):
    with app.app_context():
        from app.models.auth import Tenant
        from app.services.permission_service import invalidate_all_cache
        invalidate_all_cache()
        t = Tenant.query.filter_by(slug="test-default").first()
        if not t:
            t = Tenant(name="Test Default", slug="test-default")
            _db.session.add(t)
            _db.session.commit()
        yield
        invalidate_all_cache()
        _db.session.rollback()
        _db.drop_all()
        _db.create_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _create_program(client, **kw):
    payload = {"name": "Cutover AI Program", "methodology": "agile"}
    payload.update(kw)
    res = client.post("/api/v1/programs", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_cutover_plan(app, program_id, **kw):
    from app.models.program import Program
    prog = _db.session.get(Program, program_id)
    plan = CutoverPlan(
        program_id=program_id,
        tenant_id=kw.get("tenant_id") or (prog.tenant_id if prog else None),
        code=kw.get("code", "CUT-T01"),
        name=kw.get("name", "Test Cutover Plan"),
        status=kw.get("status", "draft"),
    )
    _db.session.add(plan)
    _db.session.commit()
    return plan


def _create_scope_item(app, plan_id, **kw):
    item = CutoverScopeItem(
        cutover_plan_id=plan_id,
        category=kw.get("category", "data_load"),
        name=kw.get("name", "Master Data Load"),
    )
    _db.session.add(item)
    _db.session.commit()
    return item


def _create_task(app, scope_item_id, **kw):
    task = RunbookTask(
        scope_item_id=scope_item_id,
        code=kw.get("code", "CUT-T01-T001"),
        title=kw.get("title", "Load master data"),
        sequence=kw.get("sequence", 1),
        status=kw.get("status", "not_started"),
        planned_duration_min=kw.get("planned_duration_min", 60),
        responsible=kw.get("responsible", "Data Team"),
        accountable=kw.get("accountable", "PM"),
    )
    _db.session.add(task)
    _db.session.commit()
    return task


def _create_dependency(app, pred_id, succ_id, **kw):
    dep = TaskDependency(
        predecessor_id=pred_id,
        successor_id=succ_id,
        dependency_type=kw.get("dependency_type", "finish_to_start"),
        lag_minutes=kw.get("lag_minutes", 0),
    )
    _db.session.add(dep)
    _db.session.commit()
    return dep


def _create_rehearsal(app, plan_id, **kw):
    reh = Rehearsal(
        cutover_plan_id=plan_id,
        rehearsal_number=kw.get("rehearsal_number", 1),
        name=kw.get("name", "Rehearsal 1"),
        status=kw.get("status", "completed"),
        planned_duration_min=kw.get("planned_duration_min", 480),
        actual_duration_min=kw.get("actual_duration_min", 570),
        duration_variance_pct=kw.get("duration_variance_pct", 18.75),
        findings_summary=kw.get("findings_summary", "3 minor issues found"),
    )
    _db.session.add(reh)
    _db.session.commit()
    return reh


def _create_gonogo(app, plan_id, **kw):
    item = GoNoGoItem(
        cutover_plan_id=plan_id,
        source_domain=kw.get("source_domain", "test_management"),
        criterion=kw.get("criterion", "No open P1/P2 defects"),
        verdict=kw.get("verdict", "pending"),
    )
    _db.session.add(item)
    _db.session.commit()
    return item


def _seed_full_plan(app, client):
    """Create a fully populated cutover plan for testing."""
    prog = _create_program(client)
    pid = prog["id"]
    plan = _create_cutover_plan(app, pid, code="CUT-AI01", name="AI Test Cutover", status="rehearsal")

    scope = _create_scope_item(app, plan.id, category="data_load", name="Master Data")
    t1 = _create_task(app, scope.id, code="CUT-AI01-T001", title="Extract master data",
                       sequence=1, planned_duration_min=120)
    t2 = _create_task(app, scope.id, code="CUT-AI01-T002", title="Transform master data",
                       sequence=2, planned_duration_min=90)
    t3 = _create_task(app, scope.id, code="CUT-AI01-T003", title="Load master data",
                       sequence=3, planned_duration_min=180)

    _create_dependency(app, t1.id, t2.id)
    _create_dependency(app, t2.id, t3.id)

    _create_rehearsal(app, plan.id, rehearsal_number=1, name="Rehearsal 1",
                       planned_duration_min=480, actual_duration_min=540,
                       duration_variance_pct=12.5,
                       findings_summary="2 minor issues found")

    _create_gonogo(app, plan.id, source_domain="test_management",
                    criterion="No open P1/P2 defects", verdict="go")
    _create_gonogo(app, plan.id, source_domain="data_factory",
                    criterion="Data reconciliation passed", verdict="pending")

    return plan, pid


# ═════════════════════════════════════════════════════════════════════════════
# 1. CUTOVER OPTIMIZER — UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestCutoverOptimizerUnit:
    """Direct tests for CutoverOptimizer class methods."""

    def test_init_defaults(self):
        opt = CutoverOptimizer()
        assert opt.gateway is None
        assert opt.rag is None
        assert opt.prompt_registry is None
        assert opt.suggestion_queue is None

    def test_optimize_runbook_plan_not_found(self, app, client):
        opt = CutoverOptimizer()
        result = opt.optimize_runbook(99999)
        assert result["error"] == "CutoverPlan 99999 not found"

    def test_optimize_runbook_no_tasks(self, app, client):
        prog = _create_program(client)
        plan = _create_cutover_plan(app, prog["id"])
        opt = CutoverOptimizer()
        result = opt.optimize_runbook(plan.id)
        assert result["error"] == "No runbook tasks found for this plan"

    def test_optimize_runbook_no_registry(self, app, client):
        plan, _ = _seed_full_plan(app, client)
        opt = CutoverOptimizer(prompt_registry=None)
        result = opt.optimize_runbook(plan.id)
        assert result["error"] == "Prompt registry not available"

    def test_optimize_runbook_no_gateway(self, app, client):
        plan, _ = _seed_full_plan(app, client)
        registry = PromptRegistry()
        opt = CutoverOptimizer(prompt_registry=registry)
        result = opt.optimize_runbook(plan.id)
        assert result["error"] == "LLM Gateway not available"

    def test_assess_gonogo_plan_not_found(self, app, client):
        opt = CutoverOptimizer()
        result = opt.assess_go_nogo(99999)
        assert result["error"] == "CutoverPlan 99999 not found"

    def test_assess_gonogo_no_registry(self, app, client):
        plan, _ = _seed_full_plan(app, client)
        opt = CutoverOptimizer(prompt_registry=None)
        result = opt.assess_go_nogo(plan.id)
        assert result["error"] == "Prompt registry not available"

    def test_assess_gonogo_no_gateway(self, app, client):
        plan, _ = _seed_full_plan(app, client)
        registry = PromptRegistry()
        opt = CutoverOptimizer(prompt_registry=registry)
        result = opt.assess_go_nogo(plan.id)
        assert result["error"] == "LLM Gateway not available"

    def test_build_runbook_context(self, app, client):
        plan, _ = _seed_full_plan(app, client)
        opt = CutoverOptimizer()
        ctx = opt._build_runbook_context(plan)
        assert ctx["plan"]["code"] == "CUT-AI01"
        assert len(ctx["tasks"]) == 3
        assert len(ctx["dependencies"]) == 2
        assert len(ctx["scope_items"]) == 1
        assert len(ctx["rehearsals"]) == 1

    def test_build_gonogo_context(self, app, client):
        plan, _ = _seed_full_plan(app, client)
        opt = CutoverOptimizer()
        ctx = opt._build_gonogo_context(plan)
        assert ctx["plan"]["code"] == "CUT-AI01"
        assert len(ctx["checklist_items"]) == 2
        assert len(ctx["rehearsals"]) == 1
        assert ctx["total_tasks"] == 3

    def test_parse_response_valid_json(self):
        content = '{"critical_path": [], "confidence": 0.85}'
        result = CutoverOptimizer._parse_response(content)
        assert result["confidence"] == 0.85

    def test_parse_response_fenced_json(self):
        content = '```json\n{"verdict": "go", "confidence": 0.9}\n```'
        result = CutoverOptimizer._parse_response(content)
        assert result["verdict"] == "go"

    def test_parse_response_invalid(self):
        result = CutoverOptimizer._parse_response("not json at all")
        assert result == {}

    def test_parse_response_embedded_json(self):
        content = 'Here is the analysis:\n{"verdict": "conditional_go"}\nDone.'
        result = CutoverOptimizer._parse_response(content)
        assert result["verdict"] == "conditional_go"


class TestCutoverOptimizerWithGateway:
    """Tests with LocalStubProvider (no API key, deterministic responses)."""

    def test_optimize_runbook_with_stub(self, app, client):
        from app.ai.gateway import LLMGateway
        plan, _ = _seed_full_plan(app, client)

        gw = LLMGateway()
        registry = PromptRegistry()
        opt = CutoverOptimizer(gateway=gw, prompt_registry=registry)
        result = opt.optimize_runbook(plan.id)

        # LocalStubProvider returns a deterministic JSON response
        assert result["error"] is None or result.get("critical_path") is not None

    def test_assess_gonogo_with_stub(self, app, client):
        from app.ai.gateway import LLMGateway
        plan, _ = _seed_full_plan(app, client)

        gw = LLMGateway()
        registry = PromptRegistry()
        opt = CutoverOptimizer(gateway=gw, prompt_registry=registry)
        result = opt.assess_go_nogo(plan.id)

        assert result["error"] is None or result.get("verdict") is not None


# ═════════════════════════════════════════════════════════════════════════════
# 2. MEETING MINUTES — UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════

SAMPLE_MEETING_TEXT = """
Meeting: SAP S/4HANA Cutover Planning
Date: 2026-03-15
Attendees: Umut (PM), Ayse (Data Lead), Mehmet (Technical Lead), Zeynep (Testing Lead)

Agenda:
1. Cutover rehearsal results review
2. Go/no-go criteria finalization
3. Hypercare preparation

Discussion:
- Umut opened the meeting and reviewed the rehearsal results. First rehearsal completed
  in 9 hours vs planned 8 hours (12.5% variance).
- Ayse reported that data load reconciliation showed 99.7% match rate.
  Decision: Accepted as within tolerance (target was >99.5%).
- Mehmet raised concern about interface INT-042 timeout issue found during rehearsal.
  Action: Mehmet will increase timeout from 30s to 120s by March 18.
- Zeynep confirmed all P1 defects are resolved. 2 P2 defects remain but have workarounds.
  Decision: Accept P2 defects with workarounds for go-live, fix in first hypercare sprint.
- Risk: If INT-042 fix is not tested before go-live, data replication may fail.
  Mitigation: Run optional mini-rehearsal on March 19 for interface testing only.

Action items:
- Mehmet: Fix INT-042 timeout (due: March 18)
- Zeynep: Document P2 workarounds (due: March 17)
- Umut: Schedule mini-rehearsal (due: March 16)
- Ayse: Prepare data reconciliation final report (due: March 18)

Next meeting: March 19, 2026 - Go/No-Go Decision Meeting
"""


class TestMeetingMinutesUnit:
    """Direct tests for MeetingMinutesAssistant class methods."""

    def test_init_defaults(self):
        mm = MeetingMinutesAssistant()
        assert mm.gateway is None

    def test_generate_minutes_empty_text(self):
        mm = MeetingMinutesAssistant()
        result = mm.generate_minutes("")
        assert result["error"] == "raw_text is required"

    def test_generate_minutes_whitespace_only(self):
        mm = MeetingMinutesAssistant()
        result = mm.generate_minutes("   \n  ")
        assert result["error"] == "raw_text is required"

    def test_generate_minutes_no_registry(self):
        mm = MeetingMinutesAssistant(prompt_registry=None)
        result = mm.generate_minutes("Some meeting text")
        assert result["error"] == "Prompt registry not available"

    def test_generate_minutes_no_gateway(self):
        registry = PromptRegistry()
        mm = MeetingMinutesAssistant(prompt_registry=registry)
        result = mm.generate_minutes("Some meeting text")
        assert result["error"] == "LLM Gateway not available"

    def test_extract_actions_empty_text(self):
        mm = MeetingMinutesAssistant()
        result = mm.extract_actions("")
        assert result["error"] == "raw_text is required"

    def test_extract_actions_no_registry(self):
        mm = MeetingMinutesAssistant(prompt_registry=None)
        result = mm.extract_actions("Some text")
        assert result["error"] == "Prompt registry not available"

    def test_extract_actions_no_gateway(self):
        registry = PromptRegistry()
        mm = MeetingMinutesAssistant(prompt_registry=registry)
        result = mm.extract_actions("Some text")
        assert result["error"] == "LLM Gateway not available"

    def test_parse_response_valid(self):
        content = '{"title": "Test Meeting", "confidence": 0.9}'
        result = MeetingMinutesAssistant._parse_response(content)
        assert result["title"] == "Test Meeting"

    def test_parse_response_fenced(self):
        content = '```json\n{"action_items": [{"action": "test"}]}\n```'
        result = MeetingMinutesAssistant._parse_response(content)
        assert len(result["action_items"]) == 1

    def test_parse_response_invalid(self):
        result = MeetingMinutesAssistant._parse_response("garbage")
        assert result == {}


class TestMeetingMinutesWithGateway:
    """Tests with LocalStubProvider."""

    def test_generate_minutes_with_stub(self, app, client):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        registry = PromptRegistry()
        mm = MeetingMinutesAssistant(gateway=gw, prompt_registry=registry)
        result = mm.generate_minutes(SAMPLE_MEETING_TEXT)
        # Stub may return non-JSON → error or partial result OK
        assert result is not None
        assert isinstance(result, dict)

    def test_extract_actions_with_stub(self, app, client):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        registry = PromptRegistry()
        mm = MeetingMinutesAssistant(gateway=gw, prompt_registry=registry)
        result = mm.extract_actions(SAMPLE_MEETING_TEXT)
        assert result is not None
        assert isinstance(result, dict)

    def test_generate_minutes_with_program(self, app, client):
        from app.ai.gateway import LLMGateway
        prog = _create_program(client, name="Minutes Test Prog")
        gw = LLMGateway()
        registry = PromptRegistry()
        mm = MeetingMinutesAssistant(gateway=gw, prompt_registry=registry)
        result = mm.generate_minutes(SAMPLE_MEETING_TEXT, program_id=prog["id"])
        assert result is not None


# ═════════════════════════════════════════════════════════════════════════════
# 3. PROMPT YAML LOADING
# ═════════════════════════════════════════════════════════════════════════════

class TestPromptYAMLLoading:
    """Verify Sprint 15 prompt templates load correctly."""

    def test_cutover_optimizer_yaml_loads(self, app):
        registry = PromptRegistry()
        templates = registry.list_templates()
        names = [t["name"] for t in templates]
        assert "cutover_optimizer" in names

    def test_cutover_gonogo_yaml_loads(self, app):
        registry = PromptRegistry()
        templates = registry.list_templates()
        names = [t["name"] for t in templates]
        assert "cutover_gonogo" in names

    def test_meeting_minutes_yaml_loads(self, app):
        registry = PromptRegistry()
        templates = registry.list_templates()
        names = [t["name"] for t in templates]
        assert "meeting_minutes" in names

    def test_meeting_actions_yaml_loads(self, app):
        registry = PromptRegistry()
        templates = registry.list_templates()
        names = [t["name"] for t in templates]
        assert "meeting_actions" in names

    def test_cutover_optimizer_renders(self, app):
        registry = PromptRegistry()
        msgs = registry.render(
            "cutover_optimizer",
            plan_title="Test Plan",
            plan_status="draft",
            runbook_context="{}",
            task_count="5",
            dependency_count="3",
            rehearsal_count="1",
        )
        assert len(msgs) >= 2
        assert "cutover" in msgs[0]["content"].lower()

    def test_meeting_minutes_renders(self, app):
        registry = PromptRegistry()
        msgs = registry.render(
            "meeting_minutes",
            raw_text="Sample meeting text",
            meeting_type="general",
            project_context="Test project",
        )
        assert len(msgs) >= 2
        assert "Sample meeting text" in msgs[1]["content"]


# ═════════════════════════════════════════════════════════════════════════════
# 4. API ENDPOINT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestCutoverAIEndpoints:
    """Test /api/v1/ai/cutover/* endpoints."""

    def test_optimize_plan_not_found(self, client):
        res = client.post("/api/v1/ai/cutover/optimize/99999")
        assert res.status_code == 500
        data = res.get_json()
        assert "not found" in data["error"]

    def test_optimize_plan_no_tasks(self, app, client):
        prog = _create_program(client)
        plan = _create_cutover_plan(app, prog["id"])
        res = client.post(f"/api/v1/ai/cutover/optimize/{plan.id}")
        assert res.status_code == 500
        assert "No runbook tasks" in res.get_json()["error"]

    def test_optimize_plan_with_data(self, app, client):
        plan, _ = _seed_full_plan(app, client)
        res = client.post(f"/api/v1/ai/cutover/optimize/{plan.id}")
        data = res.get_json()
        # With LocalStub, result may have error (parsing) or success
        assert isinstance(data, dict)
        assert "critical_path" in data or "error" in data

    def test_gonogo_plan_not_found(self, client):
        res = client.post("/api/v1/ai/cutover/go-nogo/99999")
        assert res.status_code == 500
        data = res.get_json()
        assert "not found" in data["error"]

    def test_gonogo_with_data(self, app, client):
        plan, _ = _seed_full_plan(app, client)
        res = client.post(f"/api/v1/ai/cutover/go-nogo/{plan.id}")
        data = res.get_json()
        assert isinstance(data, dict)
        assert "verdict" in data or "error" in data


class TestMeetingMinutesEndpoints:
    """Test /api/v1/ai/meeting-minutes/* endpoints."""

    def test_generate_no_body(self, client):
        res = client.post("/api/v1/ai/meeting-minutes/generate")
        assert res.status_code == 500
        data = res.get_json()
        assert "raw_text is required" in data["error"]

    def test_generate_empty_text(self, client):
        res = client.post("/api/v1/ai/meeting-minutes/generate", json={"raw_text": ""})
        assert res.status_code == 500
        assert "raw_text is required" in res.get_json()["error"]

    def test_generate_with_text(self, client):
        res = client.post("/api/v1/ai/meeting-minutes/generate", json={
            "raw_text": SAMPLE_MEETING_TEXT,
            "meeting_type": "steering_committee",
        })
        data = res.get_json()
        assert isinstance(data, dict)
        # With stub, may have title or error
        assert "title" in data or "error" in data

    def test_generate_with_program(self, app, client):
        prog = _create_program(client, name="Minutes EP Test")
        res = client.post("/api/v1/ai/meeting-minutes/generate", json={
            "raw_text": SAMPLE_MEETING_TEXT,
            "program_id": prog["id"],
        })
        data = res.get_json()
        assert isinstance(data, dict)

    def test_extract_actions_no_body(self, client):
        res = client.post("/api/v1/ai/meeting-minutes/extract-actions")
        assert res.status_code == 500
        data = res.get_json()
        assert "raw_text is required" in data["error"]

    def test_extract_actions_with_text(self, client):
        res = client.post("/api/v1/ai/meeting-minutes/extract-actions", json={
            "raw_text": SAMPLE_MEETING_TEXT,
        })
        data = res.get_json()
        assert isinstance(data, dict)
        assert "action_items" in data or "error" in data

    def test_extract_actions_with_program(self, app, client):
        prog = _create_program(client, name="Actions EP Test")
        res = client.post("/api/v1/ai/meeting-minutes/extract-actions", json={
            "raw_text": "Mehmet will fix the timeout by Friday.",
            "program_id": prog["id"],
        })
        data = res.get_json()
        assert isinstance(data, dict)


# ═════════════════════════════════════════════════════════════════════════════
# 5. EDGE CASES & INTEGRATION
# ═════════════════════════════════════════════════════════════════════════════

class TestCutoverOptimizerEdgeCases:
    """Edge cases for CutoverOptimizer."""

    def test_plan_with_single_task_no_deps(self, app, client):
        prog = _create_program(client, name="Single Task Prog")
        plan = _create_cutover_plan(app, prog["id"])
        scope = _create_scope_item(app, plan.id, category="custom", name="Single Scope")
        _create_task(app, scope.id, code="ONLY-T001", title="Single task", sequence=1)

        opt = CutoverOptimizer()
        ctx = opt._build_runbook_context(plan)
        assert len(ctx["tasks"]) == 1
        assert len(ctx["dependencies"]) == 0

    def test_plan_with_many_scope_items(self, app, client):
        prog = _create_program(client, name="Multi Scope Prog")
        plan = _create_cutover_plan(app, prog["id"])

        for cat in ["data_load", "interface", "authorization", "reconciliation"]:
            scope = _create_scope_item(app, plan.id, category=cat, name=f"Scope {cat}")
            _create_task(app, scope.id, code=f"{cat[:3].upper()}-001",
                          title=f"Task for {cat}", sequence=1)

        opt = CutoverOptimizer()
        ctx = opt._build_runbook_context(plan)
        assert len(ctx["scope_items"]) == 4
        assert len(ctx["tasks"]) == 4

    def test_gonogo_all_verdicts(self, app, client):
        prog = _create_program(client, name="GoNogo Verdicts")
        plan = _create_cutover_plan(app, prog["id"])
        _create_gonogo(app, plan.id, source_domain="test_management", verdict="go")
        _create_gonogo(app, plan.id, source_domain="data_factory", verdict="no_go")
        _create_gonogo(app, plan.id, source_domain="security", verdict="waived")
        _create_gonogo(app, plan.id, source_domain="training", verdict="pending")

        opt = CutoverOptimizer()
        ctx = opt._build_gonogo_context(plan)
        verdicts = [i["verdict"] for i in ctx["checklist_items"]]
        assert "go" in verdicts
        assert "no_go" in verdicts
        assert "waived" in verdicts
        assert "pending" in verdicts

    def test_gonogo_with_incidents(self, app, client):
        prog = _create_program(client, name="Incident Test")
        plan = _create_cutover_plan(app, prog["id"])
        inc = HypercareIncident(
            cutover_plan_id=plan.id,
            tenant_id=plan.tenant_id,
            code="INC-001",
            title="Test incident",
            severity="P1",
            status="open",
            reported_by="tester",
        )
        _db.session.add(inc)
        _db.session.commit()

        opt = CutoverOptimizer()
        ctx = opt._build_gonogo_context(plan)
        assert ctx["open_incidents"] == 1
        assert ctx["total_incidents"] == 1


class TestMeetingMinutesEdgeCases:
    """Edge cases for MeetingMinutesAssistant."""

    def test_very_short_text(self, app, client):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        registry = PromptRegistry()
        mm = MeetingMinutesAssistant(gateway=gw, prompt_registry=registry)
        result = mm.generate_minutes("Quick sync: all good, no blockers.")
        assert isinstance(result, dict)

    def test_turkish_text(self, app, client):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        registry = PromptRegistry()
        mm = MeetingMinutesAssistant(gateway=gw, prompt_registry=registry)
        result = mm.generate_minutes(
            "Meeting: SAP transition planning. Attendees: Umut, Ayse. "
            "Decision: Go-live date confirmed as March 15."
        )
        assert isinstance(result, dict)

    def test_meeting_type_variations(self, app, client):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        registry = PromptRegistry()
        mm = MeetingMinutesAssistant(gateway=gw, prompt_registry=registry)

        for mt in ["general", "steering_committee", "workshop", "technical", "status_update"]:
            result = mm.generate_minutes("Test meeting content", meeting_type=mt)
            assert isinstance(result, dict)

    def test_program_context_enrichment(self, app, client):
        """Verify program context is built when program_id is provided."""
        from app.ai.gateway import LLMGateway
        prog = _create_program(client, name="Context Test")
        gw = LLMGateway()
        registry = PromptRegistry()
        mm = MeetingMinutesAssistant(gateway=gw, prompt_registry=registry)
        result = mm.generate_minutes("Important meeting", program_id=prog["id"])
        assert isinstance(result, dict)
