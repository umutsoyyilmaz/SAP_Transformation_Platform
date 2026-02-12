#!/usr/bin/env python3
"""
SAP Transformation Platform — Quick Demo Seed (OTC + PTP).

3-minute demo environment setup. Creates two focused business scenarios:
  - OTC (Order-to-Cash): SD module — quotation → order → delivery → billing
  - PTP (Procure-to-Pay):  MM module — PR → PO → GR → invoice → payment

Usage:
    python scripts/seed_quick_demo.py              # Full OTC+PTP demo
    python scripts/seed_quick_demo.py --scenario otc   # Only OTC
    python scripts/seed_quick_demo.py --scenario ptp   # Only PTP
    make seed-demo                                 # Reset DB + seed

Output: A program with complete explore workshops, requirements,
backlog items, test cases, defects, RAID items, and audit trail —
ready for a 10-minute partner demo.
"""

import argparse
import sys
import uuid
from datetime import date, datetime, time, timezone

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.program import Program, Phase, Gate, Workstream, TeamMember, Committee
from app.models.explore import (
    ProcessLevel, ExploreWorkshop, WorkshopScopeItem,
    WorkshopAttendee, WorkshopAgendaItem,
    ProcessStep, ExploreDecision, ExploreOpenItem,
    ExploreRequirement, RequirementOpenItemLink,
    ProjectRole,
)
from app.models.backlog import BacklogItem, ConfigItem, Sprint
from app.models.testing import (
    TestPlan, TestCycle, TestCase, TestExecution, Defect,
)
from app.models.raid import Risk, Action, Issue, Decision
from app.models.audit import AuditLog

_now = datetime.now(timezone.utc)
_uid = lambda: str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════════
# 1. PROGRAM & PHASES
# ═══════════════════════════════════════════════════════════════════════════

def seed_program():
    """Create the demo program with phases and gates."""
    p = Program(
        name="GlobalTech — S/4HANA Cloud Demo",
        description=(
            "GlobalTech Industries — SAP ECC → S/4HANA Cloud Public Edition "
            "greenfield transformation. 3,200 employees, 4 plants, €1.2B revenue. "
            "SD, MM, FI/CO, PP modules. SAP Activate methodology."
        ),
        project_type="greenfield",
        methodology="sap_activate",
        status="in_progress",
        priority="critical",
        sap_product="S/4HANA Cloud",
        deployment_option="cloud",
        start_date=date(2025, 6, 1),
        go_live_date=date(2026, 9, 30),
    )
    db.session.add(p)
    db.session.flush()

    # Phases with gates
    phases_data = [
        ("Discover", "completed", 100, date(2025, 6, 1), date(2025, 7, 15)),
        ("Prepare", "completed", 100, date(2025, 7, 16), date(2025, 9, 30)),
        ("Explore", "completed", 100, date(2025, 10, 1), date(2025, 12, 31)),
        ("Realize", "in_progress", 55, date(2026, 1, 6), date(2026, 5, 31)),
        ("Deploy", "planned", 0, date(2026, 6, 1), date(2026, 8, 31)),
        ("Run", "planned", 0, date(2026, 9, 1), date(2026, 9, 30)),
    ]
    for i, (name, status, pct, start, end) in enumerate(phases_data, 1):
        ph = Phase(
            program_id=p.id, name=name, order=i, status=status,
            completion_pct=pct,
            planned_start=start, planned_end=end,
            actual_start=start if status != "planned" else None,
        )
        db.session.add(ph)
        db.session.flush()

        gate_status = "passed" if status == "completed" else ("pending" if status == "in_progress" else "not_started")
        db.session.add(Gate(
            phase_id=ph.id, name=f"{name} Gate",
            gate_type="quality_gate", status=gate_status,
        ))

    # Workstreams
    for ws_name in ["FI/CO", "MM", "SD", "PP/QM", "Basis/Integration", "Data Migration", "Testing", "PMO"]:
        db.session.add(Workstream(program_id=p.id, name=ws_name, status="active"))

    # Team members (demo users matching role-nav)
    demo_team = [
        ("Ahmet Yılmaz", "pm", "ahmet.yilmaz@globaltech.com"),
        ("Elif Demir", "module_lead", "elif.demir@globaltech.com"),
        ("Canan Öztürk", "facilitator", "canan.ozturk@globaltech.com"),
        ("Burak Aydın", "bpo", "burak.aydin@globaltech.com"),
        ("Deniz Kaya", "tech_lead", "deniz.kaya@globaltech.com"),
        ("Selin Arslan", "tester", "selin.arslan@globaltech.com"),
        ("Murat Çelik", "module_lead", "murat.celik@globaltech.com"),
    ]
    for name, role, email in demo_team:
        db.session.add(TeamMember(program_id=p.id, name=name, role=role, email=email))
        db.session.add(ProjectRole(project_id=p.id, user_id=email.split("@")[0], role=role))

    # Committees
    db.session.add(Committee(program_id=p.id, name="Steering Committee", meeting_frequency="monthly"))
    db.session.add(Committee(program_id=p.id, name="PMO Weekly", meeting_frequency="weekly"))

    db.session.flush()
    return p


# ═══════════════════════════════════════════════════════════════════════════
# 2. EXPLORE PHASE — PROCESS HIERARCHY
# ═══════════════════════════════════════════════════════════════════════════

def seed_process_hierarchy(pid):
    """Create Signavio-style L1→L4 process hierarchy."""
    levels = {}

    # L1: Enterprise
    l1 = ProcessLevel(
        id=_uid(), project_id=pid, level=1,
        name="GlobalTech Enterprise Processes", code="ENT",
        scope_status="in_scope",
    )
    db.session.add(l1)
    levels["ENT"] = l1

    # L2: Areas
    l2_data = [
        ("OTC", "Order to Cash", "SD"),
        ("PTP", "Procure to Pay", "MM"),
        ("FIN", "Finance & Controlling", "FI"),
        ("P2M", "Plan to Manufacture", "PP"),
    ]
    for code, name, area in l2_data:
        l2 = ProcessLevel(
            id=_uid(), project_id=pid, level=2, parent_id=l1.id,
            name=name, code=code, scope_status="in_scope", process_area_code=area,
        )
        db.session.add(l2)
        levels[code] = l2

    db.session.flush()

    # L3/L4: Detailed processes for OTC and PTP
    otc_processes = {
        "OTC-10": ("Sales Inquiry & Quotation", [
            ("OTC-10-01", "Create Sales Inquiry"),
            ("OTC-10-02", "Create Quotation"),
            ("OTC-10-03", "Quotation Approval"),
        ]),
        "OTC-20": ("Sales Order Processing", [
            ("OTC-20-01", "Create Sales Order"),
            ("OTC-20-02", "Credit Check"),
            ("OTC-20-03", "ATP Check"),
            ("OTC-20-04", "Order Confirmation"),
        ]),
        "OTC-30": ("Delivery & Shipping", [
            ("OTC-30-01", "Create Outbound Delivery"),
            ("OTC-30-02", "Pick & Pack"),
            ("OTC-30-03", "Post Goods Issue"),
        ]),
        "OTC-40": ("Billing & Revenue", [
            ("OTC-40-01", "Create Billing Document"),
            ("OTC-40-02", "Revenue Recognition"),
            ("OTC-40-03", "Customer Payment"),
        ]),
    }

    ptp_processes = {
        "PTP-10": ("Purchase Requisition", [
            ("PTP-10-01", "Create Purchase Requisition"),
            ("PTP-10-02", "PR Approval Workflow"),
        ]),
        "PTP-20": ("Procurement", [
            ("PTP-20-01", "Create Purchase Order"),
            ("PTP-20-02", "PO Release Strategy"),
            ("PTP-20-03", "Vendor Selection"),
        ]),
        "PTP-30": ("Goods Receipt", [
            ("PTP-30-01", "Post Goods Receipt"),
            ("PTP-30-02", "Quality Inspection"),
            ("PTP-30-03", "Stock Posting"),
        ]),
        "PTP-40": ("Invoice & Payment", [
            ("PTP-40-01", "Invoice Verification"),
            ("PTP-40-02", "3-Way Match"),
            ("PTP-40-03", "Payment Run"),
        ]),
    }

    all_l4 = {}
    for parent_code, processes in [("OTC", otc_processes), ("PTP", ptp_processes)]:
        parent = levels[parent_code]
        area = "SD" if parent_code == "OTC" else "MM"
        for l3_code, (l3_name, l4_list) in processes.items():
            l3 = ProcessLevel(
                id=_uid(), project_id=pid, level=3, parent_id=parent.id,
                name=l3_name, code=l3_code, scope_status="in_scope", process_area_code=area,
            )
            db.session.add(l3)
            db.session.flush()
            levels[l3_code] = l3

            for l4_code, l4_name in l4_list:
                l4 = ProcessLevel(
                    id=_uid(), project_id=pid, level=4, parent_id=l3.id,
                    name=l4_name, code=l4_code, scope_status="in_scope", process_area_code=area,
                )
                db.session.add(l4)
                all_l4[l4_code] = l4

    db.session.flush()
    return levels, all_l4


# ═══════════════════════════════════════════════════════════════════════════
# 3. EXPLORE WORKSHOPS
# ═══════════════════════════════════════════════════════════════════════════

def seed_workshops(pid, levels, all_l4, scenario="all"):
    """Create Fit-to-Standard workshops with scope items, decisions, etc."""
    workshops = []
    process_steps = []

    ws_defs = [
        {
            "area": "SD", "parent": "OTC",
            "name": "OTC Fit-to-Standard — Sales & Delivery",
            "code": "WS-SD-01", "wave": "Wave 1",
            "status": "completed",
            "l3_codes": ["OTC-10", "OTC-20", "OTC-30", "OTC-40"],
            "attendees": [
                ("elif.demir", "Elif Demir", "Module Lead"),
                ("burak.aydin", "Burak Aydın", "BPO"),
                ("canan.ozturk", "Canan Öztürk", "Facilitator"),
                ("ahmet.yilmaz", "Ahmet Yılmaz", "PM"),
            ],
        },
        {
            "area": "MM", "parent": "PTP",
            "name": "PTP Fit-to-Standard — Procurement",
            "code": "WS-MM-01", "wave": "Wave 1",
            "status": "completed",
            "l3_codes": ["PTP-10", "PTP-20", "PTP-30", "PTP-40"],
            "attendees": [
                ("murat.celik", "Murat Çelik", "Module Lead"),
                ("burak.aydin", "Burak Aydın", "BPO"),
                ("canan.ozturk", "Canan Öztürk", "Facilitator"),
                ("deniz.kaya", "Deniz Kaya", "Tech Lead"),
            ],
        },
    ]

    for wd in ws_defs:
        if scenario != "all" and scenario.upper() != wd["parent"]:
            continue

        ws = ExploreWorkshop(
            id=_uid(), project_id=pid, name=wd["name"], code=wd["code"],
            process_area=wd["area"], status=wd["status"], wave=wd["wave"],
            type="fit_gap",
            started_at=_now, completed_at=_now,
        )
        db.session.add(ws)
        db.session.flush()
        workshops.append(ws)

        # Scope items (L3→workshop link)
        for i, l3_code in enumerate(wd["l3_codes"]):
            if l3_code in levels:
                db.session.add(WorkshopScopeItem(
                    workshop_id=ws.id, process_level_id=levels[l3_code].id,
                    sort_order=i,
                ))

        # Attendees
        for user_id, name, role in wd["attendees"]:
            db.session.add(WorkshopAttendee(
                workshop_id=ws.id, user_id=user_id, name=name, role=role,
            ))

        # Agenda
        agenda_times = [time(9, 0), time(9, 30), time(10, 0), time(10, 30), time(11, 0)]
        for i, item in enumerate(["Opening & Scope Review", "Standard Process Demo",
                                   "Fit-Gap Analysis", "Requirements Capture", "Wrap-up"]):
            db.session.add(WorkshopAgendaItem(
                id=_uid(), workshop_id=ws.id, title=item, sort_order=i,
                duration_minutes=30, time=agenda_times[i],
            ))

        # Process steps (from L4)
        step_idx = 0
        for l4_code, l4 in all_l4.items():
            if l4_code.startswith(wd["parent"]):
                ps = ProcessStep(
                    id=_uid(), workshop_id=ws.id, process_level_id=l4.id,
                    sort_order=step_idx, fit_decision="fit",
                )
                db.session.add(ps)
                process_steps.append(ps)
                step_idx += 1

    db.session.flush()
    return workshops, process_steps


# ═══════════════════════════════════════════════════════════════════════════
# 4. REQUIREMENTS + OPEN ITEMS + DECISIONS
# ═══════════════════════════════════════════════════════════════════════════

def seed_requirements(pid, workshops, process_steps):
    """Create requirements, open items, and decisions from workshops."""
    reqs = []

    otc_reqs = [
        ("Configurable Pricing Conditions", "functional", "P1", "approved", "SD",
         "Custom pricing determination with multi-level condition types beyond standard SAP."),
        ("Credit Management Integration", "functional", "P1", "in_backlog", "SD",
         "Real-time credit check integrated with FI credit management."),
        ("Output Determination — E-Invoice", "enhancement", "P2", "approved", "SD",
         "Turkey e-invoice (e-Fatura) integration via output determination."),
        ("Available-to-Promise Enhancement", "functional", "P2", "under_review", "SD",
         "ATP check with warehouse-level stock visibility."),
        ("Batch Delivery Processing", "enhancement", "P3", "draft", "SD",
         "Batch creation of deliveries from multiple sales orders."),
    ]

    ptp_reqs = [
        ("Vendor Evaluation Scorecard", "functional", "P1", "approved", "MM",
         "Automated vendor performance scoring based on delivery, quality, price."),
        ("3-Way Match Tolerance Config", "functional", "P1", "in_backlog", "MM",
         "Configurable tolerance groups for GR/PO/invoice matching."),
        ("Automated PR Approval Workflow", "enhancement", "P2", "approved", "MM",
         "Multi-level PR approval based on cost center and amount thresholds."),
        ("Consignment Stock Management", "functional", "P2", "under_review", "MM",
         "Vendor consignment stock handling with settlement processing."),
        ("RFQ to Contract Automation", "enhancement", "P3", "draft", "MM",
         "Automated RFQ creation and evaluation with award to outline agreement."),
    ]

    ws_map = {ws.process_area: ws for ws in workshops}
    seq = 0

    for area_reqs, area in [(otc_reqs, "SD"), (ptp_reqs, "MM")]:
        ws = ws_map.get(area)
        for title, rtype, priority, status, proc_area, desc in area_reqs:
            seq += 1
            r = ExploreRequirement(
                id=_uid(), project_id=pid,
                code=f"REQ-{seq:03d}",
                title=title, description=desc,
                type=rtype, priority=priority, status=status,
                process_area=proc_area,
                workshop_id=ws.id if ws else None,
                created_by_id="canan.ozturk",
                created_by_name="Canan Öztürk",
            )
            db.session.add(r)
            reqs.append(r)

    db.session.flush()

    # Open items
    ois = []
    oi_data = [
        ("Pricing Condition Migration", "data_migration", "P1", "in_progress", "SD"),
        ("E-Invoice Legal Compliance Check", "clarification", "P1", "open", "SD"),
        ("Vendor Master Data Cleanup", "data_migration", "P2", "open", "MM"),
        ("PO Release Strategy Definition", "clarification", "P2", "resolved", "MM"),
    ]
    for i, (title, cat, priority, status, area) in enumerate(oi_data, 1):
        oi = ExploreOpenItem(
            id=_uid(), project_id=pid,
            code=f"OI-{i:03d}",
            title=title, category=cat, priority=priority, status=status,
            process_area=area,
            created_by_id="canan.ozturk",
        )
        db.session.add(oi)
        ois.append(oi)

    # Decisions
    dec_data = [
        ("Use SAP standard pricing engine with custom condition tables", "approved"),
        ("E-invoice via output determination + TÜRK.NET integration", "approved"),
        ("Adopt SAP standard 3-way match with custom tolerance groups", "approved"),
        ("PR approval workflow via SAP BTP Workflow Management", "pending"),
    ]
    for i, (desc, status) in enumerate(dec_data, 1):
        step_id = process_steps[i - 1].id if i <= len(process_steps) else process_steps[0].id
        db.session.add(ExploreDecision(
            id=_uid(), project_id=pid,
            process_step_id=step_id,
            code=f"DEC-{i:03d}",
            text=desc, status=status,
            category="design", decided_by="Steering Committee",
        ))

    # Link OIs to requirements
    if ois and reqs:
        db.session.add(RequirementOpenItemLink(
            requirement_id=reqs[0].id, open_item_id=ois[0].id,
        ))
        db.session.add(RequirementOpenItemLink(
            requirement_id=reqs[5].id, open_item_id=ois[2].id,
        ))

    db.session.flush()
    return reqs, ois


# ═══════════════════════════════════════════════════════════════════════════
# 5. BACKLOG (WRICEF) + CONFIG ITEMS
# ═══════════════════════════════════════════════════════════════════════════

def seed_backlog(pid, reqs):
    """Create backlog items (WRICEF) from converted requirements."""
    sprint = Sprint(program_id=pid, name="Sprint 1 — Realize Phase", status="active")
    db.session.add(sprint)
    db.session.flush()

    items = []
    wricef_data = [
        (reqs[0], "enhancement", "ENH-001", "Pricing Condition Enhancement", "in_progress"),
        (reqs[1], "interface", "INT-001", "FI Credit Management Integration", "open"),
        (reqs[2], "enhancement", "ENH-002", "E-Invoice Output Integration", "in_progress"),
        (reqs[5], "report", "RPT-001", "Vendor Evaluation Dashboard", "open"),
        (reqs[6], "enhancement", "ENH-003", "3-Way Match Config Objects", "in_progress"),
        (reqs[7], "workflow", "WFL-001", "PR Approval Workflow", "open"),
    ]

    for req, wtype, code, title, status in wricef_data:
        bi = BacklogItem(
            program_id=pid, title=title, code=code,
            status=status, wricef_type=wtype,
            sprint_id=sprint.id,
            explore_requirement_id=req.id,
            priority=req.priority,
        )
        db.session.add(bi)
        items.append(bi)

    # Config items
    cfg_data = [
        ("CFG-001", "SD Pricing Procedure Config", "in_progress"),
        ("CFG-002", "Credit Control Area Config", "open"),
        ("CFG-003", "MM Tolerance Group Config", "in_progress"),
        ("CFG-004", "Vendor Evaluation Criteria Config", "open"),
    ]
    for code, title, status in cfg_data:
        db.session.add(ConfigItem(
            program_id=pid, title=title, code=code, status=status,
        ))

    db.session.flush()
    return items


# ═══════════════════════════════════════════════════════════════════════════
# 6. TESTING — Plans, Cases, Executions, Defects
# ═══════════════════════════════════════════════════════════════════════════

def seed_testing(pid, reqs, backlog_items):
    """Create test plan, cases, executions, and defects."""
    plan = TestPlan(program_id=pid, name="SIT Cycle 1 — OTC + PTP", status="active")
    db.session.add(plan)
    db.session.flush()

    cycle = TestCycle(plan_id=plan.id, name="SIT Cycle 1", status="in_progress",
                      test_layer="sit")
    db.session.add(cycle)
    db.session.flush()

    # Test cases covering requirements
    tc_data = [
        ("TC-SD-001", "End-to-End Sales Order", "ready", "SD", reqs[0]),
        ("TC-SD-002", "Credit Check Blocking", "ready", "SD", reqs[1]),
        ("TC-SD-003", "E-Invoice Generation", "ready", "SD", reqs[2]),
        ("TC-SD-004", "ATP Availability Check", "draft", "SD", reqs[3]),
        ("TC-MM-001", "Purchase Requisition Flow", "ready", "MM", reqs[5]),
        ("TC-MM-002", "3-Way Match Validation", "ready", "MM", reqs[6]),
        ("TC-MM-003", "PR Approval Workflow", "ready", "MM", reqs[7]),
        ("TC-MM-004", "Consignment Settlement", "draft", "MM", reqs[8]),
        ("TC-INT-001", "Credit Integration E2E", "ready", "FI", reqs[1]),
        ("TC-REG-001", "Pricing Regression Suite", "approved", "SD", reqs[0]),
    ]
    test_cases = []
    for code, title, status, module, req in tc_data:
        tc = TestCase(
            program_id=pid, code=code, title=title, status=status,
            module=module, test_layer="sit",
            explore_requirement_id=req.id,
            backlog_item_id=backlog_items[0].id if backlog_items else None,
        )
        db.session.add(tc)
        test_cases.append(tc)

    db.session.flush()

    # Executions (mix of pass/fail/blocked)
    results = ["pass", "pass", "fail", "pass", "pass", "fail", "pass", "blocked"]
    for i, tc in enumerate(test_cases[:8]):
        db.session.add(TestExecution(
            cycle_id=cycle.id, test_case_id=tc.id,
            result=results[i],
            executed_by="selin.arslan",
            executed_at=_now,
        ))

    db.session.flush()

    # Defects from failed tests
    defect_data = [
        ("DEF-001", "Pricing Rounding Error", "S2", "open", test_cases[2]),
        ("DEF-002", "3-Way Match False Reject", "S2", "in_progress", test_cases[5]),
        ("DEF-003", "Credit Check Timeout", "S1", "open", test_cases[8]),
    ]
    defects = []
    for code, title, severity, status, tc in defect_data:
        d = Defect(
            program_id=pid, code=code, title=title,
            severity=severity, status=status,
            test_case_id=tc.id,
        )
        db.session.add(d)
        defects.append(d)

    db.session.flush()
    return test_cases, defects


# ═══════════════════════════════════════════════════════════════════════════
# 7. RAID — Risks, Actions, Issues, Decisions
# ═══════════════════════════════════════════════════════════════════════════

def seed_raid(pid):
    """Create RAID items for the demo."""
    # Risks
    risks = [
        ("E-Invoice Compliance Delay", "high", "possible", "open",
         "Turkey e-invoice regulation changes may require additional config."),
        ("Data Migration Volume", "medium", "likely", "mitigating",
         "3M vendor/customer records may exceed migration window."),
        ("Key User Availability", "high", "possible", "open",
         "BPO availability during Ramadan period may be limited."),
    ]
    for i, (title, impact, likelihood, status, desc) in enumerate(risks, 1):
        db.session.add(Risk(
            program_id=pid, code=f"R-{i:03d}",
            title=title, description=desc,
            impact=impact, probability=likelihood, status=status,
            risk_category="technical" if i <= 2 else "resource",
            owner="ahmet.yilmaz",
        ))

    # Actions
    actions = [
        ("Schedule e-invoice compliance review with legal", "high", "open"),
        ("Prepare data migration dry-run plan", "medium", "in_progress"),
        ("Book key user calendar for April-May", "high", "completed"),
    ]
    for i, (title, priority, status) in enumerate(actions, 1):
        db.session.add(Action(
            program_id=pid, code=f"A-{i:03d}",
            title=title, priority=priority, status=status,
            owner="ahmet.yilmaz",
        ))

    # Issues
    db.session.add(Issue(
        program_id=pid, code="I-001",
        title="SAP BTP Workflow license pending approval",
        severity="high", status="open",
        owner="deniz.kaya",
    ))

    # Decisions (program-level, not explore-level)
    db.session.add(Decision(
        program_id=pid, code="D-001",
        title="Go with SAP Analytics Cloud for reporting",
        status="approved",
        decision_owner="Steering Committee", decision_date=date(2025, 12, 15),
    ))

    db.session.flush()


# ═══════════════════════════════════════════════════════════════════════════
# 8. AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════════

def seed_audit(pid):
    """Create sample audit entries for demo."""
    entries = [
        ("workshop.completed", "WS-SD-01 OTC workshop completed", "canan.ozturk"),
        ("workshop.completed", "WS-MM-01 PTP workshop completed", "canan.ozturk"),
        ("requirement.approved", "REQ-001 approved by steering committee", "ahmet.yilmaz"),
        ("requirement.converted", "REQ-001 → ENH-001 WRICEF created", "elif.demir"),
        ("requirement.approved", "REQ-006 Vendor Evaluation approved", "ahmet.yilmaz"),
        ("defect.created", "DEF-003 S1 Credit Check Timeout raised", "selin.arslan"),
        ("risk.created", "R-001 E-Invoice compliance risk escalated", "ahmet.yilmaz"),
    ]
    for action, desc, user in entries:
        db.session.add(AuditLog(
            program_id=pid, action=action,
            actor=user, entity_type="demo", entity_id="seed",
        ))
    db.session.flush()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def seed_demo(scenario="all"):
    """Run the full demo seed pipeline."""
    print("═" * 60)
    print("  SAP Platform — Quick Demo Seed")
    print(f"  Scenario: {scenario.upper()}")
    print("═" * 60)

    # 1. Program
    print("\n  1/8 Program & Phases...")
    p = seed_program()
    print(f"     ✅ Program: {p.name} (id={p.id})")

    # 2. Process hierarchy
    print("  2/8 Process Hierarchy (L1→L4)...")
    levels, all_l4 = seed_process_hierarchy(p.id)
    print(f"     ✅ {len(levels)} L1-L3, {len(all_l4)} L4 processes")

    # 3. Workshops
    print("  3/8 Explore Workshops...")
    workshops, process_steps = seed_workshops(p.id, levels, all_l4, scenario)
    print(f"     ✅ {len(workshops)} workshops (completed)")

    # 4. Requirements + OIs + Decisions
    print("  4/8 Requirements & Open Items...")
    reqs, ois = seed_requirements(p.id, workshops, process_steps)
    print(f"     ✅ {len(reqs)} requirements, {len(ois)} open items")

    # 5. Backlog
    print("  5/8 Backlog (WRICEF)...")
    backlog = seed_backlog(p.id, reqs)
    print(f"     ✅ {len(backlog)} WRICEF items")

    # 6. Testing
    print("  6/8 Testing...")
    tcs, defects = seed_testing(p.id, reqs, backlog)
    print(f"     ✅ {len(tcs)} test cases, {len(defects)} defects")

    # 7. RAID
    print("  7/8 RAID...")
    seed_raid(p.id)
    print("     ✅ 3 risks, 3 actions, 1 issue, 1 decision")

    # 8. Audit
    print("  8/8 Audit Trail...")
    seed_audit(p.id)
    print("     ✅ 7 audit entries")

    db.session.commit()

    print(f"\n{'═' * 60}")
    print(f"  🎉 DEMO SEED COMPLETE — Program ID: {p.id}")
    print(f"  Ready for: make run → http://localhost:5001")
    print(f"{'═' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="Quick Demo Seed (OTC + PTP)")
    parser.add_argument("--scenario", choices=["all", "otc", "ptp"], default="all",
                        help="Seed scenario (default: all)")
    parser.add_argument("--no-reset", action="store_true",
                        help="Don't clear existing data")
    args = parser.parse_args()

    app = create_app()
    print(f"  🎯 DB: {app.config['SQLALCHEMY_DATABASE_URI']}\n")

    with app.app_context():
        if not args.no_reset:
            db.drop_all()
            db.create_all()
            print("  ♻️  Database reset complete\n")

        seed_demo(scenario=args.scenario)


if __name__ == "__main__":
    main()
