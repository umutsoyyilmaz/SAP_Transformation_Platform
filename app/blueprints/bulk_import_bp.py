"""
Bulk Import Blueprint — Sprint 8, Item 3.6

CSV-based bulk user import endpoints.

Endpoints:
  GET  /api/v1/admin/users/import/template   — Download CSV template
  POST /api/v1/admin/users/import/validate    — Validate CSV without importing
  POST /api/v1/admin/users/import             — Upload & import CSV
"""

import logging

from flask import Blueprint, g, jsonify, request, Response

from app.middleware.permission_required import require_permission
from app.services.bulk_import_service import (
    BulkImportError,
    generate_csv_template,
    import_users_from_csv,
    parse_csv,
    validate_import_rows,
)

logger = logging.getLogger(__name__)

bulk_import_bp = Blueprint("bulk_import_bp", __name__, url_prefix="/api/v1/admin/users/import")


# ═══════════════════════════════════════════════════════════════
# Error Handler
# ═══════════════════════════════════════════════════════════════
@bulk_import_bp.errorhandler(BulkImportError)
def handle_bulk_import_error(e):
    return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# Template Download
# ═══════════════════════════════════════════════════════════════
@bulk_import_bp.route("/template", methods=["GET"])
@require_permission("admin.settings")
def download_template():
    """Download a CSV template for bulk user import."""
    csv_content = generate_csv_template()
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=user_import_template.csv"},
    )


# ═══════════════════════════════════════════════════════════════
# Validate (dry run)
# ═══════════════════════════════════════════════════════════════
@bulk_import_bp.route("/validate", methods=["POST"])
@require_permission("admin.settings")
def validate_csv():
    """Validate a CSV file without importing — dry run."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    file_content = _extract_file_content()
    if not file_content:
        return jsonify({"error": "CSV file is required (file upload or raw body)"}), 400

    try:
        rows = parse_csv(file_content)
        if not rows:
            return jsonify({"error": "CSV file is empty or has no data rows"}), 400

        result = validate_import_rows(tenant_id, rows)
        return jsonify({
            "total_rows": len(rows),
            "valid_count": len(result["valid"]),
            "error_count": len(result["errors"]),
            "valid_rows": result["valid"],
            "errors": result["errors"],
        }), 200

    except BulkImportError as e:
        return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# Import
# ═══════════════════════════════════════════════════════════════
@bulk_import_bp.route("", methods=["POST"])
@require_permission("admin.settings")
def import_csv():
    """Upload and import a CSV file of users."""
    tenant_id = getattr(g, "jwt_tenant_id", None)
    if not tenant_id:
        return jsonify({"error": "Tenant context required"}), 400

    file_content = _extract_file_content()
    if not file_content:
        return jsonify({"error": "CSV file is required (file upload or raw body)"}), 400

    try:
        result = import_users_from_csv(tenant_id, file_content)
        status_code = 200 if result["status"] == "completed" else 207
        if result["status"] == "error":
            status_code = 400
        return jsonify(result), status_code

    except BulkImportError as e:
        return jsonify({"error": e.message}), e.status_code


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def _extract_file_content() -> str | None:
    """Extract CSV file content from multipart upload or raw body."""
    # Multipart file upload
    if request.files:
        file = request.files.get("file")
        if file:
            return file.read().decode("utf-8-sig")

    # JSON body with csv_content field
    data = request.get_json(silent=True)
    if data and "csv_content" in data:
        return data["csv_content"]

    # Raw body
    if request.data:
        return request.data.decode("utf-8-sig")

    return None
