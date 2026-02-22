"""
Fit-Gap report and general export endpoints.

S2-04 (FDD-F03):
    GET /api/v1/projects/<project_id>/export/fitgap
        format: excel | csv (default: excel)
        include_wricef: 1 | 0 (default: 1)
        include_config: 1 | 0 (default: 1)
        classification: comma-separated fit_status values (optional)
        sap_module: comma-separated module codes (optional)
        workshop_id: int (optional)

Audit A1: PDF format intentionally omitted (weasyprint system-level deps
    break Railway/Docker builds). Implement if PDF is required after
    confirming build environment supports Pango/Cairo.
Audit A3: Tenant isolation — all queries scoped by tenant_id.
    No temp files — content returned in-memory.
"""

import logging
from datetime import datetime, timezone

from flask import Blueprint, Response, g, jsonify, request

from app.services.export_service import generate_fitgap_excel, generate_requirement_csv

logger = logging.getLogger(__name__)

export_bp = Blueprint("export", __name__, url_prefix="/api/v1")


@export_bp.route("/projects/<int:project_id>/export/fitgap", methods=["GET"])
def export_fitgap(project_id: int):
    """Export a Fit-Gap analysis report for the given project.

    Supported formats: excel (.xlsx), csv.
    PDF is not available in this release (Audit A1).

    Query params:
        format: excel | csv (default: excel)
        include_wricef: 1 | 0 (default: 1)
        include_config: 1 | 0 (default: 1)
        classification: comma-separated fit_status filter, e.g. "fit,gap"
        sap_module: comma-separated SAP module filter, e.g. "FI,MM"
        workshop_id: int — restrict to a single workshop

    Returns:
        Binary file download (xlsx or csv) with correct Content-Disposition.
    """
    _raw_tid = getattr(g, "tenant_id", None)
    tenant_id: int | None = _raw_tid if isinstance(_raw_tid, int) else None
    fmt = request.args.get("format", "excel").lower()

    if fmt not in ("excel", "csv"):
        return jsonify({
            "error": "Unsupported format. Supported values: excel, csv.",
            "code": "INVALID_FORMAT",
        }), 400

    include_wricef = request.args.get("include_wricef", "1") != "0"
    include_config = request.args.get("include_config", "1") != "0"

    raw_classification = request.args.get("classification", "")
    classification_filter = (
        [c.strip() for c in raw_classification.split(",") if c.strip()]
        if raw_classification
        else None
    )

    raw_module = request.args.get("sap_module", "")
    sap_module_filter = (
        [m.strip() for m in raw_module.split(",") if m.strip()]
        if raw_module
        else None
    )

    workshop_id = request.args.get("workshop_id", type=int)

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    try:
        if fmt == "excel":
            content = generate_fitgap_excel(
                project_id=project_id,
                tenant_id=tenant_id,
                include_wricef=include_wricef,
                include_config=include_config,
                classification_filter=classification_filter,
                sap_module_filter=sap_module_filter,
                workshop_id=workshop_id,
            )
            filename = f"FitGap_Project{project_id}_{date_str}.xlsx"
            return Response(
                content,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        else:  # csv
            content = generate_requirement_csv(
                project_id=project_id,
                tenant_id=tenant_id,
                workshop_id=workshop_id,
                classification_filter=classification_filter,
            )
            filename = f"Requirements_Project{project_id}_{date_str}.csv"
            return Response(
                content,
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

    except Exception:
        logger.exception(
            "Export failed for project %s format=%s tenant=%s",
            project_id,
            fmt,
            tenant_id,
        )
        return jsonify({"error": "Export failed. Please try again."}), 500
