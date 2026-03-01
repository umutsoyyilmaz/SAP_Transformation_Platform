"""Program Governance module tests — Faz 2.4.

Tests CRUD + workflow for:
- ProgramReport (SteerCo reports with approval lifecycle)
- ProgramDecision (cross-project decisions)
- ProgramRisk (portfolio-level risks with scoring)
- ProgramMilestone (consolidated timeline)
- ProgramBudget (financial tracking)
- ProjectDependency (inter-project links)
"""

import pytest


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM REPORT
# ═══════════════════════════════════════════════════════════════════════════


class TestProgramReport:
    """SteerCo report CRUD + approval workflow."""

    def test_create_report_returns_201(self, client, program):
        """Valid payload creates a report."""
        resp = client.post(f"/api/v1/programs/{program['id']}/reports", json={
            "title": "SteerCo Report #1",
            "report_date": "2026-03-01",
            "overall_rag": "Green",
            "executive_summary": "All on track.",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "SteerCo Report #1"
        assert data["report_number"] == 1
        assert data["status"] == "draft"

    def test_create_report_returns_400_without_title(self, client, program):
        """Missing title returns 400."""
        resp = client.post(f"/api/v1/programs/{program['id']}/reports", json={})
        assert resp.status_code == 400

    def test_list_reports_returns_200(self, client, program):
        """List endpoint returns empty list initially."""
        resp = client.get(f"/api/v1/programs/{program['id']}/reports")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_get_report_returns_200(self, client, program):
        """Get a single report by ID."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/reports", json={
            "title": "Report Get Test",
        })
        rid = create_resp.get_json()["id"]

        resp = client.get(f"/api/v1/program-reports/{rid}")
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "Report Get Test"

    def test_update_report_returns_200(self, client, program):
        """Update a draft report."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/reports", json={
            "title": "Report Update Test",
        })
        rid = create_resp.get_json()["id"]

        resp = client.put(f"/api/v1/program-reports/{rid}", json={
            "overall_rag": "Amber",
            "executive_summary": "Some concerns.",
        })
        assert resp.status_code == 200
        assert resp.get_json()["overall_rag"] == "Amber"

    def test_approve_report_locks_status(self, client, program):
        """Approving a report changes status to 'approved'."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/reports", json={
            "title": "Report Approve Test",
        })
        rid = create_resp.get_json()["id"]

        resp = client.post(f"/api/v1/program-reports/{rid}/approve", json={
            "metrics_snapshot": '{"test": 1}',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "approved"
        assert data["metrics_snapshot"] == '{"test": 1}'

    def test_cannot_update_approved_report(self, client, program):
        """Updating an approved report returns 422."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/reports", json={
            "title": "Locked Report",
        })
        rid = create_resp.get_json()["id"]
        client.post(f"/api/v1/program-reports/{rid}/approve")

        resp = client.put(f"/api/v1/program-reports/{rid}", json={"title": "Changed"})
        assert resp.status_code == 422

    def test_present_after_approve(self, client, program):
        """Present workflow: approve → present."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/reports", json={
            "title": "Present Test",
        })
        rid = create_resp.get_json()["id"]
        client.post(f"/api/v1/program-reports/{rid}/approve")

        resp = client.post(f"/api/v1/program-reports/{rid}/present")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "presented"

    def test_delete_draft_report(self, client, program):
        """Can delete a draft report."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/reports", json={
            "title": "Delete Me",
        })
        rid = create_resp.get_json()["id"]

        resp = client.delete(f"/api/v1/program-reports/{rid}")
        assert resp.status_code == 200

    def test_cannot_delete_approved_report(self, client, program):
        """Cannot delete an approved report."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/reports", json={
            "title": "Cannot Delete",
        })
        rid = create_resp.get_json()["id"]
        client.post(f"/api/v1/program-reports/{rid}/approve")

        resp = client.delete(f"/api/v1/program-reports/{rid}")
        assert resp.status_code == 422

    def test_report_not_found_returns_404(self, client):
        """Non-existent report returns 404."""
        resp = client.get("/api/v1/program-reports/99999")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM DECISION
# ═══════════════════════════════════════════════════════════════════════════


class TestProgramDecision:
    """Cross-project decision CRUD."""

    def test_create_decision_returns_201(self, client, program):
        """Valid payload creates a decision."""
        resp = client.post(f"/api/v1/programs/{program['id']}/program-decisions", json={
            "title": "Architecture Selection",
            "category": "architecture",
            "priority": "high",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "Architecture Selection"
        assert data["status"] == "proposed"

    def test_create_decision_returns_400_without_title(self, client, program):
        """Missing title returns 400."""
        resp = client.post(f"/api/v1/programs/{program['id']}/program-decisions", json={})
        assert resp.status_code == 400

    def test_list_decisions_returns_200(self, client, program):
        """List endpoint returns 200."""
        resp = client.get(f"/api/v1/programs/{program['id']}/program-decisions")
        assert resp.status_code == 200

    def test_update_decision_sets_decided_at_on_approve(self, client, program):
        """Approving auto-sets decided_at."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/program-decisions", json={
            "title": "Auto-approve test",
        })
        did = create_resp.get_json()["id"]

        resp = client.put(f"/api/v1/program-decisions/{did}", json={
            "status": "approved",
            "decided_by": "SteerCo",
        })
        assert resp.status_code == 200
        assert resp.get_json()["decided_at"] is not None

    def test_delete_decision_returns_200(self, client, program):
        """Delete a decision."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/program-decisions", json={
            "title": "Delete Me",
        })
        did = create_resp.get_json()["id"]

        resp = client.delete(f"/api/v1/program-decisions/{did}")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM RISK
# ═══════════════════════════════════════════════════════════════════════════


class TestProgramRisk:
    """Portfolio-level risk CRUD with scoring."""

    def test_create_risk_returns_201_with_auto_score(self, client, program):
        """Risk creation auto-calculates score and RAG."""
        resp = client.post(f"/api/v1/programs/{program['id']}/risks/program", json={
            "title": "Vendor Dependency",
            "probability": 4,
            "impact": 5,
            "category": "external",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["risk_score"] == 20
        assert data["rag_status"] == "Red"

    def test_create_risk_returns_400_without_title(self, client, program):
        """Missing title returns 400."""
        resp = client.post(f"/api/v1/programs/{program['id']}/risks/program", json={})
        assert resp.status_code == 400

    def test_list_risks_returns_200(self, client, program):
        """List endpoint returns 200."""
        resp = client.get(f"/api/v1/programs/{program['id']}/risks/program")
        assert resp.status_code == 200

    def test_update_risk_recalculates_score(self, client, program):
        """Updating probability/impact recalculates score."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/risks/program", json={
            "title": "Score Change Test",
            "probability": 2,
            "impact": 2,
        })
        rid = create_resp.get_json()["id"]

        resp = client.put(f"/api/v1/program-risks/{rid}", json={
            "probability": 5,
            "impact": 5,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["risk_score"] == 25
        assert data["rag_status"] == "Red"

    def test_delete_risk_returns_200(self, client, program):
        """Delete a risk."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/risks/program", json={
            "title": "Delete Me",
        })
        rid = create_resp.get_json()["id"]

        resp = client.delete(f"/api/v1/program-risks/{rid}")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM MILESTONE
# ═══════════════════════════════════════════════════════════════════════════


class TestProgramMilestone:
    """Consolidated timeline milestone CRUD."""

    def test_create_milestone_returns_201(self, client, program):
        """Valid payload creates a milestone."""
        resp = client.post(f"/api/v1/programs/{program['id']}/milestones", json={
            "title": "Go-Live Wave 1",
            "milestone_type": "go_live",
            "planned_date": "2026-06-01",
            "is_critical_path": True,
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "Go-Live Wave 1"
        assert data["is_critical_path"] is True

    def test_create_milestone_returns_400_without_title(self, client, program):
        """Missing title returns 400."""
        resp = client.post(f"/api/v1/programs/{program['id']}/milestones", json={})
        assert resp.status_code == 400

    def test_list_milestones_returns_200(self, client, program):
        """List endpoint returns 200."""
        resp = client.get(f"/api/v1/programs/{program['id']}/milestones")
        assert resp.status_code == 200

    def test_update_milestone_returns_200(self, client, program):
        """Update a milestone."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/milestones", json={
            "title": "Update Test",
        })
        mid = create_resp.get_json()["id"]

        resp = client.put(f"/api/v1/program-milestones/{mid}", json={
            "status": "completed",
            "actual_date": "2026-06-01",
        })
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "completed"

    def test_delete_milestone_returns_200(self, client, program):
        """Delete a milestone."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/milestones", json={
            "title": "Delete Me",
        })
        mid = create_resp.get_json()["id"]

        resp = client.delete(f"/api/v1/program-milestones/{mid}")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
#  PROGRAM BUDGET
# ═══════════════════════════════════════════════════════════════════════════


class TestProgramBudget:
    """Financial tracking CRUD + summary."""

    def test_create_budget_returns_201(self, client, program):
        """Valid payload creates a budget line."""
        resp = client.post(f"/api/v1/programs/{program['id']}/budget", json={
            "category": "consulting",
            "planned_amount": 500000,
            "currency": "EUR",
            "fiscal_year": 2026,
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["category"] == "consulting"
        assert data["planned_amount"] == 500000.0

    def test_create_budget_returns_400_without_category(self, client, program):
        """Missing category returns 400."""
        resp = client.post(f"/api/v1/programs/{program['id']}/budget", json={})
        assert resp.status_code == 400

    def test_budget_summary_returns_200(self, client, program):
        """Budget summary aggregation works."""
        pid = program["id"]
        client.post(f"/api/v1/programs/{pid}/budget", json={
            "category": "consulting",
            "planned_amount": 100000,
            "actual_amount": 80000,
        })
        client.post(f"/api/v1/programs/{pid}/budget", json={
            "category": "license",
            "planned_amount": 200000,
            "actual_amount": 200000,
        })

        resp = client.get(f"/api/v1/programs/{pid}/budget/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_planned"] == 300000.0
        assert data["total_actual"] == 280000.0
        assert data["variance"] == 20000.0
        assert "consulting" in data["by_category"]
        assert "license" in data["by_category"]

    def test_update_budget_returns_200(self, client, program):
        """Update a budget line."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/budget", json={
            "category": "training",
            "planned_amount": 50000,
        })
        bid = create_resp.get_json()["id"]

        resp = client.put(f"/api/v1/program-budgets/{bid}", json={
            "actual_amount": 45000,
        })
        assert resp.status_code == 200
        assert resp.get_json()["actual_amount"] == 45000.0

    def test_delete_budget_returns_200(self, client, program):
        """Delete a budget line."""
        create_resp = client.post(f"/api/v1/programs/{program['id']}/budget", json={
            "category": "contingency",
        })
        bid = create_resp.get_json()["id"]

        resp = client.delete(f"/api/v1/program-budgets/{bid}")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
#  PROJECT DEPENDENCY
# ═══════════════════════════════════════════════════════════════════════════


class TestProjectDependency:
    """Inter-project dependency CRUD."""

    @pytest.fixture()
    def two_projects(self, client, program):
        """Create two projects under the program."""
        from app.models.project import Project
        from app.models import db as _db

        p1 = Project(
            tenant_id=1, program_id=program["id"],
            code="PROJ-A", name="Project Alpha", is_default=False,
        )
        p2 = Project(
            tenant_id=1, program_id=program["id"],
            code="PROJ-B", name="Project Beta", is_default=False,
        )
        _db.session.add_all([p1, p2])
        _db.session.commit()
        return p1.id, p2.id

    def test_create_dependency_returns_201(self, client, program, two_projects):
        """Valid payload creates a dependency."""
        p1, p2 = two_projects
        resp = client.post(f"/api/v1/programs/{program['id']}/dependencies", json={
            "source_project_id": p1,
            "target_project_id": p2,
            "dependency_type": "finish_to_start",
            "title": "Wave 1 must complete before Wave 2",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["source_project_id"] == p1
        assert data["target_project_id"] == p2

    def test_create_dependency_returns_400_without_projects(self, client, program):
        """Missing project IDs returns 400."""
        resp = client.post(f"/api/v1/programs/{program['id']}/dependencies", json={})
        assert resp.status_code == 400

    def test_create_self_dependency_returns_422(self, client, program, two_projects):
        """Same source and target returns 422."""
        p1, _ = two_projects
        resp = client.post(f"/api/v1/programs/{program['id']}/dependencies", json={
            "source_project_id": p1,
            "target_project_id": p1,
        })
        assert resp.status_code == 422

    def test_list_dependencies_returns_200(self, client, program):
        """List endpoint returns 200."""
        resp = client.get(f"/api/v1/programs/{program['id']}/dependencies")
        assert resp.status_code == 200

    def test_update_dependency_returns_200(self, client, program, two_projects):
        """Update a dependency."""
        p1, p2 = two_projects
        create_resp = client.post(f"/api/v1/programs/{program['id']}/dependencies", json={
            "source_project_id": p1,
            "target_project_id": p2,
        })
        did = create_resp.get_json()["id"]

        resp = client.put(f"/api/v1/project-dependencies/{did}", json={
            "status": "resolved",
        })
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "resolved"

    def test_delete_dependency_returns_200(self, client, program, two_projects):
        """Delete a dependency."""
        p1, p2 = two_projects
        create_resp = client.post(f"/api/v1/programs/{program['id']}/dependencies", json={
            "source_project_id": p1,
            "target_project_id": p2,
        })
        did = create_resp.get_json()["id"]

        resp = client.delete(f"/api/v1/project-dependencies/{did}")
        assert resp.status_code == 200
