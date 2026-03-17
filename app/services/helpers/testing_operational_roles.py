"""Operational role guards for testing release-readiness actions."""

from __future__ import annotations

from collections.abc import Iterable

from flask import g, jsonify


ADMIN_ROLES = {"platform_admin", "tenant_admin"}

ACTION_ROLE_MATRIX = {
    "approval_configure": {
        "program_manager",
        "project_manager",
        "test_manager",
    },
    "approval_submit": {
        "program_manager",
        "project_manager",
        "functional_consultant",
        "technical_consultant",
        "test_manager",
    },
    "approval_decide": {
        "program_manager",
        "project_manager",
        "functional_consultant",
        "test_manager",
    },
    "signoff_manage": {
        "program_manager",
        "project_manager",
        "functional_consultant",
        "test_manager",
    },
    "retest_manage": {
        "program_manager",
        "project_manager",
        "functional_consultant",
        "technical_consultant",
        "test_manager",
        "test_lead",
    },
    "release_decide": {
        "program_manager",
        "project_manager",
        "test_manager",
    },
}


def _normalize_actions(actions: Iterable[str] | None) -> list[str]:
    """Return supported action names in stable order."""
    if actions is None:
        return sorted(ACTION_ROLE_MATRIX.keys())

    normalized_actions: list[str] = []
    for action in actions:
        action_name = str(action or "").strip()
        if not action_name or action_name in normalized_actions:
            continue
        normalized_actions.append(action_name)
    return normalized_actions


def current_operational_roles() -> set[str]:
    """Return normalized JWT roles for the current request."""
    roles = {
        str(role or "").strip().lower()
        for role in getattr(g, "jwt_roles", []) or []
        if str(role or "").strip()
    }
    legacy_role = str(getattr(g, "current_user_role", "") or "").strip().lower()
    if legacy_role:
        roles.add(legacy_role)
    return roles


def has_operational_permission(action: str) -> bool:
    """Return True when the current request may perform the given action."""
    roles = current_operational_roles()
    if not roles:
        return True
    if str(getattr(g, "current_user_role", "") or "").strip().lower() == "admin":
        return True
    if roles & ADMIN_ROLES:
        return True

    allowed_roles = ACTION_ROLE_MATRIX.get(action, set())
    return bool(roles & allowed_roles)


def get_operational_permission_snapshot(actions: Iterable[str] | None = None) -> dict[str, dict[str, object]]:
    """Return allowed flags and role metadata for testing operational actions."""
    snapshot: dict[str, dict[str, object]] = {}
    for action in _normalize_actions(actions):
        allowed_roles = ACTION_ROLE_MATRIX.get(action, set())
        snapshot[action] = {
            "allowed": has_operational_permission(action),
            "allowed_roles": sorted(allowed_roles),
        }
    return snapshot


def require_operational_permission(action: str):
    """Return a 403 response tuple when the caller lacks the operational role."""
    if has_operational_permission(action):
        return None
    return jsonify({
        "error": "Operational role required",
        "action": action,
        "allowed_roles": sorted(ACTION_ROLE_MATRIX.get(action, set())),
    }), 403
