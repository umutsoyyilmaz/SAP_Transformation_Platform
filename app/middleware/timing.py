"""
Request timing middleware.

Records request duration and logs slow requests.
Adds X-Request-Duration-Ms header to all responses.
"""

import logging
import time
import uuid

from flask import Flask, g, request

logger = logging.getLogger(__name__)

# Endpoints excluded from timing logs (high frequency, low value)
_SKIP_LOG = frozenset({"/api/v1/health", "/api/v1/health/ready"})

# Slow request threshold (ms)
SLOW_THRESHOLD_MS = 1000


def init_request_timing(app: Flask):
    """Register before/after hooks for request timing."""

    @app.before_request
    def _start_timer():
        g.request_start = time.perf_counter()
        g.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])

    @app.after_request
    def _log_request(response):
        start = getattr(g, "request_start", None)
        if start is None:
            return response

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-Duration-Ms"] = f"{duration_ms:.1f}"
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")

        # Feed metrics tracker
        _record_metric(request.method, request.path, response.status_code, duration_ms)

        # Log non-static, non-skip requests
        if request.path not in _SKIP_LOG and not request.path.startswith("/static"):
            extra = {
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "remote_addr": request.remote_addr,
                "request_id": getattr(g, "request_id", ""),
            }
            if duration_ms > SLOW_THRESHOLD_MS:
                logger.warning("Slow request: %s %s %d (%.0fms)",
                               request.method, request.path,
                               response.status_code, duration_ms, extra=extra)
            elif response.status_code >= 500:
                logger.error("Server error: %s %s %d (%.0fms)",
                             request.method, request.path,
                             response.status_code, duration_ms, extra=extra)
            else:
                logger.debug("Request: %s %s %d (%.0fms)",
                             request.method, request.path,
                             response.status_code, duration_ms, extra=extra)

        return response


# ── In-memory metrics ring buffer ──────────────────────────────────────────
_metrics_buffer: list[dict] = []
_MAX_BUFFER = 10_000


def _record_metric(method: str, path: str, status_code: int, duration_ms: float):
    """Append to the in-memory ring buffer."""
    entry = {
        "ts": time.time(),
        "method": method,
        "path": path,
        "status": status_code,
        "ms": round(duration_ms, 1),
    }
    _metrics_buffer.append(entry)
    if len(_metrics_buffer) > _MAX_BUFFER:
        del _metrics_buffer[:_MAX_BUFFER // 2]  # trim oldest half


def get_recent_metrics(seconds: int = 3600) -> list[dict]:
    """Return metrics from the last N seconds."""
    cutoff = time.time() - seconds
    return [m for m in _metrics_buffer if m["ts"] >= cutoff]


def reset_metrics():
    """Clear metrics buffer (for testing)."""
    _metrics_buffer.clear()
