# Requirement Semantics Sprint 1 Closeout

## Status

Completed

## Date

2026-03-10

## Objective

Sprint 1 focused on introducing a canonical requirement semantics layer on top of
`ExploreRequirement` without breaking the existing explore flow.

Goals:

- add canonical semantic fields
- separate requirement progress from delivery progress
- block new invalid "standard-fit as requirement" writes
- provide a safe audit/backfill path for existing data

## Delivered

### 1. Canonical semantic fields added

`ExploreRequirement` now supports:

- `requirement_class`
- `delivery_pattern`
- `trigger_reason`
- `delivery_status`

These fields are additive and backfill-friendly. Legacy rows continue to work
via derived fallback properties.

## 2. Delivery progress separated from requirement status

The previous model mixed business approval and downstream delivery progress.

Sprint 1 introduced `delivery_status` with derived defaults:

- `not_mapped`
- `mapped`
- `ready_for_test`
- `validated`

Current transition behavior:

- `approve` => keeps requirement status semantics, initializes delivery state
- `convert` / `push_to_alm` => `delivery_status = mapped`
- `mark_realized` => `delivery_status = ready_for_test`
- `verify` => `delivery_status = validated`
- `unconvert` => `delivery_status = not_mapped`

## 3. Semantic guardrails added

Requirement create/update paths now reject payloads that attempt to model
standard-fit observations as requirements.

Rejected patterns:

- `fit_status in ('fit', 'standard')`
- `trigger_reason = 'standard_observation'`

Rule:

- standard-fit observations belong to process evaluation
- only delta/change needs belong to requirement management

## 4. Safe audit/backfill tool added

Script:

- `scripts/audit/audit_requirement_semantics.py`

Modes:

- dry-run => reports missing semantic fields and standard-fit observations
- apply => backfills canonical semantic fields only

No destructive cleanup happens in Sprint 1.

## Meridian results

Audit performed on `instance/sap_platform_dev.db` for `program_id=1`.

Pre-backfill findings:

- `34` total requirements
- `34` rows missing all new canonical semantic fields
- `16` rows classified as `standard_fit observation`

Backfill applied:

- `34` rows updated

Post-backfill verification:

- `0` rows missing `requirement_class`
- `0` rows missing `delivery_pattern`
- `0` rows missing `trigger_reason`
- `0` rows missing `delivery_status`
- `16` rows still flagged as `standard_observation`

Interpretation:

- semantic metadata is now present
- business cleanup is still required for rows that should likely move out of the
  requirement domain and back into process evaluation

## Tests

Validated with:

```bash
.venv/bin/python -m pytest \
  tests/project_scope/test_audit_requirement_semantics.py \
  tests/features/test_requirement_consolidation.py \
  tests/features/test_requirement_lifecycle.py -q
```

Result:

- `42 passed`

## Deferred to Sprint 2

### Domain cleanup

- remove `standard_observation` rows from the requirement working set
- define review workflow for reclassifying those rows into process evaluation

### API/UI contract cleanup

- expose new canonical fields explicitly in UI forms and list views
- stop relying on legacy `type` semantics in frontend workflows

### Analytics alignment

- move testing/reporting off legacy `Requirement`
- use `ExploreRequirement` only for coverage and traceability KPIs

### Structural cleanup

- identify and remove old requirement/scope screens still tied to deprecated flow
- reduce legacy compatibility branches once frontend is migrated

## Exit criteria met

- canonical semantic fields exist
- lifecycle separation introduced
- invalid new writes are blocked
- Meridian data has been safely backfilled
- test coverage added for new behavior
