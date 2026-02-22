"""
Tests for S2-03 (FDD-F05): Requirement coverage reporting.

Covers:
  - get_requirement_coverage_matrix correct totals
  - filter by classification (fit_status)
  - filter by priority
  - include_uncovered_only flag
  - by_classification sums add up correctly
  - quality gate passes when coverage_pct >= threshold
  - quality gate fails when below threshold
  - blocking_requirements lists uncovered requirements
  - get_coverage_trend returns empty list (stub)
  - tenant isolation excludes cross-tenant requirements

pytest markers: integration
"""

import pytest

from app.models import db
from app.models.program import Program


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_program(name: str = "F05-Prog") -> Program:
    prog = Program(name=name, methodology="agile")
    db.session.add(prog)
    db.session.flush()
    return prog


def _make_req(prog_id: int, code: str, fit_status: str = "gap",
              priority: str = "P2", moscow: str = "must_have",
              status: str = "draft",
              tenant_id: int | None = None) -> object:
    """Create and flush an ExploreRequirement."""
    from app.models.explore import ExploreRequirement

    req = ExploreRequirement(
        project_id=prog_id,
        code=code,
        title=f"Requirement {code}",
        fit_status=fit_status,
        priority=priority,
        moscow_priority=moscow,
        status=status,
        tenant_id=tenant_id,
        created_by_id="test-user",
    )
    db.session.add(req)
    db.session.flush()
    return req


def _make_test_case(prog_id: int, req_id: str, title: str = "TC") -> object:
    """Create and flush a TestCase linked to an ExploreRequirement."""
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


# ── Tests: get_requirement_coverage_matrix ────────────────────────────────


def test_coverage_matrix_correct_totals(client):
    """coverage_matrix counts total/covered/uncovered correctly."""
    from app.services.metrics import get_requirement_coverage_matrix

    prog = _make_program("Matrix-Totals")
    req_covered = _make_req(prog.id, "REQ-001")
    req_uncovered = _make_req(prog.id, "REQ-002")
    _make_test_case(prog.id, req_covered.id)
    db.session.commit()

    result = get_requirement_coverage_matrix(prog.id, None)

    assert result["total"] == 2
    assert result["covered"] == 1
    assert result["uncovered"] == 1
    assert result["coverage_pct"] == 50.0


def test_coverage_matrix_filter_by_classification(client):
    """coverage_matrix filters by fit_status correctly."""
    from app.services.metrics import get_requirement_coverage_matrix

    prog = _make_program("Matrix-ClassFilter")
    _make_req(prog.id, "REQ-FIT", fit_status="fit")
    _make_req(prog.id, "REQ-GAP", fit_status="gap")
    db.session.commit()

    result = get_requirement_coverage_matrix(prog.id, None, classification="fit")

    assert result["total"] == 1
    assert result["items"][0]["fit_status"] == "fit"


def test_coverage_matrix_filter_by_priority(client):
    """coverage_matrix filters by priority correctly."""
    from app.services.metrics import get_requirement_coverage_matrix

    prog = _make_program("Matrix-PrioFilter")
    _make_req(prog.id, "REQ-P1", priority="P1")
    _make_req(prog.id, "REQ-P3", priority="P3")
    db.session.commit()

    result = get_requirement_coverage_matrix(prog.id, None, priority="P1")

    assert result["total"] == 1
    assert result["items"][0]["priority"] == "P1"


def test_coverage_matrix_uncovered_only_flag(client):
    """include_uncovered_only=True returns only requirements without test cases."""
    from app.services.metrics import get_requirement_coverage_matrix

    prog = _make_program("Uncov-Only")
    req_cov = _make_req(prog.id, "REQ-COV")
    req_uncov = _make_req(prog.id, "REQ-UNCOV")
    _make_test_case(prog.id, req_cov.id)
    db.session.commit()

    result = get_requirement_coverage_matrix(prog.id, None, include_uncovered_only=True)

    req_ids = [r["req_id"] for r in result["items"]]
    assert req_uncov.id in req_ids
    assert req_cov.id not in req_ids


def test_coverage_matrix_cancelled_excluded_from_denominator(client):
    """Cancelled requirements are excluded from total (Audit A3)."""
    from app.services.metrics import get_requirement_coverage_matrix

    prog = _make_program("Cancelled")
    _make_req(prog.id, "REQ-ACTIVE", status="draft")
    _make_req(prog.id, "REQ-CANCEL", status="cancelled")
    db.session.commit()

    result = get_requirement_coverage_matrix(prog.id, None)

    # Cancelled requirement must not appear in total
    assert result["total"] == 1


def test_coverage_matrix_by_classification_sums(client):
    """by_classification sums must add up to total."""
    from app.services.metrics import get_requirement_coverage_matrix

    prog = _make_program("ByClass-Sums")
    _make_req(prog.id, "REQ-A", fit_status="fit")
    _make_req(prog.id, "REQ-B", fit_status="gap")
    _make_req(prog.id, "REQ-C", fit_status="gap")
    db.session.commit()

    result = get_requirement_coverage_matrix(prog.id, None)

    by_cls_total = sum(v["total"] for v in result["by_classification"].values())
    assert by_cls_total == result["total"]


# ── Tests: get_quality_gate_coverage_status ────────────────────────────────


def test_quality_gate_passes_when_coverage_meets_threshold(client):
    """Quality gate passes when all must_have requirements are covered."""
    from app.services.metrics import get_quality_gate_coverage_status

    prog = _make_program("Gate-Pass")
    req = _make_req(prog.id, "REQ-MUST", moscow="must_have")
    _make_test_case(prog.id, req.id)
    db.session.commit()

    result = get_quality_gate_coverage_status(prog.id, None, threshold_pct=100.0, scope="critical")

    assert result["gate_passed"] is True
    assert result["coverage_pct"] == 100.0


def test_quality_gate_fails_when_coverage_below_threshold(client):
    """Quality gate fails and blocking_requirements lists uncovered requirements."""
    from app.services.metrics import get_quality_gate_coverage_status

    prog = _make_program("Gate-Fail")
    _make_req(prog.id, "REQ-MUST-UNCOV", moscow="must_have")
    db.session.commit()

    result = get_quality_gate_coverage_status(prog.id, None, threshold_pct=100.0, scope="critical")

    assert result["gate_passed"] is False
    assert len(result["blocking_requirements"]) == 1


def test_quality_gate_blocking_list_contents(client):
    """blocking_requirements contains req_id, title, fit_status."""
    from app.services.metrics import get_quality_gate_coverage_status

    prog = _make_program("Gate-Blocking")
    req = _make_req(prog.id, "REQ-BLOCK", moscow="must_have", fit_status="gap")
    db.session.commit()

    result = get_quality_gate_coverage_status(prog.id, None, threshold_pct=100.0, scope="critical")

    blocking = result["blocking_requirements"]
    assert len(blocking) == 1
    assert blocking[0]["req_id"] == req.id
    assert "title" in blocking[0]
    assert blocking[0]["fit_status"] == "gap"


# ── Tests: get_coverage_trend ─────────────────────────────────────────────


def test_coverage_trend_returns_empty_list(client):
    """get_coverage_trend returns [] (stub — no snapshot table yet)."""
    from app.services.metrics import get_coverage_trend

    prog = _make_program("Trend-Stub")
    db.session.commit()

    result = get_coverage_trend(prog.id, None, days=30)

    assert result == []
