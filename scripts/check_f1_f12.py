"""Health check script for F1-F12 Test Management features."""
import re
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FEATURE_MAP = {
    "F1  UI/UX Components": {
        "files": [
            "static/js/components/tm_data_grid.js",
            "static/js/components/tm_tree_panel.js",
            "static/js/components/tm_split_pane.js",
            "static/js/components/tm_toolbar.js",
            "static/css/testing.css",
        ],
        "type": "frontend_files",
    },
    "F2  Versioning": {
        "blueprint": "app/blueprints/testing_bp.py",
        "keywords": ["version", "diff"],
        "model": "app/models/testing.py",
        "model_class": "TestCaseVersion",
        "view": "static/js/views/test_case_detail.js",
    },
    "F3  Approval Workflow": {
        "blueprint": "app/blueprints/approval_bp.py",
        "keywords": ["approval", "workflow"],
        "model": "app/models/testing.py",
        "model_class": "ApprovalWorkflow",
        "view": "static/js/views/approvals.js",
    },
    "F4  AI Pipeline": {
        "blueprint": "app/blueprints/ai_bp.py",
        "keywords": ["insight", "smart", "flaky", "coverage"],
        "model": "app/models/ai.py",
        "model_class": "AIAuditLog",
        "view": "static/js/views/ai_insights.js",
    },
    "F5  Reporting & Dashboard": {
        "blueprint": "app/blueprints/reporting_bp.py",
        "keywords": ["report", "dashboard"],
        "model": "app/models/reporting.py",
        "model_class": "Report",
        "view": "static/js/views/reports.js",
    },
    "F6  Folders/Envs/Bulk": {
        "blueprint": "app/blueprints/folders_env_bp.py",
        "keywords": ["folder", "bulk", "environment", "matrix"],
        "model": "app/models/testing_ext.py",
        "model_class": "TestSuiteFolder",
        "view": "static/js/views/suite_folders.js",
    },
    "F7  BDD / Parametric": {
        "blueprint": "app/blueprints/bdd_parametric_bp.py",
        "keywords": ["bdd", "gherkin", "parameter", "data"],
        "model": "app/models/bdd_parametric.py",
        "model_class": "TestCaseBDD",
        "view": "static/js/views/bdd_editor.js",
    },
    "F8  Exploratory/Evidence": {
        "blueprint": "app/blueprints/exploratory_evidence_bp.py",
        "keywords": ["exploratory", "evidence", "session"],
        "model": "app/models/exploratory_evidence.py",
        "model_class": "ExploratorySession",
        "view": "static/js/views/exploratory.js",
    },
    "F9  Custom Fields": {
        "blueprint": "app/blueprints/custom_fields_bp.py",
        "keywords": ["custom", "field", "layout"],
        "model": "app/models/custom_fields.py",
        "model_class": "CustomFieldDefinition",
        "view": "static/js/views/custom_fields.js",
    },
    "F10 Integrations": {
        "blueprint": "app/blueprints/integrations_bp.py",
        "keywords": ["jira", "webhook", "automation", "openapi"],
        "model": "app/models/integrations.py",
        "model_class": "JiraIntegration",
        "view": "static/js/views/integrations.js",
    },
    "F11 Observability": {
        "blueprint": "app/blueprints/observability_bp.py",
        "keywords": ["health", "metric", "task", "cache"],
        "model": "app/models/observability.py",
        "model_class": "AsyncTask",
        "view": "static/js/views/observability.js",
    },
    "F12 Gate Criteria": {
        "blueprint": "app/blueprints/gate_criteria_bp.py",
        "keywords": ["gate", "criteria", "scorecard", "go_no_go"],
        "model": "app/models/gate_criteria.py",
        "model_class": "GateCriterion",
        "view": "static/js/views/gate_criteria.js",
    },
}

issues = []

for feature, info in FEATURE_MAP.items():
    print(f"\n{'='*60}\n{feature}")

    # Frontend files check
    if info.get("type") == "frontend_files":
        for fpath in info.get("files", []):
            full = os.path.join(BASE, fpath)
            exists = os.path.exists(full)
            size = os.path.getsize(full) if exists else 0
            status = f"✅ {size//1024}KB" if exists else "❌ MISSING"
            print(f"  FE: {fpath.split('/')[-1]:40s} {status}")
            if not exists:
                issues.append(f"{feature}: FE file missing {fpath}")
        continue

    # Blueprint check
    bp = info.get("blueprint")
    if bp:
        full_bp = os.path.join(BASE, bp)
        if os.path.exists(full_bp):
            with open(full_bp) as f:
                content = f.read()
            routes = len(re.findall(r"@\w+\.route\(", content))
            kw_hits = sum(1 for kw in info.get("keywords", []) if kw in content.lower())
            print(f"  BE blueprint: {bp.split('/')[-1]:40s} ✅ {routes} routes, {kw_hits}/{len(info.get('keywords', []))} keywords")
        else:
            print(f"  BE blueprint: {bp.split('/')[-1]:40s} ❌ MISSING")
            issues.append(f"{feature}: Blueprint missing {bp}")

    # Model check
    model_file = info.get("model")
    model_class = info.get("model_class")
    if model_file and model_class:
        full_model = os.path.join(BASE, model_file)
        if os.path.exists(full_model):
            with open(full_model) as f:
                model_content = f.read()
            if f"class {model_class}" in model_content:
                print(f"  BE model:     {model_class:40s} ✅")
            else:
                print(f"  BE model:     {model_class:40s} ❌ CLASS NOT FOUND in {model_file}")
                issues.append(f"{feature}: Model class {model_class} not in {model_file}")
        else:
            print(f"  BE model:     {model_file.split('/')[-1]:40s} ❌ FILE MISSING")
            issues.append(f"{feature}: Model file missing {model_file}")

    # Frontend view check
    view = info.get("view")
    if view:
        full_view = os.path.join(BASE, view)
        if os.path.exists(full_view):
            size = os.path.getsize(full_view)
            print(f"  FE view:      {view.split('/')[-1]:40s} ✅ {size//1024}KB")
        else:
            print(f"  FE view:      {view.split('/')[-1]:40s} ❌ MISSING")
            issues.append(f"{feature}: View missing {view}")

print(f"\n{'='*60}")
print(f"SUMMARY: {len(issues)} issues found")
if issues:
    for i in issues:
        print(f"  ⚠️  {i}")
else:
    print("  All files present! ✅")
