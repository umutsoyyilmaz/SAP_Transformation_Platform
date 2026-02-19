"""Tests for AI admin dashboard service and endpoint behavior."""

import pytest

from app.models import db
from app.models.ai import AIAuditLog, AIUsageLog
from app.services.ai_admin_service import get_admin_dashboard_stats


@pytest.fixture()
def usage_and_audit_data() -> None:
    """Seed minimal AI usage and audit data for admin stats assertions."""
    db.session.add_all(
        [
            AIUsageLog(
                provider="openai",
                model="gpt-4o-mini",
                total_tokens=120,
                cost_usd=0.03,
                latency_ms=350,
                success=True,
            ),
            AIUsageLog(
                provider="anthropic",
                model="claude-3-5-haiku",
                total_tokens=80,
                cost_usd=0.02,
                latency_ms=650,
                success=False,
                error_message="rate limited",
            ),
            AIAuditLog(
                action="llm_call",
                provider="openai",
                model="gpt-4o-mini",
                user="tester",
                prompt_summary="test prompt",
                tokens_used=120,
                cost_usd=0.03,
                latency_ms=350,
                success=True,
            ),
        ]
    )
    db.session.commit()


def test_get_admin_dashboard_stats_returns_expected_keys(usage_and_audit_data) -> None:
    """Service should return the expected top-level dashboard sections."""
    stats = get_admin_dashboard_stats(tenant_id=1, program_id=1)

    assert set(stats.keys()) == {"usage", "suggestions", "embeddings", "recent_activity"}


def test_get_admin_dashboard_stats_usage_contains_required_fields(usage_and_audit_data) -> None:
    """Usage payload should include required aggregate metrics and provider split."""
    usage = get_admin_dashboard_stats(tenant_id=1, program_id=1)["usage"]

    required_fields = {
        "total_calls",
        "total_tokens",
        "total_cost_usd",
        "avg_latency_ms",
        "error_count",
        "error_rate",
        "by_provider",
    }
    assert required_fields.issubset(set(usage.keys()))
    assert usage["total_calls"] == 2
    assert usage["total_tokens"] == 200
    assert usage["error_count"] == 1
    assert "openai" in usage["by_provider"]


def test_admin_dashboard_endpoint_returns_401_without_permission(client, monkeypatch) -> None:
    """Endpoint should reject unauthenticated requests when API auth is enabled."""
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "admin-key:admin")

    response = client.get("/api/v1/ai/admin/dashboard")

    assert response.status_code == 401


def test_admin_dashboard_endpoint_returns_200_with_admin_permission(
    client,
    usage_and_audit_data,
    monkeypatch,
) -> None:
    """Endpoint should return stats for authenticated admin API key requests."""
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "admin-key:admin")

    response = client.get(
        "/api/v1/ai/admin/dashboard",
        headers={"X-API-Key": "admin-key"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "usage" in payload
    assert "recent_activity" in payload
