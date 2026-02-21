"""Bölüm 2 — workshop_session.py tenant isolation tests.

These tests document the P0 security gap in workshop_session.py where
carry_forward_steps, link_session_steps, get_session_summary, and
validate_session_start accept arbitrary workshop IDs without verifying
that the caller owns the project.

Test naming convention:
  test_<function>_<scenario>_<expected_result>

Tests marked @pytest.mark.xfail document DESIRED post-fix behavior:
  - They are RED today  (isolation not yet enforced → assertion fails)
  - They turn GREEN automatically once project_id enforcement is added

Happy-path and non-isolation error tests are plain asserts (no xfail).
"""

from datetime import date, time

import pytest

from app.models import db
from app.models.explore import ExploreWorkshop
from app.models.program import Program
from app.services.workshop_session import (
    carry_forward_steps,
    get_session_summary,
    link_session_steps,
    validate_session_start,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_program(name: str) -> Program:
    """Create and flush a minimal Program (the 'project' entity)."""
    prog = Program(name=name, status="active", methodology="agile")
    db.session.add(prog)
    db.session.flush()
    return prog


def _make_workshop(project_id: int, code: str, **kw) -> ExploreWorkshop:
    """Create and flush an ExploreWorkshop with all NOT NULL fields set.

    Uses the canonical factory pattern from tests/test_explore.py#_make_workshop.
    """
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


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def two_projects():
    """Two isolated projects, each with its own workshop.

    Returns dict with prog_a_id, prog_b_id, ws_a_id, ws_b_id.
    Intentionally uses different process_area values so session chaining
    cannot accidentally cross-match workshops.
    """
    prog_a = _make_program("Tenant Alpha SAP Project")
    prog_b = _make_program("Tenant Beta SAP Project")

    ws_a = _make_workshop(prog_a.id, code="WS-A01", process_area="FI")
    ws_b = _make_workshop(prog_b.id, code="WS-B01", process_area="MM")

    return {
        "prog_a_id": prog_a.id,
        "prog_b_id": prog_b.id,
        "ws_a_id": ws_a.id,
        "ws_b_id": ws_b.id,
    }


@pytest.fixture()
def chained_workshops():
    """Single project with two chained workshops (session 1 → session 2).

    Used to test carry_forward_steps and link_session_steps happy path.
    """
    prog = _make_program("Multi-Session Project")
    ws1 = _make_workshop(
        prog.id,
        code="WS-S01",
        process_area="SD",
        session_number=1,
        total_sessions=2,
    )
    ws2 = _make_workshop(
        prog.id,
        code="WS-S02",
        process_area="SD",
        session_number=2,
        total_sessions=2,
    )
    return {
        "prog_id": prog.id,
        "ws1_id": ws1.id,
        "ws2_id": ws2.id,
    }


# ── TestGetSessionSummary ─────────────────────────────────────────────────────


class TestGetSessionSummary:
    """get_session_summary(workshop_id) isolation tests."""

    def test_own_workshop_returns_valid_summary_dict(self, two_projects):
        """Happy path: own workshop ID returns aggregated summary."""
        result = get_session_summary(two_projects["ws_a_id"])

        assert isinstance(result, dict)
        assert "total_sessions" in result
        assert "sessions" in result
        assert "completion_pct" in result
        assert "overall_steps_total" in result

    def test_summary_total_sessions_at_least_one(self, two_projects):
        """A single non-chained workshop counts as 1 session."""
        result = get_session_summary(two_projects["ws_a_id"])
        assert result["total_sessions"] >= 1

    def test_summary_initial_completion_is_zero(self, two_projects):
        """Fresh workshop with no assessed steps has 0% completion."""
        result = get_session_summary(two_projects["ws_a_id"])
        assert result["completion_pct"] == 0.0

    def test_nonexistent_workshop_raises_value_error(self):
        """Non-existent UUID must raise ValueError, not return None."""
        with pytest.raises(ValueError, match="Workshop not found"):
            get_session_summary("00000000-0000-0000-0000-000000000000")

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "P0 isolation gap: get_session_summary(workshop_id) has no project_id "
            "parameter. Any caller that knows ws_b_id can read project_b's session "
            "data without authorization. Fix: add project_id parameter and reject "
            "mismatched workshop ownership."
        ),
    )
    def test_cross_project_access_raises_not_found(self, two_projects):
        """Caller from project_a MUST NOT read project_b's session summary.

        VULNERABILITY: Currently this call SUCCEEDS and returns project_b data.
        EXPECTED AFTER FIX: raise ValueError/NotFoundError/PermissionError.
        """
        with pytest.raises((ValueError, PermissionError)):
            # Once fixed the API will be: get_session_summary(ws_id, project_id=...)
            # and this mis-match must be rejected:
            get_session_summary(two_projects["ws_b_id"])


# ── TestValidateSessionStart ──────────────────────────────────────────────────


class TestValidateSessionStart:
    """validate_session_start(workshop_id) isolation tests."""

    def test_own_workshop_returns_result_dict(self, two_projects):
        """Happy path: returns can_start, errors, warnings keys."""
        result = validate_session_start(two_projects["ws_a_id"])

        assert isinstance(result, dict)
        assert "can_start" in result
        assert "errors" in result
        assert "warnings" in result

    def test_no_scope_items_blocks_start(self, two_projects):
        """Workshop without scope items cannot start (errors list populated)."""
        result = validate_session_start(two_projects["ws_a_id"])

        assert result["can_start"] is False
        assert any("scope" in e.lower() for e in result["errors"])

    def test_nonexistent_workshop_returns_cannot_start(self):
        """Completely unknown workshop_id returns can_start=False (graceful)."""
        result = validate_session_start("00000000-dead-beef-0000-000000000000")

        assert result["can_start"] is False
        assert len(result["errors"]) > 0

    def test_completed_status_blocks_restart(self, two_projects):
        """Workshop already completed cannot be started again."""
        ws = _make_workshop(
            two_projects["prog_a_id"],
            code="WS-DONE",
            status="completed",
        )
        result = validate_session_start(ws.id)

        assert result["can_start"] is False
        assert any("status" in e.lower() for e in result["errors"])

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "P0 isolation gap: validate_session_start has no project_id "
            "parameter. Project A can send project B's workshop ID and receive "
            "its validation data. Fix: add project_id param + ownership check."
        ),
    )
    def test_cross_project_access_is_blocked(self, two_projects):
        """Project A must not be able to validate project B's workshop.

        VULNERABILITY: Currently returns project_b workshop validation.
        EXPECTED AFTER FIX: raise ValueError/PermissionError.
        """
        with pytest.raises((ValueError, PermissionError)):
            validate_session_start(two_projects["ws_b_id"])


# ── TestCarryForwardSteps ─────────────────────────────────────────────────────


class TestCarryForwardSteps:
    """carry_forward_steps(prev_id, new_id) isolation tests."""

    def test_empty_source_returns_empty_list(self, chained_workshops):
        """No steps in previous session → carry returns []."""
        result = carry_forward_steps(
            previous_workshop_id=chained_workshops["ws1_id"],
            new_workshop_id=chained_workshops["ws2_id"],
        )
        assert result == []

    def test_carry_all_flag_accepted(self, chained_workshops):
        """carry_all=True is accepted without error even for empty workshop."""
        result = carry_forward_steps(
            previous_workshop_id=chained_workshops["ws1_id"],
            new_workshop_id=chained_workshops["ws2_id"],
            carry_all=True,
        )
        assert result == []

    def test_nonexistent_both_workshops_raise_value_error(self):
        """Both non-existent IDs raise ValueError (not silent None)."""
        with pytest.raises(ValueError):
            carry_forward_steps(
                previous_workshop_id="00000000-0000-0000-0000-000000000000",
                new_workshop_id="11111111-1111-1111-1111-111111111111",
            )

    def test_nonexistent_target_workshop_raises_value_error(self, two_projects):
        """Valid source but non-existent target raises ValueError."""
        with pytest.raises(ValueError):
            carry_forward_steps(
                previous_workshop_id=two_projects["ws_a_id"],
                new_workshop_id="11111111-1111-1111-1111-111111111111",
            )

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "P0 isolation gap (CROSS-PROJECT WRITE): carry_forward_steps allows "
            "steps from project_a's workshop to be written into project_b's workshop. "
            "This is a cross-tenant WRITE — the most critical isolation failure. "
            "Fix: verify both workshop IDs belong to the same project_id."
        ),
    )
    def test_cross_project_carry_forward_is_blocked(self, two_projects):
        """Carrying steps from project_a into project_b's workshop MUST be rejected.

        VULNERABILITY: Currently succeeds — even with steps present this would
        write project_a data into project_b's workshop with no authorization.
        EXPECTED AFTER FIX: raise ValueError/PermissionError.
        """
        with pytest.raises((ValueError, PermissionError)):
            carry_forward_steps(
                previous_workshop_id=two_projects["ws_a_id"],
                new_workshop_id=two_projects["ws_b_id"],
            )


# ── TestLinkSessionSteps ──────────────────────────────────────────────────────


class TestLinkSessionSteps:
    """link_session_steps(prev_id, new_id) isolation tests."""

    def test_no_steps_returns_zero_links(self, chained_workshops):
        """No matching steps → 0 links created."""
        result = link_session_steps(
            previous_workshop_id=chained_workshops["ws1_id"],
            new_workshop_id=chained_workshops["ws2_id"],
        )
        assert result == 0

    def test_same_workshop_link_is_idempotent(self, chained_workshops):
        """Linking an already-linked (empty) workshop returns 0, not an error."""
        link_session_steps(
            previous_workshop_id=chained_workshops["ws1_id"],
            new_workshop_id=chained_workshops["ws2_id"],
        )
        # Second call must be idempotent
        result = link_session_steps(
            previous_workshop_id=chained_workshops["ws1_id"],
            new_workshop_id=chained_workshops["ws2_id"],
        )
        assert result == 0

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "P0 isolation gap: link_session_steps has no project_id parameter. "
            "A caller can establish step links between workshops from different "
            "projects, corrupting cross-tenant process step audit trails."
        ),
    )
    def test_cross_project_linking_is_blocked(self, two_projects):
        """Linking steps across projects must be rejected.

        VULNERABILITY: Currently succeeds (returns 0 with no error).
        EXPECTED AFTER FIX: raise ValueError/PermissionError.
        """
        with pytest.raises((ValueError, PermissionError)):
            link_session_steps(
                previous_workshop_id=two_projects["ws_a_id"],
                new_workshop_id=two_projects["ws_b_id"],
            )


# ── TestWorkshopProjectOwnership ─────────────────────────────────────────────


class TestWorkshopProjectOwnership:
    """Direct model-level isolation correctness tests."""

    def test_workshops_belong_to_distinct_projects(self, two_projects):
        """Data fixture sanity: the two workshops really are in different projects."""
        ws_a = db.session.get(ExploreWorkshop, two_projects["ws_a_id"])
        ws_b = db.session.get(ExploreWorkshop, two_projects["ws_b_id"])

        assert ws_a is not None
        assert ws_b is not None
        assert ws_a.project_id != ws_b.project_id

    def test_workshop_project_id_matches_owning_program(self, two_projects):
        """Workshop.project_id FK points to correct Program row."""
        ws_a = db.session.get(ExploreWorkshop, two_projects["ws_a_id"])
        assert ws_a.project_id == two_projects["prog_a_id"]

        ws_b = db.session.get(ExploreWorkshop, two_projects["ws_b_id"])
        assert ws_b.project_id == two_projects["prog_b_id"]

    def test_workshop_ids_are_unique_across_projects(self, two_projects):
        """Primary keys must never collide across projects."""
        assert two_projects["ws_a_id"] != two_projects["ws_b_id"]
