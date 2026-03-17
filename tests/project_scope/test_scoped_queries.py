"""
Tests for app/services/helpers/scoped_queries.py

These tests are security-critical: they verify the P0 tenant isolation
helper behaves correctly under adversarial conditions.

Scenarios covered:
  1. ValueError when called with no scope parameter at all
  2. ValueError when the provided scope field does not exist on the model
  3. NotFoundError when PK is correct but scope (tenant) does not match
  4. Correct entity returned when PK + scope both match
  5. get_scoped_or_none returns None instead of raising NotFoundError
  6. get_scoped_or_none still raises ValueError for missing/invalid scope
  7. Tenant A cannot see Tenant B's data (core isolation guarantee)

Test isolation strategy:
  Relies on the autouse `session` fixture from conftest.py which rolls back
  and recreates tables after every test. Each test creates its own data.
"""

import pytest

from app.core.exceptions import NotFoundError
from app.services.helpers.scoped_queries import get_scoped, get_scoped_or_none


# ── Test helpers ─────────────────────────────────────────────────────────────


def _make_tenant(db, *, name: str = "Test Tenant", slug: str = "test-tenant"):
    """Create and flush a minimal Tenant record.

    Slug must be unique per test — the session fixture drops/recreates tables
    between tests so reuse is safe within a suite run, but within a single
    test that creates multiple tenants, distinct slugs are required.
    """
    from app.models.auth import Tenant

    tenant = Tenant(name=name, slug=slug, plan="trial", max_users=5)
    db.session.add(tenant)
    db.session.flush()
    return tenant


def _make_program(db, *, tenant_id: int, name: str = "Test Program"):
    """Create and flush a minimal Program scoped to the given tenant."""
    from app.models.program import Program

    program = Program(name=name, methodology="sap_activate", tenant_id=tenant_id)
    db.session.add(program)
    db.session.flush()
    return program


# ── 1. ValueError — no scope provided ────────────────────────────────────────


class TestGetScopedRequiresAtLeastOneScope:
    """get_scoped must refuse to execute when no scope argument is given."""

    def test_get_scoped_without_scope_raises_value_error(self):
        """No scope → ValueError. Fail-loud prevents accidental unscoped lookups."""
        from app.models.program import Program

        with pytest.raises(ValueError, match="requires at least one scope filter"):
            get_scoped(Program, 999)

    def test_error_message_includes_model_name(self):
        """ValueError message names the model to speed up debugging."""
        from app.models.program import Program

        with pytest.raises(ValueError, match="Program"):
            get_scoped(Program, 1)

    def test_all_scope_kwargs_none_is_equivalent_to_no_scope(self):
        """Explicitly passing all scopes as None is the same as not passing them."""
        from app.models.program import Program

        with pytest.raises(ValueError):
            get_scoped(Program, 1, project_id=None, program_id=None, tenant_id=None)


# ── 2. ValueError — scope field absent from model ────────────────────────────


class TestGetScopedRejectsInvalidScopeField:
    """If the model has no matching column, the scope cannot be applied.

    Silently ignoring a scope kwarg that targets a non-existent column would
    produce an unscoped query — the exact security hole we're closing.
    get_scoped raises ValueError instead.
    """

    def test_get_scoped_scope_field_not_on_model_raises_value_error(self):
        """program_id passed but Program has no program_id column → ValueError."""
        from app.models.program import Program

        with pytest.raises(ValueError, match="no applicable scope"):
            # Program does not have a program_id FK on itself
            get_scoped(Program, 1, program_id=99)

    def test_error_message_lists_missing_fields(self):
        """ValueError message names the unresolvable scope fields."""
        from app.models.program import Program

        with pytest.raises(ValueError, match="program_id"):
            get_scoped(Program, 1, program_id=99)


# ── 3. NotFoundError — wrong scope (cross-tenant access) ─────────────────────


class TestGetScopedWrongScopeRaisesNotFound:
    """Accessing an entity with a mismatched scope MUST raise NotFoundError.

    Security intent: callers cannot distinguish 'does not exist' from
    'exists but belongs to another tenant'. Both produce NotFoundError → 404.
    A 403 would confirm the resource exists — that is information disclosure.
    """

    def test_get_scoped_wrong_tenant_id_raises_not_found(self):
        """Correct PK, wrong tenant_id → NotFoundError."""
        from app.models import db

        tenant_a = _make_tenant(db, name="Company A", slug="company-a")
        tenant_b = _make_tenant(db, name="Company B", slug="company-b")
        program = _make_program(db, tenant_id=tenant_a.id, name="A's Program")

        with pytest.raises(NotFoundError):
            get_scoped(type(program), program.id, tenant_id=tenant_b.id)

    def test_get_scoped_nonexistent_pk_raises_not_found(self):
        """PK that does not exist in DB → NotFoundError (same as wrong scope)."""
        from app.models import db

        tenant = _make_tenant(db)

        with pytest.raises(NotFoundError):
            from app.models.program import Program

            get_scoped(Program, 999_999, tenant_id=tenant.id)

    def test_not_found_error_carries_resource_name(self):
        """NotFoundError includes the model name for service-layer logging."""
        from app.models import db
        from app.models.program import Program

        tenant = _make_tenant(db)

        with pytest.raises(NotFoundError) as exc_info:
            get_scoped(Program, 999_999, tenant_id=tenant.id)

        assert exc_info.value.resource == "Program"


# ── 4. Happy path — correct scope returns entity ─────────────────────────────


class TestGetScopedCorrectScopeReturnsEntity:
    """get_scoped returns the entity when both PK and scope match."""

    def test_get_scoped_correct_tenant_id_returns_program(self):
        """Correct tenant_id → Program returned as ORM object."""
        from app.models import db

        tenant = _make_tenant(db)
        program = _make_program(db, tenant_id=tenant.id, name="My Program")

        result = get_scoped(type(program), program.id, tenant_id=tenant.id)

        assert result is not None
        assert result.id == program.id
        assert result.tenant_id == tenant.id
        assert result.name == "My Program"

    def test_get_scoped_returns_correct_entity_among_multiple(self):
        """When multiple programs exist, the correct one is returned by PK + scope."""
        from app.models import db

        tenant = _make_tenant(db)
        prog_1 = _make_program(db, tenant_id=tenant.id, name="Program 1")
        prog_2 = _make_program(db, tenant_id=tenant.id, name="Program 2")

        result = get_scoped(type(prog_1), prog_2.id, tenant_id=tenant.id)

        assert result.id == prog_2.id
        assert result.name == "Program 2"

    def test_tenant_a_cannot_see_tenant_b_program(self):
        """Core isolation guarantee: Tenant A's scope never returns Tenant B's data."""
        from app.models import db

        tenant_a = _make_tenant(db, name="Tenant A", slug="tenant-a")
        tenant_b = _make_tenant(db, name="Tenant B", slug="tenant-b")
        prog_b = _make_program(db, tenant_id=tenant_b.id, name="B's Secret Program")

        # Tenant A is authenticated but tries to access B's resource by guessing the PK
        with pytest.raises(NotFoundError):
            get_scoped(type(prog_b), prog_b.id, tenant_id=tenant_a.id)


# ── 5. get_scoped_or_none — None instead of NotFoundError ────────────────────


class TestGetScopedOrNone:
    """get_scoped_or_none returns None for missing/wrong-scope entities."""

    def test_returns_none_for_nonexistent_pk(self):
        """Non-existent PK → None (not an exception)."""
        from app.models import db
        from app.models.program import Program

        tenant = _make_tenant(db)

        result = get_scoped_or_none(Program, 999_999, tenant_id=tenant.id)

        assert result is None

    def test_returns_none_for_wrong_tenant(self):
        """Wrong tenant_id → None (cross-tenant access silently blocked)."""
        from app.models import db

        tenant_a = _make_tenant(db, name="A Corp", slug="a-corp")
        tenant_b = _make_tenant(db, name="B Corp", slug="b-corp")
        program = _make_program(db, tenant_id=tenant_a.id)

        result = get_scoped_or_none(type(program), program.id, tenant_id=tenant_b.id)

        assert result is None

    def test_returns_entity_for_correct_scope(self):
        """Correct scope → entity returned (not None)."""
        from app.models import db

        tenant = _make_tenant(db)
        program = _make_program(db, tenant_id=tenant.id, name="Found Program")

        result = get_scoped_or_none(type(program), program.id, tenant_id=tenant.id)

        assert result is not None
        assert result.id == program.id


# ── 6. get_scoped_or_none — still enforces scope requirement ─────────────────


class TestGetScopedOrNoneEnforcesScope:
    """get_scoped_or_none must raise ValueError for missing/invalid scope.

    Returning None silently for a no-scope call would allow callers to
    accidentally write unscoped lookups that appear to 'work' (return None).
    This class verifies that None-on-missing does not mean None-on-everything.
    """

    def test_raises_value_error_without_any_scope(self):
        """No scope → ValueError (same enforcement as get_scoped)."""
        from app.models.program import Program

        with pytest.raises(ValueError):
            get_scoped_or_none(Program, 1)

    def test_raises_value_error_when_scope_field_not_on_model(self):
        """Scope field absent from model → ValueError (not None)."""
        from app.models.program import Program

        with pytest.raises(ValueError):
            get_scoped_or_none(Program, 1, program_id=99)
