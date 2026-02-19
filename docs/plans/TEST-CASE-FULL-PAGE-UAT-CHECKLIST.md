# Test Case Full-Page UAT Checklist
## Perga Master-Detail Test Case Experience

**Date:** 2026-02-18  
**Owner:** QA / Product / Delivery  
**Scope:** Full-page test case detail rollout (modal view/edit replacement)

Execution record template: `docs/plans/TEST-CASE-FULL-PAGE-UAT-EXECUTION-RECORD.md`

---

## 1) Entry Criteria

- [ ] Active program is selected.
- [ ] At least 1 test case exists in catalog.
- [ ] At least 1 suite exists.
- [ ] User has permission to view/edit test cases.

---

## 2) Navigation & Layout

- [ ] Clicking a catalog row opens full-page test case detail (not edit modal).
- [ ] Header shows code + title + breadcrumb-like context.
- [ ] Left panel renders master tree and selected test case highlight.
- [ ] Tree mode switch works: By Suite / By L3 / By Layer.
- [ ] Back button returns to Test Planning catalog.

---

## 3) Tabs Coverage

### 3.1 Details
- [ ] Details tab renders description/preconditions/metadata.
- [ ] Edit mode opens inline form fields.
- [ ] Save persists metadata updates.
- [ ] Suite membership changes persist via `suite_ids`.

### 3.2 Test Script
- [ ] Existing steps render in order.
- [ ] Add step works in edit mode.
- [ ] Reorder (up/down) works in edit mode.
- [ ] Remove step works in edit mode.
- [ ] Save syncs step CRUD to backend.

### 3.3 Traceability
- [ ] Derived chain summary renders.
- [ ] Dependency badges render (blocked_by / blocks).
- [ ] Performance records summary renders.

### 3.4 Executions
- [ ] Execution history table renders when cycle data exists.
- [ ] Rows include result/tester/date/cycle context.
- [ ] Evidence links open in new tab.

### 3.5 Defects
- [ ] Linked defects list renders.
- [ ] Link existing defect to current test case works.
- [ ] Unlink defect from current test case works.

### 3.6 Attachments
- [ ] Attachments tab aggregates evidence URLs from executions/runs/perf.
- [ ] URLs are clickable and open safely.

### 3.7 History
- [ ] Audit snapshot renders created/updated metadata.
- [ ] Recent activity block renders from execution events.

---

## 4) URL / Deep-Link

- [ ] URL hash updates as `#test-case-detail/{id}/tab/{tab}`.
- [ ] Refresh on a tab deep-link keeps the same tab open.
- [ ] Direct navigation with case+tab hash opens expected view.

---

## 5) Backward Compatibility

- [ ] `+ New Test Case` still uses quick-create modal.
- [ ] Legacy editor button opens modal editor for fallback.
- [ ] No regression on `suite_ids`-first payload contract.

---

## 6) Regression Smoke

- [ ] `tests/07-phase3-traceability-smoke.spec.ts` passes.
- [ ] `tests/06-fe-sprint3-smoke.spec.ts` + `tests/07-phase3-traceability-smoke.spec.ts` pass together.

---

## 7) UAT Sign-off

- Product: [ ]  
- QA: [ ]  
- Delivery Lead: [ ]  
- Date: [ ]
