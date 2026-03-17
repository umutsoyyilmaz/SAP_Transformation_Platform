"""Sprint 8 UI closeout contract checks for core platform surfaces."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_JS = ROOT / "static/js/app.js"
MAKEFILE = ROOT / "Makefile"
RUNBOOK = ROOT / "docs/reviews/SPRINT8_CLOSEOUT.md"
DIALOG_AUDIT = ROOT / "scripts" / "audit" / "audit_native_dialogs.py"

CORE_FILES = {
    "static/js/views/portfolio/program.js": ("App.confirmDialog(",),
    "static/js/views/explore/explore_workshop_detail.js": ("App.confirmDialog(", "App.promptDialog("),
    "static/js/views/explore/explore_outcomes.js": ("App.confirmDialog(",),
    "static/js/views/explore/explore_requirements.js": ("App.confirmDialog(",),
    "static/js/views/testing/data_factory.js": ("App.confirmDialog(",),
    "static/js/views/testing/defect_management.js": ("App.confirmDialog(",),
    "static/js/views/testing/test_plan_detail.js": ("App.confirmDialog(",),
    "static/js/views/testing/test_planning.js": ("App.confirmDialog(",),
    "static/js/views/testing/evidence_capture.js": ("App.confirmDialog(",),
    "static/js/views/operations/cutover.js": ("App.promptDialog(",),
    "static/js/views/integration/integration.js": ("App.promptDialog(",),
    "static/js/views/governance/approvals.js": ("App.promptDialog(",),
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_app_exposes_shared_confirm_and_prompt_dialog_helpers():
    src = _read(APP_JS)

    assert "function confirmDialog(options = {})" in src
    assert "function promptDialog(options = {})" in src
    assert "function resolveDialog(result)" in src
    assert "function submitPromptDialog()" in src
    assert "confirmDialog, promptDialog, resolveDialog, submitPromptDialog," in src


def test_core_platform_views_use_shared_dialog_helpers_instead_of_native_dialogs():
    for rel_path, expected_markers in CORE_FILES.items():
        src = _read(ROOT / rel_path)
        assert "confirm(" not in src, rel_path
        assert "prompt(" not in src, rel_path
        for marker in expected_markers:
            assert marker in src, (rel_path, marker)


def test_makefile_exposes_critical_ui_regression_targets():
    src = _read(MAKEFILE)

    assert "ui-dialog-audit" in src
    assert "ui-contract-critical" in src
    assert "ui-smoke-critical" in src
    assert "ui-regression-critical" in src
    assert "scripts/audit/audit_native_dialogs.py" in src
    assert "tests/ui_contracts/test_sprint8_ui_contract.py" in src
    assert "tests/16-cutover-integration-scope.spec.ts" in src


def test_sprint8_closeout_runbook_exists():
    src = _read(RUNBOOK)

    assert "Sprint 8 Closeout" in src
    assert "make ui-contract-critical" in src
    assert "make ui-dialog-audit" in src
    assert "make ui-smoke-critical" in src
    assert "Residual exclusions" in src
    assert "Manual test checklist" in src


def test_dialog_audit_script_tracks_only_residual_exclusions_outside_core_scope():
    src = _read(DIALOG_AUDIT)
    assert "templates/platform_admin/" in src
    assert "templates/sso_admin/" in src
    assert "templates/roles_admin/" in src
    assert "static/js/pwa.js" in src
    assert "Core violations:" in src
