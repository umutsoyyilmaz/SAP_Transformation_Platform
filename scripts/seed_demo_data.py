#!/usr/bin/env python3
"""
SAP Transformation Platform — Demo Data Seed Script (Modular).

Company: Anadolu Food & Beverage Inc.
Architecture: Signavio L1→L2→L3→L4

Usage:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --append
    python scripts/seed_demo_data.py --verbose
"""

import argparse
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.program import (
    Committee, Gate, Phase, Program, TeamMember, Workstream,
)
from app.models.scenario import Scenario, Workshop
from app.models.requirement import Requirement, RequirementTrace, OpenItem
from app.models.backlog import (
    BacklogItem, ConfigItem, FunctionalSpec, Sprint, TechnicalSpec,
)
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
    TestSuite, TestStep, TestCaseDependency, TestCycleSuite,
    TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink,
    PlanScope, PlanTestCase, PlanDataSet,
)
from app.models.scope import Process, RequirementProcessMapping, Analysis
from app.models.raid import (
    Risk, Action, Issue, Decision,
    next_risk_code, next_action_code, next_issue_code, next_decision_code,
    calculate_risk_score, risk_rag_status,
)
from app.models.notification import Notification
from app.models.data_factory import (
    DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation,
)
from app.models.integration import Interface, Wave as IntWave, ConnectivityTest, SwitchPlan, InterfaceChecklist
from app.models.explore import (
    ProcessLevel, ExploreWorkshop, WorkshopScopeItem,
    WorkshopAttendee, WorkshopAgendaItem,
    ProcessStep, ExploreDecision, ExploreOpenItem,
    ExploreRequirement, RequirementOpenItemLink,
    RequirementDependency, OpenItemComment,
)
from app.models.cutover import (
    CutoverPlan, CutoverScopeItem, RunbookTask, TaskDependency,
    Rehearsal, GoNoGoItem, HypercareIncident, HypercareSLA,
    HypercareWarRoom, PostGoliveChangeRequest,
)

# ── Modular data imports ─────────────────────────────────────────────────
from scripts.seed_data.scenarios import SCENARIOS
from scripts.seed_data.processes import PROCESS_SEED
from scripts.seed_data.requirements import REQUIREMENTS, TRACES, RPM_DATA, OI_DATA
from scripts.seed_data.backlog import SPRINTS, BACKLOG_ITEMS, CONFIG_ITEMS
from scripts.seed_data.specs_testing import (
    FS_DATA, TS_DATA, TEST_PLAN_DATA, TEST_CASE_DATA, EXECUTION_DATA, DEFECT_DATA,
    SUITE_DATA, STEP_DATA, CYCLE_SUITE_DATA,
    TEST_RUN_DATA, STEP_RESULT_DATA, DEFECT_COMMENT_DATA,
    DEFECT_HISTORY_DATA, DEFECT_LINK_DATA,
)
from scripts.seed_data.raid import RISK_DATA, ACTION_DATA, ISSUE_DATA, DECISION_DATA
from scripts.seed_data.integration import WAVES as INT_WAVES, INTERFACES as INT_INTERFACES
from scripts.seed_data.data_factory import (
    DATA_OBJECTS, MIGRATION_WAVES, CLEANSING_TASKS,
    LOAD_CYCLES, RECONCILIATIONS,
)
from scripts.seed_data.explore import (
    PROCESS_LEVELS as EXPLORE_LEVELS, WORKSHOPS as EXPLORE_WORKSHOPS,
    WORKSHOP_SCOPE_ITEMS, WORKSHOP_ATTENDEES, WORKSHOP_AGENDA_ITEMS,
    PROCESS_STEPS as EXPLORE_STEPS, DECISIONS as EXPLORE_DECISIONS,
    OPEN_ITEMS as EXPLORE_OI, REQUIREMENTS as EXPLORE_REQS,
    REQUIREMENT_OI_LINKS, REQUIREMENT_DEPENDENCIES, OPEN_ITEM_COMMENTS,
)
from scripts.seed_data.cutover import (
    CUTOVER_PLANS, SCOPE_ITEMS as CUT_SCOPE_ITEMS,
    RUNBOOK_TASKS, TASK_DEPENDENCIES,
    REHEARSALS, GO_NO_GO_ITEMS,
    HYPERCARE_INCIDENTS, SLA_TARGETS,
    WAR_ROOMS, CHANGE_REQUESTS,
)

# Auth models for admin seeding
from app.models.auth import Tenant, User, Role, Permission, RolePermission, UserRole, ProjectMember
from app.models.project import Project
from app.utils.crypto import hash_password


def _seed_admin_data():
    """Seed tenants, roles, permissions, and demo users.

    Delegates to seed_roles.py for permissions/roles, then creates
    additional demo tenants and users for a realistic demo environment.
    """
    from scripts.seed_roles import seed_permissions, seed_roles

    print("\n🔐 Seeding permissions & roles...")
    seed_permissions()
    seed_roles()

    # ── Tenants (customer tenants only — no Perga) ──────────────
    print("\n🏢 Seeding demo tenants...")
    DEMO_TENANTS = [
        {"name": "Anadolu Food Inc.", "slug": "anadolu-gida", "plan": "premium",
         "max_users": 50, "max_projects": 20, "is_active": True},
        {"name": "Demo Company", "slug": "demo", "plan": "trial",
         "max_users": 10, "max_projects": 3, "is_active": True},
    ]

    tenants = {}
    for t_data in DEMO_TENANTS:
        existing = Tenant.query.filter_by(slug=t_data["slug"]).first()
        if existing:
            tenants[t_data["slug"]] = existing
            print(f"   ⏩ Tenant '{t_data['name']}' already exists (id={existing.id})")
        else:
            t = Tenant(**t_data)
            db.session.add(t)
            db.session.flush()
            tenants[t_data["slug"]] = t
            print(f"   ✅ Tenant '{t.name}' created (id={t.id})")

    # ── Platform Admin (tenant-independent) ────────────────────
    print("\n👑 Seeding platform admin...")
    existing_admin = User.query.filter_by(email="admin@perga.io", tenant_id=None).first()
    if not existing_admin:
        admin_user = User(
            tenant_id=None,
            email="admin@perga.io",
            password_hash=hash_password("Perga2026!"),
            full_name="Platform Admin",
            status="active",
        )
        db.session.add(admin_user)
        db.session.flush()
        role = Role.query.filter_by(name="platform_admin", tenant_id=None).first()
        if role:
            db.session.add(UserRole(user_id=admin_user.id, role_id=role.id))
        print(f"   ✅ Platform admin 'admin@perga.io' created (tenant_id=None, pw=Perga2026!)")
    else:
        print(f"   ⏩ Platform admin 'admin@perga.io' already exists")

    # ── Tenant Users ───────────────────────────────────────────
    print("\n👤 Seeding demo users...")
    DEMO_USERS = [
        # Anadolu tenant admin
        {"tenant_slug": "anadolu-gida", "email": "admin@anadolu.com",
         "full_name": "Anadolu Admin", "password": "Anadolu2026!",
         "role": "tenant_admin"},
        # Anadolu project manager
        {"tenant_slug": "anadolu-gida", "email": "pm@anadolu.com",
         "full_name": "Mehmet Yilmaz", "password": "Test1234!",
         "role": "project_manager"},
        # Anadolu functional consultant
        {"tenant_slug": "anadolu-gida", "email": "consultant@anadolu.com",
         "full_name": "Ayse Kaya", "password": "Test1234!",
         "role": "functional_consultant"},
        # Demo admin
        {"tenant_slug": "demo", "email": "admin@demo.com",
         "full_name": "Demo Admin", "password": "Demo2026!",
         "role": "tenant_admin"},
        # Demo project manager
        {"tenant_slug": "demo", "email": "pm@demo.com",
         "full_name": "Demo PM", "password": "Demo1234!",
         "role": "project_manager"},
        # Demo viewer
        {"tenant_slug": "demo", "email": "viewer@demo.com",
         "full_name": "Demo Viewer", "password": "Demo1234!",
         "role": "viewer"},
    ]

    for u_data in DEMO_USERS:
        tenant = tenants.get(u_data["tenant_slug"])
        if not tenant:
            continue
        existing = User.query.filter_by(
            tenant_id=tenant.id, email=u_data["email"]
        ).first()
        if existing:
            print(f"   ⏩ User '{u_data['email']}' already exists")
            continue
        user = User(
            tenant_id=tenant.id,
            email=u_data["email"],
            password_hash=hash_password(u_data["password"]),
            full_name=u_data["full_name"],
            status="active",
        )
        db.session.add(user)
        db.session.flush()
        # Assign role
        role = Role.query.filter_by(name=u_data["role"], tenant_id=None).first()
        if role:
            db.session.add(UserRole(user_id=user.id, role_id=role.id))
        print(f"   ✅ User '{u_data['email']}' (role={u_data['role']}, pw={u_data['password']})")

    db.session.commit()
    print(f"\n   📊 Totals → Tenants: {Tenant.query.count()}, Users: {User.query.count()}")


def _ensure_demo_project_access():
    """
    Ensure demo admin has visible project scope after each seed.

    Guarantees for tenant slug='demo':
    - at least one Program
    - at least one default Project
    - admin@demo.com membership on all demo projects
    """
    demo_tenant = Tenant.query.filter_by(slug="demo").first()
    demo_admin = User.query.filter_by(email="admin@demo.com").first()
    if not demo_tenant or not demo_admin:
        return

    program = Program.query.filter_by(tenant_id=demo_tenant.id).order_by(Program.id.asc()).first()
    if not program:
        program = Program(
            tenant_id=demo_tenant.id,
            name="Demo Program",
            description="Auto-created demo program for project-scope access",
            project_type="template_rollout",
            methodology="agile",
            status="active",
            priority="high",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(program)
        db.session.flush()
        print(f"   ✅ Demo program created (id={program.id})")

    default_project = Project.query.filter_by(
        tenant_id=demo_tenant.id,
        program_id=program.id,
        is_default=True,
    ).first()
    if not default_project:
        default_project = Project(
            tenant_id=demo_tenant.id,
            program_id=program.id,
            code="DEMO-DEFAULT",
            name="Demo Default Project",
            type="implementation",
            status="active",
            is_default=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(default_project)
        db.session.flush()
        print(f"   ✅ Demo default project created (id={default_project.id})")

    created_memberships = 0
    for project in Project.query.filter_by(tenant_id=demo_tenant.id).all():
        pm = ProjectMember.query.filter_by(project_id=project.id, user_id=demo_admin.id).first()
        if pm:
            continue
        db.session.add(
            ProjectMember(
                project_id=project.id,
                user_id=demo_admin.id,
                role_in_project="owner",
            )
        )
        created_memberships += 1

    db.session.commit()
    if created_memberships:
        print(f"   ✅ Demo admin project memberships ensured (+{created_memberships})")


# ═════════════════════════════════════════════════════════════════════════════
# CORE DATA — Anadolu Food & Beverage Inc.
# ═════════════════════════════════════════════════════════════════════════════

PROGRAM_DATA = {
    "name": "Anadolu Food — S/4HANA Cloud Transformation",
    "description": (
        "Anadolu Food & Beverage Inc. — SAP ECC 6.0 to S/4HANA Cloud greenfield "
        "transformation. 5,000+ employees, 8 production facilities, annual revenue of 8.5 billion TRY. "
        "FI/CO, MM, SD, PP, QM, WM, HCM modules. SAP Activate & Signavio."
    ),
    "project_type": "greenfield",
    "methodology": "sap_activate",
    "status": "in_progress",
    "priority": "critical",
    "sap_product": "S/4HANA Cloud",
    "deployment_option": "cloud",
    "start_date": date(2025, 4, 1),
    "go_live_date": date(2026, 11, 30),
}

PHASES = [
    {"name": "Discover", "description": "Discovery: Business requirements, current process analysis, Signavio mapping",
     "order": 1, "status": "completed",
     "planned_start": date(2025, 4, 1), "planned_end": date(2025, 5, 31),
     "actual_start": date(2025, 4, 1), "actual_end": date(2025, 5, 28), "completion_pct": 100,
     "gates": [
         {"name": "Discovery Gate", "gate_type": "quality_gate", "status": "passed",
          "criteria": "Business requirements 100% gathered, Signavio L1 mapped"},
     ]},
    {"name": "Prepare", "description": "Preparation: Project plan, team, infrastructure, Signavio L2 modeling",
     "order": 2, "status": "completed",
     "planned_start": date(2025, 6, 1), "planned_end": date(2025, 8, 31),
     "actual_start": date(2025, 6, 2), "actual_end": date(2025, 8, 29), "completion_pct": 100,
     "gates": [
         {"name": "Preparation Gate", "gate_type": "quality_gate", "status": "passed",
          "criteria": "Project plan approved, environments ready, Signavio L2 completed"},
     ]},
    {"name": "Explore", "description": "Explore: Fit-to-Standard workshops, L3/L4 process analysis",
     "order": 3, "status": "completed",
     "planned_start": date(2025, 9, 1), "planned_end": date(2025, 12, 31),
     "actual_start": date(2025, 9, 1), "actual_end": date(2025, 12, 20), "completion_pct": 100,
     "gates": [
         {"name": "Explore Gate", "gate_type": "quality_gate", "status": "passed",
          "criteria": "Fit-Gap 100%, requirements approved, WRICEF list finalized"},
     ]},
    {"name": "Realize", "description": "Realize: Configuration, WRICEF development, unit testing, SIT",
     "order": 4, "status": "in_progress",
     "planned_start": date(2026, 1, 5), "planned_end": date(2026, 6, 30),
     "actual_start": date(2026, 1, 5), "completion_pct": 45,
     "gates": [
         {"name": "Realize Gate — Sprint Review 1", "gate_type": "milestone", "status": "passed",
          "criteria": "Sprint 1 completed, unit tests passed"},
         {"name": "Realize Gate — SIT Complete", "gate_type": "quality_gate", "status": "pending",
          "criteria": "SIT P1/P2 zero, pass rate >95%"},
     ]},
    {"name": "Deploy", "description": "Deploy: UAT, training, data migration, cutover preparation",
     "order": 5, "status": "not_started",
     "planned_start": date(2026, 7, 1), "planned_end": date(2026, 10, 31),
     "gates": [
         {"name": "Deploy Gate — UAT Sign-Off", "gate_type": "quality_gate", "status": "pending",
          "criteria": "UAT approved, training completed, cutover plan ready"},
         {"name": "Go-Live Readiness Gate", "gate_type": "go_no_go", "status": "pending",
          "criteria": "Go/No-Go decision, all criteria green"},
     ]},
    {"name": "Run", "description": "Run: Hypercare, stabilization, optimization",
     "order": 6, "status": "not_started",
     "planned_start": date(2026, 11, 1), "planned_end": date(2027, 1, 31)},
]

WORKSTREAMS = [
    {"name": "Finance (FI/CO)", "ws_type": "functional", "lead_name": "Ahmet Yildiz",
     "description": "Accounting, cost accounting, consolidation, tax"},
    {"name": "Materials Management (MM)", "ws_type": "functional", "lead_name": "Elif Kara",
     "description": "Procurement, inventory management, invoice verification"},
    {"name": "Sales & Distribution (SD)", "ws_type": "functional", "lead_name": "Burak Sahin",
     "description": "Sales, shipping, billing, pricing"},
    {"name": "Production Planning (PP/QM)", "ws_type": "functional", "lead_name": "Deniz Aydin",
     "description": "Production planning, MRP, quality management, HACCP"},
    {"name": "Warehouse Management (EWM)", "ws_type": "functional", "lead_name": "Gokhan Demir",
     "description": "Warehouse management, shelf management, wave picking"},
    {"name": "Human Capital (HCM)", "ws_type": "functional", "lead_name": "Seda Arslan",
     "description": "Payroll, leave management, performance management"},
    {"name": "Basis / Technology", "ws_type": "technical", "lead_name": "Murat Celik",
     "description": "System administration, authorization, Fiori, performance"},
    {"name": "Integration (BTP)", "ws_type": "technical", "lead_name": "Zeynep Koc",
     "description": "BTP CPI, interfaces, API management, e-Document"},
    {"name": "Data Migration", "ws_type": "technical", "lead_name": "Hakan Gunes",
     "description": "Data migration, data cleansing, LTMC, validation"},
    {"name": "Testing & Quality", "ws_type": "management", "lead_name": "Ayse Polat",
     "description": "Test management, SIT, UAT, regression, automation"},
    {"name": "Change Management", "ws_type": "management", "lead_name": "Canan Ozturk",
     "description": "Change management, training, communication, change agent network"},
    {"name": "PMO", "ws_type": "management", "lead_name": "Kemal Erdogan",
     "description": "Program management, planning, risk, budget, reporting"},
]

TEAM_MEMBERS = [
    {"name": "Kemal Erdogan", "email": "kemal.erdogan@anadolugida.com",
     "role": "project_manager", "raci": "accountable", "organization": "Anadolu Food"},
    {"name": "Ahmet Yildiz", "email": "ahmet.yildiz@anadolugida.com",
     "role": "functional_lead", "raci": "responsible", "organization": "Anadolu Food"},
    {"name": "Elif Kara", "email": "elif.kara@anadolugida.com",
     "role": "functional_lead", "raci": "responsible", "organization": "Anadolu Food"},
    {"name": "Burak Sahin", "email": "burak.sahin@anadolugida.com",
     "role": "functional_lead", "raci": "responsible", "organization": "Anadolu Food"},
    {"name": "Deniz Aydin", "email": "deniz.aydin@partner.com",
     "role": "functional_lead", "raci": "responsible", "organization": "SAP Partner"},
    {"name": "Zeynep Koc", "email": "zeynep.koc@partner.com",
     "role": "technical_lead", "raci": "responsible", "organization": "SAP Partner"},
    {"name": "Murat Celik", "email": "murat.celik@partner.com",
     "role": "technical_lead", "raci": "responsible", "organization": "SAP Partner"},
    {"name": "Hakan Gunes", "email": "hakan.gunes@anadolugida.com",
     "role": "team_member", "raci": "responsible", "organization": "Anadolu Food"},
    {"name": "Ayse Polat", "email": "ayse.polat@partner.com",
     "role": "team_member", "raci": "responsible", "organization": "SAP Partner"},
    {"name": "Canan Ozturk", "email": "canan.ozturk@anadolugida.com",
     "role": "team_member", "raci": "consulted", "organization": "Anadolu Food"},
    {"name": "Seda Arslan", "email": "seda.arslan@anadolugida.com",
     "role": "functional_lead", "raci": "responsible", "organization": "Anadolu Food"},
    {"name": "Gokhan Demir", "email": "gokhan.demir@partner.com",
     "role": "functional_lead", "raci": "responsible", "organization": "SAP Partner"},
]

COMMITTEES = [
    {"name": "Steering Committee", "committee_type": "steering",
     "meeting_frequency": "monthly", "chair_name": "Osman Aydin (CEO)",
     "description": "Executive decision committee. Go/No-Go, budget, scope change approval."},
    {"name": "PMO Weekly", "committee_type": "pmo",
     "meeting_frequency": "weekly", "chair_name": "Kemal Erdogan",
     "description": "Weekly project status meeting. Risk, issue, timeline tracking."},
    {"name": "Change Advisory Board (CAB)", "committee_type": "advisory",
     "meeting_frequency": "biweekly", "chair_name": "Murat Celik",
     "description": "Transport approval, technical change management, environment strategy."},
    {"name": "Architecture Review Board", "committee_type": "advisory",
     "meeting_frequency": "monthly", "chair_name": "Zeynep Koc",
     "description": "Architecture decisions, integration design, BTP strategy."},
]


# ═════════════════════════════════════════════════════════════════════════════
# HELPER
# ═════════════════════════════════════════════════════════════════════════════

def _d(val):
    """Convert an ISO date string to a date object, or return None."""
    if val and isinstance(val, str):
        return date.fromisoformat(val)
    return val


def _p(msg, verbose):
    if verbose:
        print(msg)


# ═════════════════════════════════════════════════════════════════════════════
# SEED FUNCTION
# ═════════════════════════════════════════════════════════════════════════════

def seed_all(app, append=False, verbose=False):
    """Seed ALL tables with demo data."""
    with app.app_context():
        if not append:
            print("🗑️  Clearing existing data...")
            for model in [PostGoliveChangeRequest, HypercareWarRoom,
                          HypercareSLA, HypercareIncident, GoNoGoItem,
                          TaskDependency, RunbookTask, CutoverScopeItem,
                          Rehearsal, CutoverPlan,
                          InterfaceChecklist, SwitchPlan, ConnectivityTest, Interface, IntWave,
                          Notification, Decision, Issue, Action, Risk,
                          DefectLink, DefectHistory, DefectComment,
                          TestStepResult, TestRun,
                          TestCycleSuite, TestStep, TestCaseDependency,
                          TestExecution, Defect, TestCase, TestSuite,
                          TestCycle, TestPlan,
                          TechnicalSpec, FunctionalSpec, ConfigItem, BacklogItem,
                          Sprint, RequirementTrace, OpenItem, RequirementProcessMapping, Requirement,
                          Analysis, Process, Workshop, Scenario,
                          Committee, TeamMember, Workstream, Gate, Phase, Program,
                          UserRole, RolePermission, User, Role, Permission, Tenant]:
                db.session.query(model).delete()
            db.session.commit()
            print("   Done.\n")

        # ── 0. Tenants, Roles & Users ─────────────────────────────────────
        _seed_admin_data()
        _ensure_demo_project_access()

        # ── 1. Program ───────────────────────────────────────────────────
        print("📦 Creating program...")
        anadolu_tenant = Tenant.query.filter_by(slug="anadolu-gida").first()
        program = Program(tenant_id=anadolu_tenant.id, **PROGRAM_DATA)
        db.session.add(program)
        db.session.flush()
        pid = program.id
        print(f"   ✅ Program: {program.name} (ID: {pid})")

        # ── 2. Phases + Gates ────────────────────────────────────────────
        print("\n📅 Creating phases & gates...")
        phase_ids = {}
        for p_data in PHASES:
            gates_data = p_data.pop("gates", [])
            phase = Phase(program_id=pid, **{k: v for k, v in p_data.items() if k != "gates"})
            db.session.add(phase)
            db.session.flush()
            phase_ids[p_data["name"]] = phase.id
            _p(f"   📅 Phase: {phase.name} ({phase.status})", verbose)
            for g_data in gates_data:
                gate = Gate(phase_id=phase.id, **g_data)
                db.session.add(gate)
            p_data["gates"] = gates_data  # restore
        gate_count = sum(len(p.get("gates", [])) for p in PHASES)
        print(f"   ✅ {len(PHASES)} phases, {gate_count} gates")

        # ── 3. Workstreams ───────────────────────────────────────────────
        print("\n🔧 Creating workstreams...")
        ws_ids = {}
        for ws_data in WORKSTREAMS:
            ws = Workstream(program_id=pid, **ws_data)
            db.session.add(ws)
            db.session.flush()
            ws_ids[ws_data["name"]] = ws.id
        print(f"   ✅ {len(WORKSTREAMS)} workstreams")

        # ── 4. Team Members ──────────────────────────────────────────────
        print("\n👥 Creating team members...")
        for tm_data in TEAM_MEMBERS:
            tm = TeamMember(program_id=pid, **tm_data)
            db.session.add(tm)
        print(f"   ✅ {len(TEAM_MEMBERS)} team members")

        # ── 5. Committees ────────────────────────────────────────────────
        print("\n🏛️  Creating committees...")
        for c_data in COMMITTEES:
            comm = Committee(program_id=pid, **c_data)
            db.session.add(comm)
        print(f"   ✅ {len(COMMITTEES)} committees")

        # ── 6. Scenarios + Workshops ─────────────────────────────────────
        print("\n🔮 Creating scenarios & workshops...")
        scenario_ids = {}
        total_workshops = 0
        for s_data in SCENARIOS:
            ws_list = s_data.pop("workshops", [])
            scenario = Scenario(program_id=pid, **s_data)
            db.session.add(scenario)
            db.session.flush()
            scenario_ids[s_data["name"]] = scenario.id
            for w_data in ws_list:
                workshop = Workshop(scenario_id=scenario.id, **w_data)
                db.session.add(workshop)
                total_workshops += 1
            scenario.total_workshops = len(ws_list)
            s_data["workshops"] = ws_list  # restore
        print(f"   ✅ {len(SCENARIOS)} scenarios, {total_workshops} workshops")

        # ── 7. Processes (L2→L3→L4) & Analyses ──────────────────────────
        print("\n🔍 Creating L2/L3/L4 processes & analyses...")
        proc_count = 0
        an_count = 0
        l3_ids = {}

        def _seed_proc(parent_id, data, sid):
            nonlocal proc_count, an_count
            children = data.pop("children", [])
            analyses = data.pop("analyses", [])
            area = data.pop("_area", None)
            p = Process(scenario_id=sid, parent_id=parent_id, **data)
            db.session.add(p)
            db.session.flush()
            proc_count += 1
            if p.level == "L3" and p.code:
                l3_ids[p.code] = p.id
            _p(f"   [{p.level}] {p.name}", verbose)
            for a_data in analyses:
                a = Analysis(process_id=p.id, **a_data)
                db.session.add(a)
                an_count += 1
            for child in children:
                _seed_proc(p.id, child, sid)
            data["children"] = children
            data["analyses"] = analyses
            if area is not None:
                data["_area"] = area

        # Distribute processes across scenarios by process_area
        scenario_area_map = {s["process_area"]: s["name"] for s in SCENARIOS}
        for proc_data in PROCESS_SEED:
            area = proc_data.get("_area", "order_to_cash")
            s_name = scenario_area_map.get(area, list(scenario_ids.keys())[0])
            sid = scenario_ids[s_name]
            _seed_proc(None, proc_data, sid)
        db.session.flush()
        print(f"   ✅ {proc_count} processes, {an_count} analyses")

        # ── 8. Requirements ──────────────────────────────────────────────
        print("\n📋 Creating requirements...")
        req_ids = {}
        for r_data in REQUIREMENTS:
            req = Requirement(program_id=pid, **r_data)
            db.session.add(req)
            db.session.flush()
            req_ids[r_data["code"]] = req.id
        print(f"   ✅ {len(REQUIREMENTS)} requirements")

        # ── 9. Traces ────────────────────────────────────────────────────
        print("\n🔗 Creating traces...")
        trace_count = 0
        for t in TRACES:
            req_id = req_ids.get(t["req_code"])
            if not req_id:
                continue
            target_id = None
            if t["target_type"] == "phase":
                target_id = phase_ids.get(t["target_name"])
            elif t["target_type"] == "workstream":
                target_id = ws_ids.get(t["target_name"])
            elif t["target_type"] == "scenario":
                target_id = scenario_ids.get(t["target_name"])
            if target_id:
                tr = RequirementTrace(requirement_id=req_id, target_type=t["target_type"],
                                       target_id=target_id, trace_type=t["trace_type"])
                db.session.add(tr)
                trace_count += 1
        print(f"   ✅ {trace_count} traces")

        # ── 10. Requirement–Process Mappings ─────────────────────────────
        print("\n🔗 Creating requirement–process mappings...")
        rpm_count = 0
        for m in RPM_DATA:
            r_id = req_ids.get(m["req_code"])
            p_id = l3_ids.get(m["l3_code"])
            if r_id and p_id:
                rpm = RequirementProcessMapping(requirement_id=r_id, process_id=p_id,
                                                 coverage_type=m["coverage_type"], notes=m.get("notes", ""))
                db.session.add(rpm)
                rpm_count += 1
        print(f"   ✅ {rpm_count} mappings")

        # ── 11. Open Items ───────────────────────────────────────────────
        print("\n📌 Creating open items...")
        oi_count = 0
        for oi in OI_DATA:
            r_id = req_ids.get(oi.pop("req_code"))
            if r_id:
                open_item = OpenItem(requirement_id=r_id, **oi)
                db.session.add(open_item)
                oi_count += 1
            oi["req_code"] = list(req_ids.keys())[0]  # restore key for re-run safety
        db.session.flush()
        print(f"   ✅ {oi_count} open items")

        # ── 12. Sprints ──────────────────────────────────────────────────
        print("\n🏃 Creating sprints...")
        sprint_objs = []
        for s_data in SPRINTS:
            sprint = Sprint(
                program_id=pid,
                name=s_data["name"], goal=s_data["goal"], status=s_data["status"],
                start_date=date.fromisoformat(s_data["start_date"]),
                end_date=date.fromisoformat(s_data["end_date"]),
                capacity_points=s_data["capacity_points"],
                velocity=s_data["velocity"], order=s_data["order"],
            )
            db.session.add(sprint)
            db.session.flush()
            sprint_objs.append(sprint)
        print(f"   ✅ {len(SPRINTS)} sprints")

        # ── 13. Backlog Items (WRICEF) ───────────────────────────────────
        print("\n📝 Creating backlog items...")
        backlog_objs = {}
        req_link_map = {
            "WF-MM-001": "REQ-MM-001", "WF-FI-001": "REQ-FI-002",
            "INT-SD-001": "REQ-INT-001", "INT-PP-001": "REQ-INT-002",
            "CNV-MD-001": "REQ-TEC-002", "CNV-MD-002": "REQ-TEC-002",
            "ENH-FI-001": "REQ-FI-001", "RPT-FI-001": "REQ-BIZ-001",
        }
        for bi_data in BACKLOG_ITEMS:
            sprint_idx = bi_data.pop("sprint_idx", None)
            sprint_id = sprint_objs[sprint_idx].id if sprint_idx is not None else None
            req_code = req_link_map.get(bi_data["code"])
            req_id = req_ids.get(req_code) if req_code else None
            bi = BacklogItem(program_id=pid, sprint_id=sprint_id, requirement_id=req_id, **bi_data)
            db.session.add(bi)
            db.session.flush()
            backlog_objs[bi_data["code"]] = bi
            bi_data["sprint_idx"] = sprint_idx  # restore
        print(f"   ✅ {len(BACKLOG_ITEMS)} backlog items")

        # ── 14. Config Items ─────────────────────────────────────────────
        print("\n⚙️  Creating config items...")
        cfg_req_map = {"CFG-FI-003": "REQ-FI-001", "CFG-SD-002": "REQ-SD-001", "CFG-BASIS-001": "REQ-TEC-003"}
        config_objs = {}
        for ci_data in CONFIG_ITEMS:
            req_code = cfg_req_map.get(ci_data["code"])
            req_id = req_ids.get(req_code) if req_code else None
            ci = ConfigItem(program_id=pid, requirement_id=req_id, **ci_data)
            db.session.add(ci)
            db.session.flush()
            config_objs[ci_data["code"]] = ci
        print(f"   ✅ {len(CONFIG_ITEMS)} config items")

        # ── 15. Functional Specs ─────────────────────────────────────────
        print("\n📄 Creating functional specs...")
        fs_objs = {}
        for fs_d in FS_DATA:
            bcode = fs_d.pop("backlog_code", None)
            ccode = fs_d.pop("config_code", None)
            fs = FunctionalSpec(
                backlog_item_id=backlog_objs[bcode].id if bcode and bcode in backlog_objs else None,
                config_item_id=config_objs[ccode].id if ccode and ccode in config_objs else None,
                **fs_d,
            )
            db.session.add(fs)
            db.session.flush()
            key = bcode or ccode
            fs_objs[key] = fs
            fs_d["backlog_code"] = bcode  # restore
            fs_d["config_code"] = ccode
        print(f"   ✅ {len(FS_DATA)} functional specs")

        # ── 16. Technical Specs ──────────────────────────────────────────
        print("\n📐 Creating technical specs...")
        for ts_d in TS_DATA:
            fs_key = ts_d.pop("fs_key")
            fs = fs_objs.get(fs_key)
            if fs:
                ts = TechnicalSpec(functional_spec_id=fs.id, **ts_d)
                db.session.add(ts)
            ts_d["fs_key"] = fs_key  # restore
        print(f"   ✅ {len(TS_DATA)} technical specs")

        # ── 17. Test Plans, Cycles, Cases ────────────────────────────────
        print("\n🧪 Creating test plans, cycles, cases...")
        cycle_objs = []
        plan_objs = []
        for tp_d in TEST_PLAN_DATA:
            cycles_d = tp_d.pop("cycles", [])
            plan = TestPlan(
                program_id=pid, name=tp_d["name"], description=tp_d.get("description", ""),
                status=tp_d.get("status", "draft"),
                test_strategy=tp_d.get("test_strategy", ""),
                entry_criteria=tp_d.get("entry_criteria", ""),
                exit_criteria=tp_d.get("exit_criteria", ""),
                start_date=date.fromisoformat(tp_d["start_date"]) if tp_d.get("start_date") else None,
                end_date=date.fromisoformat(tp_d["end_date"]) if tp_d.get("end_date") else None,
            )
            db.session.add(plan)
            db.session.flush()
            plan_objs.append(plan)
            for i, c_d in enumerate(cycles_d):
                cycle = TestCycle(
                    plan_id=plan.id, name=c_d["name"],
                    test_layer=c_d.get("test_layer", "sit"),
                    status=c_d.get("status", "planning"),
                    start_date=date.fromisoformat(c_d["start_date"]) if c_d.get("start_date") else None,
                    end_date=date.fromisoformat(c_d["end_date"]) if c_d.get("end_date") else None,
                    order=i + 1,
                )
                db.session.add(cycle)
                db.session.flush()
                cycle_objs.append(cycle)
            tp_d["cycles"] = cycles_d
        print(f"   ✅ {len(TEST_PLAN_DATA)} plans, {len(cycle_objs)} cycles")

        tc_objs = {}
        for tc_d in TEST_CASE_DATA:
            req_code = tc_d.pop("req_code", None)
            req_id = req_ids.get(req_code) if req_code else None
            tc = TestCase(
                program_id=pid, requirement_id=req_id,
                code=tc_d["code"], title=tc_d["title"],
                module=tc_d.get("module", ""), test_layer=tc_d.get("test_layer", "sit"),
                status=tc_d.get("status", "draft"), priority=tc_d.get("priority", "medium"),
                preconditions=tc_d.get("preconditions", ""),
                test_steps=tc_d.get("test_steps", ""),
                expected_result=tc_d.get("expected_result", ""),
                is_regression=tc_d.get("is_regression", False),
            )
            db.session.add(tc)
            db.session.flush()
            tc_objs[tc_d["code"]] = tc
            tc_d["req_code"] = req_code
        print(f"   ✅ {len(TEST_CASE_DATA)} test cases")

        # ── 17b. Test Suites & assign cases ──────────────────────────────
        print("\n📦 Creating test suites...")
        suite_objs = {}
        for s_d in SUITE_DATA:
            tc_codes = s_d.pop("tc_codes", [])
            suite = TestSuite(
                program_id=pid, name=s_d["name"],
                description=s_d.get("description", ""),
                suite_type=s_d.get("suite_type", "Custom"),
                status=s_d.get("status", "draft"),
                module=s_d.get("module", ""),
                owner=s_d.get("owner", ""),
                tags=s_d.get("tags", ""),
            )
            db.session.add(suite)
            db.session.flush()
            suite_objs[suite.name] = suite
            for code in tc_codes:
                tc = tc_objs.get(code)
                if tc:
                    tc.suite_id = suite.id
            s_d["tc_codes"] = tc_codes  # restore
        print(f"   ✅ {len(SUITE_DATA)} suites")

        # ── 17b2. PlanScope + PlanTestCase (populate plan detail tabs) ──
        print("\n📋 Populating plan scopes and plan test cases...")
        ps_count = 0
        ptc_count = 0
        if plan_objs:
            first_plan = plan_objs[0]
            # Add scope items based on requirements that have test cases
            req_code_list = list(req_ids.keys())[:5]  # first 5 requirements
            for i, rcode in enumerate(req_code_list):
                rid = req_ids[rcode]
                scope = PlanScope(
                    plan_id=first_plan.id,
                    scope_type="requirement",
                    scope_ref_id=str(rid),
                    scope_label=f"{rcode} — Requirement scope item",
                    priority=["high", "medium", "critical", "medium", "low"][i % 5],
                    risk_level=["high", "medium", "low", "medium", "high"][i % 5],
                    coverage_status=["covered", "partial", "not_covered", "covered", "partial"][i % 5],
                )
                db.session.add(scope)
                ps_count += 1

            # Add all test cases to the first plan
            tc_list = list(tc_objs.values())
            for i, tc in enumerate(tc_list):
                ptc = PlanTestCase(
                    plan_id=first_plan.id,
                    test_case_id=tc.id,
                    added_method=["manual", "scope_suggest", "suite_import", "manual"][i % 4],
                    priority=tc.priority or "medium",
                    estimated_effort=[30, 45, 60, 20, 15][i % 5],
                    execution_order=i + 1,
                )
                db.session.add(ptc)
                ptc_count += 1

            # If there's a second plan, add a subset of test cases
            if len(plan_objs) > 1:
                second_plan = plan_objs[1]
                for i, tc in enumerate(tc_list[:5]):
                    ptc = PlanTestCase(
                        plan_id=second_plan.id,
                        test_case_id=tc.id,
                        added_method="suite_import",
                        priority="high",
                        estimated_effort=45,
                        execution_order=i + 1,
                    )
                    db.session.add(ptc)
                    ptc_count += 1

            db.session.flush()
        print(f"   ✅ {ps_count} plan scopes, {ptc_count} plan test cases")

        # ── 17c. Test Steps ──────────────────────────────────────────────
        print("\n🪜 Creating test steps...")
        step_count = 0
        for st_d in STEP_DATA:
            tc = tc_objs.get(st_d["tc_code"])
            if tc:
                step = TestStep(
                    test_case_id=tc.id,
                    step_no=st_d["step_no"],
                    action=st_d["action"],
                    expected_result=st_d.get("expected_result", ""),
                    test_data=st_d.get("test_data", ""),
                    notes=st_d.get("notes", ""),
                )
                db.session.add(step)
                step_count += 1
        print(f"   ✅ {step_count} test steps")

        # ── 17d. Cycle ↔ Suite assignments ───────────────────────────────
        print("\n🔗 Assigning suites to cycles...")
        cs_count = 0
        cycle_name_map = {c.name: c for c in cycle_objs}
        for cs_d in CYCLE_SUITE_DATA:
            cycle = cycle_name_map.get(cs_d["cycle_name"])
            suite = suite_objs.get(cs_d["suite_name"])
            if cycle and suite:
                cs = TestCycleSuite(
                    cycle_id=cycle.id, suite_id=suite.id,
                    order=cs_d.get("order", 1),
                    notes=cs_d.get("notes", ""),
                )
                db.session.add(cs)
                cs_count += 1
        print(f"   ✅ {cs_count} cycle-suite assignments")

        # ── 18. Test Executions ──────────────────────────────────────────
        print("\n▶️  Creating test executions...")
        exec_objs = []
        exec_count = 0
        sit_cycle = cycle_objs[0] if cycle_objs else None
        if sit_cycle:
            for ex_d in EXECUTION_DATA:
                tc = tc_objs.get(ex_d["tc_code"])
                if tc:
                    exe = TestExecution(
                        cycle_id=sit_cycle.id, test_case_id=tc.id,
                        result=ex_d["result"], executed_by=ex_d.get("executed_by", ""),
                        executed_at=datetime.now(timezone.utc),
                        duration_minutes=ex_d.get("duration_minutes"),
                        notes=ex_d.get("notes", ""),
                    )
                    db.session.add(exe)
                    db.session.flush()
                    exec_objs.append(exe)
                    exec_count += 1
                else:
                    exec_objs.append(None)
        print(f"   ✅ {exec_count} executions")

        # ── 19. Defects ──────────────────────────────────────────────────
        print("\n🐛 Creating defects...")
        for d_d in DEFECT_DATA:
            tc_code = d_d.pop("tc_code", None)
            tc = tc_objs.get(tc_code) if tc_code else None
            defect = Defect(
                program_id=pid, test_case_id=tc.id if tc else None,
                code=d_d["code"], title=d_d["title"],
                description=d_d.get("description", ""),
                steps_to_reproduce=d_d.get("steps_to_reproduce", ""),
                severity=d_d.get("severity", "P3"), status=d_d.get("status", "new"),
                module=d_d.get("module", ""), environment=d_d.get("environment", ""),
                reported_by=d_d.get("reported_by", ""),
                assigned_to=d_d.get("assigned_to", ""),
                found_in_cycle=d_d.get("found_in_cycle", ""),
                resolution=d_d.get("resolution", ""),
                root_cause=d_d.get("root_cause", ""),
                reopen_count=d_d.get("reopen_count", 0),
            )
            db.session.add(defect)
            d_d["tc_code"] = tc_code
        print(f"   ✅ {len(DEFECT_DATA)} defects")

        # ── 19b. Test Runs  (TS-Sprint 2) ─────────────────────────────────
        print("\n🏃 Creating test runs...")
        run_objs = []
        for tr_d in TEST_RUN_DATA:
            cycle = cycle_name_map.get(tr_d["cycle_name"])
            tc = tc_objs.get(tr_d["tc_code"])
            if cycle and tc:
                run = TestRun(
                    cycle_id=cycle.id, test_case_id=tc.id,
                    run_type=tr_d.get("run_type", "manual"),
                    status=tr_d.get("status", "not_started"),
                    result=tr_d.get("result", "not_run"),
                    environment=tr_d.get("environment", ""),
                    tester=tr_d.get("tester", ""),
                    notes=tr_d.get("notes", ""),
                    duration_minutes=tr_d.get("duration_minutes"),
                )
                if tr_d.get("status") in ("completed", "in_progress"):
                    run.started_at = datetime.now(timezone.utc)
                if tr_d.get("status") == "completed":
                    run.finished_at = datetime.now(timezone.utc)
                db.session.add(run)
                db.session.flush()
                run_objs.append(run)
            else:
                run_objs.append(None)
        print(f"   ✅ {sum(1 for r in run_objs if r)} test runs")

        # ── 19c. Step Results  (ADR-FINAL: under Executions) ──────────
        print("\n📋 Creating step results...")
        sr_count = 0
        for sr_d in STEP_RESULT_DATA:
            idx = sr_d["exec_index"]
            exe = exec_objs[idx] if idx < len(exec_objs) else None
            if exe:
                sr = TestStepResult(
                    execution_id=exe.id,
                    step_no=sr_d["step_no"],
                    result=sr_d.get("result", "not_run"),
                    actual_result=sr_d.get("actual_result", ""),
                    notes=sr_d.get("notes", ""),
                    executed_at=datetime.now(timezone.utc),
                )
                db.session.add(sr)
                sr_count += 1
        print(f"   ✅ {sr_count} step results")

        # ── 19d. Defect Comments  (TS-Sprint 2) ─────────────────────────
        print("\n💬 Creating defect comments...")
        defect_objs = Defect.query.filter_by(program_id=pid).order_by(Defect.id).all()
        dc_count = 0
        for dc_d in DEFECT_COMMENT_DATA:
            idx = dc_d["defect_index"]
            if idx < len(defect_objs):
                comment = DefectComment(
                    defect_id=defect_objs[idx].id,
                    author=dc_d["author"],
                    body=dc_d["body"],
                )
                db.session.add(comment)
                dc_count += 1
        print(f"   ✅ {dc_count} defect comments")

        # ── 19e. Defect History  (TS-Sprint 2) ──────────────────────────
        print("\n📜 Creating defect history...")
        dh_count = 0
        for dh_d in DEFECT_HISTORY_DATA:
            idx = dh_d["defect_index"]
            if idx < len(defect_objs):
                hist = DefectHistory(
                    defect_id=defect_objs[idx].id,
                    field=dh_d["field"],
                    old_value=dh_d["old_value"],
                    new_value=dh_d["new_value"],
                    changed_by=dh_d["changed_by"],
                )
                db.session.add(hist)
                dh_count += 1
        print(f"   ✅ {dh_count} defect history entries")

        # ── 19f. Defect Links  (TS-Sprint 2) ────────────────────────────
        print("\n🔗 Creating defect links...")
        dl_count = 0
        for dl_d in DEFECT_LINK_DATA:
            s_idx = dl_d["source_index"]
            t_idx = dl_d["target_index"]
            if s_idx < len(defect_objs) and t_idx < len(defect_objs):
                link = DefectLink(
                    source_defect_id=defect_objs[s_idx].id,
                    target_defect_id=defect_objs[t_idx].id,
                    link_type=dl_d.get("link_type", "related"),
                    notes=dl_d.get("notes", ""),
                )
                db.session.add(link)
                dl_count += 1
        print(f"   ✅ {dl_count} defect links")

        # ── 20. RAID ─────────────────────────────────────────────────────
        print("\n⚠️  Creating RAID items...")
        for rd in RISK_DATA:
            p = int(rd.get("probability", 3))
            i = int(rd.get("impact", 3))
            score = calculate_risk_score(p, i)
            rag = risk_rag_status(score)
            risk = Risk(
                program_id=pid, code=next_risk_code(),
                title=rd["title"], description=rd.get("description", ""),
                status=rd.get("status", "identified"), owner=rd.get("owner", ""),
                priority=rd.get("priority", "medium"),
                probability=p, impact=i, risk_score=score, rag_status=rag,
                risk_category=rd.get("risk_category", "technical"),
                risk_response=rd.get("risk_response", "mitigate"),
                mitigation_plan=rd.get("mitigation_plan", ""),
                contingency_plan=rd.get("contingency_plan", ""),
                trigger_event=rd.get("trigger_event", ""),
            )
            db.session.add(risk)
        print(f"   ✅ {len(RISK_DATA)} risks")

        for ad in ACTION_DATA:
            action = Action(
                program_id=pid, code=next_action_code(),
                title=ad["title"], description=ad.get("description", ""),
                status=ad.get("status", "open"), owner=ad.get("owner", ""),
                priority=ad.get("priority", "medium"),
                action_type=ad.get("action_type", "corrective"),
                due_date=_d(ad.get("due_date")), completed_date=_d(ad.get("completed_date")),
            )
            db.session.add(action)
        print(f"   ✅ {len(ACTION_DATA)} actions")

        for id_ in ISSUE_DATA:
            issue = Issue(
                program_id=pid, code=next_issue_code(),
                title=id_["title"], description=id_.get("description", ""),
                status=id_.get("status", "open"), owner=id_.get("owner", ""),
                priority=id_.get("priority", "medium"),
                severity=id_.get("severity", "moderate"),
                escalation_path=id_.get("escalation_path", ""),
                root_cause=id_.get("root_cause", ""),
                resolution=id_.get("resolution", ""),
                resolution_date=_d(id_.get("resolution_date")),
            )
            db.session.add(issue)
        print(f"   ✅ {len(ISSUE_DATA)} issues")

        for dd in DECISION_DATA:
            decision = Decision(
                program_id=pid, code=next_decision_code(),
                title=dd["title"], description=dd.get("description", ""),
                status=dd.get("status", "proposed"), owner=dd.get("owner", ""),
                priority=dd.get("priority", "medium"),
                decision_date=_d(dd.get("decision_date")),
                decision_owner=dd.get("decision_owner", ""),
                alternatives=dd.get("alternatives", ""),
                rationale=dd.get("rationale", ""),
                impact_description=dd.get("impact_description", ""),
                reversible=dd.get("reversible", True),
            )
            db.session.add(decision)
        print(f"   ✅ {len(DECISION_DATA)} decisions")

        # ── 21. EXPLORE PHASE DATA ──────────────────────────────────────
        print("\n🔍 Creating Explore Phase data...")
        # 21a. Process Levels
        for pl_d in EXPLORE_LEVELS:
            pl = ProcessLevel(
                id=pl_d["id"], project_id=pid,
                parent_id=pl_d.get("parent_id"),
                level=pl_d["level"], code=pl_d["code"], name=pl_d["name"],
                description=pl_d.get("description", ""),
                scope_status=pl_d.get("scope_status", "in_scope"),
                fit_status=pl_d.get("fit_status"),
                process_area_code=pl_d.get("process_area_code"),
                wave=pl_d.get("wave"),
                sort_order=pl_d.get("sort_order", 0),
            )
            db.session.add(pl)
        db.session.flush()
        print(f"   ✅ {len(EXPLORE_LEVELS)} process levels")

        # 21b. Workshops
        for ws_d in EXPLORE_WORKSHOPS:
            ws = ExploreWorkshop(
                id=ws_d["id"], project_id=pid,
                code=ws_d["code"], name=ws_d["name"],
                date=_d(ws_d.get("date")),
                location=ws_d.get("location"),
                facilitator_id=ws_d.get("facilitator_id"),
                process_area=ws_d.get("process_area"),
                wave=ws_d.get("wave"),
                status=ws_d.get("status", "planned"),
                session_number=ws_d.get("session_number"),
                notes=ws_d.get("notes", ""),
            )
            db.session.add(ws)
        db.session.flush()
        print(f"   ✅ {len(EXPLORE_WORKSHOPS)} workshops")

        # 21c. Workshop scope items
        for si_d in WORKSHOP_SCOPE_ITEMS:
            si = WorkshopScopeItem(
                id=si_d["id"],
                workshop_id=si_d["workshop_id"],
                process_level_id=si_d["process_level_id"],
            )
            db.session.add(si)
        print(f"   ✅ {len(WORKSHOP_SCOPE_ITEMS)} workshop scope items")

        # 21d. Workshop attendees
        for att_d in WORKSHOP_ATTENDEES:
            att = WorkshopAttendee(
                id=att_d["id"],
                workshop_id=att_d["workshop_id"],
                user_id=att_d.get("user_id"),
                name=att_d.get("name"),
                role=att_d.get("role"),
                organization=att_d.get("organization", att_d.get("department", "customer")),
                attendance_status=att_d.get("attendance_status", "confirmed"),
            )
            db.session.add(att)
        print(f"   ✅ {len(WORKSHOP_ATTENDEES)} attendees")

        # 21e. Workshop agenda items
        from datetime import time as _time
        for ag_d in WORKSHOP_AGENDA_ITEMS:
            ag = WorkshopAgendaItem(
                id=ag_d["id"],
                workshop_id=ag_d["workshop_id"],
                title=ag_d["title"],
                sort_order=ag_d.get("sort_order", 0),
                duration_minutes=ag_d.get("duration_minutes", 30),
                type=ag_d.get("type", "session"),
                time=ag_d.get("time", _time(9, 0)),
                notes=ag_d.get("description", ag_d.get("notes", "")),
            )
            db.session.add(ag)
        print(f"   ✅ {len(WORKSHOP_AGENDA_ITEMS)} agenda items")

        # 21f. Process steps (fit decisions)
        for ps_d in EXPLORE_STEPS:
            ps = ProcessStep(
                id=ps_d["id"],
                workshop_id=ps_d["workshop_id"],
                process_level_id=ps_d["process_level_id"],
                sort_order=ps_d.get("sort_order", 0),
                fit_decision=ps_d.get("fit_decision"),
                notes=ps_d.get("notes", ps_d.get("description", "")),
            )
            db.session.add(ps)
        db.session.flush()
        print(f"   ✅ {len(EXPLORE_STEPS)} process steps")

        # 21g. Decisions
        for dec_d in EXPLORE_DECISIONS:
            dec = ExploreDecision(
                id=dec_d["id"],
                project_id=pid,
                process_step_id=dec_d["process_step_id"],
                code=dec_d.get("code", f"DEC-{EXPLORE_DECISIONS.index(dec_d)+1:03d}"),
                text=dec_d.get("text", dec_d.get("decision_text", "")),
                decided_by=dec_d.get("decided_by", dec_d.get("owner_name", "Workshop Team")),
                category=dec_d.get("category", "process"),
                status=dec_d.get("status", "active"),
                rationale=dec_d.get("rationale"),
            )
            db.session.add(dec)
        print(f"   ✅ {len(EXPLORE_DECISIONS)} decisions (explore)")

        # 21h. Open items
        for oi_d in EXPLORE_OI:
            oi = ExploreOpenItem(
                id=oi_d["id"],
                project_id=pid,
                workshop_id=oi_d["workshop_id"],
                process_step_id=oi_d.get("process_step_id"),
                code=oi_d.get("code"),
                title=oi_d.get("title"),
                description=oi_d.get("description", ""),
                priority=oi_d.get("priority", "P2"),
                status=oi_d.get("status", "open"),
                category=oi_d.get("category", "clarification"),
                assignee_id=oi_d.get("assignee_id"),
                assignee_name=oi_d.get("assignee_name"),
                created_by_id=oi_d.get("created_by_id", oi_d.get("assignee_id", "system")),
                due_date=_d(oi_d.get("due_date")),
            )
            db.session.add(oi)
        db.session.flush()
        print(f"   ✅ {len(EXPLORE_OI)} open items (explore)")

        # 21i. Requirements (explore-level)
        for r_d in EXPLORE_REQS:
            req = ExploreRequirement(
                id=r_d["id"], project_id=pid,
                process_step_id=r_d.get("process_step_id"),
                workshop_id=r_d.get("workshop_id"),
                process_level_id=r_d.get("process_level_id"),
                scope_item_id=r_d.get("scope_item_id"),
                code=r_d.get("code"),
                title=r_d.get("title"),
                description=r_d.get("description", ""),
                priority=r_d.get("priority"),
                type=r_d.get("type"),
                fit_status=r_d.get("fit_status"),
                status=r_d.get("status"),
                effort_hours=r_d.get("effort_hours"),
                effort_story_points=r_d.get("effort_story_points"),
                complexity=r_d.get("complexity"),
                created_by_id=r_d.get("created_by_id"),
                created_by_name=r_d.get("created_by_name"),
                approved_by_id=r_d.get("approved_by_id"),
                approved_by_name=r_d.get("approved_by_name"),
                process_area=r_d.get("process_area"),
                wave=r_d.get("wave"),
                alm_synced=r_d.get("alm_synced", False),
                alm_sync_status=r_d.get("alm_sync_status"),
                deferred_to_phase=r_d.get("deferred_to_phase"),
                rejection_reason=r_d.get("rejection_reason"),
            )
            db.session.add(req)
        db.session.flush()
        print(f"   ✅ {len(EXPLORE_REQS)} requirements (explore)")

        # 21j. Requirement ↔ Open Item links
        for rl_d in REQUIREMENT_OI_LINKS:
            rl = RequirementOpenItemLink(
                id=rl_d["id"],
                requirement_id=rl_d["requirement_id"],
                open_item_id=rl_d["open_item_id"],
                link_type=rl_d.get("link_type", "related"),
            )
            db.session.add(rl)
        print(f"   ✅ {len(REQUIREMENT_OI_LINKS)} requirement ↔ OI links")

        # 21k. Requirement dependencies
        for rd_d in REQUIREMENT_DEPENDENCIES:
            rd = RequirementDependency(
                id=rd_d["id"],
                requirement_id=rd_d["requirement_id"],
                depends_on_id=rd_d["depends_on_id"],
                dependency_type=rd_d.get("dependency_type", "related"),
            )
            db.session.add(rd)
        print(f"   ✅ {len(REQUIREMENT_DEPENDENCIES)} requirement dependencies")

        # 21l. Open item comments
        for cm_d in OPEN_ITEM_COMMENTS:
            cm = OpenItemComment(
                id=cm_d["id"],
                open_item_id=cm_d["open_item_id"],
                user_id=cm_d.get("user_id"),
                type=cm_d.get("type", "comment"),
                content=cm_d.get("content", ""),
            )
            db.session.add(cm)
        print(f"   ✅ {len(OPEN_ITEM_COMMENTS)} open item comments")

        # ── 22. DATA FACTORY ────────────────────────────────────────────
        print("\n🏭 Creating Data Factory data...")
        obj_objs = []
        for do_d in DATA_OBJECTS:
            dobj = DataObject(
                program_id=pid,
                name=do_d["name"], description=do_d.get("description"),
                source_system=do_d["source_system"],
                target_table=do_d.get("target_table"),
                record_count=do_d.get("record_count", 0),
                quality_score=do_d.get("quality_score"),
                status=do_d.get("status", "draft"),
                owner=do_d.get("owner"),
            )
            db.session.add(dobj)
            obj_objs.append(dobj)
        db.session.flush()
        print(f"   ✅ {len(DATA_OBJECTS)} data objects")

        wave_objs = []
        for w_d in MIGRATION_WAVES:
            wave = MigrationWave(
                program_id=pid,
                wave_number=w_d["wave_number"], name=w_d["name"],
                description=w_d.get("description"),
                planned_start=_d(w_d.get("planned_start")),
                planned_end=_d(w_d.get("planned_end")),
                status=w_d.get("status", "planned"),
            )
            db.session.add(wave)
            wave_objs.append(wave)
        db.session.flush()
        print(f"   ✅ {len(MIGRATION_WAVES)} migration waves")

        ct_count = 0
        for ct_d in CLEANSING_TASKS:
            idx = ct_d["obj_index"]
            if idx < len(obj_objs):
                ct = CleansingTask(
                    data_object_id=obj_objs[idx].id,
                    rule_type=ct_d["rule_type"],
                    rule_expression=ct_d["rule_expression"],
                    description=ct_d.get("description"),
                    pass_count=ct_d.get("pass_count"),
                    fail_count=ct_d.get("fail_count"),
                    status=ct_d.get("status", "pending"),
                )
                db.session.add(ct)
                ct_count += 1
        print(f"   ✅ {ct_count} cleansing tasks")

        lc_objs = []
        for lc_d in LOAD_CYCLES:
            oi = lc_d["obj_index"]
            wi = lc_d["wave_index"]
            if oi < len(obj_objs) and wi < len(wave_objs):
                lc = LoadCycle(
                    data_object_id=obj_objs[oi].id,
                    wave_id=wave_objs[wi].id,
                    environment=lc_d["env"],
                    load_type=lc_d["type"],
                    records_loaded=lc_d.get("loaded"),
                    records_failed=lc_d.get("failed"),
                    status=lc_d.get("status", "pending"),
                    error_log=lc_d.get("error_log"),
                )
                db.session.add(lc)
                lc_objs.append(lc)
        db.session.flush()
        print(f"   ✅ {len(lc_objs)} load cycles")

        rc_count = 0
        for rc_d in RECONCILIATIONS:
            ci = rc_d["cycle_index"]
            if ci < len(lc_objs):
                src = rc_d["source"]
                tgt = rc_d["target"]
                variance = src - tgt
                vpct = round(abs(variance) / src * 100, 2) if src else 0
                rc = Reconciliation(
                    load_cycle_id=lc_objs[ci].id,
                    source_count=src, target_count=tgt,
                    match_count=rc_d["match"],
                    variance=variance, variance_pct=vpct,
                    status=rc_d.get("status", "pending"),
                    notes=rc_d.get("notes"),
                )
                db.session.add(rc)
                rc_count += 1
        print(f"   ✅ {rc_count} reconciliations")

        # ── 23. INTEGRATION FACTORY ────────────────────────────────────
        print("\n🔌 Creating Integration Factory data...")
        int_wave_map = {}
        for i, w_data in enumerate(INT_WAVES):
            wave = IntWave(
                program_id=pid,
                name=w_data["name"],
                status=w_data["status"],
                order=w_data.get("order", i),
                planned_start=_d(w_data.get("planned_start")),
                planned_end=_d(w_data.get("planned_end")),
            )
            db.session.add(wave)
            db.session.flush()
            int_wave_map[i] = wave.id
        print(f"   ✅ {len(INT_WAVES)} waves")

        for if_data in INT_INTERFACES:
            wave_idx = if_data["wave_index"]
            iface = Interface(
                program_id=pid,
                wave_id=int_wave_map[wave_idx],
                code=if_data["code"],
                name=if_data["name"],
                source_system=if_data["source_system"],
                target_system=if_data["target_system"],
                protocol=if_data["protocol"],
                frequency=if_data["frequency"],
                direction=if_data["direction"],
                status=if_data["status"],
                module=if_data["module"],
                priority=if_data["priority"],
            )
            db.session.add(iface)
        db.session.flush()
        print(f"   ✅ {len(INT_INTERFACES)} interfaces")

        # ── 15. Governance alerts & escalation demo ──────────────────────
        print("15. Governance & Escalation Alerts")
        from app.services.escalation import EscalationService
        from app.services.governance_rules import GovernanceRules, THRESHOLDS

        # Run escalation engine — creates alert notifications from live data
        esc_result = EscalationService.check_and_alert(pid, commit=False)
        gov_alert_count = esc_result.get("alerts_generated", 0)

        # Seed example governance threshold snapshot as a notification
        threshold_summary = Notification(
            program_id=pid,
            recipient="governance_dashboard",
            title="Governance Thresholds Active",
            message=(
                f"Governance thresholds configured: "
                f"P1 OI max={THRESHOLDS['ws_complete_max_open_p1_oi']}, "
                f"Gap warning={THRESHOLDS['gap_ratio_warn_pct']}%, "
                f"Req coverage warn={THRESHOLDS['req_coverage_warn_pct']}%, "
                f"OI aging escalation={THRESHOLDS['oi_aging_escalate_days']}d"
            ),
            category="gate",
            severity="info",
            entity_type="governance",
        )
        db.session.add(threshold_summary)
        db.session.flush()
        print(f"   ✅ {gov_alert_count} escalation alerts + 1 threshold snapshot")

        # ── 16. Audit demo data (WR-2.6) ─────────────────────────────────
        print("16. Audit Demo Data")
        from app.models.audit import write_audit

        audit_count = 0

        # Simulate requirement lifecycle audit trail for first few explore reqs
        demo_actions = [
            ("requirement", "requirement.submit_for_review", {"status": {"old": "draft", "new": "under_review"}}),
            ("requirement", "requirement.approve", {"status": {"old": "under_review", "new": "approved"}, "approved_by": {"old": None, "new": "Ahmet Yilmaz"}}),
            ("requirement", "requirement.push_to_alm", {"status": {"old": "approved", "new": "in_backlog"}}),
        ]
        for ereq in EXPLORE_REQS[:3]:
            for etype, act, diff in demo_actions:
                write_audit(
                    entity_type=etype,
                    entity_id=ereq["id"],
                    action=act,
                    actor="seed-user",
                    program_id=pid,
                    diff=diff,
                )
                audit_count += 1

        # Simulate OI lifecycle audit trail
        oi_actions = [
            ("open_item", "open_item.start_progress", {"status": {"old": "open", "new": "in_progress"}}),
            ("open_item", "open_item.close", {"status": {"old": "in_progress", "new": "closed"}, "resolution": {"old": None, "new": "Resolved in workshop"}}),
        ]
        for eoi in EXPLORE_OI[:2]:
            for etype, act, diff in oi_actions:
                write_audit(
                    entity_type=etype,
                    entity_id=eoi["id"],
                    action=act,
                    actor="seed-user",
                    program_id=pid,
                    diff=diff,
                )
                audit_count += 1

        # Simulate workshop audit
        for ews in EXPLORE_WORKSHOPS[:2]:
            write_audit(
                entity_type="workshop",
                entity_id=ews["id"],
                action="workshop.complete",
                actor="facilitator-1",
                program_id=pid,
                diff={"status": {"old": "in_progress", "new": "completed"}},
            )
            audit_count += 1

        # Simulate AI audit
        write_audit(
            entity_type="ai_call",
            entity_id="demo-ai-1",
            action="ai.llm_call",
            actor="system",
            program_id=pid,
            diff={
                "prompt_name": "requirement_analyst",
                "model": "gemini-2.0-flash",
                "tokens_used": 1250,
                "cost_usd": 0.00125,
                "success": True,
            },
        )
        audit_count += 1

        print(f"   ✅ {audit_count} audit log entries")

        # ── Cutover Hub ──────────────────────────────────────────────────
        print("\n🚀 Creating cutover hub data...")
        cut_plan_map = {}  # _key → CutoverPlan
        for cp_data in CUTOVER_PLANS:
            key = cp_data.pop("_key")
            plan = CutoverPlan(program_id=pid, **cp_data)
            db.session.add(plan)
            db.session.flush()
            cut_plan_map[key] = plan
            cp_data["_key"] = key  # restore
            _p(f"   📋 Plan: {plan.code} — {plan.name} [{plan.status}]", verbose)
        print(f"   ✅ {len(CUTOVER_PLANS)} cutover plans")

        cut_si_map = {}  # _key → CutoverScopeItem
        for si_data in CUT_SCOPE_ITEMS:
            plan_key = si_data.pop("_plan")
            si_key = si_data.pop("_key")
            si = CutoverScopeItem(cutover_plan_id=cut_plan_map[plan_key].id, **si_data)
            db.session.add(si)
            db.session.flush()
            cut_si_map[si_key] = si
            si_data["_plan"] = plan_key
            si_data["_key"] = si_key
            _p(f"   📦 Scope Item: {si.name} [{si.category}]", verbose)
        print(f"   ✅ {len(CUT_SCOPE_ITEMS)} scope items")

        cut_task_map = {}  # _key → RunbookTask
        for t_data in RUNBOOK_TASKS:
            scope_key = t_data.pop("_scope")
            t_key = t_data.pop("_key")
            task = RunbookTask(scope_item_id=cut_si_map[scope_key].id, **t_data)
            db.session.add(task)
            db.session.flush()
            cut_task_map[t_key] = task
            t_data["_scope"] = scope_key
            t_data["_key"] = t_key
            _p(f"   🔧 Task: [{task.sequence:03d}] {task.title[:50]} [{task.status}]", verbose)
        print(f"   ✅ {len(RUNBOOK_TASKS)} runbook tasks")

        dep_count = 0
        for d_data in TASK_DEPENDENCIES:
            pred_key = d_data.pop("_pred")
            succ_key = d_data.pop("_succ")
            dep = TaskDependency(
                predecessor_id=cut_task_map[pred_key].id,
                successor_id=cut_task_map[succ_key].id,
                **d_data,
            )
            db.session.add(dep)
            dep_count += 1
            d_data["_pred"] = pred_key
            d_data["_succ"] = succ_key
        db.session.flush()
        print(f"   ✅ {dep_count} task dependencies")

        for r_data in REHEARSALS:
            plan_key = r_data.pop("_plan")
            r = Rehearsal(cutover_plan_id=cut_plan_map[plan_key].id, **r_data)
            db.session.add(r)
            r_data["_plan"] = plan_key
            _p(f"   🔄 Rehearsal: {r.name} [{r.status}]", verbose)
        db.session.flush()
        print(f"   ✅ {len(REHEARSALS)} rehearsals")

        for g_data in GO_NO_GO_ITEMS:
            plan_key = g_data.pop("_plan")
            g = GoNoGoItem(cutover_plan_id=cut_plan_map[plan_key].id, **g_data)
            db.session.add(g)
            g_data["_plan"] = plan_key
        db.session.flush()
        print(f"   ✅ {len(GO_NO_GO_ITEMS)} go/no-go items")

        for inc_data in HYPERCARE_INCIDENTS:
            plan_key = inc_data.pop("_plan")
            inc = HypercareIncident(
                cutover_plan_id=cut_plan_map[plan_key].id,
                tenant_id=anadolu_tenant.id,
                **inc_data,
            )
            db.session.add(inc)
            inc_data["_plan"] = plan_key
            _p(f"   🏥 Incident: {inc.code} [{inc.severity}] {inc.title[:40]}", verbose)
        db.session.flush()
        print(f"   ✅ {len(HYPERCARE_INCIDENTS)} hypercare incidents")

        for sla_data in SLA_TARGETS:
            plan_key = sla_data.pop("_plan")
            sla = HypercareSLA(cutover_plan_id=cut_plan_map[plan_key].id, **sla_data)
            db.session.add(sla)
            sla_data["_plan"] = plan_key
        db.session.flush()
        print(f"   ✅ {len(SLA_TARGETS)} SLA targets")

        # FDD-B03-Phase-3: War Rooms
        wr_map = {}  # _key → HypercareWarRoom
        inc_code_map = {}  # code → HypercareIncident
        for inc in HypercareIncident.query.filter_by(tenant_id=anadolu_tenant.id).all():
            inc_code_map[inc.code] = inc

        for wr_data in WAR_ROOMS:
            plan_key = wr_data.pop("_plan")
            wr_key = wr_data.pop("_key")
            assign_incs = wr_data.pop("_assign_incidents", [])
            assign_crs = wr_data.pop("_assign_crs", [])
            wr = HypercareWarRoom(
                cutover_plan_id=cut_plan_map[plan_key].id,
                tenant_id=anadolu_tenant.id,
                **wr_data,
            )
            db.session.add(wr)
            db.session.flush()
            wr_map[wr_key] = wr
            wr_data["_plan"] = plan_key
            wr_data["_key"] = wr_key
            wr_data["_assign_incidents"] = assign_incs
            wr_data["_assign_crs"] = assign_crs
            # Assign incidents to this war room
            for inc_code in assign_incs:
                inc_obj = inc_code_map.get(inc_code)
                if inc_obj:
                    inc_obj.war_room_id = wr.id
            _p(f"   🏠 War Room: {wr.code} — {wr.name} [{wr.status}]", verbose)
        db.session.flush()
        print(f"   ✅ {len(WAR_ROOMS)} war rooms")

        # FDD-B03-Phase-3: Post Go-Live Change Requests
        cr_map = {}  # _key → PostGoliveChangeRequest
        for cr_data in CHANGE_REQUESTS:
            plan_key = cr_data.pop("_plan")
            cr_key = cr_data.pop("_key")
            plan = cut_plan_map[plan_key]
            cr_number = cr_data.pop("cr_number")
            title = cr_data.pop("title")
            description = cr_data.pop("description", None)
            category = cr_data.pop("category", "config_change")
            priority = cr_data.pop("priority", "P3")
            status = cr_data.pop("status", "draft")
            impact = cr_data.pop("impact_assessment", None)
            # Pop non-model fields to avoid passing them
            cr_data.pop("requested_by", None)
            cr_data.pop("assigned_to", None)
            cr_data.pop("requested_at", None)
            cr_data.pop("module", None)
            cr = PostGoliveChangeRequest(
                program_id=plan.program_id,
                tenant_id=anadolu_tenant.id,
                cr_number=cr_number,
                title=title,
                description=description,
                change_type=category,
                priority=priority,
                status=status,
                impact_assessment=impact,
            )
            db.session.add(cr)
            db.session.flush()
            cr_map[cr_key] = cr
            # Restore seed data dict keys for idempotency
            cr_data["_plan"] = plan_key
            cr_data["_key"] = cr_key
            cr_data["cr_number"] = cr_number
            cr_data["title"] = title
            cr_data["description"] = description
            cr_data["category"] = category
            cr_data["priority"] = priority
            cr_data["status"] = status
            cr_data["impact_assessment"] = impact
            _p(f"   📝 CR: {cr.cr_number} — {cr.title[:40]} [{cr.status}]", verbose)
        db.session.flush()

        # Assign CRs to war rooms (from WAR_ROOMS._assign_crs)
        for wr_data in WAR_ROOMS:
            wr_key = wr_data["_key"]
            wr_obj = wr_map.get(wr_key)
            if wr_obj:
                for cr_key in wr_data.get("_assign_crs", []):
                    cr_obj = cr_map.get(cr_key)
                    if cr_obj:
                        cr_obj.war_room_id = wr_obj.id
        db.session.flush()
        print(f"   ✅ {len(CHANGE_REQUESTS)} change requests")

        # FDD-B03-Phase-2: Seed exit criteria and escalation rules for Plan 1
        _exit_criteria_count = 0
        _escalation_rules_count = 0
        try:
            from app.models.run_sustain import HypercareExitCriteria
            from app.models.cutover import EscalationRule, seed_default_escalation_rules

            plan1 = cut_plan_map.get("plan1")
            if plan1:
                # Seed exit criteria (uses service helper data)
                from app.services.hypercare_service import _STANDARD_EXIT_CRITERIA
                for spec in _STANDARD_EXIT_CRITERIA:
                    ec = HypercareExitCriteria(
                        tenant_id=anadolu_tenant.id,
                        cutover_plan_id=plan1.id,
                        **spec,
                    )
                    db.session.add(ec)
                    _exit_criteria_count += 1
                db.session.flush()

                # Seed escalation rules
                esc_rules = seed_default_escalation_rules(plan1.id, tenant_id=anadolu_tenant.id)
                _escalation_rules_count = len(esc_rules)
                db.session.flush()

            print(f"   ✅ {_exit_criteria_count} exit criteria + {_escalation_rules_count} escalation rules")
        except Exception as e:
            print(f"   ⚠️ Phase-2 seed skipped: {e}")

        cutover_total = (len(CUTOVER_PLANS) + len(CUT_SCOPE_ITEMS) + len(RUNBOOK_TASKS)
                         + dep_count + len(REHEARSALS) + len(GO_NO_GO_ITEMS)
                         + len(HYPERCARE_INCIDENTS) + len(SLA_TARGETS)
                         + len(WAR_ROOMS) + len(CHANGE_REQUESTS)
                         + _exit_criteria_count + _escalation_rules_count)
        print(f"   🚀 Cutover Hub total: {cutover_total} records")

        # ── Commit ───────────────────────────────────────────────────────
        db.session.commit()

        # ── Summary ──────────────────────────────────────────────────────
        total = (1 + len(PHASES) + gate_count + len(WORKSTREAMS) + len(TEAM_MEMBERS)
                 + len(COMMITTEES) + len(SCENARIOS) + total_workshops + proc_count + an_count
                 + len(REQUIREMENTS) + trace_count + rpm_count + oi_count
                 + len(SPRINTS) + len(BACKLOG_ITEMS) + len(CONFIG_ITEMS)
                 + len(FS_DATA) + len(TS_DATA)
                 + len(TEST_PLAN_DATA) + len(cycle_objs) + len(TEST_CASE_DATA)
                 + len(SUITE_DATA) + step_count + cs_count
                 + exec_count + len(DEFECT_DATA)
                 + len(RISK_DATA) + len(ACTION_DATA) + len(ISSUE_DATA) + len(DECISION_DATA)
                 + len(EXPLORE_LEVELS) + len(EXPLORE_WORKSHOPS)
                 + len(WORKSHOP_SCOPE_ITEMS) + len(WORKSHOP_ATTENDEES)
                 + len(WORKSHOP_AGENDA_ITEMS) + len(EXPLORE_STEPS)
                 + len(EXPLORE_DECISIONS) + len(EXPLORE_OI)
                 + len(EXPLORE_REQS) + len(REQUIREMENT_OI_LINKS)
                 + len(REQUIREMENT_DEPENDENCIES) + len(OPEN_ITEM_COMMENTS)
                 + len(DATA_OBJECTS) + len(MIGRATION_WAVES)
                 + ct_count + len(lc_objs) + rc_count
                 + len(INT_WAVES) + len(INT_INTERFACES)
                 + audit_count
                 + cutover_total)
        print(f"\n{'='*60}")
        print(f"🎉 DEMO DATA SEED COMPLETE — {total} records")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    app = create_app()
    app.config["SEEDING"] = True
    print(f"🎯 DB: {app.config['SQLALCHEMY_DATABASE_URI']}\n")
    with app.app_context():
        db.create_all()
    seed_all(app, append=args.append, verbose=args.verbose)


if __name__ == "__main__":
    main()
