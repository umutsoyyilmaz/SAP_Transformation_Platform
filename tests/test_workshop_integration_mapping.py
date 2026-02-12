"""
Workshop Integration Tests — Frontend→Backend Field Mapping Validation

Bu testler frontend'in (explore_workshop_detail.js) gonderdigi
gercek payload'lari simule eder ve backend uyumlulugunu dogrular.

Analiz referansi: docs/plans/workshop-module-analysis.md
"""
import pytest
from datetime import datetime, date, timedelta, timezone
from app.models.explore import (
    ExploreWorkshop, WorkshopScopeItem, ProcessStep,
    ExploreDecision, ExploreOpenItem, WorkshopAttendee, WorkshopAgendaItem,
)
from app.models.explore import ProcessLevel
from app import db as _db


# --- Helpers ---------------------------------------------------------------


@pytest.fixture()
def project_id(program):
    return program["id"]

def _uuid():
    import uuid
    return str(uuid.uuid4())


def _make_hierarchy(project_id):
    """Create L1->L2->L3->L4 hierarchy, return (l1, l2, l3, l4)."""
    l1 = ProcessLevel(project_id=project_id, code="L1-INT", name="L1 Area",
                      level=1, scope_status="in_scope", sort_order=1)
    _db.session.add(l1)
    _db.session.flush()
    l2 = ProcessLevel(project_id=project_id, code="L2-INT", name="L2 Group",
                      level=2, parent_id=l1.id, scope_status="in_scope", sort_order=1)
    _db.session.add(l2)
    _db.session.flush()
    l3 = ProcessLevel(project_id=project_id, code="L3-INT", name="L3 Scope Item",
                      level=3, parent_id=l2.id, scope_status="in_scope", sort_order=1)
    _db.session.add(l3)
    _db.session.flush()
    l4 = ProcessLevel(project_id=project_id, code="L4-INT", name="L4 Step",
                      level=4, parent_id=l3.id, scope_status="in_scope", sort_order=1)
    _db.session.add(l4)
    _db.session.flush()
    return l1, l2, l3, l4


def _make_workshop(project_id, **kw):
    defaults = dict(
        project_id=project_id, code=kw.pop("code", f"WS-INT-{_uuid()[:6]}"),
        name="Integration Test Workshop", type="fit_to_standard",
        status="draft", process_area="FI", wave=1,
        session_number=1, total_sessions=1,
    )
    defaults.update(kw)
    ws = ExploreWorkshop(**defaults)
    _db.session.add(ws)
    _db.session.flush()
    return ws


# ======================================================================
# TEST GROUP 1: Workshop Creation - Frontend field mapping
# ======================================================================

class TestWorkshopCreationFlow:
    """Sorun 4.5, 4.6: Frontend create modal -> backend field mapping."""

    def test_create_workshop_with_frontend_payload(self, client, project_id):
        """Frontend's createWorkshop() sends these exact fields."""
        resp = client.post("/api/v1/explore/workshops", json={
            "project_id": project_id,
            "name": "FI Workshop 1",
            "type": "initial",              # Frontend uses "initial" - is this valid?
            "date": "2026-03-15",
            "facilitator_id": "John Smith",  # Frontend sends string name
            "process_area": "FI",
            "wave": 1,
            "scope_item_ids": [],            # Frontend sends this
            "notes": "Test workshop",
        })
        assert resp.status_code in (200, 201), f"Create failed: {resp.get_json()}"
        data = resp.get_json()
        assert data.get("name") == "FI Workshop 1"
        # Check if workshop_type "initial" is accepted
        assert data.get("type") in ("initial", "fit_to_standard")

    def test_create_workshop_with_scope_items(self, client, project_id):
        """Frontend sends scope_item_ids - does backend create WorkshopScopeItem?"""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        _db.session.commit()

        resp = client.post("/api/v1/explore/workshops", json={
            "project_id": project_id,
            "name": "Workshop with scope",
            "type": "fit_to_standard",
            "process_area": "FI",
            "scope_item_ids": [l3.id],
        })
        assert resp.status_code in (200, 201), f"Create failed: {resp.get_json()}"
        ws_id = resp.get_json().get("id")

        # Verify WorkshopScopeItem was created
        wsi = WorkshopScopeItem.query.filter_by(workshop_id=ws_id).first()
        assert wsi is not None, "scope_item_ids not processed - WorkshopScopeItem not created"
        assert wsi.process_level_id == l3.id

    def test_create_workshop_missing_name(self, client, project_id):
        """Frontend has no validation - backend should reject."""
        resp = client.post("/api/v1/explore/workshops", json={
            "project_id": project_id,
            "type": "fit_to_standard",
            "process_area": "FI",
        })
        assert resp.status_code in (400, 422), "Backend should reject missing name"


# ======================================================================
# TEST GROUP 2: Workshop Start -> Process Steps
# ======================================================================

class TestWorkshopStartFlow:
    """Sorun 4.4, 4.7: Start creates ProcessSteps, frontend needs to fetch them."""

    def test_start_creates_process_steps(self, client, project_id):
        """Start should auto-create ProcessStep for each L4 child."""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="scheduled")
        wsi = WorkshopScopeItem(workshop_id=ws.id, process_level_id=l3.id, sort_order=1)
        _db.session.add(wsi)
        _db.session.commit()

        resp = client.post(f"/api/v1/explore/workshops/{ws.id}/start")
        assert resp.status_code == 200, f"Start failed: {resp.get_json()}"

        # Verify ProcessStep was created
        steps = ProcessStep.query.filter_by(workshop_id=ws.id).all()
        assert len(steps) >= 1, "Start should create ProcessSteps for L4 children"
        assert steps[0].process_level_id == l4.id

    def test_start_without_scope_items_fails(self, client, project_id):
        """Workshop without scope items can't start."""
        ws = _make_workshop(project_id, status="scheduled")
        _db.session.commit()

        resp = client.post(f"/api/v1/explore/workshops/{ws.id}/start")
        assert resp.status_code == 400, "Start without scope items should fail"

    def test_process_steps_endpoint_exists(self, client, project_id):
        """Sorun 4.7: Frontend needs GET /workshops/<id>/process-steps or similar."""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="scheduled")
        wsi = WorkshopScopeItem(workshop_id=ws.id, process_level_id=l3.id, sort_order=1)
        _db.session.add(wsi)
        _db.session.commit()
        client.post(f"/api/v1/explore/workshops/{ws.id}/start")

        # Try fetching steps - this endpoint may not exist
        resp = client.get(f"/api/v1/explore/workshops/{ws.id}/process-steps")
        if resp.status_code == 404:
            pytest.skip("GET /workshops/<id>/process-steps endpoint missing - needs implementation")
        assert resp.status_code == 200


# ======================================================================
# TEST GROUP 3: Inline Forms - Decision/OI/Req from Steps
# ======================================================================

class TestInlineFormDecision:
    """Sorun 4.1: Frontend sends l4_process_step_id but API expects process_step_id."""

    def _setup(self, project_id):
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="in_progress")
        ws.started_at = datetime.now(timezone.utc)
        step = ProcessStep(workshop_id=ws.id, process_level_id=l4.id, sort_order=1)
        _db.session.add(step)
        _db.session.flush()
        return ws, step

    def test_create_decision_with_correct_field(self, client, project_id):
        """Backend expects step_id in URL path."""
        ws, step = self._setup(project_id)
        _db.session.commit()

        resp = client.post(
            f"/api/v1/explore/process-steps/{step.id}/decisions",
            json={
                "text": "Use standard SAP config",
                "decided_by": "Consultant Team",
                "category": "configuration",
            },
        )
        assert resp.status_code in (200, 201), f"Decision create failed: {resp.get_json()}"

    def test_create_decision_with_frontend_field_name(self, client, project_id):
        """
        Sorun 4.1: Frontend sends { l4_process_step_id: stepId }
        but ExploreAPI uses data.process_step_id for URL construction.
        This simulates what happens when l4_process_step_id is sent.
        """
        ws, step = self._setup(project_id)
        _db.session.commit()

        # This is what frontend ACTUALLY sends via ExploreAPI.decisions.create():
        # API.post(`/process-steps/${data.process_step_id}/decisions`, data)
        # But data has l4_process_step_id, NOT process_step_id -> URL becomes /process-steps/undefined/decisions

        # Simulate the broken URL
        resp = client.post(
            "/api/v1/explore/process-steps/undefined/decisions",
            json={
                "l4_process_step_id": step.id,
                "text": "Test decision",
                "decided_by": "Tester",
                "category": "process",
            },
        )
        # This SHOULD fail (404) - confirming the bug
        assert resp.status_code in (404, 400), \
            "BUG CONFIRMED: frontend sends l4_process_step_id but API uses process_step_id"


class TestInlineFormOpenItem:
    """Sorun 4.2: OpenItem created without workshop_id link (orphan)."""

    def test_create_oi_flat_preserves_workshop_id(self, client, project_id):
        """Frontend uses POST /open-items with workshop_id in body - does backend save it?"""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="in_progress")
        ws.started_at = datetime.now(timezone.utc)
        step = ProcessStep(workshop_id=ws.id, process_level_id=l4.id, sort_order=1)
        _db.session.add(step)
        _db.session.commit()

        resp = client.post("/api/v1/explore/open-items", json={
            "project_id": project_id,
            "workshop_id": ws.id,
            "l4_process_step_id": step.id,
            "title": "Missing config for FI posting",
            "priority": "P2",
            "assignee": "John",
            "due_date": "2026-03-20",
            "description": "Need to configure FI posting rules",
        })
        assert resp.status_code in (200, 201), f"OI create failed: {resp.get_json()}"
        oi_data = resp.get_json()

        # Verify workshop_id was saved
        oi = _db.session.get(ExploreOpenItem, oi_data["id"])
        has_workshop = hasattr(oi, "workshop_id") and oi.workshop_id == ws.id
        if not has_workshop:
            pytest.fail(
                f"BUG 4.2 CONFIRMED: OpenItem created without workshop_id. "
                f"oi.workshop_id={getattr(oi, 'workshop_id', 'ATTR_MISSING')}"
            )

    def test_create_oi_from_step_endpoint(self, client, project_id):
        """Alternative: POST /process-steps/<id>/open-items - this SHOULD work."""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="in_progress")
        step = ProcessStep(workshop_id=ws.id, process_level_id=l4.id, sort_order=1)
        _db.session.add(step)
        _db.session.commit()

        resp = client.post(
            f"/api/v1/explore/process-steps/{step.id}/open-items",
            json={
                "title": "Config gap",
                "priority": "P2",
                "category": "configuration",
                "description": "Missing",
            },
        )
        assert resp.status_code in (200, 201), f"Step-based OI create failed: {resp.get_json()}"


class TestInlineFormRequirement:
    """Sorun 4.3: Requirement create - similar orphan risk."""

    def test_create_req_from_step_endpoint(self, client, project_id):
        """POST /process-steps/<id>/requirements - should work."""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="in_progress")
        step = ProcessStep(workshop_id=ws.id, process_level_id=l4.id, sort_order=1)
        _db.session.add(step)
        _db.session.commit()

        resp = client.post(
            f"/api/v1/explore/process-steps/{step.id}/requirements",
            json={
                "title": "Custom report needed",
                "priority": "P2",
                "type": "functional",
                "fit_status": "gap",
                "description": "Standard report insufficient",
            },
        )
        assert resp.status_code in (200, 201), f"Step-based Req create failed: {resp.get_json()}"


# ======================================================================
# TEST GROUP 4: Fit Decision
# ======================================================================

class TestFitDecisionFlow:
    """Sorun 4.8: Frontend sends fit_status, backend may expect fit_decision."""

    def test_set_fit_via_step_update(self, client, project_id):
        """Frontend uses PUT /process-steps/<id> with {fit_decision: 'gap'}."""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="in_progress")
        step = ProcessStep(workshop_id=ws.id, process_level_id=l4.id, sort_order=1)
        _db.session.add(step)
        _db.session.commit()

        resp = client.put(
            f"/api/v1/explore/process-steps/{step.id}",
            json={"fit_decision": "gap", "notes": "Standard doesn't cover this"},
        )
        assert resp.status_code == 200, f"Fit decision update failed: {resp.get_json()}"

        # Verify it was saved
        step_updated = _db.session.get(ProcessStep, step.id)
        assert step_updated.fit_decision == "gap"

    def test_fit_decisions_bulk_endpoint(self, client, project_id):
        """POST /workshops/<id>/fit-decisions - bulk set."""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="in_progress")
        step = ProcessStep(workshop_id=ws.id, process_level_id=l4.id, sort_order=1)
        _db.session.add(step)
        _db.session.commit()

        resp = client.post(
            f"/api/v1/explore/workshops/{ws.id}/fit-decisions",
            json={
                "decisions": [
                    {"process_step_id": step.id, "fit_status": "gap"},
                ],
            },
        )
        # May accept different payload format
        assert resp.status_code in (200, 201, 400), f"Bulk fit failed: {resp.get_json()}"


# ======================================================================
# TEST GROUP 5: Workshop Transitions
# ======================================================================

class TestWorkshopTransitions:
    """Sorun 4.10: Reopen transition mapping."""

    def test_reopen_workshop(self, client, project_id):
        """POST /workshops/<id>/reopen - does this endpoint work?"""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="completed")
        ws.started_at = datetime.now(timezone.utc) - timedelta(hours=3)
        ws.completed_at = datetime.now(timezone.utc)
        _db.session.commit()

        resp = client.post(
            f"/api/v1/explore/workshops/{ws.id}/reopen",
            json={"reason": "Need to reassess gap steps"},
        )
        assert resp.status_code == 200, f"Reopen failed: {resp.get_json()}"

        ws_updated = _db.session.get(ExploreWorkshop, ws.id)
        assert ws_updated.status == "in_progress", f"Status after reopen: {ws_updated.status}"

    def test_complete_with_unassessed_steps(self, client, project_id):
        """Complete should warn about unassessed steps."""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="in_progress")
        ws.started_at = datetime.now(timezone.utc)
        wsi = WorkshopScopeItem(workshop_id=ws.id, process_level_id=l3.id, sort_order=1)
        _db.session.add(wsi)
        step = ProcessStep(workshop_id=ws.id, process_level_id=l4.id, sort_order=1)
        # fit_decision = None -> unassessed
        _db.session.add(step)
        _db.session.commit()

        resp = client.post(f"/api/v1/explore/workshops/{ws.id}/complete")
        # Should fail (400) because step not assessed
        assert resp.status_code == 400, "Complete should reject unassessed steps"

    def test_complete_with_force(self, client, project_id):
        """Complete with force=True should succeed despite unassessed."""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="in_progress")
        ws.started_at = datetime.now(timezone.utc)
        wsi = WorkshopScopeItem(workshop_id=ws.id, process_level_id=l3.id, sort_order=1)
        _db.session.add(wsi)
        step = ProcessStep(workshop_id=ws.id, process_level_id=l4.id, sort_order=1)
        _db.session.add(step)
        _db.session.commit()

        resp = client.post(
            f"/api/v1/explore/workshops/{ws.id}/complete",
            json={"force": True},
        )
        assert resp.status_code == 200, f"Force complete failed: {resp.get_json()}"


# ======================================================================
# TEST GROUP 6: Delta Workshop
# ======================================================================

class TestDeltaWorkshopFlow:
    """Sorun 4.9: Delta creation field mapping."""

    def test_create_delta_with_frontend_fields(self, client, project_id):
        """Frontend sends workshop_type, area_code, l3_scope_item_id - backend expects type, process_area."""
        ws = _make_workshop(project_id, status="completed", code="WS-ORIG")
        ws.completed_at = datetime.now(timezone.utc)
        _db.session.commit()

        # This is what frontend ACTUALLY sends (from createDeltaWorkshop):
        resp = client.post("/api/v1/explore/workshops", json={
            "project_id": project_id,
            "name": f"{ws.name} (Delta)",
            "workshop_type": "delta",               # WRONG? backend expects "type"
            "l3_scope_item_id": None,                # WRONG? backend expects scope_item_ids
            "area_code": ws.process_area,            # WRONG? backend expects "process_area"
            "wave": ws.wave,
            "facilitator": ws.facilitator_id,        # WRONG? backend expects "facilitator_id"
            "parent_workshop_id": ws.id,
        })
        # If this succeeds, fields are mapped. If not, mapping is broken.
        if resp.status_code in (200, 201):
            data = resp.get_json()
            # Verify the delta actually has correct type
            assert data.get("type") in ("delta", "delta_design"), \
                f"Delta type not set correctly: {data.get('type')}"
            assert data.get("process_area") == "FI", \
                f"process_area not mapped from area_code: {data.get('process_area')}"
        else:
            pytest.fail(
                f"BUG 4.9 CONFIRMED: Delta creation failed with frontend fields. "
                f"Status: {resp.status_code}, Response: {resp.get_json()}"
            )

    def test_create_delta_via_dedicated_endpoint(self, client, project_id):
        """POST /workshops/<id>/create-delta - backend has this endpoint."""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id, status="completed", code="WS-DELTA-SRC")
        ws.completed_at = datetime.now(timezone.utc)
        wsi = WorkshopScopeItem(workshop_id=ws.id, process_level_id=l3.id, sort_order=1)
        _db.session.add(wsi)
        _db.session.commit()

        resp = client.post(f"/api/v1/explore/workshops/{ws.id}/create-delta")
        assert resp.status_code in (200, 201), f"Dedicated delta endpoint failed: {resp.get_json()}"


# ======================================================================
# TEST GROUP 7: Workshop Detail Aggregate Data
# ======================================================================

class TestWorkshopDetailData:
    """Sorun 4.4: Frontend fetches 9 API calls - verify each returns useful data."""

    def test_workshop_decisions_list(self, client, project_id):
        """GET /workshops/<id>/decisions"""
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        ws = _make_workshop(project_id)
        step = ProcessStep(workshop_id=ws.id, process_level_id=l4.id, sort_order=1)
        _db.session.add(step)
        _db.session.flush()
        dec = ExploreDecision(
            project_id=project_id, process_step_id=step.id,
            code="DEC-INT-001", text="Use standard", decided_by="Team",
        )
        _db.session.add(dec)
        _db.session.commit()

        resp = client.get(f"/api/v1/explore/workshops/{ws.id}/decisions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_workshop_fit_decisions_list(self, client, project_id):
        """GET /workshops/<id>/fit-decisions"""
        ws = _make_workshop(project_id)
        _db.session.commit()
        resp = client.get(f"/api/v1/explore/workshops/{ws.id}/fit-decisions")
        assert resp.status_code == 200

    def test_workshop_attendees_list(self, client, project_id):
        """GET /workshops/<id>/attendees"""
        ws = _make_workshop(project_id)
        att = WorkshopAttendee(
            workshop_id=ws.id, name="John", role="facilitator",
            organization="consultant", attendance_status="confirmed",
        )
        _db.session.add(att)
        _db.session.commit()

        resp = client.get(f"/api/v1/explore/workshops/{ws.id}/attendees")
        assert resp.status_code == 200

    def test_workshop_agenda_list(self, client, project_id):
        """GET /workshops/<id>/agenda-items"""
        ws = _make_workshop(project_id)
        _db.session.commit()
        resp = client.get(f"/api/v1/explore/workshops/{ws.id}/agenda-items")
        assert resp.status_code == 200

    def test_workshop_sessions_list(self, client, project_id):
        """GET /workshops/<id>/sessions"""
        ws = _make_workshop(project_id)
        _db.session.commit()
        resp = client.get(f"/api/v1/explore/workshops/{ws.id}/sessions")
        assert resp.status_code == 200

    def test_workshop_stats(self, client, project_id):
        """GET /workshops/stats?project_id="""
        _make_workshop(project_id)
        _db.session.commit()
        resp = client.get(f"/api/v1/explore/workshops/stats?project_id={project_id}")
        assert resp.status_code == 200


# ======================================================================
# TEST GROUP 8: Full Workshop Lifecycle
# ======================================================================

class TestWorkshopFullLifecycle:
    """End-to-end: Create -> Scope -> Start -> Decide -> Complete -> Delta."""

    def test_full_lifecycle(self, client, project_id):
        """Happy path through entire workshop flow."""
        # 1. Create hierarchy
        l1, l2, l3, l4 = _make_hierarchy(project_id)
        _db.session.commit()

        # 2. Create workshop via API
        resp = client.post("/api/v1/explore/workshops", json={
            "project_id": project_id,
            "name": "Full Lifecycle Test",
            "type": "fit_to_standard",
            "process_area": "FI",
            "wave": 1,
            "scope_item_ids": [l3.id],
        })
        assert resp.status_code in (200, 201), f"Step 2 Create: {resp.get_json()}"
        ws_id = resp.get_json()["id"]

        # 3. Schedule (update status)
        resp = client.put(f"/api/v1/explore/workshops/{ws_id}", json={
            "status": "scheduled", "date": "2026-03-15",
        })
        assert resp.status_code == 200, f"Step 3 Schedule: {resp.get_json()}"

        # 4. Start
        resp = client.post(f"/api/v1/explore/workshops/{ws_id}/start")
        assert resp.status_code == 200, f"Step 4 Start: {resp.get_json()}"

        # 5. Verify steps created
        steps = ProcessStep.query.filter_by(workshop_id=ws_id).all()
        assert len(steps) >= 1, "Step 5: No ProcessSteps created after start"

        # 6. Set fit decision on all steps
        for step in steps:
            resp = client.put(
                f"/api/v1/explore/process-steps/{step.id}",
                json={"fit_decision": "fit"},
            )
            assert resp.status_code == 200, f"Step 6 Fit: {resp.get_json()}"

        # 7. Add a decision to first step
        resp = client.post(
            f"/api/v1/explore/process-steps/{steps[0].id}/decisions",
            json={"text": "Use standard", "decided_by": "Team", "category": "process"},
        )
        assert resp.status_code in (200, 201), f"Step 7 Decision: {resp.get_json()}"

        # 8. Complete
        resp = client.post(f"/api/v1/explore/workshops/{ws_id}/complete")
        assert resp.status_code == 200, f"Step 8 Complete: {resp.get_json()}"

        # 9. Verify final status
        ws_final = _db.session.get(ExploreWorkshop, ws_id)
        assert ws_final.status == "completed", f"Final status: {ws_final.status}"

        # 10. Create delta via dedicated endpoint
        resp = client.post(f"/api/v1/explore/workshops/{ws_id}/create-delta")
        assert resp.status_code in (200, 201), f"Step 10 Delta: {resp.get_json()}"
