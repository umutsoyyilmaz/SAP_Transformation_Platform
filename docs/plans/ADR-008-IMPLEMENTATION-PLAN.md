# ADR-008 Implementation Plan
## Test Architecture Redesign — Full SAP Activate Traceability

**Status:** Execution Complete (Transition Mode)  
**Date:** 2026-02-18  
**Based on:** ADR-008-Test-Architecture-Redesign.md (Approved)  
**Estimated Effort:** 9 Steps, ~14 sub-tasks  
**Risk Level:** Medium (backward-compatible, additive-first)

---

## Executive Summary

ADR-008 introduces three core architectural changes:

| # | Decision | What Changes |
|---|----------|-------------|
| D1 | **L3 scope mandatory** for unit/sit/uat TCs | New `scope_resolution.py` service + endpoint validation |
| D2 | **TestCase ↔ Suite → N:M** | New `TestCaseSuiteLink` junction table + API endpoints |
| D3 | **Suite loses `suite_type`** | `purpose` + `tags` replace `suite_type` (deprecated, kept for compat) |

All changes are **additive first** — no existing functionality breaks until deprecation cleanup (Step 9).

---

## Live Progress Snapshot (2026-02-18)

### Completed
- Step 1 — `TestCaseSuiteLink` model + migration + backfill path.
- Step 2 — `scope_resolution.py` service added.
- Step 3 — `create_test_case` L3 resolve/validate + junction assignment.
- Step 4 — generation services updated (`generate_from_wricef`, `generate_from_process`).
- Step 5 — Suite N:M management endpoints added.
- Step 6 — L3 scope coverage endpoint added.
- Step 7 — Backfill utility added (`scripts/backfill_tc_scope.py`).
- Step 8 — Frontend updates shipped:
    - suite multi-select (Test Planning)
    - Scope wizard governance overrides
    - L3 coverage snapshot panel
- Step 9 — deprecation cleanup completed for active paths:
    - active write paths are `suite_ids`-first
    - purpose-first suite UX completed in primary planning screens
    - legacy `suite_type` rendered read-only in transition UI
    - compatibility path isolated for legacy `suite_id` clients
- Full-page Test Case UX rollout completed (modal view/edit replacement):
    - Phase 1: route + full-page master-detail foundation
    - Phase 2: tree grouping modes + inline metadata edit/save
    - Phase 3: step editor/reorder sync + execution history + defect linking + attachments + tab deep-link

### Verification Completed
- Focused API regression (suite/traceability/l3/scope coverage) passing.
- Phase-3 Playwright smoke passing (`e2e/tests/07-phase3-traceability-smoke.spec.ts`).
- Additional focused regression (`suite_ids` + `scope_coverage`) passing.
- Expanded Playwright smoke passing (`e2e/tests/06-fe-sprint3-smoke.spec.ts` + `e2e/tests/07-phase3-traceability-smoke.spec.ts`) — 18/18 passed.
- Expanded Playwright smoke re-validated after full-page rollout (`e2e/tests/06-fe-sprint3-smoke.spec.ts` + `e2e/tests/07-phase3-traceability-smoke.spec.ts`) — 18/18 passed.

### Next Actions
1. Track deprecation sunset milestones for `suite_id`/`suite_type` removal windows.
2. Keep transition compatibility tests green until sunset cutover.
3. Re-run release smoke on every RC cut.
4. Execute and sign off UAT checklist for full-page test case experience.
5. Capture UAT execution evidence in the execution record template.

See detailed cleanup tracker: `docs/plans/ADR-008-DEPRECATION-CLEANUP-CHECKLIST.md`.
See UAT checklist: `docs/plans/TEST-CASE-FULL-PAGE-UAT-CHECKLIST.md`.
See UAT execution record: `docs/plans/TEST-CASE-FULL-PAGE-UAT-EXECUTION-RECORD.md`.

---

## Pre-Implementation Audit — Current State

| Component | File | Current State | Impact |
|-----------|------|--------------|--------|
| `TestCase.suite_id` | `app/models/testing.py` L435 | Single FK → `test_suites.id` | **D2:** Deprecated, replaced by junction |
| `TestCase.process_level_id` | `app/models/testing.py` L430 | FK exists, **nullable** | **D1:** Auto-resolve + validate |
| `TestSuite.suite_type` | `app/models/testing.py` L934 | String(30), values: SIT/UAT/... | **D3:** Replace with `purpose` |
| `TestSuite.tags` | `app/models/testing.py` L948 | Already exists (Text) | **D3:** ✅ Already done |
| `create_test_case` | `app/blueprints/testing_bp.py` L359 | Accepts `suite_id`, `process_level_id` | **D1+D2:** Add resolve + validate + junction |
| `update_test_case` | `app/blueprints/testing_bp.py` L414 | `setattr` loop for all fields | **D2:** Add junction support |
| `generate_from_wricef` | `app/services/testing_service.py` L763 | Sets `suite_id`, **not** `process_level_id` | **D1:** Add L3 resolution |
| `generate_from_process` | `app/services/testing_service.py` L829 | Sets `suite_id` + `process_level_id` | **D2:** Add junction link |
| `import_from_suite` | `app/services/test_planning_service.py` L284 | Queries `TestCase.filter_by(suite_id=)` | **D2:** Must use junction query |
| Suite picker (FE) | `static/js/views/test_planning.js` L406 | Single `<select>` | **D2:** Multi-select chips |
| `scope_resolution.py` | — | **Does not exist** | **D1:** Brand new file |
| `TestCaseSuiteLink` model | — | **Does not exist** | **D2:** Brand new model |
| `ExploreRequirement.scope_item_id` | `app/models/explore/requirement.py` L331 | ✅ Exists (L3 FK) | Chain anchor — ready |
| `BacklogItem.explore_requirement_id` | `app/models/backlog.py` L155 | ✅ Exists | Chain link — ready |
| `ConfigItem.explore_requirement_id` | `app/models/backlog.py` L323 | ✅ Exists | Chain link — ready |
| `ProcessLevel.level/parent_id` | `app/models/explore/process.py` L70/L74 | ✅ Exists | Walk-up chain — ready |

---

## Step-by-Step Implementation Plan

### Step 1: TestCaseSuiteLink Model + DB Reset
**Risk:** None (purely additive)  
**Files:**
- `app/models/testing.py` — Add `TestCaseSuiteLink` class

**Tasks:**

#### 1.1 Add `TestCaseSuiteLink` model to testing.py
Insert **after** the `TestCycleSuite` class (~line 1080):

```python
class TestCaseSuiteLink(db.Model):
    """N:M junction: a test case can belong to multiple suites."""
    __tablename__ = "test_case_suite_links"
    __table_args__ = (
        db.UniqueConstraint("test_case_id", "suite_id", name="uq_tc_suite"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    test_case_id = db.Column(db.Integer, db.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    suite_id = db.Column(db.Integer, db.ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False, index=True)
    added_method = db.Column(db.String(30), default="manual")
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    test_case = db.relationship("TestCase", backref=db.backref("suite_links", lazy="dynamic"))
    suite = db.relationship("TestSuite", backref=db.backref("case_links", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "test_case_id": self.test_case_id,
            "suite_id": self.suite_id,
            "added_method": self.added_method,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "test_case_code": self.test_case.code if self.test_case else None,
            "test_case_title": self.test_case.title if self.test_case else None,
            "suite_name": self.suite.name if self.suite else None,
        }
```

#### 1.2 Add helper properties to `TestCase` model
Insert after `assigned_member` relationship (~line 504):

```python
@property
def suites(self):
    """All suites this TC belongs to (via N:M junction)."""
    return [link.suite for link in self.suite_links]

@property
def suite_ids(self):
    """List of suite IDs for serialization."""
    return [link.suite_id for link in self.suite_links]
```

#### 1.3 Update `TestCase.to_dict()` to include `suite_ids` and `suites`
In `to_dict()` (~line 515), add after `"suite_id"`:

```python
"suite_ids": self.suite_ids,
"suites": [
    {"id": link.suite_id, "name": link.suite.name if link.suite else None}
    for link in self.suite_links
],
```

#### 1.4 Update `TestCase.suite_id` column comment
Mark as deprecated:

```python
suite_id = db.Column(
    db.Integer, db.ForeignKey("test_suites.id", ondelete="SET NULL"),
    nullable=True, index=True,
    comment="DEPRECATED: Use test_case_suite_links. Kept for backward compat.",
)
```

#### 1.5 Add `purpose` field to `TestSuite` model
After `suite_type` (~line 934):

```python
purpose = db.Column(
    db.String(200), default="",
    comment="Free-text purpose: 'E2E order flow', 'Regression pack for pricing'",
)
```

#### 1.6 Add helper properties to `TestSuite`
After relationships:

```python
@property
def test_cases_via_links(self):
    return [link.test_case for link in self.case_links]

@property
def case_count_via_links(self):
    return self.case_links.count()
```

#### 1.7 Update `TestSuite.to_dict()`
Add `purpose` and `case_count_via_links`:

```python
"purpose": self.purpose,
"case_count": self.case_count_via_links,  # junction-based
```

#### 1.8 DB Reset
```bash
.venv/bin/python scripts/reset_db_from_models.py
.venv/bin/python scripts/seed_demo_data.py
```

**Verification:** Run `tests/test_api_testing.py` — all 207 tests must pass.

---

### Step 2: Scope Resolution Service (New File)
**Risk:** None (brand new file, no existing code depends on it)  
**Files:**
- `app/services/scope_resolution.py` — **CREATE**

**Tasks:**

#### 2.1 Create `app/services/scope_resolution.py`
Complete implementation per ADR §5.4:

- `resolve_l3_for_tc(tc_data: dict) -> str | None`
  - Resolution chain: explicit L3 → L4 walk-up → BacklogItem → ConfigItem → ExploreRequirement
- `validate_l3_for_layer(test_layer, process_level_id) -> (bool, str)`
  - unit/sit/uat → required
  - regression → recommended (warning only)
  - performance/cutover_rehearsal → optional
- `_ensure_l3(process_level_id)` — walk up ProcessLevel tree until level==3
- `_resolve_from_backlog_item(bi_id)` — BI → ExploreRequirement → scope_item_id
- `_resolve_from_config_item(ci_id)` — CI → ExploreRequirement → scope_item_id
- `_resolve_from_explore_requirement(req_id)` — scope_item_id | process_level_id | process_step fallback
- `_resolve_from_process_step(ps_id)` — ProcessStep → L4 → parent L3

**Dependency chain verified:**
```
BacklogItem.explore_requirement_id ✅ → ExploreRequirement.scope_item_id ✅ → ProcessLevel(level=3) ✅
ConfigItem.explore_requirement_id  ✅ → ExploreRequirement.scope_item_id ✅ → ProcessLevel(level=3) ✅
ExploreRequirement.process_step_id ✅ → ProcessStep.process_level_id    ✅ → ProcessLevel.parent_id ✅
```

**Verification:** Write and run unit tests (12 tests per ADR §7.1).

---

### Step 3: Update `create_test_case` Endpoint
**Risk:** Low — adds auto-resolve + validation (CREATE-only, not UPDATE)  
**Files:**
- `app/blueprints/testing_bp.py` L359-412

**Tasks:**

#### 3.1 Import scope resolution
At top of file:
```python
from app.services.scope_resolution import resolve_l3_for_tc, validate_l3_for_layer
```

#### 3.2 Add L3 auto-resolution before TC creation
After `data = request.get_json(...)`, before creating TestCase:

```python
test_layer = data.get("test_layer", "sit")

# ── L3 Scope Resolution ──
resolved_l3 = resolve_l3_for_tc(data)
if resolved_l3:
    data["process_level_id"] = resolved_l3

# ── L3 Validation (CREATE only) ──
is_valid, error_msg = validate_l3_for_layer(test_layer, data.get("process_level_id"))
if not is_valid:
    return jsonify({"error": error_msg, "resolution_attempted": True}), 400
```

#### 3.3 Add junction link creation after TC insert
After `db.session.add(tc)` + `db.session.flush()`:

```python
# ── Suite assignment via junction ──
suite_ids = data.get("suite_ids", [])
if data.get("suite_id"):
    suite_ids.append(data["suite_id"])  # backward compat

for sid in set(suite_ids):
    from app.models.testing import TestCaseSuiteLink
    link = TestCaseSuiteLink(
        test_case_id=tc.id, suite_id=sid,
        added_method="manual", tenant_id=tc.tenant_id,
    )
    db.session.add(link)
```

**Verification:** 
- Existing create tests still pass (they send `suite_id` → auto-converted to junction)
- New test: create TC with `suite_ids: [1, 2]` → both links exist
- New test: create unit TC without any L3 path → 400 error

---

### Step 4: Update `generate_from_wricef` and `generate_from_process`
**Risk:** Low — adds L3 resolve + junction links to generated TCs  
**Files:**
- `app/services/testing_service.py` L763-870

**Tasks:**

#### 4.1 `generate_from_wricef` — Add L3 resolution
At ~L780, after creating `tc_data`:

```python
from app.services.scope_resolution import resolve_l3_for_tc

tc_data = {
    "backlog_item_id": item.id if is_backlog else None,
    "config_item_id": item.id if not is_backlog else None,
}
resolved_l3 = resolve_l3_for_tc(tc_data)
```

In the `TestCase(...)` constructor, add:
```python
process_level_id=resolved_l3,
```

#### 4.2 `generate_from_wricef` — Replace `suite_id` with junction link
Remove `suite_id=suite.id` from TestCase constructor.
After `db.session.flush()` on the new TC:

```python
link = TestCaseSuiteLink(
    test_case_id=tc.id, suite_id=suite.id,
    added_method="auto_wricef", tenant_id=suite.tenant_id,
)
db.session.add(link)
```

#### 4.3 `generate_from_process` — Replace `suite_id` with junction link
Same pattern: remove `suite_id=suite.id`, add junction link with `added_method="auto_process"`.

**Verification:**
- Generate from WRICEF → TC gets `process_level_id` auto-resolved
- Generate from Process → TC gets junction link (not direct `suite_id`)
- Existing generation tests still pass

---

### Step 5: Suite N:M API Endpoints
**Risk:** None (new endpoints, old ones preserved)  
**Files:**
- `app/blueprints/testing_bp.py` — Add 4 new routes

**Tasks:**

#### 5.1 `GET /testing/suites/<suite_id>/cases` — List TCs in suite via junction
Returns `TestCaseSuiteLink` records with TC info.

#### 5.2 `POST /testing/suites/<suite_id>/cases` — Add TC to suite
Accepts `{ test_case_id, added_method?, notes? }`.
Returns 409 if link already exists (unique constraint).

#### 5.3 `DELETE /testing/suites/<suite_id>/cases/<tc_id>` — Remove TC from suite
Deletes the junction link. Returns 204.

#### 5.4 `GET /testing/catalog/<case_id>/suites` — List suites for a TC
Returns all suites a test case belongs to.

**Verification:** 7 integration tests per ADR §7.2.

---

### Step 6: L3 Scope Coverage Endpoint
**Risk:** None (new endpoint)  
**Files:**
- `app/blueprints/testing_bp.py` — Add 1 new route

**Tasks:**

#### 6.1 `GET /programs/<pid>/testing/scope-coverage/<l3_id>`
Full implementation per ADR §5.8:

1. Validate L3 exists and `level == 3`
2. Walk L4 children → ProcessSteps → find covering TCs
3. Walk ExploreRequirements → BacklogItems/ConfigItems → find covering TCs
4. Walk Interfaces linked to WRICEF items
5. Compute summary: total_tcs, passed, failed, not_run, pass_rate, readiness score
6. Return full JSON response

Also requires helper function `_get_latest_execution_result(test_cases)`.

**Verification:** 5 integration tests per ADR §7.3.

---

### Step 7: Backfill Script
**Risk:** Low (data migration, idempotent)  
**Files:**
- `scripts/backfill_tc_scope.py` — **CREATE**

**Tasks:**

#### 7.1 Create backfill management script
```python
"""Backfill process_level_id on existing TCs that lack it."""

def backfill_tc_scope():
    - Query TCs where process_level_id IS NULL and test_layer IN (unit, sit, uat)
    - For each: call resolve_l3_for_tc({backlog_item_id, config_item_id, explore_requirement_id})
    - If resolved: set tc.process_level_id
    - Report: {total_orphans, resolved, unresolved: [{id, code, title}]}
```

#### 7.2 Create suite_id → junction migration helper
```python
"""Migrate existing suite_id FK data into test_case_suite_links junction."""

def migrate_suite_links():
    - Query TCs where suite_id IS NOT NULL
    - For each: create TestCaseSuiteLink if not exists
    - Report: {migrated, skipped_duplicates}
```

**Verification:** Run on demo data, verify counts match.

---

### Step 8: Frontend Updates
**Risk:** Medium (UI changes, user-facing)  
**Files:**
- `static/js/views/test_planning.js` — Suite picker → multi-select + coverage hints

**Tasks:**

#### 8.1 Suite picker multi-select in `showCaseModal()`
Replace single `<select>` (L406) with multi-select chip component:

```html
<label>Suites</label>
<div id="tcSuiteChips" class="chip-select-container">
    <!-- chips rendered dynamically -->
</div>
```

Functions:
- `_renderSuiteChips(selectedIds)` — render removable chip per selected suite
- `_showSuiteDropdown()` — searchable dropdown to add suites
- Editing a TC: load existing `suite_ids` from response

#### 8.2 `saveCase()` payload update
Change from:
```javascript
suite_id: parseInt(...) || null,
```
To:
```javascript
suite_ids: _getSelectedSuiteIds(),
suite_id: _getSelectedSuiteIds()[0] || null,  // backward compat
```

#### 8.3 Test catalog table — show multi-suite badges
Where suite name is displayed in the table row, show `suites[]` badges instead of single suite name.

#### 8.4 Import from suite — update `test_planning_service.import_from_suite()`
Change query from:
```python
TestCase.query.filter_by(suite_id=suite_id)
```
To:
```python
tc_ids = [link.test_case_id for link in TestCaseSuiteLink.query.filter_by(suite_id=suite_id)]
TestCase.query.filter(TestCase.id.in_(tc_ids))
```

**Verification:** Manual browser testing + E2E smoke test.

---

### Step 9: Deprecation Cleanup
**Risk:** Low (can be deferred to future sprint)  
**Files:**
- `app/models/testing.py` — Mark `suite_type` officially deprecated
- `app/blueprints/testing_bp.py` — Remove `suite_id` writes from new code paths
- `tests/test_api_testing.py` — Add deprecation-aware assertions

**Tasks:**

#### 9.1 Log deprecation warnings
When `suite_id` is sent in create/update requests:
```python
import warnings
if data.get("suite_id"):
    warnings.warn("suite_id is deprecated. Use suite_ids[] instead.", DeprecationWarning)
```

#### 9.2 Mark `suite_type` → `purpose` migration complete
In TestSuite creation endpoint, if `suite_type` is sent but `purpose` is not, auto-copy:
```python
if data.get("suite_type") and not data.get("purpose"):
    data["purpose"] = data["suite_type"]
```

#### 9.3 Update delete_test_suite endpoint
Currently at L805, unlinks TCs by setting `suite_id=NULL`. Add junction cleanup:
```python
TestCaseSuiteLink.query.filter_by(suite_id=suite_id).delete()
```

---

## Test Matrix

### New Tests to Write

| Test File | Class | Test Count | Covers |
|-----------|-------|-----------|--------|
| `tests/test_scope_resolution.py` | `TestScopeResolution` | 12 | D1: L3 resolution chain (§7.1) |
| `tests/test_api_testing.py` | `TestSuiteNM` | 7 | D2: N:M junction CRUD (§7.2) |
| `tests/test_api_testing.py` | `TestScopeCoverage` | 5 | D1: L3 coverage endpoint (§7.3) |
| `tests/test_api_testing.py` | `TestL3Validation` | 4 | D1: CREATE validation |
| **Total** | | **28** | |

### Existing Tests — Expected Impact

| Test File | Current Count | Expected Breakage | Fix |
|-----------|--------------|------------------|-----|
| `tests/test_api_testing.py` | 207 | ~5 (create TC tests that don't provide L3) | Add `process_level_id` to test fixtures, or mark test_layer as "performance" |
| `tests/test_demo_flow.py` | varies | ~2 (generate tests) | Update to check junction links |
| All other test files | 2,151 | 0 | No impact |

---

## Dependency Graph

```
Step 1 (Model + DB)
  ↓
Step 2 (scope_resolution.py)     ← independent of Step 1
  ↓
Step 3 (create_test_case) ← depends on Step 1 + Step 2
  ↓
Step 4 (generate services) ← depends on Step 1 + Step 2
  ↓
Step 5 (Suite N:M API) ← depends on Step 1
  ↓
Step 6 (Scope coverage) ← depends on Step 1 + Step 2
  ↓
Step 7 (Backfill script) ← depends on Step 1 + Step 2
  ↓
Step 8 (Frontend) ← depends on Step 5
  ↓
Step 9 (Cleanup) ← depends on all above
```

**Parallelizable:** Steps 1 + 2 can be done in sequence in one commit. Steps 5 + 6 can be done together.

---

## Recommended Commit Strategy

| Commit | Steps | Message | Test Count |
|--------|-------|---------|-----------|
| C1 | 1 + 2 | `feat(testing): ADR-008 — TestCaseSuiteLink model + scope_resolution service` | 207 + 12 |
| C2 | 3 + 4 | `feat(testing): ADR-008 — L3 auto-resolve in create_test_case + generators` | ~220 |
| C3 | 5 + 6 | `feat(testing): ADR-008 — Suite N:M endpoints + L3 scope coverage` | ~235 |
| C4 | 7 | `feat(testing): ADR-008 — Backfill script for TC scope + suite migration` | ~235 |
| C5 | 8 | `feat(testing): ADR-008 — Frontend multi-suite picker + coverage hints` | ~235 |
| C6 | 9 | `chore(testing): ADR-008 — Deprecation warnings + cleanup` | ~240 |

---

## Rollback Plan

Each step is independently reversible:

| Step | Rollback Action |
|------|----------------|
| 1 | Drop `test_case_suite_links` table, remove `purpose` column |
| 2 | Delete `scope_resolution.py` |
| 3 | Revert `create_test_case` to pre-ADR state |
| 4 | Revert `generate_from_wricef` / `generate_from_process` |
| 5 | Remove new endpoints |
| 6 | Remove scope-coverage endpoint |
| 7 | Delete backfill script |
| 8 | Revert JS changes |
| 9 | Remove deprecation code |

Since we use `reset_db_from_models.py` (not Alembic migrations) in dev, rollback is simply a git revert + DB reset.

---

## Open Questions / Decisions Before Starting

| # | Question | ADR Default | Decision Needed? |
|---|----------|-------------|-----------------|
| Q1 | L3 validation on CREATE only or CREATE + UPDATE? | CREATE only (§10 Risk 1) | Recommend CREATE only initially |
| Q2 | Remove `suite_type` column or keep indefinitely? | Keep for transition (§9) | Recommend keep for 1 sprint, then remove |
| Q3 | Generate endpoints: continue setting `suite_id` too, or junction only? | Junction only (§5.6) | Recommend dual-write for 1 sprint |
| Q4 | Frontend: multi-select immediately or progressive enhancement? | Progressive (§10 Risk 4) | Recommend full multi-select |

---

## Success Criteria

- [ ] `TestCaseSuiteLink` model exists and is functional
- [ ] A test case can belong to 2+ suites simultaneously
- [ ] `create_test_case` auto-resolves L3 from WRICEF/Config chain
- [ ] Unit/SIT/UAT TCs without L3 are rejected at CREATE (with helpful error)
- [ ] `generate_from_wricef` sets `process_level_id` via scope resolution
- [ ] L3 scope coverage endpoint returns actionable coverage data
- [ ] Existing 207 testing API tests still pass (minimal fixture changes)
- [ ] 28+ new tests all pass
- [ ] Frontend suite picker supports multi-select
- [ ] Demo data seeder works with new model

---

*Plan created: 2026-02-18 | Ready for Step 1 execution*
