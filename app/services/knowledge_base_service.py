"""Knowledge Base service — FDD-I04 (S6-01).

Manages LessonLearned records across a tenant's project portfolio.

Cross-tenant visibility:
  Lessons with is_public=True are searchable by all tenants.
  When returned to an external tenant, to_dict_public() is used —
  project_id, tenant_id, author_id and linked IDs are masked.

Upvote deduplication:
  Each upvote inserts a LessonUpvote row (unique on lesson_id + user_id).
  The service rejects duplicate votes with ValidationError and keeps
  LessonLearned.upvote_count in sync as a denormalized cache.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.models import db
from app.models.run_sustain import LessonLearned, LessonUpvote

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed values — validated at service boundary, not just DB constraint
# ---------------------------------------------------------------------------

_VALID_CATEGORIES = frozenset(
    ["what_went_well", "what_went_wrong", "improve_next_time", "risk_realized", "best_practice"]
)
_VALID_IMPACTS = frozenset(["high", "medium", "low"])
_VALID_PHASES = frozenset(["discover", "prepare", "explore", "realize", "deploy", "run"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_lesson_for_tenant(tenant_id: int, lesson_id: int) -> LessonLearned:
    """Fetch a lesson owned by this tenant; raises 404-style ValueError if not found."""
    lesson = db.session.get(LessonLearned, lesson_id)
    if not lesson or lesson.tenant_id != tenant_id:
        raise ValueError(f"Lesson {lesson_id} not found")
    return lesson


def _lesson_visible_to_tenant(tenant_id: int, lesson_id: int) -> LessonLearned:
    """Fetch a lesson visible to this tenant (own OR public).

    Returns the lesson using appropriate serialization context (tracked on
    the returned object via a transient attribute _is_foreign_tenant).
    """
    lesson = db.session.get(LessonLearned, lesson_id)
    if not lesson:
        raise ValueError(f"Lesson {lesson_id} not found")
    if lesson.tenant_id != tenant_id and not lesson.is_public:
        raise ValueError(f"Lesson {lesson_id} not found")
    # Flag so callers can call the right to_dict variant
    lesson._is_foreign_tenant = lesson.tenant_id != tenant_id
    return lesson


def _serialize(lesson: LessonLearned, tenant_id: int) -> dict:
    """Use full dict for own lessons, masked dict for foreign-tenant public ones."""
    if lesson.tenant_id == tenant_id:
        return lesson.to_dict()
    return lesson.to_dict_public()


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------


def create_lesson(
    tenant_id: int,
    data: dict,
    project_id: int | None = None,
    author_id: int | None = None,
) -> dict:
    """Create a new lesson and add it to the tenant's Knowledge Base.

    Business rules:
        - title and category are required.
        - category must be one of _VALID_CATEGORIES.
        - impact, if provided, must be one of _VALID_IMPACTS.
        - sap_activate_phase, if provided, must be one of _VALID_PHASES.
        - is_public defaults to False (opt-in sharing).

    Args:
        tenant_id: Owning tenant.
        data: Lesson payload from the blueprint.
        project_id: Optional source project (passed by create-from-project routes).
        author_id: User ID of the author (from g.current_user.id in blueprint).

    Returns:
        Serialized LessonLearned dict.

    Raises:
        ValueError: If required fields are missing or enum values are invalid.
    """
    title = (data.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    if len(title) > 255:
        raise ValueError("title must be ≤ 255 characters")

    category = data.get("category", "what_went_well")
    if category not in _VALID_CATEGORIES:
        raise ValueError(f"category must be one of: {', '.join(sorted(_VALID_CATEGORIES))}")

    impact = data.get("impact")
    if impact and impact not in _VALID_IMPACTS:
        raise ValueError(f"impact must be one of: {', '.join(sorted(_VALID_IMPACTS))}")

    phase = data.get("sap_activate_phase")
    if phase and phase not in _VALID_PHASES:
        raise ValueError(f"sap_activate_phase must be one of: {', '.join(sorted(_VALID_PHASES))}")

    tags = data.get("tags", "")
    if tags and len(tags) > 500:
        tags = tags[:500]

    lesson = LessonLearned(
        tenant_id=tenant_id,
        project_id=project_id or data.get("project_id"),
        author_id=author_id or data.get("author_id"),
        title=title,
        category=category,
        description=(data.get("description") or "").strip() or None,
        recommendation=(data.get("recommendation") or "").strip() or None,
        impact=impact or None,
        sap_module=(data.get("sap_module") or "").strip()[:10] or None,
        sap_activate_phase=phase or None,
        tags=tags or None,
        linked_incident_id=data.get("linked_incident_id"),
        linked_risk_id=data.get("linked_risk_id"),
        is_public=bool(data.get("is_public", False)),
        upvote_count=0,
    )
    db.session.add(lesson)
    db.session.commit()

    logger.info(
        "LessonLearned created",
        extra={"tenant_id": tenant_id, "lesson_id": lesson.id, "category": category},
    )
    return lesson.to_dict()


def get_lesson(tenant_id: int, lesson_id: int) -> dict:
    """Fetch a single lesson — own or public.

    Returns:
        Full dict for own lessons; masked (to_dict_public) for foreign-tenant public ones.

    Raises:
        ValueError: If not found or private from another tenant.
    """
    lesson = _lesson_visible_to_tenant(tenant_id, lesson_id)
    return _serialize(lesson, tenant_id)


def update_lesson(tenant_id: int, lesson_id: int, data: dict) -> dict:
    """Update a lesson owned by this tenant.

    Only the owning tenant can edit.  is_public transitions are allowed.

    Raises:
        ValueError: If not found, or cross-tenant edit attempt.
    """
    lesson = _get_lesson_for_tenant(tenant_id, lesson_id)

    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            raise ValueError("title cannot be empty")
        if len(title) > 255:
            raise ValueError("title must be ≤ 255 characters")
        lesson.title = title

    if "category" in data:
        if data["category"] not in _VALID_CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(sorted(_VALID_CATEGORIES))}")
        lesson.category = data["category"]

    if "impact" in data:
        impact = data["impact"]
        if impact and impact not in _VALID_IMPACTS:
            raise ValueError(f"impact must be one of: {', '.join(sorted(_VALID_IMPACTS))}")
        lesson.impact = impact or None

    if "sap_activate_phase" in data:
        phase = data["sap_activate_phase"]
        if phase and phase not in _VALID_PHASES:
            raise ValueError(f"sap_activate_phase must be one of: {', '.join(sorted(_VALID_PHASES))}")
        lesson.sap_activate_phase = phase or None

    for field in ("description", "recommendation", "sap_module", "tags"):
        if field in data:
            setattr(lesson, field, (data[field] or "").strip() or None)

    if "is_public" in data:
        lesson.is_public = bool(data["is_public"])

    if "linked_incident_id" in data:
        lesson.linked_incident_id = data["linked_incident_id"]
    if "linked_risk_id" in data:
        lesson.linked_risk_id = data["linked_risk_id"]

    lesson.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    logger.info(
        "LessonLearned updated",
        extra={"tenant_id": tenant_id, "lesson_id": lesson_id},
    )
    return lesson.to_dict()


def delete_lesson(tenant_id: int, lesson_id: int) -> None:
    """Delete a lesson owned by this tenant.

    Raises:
        ValueError: If not found or belongs to another tenant.
    """
    lesson = _get_lesson_for_tenant(tenant_id, lesson_id)
    db.session.delete(lesson)
    db.session.commit()
    logger.info("LessonLearned deleted", extra={"tenant_id": tenant_id, "lesson_id": lesson_id})


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def search_lessons(
    tenant_id: int,
    query: str | None = None,
    sap_module: str | None = None,
    phase: str | None = None,
    category: str | None = None,
    include_public: bool = True,
    project_id: int | None = None,
    page: int = 1,
    per_page: int = 50,
) -> dict:
    """Full-text search over the tenant's KB plus public lessons.

    Visibility logic:
        - Own lessons (tenant_id == tenant_id): always included.
        - Cross-tenant public lessons (is_public=True): included when include_public=True.

    Text search (q):
        SQLite: LIKE-based case-insensitive match on title + description + recommendation + tags.
        PostgreSQL: same query compiles to ILIKE.

    Returns:
        Paginated result: {"items": [...], "total": N, "page": P, "per_page": PP}.
    """
    # Base visibility predicate
    if include_public:
        visibility = or_(LessonLearned.tenant_id == tenant_id, LessonLearned.is_public.is_(True))
    else:
        visibility = LessonLearned.tenant_id == tenant_id

    stmt = select(LessonLearned).where(visibility)

    # Optional filters
    if sap_module:
        stmt = stmt.where(LessonLearned.sap_module == sap_module)
    if phase:
        stmt = stmt.where(LessonLearned.sap_activate_phase == phase)
    if category:
        stmt = stmt.where(LessonLearned.category == category)
    if project_id:
        stmt = stmt.where(LessonLearned.project_id == project_id)

    # Text search — LIKE-based (SQLite + PostgreSQL compatible)
    if query and query.strip():
        q = f"%{query.strip()[:200]}%"
        stmt = stmt.where(
            or_(
                LessonLearned.title.ilike(q),
                LessonLearned.description.ilike(q),
                LessonLearned.recommendation.ilike(q),
                LessonLearned.tags.ilike(q),
            )
        )

    # Count for pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.session.execute(count_stmt).scalar_one()

    # Paginate + sort by votes desc, then newest
    offset = (page - 1) * per_page
    stmt = stmt.order_by(LessonLearned.upvote_count.desc(), LessonLearned.created_at.desc())
    stmt = stmt.offset(offset).limit(per_page)

    lessons = db.session.execute(stmt).scalars().all()

    return {
        "items": [_serialize(le, tenant_id) for le in lessons],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


# ---------------------------------------------------------------------------
# Upvote
# ---------------------------------------------------------------------------


def upvote_lesson(tenant_id: int, lesson_id: int, user_id: int) -> dict:
    """Cast an upvote for a visible lesson (own or public).

    Idempotency: duplicate votes raise ValidationError — the DB unique
    constraint (lesson_id, user_id) is the authoritative guard.

    Upvote count is kept in sync on the LessonLearned row for fast sorting.

    Raises:
        ValueError: Lesson not found or private from another tenant.
        ValueError: User already upvoted this lesson.
    """
    # Must be visible (own or public)
    lesson = _lesson_visible_to_tenant(tenant_id, lesson_id)

    try:
        vote = LessonUpvote(
            lesson_id=lesson.id,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        db.session.add(vote)
        db.session.flush()  # triggers constraint before commit
    except IntegrityError:
        db.session.rollback()
        raise ValueError("You have already upvoted this lesson")

    # Sync denormalized counter
    lesson.upvote_count = (
        db.session.execute(
            select(func.count()).where(LessonUpvote.lesson_id == lesson.id)
        ).scalar_one()
    )
    db.session.commit()

    logger.info("LessonUpvote cast", extra={"lesson_id": lesson.id, "user_id": user_id})
    return _serialize(lesson, tenant_id)


# ---------------------------------------------------------------------------
# Summary / analytics
# ---------------------------------------------------------------------------


def get_kb_summary(tenant_id: int) -> dict:
    """Return aggregate statistics for the tenant's KB view.

    Returns:
        {
          "total": 45,
          "public_count": 10,
          "by_category": {"what_went_well": 20, "what_went_wrong": 15, ...},
          "by_module": {"FI": 8, "MM": 5, ...},
          "top_voted": [{"id": .., "title": .., "upvote_count": 8}]
        }
    """
    own_lessons = LessonLearned.tenant_id == tenant_id

    # Totals
    total = db.session.execute(
        select(func.count()).where(own_lessons)
    ).scalar_one()

    public_count = db.session.execute(
        select(func.count()).where(own_lessons, LessonLearned.is_public.is_(True))
    ).scalar_one()

    # By category
    rows = db.session.execute(
        select(LessonLearned.category, func.count().label("n"))
        .where(own_lessons)
        .group_by(LessonLearned.category)
    ).all()
    by_category = {row.category: row.n for row in rows}

    # By SAP module (only non-null)
    rows = db.session.execute(
        select(LessonLearned.sap_module, func.count().label("n"))
        .where(own_lessons, LessonLearned.sap_module.isnot(None))
        .group_by(LessonLearned.sap_module)
        .order_by(func.count().desc())
        .limit(10)
    ).all()
    by_module = {row.sap_module: row.n for row in rows}

    # Top voted lessons (up to 5)
    top_lessons = db.session.execute(
        select(LessonLearned)
        .where(own_lessons)
        .order_by(LessonLearned.upvote_count.desc(), LessonLearned.created_at.desc())
        .limit(5)
    ).scalars().all()
    top_voted = [
        {"id": le.id, "title": le.title, "upvote_count": le.upvote_count}
        for le in top_lessons
    ]

    return {
        "total": total,
        "public_count": public_count,
        "by_category": by_category,
        "by_module": by_module,
        "top_voted": top_voted,
    }


# ---------------------------------------------------------------------------
# Convenience: create from incident / risk
# ---------------------------------------------------------------------------


def add_lesson_from_incident(
    tenant_id: int,
    incident_id: int,
    data: dict,
    author_id: int | None = None,
) -> dict:
    """Create a lesson pre-linked to a HypercareIncident.

    Convenience wrapper for the incident close flow. Sets linked_incident_id
    and defaults category to 'risk_realized' if not provided.

    Raises:
        ValueError: If required fields missing or incident not found.
    """
    data = dict(data)  # don't mutate caller dict
    data.setdefault("category", "risk_realized")
    data["linked_incident_id"] = incident_id
    return create_lesson(tenant_id=tenant_id, data=data, author_id=author_id)


def add_lesson_from_risk(
    tenant_id: int,
    risk_id: int,
    data: dict,
    author_id: int | None = None,
) -> dict:
    """Create a lesson pre-linked to a RAID Risk.

    Convenience wrapper for risk close flow. Defaults category to 'risk_realized'.

    Raises:
        ValueError: If required fields missing.
    """
    data = dict(data)
    data.setdefault("category", "risk_realized")
    data["linked_risk_id"] = risk_id
    return create_lesson(tenant_id=tenant_id, data=data, author_id=author_id)
