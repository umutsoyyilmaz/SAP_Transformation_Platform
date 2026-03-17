# AI-Friendly Explorer Refactor - Phase 0 Guardrails

Date: 2026-03-15
Status: Completed
Scope: Inventory stabilization and path-sensitive guardrails before any folder-level refactor.

## Objective

Phase 0 exists to prevent avoidable breakage during the explorer cleanup. The goal is to verify which roots are framework- or tooling-sensitive, identify hardcoded path dependencies, and define the safe operating boundaries for later refactor phases.

## Locked Roots

The following paths are treated as fixed and must not be renamed or relocated during the explorer refactor:

- `docker/`
- `migrations/`
- `migrations/versions/`
- `static/`
- `templates/`
- `tests/`
- `tests/conftest.py`
- `e2e/`
- `app/__init__.py`
- `wsgi.py`
- `pyproject.toml`
- `ruff.toml`
- `Makefile`

## Verified Constraints

### Flask runtime constraints

- [app/__init__.py](app/__init__.py) initializes Flask with `static_folder="../static"` and `template_folder="../templates"`.
- Renaming or relocating `static/` or `templates/` would break frontend asset serving and Jinja template resolution.
- [wsgi.py](wsgi.py) imports `create_app()` directly from `app`, so the application entrypoint must remain stable.

### Pytest constraints

- [pyproject.toml](pyproject.toml) sets `testpaths = ["tests"]` and ignores `tests/archive` explicitly.
- [tests/conftest.py](tests/conftest.py) is a root fixture anchor and must remain directly under `tests/`.
- The CI and local automation reference many tests by exact file path, not only by markers or folders.

### Playwright constraints

- [e2e/playwright.config.ts](e2e/playwright.config.ts) and sibling configs depend on the `e2e/` root layout.
- `playwright.shared.ts` and multiple Make targets expect `e2e/tests/...` and `playwright*.config.ts` to stay in place.
- `e2e/` may be reorganized internally later, but only with explicit config and script updates.

### Frontend asset constraints

- [templates/index.html](templates/index.html) hardcodes a long list of `/static/css/...` and `/static/js/...` asset paths.
- Any `static/js/` or `static/css/` regrouping requires a synchronized update in [templates/index.html](templates/index.html).

## High-Risk Path Dependencies

### `scripts/` hard dependencies

The following files currently hardcode script paths and must be updated during any scripts reorganization:

- [Makefile](Makefile): dozens of direct calls such as `scripts/data/seed/seed_demo_data.py`, `scripts/data/migrate/backfill_project_scope.py`, `scripts/testing/ci_project_scope_regression.sh`, `scripts/infrastructure/deploy.sh`, `scripts/testing/tm_migration_smoke.py`.
- `.github/workflows/ci.yml`: direct references to `scripts/testing/ci_project_scope_regression.sh`, `scripts/testing/tm_migration_smoke.py`, `scripts/infrastructure/deploy.sh`.
- [docs/reviews/project/e2e_test_gap_report.md](docs/reviews/project/e2e_test_gap_report.md): references `scripts/testing/e2e_local_test.py`.
- Multiple review and FDD documents under `docs/` reference exact script paths.

### `tests/` hard dependencies

The following files currently hardcode test file paths and must be updated during any tests reorganization:

- [Makefile](Makefile): direct file targets such as `tests/test_management/test_api_testing.py`, `tests/test_management/test_tm_release_gate.py`, `tests/ui_contracts/test_test_management_ui_contract.py`, `tests/test_management/test_tm_perf_budget.py`.
- `.github/workflows/ci.yml`: direct references to exact test files and deselect patterns.
- Many review and FDD docs under `docs/` reference individual test files by current path.

### `app/` import dependencies

- [app/__init__.py](app/__init__.py) imports a large number of blueprints by exact module path, for example `from app.blueprints.program_bp import program_bp`.
- Backend refactor under `app/blueprints/`, `app/services/`, and `app/models/` must either:
  - update all imports in one controlled wave, or
  - introduce compatibility re-export shims during transition.
- Current backend packaging is highly import-sensitive; flat-to-package moves are not safe without coordinated import rewrites.

## Safe Refactor Boundaries by Area

### Safe to restructure early

- `docs/`
- `scripts/`
- `tests/` internal layout under the fixed `tests/` root

These areas have many path references, but the breakage surface is predictable and mostly documentation, CI, and task automation.

### Restructure later, with coordinated updates

- `app/blueprints/`
- `app/services/`
- `app/models/`
- `static/js/`
- `static/css/`

These areas are coupled to Python imports, Flask wiring, and frontend asset loading order.

## Phase 0 Findings

1. The repo already has a partial cleanup skeleton for `docs/`, `scripts/`, and `tests/`, but many active files still sit in flat roots.
2. The biggest hardcoded-path surfaces are [Makefile](Makefile), `.github/workflows/ci.yml`, [templates/index.html](templates/index.html), and `docs/` references.
3. Backend package refactor is feasible, but only after path-light areas are cleaned first.
4. Frontend explorer regrouping must be treated as an include-order refactor, not a simple folder rename.

## Approved Operating Rules for Later Phases

1. Do not rename locked roots listed above.
2. Prefer phase-by-phase moves over a single large relocation.
3. Update hardcoded paths in the same change set as each move.
4. Treat [app/__init__.py](app/__init__.py) and [templates/index.html](templates/index.html) as integration chokepoints.
5. Preserve `tests/conftest.py` at the `tests/` root.
6. Preserve Playwright config file names and the `e2e/` root.

## Recommended Next Step

Phase 1 should start with `docs/` information architecture cleanup, followed by `scripts/`, then `tests/`. That order maximizes explorer clarity while keeping runtime breakage risk low.
