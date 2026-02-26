"""
Cutover Hub — Demo Seed Data
Anadolu Food & Beverage Inc. — SAP S/4HANA Transformation

Two cutover plans:
  CUT-001 — Wave 1 Go-Live (Finance + Procurement) — "executing" status
  CUT-002 — Wave 2 Go-Live (Logistics + Manufacturing) — "draft" status

Plan 1 (CUT-001)  →  5 Scope Items  →  18 Runbook Tasks  →  8 Dependencies
                   →  2 Rehearsals (completed, in_progress)
                   →  7 Go/No-Go items (mixed verdicts)
                   →  6 Hypercare Incidents (mixed status/severity)
                   →  4 SLA Targets (P1–P4)
                   →  2 War Rooms (active, monitoring)
                   →  4 Post Go-Live Change Requests

Plan 2 (CUT-002)  →  3 Scope Items  →  6 Runbook Tasks  →  2 Dependencies
                   →  1 Rehearsal (planned)
                   →  7 Go/No-Go items (all pending)
"""

from datetime import datetime, timedelta, timezone

# ── Helper ──────────────────────────────────────────────────────────────────
_base = datetime(2026, 3, 6, 22, 0, tzinfo=timezone.utc)   # Wave 1 go-live: Fri 6 Mar 2026 22:00 UTC
_base2 = datetime(2026, 6, 12, 22, 0, tzinfo=timezone.utc)  # Wave 2 go-live: Fri 12 Jun 2026 22:00 UTC


# ═════════════════════════════════════════════════════════════════════════════
# CUTOVER PLANS
# ═════════════════════════════════════════════════════════════════════════════

CUTOVER_PLANS = [
    {
        "_key": "plan1",
        "code": "CUT-001",
        "name": "Wave 1 Go-Live — Finance & Procurement",
        "description": (
            "SAP S/4HANA Wave 1 production cutover covering FI/CO, MM, and SRM modules. "
            "56-hour cutover window from Friday 22:00 to Monday 06:00. "
            "Rollback deadline: Sunday 02:00."
        ),
        "status": "executing",
        "version": 3,
        "planned_start": _base,
        "planned_end": _base + timedelta(hours=56),
        "actual_start": _base + timedelta(minutes=12),
        "cutover_manager": "Umut Soyyilmaz",
        "environment": "PRD",
        "rollback_deadline": _base + timedelta(hours=28),
        "rollback_decision_by": "Ahmet Yilmaz",
        "hypercare_start": _base + timedelta(hours=56),
        "hypercare_end": _base + timedelta(hours=56, weeks=4),
        "hypercare_duration_weeks": 4,
        "hypercare_manager": "Elif Demir",
    },
    {
        "_key": "plan2",
        "code": "CUT-002",
        "name": "Wave 2 Go-Live — Logistics & Manufacturing",
        "description": (
            "SAP S/4HANA Wave 2 production cutover covering PP, QM, WM, and SD modules. "
            "48-hour cutover window. Wave 2 depends on Wave 1 hypercare completion."
        ),
        "status": "draft",
        "version": 1,
        "planned_start": _base2,
        "planned_end": _base2 + timedelta(hours=48),
        "cutover_manager": "Mehmet Kaya",
        "environment": "PRD",
        "rollback_deadline": _base2 + timedelta(hours=24),
        "rollback_decision_by": "Ahmet Yilmaz",
        "hypercare_duration_weeks": 6,
        "hypercare_manager": "Zeynep Arslan",
    },
]


# ═════════════════════════════════════════════════════════════════════════════
# SCOPE ITEMS
# ═════════════════════════════════════════════════════════════════════════════

SCOPE_ITEMS = [
    # ── Plan 1: Wave 1 ──────────────────────────────────────────────────
    {"_plan": "plan1", "_key": "si_data",  "name": "Data Migration — Finance Master Data", "category": "data_load",       "owner": "Burak Ozkan",   "order": 1, "description": "GL accounts, cost centers, profit centers, vendor/customer master migration from legacy ECC"},
    {"_plan": "plan1", "_key": "si_iface", "name": "Interface Activation — Banks & EDI",   "category": "interface",       "owner": "Selin Yildiz",  "order": 2, "description": "Bank connectivity, EDI channels, payment gateway interfaces activation"},
    {"_plan": "plan1", "_key": "si_auth",  "name": "Authorization & Role Provisioning",    "category": "authorization",   "owner": "Can Aydin",     "order": 3, "description": "Production role assignment, SOD remediation, emergency access provisioning"},
    {"_plan": "plan1", "_key": "si_jobs",  "name": "Job Scheduling — Batch & Period Close", "category": "job_scheduling", "owner": "Derya Celik",   "order": 4, "description": "SM36/SM37 job chains, period-end close automation, BW extraction schedules"},
    {"_plan": "plan1", "_key": "si_recon", "name": "Reconciliation & Validation Checks",   "category": "reconciliation",  "owner": "Emre Koc",      "order": 5, "description": "Trial balance reconciliation, open item migration validation, intercompany balances"},

    # ── Plan 2: Wave 2 ──────────────────────────────────────────────────
    {"_plan": "plan2", "_key": "si_data2",  "name": "Data Migration — Logistics Master Data",      "category": "data_load",  "owner": "Fatma Sahin",   "order": 1, "description": "Material master, BOM, routing, work center migration"},
    {"_plan": "plan2", "_key": "si_iface2", "name": "Interface Activation — WMS & MES",             "category": "interface",  "owner": "Gokhan Demir",  "order": 2, "description": "Warehouse management system and manufacturing execution system interface go-live"},
    {"_plan": "plan2", "_key": "si_auth2",  "name": "Authorization — Production & Warehouse Roles", "category": "authorization", "owner": "Can Aydin", "order": 3, "description": "PP/QM/WM role provisioning, shop floor authorization"},
]


# ═════════════════════════════════════════════════════════════════════════════
# RUNBOOK TASKS
# ═════════════════════════════════════════════════════════════════════════════

# Task sequence numbering: plan-wide
RUNBOOK_TASKS = [
    # ── si_data: Data Migration ──────────────────────────────────────────
    {"_scope": "si_data", "_key": "t01", "sequence": 10,  "title": "Lock legacy ECC transactions (SPRO/SM01)",                "planned_duration_min": 15,  "responsible": "Burak Ozkan",   "accountable": "Umut Soyyilmaz", "status": "completed", "rollback_action": "Unlock transactions via SM01",
     "planned_start": _base, "planned_end": _base + timedelta(minutes=15)},
    {"_scope": "si_data", "_key": "t02", "sequence": 20,  "title": "Export GL balances from ECC (SE38 / ZFGL_EXPORT)",        "planned_duration_min": 45,  "responsible": "Burak Ozkan",   "accountable": "Derya Celik", "status": "completed",
     "planned_start": _base + timedelta(minutes=15), "planned_end": _base + timedelta(minutes=60)},
    {"_scope": "si_data", "_key": "t03", "sequence": 30,  "title": "Load GL opening balances via LTMC",                       "planned_duration_min": 90,  "responsible": "Burak Ozkan",   "accountable": "Derya Celik", "status": "completed",
     "planned_start": _base + timedelta(hours=1), "planned_end": _base + timedelta(hours=2, minutes=30)},
    {"_scope": "si_data", "_key": "t04", "sequence": 40,  "title": "Load vendor/customer master via S/4 Migration Cockpit",    "planned_duration_min": 120, "responsible": "Emre Koc",      "accountable": "Burak Ozkan", "status": "in_progress",
     "planned_start": _base + timedelta(hours=2, minutes=30), "planned_end": _base + timedelta(hours=4, minutes=30)},
    {"_scope": "si_data", "_key": "t05", "sequence": 50,  "title": "Validate data load — record counts & checksums",           "planned_duration_min": 60,  "responsible": "Emre Koc",      "accountable": "Burak Ozkan", "status": "not_started",
     "planned_start": _base + timedelta(hours=4, minutes=30), "planned_end": _base + timedelta(hours=5, minutes=30)},

    # ── si_iface: Interfaces ─────────────────────────────────────────────
    {"_scope": "si_iface", "_key": "t06", "sequence": 60,  "title": "Activate bank connectivity (payment gateway)",            "planned_duration_min": 30,  "responsible": "Selin Yildiz", "accountable": "Umut Soyyilmaz", "status": "completed",
     "planned_start": _base + timedelta(hours=3), "planned_end": _base + timedelta(hours=3, minutes=30)},
    {"_scope": "si_iface", "_key": "t07", "sequence": 70,  "title": "Enable EDI channels — ORDERS/INVOIC/DESADV",              "planned_duration_min": 45,  "responsible": "Selin Yildiz", "accountable": "Gokhan Demir", "status": "completed",
     "planned_start": _base + timedelta(hours=3, minutes=30), "planned_end": _base + timedelta(hours=4, minutes=15)},
    {"_scope": "si_iface", "_key": "t08", "sequence": 80,  "title": "End-to-end interface smoke test (all channels)",           "planned_duration_min": 60,  "responsible": "Selin Yildiz", "accountable": "Gokhan Demir", "status": "in_progress",
     "planned_start": _base + timedelta(hours=4, minutes=15), "planned_end": _base + timedelta(hours=5, minutes=15)},

    # ── si_auth: Authorization ───────────────────────────────────────────
    {"_scope": "si_auth", "_key": "t09", "sequence": 90,  "title": "Import production role transports (STMS)",                 "planned_duration_min": 20,  "responsible": "Can Aydin",    "accountable": "Umut Soyyilmaz", "status": "completed",
     "planned_start": _base + timedelta(hours=1), "planned_end": _base + timedelta(hours=1, minutes=20)},
    {"_scope": "si_auth", "_key": "t10", "sequence": 100, "title": "Mass user role assignment (SU01 / GRC)",                   "planned_duration_min": 45,  "responsible": "Can Aydin",    "accountable": "Elif Demir", "status": "completed",
     "planned_start": _base + timedelta(hours=1, minutes=20), "planned_end": _base + timedelta(hours=2, minutes=5)},
    {"_scope": "si_auth", "_key": "t11", "sequence": 110, "title": "Enable emergency access (firefighter IDs)",                "planned_duration_min": 15,  "responsible": "Can Aydin",    "accountable": "Elif Demir", "status": "not_started",
     "planned_start": _base + timedelta(hours=2, minutes=5), "planned_end": _base + timedelta(hours=2, minutes=20)},

    # ── si_jobs: Job Scheduling ──────────────────────────────────────────
    {"_scope": "si_jobs", "_key": "t12", "sequence": 120, "title": "Schedule month-end close batch chain (SM36)",              "planned_duration_min": 30,  "responsible": "Derya Celik",  "accountable": "Burak Ozkan", "status": "not_started",
     "planned_start": _base + timedelta(hours=6), "planned_end": _base + timedelta(hours=6, minutes=30)},
    {"_scope": "si_jobs", "_key": "t13", "sequence": 130, "title": "Schedule BW extraction jobs (RSA1)",                       "planned_duration_min": 20,  "responsible": "Derya Celik",  "accountable": "Emre Koc", "status": "not_started",
     "planned_start": _base + timedelta(hours=6, minutes=30), "planned_end": _base + timedelta(hours=6, minutes=50)},
    {"_scope": "si_jobs", "_key": "t14", "sequence": 140, "title": "Validate job chain execution (SM37 monitoring)",           "planned_duration_min": 30,  "responsible": "Derya Celik",  "accountable": "Emre Koc", "status": "not_started",
     "planned_start": _base + timedelta(hours=6, minutes=50), "planned_end": _base + timedelta(hours=7, minutes=20)},

    # ── si_recon: Reconciliation ─────────────────────────────────────────
    {"_scope": "si_recon", "_key": "t15", "sequence": 150, "title": "Run trial balance comparison (ECC vs S/4)",               "planned_duration_min": 60,  "responsible": "Emre Koc",     "accountable": "Burak Ozkan", "status": "not_started",
     "planned_start": _base + timedelta(hours=8), "planned_end": _base + timedelta(hours=9)},
    {"_scope": "si_recon", "_key": "t16", "sequence": 160, "title": "Validate open item migration — AP/AR aging",              "planned_duration_min": 45,  "responsible": "Emre Koc",     "accountable": "Burak Ozkan", "status": "not_started",
     "planned_start": _base + timedelta(hours=9), "planned_end": _base + timedelta(hours=9, minutes=45)},
    {"_scope": "si_recon", "_key": "t17", "sequence": 170, "title": "Intercompany balance reconciliation",                     "planned_duration_min": 30,  "responsible": "Emre Koc",     "accountable": "Derya Celik", "status": "not_started",
     "planned_start": _base + timedelta(hours=9, minutes=45), "planned_end": _base + timedelta(hours=10, minutes=15)},
    {"_scope": "si_recon", "_key": "t18", "sequence": 180, "title": "Sign-off data migration completion report",               "planned_duration_min": 15,  "responsible": "Burak Ozkan",  "accountable": "Umut Soyyilmaz", "status": "not_started",
     "planned_start": _base + timedelta(hours=10, minutes=15), "planned_end": _base + timedelta(hours=10, minutes=30)},

    # ── Plan 2 / si_data2: Logistics Data ───────────────────────────────
    {"_scope": "si_data2", "_key": "t19", "sequence": 10,  "title": "Export material master from ECC",                         "planned_duration_min": 60,  "responsible": "Fatma Sahin",  "accountable": "Mehmet Kaya", "status": "not_started",
     "planned_start": _base2, "planned_end": _base2 + timedelta(hours=1)},
    {"_scope": "si_data2", "_key": "t20", "sequence": 20,  "title": "Load material master via Migration Cockpit",              "planned_duration_min": 120, "responsible": "Fatma Sahin",  "accountable": "Mehmet Kaya", "status": "not_started",
     "planned_start": _base2 + timedelta(hours=1), "planned_end": _base2 + timedelta(hours=3)},

    # ── Plan 2 / si_iface2: WMS & MES ──────────────────────────────────
    {"_scope": "si_iface2", "_key": "t21", "sequence": 30,  "title": "Activate WMS RF interface endpoints",                    "planned_duration_min": 45,  "responsible": "Gokhan Demir", "accountable": "Mehmet Kaya", "status": "not_started",
     "planned_start": _base2 + timedelta(hours=3), "planned_end": _base2 + timedelta(hours=3, minutes=45)},
    {"_scope": "si_iface2", "_key": "t22", "sequence": 40,  "title": "Activate MES production confirmation interface",         "planned_duration_min": 30,  "responsible": "Gokhan Demir", "accountable": "Mehmet Kaya", "status": "not_started",
     "planned_start": _base2 + timedelta(hours=3, minutes=45), "planned_end": _base2 + timedelta(hours=4, minutes=15)},

    # ── Plan 2 / si_auth2: Authorization ────────────────────────────────
    {"_scope": "si_auth2", "_key": "t23", "sequence": 50,  "title": "Import PP/QM/WM role transports",                         "planned_duration_min": 20,  "responsible": "Can Aydin",    "accountable": "Zeynep Arslan", "status": "not_started",
     "planned_start": _base2 + timedelta(hours=1), "planned_end": _base2 + timedelta(hours=1, minutes=20)},
    {"_scope": "si_auth2", "_key": "t24", "sequence": 60,  "title": "Shop floor user provisioning & RF device auth",           "planned_duration_min": 30,  "responsible": "Can Aydin",    "accountable": "Zeynep Arslan", "status": "not_started",
     "planned_start": _base2 + timedelta(hours=1, minutes=20), "planned_end": _base2 + timedelta(hours=1, minutes=50)},
]

# ── Task Dependencies (key → key) ──────────────────────────────────────────

TASK_DEPENDENCIES = [
    # Plan 1: data flow chain
    {"_pred": "t01", "_succ": "t02", "dependency_type": "finish_to_start", "lag_minutes": 0},
    {"_pred": "t02", "_succ": "t03", "dependency_type": "finish_to_start", "lag_minutes": 0},
    {"_pred": "t03", "_succ": "t04", "dependency_type": "finish_to_start", "lag_minutes": 0},
    {"_pred": "t04", "_succ": "t05", "dependency_type": "finish_to_start", "lag_minutes": 0},
    # Interfaces after data is loaded
    {"_pred": "t05", "_succ": "t08", "dependency_type": "finish_to_start", "lag_minutes": 15},
    # Auth can happen in parallel, but firefighter after roles
    {"_pred": "t10", "_succ": "t11", "dependency_type": "finish_to_start", "lag_minutes": 0},
    # Reconciliation after data + interfaces validated
    {"_pred": "t05", "_succ": "t15", "dependency_type": "finish_to_start", "lag_minutes": 30},
    # Sign-off after all reconciliation
    {"_pred": "t17", "_succ": "t18", "dependency_type": "finish_to_start", "lag_minutes": 0},

    # Plan 2: material flow
    {"_pred": "t19", "_succ": "t20", "dependency_type": "finish_to_start", "lag_minutes": 0},
    {"_pred": "t20", "_succ": "t21", "dependency_type": "finish_to_start", "lag_minutes": 15},
]


# ═════════════════════════════════════════════════════════════════════════════
# REHEARSALS
# ═════════════════════════════════════════════════════════════════════════════

REHEARSALS = [
    {
        "_plan": "plan1",
        "rehearsal_number": 1,
        "name": "Rehearsal 1 — Dry Run (QAS)",
        "description": "First full cutover rehearsal in QAS environment. Focus on timing accuracy and data load sequence.",
        "status": "completed",
        "environment": "QAS",
        "planned_start": _base - timedelta(weeks=4),
        "planned_end": _base - timedelta(weeks=4) + timedelta(hours=56),
        "planned_duration_min": 3360,
        "actual_start": _base - timedelta(weeks=4) + timedelta(minutes=5),
        "actual_end": _base - timedelta(weeks=4) + timedelta(hours=52),
        "actual_duration_min": 3115,
        "total_tasks": 18,
        "completed_tasks": 16,
        "failed_tasks": 1,
        "skipped_tasks": 1,
        "duration_variance_pct": -7.3,
        "runbook_revision_needed": True,
        "findings_summary": (
            "Rehearsal completed 4 hours ahead of schedule. GL load task failed due to currency conversion mapping — "
            "fixed in transport CTS-4521. EDI activation took longer than planned (60 min vs 45 min planned). "
            "Recommendation: add 15 min buffer to interface tasks. Reconciliation sign-off process needs clarity."
        ),
    },
    {
        "_plan": "plan1",
        "rehearsal_number": 2,
        "name": "Rehearsal 2 — Dress Rehearsal (QAS)",
        "description": "Final dress rehearsal with all stakeholders. Includes communication plan and war-room simulation.",
        "status": "completed",
        "environment": "QAS",
        "planned_start": _base - timedelta(weeks=2),
        "planned_end": _base - timedelta(weeks=2) + timedelta(hours=56),
        "planned_duration_min": 3360,
        "actual_start": _base - timedelta(weeks=2) + timedelta(minutes=2),
        "actual_end": _base - timedelta(weeks=2) + timedelta(hours=54, minutes=30),
        "actual_duration_min": 3268,
        "total_tasks": 18,
        "completed_tasks": 18,
        "failed_tasks": 0,
        "skipped_tasks": 0,
        "duration_variance_pct": -2.7,
        "runbook_revision_needed": False,
        "findings_summary": (
            "All tasks completed successfully within tolerance. GL load timing improved after transport fix. "
            "Communication plan executed as designed — all stakeholders received status updates on schedule. "
            "Recommendation: proceed to go-live readiness review."
        ),
    },
    {
        "_plan": "plan2",
        "rehearsal_number": 1,
        "name": "Rehearsal 1 — Logistics Dry Run (QAS)",
        "description": "First logistics cutover rehearsal. Focus on material master load and WMS connectivity.",
        "status": "planned",
        "environment": "QAS",
        "planned_start": _base2 - timedelta(weeks=3),
        "planned_end": _base2 - timedelta(weeks=3) + timedelta(hours=48),
        "planned_duration_min": 2880,
    },
]


# ═════════════════════════════════════════════════════════════════════════════
# GO/NO-GO ITEMS
# ═════════════════════════════════════════════════════════════════════════════

GO_NO_GO_ITEMS = [
    # ── Plan 1: Wave 1 — mostly "go" ───────────────────────────────────
    {"_plan": "plan1", "source_domain": "test_management",     "criterion": "Open P1/P2 Defects = 0",                  "verdict": "go",       "evidence": "0 P1, 0 P2 defects open as of 2026-03-05 18:00 UTC",                    "evaluated_by": "Elif Demir",     "evaluated_at": _base - timedelta(hours=4)},
    {"_plan": "plan1", "source_domain": "data_factory",        "criterion": "Data Load Reconciliation Passed",          "verdict": "go",       "evidence": "Trial balance delta: 0.02% — within 0.1% tolerance",                    "evaluated_by": "Burak Ozkan",    "evaluated_at": _base - timedelta(hours=3)},
    {"_plan": "plan1", "source_domain": "integration_factory",  "criterion": "Interface Connectivity Verified",         "verdict": "go",       "evidence": "All 12 interfaces passed E2E connectivity test on 2026-03-04",          "evaluated_by": "Selin Yildiz",   "evaluated_at": _base - timedelta(hours=3)},
    {"_plan": "plan1", "source_domain": "security",            "criterion": "Authorization Readiness Complete",          "verdict": "no_go",    "evidence": "12 SOD conflicts outstanding — remediation ETA Sunday 06:00. 234 users provisioned but UAM sign-off blocked.", "evaluated_by": "Can Aydin",      "evaluated_at": _base - timedelta(hours=5)},
    {"_plan": "plan1", "source_domain": "training",            "criterion": "Training Completion ≥ 90%",                "verdict": "pending",  "evidence": "Training completion: 87.3% (target: 90%) — 14 users pending, crash session scheduled Saturday 09:00",  "evaluated_by": "Zeynep Arslan",  "evaluated_at": _base - timedelta(hours=6)},
    {"_plan": "plan1", "source_domain": "cutover_rehearsal",   "criterion": "Cutover Rehearsal Within Tolerance",       "verdict": "go",       "evidence": "Rehearsal 2 completed -2.7% variance (target: ±15%)",                   "evaluated_by": "Umut Soyyilmaz", "evaluated_at": _base - timedelta(hours=2)},
    {"_plan": "plan1", "source_domain": "steering_signoff",    "criterion": "Steering Committee Sign-off",              "verdict": "go",       "evidence": "Formal approval received 2026-03-05 in steering meeting #14",           "evaluated_by": "Ahmet Yilmaz",   "evaluated_at": _base - timedelta(hours=2)},

    # ── Plan 2: Wave 2 — all pending ───────────────────────────────────
    {"_plan": "plan2", "source_domain": "test_management",     "criterion": "Open P1/P2 Defects = 0",                  "verdict": "pending"},
    {"_plan": "plan2", "source_domain": "data_factory",        "criterion": "Data Load Reconciliation Passed",          "verdict": "pending"},
    {"_plan": "plan2", "source_domain": "integration_factory",  "criterion": "Interface Connectivity Verified",         "verdict": "pending"},
    {"_plan": "plan2", "source_domain": "security",            "criterion": "Authorization Readiness Complete",          "verdict": "pending"},
    {"_plan": "plan2", "source_domain": "training",            "criterion": "Training Completion ≥ 90%",                "verdict": "pending"},
    {"_plan": "plan2", "source_domain": "cutover_rehearsal",   "criterion": "Cutover Rehearsal Within Tolerance",       "verdict": "pending"},
    {"_plan": "plan2", "source_domain": "steering_signoff",    "criterion": "Steering Committee Sign-off",              "verdict": "pending"},
]


# ═════════════════════════════════════════════════════════════════════════════
# HYPERCARE INCIDENTS (Plan 1 only — in hypercare/executing)
# ═════════════════════════════════════════════════════════════════════════════

_go_live = _base + timedelta(hours=56)  # Monday 06:00 — hypercare starts

HYPERCARE_INCIDENTS = [
    {
        "_plan": "plan1",
        "code": "INC-001",
        "title": "Payment run F110 failing — missing bank key mapping",
        "description": "Automatic payment program F110 fails for vendor group ZDOM with error 'Bank key not found'. Affects 45 vendors.",
        "severity": "P1",
        "category": "functional",
        "status": "resolved",
        "reported_by": "Burak Ozkan",
        "reported_at": _go_live + timedelta(hours=2),
        "assigned_to": "Selin Yildiz",
        "resolution": "Missing bank key mapping in FBZP config — transport CTS-4589 applied. All 45 vendors now process correctly.",
        "resolved_at": _go_live + timedelta(hours=5, minutes=30),
        "resolved_by": "Selin Yildiz",
        "response_time_min": 8,
        "resolution_time_min": 210,
    },
    {
        "_plan": "plan1",
        "code": "INC-002",
        "title": "Cost center report KSB1 shows wrong currency",
        "description": "Cost center actual report shows amounts in USD instead of TRY for company code 1000.",
        "severity": "P2",
        "category": "functional",
        "status": "resolved",
        "reported_by": "Derya Celik",
        "reported_at": _go_live + timedelta(hours=8),
        "assigned_to": "Emre Koc",
        "resolution": "Controlling area currency settings corrected in OKKP. Report now displays TRY as expected.",
        "resolved_at": _go_live + timedelta(hours=14),
        "resolved_by": "Emre Koc",
        "response_time_min": 15,
        "resolution_time_min": 360,
    },
    {
        "_plan": "plan1",
        "code": "INC-003",
        "title": "EDI INVOIC inbound idoc stuck in status 51",
        "description": "Vendor EDI invoices arriving but partner profile not processing — 23 idocs stuck in status 51.",
        "severity": "P2",
        "category": "technical",
        "status": "closed",
        "reported_by": "Selin Yildiz",
        "reported_at": _go_live + timedelta(days=1, hours=3),
        "assigned_to": "Gokhan Demir",
        "resolution": "Partner profile for INVOIC message type was inactive in WE20. Activated and reprocessed all 23 idocs successfully.",
        "resolved_at": _go_live + timedelta(days=1, hours=6),
        "resolved_by": "Gokhan Demir",
        "response_time_min": 22,
        "resolution_time_min": 180,
    },
    {
        "_plan": "plan1",
        "code": "INC-004",
        "title": "User cannot post to profit center 4200 — authorization error",
        "description": "Finance team lead reports authorization error when posting to profit center 4200 (Procurement shared services).",
        "severity": "P3",
        "category": "authorization",
        "status": "investigating",
        "reported_by": "Can Aydin",
        "reported_at": _go_live + timedelta(days=2, hours=5),
        "assigned_to": "Can Aydin",
        "response_time_min": 45,
    },
    {
        "_plan": "plan1",
        "code": "INC-005",
        "title": "BW extraction delta job running slow (>4 hrs)",
        "description": "BW delta extraction for 0FI_GL_14 running 4+ hours instead of expected 45 minutes after go-live data volume.",
        "severity": "P3",
        "category": "performance",
        "status": "open",
        "reported_by": "Derya Celik",
        "reported_at": _go_live + timedelta(days=3, hours=1),
        "assigned_to": "Emre Koc",
    },
    {
        "_plan": "plan1",
        "code": "INC-006",
        "title": "Minor: FI document display shows old field label",
        "description": "FB03 document display shows legacy field label 'Region Code' instead of new label 'Segment'. Cosmetic only.",
        "severity": "P4",
        "category": "functional",
        "status": "open",
        "reported_by": "Burak Ozkan",
        "reported_at": _go_live + timedelta(days=4),
        "assigned_to": "Elif Demir",
    },
]


# ═════════════════════════════════════════════════════════════════════════════
# SLA TARGETS (Plan 1 — standard SAP)
# ═════════════════════════════════════════════════════════════════════════════

SLA_TARGETS = [
    {"_plan": "plan1", "severity": "P1", "response_target_min": 15,  "resolution_target_min": 240,  "escalation_after_min": 10,  "escalation_to": "Hypercare Manager — Elif Demir", "notes": "Critical — system down or data loss risk"},
    {"_plan": "plan1", "severity": "P2", "response_target_min": 30,  "resolution_target_min": 480,  "escalation_after_min": 20,  "escalation_to": "Hypercare Manager — Elif Demir", "notes": "High — core function impacted, workaround possible"},
    {"_plan": "plan1", "severity": "P3", "response_target_min": 240, "resolution_target_min": 1440, "escalation_after_min": 120, "escalation_to": "Module Lead",                     "notes": "Medium — secondary function impacted"},
    {"_plan": "plan1", "severity": "P4", "response_target_min": 480, "resolution_target_min": 2400, "escalation_after_min": 240, "escalation_to": "Module Lead",                     "notes": "Low — cosmetic or enhancement request"},
]


# ═════════════════════════════════════════════════════════════════════════════
# WAR ROOMS (Plan 1 — active hypercare)
# ═════════════════════════════════════════════════════════════════════════════

WAR_ROOMS = [
    {
        "_plan": "plan1",
        "_key": "wr1",
        "code": "WR-001",
        "name": "FI Payment & Bank Integration Issues",
        "description": (
            "War room for payment run failures and bank connectivity issues "
            "discovered during Wave 1 hypercare. Covers F110, FBZP config, "
            "and bank key mapping problems."
        ),
        "status": "active",
        "priority": "P1",
        "affected_module": "FI",
        "war_room_lead": "Selin Yildiz",
        "opened_at": _go_live + timedelta(hours=2),
        # Incidents INC-001 and INC-002 will be assigned to this war room
        "_assign_incidents": ["INC-001", "INC-002"],
        "_assign_crs": ["CR-001"],
    },
    {
        "_plan": "plan1",
        "_key": "wr2",
        "code": "WR-002",
        "name": "EDI & Interface Stabilization",
        "description": (
            "War room for EDI and interface issues post go-live. "
            "Monitoring partner profiles, idoc processing, and "
            "BW extraction performance."
        ),
        "status": "monitoring",
        "priority": "P2",
        "affected_module": "MM",
        "war_room_lead": "Gokhan Demir",
        "opened_at": _go_live + timedelta(days=1, hours=3),
        # Incidents INC-003 and INC-005 will be assigned to this war room
        "_assign_incidents": ["INC-003", "INC-005"],
        "_assign_crs": ["CR-002", "CR-003"],
    },
]


# ═════════════════════════════════════════════════════════════════════════════
# POST GO-LIVE CHANGE REQUESTS (Plan 1 — raised during hypercare)
# ═════════════════════════════════════════════════════════════════════════════

CHANGE_REQUESTS = [
    {
        "_plan": "plan1",
        "_key": "CR-001",
        "cr_number": "CR-001",
        "title": "Add missing bank key mapping for domestic vendors",
        "description": (
            "Root cause fix for INC-001. Need to add 12 missing bank key mappings "
            "in FBZP configuration and transport to PRD."
        ),
        "priority": "P1",
        "status": "approved",
        "category": "config_change",
        "requested_by": "Selin Yildiz",
        "assigned_to": "Burak Ozkan",
        "requested_at": _go_live + timedelta(hours=6),
        "module": "FI",
        "impact_assessment": "Low risk — config-only change, no code modification",
    },
    {
        "_plan": "plan1",
        "_key": "CR-002",
        "cr_number": "CR-002",
        "title": "Reactivate EDI partner profiles for 3 new vendors",
        "description": (
            "Three vendors onboarded post-cutover need WE20 partner profiles created "
            "for ORDERS and INVOIC message types."
        ),
        "priority": "P2",
        "status": "in_review",
        "category": "config_change",
        "requested_by": "Gokhan Demir",
        "assigned_to": "Selin Yildiz",
        "requested_at": _go_live + timedelta(days=2),
        "module": "MM",
        "impact_assessment": "Low risk — standard partner profile creation",
    },
    {
        "_plan": "plan1",
        "_key": "CR-003",
        "cr_number": "CR-003",
        "title": "Optimize BW delta extraction for 0FI_GL_14",
        "description": (
            "BW delta extraction running 4+ hours instead of 45 min. "
            "Need to implement selection optimization and parallel extraction."
        ),
        "priority": "P2",
        "status": "submitted",
        "category": "performance",
        "requested_by": "Derya Celik",
        "assigned_to": "Emre Koc",
        "requested_at": _go_live + timedelta(days=3, hours=2),
        "module": "BW",
        "impact_assessment": "Medium risk — extraction logic change, requires regression test",
    },
    {
        "_plan": "plan1",
        "_key": "CR-004",
        "cr_number": "CR-004",
        "title": "Add profit center 4200 to authorization role Z_FI_LEAD",
        "description": (
            "Finance team lead role missing authorization for profit center 4200 (Procurement shared services). "
            "Need PFCG role update and transport."
        ),
        "priority": "P3",
        "status": "submitted",
        "category": "authorization",
        "requested_by": "Can Aydin",
        "assigned_to": "Can Aydin",
        "requested_at": _go_live + timedelta(days=2, hours=6),
        "module": "FI",
        "impact_assessment": "Low risk — role authorization object value addition only",
    },
]
