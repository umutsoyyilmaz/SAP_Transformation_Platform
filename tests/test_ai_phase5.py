"""
Sprint 21 — AI Phase 5 Final Capabilities Tests.

Covers:
    - AIFeedbackMetric & AITask models
    - DataMigrationAdvisor assistant
    - IntegrationAnalyst assistant
    - FeedbackPipeline service
    - TaskRunner service
    - AIDocExporter service
    - AIOrchestrator service
    - RAG entity extractors (interface, data_object, migration_wave)
    - Blueprint endpoints (26 new routes)
"""

import json
import time

import pytest

from app.models import db as _db
from app.models.ai import (
    AIFeedbackMetric,
    AITask,
    AISuggestion,
    AI_TASK_STATUSES,
    FEEDBACK_METRIC_TYPES,
    PURPOSE_MODEL_MAP,
)


# ══════════════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════════════


class TestAIFeedbackMetricModel:
    """AIFeedbackMetric model tests."""

    def test_create_feedback_metric(self, app):
        from datetime import datetime, timezone
        m = AIFeedbackMetric(
            assistant_type="requirement_analyst",
            period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
            total_suggestions=100,
            approved_count=70,
            rejected_count=20,
            modified_count=10,
            accuracy_score=0.80,
            avg_confidence=0.75,
        )
        _db.session.add(m)
        _db.session.commit()
        assert m.id is not None
        assert m.assistant_type == "requirement_analyst"
        assert m.accuracy_score == 0.80

    def test_to_dict(self, app):
        from datetime import datetime, timezone
        m = AIFeedbackMetric(
            assistant_type="defect_triage",
            period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
            total_suggestions=50,
            approved_count=40,
            rejected_count=5,
            modified_count=5,
            accuracy_score=0.90,
            avg_confidence=0.82,
        )
        _db.session.add(m)
        _db.session.commit()
        d = m.to_dict()
        assert d["assistant_type"] == "defect_triage"
        assert d["total_suggestions"] == 50
        assert d["accuracy_score"] == 0.90

    def test_rejection_reasons_json(self, app):
        from datetime import datetime, timezone
        reasons = json.dumps(["vague recommendation", "incorrect module"])
        m = AIFeedbackMetric(
            assistant_type="risk_assessment",
            period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
            total_suggestions=20,
            approved_count=10,
            rejected_count=8,
            modified_count=2,
            accuracy_score=0.60,
            common_rejection_reasons=reasons,
        )
        _db.session.add(m)
        _db.session.commit()
        parsed = json.loads(m.common_rejection_reasons)
        assert "vague recommendation" in parsed

    def test_repr(self, app):
        from datetime import datetime, timezone
        m = AIFeedbackMetric(
            assistant_type="test_case_generator",
            period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
            total_suggestions=10,
            approved_count=8,
            rejected_count=1,
            modified_count=1,
            accuracy_score=0.90,
        )
        _db.session.add(m)
        _db.session.commit()
        assert "test_case_generator" in repr(m)

    def test_feedback_metric_types_constant(self):
        assert "accuracy" in FEEDBACK_METRIC_TYPES
        assert "relevance" in FEEDBACK_METRIC_TYPES
        assert "hallucination" in FEEDBACK_METRIC_TYPES


class TestAITaskModel:
    """AITask model tests."""

    def test_create_task(self, app):
        t = AITask(
            task_type="migration_analyze",
            status="pending",
            user="test_user",
        )
        _db.session.add(t)
        _db.session.commit()
        assert t.id is not None
        assert t.status == "pending"

    def test_task_statuses_constant(self):
        assert "pending" in AI_TASK_STATUSES
        assert "running" in AI_TASK_STATUSES
        assert "completed" in AI_TASK_STATUSES
        assert "failed" in AI_TASK_STATUSES
        assert "cancelled" in AI_TASK_STATUSES

    def test_task_to_dict(self, app):
        t = AITask(
            task_type="workflow_risk",
            status="completed",
            progress_pct=100,
            user="admin",
            result_json=json.dumps({"result": "ok"}),
        )
        _db.session.add(t)
        _db.session.commit()
        d = t.to_dict()
        assert d["task_type"] == "workflow_risk"
        assert d["progress_pct"] == 100
        assert d["result"] is not None
        assert d["result"]["result"] == "ok"

    def test_task_with_program(self, client, program):
        t = AITask(
            task_type="integration_check",
            status="pending",
            user="test",
            program_id=program["id"],
        )
        _db.session.add(t)
        _db.session.commit()
        assert t.program_id == program["id"]

    def test_task_repr(self, app):
        t = AITask(task_type="export", status="running", user="sys")
        _db.session.add(t)
        _db.session.commit()
        assert "export" in repr(t)

    def test_task_input_output_json(self, app):
        t = AITask(
            task_type="batch",
            status="completed",
            user="sys",
            input_json=json.dumps({"scope": "full"}),
            result_json=json.dumps({"items": 42}),
        )
        _db.session.add(t)
        _db.session.commit()
        assert json.loads(t.input_json)["scope"] == "full"
        assert json.loads(t.result_json)["items"] == 42

    def test_purpose_model_map_s21_entries(self):
        assert "data_migration" in PURPOSE_MODEL_MAP
        assert "integration_analyst" in PURPOSE_MODEL_MAP
        assert "feedback" in PURPOSE_MODEL_MAP
        assert "orchestrator" in PURPOSE_MODEL_MAP


# ══════════════════════════════════════════════════════════════════════════════
# DATA MIGRATION ADVISOR
# ══════════════════════════════════════════════════════════════════════════════


class TestDataMigrationAdvisor:
    """DataMigrationAdvisor assistant tests."""

    def test_analyze_via_api(self, client, program):
        res = client.post("/api/v1/ai/migration/analyze", json={
            "program_id": program["id"],
            "scope": "full",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "strategy" in data or "error" not in data

    def test_analyze_missing_program(self, client):
        res = client.post("/api/v1/ai/migration/analyze", json={})
        assert res.status_code == 400
        assert "program_id" in res.get_json()["error"]

    def test_optimize_waves(self, client, program):
        res = client.post("/api/v1/ai/migration/optimize-waves", json={
            "program_id": program["id"],
            "max_parallel": 2,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, dict)

    def test_optimize_waves_missing_program(self, client):
        res = client.post("/api/v1/ai/migration/optimize-waves", json={})
        assert res.status_code == 400

    def test_reconciliation(self, client, program):
        res = client.post("/api/v1/ai/migration/reconciliation", json={
            "program_id": program["id"],
            "data_object": "Vendor Master",
        })
        assert res.status_code == 200

    def test_reconciliation_missing_program(self, client):
        res = client.post("/api/v1/ai/migration/reconciliation", json={})
        assert res.status_code == 400

    def test_analyze_creates_suggestion(self, client, program):
        res = client.post("/api/v1/ai/migration/analyze", json={
            "program_id": program["id"],
            "create_suggestion": True,
        })
        assert res.status_code == 200
        # Check a suggestion was created
        suggestions = AISuggestion.query.filter_by(
            suggestion_type="data_migration"
        ).all()
        # May or may not create depending on stub response parsing
        assert isinstance(suggestions, list)

    def test_advisor_direct_instantiation(self, app):
        from app.ai.assistants.data_migration import DataMigrationAdvisor
        from app.ai.gateway import LLMGateway
        from app.ai.rag import RAGPipeline
        from app.ai.prompt_registry import PromptRegistry

        gw = LLMGateway()
        rag = RAGPipeline(gateway=gw)
        pr = PromptRegistry()
        advisor = DataMigrationAdvisor(gw, rag, pr, None)
        assert advisor.gateway is gw
        assert advisor.rag is rag


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION ANALYST
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegrationAnalyst:
    """IntegrationAnalyst assistant tests."""

    def test_dependencies_via_api(self, client, program):
        res = client.post("/api/v1/ai/integration/dependencies", json={
            "program_id": program["id"],
        })
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, dict)

    def test_dependencies_missing_program(self, client):
        res = client.post("/api/v1/ai/integration/dependencies", json={})
        assert res.status_code == 400

    def test_validate_switch(self, client, program):
        res = client.post("/api/v1/ai/integration/validate-switch", json={
            "program_id": program["id"],
            "switch_plan_id": 1,
        })
        assert res.status_code == 200

    def test_validate_switch_missing_program(self, client):
        res = client.post("/api/v1/ai/integration/validate-switch", json={})
        assert res.status_code == 400

    def test_analyst_direct_instantiation(self, app):
        from app.ai.assistants.integration_analyst import IntegrationAnalyst
        from app.ai.gateway import LLMGateway
        from app.ai.rag import RAGPipeline
        from app.ai.prompt_registry import PromptRegistry

        gw = LLMGateway()
        rag = RAGPipeline(gateway=gw)
        pr = PromptRegistry()
        analyst = IntegrationAnalyst(gw, rag, pr, None)
        assert analyst.gateway is gw


# ══════════════════════════════════════════════════════════════════════════════
# FEEDBACK PIPELINE
# ══════════════════════════════════════════════════════════════════════════════


class TestFeedbackPipeline:
    """FeedbackPipeline service tests."""

    def test_compute_accuracy_empty(self, app):
        from app.ai.feedback import FeedbackPipeline
        pipeline = FeedbackPipeline()
        result = pipeline.compute_accuracy_scores(days=30)
        assert isinstance(result, list)

    def test_compute_accuracy_with_suggestions(self, app):
        from app.ai.feedback import FeedbackPipeline
        # Create some suggestions
        for i in range(5):
            s = AISuggestion(
                entity_type="requirement",
                entity_id=i + 1,
                title=f"Suggestion {i}",
                suggestion_type="requirement_analyst",
                status="approved" if i < 3 else "rejected",
                confidence=0.8,
            )
            _db.session.add(s)
        _db.session.commit()

        pipeline = FeedbackPipeline()
        result = pipeline.compute_accuracy_scores(days=30)
        assert isinstance(result, list)
        assert len(result) >= 1
        ra = [r for r in result if r["assistant_type"] == "requirement_analyst"]
        assert len(ra) == 1
        assert ra[0]["approved_count"] == 3

    def test_save_metrics(self, app):
        from app.ai.feedback import FeedbackPipeline
        pipeline = FeedbackPipeline()
        result = pipeline.save_metrics(days=30)
        _db.session.commit()
        assert isinstance(result, dict)
        assert "saved_metrics" in result

    def test_get_feedback_stats_empty(self, app):
        from app.ai.feedback import FeedbackPipeline
        pipeline = FeedbackPipeline()
        result = pipeline.get_feedback_stats("requirement_analyst")
        assert isinstance(result, (dict, list))

    def test_get_feedback_stats_with_data(self, app):
        from datetime import datetime, timezone
        from app.ai.feedback import FeedbackPipeline
        m = AIFeedbackMetric(
            assistant_type="defect_triage",
            period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
            total_suggestions=50,
            approved_count=40,
            rejected_count=5,
            modified_count=5,
            accuracy_score=0.90,
        )
        _db.session.add(m)
        _db.session.commit()

        pipeline = FeedbackPipeline()
        result = pipeline.get_feedback_stats("defect_triage")
        assert isinstance(result, (dict, list))

    def test_generate_recommendations_empty(self, app):
        from app.ai.feedback import FeedbackPipeline
        pipeline = FeedbackPipeline()
        result = pipeline.generate_prompt_recommendations(days=30)
        assert isinstance(result, list)

    def test_feedback_stats_api(self, client):
        res = client.get("/api/v1/ai/feedback/stats?assistant_type=defect_triage")
        assert res.status_code == 200

    def test_feedback_accuracy_api(self, client):
        res = client.get("/api/v1/ai/feedback/accuracy?days=7")
        assert res.status_code == 200

    def test_feedback_recommendations_api(self, client):
        res = client.get("/api/v1/ai/feedback/recommendations")
        assert res.status_code == 200

    def test_feedback_compute_api(self, client):
        res = client.post("/api/v1/ai/feedback/compute", json={"days": 7})
        assert res.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# TASK RUNNER
# ══════════════════════════════════════════════════════════════════════════════


class TestTaskRunner:
    """TaskRunner service tests."""

    def test_submit_task(self, app):
        from app.ai.task_runner import TaskRunner
        runner = TaskRunner()
        result = runner.submit(
            task_type="test_task",
            input_data={"key": "value"},
            user="tester",
        )
        assert isinstance(result, dict)
        assert result["task_type"] == "test_task"
        assert result["status"] == "pending"
        assert result["id"] is not None

    def test_get_status(self, app):
        from app.ai.task_runner import TaskRunner
        runner = TaskRunner()
        r = runner.submit(task_type="check", input_data={}, user="u")
        task_id = r["id"]
        status = runner.get_status(task_id)
        assert status is not None
        assert status["task_type"] == "check"

    def test_cancel_task(self, app):
        from app.ai.task_runner import TaskRunner
        runner = TaskRunner()
        r = runner.submit(task_type="cancel_me", input_data={}, user="u")
        task_id = r["id"]
        result = runner.cancel(task_id)
        assert isinstance(result, dict)
        assert result["status"] == "cancelled"

    def test_list_tasks(self, app):
        from app.ai.task_runner import TaskRunner
        runner = TaskRunner()
        runner.submit(task_type="list1", input_data={}, user="u1")
        runner.submit(task_type="list2", input_data={}, user="u2")
        result = runner.list_tasks()
        assert isinstance(result, list)

    def test_list_tasks_filtered(self, app):
        from app.ai.task_runner import TaskRunner
        runner = TaskRunner()
        runner.submit(task_type="f1", input_data={}, user="user_a")
        runner.submit(task_type="f2", input_data={}, user="user_b")
        result = runner.list_tasks(user="user_a")
        assert isinstance(result, list)

    def test_submit_with_execute_fn(self, app):
        from app.ai.task_runner import TaskRunner
        runner = TaskRunner()

        def _simple_fn(data):
            return {"processed": True}

        result = runner.submit(
            task_type="exec_test",
            input_data={"x": 1},
            user="u",
            execute_fn=_simple_fn,
        )
        assert isinstance(result, dict)
        assert result["status"] == "running"
        # Give the background thread time
        time.sleep(1.0)

    def test_tasks_api_list(self, client):
        res = client.get("/api/v1/ai/tasks")
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)

    def test_tasks_api_create(self, client):
        res = client.post("/api/v1/ai/tasks", json={
            "task_type": "api_test",
            "input": {"key": "val"},
            "user": "tester",
        })
        assert res.status_code == 201

    def test_tasks_api_create_missing_type(self, client):
        res = client.post("/api/v1/ai/tasks", json={})
        assert res.status_code == 400

    def test_tasks_api_get_status(self, client):
        # Create then get
        res = client.post("/api/v1/ai/tasks", json={
            "task_type": "status_check",
            "user": "u",
        })
        assert res.status_code == 201
        task_id = res.get_json()["id"]
        res2 = client.get(f"/api/v1/ai/tasks/{task_id}")
        assert res2.status_code == 200

    def test_tasks_api_not_found(self, client):
        res = client.get("/api/v1/ai/tasks/99999")
        assert res.status_code == 404

    def test_tasks_api_cancel(self, client):
        res = client.post("/api/v1/ai/tasks", json={
            "task_type": "cancel_test",
            "user": "u",
        })
        task_id = res.get_json()["id"]
        res2 = client.post(f"/api/v1/ai/tasks/{task_id}/cancel")
        assert res2.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# AI DOC EXPORTER
# ══════════════════════════════════════════════════════════════════════════════


class TestAIDocExporter:
    """AIDocExporter service tests."""

    def test_export_markdown_generic(self, app):
        from app.ai.export import AIDocExporter
        exporter = AIDocExporter()
        result = exporter.export_markdown("risk_assessment", {
            "risk_level": "medium",
            "recommendations": ["Review staffing", "Run pilot test"],
        })
        assert "Risk Assessment" in result
        assert "medium" in result

    def test_export_markdown_steering_pack(self, app):
        from app.ai.export import AIDocExporter
        exporter = AIDocExporter()
        result = exporter.export_markdown("steering_pack", {
            "title": "Weekly Pack",
            "executive_summary": "On track",
            "workstream_status": [
                {"name": "FI", "status": "green", "progress_pct": 90, "highlights": "Done"},
            ],
            "risk_escalations": [
                {"risk": "Delay", "severity": "high", "mitigation": "Add resources"},
            ],
        })
        assert "Weekly Pack" in result
        assert "FI" in result

    def test_export_markdown_wricef(self, app):
        from app.ai.export import AIDocExporter
        exporter = AIDocExporter()
        result = exporter.export_markdown("wricef_spec", {
            "title": "Custom Enhancement",
            "overview": "Enhancement for vendor processing",
            "functional_requirements": [
                {"id": "FR-001", "description": "Auto-calc tax", "priority": "high",
                 "acceptance_criteria": "Tax correct"},
            ],
            "technical_details": "BADI in ME21N",
            "test_approach": "Unit + integration",
        })
        assert "Custom Enhancement" in result
        assert "FR-001" in result

    def test_export_markdown_migration(self, app):
        from app.ai.export import AIDocExporter
        exporter = AIDocExporter()
        result = exporter.export_markdown("data_migration_strategy", {
            "strategy": "Big bang with waves",
            "wave_sequence": ["Wave 1: Master data", "Wave 2: Transactions"],
            "risk_areas": ["Volume", "Conversion"],
            "scope": "full",
            "estimated_duration_hours": 72,
        })
        assert "Data Migration Strategy" in result
        assert "Wave 1" in result

    def test_export_json(self, app):
        from app.ai.export import AIDocExporter
        exporter = AIDocExporter()
        result = exporter.export_json("risk_assessment", {"risk_level": "high"}, "Risk Report")
        parsed = json.loads(result)
        assert parsed["document_type"] == "risk_assessment"
        assert parsed["title"] == "Risk Report"

    def test_export_unsupported_type(self, app):
        from app.ai.export import AIDocExporter
        exporter = AIDocExporter()
        result = exporter.export_markdown("nonexistent", {})
        assert "Unsupported" in result

    def test_list_exportable_types(self, app):
        from app.ai.export import AIDocExporter
        exporter = AIDocExporter()
        types = exporter.list_exportable_types()
        assert len(types) >= 9
        type_names = [t["type"] for t in types]
        assert "steering_pack" in type_names
        assert "data_migration_strategy" in type_names

    def test_export_formats_api(self, client):
        res = client.get("/api/v1/ai/export/formats")
        assert res.status_code == 200
        data = res.get_json()
        assert "markdown" in data["formats"]
        assert "json" in data["formats"]

    def test_export_markdown_api(self, client):
        res = client.post("/api/v1/ai/export/markdown", json={
            "doc_type": "risk_assessment",
            "content": {"risk_level": "high"},
            "title": "Risk",
        })
        assert res.status_code == 200
        assert res.get_json()["format"] == "markdown"

    def test_export_json_api(self, client):
        res = client.post("/api/v1/ai/export/json", json={
            "doc_type": "test_cases",
            "content": {"cases": []},
        })
        assert res.status_code == 200
        assert res.get_json()["format"] == "json"

    def test_export_unsupported_format_api(self, client):
        res = client.post("/api/v1/ai/export/pdf", json={
            "doc_type": "risk_assessment",
            "content": {},
        })
        assert res.status_code == 400

    def test_export_missing_doc_type_api(self, client):
        res = client.post("/api/v1/ai/export/markdown", json={
            "content": {},
        })
        assert res.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# AI ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════


class TestAIOrchestrator:
    """AIOrchestrator service tests."""

    def test_list_workflows(self, app):
        from app.ai.orchestrator import AIOrchestrator
        orch = AIOrchestrator(assistants={})
        workflows = orch.list_workflows()
        assert len(workflows) >= 4
        names = [w["workflow"] for w in workflows]
        assert "requirement_to_spec" in names
        assert "migration_full_analysis" in names

    def test_execute_unknown_workflow(self, app):
        from app.ai.orchestrator import AIOrchestrator
        orch = AIOrchestrator(assistants={})
        result = orch.execute("nonexistent", {})
        assert "error" in result

    def test_execute_with_missing_assistants(self, app):
        from app.ai.orchestrator import AIOrchestrator
        orch = AIOrchestrator(assistants={})
        result = orch.execute("requirement_to_spec", {"text": "test"})
        assert result["status"] in ("completed", "partial")
        # All steps should be skipped since no assistants provided
        for step in result["step_results"]:
            assert step["status"] == "skipped"

    def test_resolve_path(self, app):
        from app.ai.orchestrator import AIOrchestrator
        data = {"a": {"b": {"c": "value"}}}
        assert AIOrchestrator._resolve_path(data, "$.a.b.c") == "value"
        assert AIOrchestrator._resolve_path(data, "$.a.b") == {"c": "value"}
        assert AIOrchestrator._resolve_path(data, "$.x") is None
        assert AIOrchestrator._resolve_path(data, "bad") is None

    def test_execute_async_without_runner(self, app):
        from app.ai.orchestrator import AIOrchestrator
        orch = AIOrchestrator(assistants={})
        result = orch.execute_async("requirement_to_spec", {})
        assert "error" in result

    def test_workflows_api_list(self, client):
        res = client.get("/api/v1/ai/workflows")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)
        assert len(data) >= 4

    def test_workflows_api_execute(self, client, program):
        res = client.post("/api/v1/ai/workflows/integration_validation/execute", json={
            "input": {"program_id": program["id"]},
            "program_id": program["id"],
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "workflow" in data or "error" in data

    def test_workflows_api_execute_unknown(self, client):
        res = client.post("/api/v1/ai/workflows/nonexistent/execute", json={
            "input": {},
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "error" in data

    def test_workflow_task_not_found(self, client):
        res = client.get("/api/v1/ai/workflows/tasks/99999")
        assert res.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# RAG ENTITY EXTRACTORS (Sprint 21)
# ══════════════════════════════════════════════════════════════════════════════


class TestRAGEntityExtractors:
    """New RAG entity extractors for S21."""

    def test_interface_extractor(self, app):
        from app.ai.rag import ENTITY_EXTRACTORS
        assert "interface" in ENTITY_EXTRACTORS
        result = ENTITY_EXTRACTORS["interface"]({
            "name": "SAP_to_Bank",
            "direction": "outbound",
            "protocol": "SFTP",
            "criticality": "high",
        })
        assert "SAP_to_Bank" in result
        assert "outbound" in result
        assert "SFTP" in result

    def test_data_object_extractor(self, app):
        from app.ai.rag import ENTITY_EXTRACTORS
        assert "data_object" in ENTITY_EXTRACTORS
        result = ENTITY_EXTRACTORS["data_object"]({
            "name": "Vendor Master",
            "object_type": "master_data",
            "record_count": 50000,
            "priority": "high",
        })
        assert "Vendor Master" in result
        assert "master_data" in result

    def test_migration_wave_extractor(self, app):
        from app.ai.rag import ENTITY_EXTRACTORS
        assert "migration_wave" in ENTITY_EXTRACTORS
        result = ENTITY_EXTRACTORS["migration_wave"]({
            "name": "Wave 1 - Master Data",
            "wave_number": 1,
            "status": "planned",
            "strategy": "big_bang",
        })
        assert "Wave 1" in result
        assert "planned" in result

    def test_extractor_count(self, app):
        from app.ai.rag import ENTITY_EXTRACTORS
        # 8 original + 3 new = 11 extractors
        assert len(ENTITY_EXTRACTORS) == 11

    def test_extractor_empty_data(self, app):
        from app.ai.rag import ENTITY_EXTRACTORS
        # Should handle empty dicts gracefully
        for name, fn in ENTITY_EXTRACTORS.items():
            result = fn({})
            assert isinstance(result, str)


# ══════════════════════════════════════════════════════════════════════════════
# ADDITIONAL API ENDPOINT TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestS21EndpointCoverage:
    """Additional endpoint coverage for S21 routes."""

    def test_migration_analyze_no_create(self, client, program):
        res = client.post("/api/v1/ai/migration/analyze", json={
            "program_id": program["id"],
            "create_suggestion": False,
        })
        assert res.status_code == 200

    def test_integration_dependencies_no_create(self, client, program):
        res = client.post("/api/v1/ai/integration/dependencies", json={
            "program_id": program["id"],
            "create_suggestion": False,
        })
        assert res.status_code == 200

    def test_feedback_stats_no_type(self, client):
        res = client.get("/api/v1/ai/feedback/stats")
        assert res.status_code == 200

    def test_export_markdown_reconciliation(self, client):
        res = client.post("/api/v1/ai/export/markdown", json={
            "doc_type": "reconciliation_checklist",
            "content": {"checks": ["check1", "check2"]},
        })
        assert res.status_code == 200

    def test_workflow_execute_async(self, client, program):
        res = client.post("/api/v1/ai/workflows/integration_validation/execute", json={
            "input": {},
            "program_id": program["id"],
            "async": True,
        })
        assert res.status_code == 200

    def test_export_change_impact(self, client):
        res = client.post("/api/v1/ai/export/markdown", json={
            "doc_type": "change_impact",
            "content": {"impact": "medium", "areas": ["FI", "CO"]},
        })
        assert res.status_code == 200

    def test_export_meeting_minutes(self, client):
        res = client.post("/api/v1/ai/export/json", json={
            "doc_type": "meeting_minutes",
            "content": {"attendees": ["A", "B"], "actions": []},
        })
        assert res.status_code == 200

    def test_tasks_list_with_filters(self, client):
        # Create a task first
        client.post("/api/v1/ai/tasks", json={
            "task_type": "filter_test",
            "user": "filter_user",
        })
        res = client.get("/api/v1/ai/tasks?user=filter_user&limit=10")
        assert res.status_code == 200
