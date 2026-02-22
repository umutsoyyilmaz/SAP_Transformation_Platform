"""
Transport/CTS Tracking domain models (FDD-I01 / S5-04).

SAP Change and Transport System (CTS) tracking for S/4HANA go-live projects.

Models:
    - TransportWave:       Logical grouping of transports for a target system/date
    - TransportRequest:    Individual SAP transport request (EKxK-format code)
    - TransportBacklogLink: N:M link table — transport ↔ backlog items

Architecture:
    Program ──1:N──▶ TransportWave ──1:N──▶ TransportRequest
    TransportRequest ──N:M──▶ BacklogItem (via TransportBacklogLink)

Transport number format: ^[A-Z]{3}K\\d{6}$ (e.g. DEVK900123)
"""

import re
from datetime import datetime, timezone

from app.models import db

# ── Constants ─────────────────────────────────────────────────────────────────

TRANSPORT_NUMBER_RE = re.compile(r"^[A-Z]{3}K\d{6}$")

TRANSPORT_TYPES = {"workbench", "customizing", "support_pkg", "transport_of_copies"}

TRANSPORT_STATUSES = {"created", "released", "imported", "failed", "locked"}

SYSTEMS = {"DEV", "QAS", "PRE", "PRD"}

WAVE_STATUSES = {"planned", "in_progress", "completed", "cancelled"}


def validate_transport_number(transport_number: str) -> bool:
    """Return True if the transport number matches SAP CTS format ^[A-Z]{3}K\\d{6}$."""
    return bool(TRANSPORT_NUMBER_RE.match(transport_number))


# ═════════════════════════════════════════════════════════════════════════════
# TransportWave
# ═════════════════════════════════════════════════════════════════════════════


class TransportWave(db.Model):
    """
    Logical grouping of transport requests destined for the same system on the same date.

    A wave represents a scheduled deployment window — e.g. 'Wave 1 → QAS on 2026-03-15'.
    Multiple waves may target different systems (QAS → PRE → PRD) across a go-live sequence.
    """

    __tablename__ = "transport_waves"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,  # Audit correction: nullable=False enforced
        index=True,
    )
    name = db.Column(db.String(100), nullable=False)
    target_system = db.Column(
        db.String(5),
        nullable=False,
        comment="QAS | PRE | PRD",
    )
    planned_date = db.Column(db.Date, nullable=True)
    actual_date = db.Column(db.Date, nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="planned",
        comment="planned | in_progress | completed | cancelled",
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    transports = db.relationship(
        "TransportRequest",
        backref="wave",
        lazy="select",
        cascade="all, delete-orphan",
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('planned','in_progress','completed','cancelled')",
            name="ck_transport_wave_status",
        ),
        db.Index("ix_twav_tenant_project", "tenant_id", "project_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "target_system": self.target_system,
            "planned_date": self.planned_date.isoformat() if self.planned_date else None,
            "actual_date": self.actual_date.isoformat() if self.actual_date else None,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<TransportWave {self.id}: {self.name} → {self.target_system}>"


# ═════════════════════════════════════════════════════════════════════════════
# TransportRequest
# ═════════════════════════════════════════════════════════════════════════════


class TransportRequest(db.Model):
    """
    Individual SAP transport request tracked during an S/4HANA go-live project.

    The transport_number must follow SAP CTS format: ^[A-Z]{3}K\\d{6}$
    (e.g. DEVK900123 — three-letter SID + K + 6 digits).

    import_log is a JSON array of events: [{system, status, imported_at, return_code}]
    Recording each import attempt allows full audit traceability across DEV→QAS→PRE→PRD.
    """

    __tablename__ = "transport_requests"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=False,  # Audit correction: nullable=False enforced
        index=True,
    )
    transport_number = db.Column(
        db.String(20),
        nullable=False,
        index=True,
        comment="SAP CTS format: ^[A-Z]{3}K\\d{6}$ e.g. DEVK900123",
    )
    transport_type = db.Column(
        db.String(30),
        nullable=False,
        comment="workbench | customizing | support_pkg | transport_of_copies",
    )
    description = db.Column(db.String(500), nullable=True)
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sap_module = db.Column(db.String(10), nullable=True, comment="e.g. FI, MM, SD")
    wave_id = db.Column(
        db.Integer,
        db.ForeignKey("transport_waves.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_system = db.Column(
        db.String(5),
        nullable=False,
        default="DEV",
        comment="DEV | QAS | PRE | PRD",
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="created",
        comment="created | released | imported | failed | locked",
    )
    release_date = db.Column(db.DateTime(timezone=True), nullable=True)
    import_log = db.Column(
        db.JSON,
        nullable=True,
        default=list,
        comment="[{system, status, imported_at, return_code}] — appended per import event",
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    backlog_items = db.relationship(
        "BacklogItem",
        secondary="transport_backlog_links",
        lazy="select",
        overlaps="transport_requests",
    )

    # ── Constraints ──────────────────────────────────────────────────────
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('created','released','imported','failed','locked')",
            name="ck_transport_req_status",
        ),
        db.CheckConstraint(
            "transport_type IN ('workbench','customizing','support_pkg','transport_of_copies')",
            name="ck_transport_req_type",
        ),
        db.Index("ix_treq_tenant_project", "tenant_id", "project_id"),
    )

    def to_dict(self, include_backlog: bool = False) -> dict:
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "tenant_id": self.tenant_id,
            "transport_number": self.transport_number,
            "transport_type": self.transport_type,
            "description": self.description,
            "owner_id": self.owner_id,
            "sap_module": self.sap_module,
            "wave_id": self.wave_id,
            "current_system": self.current_system,
            "status": self.status,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "import_log": self.import_log or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_backlog:
            result["backlog_item_ids"] = [b.id for b in self.backlog_items]
        return result

    def __repr__(self) -> str:
        return f"<TransportRequest {self.id}: {self.transport_number} [{self.status}]>"


# ═════════════════════════════════════════════════════════════════════════════
# TransportBacklogLink (N:M association)
# ═════════════════════════════════════════════════════════════════════════════


class TransportBacklogLink(db.Model):
    """
    N:M association between TransportRequest and BacklogItem.

    Tracks which backlog items (WRICEF objects, config items, etc.) are
    delivered by which transport request. This traceability is essential
    during cutover to prove all backlog scope has been transported.
    """

    __tablename__ = "transport_backlog_links"

    transport_id = db.Column(
        db.Integer,
        db.ForeignKey("transport_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    backlog_item_id = db.Column(
        db.Integer,
        db.ForeignKey("backlog_items.id", ondelete="CASCADE"),
        primary_key=True,
    )
    linked_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "transport_id": self.transport_id,
            "backlog_item_id": self.backlog_item_id,
            "linked_at": self.linked_at.isoformat() if self.linked_at else None,
        }
