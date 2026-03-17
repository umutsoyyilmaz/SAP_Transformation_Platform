#!/usr/bin/env python3
"""Audit native browser dialog usage across core user-facing surfaces."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
PATTERN = re.compile(r"\b(confirm|alert|prompt)\s*\(")

# Residual exclusions explicitly left outside Sprint 8 closeout.
EXCLUDED_PREFIXES = (
    "templates/platform_admin/",
    "templates/sso_admin/",
    "templates/roles_admin/",
)
EXCLUDED_PATHS = {
    "static/js/pwa.js",
}

AUDIT_SCOPE = {
    "static/js/views/portfolio/program.js",
    "static/js/views/setup/project_setup.js",
    "static/js/views/explore/explore_workshop_detail.js",
    "static/js/views/explore/explore_outcomes.js",
    "static/js/views/explore/explore_requirements.js",
    "static/js/views/explore/explore_hierarchy.js",
    "static/js/views/explore/explore_workshops.js",
    "static/js/views/governance/raid.js",
    "static/js/views/governance/reports.js",
    "static/js/views/governance/reports_ai.js",
    "static/js/views/testing/data_factory.js",
    "static/js/views/testing/defect_management.js",
    "static/js/views/testing/test_plan_detail.js",
    "static/js/views/testing/test_planning.js",
    "static/js/views/testing/test_execution.js",
    "static/js/views/testing/evidence_capture.js",
    "static/js/views/delivery/backlog.js",
    "static/js/views/operations/cutover.js",
    "static/js/views/integration/integration.js",
    "static/js/views/governance/approvals.js",
}


def _iter_files() -> Iterable[Path]:
    for rel_path in sorted(AUDIT_SCOPE):
        path = ROOT / rel_path
        if path.is_file():
            yield path


def _is_excluded(rel_path: str) -> bool:
    if rel_path in EXCLUDED_PATHS:
        return True
    return any(rel_path.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def main() -> int:
    violations: list[tuple[str, int, str]] = []
    residuals: list[tuple[str, int, str]] = []

    for path in _iter_files():
        rel_path = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = PATTERN.search(line)
            if not match:
                continue
            row = (rel_path, lineno, line.strip())
            if _is_excluded(rel_path):
                residuals.append(row)
            else:
                violations.append(row)

    print("Sprint 8 Native Dialog Audit")
    print("============================")
    print(f"Audited files: {len(AUDIT_SCOPE)}")
    print(f"Core violations: {len(violations)}")
    print(f"Residual exclusions: {len(residuals)}")

    if violations:
        print("\nBlocking core violations:")
        for rel_path, lineno, line in violations:
            print(f"- {rel_path}:{lineno}: {line}")

    if residuals:
        print("\nResidual exclusions:")
        for rel_path, lineno, line in residuals:
            print(f"- {rel_path}:{lineno}: {line}")

    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
