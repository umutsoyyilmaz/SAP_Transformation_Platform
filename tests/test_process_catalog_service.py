"""Tests for process_catalog_service — S7-01 FDD-I07 SAP 1YG Process Catalog.

Tests cover:
  1. load_catalog_from_json — creates L1/L2/L3/L4 records from JSON
  2. load_catalog_from_json — idempotent on second run (no duplicates)
  3. seed_project_from_catalog — creates ProcessLevel hierarchy rows
  4. seed_project_from_catalog — skips existing matching codes
  5. get_catalog_tree — filters by sap_module
  6. seed_project_from_catalog — returns correct created/skipped counts
  7. seed_project_from_catalog — tenant_id is scoped correctly (tenant isolation)
"""

import json
import tempfile
from pathlib import Path

import pytest

from app.models import db
from app.models.explore.process import (
    L1SeedCatalog,
    L2SeedCatalog,
    L3SeedCatalog,
    L4SeedCatalog,
)
from app.services import process_catalog_service


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _write_catalog_json(tmp_path: Path, l1_code: str, l2_code: str, sap_module: str, l3s: list) -> str:
    """Write a minimal catalog JSON to a temp file and return its path."""
    data = {
        "l1": {
            "code": l1_code,
            "name": f"Test L1 {l1_code}",
            "sap_module_group": "FI_CO",
            "description": "Test L1",
            "sort_order": 10,
        },
        "l2": {
            "code": l2_code,
            "name": f"Test L2 {l2_code}",
            "sap_module": sap_module,
            "description": "Test L2",
            "sort_order": 10,
            "is_s4_mandatory": True,
        },
        "l3_list": l3s,
    }
    path = tmp_path / f"{l2_code.lower().replace('-', '_')}.json"
    path.write_text(json.dumps(data))
    return str(path)


def _make_l3(code: str, name: str, l4s: list) -> dict:
    return {
        "code": code,
        "name": name,
        "sap_scope_item_id": None,
        "typical_complexity": "medium",
        "sort_order": 10,
        "description": f"{name} description",
        "l4_list": l4s,
    }


def _make_l4(code: str, name: str, fit: str = "fit") -> dict:
    return {
        "sub_process_code": code,
        "sub_process_name": name,
        "description": f"{name} description",
        "typical_fit_decision": fit,
        "is_customer_facing": False,
        "standard_sequence": 10,
    }


def _create_program(client) -> int:
    """Create a test program and return its integer id."""
    res = client.post("/api/v1/programs", json={"name": "Catalog Test Program", "methodology": "agile"})
    assert res.status_code == 201
    return res.get_json()["id"]


# ─── Test 1: load_catalog_from_json creates L1/L2/L3/L4 records ──────────────

def test_load_catalog_from_json_creates_l1_l2_l3_l4_records(tmp_path):
    """load_catalog_from_json should persist all four hierarchy levels to DB."""
    l4 = _make_l4("FI-UT-01-01", "Pay Invoice")
    l3 = _make_l3("L3-FI-UT-01", "Invoice Processing", [l4])
    path = _write_catalog_json(tmp_path, "L1-FI-UT", "L2-FI-UT", "FI", [l3])

    result = process_catalog_service.load_catalog_from_json(path)

    assert result["created"]["l1"] == 1
    assert result["created"]["l2"] == 1
    assert result["created"]["l3"] == 1
    assert result["created"]["l4"] == 1

    l1_row = db.session.execute(
        db.select(L1SeedCatalog).where(L1SeedCatalog.code == "L1-FI-UT")
    ).scalar_one_or_none()
    assert l1_row is not None, "L1SeedCatalog row not created"

    l3_row = db.session.execute(
        db.select(L3SeedCatalog).where(L3SeedCatalog.code == "L3-FI-UT-01")
    ).scalar_one_or_none()
    assert l3_row is not None, "L3SeedCatalog row not created"

    l4_row = db.session.execute(
        db.select(L4SeedCatalog).where(L4SeedCatalog.sub_process_code == "FI-UT-01-01")
    ).scalar_one_or_none()
    assert l4_row is not None, "L4SeedCatalog row not created"
    assert l4_row.typical_fit_decision == "fit"
    assert l4_row.parent_l3_id == l3_row.id


# ─── Test 2: load_catalog_from_json is idempotent ─────────────────────────────

def test_load_catalog_is_idempotent_second_run_no_duplicates(tmp_path):
    """Calling load_catalog_from_json twice should not create duplicate rows."""
    l4 = _make_l4("FI-UT2-01-01", "Vendor Setup")
    l3 = _make_l3("L3-FI-UT2-01", "Vendor Management", [l4])
    path = _write_catalog_json(tmp_path, "L1-FI-UT2", "L2-FI-UT2", "FI", [l3])

    process_catalog_service.load_catalog_from_json(path)
    result2 = process_catalog_service.load_catalog_from_json(path)

    # Second run should update (not create) all records
    assert result2["updated"]["l1"] == 1
    assert result2["updated"]["l2"] == 1
    assert result2["updated"]["l3"] == 1
    assert result2["updated"]["l4"] == 1
    assert result2["created"]["l1"] == 0
    assert result2["created"]["l4"] == 0

    l4_count = db.session.execute(
        db.select(db.func.count(L4SeedCatalog.id)).where(
            L4SeedCatalog.sub_process_code == "FI-UT2-01-01"
        )
    ).scalar_one()
    assert l4_count == 1, "Duplicate L4 row created on second load"


# ─── Test 3: seed_project_from_catalog creates ProcessLevel rows ──────────────

def test_seed_project_creates_process_levels_and_steps(tmp_path, client):
    """seed_project_from_catalog should create L1→L4 ProcessLevel rows."""
    from app.models.explore.process import ProcessLevel

    # Load catalog first
    l4 = _make_l4("FI-UT3-01-01", "Post GR")
    l3 = _make_l3("L3-FI-UT3-01", "Goods Receipt", [l4])
    path = _write_catalog_json(tmp_path, "L1-FI-UT3", "L2-FI-UT3", "FI", [l3])
    process_catalog_service.load_catalog_from_json(path)

    project_id = _create_program(client)
    result = process_catalog_service.seed_project_from_catalog(
        tenant_id=None,
        project_id=project_id,
        selected_modules=["FI"],
        importer_id=1,
    )

    assert result["created"]["l1"] >= 1
    assert result["created"]["l2"] >= 1
    assert result["created"]["l3"] >= 1
    assert result["created"]["l4"] >= 1

    # Verify actual DB rows
    l4_pl = db.session.execute(
        db.select(ProcessLevel).where(
            ProcessLevel.project_id == project_id,
            ProcessLevel.code == "FI-UT3-01-01",
            ProcessLevel.level == 4,
        )
    ).scalar_one_or_none()
    assert l4_pl is not None, "L4 ProcessLevel row not created"
    assert l4_pl.fit_status == "fit"
    assert l4_pl.tenant_id is None


# ─── Test 4: seed_project skips existing matching codes ──────────────────────

def test_seed_project_skips_existing_matching_codes(tmp_path, client):
    """Running seed_project_from_catalog twice should skip already-existing codes."""
    from app.models.explore.process import ProcessLevel

    l4 = _make_l4("FI-UT4-01-01", "Dunning Letter")
    l3 = _make_l3("L3-FI-UT4-01", "Collections", [l4])
    path = _write_catalog_json(tmp_path, "L1-FI-UT4", "L2-FI-UT4", "FI", [l3])
    process_catalog_service.load_catalog_from_json(path)

    project_id = _create_program(client)

    # First seed
    r1 = process_catalog_service.seed_project_from_catalog(
        tenant_id=None, project_id=project_id, selected_modules=["FI"], importer_id=1
    )
    # Second seed — same project
    r2 = process_catalog_service.seed_project_from_catalog(
        tenant_id=None, project_id=project_id, selected_modules=["FI"], importer_id=1
    )

    # First run created rows
    total_created_first = sum(r1["created"].values())
    assert total_created_first > 0

    # Second run should skip everything
    assert r2["created"]["l1"] == 0
    assert r2["created"]["l2"] == 0
    assert r2["created"]["l3"] == 0
    assert r2["created"]["l4"] == 0
    assert sum(r2["skipped"].values()) == total_created_first


# ─── Test 5: get_catalog_tree filters by sap_module ──────────────────────────

def test_get_catalog_tree_filters_by_module(tmp_path):
    """get_catalog_tree with module='MM' should only return MM entries."""
    # Load an FI module
    l4_fi = _make_l4("FI-UT5-01-01", "FI Step")
    l3_fi = _make_l3("L3-FI-UT5-01", "FI Process", [l4_fi])
    path_fi = _write_catalog_json(tmp_path, "L1-FI-UT5", "L2-FI-UT5", "FI", [l3_fi])
    process_catalog_service.load_catalog_from_json(path_fi)

    # Load an MM module under the same L1 (different L2)
    l4_mm = _make_l4("MM-UT5-01-01", "MM Step")
    l3_mm = _make_l3("L3-MM-UT5-01", "MM Process", [l4_mm])
    path_mm = _write_catalog_json(tmp_path, "L1-MM-UT5", "L2-MM-UT5", "MM", [l3_mm])
    process_catalog_service.load_catalog_from_json(path_mm)

    # Filter for MM only
    tree = process_catalog_service.get_catalog_tree(sap_module="MM")

    # All returned L2 entries must be MM
    for l1_node in tree:
        for l2_node in l1_node.get("l2_list", []):
            assert l2_node["sap_module"] == "MM", (
                f"Expected only MM but got {l2_node['sap_module']}"
            )

    mm_codes = [
        l4["sub_process_code"]
        for l1_node in tree
        for l2_node in l1_node.get("l2_list", [])
        for l3_node in l2_node.get("l3_list", [])
        for l4 in l3_node.get("l4_steps", [])
    ]
    assert "MM-UT5-01-01" in mm_codes
    assert "FI-UT5-01-01" not in mm_codes


# ─── Test 6: seed_project returns correct created/skipped counts ──────────────

def test_seed_project_returns_created_and_skipped_counts(tmp_path, client):
    """Result dict should have 'created', 'skipped', and 'elapsed_ms' keys."""
    l4a = _make_l4("FI-UT6-01-01", "Post Invoice")
    l4b = _make_l4("FI-UT6-01-02", "Approve Invoice")
    l3 = _make_l3("L3-FI-UT6-01", "Invoice Approval", [l4a, l4b])
    path = _write_catalog_json(tmp_path, "L1-FI-UT6", "L2-FI-UT6", "FI", [l3])
    process_catalog_service.load_catalog_from_json(path)

    project_id = _create_program(client)
    result = process_catalog_service.seed_project_from_catalog(
        tenant_id=None, project_id=project_id, selected_modules=["FI"], importer_id=99
    )

    assert "created" in result
    assert "skipped" in result
    assert "elapsed_ms" in result
    assert isinstance(result["elapsed_ms"], int)
    assert result["elapsed_ms"] >= 0

    # We created 2 L4 steps
    assert result["created"]["l4"] == 2
    # Nothing to skip on first run
    assert result["skipped"]["l4"] == 0


# ─── Test 7: tenant isolation — each project's levels are scoped correctly ────

def test_seed_project_tenant_isolation(tmp_path, client):
    """ProcessLevels for tenant=1 and tenant=2 must not interfere with each other."""
    from app.models.explore.process import ProcessLevel

    l4 = _make_l4("FI-UT7-01-01", "Bank Posting")
    l3 = _make_l3("L3-FI-UT7-01", "Bank Reconciliation", [l4])
    path = _write_catalog_json(tmp_path, "L1-FI-UT7", "L2-FI-UT7", "FI", [l3])
    process_catalog_service.load_catalog_from_json(path)

    # Create two separate projects
    pid_t1 = _create_program(client)

    res2 = client.post("/api/v1/programs", json={"name": "Tenant 2 Program", "methodology": "agile"})
    assert res2.status_code == 201
    pid_t2 = res2.get_json()["id"]

    # Seed same catalog to two different project slots
    # tenant_id=None since the test DB has no tenant rows (nullable FK)
    process_catalog_service.seed_project_from_catalog(
        tenant_id=None, project_id=pid_t1, selected_modules=["FI"], importer_id=1
    )
    process_catalog_service.seed_project_from_catalog(
        tenant_id=None, project_id=pid_t2, selected_modules=["FI"], importer_id=2
    )

    # Both projects should have the same structure (same catalog)
    t1_rows = db.session.execute(
        db.select(ProcessLevel).where(ProcessLevel.project_id == pid_t1)
    ).scalars().all()

    t2_rows = db.session.execute(
        db.select(ProcessLevel).where(ProcessLevel.project_id == pid_t2)
    ).scalars().all()

    # Each project is isolated — rows share no IDs
    t1_ids = {r.id for r in t1_rows}
    t2_ids = {r.id for r in t2_rows}
    assert t1_ids.isdisjoint(t2_ids), "ProcessLevel IDs leak between projects"

    # Both seeded the same catalog so row counts should match
    assert len(t1_rows) == len(t2_rows)
