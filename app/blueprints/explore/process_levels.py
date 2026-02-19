"""Explore blueprint wrappers delegating ORM work to service layer."""

from flask import request

from app.blueprints.explore import explore_bp
from app.services import explore_service

@explore_bp.route("/process-levels/<pl_id>/change-history", methods=["GET"])
def get_process_level_change_history(pl_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"pl_id": pl_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="get_process_level_change_history",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels", methods=["GET"])
def list_process_levels():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="list_process_levels",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/import-template", methods=["POST"])
def import_process_template():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="import_process_template",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/bulk", methods=["POST"])
def bulk_create_process_levels():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="bulk_create_process_levels",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels", methods=["POST"])
def create_process_level():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="create_process_level",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<pl_id>", methods=["DELETE"])
def delete_process_level(pl_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"pl_id": pl_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="delete_process_level",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<pl_id>", methods=["GET"])
def get_process_level(pl_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"pl_id": pl_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="get_process_level",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<pl_id>", methods=["PUT"])
def update_process_level(pl_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"pl_id": pl_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="update_process_level",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/scope-matrix", methods=["GET"])
def get_scope_matrix():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="get_scope_matrix",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<l3_id>/seed-from-catalog", methods=["POST"])
def seed_from_catalog(l3_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"l3_id": l3_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="seed_from_catalog",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<l3_id>/children", methods=["POST"])
def add_l4_child(l3_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"l3_id": l3_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="add_l4_child",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<l3_id>/consolidate-fit", methods=["POST"])
def consolidate_fit(l3_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"l3_id": l3_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="consolidate_fit",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<l3_id>/consolidated-view", methods=["GET"])
def get_consolidated_view_endpoint(l3_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"l3_id": l3_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="get_consolidated_view_endpoint",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<l3_id>/override-fit-status", methods=["POST"])
def override_fit_endpoint(l3_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"l3_id": l3_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="override_fit_endpoint",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<l3_id>/signoff", methods=["POST"])
def signoff_endpoint(l3_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"l3_id": l3_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="signoff_endpoint",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/l2-readiness", methods=["GET"])
def l2_readiness():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="l2_readiness",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<l2_id>/confirm", methods=["POST"])
def confirm_l2(l2_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"l2_id": l2_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="confirm_l2",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/area-milestones", methods=["GET"])
def area_milestones():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="area_milestones",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<level_id>/bpmn", methods=["GET"])
def get_bpmn(level_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"level_id": level_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="get_bpmn",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/process-levels/<level_id>/bpmn", methods=["POST"])
def create_bpmn(level_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"level_id": level_id}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="create_bpmn",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/fit-propagation/propagate", methods=["POST"])
def run_fit_propagation():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_process_levels_endpoint(
        endpoint="run_fit_propagation",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )
