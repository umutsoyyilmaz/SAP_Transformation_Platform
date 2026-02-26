"""Tests for process mining service — S8-01 FDD-I05 Phase B.

Coverage:
  1. save_connection encrypts credentials (secret never stored plaintext)
  2. to_dict never leaks sensitive fields
  3. import_variants creates ProcessVariantImport DB records
  4. promote_variant_to_process_level creates L4 ProcessLevel + links variant
  5. test_connection updates status to 'active' on success
  6. test_connection updates status to 'failed' on gateway error
  7. Tenant isolation: connection from tenant A not reachable by tenant B

Run: APP_ENV=testing .venv/bin/python -m pytest tests/test_process_mining_service.py -v
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

# ── Inject ENCRYPTION_KEY before any import that touches crypto ──────────────
# _get_fernet() raises at call-time (not import-time), but setting the env var
# here — at module load — guarantees it's present for every test in this file
# regardless of pytest fixture ordering.
if not os.environ.get("ENCRYPTION_KEY"):
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from app.models import db
from app.models.auth import Tenant
from app.models.process_mining import ProcessMiningConnection, ProcessVariantImport
from app.models.program import Program
import app.services.process_mining_service as pms
from app.core.exceptions import NotFoundError


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_tenant(tenant_id: int, slug: str | None = None) -> Tenant:
    """Create or return existing Tenant row. slug defaults to 'test-<id>'."""
    existing = db.session.get(Tenant, tenant_id)
    if existing:
        return existing
    t = Tenant(id=tenant_id, name=f"Tenant {tenant_id}", slug=slug or f"test-{tenant_id}")
    db.session.add(t)
    db.session.flush()
    return t


def _make_program(tenant_id: int, program_id: int | None = None) -> Program:
    """Create and persist a Program row scoped to tenant."""
    p = Program(
        id=program_id,
        tenant_id=tenant_id,
        name="Test Program",
    )
    db.session.add(p)
    db.session.flush()
    return p


def _connection_payload(
    provider: str = "celonis",
    api_key: str = "raw-key-value",
) -> dict:
    return {
        "provider": provider,
        "connection_url": "https://test.celonis.cloud",
        "api_key": api_key,
        "is_enabled": True,
    }


def _make_connection(tenant_id: int, **kwargs) -> dict:
    """Persist a connection via the service and return the dict."""
    payload = {**_connection_payload(), **kwargs}
    return pms.save_connection(tenant_id, payload)


def _fake_gateway_result(
    ok: bool = True,
    data: list | None = None,
    error: str | None = None,
) -> MagicMock:
    """Build a lightweight ProcessMiningGatewayResult stand-in."""
    r = MagicMock()
    r.ok = ok
    r.data = data if data is not None else []
    r.error = error
    r.duration_ms = 42
    return r


# ── Tests ────────────────────────────────────────────────────────────────────


class TestSaveConnectionEncryptsCredentials:
    """save_connection must Fernet-encrypt api_key before writing."""

    def test_api_key_encrypted_at_rest(self):
        """Raw API key value must not equal the stored ciphertext."""
        _make_tenant(1)
        raw_key = "super-secret-api-key-123"

        pms.save_connection(1, _connection_payload(api_key=raw_key))

        conn = db.session.execute(
            db.select(ProcessMiningConnection).where(ProcessMiningConnection.tenant_id == 1)
        ).scalar_one()

        assert conn.api_key_encrypted is not None
        assert conn.api_key_encrypted != raw_key, (
            "api_key_encrypted must store ciphertext, not plaintext"
        )

    def test_client_secret_encrypted_at_rest(self):
        """OAuth2 client_secret must be stored as Fernet ciphertext."""
        _make_tenant(1)
        raw_secret = "oauth2-client-secret-xyz"

        pms.save_connection(1, {
            "provider": "signavio",
            "connection_url": "https://signavio.example.com",
            "client_id": "cid",
            "client_secret": raw_secret,
            "is_enabled": True,
        })

        conn = db.session.execute(
            db.select(ProcessMiningConnection).where(ProcessMiningConnection.tenant_id == 1)
        ).scalar_one()

        assert conn.encrypted_secret is not None
        assert conn.encrypted_secret != raw_secret, (
            "encrypted_secret must store ciphertext, not plaintext"
        )


class TestSensitiveFieldsNotLeaked:
    """ProcessMiningConnection.to_dict() must exclude all SENSITIVE_FIELDS."""

    def test_api_key_encrypted_absent_from_dict(self):
        """get_connection() must not return api_key_encrypted."""
        _make_tenant(1)
        _make_connection(1)

        result = pms.get_connection(1)

        assert result is not None
        assert "api_key_encrypted" not in result, (
            "api_key_encrypted must never appear in the serialized response"
        )

    def test_encrypted_secret_absent_from_dict(self):
        """get_connection() must not return encrypted_secret."""
        _make_tenant(1)
        pms.save_connection(1, {
            "provider": "signavio",
            "connection_url": "https://signavio.example.com",
            "client_id": "cid",
            "client_secret": "super_secret",
            "is_enabled": True,
        })

        result = pms.get_connection(1)

        assert "encrypted_secret" not in result, (
            "encrypted_secret must never appear in the serialized response"
        )


class TestImportVariantsCreatesRecords:
    """import_variants must persist ProcessVariantImport rows to the DB."""

    def test_creates_process_variant_import_records(self):
        """All fetched variants should be written as separate import records."""
        _make_tenant(1)
        prog = _make_program(1)
        _make_connection(1)

        fake_variants = [
            {"id": "V001", "name": "Happy Path", "caseCount": 100, "conformance": 95.5},
            {"id": "V002", "name": "Exception Path", "caseCount": 20, "conformance": 42.0},
        ]
        mock_gw = MagicMock()
        mock_gw.fetch_variants.return_value = _fake_gateway_result(data=fake_variants)

        with patch(
            "app.integrations.process_mining_gateway.build_process_mining_gateway",
            return_value=mock_gw,
        ):
            result = pms.import_variants(1, prog.id, "PROC-001")

        assert result["imported"] == 2
        assert result["skipped"] == 0

        rows = db.session.execute(
            db.select(ProcessVariantImport).where(
                ProcessVariantImport.tenant_id == 1,
                ProcessVariantImport.project_id == prog.id,
            )
        ).scalars().all()
        assert len(rows) == 2
        variant_ids = {r.variant_id for r in rows}
        assert variant_ids == {"V001", "V002"}

    def test_skips_duplicate_imports(self):
        """Re-importing the same variant IDs must not create duplicates."""
        _make_tenant(1)
        prog = _make_program(1)
        _make_connection(1)

        fake_variants = [{"id": "V001", "name": "Happy Path", "caseCount": 50}]
        mock_gw = MagicMock()
        mock_gw.fetch_variants.return_value = _fake_gateway_result(data=fake_variants)

        with patch(
            "app.integrations.process_mining_gateway.build_process_mining_gateway",
            return_value=mock_gw,
        ):
            pms.import_variants(1, prog.id, "PROC-001")
            second = pms.import_variants(1, prog.id, "PROC-001")

        assert second["imported"] == 0
        assert second["skipped"] == 1

        count = db.session.execute(
            db.select(db.func.count()).select_from(ProcessVariantImport).where(
                ProcessVariantImport.tenant_id == 1
            )
        ).scalar()
        assert count == 1

    def test_selected_variant_ids_filters_import(self):
        """Only variants in selected_variant_ids should be stored."""
        _make_tenant(1)
        prog = _make_program(1)
        _make_connection(1)

        fake_variants = [
            {"id": "V001", "name": "Happy Path"},
            {"id": "V002", "name": "Detour Path"},
            {"id": "V003", "name": "Error Path"},
        ]
        mock_gw = MagicMock()
        mock_gw.fetch_variants.return_value = _fake_gateway_result(data=fake_variants)

        with patch(
            "app.integrations.process_mining_gateway.build_process_mining_gateway",
            return_value=mock_gw,
        ):
            result = pms.import_variants(1, prog.id, "PROC-001", selected_variant_ids=["V001", "V003"])

        assert result["imported"] == 2
        stored_ids = {v["variant_id"] for v in result["variants"]}
        assert stored_ids == {"V001", "V003"}
        assert "V002" not in stored_ids


class TestPromoteVariantCreatesProcessLevel:
    """promote_variant_to_process_level must create an L4 ProcessLevel."""

    def test_creates_l4_process_level(self):
        """Promoting a variant must yield a ProcessLevel with level=4."""
        from app.models.explore.process import ProcessLevel

        _make_tenant(1)
        prog = _make_program(1)
        _make_connection(1)

        # Create an L3 parent process level
        parent_id = str(uuid.uuid4())
        parent = ProcessLevel(
            id=parent_id,
            tenant_id=1,
            project_id=prog.id,
            level=3,
            code="P.01.01.01",
            name="Order Processing",
        )
        db.session.add(parent)

        # Persist a variant import in 'imported' status
        variant = ProcessVariantImport(
            tenant_id=1,
            project_id=prog.id,
            variant_id="V001",
            process_name="Happy Path",
            status="imported",
        )
        db.session.add(variant)
        db.session.commit()

        result = pms.promote_variant_to_process_level(
            tenant_id=1,
            project_id=prog.id,
            variant_import_id=variant.id,
            parent_process_level_id=parent_id,
        )

        assert result["process_level"]["level"] == 4
        assert result["variant_import"]["status"] == "promoted"
        assert result["variant_import"]["promoted_to_process_level_id"] is not None

    def test_reject_already_promoted_variant_raises_validation_error(self):
        """Attempting to reject a 'promoted' variant must raise ValidationError."""
        from app.core.exceptions import ValidationError as VE

        _make_tenant(1)
        prog = _make_program(1)

        variant = ProcessVariantImport(
            tenant_id=1,
            project_id=prog.id,
            variant_id="V001",
            process_name="Promoted Path",
            status="promoted",
        )
        db.session.add(variant)
        db.session.commit()

        with pytest.raises(VE, match="already promoted"):
            pms.reject_variant(1, prog.id, variant.id)


class TestConnectionStatus:
    """test_connection must persist the updated status to the DB."""

    def test_updates_status_to_active_on_success(self):
        """A successful gateway ping must set connection status to 'active'."""
        _make_tenant(1)
        _make_connection(1)

        mock_gw = MagicMock()
        mock_gw.test_connection.return_value = _fake_gateway_result(ok=True)

        with patch(
            "app.integrations.process_mining_gateway.build_process_mining_gateway",
            return_value=mock_gw,
        ):
            result = pms.test_connection(1)

        assert result["ok"] is True
        assert result["status"] == "active"

        conn_dict = pms.get_connection(1)
        assert conn_dict["status"] == "active"

    def test_updates_status_to_failed_on_gateway_error(self):
        """A failed gateway ping must set status to 'failed' with error message."""
        _make_tenant(1)
        _make_connection(1)

        mock_gw = MagicMock()
        mock_gw.test_connection.return_value = _fake_gateway_result(
            ok=False, error="Connection timed out"
        )

        with patch(
            "app.integrations.process_mining_gateway.build_process_mining_gateway",
            return_value=mock_gw,
        ):
            result = pms.test_connection(1)

        assert result["ok"] is False
        assert result["status"] == "failed"

        conn_dict = pms.get_connection(1)
        assert conn_dict["status"] == "failed"
        assert "timed out" in (conn_dict.get("error_message") or "")

    def test_test_connection_raises_not_found_when_no_connection(self):
        """test_connection on a tenant with no connection must raise NotFoundError."""
        _make_tenant(1)

        with pytest.raises(NotFoundError):
            pms.test_connection(1)


class TestTenantIsolation:
    """Tenant A must NEVER be able to access Tenant B's connection."""

    def test_get_connection_returns_none_for_other_tenant(self):
        """Tenant 2 must not see tenant 1's connection (returns None)."""
        _make_tenant(1)
        _make_tenant(2)
        _make_connection(1)

        # Tenant 2 has no connection — get_connection returns None (not leaks tenant 1 data)
        result = pms.get_connection(2)
        assert result is None

    def test_delete_connection_raises_for_other_tenant(self):
        """Deleting with a different tenant_id must raise NotFoundError."""
        _make_tenant(1)
        _make_tenant(2)
        _make_connection(1)

        with pytest.raises(NotFoundError):
            pms.delete_connection(2)

    def test_list_imports_tenant_isolation(self):
        """list_imports must only return records for the requesting tenant."""
        _make_tenant(1)
        _make_tenant(2)
        prog1 = _make_program(1, program_id=None)
        prog2 = _make_program(2, program_id=None)
        db.session.commit()

        # Seed a record for tenant 1 and one for tenant 2
        db.session.add(ProcessVariantImport(
            tenant_id=1, project_id=prog1.id, variant_id="V001", status="imported"
        ))
        db.session.add(ProcessVariantImport(
            tenant_id=2, project_id=prog2.id, variant_id="V999", status="imported"
        ))
        db.session.commit()

        page_t1 = pms.list_imports(1, prog1.id)
        items_t1 = page_t1["items"]
        assert page_t1["total"] == 1
        assert all(r["tenant_id"] == 1 for r in items_t1)
        assert items_t1[0]["variant_id"] == "V001"

        # Tenant 2 project should not return tenant 1's records
        page_t2 = pms.list_imports(2, prog2.id)
        assert page_t2["total"] == 1
        assert page_t2["items"][0]["variant_id"] == "V999"
