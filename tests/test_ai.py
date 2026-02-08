"""
SAP Transformation Management Platform
Tests — AI Infrastructure (Sprint 7).

Covers:
    - AI Models (AIUsageLog, AIEmbedding, AISuggestion, AIAuditLog)
    - cost calculation
    - AI Blueprint API endpoints
        - Suggestions CRUD + lifecycle (approve/reject/modify)
        - Usage & cost endpoints
        - Audit log
        - Embeddings stats & search
        - Admin dashboard
        - Prompts listing
    - LLM Gateway (LocalStubProvider, provider routing)
    - Suggestion Queue service (create/approve/reject/list/stats)
    - Prompt Registry (built-in defaults, render, list)
"""

import json
import pytest

from app import create_app
from app.models import db as _db
from app.models.ai import (
    AIUsageLog, AIEmbedding, AISuggestion, AIAuditLog,
    calculate_cost, TOKEN_COSTS,
)


# ═════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def app():
    """Create app for testing (SQLite in-memory)."""
    from app.config import TestingConfig
    TestingConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    app = create_app("testing")
    return app


@pytest.fixture(scope="session")
def _setup_db(app):
    """Create tables once per session."""
    with app.app_context():
        _db.create_all()
    yield
    with app.app_context():
        _db.drop_all()


@pytest.fixture(autouse=True)
def session(app, _setup_db):
    """Wrap each test in a clean state."""
    with app.app_context():
        yield
        _db.session.rollback()
        for model in [AIAuditLog, AIUsageLog, AIEmbedding, AISuggestion]:
            _db.session.query(model).delete()
        _db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_suggestion(client, **overrides):
    """Helper: create a suggestion and return JSON."""
    payload = {
        "entity_type": "requirement",
        "entity_id": 1,
        "title": "Classify as Partial Fit",
        "suggestion_type": "fit_gap_classification",
        "description": "AI recommends classifying this requirement as partial fit",
        "confidence": 0.85,
        "model_used": "local-stub",
        "reasoning": "Based on SAP module analysis...",
    }
    payload.update(overrides)
    res = client.post("/api/v1/ai/suggestions", json=payload)
    assert res.status_code == 201
    return res.get_json()


def _create_usage_log(app, **overrides):
    """Helper: directly insert a usage log entry."""
    data = {
        "provider": "local",
        "model": "local-stub",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
        "cost_usd": 0.0,
        "latency_ms": 200,
        "user": "test_user",
        "purpose": "test",
        "success": True,
    }
    data.update(overrides)
    log = AIUsageLog(**data)
    _db.session.add(log)
    _db.session.commit()
    return log


def _create_audit_entry(app, **overrides):
    """Helper: directly insert an audit log entry."""
    data = {
        "action": "llm_call",
        "provider": "local",
        "model": "local-stub",
        "user": "test_user",
        "tokens_used": 150,
        "cost_usd": 0.0,
        "prompt_summary": "Test prompt",
        "response_summary": "Test response",
        "success": True,
    }
    data.update(overrides)
    entry = AIAuditLog(**data)
    _db.session.add(entry)
    _db.session.commit()
    return entry


# ═════════════════════════════════════════════════════════════════════════════
# COST CALCULATION
# ═════════════════════════════════════════════════════════════════════════════

class TestCostCalculation:
    """Test token cost calculation."""

    def test_calculate_cost_haiku(self, app):
        cost = calculate_cost("claude-3-5-haiku-20241022", 1000, 500)
        expected = (1000 * 1.00 + 500 * 5.00) / 1_000_000
        assert abs(cost - expected) < 1e-9

    def test_calculate_cost_gpt4o(self, app):
        cost = calculate_cost("gpt-4o", 10000, 5000)
        expected = (10000 * 2.50 + 5000 * 10.00) / 1_000_000
        assert abs(cost - expected) < 1e-9

    def test_calculate_cost_unknown_model(self, app):
        cost = calculate_cost("unknown-model", 1000, 500)
        assert cost == 0.0

    def test_calculate_cost_zero_tokens(self, app):
        cost = calculate_cost("claude-3-5-haiku-20241022", 0, 0)
        assert cost == 0.0

    def test_embedding_model_no_output_cost(self, app):
        cost = calculate_cost("text-embedding-3-small", 1000, 0)
        expected = (1000 * 0.02) / 1_000_000
        assert abs(cost - expected) < 1e-9


# ═════════════════════════════════════════════════════════════════════════════
# AI MODELS — to_dict
# ═════════════════════════════════════════════════════════════════════════════

class TestAIModels:
    """Test AI model helpers."""

    def test_usage_log_to_dict(self, app):
        log = _create_usage_log(app, provider="anthropic", model="claude-3-5-haiku-20241022")
        d = log.to_dict()
        assert d["provider"] == "anthropic"
        assert d["model"] == "claude-3-5-haiku-20241022"
        assert d["prompt_tokens"] == 100
        assert d["id"] is not None

    def test_embedding_to_dict(self, app):
        emb = AIEmbedding(
            entity_type="requirement", entity_id=1,
            chunk_text="Test chunk", embedding_json="[0.1,0.2]",
            module="FI",
        )
        _db.session.add(emb)
        _db.session.flush()
        d = emb.to_dict()
        assert d["entity_type"] == "requirement"
        assert d["has_embedding"] is True
        assert d["module"] == "FI"

    def test_suggestion_lifecycle(self, app):
        s = AISuggestion(
            entity_type="defect", entity_id=5, title="Triage: P1",
            suggestion_type="defect_triage", confidence=0.9,
        )
        _db.session.add(s)
        _db.session.flush()
        assert s.status == "pending"

        s.approve(reviewer="admin", note="Looks good")
        assert s.status == "approved"
        assert s.reviewed_by == "admin"

        s.mark_applied()
        assert s.status == "applied"
        assert s.applied_at is not None

    def test_suggestion_reject(self, app):
        s = AISuggestion(
            entity_type="risk", entity_id=3, title="Risk assessment",
            suggestion_type="risk_assessment",
        )
        _db.session.add(s)
        _db.session.flush()

        s.reject(reviewer="pm", note="Not applicable")
        assert s.status == "rejected"
        assert s.reviewed_by == "pm"

    def test_audit_log_to_dict(self, app):
        entry = _create_audit_entry(app)
        d = entry.to_dict()
        assert d["action"] == "llm_call"
        assert d["success"] is True
        assert d["id"] is not None


# ═════════════════════════════════════════════════════════════════════════════
# SUGGESTION API — CRUD
# ═════════════════════════════════════════════════════════════════════════════

class TestSuggestionAPI:
    """Test AI suggestion endpoints."""

    def test_create_suggestion(self, client):
        data = _create_suggestion(client)
        assert data["entity_type"] == "requirement"
        assert data["entity_id"] == 1
        assert data["status"] == "pending"
        assert data["confidence"] == 0.85
        assert data["id"] is not None

    def test_create_suggestion_missing_fields(self, client):
        res = client.post("/api/v1/ai/suggestions", json={"entity_type": "requirement"})
        assert res.status_code == 400
        assert "Missing required fields" in res.get_json()["error"]

    def test_list_suggestions_empty(self, client):
        res = client.get("/api/v1/ai/suggestions")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_suggestions_with_data(self, client):
        _create_suggestion(client, title="Suggestion 1")
        _create_suggestion(client, title="Suggestion 2")
        res = client.get("/api/v1/ai/suggestions")
        data = res.get_json()
        assert data["total"] == 2

    def test_list_suggestions_filter_status(self, client):
        _create_suggestion(client, title="S1")
        res = client.get("/api/v1/ai/suggestions?status=pending")
        data = res.get_json()
        assert data["total"] == 1

        res = client.get("/api/v1/ai/suggestions?status=approved")
        data = res.get_json()
        assert data["total"] == 0

    def test_get_suggestion_by_id(self, client):
        s = _create_suggestion(client)
        res = client.get(f"/api/v1/ai/suggestions/{s['id']}")
        assert res.status_code == 200
        assert res.get_json()["title"] == "Classify as Partial Fit"

    def test_get_suggestion_not_found(self, client):
        res = client.get("/api/v1/ai/suggestions/99999")
        assert res.status_code == 404

    def test_pending_count(self, client):
        _create_suggestion(client)
        _create_suggestion(client, title="S2")
        res = client.get("/api/v1/ai/suggestions/pending-count")
        assert res.status_code == 200
        assert res.get_json()["pending_count"] == 2

    def test_suggestion_stats(self, client):
        _create_suggestion(client)
        res = client.get("/api/v1/ai/suggestions/stats")
        assert res.status_code == 200
        stats = res.get_json()
        assert "total" in stats
        assert stats["total"] >= 1

    def test_approve_suggestion(self, client):
        s = _create_suggestion(client)
        res = client.patch(
            f"/api/v1/ai/suggestions/{s['id']}/approve",
            json={"reviewer": "admin", "note": "LGTM"},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "approved"
        assert data["reviewed_by"] == "admin"

    def test_reject_suggestion(self, client):
        s = _create_suggestion(client)
        res = client.patch(
            f"/api/v1/ai/suggestions/{s['id']}/reject",
            json={"reviewer": "pm", "note": "Not applicable"},
        )
        assert res.status_code == 200
        assert res.get_json()["status"] == "rejected"

    def test_modify_suggestion(self, client):
        s = _create_suggestion(client)
        res = client.patch(
            f"/api/v1/ai/suggestions/{s['id']}/modify",
            json={
                "suggestion_data": '{"fit_gap": "gap"}',
                "reviewer": "architect",
                "note": "Changed to gap",
            },
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "modified"

    def test_modify_suggestion_missing_data(self, client):
        s = _create_suggestion(client)
        res = client.patch(
            f"/api/v1/ai/suggestions/{s['id']}/modify",
            json={"reviewer": "admin"},
        )
        assert res.status_code == 400

    def test_approve_nonexistent(self, client):
        res = client.patch("/api/v1/ai/suggestions/99999/approve", json={})
        assert res.status_code == 404

    def test_reject_nonexistent(self, client):
        res = client.patch("/api/v1/ai/suggestions/99999/reject", json={})
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# USAGE & COST API
# ═════════════════════════════════════════════════════════════════════════════

class TestUsageAPI:
    """Test AI usage and cost endpoints."""

    def test_usage_empty(self, client):
        res = client.get("/api/v1/ai/usage")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total_calls"] == 0
        assert data["total_cost_usd"] == 0

    def test_usage_with_data(self, client, app):
        _create_usage_log(app, provider="anthropic", model="claude-3-5-haiku-20241022",
                          prompt_tokens=500, completion_tokens=200, total_tokens=700,
                          cost_usd=0.0015, purpose="requirement_analyst")
        _create_usage_log(app, provider="openai", model="gpt-4o-mini",
                          prompt_tokens=300, completion_tokens=100, total_tokens=400,
                          cost_usd=0.0001, purpose="defect_triage")
        res = client.get("/api/v1/ai/usage")
        data = res.get_json()
        assert data["total_calls"] == 2
        assert data["total_tokens"] == 1100
        assert "by_model" in data
        assert "by_purpose" in data

    def test_usage_filter_days(self, client, app):
        _create_usage_log(app)
        res = client.get("/api/v1/ai/usage?days=7")
        assert res.status_code == 200

    def test_cost_summary_empty(self, client):
        res = client.get("/api/v1/ai/usage/cost")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total_cost_usd"] == 0
        assert data["timeline"] == []

    def test_cost_summary_with_data(self, client, app):
        _create_usage_log(app, cost_usd=0.005)
        res = client.get("/api/v1/ai/usage/cost")
        data = res.get_json()
        assert data["total_cost_usd"] > 0
        assert len(data["timeline"]) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# AUDIT LOG API
# ═════════════════════════════════════════════════════════════════════════════

class TestAuditAPI:
    """Test AI audit log endpoints."""

    def test_audit_log_empty(self, client):
        res = client.get("/api/v1/ai/audit-log")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_audit_log_with_entries(self, client, app):
        _create_audit_entry(app, action="llm_call", user="admin")
        _create_audit_entry(app, action="embedding_create", user="system")
        res = client.get("/api/v1/ai/audit-log")
        data = res.get_json()
        assert data["total"] == 2

    def test_audit_log_filter_action(self, client, app):
        _create_audit_entry(app, action="llm_call")
        _create_audit_entry(app, action="search")
        res = client.get("/api/v1/ai/audit-log?action=llm_call")
        data = res.get_json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "llm_call"

    def test_audit_log_filter_user(self, client, app):
        _create_audit_entry(app, user="admin")
        _create_audit_entry(app, user="developer")
        res = client.get("/api/v1/ai/audit-log?user=admin")
        data = res.get_json()
        assert data["total"] == 1

    def test_audit_log_pagination(self, client, app):
        for i in range(5):
            _create_audit_entry(app, action=f"action_{i}")
        res = client.get("/api/v1/ai/audit-log?page=1&per_page=2")
        data = res.get_json()
        assert data["total"] == 5
        assert len(data["items"]) == 2


# ═════════════════════════════════════════════════════════════════════════════
# EMBEDDINGS / SEARCH API
# ═════════════════════════════════════════════════════════════════════════════

class TestEmbeddingsAPI:
    """Test AI embeddings endpoints."""

    def test_embedding_stats_empty(self, client):
        res = client.get("/api/v1/ai/embeddings/stats")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total_chunks"] == 0

    def test_embedding_stats_with_data(self, client, app):
        emb = AIEmbedding(
            entity_type="requirement", entity_id=1,
            chunk_text="Test requirement chunk", module="FI",
        )
        _db.session.add(emb)
        _db.session.commit()
        res = client.get("/api/v1/ai/embeddings/stats")
        data = res.get_json()
        assert data["total_chunks"] >= 1

    def test_search_no_query(self, client):
        res = client.post("/api/v1/ai/embeddings/search", json={})
        assert res.status_code == 400

    def test_search_empty_index(self, client):
        res = client.post("/api/v1/ai/embeddings/search", json={"query": "test requirement"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["count"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# ADMIN DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

class TestAdminDashboard:
    """Test AI admin dashboard endpoint."""

    def test_admin_dashboard_empty(self, client):
        res = client.get("/api/v1/ai/admin/dashboard")
        assert res.status_code == 200
        data = res.get_json()
        assert "usage" in data
        assert "suggestions" in data
        assert "embeddings" in data
        assert "recent_activity" in data
        assert data["usage"]["total_calls"] == 0

    def test_admin_dashboard_with_data(self, client, app):
        _create_usage_log(app, cost_usd=0.005)
        _create_audit_entry(app)
        _create_suggestion(client)
        res = client.get("/api/v1/ai/admin/dashboard")
        data = res.get_json()
        assert data["usage"]["total_calls"] >= 1
        assert data["suggestions"]["total"] >= 1


# ═════════════════════════════════════════════════════════════════════════════
# PROMPTS API
# ═════════════════════════════════════════════════════════════════════════════

class TestPromptsAPI:
    """Test prompt listing endpoint."""

    def test_list_prompts(self, client):
        res = client.get("/api/v1/ai/prompts")
        assert res.status_code == 200
        data = res.get_json()
        assert "prompts" in data
        names = [p["name"] for p in data["prompts"]]
        # Built-in defaults must appear
        assert "system_base" in names
        assert "requirement_analyst" in names


# ═════════════════════════════════════════════════════════════════════════════
# LLM GATEWAY — LocalStubProvider
# ═════════════════════════════════════════════════════════════════════════════

class TestLLMGateway:
    """Test LLM Gateway with local stub provider."""

    def test_gateway_init(self, app):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        # Local stub provider must always be available
        assert "local" in gw._providers

    def test_local_stub_chat(self, app):
        from app.ai.gateway import LocalStubProvider
        provider = LocalStubProvider()
        result = provider.chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="local-stub",
        )
        assert "content" in result
        assert "prompt_tokens" in result
        assert "completion_tokens" in result
        assert result["model"] == "local-stub"

    def test_local_stub_embed(self, app):
        from app.ai.gateway import LocalStubProvider
        provider = LocalStubProvider()
        vectors = provider.embed(["Test text"], model="local-stub")
        assert len(vectors) == 1
        assert len(vectors[0]) > 0  # Non-empty vector

    def test_gateway_chat_uses_local(self, app):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        result = gw.chat(
            messages=[{"role": "user", "content": "Classify this requirement"}],
            model="local-stub",
            purpose="test",
        )
        assert "content" in result
        assert result.get("provider") == "local"

    def test_gateway_embed(self, app):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        vectors = gw.embed(["Test text for embedding"])
        assert len(vectors) == 1

    def test_gateway_cost_logging(self, app):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        gw.chat(
            messages=[{"role": "user", "content": "Test prompt"}],
            model="local-stub",
            purpose="cost_test",
        )
        # Verify a usage log was created
        logs = AIUsageLog.query.filter_by(purpose="cost_test").all()
        assert len(logs) >= 1

    # ── Gemini integration tests ──

    def test_gemini_in_provider_map(self, app):
        """Gemini models must be registered in PROVIDER_MAP."""
        from app.ai.gateway import LLMGateway
        pmap = LLMGateway.PROVIDER_MAP
        assert pmap.get("gemini-2.5-flash") == "gemini"
        assert pmap.get("gemini-2.5-pro") == "gemini"
        assert pmap.get("gemini-2.0-flash") == "gemini"
        assert pmap.get("gemini-embedding-001") == "gemini"

    def test_gemini_provider_class_exists(self, app):
        """GeminiProvider class should be importable."""
        from app.ai.gateway import GeminiProvider
        provider = GeminiProvider()
        assert provider is not None
        assert hasattr(provider, "chat")
        assert hasattr(provider, "embed")

    def test_gemini_fallback_to_local_without_key(self, app):
        """Without GEMINI_API_KEY, gateway should fallback to local stub."""
        import os
        from app.ai.gateway import LLMGateway
        # Ensure no key is set
        original = os.environ.pop("GEMINI_API_KEY", None)
        try:
            gw = LLMGateway()
            provider, name = gw._get_provider("gemini-2.5-flash")
            assert name == "local"
        finally:
            if original:
                os.environ["GEMINI_API_KEY"] = original

    def test_gemini_default_chat_model(self, app):
        """Default chat model should be a Gemini model (or overridden via env)."""
        from app.ai.gateway import LLMGateway
        # Without LLM_DEFAULT_CHAT_MODEL env var, default is gemini-2.5-flash
        assert "gemini" in LLMGateway.DEFAULT_CHAT_MODEL or \
               LLMGateway.DEFAULT_CHAT_MODEL == "local-stub"  # CI may override

    def test_gemini_default_embed_model(self, app):
        """Default embed model should be gemini-embedding-001."""
        from app.ai.gateway import LLMGateway
        assert "gemini" in LLMGateway.DEFAULT_EMBED_MODEL or \
               LLMGateway.DEFAULT_EMBED_MODEL == "local-stub"

    def test_gemini_free_tier_zero_cost(self, app):
        """Gemini free-tier models must have zero cost."""
        assert calculate_cost("gemini-2.5-flash", 10000, 5000) == 0.0
        assert calculate_cost("gemini-2.5-pro", 10000, 5000) == 0.0
        assert calculate_cost("gemini-2.0-flash", 10000, 5000) == 0.0
        assert calculate_cost("gemini-embedding-001", 10000, 0) == 0.0

    def test_gemini_models_in_token_costs(self, app):
        """Gemini models must appear in TOKEN_COSTS dict."""
        assert "gemini-2.5-flash" in TOKEN_COSTS
        assert "gemini-2.5-pro" in TOKEN_COSTS
        assert "gemini-embedding-001" in TOKEN_COSTS


# ═════════════════════════════════════════════════════════════════════════════
# SUGGESTION QUEUE SERVICE
# ═════════════════════════════════════════════════════════════════════════════

class TestSuggestionQueue:
    """Test SuggestionQueue service directly."""

    def test_create(self, app):
        from app.ai.suggestion_queue import SuggestionQueue
        s = SuggestionQueue.create(
            entity_type="requirement", entity_id=1, title="Test suggestion",
            suggestion_type="general", confidence=0.7,
        )
        assert s.id is not None
        assert s.status == "pending"
        assert s.confidence == 0.7

    def test_approve(self, app):
        from app.ai.suggestion_queue import SuggestionQueue
        s = SuggestionQueue.create(
            entity_type="requirement", entity_id=1, title="S1",
        )
        approved = SuggestionQueue.approve(s.id, reviewer="admin", note="OK")
        assert approved is not None
        assert approved.status == "approved"

    def test_reject(self, app):
        from app.ai.suggestion_queue import SuggestionQueue
        s = SuggestionQueue.create(
            entity_type="defect", entity_id=5, title="Triage",
        )
        rejected = SuggestionQueue.reject(s.id, reviewer="pm", note="No")
        assert rejected is not None
        assert rejected.status == "rejected"

    def test_modify_and_approve(self, app):
        from app.ai.suggestion_queue import SuggestionQueue
        s = SuggestionQueue.create(
            entity_type="risk", entity_id=3, title="Risk assessment",
        )
        modified = SuggestionQueue.modify_and_approve(
            s.id, modified_data={"level": "high"}, reviewer="architect",
        )
        assert modified is not None
        assert modified.status == "modified"

    def test_list_suggestions(self, app):
        from app.ai.suggestion_queue import SuggestionQueue
        SuggestionQueue.create(entity_type="requirement", entity_id=1, title="S1")
        SuggestionQueue.create(entity_type="defect", entity_id=2, title="S2")
        result = SuggestionQueue.list_suggestions()
        assert result["total"] == 2
        assert len(result["items"]) == 2

    def test_list_filter_entity_type(self, app):
        from app.ai.suggestion_queue import SuggestionQueue
        SuggestionQueue.create(entity_type="requirement", entity_id=1, title="S1")
        SuggestionQueue.create(entity_type="defect", entity_id=2, title="S2")
        result = SuggestionQueue.list_suggestions(entity_type="defect")
        assert result["total"] == 1

    def test_pending_count(self, app):
        from app.ai.suggestion_queue import SuggestionQueue
        SuggestionQueue.create(entity_type="requirement", entity_id=1, title="S1")
        SuggestionQueue.create(entity_type="requirement", entity_id=2, title="S2")
        count = SuggestionQueue.get_pending_count()
        assert count == 2

    def test_stats(self, app):
        from app.ai.suggestion_queue import SuggestionQueue
        SuggestionQueue.create(entity_type="requirement", entity_id=1, title="S1")
        s2 = SuggestionQueue.create(entity_type="defect", entity_id=2, title="S2")
        SuggestionQueue.approve(s2.id)
        stats = SuggestionQueue.get_stats()
        assert stats["total"] == 2
        assert stats["by_status"]["pending"] == 1
        assert stats["by_status"]["approved"] == 1


# ═════════════════════════════════════════════════════════════════════════════
# PROMPT REGISTRY
# ═════════════════════════════════════════════════════════════════════════════

class TestPromptRegistry:
    """Test prompt template registry."""

    def test_create_registry(self, app):
        from app.ai.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        assert registry is not None

    def test_list_templates(self, app):
        from app.ai.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        templates = registry.list_templates()
        assert len(templates) >= 5  # At least 5 built-in defaults
        names = [t["name"] for t in templates]
        assert "system_base" in names
        assert "requirement_analyst" in names
        assert "defect_triage" in names
        assert "nl_query" in names
        assert "risk_assessment" in names

    def test_render_template(self, app):
        from app.ai.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        messages = registry.render(
            "requirement_analyst",
            requirement_title="GL Account Posting",
            module="FI",
            description="Post GL entries",
        )
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_render_with_variables(self, app):
        from app.ai.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        messages = registry.render(
            "system_base",
            project_name="SAP S/4HANA Migration",
        )
        # Should substitute variable in output
        assert any("SAP" in m.get("content", "") for m in messages)

    def test_get_template(self, app):
        from app.ai.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        tmpl = registry.get("requirement_analyst")
        assert tmpl is not None
        assert tmpl.name == "requirement_analyst"

    def test_get_nonexistent_template(self, app):
        from app.ai.prompt_registry import PromptRegistry
        registry = PromptRegistry()
        tmpl = registry.get("nonexistent_template_xyz")
        assert tmpl is None
