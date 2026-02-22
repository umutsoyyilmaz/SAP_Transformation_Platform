"""
Tests: Program Timeline — FDD-F04 / S3-02.

Covers all required test cases:
  1. timeline_endpoint_returns_all_phases
  2. timeline_includes_gates_nested_in_phases
  3. timeline_includes_sprints_with_date_range
  4. timeline_marks_delayed_phases_correctly
  5. critical_path_returns_delayed_items
  6. tenant_isolation_timeline_phases_not_leaked_across_programs

The timeline endpoints derive data from existing Phase, Gate, and Sprint
models — no new DB tables are created by S3-02.  All test data is created via
ORM helpers; the `session` autouse fixture rolls back after every test.
"""

from datetime import date, timedelta

import pytest

from app.models import db as _db
from app.models.auth import Tenant, User
from app.models.backlog import Sprint
from app.models.program import Gate, Phase, Program


# ── ORM helpers ────────────────────────────────────────────────────────────────


def _make_tenant(slug: str = "timeline-co") -> Tenant:
    t = Tenant(name="Timeline Co", slug=slug)
    _db.session.add(t)
    _db.session.flush()
    return t


def _make_program(tenant_id: int, name: str = "Timeline Program") -> Program:
    """Create a Program directly via ORM so tenant_id is populated."""
    p = Program(name=name, methodology="agile", tenant_id=tenant_id)
    _db.session.add(p)
    _db.session.flush()
    return p


def _make_phase(
    program_id: int,
    name: str = "Discover",
    status: str = "not_started",
    planned_start: date | None = None,
    planned_end: date | None = None,
    completion_pct: int = 0,
) -> Phase:
    ph = Phase(
        program_id=program_id,
        name=name,
        status=status,
        planned_start=planned_start,
        planned_end=planned_end,
        completion_pct=completion_pct,
        order=0,
    )
    _db.session.add(ph)
    _db.session.flush()
    return ph


def _make_gate(
    phase_id: int,
    name: str = "Quality Gate",
    planned_date: date | None = None,
    status: str = "pending",
) -> Gate:
    g = Gate(phase_id=phase_id, name=name, planned_date=planned_date, status=status)
    _db.session.add(g)
    _db.session.flush()
    return g


def _make_sprint(
    program_id: int,
    name: str = "Sprint 1",
    start_date: date | None = None,
    end_date: date | None = None,
    status: str = "planning",
    capacity_points: int | None = 30,
    velocity: int | None = None,
) -> Sprint:
    s = Sprint(
        program_id=program_id,
        name=name,
        start_date=start_date,
        end_date=end_date,
        status=status,
        capacity_points=capacity_points,
        velocity=velocity,
        order=0,
    )
    _db.session.add(s)
    _db.session.flush()
    return s


# ── 1. Timeline endpoint returns all phases ────────────────────────────────────


def test_timeline_endpoint_returns_all_phases(client: object) -> None:
    """GET /programs/<id>/timeline returns all phases for the program.

    The response must contain the 'phases' key with one entry per phase,
    plus a 'today' date string and the program metadata block.
    """
    tenant = _make_tenant("tl-all-phases")
    prog = _make_program(tenant.id)
    _make_phase(prog.id, name="Discover", status="completed")
    _make_phase(prog.id, name="Prepare",  status="in_progress")
    _make_phase(prog.id, name="Explore",  status="not_started")

    res = client.get(f"/api/v1/programs/{prog.id}/timeline")
    assert res.status_code == 200

    body = res.get_json()
    assert "phases"    in body
    assert "today"     in body
    assert "program"   in body
    assert body["program"]["id"] == prog.id

    phase_names = {p["name"] for p in body["phases"]}
    assert phase_names == {"Discover", "Prepare", "Explore"}


# ── 2. Timeline includes gates nested in phases ────────────────────────────────


def test_timeline_includes_gates_nested_in_phases(client: object) -> None:
    """Each phase in the timeline response carries a 'gates' list.

    Gates for phase A must not bleed into phase B.
    """
    tenant = _make_tenant("tl-gates")
    prog   = _make_program(tenant.id)
    ph_a   = _make_phase(prog.id, name="Discover")
    ph_b   = _make_phase(prog.id, name="Prepare")
    gate_a = _make_gate(ph_a.id, name="Gate A", planned_date=date(2026, 3, 31))
    _make_gate(ph_b.id, name="Gate B", planned_date=date(2026, 5, 30))

    res = client.get(f"/api/v1/programs/{prog.id}/timeline")
    assert res.status_code == 200

    body   = res.get_json()
    phases = {p["name"]: p for p in body["phases"]}

    # Discover phase has exactly 1 gate
    assert len(phases["Discover"]["gates"]) == 1
    assert phases["Discover"]["gates"][0]["id"] == gate_a.id
    assert phases["Discover"]["gates"][0]["name"] == "Gate A"

    # Prepare phase has exactly 1 gate (Gate B)
    assert len(phases["Prepare"]["gates"]) == 1
    assert phases["Prepare"]["gates"][0]["name"] == "Gate B"

    # Milestones list must expose gate dates
    milestone_names = {m["name"] for m in body["milestones"]}
    assert "Gate A" in milestone_names
    assert "Gate B" in milestone_names


# ── 3. Timeline includes sprints with date range ───────────────────────────────


def test_timeline_includes_sprints_with_date_range(client: object) -> None:
    """GET /programs/<id>/timeline response includes sprints with start/end dates."""
    tenant = _make_tenant("tl-sprints")
    prog   = _make_program(tenant.id)
    sp     = _make_sprint(
        prog.id,
        name="Sprint 1",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 14),
        status="active",
        capacity_points=20,
        velocity=18,
    )

    res = client.get(f"/api/v1/programs/{prog.id}/timeline")
    assert res.status_code == 200

    body    = res.get_json()
    sprints = body.get("sprints", [])
    assert len(sprints) == 1

    s = sprints[0]
    assert s["id"]               == sp.id
    assert s["name"]             == "Sprint 1"
    assert s["start_date"]       == "2026-02-01"
    assert s["end_date"]         == "2026-02-14"
    assert s["status"]           == "active"
    assert s["capacity_points"]  == 20
    assert s["velocity"]         == 18


# ── 4. Delayed phases are marked with red color ────────────────────────────────


def test_timeline_marks_delayed_phases_correctly(client: object) -> None:
    """Phases whose planned_end is in the past AND not completed receive color=#ef4444.

    A completed phase receives the neutral grey (#9ca3af) regardless of dates.
    An in-progress phase with a future end date receives its keyword color, not red.
    """
    today  = date.today()
    past   = today - timedelta(days=10)
    future = today + timedelta(days=30)

    tenant       = _make_tenant("tl-delayed")
    prog         = _make_program(tenant.id)
    ph_delayed   = _make_phase(prog.id, name="Prepare",  status="in_progress", planned_end=past)
    ph_completed = _make_phase(prog.id, name="Discover", status="completed",   planned_end=past)
    ph_on_track  = _make_phase(prog.id, name="Explore",  status="in_progress", planned_end=future)

    res = client.get(f"/api/v1/programs/{prog.id}/timeline")
    assert res.status_code == 200

    colors = {p["name"]: p["color"] for p in res.get_json()["phases"]}

    # Overdue and not done → red
    assert colors["Prepare"]  == "#ef4444", f"Delayed phase should be red, got {colors['Prepare']}"
    # Completed → neutral grey
    assert colors["Discover"] == "#9ca3af", f"Completed phase should be grey, got {colors['Discover']}"
    # In-progress with future end → brand color, NOT red
    assert colors["Explore"]  != "#ef4444", f"On-track phase must not be red, got {colors['Explore']}"


# ── 5. Critical-path endpoint returns delayed items ───────────────────────────


def test_critical_path_returns_delayed_items(client: object) -> None:
    """GET /programs/<id>/timeline/critical-path lists phases with past planned_end.

    Also verifies that at-risk gates (pending, planned within 7 days) appear.
    """
    today = date.today()
    past  = today - timedelta(days=5)
    near  = today + timedelta(days=2)  # within 7-day at-risk window

    tenant = _make_tenant("tl-critical")
    prog   = _make_program(tenant.id)
    ph     = _make_phase(prog.id, name="Realize", status="in_progress", planned_end=past)
    _make_gate(ph.id, name="At-Risk Gate", planned_date=near, status="pending")

    res = client.get(f"/api/v1/programs/{prog.id}/timeline/critical-path")
    assert res.status_code == 200

    body = res.get_json()
    assert body["total_delayed"] == 1
    assert body["delayed_items"][0]["phase_id"]  == ph.id
    assert body["delayed_items"][0]["days_late"]  >= 5

    assert body["total_at_risk"] == 1
    assert body["at_risk_gates"][0]["name"] == "At-Risk Gate"


# ── 6. Tenant isolation: phases are scoped to the queried program ──────────────


def test_tenant_isolation_timeline_cross_tenant_phases_not_leaked(client: object) -> None:
    """Program A's phases MUST NOT appear in Program B's timeline response.

    This verifies that phase data is correctly scoped by program_id,
    preventing cross-program (cross-tenant) data leakage.
    Requesting a non-existent program_id returns 404.
    """
    tenant_a = _make_tenant("tl-tenant-a")
    tenant_b = _make_tenant("tl-tenant-b")
    prog_a   = _make_program(tenant_a.id, name="Prog A")
    prog_b   = _make_program(tenant_b.id, name="Prog B")

    # Add phases ONLY to program A
    _make_phase(prog_a.id, name="Secret Phase A")

    # Program B timeline should return 200 with empty phases (not Program A's data)
    res_b = client.get(f"/api/v1/programs/{prog_b.id}/timeline")
    assert res_b.status_code == 200
    body_b = res_b.get_json()
    phase_names_b = {p["name"] for p in body_b["phases"]}
    assert "Secret Phase A" not in phase_names_b, (
        f"Program A's phase leaked into Program B's timeline: {phase_names_b}"
    )

    # Requesting a completely non-existent program_id must return 404
    res_missing = client.get("/api/v1/programs/999999/timeline")
    assert res_missing.status_code == 404
