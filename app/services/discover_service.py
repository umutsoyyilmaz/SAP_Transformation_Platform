"""
Discover phase business logic — FDD-B02 / S3-01.

Manages the Discover phase of the SAP Activate methodology:
  - ProjectCharter: why this project? (justification, scope, objectives)
  - SystemLandscape: AS-IS system inventory
  - ScopeAssessment: initial sizing estimate per SAP module

Discover -> Prepare Gate transition criteria (get_discover_gate_status):
  1. charter_approved     — ProjectCharter.status == 'approved'
  2. landscape_defined    — At least 1 active SystemLandscape record
  3. min_3_modules        — At least 3 ScopeAssessment modules defined

All functions accept tenant_id as a parameter; the g object is NEVER accessed.
db.session.commit() is called only in this file (service layer ownership).
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import db
from app.models.program import ProjectCharter, ScopeAssessment, SystemLandscape

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

VALID_PROJECT_TYPES = {"greenfield", "brownfield", "selective_migration", "cloud_move"}
VALID_CHARTER_STATUSES = {"draft", "in_review", "approved", "rejected"}
VALID_SYSTEM_TYPES = {"sap_erp", "s4hana", "non_sap", "middleware", "cloud", "legacy"}
VALID_ROLES = {"source", "target", "interface", "decommission", "keep"}
VALID_ENVIRONMENTS = {"dev", "test", "q", "prod"}
VALID_COMPLEXITIES = {"low", "medium", "high", "very_high"}
VALID_ASSESSMENT_BASES = {"workshop", "document_review", "interview", "expert_estimate"}

# Minimum number of modules for the Discover Gate
DISCOVER_GATE_MIN_MODULES = 3


# ── ProjectCharter ────────────────────────────────────────────────────────────


def get_charter(tenant_id: int, program_id: int) -> dict | None:
    """Return the charter for a program or None if it does not exist.

    Args:
        tenant_id: Tenant scope — never skipped.
        program_id: Target program.

    Returns:
        Serialized charter dict or None.
    """
    stmt = select(ProjectCharter).where(
        ProjectCharter.tenant_id == tenant_id,
        ProjectCharter.program_id == program_id,
    )
    charter = db.session.execute(stmt).scalars().first()
    return charter.to_dict() if charter else None


def create_or_update_charter(tenant_id: int, program_id: int, data: dict) -> dict:
    """Create or update the ProjectCharter for a program.

    Business rule: Only one charter per program. If one exists, update it.
    If status is 'approved', the charter is locked — only approval_notes can
    be updated; structural fields are blocked to preserve the audit record.

    Args:
        tenant_id: Tenant scope.
        program_id: Target program.
        data: Validated input dict from blueprint.

    Returns:
        Serialized charter dict.

    Raises:
        ValueError: If an approved charter cannot be modified structurally.
    """
    stmt = select(ProjectCharter).where(
        ProjectCharter.tenant_id == tenant_id,
        ProjectCharter.program_id == program_id,
    )
    charter = db.session.execute(stmt).scalars().first()

    if charter is None:
        charter = ProjectCharter(tenant_id=tenant_id, program_id=program_id)
        db.session.add(charter)
        logger.info("Creating ProjectCharter", extra={"tenant_id": tenant_id, "program_id": program_id})
    else:
        if charter.status == "approved":
            # Approved charters are locked; reject structural edits
            allowed_fields = {"approval_notes"}
            structural_keys = set(data.keys()) - allowed_fields
            if structural_keys:
                raise ValueError(
                    "Approved charter cannot be modified. "
                    "Revoke approval first or contact your project admin."
                )

    # Apply updatable fields
    UPDATABLE_FIELDS = [
        "project_objective", "business_drivers", "expected_benefits", "key_risks",
        "in_scope_summary", "out_of_scope_summary", "affected_countries",
        "affected_sap_modules", "project_type", "target_go_live_date",
        "estimated_duration_months", "approval_notes",
    ]
    for field in UPDATABLE_FIELDS:
        if field in data:
            setattr(charter, field, data[field])

    # status can only be set to draft/in_review via this function; approved/rejected
    # go through approve_charter() which enforces permission checks in the blueprint
    if "status" in data and data["status"] in {"draft", "in_review"}:
        charter.status = data["status"]

    db.session.commit()
    logger.info(
        "ProjectCharter saved",
        extra={"tenant_id": tenant_id, "program_id": program_id, "charter_id": charter.id},
    )
    return charter.to_dict()


def approve_charter(
    tenant_id: int,
    program_id: int,
    approver_id: int,
    notes: str | None = None,
) -> dict:
    """Approve the charter and unlock the Discover Gate.

    Business rule: Charter must exist and be in 'in_review' or 'draft' status.
    Once approved, discover_gate criterion 'charter_approved' becomes True.

    Args:
        tenant_id: Tenant scope.
        program_id: Target program.
        approver_id: User performing the approval.
        notes: Optional approval comment.

    Returns:
        Serialized approved charter.

    Raises:
        LookupError: If charter does not exist for this tenant/program.
        ValueError: If charter is already approved or rejected.
    """
    stmt = select(ProjectCharter).where(
        ProjectCharter.tenant_id == tenant_id,
        ProjectCharter.program_id == program_id,
    )
    charter = db.session.execute(stmt).scalars().first()
    if not charter:
        raise LookupError(f"No charter found for program {program_id} in this tenant.")
    if charter.status == "approved":
        raise ValueError("Charter is already approved.")
    if charter.status == "rejected":
        raise ValueError("Rejected charter must be reset to draft before re-approval.")

    charter.status = "approved"
    charter.approved_by_id = approver_id
    charter.approved_at = datetime.now(timezone.utc)
    charter.approval_notes = notes

    db.session.commit()
    logger.info(
        "ProjectCharter approved",
        extra={
            "tenant_id": tenant_id,
            "program_id": program_id,
            "charter_id": charter.id,
            "approver_id": approver_id,
        },
    )
    return charter.to_dict()


# ── SystemLandscape ───────────────────────────────────────────────────────────


def list_system_landscapes(tenant_id: int, program_id: int) -> list[dict]:
    """List all active system landscape entries for a program.

    Args:
        tenant_id: Tenant scope.
        program_id: Target program.

    Returns:
        List of serialized SystemLandscape dicts, ordered by id.
    """
    stmt = select(SystemLandscape).where(
        SystemLandscape.tenant_id == tenant_id,
        SystemLandscape.program_id == program_id,
    ).order_by(SystemLandscape.id)
    return [s.to_dict() for s in db.session.execute(stmt).scalars().all()]


def add_system_landscape(tenant_id: int, program_id: int, data: dict) -> dict:
    """Add a new system to the program's landscape inventory.

    Args:
        tenant_id: Tenant scope.
        program_id: Target program.
        data: Validated input dict.

    Returns:
        Serialized SystemLandscape dict.
    """
    landscape = SystemLandscape(
        tenant_id=tenant_id,
        program_id=program_id,
        system_name=data["system_name"],
        system_type=data.get("system_type", "non_sap"),
        role=data.get("role", "source"),
        vendor=data.get("vendor"),
        version=data.get("version"),
        environment=data.get("environment", "prod"),
        description=data.get("description"),
        notes=data.get("notes"),
        is_active=data.get("is_active", True),
    )
    db.session.add(landscape)
    db.session.commit()
    logger.info(
        "SystemLandscape entry added",
        extra={"tenant_id": tenant_id, "program_id": program_id, "system_name": data["system_name"]},
    )
    return landscape.to_dict()


def update_system_landscape(tenant_id: int, program_id: int, landscape_id: int, data: dict) -> dict:
    """Update an existing system landscape entry.

    Args:
        tenant_id: Tenant scope — verifies ownership.
        program_id: Must match landscape.program_id.
        landscape_id: Target record.
        data: Fields to update.

    Returns:
        Serialized updated SystemLandscape.

    Raises:
        LookupError: If not found for this tenant/program.
    """
    stmt = select(SystemLandscape).where(
        SystemLandscape.id == landscape_id,
        SystemLandscape.tenant_id == tenant_id,
        SystemLandscape.program_id == program_id,
    )
    landscape = db.session.execute(stmt).scalars().first()
    if not landscape:
        raise LookupError(f"SystemLandscape {landscape_id} not found.")

    UPDATABLE = ["system_name", "system_type", "role", "vendor", "version",
                 "environment", "description", "notes", "is_active"]
    for field in UPDATABLE:
        if field in data:
            setattr(landscape, field, data[field])

    db.session.commit()
    return landscape.to_dict()


def delete_system_landscape(tenant_id: int, program_id: int, landscape_id: int) -> None:
    """Delete a system landscape entry.

    Why hard delete: landscape entries are inventory records, not audit artifacts.
    If an entry needs to be excluded from diagrams, use is_active=False instead.

    Args:
        tenant_id: Tenant scope — verifies ownership.
        program_id: Must match landscape.program_id.
        landscape_id: Target record.

    Raises:
        LookupError: If not found for this tenant/program.
    """
    stmt = select(SystemLandscape).where(
        SystemLandscape.id == landscape_id,
        SystemLandscape.tenant_id == tenant_id,
        SystemLandscape.program_id == program_id,
    )
    landscape = db.session.execute(stmt).scalars().first()
    if not landscape:
        raise LookupError(f"SystemLandscape {landscape_id} not found.")

    db.session.delete(landscape)
    db.session.commit()
    logger.info(
        "SystemLandscape entry deleted",
        extra={"tenant_id": tenant_id, "landscape_id": landscape_id},
    )


# ── ScopeAssessment ───────────────────────────────────────────────────────────


def list_scope_assessments(tenant_id: int, program_id: int) -> list[dict]:
    """List all scope assessments for a program ordered by module name.

    Args:
        tenant_id: Tenant scope.
        program_id: Target program.

    Returns:
        List of serialized ScopeAssessment dicts.
    """
    stmt = select(ScopeAssessment).where(
        ScopeAssessment.tenant_id == tenant_id,
        ScopeAssessment.program_id == program_id,
    ).order_by(ScopeAssessment.sap_module)
    return [a.to_dict() for a in db.session.execute(stmt).scalars().all()]


def save_scope_assessment(tenant_id: int, program_id: int, sap_module: str, data: dict) -> dict:
    """Create or update a scope assessment for a specific SAP module (upsert).

    Business rule: One assessment per program+tenant+module combination.
    If an entry already exists for this module, it is updated in place.

    Args:
        tenant_id: Tenant scope.
        program_id: Target program.
        sap_module: e.g. 'FI', 'MM', 'SD' — normalised to uppercase.
        data: Validated input dict.

    Returns:
        Serialized ScopeAssessment dict.
    """
    module_upper = sap_module.upper().strip()
    stmt = select(ScopeAssessment).where(
        ScopeAssessment.tenant_id == tenant_id,
        ScopeAssessment.program_id == program_id,
        ScopeAssessment.sap_module == module_upper,
    )
    assessment = db.session.execute(stmt).scalars().first()

    if assessment is None:
        assessment = ScopeAssessment(
            tenant_id=tenant_id,
            program_id=program_id,
            sap_module=module_upper,
        )
        db.session.add(assessment)

    UPDATABLE = [
        "is_in_scope", "complexity", "estimated_requirements",
        "estimated_gaps", "notes", "assessment_basis", "assessed_by_id",
    ]
    for field in UPDATABLE:
        if field in data:
            setattr(assessment, field, data[field])

    if data.get("assessed_by_id"):
        assessment.assessed_at = datetime.now(timezone.utc)

    db.session.commit()
    logger.info(
        "ScopeAssessment saved",
        extra={"tenant_id": tenant_id, "program_id": program_id, "sap_module": module_upper},
    )
    return assessment.to_dict()


def delete_scope_assessment(tenant_id: int, program_id: int, assessment_id: int) -> None:
    """Delete a scope assessment entry.

    Args:
        tenant_id: Tenant scope.
        program_id: Must match assessment.program_id.
        assessment_id: Target record.

    Raises:
        LookupError: If not found.
    """
    stmt = select(ScopeAssessment).where(
        ScopeAssessment.id == assessment_id,
        ScopeAssessment.tenant_id == tenant_id,
        ScopeAssessment.program_id == program_id,
    )
    assessment = db.session.execute(stmt).scalars().first()
    if not assessment:
        raise LookupError(f"ScopeAssessment {assessment_id} not found.")

    db.session.delete(assessment)
    db.session.commit()


# ── Discover Gate ─────────────────────────────────────────────────────────────


def get_discover_gate_status(tenant_id: int, program_id: int) -> dict:
    """Evaluate whether all Discover → Prepare gate criteria are met.

    Gate criteria (all must pass to unlock the gate):
      1. charter_approved     — ProjectCharter.status == 'approved'
      2. landscape_defined    — >= 1 active SystemLandscape entry with is_active=True
      3. min_3_modules        — >= 3 ScopeAssessment records defined

    Returns:
        dict with keys:
          - gate_passed (bool)
          - criteria (list of criterion dicts with name, passed, current, required)

    Design note: This is a lightweight in-process gate check. For heavy
    gate evaluations (with defect counts, test coverage etc.) use gate_service.py.
    """
    # ① Charter approved?
    stmt_charter = select(ProjectCharter).where(
        ProjectCharter.tenant_id == tenant_id,
        ProjectCharter.program_id == program_id,
    )
    charter = db.session.execute(stmt_charter).scalars().first()
    charter_approved = charter is not None and charter.status == "approved"

    # ② System landscape defined (at least 1 active entry)?
    stmt_landscape = select(SystemLandscape).where(
        SystemLandscape.tenant_id == tenant_id,
        SystemLandscape.program_id == program_id,
        SystemLandscape.is_active.is_(True),
    )
    landscape_count = len(db.session.execute(stmt_landscape).scalars().all())
    landscape_defined = landscape_count >= 1

    # ③ Minimum 3 SAP modules assessed
    stmt_scope = select(ScopeAssessment).where(
        ScopeAssessment.tenant_id == tenant_id,
        ScopeAssessment.program_id == program_id,
    )
    module_count = len(db.session.execute(stmt_scope).scalars().all())
    min_modules_assessed = module_count >= DISCOVER_GATE_MIN_MODULES

    criteria = [
        {
            "name": "charter_approved",
            "label": "Project Charter approved",
            "passed": charter_approved,
            "current": charter.status if charter else "missing",
            "required": "approved",
        },
        {
            "name": "landscape_defined",
            "label": "At least 1 AS-IS system defined",
            "passed": landscape_defined,
            "current": landscape_count,
            "required": 1,
        },
        {
            "name": "min_3_modules",
            "label": f"At least {DISCOVER_GATE_MIN_MODULES} SAP modules assessed",
            "passed": min_modules_assessed,
            "current": module_count,
            "required": DISCOVER_GATE_MIN_MODULES,
        },
    ]

    gate_passed = all(c["passed"] for c in criteria)
    return {"gate_passed": gate_passed, "criteria": criteria}
