## Legacy Requirement FK Removal Plan

Status date: 2026-03-10

Purpose:
- remove integer legacy requirement links after canonical `explore_requirement_id` rollout
- avoid dual-write drift in backlog, testing, and traceability modules

Audit basis:
- source: `scripts/audit/audit_legacy_requirement_links.py`
- latest local audit result:
  - `backlog_legacy_only=0`
  - `config_legacy_only=0`
  - `test_cases_legacy_only=0`
  - `defects_legacy_only=0`
  - `unresolved_*_legacy_refs=0`

Scope:
- `backlog_items.requirement_id`
- `config_items.requirement_id`
- `test_cases.requirement_id`
- `defects.linked_requirement_id`

Pre-removal gates:
- no active UI writes legacy requirement fields
- audit script returns zero legacy-only and unresolved rows
- canonical reporting/traceability paths are green in regression tests
- compatibility aliases are documented and bounded

Execution sequence:
1. Freeze writes
   - keep accepting legacy alias payloads only for read/compat normalization
   - reject new integer legacy writes in service layer once rollout window closes
2. Backfill check
   - run `scripts/audit/audit_legacy_requirement_links.py`
   - if any legacy-only rows remain, run `scripts/migrate_legacy_requirements.py`
3. Deprecation release
   - announce `requirement_id` / `linked_requirement_id` payload removal
   - log any remaining alias usage for one sprint
4. Schema removal
   - drop legacy FKs and indexes from backlog/testing tables
   - remove service fallback joins
   - remove legacy alias handling from API payload normalization
5. Post-removal verification
   - traceability, reporting, test planning, backlog CRUD regression
   - Meridian smoke validation

Implementation backlog:
- add usage logging around legacy payload aliases before hard reject
- prepare Alembic migration for the four legacy columns
- remove fallback joins from `traceability.py` and `test_planning_service.py`
- remove legacy alias normalization from `backlog_service.py` and `testing_service.py`

Rollback:
- restore from DB backup
- re-enable alias normalization in services
- rerun migration script to repopulate canonical links if needed
