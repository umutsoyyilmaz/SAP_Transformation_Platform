"""
SAP Transformation Management Platform
Tests — Sprint 16: Notification + Scheduling.

Covers:
    1. NotificationPreference model
    2. ScheduledJob model
    3. EmailLog model
    4. EmailService (template rendering + dev-mode send)
    5. SchedulerService (job registration + execution)
    6. Scheduled jobs (overdue scanner, escalation, digests, cleanup, SLA)
    7. Notification blueprint (CRUD, preferences, scheduler API, email logs)
    8. Edge cases
"""

import pytest
from datetime import datetime, timedelta, timezone, date
from unittest.mock import patch, MagicMock

from app import create_app
from app.models import db


# ═══════════════════════════════════════════════════════════════════════════
#  FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def s16_app():
    """Session-scoped Flask app for S16 tests."""
    application = create_app("testing")
    return application


@pytest.fixture(scope="session")
def s16_db(s16_app):
    """Session-scoped DB setup."""
    with s16_app.app_context():
        db.create_all()
    yield
    with s16_app.app_context():
        db.drop_all()


@pytest.fixture(autouse=True)
def s16_session(s16_app, s16_db):
    """Per-test session with rollback + table recreate."""
    with s16_app.app_context():
        yield
        db.session.rollback()
        db.drop_all()
        db.create_all()


@pytest.fixture()
def client(s16_app):
    return s16_app.test_client()


@pytest.fixture()
def app_ctx(s16_app):
    return s16_app


def _create_program(client):
    res = client.post("/api/v1/programs", json={"name": "S16 Test Program", "methodology": "agile"})
    assert res.status_code == 201
    return res.get_json()


def _create_notification(*, title="Test Alert", message="Details here",
                         category="system", severity="info",
                         recipient="all", program_id=None):
    """Create a Notification directly in DB."""
    from app.models.notification import Notification
    n = Notification(
        title=title, message=message, category=category,
        severity=severity, recipient=recipient, program_id=program_id,
    )
    db.session.add(n)
    db.session.flush()
    return n


def _create_preference(*, user_id="test_user", category="system",
                        channel="in_app", digest_frequency="none",
                        email_address=None, is_enabled=True):
    """Create a NotificationPreference directly in DB."""
    from app.models.scheduling import NotificationPreference
    p = NotificationPreference(
        user_id=user_id, category=category, channel=channel,
        digest_frequency=digest_frequency, email_address=email_address,
        is_enabled=is_enabled,
    )
    db.session.add(p)
    db.session.flush()
    return p


def _create_scheduled_job(*, job_name="test_job", status="active", is_enabled=True):
    """Create a ScheduledJob directly in DB."""
    from app.models.scheduling import ScheduledJob
    j = ScheduledJob(
        job_name=job_name,
        description="Test job",
        schedule_type="cron",
        schedule_config={"hour": "0", "minute": "0"},
        status=status,
        is_enabled=is_enabled,
    )
    db.session.add(j)
    db.session.flush()
    return j


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 1: NotificationPreference Model
# ═══════════════════════════════════════════════════════════════════════════

class TestNotificationPreferenceModel:
    """Tests for NotificationPreference model."""

    def test_create_preference(self):
        pref = _create_preference(user_id="alice", category="risk", channel="email")
        assert pref.id is not None
        assert pref.user_id == "alice"
        assert pref.category == "risk"
        assert pref.channel == "email"
        assert pref.is_enabled is True

    def test_preference_to_dict(self):
        pref = _create_preference(user_id="bob", category="action",
                                   channel="both", digest_frequency="daily",
                                   email_address="bob@example.com")
        d = pref.to_dict()
        assert d["user_id"] == "bob"
        assert d["category"] == "action"
        assert d["channel"] == "both"
        assert d["digest_frequency"] == "daily"
        assert d["email_address"] == "bob@example.com"
        assert "created_at" in d

    def test_preference_defaults(self):
        pref = _create_preference()
        assert pref.channel == "in_app"
        assert pref.digest_frequency == "none"
        assert pref.email_address is None
        assert pref.is_enabled is True

    def test_preference_unique_constraint(self):
        from app.models.scheduling import NotificationPreference
        _create_preference(user_id="alice", category="risk")
        db.session.commit()
        # Duplicate should fail
        dup = NotificationPreference(
            user_id="alice", category="risk", channel="in_app",
            digest_frequency="none", is_enabled=True,
        )
        db.session.add(dup)
        with pytest.raises(Exception):
            db.session.flush()
        db.session.rollback()

    def test_preference_repr(self):
        pref = _create_preference(user_id="charlie", category="gate", channel="email")
        assert "charlie" in repr(pref)
        assert "gate" in repr(pref)


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 2: ScheduledJob Model
# ═══════════════════════════════════════════════════════════════════════════

class TestScheduledJobModel:
    """Tests for ScheduledJob model."""

    def test_create_job(self):
        job = _create_scheduled_job(job_name="daily_check")
        assert job.id is not None
        assert job.job_name == "daily_check"
        assert job.status == "active"
        assert job.run_count == 0

    def test_job_to_dict(self):
        job = _create_scheduled_job(job_name="weekly_report")
        d = job.to_dict()
        assert d["job_name"] == "weekly_report"
        assert d["status"] == "active"
        assert d["is_enabled"] is True
        assert d["run_count"] == 0
        assert d["error_count"] == 0

    def test_record_run_success(self):
        job = _create_scheduled_job(job_name="test_success")
        job.record_run(status="success", duration_ms=150, result={"count": 5})
        assert job.run_count == 1
        assert job.error_count == 0
        assert job.last_run_status == "success"
        assert job.last_run_duration_ms == 150
        assert job.last_run_result == {"count": 5}
        assert job.last_run_at is not None

    def test_record_run_failure(self):
        job = _create_scheduled_job(job_name="test_failure")
        job.record_run(status="failed", duration_ms=50, error="Connection refused")
        assert job.run_count == 1
        assert job.error_count == 1
        assert job.last_run_status == "failed"
        assert job.last_error == "Connection refused"

    def test_multiple_runs(self):
        job = _create_scheduled_job(job_name="multi_run")
        job.record_run(status="success", duration_ms=100)
        job.record_run(status="success", duration_ms=120)
        job.record_run(status="failed", duration_ms=50, error="timeout")
        assert job.run_count == 3
        assert job.error_count == 1

    def test_job_repr(self):
        job = _create_scheduled_job(job_name="my_job")
        assert "my_job" in repr(job)
        assert "active" in repr(job)


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 3: EmailLog Model
# ═══════════════════════════════════════════════════════════════════════════

class TestEmailLogModel:
    """Tests for EmailLog model."""

    def test_create_email_log(self):
        from app.models.scheduling import EmailLog
        log = EmailLog(
            recipient_email="test@example.com",
            recipient_name="Test User",
            subject="Test Subject",
            template_name="notification_alert",
            category="risk",
            status="sent",
        )
        db.session.add(log)
        db.session.flush()
        assert log.id is not None
        assert log.status == "sent"

    def test_email_log_to_dict(self):
        from app.models.scheduling import EmailLog
        log = EmailLog(
            recipient_email="alice@example.com",
            subject="Alert",
            status="failed",
            error_message="SMTP timeout",
        )
        db.session.add(log)
        db.session.flush()

        d = log.to_dict()
        assert d["recipient_email"] == "alice@example.com"
        assert d["status"] == "failed"
        assert d["error_message"] == "SMTP timeout"

    def test_email_log_repr(self):
        from app.models.scheduling import EmailLog
        log = EmailLog(
            recipient_email="bob@example.com",
            subject="Very Long Subject That Should Be Truncated At Forty Characters Ideally",
            status="queued",
        )
        db.session.add(log)
        db.session.flush()
        r = repr(log)
        assert "bob@example.com" in r


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 4: EmailService
# ═══════════════════════════════════════════════════════════════════════════

class TestEmailService:
    """Tests for EmailService."""

    def test_is_configured_false(self, app_ctx):
        """In testing mode, MAIL_SERVER is not set."""
        from app.services.email_service import EmailService
        assert EmailService.is_configured() is False

    def test_get_template_exists(self, app_ctx):
        from app.services.email_service import EmailService
        t = EmailService.get_template("notification_alert")
        assert t is not None
        assert "subject" in t
        assert "html" in t

    def test_get_template_missing(self, app_ctx):
        from app.services.email_service import EmailService
        assert EmailService.get_template("nonexistent") is None

    def test_send_dev_mode(self, app_ctx):
        """In dev/test mode, email is logged but not sent via SMTP."""
        from app.services.email_service import EmailService
        from app.models.scheduling import EmailLog

        log = EmailService.send(
            to_email="test@example.com",
            to_name="Test User",
            subject="Test Subject",
            html_body="<p>Hello</p>",
            template_name="notification_alert",
            category="risk",
        )
        db.session.commit()

        assert log.status == "sent"  # Dev mode simulates sent
        assert log.sent_at is not None
        assert log.recipient_email == "test@example.com"

        # Verify in DB
        stored = db.session.get(EmailLog, log.id)
        assert stored is not None
        assert stored.status == "sent"

    def test_send_from_template(self, app_ctx):
        from app.services.email_service import EmailService

        log = EmailService.send_from_template(
            to_email="alice@example.com",
            template_name="notification_alert",
            context={
                "title": "Risk Alert",
                "message": "High risk detected",
                "severity": "error",
                "severity_color": "#ef4444",
                "entity_link": "",
            },
            category="risk",
        )
        db.session.commit()

        assert log is not None
        assert "[SAP Platform] error: Risk Alert" in log.subject
        assert log.status == "sent"

    def test_send_from_template_missing(self, app_ctx):
        from app.services.email_service import EmailService

        log = EmailService.send_from_template(
            to_email="test@example.com",
            template_name="nonexistent_template",
            context={},
        )
        assert log is None

    def test_template_variables(self):
        """Test all defined templates have valid structure."""
        from app.services.email_service import _TEMPLATES
        assert len(_TEMPLATES) >= 4
        for name, tmpl in _TEMPLATES.items():
            assert "subject" in tmpl, f"Template {name} missing 'subject'"
            assert "html" in tmpl, f"Template {name} missing 'html'"


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 5: SchedulerService
# ═══════════════════════════════════════════════════════════════════════════

class TestSchedulerService:
    """Tests for SchedulerService."""

    def test_registered_jobs(self, app_ctx):
        from app.services.scheduler_service import get_registered_jobs
        jobs = get_registered_jobs()
        assert "overdue_scanner" in jobs
        assert "escalation_check" in jobs
        assert "daily_digest" in jobs
        assert "weekly_digest" in jobs
        assert "stale_notification_cleanup" in jobs
        assert "sla_compliance_check" in jobs
        assert len(jobs) >= 6

    def test_ensure_jobs_registered(self, app_ctx):
        from app.services.scheduler_service import SchedulerService
        from app.models.scheduling import ScheduledJob

        SchedulerService.init_app(app_ctx)
        created = SchedulerService.ensure_jobs_registered()

        # Should create DB records for all registered jobs
        assert len(created) >= 6

        # Verify via fresh query (objects may be detached after context exit)
        jobs = ScheduledJob.query.all()
        assert len(jobs) >= 6
        for job in jobs:
            assert job.id is not None
            assert job.status == "active"

        # Calling again should not create duplicates
        created2 = SchedulerService.ensure_jobs_registered()
        assert len(created2) == 0

    def test_list_jobs(self, app_ctx):
        from app.services.scheduler_service import SchedulerService
        SchedulerService.init_app(app_ctx)
        SchedulerService.ensure_jobs_registered()

        jobs = SchedulerService.list_jobs()
        assert len(jobs) >= 6
        for j in jobs:
            assert "job_name" in j
            assert j["registered"] is True

    def test_toggle_job(self, app_ctx):
        from app.services.scheduler_service import SchedulerService
        SchedulerService.init_app(app_ctx)
        _create_scheduled_job(job_name="toggle_test")
        db.session.commit()

        result = SchedulerService.toggle_job("toggle_test", False)
        assert result is not None
        assert result["status"] == "paused"
        assert result["is_enabled"] is False

        result2 = SchedulerService.toggle_job("toggle_test", True)
        assert result2["status"] == "active"
        assert result2["is_enabled"] is True

    def test_toggle_nonexistent_job(self, app_ctx):
        from app.services.scheduler_service import SchedulerService
        SchedulerService.init_app(app_ctx)
        result = SchedulerService.toggle_job("nonexistent", True)
        assert result is None

    def test_run_unknown_job(self, app_ctx):
        from app.services.scheduler_service import SchedulerService
        SchedulerService.init_app(app_ctx)
        result = SchedulerService.run_job("unknown_job_xyz")
        assert result["status"] == "error"
        assert "Unknown job" in result["error"]

    def test_get_job_status(self, app_ctx):
        from app.services.scheduler_service import SchedulerService
        SchedulerService.init_app(app_ctx)
        _create_scheduled_job(job_name="status_test")
        db.session.commit()

        status = SchedulerService.get_job_status("status_test")
        assert status is not None
        assert status["job_name"] == "status_test"


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 6: Scheduled Job Execution
# ═══════════════════════════════════════════════════════════════════════════

class TestScheduledJobExecution:
    """Tests for individual job execution."""

    def test_stale_cleanup(self, app_ctx):
        """Test stale notification cleanup job."""
        from app.services.scheduled_jobs import cleanup_stale_notifications
        from app.models.notification import Notification

        # Create old read notification
        old_notif = Notification(
            title="Old Read", message="", category="system", severity="info",
            is_read=True, read_at=datetime.now(timezone.utc) - timedelta(days=60),
            created_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        # Create recent read notification (should NOT be deleted)
        recent_notif = Notification(
            title="Recent Read", message="", category="system", severity="info",
            is_read=True, read_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        # Create unread notification (should NOT be deleted)
        unread_notif = Notification(
            title="Unread", message="", category="system", severity="info",
            is_read=False,
            created_at=datetime.now(timezone.utc) - timedelta(days=60),
        )
        db.session.add_all([old_notif, recent_notif, unread_notif])
        db.session.commit()

        result = cleanup_stale_notifications(app_ctx)
        assert result["deleted"] == 1

        # Verify only the old read one was deleted
        remaining = Notification.query.all()
        assert len(remaining) == 2
        assert all(n.title != "Old Read" for n in remaining)

    def test_overdue_scanner_no_items(self, app_ctx):
        """Test overdue scanner when nothing is overdue."""
        from app.services.scheduled_jobs import scan_overdue_items
        result = scan_overdue_items(app_ctx)
        assert result["actions_overdue"] == 0
        assert result["open_items_overdue"] == 0

    def test_sla_compliance_no_slas(self, app_ctx):
        """Test SLA check with no active SLAs."""
        from app.services.scheduled_jobs import check_sla_compliance
        result = check_sla_compliance(app_ctx)
        assert result["slas_checked"] == 0

    def test_daily_digest_no_prefs(self, app_ctx):
        """Test daily digest when no users have daily digest preference."""
        from app.services.scheduled_jobs import send_daily_digest
        result = send_daily_digest(app_ctx)
        assert result["users_processed"] == 0
        assert result["emails_sent"] == 0

    def test_weekly_digest_no_prefs(self, app_ctx):
        """Test weekly digest when no users have weekly preference."""
        from app.services.scheduled_jobs import send_weekly_digest
        result = send_weekly_digest(app_ctx)
        assert result["users_processed"] == 0

    def test_daily_digest_with_prefs(self, app_ctx):
        """Test daily digest sends email when user has preference."""
        from app.services.scheduled_jobs import send_daily_digest
        from app.models.scheduling import NotificationPreference, EmailLog
        from app.models.notification import Notification

        # Create user preference for daily digest
        pref = NotificationPreference(
            user_id="digest_user", category="risk",
            channel="email", digest_frequency="daily",
            email_address="digest@example.com",
        )
        db.session.add(pref)

        # Create a recent notification for this user
        n = Notification(
            title="Risk Alert", message="Something happened",
            category="risk", severity="warning", recipient="digest_user",
        )
        db.session.add(n)
        db.session.commit()

        result = send_daily_digest(app_ctx)
        assert result["users_processed"] == 1
        assert result["emails_sent"] == 1

        # Verify email log
        logs = EmailLog.query.all()
        assert len(logs) == 1
        assert logs[0].recipient_email == "digest@example.com"

    def test_escalation_check(self, app_ctx):
        """Test escalation check runs without errors."""
        from app.services.scheduled_jobs import run_escalation_check
        result = run_escalation_check(app_ctx)
        assert "programs_checked" in result
        assert "alerts_created" in result


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 7: Notification Blueprint — CRUD
# ═══════════════════════════════════════════════════════════════════════════

class TestNotificationCRUD:
    """Tests for notification CRUD endpoints."""

    def test_create_notification(self, client):
        res = client.post("/api/v1/notifications", json={
            "title": "Test Alert",
            "message": "Something happened",
            "category": "risk",
            "severity": "warning",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["title"] == "Test Alert"
        assert data["category"] == "risk"
        assert data["severity"] == "warning"

    def test_create_notification_no_title(self, client):
        res = client.post("/api/v1/notifications", json={"message": "no title"})
        assert res.status_code == 400
        assert "title" in res.get_json()["error"]

    def test_create_notification_invalid_category(self, client):
        res = client.post("/api/v1/notifications", json={
            "title": "Test", "category": "invalid_cat",
        })
        assert res.status_code == 400

    def test_create_notification_invalid_severity(self, client):
        res = client.post("/api/v1/notifications", json={
            "title": "Test", "severity": "ultra_critical",
        })
        assert res.status_code == 400

    def test_get_notification(self, client):
        # Create first
        res = client.post("/api/v1/notifications", json={
            "title": "Get Test", "category": "system",
        })
        nid = res.get_json()["id"]

        res2 = client.get(f"/api/v1/notifications/{nid}")
        assert res2.status_code == 200
        assert res2.get_json()["title"] == "Get Test"

    def test_get_notification_not_found(self, client):
        res = client.get("/api/v1/notifications/99999")
        assert res.status_code == 404

    def test_delete_notification(self, client):
        res = client.post("/api/v1/notifications", json={
            "title": "Delete Me",
        })
        nid = res.get_json()["id"]

        res2 = client.delete(f"/api/v1/notifications/{nid}")
        assert res2.status_code == 200
        assert res2.get_json()["deleted"] is True

        # Verify deleted
        res3 = client.get(f"/api/v1/notifications/{nid}")
        assert res3.status_code == 404

    def test_delete_notification_not_found(self, client):
        res = client.delete("/api/v1/notifications/99999")
        assert res.status_code == 404

    def test_broadcast_notification(self, client):
        res = client.post("/api/v1/notifications/broadcast", json={
            "title": "Broadcast Alert",
            "message": "For everyone",
            "recipients": ["alice", "bob", "charlie"],
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["broadcast"] is True
        assert data["count"] == 3

    def test_broadcast_no_title(self, client):
        res = client.post("/api/v1/notifications/broadcast", json={
            "message": "no title",
        })
        assert res.status_code == 400

    def test_notification_stats(self, client):
        # Create some notifications
        for sev in ["info", "warning", "error"]:
            client.post("/api/v1/notifications", json={
                "title": f"Alert {sev}", "severity": sev, "category": "risk",
            })

        res = client.get("/api/v1/notifications/stats")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 3
        assert data["unread"] == 3
        assert "by_category" in data
        assert "by_severity" in data


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 8: Notification Blueprint — Preferences
# ═══════════════════════════════════════════════════════════════════════════

class TestNotificationPreferencesAPI:
    """Tests for notification preferences API."""

    def test_list_preferences_empty(self, client):
        res = client.get("/api/v1/notification-preferences?user_id=alice")
        assert res.status_code == 200
        data = res.get_json()
        assert data["user_id"] == "alice"
        assert len(data["preferences"]) == 0

    def test_list_preferences_no_user(self, client):
        res = client.get("/api/v1/notification-preferences")
        assert res.status_code == 400

    def test_create_preference_api(self, client):
        res = client.post("/api/v1/notification-preferences", json={
            "user_id": "alice",
            "category": "risk",
            "channel": "email",
            "digest_frequency": "daily",
            "email_address": "alice@example.com",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["user_id"] == "alice"
        assert data["channel"] == "email"
        assert data["digest_frequency"] == "daily"

    def test_update_preference_api(self, client):
        # Create
        client.post("/api/v1/notification-preferences", json={
            "user_id": "bob", "category": "action", "channel": "in_app",
        })

        # Update (same user_id + category = upsert)
        res = client.post("/api/v1/notification-preferences", json={
            "user_id": "bob", "category": "action", "channel": "both",
            "digest_frequency": "weekly",
        })
        assert res.status_code == 200
        assert res.get_json()["channel"] == "both"
        assert res.get_json()["digest_frequency"] == "weekly"

    def test_create_preference_invalid_channel(self, client):
        res = client.post("/api/v1/notification-preferences", json={
            "user_id": "alice", "category": "risk", "channel": "pigeon",
        })
        assert res.status_code == 400

    def test_create_preference_invalid_digest(self, client):
        res = client.post("/api/v1/notification-preferences", json={
            "user_id": "alice", "category": "risk", "digest_frequency": "hourly",
        })
        assert res.status_code == 400

    def test_create_preference_no_user(self, client):
        res = client.post("/api/v1/notification-preferences", json={
            "category": "risk",
        })
        assert res.status_code == 400

    def test_create_preference_no_category(self, client):
        res = client.post("/api/v1/notification-preferences", json={
            "user_id": "alice",
        })
        assert res.status_code == 400

    def test_bulk_update_preferences(self, client):
        res = client.post("/api/v1/notification-preferences/bulk", json={
            "user_id": "alice",
            "preferences": [
                {"category": "risk", "channel": "email", "digest_frequency": "daily"},
                {"category": "action", "channel": "both"},
                {"category": "system", "channel": "none"},
            ],
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["updated"] == 3
        assert len(data["preferences"]) == 3

    def test_bulk_update_no_user(self, client):
        res = client.post("/api/v1/notification-preferences/bulk", json={
            "preferences": [{"category": "risk"}],
        })
        assert res.status_code == 400

    def test_bulk_update_no_prefs(self, client):
        res = client.post("/api/v1/notification-preferences/bulk", json={
            "user_id": "alice",
        })
        assert res.status_code == 400

    def test_delete_preference(self, client):
        res = client.post("/api/v1/notification-preferences", json={
            "user_id": "alice", "category": "risk", "channel": "email",
        })
        pref_id = res.get_json()["id"]

        res2 = client.delete(f"/api/v1/notification-preferences/{pref_id}")
        assert res2.status_code == 200
        assert res2.get_json()["deleted"] is True

    def test_delete_preference_not_found(self, client):
        res = client.delete("/api/v1/notification-preferences/99999")
        assert res.status_code == 404

    def test_list_after_create(self, client):
        client.post("/api/v1/notification-preferences", json={
            "user_id": "charlie", "category": "risk", "channel": "email",
        })
        client.post("/api/v1/notification-preferences", json={
            "user_id": "charlie", "category": "action", "channel": "in_app",
        })

        res = client.get("/api/v1/notification-preferences?user_id=charlie")
        assert res.status_code == 200
        assert len(res.get_json()["preferences"]) == 2


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 9: Notification Blueprint — Scheduler API
# ═══════════════════════════════════════════════════════════════════════════

class TestSchedulerAPI:
    """Tests for scheduler management API."""

    def test_list_jobs(self, client):
        _create_scheduled_job(job_name="test_list_a")
        _create_scheduled_job(job_name="test_list_b")
        db.session.commit()

        res = client.get("/api/v1/scheduler/jobs")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] >= 2

    def test_get_job_status(self, client):
        _create_scheduled_job(job_name="status_api_test")
        db.session.commit()

        res = client.get("/api/v1/scheduler/jobs/status_api_test")
        assert res.status_code == 200
        assert res.get_json()["job_name"] == "status_api_test"

    def test_get_job_not_found(self, client):
        res = client.get("/api/v1/scheduler/jobs/nonexistent")
        assert res.status_code == 404

    def test_trigger_job(self, client, app_ctx):
        from app.services.scheduler_service import SchedulerService
        SchedulerService.init_app(app_ctx)
        _create_scheduled_job(job_name="stale_notification_cleanup")
        db.session.commit()

        res = client.post("/api/v1/scheduler/jobs/stale_notification_cleanup/trigger")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert "duration_ms" in data

    def test_trigger_unknown_job(self, client, app_ctx):
        from app.services.scheduler_service import SchedulerService
        SchedulerService.init_app(app_ctx)

        res = client.post("/api/v1/scheduler/jobs/nonexistent_job_xyz/trigger")
        assert res.status_code == 404

    def test_toggle_job_api(self, client):
        _create_scheduled_job(job_name="toggle_api_test")
        db.session.commit()

        # Disable
        res = client.patch("/api/v1/scheduler/jobs/toggle_api_test/toggle",
                           json={"enabled": False})
        assert res.status_code == 200
        assert res.get_json()["status"] == "paused"

        # Enable
        res2 = client.patch("/api/v1/scheduler/jobs/toggle_api_test/toggle",
                            json={"enabled": True})
        assert res2.status_code == 200
        assert res2.get_json()["status"] == "active"

    def test_toggle_job_no_enabled_field(self, client):
        _create_scheduled_job(job_name="toggle_missing")
        db.session.commit()

        res = client.patch("/api/v1/scheduler/jobs/toggle_missing/toggle", json={})
        assert res.status_code == 400

    def test_toggle_job_not_found(self, client):
        res = client.patch("/api/v1/scheduler/jobs/nonexistent/toggle",
                           json={"enabled": True})
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 10: Notification Blueprint — Email Logs
# ═══════════════════════════════════════════════════════════════════════════

class TestEmailLogAPI:
    """Tests for email log API."""

    def test_list_empty(self, client):
        res = client.get("/api/v1/email-logs")
        assert res.status_code == 200
        assert res.get_json()["total"] == 0

    def test_list_with_data(self, client):
        from app.models.scheduling import EmailLog
        for i in range(3):
            db.session.add(EmailLog(
                recipient_email=f"user{i}@example.com",
                subject=f"Test {i}",
                status="sent",
            ))
        db.session.commit()

        res = client.get("/api/v1/email-logs")
        assert res.status_code == 200
        assert res.get_json()["total"] == 3

    def test_list_filter_status(self, client):
        from app.models.scheduling import EmailLog
        db.session.add(EmailLog(recipient_email="a@b.com", subject="1", status="sent"))
        db.session.add(EmailLog(recipient_email="b@b.com", subject="2", status="failed"))
        db.session.commit()

        res = client.get("/api/v1/email-logs?status=sent")
        assert res.status_code == 200
        assert res.get_json()["total"] == 1

    def test_email_stats_empty(self, client):
        res = client.get("/api/v1/email-logs/stats")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] == 0
        assert data["success_rate"] == 0

    def test_email_stats_with_data(self, client):
        from app.models.scheduling import EmailLog
        for s in ["sent", "sent", "failed"]:
            db.session.add(EmailLog(
                recipient_email="x@y.com", subject="T", status=s,
            ))
        db.session.commit()

        res = client.get("/api/v1/email-logs/stats")
        data = res.get_json()
        assert data["total"] == 3
        assert data["sent"] == 2
        assert data["failed"] == 1
        assert data["success_rate"] == pytest.approx(66.7, abs=0.1)


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 11: Email Delivery Integration
# ═══════════════════════════════════════════════════════════════════════════

class TestEmailDeliveryIntegration:
    """Tests for email delivery triggered by notification creation."""

    def test_notification_with_email_preference(self, client):
        """Creating a notification for a user with email preference should log email."""
        from app.models.scheduling import EmailLog

        # Set up preference for user
        client.post("/api/v1/notification-preferences", json={
            "user_id": "email_user",
            "category": "risk",
            "channel": "email",
            "email_address": "email_user@example.com",
        })

        # Create notification for this user
        res = client.post("/api/v1/notifications", json={
            "title": "Risk Warning",
            "category": "risk",
            "severity": "warning",
            "recipient": "email_user",
        })
        assert res.status_code == 201

        # Check email was logged
        logs = EmailLog.query.all()
        assert len(logs) == 1
        assert logs[0].recipient_email == "email_user@example.com"

    def test_notification_without_email_preference(self, client):
        """Notification without email preference should not create email log."""
        from app.models.scheduling import EmailLog

        res = client.post("/api/v1/notifications", json={
            "title": "System Alert",
            "category": "system",
            "recipient": "no_pref_user",
        })
        assert res.status_code == 201

        logs = EmailLog.query.all()
        assert len(logs) == 0

    def test_broadcast_does_not_trigger_email(self, client):
        """Broadcast notifications should not trigger individual emails."""
        from app.models.scheduling import EmailLog

        res = client.post("/api/v1/notifications", json={
            "title": "Broadcast",
            "recipient": "all",
        })
        assert res.status_code == 201

        logs = EmailLog.query.all()
        assert len(logs) == 0


# ═══════════════════════════════════════════════════════════════════════════
#  TEST CLASS 12: Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge case tests."""

    def test_constants_exist(self):
        from app.models.scheduling import (
            CHANNEL_TYPES, DIGEST_FREQUENCIES, JOB_STATUSES, EMAIL_STATUSES,
        )
        assert "in_app" in CHANNEL_TYPES
        assert "email" in CHANNEL_TYPES
        assert "both" in CHANNEL_TYPES
        assert "none" in CHANNEL_TYPES
        assert "daily" in DIGEST_FREQUENCIES
        assert "weekly" in DIGEST_FREQUENCIES
        assert "active" in JOB_STATUSES
        assert "paused" in JOB_STATUSES
        assert "sent" in EMAIL_STATUSES
        assert "failed" in EMAIL_STATUSES

    def test_safe_dict_missing_key(self):
        from app.services.email_service import _SafeDict
        d = _SafeDict({"a": 1})
        assert d["a"] == 1
        assert d["missing"] == "{missing}"

    def test_severity_colors(self):
        from app.services.email_service import SEVERITY_COLORS
        assert "info" in SEVERITY_COLORS
        assert "error" in SEVERITY_COLORS
        assert all(c.startswith("#") for c in SEVERITY_COLORS.values())

    def test_scheduler_not_initialized(self):
        """SchedulerService should handle being called without init."""
        from app.services.scheduler_service import SchedulerService
        # Temporarily clear the app
        old_app = SchedulerService._app
        SchedulerService._app = None
        try:
            result = SchedulerService.run_job("overdue_scanner")
            assert result["status"] == "error"
            assert "not initialized" in result["error"]
        finally:
            SchedulerService._app = old_app

    def test_default_schedule_known_jobs(self):
        from app.services.scheduler_service import _get_default_schedule
        sched = _get_default_schedule("overdue_scanner")
        assert "hour" in sched
        sched2 = _get_default_schedule("unknown_new_job")
        assert "hour" in sched2  # Falls back to midnight
