"""
F3 — Approval Workflow & Records unit tests.

Tests cover:
  - CRUD for approval workflows
  - Submit entity for approval
  - Approve/reject decisions
  - Rejection cascading (skip remaining stages)
  - Full approval → entity status "approved"
  - Pending approvals query
  - Entity approval status endpoint
"""
import pytest


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture()
def program(client):
    res = client.post("/api/v1/programs", json={"name": "Approval Test Program", "methodology": "agile"})
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def workflow(client, program):
    """Create a 2-stage approval workflow for test_case."""
    res = client.post(
        f"/api/v1/programs/{program['id']}/approval-workflows",
        json={
            "name": "TC Review & QA Approve",
            "entity_type": "test_case",
            "stages": [
                {"stage": 1, "role": "Reviewer", "required": True},
                {"stage": 2, "role": "QA Lead", "required": True},
            ],
        },
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def test_case(client, program):
    """Create a test case to use in approval flows."""
    res = client.post(
        f"/api/v1/programs/{program['id']}/testing/catalog",
        json={"title": "Approval Target TC", "test_type": "Manual", "test_layer": "regression"},
    )
    assert res.status_code == 201
    return res.get_json()


# ═════════════════════════════════════════════════════════════════════════
# WORKFLOW CRUD
# ═════════════════════════════════════════════════════════════════════════

class TestWorkflowCRUD:
    def test_create_workflow(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/approval-workflows",
            json={
                "name": "Plan Approval",
                "entity_type": "test_plan",
                "stages": [{"stage": 1, "role": "PM", "required": True}],
            },
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "Plan Approval"
        assert data["entity_type"] == "test_plan"
        assert len(data["stages"]) == 1

    def test_create_workflow_validation(self, client, program):
        # Missing name
        res = client.post(
            f"/api/v1/programs/{program['id']}/approval-workflows",
            json={"entity_type": "test_case", "stages": [{"stage": 1, "role": "R"}]},
        )
        assert res.status_code == 400
        assert "name" in res.get_json()["error"]

    def test_create_workflow_invalid_entity_type(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/approval-workflows",
            json={"name": "Bad", "entity_type": "invalid", "stages": [{"stage": 1, "role": "R"}]},
        )
        assert res.status_code == 400

    def test_create_workflow_empty_stages(self, client, program):
        res = client.post(
            f"/api/v1/programs/{program['id']}/approval-workflows",
            json={"name": "Empty", "entity_type": "test_case", "stages": []},
        )
        assert res.status_code == 400

    def test_list_workflows(self, client, program, workflow):
        res = client.get(f"/api/v1/programs/{program['id']}/approval-workflows")
        assert res.status_code == 200
        items = res.get_json()
        assert len(items) >= 1
        assert items[0]["name"] == workflow["name"]

    def test_list_workflows_filter_entity_type(self, client, program, workflow):
        res = client.get(f"/api/v1/programs/{program['id']}/approval-workflows?entity_type=test_plan")
        assert res.status_code == 200
        assert len(res.get_json()) == 0  # workflow is test_case

    def test_update_workflow(self, client, workflow):
        res = client.put(
            f"/api/v1/approval-workflows/{workflow['id']}",
            json={"name": "Updated Name", "is_active": False},
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["name"] == "Updated Name"
        assert data["is_active"] is False

    def test_update_workflow_not_found(self, client):
        res = client.put("/api/v1/approval-workflows/99999", json={"name": "X"})
        assert res.status_code == 404

    def test_delete_workflow(self, client, workflow):
        res = client.delete(f"/api/v1/approval-workflows/{workflow['id']}")
        assert res.status_code == 200
        assert res.get_json()["deleted"] is True

        # Verify deleted
        res2 = client.get(f"/api/v1/approval-workflows/{workflow['id']}")
        assert res2.status_code in (404, 405)

    def test_delete_workflow_not_found(self, client):
        res = client.delete("/api/v1/approval-workflows/99999")
        assert res.status_code == 404


# ═════════════════════════════════════════════════════════════════════════
# SUBMIT & DECIDE
# ═════════════════════════════════════════════════════════════════════════

class TestApprovalFlow:
    def test_submit_for_approval(self, client, workflow, test_case):
        res = client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data["submitted"] is True
        assert len(data["records"]) == 2  # 2 stages
        assert data["records"][0]["status"] == "pending"

    def test_submit_duplicate_blocked(self, client, workflow, test_case):
        client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        })
        # Submit again should fail
        res = client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        })
        assert res.status_code == 409

    def test_submit_no_workflow(self, client, program, test_case):
        # No workflow created for this program
        res = client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_plan",
            "entity_id": test_case["id"],
        })
        assert res.status_code == 404  # entity not found (it's a test_case, not test_plan)

    def test_approve_stage(self, client, workflow, test_case):
        sub = client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        }).get_json()
        rec_id = sub["records"][0]["id"]

        res = client.post(f"/api/v1/approvals/{rec_id}/decide", json={
            "decision": "approved",
            "comment": "Looks good",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "approved"
        assert data["comment"] == "Looks good"

    def test_full_approval_updates_entity(self, client, workflow, test_case):
        sub = client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        }).get_json()

        # Approve stage 1
        client.post(f"/api/v1/approvals/{sub['records'][0]['id']}/decide", json={
            "decision": "approved",
        })
        # Approve stage 2
        client.post(f"/api/v1/approvals/{sub['records'][1]['id']}/decide", json={
            "decision": "approved",
        })

        # Verify entity status is now approved
        tc = client.get(f"/api/v1/testing/catalog/{test_case['id']}").get_json()
        assert tc["status"] == "approved"

    def test_reject_cascades(self, client, workflow, test_case):
        sub = client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        }).get_json()

        # Reject stage 1
        res = client.post(f"/api/v1/approvals/{sub['records'][0]['id']}/decide", json={
            "decision": "rejected",
            "comment": "Needs rework",
        })
        assert res.status_code == 200

        # Stage 2 should be auto-skipped
        status = client.get(f"/api/v1/test_case/{test_case['id']}/approval-status").get_json()
        assert status["status"] == "rejected"
        skipped = [r for r in status["records"] if r["status"] == "skipped"]
        assert len(skipped) == 1

    def test_reject_resets_entity_status(self, client, workflow, test_case):
        sub = client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        }).get_json()

        client.post(f"/api/v1/approvals/{sub['records'][0]['id']}/decide", json={
            "decision": "rejected",
        })

        tc = client.get(f"/api/v1/testing/catalog/{test_case['id']}").get_json()
        assert tc["status"] == "draft"

    def test_decide_invalid_decision(self, client, workflow, test_case):
        sub = client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        }).get_json()

        res = client.post(f"/api/v1/approvals/{sub['records'][0]['id']}/decide", json={
            "decision": "maybe",
        })
        assert res.status_code == 400

    def test_decide_already_decided(self, client, workflow, test_case):
        sub = client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        }).get_json()

        client.post(f"/api/v1/approvals/{sub['records'][0]['id']}/decide", json={
            "decision": "approved",
        })
        # Try again
        res = client.post(f"/api/v1/approvals/{sub['records'][0]['id']}/decide", json={
            "decision": "approved",
        })
        assert res.status_code == 409


# ═════════════════════════════════════════════════════════════════════════
# QUERIES
# ═════════════════════════════════════════════════════════════════════════

class TestApprovalQueries:
    def test_pending_approvals(self, client, workflow, test_case):
        client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        })

        res = client.get("/api/v1/approvals/pending")
        assert res.status_code == 200
        items = res.get_json()
        assert len(items) >= 2  # 2 stages pending

    def test_pending_filter_by_entity_type(self, client, workflow, test_case):
        client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        })

        res = client.get("/api/v1/approvals/pending?entity_type=test_plan")
        assert res.status_code == 200
        assert len(res.get_json()) == 0

    def test_entity_approval_status_not_submitted(self, client, test_case):
        res = client.get(f"/api/v1/test_case/{test_case['id']}/approval-status")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "not_submitted"

    def test_entity_approval_status_pending(self, client, workflow, test_case):
        client.post("/api/v1/approvals/submit", json={
            "entity_type": "test_case",
            "entity_id": test_case["id"],
        })

        res = client.get(f"/api/v1/test_case/{test_case['id']}/approval-status")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "pending"
        assert len(data["records"]) == 2

    def test_entity_approval_status_invalid_type(self, client):
        res = client.get("/api/v1/invalid/1/approval-status")
        assert res.status_code == 400
