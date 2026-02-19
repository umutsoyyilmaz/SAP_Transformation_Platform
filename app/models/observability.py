"""F11 — Async Task Queue models and task status tracking.

Provides a TaskStatus model for tracking async job states,
plus stubs for Celery task definitions.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.models import db

try:
    from sqlalchemy import JSON
except ImportError:
    from sqlalchemy.types import JSON


def _utcnow():
    return datetime.now(timezone.utc)


class TaskStatus(db.Model):
    """Tracks status of async tasks."""

    __tablename__ = "task_statuses"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=True)
    task_id = Column(String(100), unique=True, index=True, nullable=False)
    task_type = Column(
        String(50), nullable=False, default="general"
    )  # automation_import | pdf_report | ai_analysis | bulk_op
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending | running | completed | failed | retrying
    progress = Column(Integer, default=0)  # 0-100
    result = Column(JSON, nullable=True)
    error_message = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(200), default="system")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by,
        }


class CacheStat(db.Model):
    """Tracks cache hit/miss statistics per tier."""

    __tablename__ = "cache_stats"

    id = Column(Integer, primary_key=True)
    tier = Column(String(30), nullable=False)
    cache_key = Column(String(200), nullable=False)
    hit = Column(Integer, nullable=False, default=0, server_default="0")
    miss = Column(Integer, nullable=False, default=0, server_default="0")
    last_hit_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "tier": self.tier,
            "cache_key": self.cache_key,
            "hit": self.hit,
            "miss": self.miss,
            "last_hit_at": self.last_hit_at.isoformat() if self.last_hit_at else None,
        }


class HealthCheckResult(db.Model):
    """Stores periodic health check results."""

    __tablename__ = "health_check_results"

    id = Column(Integer, primary_key=True)
    component = Column(String(50), nullable=False)  # database | redis | celery | storage
    status = Column(String(20), nullable=False, default="healthy")  # healthy | degraded | unhealthy
    response_time_ms = Column(Integer, default=0)
    details = Column(JSON, nullable=True)
    checked_at = Column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "component": self.component,
            "status": self.status,
            "response_time_ms": self.response_time_ms,
            "details": self.details,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }
