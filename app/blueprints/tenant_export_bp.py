"""
Tenant Data Export Blueprint — Sprint 10 (Item 4.6)

KVKK/GDPR compliant data export endpoints.
  GET /json/<tenant_id>  → full JSON export
  GET /csv/<tenant_id>   → CSV export (zip)
"""

import json
from flask import Blueprint, jsonify, Response

from app.services import tenant_export_service as svc

tenant_export_bp = Blueprint("tenant_export", __name__, url_prefix="/api/v1/admin/export")


@tenant_export_bp.route("/json/<int:tenant_id>", methods=["GET"])
def export_json(tenant_id):
    """Download full tenant data as JSON."""
    data, err = svc.export_tenant_data_json(tenant_id)
    if err:
        return jsonify({"error": err}), 404
    return Response(
        json.dumps(data, indent=2, ensure_ascii=False),
        mimetype="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=tenant_{tenant_id}_export.json"
        },
    )


@tenant_export_bp.route("/csv/<int:tenant_id>", methods=["GET"])
def export_csv(tenant_id):
    """Download tenant data as CSV files (returned as JSON with CSV strings)."""
    data, err = svc.export_tenant_data_csv(tenant_id)
    if err:
        return jsonify({"error": err}), 404
    # Return CSV map as JSON (frontend can process each entity)
    return jsonify(data), 200


@tenant_export_bp.route("/summary/<int:tenant_id>", methods=["GET"])
def export_summary(tenant_id):
    """Get a summary of what will be exported (record counts)."""
    data, err = svc.export_tenant_data_json(tenant_id)
    if err:
        return jsonify({"error": err}), 404
    summary = {
        "tenant_id": tenant_id,
        "tenant_name": data["tenant"]["name"],
        "record_counts": {
            entity: len(records) if isinstance(records, list) else 1
            for entity, records in data.items()
            if entity != "export_meta"
        },
    }
    return jsonify(summary), 200
