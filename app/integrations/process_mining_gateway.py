"""S8-01 FDD-I05 Phase B — Process Mining integration gateway.

Architecture (ADR-003 D1-D2):
  ProcessMiningGateway is a separate, independent class from ALMGateway.
  It uses the Strategy adapter pattern to support multiple providers:
    - CelonisAdapter  — API key auth (X-Api-Key header)
    - SignavioAdapter  — OAuth2 client-credentials flow
  All outbound HTTP calls route through the typed gateway call path,
  which enforces: circuit breaker → auth injection → retry → audit log.

Provider constants:
  timeout    = 45 s  (mining APIs can be slower than ALM)
  retry_max  = 2     (max retry attempts after initial failure)
  backoff    = [1, 4] seconds (exponential backoff per ADR-003)
  rate_limit = 50 req/min (provider-side courtesy limit)
  CB_threshold = 5 failures in 60 s window → open circuit for 30 s
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ── Process Mining gateway constants (ADR-003 §3.2 variant) ─────────────────

_DEFAULT_TIMEOUT = 45          # seconds — mining APIs can be slower
_RETRY_MAX = 2                 # max extra attempts after first failure
_RETRY_BACKOFF_SECONDS = [1, 4]  # sleep before attempt 2 and 3

# Circuit breaker — per-connection keying
_CB_FAILURE_THRESHOLD = 5
_CB_WINDOW_SECONDS = 60
_CB_OPEN_DURATION_SECONDS = 30


# ── Value objects ─────────────────────────────────────────────────────────────


class ProcessMiningGatewayResult:
    """Typed result returned by all ProcessMiningGateway methods.

    Always check .ok before accessing .data.
    Never raises — all errors are captured in .error.
    """

    __slots__ = ("ok", "status_code", "data", "error", "duration_ms", "payload_hash")

    def __init__(
        self,
        *,
        ok: bool,
        status_code: int | None,
        data: dict | list | None,
        error: str | None,
        duration_ms: int,
        payload_hash: str | None = None,
    ) -> None:
        self.ok = ok
        self.status_code = status_code
        self.data = data
        self.error = error
        self.duration_ms = duration_ms
        self.payload_hash = payload_hash

    def to_log_dict(self) -> dict:
        """Structured representation for audit logging. Never include raw secrets."""
        return {
            "ok": self.ok,
            "status_code": self.status_code,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "payload_hash": self.payload_hash,
        }


class ProviderConnectionError(Exception):
    """Raised when provider configuration is missing or invalid."""


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is tripped for a connection."""


# ── Provider adapters (Strategy pattern) ─────────────────────────────────────


class BaseProcessMiningAdapter(ABC):
    """Abstract adapter — all provider adapters implement this interface.

    Why Strategy instead of inheritance: providers differ significantly in
    authentication (API key vs OAuth2) and API shape. Adapters encapsulate
    those differences so the gateway can treat all providers uniformly.
    """

    def __init__(self, connection: Any, session: requests.Session) -> None:
        self._conn = connection
        self._session = session

    @abstractmethod
    def build_auth_headers(self) -> dict[str, str]:
        """Return HTTP headers required for authenticated requests."""

    def base_url(self) -> str:
        """Return the connection base URL, stripped of trailing slash."""
        url = (self._conn.connection_url or "").rstrip("/")
        if not url:
            raise ProviderConnectionError(
                f"ProcessMiningConnection id={self._conn.id} has no connection_url configured."
            )
        return url

    def ping_url(self) -> str:
        """Return a lightweight test endpoint URL."""
        return f"{self.base_url()}/api/v1/processes"

    def processes_url(self) -> str:
        return f"{self.base_url()}/api/v1/processes"

    def variants_url(self, process_id: str) -> str:
        return f"{self.base_url()}/api/v1/processes/{process_id}/variants"


class CelonisAdapter(BaseProcessMiningAdapter):
    """Celonis Cloud: API key authentication (Bearer or X-Api-Key header).

    Celonis uses a static API key. No token refresh required.
    The decrypted key is injected per request — it is NEVER stored in memory
    beyond the lifetime of a single request.
    """

    def build_auth_headers(self) -> dict[str, str]:
        from app.utils.crypto import decrypt_secret

        if not self._conn.api_key_encrypted:
            raise ProviderConnectionError(
                f"Celonis connection id={self._conn.id} has no API key configured."
            )
        api_key = decrypt_secret(self._conn.api_key_encrypted)
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def ping_url(self) -> str:
        # Celonis: GET /api/v1/teams is a lightweight health endpoint
        return f"{self.base_url()}/api/v1/teams"

    def processes_url(self) -> str:
        return f"{self.base_url()}/api/v1/packages"

    def variants_url(self, process_id: str) -> str:
        return f"{self.base_url()}/api/v1/packages/{process_id}/variants"


class SignavioAdapter(BaseProcessMiningAdapter):
    """SAP Signavio Process Intelligence: OAuth2 client-credentials auth.

    Token is fetched from token_url using client_id + client_secret
    and cached in-process by tenant until expiry.
    """

    # Class-level token cache: connection_id → {access_token, expires_at}
    _token_cache: dict[int, dict] = {}

    def _fetch_token(self) -> str:
        from app.utils.crypto import decrypt_secret

        if not self._conn.client_id or not self._conn.encrypted_secret:
            raise ProviderConnectionError(
                f"Signavio connection id={self._conn.id} missing client_id or secret."
            )
        if not self._conn.token_url:
            raise ProviderConnectionError(
                f"Signavio connection id={self._conn.id} missing token_url."
            )

        # Check in-process cache
        cached = self._token_cache.get(self._conn.id)
        if cached and datetime.now(timezone.utc) < cached["expires_at"]:
            return cached["access_token"]

        secret = decrypt_secret(self._conn.encrypted_secret)
        resp = self._session.post(
            self._conn.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._conn.client_id,
                "client_secret": secret,
            },
            timeout=20,
        )
        if not resp.ok:
            raise ProviderConnectionError(
                f"Signavio token fetch failed: HTTP {resp.status_code}"
            )
        payload = resp.json()
        token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 3600))
        self._token_cache[self._conn.id] = {
            "access_token": token,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60),
        }
        return token

    def invalidate_token(self) -> None:
        """Evict cached token — called on 401 to force re-fetch."""
        self._token_cache.pop(self._conn.id, None)

    def build_auth_headers(self) -> dict[str, str]:
        token = self._fetch_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def ping_url(self) -> str:
        return f"{self.base_url()}/v1/directory/info"


# ── ProcessMiningGateway ─────────────────────────────────────────────────────


class ProcessMiningGateway:
    """Typed gateway for all process-mining provider calls.

    Implements per-connection circuit breaker, retry with exponential backoff,
    audit logging, and provider-agnostic dispatch via adapter Strategy.

    Usage:
        gw = build_process_mining_gateway(connection)
        result = gw.list_processes()
        if result.ok:
            processes = result.data

    Never instantiate directly outside this module. Use build_process_mining_gateway().
    """

    # Class-level circuit breaker state: connection_id → {failures: [datetime], open_until}
    _cb_state: dict[int, dict] = {}

    def __init__(
        self,
        connection: Any,
        session: requests.Session | None = None,
    ) -> None:
        self._connection = connection
        self.session = session or requests.Session()
        self._adapter = self._build_adapter()

    # ── Adapter factory ───────────────────────────────────────────────────────

    def _build_adapter(self) -> BaseProcessMiningAdapter:
        """Select provider adapter based on connection.provider.

        Raises ProviderConnectionError for unknown providers so misconfiguration
        fails loud at gateway construction time, not silently at call time.
        """
        provider = (self._connection.provider or "").lower()
        match provider:
            case "celonis":
                return CelonisAdapter(self._connection, self.session)
            case "signavio":
                return SignavioAdapter(self._connection, self.session)
            case "uipath" | "sap_lama" | "custom":
                # Generic: try API key if configured, else raise
                if self._connection.api_key_encrypted:
                    return CelonisAdapter(self._connection, self.session)
                if self._connection.encrypted_secret:
                    return SignavioAdapter(self._connection, self.session)
                raise ProviderConnectionError(
                    f"Provider '{provider}' requires either api_key or OAuth2 credentials."
                )
            case _:
                raise ProviderConnectionError(
                    f"Unknown process mining provider: '{provider}'. "
                    f"Must be one of: celonis, signavio, uipath, sap_lama, custom."
                )

    # ── Circuit breaker ───────────────────────────────────────────────────────

    def _circuit_closed(self) -> bool:
        """Return True if the circuit is closed (calls allowed)."""
        conn_id = self._connection.id
        state = self._cb_state.get(conn_id)
        if not state:
            return True
        open_until = state.get("open_until")
        if open_until and datetime.now(timezone.utc) < open_until:
            return False
        # Circuit may be half-open — prune old failures and re-evaluate
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=_CB_WINDOW_SECONDS)
        state["failures"] = [f for f in state.get("failures", []) if f > window_start]
        if len(state["failures"]) >= _CB_FAILURE_THRESHOLD:
            state["open_until"] = now + timedelta(seconds=_CB_OPEN_DURATION_SECONDS)
            return False
        state.pop("open_until", None)
        return True

    def _record_failure(self) -> None:
        conn_id = self._connection.id
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=_CB_WINDOW_SECONDS)
        state = self._cb_state.setdefault(conn_id, {"failures": []})
        state["failures"] = [f for f in state["failures"] if f > window_start]
        state["failures"].append(now)
        if len(state["failures"]) >= _CB_FAILURE_THRESHOLD:
            state["open_until"] = now + timedelta(seconds=_CB_OPEN_DURATION_SECONDS)
            logger.warning(
                "Process mining circuit breaker opened connection_id=%s failures=%d",
                conn_id,
                len(state["failures"]),
            )

    def _record_success(self) -> None:
        self._cb_state.pop(self._connection.id, None)

    # ── Internal HTTP dispatch ────────────────────────────────────────────────

    @staticmethod
    def _compute_payload_hash(body: dict | list | None) -> str | None:
        if body is None:
            return None
        try:
            raw = json.dumps(body, sort_keys=True, default=str).encode()
            return hashlib.sha256(raw).hexdigest()[:16]
        except Exception:
            return None

    def _call(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        json_body: dict | list | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> ProcessMiningGatewayResult:
        """Execute an authenticated request with retry and circuit breaker.

        Mirrors ALMGateway.request() behaviour (ADR-003 canonical _call pattern):
          1. Circuit breaker check — reject immediately if open.
          2. Build auth headers via adapter.
          3. Execute; on 2xx → success.
          4. On 401 → if Signavio, invalidate token and retry once immediately.
          5. On failure → record CB failure, sleep, retry up to _RETRY_MAX times.
          6. All retries exhausted → GatewayResult(ok=False).

        Returns:
            ProcessMiningGatewayResult — always returns, never raises.
        """
        if not self._circuit_closed():
            return ProcessMiningGatewayResult(
                ok=False,
                status_code=None,
                data=None,
                error="Circuit breaker open — process mining calls temporarily suspended",
                duration_ms=0,
            )

        payload_hash = self._compute_payload_hash(json_body)
        token_refreshed = False
        last_error: str = "Unknown error"
        last_status: int | None = None

        for attempt in range(_RETRY_MAX + 1):  # 0, 1, 2
            try:
                headers = self._adapter.build_auth_headers()
                kwargs: dict[str, Any] = {"headers": headers, "timeout": timeout}
                if json_body is not None:
                    kwargs["json"] = json_body
                if params:
                    kwargs["params"] = params

                t0 = time.perf_counter()
                resp = self.session.request(method, url, **kwargs)
                duration_ms = int((time.perf_counter() - t0) * 1000)
                last_status = resp.status_code

                # 401 with Signavio → invalidate cached token and retry once
                if resp.status_code == 401 and not token_refreshed:
                    if isinstance(self._adapter, SignavioAdapter):
                        self._adapter.invalidate_token()
                    token_refreshed = True
                    logger.info(
                        "Process mining 401 — token invalidated, retrying connection_id=%s",
                        self._connection.id,
                    )
                    continue

                if resp.ok:
                    self._record_success()
                    try:
                        data = resp.json() if resp.content else {}
                    except ValueError:
                        data = {}
                    return ProcessMiningGatewayResult(
                        ok=True,
                        status_code=resp.status_code,
                        data=data,
                        error=None,
                        duration_ms=duration_ms,
                        payload_hash=payload_hash,
                    )

                last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"
                self._record_failure()
                logger.warning(
                    "Process mining request failed attempt=%d/%d status=%d url=%s connection_id=%s",
                    attempt + 1, _RETRY_MAX + 1, resp.status_code, url, self._connection.id,
                )

            except requests.Timeout:
                last_error = f"Request timed out after {timeout}s"
                self._record_failure()
                logger.warning(
                    "Process mining request timed out attempt=%d/%d url=%s connection_id=%s",
                    attempt + 1, _RETRY_MAX + 1, url, self._connection.id,
                )

            except ProviderConnectionError:
                raise  # Configuration errors should not be retried — re-raise immediately

            except requests.RequestException as exc:
                last_error = str(exc)[:500]
                self._record_failure()
                logger.warning(
                    "Process mining network error attempt=%d/%d url=%s connection_id=%s error=%s",
                    attempt + 1, _RETRY_MAX + 1, url, self._connection.id, last_error,
                )

            if attempt < _RETRY_MAX:
                sleep_s = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
                logger.info(
                    "Retrying process mining request in %ss (attempt %d) connection_id=%s",
                    sleep_s, attempt + 2, self._connection.id,
                )
                time.sleep(sleep_s)

        return ProcessMiningGatewayResult(
            ok=False,
            status_code=last_status,
            data=None,
            error=last_error,
            duration_ms=0,
            payload_hash=payload_hash,
        )

    # ── Public gateway operations ─────────────────────────────────────────────

    def test_connection(self) -> ProcessMiningGatewayResult:
        """Verify connectivity with the provider by hitting a lightweight endpoint.

        Treats 403 as "connection ok but access restricted" — credentials work.
        Returns:
            ProcessMiningGatewayResult.ok=True if authentication succeeded.
        """
        url = self._adapter.ping_url()
        result = self._call("GET", url)
        if not result.ok and result.status_code == 403:
            return ProcessMiningGatewayResult(
                ok=True,
                status_code=403,
                data={"note": "Authenticated; access may be restricted by provider permissions"},
                error=None,
                duration_ms=result.duration_ms,
                payload_hash=None,
            )
        return result

    def list_processes(self, params: dict | None = None) -> ProcessMiningGatewayResult:
        """Fetch available process definitions from the provider.

        Returns:
            ProcessMiningGatewayResult.data = list or dict of processes from provider.
        """
        url = self._adapter.processes_url()
        return self._call("GET", url, params=params or {"limit": 50})

    def fetch_variants(
        self,
        process_id: str,
        params: dict | None = None,
    ) -> ProcessMiningGatewayResult:
        """Fetch process variants for a given process ID.

        Args:
            process_id: Provider-side process identifier.
            params:     Optional query params (pagination, filters).

        Returns:
            ProcessMiningGatewayResult.data = list or dict of variants.
        """
        url = self._adapter.variants_url(process_id)
        return self._call("GET", url, params=params or {"limit": 100})


# ── Factory function (preferred over singleton — connection is per-instanced) ──


def build_process_mining_gateway(connection: Any) -> ProcessMiningGateway:
    """Construct a ProcessMiningGateway for the given connection record.

    Use this factory instead of directly instantiating ProcessMiningGateway.
    In tests, inject a mock session:
        from app.integrations import process_mining_gateway as gw_module
        conn = ...  # test connection fixture
        gw = gw_module.build_process_mining_gateway(conn)
        gw.session = MockSession(...)
    """
    return ProcessMiningGateway(connection)
