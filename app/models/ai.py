"""
SAP Transformation Management Platform
AI domain models — Sprint 7 + 9.5 KB Versioning + S19 Multi-turn + S20 Perf + S21 Final.

Models:
    - AIUsageLog: Token/cost tracking per LLM call
    - AIEmbedding: Vector store for RAG (pgvector-ready, SQLite-safe)
    - AISuggestion: AI recommendation queue (approve/reject workflow)
    - AIAuditLog: Full audit trail for every AI invocation
    - KBVersion: Knowledge Base version tracking
    - AIConversation: Multi-turn conversation session (Sprint 19)
    - AIConversationMessage: Individual messages within a conversation (Sprint 19)
    - AIResponseCache: LLM response cache with TTL (Sprint 20)
    - AITokenBudget: Per-program/user token budget tracking (Sprint 20)
    - AIFeedbackMetric: Per-assistant accuracy & feedback tracking (Sprint 21)
    - AITask: Async AI task tracking with progress (Sprint 21)
"""

import hashlib
from datetime import datetime, timezone

from app.models import db


# ── Constants ────────────────────────────────────────────────────────────────

AI_PROVIDERS = {"anthropic", "openai", "local"}
AI_MODELS = {
    "claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229",
    "gpt-4o-mini", "gpt-4o", "gpt-4-turbo",
    "text-embedding-3-small", "text-embedding-3-large",
}

SUGGESTION_STATUSES = {"pending", "approved", "rejected", "modified", "applied", "expired"}
SUGGESTION_TYPES = {
    "fit_gap_classification", "requirement_analysis", "defect_triage",
    "risk_assessment", "test_case_generation", "scope_recommendation",
    "change_impact",
    "steering_pack", "wricef_spec", "data_quality",   # S19 Doc Gen
    "conversation",                                     # S19 Multi-turn
    "general",
}

# S19 — conversation & assistant constants
CONVERSATION_STATUSES = {"active", "closed", "archived"}
ASSISTANT_TYPES = {
    "nl_query", "requirement_analyst", "defect_triage",
    "risk_assessment", "test_case_generator", "change_impact",
    "cutover_optimizer", "meeting_minutes",
    "steering_pack", "wricef_spec", "data_quality",   # S19
    "general",
}
DOC_GEN_TYPES = {"steering_pack", "wricef_spec", "data_quality"}

# S20 — performance & model routing constants
BUDGET_PERIODS = {"daily", "monthly"}
MODEL_TIERS = {
    "fast": ["gemini-2.5-flash", "gpt-4o-mini", "claude-3-5-haiku-20241022"],
    "balanced": ["gemini-2.5-flash", "gpt-4o-mini", "claude-3-5-sonnet-20241022"],
    "strong": ["gemini-2.5-pro", "gpt-4o", "claude-3-5-sonnet-20241022"],
}
# Purpose → recommended model tier mapping
PURPOSE_MODEL_MAP = {
    "defect_triage": "fast",
    "requirement_analyst": "fast",
    "risk_assessment": "fast",
    "test_case_generator": "fast",
    "change_impact": "balanced",
    "nl_query": "balanced",
    "meeting_minutes": "balanced",
    "steering_pack": "strong",
    "wricef_spec": "strong",
    "data_quality": "balanced",
    "cutover_optimizer": "strong",
    "conversation": "balanced",
    # Sprint 21
    "data_migration": "balanced",
    "integration_analyst": "balanced",
    "feedback": "fast",
    "orchestrator": "strong",
}

# Token costs per 1M tokens (input/output) — Feb 2026 pricing
TOKEN_COSTS = {
    "claude-3-5-haiku-20241022":   {"input": 1.00, "output": 5.00},
    "claude-3-5-sonnet-20241022":  {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229":      {"input": 15.00, "output": 75.00},
    "gpt-4o-mini":                 {"input": 0.15, "output": 0.60},
    "gpt-4o":                      {"input": 2.50, "output": 10.00},
    "gpt-4-turbo":                 {"input": 10.00, "output": 30.00},
    "text-embedding-3-small":      {"input": 0.02, "output": 0.00},
    "text-embedding-3-large":      {"input": 0.13, "output": 0.00},
    # Google Gemini — free tier (cost = 0 for demo)
    "gemini-2.5-flash":            {"input": 0.00, "output": 0.00},
    "gemini-2.5-pro":              {"input": 0.00, "output": 0.00},
    "gemini-2.0-flash":            {"input": 0.00, "output": 0.00},
    "gemini-embedding-001":        {"input": 0.00, "output": 0.00},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate USD cost for a given model + token counts."""
    costs = TOKEN_COSTS.get(model, {"input": 0.0, "output": 0.0})
    return (prompt_tokens * costs["input"] + completion_tokens * costs["output"]) / 1_000_000


# ── AIUsageLog ────────────────────────────────────────────────────────────────

class AIUsageLog(db.Model):
    """
    Tracks token usage and cost for every LLM API call.
    Aggregated for usage dashboards and cost monitoring.
    """

    __tablename__ = "ai_usage_logs"

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(30), nullable=False, comment="anthropic / openai / local")
    model = db.Column(db.String(80), nullable=False)
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    cost_usd = db.Column(db.Float, default=0.0)
    latency_ms = db.Column(db.Integer, default=0, comment="End-to-end latency in milliseconds")

    # Context
    user = db.Column(db.String(150), default="system")
    purpose = db.Column(db.String(100), default="", comment="e.g. requirement_analyst, defect_triage")
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="SET NULL"), nullable=True)

    # Status
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)

    # S20 — performance tracking
    cache_hit = db.Column(db.Boolean, default=False, comment="Whether response served from cache")
    fallback_provider = db.Column(db.String(30), nullable=True, comment="Provider used if primary failed")

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": self.latency_ms,
            "user": self.user,
            "purpose": self.purpose,
            "program_id": self.program_id,
            "success": self.success,
            "error_message": self.error_message,
            "cache_hit": self.cache_hit,
            "fallback_provider": self.fallback_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── AIEmbedding ───────────────────────────────────────────────────────────────

class AIEmbedding(db.Model):
    """
    Vector store for RAG retrieval.

    In production (PostgreSQL + pgvector), `embedding` is a vector(1536) column.
    In dev/test (SQLite), embeddings are stored as JSON text and searched in Python.
    """

    __tablename__ = "ai_embeddings"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), nullable=False, index=True,
                            comment="requirement, backlog_item, risk, config_item, ...")
    entity_id = db.Column(db.Integer, nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=True)

    chunk_text = db.Column(db.Text, nullable=False)
    chunk_index = db.Column(db.Integer, default=0, comment="Chunk position within entity")

    # Embedding vector — stored as JSON string for SQLite compatibility
    # In PostgreSQL migration, this becomes vector(1536) with HNSW index
    embedding_json = db.Column(db.Text, nullable=True, comment="JSON-encoded float[] for SQLite; vector(1536) in PG")

    # Metadata for filtering
    module = db.Column(db.String(50), nullable=True, comment="SAP module: FI, MM, SD...")
    phase = db.Column(db.String(50), nullable=True)
    metadata_json = db.Column(db.Text, default="{}", comment="Extra metadata as JSON")

    # ── KB Versioning (Sprint 9.5) ──
    kb_version = db.Column(db.String(30), default="1.0.0", index=True,
                           comment="KB version that produced this embedding")
    content_hash = db.Column(db.String(64), nullable=True,
                             comment="SHA-256 of source text for staleness detection")
    embedding_model = db.Column(db.String(80), nullable=True,
                                comment="Model used to generate embedding, e.g. gemini-embedding-001")
    embedding_dim = db.Column(db.Integer, nullable=True,
                              comment="Dimension of the embedding vector")
    is_active = db.Column(db.Boolean, default=True, index=True,
                          comment="Soft-delete: only active embeddings are searched")
    source_updated_at = db.Column(db.DateTime(timezone=True), nullable=True,
                                  comment="Entity updated_at at embed time")

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_ai_embedding_entity", "entity_type", "entity_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "program_id": self.program_id,
            "chunk_text": self.chunk_text,
            "chunk_index": self.chunk_index,
            "module": self.module,
            "phase": self.phase,
            "has_embedding": self.embedding_json is not None,
            "kb_version": self.kb_version,
            "content_hash": self.content_hash,
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "is_active": self.is_active,
            "source_updated_at": self.source_updated_at.isoformat() if self.source_updated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── KBVersion ─────────────────────────────────────────────────────────────────

KB_VERSION_STATUSES = {"building", "active", "archived"}


class KBVersion(db.Model):
    """
    Tracks Knowledge Base versions for reproducibility and rollback.

    Lifecycle: building → active → archived
    Only ONE version can be active at a time.
    """

    __tablename__ = "kb_versions"

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(30), unique=True, nullable=False, comment="Semantic version, e.g. 1.0.0")
    description = db.Column(db.Text, default="")
    embedding_model = db.Column(db.String(80), nullable=True)
    embedding_dim = db.Column(db.Integer, nullable=True)
    total_entities = db.Column(db.Integer, default=0)
    total_chunks = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="building", index=True,
                       comment="building | active | archived")
    created_by = db.Column(db.String(150), default="system")
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    activated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    archived_at = db.Column(db.DateTime(timezone=True), nullable=True)
    metadata_json = db.Column(db.Text, default="{}")

    def activate(self):
        """Mark this version as active, archiving any previously active version."""
        # Archive currently active versions
        KBVersion.query.filter(
            KBVersion.status == "active",
            KBVersion.id != self.id,
        ).update({"status": "archived", "archived_at": datetime.now(timezone.utc)})
        self.status = "active"
        self.activated_at = datetime.now(timezone.utc)

    def archive(self):
        """Archive this version."""
        self.status = "archived"
        self.archived_at = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "total_entities": self.total_entities,
            "total_chunks": self.total_chunks,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of text for content equality checks."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── AISuggestion ──────────────────────────────────────────────────────────────

class AISuggestion(db.Model):
    """
    AI-generated suggestion queue.

    Workflow: pending → approved/rejected/modified → applied
    When approved, the suggestion can be auto-applied to the target entity.
    """

    __tablename__ = "ai_suggestions"

    id = db.Column(db.Integer, primary_key=True)
    suggestion_type = db.Column(db.String(50), nullable=False, default="general",
                                comment="fit_gap_classification, defect_triage, ...")
    entity_type = db.Column(db.String(50), nullable=False, comment="requirement, defect, risk, ...")
    entity_id = db.Column(db.Integer, nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"), nullable=True)

    # The suggestion payload
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, default="")
    suggestion_data = db.Column(db.Text, default="{}", comment="JSON: proposed field changes")
    current_data = db.Column(db.Text, default="{}", comment="JSON: snapshot of current values")

    # AI metadata
    confidence = db.Column(db.Float, default=0.0, comment="0.0 – 1.0 confidence score")
    model_used = db.Column(db.String(80), default="")
    prompt_version = db.Column(db.String(20), default="v1")
    kb_version = db.Column(db.String(30), nullable=True, comment="KB version used for RAG context")
    reasoning = db.Column(db.Text, default="", comment="AI's reasoning / explanation")

    # Lifecycle
    status = db.Column(db.String(20), default="pending", index=True)
    reviewed_by = db.Column(db.String(150), nullable=True)
    review_note = db.Column(db.Text, nullable=True)
    applied_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def approve(self, reviewer="system", note=""):
        self.status = "approved"
        self.reviewed_by = reviewer
        self.review_note = note
        self.reviewed_at = datetime.now(timezone.utc)

    def reject(self, reviewer="system", note=""):
        self.status = "rejected"
        self.reviewed_by = reviewer
        self.review_note = note
        self.reviewed_at = datetime.now(timezone.utc)

    def mark_applied(self):
        self.status = "applied"
        self.applied_at = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "id": self.id,
            "suggestion_type": self.suggestion_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "program_id": self.program_id,
            "title": self.title,
            "description": self.description,
            "suggestion_data": self.suggestion_data,
            "current_data": self.current_data,
            "confidence": round(self.confidence, 3),
            "model_used": self.model_used,
            "prompt_version": self.prompt_version,
            "kb_version": self.kb_version,
            "reasoning": self.reasoning,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "review_note": self.review_note,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


# ── AIAuditLog ────────────────────────────────────────────────────────────────

class AIAuditLog(db.Model):
    """
    Immutable audit trail for every AI operation.
    Used for compliance, debugging, and cost attribution.
    """

    __tablename__ = "ai_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False,
                       comment="llm_call, embedding_create, suggestion_create, search, ...")
    provider = db.Column(db.String(30), default="")
    model = db.Column(db.String(80), default="")

    # Request info
    user = db.Column(db.String(150), default="system")
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="SET NULL"), nullable=True, index=True)
    prompt_hash = db.Column(db.String(64), default="", comment="SHA-256 of prompt for dedup")
    prompt_summary = db.Column(db.String(500), default="", comment="First 500 chars of prompt")

    # Response info
    tokens_used = db.Column(db.Integer, default=0)
    cost_usd = db.Column(db.Float, default=0.0)
    latency_ms = db.Column(db.Integer, default=0)
    response_summary = db.Column(db.String(500), default="", comment="First 500 chars of response")

    # Outcome
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, default="{}")

    # S20 — performance tracking
    cache_hit = db.Column(db.Boolean, default=False)
    fallback_used = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "provider": self.provider,
            "model": self.model,
            "user": self.user,
            "program_id": self.program_id,
            "prompt_summary": self.prompt_summary,
            "tokens_used": self.tokens_used,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": self.latency_ms,
            "response_summary": self.response_summary,
            "success": self.success,
            "error_message": self.error_message,
            "cache_hit": self.cache_hit,
            "fallback_used": self.fallback_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ── AIResponseCache (Sprint 20 — Performance) ────────────────────────────────

class AIResponseCache(db.Model):
    """
    LLM response cache with TTL-based expiration.
    Keyed by SHA-256 hash of serialized prompt messages.
    """

    __tablename__ = "ai_response_cache"

    id = db.Column(db.Integer, primary_key=True)
    prompt_hash = db.Column(db.String(64), nullable=False, unique=True, index=True,
                            comment="SHA-256 of JSON-serialized messages")
    model = db.Column(db.String(80), nullable=False)
    purpose = db.Column(db.String(100), default="")

    # Cached response
    response_json = db.Column(db.Text, nullable=False, comment="Full LLM response as JSON")
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)

    # TTL management
    hit_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    last_hit_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "prompt_hash": self.prompt_hash,
            "model": self.model,
            "purpose": self.purpose,
            "hit_count": self.hit_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_hit_at": self.last_hit_at.isoformat() if self.last_hit_at else None,
        }


# ── AITokenBudget (Sprint 20 — Cost Control) ─────────────────────────────────

class AITokenBudget(db.Model):
    """
    Per-program token/cost budget enforcement.
    Gateway checks budget before making LLM calls.
    """

    __tablename__ = "ai_token_budgets"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="CASCADE"),
                           nullable=True, index=True)
    user = db.Column(db.String(150), nullable=True, comment="Optional user-level budget")
    period = db.Column(db.String(20), nullable=False, default="daily",
                       comment="daily | monthly")

    # Limits
    token_limit = db.Column(db.Integer, nullable=False, default=1_000_000,
                            comment="Max tokens per period")
    cost_limit_usd = db.Column(db.Float, nullable=False, default=10.0,
                               comment="Max USD cost per period")

    # Current usage
    tokens_used = db.Column(db.Integer, default=0)
    cost_used_usd = db.Column(db.Float, default=0.0)
    request_count = db.Column(db.Integer, default=0)

    # Period tracking
    period_start = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reset_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.CheckConstraint(
            "period IN ('daily','monthly')",
            name="ck_ai_budget_period",
        ),
    )

    def is_exceeded(self):
        """Check if budget is exceeded."""
        return self.tokens_used >= self.token_limit or self.cost_used_usd >= self.cost_limit_usd

    def remaining_tokens(self):
        return max(0, self.token_limit - self.tokens_used)

    def remaining_cost(self):
        return max(0.0, self.cost_limit_usd - self.cost_used_usd)

    def to_dict(self):
        return {
            "id": self.id,
            "program_id": self.program_id,
            "user": self.user,
            "period": self.period,
            "token_limit": self.token_limit,
            "cost_limit_usd": self.cost_limit_usd,
            "tokens_used": self.tokens_used,
            "cost_used_usd": round(self.cost_used_usd, 6),
            "request_count": self.request_count,
            "is_exceeded": self.is_exceeded(),
            "remaining_tokens": self.remaining_tokens(),
            "remaining_cost_usd": round(self.remaining_cost(), 6),
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "reset_at": self.reset_at.isoformat() if self.reset_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<AITokenBudget prog={self.program_id} {self.period} {self.tokens_used}/{self.token_limit}>"


# ── AIConversation (Sprint 19 — Multi-turn) ──────────────────────────────────

class AIConversation(db.Model):
    """
    Multi-turn conversation session.
    Supports any assistant type — users can continue interacting with context.
    """

    __tablename__ = "ai_conversations"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), default="")
    assistant_type = db.Column(db.String(50), nullable=False, default="general")
    status = db.Column(db.String(20), default="active")

    # Context
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id", ondelete="SET NULL"), nullable=True)
    user = db.Column(db.String(150), default="system")
    context_json = db.Column(db.Text, default="{}", comment="Extra context: entity_id, entity_type, etc.")

    # Stats
    message_count = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    total_cost_usd = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    messages = db.relationship("AIConversationMessage", backref="conversation",
                               cascade="all, delete-orphan", order_by="AIConversationMessage.seq",
                               lazy="dynamic")

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('active','closed','archived')",
            name="ck_ai_conv_status",
        ),
    )

    def to_dict(self, include_messages=False):
        d = {
            "id": self.id,
            "title": self.title,
            "assistant_type": self.assistant_type,
            "status": self.status,
            "program_id": self.program_id,
            "user": self.user,
            "message_count": self.message_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd or 0, 6),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            d["messages"] = [m.to_dict() for m in self.messages.all()]
        return d

    def __repr__(self):
        return f"<AIConversation {self.id} [{self.assistant_type}] msgs={self.message_count}>"


class AIConversationMessage(db.Model):
    """Individual message within a multi-turn conversation."""

    __tablename__ = "ai_conversation_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("ai_conversations.id", ondelete="CASCADE"),
                                nullable=False, index=True)
    seq = db.Column(db.Integer, nullable=False, comment="Message sequence number (1-based)")
    role = db.Column(db.String(20), nullable=False, comment="user | assistant | system")
    content = db.Column(db.Text, nullable=False)

    # LLM response metadata (only for assistant messages)
    model = db.Column(db.String(80), nullable=True)
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)
    cost_usd = db.Column(db.Float, default=0.0)
    latency_ms = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.CheckConstraint(
            "role IN ('user','assistant','system')",
            name="ck_ai_msg_role",
        ),
        db.UniqueConstraint("conversation_id", "seq", name="uq_conv_msg_seq"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "seq": self.seq,
            "role": self.role,
            "content": self.content,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": round(self.cost_usd or 0, 6),
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<AIConversationMessage conv={self.conversation_id} seq={self.seq} role={self.role}>"


# ── S21 Models ─────────────────────────────────────────────────────────────

# Task statuses for async AI tasks
AI_TASK_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}

# Feedback metric types
FEEDBACK_METRIC_TYPES = {"accuracy", "relevance", "completeness", "hallucination"}


class AIFeedbackMetric(db.Model):
    """Per-assistant feedback accuracy tracking (Sprint 21)."""
    __tablename__ = "ai_feedback_metrics"

    id = db.Column(db.Integer, primary_key=True)
    assistant_type = db.Column(db.String(60), nullable=False, index=True)
    period_start = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    period_end = db.Column(db.DateTime, nullable=True)

    total_suggestions = db.Column(db.Integer, default=0)
    approved_count = db.Column(db.Integer, default=0)
    rejected_count = db.Column(db.Integer, default=0)
    modified_count = db.Column(db.Integer, default=0)

    accuracy_score = db.Column(db.Float, default=0.0)       # approve rate
    avg_confidence = db.Column(db.Float, default=0.0)
    common_rejection_reasons = db.Column(db.Text, nullable=True)  # JSON array
    prompt_improvement_hints = db.Column(db.Text, nullable=True)  # JSON array

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json as _json
        return {
            "id": self.id,
            "assistant_type": self.assistant_type,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "total_suggestions": self.total_suggestions,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "modified_count": self.modified_count,
            "accuracy_score": round(self.accuracy_score or 0, 4),
            "avg_confidence": round(self.avg_confidence or 0, 4),
            "common_rejection_reasons": _json.loads(self.common_rejection_reasons) if self.common_rejection_reasons else [],
            "prompt_improvement_hints": _json.loads(self.prompt_improvement_hints) if self.prompt_improvement_hints else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<AIFeedbackMetric assistant={self.assistant_type} acc={self.accuracy_score:.2f}>"


class AITask(db.Model):
    """Async AI task tracking with progress (Sprint 21)."""
    __tablename__ = "ai_tasks"

    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(60), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    progress_pct = db.Column(db.Integer, default=0)

    # Input / output
    input_json = db.Column(db.Text, nullable=True)
    result_json = db.Column(db.Text, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    # Context
    user = db.Column(db.String(100), nullable=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=True)
    workflow_name = db.Column(db.String(100), nullable=True)

    # Timing
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending','running','completed','failed','cancelled')",
            name="ck_ai_task_status",
        ),
    )

    def to_dict(self):
        import json as _json
        return {
            "id": self.id,
            "task_type": self.task_type,
            "status": self.status,
            "progress_pct": self.progress_pct,
            "input": _json.loads(self.input_json) if self.input_json else None,
            "result": _json.loads(self.result_json) if self.result_json else None,
            "error": self.error_message,
            "user": self.user,
            "program_id": self.program_id,
            "workflow_name": self.workflow_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self):
        return f"<AITask id={self.id} type={self.task_type} status={self.status}>"