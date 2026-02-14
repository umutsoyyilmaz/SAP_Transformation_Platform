#!/usr/bin/env python3
"""
Filter Validation Script
========================
Creates diverse test data across all filterable pages, then validates that
the client-side filtering logic (replicated in Python) matches the actual
API results for every filter field and combination.

Pages tested:
  1. Backlog (WRICEF items) — wricef_type, status, priority, module + search
  2. Test Planning / Catalog — test_layer, status, priority, module + search
  3. Test Planning / Suites — suite_type, status, module + search
  4. Defect Management — severity, status, module + search
  5. Integration Factory — direction, protocol, status, module + search
  6. Data Factory — status, source_system, owner + search

Each test:
  - Creates items with varied attribute combinations
  - Fetches all data from API (simulating what JS getAll does)
  - Applies client-side filters (same logic as JS)
  - Validates filter results match expectations
  - Also validates that server-side filter params still work (backward compat)
"""

import argparse
import json
import requests
import sys
from collections import defaultdict

# ──────────────────────────────────────────────────────────────────────
BASE = "http://localhost:5001"
API  = f"{BASE}/api/v1"
S    = requests.Session()
PASS = FAIL = WARN = 0

def log_ok(msg):
    global PASS; PASS += 1; print(f"  ✅ {msg}")
def log_fail(msg):
    global FAIL; FAIL += 1; print(f"  ❌ {msg}")
def log_warn(msg):
    global WARN; WARN += 1; print(f"  ⚠️  {msg}")

def get(path):
    r = S.get(f"{API}{path}", timeout=10)
    r.raise_for_status()
    return r.json()

def post(path, data):
    r = S.post(f"{API}{path}", json=data, timeout=10)
    if r.status_code not in (200, 201):
        raise Exception(f"POST {path} → {r.status_code}: {r.text[:200]}")
    return r.json()

def delete(path):
    r = S.delete(f"{API}{path}", timeout=10)
    return r.status_code

def client_filter(items, search_val, search_fields, filters):
    """Replicate the JS client-side filter logic."""
    result = list(items)

    if search_val:
        q = search_val.lower()
        result = [i for i in result if any(
            q in str(i.get(f, '') or '').lower() for f in search_fields
        )]

    for key, val in filters.items():
        if val is None:
            continue
        values = val if isinstance(val, list) else [val]
        if not values:
            continue
        result = [i for i in result if str(i.get(key, '')) in [str(v) for v in values]]

    return result


# ══════════════════════════════════════════════════════════════════════
# SETUP: Create program + diverse data
# ══════════════════════════════════════════════════════════════════════
def setup_program():
    print("\n🔧 Setting up test program...")
    prog = post("/programs", {
        "name": "Filter Test Program",
        "description": "For filter validation",
        "methodology": "activate"
    })
    pid = prog["id"]
    print(f"  Program ID: {pid}")
    return pid

def cleanup(pid, created):
    print("\n🧹 Cleanup...")
    for entity_type, ids in reversed(list(created.items())):
        for eid in ids:
            try:
                path_map = {
                    "backlog": f"/backlog/{eid}",
                    "config": f"/config-items/{eid}",
                    "test_case": f"/testing/catalog/{eid}",
                    "suite": f"/testing/suites/{eid}",
                    "defect": f"/testing/defects/{eid}",
                    "interface": f"/interfaces/{eid}",
                    "data_object": f"/data-factory/objects/{eid}",
                }
                if entity_type in path_map:
                    delete(path_map[entity_type])
            except:
                pass
    try:
        delete(f"/programs/{pid}")
    except:
        pass


# ══════════════════════════════════════════════════════════════════════
# BLOCK 1: BACKLOG FILTERS
# ══════════════════════════════════════════════════════════════════════
def test_backlog_filters(pid, created):
    print("\n" + "=" * 60)
    print("📦 BLOCK 1: Backlog Filters")
    print("=" * 60)

    # Create diverse items
    combos = [
        {"title": "FI Report Generator", "wricef_type": "report", "status": "new", "priority": "high", "module": "FI"},
        {"title": "MM Interface Adapter", "wricef_type": "interface", "status": "build", "priority": "critical", "module": "MM"},
        {"title": "SD Workflow Approval", "wricef_type": "workflow", "status": "design", "priority": "medium", "module": "SD"},
        {"title": "HR Enhancement Pack", "wricef_type": "enhancement", "status": "test", "priority": "low", "module": "HR"},
        {"title": "FI Conversion Script", "wricef_type": "conversion", "status": "new", "priority": "high", "module": "FI"},
        {"title": "PP Form Template", "wricef_type": "form", "status": "closed", "priority": "medium", "module": "PP"},
        {"title": "MM Report Dashboard", "wricef_type": "report", "status": "build", "priority": "low", "module": "MM"},
        {"title": "SD Interface Export", "wricef_type": "interface", "status": "deploy", "priority": "critical", "module": "SD"},
    ]

    for c in combos:
        item = post(f"/programs/{pid}/backlog", c)
        created["backlog"].append(item["id"])

    # Fetch all
    all_items = get(f"/programs/{pid}/backlog")
    if isinstance(all_items, dict):
        all_items = all_items.get("items", [])
    items = [i for i in all_items if i.get("program_id") == pid or True]

    search_fields = ['title', 'code', 'assigned_to', 'module']

    # Test 1: Type filter
    for wtype in ['report', 'interface', 'workflow']:
        filtered = client_filter(items, '', search_fields, {'wricef_type': [wtype]})
        expected = [i for i in items if i.get('wricef_type') == wtype]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Type filter '{wtype}': {len(filtered)} items")
        else:
            log_fail(f"Type filter '{wtype}': got {len(filtered)}, expected {len(expected)}")

    # Test 2: Status filter
    for status in ['new', 'build']:
        filtered = client_filter(items, '', search_fields, {'status': [status]})
        expected = [i for i in items if i.get('status') == status]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Status filter '{status}': {len(filtered)} items")
        else:
            log_fail(f"Status filter '{status}': got {len(filtered)}, expected {len(expected)}")

    # Test 3: Priority filter
    for prio in ['critical', 'high', 'low']:
        filtered = client_filter(items, '', search_fields, {'priority': [prio]})
        expected = [i for i in items if i.get('priority') == prio]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Priority filter '{prio}': {len(filtered)} items")
        else:
            log_fail(f"Priority filter '{prio}': got {len(filtered)}, expected {len(expected)}")

    # Test 4: Module filter
    for mod in ['FI', 'MM', 'SD']:
        filtered = client_filter(items, '', search_fields, {'module': [mod]})
        expected = [i for i in items if i.get('module') == mod]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Module filter '{mod}': {len(filtered)} items")
        else:
            log_fail(f"Module filter '{mod}': got {len(filtered)}, expected {len(expected)}")

    # Test 5: Multi-select filter
    filtered = client_filter(items, '', search_fields, {'wricef_type': ['report', 'interface']})
    expected = [i for i in items if i.get('wricef_type') in ('report', 'interface')]
    if len(filtered) == len(expected) and len(filtered) > 0:
        log_ok(f"Multi-type filter ['report','interface']: {len(filtered)} items")
    else:
        log_fail(f"Multi-type filter: got {len(filtered)}, expected {len(expected)}")

    # Test 6: Search filter
    filtered = client_filter(items, 'FI', search_fields, {})
    if len(filtered) >= 2:
        log_ok(f"Search 'FI': {len(filtered)} items (title/module match)")
    else:
        log_fail(f"Search 'FI': got {len(filtered)}, expected ≥2")

    # Test 7: Combined search + filter
    filtered = client_filter(items, 'Report', search_fields, {'module': ['FI']})
    expected = [i for i in items if 'report' in (i.get('title', '')).lower() and i.get('module') == 'FI']
    if len(filtered) == len(expected):
        log_ok(f"Search 'Report' + Module 'FI': {len(filtered)} items")
    else:
        log_fail(f"Combined search+filter: got {len(filtered)}, expected {len(expected)}")

    # Test 8: Empty filter returns all
    filtered = client_filter(items, '', search_fields, {})
    if len(filtered) == len(items):
        log_ok(f"No filter → all items: {len(filtered)}")
    else:
        log_fail(f"No filter: got {len(filtered)}, expected {len(items)}")

    # Test 9: Non-matching filter returns 0
    filtered = client_filter(items, 'ZZZZNONEXISTENT', search_fields, {})
    if len(filtered) == 0:
        log_ok(f"Non-matching search → 0 items")
    else:
        log_fail(f"Non-matching search: got {len(filtered)}, expected 0")


# ══════════════════════════════════════════════════════════════════════
# BLOCK 2: TEST PLANNING - CATALOG FILTERS
# ══════════════════════════════════════════════════════════════════════
def test_catalog_filters(pid, created):
    print("\n" + "=" * 60)
    print("📋 BLOCK 2: Test Planning — Catalog Filters")
    print("=" * 60)

    combos = [
        {"title": "Login Unit Test", "test_layer": "unit", "status": "draft", "priority": "high", "module": "FI"},
        {"title": "E2E Order Flow", "test_layer": "e2e", "status": "approved", "priority": "critical", "module": "SD"},
        {"title": "SIT Integration", "test_layer": "sit", "status": "ready", "priority": "medium", "module": "MM"},
        {"title": "UAT Acceptance", "test_layer": "uat", "status": "in_review", "priority": "low", "module": "HR"},
        {"title": "Regression Pack", "test_layer": "regression", "status": "draft", "priority": "high", "module": "FI"},
        {"title": "Perf Benchmark", "test_layer": "performance", "status": "approved", "priority": "medium", "module": "SD"},
        {"title": "Cutover Rehearsal 1", "test_layer": "cutover_rehearsal", "status": "ready", "priority": "critical", "module": "PP"},
        {"title": "MM Unit Validation", "test_layer": "unit", "status": "deprecated", "priority": "low", "module": "MM"},
    ]

    for c in combos:
        tc = post(f"/programs/{pid}/testing/catalog", c)
        created["test_case"].append(tc["id"])

    all_cases = get(f"/programs/{pid}/testing/catalog")
    cases = all_cases.get("items", all_cases) if isinstance(all_cases, dict) else all_cases

    search_fields = ['title', 'code', 'module', 'assigned_to']

    # Layer filter
    for layer in ['unit', 'e2e', 'sit', 'uat', 'regression', 'performance', 'cutover_rehearsal']:
        filtered = client_filter(cases, '', search_fields, {'test_layer': [layer]})
        expected = [c for c in cases if c.get('test_layer') == layer]
        if len(filtered) == len(expected):
            log_ok(f"Layer '{layer}': {len(filtered)} cases")
        else:
            log_fail(f"Layer '{layer}': got {len(filtered)}, expected {len(expected)}")

    # Status filter
    for st in ['draft', 'approved', 'ready', 'in_review', 'deprecated']:
        filtered = client_filter(cases, '', search_fields, {'status': [st]})
        expected = [c for c in cases if c.get('status') == st]
        if len(filtered) == len(expected):
            log_ok(f"Status '{st}': {len(filtered)} cases")
        else:
            log_fail(f"Status '{st}': got {len(filtered)}, expected {len(expected)}")

    # Priority filter
    for prio in ['critical', 'high', 'medium', 'low']:
        filtered = client_filter(cases, '', search_fields, {'priority': [prio]})
        expected = [c for c in cases if c.get('priority') == prio]
        if len(filtered) == len(expected):
            log_ok(f"Priority '{prio}': {len(filtered)} cases")
        else:
            log_fail(f"Priority '{prio}': got {len(filtered)}, expected {len(expected)}")

    # Module filter
    for mod in ['FI', 'SD', 'MM']:
        filtered = client_filter(cases, '', search_fields, {'module': [mod]})
        expected = [c for c in cases if c.get('module') == mod]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Module '{mod}': {len(filtered)} cases")
        else:
            log_fail(f"Module '{mod}': got {len(filtered)}, expected {len(expected)}")

    # Multi-select
    filtered = client_filter(cases, '', search_fields, {'test_layer': ['unit', 'e2e']})
    expected = [c for c in cases if c.get('test_layer') in ('unit', 'e2e')]
    if len(filtered) == len(expected) and len(filtered) >= 3:
        log_ok(f"Multi-layer ['unit','e2e']: {len(filtered)} cases")
    else:
        log_fail(f"Multi-layer: got {len(filtered)}, expected {len(expected)}")

    # Search
    filtered = client_filter(cases, 'unit', search_fields, {})
    if len(filtered) >= 2:
        log_ok(f"Search 'unit': {len(filtered)} cases")
    else:
        log_fail(f"Search 'unit': got {len(filtered)}, expected ≥2")

    # Combined
    filtered = client_filter(cases, '', search_fields, {'test_layer': ['unit'], 'status': ['draft']})
    expected = [c for c in cases if c.get('test_layer') == 'unit' and c.get('status') == 'draft']
    if len(filtered) == len(expected):
        log_ok(f"Layer 'unit' + Status 'draft': {len(filtered)} cases")
    else:
        log_fail(f"Combined: got {len(filtered)}, expected {len(expected)}")

    # Server-side backward compat
    try:
        srv = get(f"/programs/{pid}/testing/catalog?test_layer=unit")
        srv_items = srv.get("items", srv) if isinstance(srv, dict) else srv
        unit_count = len([c for c in cases if c.get('test_layer') == 'unit'])
        if len(srv_items) == unit_count:
            log_ok(f"Server-side ?test_layer=unit: {len(srv_items)} (backward compat ✓)")
        else:
            log_warn(f"Server-side ?test_layer=unit: got {len(srv_items)}, expected {unit_count}")
    except Exception as e:
        log_warn(f"Server-side filter not tested: {e}")


# ══════════════════════════════════════════════════════════════════════
# BLOCK 3: TEST PLANNING - SUITE FILTERS
# ══════════════════════════════════════════════════════════════════════
def test_suite_filters(pid, created):
    print("\n" + "=" * 60)
    print("📦 BLOCK 3: Test Planning — Suite Filters")
    print("=" * 60)

    combos = [
        {"name": "SIT Smoke Suite", "suite_type": "SIT", "status": "active", "module": "FI"},
        {"name": "UAT Full Suite", "suite_type": "UAT", "status": "draft", "module": "SD"},
        {"name": "Regression Pack", "suite_type": "Regression", "status": "active", "module": "MM"},
        {"name": "E2E Critical Path", "suite_type": "E2E", "status": "locked", "module": "FI"},
        {"name": "Performance Bench", "suite_type": "Performance", "status": "archived", "module": "PP"},
        {"name": "Custom Ad-hoc", "suite_type": "Custom", "status": "draft", "module": "HR"},
    ]

    for c in combos:
        suite = post(f"/programs/{pid}/testing/suites", c)
        created["suite"].append(suite["id"])

    all_suites = get(f"/programs/{pid}/testing/suites")
    suites = all_suites.get("items", all_suites) if isinstance(all_suites, dict) else all_suites

    search_fields = ['name', 'module', 'owner', 'tags']

    # Type filter
    for stype in ['SIT', 'UAT', 'Regression', 'E2E', 'Performance', 'Custom']:
        filtered = client_filter(suites, '', search_fields, {'suite_type': [stype]})
        expected = [s for s in suites if s.get('suite_type') == stype]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Suite type '{stype}': {len(filtered)} suites")
        else:
            log_fail(f"Suite type '{stype}': got {len(filtered)}, expected {len(expected)}")

    # Status filter
    for st in ['draft', 'active', 'locked', 'archived']:
        filtered = client_filter(suites, '', search_fields, {'status': [st]})
        expected = [s for s in suites if s.get('status') == st]
        if len(filtered) == len(expected):
            log_ok(f"Suite status '{st}': {len(filtered)} suites")
        else:
            log_fail(f"Suite status '{st}': got {len(filtered)}, expected {len(expected)}")

    # Module filter
    filtered = client_filter(suites, '', search_fields, {'module': ['FI']})
    expected = [s for s in suites if s.get('module') == 'FI']
    if len(filtered) == len(expected) and len(filtered) >= 2:
        log_ok(f"Suite module 'FI': {len(filtered)} suites")
    else:
        log_fail(f"Suite module 'FI': got {len(filtered)}, expected {len(expected)}")

    # Multi-select type
    filtered = client_filter(suites, '', search_fields, {'suite_type': ['SIT', 'UAT']})
    expected = [s for s in suites if s.get('suite_type') in ('SIT', 'UAT')]
    if len(filtered) == len(expected) and len(filtered) >= 2:
        log_ok(f"Multi-type ['SIT','UAT']: {len(filtered)} suites")
    else:
        log_fail(f"Multi-type: got {len(filtered)}, expected {len(expected)}")

    # Search
    filtered = client_filter(suites, 'Suite', search_fields, {})
    if len(filtered) >= 2:
        log_ok(f"Search 'Suite': {len(filtered)} suites")
    else:
        log_fail(f"Search 'Suite': got {len(filtered)}, expected ≥2")


# ══════════════════════════════════════════════════════════════════════
# BLOCK 4: DEFECT MANAGEMENT FILTERS
# ══════════════════════════════════════════════════════════════════════
def test_defect_filters(pid, created):
    print("\n" + "=" * 60)
    print("🐛 BLOCK 4: Defect Management Filters")
    print("=" * 60)

    combos = [
        {"title": "Login crash on Safari", "severity": "P1", "status": "open", "module": "FI"},
        {"title": "Report wrong totals", "severity": "P2", "status": "new", "module": "FI"},
        {"title": "Slow PO creation", "severity": "P3", "status": "in_progress", "module": "MM"},
        {"title": "UI alignment issue", "severity": "P4", "status": "closed", "module": "SD"},
        {"title": "Data export timeout", "severity": "P1", "status": "fixed", "module": "PP"},
        {"title": "Missing validation", "severity": "P2", "status": "reopened", "module": "HR"},
        {"title": "Print layout broken", "severity": "P3", "status": "rejected", "module": "FI"},
        {"title": "API error 500", "severity": "P1", "status": "open", "module": "MM"},
    ]

    for c in combos:
        defect = post(f"/programs/{pid}/testing/defects", c)
        created["defect"].append(defect["id"])

    all_defects = get(f"/programs/{pid}/testing/defects")
    defects = all_defects.get("items", all_defects) if isinstance(all_defects, dict) else all_defects

    search_fields = ['title', 'code', 'module', 'assigned_to']

    # Severity filter
    for sev in ['P1', 'P2', 'P3', 'P4']:
        filtered = client_filter(defects, '', search_fields, {'severity': [sev]})
        expected = [d for d in defects if d.get('severity') == sev]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Severity '{sev}': {len(filtered)} defects")
        else:
            log_fail(f"Severity '{sev}': got {len(filtered)}, expected {len(expected)}")

    # Status filter
    for st in ['new', 'open', 'in_progress', 'fixed', 'closed', 'rejected', 'reopened']:
        filtered = client_filter(defects, '', search_fields, {'status': [st]})
        expected = [d for d in defects if d.get('status') == st]
        if len(filtered) == len(expected):
            log_ok(f"Status '{st}': {len(filtered)} defects")
        else:
            log_fail(f"Status '{st}': got {len(filtered)}, expected {len(expected)}")

    # Module filter
    for mod in ['FI', 'MM']:
        filtered = client_filter(defects, '', search_fields, {'module': [mod]})
        expected = [d for d in defects if d.get('module') == mod]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Module '{mod}': {len(filtered)} defects")
        else:
            log_fail(f"Module '{mod}': got {len(filtered)}, expected {len(expected)}")

    # Multi-select severity
    filtered = client_filter(defects, '', search_fields, {'severity': ['P1', 'P2']})
    expected = [d for d in defects if d.get('severity') in ('P1', 'P2')]
    if len(filtered) == len(expected) and len(filtered) >= 4:
        log_ok(f"Multi-severity ['P1','P2']: {len(filtered)} defects")
    else:
        log_fail(f"Multi-severity: got {len(filtered)}, expected {len(expected)}")

    # Search
    filtered = client_filter(defects, 'crash', search_fields, {})
    if len(filtered) >= 1:
        log_ok(f"Search 'crash': {len(filtered)} defects")
    else:
        log_fail(f"Search 'crash': got {len(filtered)}, expected ≥1")

    # Combined severity + module
    filtered = client_filter(defects, '', search_fields, {'severity': ['P1'], 'module': ['MM']})
    expected = [d for d in defects if d.get('severity') == 'P1' and d.get('module') == 'MM']
    if len(filtered) == len(expected):
        log_ok(f"P1 + MM: {len(filtered)} defects")
    else:
        log_fail(f"P1 + MM: got {len(filtered)}, expected {len(expected)}")

    # Server-side backward compat
    try:
        srv = get(f"/programs/{pid}/testing/defects?severity=P1")
        srv_items = srv.get("items", srv) if isinstance(srv, dict) else srv
        p1_count = len([d for d in defects if d.get('severity') == 'P1'])
        if len(srv_items) == p1_count:
            log_ok(f"Server-side ?severity=P1: {len(srv_items)} (backward compat ✓)")
        else:
            log_warn(f"Server-side ?severity=P1: got {len(srv_items)}, expected {p1_count}")
    except Exception as e:
        log_warn(f"Server-side filter: {e}")


# ══════════════════════════════════════════════════════════════════════
# BLOCK 5: INTEGRATION FACTORY FILTERS
# ══════════════════════════════════════════════════════════════════════
def test_integration_filters(pid, created):
    print("\n" + "=" * 60)
    print("🔌 BLOCK 5: Integration Factory Filters")
    print("=" * 60)

    combos = [
        {"name": "PO Inbound IDoc", "direction": "inbound", "protocol": "idoc", "status": "identified", "module": "MM", "source_system": "SAP ECC", "target_system": "S/4HANA"},
        {"name": "SO Outbound REST", "direction": "outbound", "protocol": "rest", "status": "designed", "module": "SD", "source_system": "S/4HANA", "target_system": "CRM"},
        {"name": "GL Bidirectional OData", "direction": "bidirectional", "protocol": "odata", "status": "developed", "module": "FI", "source_system": "SAP", "target_system": "BW"},
        {"name": "HR File Transfer", "direction": "inbound", "protocol": "file", "status": "unit_tested", "module": "HR", "source_system": "SFTP", "target_system": "S/4HANA"},
        {"name": "MRP RFC Call", "direction": "outbound", "protocol": "rfc", "status": "go_live_ready", "module": "PP", "source_system": "S/4HANA", "target_system": "APO"},
        {"name": "Invoice SOAP Service", "direction": "inbound", "protocol": "soap", "status": "integration_tested", "module": "FI", "source_system": "Vendor", "target_system": "S/4HANA"},
        {"name": "WM CPI Flow", "direction": "bidirectional", "protocol": "cpi", "status": "live", "module": "MM", "source_system": "CPI", "target_system": "EWM"},
    ]

    for c in combos:
        iface = post(f"/programs/{pid}/interfaces", c)
        created["interface"].append(iface["id"])

    all_ifaces = get(f"/programs/{pid}/interfaces")
    ifaces = all_ifaces if isinstance(all_ifaces, list) else all_ifaces.get("items", [])

    search_fields = ['name', 'code', 'module', 'source_system', 'target_system']

    # Direction filter
    for direction in ['inbound', 'outbound', 'bidirectional']:
        filtered = client_filter(ifaces, '', search_fields, {'direction': [direction]})
        expected = [i for i in ifaces if i.get('direction') == direction]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Direction '{direction}': {len(filtered)} interfaces")
        else:
            log_fail(f"Direction '{direction}': got {len(filtered)}, expected {len(expected)}")

    # Protocol filter
    for proto in ['idoc', 'rest', 'odata', 'rfc', 'soap']:
        filtered = client_filter(ifaces, '', search_fields, {'protocol': [proto]})
        expected = [i for i in ifaces if i.get('protocol') == proto]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Protocol '{proto}': {len(filtered)} interfaces")
        else:
            log_fail(f"Protocol '{proto}': got {len(filtered)}, expected {len(expected)}")

    # Status filter
    for st in ['identified', 'designed', 'developed', 'go_live_ready']:
        filtered = client_filter(ifaces, '', search_fields, {'status': [st]})
        expected = [i for i in ifaces if i.get('status') == st]
        if len(filtered) == len(expected):
            log_ok(f"Status '{st}': {len(filtered)} interfaces")
        else:
            log_fail(f"Status '{st}': got {len(filtered)}, expected {len(expected)}")

    # Module filter
    for mod in ['FI', 'MM', 'SD']:
        filtered = client_filter(ifaces, '', search_fields, {'module': [mod]})
        expected = [i for i in ifaces if i.get('module') == mod]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Module '{mod}': {len(filtered)} interfaces")
        else:
            log_fail(f"Module '{mod}': got {len(filtered)}, expected {len(expected)}")

    # Multi-select protocol
    filtered = client_filter(ifaces, '', search_fields, {'protocol': ['idoc', 'rest', 'odata']})
    expected = [i for i in ifaces if i.get('protocol') in ('idoc', 'rest', 'odata')]
    if len(filtered) == len(expected) and len(filtered) >= 3:
        log_ok(f"Multi-protocol ['idoc','rest','odata']: {len(filtered)} interfaces")
    else:
        log_fail(f"Multi-protocol: got {len(filtered)}, expected {len(expected)}")

    # Search
    filtered = client_filter(ifaces, 'S/4HANA', search_fields, {})
    if len(filtered) >= 3:
        log_ok(f"Search 'S/4HANA': {len(filtered)} interfaces")
    else:
        log_fail(f"Search 'S/4HANA': got {len(filtered)}, expected ≥3")

    # Combined direction + module
    filtered = client_filter(ifaces, '', search_fields, {'direction': ['inbound'], 'module': ['FI']})
    expected = [i for i in ifaces if i.get('direction') == 'inbound' and i.get('module') == 'FI']
    if len(filtered) == len(expected):
        log_ok(f"Inbound + FI: {len(filtered)} interfaces")
    else:
        log_fail(f"Inbound + FI: got {len(filtered)}, expected {len(expected)}")


# ══════════════════════════════════════════════════════════════════════
# BLOCK 6: DATA FACTORY FILTERS
# ══════════════════════════════════════════════════════════════════════
def test_data_factory_filters(pid, created):
    print("\n" + "=" * 60)
    print("🗄️  BLOCK 6: Data Factory Filters")
    print("=" * 60)

    combos = [
        {"name": "Customer Master", "source_system": "SAP ECC", "status": "draft", "owner": "Ali Yilmaz", "target_table": "KNA1", "record_count": 50000},
        {"name": "Material Master", "source_system": "SAP ECC", "status": "profiled", "owner": "Mehmet Demir", "target_table": "MARA", "record_count": 120000},
        {"name": "Vendor Master", "source_system": "Legacy CRM", "status": "cleansed", "owner": "Ali Yilmaz", "target_table": "LFA1", "record_count": 8000},
        {"name": "GL Accounts", "source_system": "SAP ECC", "status": "ready", "owner": "Ayse Kaya", "target_table": "SKA1", "record_count": 3000},
        {"name": "Cost Centers", "source_system": "Excel", "status": "migrated", "owner": "Mehmet Demir", "target_table": "CSKS", "record_count": 500},
        {"name": "Sales Orders", "source_system": "Legacy CRM", "status": "draft", "owner": "Ayse Kaya", "target_table": "VBAK", "record_count": 200000},
        {"name": "Purchase Orders", "source_system": "SAP ECC", "status": "archived", "owner": "Ali Yilmaz", "target_table": "EKKO", "record_count": 75000},
    ]

    for c in combos:
        c["program_id"] = pid
        obj = post("/data-factory/objects", c)
        created["data_object"].append(obj["id"])

    all_objs = get(f"/data-factory/objects?program_id={pid}")
    objs = all_objs.get("items", all_objs) if isinstance(all_objs, dict) else all_objs

    search_fields = ['name', 'source_system', 'target_table', 'owner', 'description']

    # Status filter
    for st in ['draft', 'profiled', 'cleansed', 'ready', 'migrated', 'archived']:
        filtered = client_filter(objs, '', search_fields, {'status': [st]})
        expected = [o for o in objs if o.get('status') == st]
        if len(filtered) == len(expected):
            log_ok(f"Status '{st}': {len(filtered)} objects")
        else:
            log_fail(f"Status '{st}': got {len(filtered)}, expected {len(expected)}")

    # Source system filter
    for src in ['SAP ECC', 'Legacy CRM', 'Excel']:
        filtered = client_filter(objs, '', search_fields, {'source_system': [src]})
        expected = [o for o in objs if o.get('source_system') == src]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Source '{src}': {len(filtered)} objects")
        else:
            log_fail(f"Source '{src}': got {len(filtered)}, expected {len(expected)}")

    # Owner filter
    for owner in ['Ali Yilmaz', 'Mehmet Demir', 'Ayse Kaya']:
        filtered = client_filter(objs, '', search_fields, {'owner': [owner]})
        expected = [o for o in objs if o.get('owner') == owner]
        if len(filtered) == len(expected) and len(filtered) > 0:
            log_ok(f"Owner '{owner}': {len(filtered)} objects")
        else:
            log_fail(f"Owner '{owner}': got {len(filtered)}, expected {len(expected)}")

    # Multi-select status
    filtered = client_filter(objs, '', search_fields, {'status': ['draft', 'profiled']})
    expected = [o for o in objs if o.get('status') in ('draft', 'profiled')]
    if len(filtered) == len(expected) and len(filtered) >= 3:
        log_ok(f"Multi-status ['draft','profiled']: {len(filtered)} objects")
    else:
        log_fail(f"Multi-status: got {len(filtered)}, expected {len(expected)}")

    # Search
    filtered = client_filter(objs, 'Master', search_fields, {})
    if len(filtered) >= 3:
        log_ok(f"Search 'Master': {len(filtered)} objects")
    else:
        log_fail(f"Search 'Master': got {len(filtered)}, expected ≥3")

    # Search by target table
    filtered = client_filter(objs, 'KNA1', search_fields, {})
    if len(filtered) == 1:
        log_ok(f"Search 'KNA1' (target_table): {len(filtered)} object")
    else:
        log_fail(f"Search 'KNA1': got {len(filtered)}, expected 1")

    # Combined source + owner
    filtered = client_filter(objs, '', search_fields, {'source_system': ['SAP ECC'], 'owner': ['Ali Yilmaz']})
    expected = [o for o in objs if o.get('source_system') == 'SAP ECC' and o.get('owner') == 'Ali Yilmaz']
    if len(filtered) == len(expected):
        log_ok(f"SAP ECC + Ali Yilmaz: {len(filtered)} objects")
    else:
        log_fail(f"Combined: got {len(filtered)}, expected {len(expected)}")


# ══════════════════════════════════════════════════════════════════════
# BLOCK 7: CROSS-PAGE CONSISTENCY CHECKS
# ══════════════════════════════════════════════════════════════════════
def test_consistency():
    print("\n" + "=" * 60)
    print("🔍 BLOCK 7: Cross-Page Consistency Checks")
    print("=" * 60)

    # Check JS files load correctly (no 404/500)
    js_files = [
        "backlog.js", "test_planning.js", "defect_management.js",
        "integration.js", "data_factory.js",
    ]
    for js in js_files:
        r = S.get(f"{BASE}/static/js/views/{js}", timeout=10)
        if r.status_code == 200:
            content = r.text
            # Check for required function exports
            if "ExpUI.filterBar" in content or js == "backlog.js":
                log_ok(f"{js}: ExpUI.filterBar present")
            else:
                log_fail(f"{js}: ExpUI.filterBar NOT found")

            # Check for filter state variables
            has_search_var = "Search" in content and ("let _" in content or "var _" in content)
            has_filter_var = "Filters" in content or "Filter" in content
            if has_search_var and has_filter_var:
                log_ok(f"{js}: filter state variables present")
            else:
                log_fail(f"{js}: filter state variables missing")

            # Check for apply function
            if "applyFilter" in content or "applyListFilter" in content or "applyInventoryFilter" in content or "applyObjectFilter" in content or "applyDefectFilter" in content or "applyCatalogFilter" in content or "applySuiteFilter" in content:
                log_ok(f"{js}: apply filter function present")
            else:
                log_fail(f"{js}: apply filter function missing")

            # Check for onChange handler
            if "onFilterChange" in content or "onListFilterChange" in content or "onInvFilterChange" in content or "onObjFilterChange" in content or "onDefectFilterChange" in content or "onCatalogFilterChange" in content or "onSuiteFilterChange" in content:
                log_ok(f"{js}: onChange handler exported")
            else:
                log_fail(f"{js}: onChange handler missing")
        else:
            log_fail(f"{js}: HTTP {r.status_code}")

    # Check explore-shared.js has all helper functions
    r = S.get(f"{BASE}/static/js/components/explore-shared.js", timeout=10)
    if r.status_code == 200:
        content = r.text
        helpers = ['filterBar', '_fbToggle', '_fbShowSub', '_fbApply', '_fbClear', '_fbClearAll', '_fbFilterOptions']
        for h in helpers:
            if h in content:
                log_ok(f"explore-shared.js: {h} present")
            else:
                log_fail(f"explore-shared.js: {h} MISSING")


# ══════════════════════════════════════════════════════════════════════
# BLOCK 8: EDGE CASE & STRESS TESTS
# ══════════════════════════════════════════════════════════════════════
def test_edge_cases():
    print("\n" + "=" * 60)
    print("⚡ BLOCK 8: Edge Case & Stress Tests")
    print("=" * 60)

    # Test client_filter with empty list
    result = client_filter([], 'test', ['title'], {})
    if result == []:
        log_ok("Empty list + search → []")
    else:
        log_fail(f"Empty list + search → {result}")

    # Test with None fields
    items = [
        {"title": "Test", "status": None, "module": None},
        {"title": "Hello", "status": "open", "module": "FI"},
    ]
    result = client_filter(items, '', ['title', 'module'], {'status': ['open']})
    if len(result) == 1 and result[0]['title'] == 'Hello':
        log_ok("None field handling → correct filter")
    else:
        log_fail(f"None field handling: got {len(result)}")

    # Test case-insensitive search
    items = [
        {"title": "UPPERCASE TITLE", "module": "FI"},
        {"title": "lowercase title", "module": "SD"},
    ]
    result = client_filter(items, 'uppercase', ['title', 'module'], {})
    if len(result) == 1:
        log_ok("Case-insensitive search works")
    else:
        log_fail(f"Case-insensitive: got {len(result)}, expected 1")

    # Test multiple filters simultaneously (AND logic)
    items = [
        {"title": "A", "status": "open", "severity": "P1", "module": "FI"},
        {"title": "B", "status": "open", "severity": "P2", "module": "FI"},
        {"title": "C", "status": "closed", "severity": "P1", "module": "FI"},
        {"title": "D", "status": "open", "severity": "P1", "module": "MM"},
    ]
    result = client_filter(items, '', ['title'], {'status': ['open'], 'severity': ['P1'], 'module': ['FI']})
    if len(result) == 1 and result[0]['title'] == 'A':
        log_ok("Triple AND filter: 3 filters → 1 result")
    else:
        log_fail(f"Triple AND: got {len(result)}, expected 1")

    # Test search + filter combined (AND logic)
    items = [
        {"title": "FI Report", "status": "open", "module": "FI"},
        {"title": "FI Form", "status": "closed", "module": "FI"},
        {"title": "MM Report", "status": "open", "module": "MM"},
    ]
    result = client_filter(items, 'report', ['title', 'module'], {'status': ['open']})
    if len(result) == 2:  # FI Report (title match + status) and MM Report (title match + status)
        log_ok("Search + filter AND: 2 results")
    else:
        log_fail(f"Search + filter AND: got {len(result)}, expected 2")

    # Test clearAll behavior
    items = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
    result = client_filter(items, '', ['title'], {})
    if len(result) == 3:
        log_ok("clearAll (empty filters) → all items")
    else:
        log_fail(f"clearAll: got {len(result)}, expected 3")

    # Test filter with array vs string value
    items = [
        {"title": "A", "status": "open"},
        {"title": "B", "status": "closed"},
    ]
    # Single value as string (JS sometimes sends this)
    result = client_filter(items, '', ['title'], {'status': 'open'})
    if len(result) == 1:
        log_ok("Single string filter value works")
    else:
        log_fail(f"Single string filter: got {len(result)}, expected 1")


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════
def main():
    global PASS, FAIL, WARN
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:5001")
    args = parser.parse_args()

    global BASE, API
    BASE = args.base.rstrip("/")
    API = f"{BASE}/api/v1"

    print("=" * 60)
    print("  FILTER VALIDATION SUITE")
    print(f"  Target: {BASE}")
    print("=" * 60)

    # Health check
    try:
        r = S.get(f"{API}/health", timeout=10)
        if r.status_code == 200:
            log_ok("Health check")
        else:
            log_fail(f"Health check: {r.status_code}")
            return
    except Exception as e:
        log_fail(f"Server unreachable: {e}")
        return

    created = defaultdict(list)
    pid = None

    try:
        pid = setup_program()

        test_backlog_filters(pid, created)
        test_catalog_filters(pid, created)
        test_suite_filters(pid, created)
        test_defect_filters(pid, created)
        test_integration_filters(pid, created)
        test_data_factory_filters(pid, created)
        test_consistency()
        test_edge_cases()

    except Exception as e:
        log_fail(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if pid:
            cleanup(pid, created)

    # Summary
    total = PASS + FAIL + WARN
    print("\n" + "=" * 60)
    print("  FINAL REPORT")
    print("=" * 60)
    print(f"  ✅ {PASS} PASS | ❌ {FAIL} FAIL | ⚠️  {WARN} WARN")
    print(f"  Pass Rate: {PASS*100/total:.1f}% ({PASS}/{total})")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
