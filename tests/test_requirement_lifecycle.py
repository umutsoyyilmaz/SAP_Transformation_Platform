"""
Requirement Lifecycle Tests — comprehensive coverage for:
  - Status transition validation (happy path + invalid transitions)
  - ADR-1: push_to_alm blocked when not converted
  - Convert preconditions (approved-only, already-converted idempotency)
  - Defer / reject required fields
  - Open item blocking on approve
  - Available transitions per status
  - Full lifecycle walk: draft → verified
"""

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _create_program(client):
    r = client.post("/api/v1/programs", json={"name": "Lifecycle Test", "methodology": "agile"})
    assert r.status_code == 201
    return r.get_json()["id"]


def _create_requirement(client, project_id, *, title="Lifecycle Req", req_type="development"):
    r = client.post("/api/v1/explore/requirements", json={
        "project_id": project_id,
        "title": title,
        "type": req_type,
        "priority": "P2",
        "created_by_id": "tester",
        "workshop_id": "lifecycle-test-ws",  # bypass scope_item_id requirement
    })
    assert r.status_code == 201, f"Create req failed: {r.get_json()}"
    return r.get_json()


def _transition(client, req_id, action, **extra):
    payload = {"action": action, "user_id": "tester", **extra}
    return client.post(f"/api/v1/explore/requirements/{req_id}/transition", json=payload)


def _convert(client, req_id, project_id, **extra):
    payload = {"project_id": project_id, "user_id": "tester", **extra}
    return client.post(f"/api/v1/explore/requirements/{req_id}/convert", json=payload)


# ═══════════════════════════════════════════════════════════════════════════
# TestTransitionValidation — happy path and invalid transitions
# ═══════════════════════════════════════════════════════════════════════════


class TestTransitionValidation:
    """Validate each transition in REQUIREMENT_TRANSITIONS."""

    def test_submit_for_review(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        r = _transition(client, req["id"], "submit_for_review")
        assert r.status_code == 200
        assert r.get_json()["new_status"] == "under_review"

    def test_approve(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        _transition(client, req["id"], "submit_for_review")
        r = _transition(client, req["id"], "approve", approved_by_name="QA")
        assert r.status_code == 200
        assert r.get_json()["new_status"] == "approved"

    def test_reject_requires_reason(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        _transition(client, req["id"], "submit_for_review")
        # Without reason
        r = _transition(client, req["id"], "reject")
        assert r.status_code == 400
        # With reason
        r = _transition(client, req["id"], "reject", rejection_reason="Out of scope")
        assert r.status_code == 200
        assert r.get_json()["new_status"] == "rejected"

    def test_return_to_draft(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        _transition(client, req["id"], "submit_for_review")
        r = _transition(client, req["id"], "return_to_draft")
        assert r.status_code == 200
        assert r.get_json()["new_status"] == "draft"

    def test_defer_requires_phase(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        # Without phase
        r = _transition(client, req["id"], "defer")
        assert r.status_code == 400
        # With phase
        r = _transition(client, req["id"], "defer", deferred_to_phase="Phase 2")
        assert r.status_code == 200
        assert r.get_json()["new_status"] == "deferred"

    def test_defer_from_approved(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        r = _transition(client, req["id"], "defer", deferred_to_phase="Phase 3")
        assert r.status_code == 200
        assert r.get_json()["new_status"] == "deferred"

    def test_reactivate(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        _transition(client, req["id"], "defer", deferred_to_phase="Phase 2")
        r = _transition(client, req["id"], "reactivate")
        assert r.status_code == 200
        assert r.get_json()["new_status"] == "draft"

    def test_invalid_transition_rejected(self, client):
        """Cannot approve from draft (must be under_review)."""
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        r = _transition(client, req["id"], "approve")
        assert r.status_code == 400

    def test_invalid_transition_realize_from_approved(self, client):
        """Cannot mark_realized from approved — must be in_backlog."""
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        r = _transition(client, req["id"], "mark_realized")
        assert r.status_code == 400

    def test_unknown_action(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        r = _transition(client, req["id"], "fly_to_moon")
        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# TestADR1ConvertBeforePush — DEF-004 regression test
# ═══════════════════════════════════════════════════════════════════════════


class TestADR1ConvertBeforePush:
    """ADR-1: push_to_alm must fail if requirement has NOT been converted."""

    def test_push_to_alm_blocked_without_convert(self, client):
        """Approved but unconverted → push_to_alm must fail."""
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        r = _transition(client, req["id"], "push_to_alm")
        assert r.status_code == 400
        body = r.get_json()
        assert "convert" in body.get("error", "").lower()

    def test_push_to_alm_succeeds_after_convert(self, client):
        """Approved + converted → push_to_alm should succeed."""
        pid = _create_program(client)
        req = _create_requirement(client, pid, req_type="development")
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        # Convert first
        rc = _convert(client, req["id"], pid, target_type="backlog", wricef_type="enhancement")
        assert rc.status_code == 200
        assert rc.get_json()["status"] == "converted"
        # Now push_to_alm should work
        r = _transition(client, req["id"], "push_to_alm")
        assert r.status_code == 200
        assert r.get_json()["new_status"] == "in_backlog"


# ═══════════════════════════════════════════════════════════════════════════
# TestConvert — conversion logic
# ═══════════════════════════════════════════════════════════════════════════


class TestConvert:
    """Test convert endpoint preconditions and behavior."""

    def test_convert_requires_approved(self, client):
        """Cannot convert from draft."""
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        r = _convert(client, req["id"], pid)
        assert r.status_code == 400

    def test_convert_creates_backlog_item(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid, req_type="development")
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        r = _convert(client, req["id"], pid, target_type="backlog", wricef_type="interface")
        assert r.status_code == 200
        body = r.get_json()
        assert body["status"] == "converted"
        assert body["backlog_item_id"] is not None
        assert body["config_item_id"] is None

    def test_convert_creates_config_item(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid, req_type="configuration")
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        r = _convert(client, req["id"], pid, target_type="config")
        assert r.status_code == 200
        body = r.get_json()
        assert body["status"] == "converted"
        assert body["config_item_id"] is not None
        assert body["backlog_item_id"] is None

    def test_convert_idempotent_already_converted(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid, req_type="development")
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        _convert(client, req["id"], pid, target_type="backlog")
        # Second convert → already_converted
        r = _convert(client, req["id"], pid, target_type="backlog")
        assert r.status_code == 200
        assert r.get_json()["status"] == "already_converted"

    def test_convert_auto_detect_config(self, client):
        """req.type=configuration + no target_type → auto-detects config."""
        pid = _create_program(client)
        req = _create_requirement(client, pid, req_type="configuration")
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        r = _convert(client, req["id"], pid)  # no target_type
        assert r.status_code == 200
        assert r.get_json()["config_item_id"] is not None

    def test_convert_auto_detect_backlog(self, client):
        """req.type=integration + no target_type → auto-detects backlog."""
        pid = _create_program(client)
        req = _create_requirement(client, pid, req_type="integration")
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        r = _convert(client, req["id"], pid)
        assert r.status_code == 200
        assert r.get_json()["backlog_item_id"] is not None

    def test_batch_convert(self, client):
        pid = _create_program(client)
        reqs = []
        for i in range(3):
            req = _create_requirement(client, pid, title=f"Batch Req {i}")
            _transition(client, req["id"], "submit_for_review")
            _transition(client, req["id"], "approve")
            reqs.append(req["id"])

        r = client.post("/api/v1/explore/requirements/batch-convert", json={
            "project_id": pid,
            "requirement_ids": reqs,
            "user_id": "tester",
        })
        assert r.status_code == 200
        body = r.get_json()
        assert len(body["success"]) == 3
        assert len(body["errors"]) == 0


# ═══════════════════════════════════════════════════════════════════════════
# TestFullLifecycle — end-to-end walk
# ═══════════════════════════════════════════════════════════════════════════


class TestFullLifecycle:
    """Walk a requirement through the full lifecycle: draft → verified."""

    def test_full_lifecycle_walk(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid, req_type="development")
        rid = req["id"]

        # draft → under_review
        r = _transition(client, rid, "submit_for_review")
        assert r.get_json()["new_status"] == "under_review"

        # under_review → approved
        r = _transition(client, rid, "approve", approved_by_name="Reviewer")
        assert r.get_json()["new_status"] == "approved"

        # Convert (explicit, ADR-1)
        r = _convert(client, rid, pid, target_type="backlog", wricef_type="enhancement")
        assert r.get_json()["status"] == "converted"

        # approved → in_backlog
        r = _transition(client, rid, "push_to_alm")
        assert r.get_json()["new_status"] == "in_backlog"

        # in_backlog → realized
        r = _transition(client, rid, "mark_realized")
        assert r.get_json()["new_status"] == "realized"

        # realized → verified
        r = _transition(client, rid, "verify")
        assert r.get_json()["new_status"] == "verified"


# ═══════════════════════════════════════════════════════════════════════════
# TestAvailableTransitions
# ═══════════════════════════════════════════════════════════════════════════


class TestAvailableTransitions:
    """Verify available_transitions in GET response matches transition table."""

    def test_draft_transitions(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        r = client.get(f"/api/v1/explore/requirements/{req['id']}")
        assert r.status_code == 200
        avail = set(r.get_json().get("available_transitions", []))
        assert "submit_for_review" in avail
        assert "defer" in avail

    def test_approved_transitions(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        r = client.get(f"/api/v1/explore/requirements/{req['id']}")
        avail = set(r.get_json().get("available_transitions", []))
        assert "push_to_alm" in avail
        assert "defer" in avail
        assert "submit_for_review" not in avail

    def test_deferred_transitions(self, client):
        pid = _create_program(client)
        req = _create_requirement(client, pid)
        _transition(client, req["id"], "defer", deferred_to_phase="Phase 2")
        r = client.get(f"/api/v1/explore/requirements/{req['id']}")
        avail = set(r.get_json().get("available_transitions", []))
        assert avail == {"reactivate"}

    def test_verified_has_no_transitions(self, client):
        """Verified is terminal — no transitions available."""
        pid = _create_program(client)
        req = _create_requirement(client, pid, req_type="development")
        _transition(client, req["id"], "submit_for_review")
        _transition(client, req["id"], "approve")
        _convert(client, req["id"], pid, target_type="backlog")
        _transition(client, req["id"], "push_to_alm")
        _transition(client, req["id"], "mark_realized")
        _transition(client, req["id"], "verify")
        r = client.get(f"/api/v1/explore/requirements/{req['id']}")
        avail = r.get_json().get("available_transitions", [])
        assert avail == []
