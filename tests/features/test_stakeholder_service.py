"""
Tests for Stakeholder Management service functions (FDD-I08 / S5-05).

Covers:
  - create_stakeholder: returns 201-equivalent dict with engagement_strategy set
  - engagement_strategy: high/high → manage_closely
  - engagement_strategy: low/high → keep_informed
  - stakeholder_matrix: returns four quadrant groups
  - overdue_contacts: returns stakeholders with next_contact_date in the past
  - create_comm_plan_entry: creates entry with status=planned
  - mark_comm_completed: sets status=completed and actual_date
  - tenant isolation: cross-tenant stakeholder raises ValueError (404-equivalent)
  - list_comm_plan_entries filtered by sap_activate_phase

Marker: unit (no integration dependencies).
"""

from datetime import date, timedelta

import pytest

from app.models import db
from app.models.auth import Tenant
from app.models.program import CommunicationPlanEntry, Program, Stakeholder
from app.services import stakeholder_service


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tenant() -> Tenant:
    t = Tenant(name="Stakeholder Corp", slug="stakeholder-corp")
    db.session.add(t)
    db.session.flush()
    return t


@pytest.fixture()
def program(tenant: Tenant) -> Program:
    p = Program(
        name="Change Management Program",
        tenant_id=tenant.id,
        methodology="sap_activate",
    )
    db.session.add(p)
    db.session.flush()
    return p


@pytest.fixture()
def other_tenant() -> Tenant:
    t = Tenant(name="Other Corp", slug="other2-corp")
    db.session.add(t)
    db.session.flush()
    return t


def _make_stakeholder(
    tenant_id: int,
    program_id: int,
    name: str = "Test Stakeholder",
    influence: str = "high",
    interest: str = "high",
) -> Stakeholder:
    s = Stakeholder(
        tenant_id=tenant_id,
        program_id=program_id,
        name=name,
        influence_level=influence,
        interest_level=interest,
        engagement_strategy=stakeholder_service.calculate_engagement_strategy(
            influence, interest
        ),
        is_active=True,
    )
    db.session.add(s)
    db.session.flush()
    return s


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestCreateStakeholder:
    def test_create_stakeholder_returns_201_with_valid_data(
        self, tenant: Tenant, program: Program
    ):
        """Happy path: create stakeholder returns dict with engagement_strategy set."""
        result = stakeholder_service.create_stakeholder(
            tenant_id=tenant.id,
            program_id=program.id,
            data={
                "name": "Alice Johnson",
                "title": "CFO",
                "influence_level": "high",
                "interest_level": "high",
                "stakeholder_type": "steering",
            },
        )
        assert result["name"] == "Alice Johnson"
        assert result["engagement_strategy"] == "manage_closely"
        assert result["tenant_id"] == tenant.id
        assert result["program_id"] == program.id
        assert result["is_active"] is True

    def test_create_stakeholder_returns_400_when_name_missing(
        self, tenant: Tenant, program: Program
    ):
        """Missing name raises ValueError."""
        with pytest.raises(ValueError, match="required"):
            stakeholder_service.create_stakeholder(
                tenant_id=tenant.id,
                program_id=program.id,
                data={"influence_level": "high", "interest_level": "high"},
            )


class TestEngagementStrategy:
    def test_engagement_strategy_calculated_correctly_for_high_high(self):
        """high influence + high interest → manage_closely."""
        result = stakeholder_service.calculate_engagement_strategy("high", "high")
        assert result == "manage_closely"

    def test_engagement_strategy_calculated_correctly_for_high_low(self):
        """high influence + low interest → keep_satisfied."""
        result = stakeholder_service.calculate_engagement_strategy("high", "low")
        assert result == "keep_satisfied"

    def test_engagement_strategy_calculated_correctly_for_low_high(self):
        """low influence + high interest → keep_informed."""
        result = stakeholder_service.calculate_engagement_strategy("low", "high")
        assert result == "keep_informed"

    def test_engagement_strategy_calculated_correctly_for_low_low(self):
        """low influence + low interest → monitor."""
        result = stakeholder_service.calculate_engagement_strategy("low", "low")
        assert result == "monitor"

    def test_update_stakeholder_recomputes_strategy_when_levels_change(
        self, tenant: Tenant, program: Program
    ):
        """Updating influence_level triggers engagement_strategy recomputation."""
        s = _make_stakeholder(tenant.id, program.id, influence="low", interest="low")
        assert s.engagement_strategy == "monitor"

        result = stakeholder_service.update_stakeholder(
            tenant_id=tenant.id,
            program_id=program.id,
            stakeholder_id=s.id,
            data={
                "influence_level": "high",
                "interest_level": "high",
            },
        )
        assert result["engagement_strategy"] == "manage_closely"


class TestMatrix:
    def test_stakeholder_matrix_returns_four_quadrants(
        self, tenant: Tenant, program: Program
    ):
        """get_stakeholder_matrix groups stakeholders into 4 quadrants."""
        _make_stakeholder(tenant.id, program.id, name="S1", influence="high", interest="high")
        _make_stakeholder(tenant.id, program.id, name="S2", influence="low", interest="low")
        _make_stakeholder(tenant.id, program.id, name="S3", influence="high", interest="low")
        _make_stakeholder(tenant.id, program.id, name="S4", influence="low", interest="high")

        matrix = stakeholder_service.get_stakeholder_matrix(
            tenant_id=tenant.id, program_id=program.id
        )
        assert len(matrix["quadrants"]["manage_closely"]) == 1
        assert len(matrix["quadrants"]["keep_satisfied"]) == 1
        assert len(matrix["quadrants"]["keep_informed"]) == 1
        assert len(matrix["quadrants"]["monitor"]) == 1
        assert matrix["total_active"] == 4


class TestOverdueContacts:
    def test_overdue_contacts_returns_stakeholders_past_next_contact_date(
        self, tenant: Tenant, program: Program
    ):
        """Stakeholders with next_contact_date < today appear in overdue list."""
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)

        overdue = _make_stakeholder(tenant.id, program.id, name="Overdue")
        overdue.next_contact_date = yesterday
        db.session.flush()

        not_overdue = _make_stakeholder(tenant.id, program.id, name="Future")
        not_overdue.next_contact_date = tomorrow
        db.session.flush()

        result = stakeholder_service.get_overdue_contacts(
            tenant_id=tenant.id, program_id=program.id
        )
        names = [s["name"] for s in result]
        assert "Overdue" in names
        assert "Future" not in names


class TestCommPlan:
    def test_create_comm_plan_entry_returns_planned_status(
        self, tenant: Tenant, program: Program
    ):
        """New comm plan entry always starts with status=planned."""
        result = stakeholder_service.create_comm_plan_entry(
            tenant_id=tenant.id,
            program_id=program.id,
            data={
                "subject": "Go-Live Town Hall",
                "sap_activate_phase": "deploy",
                "channel": "video_call",
                "audience_group": "All Users",
            },
        )
        assert result["subject"] == "Go-Live Town Hall"
        assert result["status"] == "planned"
        assert result["sap_activate_phase"] == "deploy"

    def test_mark_comm_completed_sets_actual_date_and_status(
        self, tenant: Tenant, program: Program
    ):
        """mark_comm_completed sets status=completed and records actual_date."""
        entry_dict = stakeholder_service.create_comm_plan_entry(
            tenant_id=tenant.id,
            program_id=program.id,
            data={"subject": "Kick-off meeting", "sap_activate_phase": "discover"},
        )
        today = date.today()
        result = stakeholder_service.mark_comm_completed(
            tenant_id=tenant.id,
            program_id=program.id,
            entry_id=entry_dict["id"],
            actual_date=today,
        )
        assert result["status"] == "completed"
        assert result["actual_date"] == today.isoformat()

    def test_comm_plan_filter_by_phase_returns_correct_entries(
        self, tenant: Tenant, program: Program
    ):
        """list_comm_plan_entries filtered by sap_activate_phase returns only matching entries."""
        stakeholder_service.create_comm_plan_entry(
            tenant_id=tenant.id,
            program_id=program.id,
            data={"subject": "Explore workshop", "sap_activate_phase": "explore"},
        )
        stakeholder_service.create_comm_plan_entry(
            tenant_id=tenant.id,
            program_id=program.id,
            data={"subject": "Deploy meeting", "sap_activate_phase": "deploy"},
        )

        result = stakeholder_service.list_comm_plan_entries(
            tenant_id=tenant.id,
            program_id=program.id,
            sap_activate_phase="explore",
        )
        assert len(result) == 1
        assert result[0]["subject"] == "Explore workshop"


class TestTenantIsolation:
    def test_tenant_isolation_stakeholder_cross_tenant_raises_404(
        self, tenant: Tenant, program: Program, other_tenant: Tenant
    ):
        """A stakeholder owned by tenant A is not visible to tenant B — ValueError (404)."""
        s = _make_stakeholder(tenant.id, program.id)
        with pytest.raises(ValueError, match="not found"):
            stakeholder_service.get_stakeholder(
                tenant_id=other_tenant.id,
                program_id=program.id,
                stakeholder_id=s.id,
            )
