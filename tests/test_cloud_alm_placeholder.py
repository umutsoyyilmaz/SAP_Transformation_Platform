"""S3-04 tests — FDD-F07 Faz A: SAP Cloud ALM sync-log placeholder endpoint.

Scope
─────
Phase A delivers a UI placeholder only.  No live SAP Cloud ALM connection
exists yet; the endpoint must communicate this clearly so the frontend can
render the 'Coming Q2 2026' card without masking the absence of real data.

Phase B (S4-02, FDD-F07 Faz B) will replace this with a real OAuth2 sync.
"""

import pytest


# ── helpers ────────────────────────────────────────────────────────────────

def _make_program(client):
    """Create a test program via the API and return its dict."""
    res = client.post("/api/v1/programs", json={"name": "ALM Test Program", "methodology": "agile"})
    assert res.status_code == 201
    return res.get_json()


# ── tests ──────────────────────────────────────────────────────────────────


class TestCloudAlmSyncLogEndpoint:
    """GET /api/v1/programs/<pid>/integrations/cloud-alm/sync-log — Phase A."""

    def test_returns_200_for_valid_program(self, client):
        """Endpoint must return 200 regardless of whether ALM is configured."""
        prog = _make_program(client)
        res = client.get(f"/api/v1/programs/{prog['id']}/integrations/cloud-alm/sync-log")
        assert res.status_code == 200

    def test_connection_active_is_false(self, client):
        """Phase A: no live connection — connection_active must be False.

        Why: the UI uses this flag to decide whether to show a 'connected'
        badge or the 'Coming Q2 2026' placeholder.  A truthy value here would
        be a silent lie to the user.
        """
        prog = _make_program(client)
        res = client.get(f"/api/v1/programs/{prog['id']}/integrations/cloud-alm/sync-log")
        data = res.get_json()
        assert data["connection_active"] is False

    def test_logs_is_empty_list(self, client):
        """Phase A: no sync records exist — logs must be an empty list.

        Why: the frontend iterates this list to build the sync log table.
        A missing or non-list value would throw a JS TypeError.
        """
        prog = _make_program(client)
        res = client.get(f"/api/v1/programs/{prog['id']}/integrations/cloud-alm/sync-log")
        data = res.get_json()
        assert isinstance(data["logs"], list)
        assert len(data["logs"]) == 0

    def test_response_contains_program_id(self, client):
        """Response must echo back the program_id for client-side correlation."""
        prog = _make_program(client)
        res = client.get(f"/api/v1/programs/{prog['id']}/integrations/cloud-alm/sync-log")
        data = res.get_json()
        assert data["program_id"] == prog["id"]

    def test_response_contains_human_readable_message(self, client):
        """Response must include a message field to surface in admin panels."""
        prog = _make_program(client)
        res = client.get(f"/api/v1/programs/{prog['id']}/integrations/cloud-alm/sync-log")
        data = res.get_json()
        assert "message" in data
        assert len(data["message"]) > 0
