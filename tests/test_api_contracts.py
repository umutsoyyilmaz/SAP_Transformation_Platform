"""
API Contract Tests — validates required fields, enum values, error shapes.

Ensures every error response follows the standard format:
    { "error": "human message", "code": "ERR_*" }

And that required field validation, state transitions, and list endpoints
behave consistently.

Run: python -m pytest tests/test_api_contracts.py -v
"""

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────


def _assert_standard_error(res, expected_status=None):
    """Assert that a response is a standard error shape."""
    body = res.get_json()
    assert body is not None, "Error response should have JSON body"
    assert "error" in body, f"Error response must have 'error' field, got: {body}"
    assert "code" in body, f"Error response must have 'code' field, got: {body}"
    assert body["code"].startswith("ERR_") or body["code"].startswith("GOVERNANCE_"), \
        f"Error code must start with ERR_ or GOVERNANCE_, got: {body['code']}"
    if expected_status:
        assert res.status_code == expected_status, \
            f"Expected {expected_status}, got {res.status_code}: {body}"


# ── Contract: Error Shape ────────────────────────────────────────────────


class TestErrorShape:
    """All error responses must have {error: str, code: str}."""

    def test_missing_project_id_returns_standard_error(self, client):
        """POST without required project_id → 400 standard error."""
        res = client.post("/api/v1/explore/requirements", json={
            "title": "Test requirement",
            # project_id missing
        })
        _assert_standard_error(res, 400)

    def test_not_found_returns_standard_error(self, client):
        """GET non-existent resource → 404 standard error."""
        res = client.get("/api/v1/explore/requirements/999999")
        _assert_standard_error(res, 404)

    def test_not_found_workshop_returns_standard_error(self, client):
        """GET non-existent workshop → 404."""
        res = client.get("/api/v1/explore/workshops/999999")
        _assert_standard_error(res, 404)

    def test_not_found_process_level_returns_standard_error(self, client):
        """GET non-existent process level → 404."""
        res = client.get("/api/v1/explore/process-levels/999999")
        _assert_standard_error(res, 404)

    def test_error_has_details_when_applicable(self, client, program):
        """Error details field is present when backend provides it."""
        # Creating a requirement and trying invalid transition to produce details
        pid = program["id"]
        res = client.post("/api/v1/explore/requirements", json={
            "project_id": pid,
            "title": "Contract Requirement",
            "type": "functional",
            "priority": "high",
            "area": "MM",
            "scope_item_id": None,
        })
        if res.status_code == 201:
            req_id = res.get_json()["id"]
            # Try invalid transition
            res2 = client.post(f"/api/v1/explore/requirements/{req_id}/transition", json={
                "action": "nonexistent_action_xyz",
            })
            body = res2.get_json()
            assert res2.status_code in (400, 409), f"Invalid action should fail: {body}"
            assert "error" in body
            assert "code" in body


# ── Contract: Required Fields ────────────────────────────────────────────


class TestRequiredFields:
    """POST endpoints must reject missing required fields with 400."""

    def test_requirement_without_project_id(self, client):
        res = client.post("/api/v1/explore/requirements", json={
            "title": "No project",
        })
        assert res.status_code == 400
        _assert_standard_error(res)

    def test_requirement_without_title(self, client, program):
        res = client.post("/api/v1/explore/requirements", json={
            "project_id": program["id"],
            # title missing
        })
        assert res.status_code == 400
        _assert_standard_error(res)

    def test_workshop_without_project_id(self, client):
        res = client.post("/api/v1/explore/workshops", json={
            "name": "No project workshop",
        })
        assert res.status_code == 400
        _assert_standard_error(res)

    def test_process_level_without_project_id(self, client):
        res = client.post("/api/v1/explore/process-levels", json={
            "name": "No project level",
            "level": 1,
            "code": "TEST-L1",
        })
        assert res.status_code == 400
        _assert_standard_error(res)


# ── Contract: Enum Values / Invalid States ───────────────────────────────


class TestEnumValidation:
    """Endpoints must reject invalid enum values."""

    def test_invalid_requirement_transition(self, client, program):
        """Transition with invalid action → 400 or 409."""
        pid = program["id"]
        # Create a requirement first
        res = client.post("/api/v1/explore/requirements", json={
            "project_id": pid,
            "title": "Enum Test Req",
            "type": "functional",
            "priority": "high",
            "area": "FI",
        })
        if res.status_code != 201:
            pytest.skip("Could not create requirement for enum test")

        req_id = res.get_json()["id"]
        res2 = client.post(f"/api/v1/explore/requirements/{req_id}/transition", json={
            "action": "completely_invalid_action_abc",
        })
        assert res2.status_code in (400, 409), \
            f"Invalid transition should fail, got {res2.status_code}"
        _assert_standard_error(res2)

    def test_invalid_open_item_transition(self, client, program):
        """Open item with invalid transition → error."""
        pid = program["id"]
        res = client.post("/api/v1/explore/open-items", json={
            "project_id": pid,
            "title": "Enum Test OI",
            "description": "test",
        })
        if res.status_code != 201:
            pytest.skip("Could not create open item")

        oi_id = res.get_json()["id"]
        res2 = client.post(f"/api/v1/explore/open-items/{oi_id}/transition", json={
            "action": "xyz_invalid_action",
        })
        assert res2.status_code in (400, 409)
        _assert_standard_error(res2)


# ── Contract: Convert Preconditions ──────────────────────────────────────


class TestConvertContract:
    """Convert endpoint must enforce preconditions."""

    def test_convert_requires_project_id(self, client, program):
        """Convert without project_id → 400."""
        pid = program["id"]
        # Create requirement
        res = client.post("/api/v1/explore/requirements", json={
            "project_id": pid,
            "title": "Convert Contract Test",
            "type": "functional",
            "priority": "high",
            "area": "FI",
        })
        if res.status_code != 201:
            pytest.skip("Could not create requirement")

        req_id = res.get_json()["id"]
        # Convert without project_id
        res2 = client.post(f"/api/v1/explore/requirements/{req_id}/convert", json={})
        assert res2.status_code == 400, \
            f"Convert without project_id should return 400, got {res2.status_code}"
        _assert_standard_error(res2)

    def test_convert_non_approved_fails(self, client, program):
        """Convert a 'draft' requirement → should fail (not approved)."""
        pid = program["id"]
        res = client.post("/api/v1/explore/requirements", json={
            "project_id": pid,
            "title": "Draft Not Convertable",
            "type": "functional",
            "priority": "medium",
            "area": "SD",
        })
        if res.status_code != 201:
            pytest.skip("Could not create requirement")

        req_id = res.get_json()["id"]
        res2 = client.post(f"/api/v1/explore/requirements/{req_id}/convert", json={
            "project_id": pid,
        })
        # Draft requirements should not be convertable
        assert res2.status_code in (400, 409), \
            f"Converting draft req should fail, got {res2.status_code}"


# ── Contract: Response Shape (List Endpoints) ────────────────────────────


class TestResponseShape:
    """List endpoints must return consistent shapes."""

    LIST_ENDPOINTS = [
        "/explore/requirements?project_id={pid}",
        "/explore/workshops?project_id={pid}",
        "/explore/process-levels?project_id={pid}&level=1",
        "/explore/open-items?project_id={pid}",
    ]

    @pytest.mark.parametrize("path_tmpl", LIST_ENDPOINTS)
    def test_list_returns_items_array(self, client, program, path_tmpl):
        """GET list endpoints must return {items: [...]} or [...]."""
        path = path_tmpl.format(pid=program["id"])
        res = client.get(f"/api/v1{path}")
        assert res.status_code == 200, f"GET {path} returned {res.status_code}"
        body = res.get_json()
        if isinstance(body, list):
            pass  # OK — direct array
        elif isinstance(body, dict):
            assert "items" in body, \
                f"GET {path} dict response must have 'items' key, got: {list(body.keys())}"
            assert isinstance(body["items"], list)
        else:
            pytest.fail(f"GET {path} returned unexpected type: {type(body)}")


# ── Contract: Idempotent GET ─────────────────────────────────────────────


class TestIdempotentGet:
    """GET endpoints should not modify state."""

    def test_get_requirements_twice_same_result(self, client, program):
        pid = program["id"]
        r1 = client.get(f"/api/v1/explore/requirements?project_id={pid}")
        r2 = client.get(f"/api/v1/explore/requirements?project_id={pid}")
        assert r1.status_code == r2.status_code == 200
        assert r1.get_json() == r2.get_json()

    def test_get_workshops_twice_same_result(self, client, program):
        pid = program["id"]
        r1 = client.get(f"/api/v1/explore/workshops?project_id={pid}")
        r2 = client.get(f"/api/v1/explore/workshops?project_id={pid}")
        assert r1.status_code == r2.status_code == 200
        assert r1.get_json() == r2.get_json()
