"""F8 — Exploratory Testing & Evidence Capture models."""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.models import db


def _utcnow():
    return datetime.now(timezone.utc)


# ── 8.1 Exploratory Session ──────────────────────────────────────

class ExploratorySession(db.Model):
    """Session-based exploratory test."""

    __tablename__ = "exploratory_sessions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    charter = Column(Text, default="")  # What to explore & why
    scope = Column(String(200), default="")  # Module/feature area
    time_box = Column(Integer, default=60)  # Minutes allocated
    tester_id = Column(
        Integer,
        ForeignKey("team_members.id", ondelete="SET NULL"),
        nullable=True,
    )
    tester_name = Column(String(100), default="")
    status = Column(String(20), default="draft")  # draft|active|paused|completed
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    actual_duration = Column(Integer, nullable=True)  # Actual minutes
    notes = Column(Text, default="")
    environment = Column(String(100), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    session_notes = relationship(
        "ExploratoryNote",
        backref="session",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="ExploratoryNote.timestamp",
    )

    def to_dict(self, include_notes=False):
        d = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "charter": self.charter,
            "scope": self.scope,
            "time_box": self.time_box,
            "tester_id": self.tester_id,
            "tester_name": self.tester_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "actual_duration": self.actual_duration,
            "notes": self.notes,
            "environment": self.environment,
            "note_count": self.session_notes.count() if self.session_notes else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_notes:
            d["session_notes"] = [n.to_dict() for n in self.session_notes.all()]
        return d


# ── 8.1b Exploratory Notes ───────────────────────────────────────

class ExploratoryNote(db.Model):
    """Time-stamped note during an exploratory session."""

    __tablename__ = "exploratory_notes"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id = Column(
        Integer,
        ForeignKey("exploratory_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note_type = Column(
        String(20), default="observation"
    )  # observation|bug|question|idea
    content = Column(Text, default="")
    screenshot_url = Column(String(500), default="")  # URL to screenshot
    timestamp = Column(DateTime(timezone=True), default=_utcnow)
    linked_defect_id = Column(
        Integer,
        nullable=True,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "note_type": self.note_type,
            "content": self.content,
            "screenshot_url": self.screenshot_url,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "linked_defect_id": self.linked_defect_id,
        }


# ── 8.2 Execution Evidence ───────────────────────────────────────

class ExecutionEvidence(db.Model):
    """Evidence attachment for step-level execution."""

    __tablename__ = "execution_evidence"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Can link to step result OR directly to execution
    step_result_id = Column(
        Integer,
        ForeignKey("test_step_results.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    execution_id = Column(
        Integer,
        ForeignKey("test_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    evidence_type = Column(
        String(20), default="screenshot"
    )  # screenshot|video|log|document|other
    file_name = Column(String(255), default="")
    file_path = Column(String(500), default="")  # Storage path
    file_size = Column(Integer, default=0)  # Bytes
    mime_type = Column(String(100), default="")
    thumbnail_path = Column(String(500), default="")
    captured_at = Column(DateTime(timezone=True), default=_utcnow)
    captured_by = Column(String(100), default="")
    description = Column(Text, default="")
    is_primary = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_ee_step", "step_result_id"),
        Index("ix_ee_execution", "execution_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "step_result_id": self.step_result_id,
            "execution_id": self.execution_id,
            "evidence_type": self.evidence_type,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "thumbnail_path": self.thumbnail_path,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "captured_by": self.captured_by,
            "description": self.description,
            "is_primary": self.is_primary,
        }
