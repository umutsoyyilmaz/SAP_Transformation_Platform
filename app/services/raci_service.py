"""
RACI Matrix Service — FDD-F06 / S3-03.

Business context:
    The RACI matrix tracks responsibility assignments across a program's team.
    Rows = activities (tasks/deliverables); Columns = team members.
    Each cell holds one of four roles: R(esponsible), A(ccountable),
    C(onsulted), I(nformed).

    Invariant: each activity MUST have exactly one Accountable (A) assignment.
    This is enforced at the service layer because SQLite test env does not support
    PostgreSQL partial indexes. The service returns a 400-equivalent error when a
    second Accountable is attempted on the same activity.

Security:
    - All queries are scoped by (tenant_id, program_id).
    - RaciEntry.tenant_id is nullable=False — no entry can ever exist without a
      tenant scope (enforced at both model and DB level).
"""

import logging
from typing import Literal

from sqlalchemy import select

from app.models import db
from app.models.program import Program, RaciActivity, RaciEntry, TeamMember

logger = logging.getLogger(__name__)

# ── Original SAP Activate-inspired template activities ────────────────────────
# NOTE: These are original descriptions for this platform — not reproduced from
# SAP documentation.  They reflect common transformation project activities in
# natural language.

SAP_ACTIVATE_RACI_ACTIVITIES: list[dict] = [
    # discover phase
    {"name": "Project Initiation Approval", "phase": "discover", "category": "governance", "order": 1},
    {"name": "Project Objectives Definition", "phase": "discover", "category": "governance", "order": 2},
    {"name": "Organization and Stakeholder Analysis", "phase": "discover", "category": "governance", "order": 3},
    {"name": "Current System Inventory Assessment", "phase": "discover", "category": "technical", "order": 4},
    {"name": "Scope Preliminary Assessment", "phase": "discover", "category": "technical", "order": 5},
    # prepare phase
    {"name": "Project Charter Documentation", "phase": "prepare", "category": "governance", "order": 10},
    {"name": "Steering Committee Setup", "phase": "prepare", "category": "governance", "order": 11},
    {"name": "Project Management Plan Preparation", "phase": "prepare", "category": "governance", "order": 12},
    {"name": "Infrastructure and System Readiness", "phase": "prepare", "category": "technical", "order": 13},
    {"name": "Project Team Formation and Training Plan", "phase": "prepare", "category": "training", "order": 14},
    {"name": "Risk and Issue Tracking Setup", "phase": "prepare", "category": "governance", "order": 15},
    # explore phase
    {"name": "Process Workshop Management", "phase": "explore", "category": "technical", "order": 20},
    {"name": "Fit-Gap Analysis and Reporting", "phase": "explore", "category": "technical", "order": 21},
    {"name": "WRICEF List Creation", "phase": "explore", "category": "technical", "order": 22},
    {"name": "Data Migration Strategy Definition", "phase": "explore", "category": "data", "order": 23},
    {"name": "User Stories and Requirements Document", "phase": "explore", "category": "technical", "order": 24},
    {"name": "Integration Architecture Design", "phase": "explore", "category": "technical", "order": 25},
    # realize phase
    {"name": "Configuration and Development Management", "phase": "realize", "category": "technical", "order": 30},
    {"name": "WRICEF Development Approval", "phase": "realize", "category": "technical", "order": 31},
    {"name": "Data Migration Development and Testing", "phase": "realize", "category": "data", "order": 32},
    {"name": "Integration Testing (SIT)", "phase": "realize", "category": "testing", "order": 33},
    {"name": "Performance and Load Testing", "phase": "realize", "category": "testing", "order": 34},
    {"name": "Training Material Preparation", "phase": "realize", "category": "training", "order": 35},
    {"name": "Security and Authorization Concept", "phase": "realize", "category": "technical", "order": 36},
    # deploy phase
    {"name": "User Acceptance Testing (UAT) Coordination", "phase": "deploy", "category": "testing", "order": 40},
    {"name": "End User Training", "phase": "deploy", "category": "training", "order": 41},
    {"name": "Cutover Plan Preparation", "phase": "deploy", "category": "cutover", "order": 42},
    {"name": "Data Migration Execution (Prod)", "phase": "deploy", "category": "data", "order": 43},
    {"name": "Go-Live Decision", "phase": "deploy", "category": "governance", "order": 44},
    {"name": "Hypercare Support Plan", "phase": "deploy", "category": "governance", "order": 45},
    # run phase
    {"name": "Hypercare Support Monitoring", "phase": "run", "category": "governance", "order": 50},
    {"name": "Performance KPI Monitoring", "phase": "run", "category": "technical", "order": 51},
    {"name": "Bug and Issue Management", "phase": "run", "category": "technical", "order": 52},
    {"name": "Project Closure Assessment", "phase": "run", "category": "governance", "order": 53},
]

RaciRole = Literal["R", "A", "C", "I"]

VALID_RACI_ROLES: frozenset[str] = frozenset({"R", "A", "C", "I"})


# ── Public service functions ──────────────────────────────────────────────────


def get_raci_matrix(
    tenant_id: int,
    program_id: int,
    workstream_id: int | None = None,
    sap_phase: str | None = None,
) -> dict:
    """Return the RACI matrix as a pivot structure ready for the UI.

    Fetches activities and entries in two queries (no N+1).
    Also runs lightweight validation so the UI can show warning banners.

    Args:
        tenant_id: Tenant scope — all queries are filtered by this.
        program_id: Target program.
        workstream_id: Optional filter — return only activities in this workstream.
        sap_phase: Optional filter — return only activities in this SAP phase.

    Returns:
        Dict with keys:
          activities  — list of activity dicts (id, name, category, sap_activate_phase)
          team_members — list of {id, name, role} for the program's team
          matrix       — {str(activity_id): {str(member_id): raci_role}}
          validation   — {activities_without_accountable, activities_without_responsible}
    """
    _assert_program_belongs_to_tenant(tenant_id, program_id)

    # activities query (tenant + program scoped)
    act_stmt = select(RaciActivity).where(
        RaciActivity.tenant_id == tenant_id,
        RaciActivity.program_id == program_id,
    )
    if workstream_id is not None:
        act_stmt = act_stmt.where(RaciActivity.workstream_id == workstream_id)
    if sap_phase:
        act_stmt = act_stmt.where(RaciActivity.sap_activate_phase == sap_phase)
    act_stmt = act_stmt.order_by(RaciActivity.sort_order.nullsfirst(), RaciActivity.id)
    activities = db.session.execute(act_stmt).scalars().all()

    # team members for the program (tenant scoped)
    mem_stmt = select(TeamMember).where(
        TeamMember.tenant_id == tenant_id,
        TeamMember.program_id == program_id,
    )
    members = db.session.execute(mem_stmt).scalars().all()

    activity_ids = [a.id for a in activities]

    # entries for these activities (one bulk query — no N+1)
    entries: list[RaciEntry] = []
    if activity_ids:
        ent_stmt = select(RaciEntry).where(
            RaciEntry.tenant_id == tenant_id,
            RaciEntry.program_id == program_id,
            RaciEntry.activity_id.in_(activity_ids),
        )
        entries = db.session.execute(ent_stmt).scalars().all()

    # build pivot matrix: {activity_id_str: {member_id_str: role}}
    matrix: dict[str, dict[str, str]] = {}
    for entry in entries:
        a_key = str(entry.activity_id)
        m_key = str(entry.team_member_id)
        if a_key not in matrix:
            matrix[a_key] = {}
        matrix[a_key][m_key] = entry.raci_role

    # validation
    activities_without_accountable = []
    activities_without_responsible = []
    for act in activities:
        a_key = str(act.id)
        roles_for_activity = set(matrix.get(a_key, {}).values())
        if "A" not in roles_for_activity:
            activities_without_accountable.append(act.name)
        if "R" not in roles_for_activity:
            activities_without_responsible.append(act.name)

    return {
        "activities": [a.to_dict() for a in activities],
        "team_members": [
            {"id": m.id, "name": m.name, "role": m.role}
            for m in members
        ],
        "matrix": matrix,
        "validation": {
            "activities_without_accountable": activities_without_accountable,
            "activities_without_responsible": activities_without_responsible,
        },
    }


def create_activity(
    tenant_id: int,
    program_id: int,
    name: str,
    category: str | None = None,
    sap_activate_phase: str | None = None,
    workstream_id: int | None = None,
    sort_order: int | None = None,
) -> dict:
    """Create a new activity (row) in the RACI matrix for a program.

    Args:
        tenant_id: Tenant scope.
        program_id: Target program.
        name: Activity name (max 200 chars, must be non-empty).
        category: Optional — governance|technical|testing|data|training|cutover.
        sap_activate_phase: Optional — discover|prepare|explore|realize|deploy|run.
        workstream_id: Optional FK to workstreams.
        sort_order: Optional display ordering hint.

    Returns:
        Serialized RaciActivity dict.

    Raises:
        ValueError: If name is empty or program doesn't belong to tenant.
    """
    _assert_program_belongs_to_tenant(tenant_id, program_id)

    activity = RaciActivity(
        tenant_id=tenant_id,
        program_id=program_id,
        name=name.strip(),
        category=category,
        sap_activate_phase=sap_activate_phase,
        workstream_id=workstream_id,
        is_template=False,
        sort_order=sort_order,
    )
    db.session.add(activity)
    db.session.commit()

    logger.info(
        "RACI activity created",
        extra={"tenant_id": tenant_id, "program_id": program_id, "activity_id": activity.id},
    )
    return activity.to_dict()


def upsert_raci_entry(
    tenant_id: int,
    program_id: int,
    activity_id: int,
    team_member_id: int,
    raci_role: str | None,
) -> dict | None:
    """Set or clear one cell in the RACI matrix.

    Business rules enforced here:
    - If raci_role is None → delete the existing entry (clear the cell).
    - Only one Accountable (A) per activity is allowed.  Attempting to assign A
      when another team member already holds A for the same activity raises
      ValueError (the blueprint maps this to HTTP 400).

    Args:
        tenant_id: Tenant scope.
        program_id: Source program (validates ownership of activity + member).
        activity_id: Target row (must belong to this program + tenant).
        team_member_id: Target column (must belong to this program + tenant).
        raci_role: "R", "A", "C", "I", or None to delete.

    Returns:
        Serialized RaciEntry dict, or None if the entry was deleted.

    Raises:
        ValueError: If validation fails (bad role, duplicate A, wrong tenant).
    """
    _assert_program_belongs_to_tenant(tenant_id, program_id)
    _assert_activity_belongs(tenant_id, program_id, activity_id)
    _assert_member_belongs(tenant_id, program_id, team_member_id)

    # Fetch existing entry for this (activity, member) pair
    existing_stmt = select(RaciEntry).where(
        RaciEntry.activity_id == activity_id,
        RaciEntry.team_member_id == team_member_id,
        RaciEntry.tenant_id == tenant_id,
    )
    existing = db.session.execute(existing_stmt).scalar_one_or_none()

    if raci_role is None:
        # DELETE path — clear the cell
        if existing:
            db.session.delete(existing)
            db.session.commit()
            logger.info(
                "RACI entry deleted",
                extra={"tenant_id": tenant_id, "activity_id": activity_id, "member_id": team_member_id},
            )
        return None

    # Validate role value
    raci_role = raci_role.upper()
    if raci_role not in VALID_RACI_ROLES:
        raise ValueError(f"Invalid RACI role '{raci_role}'. Must be one of R, A, C, I.")

    # Accountable uniqueness check — only one A per activity
    if raci_role == "A":
        other_a_stmt = select(RaciEntry).where(
            RaciEntry.activity_id == activity_id,
            RaciEntry.raci_role == "A",
            RaciEntry.tenant_id == tenant_id,
        )
        if existing:
            # Allow updating the same row to A (no uniqueness violated)
            other_a_stmt = other_a_stmt.where(RaciEntry.team_member_id != team_member_id)
        other_a = db.session.execute(other_a_stmt).scalar_one_or_none()
        if other_a:
            raise ValueError(
                "Activity already has an Accountable assignment. "
                "Remove the existing Accountable before assigning a new one."
            )

    if existing:
        existing.raci_role = raci_role
        db.session.commit()
        logger.info(
            "RACI entry updated",
            extra={
                "tenant_id": tenant_id,
                "activity_id": activity_id,
                "member_id": team_member_id,
                "role": raci_role,
            },
        )
        return existing.to_dict()

    entry = RaciEntry(
        tenant_id=tenant_id,
        program_id=program_id,
        activity_id=activity_id,
        team_member_id=team_member_id,
        raci_role=raci_role,
    )
    db.session.add(entry)
    db.session.commit()
    logger.info(
        "RACI entry created",
        extra={
            "tenant_id": tenant_id,
            "activity_id": activity_id,
            "member_id": team_member_id,
            "role": raci_role,
        },
    )
    return entry.to_dict()


def bulk_import_sap_template_activities(tenant_id: int, program_id: int) -> int:
    """Import the SAP Activate-inspired standard activity set for a program.

    Idempotent: activities that already exist (by name match) are skipped to
    avoid duplicates on repeated calls.  Only net-new activities are inserted.

    Args:
        tenant_id: Tenant scope.
        program_id: Target program.

    Returns:
        Number of activities actually created (0 if all already exist).

    Raises:
        ValueError: If program doesn't belong to tenant.
    """
    _assert_program_belongs_to_tenant(tenant_id, program_id)

    # Fetch existing activity names for this program to skip duplicates
    existing_stmt = select(RaciActivity.name).where(
        RaciActivity.tenant_id == tenant_id,
        RaciActivity.program_id == program_id,
    )
    existing_names: set[str] = {
        row for row in db.session.execute(existing_stmt).scalars().all()
    }

    new_activities = []
    for item in SAP_ACTIVATE_RACI_ACTIVITIES:
        if item["name"] in existing_names:
            continue
        new_activities.append(
            RaciActivity(
                tenant_id=tenant_id,
                program_id=program_id,
                name=item["name"],
                category=item["category"],
                sap_activate_phase=item["phase"],
                is_template=True,
                sort_order=item["order"],
            )
        )

    if new_activities:
        db.session.add_all(new_activities)
        db.session.commit()

    count = len(new_activities)
    logger.info(
        "RACI template import completed",
        extra={"tenant_id": tenant_id, "program_id": program_id, "created_count": count},
    )
    return count


def validate_raci_matrix(tenant_id: int, program_id: int) -> dict:
    """Return validation results for the RACI matrix of a program.

    Checks:
    - Activities without any Accountable assignment.
    - Activities without any Responsible assignment.

    Args:
        tenant_id: Tenant scope.
        program_id: Target program.

    Returns:
        Dict with 'activities_without_accountable' and 'activities_without_responsible'
        (lists of activity names).
    """
    _assert_program_belongs_to_tenant(tenant_id, program_id)

    act_stmt = select(RaciActivity).where(
        RaciActivity.tenant_id == tenant_id,
        RaciActivity.program_id == program_id,
    )
    activities = db.session.execute(act_stmt).scalars().all()
    activity_ids = [a.id for a in activities]

    entries: list[RaciEntry] = []
    if activity_ids:
        ent_stmt = select(RaciEntry).where(
            RaciEntry.tenant_id == tenant_id,
            RaciEntry.program_id == program_id,
            RaciEntry.activity_id.in_(activity_ids),
        )
        entries = db.session.execute(ent_stmt).scalars().all()

    # Build role sets per activity
    roles_by_activity: dict[int, set[str]] = {a.id: set() for a in activities}
    for entry in entries:
        roles_by_activity[entry.activity_id].add(entry.raci_role)

    without_a = [a.name for a in activities if "A" not in roles_by_activity[a.id]]
    without_r = [a.name for a in activities if "R" not in roles_by_activity[a.id]]

    return {
        "activities_without_accountable": without_a,
        "activities_without_responsible": without_r,
        "is_valid": not without_a and not without_r,
    }


# ── Private helpers ───────────────────────────────────────────────────────────


def _assert_program_belongs_to_tenant(tenant_id: int, program_id: int) -> None:
    """Raise ValueError if the program doesn't belong to the given tenant.

    Why: Prevents cross-tenant operations when program_id is supplied by the
    client.  Always call before any program-scoped RACI operation.
    """
    stmt = select(Program.id).where(
        Program.id == program_id,
        Program.tenant_id == tenant_id,
    )
    result = db.session.execute(stmt).scalar_one_or_none()
    if result is None:
        raise ValueError(f"Program {program_id} not found for tenant {tenant_id}.")


def _assert_activity_belongs(tenant_id: int, program_id: int, activity_id: int) -> None:
    """Raise ValueError if the activity doesn't belong to this tenant+program."""
    stmt = select(RaciActivity.id).where(
        RaciActivity.id == activity_id,
        RaciActivity.tenant_id == tenant_id,
        RaciActivity.program_id == program_id,
    )
    result = db.session.execute(stmt).scalar_one_or_none()
    if result is None:
        raise ValueError(
            f"Activity {activity_id} not found in program {program_id} for tenant {tenant_id}."
        )


def _assert_member_belongs(tenant_id: int, program_id: int, member_id: int) -> None:
    """Raise ValueError if the team member doesn't belong to this tenant+program."""
    stmt = select(TeamMember.id).where(
        TeamMember.id == member_id,
        TeamMember.tenant_id == tenant_id,
        TeamMember.program_id == program_id,
    )
    result = db.session.execute(stmt).scalar_one_or_none()
    if result is None:
        raise ValueError(
            f"TeamMember {member_id} not found in program {program_id} for tenant {tenant_id}."
        )
