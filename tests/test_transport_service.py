"""
Tests for Transport/CTS Tracking service functions (FDD-I01 / S5-04).

Covers:
  - create_transport: returns dict with correct data
  - create_transport: rejects invalid transport number format
  - assign_backlog_to_transport: creates link, idempotent
  - record_import_result: appends to import_log, updates current_system
  - get_transport_coverage: correct counts and percentage
  - get_wave_status: returns transports with latest import
  - tenant isolation: cross-tenant transport returns 404

Marker: unit (no integration dependencies).
"""

import pytest

from app.models import db
from app.models.auth import Tenant
from app.models.backlog import BacklogItem
from app.models.program import Program
from app.models.transport import TransportRequest, TransportWave
from app.services import transport_service


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tenant() -> Tenant:
    """Create a test Tenant row (required FK by all tenant-scoped models)."""
    t = Tenant(name="Transport Corp", slug="transport-corp")
    db.session.add(t)
    db.session.flush()
    return t


@pytest.fixture()
def program(tenant: Tenant) -> Program:
    """Create a test Program owned by the test Tenant."""
    p = Program(
        name="SAP S/4 CTS Project",
        tenant_id=tenant.id,
        methodology="sap_activate",
    )
    db.session.add(p)
    db.session.flush()
    return p


@pytest.fixture()
def other_tenant() -> Tenant:
    """Second tenant for isolation tests."""
    t = Tenant(name="Other Corp", slug="other-corp")
    db.session.add(t)
    db.session.flush()
    return t


@pytest.fixture()
def backlog_item(tenant: Tenant, program: Program) -> BacklogItem:
    """Create a BacklogItem for backlog-link tests."""
    item = BacklogItem(
        tenant_id=tenant.id,
        program_id=program.id,
        title="Test Backlog Item",
        status="open",
    )
    db.session.add(item)
    db.session.flush()
    return item


def _make_transport(
    tenant_id: int,
    project_id: int,
    number: str = "DEVK900001",
    transport_type: str = "workbench",
) -> TransportRequest:
    """Helper to directly insert a TransportRequest into the session."""
    t = TransportRequest(
        tenant_id=tenant_id,
        project_id=project_id,
        transport_number=number,
        transport_type=transport_type,
        description="Test transport",
        current_system="DEV",
        status="created",
        import_log=[],
    )
    db.session.add(t)
    db.session.flush()
    return t


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestCreateTransport:
    def test_create_transport_request_returns_dict_with_correct_data(
        self, tenant: Tenant, program: Program
    ):
        """Happy path: valid transport_number creates record and returns serialized dict."""
        result = transport_service.create_transport(
            tenant_id=tenant.id,
            project_id=program.id,
            data={
                "transport_number": "DEVK900001",
                "transport_type": "workbench",
                "description": "Initial baseline transport",
            },
        )
        assert result["transport_number"] == "DEVK900001"
        assert result["transport_type"] == "workbench"
        assert result["tenant_id"] == tenant.id
        assert result["project_id"] == program.id
        assert result["current_system"] == "DEV"
        assert result["status"] == "created"

    def test_create_transport_raises_for_invalid_transport_number_format(
        self, tenant: Tenant, program: Program
    ):
        """transport_number that doesn't match ^[A-Z]{3}K\\d{6}$ is rejected."""
        with pytest.raises(ValueError, match="Invalid transport_number"):
            transport_service.create_transport(
                tenant_id=tenant.id,
                project_id=program.id,
                data={"transport_number": "BADFORMAT", "transport_type": "workbench"},
            )

    def test_create_transport_raises_for_duplicate_number_in_same_project(
        self, tenant: Tenant, program: Program
    ):
        """Duplicate transport_number within same project raises ValueError."""
        _make_transport(tenant.id, program.id, number="DEVK900002")
        with pytest.raises(ValueError, match="already exists"):
            transport_service.create_transport(
                tenant_id=tenant.id,
                project_id=program.id,
                data={"transport_number": "DEVK900002", "transport_type": "workbench"},
            )


class TestAssignBacklog:
    def test_assign_backlog_to_transport_creates_link(
        self, tenant: Tenant, program: Program, backlog_item: BacklogItem
    ):
        """Assigning a backlog item to a transport creates the N:M link."""
        transport = _make_transport(tenant.id, program.id)
        result = transport_service.assign_backlog_to_transport(
            tenant_id=tenant.id,
            project_id=program.id,
            transport_id=transport.id,
            backlog_item_id=backlog_item.id,
        )
        assert backlog_item.id in result["backlog_item_ids"]

    def test_assign_backlog_idempotent_on_duplicate_link(
        self, tenant: Tenant, program: Program, backlog_item: BacklogItem
    ):
        """Assigning the same item twice does not raise an error (idempotent)."""
        transport = _make_transport(tenant.id, program.id)
        transport_service.assign_backlog_to_transport(
            tenant_id=tenant.id,
            project_id=program.id,
            transport_id=transport.id,
            backlog_item_id=backlog_item.id,
        )
        # Second call must not raise
        result = transport_service.assign_backlog_to_transport(
            tenant_id=tenant.id,
            project_id=program.id,
            transport_id=transport.id,
            backlog_item_id=backlog_item.id,
        )
        assert result["backlog_item_ids"].count(backlog_item.id) == 1


class TestImportResult:
    def test_record_import_result_appends_to_import_log(
        self, tenant: Tenant, program: Program
    ):
        """record_import_result appends the event to import_log JSON."""
        transport = _make_transport(tenant.id, program.id)
        result = transport_service.record_import_result(
            tenant_id=tenant.id,
            project_id=program.id,
            transport_id=transport.id,
            system="QAS",
            status="imported",
            return_code=0,
        )
        assert len(result["import_log"]) == 1
        event = result["import_log"][0]
        assert event["system"] == "QAS"
        assert event["status"] == "imported"
        assert event["return_code"] == 0

    def test_record_import_result_updates_current_system_on_success(
        self, tenant: Tenant, program: Program
    ):
        """Successful import (status='imported') updates current_system."""
        transport = _make_transport(tenant.id, program.id)
        result = transport_service.record_import_result(
            tenant_id=tenant.id,
            project_id=program.id,
            transport_id=transport.id,
            system="QAS",
            status="imported",
        )
        assert result["current_system"] == "QAS"
        assert result["status"] == "imported"

    def test_record_import_result_sets_failed_status_on_failure(
        self, tenant: Tenant, program: Program
    ):
        """Failed import (status='failed') sets transport status to 'failed'."""
        transport = _make_transport(tenant.id, program.id)
        result = transport_service.record_import_result(
            tenant_id=tenant.id,
            project_id=program.id,
            transport_id=transport.id,
            system="QAS",
            status="failed",
            return_code=8,
        )
        assert result["status"] == "failed"
        # current_system should NOT update on failure
        assert result["current_system"] == "DEV"


class TestCoverage:
    def test_transport_coverage_counts_items_with_and_without_transport(
        self, tenant: Tenant, program: Program
    ):
        """Coverage analytics correctly counts linked vs unlinked backlog items."""
        item1 = BacklogItem(
            tenant_id=tenant.id, program_id=program.id, title="Item 1",
            status="open"
        )
        item2 = BacklogItem(
            tenant_id=tenant.id, program_id=program.id, title="Item 2",
            status="open"
        )
        db.session.add_all([item1, item2])
        db.session.flush()

        transport = _make_transport(tenant.id, program.id)
        transport_service.assign_backlog_to_transport(
            tenant_id=tenant.id,
            project_id=program.id,
            transport_id=transport.id,
            backlog_item_id=item1.id,
        )

        coverage = transport_service.get_transport_coverage(
            project_id=program.id, tenant_id=tenant.id
        )
        assert coverage["total_backlog_items"] == 2
        assert coverage["with_transport"] == 1
        assert coverage["without_transport"] == 1
        assert coverage["coverage_pct"] == 50.0


class TestWaveStatus:
    def test_wave_status_returns_all_transports_with_latest_import(
        self, tenant: Tenant, program: Program
    ):
        """get_wave_status includes all transports and their latest import event."""
        wave = TransportWave(
            tenant_id=tenant.id,
            project_id=program.id,
            name="Wave 1",
            target_system="QAS",
            status="planned",
        )
        db.session.add(wave)
        db.session.flush()

        t1 = TransportRequest(
            tenant_id=tenant.id,
            project_id=program.id,
            transport_number="DEVK900010",
            transport_type="workbench",
            current_system="QAS",
            status="imported",
            wave_id=wave.id,
            import_log=[
                {"system": "QAS", "status": "imported", "imported_at": "2026-01-01T00:00:00", "return_code": 0}
            ],
        )
        db.session.add(t1)
        db.session.flush()

        status = transport_service.get_wave_status(
            project_id=program.id, tenant_id=tenant.id, wave_id=wave.id
        )
        assert status["total"] == 1
        assert status["transports"][0]["transport_number"] == "DEVK900010"
        assert status["transports"][0]["latest_import"]["status"] == "imported"


class TestTenantIsolation:
    def test_tenant_isolation_get_transport_cross_tenant_raises(
        self, tenant: Tenant, program: Program,
        other_tenant: Tenant
    ):
        """A transport owned by tenant A is not visible to tenant B — raises ValueError."""
        transport = _make_transport(tenant.id, program.id, number="DEVK900099")
        # other_tenant has no program, but even if we try with program.id it should fail
        with pytest.raises(ValueError, match="not found"):
            transport_service.get_transport(
                tenant_id=other_tenant.id,
                project_id=program.id,
                transport_id=transport.id,
            )
