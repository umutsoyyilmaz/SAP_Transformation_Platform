from datetime import datetime

from flask import Blueprint, jsonify, send_file

from app.models import db
from app.models.program import Program
from app.services.reporting import compute_program_health
from app.services.metrics import ExploreMetrics
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
