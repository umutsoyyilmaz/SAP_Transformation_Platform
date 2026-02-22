"""Bölüm 5 — explore_service.py tenant isolation tests.

Covers the P0 security gap in explore_service.py where 21 functions
accept arbitrary resource IDs without verifying the caller owns the
parent project.

A caller who knows a UUID from another project can:
  1. READ that project's open items, attachments, SCRs, workshop data.
  2. WRITE decisions, open items, and requirements to foreign process steps.
  3. MODIFY open items, process steps, and attachments of other projects.

Tests marked @pytest.mark.xfail document DESIRED post-fix behavior:
  - Fail today (TypeError — no project_id param in service signatures)
  - Turn GREEN once project_id parameter + ownership check is added.

Happy-path tests run without xfail and must pass both before and after.

Services under test:
  - explore_service.get_open_item_service
  - explore_service.update_open_item_service
  - explore_service.transition_open_item_service
  - explore_service.reassign_open_item_service
  - explore_service.add_open_item_comment_service
  - explore_service.update_process_step_service
  - explore_service.create_decision_service
  - explore_service.create_step_open_item_service
  - explore_service.create_step_requirement_service
  - explore_service.create_cross_module_flag_service
  - explore_service.update_cross_module_flag_service
  - explore_service.list_fit_decisions_service
  - explore_service.set_fit_decision_bulk_service
  - explore_service.get_workshop_dependencies_service
  - explore_service.create_workshop_dependency_service
  - explore_service.resolve_workshop_dependency_service
  - explore_service.get_attachment_service
  - explore_service.delete_attachment_service
  - explore_service.get_scope_change_request_service
  - explore_service.transition_scope_change_request_service
  - explore_service.implement_scope_change_request_service
"""

from datetime import date, time

import pytest

from app.models import db
from app.models.explore import (
    Attachment,
    CrossModuleFlag,
    ExploreOpenItem,
    ExploreWorkshop,
    ProcessLevel,
    ProcessStep,
    ScopeChangeRequest,
    WorkshopDependency,
    _uuid,
    _utcnow,
)
from app.models.program import Program
from app.services import explore_service


# ── Factory helpers ───────────────────────────────────────────────────────────


def _make_program(name: str) -> Program:
    prog = Program(name=name, status="active", methodology="agile")
    db.session.add(prog)
    db.session.flush()
    return prog


def _make_workshop(project_id: int, code: str, **kw) -> ExploreWorkshop:
    defaults = dict(
        project_id=project_id,
        code=code,
        name=f"Workshop {code}",
        type="fit_to_standard",
        status="draft",
        date=date(2026, 3, 1),
        start_time=time(9, 0),
        end_time=time(12, 0),
        process_area="FI",
        wave=1,
        session_number=1,
        total_sessions=1,
    )
    defaults.update(kw)
    ws = ExploreWorkshop(**defaults)
    db.session.add(ws)
    db.session.flush()
    return ws


def _make_process_level(project_id: int, code: str) -> ProcessLevel:
    """Create a minimal L4 ProcessLevel (level number is advisory, not enforced)."""
    pl = ProcessLevel(
        project_id=project_id,
        level=4,
        code=code,
        name=f"Test Process {code}",
        sort_order=1,
        scope_status="in_scope",
        fit_status="pending",
        scope_item_code="TST",
    )
    db.session.add(pl)
    db.session.flush()
    return pl


def _make_process_step(workshop_id: str, process_level_id: str, **kw) -> ProcessStep:
    defaults = dict(
        workshop_id=workshop_id,
        process_level_id=process_level_id,
        sort_order=1,
    )
    defaults.update(kw)
    step = ProcessStep(**defaults)
    db.session.add(step)
    db.session.flush()
    return step


def _make_open_item(project_id: int, workshop_id: str, **kw) -> ExploreOpenItem:
    defaults = dict(
        project_id=project_id,
        workshop_id=workshop_id,
        code=f"OI-{_uuid()[:8].upper()}",
        title="Test Open Item",
        status="open",
        priority="P2",
        category="configuration",
        process_area="FI",
        wave=1,
        created_by_id="system",
    )
    defaults.update(kw)
    oi = ExploreOpenItem(**defaults)
    db.session.add(oi)
    db.session.flush()
    return oi


def _make_attachment(project_id: int, entity_id: str, entity_type: str = "workshop") -> Attachment:
    att = Attachment(
        id=_uuid(),
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        file_name="test.pdf",
        file_path="/uploads/test.pdf",
        category="general",
        uploaded_by="system",
        created_at=_utcnow(),
    )
    db.session.add(att)
    db.session.flush()
    return att


def _make_scope_change_request(project_id: int, code: str) -> ScopeChangeRequest:
    scr = ScopeChangeRequest(
        id=_uuid(),
        project_id=project_id,
        code=code,
        change_type="add_to_scope",
        justification="Test justification",
        requested_by="system",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.session.add(scr)
    db.session.flush()
    return scr


def _make_workshop_dependency(
    workshop_id: str, depends_on_workshop_id: str
) -> WorkshopDependency:
    dep = WorkshopDependency(
        id=_uuid(),
        workshop_id=workshop_id,
        depends_on_workshop_id=depends_on_workshop_id,
        dependency_type="information_needed",
        created_by="system",
        created_at=_utcnow(),
    )
    db.session.add(dep)
    db.session.flush()
    return dep


def _make_cross_module_flag(process_step_id: str) -> CrossModuleFlag:
    flag = CrossModuleFlag(
        id=_uuid(),
        process_step_id=process_step_id,
        target_process_area="MM",
        description="Cross-module coordination needed",
        created_by="system",
        created_at=_utcnow(),
    )
    db.session.add(flag)
    db.session.flush()
    return flag


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def two_projects():
    """Two isolated projects with full explore entity hierarchies.

    Returns dict with:
        prog_a_id, prog_b_id  — Program integer PKs
        ws_a_id,   ws_b_id    — ExploreWorkshop UUIDs (one per project)
        ws_b2_id              — Second workshop in project B (for dependency target)
        step_a_id, step_b_id  — ProcessStep UUIDs
        oi_a_id,   oi_b_id    — ExploreOpenItem UUIDs
        att_a_id,  att_b_id   — Attachment UUIDs
        scr_a_id,  scr_b_id   — ScopeChangeRequest UUIDs (a=draft, b=approved)
        dep_b_id              — WorkshopDependency UUID (ws_b → ws_b2)
        flag_b_id             — CrossModuleFlag UUID (on step_b)
    """
    prog_a = _make_program("Alpha Corp SAP")
    prog_b = _make_program("Beta Corp SAP")

    ws_a = _make_workshop(prog_a.id, "WS-ISO-A01")
    ws_b = _make_workshop(prog_b.id, "WS-ISO-B01")
    ws_b2 = _make_workshop(prog_b.id, "WS-ISO-B02")  # dependency target

    pl_a = _make_process_level(prog_a.id, "PL-ISO-A01")
    pl_b = _make_process_level(prog_b.id, "PL-ISO-B01")

    step_a = _make_process_step(ws_a.id, pl_a.id)
    step_b = _make_process_step(ws_b.id, pl_b.id)

    oi_a = _make_open_item(prog_a.id, ws_a.id)
    oi_b = _make_open_item(prog_b.id, ws_b.id)

    att_a = _make_attachment(prog_a.id, ws_a.id)
    att_b = _make_attachment(prog_b.id, ws_b.id)

    # SCR a = draft (can be submitted), scr_b = approved (can be implemented)
    scr_a = _make_scope_change_request(prog_a.id, "SCR-ISO-A01")
    scr_b = _make_scope_change_request(prog_b.id, "SCR-ISO-B01")
    scr_b.status = "approved"
    db.session.flush()

    dep_b = _make_workshop_dependency(ws_b.id, ws_b2.id)
    flag_b = _make_cross_module_flag(step_b.id)

    return {
        "prog_a_id": prog_a.id,
        "prog_b_id": prog_b.id,
        "ws_a_id": ws_a.id,
        "ws_b_id": ws_b.id,
        "ws_b2_id": ws_b2.id,
        "step_a_id": step_a.id,
        "step_b_id": step_b.id,
        "oi_a_id": oi_a.id,
        "oi_b_id": oi_b.id,
        "att_a_id": att_a.id,
        "att_b_id": att_b.id,
        "scr_a_id": scr_a.id,
        "scr_b_id": scr_b.id,
        "dep_b_id": dep_b.id,
        "flag_b_id": flag_b.id,
    }


# ── TestOpenItemServiceIsolation ──────────────────────────────────────────────


class TestOpenItemServiceIsolation:
    """Isolation tests for open item service functions.

    ExploreOpenItem has a direct project_id column — all operations
    must verify the caller's project_id matches the item's project_id.
    """

    # ── Happy path ───────────────────────────────────────────────────────

    def test_get_own_open_item_succeeds(self, two_projects):
        """Fetching an open item from the caller's own project returns data."""
        result = explore_service.get_open_item_service(
            two_projects["oi_a_id"], project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, dict)
        assert result["id"] == two_projects["oi_a_id"]

    def test_get_nonexistent_open_item_returns_404(self, two_projects):
        """Fetching a non-existent open item returns a 404 tuple."""
        result = explore_service.get_open_item_service(
            "00000000-0000-0000-0000-000000000000", project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, tuple) and result[1] == 404

    # ── Isolation (xfail — documents desired post-fix behavior) ──────────────

    def test_get_open_item_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT read project B's open item."""
        result = explore_service.get_open_item_service(
            two_projects["oi_b_id"], project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_update_open_item_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT update project B's open item."""
        result = explore_service.update_open_item_service(
            two_projects["oi_b_id"], {"title": "Hijacked"}, project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_transition_open_item_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT transition project B's open item status."""
        result = explore_service.transition_open_item_service(
            two_projects["oi_b_id"],
            {"action": "close", "resolution": "resolved"},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_reassign_open_item_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT reassign project B's open item."""
        result = explore_service.reassign_open_item_service(
            two_projects["oi_b_id"],
            {"assignee_id": "attacker-user", "assignee_name": "Attacker"},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_add_oi_comment_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT add comments to project B's open item."""
        result = explore_service.add_open_item_comment_service(
            two_projects["oi_b_id"],
            {"content": "Injected comment", "type": "comment"},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404


# ── TestProcessStepServiceIsolation ──────────────────────────────────────────


class TestProcessStepServiceIsolation:
    """Isolation tests for process step service functions.

    ProcessStep has only workshop_id (no direct project_id).
    Scope must be verified via JOIN: ProcessStep → ExploreWorkshop.project_id.
    """

    # ── Happy path ───────────────────────────────────────────────────────

    def test_update_own_process_step_succeeds(self, two_projects):
        """Updating a process step in the caller's own project succeeds."""
        result = explore_service.update_process_step_service(
            two_projects["step_a_id"], {"notes": "Updated note"}, project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, dict)
        assert result["notes"] == "Updated note"

    def test_update_nonexistent_process_step_returns_404(self, two_projects):
        """Updating a non-existent step returns 404."""
        result = explore_service.update_process_step_service(
            "00000000-0000-0000-0000-000000000000", {"notes": "x"}, project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, tuple) and result[1] == 404

    # ── Isolation ────────────────────────────────────────────────────────

    def test_update_process_step_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT update project B's process step."""
        result = explore_service.update_process_step_service(
            two_projects["step_b_id"],
            {"fit_decision": "fit"},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_create_decision_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT create decisions on project B's process step."""
        result = explore_service.create_decision_service(
            two_projects["step_b_id"],
            {"text": "Injected decision", "decided_by": "Attacker"},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_create_step_open_item_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT create open items under project B's process step."""
        result = explore_service.create_step_open_item_service(
            two_projects["step_b_id"],
            {"title": "Injected OI", "priority": "P1"},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_create_step_requirement_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT create requirements under project B's process step."""
        result = explore_service.create_step_requirement_service(
            two_projects["step_b_id"],
            {"title": "Injected Requirement"},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404


# ── TestFitDecisionServiceIsolation ──────────────────────────────────────────


class TestFitDecisionServiceIsolation:
    """Isolation tests for workshop-scoped fit decision functions.

    list_fit_decisions and set_fit_decision_bulk take workshop_id.
    Workshop must be scoped via get_scoped(ExploreWorkshop, ws_id, project_id=...).
    """

    # ── Happy path ───────────────────────────────────────────────────────

    def test_list_fit_decisions_own_workshop_returns_list(self, two_projects):
        """Listing fit decisions for own workshop returns a list."""
        result = explore_service.list_fit_decisions_service(
            two_projects["ws_a_id"], project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, list)

    # ── Isolation ────────────────────────────────────────────────────────

    def test_list_fit_decisions_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT enumerate project B's workshop fit decisions."""
        result = explore_service.list_fit_decisions_service(
            two_projects["ws_b_id"], project_id=two_projects["prog_a_id"]
        )
        # After fix: 404 tuple — workshop not found in project A
        assert isinstance(result, tuple) and result[1] == 404


# ── TestCrossModuleFlagServiceIsolation ───────────────────────────────────────


class TestCrossModuleFlagServiceIsolation:
    """Isolation tests for cross-module flag functions.

    CrossModuleFlag has no direct project_id — scope chain:
    CrossModuleFlag → ProcessStep → ExploreWorkshop.project_id (2 JOINs).
    """

    # ── Isolation ────────────────────────────────────────────────────────

    def test_create_cross_module_flag_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT raise a cross-module flag on project B's step."""
        result = explore_service.create_cross_module_flag_service(
            two_projects["step_b_id"],
            {"target_process_area": "FI", "description": "Injected flag"},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_update_cross_module_flag_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT update project B's cross-module flag."""
        result = explore_service.update_cross_module_flag_service(
            two_projects["flag_b_id"],
            {"status": "resolved"},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404


# ── TestWorkshopDependencyServiceIsolation ────────────────────────────────────


class TestWorkshopDependencyServiceIsolation:
    """Isolation tests for workshop dependency functions.

    Workshop dependency scope:
    - get/create: via ExploreWorkshop.project_id (direct get_scoped)
    - resolve: via WorkshopDependency → ExploreWorkshop.workshop_id (JOIN)
    """

    # ── Happy path ───────────────────────────────────────────────────────

    def test_get_own_workshop_dependencies_succeeds(self, two_projects):
        """Listing dependencies for own workshop returns structured payload."""
        result = explore_service.get_workshop_dependencies_service(
            two_projects["ws_a_id"], "all", project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, dict)
        assert "dependencies_out" in result
        assert "dependencies_in" in result

    # ── Isolation ────────────────────────────────────────────────────────

    def test_get_workshop_dependencies_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT read project B's workshop dependency graph."""
        result = explore_service.get_workshop_dependencies_service(
            two_projects["ws_b_id"], "all", project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_create_workshop_dependency_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT create dependencies between project B's workshops."""
        result = explore_service.create_workshop_dependency_service(
            two_projects["ws_b_id"],
            {"depends_on_workshop_id": two_projects["ws_b2_id"]},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_resolve_workshop_dependency_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT resolve project B's workshop dependency."""
        result = explore_service.resolve_workshop_dependency_service(
            two_projects["dep_b_id"], project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, tuple) and result[1] == 404


# ── TestAttachmentServiceIsolation ────────────────────────────────────────────


class TestAttachmentServiceIsolation:
    """Isolation tests for attachment service functions.

    Attachment has a direct project_id column — straightforward get_scoped.
    """

    # ── Happy path ───────────────────────────────────────────────────────

    def test_get_own_attachment_succeeds(self, two_projects):
        """Fetching an attachment from the caller's own project returns data."""
        result = explore_service.get_attachment_service(
            two_projects["att_a_id"], project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, dict)
        assert result["id"] == two_projects["att_a_id"]

    # ── Isolation ────────────────────────────────────────────────────────

    def test_get_attachment_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT read project B's attachment metadata."""
        result = explore_service.get_attachment_service(
            two_projects["att_b_id"], project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_delete_attachment_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT delete project B's attachment."""
        result = explore_service.delete_attachment_service(
            two_projects["att_b_id"], project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, tuple) and result[1] == 404


# ── TestScopeChangeRequestServiceIsolation ───────────────────────────────────


class TestScopeChangeRequestServiceIsolation:
    """Isolation tests for scope change request service functions.

    ScopeChangeRequest has a direct project_id column — straightforward get_scoped.
    """

    # ── Happy path ───────────────────────────────────────────────────────

    def test_get_own_scope_change_request_succeeds(self, two_projects):
        """Fetching an SCR from the caller's own project returns data."""
        result = explore_service.get_scope_change_request_service(
            two_projects["scr_a_id"], project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, dict)
        assert result["id"] == two_projects["scr_a_id"]

    # ── Isolation ────────────────────────────────────────────────────────

    def test_get_scope_change_request_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT read project B's scope change request."""
        result = explore_service.get_scope_change_request_service(
            two_projects["scr_b_id"], project_id=two_projects["prog_a_id"]
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_transition_scr_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT transition project B's scope change request."""
        result = explore_service.transition_scope_change_request_service(
            two_projects["scr_a_id"],  # caller uses their own SCR ID...
            {"action": "cancel"},
            project_id=two_projects["prog_b_id"],  # ...but claims it's in project B
        )
        assert isinstance(result, tuple) and result[1] == 404

    def test_implement_scr_cross_project_is_blocked(self, two_projects):
        """Project A MUST NOT implement project B's approved scope change request."""
        result = explore_service.implement_scope_change_request_service(
            two_projects["scr_b_id"],  # scr_b is 'approved' — highest risk
            {"changed_by": "attacker"},
            project_id=two_projects["prog_a_id"],
        )
        assert isinstance(result, tuple) and result[1] == 404
