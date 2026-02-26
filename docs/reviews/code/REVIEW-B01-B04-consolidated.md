# Code Review — FDD-B01 through FDD-B04 (Consolidated)

**Reviewer:** GitHub Copilot (Senior Engineer role)
**Date:** 2025-07-28
**Scope:** FDD-B01 Requirement Model Consolidation, FDD-B02 Discover Minimum Viable, FDD-B03 Run/Hypercare Incident Management, FDD-B04 Formal Sign-off Workflow
**Sources examined:** FDD spec files, implementation code, test files

---

## Overall Verdict Summary

| FDD | Title | Verdict |
|-----|-------|---------|
| B01 | Requirement Model Consolidation | 🟡 **REQUEST CHANGES** — Missing endpoint tests, legacy-redirect test replaced incorrectly |
| B02 | Discover Minimum Viable | ✅ **APPROVE** — All criteria met, test count exceeds requirements |
| B03 | Run/Hypercare Incident Management | 🟡 **REQUEST CHANGES** — Legacy Query API in 3 helpers, severity not validated |
| B04 | Formal Sign-off Workflow | 🟡 **REQUEST CHANGES** — `pending_signoffs` logic bug, timezone-naive column, `request` in service |

---

## FDD-B01 — Requirement Model Consolidation

**Files reviewed:**
- [app/models/explore/requirement.py](../../app/models/explore/requirement.py) (lines 400–550)
- [tests/test_requirement_consolidation.py](../../tests/test_requirement_consolidation.py)

### ✅ PASS — New Fields Correctly Implemented

All 6 B01 consolidation fields are present in `ExploreRequirement` (lines 406–443):

```python
requirement_type  — nullable=True ✅
moscow_priority   — nullable=True ✅
source            — nullable=True ✅
parent_id         — nullable=True, String(36) FK to explore_requirements.id ✅
external_id       — nullable=True, index=True ✅
legacy_requirement_id — nullable=True, index=True ✅
```

**Notable correction:** The FDD draft spec incorrectly typed `parent_id` as `Integer`. The implementation correctly uses `String(36)` to match the UUID primary key of `explore_requirements`. Self-referential ORM relationship with `children` backref is properly defined.

### ✅ PASS — Tests (11 of 10 required)

`tests/test_requirement_consolidation.py` contains **11 tests**, exceeding the FDD's required 10. All 10 FDD-required test *scenarios* are covered (with minor name variations for `source` and `moscow-summary` tests). A bonus test `test_explore_requirement_external_id_indexed` is a value-add.

### 🟡 WARNING — FDD-Required HTTP Endpoint Tests Missing

**Finding:** FDD-B01 §8 specifies two tests that verify HTTP-level behaviour:
- `test_legacy_requirement_returns_404_after_deprecation`
- `test_legacy_redirect_points_to_explore_requirements`

The implementation replaced these with `test_legacy_requirement_write_block_raises_runtime_error` — an ORM-level test, not an HTTP test. If the legacy requirements *endpoint* still exists in the blueprint but forwards to `explore_requirements`, there is no test confirming the 301/404 HTTP response code.

**Action required:** Search all blueprint files for any `/requirements` route that predates B01 and confirm it either returns 404 or 301. If the legacy endpoint still exists unguarded, add an HTTP-level test.

### 🟡 WARNING — API Endpoints Not Verified

FDD-B01 §5 specifies two new endpoints:
- `GET /api/v1/projects/<id>/requirements/<req_id>/children`
- `GET /api/v1/requirements/moscow-summary`

The service model supports these (children relationship and moscow_priority field exist), but no blueprint code was found containing these routes during this review. If these endpoints are not yet implemented, the FDD acceptance criteria for the API layer are **not met**.

**Action required:** Locate or create the blueprint handlers for these two endpoints.

### 🔵 NITPICK — `tenant_id` is `nullable=True` with `SET NULL`

`ExploreRequirement.tenant_id` uses `ondelete="SET NULL"`, consistent with other models in this codebase. However this means rows can become tenant-orphaned if a Tenant is deleted while requirements exist. The gate queries in service code all filter by `tenant_id`, so orphaned rows silently disappear from all tenant views — which is probably the intended behaviour, but it is risk-worthy to document.

---

## FDD-B02 — Discover Minimum Viable (Project Charter)

**Files reviewed:**
- [app/models/program.py](../../app/models/program.py) (lines 490–800)
- [app/services/discover_service.py](../../app/services/discover_service.py) (462 lines, fully read)
- [tests/test_discover.py](../../tests/test_discover.py)

### ✅ PASS — All Models Correct

`ProjectCharter`, `SystemLandscape`, and `ScopeAssessment` are all implemented in `program.py` with explicit `__tablename__`, length-bounded String columns, correct composite indexes, and docstrings explaining lifecycle.

**FDD reviewer concern addressed:** All three Discover models have `tenant_id` present with index, and the service enforces tenant scope on every query. The concern that `SystemLandscape` was raw `db.Model` has been addressed — while it does extend `db.Model` (not `TenantModel`), every service function uses `.where(SystemLandscape.tenant_id == tenant_id)` consistently.

`ScopeAssessment` has a composite `UniqueConstraint("program_id", "tenant_id", "sap_module")` preventing double-entry — the FDD reviewer's concern about double-entry risk is mitigated.

### ✅ PASS — Service Layer Complete

`discover_service.py` implements all required functions:
- `get_charter`, `create_or_update_charter` (with approved-charter lock), `approve_charter`
- `list_system_landscapes`, `add_system_landscape`, `update_system_landscape`, `delete_system_landscape`
- `list_scope_assessments`, `save_scope_assessment` (upsert), `delete_scope_assessment`
- `get_discover_gate_status` (3-criteria check, all correct)

All functions accept `tenant_id` as first parameter. No `g` access anywhere. All commits in service layer. SQLAlchemy 2.0 `select()` style used throughout.

### ✅ PASS — Gate Check Logic Correct

```python
1. charter.status == "approved"          # ✅
2. SystemLandscape count >= 1 (is_active)  # ✅
3. ScopeAssessment count >= 3              # ✅
```

The gate correctly filters `SystemLandscape` by `is_active=True`, which the FDD spec did not explicitly clarify but is the correct business interpretation.

### ✅ PASS — Tests (15 of 10 required)

`tests/test_discover.py` contains **15 tests**, well exceeding the 10 required. All FDD-required scenarios plus bonus validation tests (400 on missing fields, 404 for nonexistent programs, 422 for programs without tenant).

### 🟡 WARNING — `PhaseGate` Integration Not Implemented

FDD-B02 reviewer audit noted that `PhaseGate` integration is not defined. The `get_discover_gate_status` service returns the gate result, but there is no hook into a `gate_service.py` or `PhaseGate` model transition. This means the Discover Gate status is **informational only** — it cannot block progression to the Prepare phase programmatically.

This is an accepted known gap (noted in FDD) but should be tracked as a dependency for the Prepare gate feature.

---

## FDD-B03 — Run/Hypercare Incident Management

**Files reviewed:**
- [app/services/hypercare_service.py](../../app/services/hypercare_service.py) (800 lines, fully read)
- [tests/test_hypercare_service.py](../../tests/test_hypercare_service.py) (390 lines, fully read)

### ✅ PASS — SLA Auto-Calculation Correct

`create_incident` correctly auto-calculates both SLA deadlines:

```python
sla_response_deadline = now + timedelta(minutes=response_min)
sla_resolution_deadline = now + timedelta(minutes=resolution_min)
```

`_get_sla_targets` reads from `HypercareSLA` table first, falling back to `_SLA_DEFAULTS` (P1: 15/240 min, P2: 30/480, P3: 240/1440, P4: 480/2400). The P1 resolution default of 240 minutes = 4 hours, matching FDD spec exactly. ✅

### ✅ PASS — All 11 Tests Present

All 11 FDD-required test function names are present in `test_hypercare_service.py` with minor wording variations (`test_first_response_after_sla_deadline_sets_breach_flag_true` vs FDD's `test_first_response_after_sla_sets_breach_flag_true`).

### ✅ PASS — Tenant Isolation Pattern Correct

`_get_plan(tenant_id, plan_id)` is called at the start of every public function, preventing cross-tenant access at the service boundary. `_get_incident` also triple-scopes: `incident_id + plan_id + tenant_id`.

### ✅ PASS — `PostGoliveChangeRequest` Uses `programs.id` (Not `projects.id`)

The FDD draft incorrectly wrote `projects.id`. The model and service correctly use `program_id → programs.id`. ✅

### 🔴 BLOCKER — Legacy Query API in 3 Helper Functions

The following three helpers use the deprecated SQLAlchemy 1.x `Model.query.filter_by()` API, violating the project's coding standard (Standards §6, SQLAlchemy 2.0 style required):

**`_get_sla_targets` ([hypercare_service.py line 97](../../app/services/hypercare_service.py#L97)):**
```python
row = HypercareSLA.query.filter_by(cutover_plan_id=plan_id, severity=severity).first()
```

**`_next_incident_code` ([hypercare_service.py line 104](../../app/services/hypercare_service.py#L104)):**
```python
count = HypercareIncident.query.filter_by(cutover_plan_id=plan_id).count()
```

**`_next_cr_number` ([hypercare_service.py line 109](../../app/services/hypercare_service.py#L109)):**
```python
count = PostGoliveChangeRequest.query.filter_by(program_id=program_id).count()
```

These must be rewritten to SQLAlchemy 2.0 `select()` style before merge:

```python
# _get_sla_targets — correct form
stmt = select(HypercareSLA).where(
    HypercareSLA.cutover_plan_id == plan_id,
    HypercareSLA.severity == severity,
)
row = db.session.execute(stmt).scalar_one_or_none()

# _next_incident_code — correct form
count = db.session.execute(
    select(func.count(HypercareIncident.id))
    .where(HypercareIncident.cutover_plan_id == plan_id)
).scalar()
return f"INC-{(count + 1):03d}"
```

### 🟡 WARNING — Severity Input Not Validated

`create_incident` accepts any `severity` string from the caller (line 171: `severity = data.get("severity", "P3")`). If an invalid value is passed (e.g. `"critical"`, `"high"`), `_get_sla_targets` silently falls back to default SLA values (480/2400 min) and the invalid severity is persisted to DB. There is no 400 response to the client.

```python
# Required: validate severity at entry
VALID_SEVERITIES = {"P1", "P2", "P3", "P4"}
if severity not in VALID_SEVERITIES:
    raise ValueError(f"severity must be one of {VALID_SEVERITIES}")
```

This is especially important given the FDD's own BLOCKER note about `Defect` model severity misalignment — using inconsistent values in DB will make cross-model reporting impossible.

### 🟡 WARNING — `_next_incident_code` / `_next_cr_number` Race Condition

The sequential code generation pattern (count+1) is not race-safe under concurrent requests. Two simultaneous incident creations on the same plan can produce duplicate codes (`INC-005`, `INC-005`). Recommended fix: add a `UNIQUE` constraint on `(cutover_plan_id, code)` or use a DB sequence. Acceptable as a sprint-B known limitation but must be documented.

---

## FDD-B04 — Formal Sign-off Workflow

**Files reviewed:**
- [app/models/signoff.py](../../app/models/signoff.py) (159 lines, fully read)
- [app/services/signoff_service.py](../../app/services/signoff_service.py) (396 lines, fully read)
- [tests/test_signoff_workflow.py](../../tests/test_signoff_workflow.py)

### ✅ PASS — Critical Reviewer Fix A1 Applied

`SignoffRecord.tenant_id` is correctly marked `nullable=False` with `ondelete="CASCADE"`. The FDD draft had `nullable=True` which would have been an audit/compliance breach. Confirmed fixed:

```python
tenant_id = db.Column(
    db.Integer,
    db.ForeignKey("tenants.id", ondelete="CASCADE"),
    nullable=False,   # A1: reviewer fix applied ✅
    index=True,
)
```

### ✅ PASS — Critical Reviewer Fix A2 Applied

`approver_name_snapshot` field exists on the model and `_snapshot_approver_name(approver_id)` is called in `approve_entity` and `revoke_approval`. Name is captured at sign-off time, surviving User row deletion. ✅

### ✅ PASS — Critical Reviewer Fix A3 Applied

Self-approval guard is in `signoff_service.py::approve_entity`, not in any blueprint. Guard correctly returns `(None, {"error": ..., "status": 422})` without raising, so the blueprint pattern is consistent with the (result, error) tuple contract. ✅

### ✅ PASS — Append-Only Guarantee

No `db.session.delete()` call exists anywhere on `SignoffRecord`. No UPDATE operations on existing records. Pure append-only. `is_entity_approved()` is exported per reviewer fix A4. ✅

### ✅ PASS — All 10 FDD-Required Tests Present

`tests/test_signoff_workflow.py` contains all 10 required test names matching the FDD-B04 §8 spec exactly.

### 🔴 BLOCKER — `get_pending_signoffs` Logic Bug

**Location:** [signoff_service.py](../../app/services/signoff_service.py) — `get_pending_signoffs` function.

The function's docstring states "Pending = latest action is NOT approved". However the query filters `action != "approved"`, which includes `override_approved` records. An artifact that was **override-approved** is a valid approved state and must NOT appear in the pending queue.

```python
# Current (WRONG):
stmt = (
    select(SignoffRecord)
    .join(latest_sub, SignoffRecord.id == latest_sub.c.max_id)
    .where(SignoffRecord.action != "approved")  # ❌ includes override_approved
)

# Correct:
APPROVED_ACTIONS = {"approved", "override_approved"}
stmt = (
    select(SignoffRecord)
    .join(latest_sub, SignoffRecord.id == latest_sub.c.max_id)
    .where(SignoffRecord.action.notin_(APPROVED_ACTIONS))  # ✅
)
```

This would cause dashboard consumers (`get_signoff_summary`) to incorrectly show override-approved artifacts as needing re-approval, potentially triggering false workflow alerts.

**Note:** The summary function in `get_signoff_summary` does count `override_approved` toward the `approved` bucket: `bucket["approved"] += cnt`. This is correct. But `get_pending_signoffs` being inconsistent with `get_signoff_summary` creates contradictory API responses.

### 🔴 BLOCKER — `created_at` Timezone-Naive Column

**Location:** [signoff.py line 122](../../app/models/signoff.py#L122)

```python
created_at = db.Column(
    db.DateTime,          # ❌ missing timezone=True
    nullable=False,
    default=lambda: datetime.now(timezone.utc),
)
```

The default produces a timezone-aware datetime but the column is `db.DateTime` (no timezone). In PostgreSQL this strips timezone info on write. The `SignoffRecord` is compliance/audit data — timezone ambiguity on the created_at timestamp is a **SOX/GDPR audit risk**.

```python
# Correct:
created_at = db.Column(
    db.DateTime(timezone=True),  # ✅
    nullable=False,
    default=lambda: datetime.now(timezone.utc),
)
```

A migration must be generated alongside this fix.

### 🟡 WARNING — `request` Accessed in Service Layer

**Location:** [signoff_service.py](../../app/services/signoff_service.py) — `_get_client_ip()`

```python
from flask import request  # Imported in service module

def _get_client_ip() -> str | None:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    ...
```

Accessing Flask's `request` proxy in the service layer violates the architecture rule: "Service NEVER accesses Flask `g` directly". The same principle applies to `request`. This makes the service untestable outside a Flask request context.

**Recommended fix:** Pass the IP address as a parameter from the blueprint layer (which legitimately owns HTTP context):

```python
# Blueprint:
client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr
result, err = signoff_service.approve_entity(..., client_ip=client_ip)

# Service:
def approve_entity(..., client_ip: str | None = None) -> ...:
    record = SignoffRecord(..., approver_ip=client_ip)
```

This is a 🟡 WARNING (not BLOCKER) because the functionality is correct and it does not affect tenant isolation — but it will cause `AttributeError: Working outside of request context` if any test calls the service directly without a Flask context.

---

## Cross-Cutting Observations

### N+1 Risk in `hypercare_service.get_incident_metrics`

`get_incident_metrics` fetches all incidents for a plan and iterates in Python. For plans with hundreds of incidents this is acceptable. However if incidents grow to thousands, this becomes a performance issue. Consider adding DB-level aggregation with `func.count` / `func.avg`. File a backlog item.

### Missing Alembic Migrations

No new migration files were found for:
- `signoff_records` table (B04)
- `project_charters`, `system_landscapes`, `scope_assessments` tables (B02)
- New columns on `explore_requirements` (B01)

If these tables/columns were added directly (via `db.create_all()` in dev) rather than through `flask db migrate`, the migration history is incomplete. This will cause upgrade failures in any environment that runs Alembic. Verify migration files exist; if not, generate them before sprint close.

---

## Required Actions Before Merge

| Priority | Finding | FDD | Action |
|----------|---------|-----|--------|
| 🔴 BLOCKER | Legacy `Model.query.filter_by()` in 3 B03 helpers | B03 | Rewrite to SQLAlchemy 2.0 `select()` |
| 🔴 BLOCKER | `get_pending_signoffs` includes `override_approved` in pending | B04 | Change filter to `notin_({"approved", "override_approved"})` |
| 🔴 BLOCKER | `SignoffRecord.created_at` timezone-naive | B04 | Change to `db.DateTime(timezone=True)`, add migration |
| 🟡 WARNING | B01 HTTP-level legacy redirect/404 test missing | B01 | Add HTTP endpoint test or confirm endpoint removed |
| 🟡 WARNING | B01 `/children` and `/moscow-summary` endpoints not confirmed | B01 | Locate or implement blueprint routes |
| 🟡 WARNING | B03 `create_incident` accepts unvalidated severity strings | B03 | Add enum check, return 400 on invalid value |
| 🟡 WARNING | B03 sequential code generation race condition | B03 | Add `UNIQUE` constraint + document limitation |
| 🟡 WARNING | B04 `_get_client_ip()` accesses Flask `request` in service | B04 | Pass IP from blueprint as parameter |
| 🟡 WARNING | B02 PhaseGate integration missing (known gap) | B02 | Track as backlog item for Prepare gate feature |
| 🔵 NITPICK | All Discover models use `db.Model` not `TenantModel` | B02 | Acceptable; document service-enforced scoping pattern |
| 🔵 NITPICK | Missing Alembic migrations for new tables/columns | ALL | Verify `flask db migrate` was run; regenerate if missing |
