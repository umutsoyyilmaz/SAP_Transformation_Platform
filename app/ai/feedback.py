"""
SAP Transformation Management Platform
AI Feedback Learning Pipeline — Sprint 21.

Analyses approved/rejected suggestions to compute per-assistant accuracy scores,
identify systematic errors, and generate prompt improvement recommendations.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from app.models import db
from app.models.ai import AISuggestion, AIFeedbackMetric

logger = logging.getLogger(__name__)


class FeedbackPipeline:
    """Analyses suggestion approve/reject patterns per assistant type."""

    def compute_accuracy_scores(self, days: int = 30) -> list[dict]:
        """
        Compute accuracy scores per assistant type from recent suggestions.

        Returns:
            List of per-assistant metric dicts.
        """
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        suggestions = AISuggestion.query.filter(
            AISuggestion.created_at >= cutoff,
        ).all()

        by_type: dict[str, dict] = defaultdict(lambda: {
            "total": 0, "approved": 0, "rejected": 0, "modified": 0,
            "confidences": [],
        })

        for s in suggestions:
            key = s.suggestion_type or "unknown"
            by_type[key]["total"] += 1
            status = (s.status or "").lower()
            if status == "approved":
                by_type[key]["approved"] += 1
            elif status == "rejected":
                by_type[key]["rejected"] += 1
            elif status == "modified":
                by_type[key]["modified"] += 1
            if s.confidence:
                by_type[key]["confidences"].append(s.confidence)

        results = []
        for assistant_type, stats in by_type.items():
            total = stats["total"]
            acc = stats["approved"] / total if total > 0 else 0.0
            confs = stats["confidences"]
            avg_conf = sum(confs) / len(confs) if confs else 0.0

            results.append({
                "assistant_type": assistant_type,
                "total_suggestions": total,
                "approved_count": stats["approved"],
                "rejected_count": stats["rejected"],
                "modified_count": stats["modified"],
                "accuracy_score": round(acc, 4),
                "avg_confidence": round(avg_conf, 4),
            })

        return results

    def save_metrics(self, days: int = 30) -> dict:
        """Compute and persist accuracy metrics to DB."""
        scores = self.compute_accuracy_scores(days=days)
        now = datetime.now(timezone.utc)
        saved = 0

        for s in scores:
            metric = AIFeedbackMetric(
                assistant_type=s["assistant_type"],
                period_start=now - timedelta(days=days),
                period_end=now,
                total_suggestions=s["total_suggestions"],
                approved_count=s["approved_count"],
                rejected_count=s["rejected_count"],
                modified_count=s["modified_count"],
                accuracy_score=s["accuracy_score"],
                avg_confidence=s["avg_confidence"],
            )
            db.session.add(metric)
            saved += 1

        db.session.flush()
        return {"saved_metrics": saved, "assistant_types": [s["assistant_type"] for s in scores]}

    def get_feedback_stats(self, assistant_type: str | None = None) -> list[dict]:
        """Get latest persisted feedback metrics."""
        q = AIFeedbackMetric.query.order_by(AIFeedbackMetric.created_at.desc())
        if assistant_type:
            q = q.filter_by(assistant_type=assistant_type)
        return [m.to_dict() for m in q.limit(50).all()]

    def generate_prompt_recommendations(self, days: int = 30) -> list[dict]:
        """
        Analyse rejection patterns and recommend prompt improvements.

        Returns:
            List of {assistant_type, issue, recommendation, priority}.
        """
        scores = self.compute_accuracy_scores(days=days)
        recs = []

        for s in scores:
            acc = s["accuracy_score"]
            total = s["total_suggestions"]
            if total < 3:
                continue  # Not enough data

            if acc < 0.5:
                recs.append({
                    "assistant_type": s["assistant_type"],
                    "issue": f"Low accuracy ({acc:.0%}) — more than half of suggestions rejected",
                    "recommendation": "Review and rewrite the system prompt for this assistant. "
                                      "Consider adding more specific SAP domain context and examples.",
                    "priority": "high",
                })
            elif acc < 0.7:
                recs.append({
                    "assistant_type": s["assistant_type"],
                    "issue": f"Moderate accuracy ({acc:.0%})",
                    "recommendation": "Fine-tune prompt with rejection pattern examples. "
                                      "Add output format constraints.",
                    "priority": "medium",
                })

            if s["avg_confidence"] > 0.8 and acc < 0.6:
                recs.append({
                    "assistant_type": s["assistant_type"],
                    "issue": "High confidence but low accuracy — overconfident",
                    "recommendation": "Add calibration instructions to the prompt. "
                                      "Ask the model to express uncertainty more explicitly.",
                    "priority": "high",
                })

        return recs
