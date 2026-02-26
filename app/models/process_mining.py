"""S8-01 FDD-I05 Phase B — Process Mining data models.

Two models:
  ProcessMiningConnection — one per tenant, stores encrypted provider credentials.
  ProcessVariantImport    — process variants fetched from the mining provider and
                            linked to a project (program) for promote/reject workflow.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── ProcessMiningConnection ──────────────────────────────────────────────────


class ProcessMiningConnection(db.Model):
    """Stores connection credentials for one process-mining provider per tenant.

    Design decisions:
    - One connection per tenant (unique constraint on tenant_id) — keeps the UX
      simple; tenants connect to a single process mining system.
    - Encrypted credentials: both OAuth2 client_secret and API key are stored as
      Fernet-encrypted ciphertext. The raw values MUST NOT appear in logs or
      API responses — enforced by SENSITIVE_FIELDS and to_dict().
    - Status lifecycle: configured → testing → active → failed | disabled.
    """

    __tablename__ = "process_mining_connections"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", name="uq_pmc_tenant"),
        {"extend_existing": True},
    )

    SENSITIVE_FIELDS: frozenset[str] = frozenset({"encrypted_secret", "api_key_encrypted"})

    VALID_PROVIDERS = frozenset({"celonis", "signavio", "uipath", "sap_lama", "custom"})
    VALID_STATUSES = frozenset({"configured", "testing", "active", "failed", "disabled"})

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="One mining connection per tenant.",
    )
    provider = db.Column(
        db.String(30),
        nullable=False,
        default="celonis",
        comment="celonis | signavio | uipath | sap_lama | custom",
    )
    connection_url = db.Column(
        db.String(500),
        nullable=True,
        comment="Base API URL for the mining provider (e.g. https://tenant.celonis.cloud).",
    )
    client_id = db.Column(
        db.String(200),
        nullable=True,
        comment="OAuth2 client_id (used by Signavio).",
    )
    encrypted_secret = db.Column(
        db.Text,
        nullable=True,
        comment="Fernet-encrypted OAuth2 client_secret. NEVER log or expose.",
    )
    api_key_encrypted = db.Column(
        db.Text,
        nullable=True,
        comment="Fernet-encrypted API key (used by Celonis). NEVER log or expose.",
    )
    token_url = db.Column(
        db.String(500),
        nullable=True,
        comment="OAuth2 token endpoint (required for Signavio).",
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="configured",
        comment="configured | testing | active | failed | disabled",
    )
    last_tested_at = db.Column(db.DateTime, nullable=True)
    last_sync_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(
        db.String(500),
        nullable=True,
        comment="Most recent error response from provider (truncated to 500 chars).",
    )
    is_enabled = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    variant_imports = db.relationship(
        "ProcessVariantImport",
        back_populates="connection",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """Serialize to dict, excluding all encrypted credential fields.

        Security: SENSITIVE_FIELDS ensures raw and encrypted secrets never
        reach API responses or log serialisation. Adding a new credential
        column requires updating SENSITIVE_FIELDS.
        """
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name not in self.SENSITIVE_FIELDS
        }


# ── ProcessVariantImport ─────────────────────────────────────────────────────


class ProcessVariantImport(db.Model):
    """A process variant fetched from the mining provider and stored per project.

    Lifecycle: imported → reviewed → promoted | rejected.
    Promoted variants become L4 process steps (process_levels) in the Explore module.

    Note on FK: project_id references programs.id (not "projects" — that table
    does not exist; FDD-I05 §4.2 contains a typo that is corrected here).
    Note on promoted_to_process_level_id: process_levels.id is a UUID String(36),
    so this FK is also String(36).
    """

    __tablename__ = "process_variant_imports"
    __table_args__ = (
        db.Index("idx_pvi_tenant_project", "tenant_id", "project_id"),
        db.Index("idx_pvi_tenant_program", "tenant_id", "program_id"),
        db.Index("idx_pvi_connection", "connection_id"),
        {"extend_existing": True},
    )

    VALID_STATUSES = frozenset({"imported", "reviewed", "promoted", "rejected"})

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant scope — mandatory for row-level isolation.",
    )
    program_id = db.Column(
        db.Integer,
        db.ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Correct FK to programs. Replaces legacy project_id -> programs.id naming.",
    )
    # Faz 1.4: Re-pointed from programs.id → projects.id (was naming bug).
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK → projects.id. Was incorrectly FK → programs.id before Faz 1.4.",
    )
    connection_id = db.Column(
        db.Integer,
        db.ForeignKey("process_mining_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    variant_id = db.Column(
        db.String(100),
        nullable=True,
        comment="Provider-side unique variant identifier.",
    )
    process_name = db.Column(db.String(255), nullable=True)
    sap_module_hint = db.Column(
        db.String(10),
        nullable=True,
        comment="Inferred SAP module code (e.g. FI, MM, SD).",
    )
    variant_count = db.Column(
        db.Integer,
        nullable=True,
        comment="Number of process instances following this variant.",
    )
    conformance_rate = db.Column(
        db.Numeric(5, 2),
        nullable=True,
        comment="0-100 conformance percentage from provider.",
    )
    steps_raw = db.Column(
        db.JSON,
        nullable=True,
        comment="Raw step list as returned by provider (preserved for reference).",
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="imported",
        comment="imported | reviewed | promoted | rejected",
    )
    promoted_to_process_level_id = db.Column(
        db.String(36),
        db.ForeignKey("process_levels.id", ondelete="SET NULL"),
        nullable=True,
        comment="UUID of the L4 ProcessLevel entry created on promote. process_levels.id is String(36).",
    )
    imported_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    connection = db.relationship(
        "ProcessMiningConnection",
        back_populates="variant_imports",
        lazy="select",
    )

    def to_dict(self) -> dict:
        """Serialize to dict. conformance_rate cast to float for JSON safety."""
        result = {}
        for c in self.__table__.columns:
            val = getattr(self, c.name)
            if hasattr(val, "__float__"):  # Decimal → float
                val = float(val)
            result[c.name] = val
        return result
