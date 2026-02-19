"""Explore blueprint wrappers delegating ORM work to service layer."""

from flask import request

from app.blueprints.explore import explore_bp
from app.services import explore_service

@explore_bp.route("/requirements", methods=["GET"])
def list_requirements():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="list_requirements",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements", methods=["POST"])
def create_requirement_flat():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="create_requirement_flat",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/<req_id>", methods=["GET"])
def get_requirement(req_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"req_id": req_id}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="get_requirement",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/<req_id>", methods=["PUT"])
def update_requirement(req_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"req_id": req_id}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="update_requirement",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/<req_id>/transition", methods=["POST"])
def transition_requirement_endpoint(req_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"req_id": req_id}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="transition_requirement_endpoint",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/<req_id>/link-open-item", methods=["POST"])
def link_open_item(req_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"req_id": req_id}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="link_open_item",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/<req_id>/add-dependency", methods=["POST"])
def add_requirement_dependency(req_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"req_id": req_id}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="add_requirement_dependency",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/batch-transition", methods=["POST"])
def batch_transition_endpoint():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="batch_transition_endpoint",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/bulk-sync-alm", methods=["POST"])
def bulk_sync_alm():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="bulk_sync_alm",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/stats", methods=["GET"])
def requirement_stats():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="requirement_stats",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/coverage-matrix", methods=["GET"])
def requirement_coverage_matrix():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="requirement_coverage_matrix",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/<string:req_id>/convert", methods=["POST"])
def convert_requirement_endpoint(req_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"req_id": req_id}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="convert_requirement_endpoint",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/batch-convert", methods=["POST"])
def batch_convert_endpoint():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="batch_convert_endpoint",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<workshop_id>/documents", methods=["GET"])
def list_workshop_documents(workshop_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"workshop_id": workshop_id}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="list_workshop_documents",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<workshop_id>/documents/generate", methods=["POST"])
def generate_workshop_document(workshop_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"workshop_id": workshop_id}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="generate_workshop_document",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/<requirement_id>/linked-items", methods=["GET"])
def get_requirement_linked_items(requirement_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"requirement_id": requirement_id}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="get_requirement_linked_items",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/requirements/<string:req_id>/unconvert", methods=["POST"])
def unconvert_requirement_endpoint(req_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"req_id": req_id}
    return explore_service.dispatch_requirements_endpoint(
        endpoint="unconvert_requirement_endpoint",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )
