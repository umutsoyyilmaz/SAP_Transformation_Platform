# Requirement Canonicalization Sprint Backlog Status

Date: 2026-03-11
Status: Complete

## Completed in This Slice

- `explore_service.dispatch_requirements_endpoint()` now resolves these endpoints directly in the canonical service layer:
  - `list_requirements`
  - `create_requirement_flat`
  - `get_requirement`
  - `update_requirement`
  - `get_requirement_linked_items`
  - `transition_requirement_endpoint`
  - `batch_transition_endpoint`
  - `bulk_sync_alm`
  - `requirement_stats`
  - `requirement_coverage_matrix`
  - `convert_requirement_endpoint`
  - `batch_convert_endpoint`
  - `unconvert_requirement_endpoint`
- `app/services/explore_legacy/requirements_legacy.py` was reduced to thin compatibility wrappers for the handlers above.
- `link_open_item` and `add_requirement_dependency` were also moved to the canonical service layer.
- workshop document list/generate handlers were moved to the canonical service layer.
- `dispatch_requirements_endpoint()` legacy fallback was removed.
- `app/services/explore_legacy/requirements_legacy.py` was deleted.
- Integration fixtures were aligned with the canonical SAP requirement model:
  - requirements now carry L3 scope context
  - SIT test cases now trace to L3 through `explore_requirement_id` or `process_level_id`
- Test hygiene was aligned with the current canonical scope model:
  - `datetime.utcnow()` usage in touched explore tests was replaced with timezone-aware `datetime.now(UTC)`
  - touched tests now use `Session.get()` instead of legacy `Query.get()`
  - auth and hypercare fixtures now create real `Project` rows where project-scoped writes are required
- Testing contract cleanup was extended:
  - active suite creation/filter flows now use `purpose`
  - active test case suite assignment flows now use `suite_ids[]`
  - testing suite alias paths remain compat-only and no longer generate deprecation warning noise in the active regression package
- Broader targeted regression for the warning-cleanup package passed:
  - `tests/test_explore.py`
  - `tests/test_requirement_lifecycle.py`
  - `tests/test_auth.py`
  - `tests/test_sso.py`
  - `tests/test_project_service.py`
  - `tests/test_folders_env_f6.py`
  - `tests/test_hypercare_service.py`
- Testing API contract regression also passed:
  - `tests/test_api_testing.py`
  - `tests/test_api_test_planning_services.py`
  - no `suite_type` / `suite_id` deprecation warnings remained in the targeted regression

## Final Closeout

- Canonical requirement handlers fully own runtime behavior.
- Explore/testing/reporting surfaces no longer depend on requirement legacy runtime modules.
- Active contract cleanup completed for `suite_type`, `suite_ids`, and canonical requirement identifiers.
- Wider targeted regression passed after closeout cleanup.

## Residual Notes

- Historical ADR/design documents may still describe intermediate migration stages.
- These historical notes do not represent active runtime behavior.

## Outcome

Requirement canonicalization sprint scope is closed.
