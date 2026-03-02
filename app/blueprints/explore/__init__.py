"""
Explore Phase Management — Blueprint Package

Splits the monolithic explore_bp.py into cohesive sub-modules while
keeping a single Blueprint instance and preserving all URL routes.
"""

import logging

from flask import Blueprint, g, request

from app.utils.errors import E, api_error

logger = logging.getLogger(__name__)

explore_bp = Blueprint("explore", __name__, url_prefix="/api/v1/explore")


@explore_bp.before_request
def _resolve_explore_program_context():
    """Derive program_id from all available sources for explore endpoints.

    Resolution order:
      1. ``program_id`` or ``project_id`` query parameter
      2. ``program_id`` or ``project_id`` in JSON body (POST/PUT/PATCH)
      3. ``X-Project-Id`` header → Project lookup → project.program_id

    The resolved value is stored in ``g.explore_program_id`` so that both
    the ``_get_program_id`` helper and legacy service functions can read it.
    """
    pid = (
        request.args.get("program_id", type=int)
        or request.args.get("project_id", type=int)
    )

    if not pid:
        data = request.get_json(silent=True) or {}
        pid = data.get("program_id") or data.get("project_id")
        if pid is not None:
            try:
                pid = int(pid)
            except (TypeError, ValueError):
                pid = None

    if not pid:
        # tenant_context.py sets g.project_id only for JWT-authenticated
        # requests.  When auth is disabled (dev) or for legacy-auth users,
        # read the X-Project-Id header directly as a fallback.
        _proj_id = getattr(g, "project_id", None)
        if _proj_id is None:
            _hdr = request.headers.get("X-Project-Id")
            if _hdr and _hdr.isdigit():
                _proj_id = int(_hdr)
        if _proj_id:
            from app.models import db
            from app.models.project import Project
            proj = db.session.get(Project, _proj_id)
            if proj:
                pid = proj.program_id
                logger.debug(
                    "Derived program_id=%d from project_id=%d (X-Project-Id header)",
                    pid, _proj_id,
                )

    g.explore_program_id = pid


def _get_program_id(data=None):
    """Extract program_id from request data, query params, or project context.

    Accepts both 'program_id' and legacy 'project_id' parameter names
    for backward compatibility during the explore FK migration (Faz 1).

    Falls back to ``g.explore_program_id`` which is resolved in the
    ``before_request`` hook from query params, body, or X-Project-Id header.

    Args:
        data: Optional request body dict.

    Returns:
        Tuple of (program_id, error_response). If program_id is found,
        error_response is None. If not found, program_id is None and
        error_response is a Flask error response tuple.
    """
    pid = None
    if data:
        pid = data.get("program_id") or data.get("project_id")
    if pid is None:
        pid = (
            request.args.get("program_id", type=int)
            or request.args.get("project_id", type=int)
        )
    if not pid:
        pid = getattr(g, "explore_program_id", None)
    if not pid:
        return None, api_error(E.VALIDATION_REQUIRED, "program_id is required")
    return pid, None


# Sub-module imports — each module registers routes on explore_bp
from app.blueprints.explore import workshops        # noqa: E402, F401
from app.blueprints.explore import process_levels   # noqa: E402, F401
from app.blueprints.explore import process_steps    # noqa: E402, F401
from app.blueprints.explore import requirements     # noqa: E402, F401
from app.blueprints.explore import open_items       # noqa: E402, F401
from app.blueprints.explore import supporting       # noqa: E402, F401
from app.blueprints.explore import catalog          # noqa: E402, F401
