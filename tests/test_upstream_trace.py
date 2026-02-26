"""
Tests for S2-02 (FDD-F02): Upstream defect trace.

Covers:
  - trace_upstream_from_defect returns full chain when all links exist
  - broken chain is handled gracefully (null nodes, not 500)
  - wrong project raises ValueError → 404
  - process chain walks hierarchy L4→L1
  - trace_defects_by_process returns defects under a process level
  - filter by process level traverses child levels too
  - is_critical_path populated from L4 fit_status='gap'
  - explore_requirement appears in linked_artifacts
  - tenant isolation: defect from another tenant not found

pytest markers: integration
"""

import pytest

from app.models import db
from app.models.program import Program


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_program(name: str = "F02-Prog") -> Program:
    from app.models.auth import Tenant
    t = Tenant.query.filter_by(slug="test-default").first()
    prog = Program(name=name, methodology="agile", tenant_id=t.id)
    db.session.add(prog)
    db.session.flush()
    return prog


def _make_process_chain(prog_id: int) -> tuple:
    """Create L1→L2→L3→L4 ProcessLevel chain. Return (l1, l2, l3, l4)."""
    from app.models.explore import ProcessLevel

    l1 = ProcessLevel(project_id=prog_id, level=1, code="VC-01", name="Finance", scope_status="in_scope")
    db.session.add(l1)
    db.session.flush()

    l2 = ProcessLevel(project_id=prog_id, level=2, code="PA-FI", name="Accounts Payable",
                      parent_id=l1.id, scope_status="in_scope")
    db.session.add(l2)
    db.session.flush()

    l3 = ProcessLevel(project_id=prog_id, level=3, code="E2E-AP", name="Invoice Processing",
                      parent_id=l2.id, scope_status="in_scope")
    db.session.add(l3)
    db.session.flush()

    l4 = ProcessLevel(project_id=prog_id, level=4, code="L4-INV", name="Invoice Verification",
                      parent_id=l3.id, scope_status="in_scope", fit_status="gap")
    db.session.add(l4)
    db.session.flush()

    return l1, l2, l3, l4


def _make_explore_req(prog_id: int, process_level_id: str, code: str = "REQ-001") -> object:
    from app.models.explore import ExploreRequirement

    req = ExploreRequirement(
        project_id=prog_id,
        code=code,
        title=f"Requirement {code}",
        fit_status="gap",
        process_level_id=process_level_id,
        tenant_id=None,
        created_by_id="test-user",
    )
    db.session.add(req)
    db.session.flush()
    return req


def _make_test_case(prog_id: int, req_id: str | None = None, title: str = "TC-001") -> object:
    from app.models.testing import TestCase

    tc = TestCase(
        program_id=prog_id,
        title=title,
        status="not_run",
        explore_requirement_id=req_id,
        tenant_id=None,
    )
    db.session.add(tc)
    db.session.flush()
    return tc


def _make_defect(prog_id: int, tc_id: int | None, req_id: str | None = None,
                 title: str = "DEF-001") -> object:
    from app.models.testing import Defect

    d = Defect(
        program_id=prog_id,
        title=title,
        status="new",
        test_case_id=tc_id,
        explore_requirement_id=req_id,
        tenant_id=None,
    )
    db.session.add(d)
    db.session.flush()
    return d


# ── Tests: trace_upstream_from_defect ─────────────────────────────────────


def test_upstream_trace_returns_full_chain(client):
    """Full chain Defect→TestCase→ExploreReq→ProcessLevel is returned."""
    from app.services.traceability import trace_upstream_from_defect

    prog = _make_program("Full-Chain")
    l1, l2, l3, l4 = _make_process_chain(prog.id)
    req = _make_explore_req(prog.id, l4.id)
    tc = _make_test_case(prog.id, req.id)
    defect = _make_defect(prog.id, tc.id)
    db.session.commit()

    result = trace_upstream_from_defect(defect.id, prog.id, None)

    assert result["defect"]["id"] == defect.id
    assert result["test_case"]["id"] == tc.id
    assert result["explore_requirement"]["id"] == req.id
    # Process chain should contain the levels in ascending order
    levels = [c["level"] for c in result["process_chain"]]
    assert sorted(levels) == levels  # ascending


def test_upstream_trace_process_chain_has_4_levels(client):
    """Process chain includes L1 through L4 when full hierarchy exists."""
    from app.services.traceability import trace_upstream_from_defect

    prog = _make_program("4-Level")
    l1, l2, l3, l4 = _make_process_chain(prog.id)
    req = _make_explore_req(prog.id, l4.id, code="REQ-002")
    tc = _make_test_case(prog.id, req.id)
    defect = _make_defect(prog.id, tc.id)
    db.session.commit()

    result = trace_upstream_from_defect(defect.id, prog.id, None)

    assert len(result["process_chain"]) == 4
    assert result["process_chain"][0]["level"] == 1
    assert result["process_chain"][3]["level"] == 4


def test_upstream_trace_broken_chain_no_test_case(client):
    """Defect without test_case_id returns null test_case — no 500."""
    from app.services.traceability import trace_upstream_from_defect

    prog = _make_program("Broken-TC")
    defect = _make_defect(prog.id, tc_id=None, title="Orphan Defect")
    db.session.commit()

    result = trace_upstream_from_defect(defect.id, prog.id, None)

    assert result["defect"]["id"] == defect.id
    assert result["test_case"] is None
    assert result["explore_requirement"] is None


def test_upstream_trace_raises_for_wrong_project(client):
    """Defect from another project raises ValueError → results in 404."""
    from app.services.traceability import trace_upstream_from_defect

    prog_a = _make_program("Proj-A")
    prog_b = _make_program("Proj-B")
    defect = _make_defect(prog_b.id, tc_id=None, title="Wrong-Proj Defect")
    db.session.commit()

    with pytest.raises(ValueError):
        trace_upstream_from_defect(defect.id, prog_a.id, None)


def test_upstream_trace_is_critical_path_true_for_gap_l4(client):
    """is_critical_path is True when L4 process node has fit_status='gap'."""
    from app.services.traceability import trace_upstream_from_defect

    prog = _make_program("Critical-Path")
    l1, l2, l3, l4 = _make_process_chain(prog.id)  # l4.fit_status='gap'
    req = _make_explore_req(prog.id, l4.id, code="REQ-CRIT")
    tc = _make_test_case(prog.id, req.id)
    defect = _make_defect(prog.id, tc.id)
    db.session.commit()

    result = trace_upstream_from_defect(defect.id, prog.id, None)

    assert result["impact_summary"]["is_critical_path"] is True


def test_upstream_trace_explore_req_in_linked_artifacts(client):
    """ExploreRequirement is included in linked_artifacts list."""
    from app.services.traceability import trace_upstream_from_defect

    prog = _make_program("Artifacts-Test")
    req = _make_explore_req(prog.id, process_level_id=None, code="REQ-ART")
    tc = _make_test_case(prog.id, req.id)
    defect = _make_defect(prog.id, tc.id)
    db.session.commit()

    result = trace_upstream_from_defect(defect.id, prog.id, None)

    artifact_types = [a["type"] for a in result["linked_artifacts"]]
    assert "explore_requirement" in artifact_types


# ── Tests: trace_defects_by_process ────────────────────────────────────────


def test_defects_by_process_returns_defects_under_level(client):
    """trace_defects_by_process returns defects for requirements under L3."""
    from app.services.traceability import trace_defects_by_process

    prog = _make_program("ByProcess-Test")
    l1, l2, l3, l4 = _make_process_chain(prog.id)
    req = _make_explore_req(prog.id, l4.id, code="REQ-BP1")
    tc = _make_test_case(prog.id, req.id)
    defect = _make_defect(prog.id, tc.id)
    db.session.commit()

    # Query by L3 — should find the defect via L4 child
    results = trace_defects_by_process(prog.id, None, l3.id)

    assert any(r["defect_id"] == defect.id for r in results)


def test_defects_by_process_returns_empty_when_no_reqs(client):
    """trace_defects_by_process returns [] when process level has no requirements."""
    from app.services.traceability import trace_defects_by_process

    prog = _make_program("Empty-Process")
    l1, l2, l3, l4 = _make_process_chain(prog.id)
    db.session.commit()

    results = trace_defects_by_process(prog.id, None, l3.id)
    assert results == []


# ── Tests: tenant isolation ───────────────────────────────────────────────


def test_upstream_trace_tenant_isolation(client):
    """Defect with tenant_id=None is not found when queried as tenant_id=1.

    Isolation rule: filter_by(tenant_id=1) must never match a row stored
    with tenant_id=None.  We avoid FK violations by using NULL on the row
    and relying on strict equality in the service filter.
    """
    from app.models.testing import Defect
    from app.services.traceability import trace_upstream_from_defect

    prog = _make_program("Tenant-Iso")
    defect = Defect(
        program_id=prog.id,
        title="Untenanted Defect",
        status="new",
        tenant_id=None,  # no tenant — must NOT be visible when querying as tenant_id=1
    )
    db.session.add(defect)
    db.session.commit()

    with pytest.raises(ValueError):
        trace_upstream_from_defect(defect.id, prog.id, 1)
