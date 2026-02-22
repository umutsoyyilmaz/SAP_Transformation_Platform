"""
Security headers middleware — Sprint 14.

Applies Content-Security-Policy, X-Content-Type-Options, X-Frame-Options,
Strict-Transport-Security, Referrer-Policy, and Permissions-Policy headers
to every response.

Usage:
    from app.middleware.security_headers import init_security_headers
    init_security_headers(app)
"""


def init_security_headers(app):
    """Register after_request handler that injects security headers."""

    @app.after_request
    def _add_security_headers(response):
        # Content-Security-Policy — relaxed for SPA (inline scripts/styles)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers.setdefault("Content-Security-Policy", csp)

        # Prevent MIME-type sniffing
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # Clickjacking protection
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")

        # HTTPS enforcement (ignored over HTTP, but ready for production)
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )

        # Referrer policy
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # Permissions policy — disable dangerous browser features
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # Remove server identification
        response.headers.pop("Server", None)

        return response
