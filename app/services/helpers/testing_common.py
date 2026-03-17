"""Shared helper utilities for the testing domain services."""

from __future__ import annotations

from datetime import datetime


_DEFAULT_QUERY_LIMIT = 200
_MAX_QUERY_LIMIT = 1000


def testing_scope_tuple(entity) -> tuple[int | None, int | None]:
    """Return comparable `(program_id, project_id)` scope tuple."""
    class_name = entity.__class__.__name__
    if class_name == "TestCycle":
        plan = getattr(entity, "plan", None)
        return getattr(plan, "program_id", None), getattr(plan, "project_id", None)
    if class_name in {"TestExecution", "TestRun"}:
        cycle = getattr(entity, "cycle", None)
        plan = getattr(cycle, "plan", None)
        return getattr(plan, "program_id", None), getattr(plan, "project_id", None)
    return getattr(entity, "program_id", None), getattr(entity, "project_id", None)


def ensure_same_testing_scope(left, right, *, object_label: str) -> None:
    """Raise a stable validation error when two entities do not share scope."""
    left_program_id, left_project_id = testing_scope_tuple(left)
    right_program_id, right_project_id = testing_scope_tuple(right)

    if (
        left_program_id is not None and right_program_id is not None
        and left_program_id != right_program_id
    ):
        raise ValueError(f"{object_label} is outside the requested program scope")

    if (
        left_project_id is not None and right_project_id is not None
        and left_project_id != right_project_id
    ):
        raise ValueError(f"{object_label} is outside the active project scope")


def parse_iso_datetime(value):
    """Best-effort ISO datetime parsing for testing mutations."""
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def parse_optional_int(value, *, field_name: str) -> int | None:
    """Return optional integer or raise a stable validation error."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def paginate_query(
    query,
    *,
    limit=None,
    offset=None,
    default_limit: int = _DEFAULT_QUERY_LIMIT,
    max_limit: int = _MAX_QUERY_LIMIT,
):
    """Apply offset pagination without depending on Flask request globals."""
    total = query.count()
    try:
        limit = min(int(limit if limit is not None else default_limit), max_limit)
    except (TypeError, ValueError):
        limit = default_limit
    try:
        offset = max(int(offset if offset is not None else 0), 0)
    except (TypeError, ValueError):
        offset = 0
    items = query.limit(limit).offset(offset).all()
    return items, total


def auto_code(model, prefix: str, program_id: int) -> str:
    """Generate the next sequential code for a model within a program."""
    full_prefix = f"{prefix}-"
    last = (
        model.query
        .filter(model.program_id == program_id, model.code.like(f"{full_prefix}%"))
        .order_by(model.id.desc())
        .first()
    )
    if last and last.code.startswith(full_prefix):
        try:
            next_num = int(last.code[len(full_prefix):]) + 1
        except (ValueError, IndexError):
            next_num = model.query.filter_by(program_id=program_id).count() + 1
    else:
        next_num = model.query.filter_by(program_id=program_id).count() + 1
    return f"{full_prefix}{next_num:04d}"
