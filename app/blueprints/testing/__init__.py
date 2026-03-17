"""Testing API blueprint composition root."""

from flask import Blueprint

from .analytics import register_testing_analytics_routes
from .catalog import register_testing_catalog_routes
from .defect import register_testing_defect_routes
from .execution import register_testing_execution_routes
from .operational_permissions import register_testing_operational_permission_routes
from .planning import register_testing_planning_routes
from .route_helpers import (
    _active_testing_project_id,
    _get_or_404,
    _request_project_id,
    _resolved_testing_project_id,
)

testing_bp = Blueprint("testing", __name__, url_prefix="/api/v1")

register_testing_catalog_routes(
    testing_bp,
    get_or_404=_get_or_404,
    resolved_testing_project_id=_resolved_testing_project_id,
    request_project_id=_request_project_id,
)
register_testing_execution_routes(
    testing_bp,
    get_or_404=_get_or_404,
)
register_testing_operational_permission_routes(
    testing_bp,
    get_or_404=_get_or_404,
)
register_testing_defect_routes(
    testing_bp,
    get_or_404=_get_or_404,
    resolved_testing_project_id=_resolved_testing_project_id,
)
register_testing_analytics_routes(
    testing_bp,
    get_or_404=_get_or_404,
    resolved_testing_project_id=_resolved_testing_project_id,
)
register_testing_planning_routes(
    testing_bp,
    get_or_404=_get_or_404,
    request_project_id=_request_project_id,
    active_testing_project_id=_active_testing_project_id,
)
