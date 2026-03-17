"""
FAZ 8 — Exploratory Testing & Evidence Capture — Tests
~48 tests covering sessions, notes, timer events, evidence CRUD, set-primary, model integrity.
"""

import pytest


# ── helpers ──

API = "/api/v1"


def _post(client, url, data=None):
    return client.post(API + url, json=data or {})


def _get(client, url):
    return client.get(API + url)


def _put(client, url, data=None):
    return client.put(API + url, json=data or {})


def _delete(client, url):
    return client.delete(API + url)


# ── fixtures ──

@pytest.fixture()
def program(client):
    res = _post(client, "/programs", {"name": "F8 Test Program"})
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def test_case(client, program):
    res = _post(
        client,
        f"/programs/{program['id']}/testing/catalog",
        {"title": "F8 TC", "test_layer": "regression"},
    )
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def session(client, program):
    res = _post(
        client,
        f"/programs/{program['id']}/exploratory-sessions",
        {
            "charter": "Test login flows",
            "scope": "auth module",
            "time_box": 45,
            "tester_name": "F8 Tester",
            "environment": "staging",
        },
    )
    assert res.status_code == 201
    return res.get_json()["session"]


@pytest.fixture()
def execution(client, program, test_case):
    """Create plan → cycle → execution chain."""
    plan_res = _post(
        client,
        f"/programs/{program['id']}/testing/plans",
        {"name": "F8 Plan", "test_layer": "regression"},
    )
    assert plan_res.status_code == 201, f"Plan creation failed: {plan_res.get_json()}"
    plan = plan_res.get_json()

    cycle_res = _post(
        client,
        f"/testing/plans/{plan['id']}/cycles",
        {"name": "F8 Cycle"},
    )
    assert cycle_res.status_code == 201, f"Cycle creation failed: {cycle_res.get_json()}"
    cycle = cycle_res.get_json()

    exec_res = _post(
        client,
        f"/testing/cycles/{cycle['id']}/executions",
        {"test_case_id": test_case["id"]},
    )
    assert exec_res.status_code == 201, f"Execution creation failed: {exec_res.get_json()}"
    return exec_res.get_json()


@pytest.fixture()
def step_result(client, execution):
    res = _post(
        client,
        f"/testing/executions/{execution['id']}/step-results",
        {"step_no": 1, "result": "pass", "actual_result": "OK"},
    )
    assert res.status_code == 201
    return res.get_json()


# ═══════════════════════════════════════════════════════════════
#  8.1  Exploratory Sessions
# ═══════════════════════════════════════════════════════════════


class TestExploratorySessions:
    def test_create_session(self, client, program):
        res = _post(
            client,
            f"/programs/{program['id']}/exploratory-sessions",
            {"charter": "Explore checkout", "time_box": 30},
        )
        assert res.status_code == 201
        s = res.get_json()["session"]
        assert s["charter"] == "Explore checkout"
        assert s["status"] == "draft"
        assert s["time_box"] == 30

    def test_create_session_requires_charter(self, client, program):
        res = _post(
            client,
            f"/programs/{program['id']}/exploratory-sessions",
            {"scope": "payments"},
        )
        assert res.status_code == 400

    def test_list_sessions(self, client, program, session):
        res = _get(client, f"/programs/{program['id']}/exploratory-sessions")
        assert res.status_code == 200
        data = res.get_json()
        assert data["total"] >= 1

    def test_list_sessions_filter_status(self, client, program, session):
        res = _get(client, f"/programs/{program['id']}/exploratory-sessions?status=draft")
        assert res.status_code == 200
        for s in res.get_json()["sessions"]:
            assert s["status"] == "draft"

    def test_get_session(self, client, session):
        res = _get(client, f"/exploratory-sessions/{session['id']}")
        assert res.status_code == 200
        assert res.get_json()["session"]["charter"] == session["charter"]

    def test_get_session_with_notes(self, client, session):
        res = _get(client, f"/exploratory-sessions/{session['id']}?include_notes=true")
        assert res.status_code == 200
        assert "session_notes" in res.get_json()["session"]

    def test_update_session(self, client, session):
        res = _put(
            client,
            f"/exploratory-sessions/{session['id']}",
            {"charter": "Updated charter", "scope": "payments"},
        )
        assert res.status_code == 200
        assert res.get_json()["session"]["charter"] == "Updated charter"

    def test_delete_session(self, client, session):
        res = _delete(client, f"/exploratory-sessions/{session['id']}")
        assert res.status_code == 200
        res2 = _get(client, f"/exploratory-sessions/{session['id']}")
        assert res2.status_code == 404


class TestSessionTimer:
    def test_start_session(self, client, session):
        res = _post(client, f"/exploratory-sessions/{session['id']}/start")
        assert res.status_code == 200
        s = res.get_json()["session"]
        assert s["status"] == "active"
        assert s["started_at"] is not None

    def test_pause_session(self, client, session):
        _post(client, f"/exploratory-sessions/{session['id']}/start")
        res = _post(client, f"/exploratory-sessions/{session['id']}/pause")
        assert res.status_code == 200
        assert res.get_json()["session"]["status"] == "paused"

    def test_complete_session(self, client, session):
        _post(client, f"/exploratory-sessions/{session['id']}/start")
        res = _post(client, f"/exploratory-sessions/{session['id']}/complete")
        assert res.status_code == 200
        s = res.get_json()["session"]
        assert s["status"] == "completed"
        assert s["ended_at"] is not None

    def test_start_completed_session_fails(self, client, session):
        _post(client, f"/exploratory-sessions/{session['id']}/start")
        _post(client, f"/exploratory-sessions/{session['id']}/complete")
        res = _post(client, f"/exploratory-sessions/{session['id']}/start")
        assert res.status_code == 400

    def test_pause_draft_session_fails(self, client, session):
        res = _post(client, f"/exploratory-sessions/{session['id']}/pause")
        assert res.status_code == 400

    def test_resume_after_pause(self, client, session):
        _post(client, f"/exploratory-sessions/{session['id']}/start")
        _post(client, f"/exploratory-sessions/{session['id']}/pause")
        res = _post(client, f"/exploratory-sessions/{session['id']}/start")
        assert res.status_code == 200
        assert res.get_json()["session"]["status"] == "active"


# ═══════════════════════════════════════════════════════════════
#  8.1b  Exploratory Notes
# ═══════════════════════════════════════════════════════════════


class TestExploratoryNotes:
    def test_create_note(self, client, session):
        res = _post(
            client,
            f"/exploratory-sessions/{session['id']}/notes",
            {"content": "Login btn slow", "note_type": "observation"},
        )
        assert res.status_code == 201
        n = res.get_json()["note"]
        assert n["content"] == "Login btn slow"
        assert n["note_type"] == "observation"

    def test_create_note_requires_content(self, client, session):
        res = _post(
            client,
            f"/exploratory-sessions/{session['id']}/notes",
            {"note_type": "bug"},
        )
        assert res.status_code == 400

    def test_list_notes(self, client, session):
        _post(client, f"/exploratory-sessions/{session['id']}/notes", {"content": "n1"})
        _post(client, f"/exploratory-sessions/{session['id']}/notes", {"content": "n2"})
        res = _get(client, f"/exploratory-sessions/{session['id']}/notes")
        assert res.status_code == 200
        assert len(res.get_json()["notes"]) >= 2

    def test_update_note(self, client, session):
        cr = _post(
            client,
            f"/exploratory-sessions/{session['id']}/notes",
            {"content": "orig"},
        )
        nid = cr.get_json()["note"]["id"]
        res = _put(client, f"/exploratory-notes/{nid}", {"content": "updated"})
        assert res.status_code == 200
        assert res.get_json()["note"]["content"] == "updated"

    def test_delete_note(self, client, session):
        cr = _post(
            client,
            f"/exploratory-sessions/{session['id']}/notes",
            {"content": "del me"},
        )
        nid = cr.get_json()["note"]["id"]
        res = _delete(client, f"/exploratory-notes/{nid}")
        assert res.status_code == 200

    def test_link_note_to_defect(self, client, session):
        cr = _post(
            client,
            f"/exploratory-sessions/{session['id']}/notes",
            {"content": "bug found", "note_type": "bug"},
        )
        nid = cr.get_json()["note"]["id"]
        res = _post(client, f"/exploratory-notes/{nid}/link-defect", {"defect_id": 999})
        assert res.status_code == 200
        assert res.get_json()["note"]["linked_defect_id"] == 999

    def test_link_defect_requires_id(self, client, session):
        cr = _post(
            client,
            f"/exploratory-sessions/{session['id']}/notes",
            {"content": "x"},
        )
        nid = cr.get_json()["note"]["id"]
        res = _post(client, f"/exploratory-notes/{nid}/link-defect", {})
        assert res.status_code == 400


# ═══════════════════════════════════════════════════════════════
#  8.2  Execution Evidence
# ═══════════════════════════════════════════════════════════════


class TestExecutionEvidence:
    def test_add_execution_evidence(self, client, execution):
        res = _post(
            client,
            f"/testing/executions/{execution['id']}/evidence",
            {
                "evidence_type": "screenshot",
                "file_name": "step3.png",
                "file_path": "/storage/evidence/step3.png",
                "file_size": 204800,
                "mime_type": "image/png",
                "description": "Post-login state",
            },
        )
        assert res.status_code == 201
        ev = res.get_json()["evidence"]
        assert ev["file_name"] == "step3.png"
        assert ev["evidence_type"] == "screenshot"

    def test_list_execution_evidence(self, client, execution):
        _post(
            client,
            f"/testing/executions/{execution['id']}/evidence",
            {"evidence_type": "screenshot", "file_name": "a.png"},
        )
        _post(
            client,
            f"/testing/executions/{execution['id']}/evidence",
            {"evidence_type": "log", "file_name": "b.log"},
        )
        res = _get(client, f"/testing/executions/{execution['id']}/evidence")
        assert res.status_code == 200
        assert len(res.get_json()["evidence"]) >= 2

    def test_get_evidence(self, client, execution):
        cr = _post(
            client,
            f"/testing/executions/{execution['id']}/evidence",
            {"evidence_type": "document", "file_name": "doc.pdf"},
        )
        eid = cr.get_json()["evidence"]["id"]
        res = _get(client, f"/evidence/{eid}")
        assert res.status_code == 200
        assert res.get_json()["evidence"]["file_name"] == "doc.pdf"

    def test_update_evidence(self, client, execution):
        cr = _post(
            client,
            f"/testing/executions/{execution['id']}/evidence",
            {"evidence_type": "screenshot", "file_name": "old.png"},
        )
        eid = cr.get_json()["evidence"]["id"]
        res = _put(
            client,
            f"/evidence/{eid}",
            {"file_name": "new.png", "description": "Updated"},
        )
        assert res.status_code == 200
        assert res.get_json()["evidence"]["file_name"] == "new.png"

    def test_delete_evidence(self, client, execution):
        cr = _post(
            client,
            f"/testing/executions/{execution['id']}/evidence",
            {"evidence_type": "video", "file_name": "rec.mp4"},
        )
        eid = cr.get_json()["evidence"]["id"]
        res = _delete(client, f"/evidence/{eid}")
        assert res.status_code == 200
        res2 = _get(client, f"/evidence/{eid}")
        assert res2.status_code == 404

    def test_evidence_404(self, client):
        res = _get(client, "/evidence/99999")
        assert res.status_code == 404


class TestStepLevelEvidence:
    def test_add_step_evidence(self, client, step_result):
        res = _post(
            client,
            f"/testing/step-results/{step_result['id']}/evidence",
            {"evidence_type": "screenshot", "file_name": "s1.png"},
        )
        assert res.status_code == 201
        assert res.get_json()["evidence"]["step_result_id"] == step_result["id"]

    def test_list_step_evidence(self, client, step_result):
        _post(
            client,
            f"/testing/step-results/{step_result['id']}/evidence",
            {"evidence_type": "screenshot", "file_name": "s1.png"},
        )
        res = _get(client, f"/testing/step-results/{step_result['id']}/evidence")
        assert res.status_code == 200
        assert len(res.get_json()["evidence"]) >= 1

    def test_step_evidence_404(self, client):
        res = _get(client, "/testing/step-results/99999/evidence")
        assert res.status_code == 404


class TestSetPrimaryEvidence:
    def test_set_primary(self, client, execution):
        cr1 = _post(
            client,
            f"/testing/executions/{execution['id']}/evidence",
            {"evidence_type": "screenshot", "file_name": "a.png"},
        )
        cr2 = _post(
            client,
            f"/testing/executions/{execution['id']}/evidence",
            {"evidence_type": "screenshot", "file_name": "b.png"},
        )
        eid1 = cr1.get_json()["evidence"]["id"]
        eid2 = cr2.get_json()["evidence"]["id"]

        # Set first as primary
        res = _post(client, f"/evidence/{eid1}/set-primary")
        assert res.status_code == 200
        assert res.get_json()["evidence"]["is_primary"] is True

        # Set second as primary — first should be unset
        res2 = _post(client, f"/evidence/{eid2}/set-primary")
        assert res2.status_code == 200
        assert res2.get_json()["evidence"]["is_primary"] is True

        # Verify first is no longer primary
        check = _get(client, f"/evidence/{eid1}")
        assert check.get_json()["evidence"]["is_primary"] is False

    def test_set_primary_404(self, client):
        res = _post(client, "/evidence/99999/set-primary")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  Model Integrity
# ═══════════════════════════════════════════════════════════════


class TestModelIntegrity:
    def test_session_to_dict(self, client, session):
        res = _get(client, f"/exploratory-sessions/{session['id']}")
        s = res.get_json()["session"]
        required = {"id", "charter", "status", "time_box", "tester_name", "environment"}
        assert required.issubset(set(s.keys()))

    def test_note_to_dict(self, client, session):
        cr = _post(
            client,
            f"/exploratory-sessions/{session['id']}/notes",
            {"content": "test", "note_type": "idea"},
        )
        n = cr.get_json()["note"]
        required = {"id", "session_id", "note_type", "content", "timestamp"}
        assert required.issubset(set(n.keys()))

    def test_evidence_to_dict(self, client, execution):
        cr = _post(
            client,
            f"/testing/executions/{execution['id']}/evidence",
            {
                "evidence_type": "log",
                "file_name": "app.log",
                "file_size": 1024,
                "mime_type": "text/plain",
            },
        )
        ev = cr.get_json()["evidence"]
        required = {
            "id", "evidence_type", "file_name", "file_size",
            "mime_type", "captured_at", "is_primary",
        }
        assert required.issubset(set(ev.keys()))

    def test_session_cascade_delete(self, client, program, session):
        # Add notes
        _post(client, f"/exploratory-sessions/{session['id']}/notes", {"content": "n1"})
        _post(client, f"/exploratory-sessions/{session['id']}/notes", {"content": "n2"})
        # Delete session
        res = _delete(client, f"/exploratory-sessions/{session['id']}")
        assert res.status_code == 200
        # Notes should be gone (session 404)
        res2 = _get(client, f"/exploratory-sessions/{session['id']}/notes")
        assert res2.status_code == 404

    def test_evidence_execution_link(self, client, execution):
        cr = _post(
            client,
            f"/testing/executions/{execution['id']}/evidence",
            {"evidence_type": "screenshot", "file_name": "linked.png"},
        )
        ev = cr.get_json()["evidence"]
        assert ev["execution_id"] == execution["id"]
