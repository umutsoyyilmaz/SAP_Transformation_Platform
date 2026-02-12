"""
Rate limiting configuration — Sprint 14.

Applies per-blueprint rate limits using Flask-Limiter.
The Limiter instance is created in app/__init__.py with no default limits;
this module applies granular limits per route category.

Usage:
    from app.middleware.rate_limiter import init_rate_limits
    init_rate_limits(app, limiter)
"""


def init_rate_limits(app, limiter):
    """
    Apply rate limits to API blueprints.

    Limits (per remote IP):
        - AI endpoints:     10/minute  (LLM calls are expensive)
        - Write endpoints:  60/minute  (POST/PUT/DELETE)
        - Read endpoints:   200/minute (GET — generous for SPA)
        - Health check:     exempt

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

    app.logger.info(
        "Rate limiter configured — AI: 10/min, write: 60/min, read: 200/min"
    )
