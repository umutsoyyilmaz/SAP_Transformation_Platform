from sqlalchemy import inspect as sa_inspect

from app.models import db as _db


TABLES = [
    "process_steps",
    "workshop_scope_items",
    "workshop_attendees",
    "workshop_agenda_items",
    "requirement_open_item_links",
    "requirement_dependencies",
    "open_item_comments",
]


def test_phase1_scope_columns_exist(app):
    insp = sa_inspect(_db.engine)

    missing = []
    for table_name in TABLES:
        cols = {c["name"] for c in insp.get_columns(table_name)}
        for required in ("tenant_id", "program_id", "project_id"):
            if required not in cols:
                missing.append(f"{table_name}.{required}")

    assert missing == [], f"Missing scope columns: {missing}"


def test_phase1_composite_scope_indexes_exist(app):
    insp = sa_inspect(_db.engine)

    missing = []
    for table_name in TABLES:
        indexes = insp.get_indexes(table_name)
        has_composite = any(
            idx.get("column_names") == ["tenant_id", "program_id", "project_id"]
            for idx in indexes
        )
        if not has_composite:
            missing.append(table_name)

    assert missing == [], f"Missing composite scope indexes: {missing}"
