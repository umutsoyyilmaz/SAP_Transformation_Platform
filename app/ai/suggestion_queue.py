"""
SAP Transformation Management Platform
Suggestion Queue Service — Sprint 7.

Manages AI-generated suggestions lifecycle:
    pending → approved/rejected/modified → applied

Usage:
    from app.ai.suggestion_queue import SuggestionQueue
    sq = SuggestionQueue()
    suggestion = sq.create(
        suggestion_type="fit_gap_classification",
        entity_type="requirement", entity_id=42,
        title="Classify as Partial Fit",
        suggestion_data={"fit_gap_status": "partial_fit"},
        confidence=0.85,
        model_used="claude-3-5-haiku-20241022",
    )
    sq.approve(suggestion.id, reviewer="admin")
"""

import json
import logging
from datetime import datetime, timezone

from app.models import db
from app.models.ai import AISuggestion, SUGGESTION_STATUSES, SUGGESTION_TYPES

logger = logging.getLogger(__name__)


class SuggestionQueue:
    """Service for managing AI suggestion lifecycle."""

    # ── Create ────────────────────────────────────────────────────────────

    @staticmethod
    def create(
        *,
        suggestion_type: str = "general",
        entity_type: str,
        entity_id: int,
        title: str,
        program_id: int | None = None,
        description: str = "",
        suggestion_data: dict | None = None,
        current_data: dict | None = None,
        confidence: float = 0.0,
        model_used: str = "",
        prompt_version: str = "v1",
        reasoning: str = "",
    ) -> AISuggestion:
        """
        Create a new pending suggestion.

        Returns:
            The created AISuggestion instance.
        """
        suggestion = AISuggestion(
            suggestion_type=suggestion_type,
            entity_type=entity_type,
            entity_id=entity_id,
            program_id=program_id,
            title=title,
            description=description,
            suggestion_data=json.dumps(suggestion_data or {}),
            current_data=json.dumps(current_data or {}),
            confidence=confidence,
            model_used=model_used,
            prompt_version=prompt_version,
            reasoning=reasoning,
            status="pending",
        )
        db.session.add(suggestion)
        db.session.commit()
        logger.info("Created suggestion #%d: %s for %s/%d",
                     suggestion.id, suggestion_type, entity_type, entity_id)
        return suggestion

    # ── Review Actions ────────────────────────────────────────────────────

    @staticmethod
    def approve(suggestion_id: int, reviewer: str = "system", note: str = "") -> AISuggestion | None:
        """Approve a pending suggestion."""
        s = db.session.get(AISuggestion, suggestion_id)
        if not s or s.status != "pending":
            return None
        s.approve(reviewer, note)
        db.session.commit()
        logger.info("Suggestion #%d approved by %s", suggestion_id, reviewer)
        return s

    @staticmethod
    def reject(suggestion_id: int, reviewer: str = "system", note: str = "") -> AISuggestion | None:
        """Reject a pending suggestion."""
        s = db.session.get(AISuggestion, suggestion_id)
        if not s or s.status != "pending":
            return None
        s.reject(reviewer, note)
        db.session.commit()
        logger.info("Suggestion #%d rejected by %s", suggestion_id, reviewer)
        return s

    @staticmethod
    def modify_and_approve(
        suggestion_id: int,
        modified_data: dict,
        reviewer: str = "system",
        note: str = "",
    ) -> AISuggestion | None:
        """Modify suggestion data and approve."""
        s = db.session.get(AISuggestion, suggestion_id)
        if not s or s.status != "pending":
            return None
        s.suggestion_data = json.dumps(modified_data)
        s.status = "modified"
        s.reviewed_by = reviewer
        s.review_note = note
        s.reviewed_at = datetime.now(timezone.utc)
        db.session.commit()
        logger.info("Suggestion #%d modified+approved by %s", suggestion_id, reviewer)
        return s

    @staticmethod
    def mark_applied(suggestion_id: int) -> AISuggestion | None:
        """Mark a suggestion as applied (after data change propagated)."""
        s = db.session.get(AISuggestion, suggestion_id)
        if not s or s.status not in ("approved", "modified"):
            return None
        s.mark_applied()
        db.session.commit()
        return s

    # ── Queries ───────────────────────────────────────────────────────────

    @staticmethod
    def list_suggestions(
        *,
        program_id: int | None = None,
        status: str | None = None,
        suggestion_type: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        """
        List suggestions with filters and pagination.

        Returns:
            {items: [...], total: N, page: N, per_page: N}
        """
        q = AISuggestion.query

        if program_id:
            q = q.filter(AISuggestion.program_id == program_id)
        if status:
            q = q.filter(AISuggestion.status == status)
        if suggestion_type:
            q = q.filter(AISuggestion.suggestion_type == suggestion_type)
        if entity_type:
            q = q.filter(AISuggestion.entity_type == entity_type)
        if entity_id is not None:
            q = q.filter(AISuggestion.entity_id == entity_id)

        q = q.order_by(AISuggestion.created_at.desc())
        total = q.count()

        items = q.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "items": [s.to_dict() for s in items],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    @staticmethod
    def get_pending_count(program_id: int | None = None) -> int:
        """Get count of pending suggestions."""
        q = AISuggestion.query.filter(AISuggestion.status == "pending")
        if program_id:
            q = q.filter(AISuggestion.program_id == program_id)
        return q.count()

    @staticmethod
    def get_stats(program_id: int | None = None) -> dict:
        """Get suggestion statistics."""
        base_q = AISuggestion.query
        if program_id:
            base_q = base_q.filter(AISuggestion.program_id == program_id)

        total = base_q.count()
        status_counts = {}
        for row in db.session.query(
            AISuggestion.status,
            db.func.count(AISuggestion.id),
        ).group_by(AISuggestion.status).all():
            status_counts[row[0]] = row[1]

        type_counts = {}
        for row in db.session.query(
            AISuggestion.suggestion_type,
            db.func.count(AISuggestion.id),
        ).group_by(AISuggestion.suggestion_type).all():
            type_counts[row[0]] = row[1]

        # Average confidence for approved vs rejected
        approved_conf = db.session.query(
            db.func.avg(AISuggestion.confidence),
        ).filter(AISuggestion.status.in_(["approved", "modified", "applied"])).scalar() or 0.0

        rejected_conf = db.session.query(
            db.func.avg(AISuggestion.confidence),
        ).filter(AISuggestion.status == "rejected").scalar() or 0.0

        return {
            "total": total,
            "by_status": status_counts,
            "by_type": type_counts,
            "avg_confidence_approved": round(float(approved_conf), 3),
            "avg_confidence_rejected": round(float(rejected_conf), 3),
            "approval_rate": round(
                status_counts.get("approved", 0) + status_counts.get("modified", 0) + status_counts.get("applied", 0),
            ) / max(total, 1) * 100,
        }
