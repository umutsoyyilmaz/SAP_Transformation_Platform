"""
Platform-wide exception hierarchy.

Why this module exists:
  Previously, each service defined its own ad-hoc exception classes
  (e.g. CustomFieldNotFoundError, LayoutNotFoundError). This made it
  impossible to write a single blueprint error handler and forced
  callers to import from service modules — a layer boundary violation.

  This module provides the canonical exception types that all services
  MUST raise. Blueprints register handlers against these types once
  and get consistent HTTP status codes everywhere.

Usage:
    from app.core.exceptions import NotFoundError, ValidationError

    raise NotFoundError(resource="Program", resource_id=42)
    raise ValidationError("Title is required", details={"title": "..."})
"""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist within the given scope.

    Security note: Used for BOTH genuinely missing records AND cross-tenant
    access attempts. This intentional ambiguity prevents information disclosure
    — a 403 would confirm the resource exists; a 404 does not.

    Args:
        resource: Human-readable model/entity name (e.g. "Program", "TestCase").
        resource_id: The PK that was looked up. Included in logs, not in HTTP response.
        tenant_id: Optional — the scope that was enforced. For debug logging only.
    """

    def __init__(
        self,
        resource: str,
        resource_id: int | str | None = None,
        tenant_id: int | None = None,
    ) -> None:
        self.resource = resource
        self.resource_id = resource_id
        self.tenant_id = tenant_id
        msg = f"{resource}"
        if resource_id is not None:
            msg += f" id={resource_id}"
        msg += " not found"
        if tenant_id is not None:
            msg += f" (tenant={tenant_id})"
        super().__init__(msg)


class ValidationError(Exception):
    """Raised when input fails business-rule validation in the service layer.

    Distinct from HTTP 400 (malformed input, caught in blueprint) — this
    exception signals that the data was well-formed but violated a business
    rule (e.g. invalid state transition, duplicate code, FK constraint).

    Maps to HTTP 422 in blueprint error handlers.

    Args:
        message: Human-readable explanation of what failed.
        details: Optional field-level breakdown for structured API responses.
                 Keys are field names; values are error descriptions.
    """

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.details = details or {}
        super().__init__(message)


class ConflictError(Exception):
    """Raised when an operation would create a duplicate unique constraint violation.

    Maps to HTTP 409.

    Args:
        resource: Model name.
        field: The unique field that would be duplicated.
        value: The conflicting value (truncated in HTTP response; full in logs).
    """

    def __init__(self, resource: str, field: str, value: str | None = None) -> None:
        self.resource = resource
        self.field = field
        self.value = value
        msg = f"{resource} with {field}={value!r} already exists"
        super().__init__(msg)
