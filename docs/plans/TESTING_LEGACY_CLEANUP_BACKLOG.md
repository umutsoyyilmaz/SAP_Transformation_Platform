## Testing Legacy Cleanup Backlog

Status date: 2026-03-10

Purpose:
- retire legacy `Requirement`-based testing links in a controlled way
- keep analytics, planning, and AI flows aligned to canonical `ExploreRequirement`

Completed in Sprint 2:
- testing dashboard and traceability moved to `ExploreRequirement`
- planning suggestion and coverage moved to explore-first requirement tracing
- test catalog filter treats `requirement_id` as legacy alias for `explore_requirement_id`
- defect payload normalization promotes explore UUIDs into `explore_requirement_id`
- AI test case generation accepts `explore_requirement_id`
- report engine coverage and traceability presets use `explore_requirement_id`
- visible testing UI flows are explore-first; no active test planning/test case/defect screen sends legacy requirement ids by default
- static frontend audit confirms no active `linked_requirement_id` or test-case `requirement_id` writes remain
- testing and backlog write services now reject legacy payload fields (`requirement_id`, `linked_requirement_id`)

Remaining cleanup items:
- audit `app/services/traceability.py` and `app/services/backlog_service.py` for legacy-only testing joins
- deprecate AI assistant outputs and prompts that still describe only legacy `requirements.id`
- add migration/backfill strategy for any remaining `test_cases.requirement_id` rows
- remove backend-only compatibility writes once Meridian validation confirms zero legacy payload usage

Safe compatibility surfaces to keep temporarily:
- `requirement_id` query param on test catalog list
- legacy fallback path in `TestCaseGenerator.generate()`
- legacy `requirement` traceability route, but only as an alias to canonical `explore_requirement`

Removal criteria:
- no active UI sends `requirement_id` or integer `linked_requirement_id`
- reporting uses canonical explore requirement joins only
- Meridian validation shows no user-visible regression in testing traceability
