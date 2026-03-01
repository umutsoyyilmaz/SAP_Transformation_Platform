"""Program service layer — business logic for programs and sub-entities.

Transaction policy: public functions call db.session.commit() on success.
Internal helpers use flush() for ID generation within a transaction.

Provides:
- Program CRUD with auto SAP Activate phase generation
- Phase/Gate/Workstream/TeamMember/Committee CRUD with validation
- List/delete helpers (moved from blueprint per CLAUDE.md layering rules)
- Audit trail for all write operations
"""
import logging
from typing import Any

from app.models import db
from app.models.audit import write_audit
from app.models.program import (
    Committee,
    Gate,
    Phase,
    Program,
    TeamMember,
    Workstream,
)
from app.utils.helpers import parse_date

logger = logging.getLogger(__name__)

# ── Allowed enum values ──────────────────────────────────────────────────

PROGRAM_PROJECT_TYPES = {"greenfield", "brownfield", "bluefield", "selective_data_transition"}
PROGRAM_METHODOLOGIES = {"sap_activate", "agile", "waterfall", "hybrid"}
PROGRAM_STATUSES = {"planning", "active", "on_hold", "completed", "cancelled"}
PROGRAM_PRIORITIES = {"low", "medium", "high", "critical"}
PROGRAM_SAP_PRODUCTS = {"S/4HANA", "SuccessFactors", "Ariba", "BTP", "Other"}
PROGRAM_DEPLOYMENT_OPTIONS = {"on_premise", "cloud", "hybrid"}

PHASE_STATUSES = {"not_started", "in_progress", "completed", "skipped"}
GATE_TYPES = {"quality_gate", "milestone", "decision_point"}
GATE_STATUSES = {"pending", "passed", "failed", "waived"}
WORKSTREAM_TYPES = {"functional", "technical", "cross_cutting"}
WORKSTREAM_STATUSES = {"active", "on_hold", "completed"}
TEAM_ROLES = {"program_manager", "project_lead", "stream_lead", "consultant", "developer", "team_member"}
RACI_VALUES = {"responsible", "accountable", "consulted", "informed"}
COMMITTEE_TYPES = {"steering", "advisory", "review", "working_group"}
MEETING_FREQUENCIES = {"daily", "weekly", "biweekly", "monthly", "ad_hoc"}

# ── Field length limits (matching DB column definitions) ─────────────────

_FIELD_LIMITS: dict[str, int] = {
    "name_200": 200,
    "name_100": 100,
    "type_50": 50,
    "status_30": 30,
    "priority_20": 20,
    "email_200": 200,
    "org_100": 100,
}


def _validate_enum(value: str, allowed: set[str], field_name: str) -> str | None:
    """Return error message if value not in allowed set, else None."""
    if value and value not in allowed:
        return f"Invalid {field_name}: '{value}'. Allowed: {sorted(allowed)}"
    return None


def _validate_length(value: str, max_len: int, field_name: str) -> str | None:
    """Return error message if value exceeds max_len, else None."""
    if value and len(value) > max_len:
        return f"{field_name} exceeds maximum length of {max_len} characters"
    return None


# ── SAP Activate Phase Template ──────────────────────────────────────────

SAP_ACTIVATE_PHASES = [
    {
        "name": "Discover",
        "order": 1,
        "description": "Understand the customer's business and define the project scope.",
        "gates": [
            {"name": "Discover Gate", "gate_type": "quality_gate",
             "criteria": "Business case approved; Scope defined; Budget confirmed"},
        ],
    },
    {
        "name": "Prepare",
        "order": 2,
        "description": "Initial planning, team onboarding, and project setup.",
        "gates": [
            {"name": "Prepare Gate", "gate_type": "quality_gate",
             "criteria": "Project plan approved; Team onboarded; Environment ready"},
        ],
    },
    {
        "name": "Explore",
        "order": 3,
        "description": "Fit-to-standard workshops, business process validation.",
        "gates": [
            {"name": "Explore Gate", "gate_type": "quality_gate",
             "criteria": "Fit/Gap analysis complete; Backlog baselined; Delta design signed off"},
        ],
    },
    {
        "name": "Realize",
        "order": 4,
        "description": "Configuration, development, testing of the SAP solution.",
        "gates": [
            {"name": "Realize Gate", "gate_type": "quality_gate",
             "criteria": "Unit tests passed; Integration tests passed; UAT plan ready"},
        ],
    },
    {
        "name": "Deploy",
        "order": 5,
        "description": "Cutover, data migration, go-live preparation.",
        "gates": [
            {"name": "Go-Live Gate", "gate_type": "decision_point",
             "criteria": "Cutover rehearsal passed; Data migration validated; Go/No-go approved"},
        ],
    },
    {
        "name": "Run",
        "order": 6,
        "description": "Hypercare, stabilization, handover to operations.",
        "gates": [
            {"name": "Hypercare Gate", "gate_type": "milestone",
             "criteria": "Hypercare period completed; KPIs met; Handover accepted"},
        ],
    },
]


def _create_sap_activate_phases(program: Program) -> None:
    """Create default SAP Activate phases + gates for a program.

    Must be called within an active transaction (after program flush).
    Propagates tenant_id from program to all child entities.
    """
    for tmpl in SAP_ACTIVATE_PHASES:
        phase = Phase(
            program_id=program.id,
            tenant_id=program.tenant_id,
            name=tmpl["name"],
            description=tmpl["description"],
            order=tmpl["order"],
            status="not_started",
        )
        db.session.add(phase)
        db.session.flush()  # Get phase.id

        for g_tmpl in tmpl.get("gates", []):
            gate = Gate(
                phase_id=phase.id,
                tenant_id=program.tenant_id,
                name=g_tmpl["name"],
                gate_type=g_tmpl["gate_type"],
                criteria=g_tmpl.get("criteria", ""),
            )
            db.session.add(gate)
    db.session.flush()


# ═════════════════════════════════════════════════════════════════════════════
# PROGRAM CRUD
# ═════════════════════════════════════════════════════════════════════════════


def list_programs(
    *,
    tenant_id: int | None = None,
    status: str | None = None,
) -> list[Program]:
    """List programs, optionally filtered by tenant and/or status.

    Args:
        tenant_id: Filter by tenant (multi-tenant isolation).
        status: Filter by program status.

    Returns:
        List of Program instances ordered by created_at desc.
    """
    query = Program.query.order_by(Program.created_at.desc())
    if tenant_id is not None:
        query = query.filter_by(tenant_id=tenant_id)
    if status:
        query = query.filter_by(status=status)
    return query.all()


def get_program_detail(program_id: int, *, tenant_id: int | None = None) -> Program | None:
    """Fetch a program by ID with tenant scope.

    Note: Relationships use lazy='dynamic' so eager loading (selectinload)
    is not applicable. Children are accessed via dynamic query attributes.

    Args:
        program_id: Program primary key.
        tenant_id: If provided, enforces tenant scope.

    Returns:
        Program instance or None if not found.
    """
    query = Program.query.filter_by(id=program_id)
    if tenant_id is not None:
        query = query.filter_by(tenant_id=tenant_id)
    return query.first()


def create_program(data: dict[str, Any], *, tenant_id: int) -> tuple[Program | None, dict | None]:
    """Create a new program, auto-creating SAP Activate phases if applicable.

    Args:
        data: Validated input dict from blueprint.
        tenant_id: Owning tenant's primary key.

    Returns:
        (Program, None) on success, (None, error_dict) on validation failure.
    """
    name = (data.get("name") or "").strip()
    if not name:
        return None, {"error": "Program name is required", "status": 400}
    if err := _validate_length(name, 200, "Program name"):
        return None, {"error": err, "status": 400}

    project_type = data.get("project_type", "greenfield")
    if err := _validate_enum(project_type, PROGRAM_PROJECT_TYPES, "project_type"):
        return None, {"error": err, "status": 400}

    methodology = data.get("methodology", "sap_activate")
    if err := _validate_enum(methodology, PROGRAM_METHODOLOGIES, "methodology"):
        return None, {"error": err, "status": 400}

    status = data.get("status", "planning")
    if err := _validate_enum(status, PROGRAM_STATUSES, "status"):
        return None, {"error": err, "status": 400}

    priority = data.get("priority", "medium")
    if err := _validate_enum(priority, PROGRAM_PRIORITIES, "priority"):
        return None, {"error": err, "status": 400}

    sap_product = data.get("sap_product", "S/4HANA")
    if err := _validate_enum(sap_product, PROGRAM_SAP_PRODUCTS, "sap_product"):
        return None, {"error": err, "status": 400}

    deployment_option = data.get("deployment_option", "on_premise")
    if err := _validate_enum(deployment_option, PROGRAM_DEPLOYMENT_OPTIONS, "deployment_option"):
        return None, {"error": err, "status": 400}

    program = Program(
        tenant_id=tenant_id,
        name=name,
        description=data.get("description", ""),
        project_type=project_type,
        methodology=methodology,
        status=status,
        priority=priority,
        start_date=parse_date(data.get("start_date")),
        end_date=parse_date(data.get("end_date")),
        go_live_date=parse_date(data.get("go_live_date")),
        sap_product=sap_product,
        deployment_option=deployment_option,
    )
    db.session.add(program)
    db.session.flush()

    if program.methodology == "sap_activate":
        _create_sap_activate_phases(program)

    write_audit(
        entity_type="program",
        entity_id=str(program.id),
        action="create",
        tenant_id=tenant_id,
        program_id=program.id,
        diff={"name": {"old": None, "new": name}},
    )

    # Faz 3: Auto-create default project so operational entities have a target
    from app.services.project_service import create_project
    _proj, _proj_err = create_project(
        tenant_id=tenant_id,
        program_id=program.id,
        data={"code": "DEFAULT", "name": f"{name} - Default", "is_default": True},
    )
    if _proj:
        logger.info("Default project auto-created id=%s program=%s", _proj.id, program.id)

    db.session.commit()
    logger.info("Program created id=%s tenant=%s", program.id, tenant_id)
    return program, None


def update_program(
    program: Program,
    data: dict[str, Any],
    *,
    tenant_id: int,
) -> tuple[Program | None, dict | None]:
    """Update an existing program's fields.

    Args:
        program: Program instance to update.
        data: Dict of fields to update.
        tenant_id: Current tenant for audit context.

    Returns:
        (Program, None) on success, (None, error_dict) on validation failure.
    """
    changes: dict[str, dict] = {}

    for field in [
        "name", "description", "project_type", "methodology",
        "status", "priority", "sap_product", "deployment_option",
    ]:
        if field in data:
            value = data[field].strip() if isinstance(data[field], str) else data[field]
            old_value = getattr(program, field)
            if old_value != value:
                changes[field] = {"old": old_value, "new": value}
            setattr(program, field, value)

    # Enum validation on updated fields
    if "project_type" in data:
        if err := _validate_enum(program.project_type, PROGRAM_PROJECT_TYPES, "project_type"):
            return None, {"error": err, "status": 400}
    if "methodology" in data:
        if err := _validate_enum(program.methodology, PROGRAM_METHODOLOGIES, "methodology"):
            return None, {"error": err, "status": 400}
    if "status" in data:
        if err := _validate_enum(program.status, PROGRAM_STATUSES, "status"):
            return None, {"error": err, "status": 400}
    if "priority" in data:
        if err := _validate_enum(program.priority, PROGRAM_PRIORITIES, "priority"):
            return None, {"error": err, "status": 400}
    if "sap_product" in data:
        if err := _validate_enum(program.sap_product, PROGRAM_SAP_PRODUCTS, "sap_product"):
            return None, {"error": err, "status": 400}
    if "deployment_option" in data:
        if err := _validate_enum(program.deployment_option, PROGRAM_DEPLOYMENT_OPTIONS, "deployment_option"):
            return None, {"error": err, "status": 400}

    for date_field in ["start_date", "end_date", "go_live_date"]:
        if date_field in data:
            setattr(program, date_field, parse_date(data[date_field]))

    if not program.name:
        return None, {"error": "Program name cannot be empty", "status": 400}
    if err := _validate_length(program.name, 200, "Program name"):
        return None, {"error": err, "status": 400}

    if changes:
        write_audit(
            entity_type="program",
            entity_id=str(program.id),
            action="update",
            tenant_id=tenant_id,
            program_id=program.id,
            diff=changes,
        )

    db.session.commit()
    return program, None


def delete_program(program: Program, *, tenant_id: int) -> None:
    """Delete a program and all children (cascade).

    Args:
        program: Program instance to delete.
        tenant_id: Current tenant for audit context.
    """
    program_id = program.id
    program_name = program.name
    write_audit(
        entity_type="program",
        entity_id=str(program_id),
        action="delete",
        tenant_id=tenant_id,
        program_id=program_id,
        diff={"name": {"old": program_name, "new": None}},
    )
    db.session.delete(program)
    db.session.commit()
    logger.info("Program deleted id=%s name=%s tenant=%s", program_id, str(program_name)[:200], tenant_id)


# ═════════════════════════════════════════════════════════════════════════════
# PHASE CRUD
# ═════════════════════════════════════════════════════════════════════════════


def list_phases(*, program_id: int, tenant_id: int | None = None) -> list[Phase]:
    """List phases for a program, ordered by display sequence.

    Args:
        program_id: Parent program PK.
        tenant_id: If provided, enforces tenant scope.

    Returns:
        List of Phase instances.
    """
    query = Phase.query.filter_by(program_id=program_id)
    if tenant_id is not None:
        query = query.filter_by(tenant_id=tenant_id)
    return query.order_by(Phase.order).all()


def create_phase(
    program_id: int,
    data: dict[str, Any],
    *,
    tenant_id: int,
) -> tuple[Phase | None, dict | None]:
    """Create a phase under a program.

    Args:
        program_id: Parent program PK.
        data: Validated input dict.
        tenant_id: Owning tenant PK.

    Returns:
        (Phase, None) on success, (None, error_dict) on validation failure.
    """
    name = (data.get("name") or "").strip()
    if not name:
        return None, {"error": "Phase name is required", "status": 400}
    if err := _validate_length(name, 100, "Phase name"):
        return None, {"error": err, "status": 400}

    status = data.get("status", "not_started")
    if err := _validate_enum(status, PHASE_STATUSES, "status"):
        return None, {"error": err, "status": 400}

    phase = Phase(
        program_id=program_id,
        tenant_id=tenant_id,
        name=name,
        description=data.get("description", ""),
        order=data.get("order", 0),
        status=status,
        planned_start=parse_date(data.get("planned_start")),
        planned_end=parse_date(data.get("planned_end")),
        actual_start=parse_date(data.get("actual_start")),
        actual_end=parse_date(data.get("actual_end")),
        completion_pct=data.get("completion_pct", 0),
    )
    db.session.add(phase)
    db.session.flush()

    write_audit(
        entity_type="phase",
        entity_id=str(phase.id),
        action="create",
        tenant_id=tenant_id,
        program_id=program_id,
        diff={"name": {"old": None, "new": name}},
    )

    db.session.commit()
    return phase, None


def update_phase(phase: Phase, data: dict[str, Any], *, tenant_id: int) -> Phase:
    """Update a phase's fields.

    Args:
        phase: Phase instance to update.
        data: Dict of fields to update.
        tenant_id: Current tenant for audit context.

    Returns:
        Updated Phase instance.
    """
    if "status" in data:
        if err := _validate_enum(data["status"], PHASE_STATUSES, "status"):
            raise ValueError(err)

    for field in ["name", "description", "status"]:
        if field in data:
            setattr(phase, field,
                    data[field].strip() if isinstance(data[field], str) else data[field])

    if "order" in data:
        phase.order = data["order"]
    if "completion_pct" in data:
        phase.completion_pct = max(0, min(100, int(data["completion_pct"])))

    for date_field in ["planned_start", "planned_end", "actual_start", "actual_end"]:
        if date_field in data:
            setattr(phase, date_field, parse_date(data[date_field]))

    db.session.commit()
    return phase


def delete_phase(phase: Phase, *, tenant_id: int) -> None:
    """Delete a phase and its gates.

    Args:
        phase: Phase instance to delete.
        tenant_id: Current tenant for audit context.
    """
    write_audit(
        entity_type="phase",
        entity_id=str(phase.id),
        action="delete",
        tenant_id=tenant_id,
        program_id=phase.program_id,
        diff={"name": {"old": phase.name, "new": None}},
    )
    db.session.delete(phase)
    db.session.commit()


# ═════════════════════════════════════════════════════════════════════════════
# GATE CRUD
# ═════════════════════════════════════════════════════════════════════════════


def list_gates(*, phase_id: int, tenant_id: int | None = None) -> list[Gate]:
    """List gates for a phase, ordered by ID.

    Args:
        phase_id: Parent phase PK.
        tenant_id: If provided, enforces tenant scope.

    Returns:
        List of Gate instances.
    """
    query = Gate.query.filter_by(phase_id=phase_id)
    if tenant_id is not None:
        query = query.filter_by(tenant_id=tenant_id)
    return query.order_by(Gate.id).all()


def create_gate(
    phase_id: int,
    data: dict[str, Any],
    *,
    tenant_id: int,
) -> tuple[Gate | None, dict | None]:
    """Create a gate under a phase.

    Args:
        phase_id: Parent phase PK.
        data: Validated input dict.
        tenant_id: Owning tenant PK.

    Returns:
        (Gate, None) on success, (None, error_dict) on validation failure.
    """
    name = (data.get("name") or "").strip()
    if not name:
        return None, {"error": "Gate name is required", "status": 400}
    if err := _validate_length(name, 100, "Gate name"):
        return None, {"error": err, "status": 400}

    gate_type = data.get("gate_type", "quality_gate")
    if err := _validate_enum(gate_type, GATE_TYPES, "gate_type"):
        return None, {"error": err, "status": 400}

    status = data.get("status", "pending")
    if err := _validate_enum(status, GATE_STATUSES, "status"):
        return None, {"error": err, "status": 400}

    gate = Gate(
        phase_id=phase_id,
        tenant_id=tenant_id,
        name=name,
        description=data.get("description", ""),
        gate_type=gate_type,
        status=status,
        planned_date=parse_date(data.get("planned_date")),
        actual_date=parse_date(data.get("actual_date")),
        criteria=data.get("criteria", ""),
    )
    db.session.add(gate)
    db.session.flush()

    write_audit(
        entity_type="gate",
        entity_id=str(gate.id),
        action="create",
        tenant_id=tenant_id,
        diff={"name": {"old": None, "new": name}},
    )

    db.session.commit()
    return gate, None


def update_gate(gate: Gate, data: dict[str, Any], *, tenant_id: int) -> Gate:
    """Update a gate's fields.

    Args:
        gate: Gate instance to update.
        data: Dict of fields to update.
        tenant_id: Current tenant for audit context.

    Returns:
        Updated Gate instance.
    """
    if "gate_type" in data:
        if err := _validate_enum(data["gate_type"], GATE_TYPES, "gate_type"):
            raise ValueError(err)
    if "status" in data:
        if err := _validate_enum(data["status"], GATE_STATUSES, "status"):
            raise ValueError(err)

    for field in ["name", "description", "gate_type", "status", "criteria"]:
        if field in data:
            setattr(gate, field,
                    data[field].strip() if isinstance(data[field], str) else data[field])

    for date_field in ["planned_date", "actual_date"]:
        if date_field in data:
            setattr(gate, date_field, parse_date(data[date_field]))

    db.session.commit()
    return gate


def delete_gate(gate: Gate, *, tenant_id: int) -> None:
    """Delete a gate.

    Args:
        gate: Gate instance to delete.
        tenant_id: Current tenant for audit context.
    """
    write_audit(
        entity_type="gate",
        entity_id=str(gate.id),
        action="delete",
        tenant_id=tenant_id,
        diff={"name": {"old": gate.name, "new": None}},
    )
    db.session.delete(gate)
    db.session.commit()


# ═════════════════════════════════════════════════════════════════════════════
# WORKSTREAM CRUD
# ═════════════════════════════════════════════════════════════════════════════


def list_workstreams(*, program_id: int, tenant_id: int | None = None) -> list[Workstream]:
    """List workstreams for a program, ordered by name.

    Args:
        program_id: Parent program PK.
        tenant_id: If provided, enforces tenant scope.

    Returns:
        List of Workstream instances.
    """
    query = Workstream.query.filter_by(program_id=program_id)
    if tenant_id is not None:
        query = query.filter_by(tenant_id=tenant_id)
    return query.order_by(Workstream.name).all()


def create_workstream(
    program_id: int,
    data: dict[str, Any],
    *,
    tenant_id: int,
) -> tuple[Workstream | None, dict | None]:
    """Create a workstream under a program.

    Args:
        program_id: Parent program PK.
        data: Validated input dict.
        tenant_id: Owning tenant PK.

    Returns:
        (Workstream, None) on success, (None, error_dict) on validation failure.
    """
    name = (data.get("name") or "").strip()
    if not name:
        return None, {"error": "Workstream name is required", "status": 400}
    if err := _validate_length(name, 100, "Workstream name"):
        return None, {"error": err, "status": 400}

    ws_type = data.get("ws_type", "functional")
    if err := _validate_enum(ws_type, WORKSTREAM_TYPES, "ws_type"):
        return None, {"error": err, "status": 400}

    status = data.get("status", "active")
    if err := _validate_enum(status, WORKSTREAM_STATUSES, "status"):
        return None, {"error": err, "status": 400}

    ws = Workstream(
        program_id=program_id,
        tenant_id=tenant_id,
        name=name,
        description=data.get("description", ""),
        ws_type=ws_type,
        lead_name=data.get("lead_name", ""),
        status=status,
    )
    db.session.add(ws)
    db.session.flush()

    write_audit(
        entity_type="workstream",
        entity_id=str(ws.id),
        action="create",
        tenant_id=tenant_id,
        program_id=program_id,
        diff={"name": {"old": None, "new": name}},
    )

    db.session.commit()
    return ws, None


def update_workstream(ws: Workstream, data: dict[str, Any], *, tenant_id: int) -> Workstream:
    """Update a workstream's fields.

    Args:
        ws: Workstream instance to update.
        data: Dict of fields to update.
        tenant_id: Current tenant for audit context.

    Returns:
        Updated Workstream instance.
    """
    if "ws_type" in data:
        if err := _validate_enum(data["ws_type"], WORKSTREAM_TYPES, "ws_type"):
            raise ValueError(err)
    if "status" in data:
        if err := _validate_enum(data["status"], WORKSTREAM_STATUSES, "status"):
            raise ValueError(err)

    for field in ["name", "description", "ws_type", "lead_name", "status"]:
        if field in data:
            setattr(ws, field,
                    data[field].strip() if isinstance(data[field], str) else data[field])
    db.session.commit()
    return ws


def delete_workstream(ws: Workstream, *, tenant_id: int) -> None:
    """Delete a workstream.

    Args:
        ws: Workstream instance to delete.
        tenant_id: Current tenant for audit context.
    """
    write_audit(
        entity_type="workstream",
        entity_id=str(ws.id),
        action="delete",
        tenant_id=tenant_id,
        program_id=ws.program_id,
        diff={"name": {"old": ws.name, "new": None}},
    )
    db.session.delete(ws)
    db.session.commit()


# ═════════════════════════════════════════════════════════════════════════════
# TEAM MEMBER CRUD
# ═════════════════════════════════════════════════════════════════════════════


def list_team_members(*, program_id: int, tenant_id: int | None = None) -> list[TeamMember]:
    """List team members for a program.

    Args:
        program_id: Parent program PK.
        tenant_id: If provided, enforces tenant scope.

    Returns:
        List of TeamMember instances.
    """
    query = TeamMember.query.filter_by(program_id=program_id)
    if tenant_id is not None:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def create_team_member(
    program_id: int,
    data: dict[str, Any],
    *,
    tenant_id: int,
) -> tuple[TeamMember | None, dict | None]:
    """Add a team member to a program.

    Args:
        program_id: Parent program PK.
        data: Validated input dict.
        tenant_id: Owning tenant PK.

    Returns:
        (TeamMember, None) on success, (None, error_dict) on validation failure.
    """
    name = (data.get("name") or "").strip()
    if not name:
        return None, {"error": "Team member name is required", "status": 400}
    if err := _validate_length(name, 100, "Team member name"):
        return None, {"error": err, "status": 400}

    role = data.get("role", "team_member")
    if err := _validate_enum(role, TEAM_ROLES, "role"):
        return None, {"error": err, "status": 400}

    raci = data.get("raci", "informed")
    if err := _validate_enum(raci, RACI_VALUES, "raci"):
        return None, {"error": err, "status": 400}

    member = TeamMember(
        program_id=program_id,
        tenant_id=tenant_id,
        name=name,
        email=data.get("email", ""),
        role=role,
        raci=raci,
        workstream_id=data.get("workstream_id"),
        organization=data.get("organization", ""),
        is_active=data.get("is_active", True),
    )
    db.session.add(member)
    db.session.flush()

    write_audit(
        entity_type="team_member",
        entity_id=str(member.id),
        action="create",
        tenant_id=tenant_id,
        program_id=program_id,
        diff={"name": {"old": None, "new": name}},
    )

    db.session.commit()
    return member, None


def update_team_member(member: TeamMember, data: dict[str, Any], *, tenant_id: int) -> TeamMember:
    """Update a team member's fields.

    Args:
        member: TeamMember instance to update.
        data: Dict of fields to update.
        tenant_id: Current tenant for audit context.

    Returns:
        Updated TeamMember instance.
    """
    if "role" in data:
        if err := _validate_enum(data["role"], TEAM_ROLES, "role"):
            raise ValueError(err)
    if "raci" in data:
        if err := _validate_enum(data["raci"], RACI_VALUES, "raci"):
            raise ValueError(err)

    for field in ["name", "email", "role", "raci", "organization"]:
        if field in data:
            setattr(member, field,
                    data[field].strip() if isinstance(data[field], str) else data[field])

    if "workstream_id" in data:
        member.workstream_id = data["workstream_id"]
    if "is_active" in data:
        member.is_active = bool(data["is_active"])

    db.session.commit()
    return member


def delete_team_member(member: TeamMember, *, tenant_id: int) -> None:
    """Remove a team member from a program.

    Args:
        member: TeamMember instance to delete.
        tenant_id: Current tenant for audit context.
    """
    write_audit(
        entity_type="team_member",
        entity_id=str(member.id),
        action="delete",
        tenant_id=tenant_id,
        program_id=member.program_id,
        diff={"name": {"old": member.name, "new": None}},
    )
    db.session.delete(member)
    db.session.commit()


# ═════════════════════════════════════════════════════════════════════════════
# COMMITTEE CRUD
# ═════════════════════════════════════════════════════════════════════════════


def list_committees(*, program_id: int, tenant_id: int | None = None) -> list[Committee]:
    """List committees for a program.

    Args:
        program_id: Parent program PK.
        tenant_id: If provided, enforces tenant scope.

    Returns:
        List of Committee instances.
    """
    query = Committee.query.filter_by(program_id=program_id)
    if tenant_id is not None:
        query = query.filter_by(tenant_id=tenant_id)
    return query.all()


def create_committee(
    program_id: int,
    data: dict[str, Any],
    *,
    tenant_id: int,
) -> tuple[Committee | None, dict | None]:
    """Create a committee under a program.

    Args:
        program_id: Parent program PK.
        data: Validated input dict.
        tenant_id: Owning tenant PK.

    Returns:
        (Committee, None) on success, (None, error_dict) on validation failure.
    """
    name = (data.get("name") or "").strip()
    if not name:
        return None, {"error": "Committee name is required", "status": 400}
    if err := _validate_length(name, 100, "Committee name"):
        return None, {"error": err, "status": 400}

    committee_type = data.get("committee_type", "steering")
    if err := _validate_enum(committee_type, COMMITTEE_TYPES, "committee_type"):
        return None, {"error": err, "status": 400}

    meeting_frequency = data.get("meeting_frequency", "weekly")
    if err := _validate_enum(meeting_frequency, MEETING_FREQUENCIES, "meeting_frequency"):
        return None, {"error": err, "status": 400}

    comm = Committee(
        program_id=program_id,
        tenant_id=tenant_id,
        name=name,
        description=data.get("description", ""),
        committee_type=committee_type,
        meeting_frequency=meeting_frequency,
        chair_name=data.get("chair_name", ""),
    )
    db.session.add(comm)
    db.session.flush()

    write_audit(
        entity_type="committee",
        entity_id=str(comm.id),
        action="create",
        tenant_id=tenant_id,
        program_id=program_id,
        diff={"name": {"old": None, "new": name}},
    )

    db.session.commit()
    return comm, None


def update_committee(comm: Committee, data: dict[str, Any], *, tenant_id: int) -> Committee:
    """Update a committee's fields.

    Args:
        comm: Committee instance to update.
        data: Dict of fields to update.
        tenant_id: Current tenant for audit context.

    Returns:
        Updated Committee instance.
    """
    if "committee_type" in data:
        if err := _validate_enum(data["committee_type"], COMMITTEE_TYPES, "committee_type"):
            raise ValueError(err)
    if "meeting_frequency" in data:
        if err := _validate_enum(data["meeting_frequency"], MEETING_FREQUENCIES, "meeting_frequency"):
            raise ValueError(err)

    for field in ["name", "description", "committee_type", "meeting_frequency", "chair_name"]:
        if field in data:
            setattr(comm, field,
                    data[field].strip() if isinstance(data[field], str) else data[field])
    db.session.commit()
    return comm


def delete_committee(comm: Committee, *, tenant_id: int) -> None:
    """Delete a committee.

    Args:
        comm: Committee instance to delete.
        tenant_id: Current tenant for audit context.
    """
    write_audit(
        entity_type="committee",
        entity_id=str(comm.id),
        action="delete",
        tenant_id=tenant_id,
        program_id=comm.program_id,
        diff={"name": {"old": comm.name, "new": None}},
    )
    db.session.delete(comm)
    db.session.commit()
