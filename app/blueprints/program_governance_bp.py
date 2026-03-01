"""
SAP Transformation Management Platform
Program Governance blueprint — Faz 2.4.

Endpoints:
    REPORT       /api/v1/programs/<pid>/reports               GET, POST
                 /api/v1/program-reports/<id>                 GET, PUT, DELETE
                 /api/v1/program-reports/<id>/approve         POST
                 /api/v1/program-reports/<id>/present         POST
                 /api/v1/program-reports/<id>/project-statuses POST

    DECISION     /api/v1/programs/<pid>/decisions             GET, POST
                 /api/v1/program-decisions/<id>               GET, PUT, DELETE

    RISK         /api/v1/programs/<pid>/risks/program         GET, POST
                 /api/v1/program-risks/<id>                   GET, PUT, DELETE

    MILESTONE    /api/v1/programs/<pid>/milestones            GET, POST
                 /api/v1/program-milestones/<id>              GET, PUT, DELETE

    BUDGET       /api/v1/programs/<pid>/budget                GET, POST
                 /api/v1/programs/<pid>/budget/summary        GET
                 /api/v1/program-budgets/<id>                 GET, PUT, DELETE

    DEPENDENCY   /api/v1/programs/<pid>/dependencies          GET, POST
                 /api/v1/project-dependencies/<id>            GET, PUT, DELETE
"""

import logging

from flask import Blueprint, g, jsonify, request

from app.models import db
from app.models.program import Program
from app.models.program_governance import (
    ProgramReport,
    ProgramDecision,
    ProgramRisk,
    ProgramMilestone,
    ProgramBudget,
    ProjectDependency,
)
from app.services import program_governance_service as gov_svc
from app.services.helpers.scoped_queries import get_scoped_or_none
from app.utils.helpers import db_commit_or_error

logger = logging.getLogger(__name__)

program_governance_bp = Blueprint("program_governance", __name__, url_prefix="/api/v1")


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_program_or_404(pid: int):
    """Resolve program with tenant isolation."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if tenant_id is not None:
        prog = get_scoped_or_none(Program, pid, tenant_id=tenant_id)
    else:
        prog = Program.query.filter_by(id=pid).first()
    if not prog:
        return None, (jsonify({"error": "Program not found"}), 404)
    return prog, None


def _get_tenant_id() -> int | None:
    """Get current tenant ID from JWT context."""
    return getattr(g, "jwt_tenant_id", None)


def _get_entity_or_404(model, entity_id: int):
    """Resolve entity with tenant isolation."""
    tenant_id = _get_tenant_id()
    if tenant_id is not None:
        entity = get_scoped_or_none(model, entity_id, tenant_id=tenant_id)
    else:
        entity = db.session.get(model, entity_id)
    if not entity:
        return None, (jsonify({"error": f"{model.__name__} not found"}), 404)
    return entity, None


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM REPORT
# ═══════════════════════════════════════════════════════════════════════════


@program_governance_bp.route("/programs/<int:pid>/reports", methods=["GET"])
def list_reports(pid):
    """List all SteerCo reports for a program."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    tenant_id = _get_tenant_id() or prog.tenant_id
    return jsonify(gov_svc.list_reports(pid, tenant_id))


@program_governance_bp.route("/programs/<int:pid>/reports", methods=["POST"])
def create_report(pid):
    """Create a new SteerCo report."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400
    if len(data.get("title", "")) > 300:
        return jsonify({"error": "title too long (max 300)"}), 400

    tenant_id = _get_tenant_id() or prog.tenant_id
    user_id = getattr(g, "current_user", {}).get("id") if hasattr(g, "current_user") and isinstance(g.current_user, dict) else None
    data["created_by_id"] = user_id

    report = gov_svc.create_report(pid, tenant_id, data)
    db_commit_or_error()
    return jsonify(report.to_dict()), 201


@program_governance_bp.route("/program-reports/<int:rid>", methods=["GET"])
def get_report(rid):
    """Get a single report with optional details."""
    report, err = _get_entity_or_404(ProgramReport, rid)
    if err:
        return err
    include_details = request.args.get("include_details", "false").lower() == "true"
    return jsonify(report.to_dict(include_details=include_details))


@program_governance_bp.route("/program-reports/<int:rid>", methods=["PUT"])
def update_report(rid):
    """Update an existing report."""
    report, err = _get_entity_or_404(ProgramReport, rid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    try:
        report = gov_svc.update_report(report, data)
        db_commit_or_error()
        return jsonify(report.to_dict())
    except ValueError as e:
        return jsonify({"error": str(e)}), 422


@program_governance_bp.route("/program-reports/<int:rid>", methods=["DELETE"])
def delete_report(rid):
    """Delete a draft report."""
    report, err = _get_entity_or_404(ProgramReport, rid)
    if err:
        return err
    try:
        gov_svc.delete_report(report)
        db_commit_or_error()
        return jsonify({"message": "Report deleted"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 422


@program_governance_bp.route("/program-reports/<int:rid>/approve", methods=["POST"])
def approve_report(rid):
    """Approve a report and lock metrics snapshot."""
    report, err = _get_entity_or_404(ProgramReport, rid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    user_id = getattr(g, "current_user", {}).get("id") if hasattr(g, "current_user") and isinstance(g.current_user, dict) else None
    try:
        report = gov_svc.approve_report(report, user_id, data.get("metrics_snapshot"))
        db_commit_or_error()
        return jsonify(report.to_dict())
    except ValueError as e:
        return jsonify({"error": str(e)}), 422


@program_governance_bp.route("/program-reports/<int:rid>/present", methods=["POST"])
def present_report(rid):
    """Mark a report as presented."""
    report, err = _get_entity_or_404(ProgramReport, rid)
    if err:
        return err
    try:
        report = gov_svc.present_report(report)
        db_commit_or_error()
        return jsonify(report.to_dict())
    except ValueError as e:
        return jsonify({"error": str(e)}), 422


@program_governance_bp.route("/program-reports/<int:rid>/project-statuses", methods=["POST"])
def upsert_report_project_status(rid):
    """Create or update a project status entry within a report."""
    report, err = _get_entity_or_404(ProgramReport, rid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("project_id"):
        return jsonify({"error": "project_id is required"}), 400

    tenant_id = _get_tenant_id() or report.tenant_id
    status = gov_svc.upsert_report_project_status(
        rid, data["project_id"], tenant_id, data,
    )
    db_commit_or_error()
    return jsonify(status.to_dict()), 200


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM DECISION
# ═══════════════════════════════════════════════════════════════════════════


@program_governance_bp.route("/programs/<int:pid>/program-decisions", methods=["GET"])
def list_decisions(pid):
    """List all program-level decisions."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    tenant_id = _get_tenant_id() or prog.tenant_id
    return jsonify(gov_svc.list_decisions(pid, tenant_id))


@program_governance_bp.route("/programs/<int:pid>/program-decisions", methods=["POST"])
def create_decision(pid):
    """Create a new program-level decision."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400
    if len(data.get("title", "")) > 300:
        return jsonify({"error": "title too long (max 300)"}), 400

    tenant_id = _get_tenant_id() or prog.tenant_id
    user_id = getattr(g, "current_user", {}).get("id") if hasattr(g, "current_user") and isinstance(g.current_user, dict) else None
    data["created_by_id"] = user_id

    decision = gov_svc.create_decision(pid, tenant_id, data)
    db_commit_or_error()
    return jsonify(decision.to_dict()), 201


@program_governance_bp.route("/program-decisions/<int:did>", methods=["GET"])
def get_decision(did):
    """Get a single program decision."""
    decision, err = _get_entity_or_404(ProgramDecision, did)
    if err:
        return err
    return jsonify(decision.to_dict())


@program_governance_bp.route("/program-decisions/<int:did>", methods=["PUT"])
def update_decision(did):
    """Update an existing program decision."""
    decision, err = _get_entity_or_404(ProgramDecision, did)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    decision = gov_svc.update_decision(decision, data)
    db_commit_or_error()
    return jsonify(decision.to_dict())


@program_governance_bp.route("/program-decisions/<int:did>", methods=["DELETE"])
def delete_decision(did):
    """Delete a program decision."""
    decision, err = _get_entity_or_404(ProgramDecision, did)
    if err:
        return err
    gov_svc.delete_decision(decision)
    db_commit_or_error()
    return jsonify({"message": "Decision deleted"}), 200


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM RISK
# ═══════════════════════════════════════════════════════════════════════════


@program_governance_bp.route("/programs/<int:pid>/risks/program", methods=["GET"])
def list_risks(pid):
    """List all program-level risks (distinct from RAID risks at /programs/<pid>/risks)."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    tenant_id = _get_tenant_id() or prog.tenant_id
    return jsonify(gov_svc.list_risks(pid, tenant_id))


@program_governance_bp.route("/programs/<int:pid>/risks/program", methods=["POST"])
def create_risk(pid):
    """Create a new program-level risk."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400
    if len(data.get("title", "")) > 300:
        return jsonify({"error": "title too long (max 300)"}), 400

    tenant_id = _get_tenant_id() or prog.tenant_id
    user_id = getattr(g, "current_user", {}).get("id") if hasattr(g, "current_user") and isinstance(g.current_user, dict) else None
    data["created_by_id"] = user_id

    risk = gov_svc.create_risk(pid, tenant_id, data)
    db_commit_or_error()
    return jsonify(risk.to_dict()), 201


@program_governance_bp.route("/program-risks/<int:rid>", methods=["GET"])
def get_risk(rid):
    """Get a single program risk."""
    risk, err = _get_entity_or_404(ProgramRisk, rid)
    if err:
        return err
    return jsonify(risk.to_dict())


@program_governance_bp.route("/program-risks/<int:rid>", methods=["PUT"])
def update_risk(rid):
    """Update an existing program risk."""
    risk, err = _get_entity_or_404(ProgramRisk, rid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    risk = gov_svc.update_risk(risk, data)
    db_commit_or_error()
    return jsonify(risk.to_dict())


@program_governance_bp.route("/program-risks/<int:rid>", methods=["DELETE"])
def delete_risk(rid):
    """Delete a program risk."""
    risk, err = _get_entity_or_404(ProgramRisk, rid)
    if err:
        return err
    gov_svc.delete_risk(risk)
    db_commit_or_error()
    return jsonify({"message": "Risk deleted"}), 200


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM MILESTONE
# ═══════════════════════════════════════════════════════════════════════════


@program_governance_bp.route("/programs/<int:pid>/milestones", methods=["GET"])
def list_milestones(pid):
    """List all program milestones."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    tenant_id = _get_tenant_id() or prog.tenant_id
    return jsonify(gov_svc.list_milestones(pid, tenant_id))


@program_governance_bp.route("/programs/<int:pid>/milestones", methods=["POST"])
def create_milestone(pid):
    """Create a new program milestone."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400
    if len(data.get("title", "")) > 300:
        return jsonify({"error": "title too long (max 300)"}), 400

    tenant_id = _get_tenant_id() or prog.tenant_id
    user_id = getattr(g, "current_user", {}).get("id") if hasattr(g, "current_user") and isinstance(g.current_user, dict) else None
    data["created_by_id"] = user_id

    milestone = gov_svc.create_milestone(pid, tenant_id, data)
    db_commit_or_error()
    return jsonify(milestone.to_dict()), 201


@program_governance_bp.route("/program-milestones/<int:mid>", methods=["GET"])
def get_milestone(mid):
    """Get a single program milestone."""
    ms, err = _get_entity_or_404(ProgramMilestone, mid)
    if err:
        return err
    return jsonify(ms.to_dict())


@program_governance_bp.route("/program-milestones/<int:mid>", methods=["PUT"])
def update_milestone(mid):
    """Update an existing program milestone."""
    ms, err = _get_entity_or_404(ProgramMilestone, mid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    ms = gov_svc.update_milestone(ms, data)
    db_commit_or_error()
    return jsonify(ms.to_dict())


@program_governance_bp.route("/program-milestones/<int:mid>", methods=["DELETE"])
def delete_milestone(mid):
    """Delete a program milestone."""
    ms, err = _get_entity_or_404(ProgramMilestone, mid)
    if err:
        return err
    gov_svc.delete_milestone(ms)
    db_commit_or_error()
    return jsonify({"message": "Milestone deleted"}), 200


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM BUDGET
# ═══════════════════════════════════════════════════════════════════════════


@program_governance_bp.route("/programs/<int:pid>/budget", methods=["GET"])
def list_budgets(pid):
    """List all budget line items for a program."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    tenant_id = _get_tenant_id() or prog.tenant_id
    return jsonify(gov_svc.list_budgets(pid, tenant_id))


@program_governance_bp.route("/programs/<int:pid>/budget", methods=["POST"])
def create_budget(pid):
    """Create a new budget line item."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("category"):
        return jsonify({"error": "category is required"}), 400

    tenant_id = _get_tenant_id() or prog.tenant_id
    budget = gov_svc.create_budget(pid, tenant_id, data)
    db_commit_or_error()
    return jsonify(budget.to_dict()), 201


@program_governance_bp.route("/programs/<int:pid>/budget/summary", methods=["GET"])
def budget_summary(pid):
    """Get aggregated budget summary."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    tenant_id = _get_tenant_id() or prog.tenant_id
    return jsonify(gov_svc.get_budget_summary(pid, tenant_id))


@program_governance_bp.route("/program-budgets/<int:bid>", methods=["GET"])
def get_budget(bid):
    """Get a single budget line item."""
    budget, err = _get_entity_or_404(ProgramBudget, bid)
    if err:
        return err
    return jsonify(budget.to_dict())


@program_governance_bp.route("/program-budgets/<int:bid>", methods=["PUT"])
def update_budget(bid):
    """Update an existing budget line item."""
    budget, err = _get_entity_or_404(ProgramBudget, bid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    budget = gov_svc.update_budget(budget, data)
    db_commit_or_error()
    return jsonify(budget.to_dict())


@program_governance_bp.route("/program-budgets/<int:bid>", methods=["DELETE"])
def delete_budget(bid):
    """Delete a budget line item."""
    budget, err = _get_entity_or_404(ProgramBudget, bid)
    if err:
        return err
    gov_svc.delete_budget(budget)
    db_commit_or_error()
    return jsonify({"message": "Budget item deleted"}), 200


# ═══════════════════════════════════════════════════════════════════════════
#  PROJECT DEPENDENCY
# ═══════════════════════════════════════════════════════════════════════════


@program_governance_bp.route("/programs/<int:pid>/dependencies", methods=["GET"])
def list_dependencies(pid):
    """List all inter-project dependencies."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    tenant_id = _get_tenant_id() or prog.tenant_id
    return jsonify(gov_svc.list_dependencies(pid, tenant_id))


@program_governance_bp.route("/programs/<int:pid>/dependencies", methods=["POST"])
def create_dependency(pid):
    """Create a new inter-project dependency."""
    prog, err = _get_program_or_404(pid)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("source_project_id") or not data.get("target_project_id"):
        return jsonify({"error": "source_project_id and target_project_id are required"}), 400

    tenant_id = _get_tenant_id() or prog.tenant_id
    user_id = getattr(g, "current_user", {}).get("id") if hasattr(g, "current_user") and isinstance(g.current_user, dict) else None
    data["created_by_id"] = user_id

    try:
        dep = gov_svc.create_dependency(pid, tenant_id, data)
        db_commit_or_error()
        return jsonify(dep.to_dict()), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 422


@program_governance_bp.route("/project-dependencies/<int:did>", methods=["GET"])
def get_dependency(did):
    """Get a single project dependency."""
    dep, err = _get_entity_or_404(ProjectDependency, did)
    if err:
        return err
    return jsonify(dep.to_dict())


@program_governance_bp.route("/project-dependencies/<int:did>", methods=["PUT"])
def update_dependency(did):
    """Update an existing project dependency."""
    dep, err = _get_entity_or_404(ProjectDependency, did)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    dep = gov_svc.update_dependency(dep, data)
    db_commit_or_error()
    return jsonify(dep.to_dict())


@program_governance_bp.route("/project-dependencies/<int:did>", methods=["DELETE"])
def delete_dependency(did):
    """Delete a project dependency."""
    dep, err = _get_entity_or_404(ProjectDependency, did)
    if err:
        return err
    gov_svc.delete_dependency(dep)
    db_commit_or_error()
    return jsonify({"message": "Dependency deleted"}), 200
