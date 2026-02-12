import uuid

import pytest

from app.models import db as _db


@pytest.fixture
def seeded_program(app, client, session):
    """Create a minimal program with data for testing."""
    from app.models.program import Phase
    from app.models.explore import ExploreWorkshop, ExploreRequirement, ExploreOpenItem
    from app.models.testing import TestCase, Defect
    from app.models.backlog import BacklogItem
    from app.models.raid import Risk, Action

    res = client.post(
        "/api/v1/programs",
        json={
            "name": "Test Program",
            "project_type": "greenfield",
            "methodology": "sap_activate",
            "sap_product": "s4hana",
            "status": "active",
        },
    )
    assert res.status_code == 201
    pid = res.get_json()["id"]

    with app.app_context():

        ph = Phase(
            program_id=pid,
            name="Explore",
            status="active",
            completion_pct=60,
            order=1,
        )
        _db.session.add(ph)

        created_by_id = str(uuid.uuid4())

        for i in range(5):
            ws = ExploreWorkshop(
                project_id=pid,
                code=f"WS-{i+1}",
                name=f"Workshop {i+1}",
                status="completed" if i < 3 else "in_progress",
                process_area="FI",
            )
            _db.session.add(ws)

        for i in range(10):
            req = ExploreRequirement(
                project_id=pid,
                code=f"REQ-{i+1}",
                title=f"Req {i+1}",
                process_area="FI",
                created_by_id=created_by_id,
                created_by_name="System",
                status="approved" if i < 7 else "draft",
            )
            _db.session.add(req)

        for i in range(8):
            tc = TestCase(
                program_id=pid,
                code=f"TC-{i+1}",
                title=f"TC {i+1}",
                module="FI",
                test_layer="sit",
                status="approved",
            )
            _db.session.add(tc)

        d1 = Defect(
            program_id=pid,
            code="DEF-001",
            title="Critical bug",
            severity="S1",
            status="open",
            module="FI",
        )
        d2 = Defect(
            program_id=pid,
            code="DEF-002",
            title="Minor bug",
            severity="S3",
            status="closed",
            module="FI",
        )
        _db.session.add_all([d1, d2])

        for i in range(6):
            bi = BacklogItem(
                program_id=pid,
                title=f"Item {i+1}",
                wricef_type="enhancement",
                module="FI",
                status="done" if i < 2 else "in_progress",
                priority="high",
            )
            _db.session.add(bi)

        r1 = Risk(
            program_id=pid,
            code="RISK-001",
            title="Risk 1",
            probability=4,
            impact=5,
            status="open",
        )
        a1 = Action(program_id=pid, code="ACT-001", title="Action 1", status="open")
        _db.session.add_all([r1, a1])

        _db.session.commit()
        return pid


class TestProgramHealth:
    def test_health_endpoint(self, client, seeded_program):
        """GET /reports/program-health/<pid> returns valid health data."""
        res = client.get(f"/api/v1/reports/program-health/{seeded_program}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["overall_rag"] in ("green", "amber", "red")
        assert "areas" in data
        assert all(
            k in data["areas"]
            for k in ("explore", "backlog", "testing", "raid", "integration")
        )

    def test_health_rag_logic(self, client, seeded_program):
        """Testing RAG should be red because of open S1 defect."""
        res = client.get(f"/api/v1/reports/program-health/{seeded_program}")
        data = res.get_json()
        assert data["areas"]["testing"]["rag"] == "red"

    def test_health_explore_pct(self, client, seeded_program):
        """3 of 5 workshops completed = 60%."""
        res = client.get(f"/api/v1/reports/program-health/{seeded_program}")
        data = res.get_json()
        assert data["areas"]["explore"]["workshops"]["pct"] == 60

    def test_health_not_found(self, client):
        """Non-existent program returns 404."""
        res = client.get("/api/v1/reports/program-health/99999")
        assert res.status_code == 404

    def test_weekly_endpoint(self, client, seeded_program):
        """Weekly report endpoint works."""
        res = client.get(f"/api/v1/reports/weekly/{seeded_program}")
        assert res.status_code == 200
        data = res.get_json()
        assert data["report_type"] == "weekly"


class TestExport:
    def test_xlsx_download(self, client, seeded_program):
        """Excel export returns valid xlsx."""
        res = client.get(f"/api/v1/reports/export/xlsx/{seeded_program}")
        assert res.status_code == 200
        assert "spreadsheetml" in res.content_type

    def test_pdf_download(self, client, seeded_program):
        """HTML/PDF export returns valid HTML."""
        res = client.get(f"/api/v1/reports/export/pdf/{seeded_program}")
        assert res.status_code == 200
        assert "text/html" in res.content_type
        assert "Program Health Report" in res.data.decode()

    def test_export_not_found(self, client):
        """Export for non-existent program returns 404."""
        res = client.get("/api/v1/reports/export/xlsx/99999")
        assert res.status_code == 404
