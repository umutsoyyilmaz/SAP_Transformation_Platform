# suite_type Removal Plan

Date: 2026-03-11

## Goal

Retire `TestSuite.suite_type` and make `purpose` the only semantic suite classifier.

## Why

- `suite_type` conflicts with plan/cycle level semantics like SIT/UAT.
- reusable suite libraries should not be phase-bound
- active UI and API flows already operate purpose-first

## Current Decision

- `purpose` is canonical
- deprecated `suite_type` input is rejected at the API boundary
- `suite_type` has been removed from the model, default responses, and DB schema

## Transition Steps

1. Stop active clients from sending `suite_type`
2. Audit data drift
3. Remove `suite_type` from primary docs/UI contracts
4. Run DB migration to remove the column
5. Reject remaining `suite_type` request aliases at the API boundary

## Removal Readiness Checks

- `blank_purpose = 0`
- no active frontend payload writes `suite_type`
- no primary tests assert business behavior through `suite_type`

## Tooling

- `scripts/audit_suite_type_transition.py`
  - dry-run audit
  - `--apply` backfills blank `purpose` from deprecated `suite_type`

## Immediate Status

- active UI uses `purpose`
- active tests use `purpose`
- suite response contract is purpose-only
- suite request contract now rejects `suite_type`
- DB migration applied: `c7q8r9s0n126`
- current local audit result:
  - `total=8`
  - `blank_purpose=0`
- local backfill was applied before drop
- local DB no longer has `test_suites.suite_type`
