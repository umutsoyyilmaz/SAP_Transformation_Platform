"""
Blueprint Permission Guards — Sprint 6, Items 2.2.6 & 2.2.7

Centralized module that applies an app-level before_request guard
to enforce category-level permissions on all business-logic blueprints.

Guards use the same fallthrough logic as @require_permission:
if g.jwt_user_id is None (legacy auth), the hook passes through silently.

Architecture:
    A single app.before_request hook resolves the current endpoint's
    blueprint name, looks up the permission mapping, and enforces it.
    This avoids Flask 3.x's restriction on calling bp.before_request()
    after registration.

Permission mapping reference (from seed_roles.py):
    requirements : view, create, edit, delete, approve
    workshops    : view, create, facilitate, approve
    tests        : view, create, execute, approve
    projects     : view, create, edit, archive
    backlog      : view, create, edit
    raid         : view, create, edit, resolve
    integration  : view, create, edit
    cutover      : view, create, edit, execute
    data         : view, create, migrate
    reports      : view, export
    admin        : settings, roles, audit
"""

import logging

from flask import Flask, g, jsonify, request

logger = logging.getLogger(__name__)


# ── Permission configurations per blueprint ──────────────────────────────────

# Blueprint name → method → codename
# Missing CRUD verbs in seed (e.g. no backlog.delete) are mapped to
# the closest write permission (usually .edit or .create).
BLUEPRINT_PERMISSIONS = {
    "program": {
        "GET": "projects.view",
        "POST": "projects.create",
        "PUT": "projects.edit",
        "PATCH": "projects.edit",
        "DELETE": "projects.edit",
    },
    "testing": {
        "GET": "tests.view",
        "POST": "tests.create",
        "PUT": "tests.create",
        "PATCH": "tests.execute",
        "DELETE": "tests.create",
    },
    # explore handled separately via _resolve_explore_permission
    "backlog": {
        "GET": "backlog.view",
        "POST": "backlog.create",
        "PUT": "backlog.edit",
        "PATCH": "backlog.edit",
        "DELETE": "backlog.edit",
    },
    "raid": {
        "GET": "raid.view",
        "POST": "raid.create",
        "PUT": "raid.edit",
        "PATCH": "raid.edit",
        "DELETE": "raid.edit",
    },
    "integration": {
        "GET": "integration.view",
        "POST": "integration.create",
        "PUT": "integration.edit",
        "PATCH": "integration.edit",
        "DELETE": "integration.edit",
    },
    "cutover": {
        "GET": "cutover.view",
        "POST": "cutover.create",
        "PUT": "cutover.edit",
        "PATCH": "cutover.edit",
        "DELETE": "cutover.edit",
    },
    "data_factory": {
        "GET": "data.view",
        "POST": "data.create",
        "PUT": "data.create",
        "PATCH": "data.create",
        "DELETE": "data.create",
    },
    "reporting": {
        "GET": "reports.view",
        "POST": "reports.export",
        "PUT": "reports.export",
        "PATCH": "reports.export",
        "DELETE": "reports.export",
    },
    "run_sustain": {
        "GET": "cutover.view",
        "POST": "cutover.create",
        "PUT": "cutover.edit",
        "PATCH": "cutover.edit",
        "DELETE": "cutover.edit",
    },
    "traceability": {
        "GET": "requirements.view",
    },
    "audit": {
        "GET": "admin.audit",
    },
    # ── Sprint 4: Previously skipped admin/utility blueprints ────────────
    "feature_flag": {
        "GET": "admin.settings",
        "POST": "admin.settings",
        "PUT": "admin.settings",
        "PATCH": "admin.settings",
        "DELETE": "admin.settings",
    },
    "dashboard": {
        "GET": "admin.settings",
    },
    "tenant_export": {
        "GET": "admin.settings",
    },
    "notification_bp": {
        "GET": "admin.settings",
        "POST": "admin.settings",
        "PATCH": "admin.settings",
        "DELETE": "admin.settings",
    },
    "onboarding": {
        "GET": "admin.settings",
        "POST": "admin.settings",
    },
}

# Blueprints that are explicitly skipped:
#   health, metrics       — monitoring, stay open
#   pwa                   — public / utility routes
#   admin, platform_admin — already have per-route @require_permission
#   auth                  — auth endpoints must be open (login, register, etc.)
#   ai                    — has @require_role on sensitive routes; general AI
#                           access is open for all authenticated users

SKIP_BLUEPRINTS = {
    "health", "metrics", "pwa", "admin", "platform_admin",
    "auth", "ai", "static",
    "sso_bp", "sso_ui_bp",  # Sprint 7 — SSO has own @require_permission guards
    "scim_bp",              # Sprint 8 — SCIM uses bearer token auth
    "bulk_import_bp",       # Sprint 8 — has own @require_permission guards
    "custom_roles_bp",      # Sprint 8 — has own @require_permission guards
    "roles_ui_bp",          # Sprint 8 — UI route
    "feature_flag_ui",      # UI route, protected by same-origin auth
}

# Explore endpoints that should stay open (health / self-info)
EXPLORE_OPEN_ENDPOINTS = {"explore_health", "user_permissions"}

# Explore path prefixes that map to workshops category
WORKSHOP_PATH_PREFIXES = (
    "/workshops", "/attendees", "/agenda-items", "/decisions",
    "/workshop-dependencies",
)

# Explore category method maps
EXPLORE_CATEGORY_MAP = {
    "requirements": {
        "GET": "requirements.view",
        "POST": "requirements.create",
        "PUT": "requirements.edit",
        "PATCH": "requirements.edit",
        "DELETE": "requirements.delete",
    },
    "workshops": {
        "GET": "workshops.view",
        "POST": "workshops.create",
        "PUT": "workshops.facilitate",
        "PATCH": "workshops.facilitate",
        "DELETE": "workshops.facilitate",
    },
    "reports": {
        "GET": "reports.view",
        "POST": "reports.view",
        "PUT": "reports.view",
        "PATCH": "reports.view",
        "DELETE": "reports.view",
    },
}


def _resolve_explore_permission(method: str, path: str) -> str | None:
    """Resolve the required permission for an explore blueprint request."""
    # Strip /api/v1/explore prefix
    rel = ""
    idx = path.find("/api/v1/explore")
    if idx != -1:
        rel = path[idx + len("/api/v1/explore"):]

    if any(rel.startswith(p) for p in WORKSHOP_PATH_PREFIXES):
        category = "workshops"
    elif rel.startswith("/reports"):
        category = "reports"
    else:
        category = "requirements"

    return EXPLORE_CATEGORY_MAP[category].get(method)


def apply_all_blueprint_permissions(app: Flask):
    """
    Register a single app.before_request hook that enforces
    category-level permissions on all protected blueprints.

    Call once in create_app() after all blueprints are registered.
    """
    # Build the set of protected blueprint names at startup
    protected = set()
    for bp_name in app.blueprints:
        if bp_name in SKIP_BLUEPRINTS:
            continue
        if bp_name == "explore" or bp_name in BLUEPRINT_PERMISSIONS:
            protected.add(bp_name)

    @app.before_request
    def _enforce_blueprint_permission():
        from app.services.permission_service import has_permission

        # Determine which blueprint this request belongs to
        endpoint = request.endpoint
        if not endpoint:
            return None

        # Extract blueprint name from endpoint (format: "blueprint_name.func")
        parts = endpoint.rsplit(".", 1)
        if len(parts) < 2:
            return None  # top-level route, not a blueprint route
        bp_name = parts[0]

        if bp_name not in protected:
            return None  # Not a protected blueprint

        # Check for JWT user — legacy auth fallthrough
        user_id = getattr(g, "jwt_user_id", None)
        if user_id is None:
            return None

        fn_name = parts[1]

        # Special handling for explore blueprint
        if bp_name == "explore":
            if fn_name in EXPLORE_OPEN_ENDPOINTS:
                return None
            codename = _resolve_explore_permission(request.method, request.path)
        else:
            method_map = BLUEPRINT_PERMISSIONS.get(bp_name)
            if method_map is None:
                return None
            codename = method_map.get(request.method)

        if codename is None:
            return None

        if not has_permission(user_id, codename):
            logger.warning(
                "Blueprint permission denied: user=%d required=%s endpoint=%s",
                user_id, codename, endpoint,
            )
            return jsonify({
                "error": "Permission denied",
                "required": codename,
            }), 403

        return None

    logger.info(
        "Blueprint permissions applied to %d blueprints: %s",
        len(protected), ", ".join(sorted(protected)),
    )
