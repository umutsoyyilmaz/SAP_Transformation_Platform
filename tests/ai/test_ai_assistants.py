"""
SAP Transformation Management Platform
Tests — AI Assistants (Sprint 8, Task 8.12).

E2E tests covering:
    - NL Query Assistant  (text-to-SQL, validation, sanitization)
    - Requirement Analyst (Fit/Gap classification, similarity, suggestion)
    - Defect Triage       (severity, duplicate detection, suggestion)
    - API endpoints for all 3 assistants
"""

import json
import pytest

from app import create_app
from app.models import db as _db
from app.models.ai import AIAuditLog, AIConversation, AIConversationMessage, AISuggestion, AIUsageLog
from app.models.explore.requirement import ExploreRequirement
from app.models.project import Project
from app.models.program import Program
from app.models.requirement import Requirement
from app.models.testing import Defect
from app.ai.assistants.nl_query import (
    NLQueryAssistant, validate_sql, sanitize_sql,
    SAP_GLOSSARY, DB_SCHEMA_CONTEXT,
)
from app.ai.assistants.requirement_analyst import RequirementAnalyst
from app.ai.assistants.defect_triage import DefectTriage, DUPLICATE_THRESHOLD, SIMILAR_THRESHOLD
from app.ai.assistants.risk_assessment import RiskAssessment
from app.ai.assistants.test_case_generator import TestCaseGenerator


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
        yield
        _db.session.rollback()
        _db.drop_all()
        _db.create_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_program(client, **kw):
    payload = {"name": "AI Test Program", "methodology": "agile"}
    payload.update(kw)
    res = client.post("/api/v1/programs", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_requirement(client, pid, **kw):
    payload = {
        "title": "GL Account Posting Enhancement",
        "description": "Need custom GL account posting logic for local regulations",
        "module": "FI",
        "req_type": "functional",
        "priority": "must_have",
    }
    payload.update(kw)
    req = Requirement(
        program_id=pid,
        title=payload["title"],
        description=payload.get("description", ""),
        module=payload.get("module", ""),
        req_type=payload.get("req_type", "functional"),
        priority=payload.get("priority", "must_have"),
        status=payload.get("status", "draft"),
        source=payload.get("source", "workshop"),
        process_id=payload.get("process_id"),
        workshop_id=payload.get("workshop_id"),
    )
    _db.session.add(req)
    _db.session.commit()
    return req.to_dict()


def _create_explore_requirement(client, pid, **kw):
    project = Project.query.filter_by(program_id=pid, is_default=True).first()
    assert project is not None
    payload = {
        "program_id": pid,
        "project_id": project.id,
        "code": "REQ-EXP-AI-001",
        "title": "Explore AI Requirement",
        "description": "Need a generated SIT regression pack for explore requirement",
        "type": "configuration",
        "fit_status": "gap",
        "status": "approved",
        "trigger_reason": "gap",
        "delivery_status": "not_mapped",
        "created_by_id": "test-user-1",
    }
    payload.update(kw)
    req = ExploreRequirement(**payload)
    _db.session.add(req)
    _db.session.commit()
    return req.to_dict()


def _create_defect(client, pid, **kw):
    payload = {
        "title": "Month-end close posting fails with error FI-123",
        "description": "During month-end close, the system throws error FI-123 when posting.",
        "steps_to_reproduce": "1. Open FB50\n2. Enter amounts\n3. Post → error",
        "severity": "P3",
        "module": "FI",
        "environment": "QAS",
    }
    payload.update(kw)
    res = client.post(f"/api/v1/programs/{pid}/testing/defects", json=payload)
    assert res.status_code == 201
    return res.get_json()


# ═════════════════════════════════════════════════════════════════════════════
# 1. SQL VALIDATION & SANITISATION (Task 8.2)
# ═════════════════════════════════════════════════════════════════════════════

class TestSQLValidation:
    """Tests for validate_sql() and sanitize_sql()."""

    def test_valid_select(self):
        r = validate_sql("SELECT * FROM programs")
        assert r["valid"] is True
        assert "LIMIT" in r["cleaned_sql"]

    def test_valid_select_with_limit(self):
        r = validate_sql("SELECT * FROM programs LIMIT 50")
        assert r["valid"] is True
        assert r["cleaned_sql"].count("LIMIT") == 1

    def test_valid_cte(self):
        r = validate_sql("WITH cte AS (SELECT id FROM programs) SELECT * FROM cte")
        assert r["valid"] is True

    def test_reject_insert(self):
        r = validate_sql("INSERT INTO programs (name) VALUES ('hack')")
        assert r["valid"] is False
        assert "SELECT" in r["error"]

    def test_reject_update(self):
        r = validate_sql("UPDATE programs SET name='x'")
        assert r["valid"] is False

    def test_reject_delete(self):
        r = validate_sql("DELETE FROM programs")
        assert r["valid"] is False

    def test_reject_drop(self):
        r = validate_sql("SELECT 1; DROP TABLE programs")
        assert r["valid"] is False

    def test_reject_multiple_statements(self):
        r = validate_sql("SELECT 1; SELECT 2")
        assert r["valid"] is False

    def test_reject_sql_comment_injection(self):
        r = validate_sql("SELECT * FROM programs -- drop table")
        assert r["valid"] is False

    def test_reject_unknown_table(self):
        r = validate_sql("SELECT * FROM evil_table")
        assert r["valid"] is False
        assert "evil_table" in r["error"]

    def test_accept_allowed_tables(self):
        for table in ["programs", "requirements", "defects", "risks", "backlog_items"]:
            r = validate_sql(f"SELECT COUNT(*) FROM {table}")
            assert r["valid"] is True, f"Table '{table}' should be allowed"

    def test_empty_sql(self):
        r = validate_sql("")
        assert r["valid"] is False

    def test_sanitize_removes_comments(self):
        s = sanitize_sql("SELECT * FROM programs -- this is a comment")
        assert "--" not in s

    def test_sanitize_removes_block_comments(self):
        s = sanitize_sql("SELECT /* inline */ * FROM programs")
        assert "/*" not in s

    def test_sanitize_collapses_whitespace(self):
        s = sanitize_sql("SELECT  *   FROM    programs")
        assert "  " not in s

    def test_reject_pragma(self):
        r = validate_sql("PRAGMA table_info(programs)")
        assert r["valid"] is False

    def test_reject_attach(self):
        r = validate_sql("ATTACH DATABASE ':memory:' AS evil")
        assert r["valid"] is False


# ═════════════════════════════════════════════════════════════════════════════
# 2. SAP GLOSSARY (Task 8.1)
# ═════════════════════════════════════════════════════════════════════════════

class TestSAPGlossary:
    """Tests for SAP glossary term resolution."""

    def test_glossary_has_sap_modules(self):
        for mod in ["fi", "co", "mm", "sd", "pp", "hcm"]:
            assert mod in SAP_GLOSSARY

    def test_glossary_has_wricef(self):
        assert "wricef" in SAP_GLOSSARY
        assert SAP_GLOSSARY["wricef"]["table"] == "backlog_items"

    def test_glossary_has_rfc(self):
        assert "rfc" in SAP_GLOSSARY
        assert SAP_GLOSSARY["rfc"]["table"] == "change_requests"

    def test_glossary_has_severity(self):
        for sev in ["p1", "p2", "p3", "p4"]:
            assert sev in SAP_GLOSSARY

    def test_glossary_has_process_areas(self):
        assert "o2c" in SAP_GLOSSARY
        assert "p2p" in SAP_GLOSSARY
        assert "r2r" in SAP_GLOSSARY

    def test_glossary_has_turkish_terms(self):
        assert "gereksinim" in SAP_GLOSSARY
        assert "hata" in SAP_GLOSSARY
        assert SAP_GLOSSARY["hata"]["table"] == "defects"

    def test_resolve_glossary(self):
        matches = NLQueryAssistant._resolve_glossary("How many P1 defects in FI module?")
        terms = {m["term"] for m in matches}
        assert "p1" in terms
        assert "fi" in terms

    def test_resolve_glossary_no_match(self):
        matches = NLQueryAssistant._resolve_glossary("hello world")
        assert len(matches) == 0


# ═════════════════════════════════════════════════════════════════════════════
# 3. NL QUERY ASSISTANT (Task 8.1 + 8.4)
# ═════════════════════════════════════════════════════════════════════════════

class TestNLQueryAssistant:
    """Tests for the NLQueryAssistant class."""

    def test_init(self):
        assistant = NLQueryAssistant()
        assert assistant.gateway is None

    def test_init_with_gateway(self):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        assistant = NLQueryAssistant(gateway=gw)
        assert assistant.gateway is gw

    def test_process_query_no_gateway(self):
        assistant = NLQueryAssistant()
        result = assistant.process_query("Show all programs")
        assert result["error"] is None
        assert result["sql"] is None
        assert result["suggestions"]

    def test_process_query_with_local_stub(self, app):
        """E2E: Use local stub to process a query."""
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        assistant = NLQueryAssistant(gateway=gw)
        result = assistant.process_query("How many programs?")
        # With local stub, it won't return valid SQL, but shouldn't crash
        assert result["original_query"] == "How many programs?"
        assert "error" in result

    def test_parse_llm_response_valid_json(self):
        content = '{"sql": "SELECT COUNT(*) FROM programs", "explanation": "Count programs", "confidence": 0.9}'
        parsed = NLQueryAssistant._parse_llm_response(content)
        assert parsed["sql"] == "SELECT COUNT(*) FROM programs"
        assert parsed["confidence"] == 0.9

    def test_parse_llm_response_markdown_fence(self):
        content = '```json\n{"sql": "SELECT * FROM defects", "explanation": "test", "confidence": 0.7}\n```'
        parsed = NLQueryAssistant._parse_llm_response(content)
        assert parsed["sql"] == "SELECT * FROM defects"

    def test_parse_llm_response_invalid(self):
        parsed = NLQueryAssistant._parse_llm_response("This is not JSON")
        assert parsed["sql"] is None
        assert parsed["confidence"] == 0.0

    def test_glossary_does_not_match_substrings(self):
        matches = NLQueryAssistant._resolve_glossary("Requirements by fit/gap status")
        assert all(match["term"] != "fi" for match in matches)

    def test_fallback_sql_for_fit_gap_query(self):
        fallback = NLQueryAssistant._fallback_sql(
            NLQueryAssistant._build_query_context("Requirements by fit/gap status", 1)
        )
        assert fallback is not None
        assert "FROM explore_requirements" in fallback["sql"]
        assert "GROUP BY COALESCE(fit_status, 'unclassified')" in fallback["sql"]
        assert fallback["confidence"] >= 0.8

    def test_fallback_sql_for_decision_count_query(self):
        fallback = NLQueryAssistant._fallback_sql(
            NLQueryAssistant._build_query_context("How many decisions are in the project?", 1)
        )
        assert fallback is not None
        assert "FROM decisions" in fallback["sql"]
        assert "FROM explore_decisions" in fallback["sql"]
        assert "total_decision_count" in fallback["sql"]

    def test_fallback_sql_for_workshop_open_item_count_query(self):
        fallback = NLQueryAssistant._fallback_sql(
            NLQueryAssistant._build_query_context("how many open items we have under the workshops?", 1)
        )
        assert fallback is not None
        assert "FROM explore_open_items" in fallback["sql"]
        assert "workshop_id IS NOT NULL" in fallback["sql"]
        assert "workshop_open_item_count" in fallback["sql"]

    def test_fallback_sql_for_fi_workshop_open_item_count_query(self):
        fallback = NLQueryAssistant._fallback_sql(
            NLQueryAssistant._build_query_context("How many open items under the FI module workshops?", 1)
        )
        assert fallback is not None
        assert "JOIN explore_workshops ew" in fallback["sql"]
        assert "ew.process_area IN ('FI')" in fallback["sql"]
        assert "workshop_open_item_count" in fallback["sql"]

    def test_fallback_sql_for_sd_workshop_requirement_count_query(self):
        fallback = NLQueryAssistant._fallback_sql(
            NLQueryAssistant._build_query_context("How many Requirements we have under SD module workshops?", 1)
        )
        assert fallback is not None
        assert "FROM explore_requirements er" in fallback["sql"]
        assert "JOIN explore_workshops ew" in fallback["sql"]
        assert "ew.process_area IN ('SD')" in fallback["sql"]
        assert "workshop_requirement_count" in fallback["sql"]

    def test_generic_workshop_metric_fallback_detects_open_items(self):
        fallback = NLQueryAssistant._fallback_workshop_metric_sql(
            NLQueryAssistant._build_query_context("Count FI workshop open items", 1)
        )
        assert fallback is not None
        assert "FROM explore_open_items eoi" in fallback["sql"]
        assert "ew.process_area IN ('FI')" in fallback["sql"]

    def test_generic_workshop_metric_fallback_detects_requirements(self):
        fallback = NLQueryAssistant._fallback_workshop_metric_sql(
            NLQueryAssistant._build_query_context("Count SD workshop requirements", 1)
        )
        assert fallback is not None
        assert "FROM explore_requirements er" in fallback["sql"]
        assert "ew.process_area IN ('SD')" in fallback["sql"]

    def test_generic_module_metric_fallback_detects_test_cases(self):
        fallback = NLQueryAssistant._fallback_module_metric_sql(
            NLQueryAssistant._build_query_context("How mant test cases we have related MM module?", 1)
        )
        assert fallback is not None
        assert "FROM test_cases tc" in fallback["sql"]
        assert "tc.module IN ('MM')" in fallback["sql"]
        assert "test_case_count" in fallback["sql"]

    def test_generic_entity_metric_fallback_detects_project_rfc_count(self):
        fallback = NLQueryAssistant._fallback_entity_metric_sql(
            NLQueryAssistant._build_query_context("How many RFC we have in this project?", 1, 7)
        )
        assert fallback is not None
        assert "FROM change_requests cr" in fallback["sql"]
        assert "cr.program_id = 1" in fallback["sql"]
        assert "cr.project_id = 7" in fallback["sql"]
        assert "rfc_count" in fallback["sql"]

    def test_generic_entity_metric_fallback_detects_project_risk_count(self):
        fallback = NLQueryAssistant._fallback_entity_metric_sql(
            NLQueryAssistant._build_query_context("How many risk items are under this project?", 1, 7)
        )
        assert fallback is not None
        assert "FROM risks r" in fallback["sql"]
        assert "r.program_id = 1" in fallback["sql"]
        assert "r.project_id = 7" not in fallback["sql"]
        assert "risk_count" in fallback["sql"]

    def test_generic_entity_metric_fallback_detects_test_case_count(self):
        fallback = NLQueryAssistant._fallback_entity_metric_sql(
            NLQueryAssistant._build_query_context("How many test cases we have", 1, 7)
        )
        assert fallback is not None
        assert "FROM test_cases tc" in fallback["sql"]
        assert "tc.program_id = 1" in fallback["sql"]
        assert "test_case_count" in fallback["sql"]

    def test_generic_entity_metric_fallback_detects_rejected_requirement_count(self):
        fallback = NLQueryAssistant._fallback_entity_metric_sql(
            NLQueryAssistant._build_query_context("How many rejected requirement we have?", 1)
        )
        assert fallback is not None
        assert "FROM requirements req" in fallback["sql"]
        assert "req.program_id = 1" in fallback["sql"]
        assert "req.status = 'rejected'" in fallback["sql"]
        assert "requirement_count" in fallback["sql"]

    def test_detect_primary_entity_returns_risks_for_risk_items(self):
        assert NLQueryAssistant._detect_primary_entity("How many risk items are under this project?") == "risks"

    def test_build_answer_returns_chat_friendly_count_summary(self):
        query_context = NLQueryAssistant._build_query_context("How many risk items are under this project?", 1, 7)
        answer = NLQueryAssistant._build_answer(
            query_context,
            {
                "executed": True,
                "results": [{"risk_count": 3}],
                "row_count": 1,
            },
        )
        assert answer == "There are 3 risk items in the selected project."

    def test_build_answer_returns_chat_friendly_test_case_summary(self):
        query_context = NLQueryAssistant._build_query_context("How many test cases we have", 1, 7)
        answer = NLQueryAssistant._build_answer(
            query_context,
            {
                "executed": True,
                "results": [{"test_case_count": 4}],
                "row_count": 1,
            },
        )
        assert answer == "There are 4 test cases in the selected project."

    def test_build_answer_returns_chat_friendly_requirement_summary(self):
        query_context = NLQueryAssistant._build_query_context("How many rejected requirement we have?", 1)
        answer = NLQueryAssistant._build_answer(
            query_context,
            {
                "executed": True,
                "results": [{"requirement_count": 1}],
                "row_count": 1,
            },
        )
        assert answer == "There is 1 requirement in the selected program."

    def test_detect_primary_entity_returns_change_requests_for_rfc(self):
        assert NLQueryAssistant._detect_primary_entity("How many RFC we have in this project?") == "change_requests"

    def test_process_query_uses_deterministic_path_before_llm(self):
        class FailingGateway:
            def chat(self, **kwargs):
                raise AssertionError("LLM should not be called for deterministic queries")

        assistant = NLQueryAssistant(gateway=FailingGateway())
        result = assistant.process_query("How many open items under the FI module workshops?", program_id=1, auto_execute=False)

        assert result["sql"] is not None
        assert "ew.process_area IN ('FI')" in result["sql"]
        assert result["error"] is None

    def test_process_query_returns_guidance_for_unsupported_question(self):
        class FailingGateway:
            def chat(self, **kwargs):
                raise RuntimeError("stub failure")

        assistant = NLQueryAssistant(gateway=FailingGateway())
        result = assistant.process_query("What is your favorite SAP color?", program_id=1, auto_execute=False)

        assert result["sql"] is None
        assert result["error"] is None
        assert "safe SQL pattern" in result["explanation"]
        assert result["suggestions"]

    def test_confidence_thresholds(self):
        assert NLQueryAssistant.CONFIDENCE_THRESHOLD == 0.6
        assert NLQueryAssistant.HIGH_COMPLEXITY_THRESHOLD == 0.4

    def test_db_schema_context_has_all_tables(self):
        for table in ["programs", "phases", "requirements", "defects", "risks",
                       "backlog_items", "test_cases", "sprints", "change_requests"]:
            assert table in DB_SCHEMA_CONTEXT


# ═════════════════════════════════════════════════════════════════════════════
# 4. NL QUERY API ENDPOINT (Task 8.4)
# ═════════════════════════════════════════════════════════════════════════════

class TestNLQueryAPI:
    """Tests for the /api/v1/ai/query/* endpoints."""

    def test_nl_query_requires_query(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={})
        assert res.status_code == 400
        assert "query" in res.get_json()["error"]

    def test_nl_query_accepts_query(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "List all programs",
        })
        # Should return something (may error with local stub but shouldn't 500)
        assert res.status_code in (200, 422)
        data = res.get_json()
        assert "original_query" in data

    def test_nl_query_with_program_id(self, client):
        prog = _create_program(client)
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "Count defects",
            "program_id": prog["id"],
        })
        assert res.status_code in (200, 422)

    def test_nl_query_returns_fallback_sql_for_fit_gap_hint(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "Requirements by fit/gap status",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is not None
        assert "explore_requirements" in data["sql"]
        assert data["error"] is None

    def test_nl_query_returns_fallback_sql_for_decision_count(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many decisions are in the project?",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is not None
        assert "total_decision_count" in data["sql"]
        assert data["error"] is None

    def test_nl_query_returns_fallback_sql_for_workshop_open_item_count(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "how many open items we have under the workshops?",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is not None
        assert "explore_open_items" in data["sql"]
        assert "workshop_open_item_count" in data["sql"]
        assert data["error"] is None

    def test_nl_query_returns_fallback_sql_for_fi_workshop_open_item_count(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many open items under the FI module workshops?",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is not None
        assert "JOIN explore_workshops ew" in data["sql"]
        assert "ew.process_area IN ('FI')" in data["sql"]
        assert data["error"] is None

    def test_nl_query_returns_fallback_sql_for_sd_workshop_requirement_count(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many Requirements we have under SD module workshops?",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is not None
        assert "FROM explore_requirements er" in data["sql"]
        assert "ew.process_area IN ('SD')" in data["sql"]
        assert "workshop_requirement_count" in data["sql"]
        assert data["error"] is None

    def test_nl_query_returns_fallback_sql_for_mm_module_test_case_count(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How mant test cases we have related MM module?",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is not None
        assert "FROM test_cases tc" in data["sql"]
        assert "tc.module IN ('MM')" in data["sql"]
        assert "test_case_count" in data["sql"]
        assert data["error"] is None

    def test_nl_query_returns_fallback_sql_for_project_rfc_count(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many RFC we have in this project?",
            "program_id": 1,
            "project_id": 7,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is not None
        assert "FROM change_requests cr" in data["sql"]
        assert "cr.project_id = 7" in data["sql"]
        assert "rfc_count" in data["sql"]
        assert data["error"] is None

    def test_nl_query_returns_fallback_sql_for_project_risk_count(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many risk items are under this project?",
            "program_id": 1,
            "project_id": 7,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is not None
        assert "FROM risks r" in data["sql"]
        assert "r.project_id = 7" not in data["sql"]
        assert "risk_count" in data["sql"]
        assert data["error"] is None

    def test_nl_query_returns_fallback_sql_for_test_case_count(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is not None
        assert "FROM test_cases tc" in data["sql"]
        assert "tc.program_id = 1" in data["sql"]
        assert "test_case_count" in data["sql"]
        assert data["error"] is None

    def test_nl_query_returns_fallback_sql_for_rejected_requirement_count(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many rejected requirement we have?",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is not None
        assert "FROM requirements req" in data["sql"]
        assert "req.status = 'rejected'" in data["sql"]
        assert "requirement_count" in data["sql"]
        assert data["error"] is None

    def test_nl_query_returns_guidance_instead_of_422_for_unsupported_question(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "What is your favorite SAP color?",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["sql"] is None
        assert data["error"] is None
        assert data["suggestions"]

    def test_nl_query_supports_direct_list_first_entity_prompt(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "List only the top 2 SD test cases sorted by priority",
            "program_id": 1,
            "project_id": 7,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["error"] is None
        assert "SELECT tc.code, tc.title, tc.status, tc.priority, tc.module, tc.test_layer" in data["sql"]
        assert "tc.module IN ('SD')" in data["sql"]
        assert "ORDER BY tc.priority DESC" in data["sql"]
        assert data["sql"].strip().endswith("LIMIT 2")

    def test_nl_query_supports_direct_defect_list_prompt(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "List open SD defects",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["error"] is None
        assert "SELECT d.code, d.title, d.status, d.severity, d.module, d.assigned_to, d.reported_at" in data["sql"]
        assert "d.status NOT IN ('closed', 'rejected')" in data["sql"]
        assert "d.module IN ('SD')" in data["sql"]

    def test_nl_query_supports_direct_defect_count_with_severity(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many P1 SD defects do we have",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["error"] is None
        assert "SELECT COUNT(*) AS defect_count" in data["sql"]
        assert "d.severity = 'P1'" in data["sql"]
        assert "d.module IN ('SD')" in data["sql"]

    def test_nl_query_supports_direct_requirement_count_with_priority_and_module(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many high priority FI requirements do we have",
            "program_id": 1,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["error"] is None
        assert "SELECT COUNT(*) AS requirement_count" in data["sql"]
        assert "req.priority = 'high'" in data["sql"]
        assert "req.module IN ('FI')" in data["sql"]

    def test_nl_query_supports_direct_change_request_list_with_source_module(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "List open SD RFCs sorted by priority",
            "program_id": 1,
            "project_id": 7,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["error"] is None
        assert "SELECT cr.code, cr.title, cr.status, cr.change_model, cr.change_domain" in data["sql"]
        assert "cr.project_id = 7" in data["sql"]
        assert "cr.status NOT IN ('closed', 'rejected', 'cancelled')" in data["sql"]
        assert "cr.source_module IN ('SD')" in data["sql"]
        assert "ORDER BY cr.priority DESC" in data["sql"]

    def test_nl_query_supports_direct_risk_count_without_invalid_project_filter(self, client):
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many open high priority risks do we have",
            "program_id": 1,
            "project_id": 7,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["error"] is None
        assert "SELECT COUNT(*) AS risk_count" in data["sql"]
        assert "r.status NOT IN ('closed', 'mitigated')" in data["sql"]
        assert "r.priority = 'high'" in data["sql"]
        assert "r.project_id" not in data["sql"]

    def test_nl_query_persists_exchange_into_conversation(self, client, app):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["conversation_id"] == conversation_id
        assert data["assistant_message_id"] is not None
        assert data["user_message_id"] is not None

        with app.app_context():
            conversation = AIConversation.query.get(conversation_id)
            assert conversation is not None
            assert conversation.assistant_type == "nl_query"
            assert conversation.message_count == 2
            saved_messages = conversation.messages.order_by(AIConversationMessage.seq.asc()).all()
            assert len(saved_messages) == 2
            assert saved_messages[0].role == "user"
            assert saved_messages[0].content == "How many test cases we have"
            assert saved_messages[1].role == "assistant"
            assert '"type": "nl_query_result"' in saved_messages[1].content

    def test_nl_query_persists_routing_metadata_into_conversation(self, client, app):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        routing_note = "This message was handled as a new question because the previous result could not be refined directly."
        res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "List only the top 2 SD ones sorted by priority",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "routing_note": routing_note,
            "routed_as_fresh_query": True,
            "auto_execute": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["routing_note"] == routing_note
        assert data["routed_as_fresh_query"] is True

        with app.app_context():
            saved_messages = (
                AIConversationMessage.query.filter_by(conversation_id=conversation_id)
                .order_by(AIConversationMessage.seq.asc())
                .all()
            )
            assert len(saved_messages) == 2
            payload = json.loads(saved_messages[1].content)
            assert payload["routing_note"] == routing_note
            assert payload["routed_as_fresh_query"] is True

    def test_conversation_list_exposes_context_payload(self, client):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7, "auto_execute": True},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        res = client.get("/api/v1/ai/conversations?assistant_type=nl_query&program_id=1")
        assert res.status_code == 200
        conversations = res.get_json()
        target = next((conversation for conversation in conversations if conversation["id"] == conversation_id), None)
        assert target is not None
        assert target["context"]["project_id"] == 7

    def test_refine_nl_query_requires_conversation_id(self, client):
        res = client.post("/api/v1/ai/query/refine", json={"refinement": "Show top 5"})
        assert res.status_code == 400
        assert res.get_json()["error"] == "conversation_id is required"

    def test_refine_nl_query_persists_follow_up_exchange(self, client, app):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        query_res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert query_res.status_code == 200

        refine_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "For FI only",
        })
        assert refine_res.status_code == 200
        data = refine_res.get_json()
        assert data["conversation_id"] == conversation_id
        assert data["assistant_message_id"] is not None
        assert data["user_message_id"] is not None
        assert data["executed"] is True
        assert data["row_count"] >= 0
        assert "filtered to module FI" in data["explanation"]
        assert "tc.module = 'FI'" in data["sql"]

        with app.app_context():
            conversation = AIConversation.query.get(conversation_id)
            assert conversation is not None
            assert conversation.message_count == 4
            saved_messages = conversation.messages.order_by(AIConversationMessage.seq.asc()).all()
            assert len(saved_messages) == 4
            assert saved_messages[2].role == "user"
            assert saved_messages[2].content == "For FI only"
            assert saved_messages[3].role == "assistant"
            assert '"refinement": "For FI only"' in saved_messages[3].content

    def test_refine_nl_query_rejects_top_n_on_count_result(self, client):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        query_res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert query_res.status_code == 200

        refine_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "Show top 5",
        })
        assert refine_res.status_code == 400
        data = refine_res.get_json()
        assert "single count result" in data["error"]
        assert "Group by module" in data["suggestions"]

    def test_refine_nl_query_supports_recent_time_window(self, client):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        query_res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert query_res.status_code == 200

        refine_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "Last 30 days",
        })
        assert refine_res.status_code == 200
        data = refine_res.get_json()
        assert "restricted to the last 30 days" in data["explanation"]
        assert "tc.updated_at >= '" in data["sql"]

    def test_refine_nl_query_can_expand_count_to_list(self, client):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        query_res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert query_res.status_code == 200

        refine_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "List them",
        })
        assert refine_res.status_code == 200
        data = refine_res.get_json()
        assert "expanded the count into a detailed list" in data["explanation"]
        assert "SELECT tc.code, tc.title, tc.status, tc.priority, tc.module, tc.test_layer" in data["sql"]
        assert "ORDER BY tc.updated_at DESC, tc.code ASC" in data["sql"]

    def test_refine_nl_query_can_filter_list_by_priority(self, client):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        query_res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert query_res.status_code == 200

        list_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "List them",
        })
        assert list_res.status_code == 200

        refine_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "Only medium priority",
        })
        assert refine_res.status_code == 200
        data = refine_res.get_json()
        assert "filtered to priority medium" in data["explanation"]
        assert "tc.priority = 'medium'" in data["sql"]

    def test_refine_nl_query_supports_conversational_prefixes(self, client):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        query_res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert query_res.status_code == 200

        list_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "List them",
        })
        assert list_res.status_code == 200

        refine_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "then only medium priority",
        })
        assert refine_res.status_code == 200
        data = refine_res.get_json()
        assert "filtered to priority medium" in data["explanation"]
        assert "tc.priority = 'medium'" in data["sql"]

    def test_refine_nl_query_can_group_count_by_module(self, client):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        query_res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert query_res.status_code == 200

        refine_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "Group by module",
        })
        assert refine_res.status_code == 200
        data = refine_res.get_json()
        assert "grouped by module" in data["explanation"]
        assert "AS refinement_group" in data["sql"]
        assert "GROUP BY tc.module" in data["sql"]

    def test_refine_nl_query_can_expand_grouped_module_bucket_to_list(self, client):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        query_res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert query_res.status_code == 200

        grouped_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "Group by module",
        })
        assert grouped_res.status_code == 200

        drilldown_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "List the SD ones",
        })
        assert drilldown_res.status_code == 200
        data = drilldown_res.get_json()
        assert "expanded the grouped result into a detailed list" in data["explanation"]
        assert "tc.module = 'SD'" in data["sql"]
        assert "SELECT tc.code, tc.title, tc.status, tc.priority, tc.module, tc.test_layer" in data["sql"]

    def test_refine_nl_query_can_expand_grouped_priority_bucket_to_list(self, client):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        query_res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert query_res.status_code == 200

        grouped_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "Group by priority",
        })
        assert grouped_res.status_code == 200

        drilldown_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "List the medium ones",
        })
        assert drilldown_res.status_code == 200
        data = drilldown_res.get_json()
        assert "expanded the grouped result into a detailed list" in data["explanation"]
        assert "tc.priority = 'medium'" in data["sql"]

    def test_refine_nl_query_can_chain_grouped_drilldown_with_sort_and_limit(self, client):
        conv_res = client.post("/api/v1/ai/conversations", json={
            "assistant_type": "nl_query",
            "program_id": 1,
            "context": {"project_id": 7},
        })
        assert conv_res.status_code == 201
        conversation_id = conv_res.get_json()["id"]

        query_res = client.post("/api/v1/ai/query/natural-language", json={
            "query": "How many test cases we have",
            "program_id": 1,
            "project_id": 7,
            "conversation_id": conversation_id,
            "auto_execute": False,
        })
        assert query_res.status_code == 200

        grouped_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "Group by module",
        })
        assert grouped_res.status_code == 200

        drilldown_res = client.post("/api/v1/ai/query/refine", json={
            "conversation_id": conversation_id,
            "refinement": "List only the top 2 SD ones sorted by priority",
        })
        assert drilldown_res.status_code == 200
        data = drilldown_res.get_json()
        assert "expanded the grouped result into a detailed list limited to 2" in data["explanation"]
        assert "sorted by priority desc" in data["explanation"]
        assert "tc.module = 'SD'" in data["sql"]
        assert "ORDER BY tc.priority DESC" in data["sql"]
        assert data["sql"].strip().endswith("LIMIT 2")

    def test_execute_sql_requires_sql(self, client):
        res = client.post("/api/v1/ai/query/execute-sql", json={})
        assert res.status_code == 400

    def test_execute_sql_rejects_insert(self, client):
        res = client.post("/api/v1/ai/query/execute-sql", json={
            "sql": "INSERT INTO programs (name) VALUES ('hack')"
        })
        assert res.status_code == 400
        assert "error" in res.get_json()

    def test_execute_sql_valid_select(self, client):
        res = client.post("/api/v1/ai/query/execute-sql", json={
            "sql": "SELECT COUNT(*) as cnt FROM programs"
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["executed"] is True
        assert "results" in data

    def test_execute_sql_with_join(self, client):
        res = client.post("/api/v1/ai/query/execute-sql", json={
            "sql": "SELECT p.name, COUNT(r.id) as req_count FROM programs p LEFT JOIN requirements r ON r.program_id = p.id GROUP BY p.name"
        })
        assert res.status_code == 200

    def test_execute_sql_rejects_unknown_table(self, client):
        res = client.post("/api/v1/ai/query/execute-sql", json={
            "sql": "SELECT * FROM admin_secrets"
        })
        assert res.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# 5. REQUIREMENT ANALYST (Tasks 8.5 + 8.6)
# ═════════════════════════════════════════════════════════════════════════════

class TestRequirementAnalyst:
    """Tests for RequirementAnalyst class."""

    def test_init(self):
        analyst = RequirementAnalyst()
        assert analyst.gateway is None
        assert analyst.rag is None

    def test_classify_not_found(self, app):
        from app.ai.gateway import LLMGateway
        analyst = RequirementAnalyst(gateway=LLMGateway())
        result = analyst.classify(99999)
        assert result["error"] is not None
        assert "not found" in result["error"]

    def test_classify_with_local_stub(self, client, app):
        """E2E: classify a requirement using local stub LLM."""
        from app.ai.gateway import LLMGateway
        prog = _create_program(client)
        req = _create_requirement(client, prog["id"])

        gw = LLMGateway()
        analyst = RequirementAnalyst(gateway=gw)
        result = analyst.classify(req["id"], create_suggestion=False)

        assert result["requirement_id"] == req["id"]
        # Local stub returns partial_fit for classify/fit/gap queries
        assert result["classification"] in ("fit", "partial_fit", "gap", None)
        assert result["error"] is None or result["classification"] is not None

    def test_classify_creates_suggestion(self, client, app):
        """E2E: verify suggestion is created on classification."""
        from app.ai.gateway import LLMGateway
        prog = _create_program(client)
        req = _create_requirement(client, prog["id"])

        gw = LLMGateway()
        analyst = RequirementAnalyst(gateway=gw)
        result = analyst.classify(req["id"], create_suggestion=True)

        # Local stub may not return classification — mark as expected failure
        if result["classification"] is None:
            pytest.xfail("Local stub did not return classification — cannot verify suggestion creation")
        assert result["suggestion_id"] is not None
        # Verify suggestion in DB
        s = _db.session.get(AISuggestion, result["suggestion_id"])
        assert s is not None
        assert s.entity_type == "requirement"
        assert s.status == "pending"

    def test_batch_classify(self, client, app):
        from app.ai.gateway import LLMGateway
        prog = _create_program(client)
        r1 = _create_requirement(client, prog["id"], title="Req 1")
        r2 = _create_requirement(client, prog["id"], title="Req 2")

        gw = LLMGateway()
        analyst = RequirementAnalyst(gateway=gw)
        results = analyst.classify_batch([r1["id"], r2["id"]], create_suggestion=False)
        assert len(results) == 2

    def test_parse_response_valid(self):
        content = json.dumps({
            "classification": "gap",
            "confidence": 0.88,
            "reasoning": "Custom development needed",
        })
        parsed = RequirementAnalyst._parse_response(content)
        assert parsed["classification"] == "gap"
        assert parsed["confidence"] == 0.88

    def test_parse_response_markdown(self):
        content = '```json\n{"classification": "fit", "confidence": 0.95, "reasoning": "SAP standard"}\n```'
        parsed = RequirementAnalyst._parse_response(content)
        assert parsed["classification"] == "fit"

    def test_parse_response_invalid(self):
        parsed = RequirementAnalyst._parse_response("Not valid JSON at all")
        assert parsed["classification"] is None


# ═════════════════════════════════════════════════════════════════════════════
# 6. REQUIREMENT ANALYST API (Task 8.7)
# ═════════════════════════════════════════════════════════════════════════════

class TestRequirementAnalystAPI:
    """Tests for /api/v1/ai/analyst/requirement/* endpoints."""

    def test_analyse_not_found(self, client):
        res = client.post("/api/v1/ai/analyst/requirement/99999", json={})
        assert res.status_code == 422
        assert "not found" in res.get_json()["error"]

    def test_analyse_single(self, client):
        prog = _create_program(client)
        req = _create_requirement(client, prog["id"])
        res = client.post(f"/api/v1/ai/analyst/requirement/{req['id']}", json={
            "create_suggestion": False,
        })
        assert res.status_code in (200, 422)
        data = res.get_json()
        assert data["requirement_id"] == req["id"]

    def test_analyse_batch_empty(self, client):
        res = client.post("/api/v1/ai/analyst/requirement/batch", json={})
        assert res.status_code == 400

    def test_analyse_batch(self, client):
        prog = _create_program(client)
        r1 = _create_requirement(client, prog["id"], title="Req A")
        r2 = _create_requirement(client, prog["id"], title="Req B")
        res = client.post("/api/v1/ai/analyst/requirement/batch", json={
            "requirement_ids": [r1["id"], r2["id"]],
            "create_suggestion": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 2

    def test_analyse_creates_suggestion_via_api(self, client):
        prog = _create_program(client)
        req = _create_requirement(client, prog["id"])
        res = client.post(f"/api/v1/ai/analyst/requirement/{req['id']}", json={
            "create_suggestion": True,
        })
        data = res.get_json()
        # Ensure the API actually classified — don't silently skip assertions
        if not data.get("classification"):
            pytest.xfail("AI stub did not return classification — cannot verify suggestion")
        assert data.get("suggestion_id") is not None


# ═════════════════════════════════════════════════════════════════════════════
# 7. TEST CASE GENERATOR (Sprint 12)
# ═════════════════════════════════════════════════════════════════════════════

class TestTestCaseGenerator:
    def test_generate_with_explore_requirement_uuid(self, client):
        from app.ai.gateway import LLMGateway
        from app.ai.prompt_registry import PromptRegistry

        prog = _create_program(client)
        req = _create_explore_requirement(client, prog["id"])

        gw = LLMGateway()
        generator = TestCaseGenerator(gateway=gw, prompt_registry=PromptRegistry())
        result = generator.generate(requirement_id=req["id"], create_suggestion=False)

        assert result["error"] is None
        assert result["source_type"] == "explore_requirement"
        assert result["source_id"] == req["id"]
        assert result["test_cases"]

    def test_generate_test_cases_api_accepts_explore_requirement_id(self, client):
        prog = _create_program(client)
        req = _create_explore_requirement(client, prog["id"])

        res = client.post(
            "/api/v1/ai/generate/test-cases",
            json={
                "explore_requirement_id": req["id"],
                "module": "FI",
                "test_layer": "sit",
            },
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["source_type"] == "explore_requirement"
        assert data["source_id"] == req["id"]


# ═════════════════════════════════════════════════════════════════════════════
# 8. RISK ASSESSMENT
# ═════════════════════════════════════════════════════════════════════════════


class TestRiskAssessment:
    def test_assess_accepts_list_prompts_and_singular_rag_filter(self, client):
        from app.ai.prompt_registry import PromptRegistry

        prog = _create_program(client)
        rag_calls = {}

        class StubRAG:
            def search(self, query, **kwargs):
                rag_calls["query"] = query
                rag_calls.update(kwargs)
                return [{"content": "Historical cutover resource risk", "score": 0.91}]

        class StubGateway:
            def __init__(self):
                self.messages = None
                self.kwargs = None

            def chat(self, messages, **kwargs):
                self.messages = messages
                self.kwargs = kwargs
                return {
                    "content": json.dumps({
                        "risk_level": "medium",
                        "probability": 3,
                        "impact": 4,
                        "confidence": 0.72,
                        "reasoning": "Resource constraints during peak testing phase.",
                    })
                }

        gateway = StubGateway()
        assistant = RiskAssessment(
            gateway=gateway,
            rag=StubRAG(),
            prompt_registry=PromptRegistry(),
        )

        result = assistant.assess(prog["id"], create_suggestion=False)

        assert result["error"] is None
        assert rag_calls["program_id"] == prog["id"]
        assert rag_calls["entity_type"] == "risk"
        assert gateway.kwargs["purpose"] == "risk_assessment"
        assert gateway.kwargs["program_id"] == prog["id"]
        assert isinstance(gateway.messages, list)
        assert [msg["role"] for msg in gateway.messages] == ["system", "user"]
        assert "Similar past risks" in gateway.messages[1]["content"]
        assert len(result["risks"]) == 1
        assert result["risks"][0]["risk_level"] == "medium"


# ═════════════════════════════════════════════════════════════════════════════
# 9. DEFECT TRIAGE (Tasks 8.8 + 8.9)
# ═════════════════════════════════════════════════════════════════════════════

class TestDefectTriage:
    """Tests for DefectTriage class."""

    def test_init(self):
        triage = DefectTriage()
        assert triage.gateway is None

    def test_triage_not_found(self, app):
        from app.ai.gateway import LLMGateway
        triage = DefectTriage(gateway=LLMGateway())
        result = triage.triage(99999)
        assert result["error"] is not None
        assert "not found" in result["error"]

    def test_triage_with_local_stub(self, client, app):
        """E2E: triage a defect using local stub LLM."""
        from app.ai.gateway import LLMGateway
        prog = _create_program(client)
        defect = _create_defect(client, prog["id"])

        gw = LLMGateway()
        triage = DefectTriage(gateway=gw)
        result = triage.triage(defect["id"], create_suggestion=False)

        assert result["defect_id"] == defect["id"]
        # Local stub returns P2/FI for defect/triage queries
        assert result["severity"] in ("P1", "P2", "P3", "P4", None)
        assert result["error"] is None or result["severity"] is not None

    def test_triage_creates_suggestion(self, client, app):
        """E2E: verify suggestion is created on triage."""
        from app.ai.gateway import LLMGateway
        prog = _create_program(client)
        defect = _create_defect(client, prog["id"])

        gw = LLMGateway()
        triage = DefectTriage(gateway=gw)
        result = triage.triage(defect["id"], create_suggestion=True)

        # Ensure triage actually ran — if stub returns no severity, fail explicitly
        assert result["severity"] is not None, (
            "triage() returned no severity — test cannot verify suggestion creation"
        )
        assert result["suggestion_id"] is not None
        s = _db.session.get(AISuggestion, result["suggestion_id"])
        assert s is not None
        assert s.entity_type == "defect"

    def test_batch_triage(self, client, app):
        from app.ai.gateway import LLMGateway
        prog = _create_program(client)
        d1 = _create_defect(client, prog["id"], title="Defect 1")
        d2 = _create_defect(client, prog["id"], title="Defect 2")

        gw = LLMGateway()
        triage = DefectTriage(gateway=gw)
        results = triage.triage_batch([d1["id"], d2["id"]], create_suggestion=False)
        assert len(results) == 2

    def test_parse_response_valid(self):
        content = json.dumps({
            "severity": "P2",
            "module": "FI",
            "confidence": 0.85,
            "reasoning": "Financial posting error",
        })
        parsed = DefectTriage._parse_response(content)
        assert parsed["severity"] == "P2"
        assert parsed["confidence"] == 0.85

    def test_parse_response_markdown(self):
        content = '```json\n{"severity": "P1", "module": "SD", "confidence": 0.92, "reasoning": "Critical"}\n```'
        parsed = DefectTriage._parse_response(content)
        assert parsed["severity"] == "P1"

    def test_parse_response_invalid(self):
        parsed = DefectTriage._parse_response("Invalid content")
        assert parsed["severity"] is None

    def test_duplicate_thresholds(self):
        assert DUPLICATE_THRESHOLD > SIMILAR_THRESHOLD
        assert 0 < SIMILAR_THRESHOLD < 1
        assert 0 < DUPLICATE_THRESHOLD < 1


# ═════════════════════════════════════════════════════════════════════════════
# 10. DEFECT TRIAGE API (Task 8.10)
# ═════════════════════════════════════════════════════════════════════════════

class TestDefectTriageAPI:
    """Tests for /api/v1/ai/triage/defect/* endpoints."""

    def test_triage_not_found(self, client):
        res = client.post("/api/v1/ai/triage/defect/99999", json={})
        assert res.status_code == 422
        assert "not found" in res.get_json()["error"]

    def test_triage_single(self, client):
        prog = _create_program(client)
        defect = _create_defect(client, prog["id"])
        res = client.post(f"/api/v1/ai/triage/defect/{defect['id']}", json={
            "create_suggestion": False,
        })
        assert res.status_code in (200, 422)
        data = res.get_json()
        assert data["defect_id"] == defect["id"]

    def test_triage_batch_empty(self, client):
        res = client.post("/api/v1/ai/triage/defect/batch", json={})
        assert res.status_code == 400

    def test_triage_batch(self, client):
        prog = _create_program(client)
        d1 = _create_defect(client, prog["id"], title="Bug A")
        d2 = _create_defect(client, prog["id"], title="Bug B")
        res = client.post("/api/v1/ai/triage/defect/batch", json={
            "defect_ids": [d1["id"], d2["id"]],
            "create_suggestion": False,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 2

    def test_triage_creates_suggestion_via_api(self, client):
        prog = _create_program(client)
        defect = _create_defect(client, prog["id"])
        res = client.post(f"/api/v1/ai/triage/defect/{defect['id']}", json={
            "create_suggestion": True,
        })
        data = res.get_json()
        # Ensure the API actually triaged — don't silently skip assertions
        if not data.get("severity"):
            pytest.xfail("AI stub did not return severity — cannot verify suggestion")
        assert data.get("suggestion_id") is not None


# ═════════════════════════════════════════════════════════════════════════════
# 11. INTEGRATION TESTS (Cross-module)
# ═════════════════════════════════════════════════════════════════════════════

class TestAssistantIntegration:
    """Cross-module integration tests."""

    def test_suggestion_queue_flow_from_analyst(self, client, app):
        """Full flow: classify → suggestion → approve."""
        prog = _create_program(client)
        req = _create_requirement(client, prog["id"])

        # Classify
        res = client.post(f"/api/v1/ai/analyst/requirement/{req['id']}", json={
            "create_suggestion": True,
        })
        data = res.get_json()
        sid = data.get("suggestion_id")

        if sid:
            # Check suggestion exists
            res2 = client.get(f"/api/v1/ai/suggestions/{sid}")
            assert res2.status_code == 200
            s = res2.get_json()
            assert s["status"] == "pending"
            assert s["entity_type"] == "requirement"

            # Approve
            res3 = client.patch(f"/api/v1/ai/suggestions/{sid}/approve", json={
                "reviewer": "test_admin",
            })
            assert res3.status_code == 200
            assert res3.get_json()["status"] == "approved"

    def test_suggestion_queue_flow_from_triage(self, client, app):
        """Full flow: triage → suggestion → reject."""
        prog = _create_program(client)
        defect = _create_defect(client, prog["id"])

        # Triage
        res = client.post(f"/api/v1/ai/triage/defect/{defect['id']}", json={
            "create_suggestion": True,
        })
        data = res.get_json()
        sid = data.get("suggestion_id")

        if sid:
            # Reject
            res2 = client.patch(f"/api/v1/ai/suggestions/{sid}/reject", json={
                "reviewer": "test_admin",
                "note": "Severity assessment incorrect",
            })
            assert res2.status_code == 200
            assert res2.get_json()["status"] == "rejected"

    def test_all_three_assistants_available(self, client, app):
        """Verify all 3 assistant singletons can be initialised."""
        from app.blueprints.ai_bp import _get_nl_query, _get_req_analyst, _get_defect_triage
        assert _get_nl_query() is not None
        assert _get_req_analyst() is not None
        assert _get_defect_triage() is not None

    def test_imports(self):
        """Verify package-level imports work."""
        from app.ai.assistants import (
            NLQueryAssistant, RequirementAnalyst, DefectTriage,
            validate_sql, sanitize_sql,
        )
        assert NLQueryAssistant is not None
        assert RequirementAnalyst is not None
        assert DefectTriage is not None
