"""
AI Admin Service — aggregate statistics for the AI admin dashboard.

Extracted from ai_bp.py to comply with the service-layer rule:
all ORM queries and DB reads go here; the blueprint only calls this function.
"""

import logging

from app.ai.rag import RAGPipeline
from app.ai.suggestion_queue import SuggestionQueue
from app.models import db
from app.models.ai import AIAuditLog, AIUsageLog

logger = logging.getLogger(__name__)


def get_admin_dashboard_stats(tenant_id: int, program_id: int | None = None) -> dict:
    """Return aggregated AI system statistics for the admin dashboard.

    Queries usage logs, audit trail, suggestion queue, and embedding stats
    in a single service call so the blueprint contains no ORM logic.

    Args:
        tenant_id: Owning tenant's primary key (for future tenant-scoped stats).
        program_id: Optional program filter for suggestion/embedding stats.

    Returns:
        Dict with keys: usage, suggestions, embeddings, recent_activity.
    """
    # ── Usage aggregate stats ─────────────────────────────────────────────
    total_calls: int = AIUsageLog.query.count()
    total_tokens: int = db.session.query(db.func.sum(AIUsageLog.total_tokens)).scalar() or 0
    total_cost: float = db.session.query(db.func.sum(AIUsageLog.cost_usd)).scalar() or 0.0
    avg_latency: float = db.session.query(db.func.avg(AIUsageLog.latency_ms)).scalar() or 0.0
    error_count: int = AIUsageLog.query.filter(AIUsageLog.success.is_(False)).count()

    # ── Provider breakdown ────────────────────────────────────────────────
    provider_stats: dict = {}
    for row in db.session.query(
        AIUsageLog.provider,
        db.func.count(AIUsageLog.id),
        db.func.sum(AIUsageLog.cost_usd),
    ).group_by(AIUsageLog.provider).all():
        provider_stats[row[0]] = {"calls": row[1], "cost": round(float(row[2] or 0), 4)}

    # ── Recent audit activity (last 10 entries) ───────────────────────────
    recent = AIAuditLog.query.order_by(AIAuditLog.created_at.desc()).limit(10).all()

    # ── External subsystem stats (non-ORM) ───────────────────────────────
    suggestion_stats = SuggestionQueue.get_stats(program_id=program_id)
    embedding_stats = RAGPipeline.get_index_stats(program_id=program_id)

    logger.debug("admin_dashboard_stats fetched tenant_id=%s program_id=%s", tenant_id, program_id)

    return {
        "usage": {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(float(total_cost), 4),
            "avg_latency_ms": round(float(avg_latency)),
            "error_count": error_count,
            "error_rate": round(error_count / max(total_calls, 1) * 100, 1),
            "by_provider": provider_stats,
        },
        "suggestions": suggestion_stats,
        "embeddings": embedding_stats,
        "recent_activity": [a.to_dict() for a in recent],
    }
