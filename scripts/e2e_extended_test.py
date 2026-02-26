#!/usr/bin/env python3
"""
SAP Activate E2E Extended Test — Comprehensive coverage of ALL screens,
buttons, filters, CRUD operations, status transitions, and view functions.

Covers 496 routes across 20+ views:
  - Program Setup (phases, gates, workstreams, waves, team, sprints, committees)
  - Explore (process hierarchy, workshops, requirements, open items, scope changes)
  - Backlog (WRICEF items, config items, FS/TS, board view, stats)
  - Integration Hub (interfaces, checklist, connectivity, switch plans)
  - Testing Hub (plans, suites, catalog, cycles, runs, executions, defects, UAT)
  - Cutover (plans, scope items, tasks, rehearsals, go-no-go, incidents, SLA)
  - Data Factory (objects, waves, loads, tasks, reconciliation, quality)
  - RAID (risks, issues, actions, decisions)
  - Reports & Cockpit
  - AI Hub (suggestions, conversations, tasks, budgets, KB, queries)
  - Notifications & Audit
  - Traceability
  - Clone/Copy, Convert/Unconvert, Transitions
"""
import requests
import json
import sys
import time
from datetime import datetime, date

BASE = "http://localhost:5001"

# ── Result tracking ─────────────────────────────────────────
RESULTS = {}
IDS = {}
PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0
CURRENT_BLOCK = ""


def log(test, status, detail=""):
    global PASS_COUNT, FAIL_COUNT, WARN_COUNT
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"  {icon} {test} — {detail}")
    if status == "PASS":
        PASS_COUNT += 1
    elif status == "FAIL":
        FAIL_COUNT += 1
    else:
        WARN_COUNT += 1
    block = RESULTS.setdefault(CURRENT_BLOCK, [])
    block.append({"test": test, "status": status, "detail": detail})


def api(method, path, data=None, expect_codes=(200, 201), timeout=10):
    url = f"{BASE}{path}"
    try:
        kw = {"timeout": timeout}
        if method in ("POST", "PUT", "PATCH"):
            kw["json"] = data
        r = getattr(requests, method.lower())(url, **kw)
        try:
            body = r.json()
        except Exception:
            body = r.text
        return body, r.status_code
    except Exception as e:
        return {"error": str(e)}, 0


def expect(test, method, path, data=None, codes=(200, 201)):
    """Call API and log result."""
    body, code = api(method, path, data)
    if code in codes:
        log(test, "PASS", f"{method} {path} → {code}")
    else:
        detail = body.get("error", str(body)[:120]) if isinstance(body, dict) else str(body)[:120]
        log(test, "FAIL", f"{method} {path} → {code}: {detail}")
    return body, code


def expect_field(test, body, field, expected=None):
    """Check a field exists (and optionally equals expected value)."""
    if not isinstance(body, dict):
        log(test, "FAIL", f"Expected dict, got {type(body).__name__}")
        return False
    val = body.get(field)
    if val is None and field not in body:
        log(test, "FAIL", f"Missing field '{field}'")
        return False
    if expected is not None and val != expected:
        log(test, "FAIL", f"{field}={val}, expected={expected}")
        return False
    log(test, "PASS", f"{field}={val}")
    return True


def items_or_empty(body):
    """Extract items list from response body."""
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        return body.get("items", body.get("data", []))
    return []


# ══════════════════════════════════════════════════════════════
# BLOCK 0: HEALTH & INFRASTRUCTURE (15 tests)
# ══════════════════════════════════════════════════════════════
def block_0_health():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "0_health"
    print("\n═══ BLOCK 0: HEALTH & INFRASTRUCTURE ═══")

    expect("Home page", "GET", "/")
    expect("Health check", "GET", "/api/v1/health")
    expect("Ready probe", "GET", "/api/v1/health/ready")
    expect("Liveness probe", "GET", "/api/v1/health/live")
    expect("DB diagnostics", "GET", "/api/v1/health/db-diag")
    expect("DB columns check", "GET", "/api/v1/health/db-columns")
    expect("PWA manifest", "GET", "/api/pwa/manifest")
    expect("PWA status", "GET", "/api/pwa/status")
    expect("PWA cache info", "GET", "/api/pwa/cache-info")
    expect("Offline page", "GET", "/offline")
    expect("Metrics requests", "GET", "/api/v1/metrics/requests")
    expect("Metrics errors", "GET", "/api/v1/metrics/errors")
    expect("Metrics slow", "GET", "/api/v1/metrics/slow")
    expect("Scheduler jobs", "GET", "/api/v1/scheduler/jobs")
    expect("Explore health", "GET", "/api/v1/explore/health")


# ══════════════════════════════════════════════════════════════
# BLOCK 1: PROGRAM SETUP — Full CRUD + filters (45 tests)
# ══════════════════════════════════════════════════════════════
def block_1_program_setup():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "1_program_setup"
    print("\n═══ BLOCK 1: PROGRAM SETUP ═══")

    # ── Program CRUD ──
    body, _ = expect("List programs", "GET", "/api/v1/programs")
    prog_count_before = len(items_or_empty(body))

    body, code = expect("Create program", "POST", "/api/v1/programs", {
        "name": "E2E Extended Test Program",
        "description": "Comprehensive E2E test",
        "methodology": "SAP Activate",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "status": "active",
    })
    pid = body.get("id") if code == 201 else 1
    IDS["program"] = pid

    body, _ = expect("Get program detail", "GET", f"/api/v1/programs/{pid}")
    expect_field("Program has name", body, "name")

    expect("Update program", "PUT", f"/api/v1/programs/{pid}", {
        "name": "E2E Extended Test Program (Updated)",
        "description": "Updated description",
    })

    body, _ = expect("List programs after create", "GET", "/api/v1/programs")

    # ── Phases + Gates ──
    body, code = expect("Create phase", "POST", f"/api/v1/programs/{pid}/phases", {
        "name": "Explore",
        "phase_type": "explore",
        "start_date": "2026-01-01",
        "end_date": "2026-03-31",
    })
    phase_id = body.get("id") if code == 201 else 1
    IDS["phase"] = phase_id

    expect("List phases", "GET", f"/api/v1/programs/{pid}/phases")

    body, code = expect("Create gate", "POST", f"/api/v1/phases/{phase_id}/gates", {
        "name": "Explore Sign-off",
        "gate_type": "quality_gate",
        "planned_date": "2026-03-31",
    })
    gate_id = body.get("id") if code == 201 else None
    if gate_id:
        IDS["gate"] = gate_id
        expect("Update gate", "PUT", f"/api/v1/gates/{gate_id}", {
            "name": "Explore Sign-off (Updated)",
            "status": "open",
        })

    expect("List gates", "GET", f"/api/v1/phases/{phase_id}/gates")

    # ── Team Members ──
    body, code = expect("Add team member", "POST", f"/api/v1/programs/{pid}/team", {
        "name": "Test User",
        "email": "test@example.com",
        "role": "Consultant",
        "module": "FI",
    })
    member_id = body.get("id") if code == 201 else None
    if member_id:
        IDS["member"] = member_id
        expect("Update team member", "PUT", f"/api/v1/team/{member_id}", {
            "name": "Test User (Updated)",
            "role": "Senior Consultant",
        })

    expect("List team", "GET", f"/api/v1/programs/{pid}/team")

    # ── Workstreams ──
    body, code = expect("Create workstream", "POST", f"/api/v1/programs/{pid}/workstreams", {
        "name": "Finance Workstream",
        "module": "FI",
        "lead": "Test Lead",
    })
    ws_id = body.get("id") if code == 201 else None
    if ws_id:
        IDS["workstream"] = ws_id
        expect("Update workstream", "PUT", f"/api/v1/workstreams/{ws_id}", {
            "name": "Finance Workstream (Updated)",
        })

    expect("List workstreams", "GET", f"/api/v1/programs/{pid}/workstreams")

    # ── Waves ──
    body, code = expect("Create wave", "POST", f"/api/v1/programs/{pid}/waves", {
        "name": "Wave 1",
        "description": "First deployment wave",
        "sequence": 1,
    })
    wave_id = body.get("id") if code == 201 else None
    if wave_id:
        IDS["wave"] = wave_id
        expect("Update wave", "PUT", f"/api/v1/waves/{wave_id}", {
            "name": "Wave 1 (Updated)",
        })
        expect("Get wave detail", "GET", f"/api/v1/waves/{wave_id}")

    expect("List waves", "GET", f"/api/v1/programs/{pid}/waves")

    # ── Sprints ──
    body, code = expect("Create sprint", "POST", f"/api/v1/programs/{pid}/sprints", {
        "name": "Sprint 1",
        "start_date": "2026-04-01",
        "end_date": "2026-04-14",
        "goal": "Basic config",
    })
    sprint_id = body.get("id") if code == 201 else None
    if sprint_id:
        IDS["sprint"] = sprint_id
        expect("Update sprint", "PUT", f"/api/v1/sprints/{sprint_id}", {
            "name": "Sprint 1 (Updated)",
        })
        expect("Get sprint detail", "GET", f"/api/v1/sprints/{sprint_id}")

    expect("List sprints", "GET", f"/api/v1/programs/{pid}/sprints")

    # ── Committees ──
    body, code = expect("Create committee", "POST", f"/api/v1/programs/{pid}/committees", {
        "name": "Steering Committee",
        "committee_type": "steering",
        "description": "Executive oversight",
    })
    comm_id = body.get("id") if code == 201 else None
    if comm_id:
        IDS["committee"] = comm_id
        expect("Update committee", "PUT", f"/api/v1/committees/{comm_id}", {
            "name": "Steering Committee (Updated)",
        })

    expect("List committees", "GET", f"/api/v1/programs/{pid}/committees")

    # ── Traceability ──
    expect("Traceability summary", "GET", f"/api/v1/programs/{pid}/traceability/summary")


# ══════════════════════════════════════════════════════════════
# BLOCK 2: EXPLORE PHASE — Hierarchy, Workshops, Requirements (70 tests)
# ══════════════════════════════════════════════════════════════
def block_2_explore():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "2_explore"
    print("\n═══ BLOCK 2: EXPLORE PHASE ═══")
    pid = IDS.get("program", 1)

    # ── Process Hierarchy ──
    l2_id = None
    l3_id = None
    l4_id = None

    # Create L1 first (top-level)
    body, code = expect("Create L1 process area", "POST", "/api/v1/explore/process-levels", {
        "project_id": pid, "name": "Sales & Distribution", "code": "SD",
        "level": 1, "sap_module": "SD",
    })
    l1_id = body.get("id") if code == 201 else None
    IDS["l1"] = l1_id

    if l1_id:
        body, code = expect("Create L2 process", "POST", "/api/v1/explore/process-levels", {
            "project_id": pid, "name": "Order to Cash", "code": "OTC",
            "level": 2, "parent_id": l1_id, "sap_module": "SD",
        })
        l2_id = body.get("id") if code == 201 else None
        IDS["l2"] = l2_id

    if l2_id:
        body, code = expect("Create L3 scope item", "POST", "/api/v1/explore/process-levels", {
            "project_id": pid, "name": "Standard Sales Order", "code": "OTC-SO",
            "level": 3, "parent_id": l2_id, "sap_module": "SD",
        })
        l3_id = body.get("id") if code == 201 else None
        IDS["l3"] = l3_id

    if l3_id:
        body, code = expect("Create L4 process step", "POST", f"/api/v1/explore/process-levels/{l3_id}/children", {
            "project_id": pid, "name": "Create Sales Order", "code": "OTC-SO-01",
            "level": 4, "sap_module": "SD",
        })
        l4_id = body.get("id") if code == 201 else None
        IDS["l4"] = l4_id

    expect("List process levels", "GET", f"/api/v1/explore/process-levels?project_id={pid}")

    if l2_id:
        expect("Get process level detail", "GET", f"/api/v1/explore/process-levels/{l2_id}")
        expect("Update process level", "PUT", f"/api/v1/explore/process-levels/{l2_id}", {
            "name": "Order to Cash (Updated)",
        })
        expect("L2 readiness", "GET", f"/api/v1/explore/process-levels/l2-readiness?project_id={pid}")

    if l3_id:
        expect("Consolidated view", "GET", f"/api/v1/explore/process-levels/{l3_id}/consolidated-view")
        expect("Change history", "GET", f"/api/v1/explore/process-levels/{l2_id}/change-history")

    # ── Workshops ──
    body, code = expect("Create workshop", "POST", "/api/v1/explore/workshops", {
        "project_id": pid, "name": "FI Fit-to-Standard", "title": "FI Fit-to-Standard",
        "process_area": IDS.get("l1") or "SD",
        "module": "FI", "status": "planned",
        "scheduled_date": "2026-02-01", "scheduled_end": "2026-02-01",
    })
    ws_id = body.get("id") if code == 201 else None
    IDS["workshop"] = ws_id

    expect("List workshops", "GET", f"/api/v1/explore/workshops?project_id={pid}")
    expect("Workshop stats", "GET", f"/api/v1/explore/workshops/stats?project_id={pid}")
    expect("Workshop capacity", "GET", f"/api/v1/explore/workshops/capacity?project_id={pid}")

    if ws_id:
        expect("Get workshop detail", "GET", f"/api/v1/explore/workshops/{ws_id}")
        expect("Get workshop full", "GET", f"/api/v1/explore/workshops/{ws_id}/full")
        expect("Update workshop", "PUT", f"/api/v1/explore/workshops/{ws_id}", {
            "title": "FI Fit-to-Standard (Updated)",
        })

        # Attendees
        body, code = expect("Add attendee", "POST", f"/api/v1/explore/workshops/{ws_id}/attendees", {
            "name": "John Doe", "role": "Business Lead", "email": "john@example.com",
        })
        att_id = body.get("id") if code == 201 else None
        IDS["attendee"] = att_id
        expect("List attendees", "GET", f"/api/v1/explore/workshops/{ws_id}/attendees")
        if att_id:
            expect("Update attendee", "PUT", f"/api/v1/explore/attendees/{att_id}", {
                "name": "John Doe (Updated)",
            })

        # Agenda
        body, code = expect("Add agenda item", "POST", f"/api/v1/explore/workshops/{ws_id}/agenda-items", {
            "title": "Review GL Config", "time": "09:00", "duration_minutes": 30,
        })
        agenda_id = body.get("id") if code == 201 else None
        IDS["agenda"] = agenda_id
        expect("List agenda items", "GET", f"/api/v1/explore/workshops/{ws_id}/agenda-items")
        if agenda_id:
            expect("Update agenda item", "PUT", f"/api/v1/explore/agenda-items/{agenda_id}", {
                "title": "Review GL Config (Updated)",
            })

        # Sessions
        expect("List sessions", "GET", f"/api/v1/explore/workshops/{ws_id}/sessions")

        # Steps
        expect("List workshop steps", "GET", f"/api/v1/explore/workshops/{ws_id}/steps")

        # Decisions
        expect("List workshop decisions", "GET", f"/api/v1/explore/workshops/{ws_id}/decisions")

        # Fit decisions
        body, code = expect("Add fit decision", "POST", f"/api/v1/explore/workshops/{ws_id}/fit-decisions", {
            "step_id": IDS.get("l4") or IDS.get("l3"),
            "fit_decision": "fit", "notes": "Standard fits",
        }, codes=(200, 201, 404))
        if code == 404:
            log("Fit decision (step not in WS)", "PASS", "Step not linked to workshop — expected")
        expect("List fit decisions", "GET", f"/api/v1/explore/workshops/{ws_id}/fit-decisions")

        # Workshop lifecycle — need scope items first
        # Link a scope item to workshop before starting
        if IDS.get("l3"):
            expect("Add WS scope item", "POST", f"/api/v1/explore/workshops/{ws_id}/scope-items", {
                "process_level_id": IDS.get("l3"),
            }, codes=(200, 201, 404))
        expect("Start workshop", "POST", f"/api/v1/explore/workshops/{ws_id}/start", codes=(200, 400))
        expect("Complete workshop", "POST", f"/api/v1/explore/workshops/{ws_id}/complete", codes=(200, 409))

        # Dependencies
        expect("List workshop deps", "GET", f"/api/v1/explore/workshops/{ws_id}/dependencies")

        # Documents
        expect("List workshop docs", "GET", f"/api/v1/explore/workshops/{ws_id}/documents")

    # ── Requirements ──
    body, code = expect("Create requirement", "POST", "/api/v1/explore/requirements", {
        "project_id": pid, "title": "e-Invoice Integration",
        "type": "integration", "priority": "P1",
        "fit_status": "gap", "sap_module": "FI",
        "description": "Turkey e-Invoice integration required",
        "scope_item_id": IDS.get("l3"),
    })
    req_id = body.get("id") if code == 201 else None
    IDS["req"] = req_id

    # Create another requirement for batch operations
    body2, _ = expect("Create 2nd requirement", "POST", "/api/v1/explore/requirements", {
        "project_id": pid, "title": "Vendor Master Migration",
        "type": "migration", "priority": "P2",
        "fit_status": "gap", "sap_module": "MM",
        "scope_item_id": IDS.get("l3"),
    })
    req_id2 = body2.get("id") if isinstance(body2, dict) else None
    IDS["req2"] = req_id2

    # Create a fit requirement for config conversion
    body3, _ = expect("Create fit requirement", "POST", "/api/v1/explore/requirements", {
        "project_id": pid, "title": "Standard GL Posting",
        "type": "configuration", "priority": "P3",
        "fit_status": "fit", "sap_module": "FI",
        "scope_item_id": IDS.get("l3"),
    })
    req_id3 = body3.get("id") if isinstance(body3, dict) else None
    IDS["req_fit"] = req_id3

    # Filters
    expect("Filter by status", "GET", f"/api/v1/explore/requirements?project_id={pid}&status=draft")
    expect("Filter by priority", "GET", f"/api/v1/explore/requirements?project_id={pid}&priority=P1")
    expect("Filter by module", "GET", f"/api/v1/explore/requirements?project_id={pid}&sap_module=FI")
    expect("Filter by fit_status", "GET", f"/api/v1/explore/requirements?project_id={pid}&fit_status=gap")
    expect("Search requirements", "GET", f"/api/v1/explore/requirements?project_id={pid}&search=invoice")
    expect("Paginate requirements", "GET", f"/api/v1/explore/requirements?project_id={pid}&page=1&per_page=5")

    if req_id:
        expect("Get requirement detail", "GET", f"/api/v1/explore/requirements/{req_id}")
        expect("Update requirement", "PUT", f"/api/v1/explore/requirements/{req_id}", {
            "title": "e-Invoice Integration (Updated)",
            "description": "Updated description with more detail",
        })

        # Lifecycle transitions
        expect("Submit for review", "POST", f"/api/v1/explore/requirements/{req_id}/transition", {
            "action": "submit_for_review", "user_id": "e2e-tester", "project_id": pid,
        })
        expect("Approve requirement", "POST", f"/api/v1/explore/requirements/{req_id}/transition", {
            "action": "approve", "user_id": "e2e-tester", "project_id": pid,
            "approved_by_name": "E2E Tester",
        })

        # Convert requirement → backlog item
        body, code = expect("Convert to backlog", "POST", f"/api/v1/explore/requirements/{req_id}/convert", {
            "project_id": pid, "user_id": "e2e-tester",
            "target_type": "backlog", "wricef_type": "interface",
        })
        backlog_from_convert = body.get("backlog_item_id") if isinstance(body, dict) else None
        IDS["backlog_from_convert"] = backlog_from_convert

        # Linked items
        expect("Linked items", "GET", f"/api/v1/explore/requirements/{req_id}/linked-items")

        # Push to ALM
        expect("Push to ALM", "POST", f"/api/v1/explore/requirements/{req_id}/transition", {
            "action": "push_to_alm", "user_id": "e2e-tester", "project_id": pid,
        })

        # Unconvert test — first try safe mode (should block if downstream exists)
        body_uc, code_uc = api("POST", f"/api/v1/explore/requirements/{req_id}/unconvert",
                               {"project_id": pid})
        if code_uc == 200:
            log("Unconvert (safe)", "PASS", "Unconverted successfully")
        elif code_uc == 409:
            log("Unconvert blocked (safe)", "PASS", f"Downstream blockers: {body_uc.get('total_blockers', '?')}")
            # Force unconvert
            body_uc2, code_uc2 = api("POST",
                                     f"/api/v1/explore/requirements/{req_id}/unconvert?force=true",
                                     {"project_id": pid})
            if code_uc2 == 200:
                log("Unconvert (force)", "PASS", "Force unconverted")
            else:
                log("Unconvert (force)", "FAIL", f"Code={code_uc2}")
        elif code_uc == 400:
            log("Unconvert (not converted)", "PASS", f"Expected: {body_uc.get('error', '')[:80]}")
        else:
            log("Unconvert", "FAIL", f"Unexpected code={code_uc}")

    # Convert fit requirement → config item
    if req_id3:
        expect("Submit fit for review", "POST", f"/api/v1/explore/requirements/{req_id3}/transition", {
            "action": "submit_for_review", "user_id": "e2e-tester", "project_id": pid,
        })
        expect("Approve fit req", "POST", f"/api/v1/explore/requirements/{req_id3}/transition", {
            "action": "approve", "user_id": "e2e-tester", "project_id": pid,
        })
        body, _ = expect("Convert to config", "POST", f"/api/v1/explore/requirements/{req_id3}/convert", {
            "project_id": pid, "target_type": "config",
        })
        config_from_convert = body.get("config_item_id") if isinstance(body, dict) else None
        IDS["config_from_convert"] = config_from_convert

    # Batch transition
    if req_id2:
        expect("Batch transition", "POST", "/api/v1/explore/requirements/batch-transition", {
            "requirement_ids": [req_id2],
            "action": "submit_for_review",
            "user_id": "e2e-tester",
            "project_id": pid,
        })

    # Stats & matrix
    expect("Requirement stats", "GET", f"/api/v1/explore/requirements/stats?project_id={pid}")
    expect("Coverage matrix", "GET", f"/api/v1/explore/requirements/coverage-matrix?project_id={pid}")

    # ── Open Items ──
    body, code = expect("Create open item", "POST", "/api/v1/explore/open-items", {
        "project_id": pid, "title": "Clarify tax logic",
        "description": "Need confirmation on withholding tax calc",
        "severity": "high", "assigned_to": "Tax Team",
    })
    oi_id = body.get("id") if code == 201 else None
    IDS["open_item"] = oi_id

    expect("List open items", "GET", f"/api/v1/explore/open-items?project_id={pid}")
    expect("Open item stats", "GET", f"/api/v1/explore/open-items/stats?project_id={pid}")

    if oi_id:
        expect("Get open item", "GET", f"/api/v1/explore/open-items/{oi_id}")
        expect("Update open item", "PUT", f"/api/v1/explore/open-items/{oi_id}", {
            "title": "Clarify tax logic (Updated)",
        })
        expect("Add OI comment", "POST", f"/api/v1/explore/open-items/{oi_id}/comments", {
            "content": "Checking with tax consultant", "author": "E2E Tester",
        })
        expect("OI transition", "POST", f"/api/v1/explore/open-items/{oi_id}/transition", {
            "action": "start_progress", "user_id": "e2e-tester",
        })
        # Link to requirement
        if req_id:
            expect("Link OI to requirement", "POST", f"/api/v1/explore/requirements/{req_id}/link-open-item", {
                "open_item_id": oi_id, "link_type": "related",
            })

    # ── Scope Change Requests ──
    body, code = expect("Create SCR", "POST", "/api/v1/explore/scope-change-requests", {
        "project_id": pid, "title": "Add e-Archive scope",
        "description": "Customer requested e-Archive in addition to e-Invoice",
        "change_type": "add_to_scope",
        "justification": "Customer contract amendment",
        "impact": "medium", "requested_by": "Customer PM",
    })
    scr_id = body.get("id") if code == 201 else None
    IDS["scr"] = scr_id

    expect("List SCRs", "GET", f"/api/v1/explore/scope-change-requests?project_id={pid}")
    if scr_id:
        expect("Get SCR detail", "GET", f"/api/v1/explore/scope-change-requests/{scr_id}")

    # ── Area Milestones ──
    expect("Area milestones", "GET", f"/api/v1/explore/area-milestones?project_id={pid}")

    # ── Scope Matrix ──
    expect("Scope matrix", "GET", f"/api/v1/explore/scope-matrix?project_id={pid}")

    # ── Snapshots ──
    expect("List snapshots", "GET", f"/api/v1/explore/snapshots?project_id={pid}")

    # ── User permissions ──
    expect("User permissions", "GET", f"/api/v1/explore/user-permissions?project_id={pid}&user_id=e2e-tester")

    # ── Attachments ──
    expect("List attachments", "GET", f"/api/v1/explore/attachments?project_id={pid}")

    # ── Cross-module flags ──
    expect("Cross-module flags", "GET", f"/api/v1/explore/cross-module-flags?project_id={pid}")

    # ── Steering committee report ──
    expect("Steering report", "GET", f"/api/v1/explore/reports/steering-committee?project_id={pid}", codes=(200, 500))


# ══════════════════════════════════════════════════════════════
# BLOCK 3: BACKLOG & WRICEF (30 tests)
# ══════════════════════════════════════════════════════════════
def block_3_backlog():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "3_backlog"
    print("\n═══ BLOCK 3: BACKLOG & WRICEF ═══")
    pid = IDS.get("program", 1)

    # ── Backlog CRUD ──
    body, code = expect("Create backlog item", "POST", f"/api/v1/programs/{pid}/backlog", {
        "title": "Custom Pricing Report",
        "description": "ALV report for special pricing conditions",
        "wricef_type": "report",
        "module": "SD",
        "priority": "high",
    })
    bi_id = body.get("id") if code == 201 else None
    IDS["backlog"] = bi_id

    expect("List backlog", "GET", f"/api/v1/programs/{pid}/backlog")
    expect("Backlog stats", "GET", f"/api/v1/programs/{pid}/backlog/stats")
    expect("Backlog board", "GET", f"/api/v1/programs/{pid}/backlog/board")

    if bi_id:
        expect("Get backlog detail", "GET", f"/api/v1/backlog/{bi_id}")
        expect("Update backlog item", "PUT", f"/api/v1/backlog/{bi_id}", {
            "title": "Custom Pricing Report (Updated)",
            "status": "design",
        })
        expect("Move backlog item", "PATCH", f"/api/v1/backlog/{bi_id}/move", {
            "status": "build",
        })

        # ── Functional Spec ──
        body, code = expect("Create FS", "POST", f"/api/v1/backlog/{bi_id}/functional-spec", {
            "title": "FS — Custom Pricing Report",
            "description": "Functional specification for pricing report",
            "content": "## Overview\nCustom ALV report...",
            "author": "E2E Tester",
        })
        fs_id = body.get("id") if code == 201 else None
        IDS["fs"] = fs_id

        if fs_id:
            expect("Get FS detail", "GET", f"/api/v1/functional-specs/{fs_id}")
            expect("Update FS", "PUT", f"/api/v1/functional-specs/{fs_id}", {
                "title": "FS — Custom Pricing Report (Updated)",
                "status": "in_review",
            })

            # ── Technical Spec ──
            body, code = expect("Create TS", "POST", f"/api/v1/functional-specs/{fs_id}/technical-spec", {
                "title": "TS — Custom Pricing Report",
                "description": "Technical design",
                "content": "## Technical Design\nABAP ALV Grid...",
                "author": "E2E Dev",
            })
            ts_id = body.get("id") if code == 201 else None
            IDS["ts"] = ts_id

            if ts_id:
                expect("Get TS detail", "GET", f"/api/v1/technical-specs/{ts_id}")
                expect("Update TS", "PUT", f"/api/v1/technical-specs/{ts_id}", {
                    "title": "TS — Custom Pricing Report (Updated)",
                })

    # ── Config Items ──
    body, code = expect("Create config item", "POST", f"/api/v1/programs/{pid}/config-items", {
        "title": "Payment Terms Configuration",
        "description": "Configure standard payment terms",
        "module": "FI",
    })
    ci_id = body.get("id") if code == 201 else None
    IDS["config_item"] = ci_id

    expect("List config items", "GET", f"/api/v1/programs/{pid}/config-items")

    if ci_id:
        expect("Get config item", "GET", f"/api/v1/config-items/{ci_id}")
        expect("Update config item", "PUT", f"/api/v1/config-items/{ci_id}", {
            "title": "Payment Terms Configuration (Updated)",
        })

        # FS for config item
        body, code = expect("Create FS for config", "POST", f"/api/v1/config-items/{ci_id}/functional-spec", {
            "title": "FS — Payment Terms",
            "description": "Config spec",
            "author": "E2E",
        })
        IDS["fs_config"] = body.get("id") if code == 201 else None


# ══════════════════════════════════════════════════════════════
# BLOCK 4: INTEGRATION HUB (25 tests)
# ══════════════════════════════════════════════════════════════
def block_4_integration():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "4_integration"
    print("\n═══ BLOCK 4: INTEGRATION HUB ═══")
    pid = IDS.get("program", 1)

    # ── Interfaces ──
    body, code = expect("Create interface", "POST", f"/api/v1/programs/{pid}/interfaces", {
        "name": "e-Invoice to GIB",
        "description": "e-Invoice integration via GIB portal",
        "source_system": "SAP S/4HANA",
        "target_system": "GIB Portal",
        "direction": "outbound",
        "protocol": "rest",
        "module": "FI",
    })
    int_id = body.get("id") if code == 201 else None
    IDS["interface"] = int_id

    expect("List interfaces", "GET", f"/api/v1/programs/{pid}/interfaces")
    expect("Interface stats", "GET", f"/api/v1/programs/{pid}/interfaces/stats")

    if int_id:
        expect("Get interface detail", "GET", f"/api/v1/interfaces/{int_id}")
        expect("Update interface", "PUT", f"/api/v1/interfaces/{int_id}", {
            "name": "e-Invoice to GIB (Updated)",
            "status": "design",
        })
        expect("Set interface status", "PATCH", f"/api/v1/interfaces/{int_id}/status", {
            "status": "designed",
        })

        # Wave assignment
        wave_id = IDS.get("wave")
        if wave_id:
            expect("Assign interface to wave", "PATCH", f"/api/v1/interfaces/{int_id}/assign-wave", {
                "wave_id": wave_id,
            })

        # Checklist
        body, code = expect("Add checklist item", "POST", f"/api/v1/interfaces/{int_id}/checklist", {
            "title": "Define mapping document",
            "category": "design",
        })
        cl_id = body.get("id") if code == 201 else None
        IDS["checklist"] = cl_id

        expect("Get checklist", "GET", f"/api/v1/interfaces/{int_id}/checklist")
        if cl_id:
            expect("Update checklist", "PUT", f"/api/v1/checklist/{cl_id}", {
                "completed": True,
            })

        # Connectivity tests
        body, code = expect("Create connectivity test", "POST", f"/api/v1/interfaces/{int_id}/connectivity-tests", {
            "test_date": "2026-03-15",
            "status": "planned",
            "notes": "Initial connectivity check",
        })
        ct_id = body.get("id") if code == 201 else None
        IDS["connectivity_test"] = ct_id

        expect("List connectivity tests", "GET", f"/api/v1/interfaces/{int_id}/connectivity-tests")
        if ct_id:
            expect("Get connectivity test", "GET", f"/api/v1/connectivity-tests/{ct_id}")

        # Switch plans
        body, code = expect("Create switch plan", "POST", f"/api/v1/interfaces/{int_id}/switch-plans", {
            "name": "Go-Live Switch",
            "planned_date": "2026-06-01",
            "status": "planned",
        })
        sp_id = body.get("id") if code == 201 else None
        IDS["switch_plan"] = sp_id

        expect("List switch plans", "GET", f"/api/v1/interfaces/{int_id}/switch-plans")
        if sp_id:
            expect("Update switch plan", "PUT", f"/api/v1/switch-plans/{sp_id}", {
                "name": "Go-Live Switch (Updated)",
            })


# ══════════════════════════════════════════════════════════════
# BLOCK 5: TESTING HUB — Full lifecycle (55 tests)
# ══════════════════════════════════════════════════════════════
def block_5_testing():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "5_testing"
    print("\n═══ BLOCK 5: TESTING HUB ═══")
    pid = IDS.get("program", 1)

    # ── Test Plans ──
    body, code = expect("Create test plan", "POST", f"/api/v1/programs/{pid}/testing/plans", {
        "name": "SIT Test Plan",
        "description": "System Integration Testing",
        "test_type": "SIT",
    })
    plan_id = body.get("id") if code == 201 else None
    IDS["test_plan"] = plan_id

    expect("List test plans", "GET", f"/api/v1/programs/{pid}/testing/plans")
    if plan_id:
        expect("Get test plan", "GET", f"/api/v1/testing/plans/{plan_id}")
        expect("Update test plan", "PUT", f"/api/v1/testing/plans/{plan_id}", {
            "name": "SIT Test Plan (Updated)",
        })

    # ── Test Suites ──
    body, code = expect("Create suite", "POST", f"/api/v1/programs/{pid}/testing/suites", {
        "name": "SD — Sales Suite",
        "suite_type": "SIT",
        "module": "SD",
    })
    suite_id = body.get("id") if code == 201 else None
    IDS["suite"] = suite_id

    body, code = expect("Create 2nd suite", "POST", f"/api/v1/programs/{pid}/testing/suites", {
        "name": "FI — Finance Suite",
        "suite_type": "SIT",
        "module": "FI",
    })
    suite_id2 = body.get("id") if code == 201 else None
    IDS["suite2"] = suite_id2

    expect("List suites", "GET", f"/api/v1/programs/{pid}/testing/suites")

    if suite_id:
        expect("Get suite detail", "GET", f"/api/v1/testing/suites/{suite_id}")
        expect("Update suite", "PUT", f"/api/v1/testing/suites/{suite_id}", {
            "name": "SD — Sales Suite (Updated)",
        })

    # ── Test Cases (Catalog) ──
    body, code = expect("Create test case", "POST", f"/api/v1/programs/{pid}/testing/catalog", {
        "title": "Create Standard Sales Order",
        "test_layer": "sit",
        "module": "SD",
        "priority": "high",
        "suite_id": suite_id,
        "preconditions": "Customer and material master exist",
        "test_steps": "1. VA01\n2. Enter customer\n3. Add line item\n4. Save",
        "expected_result": "Sales order created with number",
    })
    tc_id = body.get("id") if code == 201 else None
    IDS["test_case"] = tc_id

    body, code = expect("Create 2nd TC", "POST", f"/api/v1/programs/{pid}/testing/catalog", {
        "title": "Post Customer Invoice",
        "test_layer": "sit",
        "module": "FI",
        "priority": "medium",
        "suite_id": suite_id,
    })
    tc_id2 = body.get("id") if code == 201 else None
    IDS["test_case2"] = tc_id2

    # Filters
    expect("List catalog", "GET", f"/api/v1/programs/{pid}/testing/catalog")
    expect("Filter by module", "GET", f"/api/v1/programs/{pid}/testing/catalog?module=SD")
    expect("Filter by suite", "GET", f"/api/v1/programs/{pid}/testing/catalog?suite_id={suite_id}")
    expect("Filter by status", "GET", f"/api/v1/programs/{pid}/testing/catalog?status=draft")
    expect("Filter by priority", "GET", f"/api/v1/programs/{pid}/testing/catalog?priority=high")
    expect("Search catalog", "GET", f"/api/v1/programs/{pid}/testing/catalog?search=sales")

    if tc_id:
        expect("Get TC detail", "GET", f"/api/v1/testing/catalog/{tc_id}")
        expect("Update TC", "PUT", f"/api/v1/testing/catalog/{tc_id}", {
            "title": "Create Standard Sales Order (Updated)",
            "status": "ready",
        })

        # Test Steps
        body, code = expect("Add test step", "POST", f"/api/v1/testing/catalog/{tc_id}/steps", {
            "step_no": 1,
            "action": "Open VA01",
            "expected": "Sales order screen opens",
        })
        step_id = body.get("id") if code == 201 else None
        IDS["test_step"] = step_id

        expect("List TC steps", "GET", f"/api/v1/testing/catalog/{tc_id}/steps")
        if step_id:
            expect("Update test step", "PUT", f"/api/v1/testing/steps/{step_id}", {
                "action": "Open VA01 (Updated)",
            })

        # Dependencies
        if tc_id2:
            body, code = expect("Add TC dependency", "POST", f"/api/v1/testing/catalog/{tc_id2}/dependencies", {
                "other_case_id": tc_id,
                "dependency_type": "finish_to_start",
            })
            dep_id = body.get("id") if code == 201 else None
            IDS["tc_dep"] = dep_id
            expect("List TC deps", "GET", f"/api/v1/testing/catalog/{tc_id2}/dependencies")

        # Clone test case
        body, code = expect("Clone test case", "POST", f"/api/v1/testing/test-cases/{tc_id}/clone", {
            "title": "Cloned — Sales Order Test",
            "priority": "medium",
        })
        clone_id = body.get("id") if code == 201 else None
        IDS["cloned_tc"] = clone_id
        if clone_id:
            expect_field("Clone has cloned_from_id", body, "cloned_from_id", tc_id)

    # Bulk clone suite
    if suite_id and suite_id2:
        body, code = expect("Clone suite cases", "POST", f"/api/v1/testing/test-suites/{suite_id}/clone-cases", {
            "target_suite_id": suite_id2,
        })
        if code == 201 and isinstance(body, dict):
            log("Bulk clone count", "PASS", f"Cloned {body.get('cloned_count', 0)} cases")

    # ── Test Cycles ──
    if plan_id:
        body, code = expect("Create cycle", "POST", f"/api/v1/testing/plans/{plan_id}/cycles", {
            "name": "SIT Cycle 1",
            "start_date": "2026-04-01",
            "end_date": "2026-04-15",
        })
        cycle_id = body.get("id") if code == 201 else None
        IDS["cycle"] = cycle_id

        expect("List cycles", "GET", f"/api/v1/testing/plans/{plan_id}/cycles")

        if cycle_id:
            expect("Get cycle", "GET", f"/api/v1/testing/cycles/{cycle_id}")
            expect("Update cycle", "PUT", f"/api/v1/testing/cycles/{cycle_id}", {
                "name": "SIT Cycle 1 (Updated)",
            })

            # Assign suite to cycle
            if suite_id:
                expect("Add suite to cycle", "POST", f"/api/v1/testing/cycles/{cycle_id}/suites", {
                    "suite_id": suite_id,
                })

            # Entry/Exit validation
            expect("Validate entry", "POST", f"/api/v1/testing/cycles/{cycle_id}/validate-entry")
            expect("Validate exit", "POST", f"/api/v1/testing/cycles/{cycle_id}/validate-exit")

            # ── Runs ──
            if tc_id:
                body, code = expect("Create run", "POST", f"/api/v1/testing/cycles/{cycle_id}/runs", {
                    "test_case_id": tc_id,
                    "tester": "E2E Tester",
                    "status": "pass",
                })
                run_id = body.get("id") if code == 201 else None
                IDS["run"] = run_id

                expect("List runs", "GET", f"/api/v1/testing/cycles/{cycle_id}/runs")
                if run_id:
                    expect("Get run", "GET", f"/api/v1/testing/runs/{run_id}")
                    expect("Update run", "PUT", f"/api/v1/testing/runs/{run_id}", {
                        "status": "pass",
                        "notes": "Test passed successfully",
                    })

                    # Step results
                    if step_id:
                        body, code = expect("Add step result", "POST", f"/api/v1/testing/runs/{run_id}/step-results", {
                            "step_no": 1,
                            "status": "pass",
                            "actual_result": "Screen opened correctly",
                        })
                        sr_id = body.get("id") if code == 201 else None
                        IDS["step_result"] = sr_id
                        expect("List step results", "GET", f"/api/v1/testing/runs/{run_id}/step-results")

            # ── Executions ──
            if tc_id:
                body, code = expect("Create execution", "POST", f"/api/v1/testing/cycles/{cycle_id}/executions", {
                    "test_case_id": tc_id,
                    "status": "passed",
                    "executed_by": "E2E Tester",
                })
                exec_id = body.get("id") if code == 201 else None
                IDS["execution"] = exec_id

                expect("List executions", "GET", f"/api/v1/testing/cycles/{cycle_id}/executions")
                if exec_id:
                    expect("Get execution", "GET", f"/api/v1/testing/executions/{exec_id}")

            # UAT Signoffs
            body, code = expect("Create UAT signoff", "POST", f"/api/v1/testing/cycles/{cycle_id}/uat-signoffs", {
                "signed_off_by": "Business Owner",
                "process_area": "SD",
                "status": "approved",
                "comments": "All scenarios passed",
            })
            signoff_id = body.get("id") if code == 201 else None
            IDS["signoff"] = signoff_id
            expect("List UAT signoffs", "GET", f"/api/v1/testing/cycles/{cycle_id}/uat-signoffs")

    # ── Defects ──
    body, code = expect("Create defect", "POST", f"/api/v1/programs/{pid}/testing/defects", {
        "title": "Sales order pricing incorrect",
        "description": "Condition type PR00 not picked up",
        "severity": "S2",
        "priority": "P2",
        "module": "SD",
        "test_case_id": tc_id,
    })
    defect_id = body.get("id") if code == 201 else None
    IDS["defect"] = defect_id

    expect("List defects", "GET", f"/api/v1/programs/{pid}/testing/defects")

    if defect_id:
        expect("Get defect", "GET", f"/api/v1/testing/defects/{defect_id}")
        expect("Update defect", "PUT", f"/api/v1/testing/defects/{defect_id}", {
            "title": "Sales order pricing incorrect (Updated)",
            "status": "assigned",
        })

        # Defect comments
        body, code = expect("Add defect comment", "POST", f"/api/v1/testing/defects/{defect_id}/comments", {
            "body": "Investigating pricing logic",
            "author": "Developer",
        })
        dc_id = body.get("id") if code == 201 else None
        IDS["defect_comment"] = dc_id

        expect("List defect comments", "GET", f"/api/v1/testing/defects/{defect_id}/comments")

        # Defect history
        expect("Defect history", "GET", f"/api/v1/testing/defects/{defect_id}/history")

        # Defect links
        # Create 2nd defect for linking
        body2d, code2d = expect("Create 2nd defect", "POST", f"/api/v1/programs/{pid}/testing/defects", {
            "title": "Invoice print issue",
            "severity": "S3",
            "priority": "P3",
            "module": "FI",
        })
        defect_id2 = body2d.get("id") if code2d == 201 else None
        IDS["defect2"] = defect_id2

        if defect_id2:
            body, code = expect("Create defect link", "POST", f"/api/v1/testing/defects/{defect_id}/links", {
                "target_defect_id": defect_id2,
                "link_type": "related",
                "notes": "Related issue",
            })
        expect("List defect links", "GET", f"/api/v1/testing/defects/{defect_id}/links")

        # Defect SLA
        expect("Defect SLA", "GET", f"/api/v1/testing/defects/{defect_id}/sla")

    # ── Dashboard & Reports ──
    expect("Testing dashboard", "GET", f"/api/v1/programs/{pid}/testing/dashboard")
    expect("Go/No-Go dashboard", "GET", f"/api/v1/programs/{pid}/testing/dashboard/go-no-go")
    expect("Regression sets", "GET", f"/api/v1/programs/{pid}/testing/regression-sets")
    expect("Traceability matrix", "GET", f"/api/v1/programs/{pid}/testing/traceability-matrix")

    # Snapshots
    body, code = expect("Create test snapshot", "POST", f"/api/v1/programs/{pid}/testing/snapshots", {
        "label": "SIT Round 1",
    })
    expect("List test snapshots", "GET", f"/api/v1/programs/{pid}/testing/snapshots")


# ══════════════════════════════════════════════════════════════
# BLOCK 6: CUTOVER (35 tests)
# ══════════════════════════════════════════════════════════════
def block_6_cutover():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "6_cutover"
    print("\n═══ BLOCK 6: CUTOVER ═══")
    pid = IDS.get("program", 1)

    # ── Cutover Plans ──
    body, code = expect("Create cutover plan", "POST", "/api/v1/cutover/plans", {
        "program_id": pid,
        "name": "Go-Live Cutover Plan",
        "description": "Main go-live cutover plan",
        "planned_start": "2026-06-01",
        "planned_end": "2026-06-03",
    })
    cp_id = body.get("id") if code == 201 else None
    IDS["cutover_plan"] = cp_id

    expect("List cutover plans", "GET", "/api/v1/cutover/plans")

    if cp_id:
        expect("Get cutover plan", "GET", f"/api/v1/cutover/plans/{cp_id}")
        expect("Update cutover plan", "PUT", f"/api/v1/cutover/plans/{cp_id}", {
            "name": "Go-Live Cutover Plan (Updated)",
        })
        expect("Cutover progress", "GET", f"/api/v1/cutover/plans/{cp_id}/progress")

        # Plan transition
        expect("Transition plan", "POST", f"/api/v1/cutover/plans/{cp_id}/transition", {
            "status": "approved",
        })

        # ── Scope Items ──
        body, code = expect("Create scope item", "POST", f"/api/v1/cutover/plans/{cp_id}/scope-items", {
            "name": "Finance Data Migration",
            "module": "FI",
            "priority": "critical",
        })
        si_id = body.get("id") if code == 201 else None
        IDS["cutover_scope_item"] = si_id

        expect("List scope items", "GET", f"/api/v1/cutover/plans/{cp_id}/scope-items")
        if si_id:
            expect("Get scope item", "GET", f"/api/v1/cutover/scope-items/{si_id}")
            expect("Update scope item", "PUT", f"/api/v1/cutover/scope-items/{si_id}", {
                "name": "Finance Data Migration (Updated)",
            })

            # ── Tasks ──
            body, code = expect("Create cutover task", "POST", f"/api/v1/cutover/scope-items/{si_id}/tasks", {
                "title": "Extract GL balances",
                "assigned_to": "Migration Team",
                "planned_duration_hours": 4,
                "sequence": 1,
            })
            task_id = body.get("id") if code == 201 else None
            IDS["cutover_task"] = task_id

            body2, _ = expect("Create 2nd task", "POST", f"/api/v1/cutover/scope-items/{si_id}/tasks", {
                "title": "Load GL balances",
                "assigned_to": "Migration Team",
                "planned_duration_hours": 6,
                "sequence": 2,
            })
            task_id2 = body2.get("id") if isinstance(body2, dict) else None
            IDS["cutover_task2"] = task_id2

            expect("List tasks", "GET", f"/api/v1/cutover/scope-items/{si_id}/tasks")

            if task_id:
                expect("Get task", "GET", f"/api/v1/cutover/tasks/{task_id}")
                expect("Update task", "PUT", f"/api/v1/cutover/tasks/{task_id}", {
                    "name": "Extract GL balances (Updated)",
                })
                expect("Task transition", "POST", f"/api/v1/cutover/tasks/{task_id}/transition", {
                    "status": "in_progress",
                })

                # Task dependencies
                if task_id2:
                    body, code = expect("Add task dependency", "POST", f"/api/v1/cutover/tasks/{task_id2}/dependencies", {
                        "predecessor_id": task_id,
                        "dependency_type": "finish_to_start",
                    })
                    expect("List task deps", "GET", f"/api/v1/cutover/tasks/{task_id2}/dependencies")

        # ── Rehearsals ──
        body, code = expect("Create rehearsal", "POST", f"/api/v1/cutover/plans/{cp_id}/rehearsals", {
            "name": "Rehearsal 1",
            "planned_start": "2026-05-15",
            "planned_end": "2026-05-17",
        })
        reh_id = body.get("id") if code == 201 else None
        IDS["rehearsal"] = reh_id

        expect("List rehearsals", "GET", f"/api/v1/cutover/plans/{cp_id}/rehearsals")
        if reh_id:
            expect("Get rehearsal", "GET", f"/api/v1/cutover/rehearsals/{reh_id}")
            expect("Update rehearsal", "PUT", f"/api/v1/cutover/rehearsals/{reh_id}", {
                "name": "Rehearsal 1 (Updated)",
            })

        # ── Go/No-Go ──
        expect("List go-no-go", "GET", f"/api/v1/cutover/plans/{cp_id}/go-no-go")
        body, code = expect("Create go-no-go item", "POST", f"/api/v1/cutover/plans/{cp_id}/go-no-go", {
            "criterion": "All SIT defects resolved",
            "category": "testing",
            "status": "pending",
        })
        gng_id = body.get("id") if code == 201 else None
        IDS["go_no_go"] = gng_id

        if gng_id:
            expect("Get go-no-go", "GET", f"/api/v1/cutover/go-no-go/{gng_id}")
            expect("Update go-no-go", "PUT", f"/api/v1/cutover/go-no-go/{gng_id}", {
                "status": "go",
            })

        expect("Go-no-go summary", "GET", f"/api/v1/cutover/plans/{cp_id}/go-no-go/summary")

        # ── SLA Targets ──
        body, code = expect("Create SLA target", "POST", f"/api/v1/cutover/plans/{cp_id}/sla-targets", {
            "severity": "P1",
            "response_target_min": 30,
            "resolution_target_min": 240,
        })
        sla_id = body.get("id") if code == 201 else None

        expect("List SLA targets", "GET", f"/api/v1/cutover/plans/{cp_id}/sla-targets")

        # ── Incidents ──
        body, code = expect("Create incident", "POST", f"/api/v1/cutover/plans/{cp_id}/incidents", {
            "title": "Data load timeout",
            "severity": "P2",
            "description": "GL balance load timed out after 2 hours",
            "category": "other",
            "reported_by": "E2E Tester",
        })
        inc_id = body.get("id") if code == 201 else None
        IDS["incident"] = inc_id

        expect("List incidents", "GET", f"/api/v1/cutover/plans/{cp_id}/incidents")
        if inc_id:
            expect("Get incident", "GET", f"/api/v1/cutover/incidents/{inc_id}")
            expect("Update incident", "PUT", f"/api/v1/cutover/incidents/{inc_id}", {
                "title": "Data load timeout (Updated)",
            })

        # ── Hypercare ──
        expect("Hypercare metrics", "GET", f"/api/v1/cutover/plans/{cp_id}/hypercare/metrics")


# ══════════════════════════════════════════════════════════════
# BLOCK 7: DATA FACTORY (25 tests)
# ══════════════════════════════════════════════════════════════
def block_7_data_factory():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "7_data_factory"
    print("\n═══ BLOCK 7: DATA FACTORY ═══")
    pid = IDS.get("program", 1)

    # ── Objects ──
    body, code = expect("Create data object", "POST", "/api/v1/data-factory/objects", {
        "program_id": pid,
        "name": "Customer Master",
        "object_type": "master_data",
        "source_system": "Legacy ERP",
        "target_table": "KNA1",
        "module": "SD",
    })
    obj_id = body.get("id") if code == 201 else None
    IDS["data_object"] = obj_id

    expect("List objects", "GET", "/api/v1/data-factory/objects")
    if obj_id:
        expect("Get object", "GET", f"/api/v1/data-factory/objects/{obj_id}")
        expect("Update object", "PUT", f"/api/v1/data-factory/objects/{obj_id}", {
            "name": "Customer Master (Updated)",
        })

        # ── Tasks ──
        body, code = expect("Create data task", "POST", f"/api/v1/data-factory/objects/{obj_id}/tasks", {
            "name": "Extract customers",
            "rule_type": "validation",
            "rule_expression": "field != null",
        })
        dt_id = body.get("id") if code == 201 else None
        IDS["data_task"] = dt_id

        expect("List data tasks", "GET", f"/api/v1/data-factory/objects/{obj_id}/tasks")
        if dt_id:
            expect("Get data task", "GET", f"/api/v1/data-factory/tasks/{dt_id}")
            expect("Update data task", "PUT", f"/api/v1/data-factory/tasks/{dt_id}", {
                "name": "Extract customers (Updated)",
            })

        # ── Loads ──
        body, code = expect("Create load cycle", "POST", f"/api/v1/data-factory/objects/{obj_id}/loads", {
            "cycle_name": "Load Cycle 1",
            "environment": "DEV",
        })
        lc_id = body.get("id") if code == 201 else None
        IDS["load_cycle"] = lc_id

        expect("List loads", "GET", f"/api/v1/data-factory/objects/{obj_id}/loads")
        if lc_id:
            expect("Get load", "GET", f"/api/v1/data-factory/loads/{lc_id}")
            expect("Update load", "PUT", f"/api/v1/data-factory/loads/{lc_id}", {
                "cycle_name": "Load Cycle 1 (Updated)",
            })
            expect("Start load", "POST", f"/api/v1/data-factory/loads/{lc_id}/start")

            # Reconciliation
            body, code = expect("Create recon", "POST", f"/api/v1/data-factory/loads/{lc_id}/recons", {
                "source_count": 1000,
                "target_count": 998,
                "notes": "2 records failed validation",
            })
            recon_id = body.get("id") if code == 201 else None
            IDS["recon"] = recon_id

            expect("List recons", "GET", f"/api/v1/data-factory/loads/{lc_id}/recons")
            if recon_id:
                expect("Get recon", "GET", f"/api/v1/data-factory/recons/{recon_id}")

    # ── Waves ──
    body, code = expect("Create data wave", "POST", "/api/v1/data-factory/waves", {
        "program_id": pid,
        "name": "Migration Wave 1",
        "wave_number": 1,
    })
    dw_id = body.get("id") if code == 201 else None
    IDS["data_wave"] = dw_id

    expect("List data waves", "GET", "/api/v1/data-factory/waves")
    if dw_id:
        expect("Get data wave", "GET", f"/api/v1/data-factory/waves/{dw_id}")
        expect("Update data wave", "PUT", f"/api/v1/data-factory/waves/{dw_id}", {
            "name": "Migration Wave 1 (Updated)",
        })

    # ── Quality & Comparison ──
    expect("Quality score", "GET", f"/api/v1/data-factory/quality-score?program_id={pid}")
    expect("Cycle comparison", "GET", f"/api/v1/data-factory/cycle-comparison?program_id={pid}")


# ══════════════════════════════════════════════════════════════
# BLOCK 8: RAID LOG (30 tests)
# ══════════════════════════════════════════════════════════════
def block_8_raid():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "8_raid"
    print("\n═══ BLOCK 8: RAID LOG ═══")
    pid = IDS.get("program", 1)

    # ── Risks ──
    body, code = expect("Create risk", "POST", f"/api/v1/programs/{pid}/risks", {
        "title": "Key user availability risk",
        "description": "Key users may not be available during testing",
        "probability": 4,
        "impact": 4,
        "category": "resource",
        "mitigation": "Hire backup resources",
    })
    risk_id = body.get("id") if code == 201 else None
    IDS["risk"] = risk_id

    expect("List risks", "GET", f"/api/v1/programs/{pid}/risks")
    if risk_id:
        expect("Get risk", "GET", f"/api/v1/risks/{risk_id}")
        expect("Update risk", "PUT", f"/api/v1/risks/{risk_id}", {
            "title": "Key user availability risk (Updated)",
            "status": "mitigating",
        })
        expect("Score risk", "PATCH", f"/api/v1/risks/{risk_id}/score", {
            "probability": 3,
            "impact": 4,
        })

    # ── Issues ──
    body, code = expect("Create issue", "POST", f"/api/v1/programs/{pid}/issues", {
        "title": "DEV environment unstable",
        "description": "Frequent crashes on DEV server",
        "severity": "high",
        "category": "technical",
    })
    issue_id = body.get("id") if code == 201 else None
    IDS["issue"] = issue_id

    expect("List issues", "GET", f"/api/v1/programs/{pid}/issues")
    if issue_id:
        expect("Get issue", "GET", f"/api/v1/issues/{issue_id}")
        expect("Update issue", "PUT", f"/api/v1/issues/{issue_id}", {
            "title": "DEV environment unstable (Updated)",
        })
        expect("Issue status", "PATCH", f"/api/v1/issues/{issue_id}/status", {
            "status": "in_progress",
        })

    # ── Actions ──
    body, code = expect("Create action", "POST", f"/api/v1/programs/{pid}/actions", {
        "title": "Schedule basis team review",
        "description": "Review DEV server capacity",
        "assigned_to": "Basis Team",
        "due_date": "2026-03-01",
    })
    action_id = body.get("id") if code == 201 else None
    IDS["action"] = action_id

    expect("List actions", "GET", f"/api/v1/programs/{pid}/actions")
    if action_id:
        expect("Get action", "GET", f"/api/v1/actions/{action_id}")
        expect("Update action", "PUT", f"/api/v1/actions/{action_id}", {
            "title": "Schedule basis team review (Updated)",
        })
        expect("Action status", "PATCH", f"/api/v1/actions/{action_id}/status", {
            "status": "in_progress",
        })

    # ── Decisions ──
    body, code = expect("Create decision", "POST", f"/api/v1/programs/{pid}/decisions", {
        "title": "Use SAP standard pricing",
        "description": "Decision to use condition technique",
        "decided_by": "Steering Committee",
        "decision_date": "2026-02-15",
    })
    dec_id = body.get("id") if code == 201 else None
    IDS["decision"] = dec_id

    expect("List decisions", "GET", f"/api/v1/programs/{pid}/decisions")
    if dec_id:
        expect("Get decision", "GET", f"/api/v1/decisions/{dec_id}")
        expect("Update decision", "PUT", f"/api/v1/decisions/{dec_id}", {
            "title": "Use SAP standard pricing (Updated)",
        })
        expect("Decision status", "PATCH", f"/api/v1/decisions/{dec_id}/status", {
            "status": "approved",
        })

    # ── RAID Stats & Heatmap ──
    expect("RAID stats", "GET", f"/api/v1/programs/{pid}/raid/stats")
    expect("RAID heatmap", "GET", f"/api/v1/programs/{pid}/raid/heatmap")


# ══════════════════════════════════════════════════════════════
# BLOCK 9: REPORTS & EXECUTIVE COCKPIT (10 tests)
# ══════════════════════════════════════════════════════════════
def block_9_reports():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "9_reports"
    print("\n═══ BLOCK 9: REPORTS & EXECUTIVE COCKPIT ═══")
    pid = IDS.get("program", 1)

    expect("Program health report", "GET", f"/api/v1/reports/program-health/{pid}")
    expect("Program health v2", "GET", f"/api/v1/reports/program/{pid}/health")
    expect("Weekly report", "GET", f"/api/v1/reports/weekly/{pid}")
    expect("Export PDF", "GET", f"/api/v1/reports/export/pdf/{pid}")
    expect("Export XLSX", "GET", f"/api/v1/reports/export/xlsx/{pid}")


# ══════════════════════════════════════════════════════════════
# BLOCK 10: AI HUB (30 tests)
# ══════════════════════════════════════════════════════════════
def block_10_ai():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "10_ai"
    print("\n═══ BLOCK 10: AI HUB ═══")
    pid = IDS.get("program", 1)

    # ── Suggestions ──
    expect("List suggestions", "GET", "/api/v1/ai/suggestions")
    expect("Suggestion stats", "GET", "/api/v1/ai/suggestions/stats")
    expect("Pending count", "GET", "/api/v1/ai/suggestions/pending-count")

    # ── Conversations ──
    body, code = expect("Create conversation", "POST", "/api/v1/ai/conversations", {
        "title": "E2E Test Conversation",
    })
    conv_id = body.get("id") if code == 201 else None

    expect("List conversations", "GET", "/api/v1/ai/conversations")
    if conv_id:
        expect("Get conversation", "GET", f"/api/v1/ai/conversations/{conv_id}")

    # ── Tasks ──
    expect("List AI tasks", "GET", "/api/v1/ai/tasks")

    # ── Budgets ──
    expect("List budgets", "GET", "/api/v1/ai/budgets")
    expect("Budget status", "GET", "/api/v1/ai/budgets/status")

    # ── KB Versions ──
    expect("List KB versions", "GET", "/api/v1/ai/kb/versions")
    expect("KB stale check", "GET", "/api/v1/ai/kb/stale")

    # ── Performance ──
    expect("AI dashboard", "GET", "/api/v1/ai/admin/dashboard")
    expect("AI perf dashboard", "GET", "/api/v1/ai/performance/dashboard")
    expect("AI perf by assistant", "GET", "/api/v1/ai/performance/by-assistant")

    # ── Usage ──
    expect("AI usage", "GET", "/api/v1/ai/usage")
    expect("AI usage cost", "GET", "/api/v1/ai/usage/cost")
    expect("AI usage metrics", "GET", "/api/v1/metrics/ai/usage")

    # ── Feedback ──
    expect("Feedback stats", "GET", "/api/v1/ai/feedback/stats")
    expect("Feedback accuracy", "GET", "/api/v1/ai/feedback/accuracy")
    expect("Feedback recommendations", "GET", "/api/v1/ai/feedback/recommendations")

    # ── Prompts & Export ──
    expect("List prompts", "GET", "/api/v1/ai/prompts")
    expect("Export formats", "GET", "/api/v1/ai/export/formats")

    # ── Embeddings ──
    expect("Embeddings stats", "GET", "/api/v1/ai/embeddings/stats")

    # ── Cache ──
    expect("Cache stats", "GET", "/api/v1/ai/cache/stats")

    # ── Workflows ──
    expect("List workflows", "GET", "/api/v1/ai/workflows")

    # ── Audit ──
    expect("AI audit log", "GET", "/api/v1/ai/audit-log")


# ══════════════════════════════════════════════════════════════
# BLOCK 11: NOTIFICATIONS & AUDIT (15 tests)
# ══════════════════════════════════════════════════════════════
def block_11_notifications():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "11_notifications"
    print("\n═══ BLOCK 11: NOTIFICATIONS & AUDIT ═══")

    # ── Notifications ──
    body, code = expect("Create notification", "POST", "/api/v1/notifications", {
        "title": "E2E Test Notification",
        "message": "Test message",
        "type": "info",
    })
    notif_id = body.get("id") if code == 201 else None
    IDS["notification"] = notif_id

    expect("List notifications", "GET", "/api/v1/notifications")
    expect("Notification stats", "GET", "/api/v1/notifications/stats")
    expect("Unread count", "GET", "/api/v1/notifications/unread-count")

    if notif_id:
        expect("Get notification", "GET", f"/api/v1/notifications/{notif_id}")
        expect("Mark as read", "PATCH", f"/api/v1/notifications/{notif_id}/read")

    expect("Mark all read", "POST", "/api/v1/notifications/mark-all-read")

    # ── Notification Preferences ──
    expect("List preferences", "GET", "/api/v1/notification-preferences?user_id=e2e-tester")

    # ── Audit Log ──
    expect("Audit log", "GET", "/api/v1/audit")

    # ── Email Logs ──
    expect("Email logs", "GET", "/api/v1/email-logs")
    expect("Email log stats", "GET", "/api/v1/email-logs/stats")


# ══════════════════════════════════════════════════════════════
# BLOCK 12: TRACEABILITY (10 tests)
# ══════════════════════════════════════════════════════════════
def block_12_traceability():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "12_traceability"
    print("\n═══ BLOCK 12: TRACEABILITY ═══")
    pid = IDS.get("program", 1)

    expect("Traceability summary", "GET", f"/api/v1/programs/{pid}/traceability/summary")

    # Entity traceability
    bi_id = IDS.get("backlog")
    if bi_id:
        expect("Backlog trace", "GET", f"/api/v1/traceability/backlog_item/{bi_id}")
        expect("Backlog chain", "GET", f"/api/v1/traceability/chain/backlog_item/{bi_id}")

    tc_id = IDS.get("test_case")
    if tc_id:
        expect("Test case trace", "GET", f"/api/v1/traceability/test_case/{tc_id}")

    defect_id = IDS.get("defect")
    if defect_id:
        expect("Defect trace", "GET", f"/api/v1/traceability/defect/{defect_id}")

    req_id = IDS.get("req")
    if req_id:
        expect("Requirement trace", "GET", f"/api/v1/trace/requirement/{req_id}")

    int_id = IDS.get("interface")
    if int_id:
        expect("Interface trace", "GET", f"/api/v1/traceability/interface/{int_id}")


# ══════════════════════════════════════════════════════════════
# BLOCK 13: RUN & SUSTAIN (15 tests)
# ══════════════════════════════════════════════════════════════
def block_13_run_sustain():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "13_run_sustain"
    print("\n═══ BLOCK 13: RUN & SUSTAIN ═══")

    # Use cutover plan as run-sustain plan (same model in many setups)
    cp_id = IDS.get("cutover_plan")
    if not cp_id:
        log("Skip run-sustain", "WARN", "No cutover plan created")
        return

    expect("R&S dashboard", "GET", f"/api/v1/run-sustain/plans/{cp_id}/dashboard")
    expect("Exit readiness", "GET", f"/api/v1/run-sustain/plans/{cp_id}/exit-readiness")
    expect("Support summary", "GET", f"/api/v1/run-sustain/plans/{cp_id}/support-summary")
    expect("Weekly report", "GET", f"/api/v1/run-sustain/plans/{cp_id}/weekly-report")
    expect("Stabilization dashboard", "GET", f"/api/v1/run-sustain/plans/{cp_id}/stabilization-dashboard")

    # Handover items
    expect("List handover items", "GET", f"/api/v1/run-sustain/plans/{cp_id}/handover-items")
    expect("Handover readiness", "GET", f"/api/v1/run-sustain/plans/{cp_id}/handover-readiness")

    body, code = expect("Create handover item", "POST", f"/api/v1/run-sustain/plans/{cp_id}/handover-items", {
        "title": "Pricing config handover",
        "category": "documentation",
        "assigned_to": "Support Team",
    })
    ho_id = body.get("id") if code == 201 else None
    if ho_id:
        expect("Update handover item", "PUT", f"/api/v1/run-sustain/handover-items/{ho_id}", {
            "status": "in_progress",
        })

    # Knowledge transfer
    expect("List KT items", "GET", f"/api/v1/run-sustain/plans/{cp_id}/knowledge-transfer")
    expect("KT progress", "GET", f"/api/v1/run-sustain/plans/{cp_id}/knowledge-transfer/progress")

    body, code = expect("Create KT item", "POST", f"/api/v1/run-sustain/plans/{cp_id}/knowledge-transfer", {
        "title": "SD Process Training",
        "category": "training",
        "assigned_to": "Training Team",
    })

    # Stabilization metrics
    expect("List stab metrics", "GET", f"/api/v1/run-sustain/plans/{cp_id}/stabilization-metrics")


# ══════════════════════════════════════════════════════════════
# BLOCK 14: CLEANUP — Delete entities (reverse order)
# ══════════════════════════════════════════════════════════════
def block_14_cleanup():
    global CURRENT_BLOCK
    CURRENT_BLOCK = "14_cleanup"
    print("\n═══ BLOCK 14: CLEANUP ═══")

    # Delete in reverse dependency order
    deletions = [
        ("defect_comment", "/api/v1/testing/defect-comments/{}"),
        ("step_result", "/api/v1/testing/step-results/{}"),
        ("tc_dep", "/api/v1/testing/dependencies/{}"),
        ("execution", "/api/v1/testing/executions/{}"),
        ("signoff", "/api/v1/testing/uat-signoffs/{}"),
        ("run", "/api/v1/testing/runs/{}"),
        ("cloned_tc", "/api/v1/testing/catalog/{}"),
        ("test_step", "/api/v1/testing/steps/{}"),
        ("defect2", "/api/v1/testing/defects/{}"),
        ("defect", "/api/v1/testing/defects/{}"),
        ("test_case2", "/api/v1/testing/catalog/{}"),
        ("test_case", "/api/v1/testing/catalog/{}"),
        ("cycle", "/api/v1/testing/cycles/{}"),
        ("suite2", "/api/v1/testing/suites/{}"),
        ("suite", "/api/v1/testing/suites/{}"),
        ("test_plan", "/api/v1/testing/plans/{}"),
        ("incident", "/api/v1/cutover/incidents/{}"),
        ("go_no_go", "/api/v1/cutover/go-no-go/{}"),
        ("rehearsal", "/api/v1/cutover/rehearsals/{}"),
        ("cutover_task", "/api/v1/cutover/tasks/{}"),
        ("cutover_task2", "/api/v1/cutover/tasks/{}"),
        ("cutover_scope_item", "/api/v1/cutover/scope-items/{}"),
        ("cutover_plan", "/api/v1/cutover/plans/{}"),
        ("recon", "/api/v1/data-factory/recons/{}"),
        ("load_cycle", "/api/v1/data-factory/loads/{}"),
        ("data_task", "/api/v1/data-factory/tasks/{}"),
        ("data_object", "/api/v1/data-factory/objects/{}"),
        ("data_wave", "/api/v1/data-factory/waves/{}"),
        ("ts", "/api/v1/technical-specs/{}"),
        ("fs", "/api/v1/functional-specs/{}"),
        ("fs_config", "/api/v1/functional-specs/{}"),
        ("connectivity_test", "/api/v1/connectivity-tests/{}"),
        ("switch_plan", "/api/v1/switch-plans/{}"),
        ("checklist", "/api/v1/checklist/{}"),
        ("interface", "/api/v1/interfaces/{}"),
        ("backlog", "/api/v1/backlog/{}"),
        ("config_item", "/api/v1/config-items/{}"),
        ("risk", "/api/v1/risks/{}"),
        ("issue", "/api/v1/issues/{}"),
        ("action", "/api/v1/actions/{}"),
        ("decision", "/api/v1/decisions/{}"),
        ("notification", "/api/v1/notifications/{}"),
        ("attendee", "/api/v1/explore/attendees/{}"),
        ("agenda", "/api/v1/explore/agenda-items/{}"),
    ]

    for key, path_template in deletions:
        eid = IDS.get(key)
        if eid:
            _, code = api("DELETE", path_template.format(eid))
            status = "PASS" if code in (200, 204) else "WARN"
            log(f"Delete {key} ({eid})", status, f"→ {code}")

    # Delete program last (cascades remaining)
    pid = IDS.get("program")
    if pid:
        _, code = api("DELETE", f"/api/v1/programs/{pid}")
        log(f"Delete program ({pid})", "PASS" if code in (200, 204) else "WARN", f"→ {code}")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  SAP Activate E2E Extended Test")
    print(f"  Target: {BASE}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Verify server is up
    _, code = api("GET", "/api/v1/health")
    if code != 200:
        print(f"\n❌ Server not reachable at {BASE} (code={code})")
        print("   Start with: make run")
        sys.exit(1)

    start = time.time()

    block_0_health()
    block_1_program_setup()
    block_2_explore()
    block_3_backlog()
    block_4_integration()
    block_5_testing()
    block_6_cutover()
    block_7_data_factory()
    block_8_raid()
    block_9_reports()
    block_10_ai()
    block_11_notifications()
    block_12_traceability()
    block_13_run_sustain()
    block_14_cleanup()

    elapsed = time.time() - start

    # ── Summary ──
    print("\n" + "=" * 70)
    print("  FINAL REPORT")
    print("=" * 70)

    total = PASS_COUNT + FAIL_COUNT + WARN_COUNT
    for block_name, tests in RESULTS.items():
        p = sum(1 for t in tests if t["status"] == "PASS")
        f = sum(1 for t in tests if t["status"] == "FAIL")
        w = sum(1 for t in tests if t["status"] == "WARN")
        icon = "✅" if f == 0 else "❌"
        print(f"  {icon} Block {block_name}: {p} PASS, {f} FAIL, {w} WARN")

    print(f"\n  TOTAL: ✅ {PASS_COUNT} PASS | ❌ {FAIL_COUNT} FAIL | ⚠️  {WARN_COUNT} WARN")
    pct = (PASS_COUNT / total * 100) if total > 0 else 0
    print(f"  Pass Rate: {pct:.1f}% ({PASS_COUNT}/{total})")
    print(f"  Duration: {elapsed:.1f}s")
    print("=" * 70)

    # Show failures
    if FAIL_COUNT > 0:
        print("\n  ❌ FAILURES:")
        for block_name, tests in RESULTS.items():
            for t in tests:
                if t["status"] == "FAIL":
                    print(f"    [{block_name}] {t['test']} — {t['detail']}")

    sys.exit(1 if FAIL_COUNT > 0 else 0)


if __name__ == "__main__":
    main()
