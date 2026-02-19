# ADR-008 PR Description Draft

## Title
ADR-008: L3 scope enforcement + TestCase/Suite N:M + suite_type→purpose transition (transition mode)

## Summary
This PR finalizes ADR-008 implementation and transition cleanup for SAP Activate traceability.
It keeps backward compatibility while making `suite_ids` + junction table the active contract.

## What Changed

### Backend
- Added/activated L3 scope resolution + validation for relevant test case flows.
- Completed TestCase↔Suite N:M behavior via `TestCaseSuiteLink`.
- Updated create/update/generation/import paths to prefer `suite_ids` and junction sync.
- Preserved legacy `suite_id` compatibility path with deprecation warnings.

### Frontend
- Test Planning now uses suite multi-select and `suite_ids`-first payload behavior.
- Scope governance/override UX and L3 coverage snapshot are integrated.
- Suite UX moved to purpose-first wording; legacy `suite_type` shown read-only during transition.

### E2E / Test Stability
- Stabilized smoke tests against current auth/navigation behavior.
- Updated Playwright server startup to deterministic development config + known SQLite dataset.

### Documentation
- Implementation status updated to `Execution Complete (Transition Mode)`.
- Deprecation checklist updated with latest validation evidence.
- Release readiness report added.

## Validation Evidence

### Backend
- `pytest tests/test_api_testing.py tests/test_api_test_planning_services.py tests/test_scope_resolution.py -q`
- `pytest tests/test_api_testing.py -k "suite_ids or scope_coverage" -q`

### E2E
- `npm run test:e2e -- tests/06-fe-sprint3-smoke.spec.ts tests/07-phase3-traceability-smoke.spec.ts`
- Result: `18 passed`.

## Compatibility / Risk
- Transition mode is active: `suite_id` and `suite_type` remain readable/accepted in compatibility paths only.
- Expected deprecation warnings may appear in legacy-path tests.

## Sunset Plan
- `suite_id` write-disable target: 2026-06-30
- Compatibility removal review target: 2026-09-30

## Rollback Notes
- Rollback can keep DB schema additive artifacts in place and revert active write paths to previous API behavior if required.
- No destructive migration required for immediate rollback.

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
Implements ADR-008 in transition mode: L3 scope enforcement, TestCase↔Suite N:M (`suite_ids` + junction), and purpose-first suite model.

## Key Changes
- Backend: scope resolution + N:M suite sync on create/update/generation/import paths
- Frontend: suite multi-select, governance/scope UX, purpose-first labels
- Compatibility: legacy `suite_id`/`suite_type` retained in compatibility layer with deprecation warnings
- E2E: smoke tests stabilized with deterministic Playwright server config

## Validation
- `pytest tests/test_api_testing.py tests/test_api_test_planning_services.py tests/test_scope_resolution.py -q`
- `pytest tests/test_api_testing.py -k "suite_ids or scope_coverage" -q`
- `npm run test:e2e -- tests/06-fe-sprint3-smoke.spec.ts tests/07-phase3-traceability-smoke.spec.ts`
- Result: `18 passed`

## Deprecation Timeline
- `suite_id` write-disable target: `2026-06-30`
- compatibility removal review: `2026-09-30`
```

## GitHub PR Body (Long)

```markdown
## Summary
This PR finalizes ADR-008 (Test Architecture Redesign) under transition mode.
It preserves backward compatibility while making `suite_ids` + `test_case_suite_links` the active contract.

## Scope
- L3 scope mandatory resolution for Unit/SIT/UAT test cases
- TestCase↔Suite relationship migrated from single FK to N:M junction
- `suite_type` deprecated in favor of `purpose` + `tags`

## Backend Changes
- Added/activated scope resolution validation in test case flows
- Completed junction-table based suite assignment sync on create/update
- Updated generation/import paths to avoid core dependency on legacy `suite_id`
- Kept legacy compatibility behavior with explicit deprecation warnings

## Frontend Changes
- Test Planning modal uses suite multi-select and `suite_ids`-first payloads
- Scope governance/override and L3 coverage snapshot integrated
- Purpose-first suite wording in primary screens; `suite_type` read-only in transition UI

## E2E / Regression Stabilization
- Updated sprint3 smoke checks for current navigation/auth behavior
- Ensured deterministic Playwright web server startup config
- Full smoke subset pass: `06-fe-sprint3-smoke` + `07-phase3-traceability-smoke` = `18/18`

## Validation Evidence
### Backend
- `pytest tests/test_api_testing.py tests/test_api_test_planning_services.py tests/test_scope_resolution.py -q`
- `pytest tests/test_api_testing.py -k "suite_ids or scope_coverage" -q`

### E2E
- `npm run test:e2e -- tests/06-fe-sprint3-smoke.spec.ts tests/07-phase3-traceability-smoke.spec.ts`
- Result: `18 passed`

## Compatibility / Risk
- Transition mode remains active for `suite_id`/`suite_type` compatibility paths
- Deprecation warnings are expected in legacy-path tests

## Sunset Plan
- `suite_id` write-disable target: `2026-06-30`
- compatibility removal review target: `2026-09-30`

## Rollback Notes
- Additive schema allows fast behavioral rollback without destructive migration
- Can revert active write path behavior while keeping migrated structures in place
```
