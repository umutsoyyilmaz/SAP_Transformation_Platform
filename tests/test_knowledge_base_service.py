"""
Tests for Knowledge Base service functions (FDD-I04 / S6-01).

Covers:
  - create_lesson: happy path returns dict with id
  - search_lessons: text search by title LIKE
  - search_lessons: filter by sap_module
  - cross-tenant: public lesson from another tenant IS visible
  - cross-tenant: private lesson from another tenant is NOT visible
  - upvote_lesson: increments upvote_count
  - upvote_lesson: duplicate upvote raises ValueError (409-equivalent)
  - get_kb_summary: returns by_category breakdowns
  - to_dict_public: masks project_id, tenant_id, author_id, linked IDs

Marker: unit (no integration dependencies).
"""

import pytest

from app.models import db
from app.models.auth import Tenant, User
from app.models.run_sustain import LessonLearned, LessonUpvote
from app.services import knowledge_base_service


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tenant() -> Tenant:
    t = Tenant(name="KB Corp", slug="kb-corp")
    db.session.add(t)
    db.session.flush()
    return t


@pytest.fixture()
def other_tenant() -> Tenant:
    t = Tenant(name="Other Corp", slug="other-kb-corp")
    db.session.add(t)
    db.session.flush()
    return t


@pytest.fixture()
def author(tenant: Tenant) -> User:
    u = User(
        tenant_id=tenant.id,
        email="kb_author@test.com",
        full_name="KB Author",
        password_hash="x",
        status="active",
    )
    db.session.add(u)
    db.session.flush()
    return u


def _make_lesson(
    tenant_id: int,
    title: str = "Default Lesson",
    category: str = "what_went_well",
    is_public: bool = False,
    sap_module: str | None = None,
    author_id: int | None = None,
    project_id: int | None = None,
    linked_incident_id: int | None = None,
    linked_risk_id: int | None = None,
) -> LessonLearned:
    """Helper: create a LessonLearned row directly (bypasses service validation)."""
    from datetime import datetime, timezone

    lesson = LessonLearned(
        tenant_id=tenant_id,
        title=title,
        category=category,
        is_public=is_public,
        sap_module=sap_module,
        author_id=author_id,
        project_id=project_id,
        linked_incident_id=linked_incident_id,
        linked_risk_id=linked_risk_id,
        upvote_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.session.add(lesson)
    db.session.flush()
    return lesson


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestCreateLesson:
    def test_create_lesson_returns_dict_with_id(self, tenant: Tenant, author: User):
        """Happy path: create_lesson returns a serialized dict containing 'id'."""
        result = knowledge_base_service.create_lesson(
            tenant_id=tenant.id,
            data={
                "title": "Lessons from FI cutover",
                "category": "what_went_well",
                "description": "Double-posting checks ran flawlessly.",
                "recommendation": "Automate this check.",
                "sap_module": "FI",
            },
            author_id=author.id,
        )

        assert isinstance(result, dict)
        assert "id" in result
        assert result["title"] == "Lessons from FI cutover"
        assert result["category"] == "what_went_well"
        assert result["tenant_id"] == tenant.id
        assert result["author_id"] == author.id
        assert result["is_public"] is False  # default

    def test_create_lesson_returns_400_when_title_missing(self, tenant: Tenant):
        """Missing title raises ValueError (service-level 400-equivalent)."""
        with pytest.raises(ValueError, match="[Tt]itle"):
            knowledge_base_service.create_lesson(
                tenant_id=tenant.id,
                data={"category": "what_went_well"},
            )

    def test_create_lesson_returns_400_when_category_invalid(self, tenant: Tenant):
        """Invalid category value raises ValueError."""
        with pytest.raises(ValueError, match="[Cc]ategory"):
            knowledge_base_service.create_lesson(
                tenant_id=tenant.id,
                data={"title": "Test", "category": "not_a_category"},
            )


class TestSearchLessons:
    def test_search_lessons_by_title_text(self, tenant: Tenant):
        """Text search on title returns matching lessons and excludes non-matches."""
        _make_lesson(tenant.id, title="FI posting key lessons")
        _make_lesson(tenant.id, title="SD pricing procedure notes")

        result = knowledge_base_service.search_lessons(
            tenant_id=tenant.id,
            query="FI posting",
        )

        titles = [item["title"] for item in result["items"]]
        assert "FI posting key lessons" in titles
        assert "SD pricing procedure notes" not in titles

    def test_search_lessons_filter_by_sap_module(self, tenant: Tenant):
        """sap_module filter returns only lessons for that module."""
        _make_lesson(tenant.id, title="MM inventory count", sap_module="MM")
        _make_lesson(tenant.id, title="SD delivery split", sap_module="SD")

        result = knowledge_base_service.search_lessons(
            tenant_id=tenant.id,
            sap_module="MM",
        )

        titles = [item["title"] for item in result["items"]]
        assert "MM inventory count" in titles
        assert "SD delivery split" not in titles

    def test_search_returns_paginated_response_shape(self, tenant: Tenant):
        """Response must contain items, total, page, per_page keys."""
        result = knowledge_base_service.search_lessons(tenant_id=tenant.id)

        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "per_page" in result


class TestCrossTenantVisibility:
    def test_public_lesson_from_other_tenant_is_visible(
        self, tenant: Tenant, other_tenant: Tenant
    ):
        """A public lesson from another tenant IS returned in search results."""
        _make_lesson(other_tenant.id, title="Cross-tenant FI tip", is_public=True)

        result = knowledge_base_service.search_lessons(
            tenant_id=tenant.id,
            include_public=True,
        )

        titles = [item["title"] for item in result["items"]]
        assert "Cross-tenant FI tip" in titles

    def test_private_lesson_not_visible_to_other_tenants(
        self, tenant: Tenant, other_tenant: Tenant
    ):
        """A private lesson from another tenant must NOT appear in search or get."""
        lesson = _make_lesson(other_tenant.id, title="Secret lesson", is_public=False)

        # Direct get by another tenant raises ValueError (404-equivalent)
        with pytest.raises(ValueError):
            knowledge_base_service.get_lesson(
                tenant_id=tenant.id,
                lesson_id=lesson.id,
            )

        # Search should also not include it
        result = knowledge_base_service.search_lessons(
            tenant_id=tenant.id,
            include_public=True,
        )
        titles = [item["title"] for item in result["items"]]
        assert "Secret lesson" not in titles


class TestUpvoteLesson:
    def test_upvote_increments_count(self, tenant: Tenant, author: User):
        """Upvoting a lesson increments upvote_count by 1."""
        lesson = _make_lesson(tenant.id, is_public=True)
        initial_count = lesson.upvote_count

        knowledge_base_service.upvote_lesson(
            tenant_id=tenant.id,
            lesson_id=lesson.id,
            user_id=author.id,
        )

        db.session.refresh(lesson)
        assert lesson.upvote_count == initial_count + 1

    def test_upvote_duplicate_raises_error(self, tenant: Tenant, author: User):
        """Voting twice by the same user raises ValueError (409-equivalent)."""
        lesson = _make_lesson(tenant.id, is_public=True)

        knowledge_base_service.upvote_lesson(
            tenant_id=tenant.id,
            lesson_id=lesson.id,
            user_id=author.id,
        )

        with pytest.raises(ValueError, match="already upvoted"):
            knowledge_base_service.upvote_lesson(
                tenant_id=tenant.id,
                lesson_id=lesson.id,
                user_id=author.id,
            )


class TestKbSummary:
    def test_kb_summary_returns_by_category_counts(self, tenant: Tenant):
        """get_kb_summary returns a dict with by_category breakdown."""
        _make_lesson(tenant.id, category="what_went_well")
        _make_lesson(tenant.id, category="what_went_well")
        _make_lesson(tenant.id, category="best_practice")

        summary = knowledge_base_service.get_kb_summary(tenant_id=tenant.id)

        assert "total" in summary
        assert "by_category" in summary
        assert summary["total"] >= 3
        assert summary["by_category"].get("what_went_well", 0) >= 2
        assert summary["by_category"].get("best_practice", 0) >= 1


class TestToDictPublic:
    def test_to_dict_public_masks_sensitive_fields(
        self, tenant: Tenant, author: User
    ):
        """to_dict_public() must mask project_id, tenant_id, author_id and linked IDs.

        We verify masking by creating a lesson with a valid author_id (traceable
        to a real user) then confirming to_dict_public() nullifies it along
        with tenant_id.  project_id / linked FKs are left None (no valid rows in
        test DB) — the masking contract still applies when they are set.
        """
        lesson = _make_lesson(
            tenant_id=tenant.id,
            title="Public FI tip",
            is_public=True,
            author_id=author.id,
        )

        full_dict = lesson.to_dict()
        public_dict = lesson.to_dict_public()

        # Full dict exposes actual values
        assert full_dict["tenant_id"] == tenant.id
        assert full_dict["author_id"] == author.id

        # Public dict masks all sensitive identifiers
        assert public_dict["project_id"] is None
        assert public_dict["tenant_id"] is None
        assert public_dict["author_id"] is None
        assert public_dict["linked_incident_id"] is None
        assert public_dict["linked_risk_id"] is None

        # Non-sensitive fields must still be exposed
        assert public_dict["title"] == "Public FI tip"
        assert public_dict["is_public"] is True
