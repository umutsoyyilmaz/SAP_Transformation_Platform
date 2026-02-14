"""Program service layer — business logic extracted from program_bp.py.

Transaction policy: methods use flush() for ID generation, never commit().
Caller (route handler) is responsible for db.session.commit().

Extracted operations:
- Program creation with auto SAP Activate phase generation
- Phase/Gate/Workstream/TeamMember/Committee CRUD with validation
- SAP Activate phase template constant
"""
import logging

from app.models import db
from app.models.program import (
    Committee, Gate, Phase, Program, TeamMember, Workstream,
)
from app.utils.helpers import parse_date

logger = logging.getLogger(__name__)

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


def create_sap_activate_phases(program):
    """Create default SAP Activate phases + gates for a program.

    Must be called within an active transaction (after program flush).
    """
    for tmpl in SAP_ACTIVATE_PHASES:
        phase = Phase(
            program_id=program.id,
            name=tmpl["name"],
            description=tmpl["description"],
            order=tmpl["order"],
            status="not_started",
        )
        db.session.add(phase)
        db.session.flush()  # Get phase.id

        for g in tmpl.get("gates", []):
            gate = Gate(
                phase_id=phase.id,
                name=g["name"],
                gate_type=g["gate_type"],
                criteria=g.get("criteria", ""),
            )
            db.session.add(gate)
    db.session.flush()


def create_program(data):
    """Create a new program, auto-creating SAP Activate phases if applicable.

    Returns:
        (Program, None) on success
        (None, error_dict) on validation failure.
    """
    name = data.get("name", "").strip()
    if not name:
        return None, {"error": "Program name is required", "status": 400}

    program = Program(
        name=name,
        description=data.get("description", ""),
        project_type=data.get("project_type", "greenfield"),
        methodology=data.get("methodology", "sap_activate"),
        status=data.get("status", "planning"),
        priority=data.get("priority", "medium"),
        start_date=parse_date(data.get("start_date")),
        end_date=parse_date(data.get("end_date")),
        go_live_date=parse_date(data.get("go_live_date")),
        sap_product=data.get("sap_product", "S/4HANA"),
        deployment_option=data.get("deployment_option", "on_premise"),
    )
    db.session.add(program)
    db.session.flush()  # Get program.id for auto-phase creation

    # Auto-create SAP Activate phases if methodology is sap_activate
    if program.methodology == "sap_activate":
        create_sap_activate_phases(program)

    return program, None


def update_program(program, data):
    """Update an existing program's fields.

    Returns:
        (Program, None) on success
        (None, error_dict) on validation failure.
    """
    for field in [
        "name", "description", "project_type", "methodology",
        "status", "priority", "sap_product", "deployment_option",
    ]:
        if field in data:
            value = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(program, field, value)

    for date_field in ["start_date", "end_date", "go_live_date"]:
        if date_field in data:
            setattr(program, date_field, parse_date(data[date_field]))

    if not program.name:
        return None, {"error": "Program name cannot be empty", "status": 400}

    db.session.flush()
    return program, None


# ── Phase ────────────────────────────────────────────────────────────────


def create_phase(program_id, data):
    """Create a phase under a program.

    Returns:
        (Phase, None) on success
        (None, error_dict) on validation failure.
    """
    name = data.get("name", "").strip()
    if not name:
        return None, {"error": "Phase name is required", "status": 400}

    phase = Phase(
        program_id=program_id,
        name=name,
        description=data.get("description", ""),
        order=data.get("order", 0),
        status=data.get("status", "not_started"),
        planned_start=parse_date(data.get("planned_start")),
        planned_end=parse_date(data.get("planned_end")),
        actual_start=parse_date(data.get("actual_start")),
        actual_end=parse_date(data.get("actual_end")),
        completion_pct=data.get("completion_pct", 0),
    )
    db.session.add(phase)
    db.session.flush()
    return phase, None


def update_phase(phase, data):
    """Update a phase's fields.

    Returns the updated Phase.
    """
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

    db.session.flush()
    return phase


# ── Gate ─────────────────────────────────────────────────────────────────


def create_gate(phase_id, data):
    """Create a gate under a phase.

    Returns:
        (Gate, None) on success
        (None, error_dict) on validation failure.
    """
    name = data.get("name", "").strip()
    if not name:
        return None, {"error": "Gate name is required", "status": 400}

    gate = Gate(
        phase_id=phase_id,
        name=name,
        description=data.get("description", ""),
        gate_type=data.get("gate_type", "quality_gate"),
        status=data.get("status", "pending"),
        planned_date=parse_date(data.get("planned_date")),
        actual_date=parse_date(data.get("actual_date")),
        criteria=data.get("criteria", ""),
    )
    db.session.add(gate)
    db.session.flush()
    return gate, None


def update_gate(gate, data):
    """Update a gate's fields.

    Returns the updated Gate.
    """
    for field in ["name", "description", "gate_type", "status", "criteria"]:
        if field in data:
            setattr(gate, field,
                    data[field].strip() if isinstance(data[field], str) else data[field])

    for date_field in ["planned_date", "actual_date"]:
        if date_field in data:
            setattr(gate, date_field, parse_date(data[date_field]))

    db.session.flush()
    return gate


# ── Workstream ───────────────────────────────────────────────────────────


def create_workstream(program_id, data):
    """Create a workstream.

    Returns:
        (Workstream, None) on success
        (None, error_dict) on validation failure.
    """
    name = data.get("name", "").strip()
    if not name:
        return None, {"error": "Workstream name is required", "status": 400}

    ws = Workstream(
        program_id=program_id,
        name=name,
        description=data.get("description", ""),
        ws_type=data.get("ws_type", "functional"),
        lead_name=data.get("lead_name", ""),
        status=data.get("status", "active"),
    )
    db.session.add(ws)
    db.session.flush()
    return ws, None


def update_workstream(ws, data):
    """Update a workstream's fields.

    Returns the updated Workstream.
    """
    for field in ["name", "description", "ws_type", "lead_name", "status"]:
        if field in data:
            setattr(ws, field,
                    data[field].strip() if isinstance(data[field], str) else data[field])
    db.session.flush()
    return ws


# ── Team Member ──────────────────────────────────────────────────────────


def create_team_member(program_id, data):
    """Add a team member to a program.

    Returns:
        (TeamMember, None) on success
        (None, error_dict) on validation failure.
    """
    name = data.get("name", "").strip()
    if not name:
        return None, {"error": "Team member name is required", "status": 400}

    member = TeamMember(
        program_id=program_id,
        name=name,
        email=data.get("email", ""),
        role=data.get("role", "team_member"),
        raci=data.get("raci", "informed"),
        workstream_id=data.get("workstream_id"),
        organization=data.get("organization", ""),
        is_active=data.get("is_active", True),
    )
    db.session.add(member)
    db.session.flush()
    return member, None


def update_team_member(member, data):
    """Update a team member's fields.

    Returns the updated TeamMember.
    """
    for field in ["name", "email", "role", "raci", "organization"]:
        if field in data:
            setattr(member, field,
                    data[field].strip() if isinstance(data[field], str) else data[field])

    if "workstream_id" in data:
        member.workstream_id = data["workstream_id"]
    if "is_active" in data:
        member.is_active = bool(data["is_active"])

    db.session.flush()
    return member


# ── Committee ────────────────────────────────────────────────────────────


def create_committee(program_id, data):
    """Create a committee under a program.

    Returns:
        (Committee, None) on success
        (None, error_dict) on validation failure.
    """
    name = data.get("name", "").strip()
    if not name:
        return None, {"error": "Committee name is required", "status": 400}

    comm = Committee(
        program_id=program_id,
        name=name,
        description=data.get("description", ""),
        committee_type=data.get("committee_type", "steering"),
        meeting_frequency=data.get("meeting_frequency", "weekly"),
        chair_name=data.get("chair_name", ""),
    )
    db.session.add(comm)
    db.session.flush()
    return comm, None


def update_committee(comm, data):
    """Update a committee's fields.

    Returns the updated Committee.
    """
    for field in ["name", "description", "committee_type", "meeting_frequency", "chair_name"]:
        if field in data:
            setattr(comm, field,
                    data[field].strip() if isinstance(data[field], str) else data[field])
    db.session.flush()
    return comm
