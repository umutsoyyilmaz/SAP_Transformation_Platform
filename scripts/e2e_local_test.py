#!/usr/bin/env python3
"""
SAP Activate E2E Local Test — Executes the full test plan against localhost:5001
"""
import requests
import json
import sys
import time
from datetime import datetime

BASE = "http://localhost:5001"
RESULTS = {
    "block_0_endpoints": [],
    "block_1_program_setup": [],
    "block_2_explore": [],
    "block_3_realize": [],
    "block_4_testing": [],
    "block_5_deploy": [],
    "block_6_traceability": [],
    "gaps": [],
    "errors": [],
}

IDS = {}  # Store created entity IDs


def log(block, test, status, detail=""):
    icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"  {icon} [{block}] {test} — {detail}")
    RESULTS.get(block, RESULTS["errors"]).append({
        "test": test, "status": status, "detail": detail
    })


def api(method, path, data=None, expect_codes=(200, 201)):
    url = f"{BASE}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=10)
        elif method == "POST":
            r = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            r = requests.put(url, json=data, timeout=10)
        elif method == "PATCH":
            r = requests.patch(url, json=data, timeout=10)
        elif method == "DELETE":
            r = requests.delete(url, timeout=10)
        else:
            return None, 0
        try:
            body = r.json()
        except Exception:
            body = r.text
        return body, r.status_code
    except Exception as e:
        return {"error": str(e)}, 0


# ══════════════════════════════════════════════════════════════
# BLOCK 0: ENDPOINT HEALTH CHECK
# ══════════════════════════════════════════════════════════════
def block_0():
    print("\n═══ BLOCK 0: ENDPOINT HEALTH CHECK ═══")

    # Core endpoints that should return 200
    endpoints = [
        ("GET", "/", "Home page"),
        ("GET", "/api/v1/health", "Health check"),
        ("GET", "/api/v1/health/ready", "Ready probe"),
        ("GET", "/api/v1/health/live", "Liveness probe"),
        ("GET", "/api/v1/programs", "Programs list"),
        ("GET", "/api/v1/explore/workshops?project_id=1", "Workshops list"),
        ("GET", "/api/v1/explore/requirements?project_id=1", "Requirements list"),
        ("GET", "/api/v1/explore/open-items?project_id=1", "Open items list"),
        ("GET", "/api/v1/explore/process-levels?project_id=1", "Process levels"),
        ("GET", "/api/v1/cutover/plans", "Cutover plans"),
        ("GET", "/api/v1/data-factory/objects", "Data factory objects"),
        ("GET", "/api/v1/data-factory/waves", "Data factory waves"),
        ("GET", "/api/v1/notifications", "Notifications"),
        ("GET", "/api/v1/audit", "Audit log"),
        ("GET", "/api/v1/ai/suggestions", "AI suggestions"),
    ]

    ok = fail = 0
    for method, path, name in endpoints:
        _, code = api(method, path)
        if code == 200:
            log("block_0_endpoints", name, "PASS", f"{path} → {code}")
            ok += 1
        else:
            log("block_0_endpoints", name, "FAIL", f"{path} → {code}")
            fail += 1

    print(f"\n  Block 0 Summary: {ok} OK, {fail} FAIL")
    return ok, fail


# ══════════════════════════════════════════════════════════════
# BLOCK 1: DISCOVER & PREPARE — Program + Team + Process + Scenarios
# ══════════════════════════════════════════════════════════════
def block_1():
    print("\n═══ BLOCK 1: DISCOVER & PREPARE ═══")

    # 1.1 — Create Program (replaces "Project" in test plan)
    body, code = api("POST", "/api/v1/programs", {
        "name": "ACME S/4HANA Transformation",
        "code": "ACME-S4H",
        "description": "SAP ECC 6.0 to S/4HANA 2023 FPS02 Greenfield transformation for ACME Manufacturing.",
        "customer": "ACME Manufacturing A.S.",
        "status": "Active",
        "start_date": "2026-03-01",
        "end_date": "2026-12-15",
        "methodology": "SAP Activate",
        "project_type": "Greenfield"
    })
    if code in (200, 201):
        IDS["program"] = body.get("id") or body.get("program", {}).get("id")
        log("block_1_program_setup", "1.1 Create Program", "PASS", f"ID={IDS.get('program')}")
    else:
        log("block_1_program_setup", "1.1 Create Program", "FAIL", f"code={code} body={str(body)[:200]}")
        # Try to use existing program
        progs, _ = api("GET", "/api/v1/programs")
        if isinstance(progs, list) and progs:
            IDS["program"] = progs[0].get("id")
            log("block_1_program_setup", "1.1 Using existing program", "PASS", f"ID={IDS['program']}")

    pid = IDS.get("program")
    if not pid:
        log("block_1_program_setup", "1.1 NO PROGRAM", "FAIL", "Cannot continue without program")
        return

    # 1.1b — Verify GET program
    body, code = api("GET", f"/api/v1/programs/{pid}")
    log("block_1_program_setup", "1.1b GET Program", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 1.2 — Create Phase structure (SAP Activate 6 phases)
    phases = [
        {"name": "Discover", "sequence": 1, "status": "Completed", "start_date": "2026-03-01", "end_date": "2026-03-31"},
        {"name": "Prepare", "sequence": 2, "status": "Completed", "start_date": "2026-04-01", "end_date": "2026-04-30"},
        {"name": "Explore", "sequence": 3, "status": "In Progress", "start_date": "2026-05-01", "end_date": "2026-06-30"},
        {"name": "Realize", "sequence": 4, "status": "Planned", "start_date": "2026-07-01", "end_date": "2026-09-30"},
        {"name": "Deploy", "sequence": 5, "status": "Planned", "start_date": "2026-10-01", "end_date": "2026-11-30"},
        {"name": "Run", "sequence": 6, "status": "Planned", "start_date": "2026-12-01", "end_date": "2026-12-31"},
    ]
    phase_ok = 0
    for p in phases:
        body, code = api("POST", f"/api/v1/programs/{pid}/phases", p)
        if code in (200, 201):
            phase_ok += 1
            if p["name"] == "Explore":
                IDS["explore_phase"] = body.get("id")
    log("block_1_program_setup", "1.2 Create 6 SAP Phases", "PASS" if phase_ok >= 4 else "FAIL", f"{phase_ok}/6 created")

    # 1.2b — Verify phases
    body, code = api("GET", f"/api/v1/programs/{pid}/phases")
    phase_count = len(body) if isinstance(body, list) else 0
    log("block_1_program_setup", "1.2b GET Phases", "PASS" if phase_count > 0 else "FAIL", f"{phase_count} phases")

    # 1.3 — Team Members
    team = [
        {"name": "Mehmet Yilmaz", "role": "Project Manager", "email": "mehmet.yilmaz@acme.com.tr"},
        {"name": "Ayse Kaya", "role": "Solution Architect", "email": "ayse.kaya@acme.com.tr"},
        {"name": "Ali Demir", "role": "MM Functional Consultant", "email": "ali.demir@partner.com"},
        {"name": "Zeynep Arslan", "role": "SD Functional Consultant", "email": "zeynep.arslan@partner.com"},
        {"name": "Can Ozturk", "role": "FI/CO Functional Consultant", "email": "can.ozturk@partner.com"},
        {"name": "Burak Sahin", "role": "ABAP Developer", "email": "burak.sahin@partner.com"},
        {"name": "Emre Celik", "role": "Basis/Tech Consultant", "email": "emre.celik@partner.com"},
        {"name": "Hakan Aydin", "role": "Business Process Owner", "email": "hakan.aydin@acme.com.tr"},
        {"name": "Selin Yildiz", "role": "Key User - Sales", "email": "selin.yildiz@acme.com.tr"},
        {"name": "Deniz Koc", "role": "Key User - Finance", "email": "deniz.koc@acme.com.tr"},
        {"name": "Gizem Aktas", "role": "Test Manager", "email": "gizem.aktas@partner.com"},
        {"name": "Berna Gunes", "role": "Change Management Lead", "email": "berna.gunes@acme.com.tr"},
    ]
    team_ok = 0
    for t in team:
        body, code = api("POST", f"/api/v1/programs/{pid}/team", t)
        if code in (200, 201):
            team_ok += 1
            if t["role"] == "Project Manager":
                IDS["pm_member"] = body.get("id")
    log("block_1_program_setup", "1.3 Create 12 Team Members", "PASS" if team_ok >= 10 else "FAIL", f"{team_ok}/12 created")

    # 1.3b — Verify team list
    body, code = api("GET", f"/api/v1/programs/{pid}/team")
    team_count = len(body) if isinstance(body, list) else 0
    log("block_1_program_setup", "1.3b GET Team Members", "PASS" if team_count > 0 else "FAIL", f"{team_count} members")

    # 1.4 — Process Levels (L1→L4)
    # L1: Order to Cash
    body, code = api("POST", "/api/v1/explore/process-levels", {
        "name": "Order to Cash",
        "code": "O2C",
        "level": 1,
        "description": "End-to-end order to cash process",
        "project_id": pid
    })
    if code in (200, 201):
        IDS["o2c_l1"] = body.get("id")
        log("block_1_program_setup", "1.4a L1 O2C Process", "PASS", f"ID={IDS.get('o2c_l1')}")
    else:
        log("block_1_program_setup", "1.4a L1 O2C Process", "FAIL", f"code={code} {str(body)[:200]}")

    # L2: Sales Order Management
    if IDS.get("o2c_l1"):
        body, code = api("POST", "/api/v1/explore/process-levels", {
            "name": "Sales Order Management",
            "code": "O2C-SOM",
            "level": 2,
            "parent_id": IDS["o2c_l1"],
            "project_id": pid
        })
        if code in (200, 201):
            IDS["som_l2"] = body.get("id")
            log("block_1_program_setup", "1.4b L2 SOM Process", "PASS", f"ID={IDS.get('som_l2')}")
        else:
            log("block_1_program_setup", "1.4b L2 SOM Process", "FAIL", f"code={code}")

    # L3
    if IDS.get("som_l2"):
        body, code = api("POST", "/api/v1/explore/process-levels", {
            "name": "Standard Sales Order Processing",
            "code": "O2C-SOM-001",
            "level": 3,
            "parent_id": IDS["som_l2"],
            "project_id": pid
        })
        if code in (200, 201):
            IDS["sso_l3"] = body.get("id")
            log("block_1_program_setup", "1.4c L3 SSO Process", "PASS", f"ID={IDS.get('sso_l3')}")
        else:
            log("block_1_program_setup", "1.4c L3 SSO Process", "FAIL", f"code={code}")

    # L4
    if IDS.get("sso_l3"):
        body, code = api("POST", "/api/v1/explore/process-levels", {
            "name": "Create Sales Order with Ref to Quotation",
            "code": "O2C-SOM-001-01",
            "level": 4,
            "parent_id": IDS["sso_l3"],
            "project_id": pid
        })
        if code in (200, 201):
            IDS["cso_l4"] = body.get("id")
            log("block_1_program_setup", "1.4d L4 Process Step", "PASS", f"ID={IDS.get('cso_l4')}")
        else:
            log("block_1_program_setup", "1.4d L4 Process Step", "FAIL", f"code={code}")

    # L1: Procure to Pay
    body, code = api("POST", "/api/v1/explore/process-levels", {
        "name": "Procure to Pay", "code": "P2P", "level": 1,
        "description": "End-to-end procurement process", "project_id": pid
    })
    if code in (200, 201):
        IDS["p2p_l1"] = body.get("id")
    log("block_1_program_setup", "1.4e L1 P2P Process", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # L1: Make to Stock
    body, code = api("POST", "/api/v1/explore/process-levels", {
        "name": "Make to Stock", "code": "M2S", "level": 1,
        "description": "Production planning and execution", "project_id": pid
    })
    if code in (200, 201):
        IDS["m2s_l1"] = body.get("id")
    log("block_1_program_setup", "1.4f L1 M2S Process", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # L1: Record to Report
    body, code = api("POST", "/api/v1/explore/process-levels", {
        "name": "Record to Report", "code": "R2R", "level": 1,
        "description": "Financial closing and reporting", "project_id": pid
    })
    if code in (200, 201):
        IDS["r2r_l1"] = body.get("id")
    log("block_1_program_setup", "1.4g L1 R2R Process", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # Verify tree
    body, code = api("GET", f"/api/v1/explore/process-levels?project_id={pid}&flat=true")
    pl_count = len(body) if isinstance(body, list) else (len(body.get("items", [])) if isinstance(body, dict) else 0)
    log("block_1_program_setup", "1.4h GET Process Levels tree", "PASS" if pl_count > 0 else "FAIL", f"{pl_count} levels")

    # 1.5 — Workstreams
    workstreams = [
        {"name": "SD/O2C", "module": "SD", "lead": "Zeynep Arslan"},
        {"name": "MM/P2P", "module": "MM", "lead": "Ali Demir"},
        {"name": "FI/CO", "module": "FICO", "lead": "Can Ozturk"},
        {"name": "PP/M2S", "module": "PP", "lead": "Ayse Kaya"},
    ]
    ws_ok = 0
    for ws in workstreams:
        body, code = api("POST", f"/api/v1/programs/{pid}/workstreams", ws)
        if code in (200, 201):
            ws_ok += 1
            if ws["module"] == "SD":
                IDS["ws_sd"] = body.get("id")
    log("block_1_program_setup", "1.5 Create 4 Workstreams", "PASS" if ws_ok >= 3 else "FAIL", f"{ws_ok}/4 created")

    print(f"\n  Block 1 Summary: Program={pid}, Phases created, Team created, Process L1-L4, Workstreams")


# ══════════════════════════════════════════════════════════════
# BLOCK 2: EXPLORE — Workshops & Requirements
# ══════════════════════════════════════════════════════════════
def block_2():
    print("\n═══ BLOCK 2: EXPLORE — Workshops & Requirements ═══")
    pid = IDS.get("program")
    if not pid:
        log("block_2_explore", "SKIP", "FAIL", "No program ID")
        return

    # 2.1 — Create Workshops
    workshops_data = [
        {"name": "O2C Workshop 1 — Standard Sales Order Processing", "process_area": "SD",
         "scheduled_date": "2026-04-15",
         "facilitator": "Zeynep Arslan", "l3_scope_item_id": IDS.get("sso_l3"),
         "notes": "Demonstrate SAP Best Practice for standard sales order processing."},
        {"name": "O2C Workshop 2 — Returns, Credit/Debit Memo", "process_area": "SD",
         "scheduled_date": "2026-04-17", "facilitator": "Zeynep Arslan"},
        {"name": "P2P Workshop 1 — Standard Procurement", "process_area": "MM",
         "scheduled_date": "2026-04-22", "facilitator": "Ali Demir"},
        {"name": "P2P Workshop 2 — Service Procurement & Import", "process_area": "MM",
         "scheduled_date": "2026-04-24", "facilitator": "Ali Demir"},
        {"name": "R2R Workshop 1 — GL, AP/AR, Period-End Closing", "process_area": "FICO",
         "scheduled_date": "2026-04-29", "facilitator": "Can Ozturk"},
        {"name": "M2S Workshop 1 — Production Planning, MRP", "process_area": "PP",
         "scheduled_date": "2026-05-06", "facilitator": "Ayse Kaya"},
    ]

    ws_ok = 0
    for i, ws in enumerate(workshops_data):
        ws["project_id"] = pid
        body, code = api("POST", "/api/v1/explore/workshops", ws)
        if code in (200, 201):
            ws_ok += 1
            ws_id = body.get("id")
            if i == 0:
                IDS["ws1_o2c"] = ws_id
            elif i == 2:
                IDS["ws3_p2p"] = ws_id
            elif i == 4:
                IDS["ws5_r2r"] = ws_id
        else:
            log("block_2_explore", f"Workshop create: {ws['title'][:40]}", "FAIL", f"code={code} {str(body)[:150]}")
    log("block_2_explore", "2.1 Create 6 Workshops", "PASS" if ws_ok >= 4 else "FAIL", f"{ws_ok}/6 created")

    # Verify workshops list
    body, code = api("GET", f"/api/v1/explore/workshops?project_id={pid}")
    ws_count = len(body) if isinstance(body, list) else (len(body.get("items", [])) if isinstance(body, dict) else 0)
    log("block_2_explore", "2.1b GET Workshops", "PASS" if ws_count > 0 else "FAIL", f"{ws_count} workshops")

    # 2.1c — Workshop attendees
    if IDS.get("ws1_o2c"):
        body, code = api("POST", f"/api/v1/explore/workshops/{IDS['ws1_o2c']}/attendees", {
            "name": "Selin Yildiz", "role": "Key User", "email": "selin.yildiz@acme.com.tr"
        })
        log("block_2_explore", "2.1c Add Attendee", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # 2.1d — Workshop agenda
    if IDS.get("ws1_o2c"):
        body, code = api("POST", f"/api/v1/explore/workshops/{IDS['ws1_o2c']}/agenda-items", {
            "title": "Standard Sales Order Demo (VA01)", "time": "09:00", "duration_minutes": 45, "sort_order": 1
        })
        log("block_2_explore", "2.1d Add Agenda Item", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # 2.1e — Workshop start/complete transitions
    if IDS.get("ws1_o2c"):
        body, code = api("POST", f"/api/v1/explore/workshops/{IDS['ws1_o2c']}/start", {})
        log("block_2_explore", "2.1e Start Workshop", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # 2.2 — Requirements (Fit-Gap Analysis)
    requirements = [
        # FIT
        {"title": "Standard Sales Order Creation (VA01)", "description": "ACME standard sales order process aligns with SAP Best Practice.",
         "area_code": "SD", "priority": "P1",
         "workshop_id": IDS.get("ws1_o2c"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        {"title": "Standard Pricing Procedure with Discounts", "description": "SAP standard pricing covers ACME needs.",
         "area_code": "SD", "priority": "P1",
         "workshop_id": IDS.get("ws1_o2c"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        {"title": "Available-to-Promise (ATP) Check", "description": "Standard ATP check sufficient.",
         "area_code": "SD", "priority": "P2",
         "workshop_id": IDS.get("ws1_o2c"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        # PARTIAL FIT
        {"title": "Automatic Credit Check with Custom Thresholds", "description": "SAP standard covers 90%. Need BRF+ enhancement.",
         "area_code": "SD", "priority": "P1",
         "workshop_id": IDS.get("ws1_o2c"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        {"title": "Sales Order Confirmation Output", "description": "Custom layout needed with bilingual TR/EN.",
         "area_code": "SD", "priority": "P2",
         "workshop_id": IDS.get("ws1_o2c"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        # GAP
        {"title": "Intercompany Sales with Transfer Pricing", "description": "Transfer pricing logic needs custom ABAP.",
         "area_code": "SD", "priority": "P1",
         "workshop_id": IDS.get("ws1_o2c"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        {"title": "Customer-Specific Pricing Agreement Portal", "description": "Fiori extension + custom CDS views needed.",
         "area_code": "SD", "priority": "P1",
         "workshop_id": IDS.get("ws1_o2c"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        {"title": "Turkish e-Invoice Integration", "description": "UBL-TR XML, digital signature, GIB portal.",
         "area_code": "FI", "priority": "P1",
         "workshop_id": IDS.get("ws1_o2c"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        # P2P Requirements
        {"title": "MRP-Driven PR to PO", "description": "Standard MRP run creates PRs, auto conversion to PO.",
         "area_code": "MM", "priority": "P1",
         "workshop_id": IDS.get("ws3_p2p"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        {"title": "Vendor Evaluation with Custom Criteria", "description": "Need sustainability scoring + ISO tracking.",
         "area_code": "MM", "priority": "P2",
         "workshop_id": IDS.get("ws3_p2p"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        {"title": "Subcontracting with Component Tracking", "description": "Enhanced tracking report needed.",
         "area_code": "MM", "priority": "P1",
         "workshop_id": IDS.get("ws3_p2p"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
        {"title": "Mobile Goods Receipt with Barcode/QR", "description": "Custom Fiori app + RF scanner integration.",
         "area_code": "MM", "priority": "P1",
         "workshop_id": IDS.get("ws3_p2p"), "project_id": pid, "scope_item_id": IDS.get("sso_l3")},
    ]

    req_ok = 0
    for i, req in enumerate(requirements):
        body, code = api("POST", "/api/v1/explore/requirements", req)
        if code in (200, 201):
            req_ok += 1
            req_id = body.get("id")
            if i == 0: IDS["req_sales_order"] = req_id
            elif i == 3: IDS["req_credit_check"] = req_id
            elif i == 4: IDS["req_output"] = req_id
            elif i == 5: IDS["req_intercompany"] = req_id
            elif i == 6: IDS["req_pricing_portal"] = req_id
            elif i == 7: IDS["req_einvoice"] = req_id
            elif i == 8: IDS["req_mrp"] = req_id
            elif i == 9: IDS["req_vendor_eval"] = req_id
            elif i == 10: IDS["req_subcontracting"] = req_id
            elif i == 11: IDS["req_mobile_gr"] = req_id
    log("block_2_explore", "2.2 Create 12 Requirements", "PASS" if req_ok >= 10 else "FAIL", f"{req_ok}/12 created")

    # 2.2b — Requirement filters
    body, code = api("GET", f"/api/v1/explore/requirements?process_area=SD&project_id={pid}")
    if isinstance(body, dict):
        gap_count = len(body.get("items", body.get("requirements", [])))
    elif isinstance(body, list):
        gap_count = len(body)
    else:
        gap_count = 0
    log("block_2_explore", "2.2b Filter requirements by area", "PASS" if gap_count > 0 else "FAIL", f"{gap_count} SD reqs")

    body, code = api("GET", f"/api/v1/explore/requirements?project_id={pid}")
    if isinstance(body, dict):
        sd_count = len(body.get("items", body.get("requirements", [])))
    elif isinstance(body, list):
        sd_count = len(body)
    else:
        sd_count = 0
    log("block_2_explore", "2.2c All requirements", "PASS" if sd_count > 0 else "FAIL", f"{sd_count} total reqs")

    # 2.2d — Requirement stats
    body, code = api("GET", f"/api/v1/explore/requirements/stats?project_id={pid}")
    log("block_2_explore", "2.2d Requirement Stats", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 2.3 — Open Items
    open_items = [
        {"title": "Master Data Migration Strategy Decision", "description": "Full history or active only?",
         "priority": "P1", "category": "process", "project_id": pid},
        {"title": "Integration Architecture — BTP vs Middleware", "description": "MuleSoft vs BTP decision.",
         "priority": "P1", "category": "process", "project_id": pid},
        {"title": "Organizational Structure — Sales Org", "description": "Simplify to 2 sales orgs?",
         "priority": "P2", "category": "process", "project_id": pid},
        {"title": "Go-Live Cutover Window Confirmation", "description": "December 2026 vs January 2027?",
         "priority": "P1", "category": "process", "project_id": pid},
    ]
    oi_ok = 0
    for oi in open_items:
        body, code = api("POST", "/api/v1/explore/open-items", oi)
        if code in (200, 201):
            oi_ok += 1
            if "Migration" in oi["title"]:
                IDS["oi_migration"] = body.get("id")
    log("block_2_explore", "2.3 Create 4 Open Items", "PASS" if oi_ok >= 3 else "FAIL", f"{oi_ok}/4 created")

    # 2.3b — Open Items stats
    body, code = api("GET", f"/api/v1/explore/open-items/stats?project_id={pid}")
    log("block_2_explore", "2.3b Open Items Stats", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 2.3c — Open Item transition
    if IDS.get("oi_migration"):
        body, code = api("POST", f"/api/v1/explore/open-items/{IDS['oi_migration']}/transition", {
            "action": "start_progress", "user_id": "system"
        })
        log("block_2_explore", "2.3c OI Transition", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    print(f"\n  Block 2 Summary: {ws_ok} workshops, {req_ok} requirements, {oi_ok} open items")


# ══════════════════════════════════════════════════════════════
# BLOCK 3: REALIZE — Convert, Config, Backlog, FS/TS, Interfaces
# ══════════════════════════════════════════════════════════════
def block_3():
    print("\n═══ BLOCK 3: REALIZE — Convert & Develop ═══")
    pid = IDS.get("program")
    if not pid:
        log("block_3_realize", "SKIP", "FAIL", "No program ID")
        return

    # 3.0 — First, transition requirements through lifecycle: draft → submit_for_review → approve
    for key in ["req_sales_order", "req_mrp", "req_credit_check", "req_output",
                "req_intercompany", "req_pricing_portal", "req_einvoice",
                "req_vendor_eval", "req_subcontracting", "req_mobile_gr"]:
        req_id = IDS.get(key)
        if req_id:
            # Step 1: draft → under_review
            api("POST", f"/api/v1/explore/requirements/{req_id}/transition", {
                "action": "submit_for_review", "user_id": "system"
            })
            # Step 2: under_review → approved
            api("POST", f"/api/v1/explore/requirements/{req_id}/transition", {
                "action": "approve", "user_id": "system"
            })

    # 3.1 — Convert Fit Requirement → Config Item
    if IDS.get("req_sales_order"):
        body, code = api("POST", f"/api/v1/explore/requirements/{IDS['req_sales_order']}/convert", {
            "target_type": "config", "project_id": pid
        })
        if code in (200, 201):
            IDS["config_sales_order"] = body.get("config_item_id") or body.get("id") or body.get("config_item", {}).get("id")
            log("block_3_realize", "3.1a Convert REQ→Config (Sales Order)", "PASS", f"config_id={IDS.get('config_sales_order')}")
        else:
            log("block_3_realize", "3.1a Convert REQ→Config (Sales Order)", "FAIL", f"code={code} {str(body)[:200]}")

    if IDS.get("req_mrp"):
        body, code = api("POST", f"/api/v1/explore/requirements/{IDS['req_mrp']}/convert", {
            "target_type": "config", "project_id": pid
        })
        log("block_3_realize", "3.1b Convert REQ→Config (MRP)", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # 3.2 — Convert Gap Requirement → Backlog/WRICEF
    gap_converts = [
        ("req_credit_check", "Enhancement", "E"),
        ("req_output", "Form", "F"),
        ("req_intercompany", "Enhancement", "E"),
        ("req_pricing_portal", "Enhancement", "E"),
        ("req_einvoice", "Interface", "I"),
        ("req_vendor_eval", "Enhancement", "E"),
        ("req_subcontracting", "Report", "R"),
        ("req_mobile_gr", "Workflow", "W"),
    ]
    backlog_ok = 0
    for key, wtype, wcode in gap_converts:
        req_id = IDS.get(key)
        if not req_id:
            continue
        body, code = api("POST", f"/api/v1/explore/requirements/{req_id}/convert", {
            "target_type": "backlog", "wricef_type": wcode, "project_id": pid
        })
        if code in (200, 201):
            backlog_ok += 1
            if "einvoice" in key:
                IDS["backlog_einvoice"] = body.get("backlog_item_id") or body.get("id") or body.get("backlog_item", {}).get("id")
            if "intercompany" in key:
                IDS["backlog_intercompany"] = body.get("backlog_item_id") or body.get("id") or body.get("backlog_item", {}).get("id")
        else:
            log("block_3_realize", f"3.2 Convert {key}→Backlog", "FAIL", f"code={code} {str(body)[:150]}")
    log("block_3_realize", "3.2 Convert 8 GAP REQs→Backlog", "PASS" if backlog_ok >= 5 else "FAIL", f"{backlog_ok}/8 converted")

    # 3.2b — Verify backlog list
    body, code = api("GET", f"/api/v1/programs/{pid}/backlog")
    bl_count = len(body) if isinstance(body, list) else (len(body.get("items", [])) if isinstance(body, dict) else 0)
    log("block_3_realize", "3.2b GET Backlog items", "PASS" if bl_count > 0 else "FAIL", f"{bl_count} items")

    # 3.2c — Verify config items
    body, code = api("GET", f"/api/v1/programs/{pid}/config-items")
    ci_count = len(body) if isinstance(body, list) else (len(body.get("items", [])) if isinstance(body, dict) else 0)
    log("block_3_realize", "3.2c GET Config items", "PASS" if ci_count > 0 else "FAIL", f"{ci_count} items")

    # 3.3 — Functional Spec
    bl_id = IDS.get("backlog_einvoice")
    if bl_id:
        body, code = api("POST", f"/api/v1/backlog/{bl_id}/functional-spec", {
            "title": "FS — Turkish e-Invoice Integration",
            "content": "## 1. Overview\nIntegration between SAP S/4HANA billing documents and Turkish GIB e-Invoice system.\n\n## 2. Scope\n- e-Invoice (B2B)\n- e-Archive (B2C)\n- e-Waybill (Dispatch Note)",
            "status": "Draft",
            "version": "1.0",
            "author": "Can Ozturk"
        })
        if code in (200, 201):
            IDS["fs_einvoice"] = body.get("id")
            log("block_3_realize", "3.3a Create Functional Spec", "PASS", f"id={IDS.get('fs_einvoice')}")
        else:
            log("block_3_realize", "3.3a Create Functional Spec", "FAIL", f"code={code} {str(body)[:200]}")

        # 3.3b — Technical Spec
        fs_id = IDS.get("fs_einvoice")
        if fs_id:
            body, code = api("POST", f"/api/v1/functional-specs/{fs_id}/technical-spec", {
                "title": "TS — Turkish e-Invoice Integration",
                "content": "## 1. Architecture\nCustom ABAP class ZCL_EINVOICE_HANDLER.\n\n## 2. Custom Objects\n- ZCL_EINVOICE_HANDLER\n- ZTABLE_EINV_LOG",
                "status": "Draft",
                "version": "1.0",
                "author": "Burak Sahin"
            })
            if code in (200, 201):
                IDS["ts_einvoice"] = body.get("id")
                log("block_3_realize", "3.3b Create Technical Spec", "PASS", f"id={IDS.get('ts_einvoice')}")
            else:
                log("block_3_realize", "3.3b Create Technical Spec", "FAIL", f"code={code} {str(body)[:200]}")

    # 3.4 — Interfaces
    interfaces = [
        {"name": "e-Invoice Integration (GIB)", "direction": "outbound",
         "source_system": "SAP S/4HANA", "target_system": "Foriba Connect → GIB Portal",
         "protocol": "rest", "frequency": "Real-time", "status": "identified"},
        {"name": "Bank Statement Import (MT940/CAMT.053)", "direction": "inbound",
         "source_system": "Isbank / Garanti BBVA", "target_system": "SAP S/4HANA FI",
         "protocol": "file", "frequency": "Daily", "status": "identified"},
        {"name": "EDI Integration with OEM Customers", "direction": "bidirectional",
         "source_system": "SAP S/4HANA SD", "target_system": "Customer EDI Platforms",
         "protocol": "other", "frequency": "Real-time", "status": "identified"},
        {"name": "MES Integration (Siemens)", "direction": "bidirectional",
         "source_system": "SAP S/4HANA PP", "target_system": "Siemens SIMATIC IT MES",
         "protocol": "rest", "frequency": "Real-time", "status": "identified"},
    ]
    int_ok = 0
    for intf in interfaces:
        body, code = api("POST", f"/api/v1/programs/{pid}/interfaces", intf)
        if code in (200, 201):
            int_ok += 1
            if "GIB" in intf["name"]:
                IDS["int_einvoice"] = body.get("id")
        else:
            log("block_3_realize", f"3.4 Interface: {intf['name'][:30]}", "FAIL", f"code={code} {str(body)[:150]}")
    log("block_3_realize", "3.4 Create 4 Interfaces", "PASS" if int_ok >= 3 else "FAIL", f"{int_ok}/4 created")

    # 3.4b — Verify interfaces list
    body, code = api("GET", f"/api/v1/programs/{pid}/interfaces")
    int_count = len(body) if isinstance(body, list) else (len(body.get("items", body.get("interfaces", []))) if isinstance(body, dict) else 0)
    log("block_3_realize", "3.4b GET Interfaces", "PASS" if int_count > 0 else "FAIL", f"{int_count} interfaces")

    # 3.5 — Sprints
    body, code = api("POST", f"/api/v1/programs/{pid}/sprints", {
        "name": "Sprint 1 — Core Config",
        "start_date": "2026-07-01",
        "end_date": "2026-07-14",
        "status": "Planned"
    })
    if code in (200, 201):
        IDS["sprint1"] = body.get("id")
    log("block_3_realize", "3.5 Create Sprint", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    print(f"\n  Block 3 Summary: Converts done, FS/TS created, {int_ok} interfaces, Sprint created")


# ══════════════════════════════════════════════════════════════
# BLOCK 4: TESTING — Plans, Catalog, Cycles, Executions, Defects
# ══════════════════════════════════════════════════════════════
def block_4():
    print("\n═══ BLOCK 4: TEST MANAGEMENT ═══")
    pid = IDS.get("program")
    if not pid:
        log("block_4_testing", "SKIP", "FAIL", "No program ID")
        return

    # 4.1 — Test Plan
    body, code = api("POST", f"/api/v1/programs/{pid}/testing/plans", {
        "name": "ACME S/4HANA Test Plan",
        "description": "Comprehensive test plan covering Unit, SIT, UAT, and Regression testing",
        "status": "Draft"
    })
    if code in (200, 201):
        IDS["test_plan"] = body.get("id")
        log("block_4_testing", "4.1a Create Test Plan", "PASS", f"id={IDS['test_plan']}")
    else:
        log("block_4_testing", "4.1a Create Test Plan", "FAIL", f"code={code} {str(body)[:200]}")

    # 4.1b — Test Suites
    suites = [
        {"name": "SD — Sales Order Config Tests", "module": "SD"},
        {"name": "MM — Procurement Tests", "module": "MM"},
        {"name": "FI — e-Invoice Tests", "module": "FI"},
        {"name": "PP — Production Tests", "module": "PP"},
    ]
    suite_ok = 0
    for s in suites:
        body, code = api("POST", f"/api/v1/programs/{pid}/testing/suites", s)
        if code in (200, 201):
            suite_ok += 1
            if s["module"] == "SD":
                IDS["suite_sd"] = body.get("id")
            elif s["module"] == "FI":
                IDS["suite_fi"] = body.get("id")
    log("block_4_testing", "4.1b Create 4 Test Suites", "PASS" if suite_ok >= 3 else "FAIL", f"{suite_ok}/4")

    # 4.2 — Test Catalog (Test Cases)
    test_cases = [
        {"title": "UT — Standard Sales Order Creation & Delivery",
         "description": "Verify standard sales order (OR) creation with pricing, ATP, delivery, billing.",
         "test_type": "Unit", "priority": "High", "status": "Draft",
         "steps": "1. Create quotation\n2. Create sales order\n3. Verify pricing\n4. ATP check\n5. Create delivery\n6. Post GI\n7. Create billing\n8. Verify accounting",
         "expected_result": "All documents created. Pricing correct. ATP date reasonable."},
        {"title": "UT — e-Invoice XML Generation",
         "description": "Verify UBL-TR XML generation from billing document.",
         "test_type": "Unit", "priority": "Critical", "status": "Draft",
         "steps": "1. Create billing document\n2. Trigger output\n3. Verify XML\n4. Check signature\n5. Submit to GIB test\n6. Check response\n7. Verify log",
         "expected_result": "XML generated. Signature valid. GIB accepts."},
        {"title": "SIT — Order to Cash Full Cycle",
         "description": "E2E: quotation → order → delivery → billing → e-invoice → payment",
         "test_type": "SIT", "priority": "Critical", "status": "Draft",
         "steps": "1. Create inquiry\n2. Quotation\n3. Sales order\n4. Credit check\n5. Delivery\n6. Pick/pack\n7. GI\n8. Billing\n9. e-Invoice\n10. Payment\n11. Clearing",
         "expected_result": "Complete O2C cycle. All integration points working."},
        {"title": "UAT — Export Sales with Intercompany",
         "description": "Business user validates export sales via Germany sales office.",
         "test_type": "UAT", "priority": "Critical", "status": "Draft",
         "steps": "1. German customer order\n2. DE sales org\n3. Intercompany STO\n4. Delivery from TR\n5. IC billing\n6. Customer billing\n7. Transfer pricing check\n8. EUR/TRY\n9. Customs docs",
         "expected_result": "Export process E2E. Transfer pricing correct."},
    ]
    tc_ok = 0
    for i, tc in enumerate(test_cases):
        body, code = api("POST", f"/api/v1/programs/{pid}/testing/catalog", tc)
        if code in (200, 201):
            tc_ok += 1
            tc_id = body.get("id")
            if i == 0: IDS["tc_sales_order"] = tc_id
            elif i == 1: IDS["tc_einvoice"] = tc_id
            elif i == 2: IDS["tc_o2c_sit"] = tc_id
            elif i == 3: IDS["tc_export_uat"] = tc_id
        else:
            log("block_4_testing", f"Test case: {tc['title'][:40]}", "FAIL", f"code={code} {str(body)[:150]}")
    log("block_4_testing", "4.2 Create 4 Test Cases", "PASS" if tc_ok >= 3 else "FAIL", f"{tc_ok}/4")

    # 4.2b — Test case steps
    if IDS.get("tc_sales_order"):
        body, code = api("POST", f"/api/v1/testing/catalog/{IDS['tc_sales_order']}/steps", {
            "step_number": 1, "action": "Create quotation (VA21)", "expected_result": "Quotation created"
        })
        log("block_4_testing", "4.2b Add Test Step", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # 4.3 — Test Cycle
    plan_id = IDS.get("test_plan")
    if plan_id:
        body, code = api("POST", f"/api/v1/testing/plans/{plan_id}/cycles", {
            "name": "SIT Round 1 — System Integration Testing",
            "description": "First round of integration testing",
            "status": "Planned",
            "start_date": "2026-09-01",
            "end_date": "2026-09-15",
            "test_type": "SIT"
        })
        if code in (200, 201):
            IDS["sit_r1"] = body.get("id")
            log("block_4_testing", "4.3a Create SIT Cycle", "PASS", f"id={IDS['sit_r1']}")
        else:
            log("block_4_testing", "4.3a Create SIT Cycle", "FAIL", f"code={code} {str(body)[:200]}")

    # 4.3b — Test Run (Execution)
    cycle_id = IDS.get("sit_r1")
    if cycle_id and IDS.get("tc_sales_order"):
        body, code = api("POST", f"/api/v1/testing/cycles/{cycle_id}/runs", {
            "test_case_id": IDS["tc_sales_order"],
            "status": "Pass",
            "executed_by": "Zeynep Arslan",
            "executed_date": "2026-09-03",
            "actual_result": "All documents created successfully.",
            "environment": "QAS-100"
        })
        if code in (200, 201):
            IDS["run_pass"] = body.get("id")
            log("block_4_testing", "4.3b Test Run (Pass)", "PASS", f"id={IDS.get('run_pass')}")
        else:
            log("block_4_testing", "4.3b Test Run (Pass)", "FAIL", f"code={code} {str(body)[:200]}")

    # Failed run
    if cycle_id and IDS.get("tc_einvoice"):
        body, code = api("POST", f"/api/v1/testing/cycles/{cycle_id}/runs", {
            "test_case_id": IDS["tc_einvoice"],
            "status": "Fail",
            "executed_by": "Can Ozturk",
            "executed_date": "2026-09-05",
            "actual_result": "Digital signature fails with CERT_EXPIRED.",
            "environment": "QAS-100"
        })
        if code in (200, 201):
            IDS["run_fail"] = body.get("id")
            log("block_4_testing", "4.3c Test Run (Fail)", "PASS", f"id={IDS.get('run_fail')}")
        else:
            log("block_4_testing", "4.3c Test Run (Fail)", "FAIL", f"code={code} {str(body)[:200]}")

    # 4.4 — Defects
    defects = [
        {"title": "e-Invoice digital signature fails — expired test certificate",
         "description": "CERT_EXPIRED error during SIT. Need to renew test certificate.",
         "severity": "High", "priority": "High", "status": "Open", "module": "FI",
         "assigned_to": "Emre Celik", "environment": "QAS-100"},
        {"title": "Intercompany billing uses wrong transfer price",
         "description": "Using sales price instead of cost-plus. Pricing procedure ZVKIC needs fix.",
         "severity": "Critical", "priority": "Critical", "status": "Open", "module": "SD",
         "assigned_to": "Zeynep Arslan", "environment": "QAS-100"},
        {"title": "MRP run takes 4+ hours for full planning run",
         "description": "Target: under 2 hours. Evaluate MRP Live.",
         "severity": "High", "priority": "Medium", "status": "Open", "module": "PP",
         "assigned_to": "Emre Celik", "category": "Performance", "environment": "QAS-100"},
    ]
    def_ok = 0
    for i, d in enumerate(defects):
        body, code = api("POST", f"/api/v1/programs/{pid}/testing/defects", d)
        if code in (200, 201):
            def_ok += 1
            if i == 0: IDS["defect_cert"] = body.get("id")
            elif i == 1: IDS["defect_ic"] = body.get("id")
        else:
            log("block_4_testing", f"Defect: {d['title'][:40]}", "FAIL", f"code={code} {str(body)[:150]}")
    log("block_4_testing", "4.4 Create 3 Defects", "PASS" if def_ok >= 2 else "FAIL", f"{def_ok}/3")

    # 4.4b — Defect SLA check
    if IDS.get("defect_cert"):
        body, code = api("GET", f"/api/v1/testing/defects/{IDS['defect_cert']}/sla")
        log("block_4_testing", "4.4b Defect SLA", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 4.4c — Defect comment
    if IDS.get("defect_cert"):
        body, code = api("POST", f"/api/v1/testing/defects/{IDS['defect_cert']}/comments", {
            "author": "Emre Celik", "body": "Renewing certificate from GIB test portal."
        })
        log("block_4_testing", "4.4c Defect Comment", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # 4.5 — Testing Dashboard
    body, code = api("GET", f"/api/v1/programs/{pid}/testing/dashboard")
    log("block_4_testing", "4.5 Testing Dashboard", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 4.5b — Go/No-Go
    body, code = api("GET", f"/api/v1/programs/{pid}/testing/dashboard/go-no-go")
    log("block_4_testing", "4.5b Go/No-Go Dashboard", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 4.5c — Traceability Matrix
    body, code = api("GET", f"/api/v1/programs/{pid}/testing/traceability-matrix")
    log("block_4_testing", "4.5c Traceability Matrix", "PASS" if code == 200 else "FAIL", f"code={code}")

    print(f"\n  Block 4 Summary: Plan, {suite_ok} suites, {tc_ok} test cases, {def_ok} defects")


# ══════════════════════════════════════════════════════════════
# BLOCK 5: DEPLOY — Cutover, Data Migration, Go/No-Go
# ══════════════════════════════════════════════════════════════
def block_5():
    print("\n═══ BLOCK 5: DEPLOY — Cutover & Data Migration ═══")
    pid = IDS.get("program")
    if not pid:
        log("block_5_deploy", "SKIP", "FAIL", "No program ID")
        return

    # 5.1 — Cutover Plan
    body, code = api("POST", "/api/v1/cutover/plans", {
        "name": "ACME S/4HANA Go-Live Cutover Plan",
        "description": "Production cutover plan for December 2026 go-live",
        "program_id": pid,
        "status": "Draft",
        "planned_start": "2026-12-12T18:00:00",
        "planned_end": "2026-12-15T06:00:00"
    })
    if code in (200, 201):
        IDS["cutover_plan"] = body.get("id")
        log("block_5_deploy", "5.1a Create Cutover Plan", "PASS", f"id={IDS['cutover_plan']}")
    else:
        log("block_5_deploy", "5.1a Create Cutover Plan", "FAIL", f"code={code} {str(body)[:200]}")

    cp_id = IDS.get("cutover_plan")
    if not cp_id:
        # Try listing existing
        body, code = api("GET", "/api/v1/cutover/plans")
        if isinstance(body, list) and body:
            cp_id = body[0].get("id")
            IDS["cutover_plan"] = cp_id

    # 5.1b — Cutover Scope Items
    if cp_id:
        scope_items = [
            {"name": "System Freeze & Data Extract", "category": "data_load", "order": 1},
            {"name": "Master Data Migration", "category": "data_load", "order": 2},
            {"name": "Open Documents Migration", "category": "data_load", "order": 3},
            {"name": "Transport Import to PRD", "category": "custom", "order": 4},
            {"name": "Integration Smoke Test", "category": "reconciliation", "order": 5},
        ]
        si_ok = 0
        for si in scope_items:
            body, code = api("POST", f"/api/v1/cutover/plans/{cp_id}/scope-items", si)
            if code in (200, 201):
                si_ok += 1
                if si["order"] == 1:
                    IDS["scope_item_1"] = body.get("id")
        log("block_5_deploy", "5.1b Create 5 Scope Items", "PASS" if si_ok >= 3 else "FAIL", f"{si_ok}/5")

    # 5.1c — Cutover Tasks
    si_id = IDS.get("scope_item_1")
    if si_id:
        tasks = [
            {"title": "Lock ECC transactions via SM01", "sequence": 1, "duration_hours": 1,
             "responsible": "Emre Celik", "status": "Planned"},
            {"title": "Run final data extract programs", "sequence": 2, "duration_hours": 4,
             "responsible": "Ali Demir", "status": "Planned"},
        ]
        task_ok = 0
        for t in tasks:
            body, code = api("POST", f"/api/v1/cutover/scope-items/{si_id}/tasks", t)
            if code in (200, 201):
                task_ok += 1
                if t["sequence"] == 1:
                    IDS["cutover_task_1"] = body.get("id")
        log("block_5_deploy", "5.1c Create Cutover Tasks", "PASS" if task_ok > 0 else "FAIL", f"{task_ok}/2")

    # 5.1d — Cutover progress
    if cp_id:
        body, code = api("GET", f"/api/v1/cutover/plans/{cp_id}/progress")
        log("block_5_deploy", "5.1d Cutover Progress", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 5.1e — Rehearsal
    if cp_id:
        body, code = api("POST", f"/api/v1/cutover/plans/{cp_id}/rehearsals", {
            "name": "Dress Rehearsal 1",
            "planned_start": "2026-11-15T18:00:00",
            "planned_end": "2026-11-16T12:00:00",
            "status": "Planned"
        })
        if code in (200, 201):
            IDS["rehearsal_1"] = body.get("id")
        log("block_5_deploy", "5.1e Create Rehearsal", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # 5.1f — Go/No-Go Checklist
    if cp_id:
        body, code = api("POST", f"/api/v1/cutover/plans/{cp_id}/go-no-go/seed", {})
        log("block_5_deploy", "5.1f Seed Go/No-Go", "PASS" if code in (200,201) else "FAIL", f"code={code}")

        body, code = api("GET", f"/api/v1/cutover/plans/{cp_id}/go-no-go/summary")
        log("block_5_deploy", "5.1g Go/No-Go Summary", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 5.2 — Data Factory (Data Migration)
    df_objects = [
        {"name": "Customer Master (KNA1/KNVV)", "object_type": "Master Data",
         "source_system": "ECC 6.0", "record_count": 15000, "tool": "Migration Cockpit", "status": "Mapping"},
        {"name": "Material Master (MARA/MARC)", "object_type": "Master Data",
         "source_system": "ECC 6.0", "record_count": 45000, "tool": "Migration Cockpit", "status": "Mapping"},
        {"name": "Vendor Master (LFA1/LFB1)", "object_type": "Master Data",
         "source_system": "ECC 6.0", "record_count": 5000, "tool": "Migration Cockpit", "status": "Mapping"},
        {"name": "Open Sales Orders", "object_type": "Transaction Data",
         "source_system": "ECC 6.0", "record_count": 2000, "tool": "LSMW", "status": "Analysis"},
    ]
    df_ok = 0
    for obj in df_objects:
        body, code = api("POST", "/api/v1/data-factory/objects", {**obj, "program_id": pid})
        if code in (200, 201):
            df_ok += 1
            if "Customer" in obj["name"]:
                IDS["df_customer"] = body.get("id")
    log("block_5_deploy", "5.2a Create 4 Data Migration Objects", "PASS" if df_ok >= 3 else "FAIL", f"{df_ok}/4")

    # 5.2b — Data Factory Waves
    body, code = api("POST", "/api/v1/data-factory/waves", {
        "name": "Wave 1 — Master Data", "wave_number": 1, "status": "planned", "program_id": pid
    })
    if code in (200, 201):
        IDS["df_wave1"] = body.get("id")
    log("block_5_deploy", "5.2b Create Migration Wave", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    # 5.2c — Data quality score
    body, code = api("GET", f"/api/v1/data-factory/quality-score?program_id={pid}")
    log("block_5_deploy", "5.2c Data Quality Score", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 5.3 — RAID (Risks)
    risks = [
        {"title": "Data migration quality risk", "description": "45K materials, many may have incomplete data.",
         "probability": 4, "impact": 4, "status": "identified", "risk_category": "technical",
         "owner": "Ali Demir"},
        {"title": "Go-Live date at risk due to e-Invoice delays",
         "description": "GIB certification timeline uncertain.",
         "probability": 3, "impact": 5, "status": "identified", "risk_category": "technical",
         "owner": "Can Ozturk"},
    ]
    risk_ok = 0
    for r in risks:
        body, code = api("POST", f"/api/v1/programs/{pid}/risks", r)
        if code in (200, 201):
            risk_ok += 1
    log("block_5_deploy", "5.3 Create 2 Risks", "PASS" if risk_ok > 0 else "FAIL", f"{risk_ok}/2")

    # 5.3b — Risk heatmap
    body, code = api("GET", f"/api/v1/programs/{pid}/raid/heatmap")
    log("block_5_deploy", "5.3b RAID Heatmap", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 5.4 — SLA Targets
    if cp_id:
        body, code = api("POST", f"/api/v1/cutover/plans/{cp_id}/sla-targets/seed", {})
        log("block_5_deploy", "5.4 Seed SLA Targets", "PASS" if code in (200,201) else "FAIL", f"code={code}")

    print(f"\n  Block 5 Summary: Cutover plan, scope items, data factory, RAID done")


# ══════════════════════════════════════════════════════════════
# BLOCK 6: TRACEABILITY, REPORTING, RUN-SUSTAIN
# ══════════════════════════════════════════════════════════════
def block_6():
    print("\n═══ BLOCK 6: TRACEABILITY & CROSS-CUTTING ═══")
    pid = IDS.get("program")
    if not pid:
        log("block_6_traceability", "SKIP", "FAIL", "No program ID")
        return

    # 6.1 — Traceability chain
    req_id = IDS.get("req_einvoice")
    if req_id:
        body, code = api("GET", f"/api/v1/traceability/chain/explore_requirement/{req_id}")
        if code == 200:
            depth = body.get("chain_depth", 0) if isinstance(body, dict) else 0
            log("block_6_traceability", "6.1a Traceability Chain (e-Invoice)", "PASS", f"depth={depth}")
        else:
            # Try alternate endpoint
            body2, code2 = api("GET", f"/api/v1/traceability/explore_requirement/{req_id}")
            log("block_6_traceability", "6.1a Traceability Chain", "PASS" if code2 == 200 else "FAIL",
                f"chain={code}, alt={code2}")

    # 6.1b — Linked items
    if req_id:
        body, code = api("GET", f"/api/v1/explore/requirements/{req_id}/linked-items")
        if code != 200:
            # Try alternate path
            body, code = api("GET", f"/api/v1/traceability/linked-items/explore_requirement/{req_id}")
        log("block_6_traceability", "6.1b Linked Items", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 6.1c — Program traceability summary
    body, code = api("GET", f"/api/v1/programs/{pid}/traceability/summary")
    log("block_6_traceability", "6.1c Traceability Summary", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 6.2 — Reporting
    body, code = api("GET", f"/api/v1/reports/program-health/{pid}")
    log("block_6_traceability", "6.2a Program Health Report", "PASS" if code == 200 else "FAIL", f"code={code}")

    body, code = api("GET", f"/api/v1/reports/weekly/{pid}")
    log("block_6_traceability", "6.2b Weekly Report", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 6.3 — Audit trail
    body, code = api("GET", "/api/v1/audit")
    audit_count = len(body) if isinstance(body, list) else (len(body.get("items", [])) if isinstance(body, dict) else 0)
    log("block_6_traceability", "6.3 Audit Trail", "PASS" if code == 200 else "FAIL", f"{audit_count} entries")

    # 6.4 — Run & Sustain
    cp_id = IDS.get("cutover_plan")
    if cp_id:
        body, code = api("POST", f"/api/v1/run-sustain/plans/{cp_id}/knowledge-transfer", {
            "title": "SD Module KT Session",
            "topic_area": "functional",
            "trainer": "Zeynep Arslan",
            "status": "planned",
            "format": "workshop"
        })
        log("block_6_traceability", "6.4a Knowledge Transfer", "PASS" if code in (200,201) else "FAIL", f"code={code}")

        body, code = api("POST", f"/api/v1/run-sustain/plans/{cp_id}/handover-items/seed", {})
        log("block_6_traceability", "6.4b Seed Handover Items", "PASS" if code in (200,201) else "FAIL", f"code={code}")

        body, code = api("GET", f"/api/v1/run-sustain/plans/{cp_id}/dashboard")
        log("block_6_traceability", "6.4c Run-Sustain Dashboard", "PASS" if code == 200 else "FAIL", f"code={code}")

        body, code = api("GET", f"/api/v1/run-sustain/plans/{cp_id}/exit-readiness")
        log("block_6_traceability", "6.4d Exit Readiness", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 6.5 — Notifications
    body, code = api("GET", "/api/v1/notifications/unread-count")
    log("block_6_traceability", "6.5 Notifications Count", "PASS" if code == 200 else "FAIL", f"code={code}")

    # 6.6 — Metrics
    body, code = api("GET", "/api/v1/metrics/requests")
    log("block_6_traceability", "6.6 Request Metrics", "PASS" if code == 200 else "FAIL", f"code={code}")

    print(f"\n  Block 6 Summary: Traceability, reports, audit, run-sustain done")


# ══════════════════════════════════════════════════════════════
# FINAL REPORT
# ══════════════════════════════════════════════════════════════
def final_report():
    print("\n" + "=" * 70)
    print("  📊 SAP ACTIVATE E2E TEST — FINAL REPORT")
    print("=" * 70)
    print(f"  Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Server: {BASE}")
    print(f"  Program ID: {IDS.get('program', 'N/A')}")
    print()

    total_pass = 0
    total_fail = 0
    total_warn = 0

    for block_name, tests in RESULTS.items():
        if not tests:
            continue
        passes = sum(1 for t in tests if t["status"] == "PASS")
        fails = sum(1 for t in tests if t["status"] == "FAIL")
        warns = sum(1 for t in tests if t["status"] == "WARN")
        total_pass += passes
        total_fail += fails
        total_warn += warns
        status = "✅" if fails == 0 else "❌"
        print(f"  {status} {block_name}: {passes} pass, {fails} fail, {warns} warn")

    print()
    print(f"  TOTAL: ✅ {total_pass} PASS | ❌ {total_fail} FAIL | ⚠️  {total_warn} WARN")
    rate = total_pass / max(total_pass + total_fail, 1) * 100
    print(f"  Pass Rate: {rate:.1f}%")
    print()

    # List failures
    if total_fail > 0:
        print("  ── FAILURES ──")
        for block_name, tests in RESULTS.items():
            for t in tests:
                if t["status"] == "FAIL":
                    print(f"    ❌ [{block_name}] {t['test']}: {t['detail']}")

    # SAP Activate Phase Coverage
    print("\n  ── SAP ACTIVATE PHASE COVERAGE ──")
    phases = {
        "Discover": ["Program create", "Phase create"],
        "Prepare": ["Team", "Process Levels", "Workstreams"],
        "Explore": ["Workshops", "Requirements", "Open Items", "Attendees", "Agenda"],
        "Realize": ["Convert→Config", "Convert→Backlog", "FS/TS", "Interfaces", "Sprints"],
        "Deploy": ["Cutover Plan", "Scope Items", "Tasks", "Go/No-Go", "Data Factory", "Rehearsal"],
        "Run": ["Knowledge Transfer", "Handover", "Stabilization", "Exit Readiness"],
    }
    for phase, features in phases.items():
        print(f"    {phase}: {', '.join(features)}")

    # Created IDs
    print(f"\n  ── CREATED ENTITIES ({len(IDS)}) ──")
    for k, v in IDS.items():
        print(f"    {k}: {v}")

    print("\n" + "=" * 70)


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("🧪 SAP ACTIVATE E2E LOCAL TEST — Starting...")
    print(f"   Target: {BASE}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    block_0()
    block_1()
    block_2()
    block_3()
    block_4()
    block_5()
    block_6()
    final_report()
