"""
Explore Phase Management — Blueprint Package

Splits the monolithic explore_bp.py into cohesive sub-modules while
keeping a single Blueprint instance and preserving all URL routes.
"""

from flask import Blueprint, request

from app.utils.errors import E, api_error

explore_bp = Blueprint("explore", __name__, url_prefix="/api/v1/explore")


def _get_program_id(data=None):
    """Extract program_id from request data or query params.

    Accepts both 'program_id' and legacy 'project_id' parameter names
    for backward compatibility during the explore FK migration (Faz 1).

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
