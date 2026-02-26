# Cutover Module Detailed Review (2026-02-23)

## Scope
- Backend API: `app/blueprints/cutover_bp.py`
- Service layer: `app/services/cutover_service.py`
- Domain models: `app/models/cutover.py`
- Frontend view: `static/js/views/cutover.js`
- Existing tests: `tests/test_api_cutover.py`, `tests/test_cutover_warroom.py`

## Findings (ordered by severity)

### 1. [Critical] Hypercare incident creation is broken (DB integrity error)
- Evidence:
  - `HypercareIncident.tenant_id` is mandatory (`nullable=False`): `app/models/cutover.py:1000`.
  - Incident creation does not set `tenant_id`: `app/services/cutover_service.py:1107`.
- Runtime proof:
  - Command run: `PYTHONPATH=. pytest -q tests/test_api_cutover.py::TestHypercareIncident::test_create`
  - Result: `sqlite3.IntegrityError: NOT NULL constraint failed: hypercare_incidents.tenant_id`
- Impact:
  - `POST /api/v1/cutover/plans/<id>/incidents` fails at runtime in real environments.

### 2. [Critical] Tenant propagation is missing in core create flows; war-room endpoints can’t operate on API-created data
- Evidence:
  - These create methods do not set `tenant_id` even though models have tenant fields:
    - `create_plan`: `app/services/cutover_service.py:586`
    - `create_scope_item`: `app/services/cutover_service.py:686`
    - `create_task`: `app/services/cutover_service.py:768`
    - `create_rehearsal`: `app/services/cutover_service.py:893`
    - `create_go_no_go`: `app/services/cutover_service.py:982`
    - `create_sla_target`: `app/services/cutover_service.py:1196`
  - War-room flows strictly filter by tenant/program:
    - `start_cutover_clock`: `app/services/cutover_service.py:1293`
    - `_get_task_for_tenant`: `app/services/cutover_service.py:1807`
    - live-status task query: `app/services/cutover_service.py:1550`
- Impact:
  - Records created from standard cutover endpoints can be invisible to war-room operations due to `tenant_id=NULL`.
  - Causes “not found for tenant …” errors even for existing business data.

### 3. [High] IDOR / cross-tenant access risk in non-war-room cutover endpoints
- Evidence:
  - Most CRUD endpoints fetch by raw PK via shared helper:
    - Usage example: `app/blueprints/cutover_bp.py:75`
    - Helper implementation uses `db.session.get(model, pk)` only: `app/utils/helpers.py:33`
  - No tenant/program ownership check in these CRUD routes.
- Impact:
  - If an attacker can guess IDs and auth middleware does not fully isolate at DB layer, records from other tenants/programs may be read/updated/deleted.

### 4. [High] API error handling is inconsistent; DB failures can leak as 500 stack errors
- Evidence:
  - Cutover blueprint methods call service commit paths directly, no `db_commit_or_error` wrapper in this module.
  - Concrete failing path already observed in finding #1 at `app/blueprints/cutover_bp.py:501`.
- Impact:
  - Constraint violations surface as unhandled 500 instead of controlled 4xx/5xx API contract.

### 5. [Medium] War-room live-status returns an always-null planned duration field
- Evidence:
  - Response uses `plan.planned_duration_minutes` via `hasattr(...)`: `app/services/cutover_service.py:1608`.
  - `CutoverPlan` model has no `planned_duration_minutes` column/property (timeline uses `planned_start/planned_end`): `app/models/cutover.py:236`.
- Impact:
  - `clock.planned_total_minutes` is effectively always `null`; ETA/schedule quality is reduced.

### 6. [Medium] Frontend fallback for tenant_id is unreliable in some runtime modes
- Evidence:
  - War-room calls send `tenant_id` from `App.currentTenantId?.() || _activePlan.tenant_id`: `static/js/views/cutover.js:1188`.
  - `CutoverPlan.to_dict()` does not include `tenant_id`: `app/models/cutover.py:330`.
- Impact:
  - In environments where `App.currentTenantId()` is unavailable, war-room calls may send undefined tenant and fail with 400.

## Test Coverage Gaps
- No API-level tests for war-room endpoints (`/start-clock`, `/live-status`, `/start-task`, `/complete-task`, `/flag-issue`, `/critical-path`).
- No regression test ensuring all cutover entity create flows persist correct `tenant_id`.
- No negative tests for cross-tenant ID access on cutover CRUD routes.

## Recommended Fix Order
1. Fix tenant propagation in all cutover create services (derive from parent `Program`/`CutoverPlan` consistently).
2. Add tenant/program scoping guards to all cutover CRUD routes (not only war-room).
3. Add structured error handling in cutover blueprint for DB integrity errors.
4. Replace `planned_duration_minutes` in live-status with computed value from `planned_start/planned_end` or sum of task durations.
5. Add API tests for war-room endpoints and cross-tenant access controls.

## Assumptions
- Review assumes shared-schema multi-tenant operation where `tenant_id` is security-critical.
- If deployment uses strict DB/schema isolation per tenant, finding #3 risk level may decrease, but scoping at service/API layer is still recommended.
