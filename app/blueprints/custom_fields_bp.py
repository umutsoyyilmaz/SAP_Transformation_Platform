"""
FAZ 9 — Custom Fields & Layout Engine

Blueprint: custom_fields_bp
Prefix: /api/v1

Endpoints:
  Custom Field Definitions:
    GET/POST  /programs/<pid>/custom-fields             -- List/create definitions
    GET/PUT/DELETE /custom-fields/<fid>                  -- Single definition CRUD

  Custom Field Values:
    GET/POST   /custom-fields/values/<entity_type>/<eid> -- Get/set values for entity
    PUT/DELETE /custom-field-values/<vid>                -- Update/delete single value
    GET        /custom-fields/<fid>/values               -- All values for a field def

  Layout Configs:
    GET/POST   /programs/<pid>/layouts                   -- List/create layouts
    GET/PUT/DELETE /layouts/<lid>                        -- Single layout CRUD
    POST       /layouts/<lid>/set-default                -- Mark as default layout
"""

import logging

from flask import Blueprint, jsonify, request

from app.models.program import Program
from app.utils.helpers import get_or_404 as _get_or_404
from app.services.custom_fields_service import (
    CustomFieldConflictError,
    CustomFieldNotFoundError,
    LayoutNotFoundError,
    create_field_definition,
    create_layout,
    delete_field_definition,
    delete_field_value,
    delete_layout,
    get_entity_field_values,
    get_field_definition,
    get_layout,
    list_field_definitions,
    list_field_values,
    list_layouts,
    set_default_layout,
    set_entity_field_values,
    update_field_definition,
    update_field_value,
    update_layout,
)

logger = logging.getLogger(__name__)

custom_fields_bp = Blueprint(
    "custom_fields", __name__, url_prefix="/api/v1"
)


def _actor() -> str:
    """Extract actor identifier from request headers for audit purposes."""
    return request.headers.get("X-User", "system")


def _pagination_args(default_limit: int = 200) -> tuple[int, int]:
    """Parse limit/offset pagination query parameters from the current request.

    Args:
        default_limit: Fallback limit when not supplied by caller.

    Returns:
        Tuple of (limit, offset).
    """
    try:
        limit = min(int(request.args.get("limit", default_limit)), 1000)
    except (ValueError, TypeError):
        limit = default_limit
    try:
        offset = max(int(request.args.get("offset", 0)), 0)
    except (ValueError, TypeError):
        offset = 0
    return limit, offset


# ------------------------------------------------------------------
#  9.1  Custom Field Definitions
# ------------------------------------------------------------------

@custom_fields_bp.route("/programs/<int:pid>/custom-fields", methods=["GET"])
def list_field_definitions_route(pid):
    """List custom field definitions for a program, with optional entity_type filter."""
    prog, err = _get_or_404(Program, pid)
    if err:
        return err

    entity_type = request.args.get("entity_type", "") or None
    limit, offset = _pagination_args()
    try:
        fields, total = list_field_definitions(
            program_id=pid, entity_type=entity_type, limit=limit, offset=offset
        )
    except Exception:
        logger.exception("Unexpected error in list_field_definitions program=%s", pid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"fields": fields, "total": total}), 200


@custom_fields_bp.route("/programs/<int:pid>/custom-fields", methods=["POST"])
def create_field_definition_route(pid):
    """Create a new custom field definition for a program."""
    prog, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    field_name = data.get("field_name", "")
    if not field_name or len(field_name) > 255:
        return jsonify({"error": "field_name is required and must be <= 255 chars"}), 400

    try:
        field = create_field_definition(
            program_id=pid,
            tenant_id=getattr(prog, "tenant_id", None),
            data=data,
        )
    except CustomFieldConflictError as exc:
        return jsonify({"error": str(exc)}), 409
    except Exception:
        logger.exception("Unexpected error in create_field_definition program=%s", pid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"field": field}), 201


@custom_fields_bp.route("/custom-fields/<int:fid>", methods=["GET"])
def get_field_definition_route(fid):
    """Fetch a single custom field definition by id."""
    try:
        field = get_field_definition(fid)
    except CustomFieldNotFoundError:
        return jsonify({"error": "CustomFieldDefinition not found"}), 404
    except Exception:
        logger.exception("Unexpected error in get_field_definition fid=%s", fid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"field": field}), 200


@custom_fields_bp.route("/custom-fields/<int:fid>", methods=["PUT"])
def update_field_definition_route(fid):
    """Apply a partial update to a custom field definition."""
    data = request.get_json(silent=True) or {}
    try:
        field = update_field_definition(fid, data)
    except CustomFieldNotFoundError:
        return jsonify({"error": "CustomFieldDefinition not found"}), 404
    except Exception:
        logger.exception("Unexpected error in update_field_definition fid=%s", fid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"field": field}), 200


@custom_fields_bp.route("/custom-fields/<int:fid>", methods=["DELETE"])
def delete_field_definition_route(fid):
    """Delete a custom field definition."""
    try:
        delete_field_definition(fid)
    except CustomFieldNotFoundError:
        return jsonify({"error": "CustomFieldDefinition not found"}), 404
    except Exception:
        logger.exception("Unexpected error in delete_field_definition fid=%s", fid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"deleted": True}), 200


# ------------------------------------------------------------------
#  9.1b  Custom Field Values
# ------------------------------------------------------------------

@custom_fields_bp.route(
    "/custom-fields/values/<entity_type>/<int:eid>", methods=["GET"]
)
def get_entity_field_values_route(entity_type, eid):
    """Get all custom field values for a specific entity."""
    try:
        values = get_entity_field_values(entity_type, eid)
    except Exception:
        logger.exception(
            "Unexpected error in get_entity_field_values type=%s id=%s", entity_type, eid
        )
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"values": values, "entity_type": entity_type, "entity_id": eid}), 200


@custom_fields_bp.route(
    "/custom-fields/values/<entity_type>/<int:eid>", methods=["POST"]
)
def set_entity_field_values_route(entity_type, eid):
    """Set/update custom field values for an entity. Accepts {values: {field_id: value}}"""
    data = request.get_json(silent=True) or {}
    field_values = data.get("values", {})
    if not field_values:
        return jsonify({"error": "values dict is required"}), 400

    try:
        results = set_entity_field_values(entity_type, eid, field_values)
    except CustomFieldNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        logger.exception(
            "Unexpected error in set_entity_field_values type=%s id=%s", entity_type, eid
        )
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"values": results}), 200


@custom_fields_bp.route("/custom-field-values/<int:vid>", methods=["PUT"])
def update_field_value_route(vid):
    """Update the scalar value of a single custom field value row."""
    data = request.get_json(silent=True) or {}
    if "value" not in data:
        return jsonify({"error": "value is required"}), 400

    try:
        result = update_field_value(vid, str(data["value"]))
    except CustomFieldNotFoundError:
        return jsonify({"error": "CustomFieldValue not found"}), 404
    except Exception:
        logger.exception("Unexpected error in update_field_value vid=%s", vid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"value": result}), 200


@custom_fields_bp.route("/custom-field-values/<int:vid>", methods=["DELETE"])
def delete_field_value_route(vid):
    """Delete a single custom field value row."""
    try:
        delete_field_value(vid)
    except CustomFieldNotFoundError:
        return jsonify({"error": "CustomFieldValue not found"}), 404
    except Exception:
        logger.exception("Unexpected error in delete_field_value vid=%s", vid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"deleted": True}), 200


@custom_fields_bp.route("/custom-fields/<int:fid>/values", methods=["GET"])
def list_field_values_route(fid):
    """List all values stored for a specific field definition."""
    try:
        values = list_field_values(fid)
    except CustomFieldNotFoundError:
        return jsonify({"error": "CustomFieldDefinition not found"}), 404
    except Exception:
        logger.exception("Unexpected error in list_field_values fid=%s", fid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"values": values}), 200


# ------------------------------------------------------------------
#  9.2  Layout Configs
# ------------------------------------------------------------------

@custom_fields_bp.route("/programs/<int:pid>/layouts", methods=["GET"])
def list_layouts_route(pid):
    """List layout configs for a program, with optional entity_type filter."""
    prog, err = _get_or_404(Program, pid)
    if err:
        return err

    entity_type = request.args.get("entity_type", "") or None
    limit, offset = _pagination_args()
    try:
        layouts, total = list_layouts(
            program_id=pid, entity_type=entity_type, limit=limit, offset=offset
        )
    except Exception:
        logger.exception("Unexpected error in list_layouts program=%s", pid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"layouts": layouts, "total": total}), 200


@custom_fields_bp.route("/programs/<int:pid>/layouts", methods=["POST"])
def create_layout_route(pid):
    """Create a new layout config for a program."""
    prog, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    name = data.get("name", "")
    if not name or len(name) > 255:
        return jsonify({"error": "name is required and must be <= 255 chars"}), 400

    data.setdefault("created_by", _actor())
    try:
        layout = create_layout(
            program_id=pid,
            tenant_id=getattr(prog, "tenant_id", None),
            data=data,
        )
    except Exception:
        logger.exception("Unexpected error in create_layout program=%s", pid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"layout": layout}), 201


@custom_fields_bp.route("/layouts/<int:lid>", methods=["GET"])
def get_layout_route(lid):
    """Fetch a single layout config by id."""
    try:
        layout = get_layout(lid)
    except LayoutNotFoundError:
        return jsonify({"error": "LayoutConfig not found"}), 404
    except Exception:
        logger.exception("Unexpected error in get_layout lid=%s", lid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"layout": layout}), 200


@custom_fields_bp.route("/layouts/<int:lid>", methods=["PUT"])
def update_layout_route(lid):
    """Apply a partial update to a layout config."""
    data = request.get_json(silent=True) or {}
    try:
        layout = update_layout(lid, data)
    except LayoutNotFoundError:
        return jsonify({"error": "LayoutConfig not found"}), 404
    except Exception:
        logger.exception("Unexpected error in update_layout lid=%s", lid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"layout": layout}), 200


@custom_fields_bp.route("/layouts/<int:lid>", methods=["DELETE"])
def delete_layout_route(lid):
    """Delete a layout config."""
    try:
        delete_layout(lid)
    except LayoutNotFoundError:
        return jsonify({"error": "LayoutConfig not found"}), 404
    except Exception:
        logger.exception("Unexpected error in delete_layout lid=%s", lid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"deleted": True}), 200


@custom_fields_bp.route("/layouts/<int:lid>/set-default", methods=["POST"])
def set_default_layout_route(lid):
    """Mark this layout as default; unmark all sibling layouts for the same program+entity_type."""
    try:
        layout = set_default_layout(lid)
    except LayoutNotFoundError:
        return jsonify({"error": "LayoutConfig not found"}), 404
    except Exception:
        logger.exception("Unexpected error in set_default_layout lid=%s", lid)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({"layout": layout}), 200
