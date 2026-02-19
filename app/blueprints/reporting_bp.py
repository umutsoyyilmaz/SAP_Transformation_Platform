from datetime import datetime

from flask import Blueprint, jsonify, request, send_file

from app.models import db
from app.models.program import Program
from app.models.reporting import ReportDefinition, DashboardLayout
from app.services.reporting import compute_program_health
from app.services.metrics import ExploreMetrics
from app.services.report_engine import ReportEngine
from app.services.dashboard_engine import DashboardEngine
from app.services.export_service import (
    export_program_health_html,
    export_program_health_xlsx,
)

reporting_bp = Blueprint("reporting", __name__, url_prefix="/api/v1/reports")


@reporting_bp.route("/program-health/<int:pid>", methods=["GET"])
def program_health(pid):
    """
    GET /api/v1/reports/program-health/<pid>
    Returns full program health snapshot with RAG per area.
    """
    program = db.session.get(Program, pid)
    if not program:
        return jsonify({"error": "Program not found"}), 404
    return jsonify(compute_program_health(pid)), 200


@reporting_bp.route("/program/<int:pid>/health", methods=["GET"])
def program_explore_health(pid):
    """
    GET /api/v1/reports/program/<pid>/health
    Returns Explore-only health metrics with governance thresholds.
    """
    from app.models.program import Program as _Prog
    program = db.session.get(_Prog, pid)
    if not program:
        return jsonify({"error": "Program not found"}), 404
    return jsonify(ExploreMetrics.program_health(pid)), 200


@reporting_bp.route("/weekly/<int:pid>", methods=["GET"])
def weekly_report(pid):
    """
    GET /api/v1/reports/weekly/<pid>
    Returns program health + comparison to last snapshot (if exists).
    For now, just returns current health. Historical snapshots will be
    added when we implement snapshot storage.
    """
    program = db.session.get(Program, pid)
    if not program:
        return jsonify({"error": "Program not found"}), 404

    health = compute_program_health(pid)
    health["report_type"] = "weekly"
    return jsonify(health), 200


@reporting_bp.route("/export/xlsx/<int:pid>", methods=["GET"])
def export_xlsx(pid):
    """GET /api/v1/reports/export/xlsx/<pid> — Download Excel report."""
    program = db.session.get(Program, pid)
    if not program:
        return jsonify({"error": "Program not found"}), 404
    health = compute_program_health(pid)
    buf = export_program_health_xlsx(health)
    filename = f"program_health_{pid}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        buf,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@reporting_bp.route("/export/pdf/<int:pid>", methods=["GET"])
def export_pdf(pid):
    """GET /api/v1/reports/export/pdf/<pid> — Download HTML report (print-ready)."""
    program = db.session.get(Program, pid)
    if not program:
        return jsonify({"error": "Program not found"}), 404
    health = compute_program_health(pid)
    html = export_program_health_html(health)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


# ═════════════════════════════════════════════════════════════════════════════
# F5 — Preset Report Library
# ═════════════════════════════════════════════════════════════════════════════

@reporting_bp.route("/presets", methods=["GET"])
def list_presets():
    """GET /api/v1/reports/presets — List all preset report types."""
    presets = ReportEngine.list_presets()
    category = request.args.get("category")
    if category:
        presets = [p for p in presets if p["category"] == category]
    return jsonify({"presets": presets}), 200


@reporting_bp.route("/presets/<string:report_key>/<int:pid>", methods=["GET"])
def run_preset(report_key, pid):
    """GET /api/v1/reports/presets/<key>/<pid> — Run a preset report."""
    program = db.session.get(Program, pid)
    if not program:
        return jsonify({"error": "Program not found"}), 404
    kwargs = {}
    if request.args.get("days"):
        kwargs["days"] = int(request.args["days"])
    result = ReportEngine.run(report_key, pid, **kwargs)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200


# ═════════════════════════════════════════════════════════════════════════════
# F5 — Report Definition CRUD
# ═════════════════════════════════════════════════════════════════════════════

@reporting_bp.route("/definitions", methods=["GET"])
def list_definitions():
    """GET /api/v1/reports/definitions — List saved report definitions."""
    pid = request.args.get("program_id", type=int)
    q = ReportDefinition.query
    if pid:
        q = q.filter_by(program_id=pid)
    category = request.args.get("category")
    if category:
        q = q.filter_by(category=category)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    paginated = q.order_by(ReportDefinition.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "definitions": [d.to_dict() for d in paginated.items],
        "total": paginated.total,
        "page": page,
        "per_page": per_page,
    }), 200


@reporting_bp.route("/definitions", methods=["POST"])
def create_definition():
    """POST /api/v1/reports/definitions — Create a report definition."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    defn = ReportDefinition(
        program_id=data.get("program_id"),
        name=name,
        description=data.get("description", ""),
        category=data.get("category", "custom"),
        query_type=data.get("query_type", "preset"),
        query_config=data.get("query_config", {}),
        chart_type=data.get("chart_type", "table"),
        chart_config=data.get("chart_config", {}),
        is_preset=data.get("is_preset", False),
        is_public=data.get("is_public", True),
        created_by=data.get("created_by"),
        schedule=data.get("schedule"),
    )
    db.session.add(defn)
    db.session.commit()
    return jsonify(defn.to_dict()), 201


@reporting_bp.route("/definitions/<int:did>", methods=["GET"])
def get_definition(did):
    """GET /api/v1/reports/definitions/<id> — Get report definition."""
    defn = db.session.get(ReportDefinition, did)
    if not defn:
        return jsonify({"error": "Not found"}), 404
    return jsonify(defn.to_dict()), 200


@reporting_bp.route("/definitions/<int:did>", methods=["PUT"])
def update_definition(did):
    """PUT /api/v1/reports/definitions/<id> — Update report definition."""
    defn = db.session.get(ReportDefinition, did)
    if not defn:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "category", "query_type", "query_config",
                  "chart_type", "chart_config", "is_preset", "is_public", "schedule"):
        if field in data:
            setattr(defn, field, data[field])
    db.session.commit()
    return jsonify(defn.to_dict()), 200


@reporting_bp.route("/definitions/<int:did>", methods=["DELETE"])
def delete_definition(did):
    """DELETE /api/v1/reports/definitions/<id> — Delete report definition."""
    defn = db.session.get(ReportDefinition, did)
    if not defn:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(defn)
    db.session.commit()
    return jsonify({"deleted": True}), 200


@reporting_bp.route("/definitions/<int:did>/run", methods=["GET"])
def run_definition(did):
    """GET /api/v1/reports/definitions/<id>/run — Execute a saved report."""
    defn = db.session.get(ReportDefinition, did)
    if not defn:
        return jsonify({"error": "Not found"}), 404
    if defn.query_type == "preset":
        report_key = (defn.query_config or {}).get("preset_key", "")
        if not report_key:
            return jsonify({"error": "No preset_key in query_config"}), 400
        result = ReportEngine.run(report_key, defn.program_id or 0)
    else:
        result = {"error": "Custom query builder not yet implemented"}
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200


# ═════════════════════════════════════════════════════════════════════════════
# F5 — Dashboard Layout CRUD
# ═════════════════════════════════════════════════════════════════════════════

@reporting_bp.route("/dashboards", methods=["GET"])
def list_dashboards():
    """GET /api/v1/reports/dashboards — List dashboard layouts."""
    pid = request.args.get("program_id", type=int)
    q = DashboardLayout.query
    if pid:
        q = q.filter_by(program_id=pid)
    return jsonify({"dashboards": [d.to_dict() for d in q.all()]}), 200


@reporting_bp.route("/dashboards", methods=["POST"])
def create_dashboard():
    """POST /api/v1/reports/dashboards — Create dashboard layout."""
    data = request.get_json(silent=True) or {}
    if not data.get("program_id"):
        return jsonify({"error": "program_id is required"}), 400
    layout = DashboardLayout(
        user_id=data.get("user_id"),
        program_id=data["program_id"],
        layout=data.get("layout", []),
    )
    db.session.add(layout)
    db.session.commit()
    return jsonify(layout.to_dict()), 201


@reporting_bp.route("/dashboards/<int:did>", methods=["GET"])
def get_dashboard(did):
    """GET /api/v1/reports/dashboards/<id> — Get dashboard layout."""
    layout = db.session.get(DashboardLayout, did)
    if not layout:
        return jsonify({"error": "Not found"}), 404
    return jsonify(layout.to_dict()), 200


@reporting_bp.route("/dashboards/<int:did>", methods=["PUT"])
def update_dashboard(did):
    """PUT /api/v1/reports/dashboards/<id> — Update dashboard layout."""
    layout = db.session.get(DashboardLayout, did)
    if not layout:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    if "layout" in data:
        layout.layout = data["layout"]
    db.session.commit()
    return jsonify(layout.to_dict()), 200


@reporting_bp.route("/dashboards/<int:did>", methods=["DELETE"])
def delete_dashboard(did):
    """DELETE /api/v1/reports/dashboards/<id> — Delete dashboard layout."""
    layout = db.session.get(DashboardLayout, did)
    if not layout:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(layout)
    db.session.commit()
    return jsonify({"deleted": True}), 200


# ═════════════════════════════════════════════════════════════════════════════
# F5 — Dashboard Gadgets API
# ═════════════════════════════════════════════════════════════════════════════

@reporting_bp.route("/gadgets/types", methods=["GET"])
def gadget_types():
    """GET /api/v1/reports/gadgets/types — List available gadget types."""
    return jsonify({"gadgets": DashboardEngine.list_gadget_types()}), 200


@reporting_bp.route("/gadgets/<string:gadget_type>/<int:pid>", methods=["GET"])
def gadget_data(gadget_type, pid):
    """GET /api/v1/reports/gadgets/<type>/<pid> — Get gadget data."""
    program = db.session.get(Program, pid)
    if not program:
        return jsonify({"error": "Program not found"}), 404
    result = DashboardEngine.compute(gadget_type, pid)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200
