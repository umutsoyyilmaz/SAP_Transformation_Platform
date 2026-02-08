"""
SAP Transformation Management Platform
AI domain models — Sprint 7.

Models:
    - AIUsageLog: Token/cost tracking per LLM call
    - AIEmbedding: Vector store for RAG (pgvector-ready, SQLite-safe)
    - AISuggestion: AI recommendation queue (approve/reject workflow)
    - AIAuditLog: Full audit trail for every AI invocation
"""

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
    "general",
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


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
    program_id = db.Column(db.Integer, nullable=True)
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
