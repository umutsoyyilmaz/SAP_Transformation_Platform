#!/usr/bin/env bash
set -euo pipefail

export APP_ENV="${APP_ENV:-testing}"
export GEMINI_API_KEY="${GEMINI_API_KEY:-}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[scope-regression] Suite A: Unit (scope resolver + RBAC)"
"${PYTHON_BIN}" -m pytest -q \
  tests/project_scope/test_scoped_queries.py \
  tests/project_scope/test_project_scope_resolver.py \
  tests/auth/test_rbac_scope_aware.py

echo "[scope-regression] Suite B: Integration (ownership + isolation)"
"${PYTHON_BIN}" -m pytest -q \
  tests/features/test_api_projects.py \
  tests/features/test_api_backlog.py \
  tests/features/test_api_raid.py \
  tests/features/test_discover.py \
  tests/features/test_api_integration.py \
  tests/auth/test_tenant_isolation.py \
  tests/features/test_my_projects_visibility.py \
  tests/project_scope/test_scope_observability_story_51.py \
  tests/features/test_data_quality_guard_jobs.py

echo "[scope-regression] Suite C: SPA contract (context selector + URL/state)"
"${PYTHON_BIN}" -m pytest -q \
  tests/ui_contracts/test_frontend_context_guard_contract.py \
  tests/ui_contracts/test_context_url_routing_contract.py \
  tests/ui_contracts/test_program_projects_ui_contract.py \
  tests/ui_contracts/test_my_projects_ui_contract.py

echo "[scope-regression] Suite D: Guard rules (unsafe lookup prevention)"
"${PYTHON_BIN}" -m pytest -q \
  tests/project_scope/test_scoped_lookup_guard.py

echo "[scope-regression] PASS"
