#!/usr/bin/env python3
"""
SAP Transformation Platform — Anadolu Holding Demo Seed.

Realistic Turkish SAP transformation project: Anadolu Holding S/4HANA.
Brownfield approach, SD/MM/FI/CO modules, ~97 records.

Source: SEED_DATA_MANUAL_ENTRY.md

Usage:
    python scripts/seed_anadolu_demo.py              # Add to existing DB
    python scripts/seed_anadolu_demo.py --reset      # Reset DB and load
"""

import argparse
import sys
import uuid
from datetime import date, datetime, time, timezone

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.program import Program, Phase, Workstream, TeamMember
from app.models.scenario import Scenario
from app.models.scope import Process, Analysis
from app.models.explore import (
    ProcessLevel,
    ExploreWorkshop,
    WorkshopAttendee,
    WorkshopAgendaItem,
    ProcessStep,
    ExploreDecision,
    ExploreOpenItem,
    ExploreRequirement,
)
from app.models.backlog import BacklogItem, ConfigItem
from app.models.testing import TestPlan, TestCycle, TestCase, TestExecution
from app.models.raid import Risk, Action

_now = datetime.now(timezone.utc)
_uid = lambda: str(uuid.uuid4())

# ═══════════════════════════════════════════════════════════════════════════
# 1. PROGRAM & INFRA
# ═══════════════════════════════════════════════════════════════════════════

def seed_program():
    """Anadolu Holding S/4HANA Transformation program."""
    p = Program(
        name="Anadolu Holding S/4HANA Transformation",
        description=(
            "Anadolu Holding transformation project from existing ECC 6.0 system to S/4HANA. "
            "4 main modules in scope, planned for 12 months duration. "
            "Brownfield approach targeting migration to modern platform while preserving existing customizations."
        ),
        project_type="brownfield",
        methodology="sap_activate",
        status="active",
        priority="critical",
        sap_product="S/4HANA 2023 FPS02",
        deployment_option="on_premise",
        start_date=date(2026, 3, 1),
        end_date=date(2027, 3, 1),
        go_live_date=date(2027, 1, 15),
    )
    db.session.add(p)
    db.session.flush()

    # Phases
    phases = []
    for idx, (name, status, pct, sd, ed) in enumerate([
        ("Discover", "completed", 100, date(2026, 3, 1), date(2026, 3, 14)),
        ("Prepare", "completed", 100, date(2026, 3, 15), date(2026, 3, 31)),
        ("Explore", "in_progress", 35, date(2026, 4, 1), date(2026, 6, 30)),
        ("Realize", "planned", 0, date(2026, 7, 1), date(2026, 10, 31)),
        ("Deploy", "planned", 0, date(2026, 11, 1), date(2026, 12, 31)),
        ("Run", "planned", 0, date(2027, 1, 1), date(2027, 3, 1)),
    ]):
        ph = Phase(
            program_id=p.id, name=name, status=status,
            completion_pct=pct, planned_start=sd, planned_end=ed,
            order=idx,
        )
        db.session.add(ph)
        phases.append(ph)
    db.session.flush()

    # Workstreams
    ws_data = [
        ("SD — Sales & Distribution", "SD"),
        ("MM — Materials Management", "MM"),
        ("FI — Financial Accounting", "FI"),
        ("CO — Controlling", "CO"),
    ]
    workstreams = {}
    for ws_name, mod in ws_data:
        ws = Workstream(program_id=p.id, name=ws_name, ws_type="functional", status="active")
        db.session.add(ws)
        workstreams[mod] = ws
    db.session.flush()

    # Team Members
    members = [
        ("Ayse Demir", "project_lead", "ayse.demir@consulting.com"),
        ("Burak Kaya", "consultant", "burak.kaya@consulting.com"),
        ("Canan Ozturk", "stream_lead", "canan.ozturk@consulting.com"),
        ("Deniz Aksoy", "developer", "deniz.aksoy@consulting.com"),
        ("Mehmet Yilmaz", "team_member", "mehmet.yilmaz@anadoluholding.com.tr"),
    ]
    for mname, mrole, memail in members:
        tm = TeamMember(program_id=p.id, name=mname, role=mrole, email=memail)
        db.session.add(tm)
    db.session.flush()

    print(f"  ✅ Program: {p.name} (id={p.id})")
    print(f"  ✅ {len(phases)} phases, {len(workstreams)} workstreams, {len(members)} team members")
    return p, phases, workstreams


# ═══════════════════════════════════════════════════════════════════════════
# 2. SCENARIOS (5)
# ═══════════════════════════════════════════════════════════════════════════

def seed_scenarios(program):
    scenarios = {}
    data = [
        ("S-001", "Order to Cash", "SD", "order_to_cash", "in_analysis",
         "Covers the entire sales process from customer order to collection. Includes standard order, returns, credit/debit memo, ATP check, and billing. Referenced SAP Best Practice scope items 1YG, BD9."),
        ("S-002", "Procure to Pay", "MM", "procure_to_pay", "in_analysis",
         "Covers the entire procurement process from purchase requisition to supplier payment. Purchase requisition, purchase order, goods receipt, invoice verification, and payment. Referenced scope items J58, 2NM."),
        ("S-003", "Record to Report", "FI", "record_to_report", "draft",
         "Process from accounting entries to financial reporting. General ledger, accounts receivable/payable management, asset accounting, period-end closing, and reporting. Referenced scope items J77, BEV."),
        ("S-004", "Plan to Produce", "CO", "plan_to_produce", "draft",
         "Production planning and cost control scenario. Cost center accounting, internal orders, product costing, and profit/cost analysis. CO module focused."),
        ("S-005", "O2C + R2R Integration Test", "SD", "order_to_cash", "draft",
         "Sales invoice automatically creating FI accounting entry, reflecting in accounts receivable, and flowing to reporting. Cross-module integration test."),
    ]
    for code, name, mod, pa, status, desc in data:
        s = Scenario(
            program_id=program.id, name=name, description=desc,
            sap_module=mod, process_area=pa, status=status,
            priority="high" if status == "in_analysis" else "medium",
        )
        db.session.add(s)
        db.session.flush()
        scenarios[code] = s

    print(f"  ✅ {len(scenarios)} scenarios")
    return scenarios


# ═══════════════════════════════════════════════════════════════════════════
# 3. PROCESS HIERARCHY (L2/L3) & ANALYSES
# ═══════════════════════════════════════════════════════════════════════════

def seed_processes_and_analyses(program, scenarios):
    """Create L2/L3 process nodes + Analysis records."""
    processes = {}

    # L2 Process Areas
    l2_data = [
        ("S-001", "Sales & Distribution", "SD", "O2C"),
        ("S-002", "Procurement", "MM", "P2P"),
        ("S-003", "Financial Accounting", "FI", "R2R"),
        ("S-004", "Controlling", "CO", "P2Pr"),
    ]
    for sc_code, name, mod, proc_code in l2_data:
        p2 = Process(
            scenario_id=scenarios[sc_code].id,
            name=name, level="L2", module=mod,
            process_id_code=proc_code,
        )
        db.session.add(p2)
        db.session.flush()
        processes[f"{sc_code}_L2"] = p2

    # L3 Processes (for analysis targets)
    l3_data = [
        ("S-001", "Standard Sales Order Processing", "SD", "O2C-001", "S-001_L2"),
        ("S-001", "Billing & Credit Management", "SD", "O2C-002", "S-001_L2"),
        ("S-002", "Procurement & Goods Receipt", "MM", "P2P-001", "S-002_L2"),
        ("S-002", "Invoice Verification & Payment", "MM", "P2P-002", "S-002_L2"),
        ("S-003", "General Ledger & Closing", "FI", "R2R-001", "S-003_L2"),
    ]
    for sc_code, name, mod, proc_code, parent_key in l3_data:
        p3 = Process(
            scenario_id=scenarios[sc_code].id,
            parent_id=processes[parent_key].id,
            name=name, level="L3", module=mod,
            process_id_code=proc_code,
        )
        db.session.add(p3)
        db.session.flush()
        processes[proc_code] = p3

    # Analyses (4)
    analyses = {}
    anl_data = [
        ("ANL-001", "O2C Fit-to-Standard Workshop", "O2C-001", "workshop", "completed",
         "Comparison workshop of Order to Cash process against SAP Best Practice. SD module core processes reviewed. Attendees: SD consultants, sales manager, warehouse supervisor.",
         date(2026, 3, 15)),
        ("ANL-002", "O2C Gap Detail Analysis", "O2C-001", "fit_gap", "in_progress",
         "Detailed analysis of gaps identified in the workshop. Solution alternatives and effort estimates being prepared for each gap.",
         date(2026, 3, 22)),
        ("ANL-003", "P2P Fit-to-Standard Workshop", "P2P-001", "workshop", "completed",
         "Comparison workshop of Procure to Pay process against SAP Best Practice. MM module procurement processes reviewed.",
         date(2026, 3, 18)),
        ("ANL-004", "R2R Fit-to-Standard Workshop", "R2R-001", "workshop", "planned",
         "Comparison workshop of Record to Report process against SAP Best Practice. FI module accounting processes being planned.",
         date(2026, 4, 5)),
    ]
    for code, name, proc_code, atype, status, desc, adate in anl_data:
        a = Analysis(
            process_id=processes[proc_code].id,
            name=name, description=desc,
            analysis_type=atype, status=status, date=adate,
        )
        db.session.add(a)
        db.session.flush()
        analyses[code] = a

    print(f"  ✅ {len(processes)} processes (L2+L3), {len(analyses)} analyses")
    return processes, analyses


# ═══════════════════════════════════════════════════════════════════════════
# 4. EXPLORE WORKSHOPS (Sessions) + ProcessLevels
# ═══════════════════════════════════════════════════════════════════════════

def seed_workshops(program):
    """Create ExploreWorkshop sessions and ProcessLevel hierarchy."""

    # Process Levels (L1→L4)
    levels = {}
    level_map = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
    pl_data = [
        ("SD — Sales & Distribution", 1, "SD", "VC-SD", None),
        ("Sales Order Processing", 2, "SD", "PA-SD01", "VC-SD"),
        ("Standard Sales Order & Delivery", 3, "SD", "SD-001", "PA-SD01"),
        ("ATP Check", 4, "SD", "SD-001.01", "SD-001"),
        ("Delivery Split Logic", 4, "SD", "SD-001.02", "SD-001"),
        ("Pricing Procedure", 4, "SD", "SD-001.03", "SD-001"),
        ("Billing & Credit Management", 3, "SD", "SD-002", "PA-SD01"),
        ("Intercompany Billing", 4, "SD", "SD-002.01", "SD-002"),
        ("Credit Management", 4, "SD", "SD-002.02", "SD-002"),
        ("MM — Materials Management", 1, "MM", "VC-MM", None),
        ("Procurement", 2, "MM", "PA-MM01", "VC-MM"),
        ("Purchase Requisition & PO", 3, "MM", "MM-001", "PA-MM01"),
        ("PR Approval (Release Strategy)", 4, "MM", "MM-001.01", "MM-001"),
        ("Auto PO Creation", 4, "MM", "MM-001.02", "MM-001"),
        ("Goods Receipt & Inventory", 3, "MM", "MM-002", "PA-MM01"),
        ("GR Tolerance Check", 4, "MM", "MM-002.01", "MM-002"),
        ("Vendor Scoring", 4, "MM", "MM-002.02", "MM-002"),
        ("Consignment Reporting", 4, "MM", "MM-002.03", "MM-002"),
        ("FI — Financial Accounting", 1, "FI", "VC-FI", None),
        ("CO — Controlling", 1, "CO", "VC-CO", None),
    ]
    for pl_name, pl_level, mod, pl_code, parent_code in pl_data:
        parent_id = levels[parent_code].id if parent_code else None
        pl = ProcessLevel(
            id=_uid(), project_id=program.id,
            name=pl_name, level=pl_level,
            code=pl_code,
            process_area_code=mod,
            parent_id=parent_id,
        )
        db.session.add(pl)
        db.session.flush()
        levels[pl_code] = pl

    # Workshops (Sessions)
    workshops = {}
    ws_data = [
        ("SES-001", "O2C Workshop Day 1: Sales Order & Delivery", "SD",
         "fit_to_standard", "completed", date(2026, 3, 15), time(9, 0), time(13, 0),
         "Canan Ozturk"),
        ("SES-002", "O2C Workshop Day 2: Billing & Credit Management", "SD",
         "fit_to_standard", "completed", date(2026, 3, 16), time(9, 0), time(13, 0),
         "Canan Ozturk"),
        ("SES-003", "P2P Workshop Day 1: Procurement & Goods Receipt", "MM",
         "fit_to_standard", "completed", date(2026, 3, 18), time(9, 0), time(13, 0),
         "Fatih Korkmaz"),
        ("SES-004", "P2P Workshop Day 2: Invoice Verification & Payment", "MM",
         "fit_to_standard", "completed", date(2026, 3, 19), time(10, 0), time(13, 0),
         "Fatih Korkmaz"),
    ]
    for code, name, mod, wtype, status, wdate, st, et, fac in ws_data:
        w = ExploreWorkshop(
            id=_uid(), project_id=program.id,
            code=code, name=name, type=wtype, status=status,
            date=wdate, start_time=st, end_time=et,
            process_area=mod,
        )
        db.session.add(w)
        db.session.flush()
        workshops[code] = w

    print(f"  ✅ {len(levels)} process levels, {len(workshops)} workshops (sessions)")
    return workshops, levels


# ═══════════════════════════════════════════════════════════════════════════
# 5. ATTENDEES (9)
# ═══════════════════════════════════════════════════════════════════════════

def seed_attendees(workshops):
    att_data = {
        "SES-001": [
            ("Canan Ozturk", "Facilitator / SD Consultant", "consultant"),
            ("Mehmet Yilmaz", "Business Owner", "customer"),
            ("Elif Kara", "Key User - Sales", "customer"),
            ("Hasan Demir", "Key User - Logistics", "customer"),
            ("Burak Kaya", "Solution Architect", "consultant"),
        ],
        "SES-003": [
            ("Fatih Korkmaz", "Facilitator / MM Consultant", "consultant"),
            ("Aylin Sahin", "Key User - Purchasing", "customer"),
            ("Serkan Yildiz", "Key User - Warehouse", "customer"),
            ("Zehra Aydin", "Finance Representative", "customer"),
        ],
    }
    count = 0
    for ws_code, people in att_data.items():
        for name, role, org in people:
            a = WorkshopAttendee(
                id=_uid(), workshop_id=workshops[ws_code].id,
                name=name, role=role, organization=org,
                attendance_status="present",
            )
            db.session.add(a)
            count += 1
    db.session.flush()
    print(f"  ✅ {count} attendees")


# ═══════════════════════════════════════════════════════════════════════════
# 6. AGENDA ITEMS (13)
# ═══════════════════════════════════════════════════════════════════════════

def seed_agenda(workshops):
    agenda_data = {
        "SES-001": [
            (time(9, 0), "Project scope and workshop objective", 15, "session"),
            (time(9, 15), "SAP Best Practice: Standard Sales Order (1YG)", 45, "demo"),
            (time(10, 0), "Current process vs. SAP Standard comparison", 60, "discussion"),
            (time(11, 0), "ATP Check and Availability processes", 30, "session"),
            (time(11, 30), "Delivery & Shipping Point configuration", 30, "session"),
            (time(12, 0), "Gap identification and prioritization", 30, "discussion"),
            (time(12, 30), "Next steps and actions", 10, "wrap_up"),
        ],
        "SES-003": [
            (time(9, 0), "P2P process overview", 15, "session"),
            (time(9, 15), "SAP Best Practice: Basic Procurement (J58)", 45, "demo"),
            (time(10, 0), "Purchase requisition and approval process review", 45, "discussion"),
            (time(10, 45), "Goods receipt and warehouse processes", 30, "session"),
            (time(11, 15), "Gap identification and discussion", 30, "discussion"),
            (time(11, 45), "Actions", 15, "wrap_up"),
        ],
    }
    count = 0
    for ws_code, items in agenda_data.items():
        for idx, (t, title, dur, atype) in enumerate(items):
            ai = WorkshopAgendaItem(
                id=_uid(), workshop_id=workshops[ws_code].id,
                time=t, title=title, duration_minutes=dur,
                type=atype, sort_order=idx + 1,
            )
            db.session.add(ai)
            count += 1
    db.session.flush()
    print(f"  ✅ {count} agenda items")


# ═══════════════════════════════════════════════════════════════════════════
# 7. PROCESS STEPS + FIT-GAP (11)
# ═══════════════════════════════════════════════════════════════════════════

def seed_fitgap(workshops, levels):
    """ProcessStep = FitGap items tied to workshops and L4 process levels."""
    steps = {}
    # Map gap items to L4 level codes (unique workshop+level per step)
    gap_data = [
        # SES-001 FitGap — each must have unique (workshop_id, process_level_id)
        ("GAP-001", "SES-001", "SD-001.03", "fit",
         "SAP standard order process (VA01-VA02-VA03) meets the current process. Pricing procedure is covered."),
        ("GAP-003", "SES-001", "SD-001.01", "partial_fit",
         "Plant-level ATP is available in standard. Enhancement needed for storage location-based ATP."),
        ("GAP-004", "SES-001", "SD-002.01", "gap",
         "Current intercompany billing is entirely manual. SAP standard BD9 exists but transfer pricing rules require custom development."),
        ("GAP-005", "SES-001", "SD-001.02", "partial_fit",
         "Standard delivery split is available. Customer-specific split rules require enhancement."),
        ("GAP-006", "SES-001", "SD-002.02", "fit",
         "SAP Credit Management (1E1) provides online credit control. Can be migrated with configuration."),
        # SES-003 FitGap
        ("GAP-007", "SES-003", "MM-001.01", "fit",
         "SAP standard PR process fully meets the current process. Approval process will be handled with Release Strategy."),
        ("GAP-008", "SES-003", "MM-001.02", "fit",
         "Automatic PO creation after MRP run is available in SAP standard (ME59N)."),
        ("GAP-009", "SES-003", "MM-002.02", "gap",
         "Current Excel-based vendor scoring system contains 15 custom criteria. SAP standard evaluation only has 5 criteria. Custom report required."),
        ("GAP-010", "SES-003", "MM-002.03", "partial_fit",
         "Consignment stock tracking is available in standard. 3 custom reports required: aging, turnover, value."),
        ("GAP-011", "SES-003", "MM-002.01", "fit",
         "Goods receipt tolerance check is available in SAP standard. Can be configured with OMBR/OMBW config transactions."),
    ]
    for code, ws_code, level_code, decision, notes in gap_data:
        ps = ProcessStep(
            id=_uid(),
            workshop_id=workshops[ws_code].id,
            process_level_id=levels[level_code].id,
            fit_decision=decision,
            notes=notes,
            sort_order=len(steps) + 1,
            demo_shown=True,
            bpmn_reviewed=True,
        )
        db.session.add(ps)
        db.session.flush()
        steps[code] = ps

    print(f"  ✅ {len(steps)} fit-gap items (process steps)")
    return steps


# ═══════════════════════════════════════════════════════════════════════════
# 8. QUESTIONS / OPEN ITEMS (8)
# ═══════════════════════════════════════════════════════════════════════════

def seed_questions(program, workshops):
    q_data = [
        ("Q-001", "SES-001", "How many different order types are used in the current system?",
         "12 different order types exist. 7 are covered in SAP standard, 5 will continue as custom developments.",
         "closed", "Elif Kara", "clarification"),
        ("Q-002", "SES-001", "At what level is the ATP check performed? Plant or storage location?",
         "Currently at plant level. SAP standard ATP also supports storage location level, can be solved with configuration.",
         "closed", "Hasan Demir", "technical"),
        ("Q-003", "SES-001", "How does billing work in intercompany sales?",
         "Manual in current system. Automatic intercompany billing is possible in S/4HANA with scope item BD9.",
         "closed", "Mehmet Yilmaz", "process"),
        ("Q-004", "SES-001", "Is credit limit check performed online or in batch?",
         "", "open", "Elif Kara", "technical"),
        ("Q-005", "SES-001", "How will the process work for third-party sales?",
         "", "open", "Mehmet Yilmaz", "scope"),
        ("Q-006", "SES-003", "Is the supplier evaluation system available in SAP?",
         "Supplier Evaluation (ME61-ME65) is available in SAP standard. Custom development may be needed to migrate custom criteria.",
         "closed", "Aylin Sahin", "technical"),
        ("Q-007", "SES-003", "How will purchase approval limits be defined?",
         "Will be defined with Release Strategy in SAP. The current 4-tier approval process can be fully replicated.",
         "closed", "Aylin Sahin", "process"),
        ("Q-008", "SES-003", "Is the consignment procurement process available?",
         "Yes, available within scope item 2NM. However, custom consignment reports are not available in SAP standard.",
         "closed", "Serkan Yildiz", "process"),
    ]
    count = 0
    creator_id = _uid()  # dummy user ID
    for code, ws_code, title, resolution, status, asked_by, category in q_data:
        q = ExploreOpenItem(
            id=_uid(), project_id=program.id,
            workshop_id=workshops[ws_code].id,
            code=code, title=title,
            description=f"Question: {title}",
            status=status,
            priority="P2" if status == "open" else "P3",
            category=category,
            assignee_name=asked_by,
            resolution=resolution if resolution else None,
            created_by_id=creator_id,
            process_area=workshops[ws_code].process_area,
        )
        db.session.add(q)
        count += 1
    db.session.flush()
    print(f"  ✅ {count} questions (open items)")


# ═══════════════════════════════════════════════════════════════════════════
# 9. DECISIONS (5)
# ═══════════════════════════════════════════════════════════════════════════

def seed_decisions(program, steps):
    dec_data = [
        ("DEC-001", "GAP-001", "Order type consolidation",
         "7 of the 12 existing order types will be mapped to SAP standard types. 5 custom types will continue.",
         "Mehmet Yilmaz, Canan Ozturk", "process", "active"),
        ("DEC-002", "GAP-003", "ATP level decision",
         "ATP check will remain at plant level, storage location level will be deferred to Phase 2.",
         "Hasan Demir, Burak Kaya", "technical", "active"),
        ("DEC-003", "GAP-004", "Intercompany approach",
         "SAP standard BD9 scope item will be used. ABAP enhancement will be developed for transfer pricing rules.",
         "Mehmet Yilmaz", "scope", "active"),
        ("DEC-004", "GAP-007", "Release Strategy structure",
         "4-tier approval process will be implemented exactly with SAP Release Strategy.",
         "Aylin Sahin", "process", "active"),
        ("DEC-005", "GAP-009", "Vendor Evaluation approach",
         "SAP standard evaluation + custom Z-report combination.",
         "Aylin Sahin, Fatih Korkmaz", "technical", "active"),
    ]
    count = 0
    for code, step_code, text, rationale, decided_by, category, status in dec_data:
        d = ExploreDecision(
            id=_uid(), project_id=program.id,
            process_step_id=steps[step_code].id,
            code=code, text=text, rationale=rationale,
            decided_by=decided_by, category=category, status=status,
        )
        db.session.add(d)
        count += 1
    db.session.flush()
    print(f"  ✅ {count} decisions")


# ═══════════════════════════════════════════════════════════════════════════
# 10. RISKS (5)
# ═══════════════════════════════════════════════════════════════════════════

def seed_risks(program):
    risk_data = [
        ("RSK-001", "Data Migration complexity",
         "Open order and historical data conversion during consolidation of 12 order types to 7 may be complex. 50K+ open orders exist.",
         "high", 4, 5, "Deniz Aksoy",
         "Migration pilot study will be conducted. Test with first 1000 records, then full migration. Fallback plan will be prepared."),
        ("RSK-002", "Intercompany development timeline",
         "Transfer pricing ABAP development may threaten the Go-live date. Complexity is high.",
         "high", 3, 4, "Burak Kaya",
         "Early prototype (starting in Sprint 2). If necessary, will be removed from Go-live scope and moved to Phase 2."),
        ("RSK-003", "Key User availability",
         "Elif Kara (SD Key User) will be on leave for 2 weeks in April. Affects workshop planning.",
         "medium", 3, 3, "Ayse Demir",
         "Backup key user (Gamze Yildiz) will be assigned. Critical workshops will be completed before April."),
        ("RSK-004", "Custom report performance",
         "Vendor scoring custom report may run slowly on large data sets (100K+ supplier records).",
         "low", 2, 3, "Deniz Aksoy",
         "Performance will be ensured with HANA optimization + CDS view usage."),
        ("RSK-005", "Insufficient user training",
         "Training for 200+ end users may not be completed within adequate timeframe.",
         "medium", 3, 3, "Ayse Demir",
         "Train-the-trainer approach. 15 super users will be trained."),
    ]
    count = 0
    for code, title, desc, priority, prob, impact, owner, mitigation in risk_data:
        r = Risk(
            program_id=program.id,
            code=code, title=title, description=desc,
            status="open", owner=owner, priority=priority,
            probability=prob, impact=impact,
            mitigation_plan=mitigation,
        )
        r.recalculate_score()
        db.session.add(r)
        count += 1
    db.session.flush()
    print(f"  ✅ {count} risks")


# ═══════════════════════════════════════════════════════════════════════════
# 11. ACTIONS (8)
# ═══════════════════════════════════════════════════════════════════════════

def seed_actions(program):
    act_data = [
        ("ACT-001", "Prepare order type mapping document", "Canan Ozturk",
         date(2026, 3, 25), "high", "in_progress", "follow_up"),
        ("ACT-002", "Write ATP enhancement scope document", "Canan Ozturk",
         date(2026, 3, 28), "high", "open", "follow_up"),
        ("ACT-003", "Document intercompany transfer pricing rules", "Mehmet Yilmaz",
         date(2026, 4, 1), "critical", "open", "preventive"),
        ("ACT-004", "Get backup key user (Gamze Yildiz) approval", "Ayse Demir",
         date(2026, 3, 20), "medium", "completed", "corrective"),
        ("ACT-005", "Prepare data migration pilot plan", "Deniz Aksoy",
         date(2026, 4, 5), "high", "open", "preventive"),
        ("ACT-006", "Release Strategy detailed design", "Fatih Korkmaz",
         date(2026, 3, 28), "medium", "in_progress", "follow_up"),
        ("ACT-007", "Vendor scoring criteria list (15 criteria detailed)", "Aylin Sahin",
         date(2026, 3, 30), "high", "open", "follow_up"),
        ("ACT-008", "Write consignment report requirements", "Serkan Yildiz",
         date(2026, 4, 2), "medium", "open", "follow_up"),
    ]
    count = 0
    for code, title, owner, due, priority, status, atype in act_data:
        a = Action(
            program_id=program.id,
            code=code, title=title, owner=owner,
            due_date=due, priority=priority, status=status,
            action_type=atype,
        )
        db.session.add(a)
        count += 1
    db.session.flush()
    print(f"  ✅ {count} actions")


# ═══════════════════════════════════════════════════════════════════════════
# 12. REQUIREMENTS (12)
# ═══════════════════════════════════════════════════════════════════════════

def seed_requirements(program, workshops, steps, levels):
    """Create ExploreRequirements — Fit, Partial Fit, Gap."""
    reqs = {}
    creator_id = _uid()

    req_data = [
        # Fit requirements
        ("REQ-001", "Standard Sales Order Configuration", "Fit", "SD", "P1", "approved",
         "configuration", "SES-001", "GAP-001",
         "Standard order type (OR) configuration. Order type, item category determination, schedule line category, copy control settings. Within scope item 1YG.", 0),
        ("REQ-002", "SD Pricing Procedure Setup", "Fit", "SD", "P1", "approved",
         "configuration", "SES-001", "GAP-001",
         "Pricing procedure configuration. 8 condition type and access sequence definitions.", 0),
        ("REQ-003", "Credit Management Configuration", "Fit", "SD", "P2", "approved",
         "configuration", "SES-001", "GAP-006",
         "SAP Credit Management (FIN-FSCM-CR) configuration. Credit segment, risk category, automatic credit decision rules.", 0),
        ("REQ-004", "Purchase Requisition Approval (Release Strategy)", "Fit", "MM", "P1", "approved",
         "configuration", "SES-003", "GAP-007",
         "Purchase requisition approval strategy configuration. 4-tier approval.", 0),
        ("REQ-005", "GR Tolerance Configuration", "Fit", "MM", "P3", "approved",
         "configuration", "SES-003", "GAP-011",
         "Goods receipt tolerance check settings. Quantity tolerance 5%, price tolerance 3%.", 0),
        # Partial Fit requirements
        ("REQ-006", "ATP Check Enhancement", "Partial Fit", "SD", "P1", "under_review",
         "enhancement", "SES-001", "GAP-003",
         "BADI implementation needed for storage location-based ATP logic and alternative plant check.", 12),
        ("REQ-007", "Delivery Split Custom Logic", "Partial Fit", "SD", "P2", "under_review",
         "enhancement", "SES-001", "GAP-005",
         "Same-day delivery priority logic and customer-specific partial shipment restriction rules. User exit USEREXIT_MOVE_FIELD_TO_VBLK.", 8),
        ("REQ-008", "Consignment Stock Reporting", "Partial Fit", "MM", "P2", "draft",
         "enhancement", "SES-003", "GAP-010",
         "3 custom reports required: aging report, turnover analysis, value report. CDS view + Fiori app approach.", 15),
        # Gap requirements
        ("REQ-009", "Intercompany Billing Automation", "Gap", "SD", "P1", "approved",
         "development", "SES-001", "GAP-004",
         "Transfer pricing custom logic on top of SAP standard BD9. ABAP enhancement + custom pricing procedure. Estimate: 40 person-days.", 40),
        ("REQ-010", "Vendor Scoring Custom Report", "Gap", "MM", "P1", "approved",
         "development", "SES-003", "GAP-009",
         "15-criteria vendor scoring report. Z-report + ALV + Fiori dashboard. Estimate: 20 person-days.", 20),
        ("REQ-011", "Custom IDoc for Intercompany Orders", "Gap", "SD", "P1", "draft",
         "integration", "SES-001", "GAP-004",
         "Custom IDoc message type for intercompany order creation. Z-segment on top of ORDERS05 base IDoc. Estimate: 15 person-days.", 15),
        ("REQ-012", "Automated Dunning Workflow", "Gap", "FI", "P2", "draft",
         "development", None, None,
         "Automated collection reminder workflow. Custom workflow on top of SAP standard dunning (F150). BRFplus decision table. Estimate: 25 person-days.", 25),
    ]

    fit_map = {"Fit": "fit", "Partial Fit": "partial_fit", "Gap": "gap"}

    for code, title, fit, mod, priority, status, rtype, ws_code, step_code, desc, effort in req_data:
        ws_id = workshops[ws_code].id if ws_code else None
        ps_id = steps[step_code].id if step_code else None
        r = ExploreRequirement(
            id=_uid(), project_id=program.id,
            workshop_id=ws_id,
            process_step_id=ps_id,
            code=code, title=title, description=desc,
            priority=priority, type=rtype,
            fit_status=fit_map[fit], status=status,
            sap_module=mod,
            effort_hours=effort * 8 if effort else None,
            complexity="high" if effort >= 20 else "medium" if effort >= 8 else "low",
            created_by_id=creator_id,
            created_by_name="Seed Script",
        )
        db.session.add(r)
        db.session.flush()
        reqs[code] = r

    print(f"  ✅ {len(reqs)} requirements")
    return reqs


# ═══════════════════════════════════════════════════════════════════════════
# 13. WRICEF ITEMS (6)
# ═══════════════════════════════════════════════════════════════════════════

def seed_wricef(program, reqs):
    items = {}
    w_data = [
        ("W-001", "ATP Check Enhancement (BADI)", "enhancement", "SD",
         "High", "new", "REQ-006",
         "BADI implementation: BAPI_MATERIAL_AVAILABILITY. Storage location-based ATP logic. Estimate: 12 person-days.", 12),
        ("W-002", "Delivery Split Custom Logic", "enhancement", "SD",
         "Medium", "new", "REQ-007",
         "User exit USEREXIT_MOVE_FIELD_TO_VBLK enhancement. Same-day delivery priority. Estimate: 8 person-days.", 8),
        ("W-003", "Intercompany Billing Enhancement", "enhancement", "SD",
         "Critical", "design", "REQ-009",
         "ABAP enhancement: transfer pricing logic, custom pricing procedure ZINTER. Estimate: 40 person-days.", 40),
        ("R-001", "Vendor Scoring Dashboard", "report", "MM",
         "High", "new", "REQ-010",
         "ALV interactive report + Fiori app. 15 criteria, weighted scoring. CDS view: ZI_VENDOR_SCORE. Estimate: 20 person-days.", 20),
        ("I-001", "Intercompany Order IDoc", "interface", "SD",
         "High", "new", "REQ-011",
         "Custom IDoc message type ZORDERS_IC. Base: ORDERS05. Z-segment: Z1ICDATA. Estimate: 15 person-days.", 15),
        ("W-004", "Dunning Workflow Automation", "workflow", "FI",
         "Medium", "new", "REQ-012",
         "SAP Workflow + BRFplus. Dunning trigger → mail → escalation → portal notification. Estimate: 25 person-days.", 25),
    ]
    priority_map = {"Critical": "critical", "High": "high", "Medium": "medium", "Low": "low"}

    for code, title, wtype, mod, priority, status, req_code, desc, effort in w_data:
        bi = BacklogItem(
            program_id=program.id,
            explore_requirement_id=reqs[req_code].id,
            code=code, title=title, description=desc,
            wricef_type=wtype, module=mod,
            status=status,
            priority=priority_map.get(priority, "medium"),
            estimated_hours=effort * 8,
            story_points=effort // 2,
            complexity="high" if effort >= 20 else "medium",
        )
        db.session.add(bi)
        db.session.flush()
        items[code] = bi

    print(f"  ✅ {len(items)} WRICEF items")
    return items


# ═══════════════════════════════════════════════════════════════════════════
# 14. CONFIG ITEMS (5)
# ═══════════════════════════════════════════════════════════════════════════

def seed_config_items(program, reqs):
    configs = {}
    cfg_data = [
        ("CFG-001", "Sales Order Type Configuration", "SD", "in_progress", "REQ-001",
         "VOV8, VOV7, OVLP",
         "Order type OR configuration: item category determination (TAN, TAX), schedule line (CP, CN), copy control, partner determination."),
        ("CFG-002", "SD Pricing Procedure Config", "SD", "in_progress", "REQ-002",
         "V/08, VK11-VK13",
         "Condition type definitions via pricing procedure RVAA01. Access sequence, condition tables, condition records."),
        ("CFG-003", "Credit Management Setup", "SD", "planned", "REQ-003",
         "UKM_ADMIN, FDK43",
         "Credit segment ZSTD definition, risk category A/B/C, credit control area 1000, automatic credit decision rules."),
        ("CFG-004", "MM Release Strategy", "MM", "in_progress", "REQ-004",
         "SPRO, CL02, ME28",
         "Release group Z1, release code (Z1-Z4), release strategy definitions. Classification: purchasing group + net value range."),
        ("CFG-005", "GR Tolerance Setup", "MM", "planned", "REQ-005",
         "OMBR, OMBW",
         "Tolerance key PE: qty tolerance 5%, price tolerance 3%. Plant-based definition. Active for movement types 101 and 102."),
    ]
    for code, title, mod, status, req_code, tcode, desc in cfg_data:
        ci = ConfigItem(
            program_id=program.id,
            explore_requirement_id=reqs[req_code].id,
            code=code, title=title, description=desc,
            module=mod, status=status,
            transaction_code=tcode,
            priority="high",
        )
        db.session.add(ci)
        db.session.flush()
        configs[code] = ci

    print(f"  ✅ {len(configs)} config items")
    return configs


# ═══════════════════════════════════════════════════════════════════════════
# 15. TEST CASES (8)
# ═══════════════════════════════════════════════════════════════════════════

def seed_test_cases(program, wricef, configs):
    cases = {}
    tc_data = [
        # Unit tests
        ("UT-001", "Unit Test: SD Pricing Procedure", "unit", "SD", "ready",
         "CFG-002", None,
         "Create order with VA01 → verify 8 condition types are correct → validate net value calculation",
         "VA01 → create order", "Condition types PR00, K004, K005, K007, MWST, HA00, HB00, ZK01 present. Net value correct."),
        ("UT-002", "Unit Test: ATP Check Enhancement", "unit", "SD", "draft",
         None, "W-001",
         "VA01 → storage location-based ATP → verify result → alternative plant check → verify ordering",
         "VA01 → trigger ATP check", "Storage location-based ATP result correct. Alternative plant ordering as expected."),
        ("UT-003", "Unit Test: Release Strategy", "unit", "MM", "ready",
         "CFG-004", None,
         "Create PR with ME51N → test each level: <5K automatic, 5K-25K dept manager, 25K-100K director, >100K CEO",
         "ME51N → create PR", "Correct release code triggered at each tier."),
        ("UT-004", "Unit Test: Vendor Scoring Report", "unit", "MM", "draft",
         None, "R-001",
         "Execute Z-report → are 15 criteria calculated correctly → check weighted score → is drill-down working",
         "Z-report execute", "15 criteria displayed with weighted score. Drill-down OK."),
        # SIT tests
        ("SIT-001", "SIT: O2C End-to-End Flow", "sit", "SD", "draft",
         None, None,
         "VA01 order → VL01N delivery → VL02N PGI → VF01 invoice → FI accounting entry → accounts receivable verification",
         "VA01 → VL01N → VF01 → FI posting", "Entire chain completed without issues. FI entry created."),
        ("SIT-002", "SIT: P2P End-to-End Flow", "sit", "MM", "draft",
         None, None,
         "ME51N requisition → ME21N order → MIGO goods receipt → MIRO invoice verification → FI accounting entry → payment plan",
         "ME51N → ME21N → MIGO → MIRO", "P2P chain completed. FI entry OK."),
        # UAT tests
        ("UAT-001", "UAT: Sales Order Processing", "uat", "SD", "draft",
         None, None,
         "End user scenario: receive order from customer → check stock → plan delivery → issue invoice → collection tracking",
         "Receive order → delivery → invoice", "End user scenario successful."),
        ("UAT-002", "UAT: Procurement Cycle", "uat", "MM", "draft",
         None, None,
         "End user scenario: identify material need → create PR → get approval → send PO → goods receipt → invoice matching",
         "PR → PO → GR → IR", "Procurement cycle OK."),
    ]
    for code, title, layer, mod, status, cfg_code, wricef_code, desc, steps, expected in tc_data:
        cfg_id = configs[cfg_code].id if cfg_code else None
        wricef_id = wricef[wricef_code].id if wricef_code else None
        tc = TestCase(
            program_id=program.id,
            config_item_id=cfg_id,
            backlog_item_id=wricef_id,
            code=code, title=title, description=desc,
            test_layer=layer, module=mod, status=status,
            test_steps=steps, expected_result=expected,
            priority="high" if layer == "unit" else "medium",
        )
        db.session.add(tc)
        db.session.flush()
        cases[code] = tc

    print(f"  ✅ {len(cases)} test cases")
    return cases


# ═══════════════════════════════════════════════════════════════════════════
# 16. TEST CYCLES (3) + TEST PLAN
# ═══════════════════════════════════════════════════════════════════════════

def seed_test_cycles(program, cases):
    # Test Plan (required parent)
    tp = TestPlan(
        program_id=program.id,
        name="Anadolu Holding — Master Test Plan",
        description="Unit, SIT, and UAT test plan for SD/MM/FI/CO modules.",
        status="active",
    )
    db.session.add(tp)
    db.session.flush()

    cycles = {}
    cycle_data = [
        ("TC-001", "Sprint 1 Unit Test Cycle", "unit", "planning",
         date(2026, 5, 1), date(2026, 5, 15),
         "First sprint unit tests. SD pricing, ATP enhancement, MM release strategy tests."),
        ("TC-002", "SIT Cycle 1 — Core Processes", "sit", "planning",
         date(2026, 6, 1), date(2026, 6, 30),
         "O2C and P2P end-to-end integration tests. Cross-module connections will be verified."),
        ("TC-003", "UAT Cycle 1 — Business Validation", "uat", "planning",
         date(2026, 8, 1), date(2026, 8, 31),
         "End user acceptance tests. Real business scenarios will be tested by key users."),
    ]
    for idx, (code, name, layer, status, sd, ed, desc) in enumerate(cycle_data):
        tc = TestCycle(
            plan_id=tp.id, name=name, description=desc,
            test_layer=layer, status=status,
            start_date=sd, end_date=ed,
            order=idx + 1,
        )
        db.session.add(tc)
        db.session.flush()
        cycles[code] = tc

    print(f"  ✅ 1 test plan, {len(cycles)} test cycles")
    return cycles


# ═══════════════════════════════════════════════════════════════════════════
# 17. TEST EXECUTIONS (2)
# ═══════════════════════════════════════════════════════════════════════════

def seed_test_executions(cycles, cases):
    exec_data = [
        ("TC-001", "UT-001", "pass", "Canan Ozturk", 45,
         "8/8 condition types returned correctly. Net value calculation OK."),
        ("TC-001", "UT-003", "fail", "Fatih Korkmaz", 60,
         "Release code Z4 not triggering at >100K level. Config missing — classification object to be updated."),
    ]
    count = 0
    for cycle_code, case_code, result, executor, dur, notes in exec_data:
        te = TestExecution(
            cycle_id=cycles[cycle_code].id,
            test_case_id=cases[case_code].id,
            result=result, executed_by=executor,
            duration_minutes=dur, notes=notes,
            executed_at=_now,
        )
        db.session.add(te)
        count += 1
    db.session.flush()
    print(f"  ✅ {count} test executions")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Seed Anadolu Holding demo data")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.reset:
            print("\n⚠️  DB being reset (drop_all + create_all)...")
            db.drop_all()
            db.create_all()
            print("   ✅ DB recreated\n")

        print("=" * 60)
        print("🏢 Loading Anadolu Holding S/4HANA Demo Data...")
        print("=" * 60)
        print()

        # 1. Program
        program, phases, workstreams = seed_program()

        # 2. Scenarios
        scenarios = seed_scenarios(program)

        # 3. Process hierarchy + Analyses
        processes, analyses = seed_processes_and_analyses(program, scenarios)

        # 4. Explore Workshops + Process Levels
        workshops, levels = seed_workshops(program)

        # 5. Attendees
        seed_attendees(workshops)

        # 6. Agenda
        seed_agenda(workshops)

        # 7. Fit-Gap (ProcessSteps)
        steps = seed_fitgap(workshops, levels)

        # 8. Questions (Open Items)
        seed_questions(program, workshops)

        # 9. Decisions
        seed_decisions(program, steps)

        # 10. Risks
        seed_risks(program)

        # 11. Actions
        seed_actions(program)

        # 12. Requirements
        reqs = seed_requirements(program, workshops, steps, levels)

        # 13. WRICEF Items
        wricef = seed_wricef(program, reqs)

        # 14. Config Items
        configs = seed_config_items(program, reqs)

        # 15. Test Cases
        cases = seed_test_cases(program, wricef, configs)

        # 16. Test Cycles
        cycles = seed_test_cycles(program, cases)

        # 17. Test Executions
        seed_test_executions(cycles, cases)

        db.session.commit()

        print()
        print("=" * 60)
        print("🎉 ANADOLU HOLDING DEMO DATA LOADING COMPLETED")
        print("=" * 60)
        print()
        print("   📊 Summary:")
        print("   ├── 1 Program (Anadolu Holding S/4HANA)")
        print("   ├── 5 Scenarios (O2C, P2P, R2R, P2Pr, Composite)")
        print("   ├── 4 Analyses")
        print("   ├── 4 Workshops (Sessions)")
        print("   ├── 9 Attendees")
        print("   ├── 13 Agenda Items")
        print("   ├── 10 Fit-Gap Items")
        print("   ├── 8 Questions (Open Items)")
        print("   ├── 5 Decisions")
        print("   ├── 5 Risks")
        print("   ├── 8 Actions")
        print("   ├── 12 Requirements")
        print("   ├── 6 WRICEF Items")
        print("   ├── 5 Config Items")
        print("   ├── 8 Test Cases")
        print("   ├── 3 Test Cycles")
        print("   └── 2 Test Executions")
        print()
        print("   🔗 http://localhost:5001")
        print()


if __name__ == "__main__":
    main()
