from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

import app.services.change_management_service as cm_svc
import app.services.hypercare_service as hypercare_svc
from app.models import db
from app.models.backlog import BacklogItem
from app.models.change_management import ChangeDecision, ChangeRequest
from app.models.cutover import CutoverPlan, PostGoliveChangeRequest
from app.models.program import Program
from app.models.project import Project
from app.models.workstream import Committee


def _create_committee(program_id: int, project) -> Committee:
    committee = Committee(
        tenant_id=project.tenant_id,
        program_id=program_id,
        project_id=project.id,
        name="CAB Board",
        committee_type="advisory",
        meeting_frequency="weekly",
    )
    db.session.add(committee)
    db.session.commit()
    return committee


def _create_board(client, program_id: int, project, committee_id: int) -> dict:
    res = client.post(
        "/api/v1/change-management/boards",
        json={
            "program_id": program_id,
            "project_id": project.id,
            "committee_id": committee_id,
            "name": "CAB Board",
            "board_kind": "cab",
            "quorum_min": 1,
        },
    )
    assert res.status_code == 201, res.get_json()
    return res.get_json()


def _create_approved_change_request(client, program_id: int, project, board_id: int, *, requires_pir: bool = False) -> dict:
    create_res = client.post(
        "/api/v1/change-management/change-requests",
        json={
            "program_id": program_id,
            "project_id": project.id,
            "title": "Enterprise RFC",
            "description": "Lifecycle test RFC",
            "change_model": "normal",
            "change_domain": "config",
            "requires_pir": requires_pir,
        },
    )
    assert create_res.status_code == 201, create_res.get_json()
    change_request = create_res.get_json()

    submit_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/submit",
        json={"program_id": program_id, "project_id": project.id},
    )
    assert submit_res.status_code == 200, submit_res.get_json()

    assess_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/assess",
        json={
            "program_id": program_id,
            "project_id": project.id,
            "impact_summary": "Touches core configuration",
            "implementation_plan": "Deploy transport",
            "rollback_plan": "Re-import prior transport",
            "risk_level": "medium",
        },
    )
    assert assess_res.status_code == 200, assess_res.get_json()

    route_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/route",
        json={
            "program_id": program_id,
            "project_id": project.id,
            "board_profile_id": board_id,
        },
    )
    assert route_res.status_code == 200, route_res.get_json()

    decision_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/decisions",
        json={
            "program_id": program_id,
            "project_id": project.id,
            "board_profile_id": board_id,
            "decision": "approved",
            "rationale": "CAB approved for planned deployment",
        },
    )
    assert decision_res.status_code == 201, decision_res.get_json()

    return client.get(
        f"/api/v1/change-management/change-requests/{change_request['id']}",
        query_string={"program_id": program_id, "project_id": project.id},
    ).get_json()


def test_change_request_end_to_end_with_pir(client, program, project):
    committee = _create_committee(program["id"], project)
    board = _create_board(client, program["id"], project, committee.id)
    change_request = _create_approved_change_request(
        client,
        program["id"],
        project,
        board["id"],
        requires_pir=True,
    )

    now = datetime.now(timezone.utc)
    schedule_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/schedule",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "planned_start": now.isoformat(),
            "planned_end": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert schedule_res.status_code == 200, schedule_res.get_json()
    assert schedule_res.get_json()["status"] == "scheduled"

    implementation_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/implementations",
        json={"program_id": program["id"], "project_id": project.id},
    )
    assert implementation_res.status_code == 201, implementation_res.get_json()
    implementation = implementation_res.get_json()

    start_res = client.post(
        f"/api/v1/change-management/implementations/{implementation['id']}/start",
        json={"program_id": program["id"], "project_id": project.id},
    )
    assert start_res.status_code == 200, start_res.get_json()

    complete_res = client.post(
        f"/api/v1/change-management/implementations/{implementation['id']}/complete",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "status": "completed",
            "execution_notes": "Transport imported to PRD",
        },
    )
    assert complete_res.status_code == 200, complete_res.get_json()
    assert complete_res.get_json()["status"] == "completed"

    validate_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/validate",
        json={"program_id": program["id"], "project_id": project.id},
    )
    assert validate_res.status_code == 200, validate_res.get_json()
    assert validate_res.get_json()["status"] == "pir_pending"

    pir_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/pir",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "summary": "PIR opened for mandatory review",
        },
    )
    assert pir_res.status_code == 201, pir_res.get_json()
    pir = pir_res.get_json()

    complete_pir_res = client.post(
        f"/api/v1/change-management/pir/{pir['id']}/complete",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "outcome": "successful",
            "summary": "No production regression detected",
            "create_lesson_learned": True,
        },
    )
    assert complete_pir_res.status_code == 200, complete_pir_res.get_json()
    assert complete_pir_res.get_json()["status"] == "completed"
    assert complete_pir_res.get_json()["lesson_learned_id"] is not None

    close_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/close",
        json={"program_id": program["id"], "project_id": project.id},
    )
    assert close_res.status_code == 200, close_res.get_json()
    assert close_res.get_json()["status"] == "closed"


def test_freeze_exception_allows_schedule_after_approval(client, program, project):
    committee = _create_committee(program["id"], project)
    board = _create_board(client, program["id"], project, committee.id)
    change_request = _create_approved_change_request(client, program["id"], project, board["id"])

    now = datetime.now(timezone.utc)
    window_res = client.post(
        "/api/v1/change-management/windows",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "title": "Cutover Freeze",
            "window_type": "freeze",
            "start_at": now.isoformat(),
            "end_at": (now + timedelta(hours=2)).isoformat(),
        },
    )
    assert window_res.status_code == 201, window_res.get_json()

    schedule_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/schedule",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "planned_start": (now + timedelta(minutes=15)).isoformat(),
            "planned_end": (now + timedelta(minutes=45)).isoformat(),
        },
    )
    assert schedule_res.status_code == 400
    assert "freeze" in schedule_res.get_json()["error"].lower()

    exception_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/exceptions",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "justification": "Approved cutover exception required",
        },
    )
    assert exception_res.status_code == 201, exception_res.get_json()
    freeze_exception = exception_res.get_json()
    assert freeze_exception["status"] == "pending"

    approve_res = client.post(
        f"/api/v1/change-management/exceptions/{freeze_exception['id']}/approve",
        json={"program_id": program["id"], "project_id": project.id},
    )
    assert approve_res.status_code == 200, approve_res.get_json()
    assert approve_res.get_json()["status"] == "approved"

    schedule_ok_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/schedule",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "planned_start": (now + timedelta(minutes=15)).isoformat(),
            "planned_end": (now + timedelta(minutes=45)).isoformat(),
        },
    )
    assert schedule_ok_res.status_code == 200, schedule_ok_res.get_json()
    assert schedule_ok_res.get_json()["status"] == "scheduled"


def test_scope_change_request_can_be_promoted_to_canonical_rfc(client, program, project):
    create_res = client.post(
        "/api/v1/explore/scope-change-requests",
        json={
            "project_id": project.id,
            "change_type": "add_to_scope",
            "justification": "Template rollout requires additional process scope",
            "impact_assessment": "Increases design backlog",
            "requested_by": "42",
        },
    )
    assert create_res.status_code == 201, create_res.get_json()
    scope_change_request = create_res.get_json()

    promote_res = client.post(
        f"/api/v1/explore/scope-change-requests/{scope_change_request['id']}/promote",
        json={"project_id": project.id, "risk_level": "high"},
    )
    assert promote_res.status_code == 201, promote_res.get_json()
    payload = promote_res.get_json()
    canonical = payload["canonical_change_request"]
    assert canonical["source_entity_type"] == "scope_change_request"
    assert canonical["legacy_code"] == scope_change_request["code"]
    assert canonical["change_domain"] == "scope"

    detail_res = client.get(
        f"/api/v1/explore/scope-change-requests/{scope_change_request['id']}",
        query_string={"project_id": project.id},
    )
    assert detail_res.status_code == 200, detail_res.get_json()
    assert detail_res.get_json()["canonical_change_request"]["id"] == canonical["id"]


def test_hypercare_legacy_change_request_mirrors_canonical(project):
    plan = CutoverPlan(
        tenant_id=project.tenant_id,
        program_id=project.program_id,
        project_id=project.id,
        name="Hypercare Plan",
        status="executing",
    )
    db.session.add(plan)
    db.session.commit()

    created = hypercare_svc.create_change_request(
        project.tenant_id,
        plan.id,
        {
            "title": "Emergency hotfix",
            "change_type": "emergency",
            "priority": "P1",
        },
    )
    assert created["canonical_change_request"] is not None
    assert created["canonical_change_request"]["code"].startswith("RFC-")

    legacy = db.session.get(PostGoliveChangeRequest, created["id"])
    legacy.status = "pending_approval"
    db.session.commit()

    approved = hypercare_svc.approve_change_request(project.tenant_id, plan.id, legacy.id, approver_id=None)
    assert approved["canonical_change_request"] is not None
    assert approved["canonical_change_request"]["status"] == "approved"

    decision = (
        ChangeDecision.query
        .filter(ChangeDecision.change_request_id == approved["canonical_change_request"]["id"])
        .order_by(ChangeDecision.id.desc())
        .first()
    )
    assert decision is not None
    assert decision.decision == "approved"

    canonical = cm_svc.get_canonical_reference_for_legacy("post_golive_change_request", legacy.id)
    assert canonical["id"] == approved["canonical_change_request"]["id"]


# ── 3a. Emergency path ────────────────────────────────────────────────────────


def test_emergency_change_bypasses_cab_and_goes_ecab(client, program, project):
    """Emergency RFC routes through ECAB and reaches ecab_authorized without cab_pending gate."""
    committee = _create_committee(program["id"], project)
    ecab_board = client.post(
        "/api/v1/change-management/boards",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "committee_id": committee.id,
            "name": "ECAB Board",
            "board_kind": "ecab",
            "quorum_min": 1,
        },
    )
    assert ecab_board.status_code == 201, ecab_board.get_json()
    board_id = ecab_board.get_json()["id"]

    create_res = client.post(
        "/api/v1/change-management/change-requests",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "title": "Emergency hotfix",
            "description": "Critical production fix required",
            "change_model": "emergency",
            "change_domain": "config",
        },
    )
    assert create_res.status_code == 201, create_res.get_json()
    cr_id = create_res.get_json()["id"]

    submit_res = client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/submit",
        json={"program_id": program["id"], "project_id": project.id},
    )
    assert submit_res.status_code == 200

    assess_res = client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/assess",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "impact_summary": "Affects production only",
            "implementation_plan": "Apply patch directly",
            "rollback_plan": "Revert patch",
            "risk_level": "critical",
        },
    )
    assert assess_res.status_code == 200

    route_res = client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/route",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "board_profile_id": board_id,
        },
    )
    assert route_res.status_code == 200
    assert route_res.get_json()["status"] == "cab_pending"

    decision_res = client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/decisions",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "board_profile_id": board_id,
            "decision": "emergency_authorized",
            "rationale": "ECAB authorized emergency fix",
        },
    )
    assert decision_res.status_code == 201, decision_res.get_json()

    detail_res = client.get(
        f"/api/v1/change-management/change-requests/{cr_id}",
        query_string={"program_id": program["id"], "project_id": project.id},
    )
    assert detail_res.status_code == 200
    assert detail_res.get_json()["status"] == "ecab_authorized"


# ── 3b. Illegal state transition ─────────────────────────────────────────────


def test_illegal_state_transition_returns_error(client, program, project):
    """Submitting an already-submitted RFC returns 400 with a clear error message."""
    create_res = client.post(
        "/api/v1/change-management/change-requests",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "title": "Double-submit RFC",
            "change_model": "normal",
            "change_domain": "config",
        },
    )
    assert create_res.status_code == 201
    cr_id = create_res.get_json()["id"]

    first_submit = client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/submit",
        json={"program_id": program["id"], "project_id": project.id},
    )
    assert first_submit.status_code == 200

    second_submit = client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/submit",
        json={"program_id": program["id"], "project_id": project.id},
    )
    assert second_submit.status_code == 400
    assert "draft" in second_submit.get_json()["error"].lower()


# ── 3c. Tenant isolation ──────────────────────────────────────────────────────


def test_change_request_not_accessible_across_tenants(program, project):
    """Service raises ValueError when fetching a change request with a foreign tenant_id."""
    create_res = cm_svc.create_change_request(
        {
            "program_id": program["id"],
            "project_id": project.id,
            "title": "Tenant-scoped RFC",
            "change_model": "normal",
            "change_domain": "config",
        },
        tenant_id=project.tenant_id,
    )
    cr_id = create_res["id"]

    with pytest.raises(ValueError, match="Change request not found"):
        cm_svc.get_change_request(cr_id, tenant_id=project.tenant_id + 9999)


# ── 3d. Permission resolver unit test ────────────────────────────────────────


def test_change_management_permission_resolver_maps_routes_correctly():
    """_resolve_change_management_permission maps HTTP method + path to the expected codename."""
    from app.middleware.blueprint_permissions import _resolve_change_management_permission as resolve

    # Basic change-requests list/create
    assert resolve("GET", "/api/v1/change-management/change-requests") == "change.view"
    assert resolve("POST", "/api/v1/change-management/change-requests") == "change.create"

    # Sub-action paths
    assert resolve("POST", "/api/v1/change-management/change-requests/1/assess") == "change.assess"
    assert resolve("POST", "/api/v1/change-management/change-requests/1/route") == "change.approve"
    assert resolve("POST", "/api/v1/change-management/change-requests/1/schedule") == "change.schedule"
    assert resolve("POST", "/api/v1/change-management/change-requests/1/validate") == "change.execute"
    assert resolve("POST", "/api/v1/change-management/change-requests/1/close") == "change.execute"

    # Analytics requires audit permission
    assert resolve("GET", "/api/v1/change-management/analytics") == "change.audit"

    # Implementations
    assert resolve("GET", "/api/v1/change-management/implementations/5") == "change.view"
    assert resolve("POST", "/api/v1/change-management/implementations/5/start") == "change.execute"

    # PIR
    assert resolve("GET", "/api/v1/change-management/pir/3") == "change.view"
    assert resolve("POST", "/api/v1/change-management/pir/3/complete") == "change.audit"


# ── 3e. Blackout window blocking ─────────────────────────────────────────────


def test_schedule_blocked_by_blackout_window(client, program, project):
    """Scheduling an RFC during an active blackout window returns 400."""
    committee = _create_committee(program["id"], project)
    board = _create_board(client, program["id"], project, committee.id)
    change_request = _create_approved_change_request(client, program["id"], project, board["id"])

    now = datetime.now(timezone.utc)
    window_res = client.post(
        "/api/v1/change-management/windows",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "title": "Go-live Blackout",
            "window_type": "blackout",
            "start_at": now.isoformat(),
            "end_at": (now + timedelta(hours=3)).isoformat(),
        },
    )
    assert window_res.status_code == 201, window_res.get_json()

    schedule_res = client.post(
        f"/api/v1/change-management/change-requests/{change_request['id']}/schedule",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "planned_start": (now + timedelta(minutes=30)).isoformat(),
            "planned_end": (now + timedelta(minutes=90)).isoformat(),
        },
    )
    assert schedule_res.status_code == 400
    error_text = schedule_res.get_json()["error"].lower()
    assert "blackout" in error_text


# ── 3f. Analytics endpoint ────────────────────────────────────────────────────


def test_analytics_summary_returns_expected_kpis(client, program, project):
    """GET /analytics returns all required KPI fields for the given program/project scope."""
    committee = _create_committee(program["id"], project)
    board = _create_board(client, program["id"], project, committee.id)

    # Create two RFCs — one normal, one emergency
    for change_model, title in [("normal", "Normal RFC"), ("emergency", "Emergency RFC")]:
        client.post(
            "/api/v1/change-management/change-requests",
            json={
                "program_id": program["id"],
                "project_id": project.id,
                "title": title,
                "change_model": change_model,
                "change_domain": "config",
            },
        )

    res = client.get(
        "/api/v1/change-management/analytics",
        query_string={"program_id": program["id"], "project_id": project.id},
    )
    assert res.status_code == 200, res.get_json()
    payload = res.get_json()

    assert "summary" in payload
    summary = payload["summary"]
    assert summary["total_changes"] >= 2
    assert "change_success_rate" in summary
    assert "emergency_ratio" in summary
    assert "backout_rate" in summary
    assert "freeze_exceptions" in summary
    assert "pir_overdue" in summary
    assert "status_counts" in payload
    assert "model_counts" in payload


# ── 3g. CAB decision with conditions ─────────────────────────────────────────


def test_cab_decision_records_approver_and_conditions(client, program, project):
    """approved_with_conditions decision stores conditions text and sets status to approved."""
    committee = _create_committee(program["id"], project)
    board = _create_board(client, program["id"], project, committee.id)
    cr_id = None

    create_res = client.post(
        "/api/v1/change-management/change-requests",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "title": "Conditional RFC",
            "change_model": "normal",
            "change_domain": "config",
        },
    )
    assert create_res.status_code == 201
    cr_id = create_res.get_json()["id"]

    client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/submit",
        json={"program_id": program["id"], "project_id": project.id},
    )
    client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/assess",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "impact_summary": "Low-risk config change",
            "implementation_plan": "Apply via transport",
            "rollback_plan": "Re-import previous transport",
            "risk_level": "low",
        },
    )
    client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/route",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "board_profile_id": board["id"],
        },
    )

    conditions_text = "Deploy only after full backup confirmed and smoke test passed"
    decision_res = client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/decisions",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "board_profile_id": board["id"],
            "decision": "approved_with_conditions",
            "conditions": conditions_text,
            "rationale": "CAB approves with backup precondition",
        },
    )
    assert decision_res.status_code == 201, decision_res.get_json()

    stored_decision = (
        ChangeDecision.query
        .filter_by(change_request_id=cr_id)
        .order_by(ChangeDecision.id.desc())
        .first()
    )
    assert stored_decision is not None
    assert stored_decision.decision == "approved_with_conditions"
    assert stored_decision.conditions == conditions_text

    detail_res = client.get(
        f"/api/v1/change-management/change-requests/{cr_id}",
        query_string={"program_id": program["id"], "project_id": project.id},
    )
    assert detail_res.get_json()["status"] == "approved"


# ── 3h. Cross-project artifact link guard ────────────────────────────────────


def test_change_link_rejects_cross_project_artifact(client, program, project):
    """Adding a link to a BacklogItem from a different program scope returns 400."""
    create_res = client.post(
        "/api/v1/change-management/change-requests",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "title": "Scoped RFC",
            "change_model": "normal",
            "change_domain": "config",
        },
    )
    assert create_res.status_code == 201
    cr_id = create_res.get_json()["id"]

    # Create an artifact that belongs to a completely different program + project
    other_program = Program(name="Other Program", tenant_id=project.tenant_id)
    db.session.add(other_program)
    db.session.flush()
    other_project = Project(
        tenant_id=project.tenant_id,
        program_id=other_program.id,
        code="OTH-01",
        name="Other Project",
        is_default=True,
    )
    db.session.add(other_project)
    db.session.flush()
    foreign_item = BacklogItem(
        tenant_id=project.tenant_id,
        program_id=other_program.id,
        project_id=other_project.id,
        code="BL-FOREIGN",
        title="Foreign backlog item",
        wricef_type="report",
        status="new",
    )
    db.session.add(foreign_item)
    db.session.commit()

    link_res = client.post(
        f"/api/v1/change-management/change-requests/{cr_id}/links",
        json={
            "program_id": program["id"],
            "project_id": project.id,
            "linked_entity_type": "backlog_item",
            "linked_entity_id": foreign_item.id,
            "relationship_type": "affected",
        },
    )
    assert link_res.status_code == 400
    assert "scope" in link_res.get_json()["error"].lower()
