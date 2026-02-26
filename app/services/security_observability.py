"""Security observability helpers for scope-related incidents."""

from __future__ import annotations

import time
from typing import Any

from flask import has_request_context, request

_SECURITY_EVENTS: list[dict[str, Any]] = []
_MAX_SECURITY_EVENTS = 5000


ALERT_RULES = (
    {
        "event_type": "cross_scope_access_attempt",
        "threshold": 3,
        "window_seconds": 300,
        "severity": "high",
        "code": "SEC-CROSS-SCOPE-001",
    },
    {
        "event_type": "scope_mismatch_error",
        "threshold": 5,
        "window_seconds": 300,
        "severity": "medium",
        "code": "SEC-SCOPE-MISMATCH-001",
    },
)


def _trim() -> None:
    if len(_SECURITY_EVENTS) > _MAX_SECURITY_EVENTS:
        del _SECURITY_EVENTS[: _MAX_SECURITY_EVENTS // 2]


def extract_scope_from_request() -> tuple[int | None, int | None, int | None]:
    """Best-effort scope extraction from route/query/body."""
    if not has_request_context():
        return None, None, None

    tenant_id = None
    program_id = None
    project_id = None

    try:
        from flask import g

        tenant_id = getattr(g, "jwt_tenant_id", None) or getattr(g, "tenant_id", None)
    except Exception:
        tenant_id = None

    view_args = request.view_args or {}
    program_id = view_args.get("program_id")
    project_id = view_args.get("project_id")

    if program_id is None:
        program_id = request.args.get("program_id", type=int)
    if project_id is None:
        project_id = request.args.get("project_id", type=int)

    if program_id is None or project_id is None:
        payload = request.get_json(silent=True) or {}
        if program_id is None:
            program_id = payload.get("program_id")
        if project_id is None:
            project_id = payload.get("project_id")

    return tenant_id, _to_int(program_id), _to_int(project_id)


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return None


def record_security_event(
    *,
    event_type: str,
    reason: str,
    severity: str = "warning",
    tenant_id: int | None = None,
    program_id: int | None = None,
    project_id: int | None = None,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if tenant_id is None or program_id is None or project_id is None:
        r_tenant, r_program, r_project = extract_scope_from_request()
        tenant_id = tenant_id if tenant_id is not None else r_tenant
        program_id = program_id if program_id is not None else r_program
        project_id = project_id if project_id is not None else r_project

    path = None
    method = None
    if has_request_context():
        path = request.path
        method = request.method

    event = {
        "ts": time.time(),
        "event_type": event_type,
        "severity": severity,
        "reason": reason,
        "tenant_id": tenant_id,
        "program_id": program_id,
        "project_id": project_id,
        "path": path,
        "method": method,
        "request_id": request_id,
        "details": details or {},
    }
    _SECURITY_EVENTS.append(event)
    _trim()
    return event


def get_recent_security_events(*, seconds: int = 3600, event_type: str | None = None) -> list[dict[str, Any]]:
    cutoff = time.time() - seconds
    rows = [e for e in _SECURITY_EVENTS if e["ts"] >= cutoff]
    if event_type:
        rows = [e for e in rows if e["event_type"] == event_type]
    return rows


def evaluate_security_alerts(*, now: float | None = None) -> dict[str, Any]:
    now = now or time.time()
    triggered = []
    counts = {}

    for rule in ALERT_RULES:
        cutoff = now - rule["window_seconds"]
        matched = [
            e for e in _SECURITY_EVENTS
            if e["event_type"] == rule["event_type"] and e["ts"] >= cutoff
        ]
        counts[rule["event_type"]] = len(matched)
        if len(matched) >= rule["threshold"]:
            triggered.append({
                "code": rule["code"],
                "event_type": rule["event_type"],
                "severity": rule["severity"],
                "window_seconds": rule["window_seconds"],
                "threshold": rule["threshold"],
                "observed": len(matched),
                "latest": matched[-1] if matched else None,
            })

    return {"counts": counts, "alerts": triggered}


def reset_security_events() -> None:
    _SECURITY_EVENTS.clear()
