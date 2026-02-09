"""Tests for monitoring: health checks, metrics, and request timing."""

import pytest
from app import create_app
from app.models import db
from app.middleware.timing import reset_metrics


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    reset_metrics()
    return app.test_client()


# ── Health Endpoints ────────────────────────────────────────────────────


class TestHealthEndpoints:
    """Health check endpoint tests."""

    def test_health_basic(self, client):
        """GET /api/v1/health returns 200."""
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"

    def test_health_ready(self, client):
        """GET /api/v1/health/ready returns 200."""
        res = client.get("/api/v1/health/ready")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"

    def test_health_live(self, client):
        """GET /api/v1/health/live returns detailed checks."""
        res = client.get("/api/v1/health/live")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert "database" in data["checks"]
        assert data["checks"]["database"]["status"] == "ok"
        assert "latency_ms" in data["checks"]["database"]
        assert "app" in data["checks"]

    def test_health_live_has_pgvector_info(self, client):
        """Live health check includes pgvector status."""
        res = client.get("/api/v1/health/live")
        data = res.get_json()
        # SQLite test DB won't have pgvector, but field should exist
        assert "pgvector" in data["checks"]

    def test_health_no_auth_required(self, client):
        """Health endpoints don't require API key."""
        for path in ["/api/v1/health", "/api/v1/health/ready", "/api/v1/health/live"]:
            res = client.get(path)
            assert res.status_code == 200, f"Auth required for {path}"


# ── Request Timing ──────────────────────────────────────────────────────


class TestRequestTiming:
    """Request timing middleware tests."""

    def test_duration_header_present(self, client):
        """Every response should have X-Request-Duration-Ms header."""
        res = client.get("/api/v1/health")
        assert "X-Request-Duration-Ms" in res.headers
        duration = float(res.headers["X-Request-Duration-Ms"])
        assert duration >= 0

    def test_request_id_header(self, client):
        """Responses should have X-Request-ID header."""
        res = client.get("/api/v1/health")
        assert "X-Request-ID" in res.headers
        assert len(res.headers["X-Request-ID"]) > 0

    def test_custom_request_id_passthrough(self, client):
        """Client-provided X-Request-ID should be preserved."""
        res = client.get("/api/v1/health", headers={"X-Request-ID": "test-123"})
        assert res.headers["X-Request-ID"] == "test-123"


# ── Metrics Endpoints ──────────────────────────────────────────────────


class TestMetricsEndpoints:
    """Metrics API tests."""

    def test_metrics_requests_empty(self, client):
        """Metrics endpoint returns valid structure when no data."""
        res = client.get("/api/v1/metrics/requests")
        assert res.status_code == 200
        data = res.get_json()
        assert "total_requests" in data
        assert "avg_latency_ms" in data

    def test_metrics_after_requests(self, client):
        """Metrics should include recent requests."""
        # Make some requests first
        for _ in range(5):
            client.get("/api/v1/health")
        res = client.get("/api/v1/metrics/requests")
        data = res.get_json()
        # At least the 5 health requests + possibly the metrics request itself
        assert data["total_requests"] >= 5

    def test_metrics_errors(self, client):
        """Error distribution endpoint works."""
        # Generate a 404
        client.get("/api/v1/nonexistent")
        res = client.get("/api/v1/metrics/errors")
        assert res.status_code == 200
        data = res.get_json()
        assert "total_errors" in data
        assert "error_rate" in data
        assert "by_status" in data

    def test_metrics_slow(self, client):
        """Slow endpoints endpoint works."""
        res = client.get("/api/v1/metrics/slow")
        assert res.status_code == 200
        data = res.get_json()
        assert "endpoints" in data
        assert "threshold_ms" in data

    def test_metrics_custom_window(self, client):
        """Metrics accept custom window parameter."""
        res = client.get("/api/v1/metrics/requests?window=60")
        assert res.status_code == 200
        data = res.get_json()
        assert data["window_seconds"] == 60

    def test_metrics_ai_usage(self, client):
        """AI usage metrics endpoint returns valid structure."""
        res = client.get("/api/v1/metrics/ai/usage")
        assert res.status_code == 200
        data = res.get_json()
        assert "today" in data
        assert "by_provider" in data
        assert "trend_7d" in data
        assert "request_count" in data["today"]
        assert "prompt_tokens" in data["today"]
        assert "total_cost_usd" in data["today"]

    def test_metrics_no_auth_required(self, client):
        """Metrics endpoints don't require API key."""
        for path in [
            "/api/v1/metrics/requests",
            "/api/v1/metrics/errors",
            "/api/v1/metrics/slow",
            "/api/v1/metrics/ai/usage",
        ]:
            res = client.get(path)
            assert res.status_code == 200, f"Auth required for {path}"
