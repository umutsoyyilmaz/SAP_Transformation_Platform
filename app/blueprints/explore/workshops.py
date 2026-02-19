"""Explore blueprint wrappers delegating ORM work to service layer."""

from flask import request

from app.blueprints.explore import explore_bp
from app.services import explore_service

@explore_bp.route("/workshops", methods=["GET"])
def list_workshops():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="list_workshops",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>", methods=["GET"])
def get_workshop(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="get_workshop",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>/full", methods=["GET"])
def get_workshop_full(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="get_workshop_full",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops", methods=["POST"])
def create_workshop():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="create_workshop",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>", methods=["PUT"])
def update_workshop(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="update_workshop",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>", methods=["DELETE"])
def delete_workshop(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="delete_workshop",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>/steps", methods=["GET"])
def list_workshop_steps(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="list_workshop_steps",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>/start", methods=["POST"])
def start_workshop(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="start_workshop",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>/complete", methods=["POST"])
def complete_workshop(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="complete_workshop",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<workshop_id>/reopen", methods=["POST"])
def reopen_workshop(workshop_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"workshop_id": workshop_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="reopen_workshop",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<workshop_id>/create-delta", methods=["POST"])
def create_delta_workshop(workshop_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"workshop_id": workshop_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="create_delta_workshop",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/capacity", methods=["GET"])
def workshop_capacity():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="workshop_capacity",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/stats", methods=["GET"])
def workshop_stats():
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="workshop_stats",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>/attendees", methods=["GET"])
def list_attendees(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="list_attendees",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>/attendees", methods=["POST"])
def create_attendee(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="create_attendee",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/attendees/<att_id>", methods=["PUT"])
def update_attendee(att_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"att_id": att_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="update_attendee",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/attendees/<att_id>", methods=["DELETE"])
def delete_attendee(att_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"att_id": att_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="delete_attendee",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>/agenda-items", methods=["GET"])
def list_agenda_items(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="list_agenda_items",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>/agenda-items", methods=["POST"])
def create_agenda_item(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="create_agenda_item",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/agenda-items/<item_id>", methods=["PUT"])
def update_agenda_item(item_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"item_id": item_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="update_agenda_item",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/agenda-items/<item_id>", methods=["DELETE"])
def delete_agenda_item(item_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"item_id": item_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="delete_agenda_item",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>/decisions", methods=["GET"])
def list_workshop_decisions(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="list_workshop_decisions",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/decisions/<dec_id>", methods=["PUT"])
def update_decision(dec_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"dec_id": dec_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="update_decision",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/decisions/<dec_id>", methods=["DELETE"])
def delete_decision(dec_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"dec_id": dec_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="delete_decision",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )

@explore_bp.route("/workshops/<ws_id>/sessions", methods=["GET"])
def list_workshop_sessions(ws_id):
    """Delegate endpoint logic to explore_service while keeping blueprint thin."""
    data = request.get_json(silent=True) or {}
    query_params = request.args.to_dict(flat=True)
    route_params = {"ws_id": ws_id}
    return explore_service.dispatch_workshops_endpoint(
        endpoint="list_workshop_sessions",
        route_params=route_params,
        query_params=query_params,
        data=data,
    )
