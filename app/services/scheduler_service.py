"""
SAP Transformation Management Platform
Scheduler Service — Sprint 16.

Provides a lightweight background job scheduler using APScheduler-compatible
patterns, but implemented with a simple thread-based approach to avoid
adding heavy dependencies.

In production, this would be replaced by Celery/APScheduler.
In development/testing, jobs can be triggered manually via API.

Architecture:
    - SchedulerService: Manages job registration and execution
    - Jobs are stored in ScheduledJob model for persistence
    - Manual trigger API for development and testing
    - Pluggable job functions registered via decorator
"""

from __future__ import annotations

import logging
import time
import threading
from datetime import datetime, timezone
from typing import Callable

from flask import Flask

from app.models import db
from app.models.scheduling import ScheduledJob

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  Job Registry
# ═══════════════════════════════════════════════════════════════════════════

_job_registry: dict[str, Callable] = {}


def register_job(name: str):
    """Decorator to register a job function.

    Usage:
        @register_job("overdue_scanner")
        def scan_overdue_items(app):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        _job_registry[name] = fn
        return fn
    return decorator


def get_registered_jobs() -> dict[str, Callable]:
    """Return all registered job functions."""
    return dict(_job_registry)


class SchedulerService:
    """
    Lightweight scheduler service.

    Manages job registration, persistence, and execution.
    Jobs are executed within Flask app context.
    """

    _app: Flask | None = None
    _running: bool = False
    _thread: threading.Thread | None = None

    @classmethod
    def init_app(cls, app: Flask) -> None:
        """Initialize scheduler with Flask app context."""
        cls._app = app
        app.extensions["scheduler"] = cls
        logger.info("SchedulerService initialized with %d registered jobs",
                     len(_job_registry))

    @classmethod
    def ensure_jobs_registered(cls) -> list[ScheduledJob]:
        """
        Ensure all registered jobs have a corresponding DB record.
        Creates missing records with default config.
        """
        if not cls._app:
            return []

        created = []
        with cls._app.app_context():
            for name, _fn in _job_registry.items():
                existing = ScheduledJob.query.filter_by(job_name=name).first()
                if not existing:
                    job = ScheduledJob(
                        job_name=name,
                        description=_fn.__doc__ or f"Scheduled job: {name}",
                        schedule_type="cron",
                        schedule_config=_get_default_schedule(name),
                        status="active",
                        is_enabled=True,
                    )
                    db.session.add(job)
                    created.append(job)
            if created:
                db.session.commit()
                logger.info("Created %d scheduled job records", len(created))
        return created

    @classmethod
    def run_job(cls, job_name: str) -> dict:
        """
        Execute a single job by name.

        Returns:
            Dict with status, duration_ms, result or error.
        """
        fn = _job_registry.get(job_name)
        if not fn:
            return {"status": "error", "error": f"Unknown job: {job_name}"}

        if not cls._app:
            return {"status": "error", "error": "Scheduler not initialized"}

        start = time.monotonic()
        result = None
        error = None
        status = "success"

        try:
            with cls._app.app_context():
                result = fn(cls._app)
        except Exception as exc:
            status = "failed"
            error = str(exc)
            logger.exception("Job %s failed: %s", job_name, exc)

        duration_ms = int((time.monotonic() - start) * 1000)

        # Update DB record
        try:
            with cls._app.app_context():
                job_record = ScheduledJob.query.filter_by(job_name=job_name).first()
                if job_record:
                    job_record.record_run(
                        status=status,
                        duration_ms=duration_ms,
                        result=result if isinstance(result, dict) else {"output": str(result)},
                        error=error,
                    )
                    db.session.commit()
        except Exception:
            logger.exception("Failed to update job record for %s", job_name)

        return {
            "job_name": job_name,
            "status": status,
            "duration_ms": duration_ms,
            "result": result,
            "error": error,
        }

    @classmethod
    def list_jobs(cls) -> list[dict]:
        """List all registered jobs with their DB status."""
        jobs = []
        for name in _job_registry:
            job_record = ScheduledJob.query.filter_by(job_name=name).first()
            jobs.append({
                "job_name": name,
                "registered": True,
                "db_record": job_record.to_dict() if job_record else None,
            })
        return jobs

    @classmethod
    def get_job_status(cls, job_name: str) -> dict | None:
        """Get status of a specific job."""
        job_record = ScheduledJob.query.filter_by(job_name=job_name).first()
        if job_record:
            return job_record.to_dict()
        return None

    @classmethod
    def toggle_job(cls, job_name: str, enabled: bool) -> dict | None:
        """Enable or disable a scheduled job."""
        job_record = ScheduledJob.query.filter_by(job_name=job_name).first()
        if not job_record:
            return None
        job_record.is_enabled = enabled
        job_record.status = "active" if enabled else "paused"
        db.session.commit()
        return job_record.to_dict()


def _get_default_schedule(job_name: str) -> dict:
    """Return default schedule config for known job types."""
    defaults = {
        "overdue_scanner": {"hour": "8", "minute": "0", "description": "Daily at 08:00"},
        "escalation_check": {"hour": "9", "minute": "0", "description": "Daily at 09:00"},
        "daily_digest": {"hour": "7", "minute": "0", "description": "Daily at 07:00"},
        "weekly_digest": {"day_of_week": "mon", "hour": "8", "minute": "0",
                          "description": "Mondays at 08:00"},
        "stale_notification_cleanup": {"hour": "2", "minute": "0",
                                       "description": "Daily at 02:00"},
        "sla_compliance_check": {"hour": "*/4", "minute": "0",
                                 "description": "Every 4 hours"},
    }
    return defaults.get(job_name, {"hour": "0", "minute": "0",
                                    "description": "Daily at midnight"})
