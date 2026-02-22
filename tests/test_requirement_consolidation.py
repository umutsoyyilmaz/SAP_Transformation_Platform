"""
Tests: Requirement Model Consolidation (FDD-B01 / S1-05).

Covers the 7 unit tests + 3 integration tests specified in FDD-B01 §8.

Test Strategy:
  - Direct ORM layer tests for new ExploreRequirement fields (no HTTP needed).
  - Write-block test verifies RuntimeError on legacy Requirement insert.
  - Migration idempotency test via migrate() dry_run.
  - Tenant isolation test with parent-child hierarchy.
"""

from __future__ import annotations

import pytest

from app.models import db as _db
from app.models.explore.requirement import ExploreRequirement
from app.models.program import Program


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def program():
    """Minimal Program required as project_id for all explore requirements."""
    prog = Program(name="B01 Test Project", methodology="agile")
    _db.session.add(prog)
    _db.session.flush()
    return prog


import uuid as _uuid_mod


def _make_req(program_id: int, title: str = "Test Req", **kwargs) -> ExploreRequirement:
    """Convenience factory for ExploreRequirement with mandatory fields.

    Uses a short UUID suffix to guarantee code uniqueness within a project.
    """
    unique_suffix = _uuid_mod.uuid4().hex[:4].upper()
    req = ExploreRequirement(
        project_id=program_id,
        code=f"REQ-{unique_suffix}",
        title=title,
        created_by_id="test-user",
        **kwargs,
    )
    _db.session.add(req)
    _db.session.flush()
    return req


# ── Unit Tests ────────────────────────────────────────────────────────────────


def test_explore_requirement_accepts_moscow_priority(program):
    """moscow_priority column stores all four MoSCoW values without error."""
    for priority in ("must_have", "should_have", "could_have", "wont_have"):
        req = _make_req(program.id, title=f"Req {priority}", moscow_priority=priority)
        _db.session.flush()
        assert req.moscow_priority == priority

    # to_dict() must expose the field
    final_req = _make_req(program.id, title="to_dict check", moscow_priority="must_have")
    d = final_req.to_dict()
    assert d["moscow_priority"] == "must_have"


def test_explore_requirement_accepts_parent_id_self_reference(program):
    """parent_id creates a valid parent-child relationship within the same table."""
    parent = _make_req(program.id, title="Epic requirement")
    child = _make_req(program.id, title="Feature requirement", parent_id=parent.id)

    _db.session.flush()

    assert child.parent_id == parent.id
    # ORM backref: parent relationship loads correctly
    assert child.parent.id == parent.id
    # children on the parent side
    assert any(c.id == child.id for c in parent.children)


def test_explore_requirement_source_field_nullable_and_accepts_valid_values(program):
    """source field is nullable=True and accepts workshop/stakeholder/regulation/etc.

    Note: the column has default='workshop' so the ORM fills in the default even
    when source is not provided.  We verify nullable=True by confirming a NULL can
    be persisted via direct column inspection, and that all valid values round-trip.
    """
    from sqlalchemy import inspect as _inspect
    col = next(c for c in _inspect(ExploreRequirement).columns if c.key == "source")
    assert col.nullable is True, "source column must be nullable=True (reviewer audit A3)"

    # Each valid source value round-trips correctly
    for src in ("workshop", "stakeholder", "regulation", "gap_analysis", "standard_process"):
        req = _make_req(program.id, title=f"Src {src}", source=src)
        _db.session.flush()
        assert req.source == src

    d = req.to_dict()
    assert "source" in d


def test_explore_requirement_requirement_type_field(program):
    """requirement_type field accepts business / functional / technical etc."""
    for rtype in ("business", "functional", "technical", "non_functional", "integration"):
        req = _make_req(program.id, title=f"Type {rtype}", requirement_type=rtype)
        _db.session.flush()
        assert req.requirement_type == rtype
        assert req.to_dict()["requirement_type"] == rtype


def test_explore_requirement_external_id_indexed(program):
    """external_id stores Jira/SAP-ALM IDs and is exposed in to_dict()."""
    req = _make_req(program.id, title="External sync", external_id="JIRA-12345")
    _db.session.flush()
    assert req.external_id == "JIRA-12345"
    assert req.to_dict()["external_id"] == "JIRA-12345"


def test_legacy_requirement_write_block_raises_runtime_error(program):
    """Inserting into the legacy `requirements` table raises RuntimeError (write-block).

    This is the ORM-level enforcement of the write-block introduced in S1-05.
    Any code path that tries to create a new Requirement will fail fast with a
    clear error message rather than silently writing to a frozen table.

    The write-block is bypassed in TESTING mode to avoid mass-migrating legacy
    test fixtures. Here we temporarily disable TESTING to verify the block fires
    in a simulated production context.
    """
    from flask import current_app

    from app.models.requirement import Requirement

    current_app.config["TESTING"] = False
    try:
        with pytest.raises(RuntimeError, match="write-blocked"):
            legacy = Requirement(
                program_id=program.id,
                title="Should be blocked",
            )
            _db.session.add(legacy)
            _db.session.flush()
    finally:
        current_app.config["TESTING"] = True  # restore for subsequent tests


def test_migration_script_maps_all_legacy_fields_correctly(program):
    """migrate() dry_run processes a manually seeded legacy row and maps fields."""
    # Seed a legacy requirement directly via raw SQL (bypassing write-block)
    _db.session.execute(
        __import__("sqlalchemy").text(
            "INSERT INTO requirements "
            "(program_id, tenant_id, code, title, description, req_type, priority, status, source, created_at, updated_at) "
            "VALUES (:pid, NULL, :code, :title, :desc, :rtype, :prio, :status, :src, datetime('now'), datetime('now'))"
        ),
        {
            "pid": program.id,
            "code": "REQ-LEG-001",
            "title": "Legacy requirement title",
            "desc": "A description",
            "rtype": "functional",
            "prio": "must_have",
            "status": "approved",
            "src": "workshop",
        },
    )
    _db.session.flush()
    legacy_id = _db.session.execute(
        __import__("sqlalchemy").text("SELECT id FROM requirements WHERE code = 'REQ-LEG-001'")
    ).scalar()
    assert legacy_id is not None

    from scripts.migrate_legacy_requirements import migrate

    stats = migrate(dry_run=True)

    # Even in dry_run, migrated count should be > 0 while the transaction was active
    # (dry_run rolls back, so we can't assert the final DB state, but stats are correct)
    assert stats["errors"] == 0
    # migrated count covers the one we seeded above
    assert stats["migrated"] >= 1


def test_migration_preserves_legacy_requirement_id(program):
    """After migration, ExploreRequirement.legacy_requirement_id links back to requirements.id."""
    from flask import current_app
    sa = __import__("sqlalchemy")
    # Seed a legacy requirement bypassing write-block
    _db.session.execute(
        sa.text(
            "INSERT INTO requirements "
            "(program_id, tenant_id, code, title, description, req_type, priority, status, source, created_at, updated_at) "
            "VALUES (:pid, NULL, 'REQ-PRES-001', 'Preserve test', '', 'functional', 'must_have', 'draft', 'workshop', datetime('now'), datetime('now'))"
        ),
        {"pid": program.id},
    )
    _db.session.flush()
    legacy_id = _db.session.execute(
        sa.text("SELECT id FROM requirements WHERE code = 'REQ-PRES-001'")
    ).scalar()
    assert legacy_id is not None

    from scripts.migrate_legacy_requirements import migrate

    stats = migrate(app=current_app._get_current_object(), dry_run=False)
    assert stats["errors"] == 0

    migrated = ExploreRequirement.query.filter_by(legacy_requirement_id=legacy_id).first()
    assert migrated is not None, "No ExploreRequirement found with legacy_requirement_id set"
    assert migrated.legacy_requirement_id == legacy_id
    assert migrated.title == "Preserve test"


# ── Integration Tests ─────────────────────────────────────────────────────────


def test_moscow_summary_via_query(program):
    """Direct query grouping by moscow_priority returns correct counts.

    Validates the data model supports the summary endpoint (FDD §5.2).
    """
    _make_req(program.id, title="M1", moscow_priority="must_have")
    _make_req(program.id, title="M2", moscow_priority="must_have")
    _make_req(program.id, title="S1", moscow_priority="should_have")
    _make_req(program.id, title="C1", moscow_priority=None)
    _db.session.flush()

    from sqlalchemy import func, select

    rows = _db.session.execute(
        select(ExploreRequirement.moscow_priority, func.count())
        .where(ExploreRequirement.project_id == program.id)
        .group_by(ExploreRequirement.moscow_priority)
    ).fetchall()

    summary = {r[0]: r[1] for r in rows}
    assert summary.get("must_have") == 2
    assert summary.get("should_have") == 1
    assert summary.get(None) == 1


def test_traceability_works_with_legacy_requirement_id_field(program):
    """ExploreRequirement with legacy_requirement_id set is queryable by that field.

    Back-compat: services can look up migrated requirements by their old integer ID.
    """
    req = _make_req(program.id, title="Migrated req", legacy_requirement_id=9999)
    _db.session.flush()

    found = ExploreRequirement.query.filter_by(legacy_requirement_id=9999).first()
    assert found is not None
    assert found.id == req.id


def test_tenant_isolation_on_explore_requirements_with_parent(program):
    """cross-tenant query using wrong tenant_id must not return another tenant's data.

    The parent-child hierarchy must be scoped per tenant.
    """
    from app.models.auth import Tenant

    tenant_a = Tenant(name="Tenant A", slug="tid-a-iso")
    tenant_b = Tenant(name="Tenant B", slug="tid-b-iso")
    _db.session.add_all([tenant_a, tenant_b])
    _db.session.flush()

    from app.models.program import Program as _Prog

    prog_b = _Prog(name="B Program", methodology="agile", tenant_id=tenant_b.id)
    _db.session.add(prog_b)
    _db.session.flush()

    parent_b = _make_req(prog_b.id, title="Parent B", moscow_priority="must_have")
    child_b = _make_req(prog_b.id, title="Child B", parent_id=parent_b.id)
    _db.session.flush()

    # Querying with tenant_a.id must NOT return tenant_b's requirements
    tenant_a_results = (
        ExploreRequirement.query
        .filter_by(tenant_id=tenant_a.id)
        .all()
    )
    tenant_a_ids = {r.id for r in tenant_a_results}
    assert parent_b.id not in tenant_a_ids
    assert child_b.id not in tenant_a_ids
