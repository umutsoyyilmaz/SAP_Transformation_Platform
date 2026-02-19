"""
FAZ 9 — Custom Fields & Layout Engine service layer.

Centralises all ORM queries and mutations for CustomFieldDefinition,
CustomFieldValue and LayoutConfig so that blueprints remain HTTP-only.
Every db.session.commit() in this module is intentional and constitutes
the single source of truth for transaction ownership.
"""

import logging

from app.models import db
from app.models.custom_fields import (
    CustomFieldDefinition,
    CustomFieldValue,
    LayoutConfig,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Typed exceptions
# ──────────────────────────────────────────────────────────────────────────────

class CustomFieldNotFoundError(Exception):
    """Raised when a requested custom-field resource does not exist."""


class CustomFieldConflictError(Exception):
    """Raised when a duplicate field name is detected within the same program/entity."""


class LayoutNotFoundError(Exception):
    """Raised when a requested layout resource does not exist."""


# ──────────────────────────────────────────────────────────────────────────────
# Custom Field Definitions
# ──────────────────────────────────────────────────────────────────────────────

def list_field_definitions(
    program_id: int,
    entity_type: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return paginated field definitions for a program, optionally filtered by entity type.

    Args:
        program_id: PK of the owning Program.
        entity_type: Optional entity-type filter (e.g. "test_case").
        limit: Maximum number of records to return.
        offset: Number of records to skip.

    Returns:
        Tuple of (list of to_dict results, total count).
    """
    q = CustomFieldDefinition.query.filter_by(program_id=program_id)
    if entity_type:
        q = q.filter_by(entity_type=entity_type)
    q = q.order_by(
        CustomFieldDefinition.entity_type,
        CustomFieldDefinition.sort_order,
    )
    total: int = q.count()
    items = q.limit(limit).offset(offset).all()
    return [f.to_dict() for f in items], total


def create_field_definition(program_id: int, tenant_id: int | None, data: dict) -> dict:
    """Persist a new custom field definition, enforcing uniqueness within program+entity_type.

    Args:
        program_id: PK of the owning Program.
        tenant_id: Tenant PK inherited from the Program record.
        data: Validated input dict from blueprint.

    Returns:
        Serialized field definition dict.

    Raises:
        CustomFieldConflictError: If field_name already exists for program+entity_type.
    """
    entity_type: str = data.get("entity_type", "test_case")
    field_name: str = data["field_name"]

    duplicate = CustomFieldDefinition.query.filter_by(
        program_id=program_id,
        entity_type=entity_type,
        field_name=field_name,
    ).first()
    if duplicate:
        raise CustomFieldConflictError(
            f"Field '{field_name}' already exists for {entity_type}"
        )

    field = CustomFieldDefinition(
        program_id=program_id,
        tenant_id=tenant_id,
        entity_type=entity_type,
        field_name=field_name,
        field_label=data.get("field_label", field_name),
        field_type=data.get("field_type", "text"),
        options=data.get("options", []),
        is_required=data.get("is_required", False),
        is_filterable=data.get("is_filterable", True),
        sort_order=data.get("sort_order", 0),
        default_value=data.get("default_value", ""),
        description=data.get("description", ""),
    )
    db.session.add(field)
    db.session.commit()
    logger.info("CustomFieldDefinition created id=%s program=%s", field.id, program_id)
    return field.to_dict()


def get_field_definition(fid: int) -> dict:
    """Fetch a single field definition by PK.

    Args:
        fid: Primary key of the CustomFieldDefinition.

    Returns:
        Serialized field definition dict.

    Raises:
        CustomFieldNotFoundError: If no record with that PK exists.
    """
    field = db.session.get(CustomFieldDefinition, fid)
    if not field:
        raise CustomFieldNotFoundError(f"CustomFieldDefinition {fid} not found")
    return field.to_dict()


def update_field_definition(fid: int, data: dict) -> dict:
    """Apply a partial update to a field definition.

    Args:
        fid: Primary key of the CustomFieldDefinition to update.
        data: Fields to update (any subset of the mutable attributes).

    Returns:
        Updated serialized dict.

    Raises:
        CustomFieldNotFoundError: If record does not exist.
    """
    field = db.session.get(CustomFieldDefinition, fid)
    if not field:
        raise CustomFieldNotFoundError(f"CustomFieldDefinition {fid} not found")

    mutable_attrs = (
        "field_name", "field_label", "field_type", "options",
        "is_required", "is_filterable", "sort_order",
        "default_value", "description", "entity_type",
    )
    for attr in mutable_attrs:
        if attr in data:
            setattr(field, attr, data[attr])

    db.session.commit()
    logger.info("CustomFieldDefinition updated id=%s", fid)
    return field.to_dict()


def delete_field_definition(fid: int) -> None:
    """Delete a custom field definition and rely on cascade for orphan values.

    Args:
        fid: PK of the CustomFieldDefinition to delete.

    Raises:
        CustomFieldNotFoundError: If record does not exist.
    """
    field = db.session.get(CustomFieldDefinition, fid)
    if not field:
        raise CustomFieldNotFoundError(f"CustomFieldDefinition {fid} not found")
    db.session.delete(field)
    db.session.commit()
    logger.info("CustomFieldDefinition deleted id=%s", fid)


# ──────────────────────────────────────────────────────────────────────────────
# Custom Field Values
# ──────────────────────────────────────────────────────────────────────────────

def get_entity_field_values(entity_type: str, entity_id: int) -> list[dict]:
    """Return all custom field values stored for a given entity instance.

    Args:
        entity_type: E.g. "test_case", "requirement".
        entity_id: PK of the entity instance.

    Returns:
        List of serialized CustomFieldValue dicts.
    """
    values = (
        CustomFieldValue.query
        .filter_by(entity_type=entity_type, entity_id=entity_id)
        .all()
    )
    return [v.to_dict() for v in values]


def set_entity_field_values(
    entity_type: str,
    entity_id: int,
    field_values: dict,
) -> list[dict]:
    """Upsert a batch of field values for an entity.

    Iterates over the provided mapping of field_id → value, creating new
    CustomFieldValue rows or updating existing ones, then commits once.

    Args:
        entity_type: Entity type string.
        entity_id: PK of the entity.
        field_values: Mapping of field_id (as int or str) → scalar value.

    Returns:
        List of serialized dicts for all upserted rows.

    Raises:
        CustomFieldNotFoundError: If any field_id does not exist.
    """
    results = []
    for field_id_raw, val in field_values.items():
        field_id = int(field_id_raw)
        field_def = db.session.get(CustomFieldDefinition, field_id)
        if not field_def:
            raise CustomFieldNotFoundError(f"CustomFieldDefinition {field_id} not found")

        existing = CustomFieldValue.query.filter_by(
            field_id=field_id,
            entity_type=entity_type,
            entity_id=entity_id,
        ).first()

        if existing:
            existing.value = str(val)
            results.append(existing)
        else:
            cfv = CustomFieldValue(
                field_id=field_id,
                tenant_id=field_def.tenant_id,
                entity_type=entity_type,
                entity_id=entity_id,
                value=str(val),
            )
            db.session.add(cfv)
            results.append(cfv)

    db.session.commit()
    logger.info(
        "CustomFieldValues upserted entity_type=%s entity_id=%s count=%s",
        entity_type,
        entity_id,
        len(results),
    )
    return [r.to_dict() for r in results]


def update_field_value(vid: int, value_str: str) -> dict:
    """Update the scalar value of a single CustomFieldValue row.

    Args:
        vid: PK of the CustomFieldValue.
        value_str: New string value to store.

    Returns:
        Updated serialized dict.

    Raises:
        CustomFieldNotFoundError: If record does not exist.
    """
    val = db.session.get(CustomFieldValue, vid)
    if not val:
        raise CustomFieldNotFoundError(f"CustomFieldValue {vid} not found")
    val.value = value_str
    db.session.commit()
    return val.to_dict()


def delete_field_value(vid: int) -> None:
    """Delete a single CustomFieldValue row.

    Args:
        vid: PK of the CustomFieldValue.

    Raises:
        CustomFieldNotFoundError: If record does not exist.
    """
    val = db.session.get(CustomFieldValue, vid)
    if not val:
        raise CustomFieldNotFoundError(f"CustomFieldValue {vid} not found")
    db.session.delete(val)
    db.session.commit()
    logger.info("CustomFieldValue deleted id=%s", vid)


def list_field_values(fid: int) -> list[dict]:
    """Return all values stored for a given field definition, ordered by entity_id.

    Args:
        fid: PK of the CustomFieldDefinition whose values to list.

    Returns:
        List of serialized CustomFieldValue dicts.

    Raises:
        CustomFieldNotFoundError: If the field definition does not exist.
    """
    field = db.session.get(CustomFieldDefinition, fid)
    if not field:
        raise CustomFieldNotFoundError(f"CustomFieldDefinition {fid} not found")

    values = (
        CustomFieldValue.query
        .filter_by(field_id=fid)
        .order_by(CustomFieldValue.entity_id)
        .all()
    )
    return [v.to_dict() for v in values]


# ──────────────────────────────────────────────────────────────────────────────
# Layout Configs
# ──────────────────────────────────────────────────────────────────────────────

def list_layouts(
    program_id: int,
    entity_type: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return paginated LayoutConfig records for a program.

    Args:
        program_id: Owning Program PK.
        entity_type: Optional entity-type filter.
        limit: Maximum number of records to return.
        offset: Number of records to skip.

    Returns:
        Tuple of (list of to_dict results, total count).
    """
    q = LayoutConfig.query.filter_by(program_id=program_id)
    if entity_type:
        q = q.filter_by(entity_type=entity_type)
    q = q.order_by(LayoutConfig.is_default.desc(), LayoutConfig.name)
    total: int = q.count()
    items = q.limit(limit).offset(offset).all()
    return [lc.to_dict() for lc in items], total


def create_layout(program_id: int, tenant_id: int | None, data: dict) -> dict:
    """Create a new LayoutConfig for the given program.

    Args:
        program_id: Owning Program PK.
        tenant_id: Tenant PK inherited from the Program row.
        data: Validated input dict from blueprint.

    Returns:
        Serialized LayoutConfig dict.
    """
    layout = LayoutConfig(
        program_id=program_id,
        tenant_id=tenant_id,
        entity_type=data.get("entity_type", "test_case"),
        name=data["name"],
        is_default=data.get("is_default", False),
        sections=data.get("sections", []),
        created_by=data.get("created_by", "system"),
    )
    db.session.add(layout)
    db.session.commit()
    logger.info("LayoutConfig created id=%s program=%s", layout.id, program_id)
    return layout.to_dict()


def get_layout(lid: int) -> dict:
    """Fetch a single LayoutConfig by PK.

    Args:
        lid: Primary key of the LayoutConfig.

    Returns:
        Serialized dict.

    Raises:
        LayoutNotFoundError: If no record with that PK exists.
    """
    layout = db.session.get(LayoutConfig, lid)
    if not layout:
        raise LayoutNotFoundError(f"LayoutConfig {lid} not found")
    return layout.to_dict()


def update_layout(lid: int, data: dict) -> dict:
    """Apply a partial update to a LayoutConfig.

    Args:
        lid: PK of the LayoutConfig to update.
        data: Fields to update.

    Returns:
        Updated serialized dict.

    Raises:
        LayoutNotFoundError: If record does not exist.
    """
    layout = db.session.get(LayoutConfig, lid)
    if not layout:
        raise LayoutNotFoundError(f"LayoutConfig {lid} not found")

    for attr in ("name", "entity_type", "sections", "is_default"):
        if attr in data:
            setattr(layout, attr, data[attr])

    db.session.commit()
    logger.info("LayoutConfig updated id=%s", lid)
    return layout.to_dict()


def delete_layout(lid: int) -> None:
    """Delete a LayoutConfig record.

    Args:
        lid: PK of the LayoutConfig to delete.

    Raises:
        LayoutNotFoundError: If record does not exist.
    """
    layout = db.session.get(LayoutConfig, lid)
    if not layout:
        raise LayoutNotFoundError(f"LayoutConfig {lid} not found")
    db.session.delete(layout)
    db.session.commit()
    logger.info("LayoutConfig deleted id=%s", lid)


def set_default_layout(lid: int) -> dict:
    """Mark one layout as default and unmark sibling layouts for the same program+entity_type.

    Uses a single query to locate siblings, keeping the transaction tight and
    avoiding an N+1 update loop.

    Args:
        lid: PK of the LayoutConfig to promote as default.

    Returns:
        Serialized dict of the newly-defaulted layout.

    Raises:
        LayoutNotFoundError: If the layout does not exist.
    """
    layout = db.session.get(LayoutConfig, lid)
    if not layout:
        raise LayoutNotFoundError(f"LayoutConfig {lid} not found")

    # Clear existing defaults among siblings (same program + entity_type, different id)
    siblings = (
        LayoutConfig.query
        .filter_by(
            program_id=layout.program_id,
            entity_type=layout.entity_type,
        )
        .filter(LayoutConfig.id != lid, LayoutConfig.is_default.is_(True))
        .all()
    )
    for sib in siblings:
        sib.is_default = False

    layout.is_default = True
    db.session.commit()
    logger.info("LayoutConfig set as default id=%s program=%s", lid, layout.program_id)
    return layout.to_dict()
