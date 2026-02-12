"""
Sprint 20 – AI Performance & Polish Tests.

Covers:
    - ResponseCacheService (two-tier cache, TTL, stats, memory eviction)
    - ModelSelector (purpose routing, fallback chain, availability)
    - TokenBudgetService (CRUD, check, record, exceed, auto-reset)
    - LLMGateway S20 integration (cache hit/miss, budget enforcement, fallback)
    - Blueprint endpoints (performance dashboard, by-assistant, cache, budgets)
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

from app.models import db
from app.models.ai import (
    AIResponseCache, AITokenBudget, AIUsageLog, AIAuditLog,
    MODEL_TIERS, PURPOSE_MODEL_MAP, BUDGET_PERIODS,
)


# ═══════════════════════════════════════════════════════════════════════════
#  1. MODEL CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════


class TestAIConstants:
    """Verify S20 model-tier and budget-period constants."""

    def test_model_tiers_has_three_tiers(self):
        assert set(MODEL_TIERS.keys()) == {"fast", "balanced", "strong"}

    def test_each_tier_has_models(self):
        for tier, models in MODEL_TIERS.items():
            assert len(models) >= 2, f"Tier '{tier}' has too few models"

    def test_purpose_model_map_covers_assistants(self):
        expected = {
            "nl_query", "requirement_analyst", "defect_triage",
            "risk_assessment", "test_case_generator", "change_impact",
        }
        assert expected.issubset(set(PURPOSE_MODEL_MAP.keys()))

    def test_budget_periods(self):
        assert BUDGET_PERIODS == {"daily", "monthly"}


# ═══════════════════════════════════════════════════════════════════════════
#  2. RESPONSE CACHE SERVICE
# ═══════════════════════════════════════════════════════════════════════════


class TestResponseCacheService:
    """Two-tier LLM response cache tests."""

    def _svc(self):
        from app.ai.cache import ResponseCacheService
        return ResponseCacheService(ttl_seconds=10)

    def test_compute_hash_deterministic(self):
        svc = self._svc()
        msgs = [{"role": "user", "content": "hello"}]
        h1 = svc.compute_hash(msgs, "model-a")
        h2 = svc.compute_hash(msgs, "model-a")
        assert h1 == h2

    def test_compute_hash_varies_with_model(self):
        svc = self._svc()
        msgs = [{"role": "user", "content": "hello"}]
        h1 = svc.compute_hash(msgs, "model-a")
        h2 = svc.compute_hash(msgs, "model-b")
        assert h1 != h2

    def test_set_and_get(self):
        svc = self._svc()
        ph = svc.compute_hash([{"role": "user", "content": "test"}], "m")
        svc.set(ph, {"content": "response text"}, "m", "test", 10, 5)
        cached = svc.get(ph)
        assert cached is not None
        assert cached["content"] == "response text"

    def test_cache_miss(self):
        svc = self._svc()
        assert svc.get("nonexistent_hash") is None

    def test_should_cache_skips_conversation(self):
        svc = self._svc()
        assert svc.should_cache("requirement_analyst") is True
        assert svc.should_cache("conversation") is False
        assert svc.should_cache("conversation_general") is False

    def test_invalidate_specific(self):
        svc = self._svc()
        ph = "hash_to_invalidate"
        svc.set(ph, {"text": "resp"}, "m", "test", 10, 5)
        assert svc.get(ph) is not None
        svc.invalidate(prompt_hash=ph)
        assert svc.get(ph) is None

    def test_invalidate_all(self):
        svc = self._svc()
        svc.set("h1", {"t": "r1"}, "m", "test", 10, 5)
        svc.set("h2", {"t": "r2"}, "m", "test", 10, 5)
        svc.invalidate()  # all
        assert svc.get("h1") is None
        assert svc.get("h2") is None

    def test_get_stats(self):
        svc = self._svc()
        ph = svc.compute_hash([{"role": "user", "content": "x"}], "m")
        svc.set(ph, {"text": "resp"}, "m", "test", 10, 5)
        svc.get(ph)  # hit
        svc.get("missing")  # miss
        stats = svc.get_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["sets"] >= 1
        assert "hit_rate_pct" in stats

    def test_memory_limit_eviction(self):
        from app.ai.cache import ResponseCacheService, MAX_MEMORY_ENTRIES
        svc = ResponseCacheService(ttl_seconds=60)
        # Fill beyond limit
        for i in range(MAX_MEMORY_ENTRIES + 10):
            svc.set(f"hash_{i}", {"i": i}, "m", "test", 1, 1)
        stats = svc.get_stats()
        assert stats["memory_entries"] <= MAX_MEMORY_ENTRIES

    def test_cleanup_expired(self):
        svc = self._svc()
        # Insert an already-expired DB entry
        expired = AIResponseCache(
            prompt_hash="expired_hash",
            model="m",
            purpose="test",
            response_json='{"text":"old"}',
            prompt_tokens=1,
            completion_tokens=1,
            hit_count=0,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.session.add(expired)
        db.session.flush()
        assert AIResponseCache.query.filter_by(prompt_hash="expired_hash").first() is not None
        svc.cleanup_expired()
        assert AIResponseCache.query.filter_by(prompt_hash="expired_hash").first() is None


# ═══════════════════════════════════════════════════════════════════════════
#  3. MODEL SELECTOR
# ═══════════════════════════════════════════════════════════════════════════


class TestModelSelector:
    """Smart model routing tests."""

    def _svc(self, providers=None):
        from app.ai.model_selector import ModelSelector
        return ModelSelector(available_providers=providers or {"local", "gemini"})

    def test_select_by_purpose(self):
        sel = self._svc({"local", "gemini"})
        model = sel.select(purpose="nl_query")
        assert model is not None

    def test_select_explicit_model_takes_precedence(self):
        sel = self._svc()
        result = sel.select(purpose="nl_query", explicit_model="gpt-4o")
        assert result == "gpt-4o"

    def test_select_default_fallback(self):
        sel = self._svc({"local"})  # only local available
        result = sel.select(purpose="unknown_purpose", default_model="local-stub")
        # balanced tier models: gemini-2.5-flash, gpt-4o, claude-3-5-sonnet; none available except local
        # So it falls through to default
        assert result is not None

    def test_fallback_chain_includes_local_stub(self):
        sel = self._svc({"local"})
        chain = sel.get_fallback_chain("gemini-2.5-flash")
        assert "local-stub" in chain

    def test_fallback_chain_is_list(self):
        sel = self._svc({"local", "gemini"})
        chain = sel.get_fallback_chain("gemini-2.5-flash")
        assert isinstance(chain, list)

    def test_model_to_provider_mapping(self):
        sel = self._svc()
        assert sel._model_to_provider("gemini-2.5-flash") == "gemini"
        assert sel._model_to_provider("gpt-4o") == "openai"
        assert sel._model_to_provider("claude-3-5-haiku-20241022") == "anthropic"
        assert sel._model_to_provider("local-stub") == "local"


# ═══════════════════════════════════════════════════════════════════════════
#  4. TOKEN BUDGET SERVICE
# ═══════════════════════════════════════════════════════════════════════════


class TestTokenBudgetService:
    """Token/cost budget enforcement tests."""

    def _svc(self):
        from app.ai.budget import TokenBudgetService
        return TokenBudgetService()

    def test_no_budget_allows_all(self):
        svc = self._svc()
        result = svc.check_budget(program_id=9999, user="nobody")
        assert result["allowed"] is True

    def test_create_budget(self):
        svc = self._svc()
        budget = svc.create_or_update(
            user="tester",
            period="daily", token_limit=500_000, cost_limit_usd=5.0,
        )
        db.session.commit()
        assert budget.id is not None
        assert budget.token_limit == 500_000

    def test_check_within_budget(self):
        svc = self._svc()
        svc.create_or_update(user="u_within", period="daily", token_limit=1_000_000)
        db.session.commit()
        result = svc.check_budget(user="u_within")
        assert result["allowed"] is True

    def test_record_usage(self):
        svc = self._svc()
        svc.create_or_update(user="u_usage", period="daily", token_limit=1_000_000)
        db.session.commit()
        svc.record_usage(program_id=None, user="u_usage", tokens=5000, cost_usd=0.05)
        db.session.commit()
        budget = svc.get_budget(user="u_usage")
        assert budget.tokens_used == 5000
        assert budget.request_count == 1

    def test_exceed_budget(self):
        svc = self._svc()
        svc.create_or_update(
            user="u_exceed", period="daily",
            token_limit=100, cost_limit_usd=0.001,
        )
        db.session.commit()
        svc.record_usage(program_id=None, user="u_exceed", tokens=200, cost_usd=0.01)
        db.session.commit()
        result = svc.check_budget(user="u_exceed")
        assert result["allowed"] is False
        assert "exceeded" in result["reason"].lower()

    def test_reset_budget(self):
        svc = self._svc()
        budget = svc.create_or_update(user="u_reset", period="daily", token_limit=1000)
        db.session.commit()
        svc.record_usage(program_id=None, user="u_reset", tokens=500, cost_usd=0.01)
        db.session.commit()
        reset = svc.reset_budget(budget.id)
        db.session.commit()
        assert reset.tokens_used == 0
        assert reset.request_count == 0

    def test_list_budgets(self):
        svc = self._svc()
        svc.create_or_update(user="u_list1", period="daily")
        svc.create_or_update(user="u_list2", period="monthly")
        db.session.commit()
        budgets = svc.list_budgets()
        assert len(budgets) >= 2

    def test_delete_budget(self):
        svc = self._svc()
        budget = svc.create_or_update(user="u_del", period="daily")
        db.session.commit()
        bid = budget.id
        assert svc.delete_budget(bid) is True
        db.session.commit()
        assert svc.delete_budget(bid) is False

    def test_auto_reset_expired_period(self):
        svc = self._svc()
        budget = svc.create_or_update(user="u_autoreset", period="daily", token_limit=1000)
        db.session.commit()
        svc.record_usage(program_id=None, user="u_autoreset", tokens=500, cost_usd=0.01)
        db.session.commit()
        # Force reset_at into the past
        budget.reset_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.session.commit()
        # Next access should auto-reset
        result = svc.check_budget(user="u_autoreset")
        assert result["allowed"] is True
        fresh = svc.get_budget(user="u_autoreset")
        assert fresh.tokens_used == 0

    def test_compute_reset_at_daily(self):
        svc = self._svc()
        now = datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc)
        reset = svc._compute_reset_at("daily", now)
        assert reset.day == 16
        assert reset.hour == 0

    def test_compute_reset_at_monthly(self):
        svc = self._svc()
        now = datetime(2025, 6, 15, 10, 30, tzinfo=timezone.utc)
        reset = svc._compute_reset_at("monthly", now)
        assert reset.month == 7
        assert reset.day == 1

    def test_compute_reset_at_december(self):
        svc = self._svc()
        now = datetime(2025, 12, 15, 10, 30, tzinfo=timezone.utc)
        reset = svc._compute_reset_at("monthly", now)
        assert reset.year == 2026
        assert reset.month == 1


# ═══════════════════════════════════════════════════════════════════════════
#  5. AI RESPONSE CACHE MODEL
# ═══════════════════════════════════════════════════════════════════════════


class TestAIResponseCacheModel:
    """ORM model tests."""

    def test_create_and_query(self):
        entry = AIResponseCache(
            prompt_hash="test_hash_model",
            model="gemini-2.5-flash",
            purpose="test",
            response_json='{"text":"hello"}',
            prompt_tokens=10,
            completion_tokens=5,
            hit_count=0,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        db.session.add(entry)
        db.session.flush()
        assert entry.id is not None
        found = AIResponseCache.query.filter_by(prompt_hash="test_hash_model").first()
        assert found is not None

    def test_is_expired(self):
        entry = AIResponseCache(
            prompt_hash="exp_test",
            model="m",
            purpose="t",
            response_json="{}",
            prompt_tokens=0,
            completion_tokens=0,
            hit_count=0,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert entry.is_expired() is True

    def test_to_dict(self):
        entry = AIResponseCache(
            prompt_hash="dict_test",
            model="m",
            purpose="t",
            response_json='{"key":"val"}',
            prompt_tokens=10,
            completion_tokens=5,
            hit_count=3,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        d = entry.to_dict()
        assert d["prompt_hash"] == "dict_test"
        assert d["hit_count"] == 3


# ═══════════════════════════════════════════════════════════════════════════
#  6. AI TOKEN BUDGET MODEL
# ═══════════════════════════════════════════════════════════════════════════


class TestAITokenBudgetModel:
    """ORM model tests."""

    def test_create_and_query(self):
        budget = AITokenBudget(
            program_id=None,
            user="model_test",
            period="daily",
            token_limit=500_000,
            cost_limit_usd=5.0,
            tokens_used=0,
            cost_used_usd=0.0,
            request_count=0,
            period_start=datetime.now(timezone.utc),
            reset_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        db.session.add(budget)
        db.session.flush()
        assert budget.id is not None

    def test_is_exceeded_tokens(self):
        budget = AITokenBudget(
            period="daily", token_limit=100,
            cost_limit_usd=100.0,
            tokens_used=150,
            cost_used_usd=0.0,
        )
        assert budget.is_exceeded() is True

    def test_is_exceeded_cost(self):
        budget = AITokenBudget(
            period="daily", token_limit=1_000_000,
            cost_limit_usd=1.0,
            tokens_used=100,
            cost_used_usd=2.0,
        )
        assert budget.is_exceeded() is True

    def test_remaining_tokens(self):
        budget = AITokenBudget(
            period="daily", token_limit=1000,
            tokens_used=300,
        )
        assert budget.remaining_tokens() == 700

    def test_remaining_cost(self):
        budget = AITokenBudget(
            period="daily", cost_limit_usd=10.0,
            cost_used_usd=3.5,
        )
        assert budget.remaining_cost() == pytest.approx(6.5)

    def test_to_dict(self):
        budget = AITokenBudget(
            program_id=None,
            user="dict_test",
            period="monthly",
            token_limit=1_000_000,
            cost_limit_usd=50.0,
            tokens_used=100_000,
            cost_used_usd=5.0,
            request_count=42,
            period_start=datetime.now(timezone.utc),
            reset_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        d = budget.to_dict()
        assert d["period"] == "monthly"
        assert d["remaining_tokens"] == 900_000


# ═══════════════════════════════════════════════════════════════════════════
#  7. USAGE / AUDIT LOG S20 FIELDS
# ═══════════════════════════════════════════════════════════════════════════


class TestUsageAuditS20Fields:
    """Verify new cache_hit and fallback fields on log models."""

    def test_usage_log_cache_hit_field(self):
        log = AIUsageLog(
            provider="cache", model="m", purpose="test",
            prompt_tokens=0, completion_tokens=0, total_tokens=0,
            cost_usd=0.0, latency_ms=0, success=True,
            cache_hit=True, fallback_provider="local",
        )
        db.session.add(log)
        db.session.flush()
        d = log.to_dict()
        assert d["cache_hit"] is True
        assert d["fallback_provider"] == "local"

    def test_audit_log_fallback_field(self):
        log = AIAuditLog(
            action="llm_call", provider="gemini", model="gemini-2.5-flash",
            user="tester", prompt_hash="abc", tokens_used=100,
            cost_usd=0.001, latency_ms=200, success=True,
            cache_hit=False, fallback_used=True,
        )
        db.session.add(log)
        db.session.flush()
        d = log.to_dict()
        assert d["cache_hit"] is False
        assert d["fallback_used"] is True


# ═══════════════════════════════════════════════════════════════════════════
#  8. GATEWAY S20 INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════


class TestGatewayS20:
    """LLMGateway cache / budget / fallback integration tests."""

    def _gw(self):
        from app.ai.gateway import LLMGateway
        gw = LLMGateway()
        return gw

    def test_gateway_has_perf_services(self):
        gw = self._gw()
        assert gw._cache is not None
        assert gw._model_selector is not None
        assert gw._budget_service is not None

    def test_chat_returns_cache_hit_field(self):
        gw = self._gw()
        result = gw.chat(
            [{"role": "user", "content": "hello s20"}],
            model="local-stub",
            purpose="test",
        )
        assert "cache_hit" in result
        assert "fallback_provider" in result

    def test_cache_hit_on_second_call(self):
        gw = self._gw()
        msgs = [{"role": "user", "content": "cacheable query s20"}]
        r1 = gw.chat(msgs, model="local-stub", purpose="test")
        assert r1["cache_hit"] is False
        r2 = gw.chat(msgs, model="local-stub", purpose="test")
        assert r2["cache_hit"] is True
        assert r2["provider"] == "cache"

    def test_skip_cache_flag(self):
        gw = self._gw()
        msgs = [{"role": "user", "content": "no-cache query"}]
        gw.chat(msgs, model="local-stub", purpose="test")
        r2 = gw.chat(msgs, model="local-stub", purpose="test", skip_cache=True)
        assert r2["cache_hit"] is False

    def test_conversation_purpose_not_cached(self):
        gw = self._gw()
        msgs = [{"role": "user", "content": "conv message"}]
        gw.chat(msgs, model="local-stub", purpose="conversation")
        r2 = gw.chat(msgs, model="local-stub", purpose="conversation")
        assert r2["cache_hit"] is False

    def test_budget_enforcement(self):
        gw = self._gw()
        svc = gw._budget_service
        svc.create_or_update(
            user="budget_block", period="daily",
            token_limit=1, cost_limit_usd=0.0001,
        )
        db.session.commit()
        svc.record_usage(program_id=None, user="budget_block", tokens=100, cost_usd=1.0)
        db.session.commit()
        with pytest.raises(RuntimeError, match="Budget exceeded"):
            gw.chat(
                [{"role": "user", "content": "blocked"}],
                model="local-stub",
                purpose="test",
                user="budget_block",
                skip_cache=True,
            )

    def test_skip_budget_flag(self):
        gw = self._gw()
        svc = gw._budget_service
        svc.create_or_update(
            user="budget_skip", period="daily",
            token_limit=1, cost_limit_usd=0.0001,
        )
        db.session.commit()
        svc.record_usage(program_id=None, user="budget_skip", tokens=100, cost_usd=1.0)
        db.session.commit()
        # Should NOT raise when skip_budget=True
        result = gw.chat(
            [{"role": "user", "content": "allowed by skip"}],
            model="local-stub",
            purpose="test",
            user="budget_skip",
            skip_cache=True,
            skip_budget=True,
        )
        assert result["content"]

    def test_model_selector_routes_purpose(self):
        gw = self._gw()
        # The model selector should pick a model even without explicit model
        result = gw.chat(
            [{"role": "user", "content": "selector test"}],
            purpose="requirement_analyst",
            skip_cache=True,
        )
        assert result["model"] is not None


# ═══════════════════════════════════════════════════════════════════════════
#  9. BLUEPRINT ENDPOINTS (S20)
# ═══════════════════════════════════════════════════════════════════════════


class TestPerformanceEndpoints:
    """Performance dashboard and by-assistant endpoints."""

    def test_dashboard_empty(self, client):
        resp = client.get("/api/v1/ai/performance/dashboard")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_requests"] == 0

    def test_dashboard_with_data(self, client):
        # Insert a usage log
        log = AIUsageLog(
            provider="local", model="local-stub", purpose="test",
            prompt_tokens=10, completion_tokens=5, total_tokens=15,
            cost_usd=0.001, latency_ms=50, success=True,
        )
        db.session.add(log)
        db.session.commit()
        resp = client.get("/api/v1/ai/performance/dashboard")
        data = resp.get_json()
        assert data["total_requests"] >= 1
        assert "by_model" in data
        assert "by_purpose" in data

    def test_dashboard_days_filter(self, client):
        resp = client.get("/api/v1/ai/performance/dashboard?days=1")
        assert resp.status_code == 200

    def test_by_assistant_empty(self, client):
        resp = client.get("/api/v1/ai/performance/by-assistant")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["assistants"] == {}

    def test_by_assistant_with_data(self, client):
        log = AIUsageLog(
            provider="local", model="local-stub", purpose="requirement_analyst",
            prompt_tokens=100, completion_tokens=50, total_tokens=150,
            cost_usd=0.01, latency_ms=200, success=True,
        )
        db.session.add(log)
        db.session.commit()
        resp = client.get("/api/v1/ai/performance/by-assistant")
        data = resp.get_json()
        assert "requirement_analyst" in data["assistants"]
        a = data["assistants"]["requirement_analyst"]
        assert a["requests"] >= 1
        assert "avg_latency_ms" in a
        assert "p95_latency_ms" in a
        assert "cache_hit_rate_pct" in a


class TestCacheEndpoints:
    """Cache stats and clear endpoints."""

    def test_cache_stats(self, client):
        resp = client.get("/api/v1/ai/cache/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        # Should have stats or enabled:False
        assert isinstance(data, dict)

    def test_cache_clear(self, client):
        resp = client.post("/api/v1/ai/cache/clear")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "cleared" in data


class TestBudgetEndpoints:
    """Token budget CRUD endpoints."""

    def test_list_budgets_empty(self, client):
        resp = client.get("/api/v1/ai/budgets")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_create_budget(self, client):
        resp = client.post(
            "/api/v1/ai/budgets",
            json={
                "user": "ep_create",
                "period": "daily",
                "token_limit": 500_000,
                "cost_limit_usd": 5.0,
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["token_limit"] == 500_000

    def test_list_budgets_after_create(self, client):
        client.post(
            "/api/v1/ai/budgets",
            json={"user": "ep_list", "period": "monthly"},
        )
        resp = client.get("/api/v1/ai/budgets")
        assert len(resp.get_json()) >= 1

    def test_delete_budget(self, client):
        resp = client.post(
            "/api/v1/ai/budgets",
            json={"user": "ep_del", "period": "daily"},
        )
        bid = resp.get_json()["id"]
        resp2 = client.delete(f"/api/v1/ai/budgets/{bid}")
        assert resp2.status_code == 200
        assert resp2.get_json()["deleted"] is True

    def test_delete_budget_not_found(self, client):
        resp = client.delete("/api/v1/ai/budgets/99999")
        assert resp.status_code == 404

    def test_reset_budget_endpoint(self, client):
        resp = client.post(
            "/api/v1/ai/budgets",
            json={"user": "ep_reset", "period": "daily", "token_limit": 1000},
        )
        bid = resp.get_json()["id"]
        resp2 = client.post(f"/api/v1/ai/budgets/{bid}/reset")
        assert resp2.status_code == 200
        assert resp2.get_json()["tokens_used"] == 0

    def test_reset_budget_not_found(self, client):
        resp = client.post("/api/v1/ai/budgets/99999/reset")
        assert resp.status_code == 404

    def test_budget_status_no_budget(self, client):
        resp = client.get("/api/v1/ai/budgets/status?program_id=99999")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["allowed"] is True

    def test_budget_status_with_budget(self, client):
        client.post(
            "/api/v1/ai/budgets",
            json={"user": "ep_status", "period": "daily", "token_limit": 1_000_000},
        )
        resp = client.get("/api/v1/ai/budgets/status?user=ep_status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["allowed"] is True
