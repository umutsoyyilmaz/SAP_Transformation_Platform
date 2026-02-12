"""
SAP Transformation Management Platform
Tests — Sprint 17: Run/Sustain Module.

Coverage:
  - KnowledgeTransfer model + CRUD API
  - HandoverItem model + CRUD API + seed
  - StabilizationMetric model + CRUD API
  - Run/Sustain service (progress, readiness, exit gate, weekly report)
  - Dashboard & assessment endpoints
  - SLA compliance job (fixed)
  - Edge cases & constants
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from app.models import db


# ═══════════════════════════════════════════════════════════════════════════
# Helpers  (uses session-scoped app + autouse session from conftest.py)
# ═══════════════════════════════════════════════════════════════════════════

def _create_plan():
    """Create a CutoverPlan for FK references."""
    from app.models.cutover import CutoverPlan
    from app.models.program import Program

    prog = Program(name="Test Program", status="active")
    db.session.add(prog)
    db.session.flush()

    plan = CutoverPlan(
        name="GoLive-Test",
        program_id=prog.id,
        status="hypercare",
        hypercare_start=datetime.now(timezone.utc) - timedelta(weeks=2),
        hypercare_end=datetime.now(timezone.utc) + timedelta(weeks=2),
        hypercare_duration_weeks=4,
    )
    db.session.add(plan)
    db.session.commit()
    return plan


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 1: KnowledgeTransfer Model
# ═══════════════════════════════════════════════════════════════════════════

class TestKnowledgeTransferModel:
    """Tests for KnowledgeTransfer model."""

    def test_create(self):
        from app.models.run_sustain import KnowledgeTransfer
        plan = _create_plan()
        kt = KnowledgeTransfer(
            cutover_plan_id=plan.id,
            title="SAP MM Training",
            topic_area="functional",
            trainer="Alice",
            audience="AMS Team",
        )
        db.session.add(kt)
        db.session.commit()
        assert kt.id is not None
        assert kt.status == "planned"
        assert kt.format == "workshop"

    def test_to_dict(self):
        from app.models.run_sustain import KnowledgeTransfer
        plan = _create_plan()
        kt = KnowledgeTransfer(
            cutover_plan_id=plan.id,
            title="Tech Overview",
            topic_area="technical",
            format="documentation",
        )
        db.session.add(kt)
        db.session.commit()
        d = kt.to_dict()
        assert d["title"] == "Tech Overview"
        assert d["topic_area"] == "technical"
        assert d["format"] == "documentation"
        assert "created_at" in d

    def test_repr(self):
        from app.models.run_sustain import KnowledgeTransfer
        plan = _create_plan()
        kt = KnowledgeTransfer(
            cutover_plan_id=plan.id,
            title="Security Review",
            topic_area="security",
        )
        db.session.add(kt)
        db.session.commit()
        r = repr(kt)
        assert "Security Review" in r
        assert "planned" in r


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 2: HandoverItem Model
# ═══════════════════════════════════════════════════════════════════════════

class TestHandoverItemModel:
    """Tests for HandoverItem model."""

    def test_create(self):
        from app.models.run_sustain import HandoverItem
        plan = _create_plan()
        item = HandoverItem(
            cutover_plan_id=plan.id,
            title="Admin Guide",
            category="documentation",
            priority="high",
        )
        db.session.add(item)
        db.session.commit()
        assert item.id is not None
        assert item.status == "pending"

    def test_to_dict(self):
        from app.models.run_sustain import HandoverItem
        plan = _create_plan()
        item = HandoverItem(
            cutover_plan_id=plan.id,
            title="Monitoring Setup",
            category="monitoring",
            responsible="Bob",
        )
        db.session.add(item)
        db.session.commit()
        d = item.to_dict()
        assert d["title"] == "Monitoring Setup"
        assert d["category"] == "monitoring"
        assert d["responsible"] == "Bob"

    def test_repr(self):
        from app.models.run_sustain import HandoverItem
        plan = _create_plan()
        item = HandoverItem(
            cutover_plan_id=plan.id,
            title="Escalation Procedures",
            category="support",
        )
        db.session.add(item)
        db.session.commit()
        assert "Escalation" in repr(item)


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 3: StabilizationMetric Model
# ═══════════════════════════════════════════════════════════════════════════

class TestStabilizationMetricModel:
    """Tests for StabilizationMetric model."""

    def test_create(self):
        from app.models.run_sustain import StabilizationMetric
        plan = _create_plan()
        m = StabilizationMetric(
            cutover_plan_id=plan.id,
            metric_name="Response Time",
            metric_type="system",
            unit="ms",
            target_value=200,
            current_value=180,
            is_within_target=True,
            trend="improving",
        )
        db.session.add(m)
        db.session.commit()
        assert m.id is not None
        assert m.is_within_target is True

    def test_to_dict(self):
        from app.models.run_sustain import StabilizationMetric
        plan = _create_plan()
        m = StabilizationMetric(
            cutover_plan_id=plan.id,
            metric_name="Order Processing",
            metric_type="business",
            unit="%",
            target_value=98,
            current_value=95,
        )
        db.session.add(m)
        db.session.commit()
        d = m.to_dict()
        assert d["metric_name"] == "Order Processing"
        assert d["metric_type"] == "business"
        assert d["target_value"] == 98

    def test_repr(self):
        from app.models.run_sustain import StabilizationMetric
        plan = _create_plan()
        m = StabilizationMetric(
            cutover_plan_id=plan.id,
            metric_name="CPU Usage",
            metric_type="system",
            unit="%",
            target_value=80,
            current_value=65,
        )
        db.session.add(m)
        db.session.commit()
        r = repr(m)
        assert "CPU Usage" in r


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 4: KnowledgeTransfer CRUD API
# ═══════════════════════════════════════════════════════════════════════════

class TestKnowledgeTransferAPI:
    """Tests for KT API endpoints."""

    def test_create_kt(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                         json={"title": "MM Training", "topic_area": "functional",
                               "trainer": "Alice", "audience": "Key Users"})
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["title"] == "MM Training"
        assert data["topic_area"] == "functional"

    def test_create_kt_no_title(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                         json={})
        assert rv.status_code == 400

    def test_create_kt_invalid_topic(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                         json={"title": "Test", "topic_area": "invalid"})
        assert rv.status_code == 400

    def test_list_kt(self, client):
        plan = _create_plan()
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                    json={"title": "Session 1", "topic_area": "functional"})
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                    json={"title": "Session 2", "topic_area": "technical"})
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer")
        assert rv.status_code == 200
        assert len(rv.get_json()) == 2

    def test_list_kt_filter_topic(self, client):
        plan = _create_plan()
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                    json={"title": "A", "topic_area": "functional"})
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                    json={"title": "B", "topic_area": "technical"})
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer?topic_area=technical")
        assert len(rv.get_json()) == 1

    def test_get_kt(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                         json={"title": "Get Test", "topic_area": "process"})
        kt_id = rv.get_json()["id"]
        rv2 = client.get(f"/api/v1/run-sustain/knowledge-transfer/{kt_id}")
        assert rv2.status_code == 200
        assert rv2.get_json()["title"] == "Get Test"

    def test_get_kt_404(self, client):
        rv = client.get("/api/v1/run-sustain/knowledge-transfer/999")
        assert rv.status_code == 404

    def test_update_kt(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                         json={"title": "Original", "topic_area": "functional"})
        kt_id = rv.get_json()["id"]
        rv2 = client.put(f"/api/v1/run-sustain/knowledge-transfer/{kt_id}",
                         json={"title": "Updated", "status": "completed"})
        assert rv2.status_code == 200
        assert rv2.get_json()["title"] == "Updated"
        assert rv2.get_json()["status"] == "completed"
        assert rv2.get_json()["completed_date"] is not None

    def test_delete_kt(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                         json={"title": "To Delete", "topic_area": "functional"})
        kt_id = rv.get_json()["id"]
        rv2 = client.delete(f"/api/v1/run-sustain/knowledge-transfer/{kt_id}")
        assert rv2.status_code == 200
        assert rv2.get_json()["deleted"] is True

    def test_delete_kt_404(self, client):
        rv = client.delete("/api/v1/run-sustain/knowledge-transfer/999")
        assert rv.status_code == 404

    def test_kt_progress(self, client):
        plan = _create_plan()
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                    json={"title": "A", "topic_area": "functional", "status": "completed"})
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                    json={"title": "B", "topic_area": "functional", "status": "planned"})
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer/progress")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total"] == 2
        assert data["completed"] == 1
        assert data["completion_pct"] == 50.0


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 5: HandoverItem CRUD API
# ═══════════════════════════════════════════════════════════════════════════

class TestHandoverItemAPI:
    """Tests for HandoverItem API endpoints."""

    def test_create_item(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                         json={"title": "Admin Guide", "category": "documentation", "priority": "high"})
        assert rv.status_code == 201
        assert rv.get_json()["category"] == "documentation"

    def test_create_no_title(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items", json={})
        assert rv.status_code == 400

    def test_create_invalid_category(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                         json={"title": "X", "category": "invalid"})
        assert rv.status_code == 400

    def test_list_items(self, client):
        plan = _create_plan()
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                    json={"title": "A", "category": "documentation"})
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                    json={"title": "B", "category": "monitoring"})
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/handover-items")
        assert len(rv.get_json()) == 2

    def test_list_filter_category(self, client):
        plan = _create_plan()
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                    json={"title": "A", "category": "documentation"})
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                    json={"title": "B", "category": "monitoring"})
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/handover-items?category=monitoring")
        assert len(rv.get_json()) == 1

    def test_get_item(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                         json={"title": "Get Test", "category": "process"})
        item_id = rv.get_json()["id"]
        rv2 = client.get(f"/api/v1/run-sustain/handover-items/{item_id}")
        assert rv2.status_code == 200

    def test_get_item_404(self, client):
        rv = client.get("/api/v1/run-sustain/handover-items/999")
        assert rv.status_code == 404

    def test_update_item(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                         json={"title": "Original", "category": "documentation"})
        item_id = rv.get_json()["id"]
        rv2 = client.put(f"/api/v1/run-sustain/handover-items/{item_id}",
                         json={"status": "completed"})
        assert rv2.status_code == 200
        assert rv2.get_json()["status"] == "completed"
        assert rv2.get_json()["completed_date"] is not None

    def test_delete_item(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                         json={"title": "Del", "category": "documentation"})
        item_id = rv.get_json()["id"]
        rv2 = client.delete(f"/api/v1/run-sustain/handover-items/{item_id}")
        assert rv2.status_code == 200

    def test_delete_item_404(self, client):
        rv = client.delete("/api/v1/run-sustain/handover-items/999")
        assert rv.status_code == 404

    def test_seed_handover(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items/seed")
        assert rv.status_code == 201
        assert rv.get_json()["created"] == 10

        # Second call should not duplicate
        rv2 = client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items/seed")
        assert rv2.get_json()["created"] == 0

    def test_handover_readiness(self, client):
        plan = _create_plan()
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                    json={"title": "A", "category": "documentation", "status": "completed"})
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                    json={"title": "B", "category": "documentation", "status": "pending"})
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/handover-readiness")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["completed"] == 1
        assert data["completion_pct"] == 50.0


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 6: StabilizationMetric CRUD API
# ═══════════════════════════════════════════════════════════════════════════

class TestStabilizationMetricAPI:
    """Tests for StabilizationMetric API endpoints."""

    def test_create_metric(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                         json={"metric_name": "Response Time", "metric_type": "system",
                               "unit": "ms", "target_value": 200, "current_value": 180})
        assert rv.status_code == 201
        assert rv.get_json()["metric_name"] == "Response Time"

    def test_create_no_name(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics", json={})
        assert rv.status_code == 400

    def test_create_invalid_type(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                         json={"metric_name": "X", "metric_type": "invalid"})
        assert rv.status_code == 400

    def test_list_metrics(self, client):
        plan = _create_plan()
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                    json={"metric_name": "A", "metric_type": "system"})
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                    json={"metric_name": "B", "metric_type": "business"})
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics")
        assert len(rv.get_json()) == 2

    def test_list_filter_type(self, client):
        plan = _create_plan()
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                    json={"metric_name": "A", "metric_type": "system"})
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                    json={"metric_name": "B", "metric_type": "business"})
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics?metric_type=system")
        assert len(rv.get_json()) == 1

    def test_get_metric(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                         json={"metric_name": "CPU", "metric_type": "system"})
        m_id = rv.get_json()["id"]
        rv2 = client.get(f"/api/v1/run-sustain/stabilization-metrics/{m_id}")
        assert rv2.status_code == 200

    def test_get_metric_404(self, client):
        rv = client.get("/api/v1/run-sustain/stabilization-metrics/999")
        assert rv.status_code == 404

    def test_update_metric(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                         json={"metric_name": "Throughput", "metric_type": "system"})
        m_id = rv.get_json()["id"]
        rv2 = client.put(f"/api/v1/run-sustain/stabilization-metrics/{m_id}",
                         json={"current_value": 95.5, "trend": "improving", "is_within_target": True})
        assert rv2.status_code == 200
        assert rv2.get_json()["current_value"] == 95.5
        assert rv2.get_json()["trend"] == "improving"

    def test_update_invalid_trend(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                         json={"metric_name": "X", "metric_type": "system"})
        m_id = rv.get_json()["id"]
        rv2 = client.put(f"/api/v1/run-sustain/stabilization-metrics/{m_id}",
                         json={"trend": "invalid"})
        assert rv2.status_code == 400

    def test_delete_metric(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                         json={"metric_name": "Del", "metric_type": "system"})
        m_id = rv.get_json()["id"]
        rv2 = client.delete(f"/api/v1/run-sustain/stabilization-metrics/{m_id}")
        assert rv2.status_code == 200

    def test_delete_metric_404(self, client):
        rv = client.delete("/api/v1/run-sustain/stabilization-metrics/999")
        assert rv.status_code == 404

    def test_stabilization_dashboard(self, client):
        plan = _create_plan()
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                    json={"metric_name": "A", "metric_type": "system",
                          "is_within_target": True, "target_value": 100, "current_value": 95})
        client.post(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-metrics",
                    json={"metric_name": "B", "metric_type": "system",
                          "is_within_target": False, "target_value": 100, "current_value": 50})
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/stabilization-dashboard")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total_metrics"] == 2
        assert data["within_target"] == 1
        assert data["health_pct"] == 50.0


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 7: Dashboard & Assessments API
# ═══════════════════════════════════════════════════════════════════════════

class TestDashboardAPI:
    """Tests for Run/Sustain dashboard & assessment endpoints."""

    def test_dashboard(self, client):
        plan = _create_plan()
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/dashboard")
        assert rv.status_code == 200
        data = rv.get_json()
        assert "incidents" in data
        assert "knowledge_transfer" in data
        assert "handover" in data
        assert "stabilization" in data

    def test_dashboard_404(self, client):
        rv = client.get("/api/v1/run-sustain/plans/999/dashboard")
        assert rv.status_code == 404

    def test_exit_readiness_empty(self, client):
        plan = _create_plan()
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/exit-readiness")
        assert rv.status_code == 200
        data = rv.get_json()
        assert "criteria" in data
        assert len(data["criteria"]) == 5
        assert "ready" in data

    def test_exit_readiness_all_met(self, client):
        """With empty data, most criteria are 'met' (100% of 0 = 100%)."""
        plan = _create_plan()
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/exit-readiness")
        data = rv.get_json()
        # With no incidents, no KT, no handover, no metrics —
        # incidents criterion is met (0 open P1/P2),
        # KT/handover/stab all have 100% of 0 items = met
        # SLA may be not_met (no data)
        assert data["summary"]["met"] >= 4

    def test_exit_readiness_not_met(self, client):
        from app.models.cutover import HypercareIncident
        plan = _create_plan()
        # Create an open P1 incident
        inc = HypercareIncident(
            cutover_plan_id=plan.id,
            title="Critical Failure",
            severity="P1",
            status="open",
        )
        db.session.add(inc)
        db.session.commit()

        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/exit-readiness")
        data = rv.get_json()
        # P1 open → incidents criterion not met
        inc_crit = next(c for c in data["criteria"] if "P1/P2" in c["criterion"])
        assert inc_crit["status"] == "not_met"

    def test_weekly_report(self, client):
        plan = _create_plan()
        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/weekly-report")
        assert rv.status_code == 200
        data = rv.get_json()
        assert "incidents" in data
        assert "knowledge_transfer" in data
        assert "handover" in data
        assert "stabilization" in data
        assert "exit_readiness" in data
        assert "hypercare_period" in data

    def test_support_summary(self, client):
        from app.models.cutover import HypercareIncident
        plan = _create_plan()
        inc = HypercareIncident(
            cutover_plan_id=plan.id,
            title="Bug Fix",
            severity="P3",
            status="open",
            assigned_to="Alice",
        )
        db.session.add(inc)
        db.session.commit()

        rv = client.get(f"/api/v1/run-sustain/plans/{plan.id}/support-summary")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["total_incidents"] == 1
        assert "Alice" in data["by_assignee"]


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 8: Run/Sustain Service Logic
# ═══════════════════════════════════════════════════════════════════════════

class TestRunSustainService:
    """Tests for service-level computations."""

    def test_kt_progress_empty(self):
        from app.services.run_sustain_service import compute_kt_progress
        plan = _create_plan()
        result = compute_kt_progress(plan.id)
        assert result["total"] == 0
        assert result["completion_pct"] == 100.0

    def test_kt_progress_with_data(self):
        from app.models.run_sustain import KnowledgeTransfer
        from app.services.run_sustain_service import compute_kt_progress
        plan = _create_plan()
        for i, status in enumerate(["completed", "planned", "cancelled"]):
            kt = KnowledgeTransfer(
                cutover_plan_id=plan.id,
                title=f"KT-{i}",
                topic_area="functional",
                status=status,
            )
            db.session.add(kt)
        db.session.commit()
        result = compute_kt_progress(plan.id)
        assert result["total"] == 3
        assert result["active"] == 2  # 3 - 1 cancelled
        assert result["completed"] == 1
        assert result["completion_pct"] == 50.0

    def test_handover_readiness_with_data(self):
        from app.models.run_sustain import HandoverItem
        from app.services.run_sustain_service import compute_handover_readiness
        plan = _create_plan()
        for status in ["completed", "completed", "in_progress", "blocked"]:
            item = HandoverItem(
                cutover_plan_id=plan.id,
                title=f"Item-{status}",
                category="documentation",
                status=status,
            )
            db.session.add(item)
        db.session.commit()
        result = compute_handover_readiness(plan.id)
        assert result["total"] == 4
        assert result["completed"] == 2
        assert result["completion_pct"] == 50.0
        assert result["blocked"] == 1

    def test_stabilization_dashboard_with_data(self):
        from app.models.run_sustain import StabilizationMetric
        from app.services.run_sustain_service import compute_stabilization_dashboard
        plan = _create_plan()
        for i, (is_ok, trend) in enumerate([(True, "stable"), (True, "improving"), (False, "degrading")]):
            m = StabilizationMetric(
                cutover_plan_id=plan.id,
                metric_name=f"M-{i}",
                metric_type="system",
                is_within_target=is_ok,
                trend=trend,
            )
            db.session.add(m)
        db.session.commit()
        result = compute_stabilization_dashboard(plan.id)
        assert result["total_metrics"] == 3
        assert result["within_target"] == 2
        assert result["degrading"] == 1

    def test_support_summary_empty(self):
        from app.services.run_sustain_service import compute_support_summary
        plan = _create_plan()
        result = compute_support_summary(plan.id)
        assert result["total_incidents"] == 0
        assert result["avg_resolution_min"] is None

    def test_support_summary_with_data(self):
        from app.models.cutover import HypercareIncident
        from app.services.run_sustain_service import compute_support_summary
        plan = _create_plan()
        for i in range(3):
            inc = HypercareIncident(
                cutover_plan_id=plan.id,
                title=f"Inc-{i}",
                severity="P3",
                status="resolved" if i < 2 else "open",
                assigned_to="Alice" if i < 2 else "Bob",
                resolution_time_min=60 if i < 2 else None,
            )
            db.session.add(inc)
        db.session.commit()
        result = compute_support_summary(plan.id)
        assert result["total_incidents"] == 3
        assert result["open_incidents"] == 1
        assert result["avg_resolution_min"] == 60.0
        assert "Alice" in result["by_assignee"]
        assert "Bob" in result["by_assignee"]

    def test_seed_handover_items(self):
        from app.services.run_sustain_service import seed_handover_items
        plan = _create_plan()
        items = seed_handover_items(plan.id)
        assert len(items) == 10
        # Second call returns empty
        items2 = seed_handover_items(plan.id)
        assert len(items2) == 0


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 9: SLA Compliance Job (Fixed)
# ═══════════════════════════════════════════════════════════════════════════

class TestSLAComplianceJob:
    """Tests for the fixed SLA compliance scheduled job."""

    def test_sla_job_no_data(self, app):
        from app.services.scheduled_jobs import check_sla_compliance
        result = check_sla_compliance(app)
        assert result["slas_checked"] == 0
        assert result["breaches_found"] == 0

    def test_sla_job_with_breach(self, app):
        from app.models.cutover import HypercareSLA, HypercareIncident
        from app.services.scheduled_jobs import check_sla_compliance

        plan = _create_plan()

        # Create SLA: P1 must respond within 15 minutes
        sla = HypercareSLA(
            cutover_plan_id=plan.id,
            severity="P1",
            response_target_min=15,
            resolution_target_min=240,
        )
        db.session.add(sla)

        # Create an old open P1 incident (2 hours ago, no response)
        inc = HypercareIncident(
            cutover_plan_id=plan.id,
            title="Critical System Failure",
            severity="P1",
            status="open",
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db.session.add(inc)
        db.session.commit()

        result = check_sla_compliance(app)
        assert result["slas_checked"] >= 1
        assert result["breaches_found"] >= 1  # Both response and resolution breached

    def test_sla_job_no_breach(self, app):
        from app.models.cutover import HypercareSLA, HypercareIncident
        from app.services.scheduled_jobs import check_sla_compliance

        plan = _create_plan()

        sla = HypercareSLA(
            cutover_plan_id=plan.id,
            severity="P3",
            response_target_min=480,    # 8 hours
            resolution_target_min=2400,  # 40 hours
        )
        db.session.add(sla)

        # Create a very recent open incident with response already logged
        inc = HypercareIncident(
            cutover_plan_id=plan.id,
            title="Minor Issue",
            severity="P3",
            status="investigating",
            response_time_min=5,  # Already responded
        )
        db.session.add(inc)
        db.session.commit()

        result = check_sla_compliance(app)
        assert result["breaches_found"] == 0


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 10: Edge Cases & Constants
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge case and constant validation tests."""

    def test_model_constants(self):
        from app.models.run_sustain import (
            KT_TOPIC_AREAS, KT_STATUSES, KT_FORMATS,
            HANDOVER_CATEGORIES, HANDOVER_STATUSES,
            METRIC_TYPES, METRIC_TRENDS,
        )
        assert "functional" in KT_TOPIC_AREAS
        assert "completed" in KT_STATUSES
        assert "workshop" in KT_FORMATS
        assert "documentation" in HANDOVER_CATEGORIES
        assert "completed" in HANDOVER_STATUSES
        assert "system" in METRIC_TYPES
        assert "improving" in METRIC_TRENDS

    def test_standard_handover_items_count(self):
        from app.services.run_sustain_service import STANDARD_HANDOVER_ITEMS
        assert len(STANDARD_HANDOVER_ITEMS) == 10
        for item in STANDARD_HANDOVER_ITEMS:
            assert "title" in item
            assert "category" in item

    def test_exit_readiness_missing_plan(self):
        from app.services.run_sustain_service import evaluate_hypercare_exit
        result = evaluate_hypercare_exit(99999)
        assert result["ready"] is False
        assert "error" in result

    def test_weekly_report_missing_plan(self):
        from app.services.run_sustain_service import generate_weekly_report
        result = generate_weekly_report(99999)
        assert "error" in result

    def test_update_kt_invalid_format(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                         json={"title": "Test", "topic_area": "functional"})
        kt_id = rv.get_json()["id"]
        rv2 = client.put(f"/api/v1/run-sustain/knowledge-transfer/{kt_id}",
                         json={"format": "invalid"})
        assert rv2.status_code == 400

    def test_update_handover_invalid_status(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                         json={"title": "Test", "category": "documentation"})
        item_id = rv.get_json()["id"]
        rv2 = client.put(f"/api/v1/run-sustain/handover-items/{item_id}",
                         json={"status": "invalid"})
        assert rv2.status_code == 400

    def test_update_handover_invalid_priority(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/handover-items",
                         json={"title": "Test", "category": "documentation"})
        item_id = rv.get_json()["id"]
        rv2 = client.put(f"/api/v1/run-sustain/handover-items/{item_id}",
                         json={"priority": "invalid"})
        assert rv2.status_code == 400

    def test_create_kt_invalid_format(self, client):
        plan = _create_plan()
        rv = client.post(f"/api/v1/run-sustain/plans/{plan.id}/knowledge-transfer",
                         json={"title": "X", "format": "bad"})
        assert rv.status_code == 400
