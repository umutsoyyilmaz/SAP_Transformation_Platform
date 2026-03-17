## Explore Legacy Namespace Removal Plan

Status date: 2026-03-11
Status: Complete

Purpose:
- retire `app/services/explore_legacy/*` after canonical Explore APIs are stabilized
- remove dispatcher indirection from `app/services/explore_service.py`
- avoid carrying duplicate business rules across legacy and canonical Explore flows

Current live inventory:
- No live `explore_legacy` service modules remain.
- Dispatcher entrypoints still exist in [explore_service.py](/Users/umutsoyyilmaz/Downloads/SAP_Transformation_Platform-main/app/services/explore_service.py), but they now resolve directly to canonical handlers.

Observed call path:
- `explore_service.dispatch_workshops_endpoint()` → canonical handlers
- `explore_service.dispatch_process_levels_endpoint()` → canonical handlers
- `explore_service.dispatch_requirements_endpoint()` → canonical handlers

Removal principles:
- remove by slice, not by namespace-wide big bang
- preserve endpoint contracts only where UI still depends on them
- move surviving business rules into canonical services before deleting wrappers

Sprint plan:

Sprint 3A: Requirements slice
- completed
- canonical handlers added
- legacy fallback removed
- `requirements_legacy.py` deleted

Sprint 3B: Workshop slice
- completed
- workshop CRUD, lifecycle, KPI, attendee/agenda/decision/session flows moved to canonical handlers
- legacy fallback removed
- `workshops_legacy.py` deleted

Sprint 3C: Process hierarchy slice
- completed
- process hierarchy CRUD, scope matrix, seeding, signoff, BPMN, readiness, propagation flows moved to canonical handlers
- legacy fallback removed
- `process_levels_legacy.py` deleted

Sprint 3D: Namespace shutdown
- completed
- `app/services/explore_legacy/__init__.py` deleted
- `explore_legacy` imports removed from `explore_service.py`
- docs/comment drift cleanup completed on active status surfaces

Exit criteria:
- no runtime import of `app.services.explore_legacy`
- no fallback import of `app.services.explore_legacy` in `explore_service.py`
- explore requirements/workshops/hierarchy UI smoke tests green
- no user-visible route regression in Meridian dataset

Risks:
- runtime dual-path risk is closed
- remaining references, if any, are historical documentation only

Completion log:
1. `requirements_legacy.py` removed on 2026-03-10
2. `workshops_legacy.py` removed on 2026-03-10
3. `process_levels_legacy.py` removed on 2026-03-10
4. `app/services/explore_legacy/__init__.py` removed on 2026-03-10
5. targeted warning-cleanup regression passed on 2026-03-10 after project-scoped test fixtures were aligned
6. active cleanup/status docs aligned to post-removal final state on 2026-03-11
