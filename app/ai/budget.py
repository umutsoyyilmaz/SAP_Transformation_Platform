"""
SAP Transformation Management Platform
Token Budget Service — Sprint 20 (Cost Control).

Enforces per-program and per-user token/cost budgets:
    - Check budget before LLM call → reject if exceeded
    - Record usage after successful call
    - Auto-reset when period rolls over
    - CRUD API for budget management
"""

import logging
from datetime import datetime, timedelta, timezone

from app.models import db
from app.models.ai import AITokenBudget

logger = logging.getLogger(__name__)


class TokenBudgetService:
    """Manages AI token budgets per program/user."""

    def get_budget(self, program_id: int | None = None,
                   user: str | None = None) -> AITokenBudget | None:
        """Get active budget for a program/user, auto-resetting if period expired."""
        q = AITokenBudget.query
        if program_id is not None:
            q = q.filter_by(program_id=program_id)
        if user:
            q = q.filter_by(user=user)

        budget = q.first()
        if budget:
            self._auto_reset_if_needed(budget)
        return budget

    def check_budget(self, program_id: int | None = None,
                     user: str | None = None) -> dict:
        """
        Check if a request is within budget.

        Returns:
            {"allowed": bool, "reason": str|None, "budget": dict|None}
        """
        budget = self.get_budget(program_id=program_id, user=user)
        if not budget:
            # No budget defined → unlimited
            return {"allowed": True, "reason": None, "budget": None}

        if budget.is_exceeded():
            return {
                "allowed": False,
                "reason": (
                    f"Token budget exceeded: {budget.tokens_used}/{budget.token_limit} tokens, "
                    f"${budget.cost_used_usd:.4f}/${budget.cost_limit_usd:.2f} cost. "
                    f"Resets at {budget.reset_at.isoformat() if budget.reset_at else 'N/A'}."
                ),
                "budget": budget.to_dict(),
            }

        return {"allowed": True, "reason": None, "budget": budget.to_dict()}

    def record_usage(self, program_id: int | None, user: str | None,
                     tokens: int, cost_usd: float):
        """Record token/cost usage against all matching budgets."""
        budgets = []
        if program_id is not None:
            b = self.get_budget(program_id=program_id)
            if b:
                budgets.append(b)
        if user:
            b = self.get_budget(user=user)
            if b and b not in budgets:
                budgets.append(b)

        for budget in budgets:
            budget.tokens_used = (budget.tokens_used or 0) + tokens
            budget.cost_used_usd = (budget.cost_used_usd or 0) + cost_usd
            budget.request_count = (budget.request_count or 0) + 1
        if budgets:
            db.session.flush()

    def create_or_update(self, program_id: int | None = None,
                         user: str | None = None,
                         period: str = "daily",
                         token_limit: int = 1_000_000,
                         cost_limit_usd: float = 10.0) -> AITokenBudget:
        """Create or update a budget."""
        budget = self.get_budget(program_id=program_id, user=user)
        now = datetime.now(timezone.utc)

        if budget:
            budget.period = period
            budget.token_limit = token_limit
            budget.cost_limit_usd = cost_limit_usd
        else:
            reset_at = self._compute_reset_at(period, now)
            budget = AITokenBudget(
                program_id=program_id,
                user=user,
                period=period,
                token_limit=token_limit,
                cost_limit_usd=cost_limit_usd,
                tokens_used=0,
                cost_used_usd=0.0,
                request_count=0,
                period_start=now,
                reset_at=reset_at,
            )
            db.session.add(budget)

        db.session.flush()
        return budget

    def reset_budget(self, budget_id: int) -> AITokenBudget | None:
        """Manually reset a budget's usage counters."""
        budget = db.session.get(AITokenBudget, budget_id)
        if not budget:
            return None
        now = datetime.now(timezone.utc)
        budget.tokens_used = 0
        budget.cost_used_usd = 0.0
        budget.request_count = 0
        budget.period_start = now
        budget.reset_at = self._compute_reset_at(budget.period, now)
        db.session.flush()
        return budget

    def list_budgets(self, program_id: int | None = None) -> list[dict]:
        """List all budgets, optionally filtered by program."""
        q = AITokenBudget.query.order_by(AITokenBudget.created_at.desc())
        if program_id is not None:
            q = q.filter_by(program_id=program_id)
        return [b.to_dict() for b in q.all()]

    def delete_budget(self, budget_id: int) -> bool:
        """Delete a budget."""
        budget = db.session.get(AITokenBudget, budget_id)
        if not budget:
            return False
        db.session.delete(budget)
        db.session.flush()
        return True

    # ── Internal ──────────────────────────────────────────────────────────

    def _auto_reset_if_needed(self, budget: AITokenBudget):
        """Reset usage counters if period has expired."""
        if not budget.reset_at:
            return
        now = datetime.now(timezone.utc)
        reset_at = budget.reset_at
        # SQLite stores naive datetimes; coerce to UTC-aware for comparison
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        if now >= reset_at:
            logger.info("Auto-resetting budget %d (period=%s)", budget.id, budget.period)
            budget.tokens_used = 0
            budget.cost_used_usd = 0.0
            budget.request_count = 0
            budget.period_start = now
            budget.reset_at = self._compute_reset_at(budget.period, now)
            db.session.flush()

    @staticmethod
    def _compute_reset_at(period: str, from_dt: datetime) -> datetime:
        """Compute next reset datetime for a given period."""
        if period == "monthly":
            # Reset on the 1st of next month
            if from_dt.month == 12:
                return from_dt.replace(year=from_dt.year + 1, month=1, day=1,
                                       hour=0, minute=0, second=0, microsecond=0)
            return from_dt.replace(month=from_dt.month + 1, day=1,
                                   hour=0, minute=0, second=0, microsecond=0)
        else:
            # Daily — reset at midnight UTC next day
            next_day = from_dt + timedelta(days=1)
            return next_day.replace(hour=0, minute=0, second=0, microsecond=0)
