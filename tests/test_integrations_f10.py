"""F10 — External Integrations & Public API tests."""

import json
import pytest

from app import create_app
from app.models import db
from app.models.integrations import (
    AutomationImportJob,
    JiraIntegration,
    WebhookDelivery,
    WebhookSubscription,
)


@pytest.fixture()
def f10_client():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SECRET_KEY="test-f10",
        WTF_CSRF_ENABLED=False,
        SERVER_NAME="localhost",
    )
    with app.app_context():
        db.create_all()
        # seed a program
        from app.models.program import Program
        p = Program(name="F10 Test Program", status="active")
        db.session.add(p)
        db.session.commit()
        with app.test_client() as client:
            client.program_id = p.id
            yield client


# ═════════════════════════════════════════════════════════════════
# 1. Jira Integration
# ═════════════════════════════════════════════════════════════════
class TestJiraIntegration:
    def test_create_jira_integration(self, f10_client):
        r = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration",
            json={
                "jira_url": "https://test.atlassian.net",
                "project_key": "TP",
                "auth_type": "api_token",
                "credentials": "secret-token",
            },
        )
        assert r.status_code == 201
        d = r.get_json()
        assert d["project_key"] == "TP"
        assert d["jira_url"] == "https://test.atlassian.net"
        assert d["is_active"] is True

    def test_duplicate_jira_integration_409(self, f10_client):
        f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration",
            json={"jira_url": "https://a.net", "project_key": "A"},
        )
        r = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration",
            json={"jira_url": "https://b.net", "project_key": "B"},
        )
        assert r.status_code == 409

    def test_get_jira_integration(self, f10_client):
        f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration",
            json={"jira_url": "https://test.net", "project_key": "T"},
        )
        r = f10_client.get(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration"
        )
        assert r.status_code == 200
        assert r.get_json()["project_key"] == "T"

    def test_get_jira_integration_404(self, f10_client):
        r = f10_client.get(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration"
        )
        assert r.status_code == 404

    def test_update_jira_integration(self, f10_client):
        cr = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration",
            json={"jira_url": "https://old.net", "project_key": "OLD"},
        )
        jid = cr.get_json()["id"]
        r = f10_client.put(
            f"/api/v1/jira-integrations/{jid}",
            json={"project_key": "NEW", "is_active": False},
        )
        assert r.status_code == 200
        assert r.get_json()["project_key"] == "NEW"
        assert r.get_json()["is_active"] is False

    def test_delete_jira_integration(self, f10_client):
        cr = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration",
            json={"jira_url": "https://del.net", "project_key": "DEL"},
        )
        jid = cr.get_json()["id"]
        r = f10_client.delete(f"/api/v1/jira-integrations/{jid}")
        assert r.status_code == 204

    def test_trigger_jira_sync(self, f10_client):
        cr = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration",
            json={"jira_url": "https://sync.net", "project_key": "SY"},
        )
        jid = cr.get_json()["id"]
        r = f10_client.post(f"/api/v1/jira-integrations/{jid}/sync")
        assert r.status_code == 200
        assert r.get_json()["status"] == "syncing"

    def test_sync_inactive_jira_fails(self, f10_client):
        cr = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration",
            json={"jira_url": "https://x.net", "project_key": "X"},
        )
        jid = cr.get_json()["id"]
        f10_client.put(f"/api/v1/jira-integrations/{jid}", json={"is_active": False})
        r = f10_client.post(f"/api/v1/jira-integrations/{jid}/sync")
        assert r.status_code == 400

    def test_jira_sync_status(self, f10_client):
        cr = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration",
            json={"jira_url": "https://s.net", "project_key": "S"},
        )
        jid = cr.get_json()["id"]
        r = f10_client.get(f"/api/v1/jira-integrations/{jid}/status")
        assert r.status_code == 200
        assert r.get_json()["sync_status"] == "idle"


# ═════════════════════════════════════════════════════════════════
# 2. Automation Import Jobs
# ═════════════════════════════════════════════════════════════════
class TestAutomationImport:
    def _create_job(self, client, **kwargs):
        payload = {
            "program_id": client.program_id,
            "source": "jenkins",
            "build_id": "build-42",
            "entity_type": "junit",
            "file_path": "/reports/results.xml",
        }
        payload.update(kwargs)
        return client.post(
            "/api/v1/integrations/automation/import", json=payload
        )

    def test_create_import_job(self, f10_client):
        r = self._create_job(f10_client)
        assert r.status_code == 202
        d = r.get_json()
        assert d["status"] == "queued"
        assert d["source"] == "jenkins"
        assert d["request_id"]  # UUID

    def test_create_import_job_missing_program(self, f10_client):
        r = f10_client.post(
            "/api/v1/integrations/automation/import", json={"source": "manual"}
        )
        assert r.status_code == 400

    def test_get_import_status_by_request_id(self, f10_client):
        cr = self._create_job(f10_client)
        rid = cr.get_json()["request_id"]
        r = f10_client.get(f"/api/v1/integrations/automation/status/{rid}")
        assert r.status_code == 200
        assert r.get_json()["request_id"] == rid

    def test_get_import_status_404(self, f10_client):
        r = f10_client.get(
            "/api/v1/integrations/automation/status/nonexistent-uuid"
        )
        assert r.status_code == 404

    def test_list_automation_jobs(self, f10_client):
        self._create_job(f10_client, build_id="b1")
        self._create_job(f10_client, build_id="b2")
        r = f10_client.get(
            f"/api/v1/programs/{f10_client.program_id}/automation-jobs"
        )
        assert r.status_code == 200
        d = r.get_json()
        assert d["total"] == 2

    def test_list_automation_jobs_filter_status(self, f10_client):
        self._create_job(f10_client)
        r = f10_client.get(
            f"/api/v1/programs/{f10_client.program_id}/automation-jobs?status=queued"
        )
        assert r.get_json()["total"] == 1
        r2 = f10_client.get(
            f"/api/v1/programs/{f10_client.program_id}/automation-jobs?status=completed"
        )
        assert r2.get_json()["total"] == 0

    def test_process_job_to_completed(self, f10_client):
        cr = self._create_job(f10_client)
        jid = cr.get_json()["id"]
        # processing
        r1 = f10_client.post(
            f"/api/v1/automation-jobs/{jid}/process",
            json={"status": "processing"},
        )
        assert r1.get_json()["status"] == "processing"
        assert r1.get_json()["started_at"] is not None
        # completed
        r2 = f10_client.post(
            f"/api/v1/automation-jobs/{jid}/process",
            json={
                "status": "completed",
                "result_summary": {"passed": 10, "failed": 2},
            },
        )
        assert r2.get_json()["status"] == "completed"
        assert r2.get_json()["result_summary"]["passed"] == 10

    def test_process_job_to_failed(self, f10_client):
        cr = self._create_job(f10_client)
        jid = cr.get_json()["id"]
        r = f10_client.post(
            f"/api/v1/automation-jobs/{jid}/process",
            json={"status": "failed", "error_message": "Parse error"},
        )
        assert r.get_json()["status"] == "failed"
        assert "Parse error" in r.get_json()["error_message"]

    def test_process_job_invalid_status(self, f10_client):
        cr = self._create_job(f10_client)
        jid = cr.get_json()["id"]
        r = f10_client.post(
            f"/api/v1/automation-jobs/{jid}/process",
            json={"status": "invalid"},
        )
        assert r.status_code == 400


# ═════════════════════════════════════════════════════════════════
# 3. Webhooks
# ═════════════════════════════════════════════════════════════════
class TestWebhooks:
    def _create_webhook(self, client, **kwargs):
        payload = {
            "name": "Test Hook",
            "url": "https://example.com/hook",
            "events": ["defect.created", "execution.completed"],
            "secret": "my-secret",
        }
        payload.update(kwargs)
        return client.post(
            f"/api/v1/programs/{client.program_id}/webhooks", json=payload
        )

    def test_create_webhook(self, f10_client):
        r = self._create_webhook(f10_client)
        assert r.status_code == 201
        d = r.get_json()
        assert d["name"] == "Test Hook"
        assert d["is_active"] is True
        assert "defect.created" in d["events"]

    def test_create_webhook_missing_url(self, f10_client):
        r = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/webhooks",
            json={"name": "No URL"},
        )
        assert r.status_code == 400

    def test_create_webhook_invalid_event(self, f10_client):
        r = self._create_webhook(
            f10_client, events=["invalid.event"]
        )
        assert r.status_code == 400

    def test_list_webhooks(self, f10_client):
        self._create_webhook(f10_client, name="H1")
        self._create_webhook(f10_client, name="H2")
        r = f10_client.get(
            f"/api/v1/programs/{f10_client.program_id}/webhooks"
        )
        assert r.get_json()["total"] == 2

    def test_get_webhook(self, f10_client):
        cr = self._create_webhook(f10_client)
        wid = cr.get_json()["id"]
        r = f10_client.get(f"/api/v1/webhooks/{wid}")
        assert r.status_code == 200
        assert r.get_json()["id"] == wid

    def test_update_webhook(self, f10_client):
        cr = self._create_webhook(f10_client)
        wid = cr.get_json()["id"]
        r = f10_client.put(
            f"/api/v1/webhooks/{wid}",
            json={"name": "Updated", "is_active": False},
        )
        assert r.status_code == 200
        assert r.get_json()["name"] == "Updated"
        assert r.get_json()["is_active"] is False

    def test_delete_webhook(self, f10_client):
        cr = self._create_webhook(f10_client)
        wid = cr.get_json()["id"]
        r = f10_client.delete(f"/api/v1/webhooks/{wid}")
        assert r.status_code == 204

    def test_webhook_404(self, f10_client):
        r = f10_client.get("/api/v1/webhooks/9999")
        assert r.status_code == 404


# ═════════════════════════════════════════════════════════════════
# 4. Webhook Deliveries & Test
# ═════════════════════════════════════════════════════════════════
class TestWebhookDeliveries:
    def _create_webhook(self, client):
        r = client.post(
            f"/api/v1/programs/{client.program_id}/webhooks",
            json={"name": "DH", "url": "https://example.com/d", "events": ["defect.created"]},
        )
        return r.get_json()["id"]

    def test_test_webhook_creates_delivery(self, f10_client):
        wid = self._create_webhook(f10_client)
        r = f10_client.post(f"/api/v1/webhooks/{wid}/test")
        assert r.status_code == 201
        d = r.get_json()
        assert d["event_type"] == "ping"
        assert d["response_status"] == 200

    def test_test_inactive_webhook_fails(self, f10_client):
        wid = self._create_webhook(f10_client)
        f10_client.put(f"/api/v1/webhooks/{wid}", json={"is_active": False})
        r = f10_client.post(f"/api/v1/webhooks/{wid}/test")
        assert r.status_code == 400

    def test_list_deliveries(self, f10_client):
        wid = self._create_webhook(f10_client)
        f10_client.post(f"/api/v1/webhooks/{wid}/test")
        f10_client.post(f"/api/v1/webhooks/{wid}/test")
        r = f10_client.get(f"/api/v1/webhooks/{wid}/deliveries")
        assert r.status_code == 200
        assert r.get_json()["total"] == 2

    def test_deliveries_for_nonexistent_webhook(self, f10_client):
        r = f10_client.get("/api/v1/webhooks/9999/deliveries")
        assert r.status_code == 404


# ═════════════════════════════════════════════════════════════════
# 5. OpenAPI Spec
# ═════════════════════════════════════════════════════════════════
class TestOpenAPISpec:
    def test_openapi_spec(self, f10_client):
        r = f10_client.get("/api/v1/openapi.json")
        assert r.status_code == 200
        d = r.get_json()
        assert d["openapi"] == "3.0.3"
        assert "paths" in d
        assert "/integrations/automation/import" in d["paths"]


# ═════════════════════════════════════════════════════════════════
# 6. Dispatch helper
# ═════════════════════════════════════════════════════════════════
class TestWebhookDispatch:
    def test_dispatch_webhook_event(self, f10_client):
        from app.blueprints.integrations_bp import dispatch_webhook_event
        from flask import current_app

        # Create a webhook that listens to defect.created
        pid = f10_client.program_id
        f10_client.post(
            f"/api/v1/programs/{pid}/webhooks",
            json={
                "name": "Dispatch Test",
                "url": "https://example.com/dispatch",
                "events": ["defect.created"],
                "secret": "s3cret",
            },
        )
        # Dispatch event
        with current_app.app_context():
            dispatch_webhook_event(pid, "defect.created", {"defect_id": 42})

        # Should have a delivery
        sub = WebhookSubscription.query.filter_by(program_id=pid).first()
        deliveries = WebhookDelivery.query.filter_by(subscription_id=sub.id).all()
        assert len(deliveries) == 1
        assert deliveries[0].event_type == "defect.created"
        assert "signature" in deliveries[0].payload

    def test_dispatch_skips_inactive_webhook(self, f10_client):
        from app.blueprints.integrations_bp import dispatch_webhook_event
        from flask import current_app

        pid = f10_client.program_id
        cr = f10_client.post(
            f"/api/v1/programs/{pid}/webhooks",
            json={
                "name": "Inactive",
                "url": "https://example.com/inactive",
                "events": ["defect.created"],
                "is_active": False,
            },
        )
        with current_app.app_context():
            dispatch_webhook_event(pid, "defect.created", {"defect_id": 1})

        sub = WebhookSubscription.query.filter_by(program_id=pid).first()
        deliveries = WebhookDelivery.query.filter_by(subscription_id=sub.id).all()
        assert len(deliveries) == 0

    def test_dispatch_skips_non_matching_event(self, f10_client):
        from app.blueprints.integrations_bp import dispatch_webhook_event
        from flask import current_app

        pid = f10_client.program_id
        f10_client.post(
            f"/api/v1/programs/{pid}/webhooks",
            json={
                "name": "Selective",
                "url": "https://example.com/sel",
                "events": ["execution.completed"],
            },
        )
        with current_app.app_context():
            dispatch_webhook_event(pid, "defect.created", {"defect_id": 1})

        sub = WebhookSubscription.query.filter_by(program_id=pid).first()
        deliveries = WebhookDelivery.query.filter_by(subscription_id=sub.id).all()
        assert len(deliveries) == 0


# ═════════════════════════════════════════════════════════════════
# 7. Model Integrity
# ═════════════════════════════════════════════════════════════════
class TestModelIntegrity:
    def test_jira_integration_to_dict(self, f10_client):
        r = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/jira-integration",
            json={"jira_url": "https://t.net", "project_key": "T"},
        )
        d = r.get_json()
        assert "id" in d
        assert "created_at" in d
        assert "auth_type" in d

    def test_automation_job_to_dict(self, f10_client):
        r = f10_client.post(
            "/api/v1/integrations/automation/import",
            json={"program_id": f10_client.program_id},
        )
        d = r.get_json()
        assert "request_id" in d
        assert "status" in d
        assert "result_summary" in d

    def test_webhook_to_dict(self, f10_client):
        r = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/webhooks",
            json={"name": "Dict Test", "url": "https://dt.com", "events": []},
        )
        d = r.get_json()
        assert "url" in d
        assert "retry_config" in d

    def test_delivery_to_dict(self, f10_client):
        cr = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/webhooks",
            json={"name": "DT", "url": "https://dt2.com", "events": []},
        )
        wid = cr.get_json()["id"]
        r = f10_client.post(f"/api/v1/webhooks/{wid}/test")
        d = r.get_json()
        assert "attempt_no" in d
        assert "delivered_at" in d

    def test_webhook_cascade_delete(self, f10_client):
        cr = f10_client.post(
            f"/api/v1/programs/{f10_client.program_id}/webhooks",
            json={"name": "Cascade", "url": "https://cas.com", "events": []},
        )
        wid = cr.get_json()["id"]
        f10_client.post(f"/api/v1/webhooks/{wid}/test")
        f10_client.post(f"/api/v1/webhooks/{wid}/test")
        # Delete webhook → deliveries should cascade
        f10_client.delete(f"/api/v1/webhooks/{wid}")
        from flask import current_app

        with current_app.app_context():
            count = WebhookDelivery.query.filter_by(subscription_id=wid).count()
            assert count == 0
