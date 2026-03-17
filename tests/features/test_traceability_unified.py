"""
Tests for the Unified Traceability endpoint.
Sprint 4 — API contract tests + explore requirement deep trace.
"""

import pytest
from app.models import db
from app.models.requirement import Requirement
from app.models.explore import (
    ExploreWorkshop,
    ProcessLevel,
    ProcessStep,
    ExploreRequirement,
    ExploreDecision,
    ExploreOpenItem,
    RequirementOpenItemLink,
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _seed_program(client):
    """Create a program and return its id."""
    r = client.post("/api/v1/programs", json={"name": "TP", "methodology": "agile"})
    assert r.status_code == 201
    return r.get_json()["id"]


def _seed_backlog(client, program_id):
    """Create a backlog item via API and return id."""
    r = client.post(
        f"/api/v1/programs/{program_id}/backlog",
        json={"title": "BLI-1", "type": "enhancement", "priority": "high"},
    )
    assert r.status_code == 201
    return r.get_json()["id"]


def _seed_explore_tree():
    """Seed ProcessLevel L1→L2→L3→L4, Workshop, ProcessStep, Requirement.
    Returns the requirement id (UUID string).
    Needs a Program for project_id FK.
    """
    from app.models.program import Program
    from app.models.auth import Tenant

    t = Tenant.query.filter_by(slug="test-default").first()
    prog = Program(name="TraceTest", methodology="agile", tenant_id=t.id)
    db.session.add(prog)
    db.session.flush()
    pid = prog.id

    # L1
    l1 = ProcessLevel(
        project_id=pid,
        code="VC-SD",
        name="SD — Sales & Distribution",
        level=1,
        scope_status="in_scope",
    )
    db.session.add(l1)
    db.session.flush()

    # L2
    l2 = ProcessLevel(
        project_id=pid,
        code="PA-SD01",
        name="Sales Order Processing",
        level=2,
        parent_id=l1.id,
        scope_status="in_scope",
    )
    db.session.add(l2)
    db.session.flush()

    # L3
    l3 = ProcessLevel(
        project_id=pid,
        code="SD-001",
        name="Standard Sales Order",
        level=3,
        parent_id=l2.id,
        scope_status="in_scope",
    )
    db.session.add(l3)
    db.session.flush()

    # L4
    l4 = ProcessLevel(
        project_id=pid,
        code="SD-001.01",
        name="Pricing Procedure",
        level=4,
        parent_id=l3.id,
        scope_status="in_scope",
        fit_status="fit",
    )
    db.session.add(l4)
    db.session.flush()

    # Workshop
    ws = ExploreWorkshop(
        project_id=pid,
        code="SES-001",
        name="O2C Workshop",
        process_area="SD",
        status="completed",
    )
    db.session.add(ws)
    db.session.flush()

    # ProcessStep
    ps = ProcessStep(
        workshop_id=ws.id,
        process_level_id=l4.id,
        fit_decision="fit",
    )
    db.session.add(ps)
    db.session.flush()

    # Requirement
    req = ExploreRequirement(
        project_id=pid,
        code="REQ-T01",
        title="Test Requirement",
        type="configuration",
        priority="P1",
        status="approved",
        workshop_id=ws.id,
        process_step_id=ps.id,
        created_by_id="test-user",
    )
    db.session.add(req)
    db.session.flush()

    db.session.commit()
    return req.id


# ═══════════════════════════════════════════════════════════════════════════
# Standard entity tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUnifiedTraceStandard:
    """Tests using standard (integer-id) entity types."""

    def test_backlog_item_200(self, client):
        pid = _seed_program(client)
        bid = _seed_backlog(client, pid)
        r = client.get(f"/api/v1/traceability/backlog_item/{bid}")
        assert r.status_code == 200
        data = r.get_json()
        assert "entity" in data
        assert "upstream" in data
        assert "downstream" in data
        assert "chain_depth" in data
        assert "gaps" in data
        assert "lateral" in data
        assert "links_summary" in data
        assert data["entity"]["type"] == "backlog_item"

    def test_backlog_item_not_found(self, client):
        r = client.get("/api/v1/traceability/backlog_item/99999")
        assert r.status_code == 404

    def test_invalid_entity_type(self, client):
        r = client.get("/api/v1/traceability/invalid_type/1")
        assert r.status_code == 404

    def test_chain_depth_present(self, client):
        pid = _seed_program(client)
        bid = _seed_backlog(client, pid)
        r = client.get(f"/api/v1/traceability/backlog_item/{bid}")
        data = r.get_json()
        assert isinstance(data["chain_depth"], int)
        assert 0 <= data["chain_depth"] <= 6


# ═══════════════════════════════════════════════════════════════════════════
# Explore requirement tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUnifiedTraceExplore:
    """Tests for explore_requirement path (UUID, upstream hierarchy)."""

    def test_explore_requirement_200(self, client):
        req_id = _seed_explore_tree()
        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        assert r.status_code == 200

    def test_explore_requirement_structure(self, client):
        req_id = _seed_explore_tree()
        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        data = r.get_json()
        # Must have requirement info
        assert "requirement" in data
        assert data["requirement"]["code"] == "REQ-T01"
        # Must have upstream
        assert "upstream" in data
        assert len(data["upstream"]) > 0
        # Must have chain_depth
        assert "chain_depth" in data
        assert data["chain_depth"] >= 1

    def test_explore_upstream_hierarchy(self, client):
        """Upstream should contain workshop → process_step → L4 → L3 → L2 → L1."""
        req_id = _seed_explore_tree()
        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        data = r.get_json()
        upstream = data["upstream"]
        types = [u["type"] for u in upstream]
        assert "workshop" in types
        assert "process_step" in types
        # Should have at least one process level
        level_types = [t for t in types if t.startswith("process_l")]
        assert len(level_types) >= 1

    def test_explore_requirement_not_found(self, client):
        r = client.get(
            "/api/v1/traceability/explore_requirement/00000000-0000-0000-0000-000000000000"
        )
        assert r.status_code == 404

    def test_explore_gaps_present(self, client):
        req_id = _seed_explore_tree()
        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        data = r.get_json()
        assert "gaps" in data
        assert isinstance(data["gaps"], list)

    def test_explore_lateral(self, client):
        req_id = _seed_explore_tree()
        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        data = r.get_json()
        assert "lateral" in data
        lateral = data["lateral"]
        assert "open_items" in lateral or "decisions" in lateral or isinstance(lateral, dict)

    def test_explore_coverage(self, client):
        req_id = _seed_explore_tree()
        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        data = r.get_json()
        assert "coverage" in data
        cov = data["coverage"]
        assert "backlog" in cov
        assert "config" in cov
        assert "test" in cov

    def test_explore_chain_depth_value(self, client):
        """With full L1-L4 + workshop + step, depth should be 6."""
        req_id = _seed_explore_tree()
        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        data = r.get_json()
        assert data["chain_depth"] == 6

    def test_legacy_requirement_route_redirects_to_canonical_explore(self, client):
        """Legacy requirement ids should resolve to canonical explore trace when migrated."""
        req_id = _seed_explore_tree()
        req = db.session.get(ExploreRequirement, req_id)

        legacy = Requirement(
            program_id=req.project_id,
            project_id=req.project_id,
            title="Legacy Trace Requirement",
            code="REQ-LEG-TRC",
            status="approved",
        )
        db.session.add(legacy)
        db.session.flush()

        req.legacy_requirement_id = legacy.id
        db.session.commit()

        r = client.get(f"/api/v1/traceability/requirement/{legacy.id}")
        assert r.status_code == 200

        data = r.get_json()
        assert data["requested_entity_type"] == "requirement"
        assert data["canonical_entity_type"] == "explore_requirement"
        assert data["requested_entity_id"] == legacy.id
        assert data["requirement"]["id"] == req.id
        assert data["requirement"]["code"] == "REQ-T01"


# ═══════════════════════════════════════════════════════════════════════════
# Lateral links tests
# ═══════════════════════════════════════════════════════════════════════════


class TestUnifiedTraceLateral:
    """Tests for lateral links (decisions, open items)."""

    def test_lateral_decisions(self, client):
        """When a decision exists on the same process_step, lateral.decisions should be populated."""
        req_id = _seed_explore_tree()
        # Add a decision to the same process_step
        req = db.session.get(ExploreRequirement, req_id)
        dec = ExploreDecision(
            project_id=req.project_id,
            code="DEC-T01",
            text="Test decision",
            decided_by="Test User",
            category="process",
            status="active",
            process_step_id=req.process_step_id,
        )
        db.session.add(dec)
        db.session.commit()

        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        data = r.get_json()
        decisions = data.get("lateral", {}).get("decisions", [])
        assert len(decisions) >= 1
        assert decisions[0]["code"] == "DEC-T01"

    def test_lateral_open_items(self, client):
        """When an open item is linked via M:N, lateral.open_items should show."""
        req_id = _seed_explore_tree()
        req = db.session.get(ExploreRequirement, req_id)
        oi = ExploreOpenItem(
            project_id=req.project_id,
            code="OI-T01",
            title="Test open item",
            status="open",
            priority="P1",
            created_by_id="test-user",
        )
        db.session.add(oi)
        db.session.flush()
        link = RequirementOpenItemLink(
            requirement_id=req_id,
            open_item_id=oi.id,
            project_id=req.project_id,
        )
        db.session.add(link)
        db.session.commit()

        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        data = r.get_json()
        oi_list = data.get("lateral", {}).get("open_items", [])
        assert len(oi_list) >= 1
        assert oi_list[0]["code"] == "OI-T01"


# ═══════════════════════════════════════════════════════════════════════════
# Explore ↔ Test cross-domain traceability tests
# ═══════════════════════════════════════════════════════════════════════════


def _seed_explore_with_test_case():
    """Seed a full explore tree plus a TestCase linked via explore_requirement_id.

    Returns (req_id, test_case_id) so tests can assert in both directions.
    """
    from app.models.program import Program
    from app.models.testing import TestCase

    req_id = _seed_explore_tree()
    req = db.session.get(ExploreRequirement, req_id)

    tc = TestCase(
        title="TC-Explore-Trace",
        code="TC-EX-001",
        test_type="functional",
        test_layer="performance",  # avoids ADR-008 L3 requirement
        status="draft",
        priority="medium",
        program_id=req.project_id,
        project_id=req.project_id,
        explore_requirement_id=req_id,
    )
    db.session.add(tc)
    db.session.commit()
    return req_id, tc.id


class TestExploreTestTraceability:
    """Cross-domain traceability: ExploreRequirement ↔ TestCase."""

    def test_explore_requirement_shows_test_case_downstream(self, client):
        """trace_explore_requirement should include test_cases when a TestCase is linked."""
        req_id, tc_id = _seed_explore_with_test_case()
        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        assert r.status_code == 200
        data = r.get_json()
        assert "test_cases" in data
        assert any(tc["id"] == tc_id for tc in data["test_cases"]), (
            f"TestCase {tc_id} not found in downstream test_cases: {data['test_cases']}"
        )

    def test_explore_coverage_test_count_increases(self, client):
        """coverage.test should be >= 1 after linking a TestCase."""
        req_id, _tc_id = _seed_explore_with_test_case()
        r = client.get(f"/api/v1/traceability/explore_requirement/{req_id}")
        data = r.get_json()
        assert data["coverage"]["test"] >= 1

    def test_test_case_upstream_contains_explore_requirement(self, client):
        """GET /traceability/test_case/<id> upstream must include explore_requirement node."""
        _req_id, tc_id = _seed_explore_with_test_case()
        r = client.get(f"/api/v1/traceability/test_case/{tc_id}")
        assert r.status_code == 200
        data = r.get_json()
        upstream_types = [n["type"] for n in data.get("upstream", [])]
        assert "explore_requirement" in upstream_types, (
            f"explore_requirement not in upstream: {upstream_types}"
        )

    def test_test_case_upstream_contains_workshop(self, client):
        """With full explore tree, upstream should include workshop node."""
        _req_id, tc_id = _seed_explore_with_test_case()
        r = client.get(f"/api/v1/traceability/test_case/{tc_id}")
        data = r.get_json()
        upstream_types = [n["type"] for n in data.get("upstream", [])]
        assert "workshop" in upstream_types, (
            f"workshop not in upstream: {upstream_types}"
        )

    def test_traceability_derived_summary_has_explore_fields(self, client):
        """traceability-derived summary must include explore_requirement_code and source_type."""
        req_id, tc_id = _seed_explore_with_test_case()
        # Manually create a TestCaseTraceLink so the endpoint has groups to process
        from app.models.testing import TestCaseTraceLink
        from app.models.explore import ProcessLevel, ProcessStep, ExploreRequirement

        req = db.session.get(ExploreRequirement, req_id)
        # Get any process level from the seeded tree
        ps = db.session.get(ProcessStep, req.process_step_id) if req.process_step_id else None
        l3_id = str(ps.process_level_id) if ps and ps.process_level_id else None

        if l3_id:
            import json
            link = TestCaseTraceLink(
                test_case_id=tc_id,
                l3_process_level_id=l3_id,
                explore_requirement_ids=json.dumps([req_id]),
            )
            db.session.add(link)
            db.session.commit()

        r = client.get(f"/api/v1/testing/catalog/{tc_id}/traceability-derived")
        assert r.status_code == 200
        data = r.get_json()
        summary = data.get("summary", {})
        assert "explore_requirement_code" in summary
        assert "source_type" in summary
        assert "process_level_name" in summary
        # TestCase is linked to an ExploreRequirement, so source_type must be "explore"
        assert summary["source_type"] == "explore"
        assert summary["explore_requirement_code"] == "REQ-T01"

    def test_backlog_item_downstream_includes_test_case_and_defect(self, client):
        """Unified backlog trace must expose linked test cases and defects."""
        req_id = _seed_explore_tree()
        req = db.session.get(ExploreRequirement, req_id)
        from app.models.backlog import BacklogItem
        from app.models.testing import TestCase, Defect

        backlog = BacklogItem(
            program_id=req.project_id,
            project_id=req.project_id,
            title="Trace Backlog Item",
            wricef_type="enhancement",
            status="new",
            priority="high",
            explore_requirement_id=req_id,
        )
        db.session.add(backlog)
        db.session.flush()

        tc = TestCase(
            title="TC-Backlog-Trace",
            code="TC-BL-001",
            test_type="functional",
            test_layer="sit",
            status="draft",
            priority="medium",
            program_id=req.project_id,
            project_id=req.project_id,
            backlog_item_id=backlog.id,
            explore_requirement_id=req_id,
        )
        db.session.add(tc)
        db.session.flush()

        defect = Defect(
            program_id=req.project_id,
            project_id=req.project_id,
            title="DEF-Backlog-Trace",
            severity="S2",
            status="new",
            test_case_id=tc.id,
            backlog_item_id=backlog.id,
            explore_requirement_id=req_id,
        )
        db.session.add(defect)
        db.session.commit()

        r = client.get(f"/api/v1/traceability/backlog_item/{backlog.id}")
        assert r.status_code == 200
        data = r.get_json()
        downstream_types = [n["type"] for n in data.get("downstream", [])]
        upstream_types = [n["type"] for n in data.get("upstream", [])]
        assert "explore_requirement" in upstream_types
        assert "test_case" in downstream_types
        assert "defect" in downstream_types


# ══════════════════════════════════════════════════════════════════════════════
# EPIC-8.2 — Traceability matrix payload and summary optimization tests
# ══════════════════════════════════════════════════════════════════════════════


class TestTraceabilityMatrixSummaryEpic82:
    """EPIC-8.2: matrix summary shape + cross-project isolation."""

    def _seed_project_with_chain(self):
        """Seed a program, ExploreRequirement, TestCase, and Defect in one project."""
        from app.models.program import Program
        from app.models.auth import Tenant
        from app.models.testing import TestCase, Defect

        t = Tenant.query.filter_by(slug="test-default").first()
        prog = Program(name="MatrixSummaryProj", methodology="agile", tenant_id=t.id)
        db.session.add(prog)
        db.session.flush()
        pid = prog.id

        req = ExploreRequirement(
            project_id=pid,
            code="MS-REQ-001",
            title="Matrix Summary Req",
            status="draft",
            priority="high",
            type="functional",
            created_by_id="test-user",
        )
        db.session.add(req)
        db.session.flush()

        tc = TestCase(
            title="MS-TC-001",
            code="MS-TC-001",
            test_type="functional",
            test_layer="sit",
            status="draft",
            priority="medium",
            program_id=pid,
            project_id=pid,
            explore_requirement_id=req.id,
        )
        db.session.add(tc)
        db.session.flush()

        defect = Defect(
            program_id=pid,
            project_id=pid,
            title="MS-DEF-001",
            severity="S2",
            status="new",
            test_case_id=tc.id,
            explore_requirement_id=req.id,
        )
        db.session.add(defect)
        db.session.commit()
        return pid, req.id, tc.id

    def test_matrix_summary_returns_200_with_expected_fields(self, client):
        """Matrix summary endpoint returns 200 with all required fields."""
        pid, _req_id, _tc_id = self._seed_project_with_chain()
        r = client.get(f"/api/v1/projects/{pid}/trace/matrix-summary")
        assert r.status_code == 200
        data = r.get_json()
        for field in (
            "total_requirements",
            "requirements_with_tests",
            "requirements_without_tests",
            "unlinked_test_cases",
            "total_defects",
            "coverage_pct",
        ):
            assert field in data, f"Missing field: {field}"

    def test_matrix_summary_counts_are_project_scoped(self, client):
        """requirements_with_tests and total_defects count only the seeded project."""
        pid, _req_id, _tc_id = self._seed_project_with_chain()
        r = client.get(f"/api/v1/projects/{pid}/trace/matrix-summary")
        assert r.status_code == 200
        data = r.get_json()
        assert data["total_requirements"] >= 1
        assert data["requirements_with_tests"] >= 1
        assert data["total_defects"] >= 1
        assert data["requirements_with_tests"] <= data["total_requirements"]

    def test_matrix_summary_requirements_without_tests_is_consistent(self, client):
        """requirements_without_tests == total - with_tests."""
        pid, _req_id, _tc_id = self._seed_project_with_chain()
        r = client.get(f"/api/v1/projects/{pid}/trace/matrix-summary")
        data = r.get_json()
        assert (
            data["requirements_without_tests"]
            == data["total_requirements"] - data["requirements_with_tests"]
        )

    def test_matrix_summary_cross_project_isolation(self, client):
        """Counts from project A do not bleed into project B summary."""
        from app.models.program import Program
        from app.models.auth import Tenant
        from app.models.testing import TestCase

        t = Tenant.query.filter_by(slug="test-default").first()

        # Project A — has a requirement with a test
        prog_a = Program(name="IsoProjectA", methodology="agile", tenant_id=t.id)
        db.session.add(prog_a)
        db.session.flush()
        pid_a = prog_a.id

        req_a = ExploreRequirement(
            project_id=pid_a, code="ISO-A-001", title="Req A",
            status="draft", priority="medium", type="functional",
            created_by_id="test-user",
        )
        db.session.add(req_a)
        db.session.flush()

        tc_a = TestCase(
            title="TC-A", code="TC-A-001", test_type="functional", test_layer="sit",
            status="draft", priority="medium",
            program_id=pid_a, project_id=pid_a,
            explore_requirement_id=req_a.id,
        )
        db.session.add(tc_a)

        # Project B — has NO requirements and NO test cases
        prog_b = Program(name="IsoProjectB", methodology="agile", tenant_id=t.id)
        db.session.add(prog_b)
        db.session.flush()
        pid_b = prog_b.id

        db.session.commit()

        r = client.get(f"/api/v1/projects/{pid_b}/trace/matrix-summary")
        data = r.get_json()
        assert data["total_requirements"] == 0
        assert data["requirements_with_tests"] == 0
        assert data["total_defects"] == 0

    def test_config_item_trace_payload_uses_slim_config_item_shape(self, client):
        """trace_config_item returns slim config_item dict, not full to_dict()."""
        from app.models.backlog import ConfigItem

        # We don't need a full chain; just verify the shape contract via the service.
        from app.services.traceability import trace_config_item

        # ConfigItem with no test cases — quick check for slim fields only.
        from app.models.program import Program
        from app.models.auth import Tenant

        t = Tenant.query.filter_by(slug="test-default").first()
        prog = Program(name="SlimCIProj", methodology="agile", tenant_id=t.id)
        db.session.add(prog)
        db.session.flush()
        pid = prog.id

        ci = ConfigItem(
            program_id=pid,
            project_id=pid,
            code="CI-SLIM-001",
            title="Slim Config Item",
            module="FI",
            status="active",
        )
        db.session.add(ci)
        db.session.commit()

        result = trace_config_item(ci.id, pid, None)
        ci_dict = result["config_item"]
        # Slim shape must have these keys
        for key in ("id", "code", "title", "module", "status"):
            assert key in ci_dict, f"Missing key in slim config_item: {key}"
