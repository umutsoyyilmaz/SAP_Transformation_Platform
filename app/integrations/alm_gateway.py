"""
SAP Cloud ALM Integration Gateway — FDD-F07, S4-02.

All outbound HTTP calls to SAP Cloud ALM REST API go through this class.
Direct `requests` calls in services or blueprints are FORBIDDEN.

Design mirrors `app/ai/gateway.py`:
  - OAuth2 client credentials with in-memory token cache + auto-refresh
  - Retry: max 2 attempts, exponential backoff (1 s → 4 s)
  - Timeout: 30 s (configurable per call)
  - Circuit breaker: ≥5 failures in 60 s → 30 s pause per tenant
  - Structured result returned to service; service writes to CloudALMSyncLog

Threading: token cache and circuit breaker state are in-memory dicts.
Flask is single-threaded by default; for multi-worker deployments migrate
to Redis-backed state (deferred: Faz C, ADR-003 appendix item).

Testability: pass a mock `session` to ALMGateway() in tests instead of
letting it create a real requests.Session internally.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ── Circuit breaker constants ──────────────────────────────────────────────
_CB_FAILURE_THRESHOLD = 5          # failures within window before opening
_CB_WINDOW_SECONDS = 60            # failure counting window (seconds)
_CB_OPEN_DURATION_SECONDS = 30     # how long circuit stays open

# ── Retry constants ────────────────────────────────────────────────────────
_RETRY_MAX = 2
_RETRY_BACKOFF_SECONDS = [1, 4]    # sleep[0] after 1st fail, sleep[1] after 2nd

# ── Default request timeout ────────────────────────────────────────────────
_DEFAULT_TIMEOUT = 30


class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open for this tenant.

    Callers should surface this as a 503 / retry-after response.
    """


class GatewayResult:
    """Structured return value from ALMGateway calls.

    Attributes:
        ok:             True if the call succeeded (HTTP 2xx + no exception).
        status_code:    HTTP status code (None if network-level failure).
        data:           Parsed JSON response body (dict or list), else None.
        error:          Human-readable error message or None.
        duration_ms:    Round-trip latency in milliseconds.
        payload_hash:   SHA-256 of the serialised request payload (hex).
    """

    def __init__(
        self,
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
        """Return fields suitable for CloudALMSyncLog creation."""
        return {
            "http_status_code": self.status_code,
            "error_message": self.error,
            "duration_ms": self.duration_ms,
            "payload_hash": self.payload_hash,
            "sync_status": "success" if self.ok else "error",
        }


class ALMGateway:
    """SAP Cloud ALM REST API gateway.

    Instantiate once at module level (module-level singleton pattern).
    Pass a custom `session` in tests to intercept HTTP calls without
    making real network requests.

    Usage:
        from app.integrations.alm_gateway import alm_gateway
        result = alm_gateway.test_connection(config, tenant_id=1)
    """

    def __init__(self, session: requests.Session | None = None) -> None:
        # Inject custom session for testing; create real one lazily otherwise.
        self._session: requests.Session | None = session

        # Token cache: tenant_id → {"access_token": str, "expires_at": datetime}
        self._token_cache: dict[int, dict] = {}

        # Circuit breaker: tenant_id → {"failures": [datetime, ...], "open_until": datetime|None}
        self._cb_state: dict[int, dict] = {}

    # ── HTTP session ─────────────────────────────────────────────────────────

    @property
    def session(self) -> requests.Session:
        """Return (or lazily create) the requests.Session."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    # ── OAuth2 token management ───────────────────────────────────────────────

    def _get_cached_token(self, tenant_id: int) -> str | None:
        """Return a valid cached access token, or None if expired/absent."""
        entry = self._token_cache.get(tenant_id)
        if not entry:
            return None
        # Treat token as expired 60 s before actual expiry to avoid race conditions
        if datetime.now(timezone.utc) >= entry["expires_at"] - timedelta(seconds=60):
            return None
        return entry["access_token"]

    def get_token(self, config: Any, tenant_id: int) -> str:
        """Return a valid OAuth2 access token for the given config.

        Uses client credentials flow (grant_type=client_credentials).
        Caches the token until 60 s before expiry to prevent hammering the
        token endpoint on every API call.

        Args:
            config: CloudALMConfig ORM instance with token_url, client_id,
                    and the *decrypted* client_secret passed as
                    `config._plaintext_secret` (service sets this transiently
                    before calling the gateway, never persisted).
            tenant_id: Used as cache key.

        Returns:
            Bearer access token string.

        Raises:
            requests.HTTPError: If token endpoint returns non-2xx.
            ValueError: If token response is missing access_token.
        """
        cached = self._get_cached_token(tenant_id)
        if cached:
            return cached

        # Request new token via client credentials
        logger.info("Fetching OAuth2 token for tenant=%s", tenant_id)
        resp = self.session.post(
            config.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": config.client_id,
                "client_secret": config._plaintext_secret,
            },
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()

        access_token = body.get("access_token")
        if not access_token:
            raise ValueError(f"OAuth2 token response missing access_token: {body}")

        expires_in = int(body.get("expires_in", 3600))
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        self._token_cache[tenant_id] = {
            "access_token": access_token,
            "expires_at": expires_at,
        }
        logger.info(
            "OAuth2 token obtained tenant=%s expires_in=%ss", tenant_id, expires_in
        )
        return access_token

    def invalidate_token(self, tenant_id: int) -> None:
        """Evict cached token; next call will re-fetch from token endpoint."""
        self._token_cache.pop(tenant_id, None)

    # ── Circuit breaker ───────────────────────────────────────────────────────

    def _ensure_cb_entry(self, tenant_id: int) -> dict:
        if tenant_id not in self._cb_state:
            self._cb_state[tenant_id] = {"failures": [], "open_until": None}
        return self._cb_state[tenant_id]

    def _circuit_closed(self, tenant_id: int) -> bool:
        """Return True if the circuit allows calls; False if open (paused)."""
        state = self._ensure_cb_entry(tenant_id)
        now = datetime.now(timezone.utc)

        # If circuit has been explicitly opened, check if cool-down elapsed
        if state["open_until"] and now < state["open_until"]:
            logger.warning(
                "Circuit open for tenant=%s until %s", tenant_id, state["open_until"]
            )
            return False

        # Prune failures outside the counting window
        window_start = now - timedelta(seconds=_CB_WINDOW_SECONDS)
        state["failures"] = [f for f in state["failures"] if f >= window_start]

        if len(state["failures"]) >= _CB_FAILURE_THRESHOLD:
            # Open the circuit
            state["open_until"] = now + timedelta(seconds=_CB_OPEN_DURATION_SECONDS)
            logger.error(
                "Circuit opened for tenant=%s: %d failures in %ds window",
                tenant_id,
                len(state["failures"]),
                _CB_WINDOW_SECONDS,
            )
            return False

        return True

    def _record_failure(self, tenant_id: int) -> None:
        state = self._ensure_cb_entry(tenant_id)
        state["failures"].append(datetime.now(timezone.utc))

    def _record_success(self, tenant_id: int) -> None:
        """On success, reset failure history and close the circuit."""
        state = self._ensure_cb_entry(tenant_id)
        state["failures"].clear()
        state["open_until"] = None

    # ── Core request dispatcher ───────────────────────────────────────────────

    def _compute_payload_hash(self, payload: dict | list | None) -> str | None:
        """Return SHA-256 hex digest of the JSON-serialised payload."""
        if payload is None:
            return None
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _do_request(
        self,
        method: str,
        url: str,
        headers: dict,
        *,
        json_body: dict | list | None = None,
        params: dict | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> requests.Response:
        """Execute a single HTTP request, no retry logic here."""
        kwargs: dict[str, Any] = {"headers": headers, "timeout": timeout}
        if json_body is not None:
            kwargs["json"] = json_body
        if params:
            kwargs["params"] = params
        return self.session.request(method, url, **kwargs)

    def request(
        self,
        method: str,
        url: str,
        *,
        config: Any,
        tenant_id: int,
        json_body: dict | list | None = None,
        params: dict | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> GatewayResult:
        """Execute an authenticated request to SAP Cloud ALM with retries.

        Implements:
          1. Circuit breaker check — reject immediately if tenant is paused.
          2. OAuth2 token injection.
          3. Execute request; on 2xx → return success result.
          4. On failure (non-2xx or network error):
             - Record failure for circuit breaker.
             - Retry up to _RETRY_MAX times with exponential backoff.
             - If all retries exhausted → return error result.
          5. 401 Unauthorized → invalidate token cache and retry once.

        Args:
            method:     HTTP verb ("GET", "POST", "PUT", etc.)
            url:        Full URL for the target ALM endpoint.
            config:     CloudALMConfig with OAuth2 credentials.
            tenant_id:  Used for circuit breaker + token cache keying.
            json_body:  JSON-serialisable request body (optional).
            params:     URL query params (optional).
            timeout:    Per-request timeout in seconds.

        Returns:
            GatewayResult — always returns (never raises). Callers check .ok.
        """
        if not self._circuit_closed(tenant_id):
            return GatewayResult(
                ok=False,
                status_code=None,
                data=None,
                error="Circuit breaker is open — SAP Cloud ALM calls temporarily suspended",
                duration_ms=0,
            )

        payload_hash = self._compute_payload_hash(json_body)
        token_refreshed = False
        last_error: str = "Unknown error"
        last_status: int | None = None

        for attempt in range(_RETRY_MAX + 1):  # 0, 1, 2
            try:
                token = self.get_token(config, tenant_id)
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }

                t0 = time.perf_counter()
                resp = self._do_request(
                    method, url, headers,
                    json_body=json_body, params=params, timeout=timeout,
                )
                duration_ms = int((time.perf_counter() - t0) * 1000)
                last_status = resp.status_code

                if resp.status_code == 401 and not token_refreshed:
                    # Token rejected — evict cache and retry once immediately
                    self.invalidate_token(tenant_id)
                    token_refreshed = True
                    continue

                if resp.ok:
                    self._record_success(tenant_id)
                    try:
                        data = resp.json() if resp.content else {}
                    except ValueError:
                        data = {}
                    return GatewayResult(
                        ok=True,
                        status_code=resp.status_code,
                        data=data,
                        error=None,
                        duration_ms=duration_ms,
                        payload_hash=payload_hash,
                    )

                # Non-2xx — record failure and decide whether to retry
                last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"
                self._record_failure(tenant_id)
                logger.warning(
                    "ALM request failed attempt=%d/%d status=%d url=%s tenant=%s",
                    attempt + 1, _RETRY_MAX + 1, resp.status_code, url, tenant_id,
                )

            except requests.Timeout:
                duration_ms = int(timeout * 1000)
                last_error = f"Request timed out after {timeout}s"
                self._record_failure(tenant_id)
                logger.warning(
                    "ALM request timed out attempt=%d/%d url=%s tenant=%s",
                    attempt + 1, _RETRY_MAX + 1, url, tenant_id,
                )

            except requests.RequestException as exc:
                duration_ms = 0
                last_error = str(exc)[:500]
                self._record_failure(tenant_id)
                logger.warning(
                    "ALM network error attempt=%d/%d url=%s tenant=%s error=%s",
                    attempt + 1, _RETRY_MAX + 1, url, tenant_id, last_error,
                )

            # Sleep before retry (except after last attempt)
            if attempt < _RETRY_MAX:
                sleep_s = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
                logger.info("Retrying ALM request in %ss (attempt %d)", sleep_s, attempt + 2)
                time.sleep(sleep_s)

        # All retries exhausted
        t_total = sum(_RETRY_BACKOFF_SECONDS[:_RETRY_MAX]) * 1000
        return GatewayResult(
            ok=False,
            status_code=last_status,
            data=None,
            error=last_error,
            duration_ms=t_total,
            payload_hash=payload_hash,
        )

    # ── SAP Cloud ALM specific operations ─────────────────────────────────────

    def test_connection(self, config: Any, tenant_id: int) -> GatewayResult:
        """Verify connectivity by requesting an OAuth2 token and a lightweight endpoint.

        Uses GET /api/calm-ops/v1/projects (pagination limit=1) as the
        probe — it's the lightest read-only endpoint in the Cloud ALM API.
        If the token fetch succeeds but the probe returns 403, we still
        consider the connection "ok" (credentials work; permissions TBD).

        Returns:
            GatewayResult.ok=True if authentication succeeds.
        """
        url = f"{config.alm_url.rstrip('/')}/api/calm-ops/v1/projects"
        result = self.request(
            "GET", url,
            config=config, tenant_id=tenant_id,
            params={"$top": 1},
        )
        # 403 = authenticated but no project access — still "connection ok"
        if not result.ok and result.status_code == 403:
            return GatewayResult(
                ok=True,
                status_code=403,
                data={"note": "Authenticated; project access restricted"},
                error=None,
                duration_ms=result.duration_ms,
                payload_hash=None,
            )
        return result

    def push_requirements(
        self,
        config: Any,
        tenant_id: int,
        requirements: list[dict],
    ) -> GatewayResult:
        """POST a batch of requirements to SAP Cloud ALM.

        SAP Cloud ALM endpoint: POST /api/calm-ops/v1/requirements
        (standard ODATA/REST batch create).

        The requirement payload shape expected by Cloud ALM:
          {"title": str, "description": str, "externalId": str, "priority": str}

        Returns:
            GatewayResult.data = {
              "created": list[{externalId, almId}],
              "updated": list[{externalId, almId}],
              "errors": list[{externalId, error}],
            }
        """
        url = f"{config.alm_url.rstrip('/')}/api/calm-ops/v1/requirements"
        return self.request(
            "POST", url,
            config=config, tenant_id=tenant_id,
            json_body={"requirements": requirements},
        )

    def pull_requirements(
        self,
        config: Any,
        tenant_id: int,
        project_id_filter: str | None = None,
    ) -> GatewayResult:
        """GET requirements from SAP Cloud ALM for this ALM project.

        Returns:
            GatewayResult.data = {"value": list[dict]}  (OData response shape)
        """
        url = f"{config.alm_url.rstrip('/')}/api/calm-ops/v1/requirements"
        params: dict = {"$format": "json"}
        if project_id_filter:
            params["$filter"] = f"projectId eq '{project_id_filter}'"
        return self.request(
            "GET", url,
            config=config, tenant_id=tenant_id,
            params=params,
        )

    def push_test_results(
        self,
        config: Any,
        tenant_id: int,
        test_results: list[dict],
    ) -> GatewayResult:
        """POST test execution results to SAP Cloud ALM.

        Endpoint: POST /api/calm-ops/v1/test-runs

        Args:
            test_results: List of test result dicts, each with at least:
                {externalTestCaseId, status, executedAt, executedBy, notes}
        """
        url = f"{config.alm_url.rstrip('/')}/api/calm-ops/v1/test-runs"
        return self.request(
            "POST", url,
            config=config, tenant_id=tenant_id,
            json_body={"testRuns": test_results},
        )


# Module-level singleton — import this instance in services.
# In tests, override via:
#   from app.integrations import alm_gateway as gw_module
#   gw_module.alm_gateway = ALMGateway(session=mock_session)
alm_gateway = ALMGateway()
