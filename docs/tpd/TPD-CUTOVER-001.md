# TPD: Cutover Hub Module — Comprehensive Test Plan

**Based on:** FDD-I03 (War Room), FDD-B03 (Hypercare), FDD-B03-Phase-2 (Escalations), FDD-B03-Phase-3 (War Rooms)
**Date:** 2026-02-24
**Total Scenarios:** 247
**Priority Breakdown:** P0: 78 | P1: 102 | P2: 67
**Existing Coverage:** 138 tests across 5 files
**New Scenarios Needed:** 109

---

## 1. Test Strategy

### Scope

- **In scope:**
  - CutoverPlan CRUD + 9-state lifecycle (draft → approved → rehearsal → ready → executing → completed → hypercare → closed | rolled_back)
  - CutoverScopeItem CRUD + computed status
  - RunbookTask CRUD + 6-state lifecycle + dependency graph + critical path
  - TaskDependency: add/remove + cycle detection + same-plan enforcement
  - Rehearsal CRUD + lifecycle + metrics computation + variance flag
  - GoNoGoItem CRUD + seed + summary aggregation + execution gate
  - HypercareIncident CRUD + lifecycle + SLA deadline auto-calculation + breach detection
  - HypercareSLA CRUD + seed (P1-P4 SAP standard)
  - EscalationRule CRUD + seed (8-rule SAP matrix)
  - EscalationEvent: auto-trigger engine + manual escalate + acknowledge
  - PostGoliveChangeRequest CRUD + approval workflow
  - IncidentComment: append-only + is_internal visibility
  - HypercareWarRoom CRUD + incident/CR assignment + analytics
  - HypercareExitCriteria: seed + auto-evaluate + manual update + exit signoff gate
  - War Room Clock: start-clock + live-status (30s polling) + task execution + flag-issue
  - Cutover-to-Hypercare plan transition with signoff guard (BR-E05)
  - Tenant isolation across ALL entities (P0 — non-negotiable)
  - Permission enforcement on ALL 100+ endpoints

- **Out of scope:**
  - AI cutover optimizer assistant (separate AI test suite)
  - Playwright E2E browser tests (deferred to E2E phase)
  - PostgreSQL-specific behavior (tested in staging, not unit)
  - Redis rate limiting on cutover endpoints
  - Background scheduler for SLA breach detection (Phase B — currently lazy)

- **Test types:** Unit (service layer), Integration (API via test client), Tenant Isolation, State Machine, Dependency Graph
- **Test environment:** SQLite in-memory (unit/integration), PostgreSQL (staging)

### Risk-Based Priority

| Risk Area | Likelihood | Impact | Priority |
|---|---|---|---|
| Cross-tenant cutover plan leak | Low | Critical (GDPR, company-ending) | P0 |
| Cross-tenant incident data leak | Low | Critical | P0 |
| Auth bypass on cutover endpoints | Low | Critical | P0 |
| Plan lifecycle skip (draft→executing) | Medium | High (ungated go-live) | P0 |
| Pending Go/No-Go ignored during execution | Medium | Critical (ungated go-live) | P0 |
| Circular dependency not detected | Low | High (infinite loop, crash) | P0 |
| SLA deadline miscalculated | Medium | High (missed escalation) | P0 |
| Escalation engine fires duplicate | Medium | Medium (notification spam) | P0 |
| Exit signoff bypassed | Low | Critical (premature closure) | P0 |
| Predecessor guard bypassed (task starts blocked) | Medium | High (execution chaos) | P0 |
| Input validation bypass (missing fields) | Medium | Medium | P1 |
| Code auto-generation collision | Low | Medium | P1 |
| Delay calculation wrong | Medium | Medium | P1 |
| Critical path calculation wrong | Medium | Medium | P1 |
| War room analytics count wrong | Medium | Low | P1 |
| Rehearsal metrics variance wrong | Medium | Low | P1 |
| Pagination/sort on large datasets | High | Low | P2 |
| UI state inconsistency after tab switch | Medium | Low | P2 |
| Performance on 1000+ tasks | Low | Medium | P2 |

---

## 2. CutoverPlan API Test Scenarios

### 2.1 POST /api/v1/cutover/plans — Create

#### P0 — Critical Path
| ID | Scenario | Input | Expected | HTTP | Existing? |
|---|---|---|---|---|---|
| TC-CP-001 | Create with required fields | `{"program_id":1, "name":"Wave 1"}` | Plan created, code=CUT-001 | 201 | YES |
| TC-CP-002 | Sequential code generation | Create 2 plans | Codes CUT-001, CUT-002 | 201 | YES |
| TC-CP-003 | Create with all optional fields | `{"program_id":1, "name":"W1", "description":"...", "cutover_manager":"John", "environment":"QAS", "planned_start":"2026-03-01T22:00", "planned_end":"2026-03-03T06:00", "rollback_deadline":"2026-03-02T12:00"}` | All fields persisted correctly | 201 | NO |
| TC-CP-004 | Datetime fields parsed from ISO | `{"planned_start":"2026-03-01"}` | Parsed as datetime, not string | 201 | NO |

#### P1 — Input Validation
| ID | Scenario | Input | Expected | HTTP | Existing? |
|---|---|---|---|---|---|
| TC-CP-010 | Missing program_id | `{"name":"W1"}` | "program_id and name are required" | 400 | YES |
| TC-CP-011 | Missing name | `{"program_id":1}` | "program_id and name are required" | 400 | YES |
| TC-CP-012 | Empty body | `{}` | "program_id and name are required" | 400 | NO |
| TC-CP-013 | Name = empty string | `{"program_id":1, "name":""}` | Error or empty name accepted (check FDD) | 400 | NO |
| TC-CP-014 | Name = 200 chars (boundary) | `{"program_id":1, "name":"x"*200}` | Created | 201 | NO |
| TC-CP-015 | Name = 201 chars (over limit) | `{"program_id":1, "name":"x"*201}` | DB error or 400 | 400/500 | NO |
| TC-CP-016 | Invalid environment value | `{"program_id":1, "name":"W1", "environment":"INVALID"}` | Extra fields ignored (no enum check) | 201 | NO |
| TC-CP-017 | SQL injection in name | `{"program_id":1, "name":"'; DROP TABLE--"}` | Treated as literal string | 201 | NO |
| TC-CP-018 | XSS in description | `{"program_id":1, "name":"W1", "description":"<script>alert(1)</script>"}` | Stored as text, rendered safely | 201 | NO |
| TC-CP-019 | program_id = non-existent | `{"program_id":99999, "name":"W1"}` | FK violation or orphan plan | 500/400 | NO |

### 2.2 GET /api/v1/cutover/plans — List

| ID | Scenario | Input | Expected | HTTP | Existing? |
|---|---|---|---|---|---|
| TC-CP-020 | List all plans for program | `?program_id=1` | Returns matching plans | 200 | YES |
| TC-CP-021 | Filter by status | `?program_id=1&status=draft` | Only draft plans | 200 | YES |
| TC-CP-022 | No matching plans | `?program_id=999` | Empty items[], total=0 | 200 | NO |
| TC-CP-023 | Missing program_id filter | No params | Returns ALL plans (cross-program!) | 200 | NO |

### 2.3 GET /api/v1/cutover/plans/:id — Get Single

| ID | Scenario | Input | Expected | HTTP | Existing? |
|---|---|---|---|---|---|
| TC-CP-030 | Get existing plan | Valid plan_id | Full plan dict with counts | 200 | YES |
| TC-CP-031 | Get with children | `?include=children` | Includes scope_items, rehearsals, go_no_go | 200 | YES |
| TC-CP-032 | Get non-existent plan | plan_id=9999 | "CutoverPlan not found" | 404 | YES |

### 2.4 PUT /api/v1/cutover/plans/:id — Update

| ID | Scenario | Input | Expected | HTTP | Existing? |
|---|---|---|---|---|---|
| TC-CP-040 | Update name | `{"name":"Wave 1 v2"}` | Name updated | 200 | YES |
| TC-CP-041 | Update hypercare fields | `{"hypercare_duration_weeks":6, "hypercare_manager":"Jane"}` | Fields updated | 200 | YES |
| TC-CP-042 | Update non-existent plan | PUT /plans/9999 | 404 | 404 | NO |
| TC-CP-043 | Update code (should be immutable) | `{"code":"CUT-999"}` | Code NOT changed (not in updatable) | 200 | NO |
| TC-CP-044 | Update status directly (bypass transition) | `{"status":"executing"}` | Status NOT changed (not in updatable) | 200 | NO |

### 2.5 DELETE /api/v1/cutover/plans/:id — Delete

| ID | Scenario | Input | Expected | HTTP | Existing? |
|---|---|---|---|---|---|
| TC-CP-050 | Delete existing plan | Valid plan_id | Plan + all children cascaded | 200 | YES |
| TC-CP-051 | Delete non-existent plan | plan_id=9999 | 404 | 404 | NO |
| TC-CP-052 | Delete plan with children | Plan with scope items + tasks | All scope items + tasks deleted | 200 | NO |

---

## 3. State Machine Test Scenarios

### 3.1 CutoverPlan Transitions

#### Valid Transitions (All Must Succeed — 200)
| ID | From | To | Guard | Existing? |
|---|---|---|---|---|
| TC-SM-001 | draft | approved | None | YES |
| TC-SM-002 | approved | rehearsal | None | YES |
| TC-SM-003 | approved | ready | ≥1 completed rehearsal | YES |
| TC-SM-004 | rehearsal | approved | None | NO |
| TC-SM-005 | rehearsal | ready | ≥1 completed rehearsal | NO |
| TC-SM-006 | ready | executing | 0 pending go/no-go items | YES |
| TC-SM-007 | ready | approved | None | NO |
| TC-SM-008 | executing | completed | None (sets actual_end) | YES |
| TC-SM-009 | executing | rolled_back | None (sets actual_end) | NO |
| TC-SM-010 | completed | hypercare | Sets hypercare_start/end | YES |
| TC-SM-011 | hypercare | closed | Exit signoff approved (BR-E05) | YES |
| TC-SM-012 | rolled_back | draft | None | NO |

#### Invalid Transitions (All Must Fail — 409)
| ID | From | To | Expected Error | Existing? |
|---|---|---|---|---|
| TC-SM-020 | draft | ready | "Invalid transition: draft → ready" | NO |
| TC-SM-021 | draft | executing | "Invalid transition: draft → executing" | NO |
| TC-SM-022 | draft | completed | "Invalid transition: draft → completed" | YES |
| TC-SM-023 | draft | closed | "Invalid transition: draft → closed" | NO |
| TC-SM-024 | approved | executing | "Invalid transition: approved → executing" | NO |
| TC-SM-025 | executing | draft | "Invalid transition: executing → draft" | NO |
| TC-SM-026 | completed | draft | "Invalid transition: completed → draft" | NO |
| TC-SM-027 | closed | anything | "Invalid transition: closed → *" | NO |
| TC-SM-028 | hypercare | draft | "Invalid transition: hypercare → draft" | NO |

#### Guard Condition Tests (P0 — Business Critical)
| ID | Scenario | Setup | Expected | Existing? |
|---|---|---|---|---|
| TC-SM-040 | Ready blocked: 0 completed rehearsals | Plan in approved, no rehearsals | 409: "At least one completed rehearsal required" | YES |
| TC-SM-041 | Ready succeeds: 1 completed rehearsal | Create + complete 1 rehearsal | 200: Status = ready | YES |
| TC-SM-042 | Execute blocked: pending go/no-go items | Plan in ready, 3 pending items | 409: "3 Go/No-Go item(s) still pending" | YES |
| TC-SM-043 | Execute succeeds: all go/no-go resolved | All items verdict=go or waived | 200: Status = executing, actual_start set | NO |
| TC-SM-044 | Execute succeeds: go + waived mix | 5 go + 2 waived | 200: Waived doesn't block | NO |
| TC-SM-045 | Close blocked: no exit signoff | Plan in hypercare, no signoff | 409: "Hypercare exit sign-off required" | YES |
| TC-SM-046 | Close succeeds: exit signoff approved | SignoffRecord with action=approved | 200: Status = closed | YES |
| TC-SM-047 | Close succeeds: override signoff | SignoffRecord with action=override_approved | 200: Override accepted | NO |

### 3.2 RunbookTask Transitions

#### Valid Transitions
| ID | From | To | Guard | Existing? |
|---|---|---|---|---|
| TC-TT-001 | not_started | in_progress | All predecessors completed/skipped | YES |
| TC-TT-002 | not_started | skipped | None | NO |
| TC-TT-003 | in_progress | completed | Sets actual_end, calculates duration | YES |
| TC-TT-004 | in_progress | failed | Sets actual_end | NO |
| TC-TT-005 | in_progress | rolled_back | None | NO |
| TC-TT-006 | completed | rolled_back | None | NO |
| TC-TT-007 | failed | in_progress | Retry (predecessors still valid) | NO |
| TC-TT-008 | failed | skipped | Skip failed task | NO |
| TC-TT-009 | skipped | not_started | Re-enable task | NO |
| TC-TT-010 | rolled_back | not_started | Re-enable after rollback | NO |

#### Invalid Transitions
| ID | From | To | Existing? |
|---|---|---|---|
| TC-TT-020 | not_started | completed | YES |
| TC-TT-021 | not_started | failed | NO |
| TC-TT-022 | completed | in_progress | NO |
| TC-TT-023 | completed | not_started | NO |
| TC-TT-024 | skipped | completed | NO |

#### Predecessor Guard Tests (P0)
| ID | Scenario | Setup | Expected | Existing? |
|---|---|---|---|---|
| TC-TT-040 | Start blocked: predecessor not_started | A→B, A in not_started | 409: "Predecessor ... is 'not_started'" | YES |
| TC-TT-041 | Start blocked: predecessor in_progress | A→B, A in in_progress | 409: "Predecessor ... is 'in_progress'" | NO |
| TC-TT-042 | Start succeeds: predecessor completed | A→B, A completed | 200: B transitions to in_progress | YES |
| TC-TT-043 | Start succeeds: predecessor skipped | A→B, A skipped | 200: B allowed to start | NO |
| TC-TT-044 | Start blocked: one of many predecessors incomplete | A→C, B→C; A completed, B not_started | 409: "Predecessor B is 'not_started'" | NO |
| TC-TT-045 | Start succeeds: all predecessors completed | A→C, B→C; A completed, B completed | 200: C starts | NO |
| TC-TT-046 | Cross-plan predecessor injection blocked | A (plan1) → B (plan2) dep via tampered FK | Dependency rejected (plan-scoped lookup) | NO |

### 3.3 Rehearsal Transitions

| ID | From | To | Existing? |
|---|---|---|---|
| TC-RT-001 | planned | in_progress | YES |
| TC-RT-002 | planned | cancelled | NO |
| TC-RT-003 | in_progress | completed | YES |
| TC-RT-004 | in_progress | cancelled | NO |
| TC-RT-005 | completed | (terminal) | YES |
| TC-RT-006 | cancelled | planned | NO |
| TC-RT-010 | planned | completed (invalid) | YES |

### 3.4 HypercareIncident Transitions

| ID | From | To | Side Effects | Existing? |
|---|---|---|---|---|
| TC-IT-001 | open | investigating | None | YES |
| TC-IT-002 | open | resolved | Sets resolved_at, calculates resolution_time | NO |
| TC-IT-003 | open | closed | Shortcut close | NO |
| TC-IT-004 | investigating | resolved | Sets resolved_at, calculates resolution_time | YES |
| TC-IT-005 | investigating | closed | Direct close | NO |
| TC-IT-006 | resolved | closed | Final close | NO |
| TC-IT-007 | resolved | open | Re-open: clears resolved_at/resolved_by/resolution_time | NO |
| TC-IT-008 | closed | open | Re-open from closed | NO |
| TC-IT-010 | open | open (self-transition) | Invalid | NO |
| TC-IT-011 | closed | investigating (invalid) | Invalid | NO |

---

## 4. Tenant Isolation Test Scenarios (ALWAYS P0)

### 4.1 CutoverPlan Isolation
| ID | Scenario | Setup | Action | Expected | Existing? |
|---|---|---|---|---|---|
| TC-TI-001 | Tenant A cannot list Tenant B's plans | Create plan in Tenant B | GET /plans?program_id=B | Empty list (not B's plans) | NO |
| TC-TI-002 | Tenant A cannot read Tenant B's plan | Create plan in Tenant B | GET /plans/:id as A | 404 (NOT 403) | NO |
| TC-TI-003 | Tenant A cannot update Tenant B's plan | Create plan in Tenant B | PUT /plans/:id as A | 404 | NO |
| TC-TI-004 | Tenant A cannot delete Tenant B's plan | Create plan in Tenant B | DELETE /plans/:id as A | 404 | NO |
| TC-TI-005 | Tenant A cannot transition Tenant B's plan | Create plan in Tenant B | POST /plans/:id/transition as A | 404 | NO |

### 4.2 RunbookTask Isolation
| ID | Scenario | Setup | Action | Expected | Existing? |
|---|---|---|---|---|---|
| TC-TI-010 | Cross-tenant task read blocked | Task in B | GET /tasks/:id as A | 404 | NO |
| TC-TI-011 | Cross-tenant task start blocked | Task in B | POST /tasks/:id/start-task as A | 404/ValueError | NO |
| TC-TI-012 | Cross-tenant dependency injection blocked | Task A (tenant A), Task B (tenant B) | POST dependency A→B | "Same plan" error | NO |

### 4.3 Incident Isolation
| ID | Scenario | Setup | Action | Expected | Existing? |
|---|---|---|---|---|---|
| TC-TI-020 | Cross-tenant incident list empty | 3 incidents in B | GET /incidents as A | Empty items[] | NO |
| TC-TI-021 | Cross-tenant incident read blocked | Incident in B | GET /incidents/:id as A | 404 | YES |
| TC-TI-022 | Cross-tenant incident update blocked | Incident in B | PUT /incidents/:id as A | 404 | NO |

### 4.4 War Room Isolation
| ID | Scenario | Setup | Action | Expected | Existing? |
|---|---|---|---|---|---|
| TC-TI-030 | Cross-tenant war room list empty | WR in B | GET /war-rooms as A | Empty | YES |
| TC-TI-031 | Cross-tenant war room detail blocked | WR in B | GET /war-rooms/:id as A | 404 | NO |

### 4.5 War Room Clock Isolation
| ID | Scenario | Setup | Action | Expected | Existing? |
|---|---|---|---|---|---|
| TC-TI-040 | Cross-tenant start-clock blocked | Plan in B | POST /start-clock as A | ValueError → 404 | NO |
| TC-TI-041 | Cross-tenant live-status blocked | Plan in B | GET /live-status as A | ValueError → 404 | YES |

### 4.6 Escalation Isolation
| ID | Scenario | Setup | Action | Expected | Existing? |
|---|---|---|---|---|---|
| TC-TI-050 | Cross-tenant escalation rules invisible | Rules in B | GET rules as A | Empty | YES |
| TC-TI-051 | Cross-tenant escalation events invisible | Events in B | GET events as A | Empty | YES |

### 4.7 Exit Criteria Isolation
| ID | Scenario | Setup | Action | Expected | Existing? |
|---|---|---|---|---|---|
| TC-TI-060 | Cross-tenant exit criteria invisible | Criteria in B | GET criteria as A | ValueError | YES |

---

## 5. Dependency Graph & Cycle Detection Tests

### 5.1 Dependency CRUD
| ID | Scenario | Expected | HTTP | Existing? |
|---|---|---|---|---|
| TC-DEP-001 | Add valid dependency (A→B) | Dependency created | 201 | YES |
| TC-DEP-002 | List predecessors and successors | Returns separate arrays | 200 | YES |
| TC-DEP-003 | Delete dependency | Dependency removed | 200 | YES |

### 5.2 Cycle Detection (P0 — prevents infinite loop)
| ID | Scenario | Setup | Expected | Existing? |
|---|---|---|---|---|
| TC-DEP-010 | Self-loop rejected | A→A | 409: "Adding this dependency would create a cycle" | NO |
| TC-DEP-011 | Direct cycle rejected | A→B, then B→A | 409: cycle detected | YES |
| TC-DEP-012 | Transitive cycle rejected | A→B→C, then C→A | 409: cycle detected | YES |
| TC-DEP-013 | Long chain cycle (5 nodes) | A→B→C→D→E, then E→A | 409: cycle detected | NO |
| TC-DEP-014 | Diamond DAG allowed | A→B, A→C, B→D, C→D | All valid (no cycle) | NO |

### 5.3 Same-Plan Enforcement
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-DEP-020 | Tasks in same plan: allowed | Dependency created | YES (implicit) |
| TC-DEP-021 | Tasks in different plans: rejected | 409: "Tasks must belong to the same cutover plan" | NO |

### 5.4 Duplicate Prevention
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-DEP-030 | Same dependency twice | 409: "Dependency already exists" | YES |

### 5.5 Critical Path Calculation (P1)
| ID | Scenario | Setup | Expected | Existing? |
|---|---|---|---|---|
| TC-CP-070 | Linear chain A→B→C | Weights: A=10, B=20, C=10 | Critical path = [A,B,C], total=40 | YES |
| TC-CP-071 | Two parallel chains | A→B (30min) and C→D (40min) | Critical path = [C,D] (longer) | NO |
| TC-CP-072 | Empty plan (no tasks) | No tasks | Returns empty [] | NO |
| TC-CP-073 | Single task (no deps) | 1 task, no deps | Returns [task_id] | NO |
| TC-CP-074 | Cycle in graph | A→B→A | ValueError: "Circular dependency detected" | NO |
| TC-CP-075 | is_critical_path flag set | After calculation | Tasks on path have is_critical_path=True, others False | YES |

---

## 6. SLA & Escalation Test Scenarios

### 6.1 SLA Deadline Calculation (P0)
| ID | Scenario | Input | Expected | Existing? |
|---|---|---|---|---|
| TC-SLA-001 | P1 incident: 15min response SLA | Create P1 incident | sla_response_deadline = created_at + 15min | YES |
| TC-SLA-002 | P1 incident: 4hr resolution SLA | Create P1 incident | sla_resolution_deadline = created_at + 240min | YES |
| TC-SLA-003 | P2 incident: 30min response SLA | Create P2 incident | sla_response_deadline = created_at + 30min | NO |
| TC-SLA-004 | P3 incident: 4hr response SLA | Create P3 incident | sla_response_deadline = created_at + 240min | NO |
| TC-SLA-005 | P4 incident: 8hr response SLA | Create P4 incident | sla_response_deadline = created_at + 480min | NO |
| TC-SLA-006 | No plan-specific SLA: use defaults | No seeded SLA targets | Falls back to _SLA_DEFAULTS | NO |
| TC-SLA-007 | Custom SLA overrides default | Seed SLA with P1=5min response | Uses 5min, not 15min | NO |

### 6.2 SLA Breach Detection (P0)
| ID | Scenario | Setup | Expected | Existing? |
|---|---|---|---|---|
| TC-SLA-010 | Response SLA not breached (on time) | first_response_at < deadline | sla_response_breached = False | NO |
| TC-SLA-011 | Response SLA breached (late) | first_response_at > deadline | sla_response_breached = True | YES |
| TC-SLA-012 | Response SLA breached (no response) | first_response_at = None, now > deadline | sla_response_breached = True | YES |
| TC-SLA-013 | Resolution SLA not breached (resolved on time) | resolved_at < deadline | sla_resolution_breached = False | NO |
| TC-SLA-014 | Resolution SLA breached (still open past deadline) | status=open, now > deadline | sla_resolution_breached = True | NO |
| TC-SLA-015 | Resolution SLA not breached (resolved before check) | status=resolved | sla_resolution_breached = False | NO |

### 6.3 Escalation Engine (P0)
| ID | Scenario | Setup | Expected | Existing? |
|---|---|---|---|---|
| TC-ESC-001 | Auto-trigger L1 on P1 no_response after 10min | P1 incident open 15min, no response | EscalationEvent created (L1, is_auto=True) | YES |
| TC-ESC-002 | No duplicate events at same level | Evaluate twice for same incident | Only 1 event at L1 (idempotent) | YES |
| TC-ESC-003 | Skip resolved incidents | Resolved P1 incident, overdue | No escalation event created | YES |
| TC-ESC-004 | Skip inactive rules | Rule with is_active=False | Rule skipped during evaluation | NO |
| TC-ESC-005 | Multi-level escalation chain | P1 open 120+ min | L1→L2→L3→vendor events in sequence | NO |
| TC-ESC-006 | Manual escalation succeeds | POST /escalate with level + notes | Event with is_auto=False | YES |
| TC-ESC-007 | Manual escalation blocked on resolved | Resolved incident | ValueError: can't escalate resolved | YES |
| TC-ESC-008 | Acknowledge escalation | POST /acknowledge | acknowledged_at set + acknowledged_by | YES |
| TC-ESC-009 | Acknowledge is idempotent | Acknowledge twice | No error, timestamp unchanged | YES |
| TC-ESC-010 | List unacknowledged only | `?unacknowledged_only=true` | Filters correctly | NO |

### 6.4 Escalation Rule CRUD (P1)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-ESC-020 | Create rule | Rule created | YES |
| TC-ESC-021 | Duplicate level_order rejected | IntegrityError | YES |
| TC-ESC-022 | Seed 8 default rules | 8 rules (P1:4, P2:2, P3:1, P4:1) | YES |
| TC-ESC-023 | Seed is idempotent | Returns empty on 2nd call | YES |
| TC-ESC-024 | Update rule trigger_after_min | Updated | YES |
| TC-ESC-025 | Delete rule | Deleted | YES |

---

## 7. Rehearsal & Metrics Test Scenarios

### 7.1 Rehearsal CRUD (P1)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-RH-001 | Create rehearsal (auto-number=1) | rehearsal_number=1 | YES |
| TC-RH-002 | 2nd rehearsal auto-number=2 | rehearsal_number=2 | YES |
| TC-RH-003 | List ordered by number | [1, 2, 3] | YES |
| TC-RH-004 | Update rehearsal | Fields updated | YES |
| TC-RH-005 | Delete rehearsal | Deleted | YES |

### 7.2 Metrics Computation (P1)
| ID | Scenario | Setup | Expected | Existing? |
|---|---|---|---|---|
| TC-RH-010 | Compute with 0 tasks | Empty plan | total=0, completed=0 | NO |
| TC-RH-011 | Compute with mixed statuses | 3 completed, 1 failed, 1 skipped, 5 not_started | total=10, completed=3, failed=1, skipped=1 | YES |
| TC-RH-012 | Variance: actual < planned (early) | planned=100min, actual=80min | variance=-20.0% | NO |
| TC-RH-013 | Variance: actual > planned (late) | planned=100min, actual=130min | variance=30.0% | NO |
| TC-RH-014 | runbook_revision_needed: failed > 0 | 1 failed task | runbook_revision_needed=True | NO |
| TC-RH-015 | runbook_revision_needed: |variance| > 15% | variance=20% | runbook_revision_needed=True | NO |
| TC-RH-016 | runbook_revision_needed: clean | 0 failed, variance=5% | runbook_revision_needed=False | NO |

---

## 8. Go/No-Go Decision Pack Tests

### 8.1 Go/No-Go CRUD & Seed (P0)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-GNG-001 | Seed 7 default items | All 7 source_domains present | YES |
| TC-GNG-002 | Seed twice rejected | 409: "items already exist" | YES |
| TC-GNG-003 | Create custom item | Item created with custom source | YES |
| TC-GNG-004 | Update verdict to "go" | Verdict updated, evaluated_at set | YES |
| TC-GNG-005 | Update verdict to "no_go" | Verdict updated | YES |
| TC-GNG-006 | Update verdict to "waived" | Verdict updated, evaluated_at set | NO |
| TC-GNG-007 | Delete item | Item deleted | YES |

### 8.2 Go/No-Go Summary Aggregation (P0)
| ID | Scenario | Setup | Expected | Existing? |
|---|---|---|---|---|
| TC-GNG-010 | All pending | 7 items, all pending | overall="pending" | YES |
| TC-GNG-011 | All go | 7 items, all go | overall="go" | YES |
| TC-GNG-012 | Mixed with no_go | 5 go + 2 no_go | overall="no_go" | YES |
| TC-GNG-013 | Mixed with pending | 5 go + 2 pending | overall="pending" | NO |
| TC-GNG-014 | All waived | 7 items, all waived | overall="go" | NO |
| TC-GNG-015 | Go + waived mix | 5 go + 2 waived | overall="go" | NO |
| TC-GNG-016 | No items | Empty plan | overall="no_items" | YES |
| TC-GNG-017 | Single no_go blocks all | 6 go + 1 no_go | overall="no_go" | NO |

---

## 9. War Room Clock & Live Status Tests

### 9.1 Start Clock (P0)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-WR-001 | Start clock on ready plan | Status→executing, actual_start=now | YES |
| TC-WR-002 | Start clock on non-ready plan | 422: "plan is 'draft', expected 'ready'" | YES |
| TC-WR-003 | Start clock with wrong tenant_id | ValueError: "not found for tenant" | NO |
| TC-WR-004 | Start clock with wrong program_id | ValueError: "not found for tenant" | NO |
| TC-WR-005 | Missing program_id in body | 400: "program_id and tenant_id required" | NO |

### 9.2 Task Execution (P0)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-WR-010 | Start task (no predecessors) | Status→in_progress, actual_start=now | YES |
| TC-WR-011 | Start task blocked by predecessor | ValueError: blocked by predecessor | NO |
| TC-WR-012 | Complete task | Status→completed, actual_end=now, delay_minutes calculated | YES |
| TC-WR-013 | Complete task early (negative delay) | delay_minutes < 0 | NO |
| TC-WR-014 | Complete critical path task late | Warning logged, delay_minutes > 0 | NO |
| TC-WR-015 | Flag issue on task | issue_note = "[timestamp] note" | YES |
| TC-WR-016 | Flag issue twice (append) | issue_note has 2 entries separated by newline | NO |
| TC-WR-017 | Flag issue with empty note | 400: "note is required" | NO |

### 9.3 Live Status Snapshot (P1)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-WR-020 | Live status: 0 tasks | tasks.total=0, completion=0% | NO |
| TC-WR-021 | Live status: mixed task states | Correct counts for each status | YES |
| TC-WR-022 | Live status: behind schedule | is_behind_schedule=True when critical path delayed | YES |
| TC-WR-023 | Live status: go/no-go counts | Correct passed/pending/failed counts | NO |
| TC-WR-024 | Live status: workstream breakdown | Per-workstream task counts | NO |
| TC-WR-025 | Live status: elapsed_minutes | elapsed = now - actual_start (correct) | NO |

---

## 10. Change Request & Comment Tests

### 10.1 Change Request CRUD (P1)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-CR-001 | Create CR (auto-code CR-001) | Code generated | YES |
| TC-CR-002 | Sequential CR codes | CR-001, CR-002, CR-003 | YES |
| TC-CR-003 | Approve CR | Status=approved, approved_at set | YES |
| TC-CR-004 | Reject CR | Status=rejected, rejection_reason stored | NO |
| TC-CR-005 | Approve already-approved CR | Error or no-op | NO |
| TC-CR-006 | Assign CR to war room | cr.war_room_id set | YES |

### 10.2 Incident Comments (P1)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-CMT-001 | Add public comment | is_internal=False, content stored | YES |
| TC-CMT-002 | Add internal comment | is_internal=True, not visible to customer | YES |
| TC-CMT-003 | List comments by created_at | Ordered chronologically | NO |
| TC-CMT-004 | Comment types: escalation | comment_type="escalation" | NO |
| TC-CMT-005 | Comment updates last_activity_at | incident.last_activity_at updated | NO |
| TC-CMT-006 | Empty content rejected | 400: content required | NO |

---

## 11. Exit Criteria & Signoff Tests

### 11.1 Exit Criteria (P0 — gates production closure)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-EX-001 | Seed 5 standard criteria | All 5 types present | YES |
| TC-EX-002 | Seed is idempotent | Returns empty on 2nd call | YES |
| TC-EX-003 | Auto-evaluate incident criterion | Checks open P1/P2 count = 0 | YES |
| TC-EX-004 | Auto-evaluate SLA criterion | Checks breach rate < threshold | NO |
| TC-EX-005 | Update manual criterion status | Status updated, evidence stored | YES |
| TC-EX-006 | Block manual "met" on auto criterion | ValueError: BR-E02 | YES |
| TC-EX-007 | Create custom criterion | Custom type accepted | YES |

### 11.2 Exit Signoff Gate (P0)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-EX-010 | Signoff blocked: mandatory not met | ValueError: "mandatory criteria not met" | YES |
| TC-EX-011 | Signoff succeeds: all mandatory met | SignoffRecord created | YES |
| TC-EX-012 | Plan close uses is_entity_approved() | Returns True for approved record | YES |
| TC-EX-013 | Plan close: no signoff record | is_entity_approved returns False | NO |
| TC-EX-014 | Plan close: rejected signoff | is_entity_approved returns False | NO |
| TC-EX-015 | Plan close: override_approved | is_entity_approved returns True | NO |

---

## 12. War Room Management Tests

### 12.1 War Room CRUD (P1)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-WRM-001 | Create war room (auto-code WR-001) | Code generated | YES |
| TC-WRM-002 | List war rooms by status | Filtered correctly | YES |
| TC-WRM-003 | Update war room fields | Updated | YES |
| TC-WRM-004 | Close war room | status=closed, closed_at=now | YES |
| TC-WRM-005 | Missing name rejected | ValueError | YES |

### 12.2 Assignment (P1)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-WRM-010 | Assign incident to WR | incident.war_room_id set | YES |
| TC-WRM-011 | Assign CR to WR | cr.war_room_id set | YES |
| TC-WRM-012 | Unassign incident | war_room_id cleared | YES |
| TC-WRM-013 | Assign to non-existent WR | Error | NO |

### 12.3 Analytics (P2)
| ID | Scenario | Expected | Existing? |
|---|---|---|---|
| TC-WRM-020 | Analytics: incident counts per WR | Correct open/total counts | YES |
| TC-WRM-021 | Analytics: empty war room | 0 incidents, 0 CRs | NO |
| TC-WRM-022 | to_dict includes computed counts | incident_count, open_incident_count, cr_count | NO |

---

## 13. Boundary Value & Edge Case Scenarios (P2)

### 13.1 String Field Boundaries
| ID | Field | Model | Max Length | Test Value | Expected |
|---|---|---|---|---|---|
| TC-BV-001 | name | CutoverPlan | 200 | 200 chars | Created |
| TC-BV-002 | name | CutoverPlan | 200 | 201 chars | Error |
| TC-BV-003 | title | RunbookTask | 300 | 300 chars | Created |
| TC-BV-004 | title | RunbookTask | 300 | 301 chars | Error |
| TC-BV-005 | title | HypercareIncident | 300 | 300 chars | Created |
| TC-BV-006 | criterion | GoNoGoItem | 300 | 300 chars | Created |
| TC-BV-007 | code | CutoverPlan | 30 | Generated (CUT-001) | 8 chars (within limit) |
| TC-BV-008 | name | HypercareWarRoom | 255 | 255 chars | Created |

### 13.2 Numeric Boundaries
| ID | Field | Test Value | Expected |
|---|---|---|---|
| TC-BV-010 | planned_duration_min | 0 | Accepted (0 min task) |
| TC-BV-011 | planned_duration_min | -1 | Should reject or accept? (FLAG) |
| TC-BV-012 | lag_minutes | 0 | Default behavior |
| TC-BV-013 | lag_minutes | -1 | Should reject or accept? (FLAG) |
| TC-BV-014 | hypercare_duration_weeks | 0 | Accepted |
| TC-BV-015 | hypercare_duration_weeks | 52 | Accepted |

### 13.3 Datetime Parsing
| ID | Input Format | Expected |
|---|---|---|
| TC-BV-020 | "2026-03-01T22:00:00" | Parsed correctly |
| TC-BV-021 | "2026-03-01T22:00" | Parsed (no seconds) |
| TC-BV-022 | "2026-03-01 22:00:00" | Parsed (space separator) |
| TC-BV-023 | "2026-03-01" | Parsed (date only) |
| TC-BV-024 | "" (empty string) | Returns None |
| TC-BV-025 | "not-a-date" | ValueError raised |
| TC-BV-026 | null/None | Returns None |

### 13.4 Unicode & Special Characters
| ID | Field | Test Value | Expected |
|---|---|---|---|
| TC-BV-030 | name | "SAP S/4HANA — Finance & Procurement" | UTF-8 preserved |
| TC-BV-031 | description | "中文描述 Chinese Description" | UTF-8 preserved |
| TC-BV-032 | criterion | "Ürün Kalitesi ≥ 95%" | UTF-8 preserved |
| TC-BV-033 | title | "Task: Use `jq` to parse JSON" | Backticks preserved |

### 13.5 Concurrency & Race Conditions (P2)
| ID | Scenario | Expected |
|---|---|---|
| TC-BV-040 | Simultaneous plan creation (code collision) | UNIQUE constraint prevents duplicate codes |
| TC-BV-041 | Simultaneous task completion | Both succeed (no shared state) |
| TC-BV-042 | Simultaneous incident code generation | UNIQUE prevents collision |

---

## 14. Hypercare Metrics Aggregation Tests (P1)

| ID | Scenario | Setup | Expected | Existing? |
|---|---|---|---|---|
| TC-HM-001 | Metrics with 0 incidents | Empty plan | total=0, sla_compliance_pct=None | YES |
| TC-HM-002 | Metrics with mixed severity | 2xP1, 3xP2, 1xP3 | by_severity correct | YES |
| TC-HM-003 | Metrics with mixed status | 2 open, 1 investigating, 3 resolved, 1 closed | by_status correct | NO |
| TC-HM-004 | SLA compliance: all met | 5 resolved within SLA | sla_compliance_pct = 100.0 | NO |
| TC-HM-005 | SLA compliance: 50% | 2 met, 2 breached | sla_compliance_pct = 50.0 | NO |
| TC-HM-006 | SLA compliance: no resolved | All open | sla_compliance_pct = None | NO |
| TC-HM-007 | Hypercare dates in response | Plan has hypercare_start/end | Dates serialized correctly | YES |

---

## 15. UI Test Scenarios (Manual — Human Executes)

### 15.1 Cutover Hub Navigation
| ID | Scenario | Steps | Expected |
|---|---|---|---|
| TC-UI-001 | No program selected | Navigate to Cutover Hub without program | Empty state: "Select a program first" |
| TC-UI-002 | Tab switching | Click Plans → Runbook → Rehearsals → Go/No-Go → Hypercare | Each tab renders correct content |
| TC-UI-003 | Plan card selection | Click plan card | Card highlighted, detail panel loads |
| TC-UI-004 | Create plan modal | Click "+ New Plan" | Modal opens with program_id pre-filled |
| TC-UI-005 | Status badge colors | View plans in different statuses | Each status has distinct color |

### 15.2 Runbook Tab
| ID | Scenario | Steps | Expected |
|---|---|---|---|
| TC-UI-010 | Empty runbook | No scope items | "No scope items" message |
| TC-UI-011 | Task hierarchy | Scope items with tasks | Tree structure visible |
| TC-UI-012 | Task status badges | Tasks in various states | Correct badge per status |
| TC-UI-013 | Dependency indicator | Tasks with predecessors | Dependency shown in task detail |

### 15.3 Go/No-Go Tab
| ID | Scenario | Steps | Expected |
|---|---|---|---|
| TC-UI-020 | Seed default items | Click "Seed Defaults" | 7 items appear |
| TC-UI-021 | Verdict update | Click go/no-go/waived dropdown | Badge updates immediately |
| TC-UI-022 | Summary badge | All items go | Green "GO" summary badge |
| TC-UI-023 | Summary badge | Any no_go | Red "NO-GO" summary badge |

### 15.4 Hypercare Tab
| ID | Scenario | Steps | Expected |
|---|---|---|---|
| TC-UI-030 | Incident list | Navigate to Hypercare tab | Incidents sorted by reported_at DESC |
| TC-UI-031 | SLA breach indicator | Incident past SLA | Red SLA badge visible |
| TC-UI-032 | Filter by severity | Select P1 filter | Only P1 incidents shown |
| TC-UI-033 | Create incident | Click "New Incident" | Form with severity/category selectors |

### 15.5 War Room Dashboard
| ID | Scenario | Steps | Expected |
|---|---|---|---|
| TC-UI-040 | System health indicator | Open P1 incident exists | RED health status |
| TC-UI-041 | System health indicator | Open P2, no P1 | YELLOW health status |
| TC-UI-042 | System health indicator | No open P1/P2 | GREEN health status |
| TC-UI-043 | Live clock display | Plan in executing | Elapsed time ticking |
| TC-UI-044 | Task completion rate | Mixed task states | Percentage correct |

---

## 16. Traceability Matrix

| Business Rule | Description | Test Cases | Coverage |
|---|---|---|---|
| BR-01 | Plan code auto-generated (CUT-###) | TC-CP-001, TC-CP-002 | FULL |
| BR-02 | Plan lifecycle follows state machine | TC-SM-001 to TC-SM-028 | FULL |
| BR-03 | Ready requires completed rehearsal | TC-SM-040, TC-SM-041 | FULL |
| BR-04 | Execute requires 0 pending go/no-go | TC-SM-042, TC-SM-043, TC-SM-044 | FULL |
| BR-05 | Task predecessor guard | TC-TT-040 to TC-TT-046 | FULL |
| BR-06 | Dependency cycle detection | TC-DEP-010 to TC-DEP-014 | FULL |
| BR-07 | Tasks must be in same plan | TC-DEP-020, TC-DEP-021 | FULL |
| BR-08 | Incident SLA auto-calculated | TC-SLA-001 to TC-SLA-007 | FULL |
| BR-09 | SLA breach lazy evaluation | TC-SLA-010 to TC-SLA-015 | FULL |
| BR-10 | Escalation engine no duplicate events (BR-ES06) | TC-ESC-002 | FULL |
| BR-11 | Escalation skips resolved incidents (BR-ES02) | TC-ESC-003 | FULL |
| BR-12 | Manual escalation blocked on resolved (BR-ES03) | TC-ESC-007 | FULL |
| BR-13 | Acknowledge is idempotent (BR-ES04) | TC-ESC-009 | FULL |
| BR-14 | Exit signoff blocks unmet criteria (BR-E01) | TC-EX-010 | FULL |
| BR-15 | Manual met blocked on auto criteria (BR-E02) | TC-EX-006 | FULL |
| BR-E05 | Hypercare→closed requires signoff | TC-SM-045, TC-SM-046, TC-SM-047 | FULL |
| BR-L01 | Lesson only from resolved incident | test_hypercare_phase2 | FULL |
| BR-TI | Tenant isolation on ALL entities | TC-TI-001 to TC-TI-060 | FULL |

### Coverage Gap Alerts

| Gap | Description | Risk | Recommendation |
|---|---|---|---|
| GAP-01 | `list_plans()` without program_id returns ALL plans cross-program | MEDIUM | Add program_id validation or tenant filter in list_plans() |
| GAP-02 | `get_or_404()` does not filter by tenant_id | HIGH | Relies on global filter — verify with explicit test |
| GAP-03 | No input length validation in blueprints | MEDIUM | DB constraint catches it as 500, should be 400 |
| GAP-04 | `environment` field accepts any string (no enum check) | LOW | Consider adding CHECK constraint or blueprint validation |
| GAP-05 | `planned_duration_min` accepts negative values | LOW | Add CHECK constraint planned_duration_min >= 0 |
| GAP-06 | CutoverPlan.code UNIQUE globally but generated from global count — race condition possible | MEDIUM | Use DB sequence or retry logic |
| GAP-07 | No permission check (`@require_permission`) on cutover_bp routes | HIGH | Verify middleware applies permissions |
| GAP-08 | Incident `resolution_time_min` overflow for long-running incidents | LOW | 32-bit int limit = ~4 years, unlikely but should test |

---

## 17. Test Data Requirements

### Seed Data for Test Environment
| Entity | Count | Variants |
|---|---|---|
| Tenants | 2 | Tenant A (default), Tenant B (isolation tests) |
| Programs per tenant | 2 | Program 1 (active), Program 2 (isolation) |
| CutoverPlans per program | 3 | 1 draft, 1 executing, 1 hypercare |
| ScopeItems per plan | 3 | data_load, interface, custom |
| RunbookTasks per scope item | 5 | Mixed statuses: 2 completed, 1 in_progress, 2 not_started |
| TaskDependencies | 4 | Linear chain + diamond pattern |
| Rehearsals per plan | 2 | 1 completed, 1 planned |
| GoNoGoItems per plan | 7 | Seeded defaults (mixed verdicts) |
| HypercareIncidents per plan | 6 | 2xP1, 2xP2, 1xP3, 1xP4; mixed statuses |
| HypercareSLA per plan | 4 | Seeded P1-P4 defaults |
| EscalationRules per plan | 8 | Seeded 8-rule matrix |
| EscalationEvents | 3 | 1 auto, 1 manual, 1 acknowledged |
| ChangeRequests | 3 | draft, approved, rejected |
| WarRooms | 2 | 1 active, 1 closed |
| IncidentComments | 4 | 2 public, 2 internal |
| ExitCriteria | 5 | Seeded defaults |

---

## 18. Coder Agent Instructions

### What to Implement as Automated Tests
- **ALL P0 scenarios (78)** → pytest, MUST pass before merge
- **ALL P1 scenarios (102)** → pytest, SHOULD pass before merge
- **Tenant isolation tests (Section 4)** → pytest, MUST pass (NON-NEGOTIABLE)
- **State machine tests (Section 3)** → pytest, MUST pass
- **Dependency/cycle tests (Section 5)** → pytest, MUST pass

### What Remains Manual (Human Tests)
- UI scenarios (Section 15) → Human executes from checklist
- Performance scenarios → Run after integration, not on every commit

### Test File Structure
```
tests/
├── test_cutover_plan_create.py      ← TC-CP-001 to TC-CP-019
├── test_cutover_plan_read.py        ← TC-CP-020 to TC-CP-032
├── test_cutover_plan_update.py      ← TC-CP-040 to TC-CP-044
├── test_cutover_plan_delete.py      ← TC-CP-050 to TC-CP-052
├── test_cutover_plan_transition.py  ← TC-SM-001 to TC-SM-047
├── test_cutover_task_transition.py  ← TC-TT-001 to TC-TT-045
├── test_cutover_dependency.py       ← TC-DEP-001 to TC-DEP-030
├── test_cutover_critical_path.py    ← TC-CP-070 to TC-CP-075
├── test_cutover_rehearsal.py        ← TC-RH-001 to TC-RH-016
├── test_cutover_gonogo.py           ← TC-GNG-001 to TC-GNG-017
├── test_cutover_sla.py              ← TC-SLA-001 to TC-SLA-015
├── test_cutover_escalation.py       ← TC-ESC-001 to TC-ESC-025
├── test_cutover_incident.py         ← TC-IT-001 to TC-IT-011
├── test_cutover_warroom_clock.py    ← TC-WR-001 to TC-WR-025
├── test_cutover_cr_comments.py      ← TC-CR-001 to TC-CMT-006
├── test_cutover_exit_signoff.py     ← TC-EX-001 to TC-EX-015
├── test_cutover_war_room_mgmt.py    ← TC-WRM-001 to TC-WRM-022
├── test_cutover_tenant_isolation.py ← TC-TI-001 to TC-TI-060 (CRITICAL)
├── test_cutover_boundary.py         ← TC-BV-001 to TC-BV-042
└── test_cutover_metrics.py          ← TC-HM-001 to TC-HM-007
```

### Test Naming Convention
```python
def test_TC_CP_001_create_plan_with_required_fields_returns_201(client):
def test_TC_SM_040_ready_blocked_without_completed_rehearsal_returns_409(client):
def test_TC_TI_001_tenant_a_cannot_list_tenant_b_plans(client_a, client_b):
def test_TC_DEP_012_transitive_cycle_a_b_c_a_rejected_returns_409(client):
def test_TC_SLA_001_p1_incident_response_deadline_15_minutes(client):
```

### Handoff Summary
```
Total automated scenarios:     247
P0 (MUST pass):                 78
P1 (SHOULD pass):              102
P2 (NICE to have):              67
Already covered by tests:      138
NEW scenarios to implement:    109
Test files to create:           20
Critical: Tenant isolation (Section 4) is NON-NEGOTIABLE
```

---

## 19. Identified Design Gaps (Flagged for Architect)

| ID | Gap | Severity | Recommendation |
|---|---|---|---|
| DG-01 | `list_plans()` without program_id leaks all plans | HIGH | Require program_id parameter or auto-filter by tenant |
| DG-02 | `get_or_404()` uses `db.session.get()` which bypasses tenant filter | HIGH | Verify tenant middleware applies to `.get()` calls |
| DG-03 | No `@require_permission` decorators visible on cutover_bp routes | HIGH | Verify blueprint_permissions middleware covers all routes |
| DG-04 | Plan code generated from global COUNT — race condition on concurrent creates | MEDIUM | Use DB SEQUENCE or UUID prefix |
| DG-05 | SLA breach detection is lazy (not background) — breaches only detected on API call | MEDIUM | Phase B: Add APScheduler job for real-time SLA monitoring |
| DG-06 | Escalation engine is on-demand (POST /evaluate) — not automatic | MEDIUM | Phase B: Add periodic evaluation job |
| DG-07 | `planned_duration_min` and `lag_minutes` accept negative values | LOW | Add CHECK constraints |
| DG-08 | `environment` field has no server-side enum validation | LOW | Add CHECK constraint: PRD, QAS, Sandbox |
| DG-09 | No audit trail for plan transitions (only current status stored) | MEDIUM | Consider status_history table or event log |
| DG-10 | `to_dict()` calls `.count()` on lazy relationships — N+1 risk on list endpoints | LOW | Pre-aggregate counts in service layer |
