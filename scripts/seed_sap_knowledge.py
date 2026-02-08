#!/usr/bin/env python3
"""
SAP Activate Knowledge Base — Seed Data Script.

Populates the SAP Transformation Platform with reference data:
    - SAP Activate methodology phases, gates, and deliverables
    - Common SAP workstream templates
    - Standard committee structures

Usage:
    python scripts/seed_sap_knowledge.py
    python scripts/seed_sap_knowledge.py --program-id 1   # Attach to existing program
"""

import argparse
import sys

sys.path.insert(0, ".")

from app import create_app
from app.models import db
from app.models.program import (
    Committee,
    Gate,
    Phase,
    Program,
    TeamMember,
    Workstream,
)

# ═════════════════════════════════════════════════════════════════════════════
# SAP ACTIVATE PHASE TEMPLATES
# ═════════════════════════════════════════════════════════════════════════════

SAP_ACTIVATE_PHASES = [
    {
        "name": "Discover",
        "order": 1,
        "description": (
            "Understand the customer's business, strategy, and pain points. "
            "Define the project vision, scope, and business case. "
            "Key deliverables: Business Case, High-Level Scope, Initial Roadmap."
        ),
        "gates": [
            {
                "name": "Discover Quality Gate",
                "gate_type": "quality_gate",
                "criteria": (
                    "✅ Business case approved by sponsor\n"
                    "✅ High-level scope document signed off\n"
                    "✅ Budget and timeline confirmed\n"
                    "✅ Executive sponsor identified\n"
                    "✅ Initial risk assessment completed"
                ),
            },
        ],
    },
    {
        "name": "Prepare",
        "order": 2,
        "description": (
            "Set up the project governance, team, system landscape, and tools. "
            "Onboard team members, establish communication channels. "
            "Key deliverables: Project Charter, Team Org Chart, System Landscape Plan."
        ),
        "gates": [
            {
                "name": "Prepare Quality Gate",
                "gate_type": "quality_gate",
                "criteria": (
                    "✅ Project charter signed off\n"
                    "✅ Team onboarded and trained\n"
                    "✅ Development environment available\n"
                    "✅ Governance structure established\n"
                    "✅ Communication plan in place"
                ),
            },
        ],
    },
    {
        "name": "Explore",
        "order": 3,
        "description": (
            "Conduct Fit-to-Standard workshops. Validate standard SAP processes "
            "against business requirements. Identify gaps and define backlog items. "
            "Key deliverables: Fit/Gap Analysis, Backlog, Delta Design Documents."
        ),
        "gates": [
            {
                "name": "Explore Quality Gate",
                "gate_type": "quality_gate",
                "criteria": (
                    "✅ All Fit-to-Standard workshops completed\n"
                    "✅ Fit/Gap analysis documented\n"
                    "✅ Backlog baselined and prioritized\n"
                    "✅ Delta design documents signed off\n"
                    "✅ Integration strategy defined\n"
                    "✅ Data migration strategy defined"
                ),
            },
        ],
    },
    {
        "name": "Realize",
        "order": 4,
        "description": (
            "Configure, develop, and test the SAP solution. Execute iterative "
            "sprints for configuration and RICEFW development. "
            "Key deliverables: Configured System, Test Results, Training Materials."
        ),
        "gates": [
            {
                "name": "Realize Quality Gate (SIT)",
                "gate_type": "quality_gate",
                "criteria": (
                    "✅ All configuration completed\n"
                    "✅ RICEFW development completed\n"
                    "✅ Unit tests passed\n"
                    "✅ System Integration Testing (SIT) passed\n"
                    "✅ Performance testing completed"
                ),
            },
            {
                "name": "Realize Quality Gate (UAT)",
                "gate_type": "quality_gate",
                "criteria": (
                    "✅ User Acceptance Testing (UAT) plan approved\n"
                    "✅ UAT executed and defects resolved\n"
                    "✅ Training materials prepared\n"
                    "✅ Cutover plan drafted"
                ),
            },
        ],
    },
    {
        "name": "Deploy",
        "order": 5,
        "description": (
            "Execute cutover activities, final data migration, and go-live. "
            "Conduct dress rehearsals and obtain Go/No-Go decision. "
            "Key deliverables: Cutover Plan, Migration Results, Go-Live Sign-off."
        ),
        "gates": [
            {
                "name": "Go/No-Go Decision Gate",
                "gate_type": "decision_point",
                "criteria": (
                    "✅ Cutover rehearsal completed successfully\n"
                    "✅ Final data migration validated\n"
                    "✅ End-user training completed\n"
                    "✅ Support organization ready\n"
                    "✅ Go/No-Go decision approved by SteerCo"
                ),
            },
        ],
    },
    {
        "name": "Run",
        "order": 6,
        "description": (
            "Hypercare support, issue resolution, stabilization. "
            "Monitor system performance and business KPIs. "
            "Handover to Application Management Services (AMS). "
            "Key deliverables: Hypercare Report, KPI Dashboard, AMS Handover."
        ),
        "gates": [
            {
                "name": "Hypercare Exit Gate",
                "gate_type": "milestone",
                "criteria": (
                    "✅ Hypercare period completed (typically 4-8 weeks)\n"
                    "✅ Critical/high priority tickets resolved\n"
                    "✅ Business KPIs within acceptable range\n"
                    "✅ AMS team trained and ready\n"
                    "✅ Project closure report signed off"
                ),
            },
        ],
    },
]

# ═════════════════════════════════════════════════════════════════════════════
# STANDARD SAP WORKSTREAMS
# ═════════════════════════════════════════════════════════════════════════════

SAP_WORKSTREAMS = [
    # Functional
    {"name": "Finance (FI/CO)", "ws_type": "functional", "description": "General Ledger, AP/AR, Cost Centers, Profitability Analysis"},
    {"name": "Materials Management (MM)", "ws_type": "functional", "description": "Procurement, Inventory Management, Warehouse"},
    {"name": "Sales & Distribution (SD)", "ws_type": "functional", "description": "Order-to-Cash, Pricing, Shipping, Billing"},
    {"name": "Production Planning (PP)", "ws_type": "functional", "description": "MRP, Production Orders, Shop Floor Control"},
    {"name": "Quality Management (QM)", "ws_type": "functional", "description": "Quality Planning, Inspection, Notifications"},
    {"name": "Plant Maintenance (PM)", "ws_type": "functional", "description": "Preventive/Corrective Maintenance, Work Orders"},
    {"name": "Human Capital Management (HCM)", "ws_type": "functional", "description": "Org Management, Personnel Admin, Payroll"},
    {"name": "Project System (PS)", "ws_type": "functional", "description": "WBS, Network Activities, Billing"},
    # Technical
    {"name": "Basis / Technology", "ws_type": "technical", "description": "System Administration, Landscape, Security, Authorizations"},
    {"name": "Integration (Middleware)", "ws_type": "technical", "description": "SAP BTP Integration Suite, CPI, APIs"},
    {"name": "Data Migration", "ws_type": "technical", "description": "Data extraction, transformation, validation, loading"},
    {"name": "RICEFW Development", "ws_type": "technical", "description": "Reports, Interfaces, Conversions, Enhancements, Forms, Workflows"},
    # Cross-cutting
    {"name": "Testing", "ws_type": "cross_cutting", "description": "Test Strategy, SIT, UAT, Performance, Regression"},
    {"name": "Change Management & Training", "ws_type": "cross_cutting", "description": "Stakeholder engagement, training, communication"},
    {"name": "Cutover Management", "ws_type": "cross_cutting", "description": "Cutover planning, rehearsals, go-live execution"},
]

# ═════════════════════════════════════════════════════════════════════════════
# STANDARD COMMITTEES
# ═════════════════════════════════════════════════════════════════════════════

SAP_COMMITTEES = [
    {
        "name": "Steering Committee (SteerCo)",
        "committee_type": "steering",
        "meeting_frequency": "monthly",
        "description": "Executive-level governance body. Approves budget, scope changes, and key decisions.",
    },
    {
        "name": "Project Management Office (PMO)",
        "committee_type": "working_group",
        "meeting_frequency": "weekly",
        "description": "Operational project management. Tracks progress, risks, and issues.",
    },
    {
        "name": "Change Advisory Board (CAB)",
        "committee_type": "advisory",
        "meeting_frequency": "biweekly",
        "description": "Reviews and approves change requests and scope changes.",
    },
    {
        "name": "Architecture Review Board (ARB)",
        "committee_type": "review",
        "meeting_frequency": "biweekly",
        "description": "Technical architecture decisions, integration patterns, security.",
    },
]


# ═════════════════════════════════════════════════════════════════════════════
# SEED FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def seed_program(app, program_id=None):
    """
    Create a demo SAP Activate program with all reference data,
    or attach reference data to an existing program.
    """
    with app.app_context():
        if program_id:
            program = db.session.get(Program, program_id)
            if not program:
                print(f"  ❌ Program {program_id} not found!")
                return
            print(f"  🔗 Attaching seed data to existing program: {program.name}")
        else:
            program = Program(
                name="[Demo] SAP S/4HANA Greenfield — SAP Activate",
                description=(
                    "Reference implementation demonstrating a full SAP Activate "
                    "methodology program with all phases, gates, workstreams, "
                    "committees, and team roles."
                ),
                project_type="greenfield",
                methodology="sap_activate",
                status="planning",
                priority="high",
                sap_product="S/4HANA",
                deployment_option="cloud",
            )
            db.session.add(program)
            db.session.flush()
            print(f"  ✅ Created demo program: {program.name} (ID: {program.id})")

        # Phases + Gates
        print("\n  ── Seeding phases & gates ──")
        for tmpl in SAP_ACTIVATE_PHASES:
            phase = Phase(
                program_id=program.id,
                name=tmpl["name"],
                description=tmpl["description"],
                order=tmpl["order"],
                status="not_started",
            )
            db.session.add(phase)
            db.session.flush()
            print(f"    📅 Phase: {phase.name} (ID: {phase.id})")

            for g in tmpl.get("gates", []):
                gate = Gate(
                    phase_id=phase.id,
                    name=g["name"],
                    gate_type=g["gate_type"],
                    criteria=g.get("criteria", ""),
                )
                db.session.add(gate)
                print(f"       🚪 Gate: {gate.name}")

        # Workstreams
        print("\n  ── Seeding workstreams ──")
        for ws_tmpl in SAP_WORKSTREAMS:
            ws = Workstream(
                program_id=program.id,
                name=ws_tmpl["name"],
                description=ws_tmpl.get("description", ""),
                ws_type=ws_tmpl["ws_type"],
                status="active",
            )
            db.session.add(ws)
            print(f"    🔧 Workstream: {ws.name} ({ws.ws_type})")

        # Committees
        print("\n  ── Seeding committees ──")
        for comm_tmpl in SAP_COMMITTEES:
            comm = Committee(
                program_id=program.id,
                name=comm_tmpl["name"],
                description=comm_tmpl.get("description", ""),
                committee_type=comm_tmpl["committee_type"],
                meeting_frequency=comm_tmpl["meeting_frequency"],
            )
            db.session.add(comm)
            print(f"    🏛️  Committee: {comm.name}")

        db.session.commit()
        print(f"\n  🎉 Seed data applied to program ID: {program.id}")


def main():
    parser = argparse.ArgumentParser(description="Seed SAP Activate reference data")
    parser.add_argument(
        "--program-id", type=int, default=None,
        help="Attach seed data to existing program ID"
    )
    args = parser.parse_args()

    app = create_app()
    print(f"🎯 Target DB: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print()

    seed_program(app, args.program_id)
    print("\n🏁 Done!")


if __name__ == "__main__":
    main()
