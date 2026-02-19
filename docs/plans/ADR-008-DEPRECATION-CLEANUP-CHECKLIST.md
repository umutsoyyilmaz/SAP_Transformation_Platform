# ADR-008 Deprecation Cleanup Checklist
## suite_id / suite_type Transition Guardrail

**Status:** Cleanup Complete (Transition Mode)  
**Date:** 2026-02-18  
**Owner:** Platform Team

---

## 1) Current Contract (Transition Window)

- `TestCase.suite_id` is **deprecated** but still readable for backward compatibility.
- `TestCase.suite_ids` + `TestCaseSuiteLink` is the **source of truth**.
- `TestSuite.suite_type` is **deprecated**; `purpose` + `tags` is the target model.
- API accepts legacy `suite_id` payloads, but new UI/API flows should send `suite_ids`.

---

## 2) Completed

- [x] N:M junction model added (`test_case_suite_links`).
- [x] Migration added + backfill (`suite_id -> junction`).
- [x] New/active frontend path sends `suite_ids` (Test Planning modal).
- [x] `create_test_case` / `update_test_case` use junction sync for suite membership.
- [x] Auto-generation flows (`generate_from_wricef`, `generate_from_process`) stopped writing `suite_id` directly.
- [x] Clone flow now links suites via junction as primary path.

---

## 3) Remaining Cleanup

### 3.1 Backend
- [x] Remove direct `TestCase.query.filter_by(suite_id=...)` from non-legacy service paths.
- [x] Keep legacy mirror writes only when request is legacy-only (`suite_id` without `suite_ids`).
- [x] Add guard test: new endpoints must not require `suite_id`.

### 3.2 Frontend
- [x] Remove fallback reads `tc.suite_id` after one release window.
- [x] Keep only `suite_ids` selection/state in UI models.
- [x] Replace catalog row modal detail path with full-page test case detail view.
- [x] Keep modal as quick-create/legacy fallback only.

### 3.3 API Contract
- [x] Mark `suite_id` as deprecated in docs/Swagger blocks.
- [x] Add sunset target date for `suite_id` write support.

**Sunset Target**
- `suite_id` write support deprecation notice active: **2026-02-18**
- planned write-disable target (API): **2026-06-30**
- planned compatibility removal review: **2026-09-30**

### 3.4 Suite Type Cleanup
- [x] Replace remaining “type-first” labels with `purpose` in list/detail UI where applicable.
- [x] Keep `suite_type` read-only for transition until deprecation window closes.

---

## 4) Exit Criteria (Cleanup Done)

- [x] All active write paths use `suite_ids` + junction only.
- [x] Legacy `suite_id` accepted only in compatibility layer (no core business logic dependency).
- [x] Tests cover both: legacy compatibility and modern contract.
- [x] Deprecation notice + removal release target documented.

---

## 5) Recommended Sunset Sequence

1. **Release N:** keep compatibility, emit deprecation warnings.
2. **Release N+1:** remove `suite_id` from frontend payloads entirely.
3. **Release N+2:** disable `suite_id` writes in API (reads still available).
4. **Release N+3:** remove model-level operational dependency; keep migration note in docs.

### Planned Timeline (Calendar)
- **R2026.02 (done):** Deprecation warnings + modern `suite_ids` path in active flows
- **R2026.06 (target):** Disable legacy `suite_id` writes in main test case endpoints
- **R2026.09 (target):** Review and remove remaining compatibility branches where safe

---

## 6) Latest Validation Evidence (2026-02-18)

- Backend regression pass: `pytest tests/test_api_testing.py tests/test_api_test_planning_services.py tests/test_scope_resolution.py -q`
- Focused API contract pass: `pytest tests/test_api_testing.py -k "suite_ids or scope_coverage" -q`
- E2E smoke pass: `npm run test:e2e -- tests/06-fe-sprint3-smoke.spec.ts tests/07-phase3-traceability-smoke.spec.ts`
- Result: **18/18 Playwright tests passed**, ADR-008 transition behavior validated in UI + API paths.

### Full-Page UX Sign-off Artifact
- UAT checklist prepared: `docs/plans/TEST-CASE-FULL-PAGE-UAT-CHECKLIST.md`
