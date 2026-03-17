# ADR-008 Deprecation Cleanup Checklist
## suite_id / suite_type Transition Guardrail

**Status:** Cleanup Complete (Sunset Applied)
**Date:** 2026-03-11
**Owner:** Platform Team

---

## 1) Current Contract

- `TestCase.suite_ids` + `TestCaseSuiteLink` is the active and only suite-membership contract for test cases.
- `TestCase.suite_id` has been removed from model, DB schema, and default API responses.
- `TestSuite.suite_type` has been removed from model/DB/API responses.
- API no longer accepts legacy `suite_type` payloads; `purpose` is required.

---

## 2) Completed

- [x] N:M junction model added (`test_case_suite_links`).
- [x] Migration added + backfill (`suite_id -> junction`).
- [x] New/active frontend path sends `suite_ids` (Test Planning modal).
- [x] `create_test_case` / `update_test_case` use junction sync for suite membership.
- [x] Auto-generation flows (`generate_from_wricef`, `generate_from_process`) stopped writing `suite_id` directly.
- [x] Clone flow now links suites via junction as primary path.
- [x] `TestCase.suite_id` removed from model and default serialization.
- [x] Alembic migration applied to drop `test_cases.suite_id`.
- [x] API rejects legacy `suite_id` writes for test case create/update/clone flows.

---

## 3) Remaining Cleanup

### 3.1 Backend
- [x] Remove direct `TestCase.query.filter_by(suite_id=...)` from non-legacy service paths.
- [x] Remove legacy mirror writes from active runtime code.
- [x] Add guard tests: legacy `suite_id` writes are rejected.

### 3.2 Frontend
- [x] Remove fallback reads `tc.suite_id` after one release window.
- [x] Keep only `suite_ids` selection/state in UI models.
- [x] Replace catalog row modal detail path with full-page test case detail view.
- [x] Keep modal as quick-create/legacy fallback only.

### 3.3 API Contract
- [x] Mark `suite_id` as deprecated in docs/Swagger blocks.
- [x] Remove `suite_id` from active test case response contract.
- [x] Reject `suite_id` request aliases at the API boundary.

### 3.4 Suite Type Cleanup
- [x] Replace remaining “type-first” labels with `purpose` in list/detail UI where applicable.
- [x] Remove `suite_type` from model and DB schema.
- [x] Reject `suite_type` request aliases at the API boundary.

---

## 4) Exit Criteria (Cleanup Done)

- [x] All active write paths use `suite_ids` + junction only.
- [x] Legacy `suite_id` compatibility branch removed from active runtime code.
- [x] Tests cover modern contract and legacy alias rejection.
- [x] Deprecation notice + removal execution documented.

---

## 5) Final Sunset State

1. `suite_type` sunset is complete: model, DB, and default API contract are purpose-only.
2. `TestCase.suite_id` sunset is complete: model, DB, and active API contract use `suite_ids` only.
3. Historical documentation may still reference intermediate deprecation phases.

---

## 6) Latest Validation Evidence (2026-03-11)

- Backend regression pass: `pytest tests/test_management/test_api_testing.py tests/test_management/test_api_test_planning_services.py tests/project_scope/test_scope_resolution.py -q`
- Focused API contract pass: `pytest tests/test_management/test_api_testing.py -k "suite_ids or scope_coverage" -q`
- Suite removal regression pass: `pytest tests/test_management/test_api_testing.py tests/test_management/test_api_test_planning_services.py tests/quality/test_reporting_f5.py tests/quality/test_final_polish.py tests/project_scope/test_scoped_lookup_guard.py -q`
- DB migration applied: `d8r9s0t1o227`

### Full-Page UX Sign-off Artifact
- UAT checklist prepared: `docs/plans/TEST-CASE-FULL-PAGE-UAT-CHECKLIST.md`
