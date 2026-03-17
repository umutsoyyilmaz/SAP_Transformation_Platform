"""Unit tests for sap_auth_service (FDD-I02 / S7-02).

Coverage:
  1. create_sap_auth_role           — returns dict with correct fields
  2. add_auth_object                — links auth object to role
  3. SOD matrix — conflict detected — F_BKPF_BUK ACTVT 01 + 60 creates risk
  4. SOD matrix — no conflict       — no overlap in ACTVT produces no rows
  5. export_auth_concept_excel      — returns non-empty bytes (valid xlsx magic)
  6. get_role_coverage              — counts linked process steps correctly
  7. tenant isolation               — cross-tenant raises ValueError
"""

import pytest

from app.models import db
from app.models.auth import Tenant
from app.models.program import Program
from app.services import sap_auth_service


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def tenant() -> Tenant:
    """Create and persist a test tenant."""
    t = Tenant(name="Auth Test Corp", slug="auth-test-corp")
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture()
def other_tenant() -> Tenant:
    """Second tenant for isolation tests."""
    t = Tenant(name="Other Auth Corp", slug="other-auth-corp")
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture()
def program(tenant: Tenant) -> Program:
    """Create and persist a test program owned by tenant."""
    p = Program(name="Auth Concept Project", tenant_id=tenant.id)
    db.session.add(p)
    db.session.commit()
    return p


# ── 1. Create role ────────────────────────────────────────────────────────────


class TestCreateSapAuthRole:
    def test_create_sap_auth_role_returns_dict_with_id(self, tenant: Tenant, program: Program):
        """Happy path: valid role creation returns serialised dict with id and defaults."""
        result = sap_auth_service.create_sap_auth_role(
            tenant_id=tenant.id,
            project_id=program.id,
            data={
                "role_name": "Z_FI_AR_CLERK",
                "role_type": "single",
                "sap_module": "FI",
            },
        )

        assert isinstance(result, dict)
        assert result["id"] is not None
        assert result["role_name"] == "Z_FI_AR_CLERK"
        assert result["role_type"] == "single"
        assert result["sap_module"] == "FI"
        assert result["status"] == "draft"
        assert result["tenant_id"] == tenant.id
        assert result["project_id"] == program.id

    def test_create_sap_auth_role_raises_on_missing_role_name(self, tenant: Tenant, program: Program):
        """Missing role_name must raise ValueError."""
        with pytest.raises(ValueError, match="role_name"):
            sap_auth_service.create_sap_auth_role(tenant.id, program.id, {})

    def test_create_sap_auth_role_raises_on_name_exceeds_30_chars(self, tenant: Tenant, program: Program):
        """Role names exceeding SAP's 30-char PFCG limit must be rejected."""
        with pytest.raises(ValueError, match="30"):
            sap_auth_service.create_sap_auth_role(
                tenant.id, program.id,
                {"role_name": "Z_THIS_ROLE_NAME_IS_WAY_TOO_LONG_FOR_SAP"},
            )

    def test_create_sap_auth_role_raises_on_invalid_project(self, tenant: Tenant):
        """Project that doesn't belong to tenant must raise ValueError."""
        with pytest.raises(ValueError):
            sap_auth_service.create_sap_auth_role(
                tenant_id=tenant.id,
                project_id=99999,
                data={"role_name": "Z_TEST"},
            )


# ── 2. Add auth object ────────────────────────────────────────────────────────


class TestAddAuthObject:
    def test_add_auth_object_links_to_role(self, tenant: Tenant, program: Program):
        """Auth object is created and linked to the specified role."""
        role = sap_auth_service.create_sap_auth_role(
            tenant.id, program.id,
            {"role_name": "Z_FI_POST"},
        )

        obj = sap_auth_service.add_auth_object(
            tenant_id=tenant.id,
            project_id=program.id,
            role_id=role["id"],
            data={
                "auth_object": "F_BKPF_BUK",
                "auth_object_description": "FI document company code",
                "field_values": {"ACTVT": ["01", "02", "03"], "BUKRS": ["1000"]},
                "source": "su24",
            },
        )

        assert obj["auth_object"] == "F_BKPF_BUK"
        assert obj["auth_role_id"] == role["id"]
        assert obj["field_values"]["ACTVT"] == ["01", "02", "03"]

        # Confirm role now reports 1 auth object
        full_role = sap_auth_service.get_sap_auth_role(tenant.id, program.id, role["id"])
        assert len(full_role["auth_objects"]) == 1

    def test_add_auth_object_raises_on_invalid_json_field_values(self, tenant: Tenant, program: Program):
        """Non-dict field_values must raise ValueError."""
        role = sap_auth_service.create_sap_auth_role(tenant.id, program.id, {"role_name": "Z_TEST2"})
        with pytest.raises((ValueError, TypeError)):
            sap_auth_service.add_auth_object(
                tenant.id, program.id, role["id"],
                {"auth_object": "F_BKPF_BUK", "field_values": "not-a-dict"},
            )


# ── 3. SOD matrix — conflict detected ────────────────────────────────────────


class TestSodMatrixConflictDetected:
    def test_sod_matrix_detects_create_approve_conflict(self, tenant: Tenant, program: Program):
        """
        Business rule: Two roles that together hold F_BKPF_BUK ACTVT 01 (create)
        and ACTVT 60 (approve) trigger a critical SOD conflict.

        This is the most important SOD check in SAP FI — it prevents a single
        employee from creating *and* approving financial documents.
        """
        role_creator = sap_auth_service.create_sap_auth_role(
            tenant.id, program.id, {"role_name": "Z_FI_CREATOR"}
        )
        role_approver = sap_auth_service.create_sap_auth_role(
            tenant.id, program.id, {"role_name": "Z_FI_APPROVER"}
        )

        sap_auth_service.add_auth_object(
            tenant.id, program.id, role_creator["id"],
            {"auth_object": "F_BKPF_BUK", "field_values": {"ACTVT": ["01"], "BUKRS": ["*"]}},
        )
        sap_auth_service.add_auth_object(
            tenant.id, program.id, role_approver["id"],
            {"auth_object": "F_BKPF_BUK", "field_values": {"ACTVT": ["60"], "BUKRS": ["*"]}},
        )

        conflicts = sap_auth_service.generate_sod_matrix(tenant.id, program.id)

        fi_conflicts = [
            c for c in conflicts
            if c.get("conflicting_auth_object") == "F_BKPF_BUK"
        ]
        assert len(fi_conflicts) >= 1

        critical = next((c for c in fi_conflicts if c["risk_level"] == "critical"), None)
        assert critical is not None, "Expected a critical F_BKPF_BUK SOD conflict"
        assert not critical["is_accepted"]


# ── 4. SOD matrix — no conflict ───────────────────────────────────────────────


class TestSodMatrixNoConflict:
    def test_sod_matrix_no_conflict_when_no_actvt_overlap(self, tenant: Tenant, program: Program):
        """
        Two roles with non-overlapping auth objects produce no SOD rows.
        This validates that the algorithm doesn't generate false positives.
        """
        role_a = sap_auth_service.create_sap_auth_role(
            tenant.id, program.id, {"role_name": "Z_MM_VIEW"}
        )
        role_b = sap_auth_service.create_sap_auth_role(
            tenant.id, program.id, {"role_name": "Z_SD_VIEW"}
        )

        # M_BEST_BSA objects but non-conflicting activities (not 01+08 combo)
        sap_auth_service.add_auth_object(
            tenant.id, program.id, role_a["id"],
            {"auth_object": "M_BEST_BSA", "field_values": {"ACTVT": ["03"]}},
        )
        sap_auth_service.add_auth_object(
            tenant.id, program.id, role_b["id"],
            {"auth_object": "S_TCODE", "field_values": {"TCD": ["ME21N"]}},
        )

        conflicts = sap_auth_service.generate_sod_matrix(tenant.id, program.id)
        assert len(conflicts) == 0


# ── 5. Export Excel ───────────────────────────────────────────────────────────


class TestExportExcel:
    def test_export_auth_concept_returns_excel_bytes(self, tenant: Tenant, program: Program):
        """
        export_auth_concept_excel must return non-empty bytes whose first 4 bytes
        match the PKZIP magic number (xlsx is a ZIP container).
        """
        sap_auth_service.create_sap_auth_role(
            tenant.id, program.id, {"role_name": "Z_EXPORT_TEST", "sap_module": "FI"}
        )

        result = sap_auth_service.export_auth_concept_excel(tenant.id, program.id)

        assert isinstance(result, bytes)
        assert len(result) > 0
        # PKZIP/xlsx magic: PK\x03\x04
        assert result[:4] == b"PK\x03\x04", "Expected xlsx (PKZIP) magic number"


# ── 6. Role coverage ──────────────────────────────────────────────────────────


class TestRoleCoverage:
    def test_role_coverage_counts_linked_process_steps(self, tenant: Tenant, program: Program):
        """
        Coverage percentage reflects the number of unique process step IDs
        that are linked to at least one role.

        Business importance: coverage drives the go-live readiness checklist.
        """
        role = sap_auth_service.create_sap_auth_role(
            tenant.id, program.id, {"role_name": "Z_COV_TEST"}
        )

        # Link role to 3 process steps
        sap_auth_service.link_role_to_process_steps(
            tenant_id=tenant.id,
            project_id=program.id,
            role_id=role["id"],
            process_step_ids=[101, 102, 103],
        )

        coverage = sap_auth_service.get_role_coverage(tenant.id, program.id)

        assert isinstance(coverage, dict)
        assert coverage["covered_steps"] == 3
        assert coverage["coverage_pct"] >= 0  # can't assert total without seed data
        assert isinstance(coverage["role_summary"], list)

    def test_role_coverage_returns_zero_when_no_roles(self, tenant: Tenant, program: Program):
        """Empty project returns zero coverage without error."""
        coverage = sap_auth_service.get_role_coverage(tenant.id, program.id)
        assert coverage["covered_steps"] == 0
        assert coverage["coverage_pct"] == 0.0


# ── 7. Tenant isolation ───────────────────────────────────────────────────────


class TestTenantIsolation:
    def test_cross_tenant_role_access_raises_valueerror(
        self, tenant: Tenant, other_tenant: Tenant, program: Program
    ):
        """
        Tenant A must not be able to access Tenant B's roles.
        The service must raise ValueError rather than silently returning data,
        which would constitute a cross-tenant data leak.
        """
        # Create a role under tenant
        role = sap_auth_service.create_sap_auth_role(
            tenant.id, program.id, {"role_name": "Z_SECRET_ROLE"}
        )

        # other_tenant tries to fetch it — must fail
        with pytest.raises(ValueError):
            sap_auth_service.get_sap_auth_role(
                tenant_id=other_tenant.id,
                project_id=program.id,
                role_id=role["id"],
            )

    def test_cross_tenant_project_raises_valueerror(
        self, tenant: Tenant, other_tenant: Tenant, program: Program
    ):
        """
        other_tenant cannot create roles inside a program it doesn't own.
        program.tenant_id == tenant.id, so other_tenant must be rejected.
        """
        with pytest.raises(ValueError):
            sap_auth_service.create_sap_auth_role(
                tenant_id=other_tenant.id,  # wrong tenant
                project_id=program.id,       # belongs to `tenant`
                data={"role_name": "Z_HACKED"},
            )
