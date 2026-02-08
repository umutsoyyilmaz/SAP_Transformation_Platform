"""
SAP Transformation Management Platform
Tests — RAID API (Sprint 6).

Covers:
    - Risk CRUD + scoring + heatmap
    - Action CRUD + status patch + auto-complete
    - Issue CRUD + status patch + auto-resolve date
    - Decision CRUD + status patch + approval notification
    - RAID aggregate stats
    - Notification CRUD + unread count + mark-read
"""

import pytest

from app import create_app
from app.models import db as _db
from app.models.program import Program
from app.models.raid import Risk, Action, Issue, Decision
from app.models.notification import Notification


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
        for model in [Notification, Decision, Issue, Action, Risk, Program]:
            _db.session.query(model).delete()
        _db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_program(client, **kw):
    payload = {"name": "Test Program", "methodology": "agile"}
    payload.update(kw)
    res = client.post("/api/v1/programs", json=payload)
    assert res.status_code == 201
    return res.get_json()


# ═════════════════════════════════════════════════════════════════════════════
# RISK TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestRiskCRUD:
    def test_create_risk(self, client):
        prog = _create_program(client)
        res = client.post(f"/api/v1/programs/{prog['id']}/risks", json={
            "title": "Data loss risk",
            "probability": 4,
            "impact": 5,
            "risk_category": "technical",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["title"] == "Data loss risk"
        assert data["code"].startswith("RSK-")
        assert data["probability"] == 4
        assert data["impact"] == 5
        assert data["risk_score"] == 20
        assert data["rag_status"] == "red"
        assert data["raid_type"] == "risk"

    def test_create_risk_missing_title(self, client):
        prog = _create_program(client)
        res = client.post(f"/api/v1/programs/{prog['id']}/risks", json={})
        assert res.status_code == 400

    def test_create_risk_auto_score(self, client):
        prog = _create_program(client)
        res = client.post(f"/api/v1/programs/{prog['id']}/risks", json={
            "title": "Low risk", "probability": 1, "impact": 2,
        })
        data = res.get_json()
        assert data["risk_score"] == 2
        assert data["rag_status"] == "green"

    def test_list_risks(self, client):
        prog = _create_program(client)
        client.post(f"/api/v1/programs/{prog['id']}/risks", json={"title": "R1", "probability": 5, "impact": 5})
        client.post(f"/api/v1/programs/{prog['id']}/risks", json={"title": "R2", "probability": 1, "impact": 1})
        res = client.get(f"/api/v1/programs/{prog['id']}/risks")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 2
        # Ordered by score desc
        assert data[0]["risk_score"] >= data[1]["risk_score"]

    def test_list_risks_filter_status(self, client):
        prog = _create_program(client)
        client.post(f"/api/v1/programs/{prog['id']}/risks", json={"title": "R1", "status": "identified"})
        client.post(f"/api/v1/programs/{prog['id']}/risks", json={"title": "R2", "status": "closed"})
        res = client.get(f"/api/v1/programs/{prog['id']}/risks?status=identified")
        assert len(res.get_json()) == 1

    def test_get_risk(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/risks", json={"title": "Single"}).get_json()
        res = client.get(f"/api/v1/risks/{created['id']}")
        assert res.status_code == 200
        assert res.get_json()["title"] == "Single"

    def test_get_risk_not_found(self, client):
        res = client.get("/api/v1/risks/99999")
        assert res.status_code == 404

    def test_update_risk(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/risks", json={
            "title": "Original", "probability": 2, "impact": 2,
        }).get_json()
        res = client.put(f"/api/v1/risks/{created['id']}", json={
            "title": "Updated", "probability": 5, "impact": 5,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["title"] == "Updated"
        assert data["risk_score"] == 25
        assert data["rag_status"] == "red"

    def test_delete_risk(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/risks", json={"title": "Delete me"}).get_json()
        res = client.delete(f"/api/v1/risks/{created['id']}")
        assert res.status_code == 200
        res2 = client.get(f"/api/v1/risks/{created['id']}")
        assert res2.status_code == 404

    def test_recalculate_score(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/risks", json={
            "title": "Recalc", "probability": 3, "impact": 3,
        }).get_json()
        assert created["risk_score"] == 9
        # Update probability directly, then recalculate
        client.put(f"/api/v1/risks/{created['id']}", json={"probability": 5, "impact": 4})
        res = client.patch(f"/api/v1/risks/{created['id']}/score")
        assert res.status_code == 200
        assert res.get_json()["risk_score"] == 20

    def test_risk_creates_notification_on_high_score(self, client):
        prog = _create_program(client)
        client.post(f"/api/v1/programs/{prog['id']}/risks", json={
            "title": "Critical risk", "probability": 5, "impact": 4,
        })
        res = client.get("/api/v1/notifications?unread_only=true")
        items = res.get_json()["items"]
        assert any("Critical risk" in n["title"] or "RSK-" in n["title"] for n in items)

    def test_create_risk_for_invalid_program(self, client):
        res = client.post("/api/v1/programs/99999/risks", json={"title": "Bad"})
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# ACTION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestActionCRUD:
    def test_create_action(self, client):
        prog = _create_program(client)
        res = client.post(f"/api/v1/programs/{prog['id']}/actions", json={
            "title": "Plan migration",
            "action_type": "preventive",
            "due_date": "2025-06-01",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["code"].startswith("ACT-")
        assert data["due_date"] == "2025-06-01"
        assert data["raid_type"] == "action"

    def test_create_action_missing_title(self, client):
        prog = _create_program(client)
        res = client.post(f"/api/v1/programs/{prog['id']}/actions", json={})
        assert res.status_code == 400

    def test_list_actions(self, client):
        prog = _create_program(client)
        client.post(f"/api/v1/programs/{prog['id']}/actions", json={"title": "A1"})
        client.post(f"/api/v1/programs/{prog['id']}/actions", json={"title": "A2"})
        res = client.get(f"/api/v1/programs/{prog['id']}/actions")
        assert len(res.get_json()) == 2

    def test_update_action(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/actions", json={"title": "Old"}).get_json()
        res = client.put(f"/api/v1/actions/{created['id']}", json={"title": "New", "status": "in_progress"})
        assert res.status_code == 200
        assert res.get_json()["title"] == "New"

    def test_delete_action(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/actions", json={"title": "Del"}).get_json()
        res = client.delete(f"/api/v1/actions/{created['id']}")
        assert res.status_code == 200

    def test_action_auto_complete_date(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/actions", json={"title": "Done"}).get_json()
        res = client.patch(f"/api/v1/actions/{created['id']}/status", json={"status": "completed"})
        data = res.get_json()
        assert data["status"] == "completed"
        assert data["completed_date"] is not None

    def test_action_status_patch_missing(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/actions", json={"title": "X"}).get_json()
        res = client.patch(f"/api/v1/actions/{created['id']}/status", json={})
        assert res.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# ISSUE TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestIssueCRUD:
    def test_create_issue(self, client):
        prog = _create_program(client)
        res = client.post(f"/api/v1/programs/{prog['id']}/issues", json={
            "title": "Server crash",
            "severity": "critical",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["code"].startswith("ISS-")
        assert data["severity"] == "critical"
        assert data["raid_type"] == "issue"

    def test_create_issue_missing_title(self, client):
        prog = _create_program(client)
        res = client.post(f"/api/v1/programs/{prog['id']}/issues", json={})
        assert res.status_code == 400

    def test_critical_issue_creates_notification(self, client):
        prog = _create_program(client)
        client.post(f"/api/v1/programs/{prog['id']}/issues", json={
            "title": "System down", "severity": "critical",
        })
        res = client.get("/api/v1/notifications")
        items = res.get_json()["items"]
        assert any("critical" in n["title"].lower() or "ISS-" in n["title"] for n in items)

    def test_list_issues_filter(self, client):
        prog = _create_program(client)
        client.post(f"/api/v1/programs/{prog['id']}/issues", json={"title": "I1", "severity": "critical"})
        client.post(f"/api/v1/programs/{prog['id']}/issues", json={"title": "I2", "severity": "minor"})
        res = client.get(f"/api/v1/programs/{prog['id']}/issues?severity=critical")
        assert len(res.get_json()) == 1

    def test_update_issue(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/issues", json={"title": "Bug"}).get_json()
        res = client.put(f"/api/v1/issues/{created['id']}", json={"resolution": "Fixed config"})
        assert res.get_json()["resolution"] == "Fixed config"

    def test_delete_issue(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/issues", json={"title": "Del"}).get_json()
        res = client.delete(f"/api/v1/issues/{created['id']}")
        assert res.status_code == 200

    def test_issue_auto_resolve_date(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/issues", json={"title": "Fix"}).get_json()
        res = client.patch(f"/api/v1/issues/{created['id']}/status", json={"status": "resolved"})
        assert res.get_json()["resolution_date"] is not None

    def test_issue_status_patch_not_found(self, client):
        res = client.patch("/api/v1/issues/99999/status", json={"status": "closed"})
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# DECISION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestDecisionCRUD:
    def test_create_decision(self, client):
        prog = _create_program(client)
        res = client.post(f"/api/v1/programs/{prog['id']}/decisions", json={
            "title": "Use cloud",
            "alternatives": "Cloud vs On-Prem",
            "rationale": "Cost savings",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["code"].startswith("DEC-")
        assert data["status"] == "proposed"
        assert data["raid_type"] == "decision"

    def test_create_decision_missing_title(self, client):
        prog = _create_program(client)
        res = client.post(f"/api/v1/programs/{prog['id']}/decisions", json={})
        assert res.status_code == 400

    def test_list_decisions(self, client):
        prog = _create_program(client)
        client.post(f"/api/v1/programs/{prog['id']}/decisions", json={"title": "D1"})
        client.post(f"/api/v1/programs/{prog['id']}/decisions", json={"title": "D2"})
        res = client.get(f"/api/v1/programs/{prog['id']}/decisions")
        assert len(res.get_json()) == 2

    def test_update_decision(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/decisions", json={"title": "Old"}).get_json()
        res = client.put(f"/api/v1/decisions/{created['id']}", json={"title": "Updated", "reversible": False})
        data = res.get_json()
        assert data["title"] == "Updated"
        assert data["reversible"] is False

    def test_delete_decision(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/decisions", json={"title": "Del"}).get_json()
        res = client.delete(f"/api/v1/decisions/{created['id']}")
        assert res.status_code == 200

    def test_decision_approval_notification(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/decisions", json={"title": "Big call"}).get_json()
        client.patch(f"/api/v1/decisions/{created['id']}/status", json={"status": "approved"})
        res = client.get("/api/v1/notifications")
        items = res.get_json()["items"]
        assert any("approved" in n["title"].lower() or "DEC-" in n["title"] for n in items)

    def test_decision_status_patch(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/decisions", json={"title": "Patch"}).get_json()
        res = client.patch(f"/api/v1/decisions/{created['id']}/status", json={"status": "rejected"})
        assert res.get_json()["status"] == "rejected"

    def test_decision_status_patch_missing(self, client):
        prog = _create_program(client)
        created = client.post(f"/api/v1/programs/{prog['id']}/decisions", json={"title": "Err"}).get_json()
        res = client.patch(f"/api/v1/decisions/{created['id']}/status", json={})
        assert res.status_code == 400


# ═════════════════════════════════════════════════════════════════════════════
# RAID STATS & HEATMAP
# ═════════════════════════════════════════════════════════════════════════════

class TestRaidAggregate:
    def test_raid_stats(self, client):
        prog = _create_program(client)
        pid = prog["id"]
        client.post(f"/api/v1/programs/{pid}/risks", json={"title": "R1", "probability": 5, "impact": 5})
        client.post(f"/api/v1/programs/{pid}/actions", json={"title": "A1"})
        client.post(f"/api/v1/programs/{pid}/issues", json={"title": "I1", "severity": "critical"})
        client.post(f"/api/v1/programs/{pid}/decisions", json={"title": "D1"})
        res = client.get(f"/api/v1/programs/{pid}/raid/stats")
        assert res.status_code == 200
        data = res.get_json()
        assert data["risks"]["total"] == 1
        assert data["risks"]["critical"] == 1
        assert data["actions"]["total"] == 1
        assert data["issues"]["total"] == 1
        assert data["decisions"]["total"] == 1
        assert data["summary"]["total_items"] == 4

    def test_raid_stats_not_found(self, client):
        res = client.get("/api/v1/programs/99999/raid/stats")
        assert res.status_code == 404

    def test_raid_heatmap(self, client):
        prog = _create_program(client)
        pid = prog["id"]
        client.post(f"/api/v1/programs/{pid}/risks", json={"title": "R1", "probability": 3, "impact": 4})
        client.post(f"/api/v1/programs/{pid}/risks", json={"title": "R2", "probability": 3, "impact": 4})
        res = client.get(f"/api/v1/programs/{pid}/raid/heatmap")
        assert res.status_code == 200
        data = res.get_json()
        assert "matrix" in data
        assert len(data["matrix"]) == 5  # 5×5
        # Both risks at p=3,i=4 → matrix[2][3]
        assert len(data["matrix"][2][3]) == 2


# ═════════════════════════════════════════════════════════════════════════════
# NOTIFICATION TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestNotificationAPI:
    def test_list_notifications_empty(self, client):
        res = client.get("/api/v1/notifications")
        assert res.status_code == 200
        data = res.get_json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_unread_count(self, client):
        prog = _create_program(client)
        # Creating a critical issue auto-creates a notification
        client.post(f"/api/v1/programs/{prog['id']}/issues", json={
            "title": "Big problem", "severity": "critical",
        })
        res = client.get("/api/v1/notifications/unread-count")
        assert res.status_code == 200
        assert res.get_json()["unread_count"] >= 1

    def test_mark_notification_read(self, client):
        prog = _create_program(client)
        client.post(f"/api/v1/programs/{prog['id']}/issues", json={
            "title": "Alert", "severity": "critical",
        })
        notifs = client.get("/api/v1/notifications").get_json()["items"]
        nid = notifs[0]["id"]
        res = client.patch(f"/api/v1/notifications/{nid}/read")
        assert res.status_code == 200
        assert res.get_json()["is_read"] is True

    def test_mark_notification_read_not_found(self, client):
        res = client.patch("/api/v1/notifications/99999/read")
        assert res.status_code == 404

    def test_mark_all_read(self, client):
        prog = _create_program(client)
        # Create multiple notifications
        client.post(f"/api/v1/programs/{prog['id']}/risks", json={
            "title": "High", "probability": 5, "impact": 5,
        })
        client.post(f"/api/v1/programs/{prog['id']}/issues", json={
            "title": "Crit", "severity": "critical",
        })
        before = client.get("/api/v1/notifications/unread-count").get_json()["unread_count"]
        assert before >= 2
        res = client.post("/api/v1/notifications/mark-all-read", json={})
        assert res.status_code == 200
        assert res.get_json()["marked_read"] >= 2
        after = client.get("/api/v1/notifications/unread-count").get_json()["unread_count"]
        assert after == 0

    def test_notification_pagination(self, client):
        prog = _create_program(client)
        # Create 3 notifications via critical issues
        for i in range(3):
            client.post(f"/api/v1/programs/{prog['id']}/issues", json={
                "title": f"Issue {i}", "severity": "critical",
            })
        res = client.get("/api/v1/notifications?limit=2&offset=0")
        data = res.get_json()
        assert len(data["items"]) == 2
        assert data["total"] >= 3


# ═════════════════════════════════════════════════════════════════════════════
# RISK SCORING UNIT TESTS
# ═════════════════════════════════════════════════════════════════════════════

class TestRiskScoring:
    def test_score_calculation(self):
        from app.models.raid import calculate_risk_score, risk_rag_status
        assert calculate_risk_score(1, 1) == 1
        assert calculate_risk_score(5, 5) == 25
        assert calculate_risk_score(3, 3) == 9
        assert calculate_risk_score(0, 0) == 1  # clamped to 1

    def test_rag_classification(self):
        from app.models.raid import risk_rag_status
        assert risk_rag_status(1) == "green"
        assert risk_rag_status(4) == "green"
        assert risk_rag_status(5) == "amber"
        assert risk_rag_status(9) == "amber"
        assert risk_rag_status(10) == "orange"
        assert risk_rag_status(15) == "orange"
        assert risk_rag_status(16) == "red"
        assert risk_rag_status(25) == "red"
