"""Unit tests for app.services.cloud_alm_service — FDD-F07 Phase B, S4-02.

Test strategy
-------------
All outbound HTTP is mocked via patch.object on the module-level
`alm_gateway` singleton so no real SAP Cloud ALM instance is needed.

The ENCRYPTION_KEY env var is set once per session to a freshly generated
Fernet key; every test can then call encrypt_secret / decrypt_secret normally.

Each test creates its own data and tears down via the `session` autouse
fixture (rollback + recreate tables).

Coverage
--------
    1. test_connection_returns_ok_with_valid_mock_oauth
    2. test_push_requirements_calls_correct_alm_endpoint
    3. test_push_requirements_writes_sync_log_on_success
    4. test_push_requirements_writes_sync_log_on_error
    5. test_push_requirements_updates_external_id_on_each_requirement
    6. test_get_config_does_not_return_encrypted_secret
    7. test_tenant_isolation_push_blocks_cross_tenant_config
"""

import os
import uuid
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

import app.integrations.alm_gateway as gw_module
from app.integrations.alm_gateway import GatewayResult
from app.models import db
from app.models.auth import Tenant
from app.models.explore.infrastructure import CloudALMSyncLog
from app.models.explore.requirement import ExploreRequirement
from app.models.integrations import CloudALMConfig
from app.models.program import Program
from app.utils.crypto import encrypt_secret
import app.services.cloud_alm_service as cloud_alm_svc


# ── Session fixture: configure ENCRYPTION_KEY once ──────────────────────────


@pytest.fixture(scope="session", autouse=True)
def encryption_key():
    """Set a stable ENCRYPTION_KEY for the entire test session.

    Without this, `encrypt_secret` / `decrypt_secret` raise RuntimeError
    because ENCRYPTION_KEY env var is not set in the test environment.
    The key is set BEFORE any test runs and is intentionally session-scoped
    so every test uses the same key (required for encrypt/decrypt to work
    across fixture boundaries that create DB rows earlier in the session).
    """
    key = Fernet.generate_key().decode()
    os.environ["ENCRYPTION_KEY"] = key
    yield key
    # Leave it set so teardown in other tests doesn't fail


# ── Helper factories ─────────────────────────────────────────────────────────


_tenant_counter = 0


def _make_tenant(slug_prefix: str = "t") -> Tenant:
    """Create and flush a unique Tenant row.

    Each call produces a unique slug so tests can create multiple tenants
    without UNIQUE constraint violations on the tenants table.
    """
    global _tenant_counter
    _tenant_counter += 1
    t = Tenant(name=f"Test Tenant {_tenant_counter}", slug=f"{slug_prefix}-{_tenant_counter}")
    db.session.add(t)
    db.session.flush()
    return t


def _make_program(tenant_id: int, name: str = "Test Program") -> Program:
    """Create and flush a minimal Program row."""
    prog = Program(tenant_id=tenant_id, name=name)
    db.session.add(prog)
    db.session.flush()
    return prog


def _make_config(tenant_id: int, secret: str = "test-client-secret") -> CloudALMConfig:
    """Create and flush a CloudALMConfig with encrypted secret."""
    cfg = CloudALMConfig(
        tenant_id=tenant_id,
        alm_url="https://example.alm.cloud.sap",
        client_id="test-client-id",
        encrypted_secret=encrypt_secret(secret),
        token_url="https://auth.hana.ondemand.com/oauth/token",
        sync_requirements=True,
        sync_test_results=False,
        is_active=True,
    )
    db.session.add(cfg)
    db.session.flush()
    return cfg


def _make_requirement(
    project_id: int,
    tenant_id: int,
    status: str = "approved",
    code_suffix: str = "001",
) -> ExploreRequirement:
    """Create and flush a minimal ExploreRequirement."""
    req = ExploreRequirement(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        project_id=project_id,
        code=f"REQ-{code_suffix}",
        title=f"Requirement {code_suffix}",
        status=status,
        type="development",
        priority="P2",
        created_by_id=str(uuid.uuid4()),
    )
    db.session.add(req)
    db.session.flush()
    return req


def _ok_result(**kwargs) -> GatewayResult:
    """Convenience: build a successful GatewayResult."""
    defaults = dict(ok=True, status_code=200, data={}, error=None, duration_ms=50, payload_hash="abc123")
    defaults.update(kwargs)
    return GatewayResult(
        ok=defaults["ok"],
        status_code=defaults["status_code"],
        data=defaults["data"],
        error=defaults["error"],
        duration_ms=defaults["duration_ms"],
        payload_hash=defaults["payload_hash"],
    )


def _err_result(**kwargs) -> GatewayResult:
    """Convenience: build a failed GatewayResult."""
    defaults = dict(ok=False, status_code=500, data=None, error="Internal Server Error", duration_ms=100, payload_hash=None)
    defaults.update(kwargs)
    return GatewayResult(
        ok=defaults["ok"],
        status_code=defaults["status_code"],
        data=defaults["data"],
        error=defaults["error"],
        duration_ms=defaults["duration_ms"],
        payload_hash=defaults["payload_hash"],
    )


# ── Tests ────────────────────────────────────────────────────────────────────


class TestTestConnection:
    """Covers: test_connection_returns_ok_with_valid_mock_oauth."""

    def test_test_connection_returns_ok_with_valid_mock_oauth(self):
        """test_connection() returns ok=True when gateway mock succeeds.

        Given: a valid CloudALMConfig exists for tenant
        When:  the gateway returns a successful GatewayResult
        Then:  the service returns {"ok": True} and persists last_test_status="ok"
        """
        t = _make_tenant()
        _make_config(tenant_id=t.id)
        db.session.commit()

        mock_result = _ok_result(data={"projects": []})
        with patch.object(gw_module.alm_gateway, "test_connection", return_value=mock_result) as mock_tc:
            result = cloud_alm_svc.test_connection(tenant_id=t.id, user_id=None)

        assert result["ok"] is True
        assert result["error"] is None
        assert result["duration_ms"] == 50
        mock_tc.assert_called_once()

        # Config should have last_test_status updated
        cfg = db.session.execute(
            select(CloudALMConfig).where(CloudALMConfig.tenant_id == t.id)
        ).scalar_one()
        assert cfg.last_test_status == "ok"
        assert cfg.last_test_at is not None

    def test_test_connection_raises_if_no_config_exists(self):
        """test_connection() raises ValueError when no config is set up.

        This prevents a confusing 500 that would mask the missing-config state.
        """
        with pytest.raises(ValueError, match="No Cloud ALM config"):
            cloud_alm_svc.test_connection(tenant_id=99, user_id=None)


class TestPushRequirements:
    """Covers tests 2–5: push requirements endpoint/log/external-id behaviour."""

    def test_push_requirements_calls_push_gateway_method(self):
        """push_requirements() delegates to gateway.push_requirements (not test_connection etc.)."""
        t = _make_tenant()
        prog = _make_program(tenant_id=t.id)
        _make_config(tenant_id=t.id)
        _make_requirement(project_id=prog.id, tenant_id=t.id, code_suffix="001")
        db.session.commit()

        mock_result = _ok_result(data={"created": [], "updated": [], "errors": []})
        with patch.object(gw_module.alm_gateway, "push_requirements", return_value=mock_result) as mock_push:
            cloud_alm_svc.push_requirements(tenant_id=t.id, project_id=prog.id)

        mock_push.assert_called_once()
        # Verify the payload passed contains at least one requirement dict
        call_args = mock_push.call_args
        payload = call_args.args[2]  # push_requirements(config, tenant_id, requirements)
        assert isinstance(payload, list)
        assert len(payload) >= 1
        assert "externalId" in payload[0]

    def test_push_requirements_writes_sync_log_on_success(self):
        """On success, exactly one CloudALMSyncLog row with direction='push' and status='success' is written."""
        t = _make_tenant()
        prog = _make_program(tenant_id=t.id)
        _make_config(tenant_id=t.id)
        _make_requirement(project_id=prog.id, tenant_id=t.id, code_suffix="002")
        db.session.commit()

        mock_result = _ok_result(data={"created": [], "updated": [], "errors": []})
        with patch.object(gw_module.alm_gateway, "push_requirements", return_value=mock_result):
            cloud_alm_svc.push_requirements(tenant_id=t.id, project_id=prog.id)

        logs = db.session.execute(
            select(CloudALMSyncLog).where(
                CloudALMSyncLog.tenant_id == t.id,
                CloudALMSyncLog.sync_direction == "push",
            )
        ).scalars().all()

        assert len(logs) == 1
        assert logs[0].sync_status == "success"
        assert logs[0].project_id == prog.id

    def test_push_requirements_writes_sync_log_on_error(self):
        """On gateway error, a sync log is written with status='error', not swallowed silently."""
        t = _make_tenant()
        prog = _make_program(tenant_id=t.id)
        _make_config(tenant_id=t.id)
        _make_requirement(project_id=prog.id, tenant_id=t.id, code_suffix="003")
        db.session.commit()

        mock_result = _err_result()
        with patch.object(gw_module.alm_gateway, "push_requirements", return_value=mock_result):
            result = cloud_alm_svc.push_requirements(tenant_id=t.id, project_id=prog.id)

        # Service should still return a structured result, not raise
        assert result["errors"] >= 1

        logs = db.session.execute(
            select(CloudALMSyncLog).where(
                CloudALMSyncLog.tenant_id == t.id,
                CloudALMSyncLog.sync_direction == "push",
            )
        ).scalars().all()

        assert len(logs) == 1
        assert logs[0].sync_status == "error"

    def test_push_requirements_updates_external_id_on_each_requirement(self):
        """When gateway returns alm_id in 'created', the requirement.alm_id is populated."""
        t = _make_tenant()
        prog = _make_program(tenant_id=t.id)
        _make_config(tenant_id=t.id)
        req = _make_requirement(project_id=prog.id, tenant_id=t.id, code_suffix="004")
        db.session.commit()

        alm_external_id = "ALM-9999"
        mock_result = _ok_result(
            data={
                "created": [{"externalId": req.id, "almId": alm_external_id}],
                "updated": [],
                "errors": [],
            }
        )
        with patch.object(gw_module.alm_gateway, "push_requirements", return_value=mock_result):
            cloud_alm_svc.push_requirements(tenant_id=t.id, project_id=prog.id)

        # Re-fetch from DB to confirm commit propagated
        updated_req = db.session.get(ExploreRequirement, req.id)
        assert updated_req.alm_id == alm_external_id
        assert updated_req.alm_synced is True
        assert updated_req.alm_sync_status == "synced"


class TestConfigSecurity:
    """Covers: test_get_config_does_not_return_encrypted_secret."""

    def test_get_config_does_not_return_encrypted_secret(self):
        """get_config() must NEVER return encrypted_secret in its dict output.

        Security contract: the secret is write-only from the API perspective.
        Even SENSITIVE_FIELDS containing a typo would expose it — this test
        is the last-line defence against that regression.
        """
        t = _make_tenant()
        _make_config(tenant_id=t.id)
        db.session.commit()

        config_dict = cloud_alm_svc.get_config(tenant_id=t.id)
        assert config_dict is not None
        assert "encrypted_secret" not in config_dict
        # Ensure other expected fields ARE present
        assert "alm_url" in config_dict
        assert "client_id" in config_dict
        assert "tenant_id" in config_dict

    def test_create_or_update_config_does_not_return_encrypted_secret(self):
        """create_or_update_config() return value must also exclude encrypted_secret."""
        t = _make_tenant()
        db.session.commit()
        with patch.object(gw_module.alm_gateway, "invalidate_token"):
            result = cloud_alm_svc.create_or_update_config(
                tenant_id=t.id,
                data={
                    "alm_url": "https://test.alm.cloud.sap",
                    "client_id": "cid",
                    "client_secret": "super-secret",
                    "token_url": "https://auth.hana.ondemand.com/oauth/token",
                },
            )
        assert "encrypted_secret" not in result


class TestTenantIsolation:
    """Covers: test_tenant_isolation_push_blocks_cross_tenant_config."""

    def test_tenant_isolation_push_blocks_cross_tenant_config(self):
        """push_requirements() for tenant 2 must not use tenant 1's config.

        Structural guarantee: CloudALMConfig has unique-per-tenant constraint,
        so `_get_config(tenant_id=t2.id)` returns None and the service raises
        ValueError before any gateway call is made.
        This test verifies the isolation path is exercised, preventing
        accidental cross-tenant secret reuse.
        """
        # Only create config for tenant 1
        t1 = _make_tenant(slug_prefix="iso-a")
        t2 = _make_tenant(slug_prefix="iso-b")
        _make_config(tenant_id=t1.id)
        prog = _make_program(tenant_id=t1.id)
        db.session.commit()

        # Push with tenant 2 — no config exists for tenant 2
        with pytest.raises(ValueError, match="No Cloud ALM config"):
            cloud_alm_svc.push_requirements(tenant_id=t2.id, project_id=prog.id)
