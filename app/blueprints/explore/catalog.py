"""Process Catalog routes for the Explore blueprint.

Provides three endpoints:
  GET  /api/v1/explore/catalog/modules
       Returns L1 module groups with L2 sub-modules and L4 step counts.
       Used by the Quick Start wizard to render the module selection screen.

  GET  /api/v1/explore/catalog/tree?module=FI
       Returns the full L1→L2→L3→L4 catalog tree, optionally filtered
       by SAP module code (e.g. ?module=FI).

  POST /api/v1/explore/projects/<project_id>/seed-from-catalog
       Seeds a project's ProcessLevel hierarchy from selected catalog modules.
       Body: {"tenant_id": 1, "modules": ["FI", "MM"]}
       Returns created/skipped counts and elapsed time.

FDD Reference: FDD-I07-sap-1yg-seed-catalog.md §6
"""

import logging

from flask import jsonify, request

from app.blueprints.explore import explore_bp
from app.services import process_catalog_service

logger = logging.getLogger(__name__)


@explore_bp.route("/catalog/modules", methods=["GET"])
def list_catalog_modules():
    """Return available SAP modules with L4 step counts.

    Used by the Quick Start wizard module-selection step.

    Returns:
        200 — List of L1 groups with nested L2 modules and step_count.
        500 — If catalog has not been loaded yet.
    """
    modules = process_catalog_service.get_catalog_modules()
    return jsonify(modules), 200


@explore_bp.route("/catalog/tree", methods=["GET"])
def get_catalog_tree():
    """Return the full catalog tree, optionally filtered by SAP module.

    Query params:
        module (optional): SAP module code, e.g. "FI" or "MM".

    Returns:
        200 — Nested L1→L2→L3→L4 tree.
    """
    sap_module = request.args.get("module") or None
    tree = process_catalog_service.get_catalog_tree(sap_module=sap_module)
    return jsonify(tree), 200


@explore_bp.route("/projects/<int:project_id>/seed-from-catalog", methods=["POST"])
def seed_project_from_catalog(project_id: int):
    """Seed a project's process hierarchy from selected SAP catalog modules.

    Body (JSON):
        tenant_id (int, required): Owning tenant for the project.
        modules   (list[str], required): SAP module codes, e.g. ["FI", "MM"].

    Returns:
        200 — {"created": {...}, "skipped": {...}, "elapsed_ms": N}
        400 — Missing or invalid body fields.
        500 — Unexpected error.
    """
    data = request.get_json(silent=True) or {}

    tenant_id = data.get("tenant_id")
    modules = data.get("modules")

    errors: dict[str, str] = {}
    if not tenant_id or not isinstance(tenant_id, int):
        errors["tenant_id"] = "tenant_id is required and must be an integer."
    if not modules or not isinstance(modules, list) or len(modules) == 0:
        errors["modules"] = "modules is required and must be a non-empty list of SAP module codes."

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    # Sanitize: strip whitespace, uppercase
    clean_modules = [str(m).strip().upper() for m in modules if str(m).strip()]
    if not clean_modules:
        return jsonify({"error": "Validation failed", "details": {"modules": "All module values were blank."}}), 400

    # Infer importer_id from query string (passed by JS layer) or default 0
    importer_id = request.args.get("user_id", 0, type=int)

    try:
        result = process_catalog_service.seed_project_from_catalog(
            tenant_id=tenant_id,
            project_id=project_id,
            selected_modules=clean_modules,
            importer_id=importer_id,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    logger.info(
        "Catalog seed completed for project %s modules=%s created=%s",
        project_id,
        clean_modules,
        result["created"],
    )
    return jsonify(result), 200
