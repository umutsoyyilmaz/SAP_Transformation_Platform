"""F10 — External Integrations & Public API models."""

from datetime import datetime, timezone
import uuid

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

try:
    from sqlalchemy import JSON
except ImportError:
    from sqlalchemy.types import JSON


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


# ── 10.1 Jira Integration ────────────────────────────────────────

class JiraIntegration(db.Model):
    """Jira project connection."""

    __tablename__ = "jira_integrations"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"))
    jira_url = Column(String(500), default="")
    project_key = Column(String(20), default="")
    auth_type = Column(String(20), default="api_token")  # oauth2 | api_token | basic
    credentials = Column(Text, default="")  # Encrypted
    field_mapping = Column(JSON, default=dict)
    sync_config = Column(
        JSON, default=lambda: {"direction": "bidirectional", "interval": 300}
    )
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String(30), default="idle")  # idle | syncing | error
    sync_error = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "jira_url": self.jira_url,
            "project_key": self.project_key,
            "auth_type": self.auth_type,
            "field_mapping": self.field_mapping or {},
            "sync_config": self.sync_config or {},
            "is_active": self.is_active,
            "last_sync_at": self.last_sync_at.isoformat()
            if self.last_sync_at
            else None,
            "sync_status": self.sync_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── 10.2 Automation Import Job ────────────────────────────────────

class AutomationImportJob(db.Model):
    """Async automation result import job."""

    __tablename__ = "automation_import_jobs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=True)
    request_id = Column(String(36), unique=True, index=True, default=_uuid)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"))
    source = Column(
        String(30), default="manual"
    )  # jenkins | github_actions | azure_devops | gitlab | manual
    build_id = Column(String(100), default="")
    entity_type = Column(
        String(20), default="junit"
    )  # junit | testng | cucumber | robot | hpuft | qaf | csv
    file_path = Column(String(500), default="")
    file_size = Column(Integer, default=0)
    status = Column(
        String(20), default="queued"
    )  # queued | processing | completed | failed
    result_summary = Column(JSON, default=dict)
    test_suite_id = Column(Integer, nullable=True)
    error_message = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(200), default="system")

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "request_id": self.request_id,
            "program_id": self.program_id,
            "source": self.source,
            "build_id": self.build_id,
            "entity_type": self.entity_type,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "status": self.status,
            "result_summary": self.result_summary or {},
            "test_suite_id": self.test_suite_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "created_by": self.created_by,
        }


# ── 10.3 Webhook Subscription & Delivery ─────────────────────────

class WebhookSubscription(db.Model):
    """Outbound webhook subscription."""

    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"))
    name = Column(String(100), default="")
    url = Column(String(500), nullable=False)
    secret = Column(String(100), default="")  # HMAC signing secret
    events = Column(JSON, default=list)  # ["defect.created", ...]
    headers = Column(JSON, default=dict)  # Custom headers
    is_active = Column(Boolean, default=True)
    retry_config = Column(
        JSON,
        default=lambda: {"max_retries": 3, "backoff_seconds": [5, 30, 120]},
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    deliveries = relationship(
        "WebhookDelivery",
        backref="subscription",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "program_id": self.program_id,
            "name": self.name,
            "url": self.url,
            "events": self.events or [],
            "headers": self.headers or {},
            "is_active": self.is_active,
            "retry_config": self.retry_config or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WebhookDelivery(db.Model):
    """Webhook delivery attempt log."""

    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=True)
    subscription_id = Column(
        Integer,
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
    )
    event_type = Column(String(50), default="")
    payload = Column(JSON, default=dict)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, default="")
    attempt_no = Column(Integer, default=1)
    delivered_at = Column(DateTime(timezone=True), default=_utcnow)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "event_type": self.event_type,
            "payload": self.payload or {},
            "response_status": self.response_status,
            "response_body": self.response_body,
            "attempt_no": self.attempt_no,
            "delivered_at": self.delivered_at.isoformat()
            if self.delivered_at
            else None,
        }


# ── S4-02: CloudALMConfig — SAP Cloud ALM connection config (FDD-F07 Faz B) ──

class CloudALMConfig(db.Model):
    """SAP Cloud ALM OAuth2 connection configuration, one row per tenant.

    Security contract:
      - `client_secret` is NEVER stored plaintext.  It is encrypted at the
        service layer via `app.utils.crypto.encrypt_secret()` and stored in
        `encrypted_secret`.
      - `to_dict()` explicitly excludes `encrypted_secret` via SENSITIVE_FIELDS.
      - Any change to this model must preserve that exclusion.

    Lifecycle:
      draft (not yet tested) → active (test_connection ok) → error (test failed)
    """

    __tablename__ = "cloud_alm_configs"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="One config per tenant — enforced by unique constraint",
    )
    alm_url = Column(
        String(500),
        nullable=False,
        comment="SAP Cloud ALM base URL: https://<tenant>.alm.cloud.sap",
    )
    client_id = Column(String(200), nullable=False, comment="OAuth2 client_id")
    encrypted_secret = Column(
        Text,
        nullable=False,
        comment="Fernet-encrypted OAuth2 client_secret — never plaintext",
    )
    token_url = Column(
        String(500),
        nullable=False,
        comment="OAuth2 token endpoint: https://<auth-server>/oauth/token",
    )
    sync_requirements = Column(Boolean, nullable=False, default=True)
    sync_test_results = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_test_at = Column(DateTime(timezone=True), nullable=True)
    last_test_status = Column(
        String(20),
        nullable=True,
        comment="ok | error | timeout",
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    SENSITIVE_FIELDS: frozenset[str] = frozenset({"encrypted_secret"})

    def to_dict(self) -> dict:
        """Serialise config excluding the encrypted secret.

        Security: encrypted_secret is in SENSITIVE_FIELDS and must NEVER
        appear in any API response — even to admins.  The secret is write-only
        from the API perspective.
        """
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name not in self.SENSITIVE_FIELDS
        }

