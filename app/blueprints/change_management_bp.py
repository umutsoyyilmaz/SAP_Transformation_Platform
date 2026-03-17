"""Enterprise Change Management API blueprint."""

from __future__ import annotations

import logging

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.models import db
from app.services import change_management_service as svc

change_management_bp = Blueprint(
    "change_management", __name__, url_prefix="/api/v1/change-management"
)
logger = logging.getLogger(__name__)


def _coerce_int(value):
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _request_tenant_id() -> int | None:
    for attr in ("jwt_tenant_id", "tenant_id"):
        value = getattr(g, attr, None)
        if value is not None:
            return _coerce_int(value)
    return None


def _request_scope(data: dict | None = None) -> dict:
    data = data or {}
    return {
        "tenant_id": _request_tenant_id(),
        "program_id": _coerce_int(data.get("program_id")) or request.args.get("program_id", type=int),
        "project_id": _coerce_int(data.get("project_id")) or request.args.get("project_id", type=int) or _coerce_int(getattr(g, "project_id", None)),
    }


def _json_body() -> dict:
    return request.get_json(silent=True) or {}


def _respond(payload, status: int = 200):
    return jsonify(payload), status


def _handle(callable_, *args, status: int = 200, **kwargs):
    try:
        return _respond(callable_(*args, **kwargs), status)
    except ValueError as exc:
        return _respond({"error": str(exc)}, 400)


@change_management_bp.errorhandler(SQLAlchemyError)
def _handle_sqlalchemy_error(exc):
    db.session.rollback()
    logger.exception("Change Management database error: %s", exc)
    return jsonify({"error": "Database error"}), 500


@change_management_bp.route("/change-requests", methods=["GET"])
def list_change_requests():
    scope = _request_scope()
    return _handle(
        svc.list_change_requests,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=request.args.get("status"),
        change_model=request.args.get("change_model"),
        change_domain=request.args.get("change_domain"),
        search=request.args.get("search"),
    )


@change_management_bp.route("/change-requests", methods=["POST"])
def create_change_request():
    data = _json_body()
    return _handle(svc.create_change_request, data, tenant_id=_request_tenant_id(), status=201)


@change_management_bp.route("/change-requests/<int:change_request_id>", methods=["GET"])
def get_change_request(change_request_id: int):
    scope = _request_scope()
    return _handle(
        svc.get_change_request,
        change_request_id,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        include_children=request.args.get("include") == "children",
    )


@change_management_bp.route("/change-requests/<int:change_request_id>", methods=["PUT"])
def update_change_request(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.update_change_request,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/submit", methods=["POST"])
def submit_change_request(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.submit_change_request,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/assess", methods=["POST"])
def assess_change_request(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.assess_change_request,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/route", methods=["POST"])
def route_change_request(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.route_change_request,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/schedule", methods=["POST"])
def schedule_change_request(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.schedule_change_request,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/validate", methods=["POST"])
def validate_change_request(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.validate_change_request,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/close", methods=["POST"])
def close_change_request(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.close_change_request,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/links", methods=["GET"])
def get_change_request_links(change_request_id: int):
    scope = _request_scope()
    return _handle(
        svc.list_change_links,
        change_request_id,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/links", methods=["POST"])
def add_change_request_link(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.add_change_link,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=201,
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/decisions", methods=["POST"])
def create_change_request_decision(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.create_decision,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=201,
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/exceptions", methods=["GET"])
def list_change_request_exceptions(change_request_id: int):
    scope = _request_scope()
    return _handle(
        svc.list_freeze_exceptions,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=request.args.get("status"),
        change_request_id=change_request_id,
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/exceptions", methods=["POST"])
def create_change_request_exception(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.create_freeze_exception,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=201,
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/implementations", methods=["GET"])
def list_change_request_implementations(change_request_id: int):
    scope = _request_scope()
    return _handle(
        svc.list_implementations,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        change_request_id=change_request_id,
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/implementations", methods=["POST"])
def create_change_request_implementation(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.create_implementation,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=201,
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/pir", methods=["GET"])
def list_change_request_pir(change_request_id: int):
    scope = _request_scope()
    return _handle(
        svc.list_pirs,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=request.args.get("status"),
        change_request_id=change_request_id,
    )


@change_management_bp.route("/change-requests/<int:change_request_id>/pir", methods=["POST"])
def create_change_request_pir(change_request_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.create_pir,
        change_request_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=201,
    )


@change_management_bp.route("/boards", methods=["GET"])
def list_boards():
    scope = _request_scope()
    return _handle(
        svc.list_boards,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        board_kind=request.args.get("board_kind"),
    )


@change_management_bp.route("/boards", methods=["POST"])
def create_board():
    data = _json_body()
    return _handle(svc.create_board_profile, data, tenant_id=_request_tenant_id(), status=201)


@change_management_bp.route("/boards/<int:board_profile_id>", methods=["GET"])
def get_board(board_profile_id: int):
    scope = _request_scope()
    return _handle(
        svc.get_board_profile,
        board_profile_id,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/boards/<int:board_profile_id>", methods=["PUT"])
def update_board(board_profile_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.update_board_profile,
        board_profile_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/boards/<int:board_profile_id>/meetings", methods=["GET"])
def list_board_meetings(board_profile_id: int):
    scope = _request_scope()
    return _handle(
        svc.list_meetings,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        board_profile_id=board_profile_id,
    )


@change_management_bp.route("/boards/<int:board_profile_id>/meetings", methods=["POST"])
def create_board_meeting(board_profile_id: int):
    data = _json_body()
    data.setdefault("board_profile_id", board_profile_id)
    return _handle(svc.create_meeting, data, tenant_id=_request_tenant_id(), status=201)


@change_management_bp.route("/meetings", methods=["GET"])
def list_meetings():
    scope = _request_scope()
    return _handle(
        svc.list_meetings,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        board_profile_id=request.args.get("board_profile_id", type=int),
    )


@change_management_bp.route("/meetings/<int:meeting_id>", methods=["GET"])
def get_meeting(meeting_id: int):
    scope = _request_scope()
    return _handle(
        svc.get_meeting,
        meeting_id,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/meetings/<int:meeting_id>", methods=["PUT"])
def update_meeting(meeting_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.update_meeting,
        meeting_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/meetings/<int:meeting_id>/attendance", methods=["POST"])
def add_attendance(meeting_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.add_meeting_attendance,
        meeting_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=201,
    )


@change_management_bp.route("/decisions", methods=["GET"])
def list_decisions():
    scope = _request_scope()
    return _handle(
        svc.list_decisions,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        change_request_id=request.args.get("change_request_id", type=int),
        board_profile_id=request.args.get("board_profile_id", type=int),
    )


@change_management_bp.route("/templates", methods=["GET"])
def list_templates():
    scope = _request_scope()
    return _handle(
        svc.list_standard_templates,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/templates", methods=["POST"])
def create_template():
    data = _json_body()
    return _handle(svc.create_standard_template, data, tenant_id=_request_tenant_id(), status=201)


@change_management_bp.route("/templates/<int:template_id>/instantiate", methods=["POST"])
def instantiate_template(template_id: int):
    data = _json_body()
    return _handle(svc.instantiate_standard_template, template_id, data, tenant_id=_request_tenant_id(), status=201)


@change_management_bp.route("/policies", methods=["GET"])
def list_policies():
    scope = _request_scope()
    return _handle(
        svc.list_policy_rules,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/policies", methods=["POST"])
def create_policy():
    data = _json_body()
    return _handle(svc.create_policy_rule, data, tenant_id=_request_tenant_id(), status=201)


@change_management_bp.route("/windows", methods=["GET"])
def list_windows():
    scope = _request_scope()
    return _handle(
        svc.list_calendar_windows,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        window_type=request.args.get("window_type"),
    )


@change_management_bp.route("/windows", methods=["POST"])
def create_window():
    data = _json_body()
    return _handle(svc.create_calendar_window, data, tenant_id=_request_tenant_id(), status=201)


@change_management_bp.route("/windows/<int:window_id>", methods=["PUT"])
def update_window(window_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.update_calendar_window,
        window_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/exceptions", methods=["GET"])
def list_exceptions():
    scope = _request_scope()
    return _handle(
        svc.list_freeze_exceptions,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=request.args.get("status"),
    )


@change_management_bp.route("/exceptions/<int:exception_id>/approve", methods=["POST"])
def approve_exception(exception_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.decide_freeze_exception,
        exception_id,
        data,
        approve=True,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/exceptions/<int:exception_id>/reject", methods=["POST"])
def reject_exception(exception_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.decide_freeze_exception,
        exception_id,
        data,
        approve=False,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/implementations", methods=["GET"])
def list_implementations():
    scope = _request_scope()
    return _handle(
        svc.list_implementations,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        change_request_id=request.args.get("change_request_id", type=int),
    )


@change_management_bp.route("/implementations/<int:implementation_id>/start", methods=["POST"])
def start_implementation(implementation_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.start_implementation,
        implementation_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/implementations/<int:implementation_id>/complete", methods=["POST"])
def complete_implementation(implementation_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.complete_implementation,
        implementation_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/implementations/<int:implementation_id>/rollback", methods=["POST"])
def rollback_implementation(implementation_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.create_rollback,
        implementation_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=201,
    )


@change_management_bp.route("/pir", methods=["GET"])
def list_pir():
    scope = _request_scope()
    return _handle(
        svc.list_pirs,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=request.args.get("status"),
    )


@change_management_bp.route("/pir/<int:pir_id>", methods=["GET"])
def get_pir(pir_id: int):
    scope = _request_scope()
    return _handle(
        svc.get_pir_record,
        pir_id,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/pir/<int:pir_id>", methods=["PUT"])
def update_pir(pir_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.update_pir,
        pir_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/pir/<int:pir_id>/findings", methods=["POST"])
def add_pir_finding(pir_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.add_pir_finding,
        pir_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=201,
    )


@change_management_bp.route("/pir/<int:pir_id>/actions", methods=["POST"])
def add_pir_action(pir_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.add_pir_action,
        pir_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
        status=201,
    )


@change_management_bp.route("/pir/<int:pir_id>/complete", methods=["POST"])
def complete_pir(pir_id: int):
    data = _json_body()
    scope = _request_scope(data)
    return _handle(
        svc.complete_pir,
        pir_id,
        data,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )


@change_management_bp.route("/analytics", methods=["GET"])
def analytics():
    scope = _request_scope()
    return _handle(
        svc.analytics_summary,
        tenant_id=scope["tenant_id"],
        program_id=scope["program_id"],
        project_id=scope["project_id"],
    )
