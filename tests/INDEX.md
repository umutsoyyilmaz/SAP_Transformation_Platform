# Tests Index

This directory keeps `conftest.py` at the root for pytest fixture discovery and groups test files by intent.

## Categories

- `ai/`: AI, knowledge base, assistant, performance, and phase rollout coverage.
- `auth/`: authentication, SSO, RBAC, tenant isolation, and tenant migration coverage.
- `project_scope/`: scope resolution, backfill, guardrails, observability, and schema/backfill regression coverage.
- `ui_contracts/`: frontend route, shell, workspace, governance, project setup, and test management contract checks.
- `test_management/`: test planning, execution, release gate, performance budget, and shared TM fixtures.
- `features/`: cross-module API, business workflow, cutover, workshop, explore, and domain feature suites.
- `quality/`: reporting, polish, monitoring, PWA, demo flow, audit/trace, and quality regression suites.
- `unit/`: reserved for future explicit unit-only grouping.
- `integration/`: reserved for future explicit integration-only grouping.
- `e2e/`: reserved for legacy pytest-style end-to-end tests inside the Python test tree.

## Notes

- Historical documents may describe pre-refactor flat paths. Use the current folder taxonomy above when adding or moving tests.
- Automation entry points such as `Makefile`, `.github/workflows/ci.yml`, and `scripts/testing/ci_project_scope_regression.sh` already follow this layout.
