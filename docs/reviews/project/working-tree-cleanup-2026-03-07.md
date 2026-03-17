# Working Tree Cleanup Inventory — 2026-03-07

## Purpose

Reduce the current dirty worktree into reviewable change sets without
discarding user work or unrelated in-progress refactors.

## Already Cleaned

- Moved manual prompt artifact out of `e2e/` root:
  - `e2e/UITEST` -> `docs/archive/perga_e2e_prompt.md`
- Moved ad hoc helper scripts out of `tests/`:
  - `tests/create_admin.py` -> `scripts/seed_data/create_admin.py`
  - `tests/seed_and_test.py` -> `scripts/seed_data/seed_and_smoke.py`
  - `tests/test_e2e_perga.py` -> `scripts/testing/manual_perga_e2e.py`

## Keep In Main Product Diff

These are directly tied to the completed scope/security/UX/testing backlog:

- `app/blueprints/backlog_bp.py`
- `app/blueprints/discover_bp.py`
- `app/blueprints/program_bp.py`
- `app/blueprints/raid_bp.py`
- `app/blueprints/reporting_bp.py`
- `app/blueprints/testing/__init__.py`
- `app/models/_project_id_sync.py`
- `app/services/backlog_service.py`
- `app/services/discover_service.py`
- `app/services/open_item_lifecycle.py`
- `app/services/program_service.py`
- `app/services/reporting.py`
- `app/services/testing_service.py`
- `app/services/traceability.py`
- `app/models/testing.py`
- `static/js/app.js`
- `static/js/components/trace-chain.js`
- `static/js/views/program.js`
- `static/js/views/project_setup.js` (project-scope work; see mixed-file note below)
- `static/js/views/explore_*`
- `static/js/views/test_*`
- `static/js/views/approvals.js`
- `static/js/views/defect_management.js`
- `static/js/views/testing/evidence_capture.js`
- `templates/index.html`
- targeted regression and E2E coverage:
  - `tests/conftest.py`
  - `tests/test_api_backlog.py`
  - `tests/test_api_program.py`
  - `tests/test_api_raid.py`
  - `tests/test_api_test_planning_services.py`
  - `tests/test_api_testing.py`
  - `tests/test_cloud_alm_service.py`
  - `tests/test_coverage_reporting.py`
  - `tests/test_export_service.py`
  - `tests/test_process_mining_service.py`
  - `tests/test_project_service.py`
  - `tests/test_requirement_consolidation.py`
  - `tests/test_tenant_migration.py`
  - `tests/test_timeline.py`
  - `tests/test_traceability_unified.py`
  - `tests/test_upstream_trace.py`
  - `tests/test_workshop_integration_mapping.py`
  - `tests/test_explore_ui_contract.py`
  - `tests/test_test_management_ui_contract.py`
  - `e2e/tests/03-explore.spec.ts`
  - `e2e/tests/10-test-management-ops.spec.ts`
  - `e2e/tests/11-test-management-workflows.spec.ts`
  - `e2e/tests/12-cross-module-traceability.spec.ts`

### Partial file keep: `app/services/project_service.py`

Keep only the project CRUD / ownership helpers that are already wired into the
product behavior delivered on this branch:

- `list_projects()`
- `list_authorized_projects()`
- `create_project()`
- `update_project()`
- `get_project_detail()`
- `delete_project()`

Related tests that stay with the main diff:

- `test_create_project_success`
- `test_create_project_duplicate_code_returns_409`
- `test_update_project_cross_program_forbidden`
- `test_project_id_sync_sets_none_without_default_project`
- `test_delete_project_non_default_succeeds`
- `test_delete_project_default_blocked`
- `test_get_project_detail`

Additional keep note:

- `app/blueprints/raid_bp.py` is in-scope with the same legacy `tenant_id=NULL`
  ownership fallback pattern already fixed in backlog paths; its companion
  regression coverage in `tests/test_api_raid.py` should stay with the main
  security diff.

## Separate Change Set Candidates

These appear to be larger refactors that should likely be reviewed in their
own commit/PR rather than mixed into the product-behavior diff:

### Developer experience / local tooling

Decision: should move out of the main product branch into its own local-dev
change set. Rationale:

- the diff is purely developer experience (`make run` behavior, help text)
- it does not affect the shipped Explore / Testing / scope-security behavior
- it will create noisy review churn if kept with the product backlog diff

- `Makefile`

### Extra project health helpers

Decision: should move out of the main product branch into their own cleanup or
follow-up feature change set. Rationale:

- no blueprint, frontend, or regression test currently calls them
- they widen `project_service.py` beyond the project-scope/security work
- `project_setup.js` renders RAG fields from project payload, but current flow
  does not call these dedicated helpers

- `app/services/project_health_service.py`

### Model split

Decision: should move out of the main product branch into its own refactor
change set. Rationale:

- the diff is primarily structural extraction, not backlog behavior
- the package can now stand mostly behind `app.models.program`
- direct service coupling was reduced during cleanup
- remaining references already consume the re-export layer from
  `app.models.program`, which makes later extraction safer

- `app/models/program.py`
- `app/models/workstream.py`
- `app/models/governance_docs.py`
- `app/models/raci.py`
- `app/models/stakeholder.py`
- `tests/test_project_scope_fk_regression.py`

### CSS split

Decision: can stay on this branch. Rationale:

- `templates/index.html` now uses `main.css` as the single entrypoint again
- service worker, smoke tests, and PWA checks continue to reference `main.css`
- the split is now mostly an internal asset organization change behind the
  compatibility shim

- `static/css/main.css`
- `static/css/base.css`
- `static/css/program-views.css`
- `static/css/project-setup.css`
- `static/css/backlog.css`
- `static/css/raid-ai.css`
- `static/css/explore.css`
- `static/css/discover.css`
- `scripts/infrastructure/split_main_css.py`

### AI document actions extracted from mixed views

Decision: keep isolated as their own follow-up feature files. Rationale:

- they are self-contained AI entry points
- they no longer need to stay embedded inside broader backlog/reporting views
- this reduces noise in `backlog.js` and `reports.js`

- `static/js/views/backlog_ai.js`
- `static/js/views/reports_ai.js`

### Project setup info surface extracted from main view

Decision: keep isolated as its own follow-up feature file. Rationale:

- richer project info display/editing is now physically separate from the
  core project-scope tab orchestration
- this reduces noise in `project_setup.js`
- it remains visible as a follow-up feature candidate instead of being hidden
  inside the main setup flow

- `static/js/views/project_setup_info.js`

### Discover charter surface extracted from main view

Decision: keep isolated as its own follow-up feature file. Rationale:

- charter payload normalization and approval modal logic are now physically
  separate from the broader Discover workspace shell
- this reduces noise in `discover.js`
- the feature remains easy to split later without disturbing the main
  navigation/workspace flow

- `static/js/views/discover_charter.js`

## Needs Review Before Cleanup

These still need a deliberate cleanup decision because they span multiple
themes or likely contain user work beyond the backlog delivered here:

- broad service/test files outside the targeted regression set
- mixed frontend files that combine shipped UX work with unrelated edits:
  - `static/js/views/discover.js`

### Mixed frontend file: `static/js/views/project_setup.js`

Keep on this branch:

- project-scoped methodology loading via `project_id`
- project-scoped team loading via `project_id`
- project-scoped governance loading via `project_id`
- project timeline tab via `project_id`

Needs follow-up review / possible split:

- save flow wiring for the richer project info surface
- interaction between the core setup tabs and `project_setup_info.js`

Reason:

- the heavy UI/template surface was extracted, but the branch still contains
  the project-info feature wiring alongside the project-scope fixes

### Mixed frontend file: `static/js/views/discover.js`

Likely keep, but still review separately for scope clarity:

- charter workspace wiring and callback flow into `discover_charter.js`
- enum label polish and empty-state improvements
- table badge / readability improvements

Reason:

- the charter-specific modal/payload logic was extracted, but the file still
  carries broader UX polish alongside the shipped Discover workspace behavior

## Next Cleanup Pass

1. Review the `Needs Review` group and classify each file.
2. Keep the `Model split` group isolated and avoid adding new dependencies to it.
3. Leave the `CSS split` group on this branch behind `main.css`.
4. Decide whether `Makefile` and `project_health_service.py` stay as local-only
   changes or move to their own follow-up patch.
5. If preparing a final PR, remove the `Makefile` and `Model split` groups from
   the product diff first, then review the isolated feature files
   (`*_ai.js`, `project_setup_info.js`, `discover_charter.js`,
   `project_health_service.py`) one by one.

## Final PR Candidate Set

Minimal product PR based on the current worktree:

### Include

- everything in `Keep In Main Product Diff`
- CSS split group:
  - `static/css/main.css`
  - `static/css/base.css`
  - `static/css/program-views.css`
  - `static/css/project-setup.css`
  - `static/css/backlog.css`
  - `static/css/raid-ai.css`
  - `static/css/explore.css`
  - `static/css/discover.css`
  - `static/css/explore-tokens.css`
  - `scripts/infrastructure/split_main_css.py`
- extracted UI helpers still required by included views:
  - `static/js/views/backlog_ai.js`
  - `static/js/views/reports_ai.js`
  - `static/js/views/project_setup_info.js`
  - `static/js/views/discover_charter.js`
- supporting shared/front-end glue discovered during cleanup:
  - `static/js/components/explore-shared.js`
  - `static/js/components/pg_command_palette.js`
  - `app/services/explore_legacy/process_levels_legacy.py`
  - `e2e/playwright.explore.config.ts`
  - `e2e/playwright.tm.config.ts`

### Do Not Include In This PR

- `Makefile`
- `app/services/project_health_service.py`
- Model split group:
  - `app/models/program.py`
  - `app/models/workstream.py`
  - `app/models/governance_docs.py`
  - `app/models/raci.py`
  - `app/models/stakeholder.py`
  - `tests/test_project_scope_fk_regression.py`
- cleanup-only docs / moved manual helpers:
  - `docs/archive/perga_e2e_prompt.md`
  - `docs/reviews/project/working-tree-cleanup-2026-03-07.md`
  - `scripts/testing/manual_perga_e2e.py`
  - `scripts/seed_data/create_admin.py`
  - `scripts/seed_data/seed_and_smoke.py`
- broader workspace/dashboard/auth package not required for the core PR:
  - `app/__init__.py`
  - `app/auth.py`
  - `app/middleware/blueprint_permissions.py`
  - `app/services/dashboard_engine.py`
  - `static/js/auth.js`
  - `static/js/components/workspace-shared.js`
  - `static/js/views/ai_insights.js`
  - `static/js/views/cutover.js`
  - `static/js/views/dashboard.js`
  - `static/js/views/data_factory.js`
  - `static/js/views/executive_cockpit.js`
  - `static/js/views/integration.js`
  - `static/js/views/raci.js`
  - `static/js/views/raid.js`
  - `static/js/views/timeline.js`
  - `static/css/pg-dashboard.css`
  - `e2e/tests/02-dashboard.spec.ts`
  - `tests/test_api_projects.py`
  - `tests/test_discover.py`
  - `tests/test_reporting_f5.py`
  - `tests/test_workspace_ui_contract.py`

## Physical Separation Plan

Use this sequence when actually splitting the current worktree into reviewable
change sets.

### Pass 1: Main Product PR

Goal: keep only the core backlog / scope-security / Explore / Test Management
product work plus the files listed in `Include`.

Actions:

1. Create a safety snapshot branch from the current dirty state.
2. Stage only the files in `Include`.
3. Run the targeted verification already used during development:
   - Python targeted API/regression tests
   - JS `node --check` for touched frontend files
   - Explore/TM Playwright smoke/workflow specs
4. Review the staged diff only.

Expected output:

- the main product PR / commit

### Pass 2: Local Dev / Tooling PR

Goal: isolate the `Makefile` ergonomics change.

Files:

- `Makefile`

Checks:

- `make help`
- `make run` / `make run-debug` behavior review

Expected output:

- separate local-dev PR / commit

### Pass 3: Model Split Refactor PR

Goal: isolate structural model extraction from behavioral changes.

Files:

- `app/models/program.py`
- `app/models/workstream.py`
- `app/models/governance_docs.py`
- `app/models/raci.py`
- `app/models/stakeholder.py`
- `tests/test_project_scope_fk_regression.py`

Checks:

- import smoke via `python3 -m py_compile`
- targeted FK / scope regression tests
- verify app code still consumes models through `app.models.program`

Expected output:

- separate refactor PR / commit

### Pass 4: Follow-up Feature PRs

Goal: decide whether extracted helper surfaces ship now or later.

Candidate files:

- `app/services/project_health_service.py`
- `static/js/views/backlog_ai.js`
- `static/js/views/reports_ai.js`
- `static/js/views/project_setup_info.js`
- `static/js/views/discover_charter.js`

Decision rule:

- if the main product PR references the file at runtime, keep it there
- if the file is not referenced by shipped routes/views, move it into its own
  follow-up feature PR

### Pass 5: Cleanup-only Support Files

Goal: keep archival/manual helpers out of product review.

Files:

- `docs/archive/perga_e2e_prompt.md`
- `docs/reviews/project/working-tree-cleanup-2026-03-07.md`
- `scripts/testing/manual_perga_e2e.py`
- `scripts/seed_data/create_admin.py`
- `scripts/seed_data/seed_and_smoke.py`

Expected output:

- docs/support cleanup commit, or leave uncommitted if purely local

### Branch Strategy

Recommended split:

1. `feature/core-product-pr`
2. `chore/local-dev-makefile`
3. `refactor/model-split`
4. optional follow-up feature branches for extracted helper files

### Important Safety Rule

Do not use destructive cleanup commands on the current dirty branch. Build the
split by staging / branching from the snapshot state so unrelated user changes
are not lost.

## Core Product PR Staging Checklist

Stage exactly these paths for the minimal core product PR:

### Backend

- `app/blueprints/backlog_bp.py`
- `app/blueprints/discover_bp.py`
- `app/blueprints/program_bp.py`
- `app/blueprints/raid_bp.py`
- `app/blueprints/reporting_bp.py`
- `app/blueprints/testing/__init__.py`
- `app/models/_project_id_sync.py`
- `app/models/testing.py`
- `app/services/backlog_service.py`
- `app/services/discover_service.py`
- `app/services/explore_legacy/process_levels_legacy.py`
- `app/services/open_item_lifecycle.py`
- `app/services/program_service.py`
- `app/services/project_service.py`
- `app/services/reporting.py`
- `app/services/testing_service.py`
- `app/services/traceability.py`

### Frontend CSS / Templates

- `static/css/main.css`
- `static/css/base.css`
- `static/css/program-views.css`
- `static/css/project-setup.css`
- `static/css/backlog.css`
- `static/css/raid-ai.css`
- `static/css/explore.css`
- `static/css/discover.css`
- `static/css/explore-tokens.css`
- `templates/index.html`

### Frontend Components / Views

- `static/js/app.js`
- `static/js/components/explore-shared.js`
- `static/js/components/governance-shared.js`
- `static/js/components/pg_command_palette.js`
- `static/js/components/trace-chain.js`
- `static/js/views/approvals.js`
- `static/js/views/backlog.js`
- `static/js/views/backlog_ai.js`
- `static/js/views/defect_management.js`
- `static/js/views/discover.js`
- `static/js/views/discover_charter.js`
- `static/js/views/testing/evidence_capture.js`
- `static/js/views/explore_dashboard.js`
- `static/js/views/explore_hierarchy.js`
- `static/js/views/explore_outcomes.js`
- `static/js/views/explore_requirements.js`
- `static/js/views/explore_workshop_detail.js`
- `static/js/views/explore_workshops.js`
- `static/js/views/program.js`
- `static/js/views/project_setup.js`
- `static/js/views/project_setup_info.js`
- `static/js/views/reports.js`
- `static/js/views/reports_ai.js`
- `static/js/views/testing/test_execution.js`
- `static/js/views/test_overview.js`
- `static/js/views/testing/test_planning.js`
- `static/js/views/testing_shared.js`

### Tests / E2E

- `tests/conftest.py`
- `tests/test_api_backlog.py`
- `tests/test_api_program.py`
- `tests/test_api_raid.py`
- `tests/test_api_test_planning_services.py`
- `tests/test_api_testing.py`
- `tests/test_cloud_alm_service.py`
- `tests/test_coverage_reporting.py`
- `tests/test_export_service.py`
- `tests/test_explore_ui_contract.py`
- `tests/test_process_mining_service.py`
- `tests/test_project_service.py`
- `tests/test_requirement_consolidation.py`
- `tests/test_tenant_migration.py`
- `tests/test_test_management_ui_contract.py`
- `tests/test_timeline.py`
- `tests/test_traceability_unified.py`
- `tests/test_upstream_trace.py`
- `tests/test_workshop_integration_mapping.py`
- `e2e/playwright.explore.config.ts`
- `e2e/playwright.tm.config.ts`
- `e2e/tests/03-explore.spec.ts`
- `e2e/tests/10-test-management-ops.spec.ts`
- `e2e/tests/11-test-management-workflows.spec.ts`
- `e2e/tests/12-cross-module-traceability.spec.ts`

### Support

- `scripts/infrastructure/split_main_css.py`
