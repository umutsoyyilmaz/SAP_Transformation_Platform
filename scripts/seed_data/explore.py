"""
SEED-002 — Explore Phase Demo Data
Company: Anadolu Gıda ve İçecek A.Ş.  |  Project: "S/4HANA Greenfield 2026"

Hierarchy:  5 L1  →  10 L2  →  50 L3  →  200 L4
Workshops:  20 (mixed statuses)
Steps:      100 process_steps (fit decisions)
Decisions:  50
Open Items: 30
Requirements: 40
+ attendees, agenda items, scope items, links
"""
import uuid
from datetime import date, datetime, timedelta

# ── helpers ──────────────────────────────────────────────────────────────
_BASE = datetime(2026, 3, 1, 8, 0, 0)


def _id(tag: str) -> str:
    """Deterministic UUID from tag for reproducible seeding."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"explore-demo-{tag}"))


# ═════════════════════════════════════════════════════════════════════════
# 1. PROCESS HIERARCHY  (5 L1  → 10 L2  → 50 L3  → 200 L4)
# ═════════════════════════════════════════════════════════════════════════

PROCESS_LEVELS = []

# ── L1 End-to-End Processes ──────────────────────────────────────────────
_L1 = [
    ("L1-OTC", "Order to Cash", "SD"),
    ("L1-PTP", "Procure to Pay", "MM"),
    ("L1-RTR", "Record to Report", "FI"),
    ("L1-PTD", "Plan to Deliver", "PP"),
    ("L1-HCM", "Hire to Retire", "HR"),
]

for i, (code, name, area) in enumerate(_L1, 1):
    PROCESS_LEVELS.append({
        "id": _id(code), "project_id": 1, "parent_id": None,
        "level": 1, "code": code, "name": name,
        "description": f"End-to-end {name} process group",
        "scope_status": "in_scope", "fit_status": None,
        "process_area_code": area, "wave": 1, "sort_order": i,
    })

# ── L2 Process Groups (2 per L1 = 10) ────────────────────────────────────
_L2_MAP = {
    "L1-OTC": [("L2-SD-SALES", "Sales Order Management", "SD", 1),
               ("L2-SD-SHIP",  "Delivery & Shipping",     "SD", 1)],
    "L1-PTP": [("L2-MM-PROC",  "Procurement",             "MM", 1),
               ("L2-MM-INV",   "Invoice Verification",    "MM", 2)],
    "L1-RTR": [("L2-FI-GL",    "General Ledger",          "FI", 1),
               ("L2-FI-AP",    "Accounts Payable",        "FI", 2)],
    "L1-PTD": [("L2-PP-PLAN",  "Production Planning",     "PP", 2),
               ("L2-PP-EXEC",  "Shop Floor Execution",    "PP", 2)],
    "L1-HCM": [("L2-HR-PA",    "Personnel Administration","HR", 3),
               ("L2-HR-TIME",  "Time Management",         "HR", 3)],
}

for l1_code, children in _L2_MAP.items():
    for j, (code, name, area, wave) in enumerate(children, 1):
        PROCESS_LEVELS.append({
            "id": _id(code), "project_id": 1, "parent_id": _id(l1_code),
            "level": 2, "code": code, "name": name,
            "description": f"{name} process group under {l1_code}",
            "scope_status": "in_scope", "fit_status": None,
            "process_area_code": area, "wave": wave, "sort_order": j,
            "readiness_pct": 0.0,
        })

# ── L3 Scope Items (5 per L2 = 50) ───────────────────────────────────────
_L3_NAMES = {
    "L2-SD-SALES": [("1OC", "Standard Sales Order"),
                     ("2OC", "Credit Management"),
                     ("3OC", "Third-Party Sales"),
                     ("4OC", "Consignment Sales"),
                     ("5OC", "Free-of-Charge Delivery")],
    "L2-SD-SHIP":  [("1SH", "Outbound Delivery"),
                     ("2SH", "Picking & Packing"),
                     ("3SH", "Proof of Delivery"),
                     ("4SH", "Transportation"),
                     ("5SH", "Returns Processing")],
    "L2-MM-PROC":  [("1MM", "Purchase Requisition"),
                     ("2MM", "Purchase Order"),
                     ("3MM", "Source Determination"),
                     ("4MM", "Contract Management"),
                     ("5MM", "Vendor Evaluation")],
    "L2-MM-INV":   [("1IV", "3-Way Match"),
                     ("2IV", "ERS Processing"),
                     ("3IV", "Blocked Invoices"),
                     ("4IV", "Down Payments"),
                     ("5IV", "GR/IR Clearing")],
    "L2-FI-GL":    [("1GL", "Journal Entry"),
                     ("2GL", "Period-End Closing"),
                     ("3GL", "Accruals & Deferrals"),
                     ("4GL", "Financial Statements"),
                     ("5GL", "Intercompany")],
    "L2-FI-AP":    [("1AP", "Vendor Invoice"),
                     ("2AP", "Payment Run"),
                     ("3AP", "Vendor Down Payment"),
                     ("4AP", "Bank Reconciliation"),
                     ("5AP", "Withholding Tax")],
    "L2-PP-PLAN":  [("1PL", "MRP Run"),
                     ("2PL", "Planned Order Conversion"),
                     ("3PL", "Scheduling"),
                     ("4PL", "Demand Management"),
                     ("5PL", "BOM & Routing")],
    "L2-PP-EXEC":  [("1EX", "Production Order Release"),
                     ("2EX", "Goods Issue to Prod"),
                     ("3EX", "Operation Confirmation"),
                     ("4EX", "Goods Receipt from Prod"),
                     ("5EX", "Order Settlement")],
    "L2-HR-PA":    [("1PA", "Hire Employee"),
                     ("2PA", "Org Management"),
                     ("3PA", "Personnel Change"),
                     ("4PA", "Termination"),
                     ("5PA", "Payroll Processing")],
    "L2-HR-TIME":  [("1TM", "Time Recording"),
                     ("2TM", "Absence Management"),
                     ("3TM", "Overtime & Shift"),
                     ("4TM", "Time Evaluation"),
                     ("5TM", "Attendance & Sub")],
}

_L3_IDS = {}  # code → id  (used later for workshop scope items)
for l2_code, items in _L3_NAMES.items():
    parent_area = next(p["process_area_code"] for p in PROCESS_LEVELS
                       if p["code"] == l2_code)
    parent_wave = next(p.get("wave", 1) for p in PROCESS_LEVELS
                       if p["code"] == l2_code)
    for k, (scope_code, name) in enumerate(items, 1):
        l3_code = f"L3-{scope_code}"
        l3_id = _id(l3_code)
        _L3_IDS[l3_code] = l3_id
        PROCESS_LEVELS.append({
            "id": l3_id, "project_id": 1, "parent_id": _id(l2_code),
            "level": 3, "code": l3_code, "name": name,
            "description": f"Scope item {scope_code}: {name}",
            "scope_status": "in_scope", "fit_status": "pending",
            "scope_item_code": scope_code,
            "process_area_code": parent_area, "wave": parent_wave,
            "sort_order": k,
        })

# ── L4 Sub-Processes (4 per L3 = 200) ────────────────────────────────────
_L4_IDS = {}  # l4_code → id
_l4_seq = 0
for l3_code, l3_id in _L3_IDS.items():
    scope_code = l3_code.replace("L3-", "")
    parent = next(p for p in PROCESS_LEVELS if p["id"] == l3_id)
    for n in range(1, 5):
        _l4_seq += 1
        l4_code = f"L4-{scope_code}-{n:02d}"
        l4_id = _id(l4_code)
        _L4_IDS[l4_code] = l4_id
        PROCESS_LEVELS.append({
            "id": l4_id, "project_id": 1, "parent_id": l3_id,
            "level": 4, "code": l4_code,
            "name": f"{parent['name']} — Step {n}",
            "description": f"Sub-process step {n} of {scope_code}",
            "scope_status": "in_scope", "fit_status": "pending",
            "scope_item_code": scope_code,
            "process_area_code": parent["process_area_code"],
            "wave": parent.get("wave", 1), "sort_order": n,
        })

assert len([p for p in PROCESS_LEVELS if p["level"] == 1]) == 5
assert len([p for p in PROCESS_LEVELS if p["level"] == 2]) == 10
assert len([p for p in PROCESS_LEVELS if p["level"] == 3]) == 50
assert len([p for p in PROCESS_LEVELS if p["level"] == 4]) == 200

# ═════════════════════════════════════════════════════════════════════════
# 2. WORKSHOPS  (20 — mixed statuses across areas)
# ═════════════════════════════════════════════════════════════════════════

_WS_DEFS = [
    # (code, name, type, status, area, wave, facilitator, session, total, l3_codes_slice)
    ("WS-SD-001",  "SD Sales Order F2S",      "fit_to_standard", "completed",  "SD", 1, "usr-002", 1, 1, ["L3-1OC","L3-2OC"]),
    ("WS-SD-002",  "SD Shipping F2S",         "fit_to_standard", "completed",  "SD", 1, "usr-002", 1, 1, ["L3-1SH","L3-2SH"]),
    ("WS-SD-003",  "SD Returns Deep Dive",    "deep_dive",       "completed",  "SD", 1, "usr-002", 1, 1, ["L3-5SH"]),
    ("WS-SD-004A", "SD Advanced Sales Sess A", "fit_to_standard","completed",  "SD", 1, "usr-002", 1, 2, ["L3-3OC","L3-4OC"]),
    ("WS-SD-004B", "SD Advanced Sales Sess B", "fit_to_standard","completed",  "SD", 1, "usr-002", 2, 2, ["L3-3OC","L3-4OC"]),
    ("WS-MM-001",  "MM Procurement F2S",      "fit_to_standard", "completed",  "MM", 1, "usr-003", 1, 1, ["L3-1MM","L3-2MM"]),
    ("WS-MM-002",  "MM Contracts F2S",        "fit_to_standard", "completed",  "MM", 1, "usr-003", 1, 1, ["L3-4MM","L3-5MM"]),
    ("WS-MM-003",  "MM Invoice Verification", "fit_to_standard", "in_progress","MM", 2, "usr-003", 1, 1, ["L3-1IV","L3-2IV","L3-3IV"]),
    ("WS-FI-001",  "FI General Ledger F2S",   "fit_to_standard", "completed",  "FI", 1, "usr-004", 1, 1, ["L3-1GL","L3-2GL","L3-3GL"]),
    ("WS-FI-002",  "FI AP F2S",              "fit_to_standard", "scheduled",  "FI", 2, "usr-004", 1, 1, ["L3-1AP","L3-2AP"]),
    ("WS-FI-003",  "FI Period-End Deep Dive", "deep_dive",       "draft",      "FI", 2, "usr-004", 1, 1, ["L3-4GL","L3-5GL"]),
    ("WS-PP-001",  "PP Planning F2S",         "fit_to_standard", "completed",  "PP", 2, "usr-005", 1, 1, ["L3-1PL","L3-2PL"]),
    ("WS-PP-002",  "PP Execution F2S",        "fit_to_standard", "scheduled",  "PP", 2, "usr-005", 1, 1, ["L3-1EX","L3-2EX","L3-3EX"]),
    ("WS-PP-003",  "PP Advanced Planning",    "deep_dive",       "draft",      "PP", 2, "usr-005", 1, 1, ["L3-3PL","L3-4PL","L3-5PL"]),
    ("WS-HR-001",  "HR PA F2S",              "fit_to_standard", "completed",  "HR", 3, "usr-007", 1, 1, ["L3-1PA","L3-2PA"]),
    ("WS-HR-002",  "HR Time Mgmt F2S",       "fit_to_standard", "in_progress","HR", 3, "usr-007", 1, 1, ["L3-1TM","L3-2TM"]),
    ("WS-HR-003",  "HR Payroll Deep Dive",    "deep_dive",       "draft",      "HR", 3, "usr-007", 1, 1, ["L3-5PA"]),
    ("WS-SD-005",  "SD Free-of-Charge F2S",   "fit_to_standard", "scheduled",  "SD", 1, "usr-002", 1, 1, ["L3-5OC"]),
    ("WS-MM-004",  "MM Source & Eval F2S",    "fit_to_standard", "draft",      "MM", 1, "usr-003", 1, 1, ["L3-3MM"]),
    ("WS-FI-004",  "FI Withholding Tax DD",   "deep_dive",       "draft",      "FI", 2, "usr-004", 1, 1, ["L3-5AP"]),
]

WORKSHOPS = []
WORKSHOP_SCOPE_ITEMS = []
WORKSHOP_ATTENDEES = []
WORKSHOP_AGENDA_ITEMS = []

for idx, (code, name, wtype, wstatus, area, wave, fac, sess, tsess, l3s) in enumerate(_WS_DEFS):
    ws_id = _id(code)
    ws_date = _BASE + timedelta(days=idx * 3)

    WORKSHOPS.append({
        "id": ws_id, "project_id": 1, "code": code, "name": name,
        "type": wtype, "status": wstatus,
        "date": ws_date.date().isoformat(),
        "start_time": "09:00", "end_time": "17:00",
        "facilitator_id": fac,
        "process_area": area, "wave": wave,
        "session_number": sess, "total_sessions": tsess,
        "notes": f"Workshop {code} — {name}",
        "started_at": ws_date.isoformat() if wstatus in ("completed", "in_progress") else None,
        "completed_at": (ws_date + timedelta(hours=8)).isoformat() if wstatus == "completed" else None,
    })

    # scope items
    for si, l3_code in enumerate(l3s):
        WORKSHOP_SCOPE_ITEMS.append({
            "id": _id(f"wsi-{code}-{l3_code}"),
            "workshop_id": ws_id,
            "process_level_id": _L3_IDS[l3_code],
            "sort_order": si + 1,
        })

    # attendees (facilitator + 2 fixed per workshop)
    WORKSHOP_ATTENDEES.append({
        "id": _id(f"att-{code}-fac"),
        "workshop_id": ws_id, "user_id": fac,
        "name": f"Facilitator ({fac})", "role": "Facilitator",
        "organization": "consultant",
        "attendance_status": "confirmed" if wstatus != "draft" else "invited",
        "is_required": True,
    })
    WORKSHOP_ATTENDEES.append({
        "id": _id(f"att-{code}-bpo"),
        "workshop_id": ws_id, "user_id": "usr-010",
        "name": "Emre Aydın", "role": "Business Process Owner",
        "organization": "customer",
        "attendance_status": "confirmed" if wstatus != "draft" else "invited",
        "is_required": True,
    })
    WORKSHOP_ATTENDEES.append({
        "id": _id(f"att-{code}-tech"),
        "workshop_id": ws_id, "user_id": "usr-008",
        "name": "Can Özdemir", "role": "Technical Advisor",
        "organization": "consultant",
        "attendance_status": "tentative",
        "is_required": False,
    })

    # agenda items (standard 4-item template)
    for a_idx, (a_title, a_dur, a_type) in enumerate([
        ("Opening & Scope Review",    15, "session"),
        ("Process Walkthrough",       120, "demo"),
        ("Break",                     15, "break"),
        ("Gap Discussion & Wrap-up",  90, "discussion"),
    ], 1):
        WORKSHOP_AGENDA_ITEMS.append({
            "id": _id(f"agi-{code}-{a_idx}"),
            "workshop_id": ws_id, "title": a_title,
            "duration_minutes": a_dur, "type": a_type,
            "sort_order": a_idx,
        })

# ═════════════════════════════════════════════════════════════════════════
# 3. PROCESS STEPS  (100 — for completed & in_progress workshops)
# ═════════════════════════════════════════════════════════════════════════

PROCESS_STEPS = []
_step_seq = 0

# Build set of L4 ids under each L3
_L4_BY_L3 = {}
for pl in PROCESS_LEVELS:
    if pl["level"] == 4:
        _L4_BY_L3.setdefault(pl["parent_id"], []).append(pl)

_FIT_CYCLE = ["fit", "fit", "gap", "partial_fit"]  # 50% fit, 25% gap, 25% partial

for ws in WORKSHOPS:
    if ws["status"] not in ("completed", "in_progress"):
        continue
    # get L3s scoped to this workshop
    ws_l3_ids = [si["process_level_id"] for si in WORKSHOP_SCOPE_ITEMS
                 if si["workshop_id"] == ws["id"]]
    for l3_id in ws_l3_ids:
        l4s = _L4_BY_L3.get(l3_id, [])
        for s_idx, l4 in enumerate(l4s):
            _step_seq += 1
            is_assessed = ws["status"] == "completed"
            fit = _FIT_CYCLE[_step_seq % 4] if is_assessed else None
            PROCESS_STEPS.append({
                "id": _id(f"step-{_step_seq}"),
                "workshop_id": ws["id"],
                "process_level_id": l4["id"],
                "sort_order": s_idx + 1,
                "fit_decision": fit,
                "notes": f"Step {_step_seq}: assessed in {ws['code']}" if is_assessed else None,
                "demo_shown": is_assessed,
                "bpmn_reviewed": is_assessed and _step_seq % 3 == 0,
                "assessed_by": ws["facilitator_id"] if is_assessed else None,
            })

# ═════════════════════════════════════════════════════════════════════════
# 4. DECISIONS  (50 — from completed workshops)
# ═════════════════════════════════════════════════════════════════════════

DECISIONS = []
_dec_seq = 0
_CATEGORIES = ["process", "technical", "scope", "organizational", "data"]

_completed_steps = [s for s in PROCESS_STEPS if s["fit_decision"] is not None]
for i, step in enumerate(_completed_steps):
    if i % 2 == 0:  # ~50 decisions from ~100 assessed steps
        _dec_seq += 1
        ws = next(w for w in WORKSHOPS if w["id"] == step["workshop_id"])
        DECISIONS.append({
            "id": _id(f"dec-{_dec_seq}"),
            "project_id": 1,
            "process_step_id": step["id"],
            "code": f"DEC-{_dec_seq:03d}",
            "text": f"Decision {_dec_seq}: {'Use standard' if step['fit_decision'] == 'fit' else 'Custom development required'} for step {step['sort_order']}",
            "decided_by": "Workshop Team",
            "decided_by_user_id": ws["facilitator_id"],
            "category": _CATEGORIES[_dec_seq % 5],
            "status": "active",
            "rationale": f"Based on fit analysis in {ws['code']}",
        })

# ═════════════════════════════════════════════════════════════════════════
# 5. OPEN ITEMS  (30 — mix of statuses)
# ═════════════════════════════════════════════════════════════════════════

OPEN_ITEMS = []
_oi_seq = 0
_OI_STATUSES = ["open", "open", "in_progress", "in_progress", "blocked", "closed"]
_OI_PRIORITIES = ["P1", "P2", "P2", "P3", "P3", "P4"]
_OI_CATEGORIES = [
    "configuration", "development", "data_migration",
    "integration", "authorization", "testing",
]

_gap_steps = [s for s in PROCESS_STEPS
              if s["fit_decision"] in ("gap", "partial_fit")]
for i, step in enumerate(_gap_steps):
    if _oi_seq >= 30:
        break
    _oi_seq += 1
    ws = next(w for w in WORKSHOPS if w["id"] == step["workshop_id"])
    oi_status = _OI_STATUSES[_oi_seq % 6]
    OPEN_ITEMS.append({
        "id": _id(f"oi-{_oi_seq}"),
        "project_id": 1,
        "process_step_id": step["id"],
        "workshop_id": ws["id"],
        "process_level_id": step["process_level_id"],
        "code": f"OI-{_oi_seq:03d}",
        "title": f"Open Item {_oi_seq}: Clarify gap for step in {ws['code']}",
        "description": f"Needs further analysis from {ws['name']}",
        "status": oi_status,
        "priority": _OI_PRIORITIES[_oi_seq % 6],
        "category": _OI_CATEGORIES[_oi_seq % 6],
        "assignee_id": f"usr-{((_oi_seq % 5) + 2):03d}",
        "assignee_name": ["Burak Şahin", "Elif Demir", "Ahmet Yıldız",
                          "Zeynep Arslan", "Hakan Çelik"][_oi_seq % 5],
        "created_by_id": ws["facilitator_id"],
        "due_date": (_BASE + timedelta(days=14 + _oi_seq * 2)).date().isoformat(),
        "resolved_date": (_BASE + timedelta(days=10 + _oi_seq)).date().isoformat() if oi_status == "closed" else None,
        "resolution": f"Resolved via configuration change" if oi_status == "closed" else None,
        "process_area": ws["process_area"],
        "wave": ws["wave"],
    })

# ═════════════════════════════════════════════════════════════════════════
# 6. REQUIREMENTS  (40 — lifecycle mix)
# ═════════════════════════════════════════════════════════════════════════

REQUIREMENTS = []
_req_seq = 0
_REQ_STATUSES = [
    "draft", "draft", "under_review", "approved", "approved",
    "in_backlog", "realized", "verified", "deferred", "rejected",
]
_REQ_TYPES = [
    "functional", "functional", "technical", "data_migration",
    "integration", "authorization",
]
_REQ_PRIORITIES = ["P1", "P2", "P2", "P3"]

for i, step in enumerate(_gap_steps):
    if _req_seq >= 40:
        break
    _req_seq += 1
    ws = next(w for w in WORKSHOPS if w["id"] == step["workshop_id"])
    req_status = _REQ_STATUSES[_req_seq % 10]
    REQUIREMENTS.append({
        "id": _id(f"req-{_req_seq}"),
        "project_id": 1,
        "process_step_id": step["id"],
        "workshop_id": ws["id"],
        "process_level_id": step["process_level_id"],
        "scope_item_id": None,  # linked at L4 level
        "code": f"REQ-{_req_seq:03d}",
        "title": f"Requirement {_req_seq}: Custom logic for gap in {ws['code']}",
        "description": f"Develop custom solution for gap identified in {ws['name']}, step {step['sort_order']}",
        "priority": _REQ_PRIORITIES[_req_seq % 4],
        "type": _REQ_TYPES[_req_seq % 6],
        "fit_status": step["fit_decision"],
        "status": req_status,
        "effort_hours": 8 * ((_req_seq % 5) + 1),
        "effort_story_points": (_req_seq % 5) + 1,
        "complexity": ["low", "medium", "medium", "high", "very_high"][_req_seq % 5],
        "created_by_id": ws["facilitator_id"],
        "created_by_name": "Workshop Team",
        "approved_by_id": "usr-001" if req_status in ("approved", "in_backlog", "realized", "verified") else None,
        "approved_by_name": "Mehmet Kaya" if req_status in ("approved", "in_backlog", "realized", "verified") else None,
        "process_area": ws["process_area"],
        "wave": ws["wave"],
        "alm_synced": req_status in ("in_backlog", "realized", "verified"),
        "alm_sync_status": "synced" if req_status in ("in_backlog", "realized", "verified") else None,
        "deferred_to_phase": "Phase 2" if req_status == "deferred" else None,
        "rejection_reason": "Out of scope for current release" if req_status == "rejected" else None,
    })

# ═════════════════════════════════════════════════════════════════════════
# 7. REQUIREMENT ↔ OPEN ITEM LINKS  (15 blocking links)
# ═════════════════════════════════════════════════════════════════════════

REQUIREMENT_OI_LINKS = []
_link_seq = 0
for i, req in enumerate(REQUIREMENTS[:15]):
    if i < len(OPEN_ITEMS):
        _link_seq += 1
        REQUIREMENT_OI_LINKS.append({
            "id": _id(f"roil-{_link_seq}"),
            "requirement_id": req["id"],
            "open_item_id": OPEN_ITEMS[i]["id"],
            "link_type": "blocks" if i % 3 == 0 else "related",
        })

# ═════════════════════════════════════════════════════════════════════════
# 8. REQUIREMENT DEPENDENCIES  (10 cross-dependencies)
# ═════════════════════════════════════════════════════════════════════════

REQUIREMENT_DEPENDENCIES = []
for i in range(10):
    if i + 10 < len(REQUIREMENTS):
        REQUIREMENT_DEPENDENCIES.append({
            "id": _id(f"rdep-{i+1}"),
            "requirement_id": REQUIREMENTS[i]["id"],
            "depends_on_id": REQUIREMENTS[i + 10]["id"],
            "dependency_type": "blocks" if i % 3 == 0 else "related",
        })

# ═════════════════════════════════════════════════════════════════════════
# 9. OPEN ITEM COMMENTS  (20 activity entries)
# ═════════════════════════════════════════════════════════════════════════

OPEN_ITEM_COMMENTS = []
_cmt_types = ["comment", "status_change", "reassignment", "comment"]
for i, oi in enumerate(OPEN_ITEMS[:20]):
    OPEN_ITEM_COMMENTS.append({
        "id": _id(f"oic-{i+1}"),
        "open_item_id": oi["id"],
        "user_id": oi["assignee_id"],
        "type": _cmt_types[i % 4],
        "content": f"Update on {oi['code']}: {'Investigating options' if i % 2 == 0 else 'Progress being made'}",
    })

# ═════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════════════════
SEED_SUMMARY = {
    "process_levels": len(PROCESS_LEVELS),
    "  L1": len([p for p in PROCESS_LEVELS if p["level"] == 1]),
    "  L2": len([p for p in PROCESS_LEVELS if p["level"] == 2]),
    "  L3": len([p for p in PROCESS_LEVELS if p["level"] == 3]),
    "  L4": len([p for p in PROCESS_LEVELS if p["level"] == 4]),
    "workshops": len(WORKSHOPS),
    "workshop_scope_items": len(WORKSHOP_SCOPE_ITEMS),
    "workshop_attendees": len(WORKSHOP_ATTENDEES),
    "workshop_agenda_items": len(WORKSHOP_AGENDA_ITEMS),
    "process_steps": len(PROCESS_STEPS),
    "decisions": len(DECISIONS),
    "open_items": len(OPEN_ITEMS),
    "requirements": len(REQUIREMENTS),
    "req_oi_links": len(REQUIREMENT_OI_LINKS),
    "req_dependencies": len(REQUIREMENT_DEPENDENCIES),
    "oi_comments": len(OPEN_ITEM_COMMENTS),
}

if __name__ == "__main__":
    for k, v in SEED_SUMMARY.items():
        print(f"  {k}: {v}")
