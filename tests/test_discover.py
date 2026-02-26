"""
Tests: Discover Phase MVP — FDD-B02 / S3-01.

Covers all required test cases:
  1.  POST charter → 201
  2.  Charter upsert does not create duplicates
  3.  Charter approve sets status=approved
  4.  Approved charter rejects structural edits (422)
  5.  Gate status fails when charter not approved
  6.  Gate status fails when no system landscape
  7.  Gate status passes when all 3 criteria met
  8.  System landscape create + list
  9.  Scope assessment upsert by module (idempotent)
  10. DELETE scope assessment removes the record
  11. Tenant isolation: charter cross-tenant returns 404
  12. Tenant isolation: landscape cross-tenant returns 404
  13. Missing required field returns 400
  14. Non-existent program returns 404
  15. Program without tenant_id returns 422

Setup: Tenant → User → Program created via ORM for each test (same pattern
as test_signoff_workflow.py).  The `session` autouse fixture rolls back after
every test, so no state leaks between runs.
"""

import pytest

from app.models import db as _db
from app.models.auth import Tenant, User
from app.models.program import Program


# ── ORM helpers ────────────────────────────────────────────────────────────────


def _make_tenant(slug: str = "discover-co") -> Tenant:
    t = Tenant(name="Discover Co", slug=slug)
    _db.session.add(t)
    _db.session.flush()
    return t


def _make_user(email: str, tenant_id: int) -> User:
    u = User(email=email, full_name="Discover User", tenant_id=tenant_id)
    _db.session.add(u)
    _db.session.flush()
    return u


def _make_program(tenant_id: int, name: str = "Discover Program") -> Program:
    """Create a Program directly via ORM so tenant_id is populated."""
    p = Program(name=name, methodology="agile", tenant_id=tenant_id)
    _db.session.add(p)
    _db.session.flush()
    return p


def _charter_payload(**overrides) -> dict:
    """Minimal valid charter payload."""
    base = {
        "project_objective": "Migrate ECC 6.0 to SAP S/4HANA 2023",
        "project_type": "greenfield",
    }
    base.update(overrides)
    return base


# ── 1. Create charter returns 201 ──────────────────────────────────────────────


def test_create_charter_returns_201_with_valid_payload(client: object) -> None:
    """POST /programs/<pid>/discover/charter with valid body → 201."""
    tenant = _make_tenant()
    prog = _make_program(tenant.id)

    res = client.post(
        f"/api/v1/programs/{prog.id}/discover/charter",
        json=_charter_payload(),
    )

    assert res.status_code == 201
    body = res.get_json()
    assert body["project_objective"] == "Migrate ECC 6.0 to SAP S/4HANA 2023"
    assert body["status"] == "draft"
    assert body["program_id"] == prog.id


# ── 2. Charter upsert is idempotent ───────────────────────────────────────────


def test_create_charter_upsert_does_not_create_duplicate(client: object) -> None:
    """Two POSTs to the same program update the same charter row."""
    tenant = _make_tenant("upsert-co")
    prog = _make_program(tenant.id)

    client.post(f"/api/v1/programs/{prog.id}/discover/charter",
                json=_charter_payload())
    client.post(f"/api/v1/programs/{prog.id}/discover/charter",
                json=_charter_payload(project_objective="Updated objective"))

    res = client.get(f"/api/v1/programs/{prog.id}/discover/charter")
    assert res.status_code == 200
    assert res.get_json()["project_objective"] == "Updated objective"


# ── 3. Charter approve sets status = approved ──────────────────────────────────


def test_charter_approve_sets_status_to_approved(client: object) -> None:
    """POST .../charter/approve transitions status from draft/in_review → approved."""
    tenant = _make_tenant("approve-co")
    user = _make_user("approver@example.com", tenant.id)
    prog = _make_program(tenant.id)

    client.post(f"/api/v1/programs/{prog.id}/discover/charter",
                json=_charter_payload())

    res = client.post(
        f"/api/v1/programs/{prog.id}/discover/charter/approve",
        json={"approver_id": user.id, "notes": "Approved in board meeting"},
    )

    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "approved"
    assert body["approved_by_id"] == user.id
    assert body["approval_notes"] == "Approved in board meeting"


# ── 4. Approved charter is locked against structural edits ────────────────────


def test_approved_charter_rejects_structural_edits(client: object) -> None:
    """POST/PUT to an approved charter returns 422 (business rule lock)."""
    tenant = _make_tenant("lock-co")
    user = _make_user("locker@example.com", tenant.id)
    prog = _make_program(tenant.id)

    client.post(f"/api/v1/programs/{prog.id}/discover/charter",
                json=_charter_payload())
    client.post(f"/api/v1/programs/{prog.id}/discover/charter/approve",
                json={"approver_id": user.id})

    res = client.post(
        f"/api/v1/programs/{prog.id}/discover/charter",
        json=_charter_payload(project_objective="Trying to change after approval"),
    )
    assert res.status_code == 422


# ── 5. Gate fails when charter not approved ────────────────────────────────────


def test_discover_gate_fails_when_charter_not_approved(client: object) -> None:
    """Gate status criterion 'charter_approved' is False when no charter exists."""
    tenant = _make_tenant("gate-fail-co")
    prog = _make_program(tenant.id)

    res = client.get(f"/api/v1/programs/{prog.id}/discover/gate-status")
    assert res.status_code == 200
    body = res.get_json()
    assert body["gate_passed"] is False
    criteria_map = {c["name"]: c["passed"] for c in body["criteria"]}
    assert criteria_map["charter_approved"] is False


# ── 6. Gate fails when no system in landscape ─────────────────────────────────


def test_discover_gate_fails_when_no_system_landscape(client: object) -> None:
    """Gate status criterion 'landscape_defined' is False when no systems exist."""
    tenant = _make_tenant("gate-noland-co")
    user = _make_user("gl@example.com", tenant.id)
    prog = _make_program(tenant.id)

    # Approve charter so that criterion 1 passes
    client.post(f"/api/v1/programs/{prog.id}/discover/charter",
                json=_charter_payload())
    client.post(f"/api/v1/programs/{prog.id}/discover/charter/approve",
                json={"approver_id": user.id})

    res = client.get(f"/api/v1/programs/{prog.id}/discover/gate-status")
    body = res.get_json()
    criteria_map = {c["name"]: c["passed"] for c in body["criteria"]}
    assert criteria_map["landscape_defined"] is False
    assert body["gate_passed"] is False


# ── 7. Gate passes when all 3 criteria met ────────────────────────────────────


def test_discover_gate_passes_when_all_criteria_met(client: object) -> None:
    """Gate passes when: charter approved + ≥1 active system + ≥3 modules in scope."""
    tenant = _make_tenant("gate-pass-co")
    user = _make_user("gp@example.com", tenant.id)
    prog = _make_program(tenant.id)

    # Criterion 1: approved charter
    client.post(f"/api/v1/programs/{prog.id}/discover/charter",
                json=_charter_payload())
    client.post(f"/api/v1/programs/{prog.id}/discover/charter/approve",
                json={"approver_id": user.id})

    # Criterion 2: at least 1 active system
    client.post(f"/api/v1/programs/{prog.id}/discover/landscape",
                json={"system_name": "ECC Production", "system_type": "sap_erp",
                      "role": "source", "is_active": True})

    # Criterion 3: at least 3 modules in scope
    for mod in ["FI", "CO", "MM"]:
        client.post(f"/api/v1/programs/{prog.id}/discover/scope-assessment",
                    json={"sap_module": mod, "is_in_scope": True})

    res = client.get(f"/api/v1/programs/{prog.id}/discover/gate-status")
    assert res.status_code == 200
    body = res.get_json()
    assert body["gate_passed"] is True
    assert all(c["passed"] for c in body["criteria"])


# ── 8. System landscape create and list ───────────────────────────────────────


def test_system_landscape_create_and_list(client: object) -> None:
    """POST landscape → 201; GET landscape returns the added system."""
    tenant = _make_tenant("land-co")
    prog = _make_program(tenant.id)

    res_create = client.post(
        f"/api/v1/programs/{prog.id}/discover/landscape",
        json={"system_name": "SAP S/4HANA Cloud", "system_type": "s4hana",
              "role": "target", "vendor": "SAP", "environment": "prod"},
    )
    assert res_create.status_code == 201
    created_id = res_create.get_json()["id"]

    res_list = client.get(f"/api/v1/programs/{prog.id}/discover/landscape")
    assert res_list.status_code == 200
    items = res_list.get_json().get("items", res_list.get_json())
    assert any(s["id"] == created_id for s in items)
    assert any(s["system_name"] == "SAP S/4HANA Cloud" for s in items)


# ── 9. Scope assessment upsert is idempotent ──────────────────────────────────


def test_scope_assessment_upsert_by_module_is_idempotent(client: object) -> None:
    """POST scope-assessment twice for same module updates the record, not creates two."""
    tenant = _make_tenant("scope-co")
    prog = _make_program(tenant.id)

    client.post(f"/api/v1/programs/{prog.id}/discover/scope-assessment",
                json={"sap_module": "FI", "is_in_scope": True, "complexity": "low"})
    client.post(f"/api/v1/programs/{prog.id}/discover/scope-assessment",
                json={"sap_module": "FI", "is_in_scope": True, "complexity": "high"})

    res = client.get(f"/api/v1/programs/{prog.id}/discover/scope-assessment")
    items = res.get_json().get("items", res.get_json())
    fi_rows = [a for a in items if a["sap_module"] == "FI"]
    assert len(fi_rows) == 1, "Upsert must not create duplicate rows for the same module"
    assert fi_rows[0]["complexity"] == "high"


# ── 10. DELETE scope assessment ───────────────────────────────────────────────


def test_delete_scope_assessment_removes_record(client: object) -> None:
    """DELETE scope-assessment/<id> removes the record; subsequent GET omits it."""
    tenant = _make_tenant("del-scope-co")
    prog = _make_program(tenant.id)

    # scope-assessment is an upsert endpoint; it returns 200 for both create and update
    res_create = client.post(f"/api/v1/programs/{prog.id}/discover/scope-assessment",
                             json={"sap_module": "SD", "is_in_scope": True})
    assert res_create.status_code == 200
    aid = res_create.get_json()["id"]

    res_del = client.delete(f"/api/v1/programs/{prog.id}/discover/scope-assessment/{aid}")
    assert res_del.status_code == 204

    res_list = client.get(f"/api/v1/programs/{prog.id}/discover/scope-assessment")
    items = res_list.get_json().get("items", res_list.get_json())
    assert all(a["id"] != aid for a in items)


# ── 11. Tenant isolation: charter cross-tenant returns 404 ────────────────────


def test_tenant_isolation_charter_cross_tenant_returns_404(client: object) -> None:
    """Tenant A's charter is invisible to Tenant B's program (returns 404).

    Security requirement: returning 403 would confirm resource existence.
    404 is the correct response to avoid information leakage.
    """
    tenant_a = _make_tenant("tenant-a")
    tenant_b = _make_tenant("tenant-b")
    prog_a = _make_program(tenant_a.id, name="Prog A")
    prog_b = _make_program(tenant_b.id, name="Prog B")

    # Create charter for program A
    client.post(f"/api/v1/programs/{prog_a.id}/discover/charter",
                json=_charter_payload())

    # Access program B's charter endpoint — should return 404 (charter doesn't exist for B)
    res = client.get(f"/api/v1/programs/{prog_b.id}/discover/charter")
    assert res.status_code == 404


# ── 12. Tenant isolation: landscape cross-tenant returns empty list ────────────


def test_tenant_isolation_landscape_cross_tenant_returns_empty_list(client: object) -> None:
    """Systems in Tenant A's program are NOT visible via Tenant B's program endpoint."""
    tenant_a = _make_tenant("land-a")
    tenant_b = _make_tenant("land-b")
    prog_a = _make_program(tenant_a.id, name="Land A")
    prog_b = _make_program(tenant_b.id, name="Land B")

    # Add system to program A
    client.post(f"/api/v1/programs/{prog_a.id}/discover/landscape",
                json={"system_name": "Secret ERP", "system_type": "sap_erp",
                      "role": "source"})

    # Program B should see zero systems
    res = client.get(f"/api/v1/programs/{prog_b.id}/discover/landscape")
    assert res.status_code == 200
    items = res.get_json().get("items", res.get_json())
    assert items == [], f"Expected empty list for tenant B, got: {items}"


# ── 13. Missing required field returns 400 ────────────────────────────────────


def test_create_charter_returns_400_when_project_objective_missing(client: object) -> None:
    """project_objective is required; omitting it → 400."""
    tenant = _make_tenant("val-co")
    prog = _make_program(tenant.id)

    res = client.post(f"/api/v1/programs/{prog.id}/discover/charter",
                      json={"project_type": "greenfield"})
    assert res.status_code == 400
    body = res.get_json()
    assert "details" in body or "error" in body


def test_create_landscape_returns_400_when_system_name_missing(client: object) -> None:
    """system_name is required for landscape; omitting it → 400."""
    tenant = _make_tenant("land-val-co")
    prog = _make_program(tenant.id)

    res = client.post(f"/api/v1/programs/{prog.id}/discover/landscape",
                      json={"system_type": "sap_erp"})
    assert res.status_code == 400


# ── 14. Non-existent program returns 404 ──────────────────────────────────────


def test_charter_returns_404_for_nonexistent_program(client: object) -> None:
    """GET charter for program 99999 → 404."""
    res = client.get("/api/v1/programs/99999/discover/charter")
    assert res.status_code == 404


def test_gate_status_returns_404_for_nonexistent_program(client: object) -> None:
    """GET gate-status for non-existent program → 404."""
    res = client.get("/api/v1/programs/99999/discover/gate-status")
    assert res.status_code == 404


# ── 15. Program without tenant_id returns 422 ─────────────────────────────────


def test_discover_returns_422_for_program_without_tenant_id(client: object) -> None:
    """Programs with no tenant_id → DB rejects the insert (nullable=False).

    Since SEC-03 enforces tenant_id NOT NULL at the model level,
    a Program without tenant_id can no longer be created. We verify the
    DB-level constraint instead.
    """
    import sqlalchemy.exc
    prog = Program(name="Orphan Program", methodology="agile")
    _db.session.add(prog)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        _db.session.flush()
    _db.session.rollback()
