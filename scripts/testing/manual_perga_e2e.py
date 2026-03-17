"""Manual end-to-end reference flow for exploratory runs.

It remains pytest-shaped, but lives outside `tests/` so it is not
collected as part of the default regression suite.
"""

import pytest
from app import create_app
from app.models import db

@pytest.fixture(scope="module")
def app():
    app = create_app("testing")
    with app.app_context():
        # Block 0.1: Data Reset
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
    yield app

@pytest.fixture(scope="module")
def client(app):
    return app.test_client()

@pytest.fixture(scope="module")
def test_data():
    return {}

def test_block_0_health_checks(client):
    print("\n=== BLOCK 0: SMOKE TESTS ===")
    endpoints = [
        "/api/v1/projects", "/api/v1/scenarios", "/api/v1/explore/workshops",
        "/api/v1/explore/requirements", "/api/v1/explore/open-items",
        "/api/v1/explore/process-levels", "/api/v1/explore/dashboard",
        "/api/v1/backlog", "/api/v1/config-items", "/api/v1/testing/test-cases",
        "/api/v1/testing/test-suites", "/api/v1/testing/test-executions",
        "/api/v1/testing/defects", "/api/v1/team-members", "/api/v1/interfaces",
        "/api/v1/programs", "/api/v1/raid", "/api/v1/notifications",
        "/api/v1/cutover/tasks"
    ]
    for ep in endpoints:
        resp = client.get(ep)
        # Even if some routing is missing (404), as long as it doesn't crash (500)
        assert resp.status_code in [200, 404, 403, 401], f"Endpoint {ep} returned {resp.status_code}"

def test_block_1_program_and_project(client, test_data):
    print("\n=== BLOCK 1: PROGRAM & PROJECT ===")

    # 1.1 Program
    prog_resp = client.post("/api/v1/programs", json={
        "name": "ACME Global Transformation",
        "code": "ACME-GTX",
        "description": "Global SAP S/4HANA 2023 FPS02.",
        "status": "active"
    })
    assert prog_resp.status_code == 201, f"Failed: {prog_resp.data}"
    test_data['program_id'] = prog_resp.json["id"]

    # 1.2 Project
    proj_resp = client.post("/api/v1/projects", json={
        "name": "ACME Turkey S/4HANA Greenfield",
        "code": "ACME-TR-S4H",
        "description": "Turkey pilot.",
        "customer": "ACME Manufacturing A.Ş.",
        "program_id": test_data['program_id'],
        "sap_product": "S/4HANA 2023 FPS02",
        "methodology": "SAP Activate",
        "status": "active",
        "start_date": "2026-03-01",
        "target_go_live": "2027-10-01"
    })
    assert proj_resp.status_code == 201, f"Failed: {proj_resp.data}"
    test_data['project_id'] = proj_resp.json["id"]

def test_block_1_scenarios_and_hierarchy(client, test_data):
    project_id = test_data['project_id']

    # 1.4 Scenarios
    scenarios = [("Order to Cash", "O2C"), ("Procure to Pay", "P2P")]
    test_data['scenario_ids'] = {}
    for s_name, s_code in scenarios:
        resp = client.post("/api/v1/scenarios", json={
            "name": s_name, "code": s_code, "project_id": project_id,
            "scenario_type": "e2e", "status": "active"
        })
        assert resp.status_code == 201
        test_data['scenario_ids'][s_code] = resp.json["id"]

    # 1.6 Process Hierarchy (L1 -> L3 partial mock to continue the flow)
    resp_l1 = client.post("/api/v1/explore/process-levels", json={
        "name": "Sales", "level": 1, "process_area": "SD",
        "scope_status": "in_scope", "project_id": project_id
    })
    assert resp_l1.status_code in [201, 200]

def test_block_2_explore_workshop(client, test_data):
    project_id = test_data['project_id']
    print("\n=== BLOCK 2: WORKSHOPS ===")

    # Workshop
    ws_resp = client.post("/api/v1/explore/workshops", json={
        "name": "O2C Sales Order Processing Workshop",
        "project_id": project_id,
        "process_area": "SD",
        "wave": 1,
        "status": "draft"
    })

    if ws_resp.status_code == 201:
        test_data['workshop_id'] = ws_resp.json.get("id")

        # Start Workshop
        client.post(f"/api/v1/explore/workshops/{test_data['workshop_id']}/start", json={})

def test_block_3_realize_backlog(client, test_data):
    print("\n=== BLOCK 3: REALIZE ===")
    project_id = test_data['project_id']

    # Backlog Item
    bl_resp = client.post("/api/v1/backlog", json={
        "title": "Custom Pricing",
        "description": "Develop custom pricing procedure",
        "wricef_type": "enhancement",
        "status": "new",
        "project_id": project_id,
        "module": "SD"
    })
    if bl_resp.status_code == 201:
        test_data['backlog_id'] = bl_resp.json.get("id")

def test_block_4_testing(client, test_data):
    print("\n=== BLOCK 4: TESTING ===")
    project_id = test_data['project_id']
    backlog_id = test_data.get('backlog_id', None)

    if backlog_id:
        tc_resp = client.post("/api/v1/testing/test-cases", json={
            "title": "UT: Rebate Pricing",
            "test_level": "unit",
            "status": "ready",
            "project_id": project_id,
            "backlog_item_id": backlog_id,
            "module": "SD"
        })
        assert tc_resp.status_code == 201

# End of test flow definition
