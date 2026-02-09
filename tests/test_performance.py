"""
Performance / benchmark tests.

These tests measure API response times under load.
Skipped by default — run with: pytest -m performance -v

Thresholds are generous for CI (not micro-benchmarks).
"""

import time

import pytest

pytestmark = [pytest.mark.performance, pytest.mark.slow]


# ── Helpers ──────────────────────────────────────────────────────────────

def _post(client, url, json=None):
    res = client.post(url, json=json or {})
    assert res.status_code in (200, 201), f"POST {url} → {res.status_code}"
    return res.get_json()


def _timed_get(client, url, threshold_ms=500):
    """GET with timing assertion."""
    t0 = time.perf_counter()
    res = client.get(url)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert res.status_code == 200, f"GET {url} → {res.status_code}"
    assert elapsed_ms < threshold_ms, (
        f"GET {url} took {elapsed_ms:.0f}ms (threshold: {threshold_ms}ms)"
    )
    return res.get_json(), elapsed_ms


def _seed_bulk_data(client, pid, n_requirements=200, n_defects=100, n_test_cases=150):
    """Seed a reasonable amount of test data."""
    for i in range(n_requirements):
        client.post(f"/api/v1/programs/{pid}/requirements", json={
            "title": f"Requirement {i+1}",
            "req_type": "functional" if i % 2 == 0 else "technical",
            "priority": ["Low", "Medium", "High", "Critical"][i % 4],
            "fit_status": ["Fit", "Partial Fit", "Gap"][i % 3],
        })

    for i in range(n_test_cases):
        client.post(f"/api/v1/programs/{pid}/testing/catalog", json={
            "title": f"Test Case {i+1}",
            "test_type": "unit" if i % 3 == 0 else "integration",
            "priority": "medium",
        })

    for i in range(n_defects):
        client.post(f"/api/v1/programs/{pid}/testing/defects", json={
            "title": f"Defect {i+1}",
            "severity": ["low", "medium", "high", "critical"][i % 4],
            "status": ["new", "in_progress", "resolved", "closed"][i % 4],
        })


# ── Performance Tests ────────────────────────────────────────────────────


class TestAPIPerformance:
    """API response time benchmarks with bulk data."""

    @pytest.fixture(autouse=True)
    def setup_bulk_data(self, client):
        """Seed bulk data for performance tests."""
        prog = _post(client, "/api/v1/programs", {
            "name": "Performance Test Program",
            "methodology": "agile"
        })
        self.pid = prog["id"]
        _seed_bulk_data(client, self.pid, n_requirements=200, n_defects=100, n_test_cases=150)

    def test_requirement_list_under_500ms(self, client):
        """GET /requirements (paginated) should be fast."""
        data, ms = _timed_get(
            client,
            f"/api/v1/programs/{self.pid}/requirements?limit=50&offset=0",
            threshold_ms=500,
        )
        assert "items" in data
        assert len(data["items"]) == 50

    def test_requirement_list_page_2(self, client):
        """Second page should also be fast (offset pagination)."""
        data, ms = _timed_get(
            client,
            f"/api/v1/programs/{self.pid}/requirements?limit=50&offset=50",
            threshold_ms=500,
        )
        assert "items" in data

    def test_test_case_list_under_500ms(self, client):
        """GET /testing/catalog paginated."""
        data, ms = _timed_get(
            client,
            f"/api/v1/programs/{self.pid}/testing/catalog?limit=50",
            threshold_ms=500,
        )

    def test_defect_list_under_500ms(self, client):
        """GET /testing/defects paginated."""
        data, ms = _timed_get(
            client,
            f"/api/v1/programs/{self.pid}/testing/defects?limit=50",
            threshold_ms=500,
        )

    def test_testing_dashboard_under_1s(self, client):
        """Dashboard aggregation with 200+ entities should be fast."""
        data, ms = _timed_get(
            client,
            f"/api/v1/programs/{self.pid}/testing/dashboard",
            threshold_ms=1000,
        )

    def test_risk_list_under_500ms(self, client):
        """Risk list with bulk data."""
        # Seed some risks
        for i in range(50):
            _post(client, f"/api/v1/programs/{self.pid}/risks", {
                "title": f"Risk {i+1}",
                "probability": (i % 5) + 1,
                "impact": (i % 5) + 1,
                "status": "open",
                "owner": "test",
                "category": "technical"
            })
        data, ms = _timed_get(
            client,
            f"/api/v1/programs/{self.pid}/risks?limit=50",
            threshold_ms=500,
        )

    def test_health_under_100ms(self, client):
        """Health check should be very fast."""
        data, ms = _timed_get(client, "/api/v1/health/ready", threshold_ms=100)

    def test_concurrent_api_pattern(self, client):
        """Simulate sequential API calls (proxy for concurrency)."""
        endpoints = [
            f"/api/v1/programs/{self.pid}/requirements?limit=10",
            f"/api/v1/programs/{self.pid}/testing/catalog?limit=10",
            f"/api/v1/programs/{self.pid}/testing/defects?limit=10",
            "/api/v1/health/ready",
        ]
        t0 = time.perf_counter()
        for url in endpoints:
            res = client.get(url)
            assert res.status_code == 200
        total_ms = (time.perf_counter() - t0) * 1000
        avg_ms = total_ms / len(endpoints)
        assert avg_ms < 500, f"Average request time: {avg_ms:.0f}ms (threshold: 500ms)"
