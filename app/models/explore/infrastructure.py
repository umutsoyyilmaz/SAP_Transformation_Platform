"""
Explore Phase — Infrastructure Models

CloudALMSyncLog, Attachment, DailySnapshot.
"""

import uuid
from datetime import date, datetime, timezone

from app.models import db


__all__ = [
    "CloudALMSyncLog",
    "Attachment",
    "DailySnapshot",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


# ═════════════════════════════════════════════════════════════════════════════
# 13. CloudALMSyncLog — Sync audit trail (T-013)
# ═════════════════════════════════════════════════════════════════════════════

class CloudALMSyncLog(db.Model):
    """Audit log for SAP Cloud ALM synchronization of requirements."""

    __tablename__ = "cloud_alm_sync_logs"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requirement_id = db.Column(
        db.String(36), db.ForeignKey("explore_requirements.id", ondelete="CASCADE"),
        nullable=True, index=True,
        comment="Specific requirement for per-req logs; NULL for batch/test ops",
    )
    sync_direction = db.Column(
        db.String(5), nullable=False,
        comment="push | pull",
    )
    sync_status = db.Column(
        db.String(10), nullable=False,
        comment="success | error | partial",
    )
    alm_item_id = db.Column(db.String(50), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    payload = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    # ── S4-02 Phase B additions: richer audit trail ─────────────────────────
    http_status_code = db.Column(db.Integer, nullable=True, comment="HTTP status from ALM API")
    records_pushed = db.Column(db.Integer, nullable=True, comment="Count of records sent to ALM")
    records_pulled = db.Column(db.Integer, nullable=True, comment="Count of records received from ALM")
    duration_ms = db.Column(db.Integer, nullable=True, comment="Round-trip latency in milliseconds")
    triggered_by = db.Column(
        db.String(20), nullable=True,
        comment="manual | scheduled | webhook",
    )
    user_id = db.Column(db.Integer, nullable=True, comment="User who triggered the sync (FK → users.id)")
    payload_hash = db.Column(
        db.String(64), nullable=True,
        comment="SHA-256 hex digest of the serialised payload for integrity audit",
    )
    project_id = db.Column(
        db.Integer, nullable=True, index=True,
        comment="Program/project scope — enables sync-log listing by project",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "requirement_id": self.requirement_id,
            "project_id": self.project_id,
            "sync_direction": self.sync_direction,
            "sync_status": self.sync_status,
            "alm_item_id": self.alm_item_id,
            "error_message": self.error_message,
            "http_status_code": self.http_status_code,
            "records_pushed": self.records_pushed,
            "records_pulled": self.records_pulled,
            "duration_ms": self.duration_ms,
            "triggered_by": self.triggered_by,
            "user_id": self.user_id,
            "payload_hash": self.payload_hash,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<CloudALMSyncLog {self.id[:8]} {self.sync_direction}:{self.sync_status}>"


# ═════════════════════════════════════════════════════════════════════════════
# 20. Attachment — Polymorphic file attachments (T-019, GAP-07)
# ═════════════════════════════════════════════════════════════════════════════

class Attachment(db.Model):
    """
    Polymorphic file attachment — can be linked to any explore entity
    (workshop, process_step, requirement, open_item, decision, process_level).

    Uses entity_type + entity_id pattern for polymorphic association.
    """

    __tablename__ = "attachments"
    __table_args__ = (
        db.Index(
            "idx_att_entity", "entity_type", "entity_id",
        ),
        db.Index("idx_att_project", "project_id"),
        db.Index("idx_att_program", "program_id"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Correct FK to programs. Replaces legacy project_id -> programs.id naming.",
    )
    # LEGACY: project_id currently FK -> programs.id (naming bug).
    project_id = db.Column(
        db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    entity_type = db.Column(
        db.String(20), nullable=False,
        comment="workshop | process_step | requirement | open_item | decision | process_level",
    )
    entity_id = db.Column(
        db.String(36), nullable=False,
        comment="UUID of the parent entity",
    )
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False, comment="Server storage path")
    file_size = db.Column(db.Integer, nullable=True, comment="Size in bytes")
    mime_type = db.Column(db.String(100), nullable=True)
    category = db.Column(
        db.String(20), nullable=False, default="general",
        comment="screenshot | bpmn_diagram | test_evidence | meeting_notes | config_doc | design_doc | general",
    )
    description = db.Column(db.Text, nullable=True)
    uploaded_by = db.Column(db.String(36), nullable=False, comment="FK → user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "project_id": self.project_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "category": self.category,
            "description": self.description,
            "uploaded_by": self.uploaded_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Attachment {self.file_name} on {self.entity_type}:{self.entity_id[:8]}>"


# ═════════════════════════════════════════════════════════════════════════════
# 25. DailySnapshot — Daily project metrics snapshot [GAP-08] (T-022)
# ═════════════════════════════════════════════════════════════════════════════

class DailySnapshot(db.Model):
    """Stores daily aggregated metrics for project dashboards & trend charts."""

    __tablename__ = "daily_snapshots"
    __table_args__ = (
        db.UniqueConstraint("project_id", "snapshot_date", name="uq_snapshot_project_date"),
    )

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_id = db.Column(
        db.String(36), nullable=False, index=True,
        comment="FK → programs",
    )
    snapshot_date = db.Column(db.Date, nullable=False, default=date.today)
    metrics = db.Column(db.Text, nullable=True, comment="JSON blob of metrics")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "project_id": self.project_id,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "metrics": json.loads(self.metrics) if self.metrics else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<DailySnapshot {self.project_id} {self.snapshot_date}>"
