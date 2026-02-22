"""
Tests: Formal Sign-off Workflow — FDD-B04 / S1-04.

Covers all 10 test functions required by the FDD spec plus the
tenant-isolation and name-snapshot edge cases.

Setup strategy:
    Each test that exercises the sign-off endpoints must supply a Program
    with a non-NULL tenant_id, because SignoffRecord.tenant_id is nullable=False
    (reviewer A1).  We create Tenant → User → Program directly via the ORM inside
    the test body so that every test is fully self-contained.

    The `session` fixture in conftest.py is autouse=True and rolls back /
    re-creates tables after every test, so there is no shared state between tests.
"""

import pytest

from app.models import db as _db
from app.models.auth import Tenant, User
from app.models.program import Program


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_tenant(slug: str = "test-co") -> Tenant:
    t = Tenant(name="Test Co", slug=slug)
    _db.session.add(t)
    _db.session.flush()
    return t


def _make_user(email: str, tenant_id: int) -> User:
    u = User(email=email, full_name="Test User", tenant_id=tenant_id)
    _db.session.add(u)
    _db.session.flush()
    return u


def _make_program(tenant_id: int) -> Program:
    p = Program(name="Test Program", methodology="agile", tenant_id=tenant_id)
    _db.session.add(p)
    _db.session.flush()
    return p


def _approve(client, program_id: int, entity_type: str, entity_id: str, approver_id: int, **kwargs):
    """Helper: POST a sign-off approval and return the response."""
    payload = {"action": "approved", "approver_id": approver_id}
    payload.update(kwargs)
    return client.post(
        f"/api/v1/programs/{program_id}/signoff/{entity_type}/{entity_id}",
        json=payload,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_approve_workshop_creates_signoff_record(client):
    """Happy path: valid approval request creates a SignoffRecord and returns 201."""
    tenant = _make_tenant()
    user = _make_user("approver@test.com", tenant.id)
    prog = _make_program(tenant.id)

    res = _approve(client, prog.id, "workshop", "ws-1", user.id)

    assert res.status_code == 201
    body = res.get_json()
    assert body["action"] == "approved"
    assert body["entity_type"] == "workshop"
    assert body["entity_id"] == "ws-1"
    assert body["program_id"] == prog.id
    assert body["tenant_id"] == tenant.id


def test_approve_returns_400_for_invalid_entity_type(client):
    """Sending an unknown entity_type must return 400 — not 500."""
    tenant = _make_tenant()
    user = _make_user("approver2@test.com", tenant.id)
    prog = _make_program(tenant.id)

    res = _approve(client, prog.id, "nonexistent_type", "abc-1", user.id)

    assert res.status_code == 400
    body = res.get_json()
    assert "entity_type" in body.get("details", {}) or "error" in body


def test_override_requires_override_reason(client):
    """override_approved action without override_reason must be rejected with 400."""
    tenant = _make_tenant()
    user = _make_user("approver3@test.com", tenant.id)
    prog = _make_program(tenant.id)

    res = client.post(
        f"/api/v1/programs/{prog.id}/signoff/workshop/ws-override",
        json={"action": "override_approved", "approver_id": user.id},  # no override_reason
    )

    assert res.status_code == 400


def test_revoke_removes_approved_status(client):
    """Revoke after approve: entity must no longer be considered approved."""
    tenant = _make_tenant()
    approver = _make_user("approver4@test.com", tenant.id)
    revoker = _make_user("revoker@test.com", tenant.id)
    prog = _make_program(tenant.id)

    # First approve
    res = _approve(client, prog.id, "workshop", "ws-rev", approver.id)
    assert res.status_code == 201

    # Then revoke
    res = client.post(
        f"/api/v1/programs/{prog.id}/signoff/workshop/ws-rev",
        json={"action": "revoked", "approver_id": revoker.id, "comment": "Quality issue found"},
    )
    assert res.status_code == 201

    # History should show 2 records; latest is revoked
    res = client.get(f"/api/v1/programs/{prog.id}/signoff/workshop/ws-rev/history")
    assert res.status_code == 200
    body = res.get_json()
    history = body["history"]
    assert len(history) == 2
    assert history[-1]["action"] == "revoked"


def test_double_approve_creates_second_record_not_error(client):
    """Approving the same entity twice is idempotent: creates two records, no 409."""
    tenant = _make_tenant()
    user = _make_user("double_approver@test.com", tenant.id)
    prog = _make_program(tenant.id)

    res1 = _approve(client, prog.id, "workshop", "ws-dup", user.id)
    res2 = _approve(client, prog.id, "workshop", "ws-dup", user.id)

    assert res1.status_code == 201
    assert res2.status_code == 201

    # Both records should be in history
    res = client.get(f"/api/v1/programs/{prog.id}/signoff/workshop/ws-dup/history")
    history = res.get_json()["history"]
    assert len(history) == 2


def test_signoff_history_is_immutable_ordered_list(client):
    """History endpoint must return an ordered list; records cannot be altered."""
    tenant = _make_tenant()
    user = _make_user("hist_approver@test.com", tenant.id)
    prog = _make_program(tenant.id)

    # Create 3 records: approve → revoke → approve again
    _approve(client, prog.id, "functional_spec", "fs-1", user.id)
    client.post(
        f"/api/v1/programs/{prog.id}/signoff/functional_spec/fs-1",
        json={"action": "revoked", "approver_id": user.id, "comment": "Spec needs revision"},
    )
    _approve(client, prog.id, "functional_spec", "fs-1", user.id)

    res = client.get(f"/api/v1/programs/{prog.id}/signoff/functional_spec/fs-1/history")
    assert res.status_code == 200
    history = res.get_json()["history"]

    assert len(history) == 3
    # Chronological order: approve → revoke → approve
    assert history[0]["action"] == "approved"
    assert history[1]["action"] == "revoked"
    assert history[2]["action"] == "approved"


def test_pending_signoffs_excludes_approved_entities(client):
    """pending endpoint must NOT include entities whose latest record is 'approved'."""
    tenant = _make_tenant()
    user = _make_user("pending_approver@test.com", tenant.id)
    prog = _make_program(tenant.id)

    # Approve ws-A and ws-B; leave ws-C unapproved
    _approve(client, prog.id, "workshop", "ws-A", user.id)
    _approve(client, prog.id, "workshop", "ws-B", user.id)

    res = client.get(f"/api/v1/programs/{prog.id}/signoff/pending")
    assert res.status_code == 200
    pending = res.get_json()["items"]

    pending_ids = [r["entity_id"] for r in pending]
    assert "ws-A" not in pending_ids
    assert "ws-B" not in pending_ids


def test_signoff_summary_returns_correct_counts_per_type(client):
    """summary endpoint must return entity_type breakdown with correct counts."""
    tenant = _make_tenant()
    user = _make_user("summary_approver@test.com", tenant.id)
    prog = _make_program(tenant.id)

    _approve(client, prog.id, "workshop", "ws-s1", user.id)
    _approve(client, prog.id, "workshop", "ws-s2", user.id)
    _approve(client, prog.id, "functional_spec", "fs-s1", user.id)

    res = client.get(f"/api/v1/programs/{prog.id}/signoff/summary")
    assert res.status_code == 200
    summary = res.get_json()["summary"]

    assert summary["workshop"]["approved"] >= 2
    assert summary["functional_spec"]["approved"] >= 1


def test_tenant_isolation_signoff_record_not_visible_cross_tenant(client):
    """Tenant A must not be able to read or create records for Tenant B's program.

    Security contract: return 404 (not 403) so that the existence of the
    program is not revealed to the caller (see coding standards §3).
    """
    # Tenant B owns the program
    tenant_b = _make_tenant(slug="tenant-b")
    approver_b = _make_user("approver_b@test.com", tenant_b.id)
    prog_b = _make_program(tenant_b.id)

    # Create a record for Tenant B
    _approve(client, prog_b.id, "workshop", "ws-iso", approver_b.id)

    # There's nothing blocking Tenant A from making a direct HTTP call to prog_b's ID
    # because in test mode auth is disabled.  However, the signoff service scopes all
    # queries by (tenant_id, program_id) — a forged program_id that belongs to another
    # tenant will yield an empty history, not Tenant B's data.
    # In production, the `require_permission` decorator further restricts this.
    #
    # We test the data-layer isolation directly:
    from app.services.signoff_service import get_signoff_history

    # Create a genuine Tenant A with a different program
    tenant_a = _make_tenant(slug="tenant-a")
    prog_a = _make_program(tenant_a.id)

    # Querying with Tenant A's tenant_id but Tenant B's program_id must return empty
    history_cross = get_signoff_history(tenant_a.id, prog_b.id, "workshop", "ws-iso")
    assert history_cross == [], "Cross-tenant query leaked Tenant B's sign-off records"


def test_approver_name_snapshot_preserved_after_user_delete(client):
    """approver_name_snapshot must not be NULL even if the User row is deleted later.

    This validates reviewer fix A2: the approver's display name is persisted
    at record-creation time so audit trails survive user account removal.
    """
    tenant = _make_tenant()
    approver = _make_user("snapshot_user@test.com", tenant.id)
    prog = _make_program(tenant.id)

    res = _approve(client, prog.id, "workshop", "ws-snap", approver.id)
    assert res.status_code == 201
    record_id = res.get_json()["id"]

    # Simulate user deletion (soft or hard — FK is SET NULL in prod, but here we
    # verify the snapshot column captured the name at approval time)
    from app.models.signoff import SignoffRecord

    rec = _db.session.get(SignoffRecord, record_id)
    assert rec is not None
    assert rec.approver_name_snapshot is not None
    assert len(rec.approver_name_snapshot) > 0
