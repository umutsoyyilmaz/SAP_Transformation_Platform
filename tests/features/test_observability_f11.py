"""F11 — Technical Infrastructure & Observability tests."""

import pytest

from app.models.observability import CacheStat, HealthCheckResult, TaskStatus


# Uses shared fixtures from conftest.py: client, session (autouse rollback)


# ═════════════════════════════════════════════════════════════════
# 1. Async Task Management
# ═════════════════════════════════════════════════════════════════
class TestAsyncTasks:
    def _create_task(self, client, **kwargs):
        payload = {"task_type": "automation_import"}
        payload.update(kwargs)
        return client.post("/api/v1/tasks", json=payload)

    def test_create_task(self, client):
        r = self._create_task(client)
        assert r.status_code == 201
        d = r.get_json()
        assert d["status"] == "pending"
        assert d["task_type"] == "automation_import"
        assert d["progress"] == 0

    def test_get_task(self, client):
        cr = self._create_task(client)
        tid = cr.get_json()["task_id"]
        r = client.get(f"/api/v1/tasks/{tid}")
        assert r.status_code == 200
        assert r.get_json()["task_id"] == tid

    def test_get_task_404(self, client):
        r = client.get("/api/v1/tasks/nonexistent")
        assert r.status_code == 404

    def test_list_tasks(self, client):
        self._create_task(client, task_type="pdf_report")
        self._create_task(client, task_type="automation_import")
        r = client.get("/api/v1/tasks")
        assert r.get_json()["total"] == 2

    def test_list_tasks_filter_type(self, client):
        self._create_task(client, task_type="pdf_report")
        self._create_task(client, task_type="automation_import")
        r = client.get("/api/v1/tasks?type=pdf_report")
        assert r.get_json()["total"] == 1

    def test_list_tasks_filter_status(self, client):
        self._create_task(client)
        r = client.get("/api/v1/tasks?status=pending")
        assert r.get_json()["total"] == 1
        r2 = client.get("/api/v1/tasks?status=running")
        assert r2.get_json()["total"] == 0

    def test_update_task_to_running(self, client):
        cr = self._create_task(client)
        tid = cr.get_json()["task_id"]
        r = client.put(
            f"/api/v1/tasks/{tid}",
            json={"status": "running", "progress": 25},
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] == "running"
        assert d["progress"] == 25
        assert d["started_at"] is not None

    def test_update_task_to_completed(self, client):
        cr = self._create_task(client)
        tid = cr.get_json()["task_id"]
        client.put(f"/api/v1/tasks/{tid}", json={"status": "running"})
        r = client.put(
            f"/api/v1/tasks/{tid}",
            json={"status": "completed", "progress": 100, "result": {"count": 42}},
        )
        d = r.get_json()
        assert d["status"] == "completed"
        assert d["progress"] == 100
        assert d["result"]["count"] == 42
        assert d["completed_at"] is not None

    def test_update_task_to_failed(self, client):
        cr = self._create_task(client)
        tid = cr.get_json()["task_id"]
        r = client.put(
            f"/api/v1/tasks/{tid}",
            json={"status": "failed", "error_message": "Parse error"},
        )
        assert r.get_json()["status"] == "failed"
        assert "Parse error" in r.get_json()["error_message"]

    def test_update_task_invalid_status(self, client):
        cr = self._create_task(client)
        tid = cr.get_json()["task_id"]
        r = client.put(f"/api/v1/tasks/{tid}", json={"status": "invalid"})
        assert r.status_code == 400

    def test_update_task_404(self, client):
        r = client.put("/api/v1/tasks/no-such-task", json={"status": "running"})
        assert r.status_code == 404


# ═════════════════════════════════════════════════════════════════
# 2. Cache Management
# ═════════════════════════════════════════════════════════════════
class TestCacheManagement:
    def test_get_cache_tiers(self, client):
        r = client.get("/api/v1/cache/tiers")
        assert r.status_code == 200
        tiers = r.get_json()["tiers"]
        assert "dashboard" in tiers
        assert "api_response" in tiers

    def test_get_cache_stats_empty(self, client):
        r = client.get("/api/v1/cache/stats")
        assert r.status_code == 200
        assert r.get_json()["stats"] == {}

    def test_record_cache_hit(self, client):
        r = client.post(
            "/api/v1/cache/record",
            json={"tier": "dashboard", "key": "dash:1", "hit": True},
        )
        assert r.status_code == 201
        assert r.get_json()["hit"] == 1

    def test_record_cache_miss(self, client):
        r = client.post(
            "/api/v1/cache/record",
            json={"tier": "dashboard", "key": "dash:2", "hit": False},
        )
        assert r.status_code == 201
        assert r.get_json()["miss"] == 1

    def test_cache_stats_aggregation(self, client):
        client.post(
            "/api/v1/cache/record",
            json={"tier": "dashboard", "key": "a", "hit": True},
        )
        client.post(
            "/api/v1/cache/record",
            json={"tier": "dashboard", "key": "b", "hit": False},
        )
        r = client.get("/api/v1/cache/stats")
        stats = r.get_json()["stats"]
        assert "dashboard" in stats
        assert stats["dashboard"]["hit"] == 1
        assert stats["dashboard"]["miss"] == 1
        assert stats["dashboard"]["hit_rate"] == 50.0

    def test_invalidate_cache(self, client):
        r = client.post(
            "/api/v1/cache/invalidate",
            json={"tier": "dashboard", "key": "some:key"},
        )
        assert r.status_code == 200
        assert r.get_json()["invalidated"] is True

    def test_invalidate_cache_missing_params(self, client):
        r = client.post("/api/v1/cache/invalidate", json={})
        assert r.status_code == 400


# ═════════════════════════════════════════════════════════════════
# 3. Health Checks
# ═════════════════════════════════════════════════════════════════
class TestHealthChecks:
    def test_health_detailed(self, client):
        r = client.get("/api/v1/health/detailed")
        assert r.status_code == 200
        d = r.get_json()
        assert d["status"] == "healthy"
        assert "database" in d["components"]
        assert "redis" in d["components"]
        assert "celery" in d["components"]
        assert "storage" in d["components"]

    def test_database_health_response_time(self, client):
        r = client.get("/api/v1/health/detailed")
        db_health = r.get_json()["components"]["database"]
        assert db_health["status"] == "healthy"
        assert "response_time_ms" in db_health

    def test_run_health_check(self, client):
        r = client.post("/api/v1/health/check")
        assert r.status_code == 201
        results = r.get_json()["results"]
        assert len(results) == 4
        assert all(res["status"] == "healthy" for res in results)

    def test_health_history(self, client):
        client.post("/api/v1/health/check")
        r = client.get("/api/v1/health/history")
        assert r.status_code == 200
        assert len(r.get_json()["items"]) == 4

    def test_health_history_filter_component(self, client):
        client.post("/api/v1/health/check")
        r = client.get("/api/v1/health/history?component=database")
        items = r.get_json()["items"]
        assert len(items) == 1
        assert items[0]["component"] == "database"


# ═════════════════════════════════════════════════════════════════
# 4. Metrics
# ═════════════════════════════════════════════════════════════════
class TestMetrics:
    def test_metrics_summary(self, client):
        r = client.get("/api/v1/metrics/summary")
        assert r.status_code == 200
        d = r.get_json()
        assert "tasks" in d
        assert "cache" in d
        assert "health" in d
        assert "rate_limits" in d

    def test_metrics_with_data(self, client):
        """Task counts should reflect newly created tasks."""
        client.post("/api/v1/tasks", json={"task_type": "test"})
        client.post("/api/v1/tasks", json={"task_type": "test2"})
        r = client.get("/api/v1/metrics/summary")
        assert r.get_json()["tasks"]["pending"] == 2

    def test_rate_limit_status(self, client):
        r = client.get("/api/v1/rate-limit/status")
        assert r.status_code == 200
        tiers = r.get_json()["tiers"]
        assert "ui" in tiers
        assert "ai" in tiers
        assert "bulk" in tiers


# ═════════════════════════════════════════════════════════════════
# 5. Model Integrity
# ═════════════════════════════════════════════════════════════════
class TestModelIntegrity:
    def test_task_status_to_dict(self, client):
        r = client.post("/api/v1/tasks", json={"task_type": "test"})
        d = r.get_json()
        assert "task_id" in d
        assert "status" in d
        assert "created_at" in d

    def test_cache_stat_to_dict(self, client):
        r = client.post(
            "/api/v1/cache/record",
            json={"tier": "test", "key": "k1", "hit": True},
        )
        d = r.get_json()
        assert "tier" in d
        assert "hit" in d
        assert "miss" in d

    def test_health_check_result_to_dict(self, client):
        r = client.post("/api/v1/health/check")
        results = r.get_json()["results"]
        assert "component" in results[0]
        assert "status" in results[0]
        assert "response_time_ms" in results[0]
