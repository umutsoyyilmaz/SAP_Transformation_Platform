from __future__ import annotations

import sqlalchemy as sa


def _fk(model_cls, column_name: str):
    col = getattr(model_cls, column_name).property.columns[0]
    return next(iter(col.foreign_keys))


def _index_map(model_cls) -> dict[str, list[str]]:
    return {
        idx.name: [col.name for col in idx.columns]
        for idx in model_cls.__table__.indexes
    }


def _unique_map(model_cls) -> dict[str, list[str]]:
    uniques = {}
    for constraint in model_cls.__table__.constraints:
        if isinstance(constraint, sa.UniqueConstraint) and constraint.name:
            uniques[constraint.name] = [col.name for col in constraint.columns]
    return uniques


def test_process_level_is_project_owned(app):
    from app.models.explore.process import ProcessLevel

    with app.app_context():
        col = ProcessLevel.project_id.property.columns[0]
        fk = _fk(ProcessLevel, "project_id")
        assert col.nullable is False
        assert fk.target_fullname == "projects.id"
        assert fk.ondelete == "RESTRICT"
        assert _unique_map(ProcessLevel)["uq_pl_project_code"] == ["project_id", "code"]
        indexes = _index_map(ProcessLevel)
        assert indexes["idx_pl_project_parent"] == ["project_id", "parent_id"]
        assert indexes["idx_pl_project_level"] == ["project_id", "level"]
        assert indexes["idx_pl_project_scope_item"] == ["project_id", "scope_item_code"]


def test_process_step_is_project_owned(app):
    from app.models.explore.process import ProcessStep

    with app.app_context():
        col = ProcessStep.project_id.property.columns[0]
        fk = _fk(ProcessStep, "project_id")
        assert col.nullable is False
        assert fk.target_fullname == "projects.id"
        assert fk.ondelete == "RESTRICT"


def test_explore_workshop_is_project_owned(app):
    from app.models.explore.workshop import ExploreWorkshop

    with app.app_context():
        col = ExploreWorkshop.project_id.property.columns[0]
        fk = _fk(ExploreWorkshop, "project_id")
        assert col.nullable is False
        assert fk.target_fullname == "projects.id"
        assert fk.ondelete == "RESTRICT"
        assert _unique_map(ExploreWorkshop)["uq_ews_project_code"] == ["project_id", "code"]
        indexes = _index_map(ExploreWorkshop)
        assert indexes["idx_ews_project_status"] == ["project_id", "status"]
        assert indexes["idx_ews_project_date"] == ["project_id", "date"]
        assert indexes["idx_ews_project_area"] == ["project_id", "process_area"]


def test_workshop_scope_item_is_project_owned(app):
    from app.models.explore.workshop import WorkshopScopeItem

    with app.app_context():
        col = WorkshopScopeItem.project_id.property.columns[0]
        fk = _fk(WorkshopScopeItem, "project_id")
        assert col.nullable is False
        assert fk.target_fullname == "projects.id"
        assert fk.ondelete == "RESTRICT"
