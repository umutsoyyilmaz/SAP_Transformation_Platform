# ADR-008 PR Description Draft

## Title
ADR-008: L3 scope enforcement + TestCase/Suite N:M + suite_type removal

## Summary
This PR finalizes ADR-008 implementation and post-transition cleanup for SAP Activate traceability.
It keeps `suite_ids` + junction table as the active contract and removes both `suite_type` and legacy `TestCase.suite_id`.

## What Changed

### Backend
- Added/activated L3 scope resolution + validation for relevant test case flows.
- Completed TestCase↔Suite N:M behavior via `TestCaseSuiteLink`.
- Updated create/update/generation/import paths to prefer `suite_ids` and junction sync.
- Removed the remaining `suite_id` compatibility path from active test case flows.

### Frontend
- Test Planning now uses suite multi-select and `suite_ids`-first payload behavior.
- Scope governance/override UX and L3 coverage snapshot are integrated.
- Suite UX is purpose-first with no active `suite_type` surface.

### E2E / Test Stability
- Stabilized smoke tests against current auth/navigation behavior.
- Updated Playwright server startup to deterministic development config + known SQLite dataset.

### Documentation
- Implementation status updated to `Execution Complete (Post-Transition)`.
- Deprecation checklist updated with latest validation evidence.
- Release readiness report added.

## Validation Evidence

### Backend
- `pytest tests/test_management/test_api_testing.py tests/test_management/test_api_test_planning_services.py tests/project_scope/test_scope_resolution.py -q`
- `pytest tests/test_management/test_api_testing.py -k "suite_ids or scope_coverage" -q`

### E2E
- `npm run test:e2e -- tests/06-fe-sprint3-smoke.spec.ts tests/07-phase3-traceability-smoke.spec.ts`
- Result: `18 passed`.

## Compatibility / Risk
- `suite_type` has been removed from model/DB/default API contract.
- `TestCase.suite_id` has been removed from model/DB/default API contract.

## Sunset Plan
- No active sunset items remain in the ADR-008 scope.

## Rollback Notes
- `suite_type` drop is destructive at schema level; rollback requires Alembic downgrade or DB restore.
- Pre-drop DB backup should be retained for fast rollback.

## Checklist
- [x] Core ADR-008 implementation complete
- [x] Transition cleanup complete for active paths
- [x] Backend regression matrix green
- [x] E2E smoke matrix green
- [x] Plan/checklist/readiness docs updated

---

## GitHub PR Body (Short)

```markdown
## Summary
Implements ADR-008 post-transition state: L3 scope enforcement, TestCase↔Suite N:M (`suite_ids` + junction), and purpose-only suite model.

## Key Changes
- Backend: scope resolution + N:M suite sync on create/update/generation/import/clone paths
- Frontend: suite multi-select, governance/scope UX, purpose-first labels
- Compatibility: no active `suite_id` / `suite_type` legacy path remains in test case runtime
- E2E: smoke tests stabilized with deterministic Playwright server config

## Validation
- `pytest tests/test_management/test_api_testing.py tests/test_management/test_api_test_planning_services.py tests/project_scope/test_scope_resolution.py -q`
- `pytest tests/test_management/test_api_testing.py -k "suite_ids or scope_coverage" -q`
- `npm run test:e2e -- tests/06-fe-sprint3-smoke.spec.ts tests/07-phase3-traceability-smoke.spec.ts`
- Result: `18 passed`

## Deprecation Timeline
- `suite_type` removed
- `TestCase.suite_id` removed
```

## GitHub PR Body (Long)

```markdown
## Summary
This PR finalizes ADR-008 (Test Architecture Redesign) in post-transition state.
It keeps `suite_ids` + `test_case_suite_links` as the active contract and removes `suite_type`.
It also removes the legacy `TestCase.suite_id` mirror field from runtime code and schema.

## Scope
- L3 scope mandatory resolution for Unit/SIT/UAT test cases
- TestCase↔Suite relationship migrated from single FK to N:M junction
- `suite_type` removed in favor of `purpose` + `tags`

## Backend Changes
- Added/activated scope resolution validation in test case flows
- Completed junction-table based suite assignment sync on create/update
- Updated generation/import/clone paths to avoid core dependency on legacy `suite_id`
- Removed the remaining `suite_id` compatibility behavior from active runtime code

## Frontend Changes
- Test Planning modal uses suite multi-select and `suite_ids`-first payloads
- Scope governance/override and L3 coverage snapshot integrated
- Purpose-first suite wording in primary screens

## E2E / Regression Stabilization
- Updated sprint3 smoke checks for current navigation/auth behavior
- Ensured deterministic Playwright web server startup config
- Full smoke subset pass: `06-fe-sprint3-smoke` + `07-phase3-traceability-smoke` = `18/18`

## Validation Evidence
### Backend
- `pytest tests/test_management/test_api_testing.py tests/test_management/test_api_test_planning_services.py tests/project_scope/test_scope_resolution.py -q`
- `pytest tests/test_management/test_api_testing.py -k "suite_ids or scope_coverage" -q`

### E2E
- `npm run test:e2e -- tests/06-fe-sprint3-smoke.spec.ts tests/07-phase3-traceability-smoke.spec.ts`
- Result: `18 passed`

## Compatibility / Risk
- Transition cleanup is complete for `suite_type`
- Transition cleanup is complete for `TestCase.suite_id`

## Sunset Plan
- No active sunset items remain in ADR-008 scope

## Rollback Notes
- Additive schema allows fast behavioral rollback without destructive migration
- Can revert active write path behavior while keeping migrated structures in place
```
