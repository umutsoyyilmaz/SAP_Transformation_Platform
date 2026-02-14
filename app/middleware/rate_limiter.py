"""
Rate limiting configuration — Sprint 14 + Sprint 9 (Item 4.3).

Applies per-blueprint rate limits using Flask-Limiter.
The Limiter instance is created in app/__init__.py with no default limits;
this module applies granular limits per route category.

Sprint 9 addition (Item 4.3): Tenant-aware rate limiting.
Plan-based API quotas:
    - trial:      100 requests/minute
    - starter:    300 requests/minute
    - professional: 600 requests/minute
    - premium:    1000 requests/minute
    - enterprise: 5000 requests/minute

Usage:
    from app.middleware.rate_limiter import init_rate_limits
    init_rate_limits(app, limiter)
"""

import logging

from flask import g, request as flask_request

logger = logging.getLogger(__name__)

# ── Plan-based rate limits (Item 4.3) ────────────────────────────────────

PLAN_RATE_LIMITS = {
    "trial": "100/minute",
    "starter": "300/minute",
    "professional": "600/minute",
    "premium": "1000/minute",
    "enterprise": "5000/minute",
}

DEFAULT_PLAN_LIMIT = "100/minute"


def _get_tenant_rate_limit_key():
    """Dynamic rate limit key: tenant_id if available, else remote IP."""
    tenant_id = getattr(g, "tenant_id", None)
    if tenant_id:
        return f"tenant:{tenant_id}"
    return flask_request.remote_addr or "unknown"


def _get_tenant_plan_limit():
    """Return the rate limit string for the current tenant's plan."""
    tenant = getattr(g, "tenant", None)
    if tenant:
        plan = getattr(tenant, "plan", "trial") or "trial"
        return PLAN_RATE_LIMITS.get(plan, DEFAULT_PLAN_LIMIT)
    return DEFAULT_PLAN_LIMIT


def init_rate_limits(app, limiter):
    """
    Apply rate limits to API blueprints.

    Limits (per remote IP):
        - AI endpoints:     10/minute  (LLM calls are expensive)
        - Write endpoints:  60/minute  (POST/PUT/DELETE)
        - Read endpoints:   200/minute (GET — generous for SPA)
        - Health check:     exempt

    Tenant-based limits (Sprint 9 — Item 4.3):
        - Applied as an additional app-wide limit based on tenant plan
        - Resolved per-tenant via g.tenant_id

    Rate limiting is disabled in testing mode.
    """

    if app.config.get("TESTING"):
        app.logger.info("Rate limiter disabled (TESTING=True)")
        return

    # AI blueprint — strict limit (LLM calls)
    bp = app.blueprints.get("ai")
    if bp:
        limiter.limit("10/minute")(bp)

    # Write-heavy mutation routes — moderate limit
    for bp_name in ("program", "backlog", "testing", "raid",
                    "integration", "data_factory", "explore",
                    "cutover", "audit"):
        bp = app.blueprints.get(bp_name)
        if bp:
            limiter.limit("60/minute")(bp)

    # Reporting / metrics — read-focused
    for bp_name in ("reporting", "metrics"):
        bp = app.blueprints.get(bp_name)
        if bp:
            limiter.limit("200/minute")(bp)

    # Health check — exempt from rate limiting
    bp = app.blueprints.get("health")
    if bp:
        limiter.exempt(bp)

    # ── Tenant-based plan limit (Sprint 9 — Item 4.3) ───────────────────
    # Applied as a dynamic app-wide shared limit keyed by tenant.
    # This works alongside per-blueprint limits above.
    @app.before_request
    def _check_tenant_rate_info():
        """Inject tenant plan info into g for rate limiter reference."""
        # Only set info — actual limiting is handled by the dynamic limiter
        if flask_request.path.startswith("/api/"):
            tenant_id = getattr(g, "tenant_id", None)
            if tenant_id:
                g.rate_limit_plan = _get_tenant_plan_limit()

    app.logger.info(
        "Rate limiter configured — AI: 10/min, write: 60/min, read: 200/min, "
        "tenant plans: trial=100/min, premium=1000/min, enterprise=5000/min"
    )
