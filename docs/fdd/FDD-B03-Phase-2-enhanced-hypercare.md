# FDD-B03-Phase-2: Enhanced Hypercare War Room — Exit Criteria, Escalation Engine & Analytics

**Oncelik:** P1
**Tarih:** 2026-02-23
**Effort:** XL (3 sprint)
**Faz Etkisi:** Deploy / Run — Go-live sonrasi destek, stabilizasyon, hypercare cikis yonetimi
**Pipeline:** Tip 3 — Architect → QA → Coder → Reviewer

---

## Context

FDD-B03 MVP (Sprint 4) delivered a functional Hypercare War Room with incident CRUD, SLA tracking, change request management, and a basic dashboard. The current UI (screenshot) shows 8 metric cards, incident/CR tables, and create modals — all working.

However, three critical gaps remain that prevent professional hypercare management:

1. **No formal exit criteria** — The platform cannot determine when hypercare should end. Constants `EXIT_CRITERIA_TYPES` and `EXIT_CRITERIA_STATUSES` exist in `run_sustain.py` (lines 35-36) but no model was ever created.
2. **No escalation engine** — `HypercareSLA.escalation_after_min` exists but is never evaluated. P1 incidents can sit unattended without automated escalation.
3. **No analytics/trends** — Dashboard shows point-in-time counts only; no burn-down, root cause analysis, or system health indicator.

This FDD extends the existing implementation to close these gaps.

---

## 1. Business Context

- **Problem:** Hypercare periods run indefinitely because there's no formal exit assessment. Escalations happen manually via phone/email outside the platform. War room operators lack trend data for decision-making.
- **User Story:** As a Hypercare Manager, I want automated escalation rules, formal exit criteria with sign-off, and incident trend analytics, so that I can manage the hypercare period professionally and transition to BAU on time.
- **SAP Relevance:** Maps to SAP Activate "Run" phase — hypercare exit is a gated milestone requiring formal sign-off before BAU handover.
- **Best Practice Reference:** ServiceNow (multi-level escalation + SLA pause), Jira SM (custom SLA rules + breach alerts), SAP Solution Manager (incident correlation + CAB workflow).

---

## 2. Scope

**In Scope (this FDD):**
- Hypercare Exit Criteria model + auto-evaluation + formal sign-off [MVP]
- Multi-level Escalation Rules + Engine + Events audit trail [MVP]
- Incident analytics (burn-down, root cause, module heatmap, SLA trends) [Enhanced]
- Enhanced war room dashboard (go-live timer, health RAG, escalation alerts, exit readiness) [MVP/Enhanced]
- Incident-to-Lesson-Learned pipeline [Enhanced]
- CutoverPlan `hypercare → closed` transition guard [MVP]

**Out of Scope:**
- Email/SMS notification delivery (platform notifications only — email channel is future)
- Real-time WebSocket push (30s polling used; SSE/WS is a future infrastructure decision)
- AI-powered semantic search for similar lessons (keyword-only now; AI is Advanced tier)
- SLA pause/resume for business hours (would require timezone + calendar config)

**Dependencies:**
- Existing: `signoff_service.py`, `knowledge_base_service.py`, `run_sustain_service.py`, `notification.py`
- FDD-B03 MVP must be fully implemented (it is)

---

## 3. Data Model Changes

### 3.1 New Model: `HypercareExitCriteria` [MVP]

**File:** [run_sustain.py](app/models/run_sustain.py) — insert after `StabilizationMetric` (line 347)

Uses the orphaned constants at lines 35-36: `EXIT_CRITERIA_TYPES`, `EXIT_CRITERIA_STATUSES`.

| Field | Type | Nullable | Default | Notes |
|-------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| tenant_id | FK tenants.id | Yes | — | SET NULL on delete |
| cutover_plan_id | FK cutover_plans.id | No | — | CASCADE on delete |
| criteria_type | String(20) | No | — | incident\|sla\|kt\|handover\|metric\|custom |
| name | String(300) | No | — | Human-readable criterion name |
| description | Text | — | "" | |
| threshold_operator | String(5) | Yes | — | gte\|lte\|eq |
| threshold_value | Float | Yes | — | Target: 0 for zero P1, 95.0 for 95% SLA |
| current_value | Float | Yes | — | Last evaluated value |
| status | String(15) | No | "not_met" | not_met\|partially_met\|met |
| is_auto_evaluated | Boolean | No | True | False = manual-only assessment |
| is_mandatory | Boolean | No | True | True = blocks exit sign-off |
| weight | Integer | No | 1 | For weighted readiness score |
| evaluated_at | DateTime(tz) | Yes | — | Last evaluation timestamp |
| evaluated_by | String(150) | — | "" | "system" or user name |
| evidence | Text | — | "" | Proof: "Last P1 resolved 52h ago" |
| notes | Text | — | "" | |
| created_at | DateTime(tz) | — | utcnow | |
| updated_at | DateTime(tz) | — | utcnow | |

**Constraints:** `ck_exit_criteria_type`, `ck_exit_criteria_status`

### 3.2 New Model: `EscalationRule` [MVP]

**File:** [cutover.py](app/models/cutover.py) — insert after `seed_default_sla_targets()` (line 1302)

| Field | Type | Nullable | Default | Notes |
|-------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| tenant_id | FK tenants.id | Yes | — | SET NULL on delete |
| cutover_plan_id | FK cutover_plans.id | No | — | CASCADE on delete |
| severity | String(10) | No | — | P1\|P2\|P3\|P4 |
| escalation_level | String(20) | No | — | L1\|L2\|L3\|vendor\|management |
| level_order | Integer | No | 1 | Evaluation order within severity |
| trigger_type | String(30) | No | "no_response" | no_response\|no_update\|no_resolution\|severity_escalation |
| trigger_after_min | Integer | No | — | Minutes before escalation fires |
| escalate_to_role | String(100) | — | "" | "Hypercare Manager", "SAP Basis Team" |
| escalate_to_user_id | FK users.id | Yes | — | Optional specific user |
| notification_channel | String(30) | — | "platform" | platform\|email |
| is_active | Boolean | No | True | Inactive rules skipped |
| created_at | DateTime(tz) | — | utcnow | |

**Constraints:** `uq_escalation_severity_level(cutover_plan_id, severity, level_order)`, `ck_esc_rule_severity`, `ck_esc_rule_level`

### 3.3 New Model: `EscalationEvent` [MVP]

**File:** [cutover.py](app/models/cutover.py) — insert after `EscalationRule`

Append-only audit record (same pattern as `SignoffRecord`).

| Field | Type | Nullable | Default | Notes |
|-------|------|----------|---------|-------|
| id | Integer PK | No | auto | |
| tenant_id | FK tenants.id | Yes | — | SET NULL |
| incident_id | FK hypercare_incidents.id | No | — | CASCADE |
| escalation_rule_id | FK escalation_rules.id | Yes | — | Null for manual escalations |
| escalation_level | String(20) | No | — | L1\|L2\|L3\|vendor\|management |
| escalated_to | String(150) | No | — | Role or person name |
| escalated_to_user_id | FK users.id | Yes | — | Platform user notified |
| trigger_type | String(30) | No | — | no_response\|no_update\|no_resolution\|severity_escalation\|manual |
| is_auto | Boolean | No | True | False for manual escalations |
| notes | Text | — | "" | |
| acknowledged_at | DateTime(tz) | Yes | — | When recipient confirmed |
| acknowledged_by_user_id | FK users.id | Yes | — | |
| created_at | DateTime(tz) | No | utcnow | |

**Indexes:** `ix_esc_event_incident_time(incident_id, created_at)`, `ix_esc_event_unack(acknowledged_at)`

### 3.4 Modified Model: `HypercareIncident` — Add Escalation Tracking

**File:** [cutover.py](app/models/cutover.py) — insert after line 1093 (`change_request_id` column)

| New Field | Type | Default | Notes |
|-----------|------|---------|-------|
| current_escalation_level | String(20) | None | L1\|L2\|L3\|vendor\|management |
| escalation_count | Integer | 0 | Total escalation events |
| last_escalated_at | DateTime(tz) | None | Most recent escalation |
| last_activity_at | DateTime(tz) | None | Last comment/status change — used by no_update trigger |

Also add `escalation_events` relationship + update `to_dict()` with these 4 fields.

### 3.5 Modified Model: `IncidentComment` — Add comment_type

**File:** [cutover.py](app/models/cutover.py) — insert after line 1413 (`is_internal` column)

| New Field | Type | Default | Notes |
|-----------|------|---------|-------|
| comment_type | String(20) | "comment" | comment\|escalation\|status_change\|assignment |

Auto-included in `to_dict()` via column introspection (no code change needed for serialization).

### 3.6 Modified: `VALID_ENTITY_TYPES` in SignoffRecord

**File:** [signoff.py](app/models/signoff.py) line 20 — add `"hypercare_exit"` to the frozenset.

### 3.7 Migration

```
flask db migrate -m "fdd_b03_phase2_exit_criteria_escalation"
```

---

## 4. Business Rules

### Exit Criteria

| ID | Rule | HTTP |
|---|---|---|
| BR-E01 | All mandatory exit criteria must have `status='met'` before requesting formal exit sign-off | 422 |
| BR-E02 | Cannot manually set `status='met'` on `is_auto_evaluated=True` criterion (must disable auto-eval first) | 422 |
| BR-E03 | `seed_exit_criteria()` is idempotent — returns empty list if criteria already exist | 200 |
| BR-E04 | Self-approval not permitted for exit sign-off (delegated to signoff_service) | 422 |
| BR-E05 | CutoverPlan `hypercare → closed` requires approved exit sign-off | 422 |
| BR-E06 | Only `criteria_type='custom'` can be manually created; standard types via seed only | 400 |

### Escalation

| ID | Rule | HTTP |
|---|---|---|
| BR-ES01 | Rules unique per `(plan_id, severity, level_order)` — DB enforced | 400 |
| BR-ES02 | Auto-escalation only evaluates `status in (open, investigating)` incidents | — |
| BR-ES03 | Manual escalation requires `status in (open, investigating)` | 422 |
| BR-ES04 | `acknowledge_escalation()` is idempotent | 200 |
| BR-ES05 | EscalationEvent records are append-only (no update/delete endpoints) | — |
| BR-ES06 | Max one EscalationEvent per `(incident_id, escalation_level)` per rule — prevents duplicates | — |

### Lesson Pipeline

| ID | Rule | HTTP |
|---|---|---|
| BR-L01 | `create_lesson_from_incident()` requires `status in (resolved, closed)` | 422 |

### State Machine: Escalation Level (monotonically increasing)

```
null → L1 → L2 → L3 → vendor → management
```

### State Machine: Exit Criteria Status (bidirectional — can regress)

```
not_met ⇄ partially_met ⇄ met
```

### CutoverPlan Transition Guard

```
hypercare → closed   [GUARD: signoff_service.is_entity_approved("hypercare_exit", plan_id)]
```

---

## 5. API Contract

### 5.1 Exit Criteria Endpoints [MVP]

**POST** `/api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria/seed`
- Permission: `hypercare.manage`
- Request: `{}` (no body)
- 201: `{"items": [...], "total": 5}` | 200: `{"items": [], "message": "Already exist"}`

**GET** `/api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria`
- Permission: `hypercare.read`
- Query: `?status=met&criteria_type=incident`
- 200: `{"items": [...], "total": N}`

**GET** `/api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria/evaluate`
- Permission: `hypercare.manage`
- Query: `?program_id=1` (required)
- 200: `{"plan_id": 1, "ready": bool, "recommendation": str, "criteria": [...], "summary": {"met": N, "total": N, "mandatory_met": N, "mandatory_total": N, "pct": float}}`

**PUT** `/api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria/<criterion_id>`
- Permission: `hypercare.manage`
- Request: `{"status": "met", "evidence": "...", "evaluated_by": "..."}`
- 200: criterion dict | 422: BR-E02 violation

**POST** `/api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria`
- Permission: `hypercare.manage`
- Request: `{"name": "...", "description": "...", "is_mandatory": true}`
- 201: criterion dict with `criteria_type='custom'`

**POST** `/api/v1/run-sustain/plans/<plan_id>/hypercare/exit-criteria/signoff`
- Permission: `hypercare.approve`
- Request: `{"approver_id": 5, "comment": "..."}`
- 200: signoff record | 422: BR-E01 violation

### 5.2 Escalation Rule Endpoints [MVP]

**GET** `/api/v1/run-sustain/plans/<plan_id>/hypercare/escalation-rules`
- Permission: `hypercare.read`
- Query: `?severity=P1`
- 200: `{"items": [...], "total": N}`

**POST** `/api/v1/run-sustain/plans/<plan_id>/hypercare/escalation-rules`
- Permission: `hypercare.manage`
- Request: `{"severity": "P1", "escalation_level": "L2", "level_order": 2, "trigger_type": "no_response", "trigger_after_min": 30, "escalate_to_role": "Hypercare Manager"}`
- 201: rule dict | 400: duplicate/invalid

**PUT** `/api/v1/run-sustain/plans/<plan_id>/hypercare/escalation-rules/<rule_id>`
- Permission: `hypercare.manage`
- 200: updated rule

**DELETE** `/api/v1/run-sustain/plans/<plan_id>/hypercare/escalation-rules/<rule_id>`
- Permission: `hypercare.manage`
- 200: `{"deleted": true, "id": N}`

**POST** `/api/v1/run-sustain/plans/<plan_id>/hypercare/escalation-rules/seed`
- Permission: `hypercare.manage`
- 201: `{"items": [...], "total": 8}` (SAP-standard defaults: P1=4 levels, P2=2, P3=1, P4=1)

### 5.3 Escalation Event Endpoints [MVP]

**GET** `/api/v1/run-sustain/plans/<plan_id>/hypercare/escalations`
- Query: `?incident_id=5&unacknowledged=true`
- 200: `{"items": [...], "total": N}`

**POST** `/api/v1/run-sustain/plans/<plan_id>/hypercare/escalations/evaluate`
- Permission: `hypercare.manage`
- 200: `{"new_escalations": [...], "evaluated_incidents": N}`

**POST** `/api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/escalate`
- Permission: `hypercare.manage`
- Request: `{"escalation_level": "L2", "escalated_to": "Program Director", "notes": "..."}`
- 201: event dict | 422: BR-ES03

**POST** `/api/v1/run-sustain/plans/<plan_id>/hypercare/escalations/<event_id>/acknowledge`
- Permission: `hypercare.update`
- 200: acknowledged event dict

### 5.4 Analytics & War Room Endpoints [Enhanced]

**GET** `/api/v1/run-sustain/plans/<plan_id>/hypercare/analytics`
- Permission: `hypercare.read`
- 200: `{"burn_down": [...], "root_cause_distribution": {...}, "module_heatmap": {...}, "sla_compliance_trend": [...], "team_workload": {...}, "mttr_by_severity": {...}, "category_distribution": {...}}`

**GET** `/api/v1/run-sustain/plans/<plan_id>/hypercare/war-room`
- Permission: `hypercare.read`
- 200: `{"metrics": {existing}, "go_live_plus_days": N, "hypercare_phase": str, "hypercare_remaining_days": N, "system_health": "green"|"yellow"|"red", "active_escalations": [...], "p1_p2_feed": [...], "exit_readiness_pct": float}`

**System health RAG logic:**
- RED: open P1 OR SLA breached > 3 OR escalation at L3+
- YELLOW: open P2 OR SLA breached > 0 OR escalation at L1/L2
- GREEN: none of the above

### 5.5 Incident-to-Lesson Endpoints [Enhanced]

**POST** `/api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/create-lesson`
- Permission: `hypercare.manage`
- Request: `{"title": "...", "category": "..."}` (all optional — pre-populated from incident)
- 201: lesson dict | 422: BR-L01

**GET** `/api/v1/run-sustain/plans/<plan_id>/hypercare/incidents/<incident_id>/similar-lessons`
- Permission: `hypercare.read`
- Query: `?max_results=5`
- 200: `{"items": [...], "total": N}`

---

## 6. UI Behavior (Functional Description)

### 6.1 Enhanced War Room Header [MVP]

Replace static header with dynamic context bar:
- **Go-Live + N days** counter (from `CutoverPlan.hypercare_start`)
- **Phase indicator**: "Week 1 — Stabilization" / "Weeks 2-4 — Optimization" / "Exit Assessment"
- **Remaining days** countdown
- **System Health** RAG dot (green/yellow/red)

### 6.2 Escalation Alerts Panel [MVP]

New section between metrics cards and incident table:
- Shows unacknowledged escalation events (last 5)
- Each alert: severity badge, incident code, escalated-to name, time ago
- **Acknowledge** button per alert
- Critical styling (red border) for L3/vendor/management levels

### 6.3 Exit Readiness Widget [MVP]

New section after Change Requests table:
- Progress bar showing exit readiness percentage
- Grid of criteria with status icons (checkmark/warning/cross)
- Mandatory criteria highlighted
- **"Request Formal Exit Sign-off"** button — disabled until all mandatory criteria met

### 6.4 P1/P2 Live Feed [Enhanced]

30-second polling of `/hypercare/war-room` endpoint with selective DOM updates (no full re-render) for:
- P1/P2 incidents created/updated in last 24h
- Active escalation alerts

### 6.5 Incident Detail Modal Enhancements [Enhanced]

- **Escalate** button (visible when open/investigating)
- **Create Lesson** button (visible when resolved/closed)
- Escalation history timeline
- Similar lessons panel from knowledge base

---

## 7. Acceptance Criteria

- [x] AC-01: `seed_exit_criteria()` creates 5 standard SAP exit criteria with auto-evaluation thresholds
- [x] AC-02: `evaluate_exit_criteria()` computes current values from live incident/SLA/KT/handover/metric data
- [x] AC-03: Formal exit sign-off blocked when any mandatory criterion is `not_met` (BR-E01)
- [x] AC-04: CutoverPlan `hypercare → closed` transition blocked without approved exit sign-off (BR-E05)
- [x] AC-05: `seed_default_escalation_rules()` creates 8 rules (P1:4 levels, P2:2, P3:1, P4:1)
- [x] AC-06: `evaluate_escalations()` creates EscalationEvent for P1 incident after trigger_after_min exceeded
- [x] AC-07: Duplicate escalation prevention: same level not re-triggered for same incident (BR-ES06)
- [x] AC-08: War room dashboard shows go-live timer, hypercare phase, system health RAG
- [x] AC-09: Incident analytics returns burn-down, root cause distribution, module heatmap
- [x] AC-10: One-click lesson creation from resolved incident pre-populates fields correctly
- [x] AC-11: All 42 tests pass including tenant isolation scenarios
- [x] AC-12: All endpoints have `@require_permission` decorator

---

## 8. Edge Cases & Error Scenarios

- EC-01: `hypercare_start` not set on CutoverPlan → `go_live_plus_days=null`, phase="Hypercare Active"
- EC-02: Plan with 0 incidents → all analytics return empty/zero, no errors
- EC-03: Exit criterion regresses (P1 opens after criterion was "met") → auto-eval sets back to "not_met"
- EC-04: Escalation rule fires but `escalate_to_user_id` no longer exists → event created with role only, no user notification fails gracefully
- EC-05: Two users call `evaluate_escalations()` concurrently → DB unique constraint prevents duplicate events; second call gets IntegrityError caught → no duplicate
- EC-06: Manual escalation on already-escalated-to-higher-level incident → still creates event (manual overrides monotonicity restriction for operator flexibility)

---

## 9. Performance Considerations

- **Expected volume:** 50-200 incidents per hypercare period (4-8 weeks), 8-20 escalation rules, 5-10 exit criteria
- **Analytics queries:** Aggregations on max ~200 incidents — no performance concern for SQLite/PostgreSQL
- **Burn-down:** Capped at 90 days (BR-A01)
- **Lazy evaluation pattern:** Escalation engine runs inline per API call (same as existing SLA breach detection) — acceptable at this volume. Background scheduler added as enhancement for high-volume tenants.
- **Indexes:** `ix_esc_event_incident_time`, `ix_esc_event_unack` for escalation event queries

---

## 10. Security Considerations

- **Permissions:** `hypercare.read` (view), `hypercare.manage` (CRUD/evaluate), `hypercare.update` (status changes), `hypercare.approve` (exit sign-off)
- **Tenant isolation:** All new models include `tenant_id`. All queries use `query_for_tenant(tenant_id)` or explicit tenant filter
- **Self-approval guard:** Exit sign-off delegates to `signoff_service` which enforces this
- **Append-only audit:** EscalationEvent records never updated (only acknowledged_at can be set)

---

## 11. Migration Notes

- **New tables:** `hypercare_exit_criteria`, `escalation_rules`, `escalation_events`
- **Schema changes:** 4 columns added to `hypercare_incidents`, 1 column to `incident_comments`
- **Data migration:** No — new tables start empty; seeded via API calls

---

## 12. Implementation Order

### Phase A: Foundation (Sprint 1, ~3 days)
1. Add all 3 new models + modify existing models in `cutover.py` and `run_sustain.py`
2. Add `"hypercare_exit"` to `VALID_ENTITY_TYPES` in `signoff.py`
3. Generate Alembic migration

### Phase B: Exit Criteria (Sprint 1, ~2 days)
4. Service functions: `seed_exit_criteria`, `list_exit_criteria`, `evaluate_exit_criteria`, `update_exit_criterion`, `create_exit_criterion`, `request_exit_signoff`
5. Blueprint: 6 endpoints
6. CutoverPlan transition guard in `cutover_service.py`
7. Unit tests for exit criteria

### Phase C: Escalation Engine (Sprint 1-2, ~3 days)
8. Service functions: `create_escalation_rule`, `list_escalation_rules`, `update_escalation_rule`, `delete_escalation_rule`, `seed_default_escalation_rules`, `evaluate_escalations`, `escalate_incident_manually`, `acknowledge_escalation`, `list_escalation_events`
9. Blueprint: 9 endpoints
10. Unit tests for escalation

### Phase D: Analytics & War Room (Sprint 2, ~2 days)
11. Service: `get_incident_analytics`, `get_war_room_dashboard`
12. Blueprint: 2 endpoints
13. Tests

### Phase E: Lesson Pipeline (Sprint 2, ~1 day)
14. Service: `create_lesson_from_incident`, `suggest_similar_lessons`
15. Blueprint: 2 endpoints
16. Tests

### Phase F: Frontend (Sprint 2-3, ~3 days)
17. War room header with go-live timer, phase, RAG indicator
18. Escalation alerts panel
19. Exit readiness widget with sign-off button
20. P1/P2 live feed (30s polling)
21. Incident detail modal: escalate/create-lesson buttons, escalation history, similar lessons

### Phase G: Scheduled Job (Sprint 3, ~1 day)
22. `auto_escalate_incidents` in `scheduled_jobs.py`

---

## Files Modified

| File | Change |
|------|--------|
| [run_sustain.py](app/models/run_sustain.py) | Added `HypercareExitCriteria` model |
| [cutover.py](app/models/cutover.py) | Added `EscalationRule`, `EscalationEvent`, modified `HypercareIncident`, `IncidentComment` |
| [signoff.py](app/models/signoff.py) | Added `"hypercare_exit"` to `VALID_ENTITY_TYPES` |
| [hypercare_service.py](app/services/hypercare_service.py) | Added 20 new service functions |
| [hypercare_bp.py](app/blueprints/hypercare_bp.py) | Added 19 new endpoints |
| [cutover_service.py](app/services/cutover_service.py) | Transition guard for `hypercare → closed` |
| [hypercare.js](static/js/views/hypercare.js) | Enhanced war room dashboard UI |
| [scheduled_jobs.py](app/services/scheduled_jobs.py) | `auto_escalate_incidents` job |
| [blueprint_permissions.py](app/middleware/blueprint_permissions.py) | Added `hypercare` blueprint permission mapping |
| [seed_demo_data.py](scripts/seed_demo_data.py) | Exit criteria + escalation rules for demo plan |

## Files Created

| File | Purpose |
|------|---------|
| [test_hypercare_phase2.py](tests/test_hypercare_phase2.py) | 42 test functions covering all Phase 2 features |

---

## Verification Results

1. **Unit tests:** `pytest tests/test_hypercare_phase2.py -v` — **42 passed**
2. **Existing tests:** `pytest tests/test_hypercare_service.py -v` — **11 passed**, no regressions
3. **Lint:** `ruff check` — clean (only pre-existing UP017 warnings in shared files)

---

## REVIEWER AUDIT NOTU

| # | Eylem | Sahip | Durum |
|---|---|---|---|
| A1 | Verify `HypercareExitCriteria.tenant_id` follows same nullable pattern as `StabilizationMetric` (nullable=True, ondelete=SET NULL) | Coder | Done |
| A2 | Confirm `evaluate_escalations()` handles concurrent calls safely (DB unique constraint + IntegrityError catch) | Coder | Done |
| A3 | Ensure `last_activity_at` is updated on every comment, status change, and assignment change in existing service functions | Coder | Done |
| A4 | Verify scheduled job `auto_escalate_incidents` only processes plans with `status='hypercare'` to avoid evaluating closed/draft plans | Coder | Done |
| A5 | Test that exit sign-off via signoff_service properly checks self-approval guard (requestor_id != approver_id) | QA | Covered by test |
