"""Standardised API error responses.

Usage
-----
    from app.utils.errors import api_error, E

    return api_error(E.NOT_FOUND, "Workshop not found")
    return api_error(E.VALIDATION_REQUIRED, "project_id is required")
    return api_error(E.GOVERNANCE_BLOCK, "Gate blocked", details={"governance": gov})
"""

from __future__ import annotations

from flask import jsonify


# ── Error code constants ──────────────────────────────────────────────
class E:
    """Machine-readable error code constants.

    Convention:
     • ERR_  prefix for standard application errors
     • GOVERNANCE_ prefix for governance-gate errors
    """

    # Validation – HTTP 400
    VALIDATION_REQUIRED = "ERR_VALIDATION_REQUIRED"
    VALIDATION_INVALID = "ERR_VALIDATION_INVALID"
    VALIDATION_CONSTRAINT = "ERR_VALIDATION_CONSTRAINT"

    # Not-found – HTTP 404
    NOT_FOUND = "ERR_NOT_FOUND"

    # Conflict / duplicate – HTTP 409
    CONFLICT_DUPLICATE = "ERR_CONFLICT_DUPLICATE"
    CONFLICT_STATE = "ERR_CONFLICT_STATE"

    # Permissions – HTTP 403
    FORBIDDEN = "ERR_FORBIDDEN"

    # Server – HTTP 500
    DATABASE = "ERR_DATABASE"
    INTERNAL = "ERR_INTERNAL"

    # Governance – HTTP 400 (block) / 200 (warn)
    GOVERNANCE_BLOCK = "GOVERNANCE_BLOCK"
    GOVERNANCE_WARN = "GOVERNANCE_WARN"


# ── Default HTTP status mapping ───────────────────────────────────────
_DEFAULT_STATUS: dict[str, int] = {
    E.VALIDATION_REQUIRED: 400,
    E.VALIDATION_INVALID: 400,
    E.VALIDATION_CONSTRAINT: 400,
    E.NOT_FOUND: 404,
    E.CONFLICT_DUPLICATE: 409,
    E.CONFLICT_STATE: 409,
    E.FORBIDDEN: 403,
    E.DATABASE: 500,
    E.INTERNAL: 500,
    E.GOVERNANCE_BLOCK: 400,
    E.GOVERNANCE_WARN: 400,
}


def api_error(
    code: str,
    message: str,
    *,
    status: int | None = None,
    details: dict | None = None,
):
    """Return a standard JSON error response.

    Parameters
    ----------
    code : str
        Machine-readable error code (use ``E.*`` constants).
    message : str
        Human-readable explanation for developers / UI.
    status : int, optional
        HTTP status override.  Falls back to ``_DEFAULT_STATUS[code]``,
        then to ``400``.
    details : dict, optional
        Extra structured payload (governance result, blocking IDs, etc.).

    Returns
    -------
    tuple[Response, int]
        ``(jsonify(body), http_status)`` – drop-in for Flask views.
    """

    http_status = status or _DEFAULT_STATUS.get(code, 400)

    body: dict = {
        "error": message,
        "code": code,
    }
    if details:
        body["details"] = details

    return jsonify(body), http_status
