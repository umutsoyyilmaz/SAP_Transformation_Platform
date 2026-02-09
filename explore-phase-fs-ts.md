# SAP Activate Explore Phase Management System
## Functional & Technical Specification v1.0

---

## 1. Document Overview

### 1.1 Purpose
This document defines the complete Functional Specification (FS) and Technical Specification (TS) for the **Explore Phase Management System** within the ProjektCoPilot platform. It covers 4 interconnected modules that manage the SAP Activate Explore phase — from process hierarchy navigation through Fit-to-Standard workshop execution to requirement and open item lifecycle management.

### 1.2 Module Map

```
+--------------------------------------------------------------+
|                    EXPLORE PHASE SYSTEM                       |
+--------------+--------------+-------------+------------------+
|  Module A    |  Module B    |  Module C   |  Module D        |
|  Process     |  Workshop    |  Workshop   |  Requirement     |
|  Hierarchy   |  Hub         |  Detail     |  & Open Item Hub |
|  Manager     |              |             |                  |
+--------------+--------------+-------------+------------------+
| L1-L4 tree   | 300+ WS list | Single WS   | Cross-WS        |
| Scope matrix | Table/Kanban | Steps+Fit   | REQ registry     |
| Fit overview | Capacity     | Decisions   | OI tracker       |
| Navigation   | Filtering    | Capture     | Lifecycle        |
+--------------+--------------+-------------+------------------+
         |              |             |              |
+--------------------------------------------------------------+
|              SHARED DATA MODEL & API LAYER                    |
+--------------------------------------------------------------+
```

### 1.3 Navigation Flow

```
Module A: Process Hierarchy Manager
    +- Click workshop badge on L3 node -> Module B (filtered to that scope item)
    +- Click requirement badge on L4 node -> Module D (filtered to that requirement)
    +- Click scope matrix row -> Module C (opens that workshop)

Module B: Workshop Hub
    +- Click table row -> Module C (workshop detail)
    +- Click open item count -> Module D (OI tab, filtered to that workshop)
    +- Click requirement count -> Module D (REQ tab, filtered to that workshop)

Module C: Workshop Detail
    +- Add requirement in process step -> Creates REQ in Module D
    +- Add open item in process step -> Creates OI in Module D
    +- Close/navigate back -> Module B

Module D: Requirement & Open Item Hub
    +- Click workshop code link -> Module C (opens source workshop)
    +- Click scope item code -> Module A (navigates to that L3 node)
    +- Click linked OI/REQ -> Jumps to that item within Module D
```

---

## 2. Data Model

### 2.1 Entity Relationship Diagram

```
ProcessLevel (L1-L4)
+-- 1:N -> ProcessLevel (self-referential: parent_id)
+-- N:M -> Workshop (via WorkshopScopeItem)
+-- 1:N -> Requirement (via process_step -> process_level_id)
+-- 1:N -> OpenItem (via process_step -> process_level_id)

Workshop
+-- 1:N -> WorkshopScopeItem
+-- 1:N -> WorkshopAttendee
+-- 1:N -> WorkshopAgendaItem
+-- 1:N -> ProcessStep (workshop execution context)
+-- N:1 -> Facilitator (User)

ProcessStep (L4 subprocess within workshop context)
+-- N:1 -> Workshop
+-- N:1 -> ProcessLevel (L4 reference)
+-- 1:N -> Decision
+-- 1:N -> OpenItem
+-- 1:N -> Requirement

Requirement
+-- N:1 -> ProcessStep (origin)
+-- N:1 -> Workshop (origin)
+-- N:1 -> ProcessLevel (scope item L3)
+-- N:M -> OpenItem (via RequirementOpenItemLink)
+-- N:M -> Requirement (self-ref: dependencies)
+-- 1:1 -> CloudALMSync (optional)

OpenItem
+-- N:1 -> ProcessStep (origin)
+-- N:1 -> Workshop (origin)
+-- N:1 -> User (assignee)
+-- N:M -> Requirement (via RequirementOpenItemLink)
+-- 1:N -> OpenItemComment
```

### 2.2 Table Definitions

#### 2.2.1 `process_level`

Stores the L1-L4 SAP Signavio process hierarchy. Self-referential tree structure.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `parent_id` | UUID | YES | FK -> process_level (NULL for L1 roots) |
| `level` | INTEGER | NO | 1=Value Chain, 2=Process Area, 3=E2E Process, 4=Sub-Process |
| `code` | VARCHAR(20) | NO | Unique within project. L1: "VC-001", L2: "PA-FIN", L3: "J58", L4: "J58.01" |
| `name` | VARCHAR(200) | NO | Process name |
| `description` | TEXT | YES | Detailed description |
| `scope_status` | ENUM | NO | `in_scope`, `out_of_scope`, `under_review`. Default: `under_review` |
| `fit_status` | ENUM | YES | `fit`, `gap`, `partial_fit`, `pending`. NULL for L1/L2 (calculated). Set at L3/L4. |
| `scope_item_code` | VARCHAR(10) | YES | SAP scope item code (L3 only, e.g., "J58", "BD9") |
| `bpmn_available` | BOOLEAN | NO | Whether BPMN diagram exists in Signavio. Default: false |
| `bpmn_reference` | VARCHAR(500) | YES | Signavio BPMN URL or reference ID |
| `process_area_code` | VARCHAR(5) | YES | Denormalized: FI, CO, SD, MM, PP, QM, PM, WM, HR, PS |
| `wave` | INTEGER | YES | Implementation wave (1-4+) |
| `sort_order` | INTEGER | NO | Display order within parent. Default: 0 |
| `created_at` | TIMESTAMP | NO | |
| `updated_at` | TIMESTAMP | NO | |

**Indexes:**
- `idx_pl_project_parent` ON (`project_id`, `parent_id`)
- `idx_pl_project_level` ON (`project_id`, `level`)
- `idx_pl_scope_item` ON (`project_id`, `scope_item_code`)
- `idx_pl_code` UNIQUE ON (`project_id`, `code`)

**Constraints:**
- `level` must be `parent.level + 1` (except L1 where parent_id is NULL)
- `scope_item_code` required when `level = 3`
- `fit_status` required when `level IN (3, 4)`

**Computed Fields (calculated via query, not stored):**
- `fit_summary` for L1/L2/L3: aggregate {fit, gap, partial_fit, pending} from descendant L4 nodes
- `completion_pct`: percentage of descendant L4 nodes with fit_status != 'pending'

---

#### 2.2.2 `workshop`

Each Fit-to-Standard workshop session. A scope item (L3) may have 1-N workshops.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `code` | VARCHAR(20) | NO | Auto-generated: WS-{area}-{seq}{session_letter} |
| `name` | VARCHAR(200) | NO | Workshop title |
| `type` | ENUM | NO | `fit_to_standard`, `deep_dive`, `follow_up`, `delta_design`. Default: `fit_to_standard` |
| `status` | ENUM | NO | `draft`, `scheduled`, `in_progress`, `completed`, `cancelled`. Default: `draft` |
| `date` | DATE | YES | Scheduled date |
| `start_time` | TIME | YES | |
| `end_time` | TIME | YES | |
| `facilitator_id` | UUID | YES | FK -> user |
| `process_area` | VARCHAR(5) | NO | FI, CO, SD, MM, PP, QM, PM, WM, HR, PS |
| `wave` | INTEGER | YES | Implementation wave |
| `session_number` | INTEGER | NO | Session sequence. Default: 1 |
| `total_sessions` | INTEGER | NO | Total planned. Default: 1 |
| `location` | VARCHAR(200) | YES | |
| `meeting_link` | VARCHAR(500) | YES | |
| `notes` | TEXT | YES | |
| `summary` | TEXT | YES | AI-generated or manual summary |
| `created_at` | TIMESTAMP | NO | |
| `updated_at` | TIMESTAMP | NO | |
| `started_at` | TIMESTAMP | YES | |
| `completed_at` | TIMESTAMP | YES | |

**Indexes:**
- `idx_ws_project_status` ON (`project_id`, `status`)
- `idx_ws_project_date` ON (`project_id`, `date`)
- `idx_ws_project_area` ON (`project_id`, `process_area`)
- `idx_ws_facilitator` ON (`facilitator_id`, `date`)
- `idx_ws_code` UNIQUE ON (`project_id`, `code`)

**Code Generation:** `WS-{area}-{seq}{letter}` Examples: WS-SD-01, WS-FI-03A, WS-FI-03B

---

#### 2.2.3 `workshop_scope_item`

N:M between Workshop and ProcessLevel (L3 scope items).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `workshop_id` | UUID | NO | FK -> workshop |
| `process_level_id` | UUID | NO | FK -> process_level (must be level=3) |
| `sort_order` | INTEGER | NO | Default: 0 |

**Constraint:** Referenced process_level must have level = 3. Unique: (workshop_id, process_level_id)

---

#### 2.2.4 `workshop_attendee`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `workshop_id` | UUID | NO | FK -> workshop |
| `user_id` | UUID | YES | FK -> user (if registered) |
| `name` | VARCHAR(100) | NO | Display name |
| `role` | VARCHAR(100) | YES | E.g., "Sales Director", "SD Consultant" |
| `organization` | ENUM | NO | `customer`, `consultant`, `partner`, `vendor` |
| `attendance_status` | ENUM | NO | `confirmed`, `tentative`, `declined`, `present`, `absent`. Default: `confirmed` |
| `is_required` | BOOLEAN | NO | Default: true |

---

#### 2.2.5 `workshop_agenda_item`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `workshop_id` | UUID | NO | FK -> workshop |
| `time` | TIME | NO | Start time |
| `title` | VARCHAR(200) | NO | |
| `duration_minutes` | INTEGER | NO | |
| `type` | ENUM | NO | `session`, `break`, `demo`, `discussion`, `wrap_up`. Default: `session` |
| `sort_order` | INTEGER | NO | |
| `notes` | TEXT | YES | |

---

#### 2.2.6 `process_step`

Workshop-scoped execution record for each L4 sub-process discussed. Created when workshop starts. Links L4 process definition to workshop-specific outcomes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `workshop_id` | UUID | NO | FK -> workshop |
| `process_level_id` | UUID | NO | FK -> process_level (must be level=4) |
| `sort_order` | INTEGER | NO | |
| `fit_decision` | ENUM | YES | `fit`, `gap`, `partial_fit`. NULL = not assessed |
| `notes` | TEXT | YES | Discussion notes |
| `demo_shown` | BOOLEAN | NO | Default: false |
| `bpmn_reviewed` | BOOLEAN | NO | Default: false |
| `assessed_at` | TIMESTAMP | YES | |
| `assessed_by` | UUID | YES | FK -> user |

**Constraints:** process_level must have level=4. Unique: (workshop_id, process_level_id)

**Business Rule:** When fit_decision is set, it propagates to process_level.fit_status

---

#### 2.2.7 `decision`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `process_step_id` | UUID | NO | FK -> process_step |
| `code` | VARCHAR(10) | NO | Auto: DEC-{seq}. Project-wide. |
| `text` | TEXT | NO | Decision statement |
| `decided_by` | VARCHAR(100) | NO | Name of decider |
| `decided_by_user_id` | UUID | YES | FK -> user |
| `category` | ENUM | NO | `process`, `technical`, `scope`, `organizational`, `data`. Default: `process` |
| `status` | ENUM | NO | `active`, `superseded`, `revoked`. Default: `active` |
| `rationale` | TEXT | YES | |
| `created_at` | TIMESTAMP | NO | |

---

#### 2.2.8 `open_item`

Action items and investigation tasks. Born in workshops but live independently.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `process_step_id` | UUID | YES | FK -> process_step (origin) |
| `workshop_id` | UUID | YES | FK -> workshop (origin) |
| `process_level_id` | UUID | YES | FK -> process_level (scope item context) |
| `code` | VARCHAR(10) | NO | Auto: OI-{seq}. Project-wide. |
| `title` | VARCHAR(500) | NO | |
| `description` | TEXT | YES | |
| `status` | ENUM | NO | `open`, `in_progress`, `blocked`, `closed`, `cancelled`. Default: `open` |
| `priority` | ENUM | NO | `P1`, `P2`, `P3`, `P4`. Default: `P2` |
| `category` | ENUM | NO | `clarification`, `technical`, `scope`, `data`, `process`, `organizational`. Default: `clarification` |
| `assignee_id` | UUID | YES | FK -> user |
| `assignee_name` | VARCHAR(100) | YES | |
| `created_by_id` | UUID | NO | FK -> user |
| `due_date` | DATE | YES | |
| `resolved_date` | DATE | YES | |
| `resolution` | TEXT | YES | |
| `blocked_reason` | TEXT | YES | |
| `process_area` | VARCHAR(5) | YES | Denormalized |
| `wave` | INTEGER | YES | Denormalized |
| `created_at` | TIMESTAMP | NO | |
| `updated_at` | TIMESTAMP | NO | |

**Indexes:**
- `idx_oi_project_status` ON (`project_id`, `status`)
- `idx_oi_assignee_status` ON (`assignee_id`, `status`)
- `idx_oi_project_due` ON (`project_id`, `due_date`) WHERE status IN ('open','in_progress','blocked')
- `idx_oi_workshop` ON (`workshop_id`)
- `idx_oi_code` UNIQUE ON (`project_id`, `code`)

**Computed:**
- `is_overdue`: status IN ('open','in_progress') AND due_date < CURRENT_DATE
- `days_overdue`: CURRENT_DATE - due_date (when overdue)

---

#### 2.2.9 `requirement`

Delta requirements from Fit-to-Standard analysis. Full lifecycle from capture to verification.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `process_step_id` | UUID | YES | FK -> process_step (origin) |
| `workshop_id` | UUID | YES | FK -> workshop (origin) |
| `process_level_id` | UUID | YES | FK -> process_level (L4 where gap identified) |
| `scope_item_id` | UUID | YES | FK -> process_level (L3, denormalized) |
| `code` | VARCHAR(10) | NO | Auto: REQ-{seq}. Project-wide. |
| `title` | VARCHAR(500) | NO | |
| `description` | TEXT | YES | |
| `priority` | ENUM | NO | `P1`, `P2`, `P3`, `P4`. Default: `P2` |
| `type` | ENUM | NO | `development`, `configuration`, `integration`, `migration`, `enhancement`, `workaround`. Default: `configuration` |
| `fit_status` | ENUM | NO | `gap`, `partial_fit`. What triggered this requirement. |
| `status` | ENUM | NO | See lifecycle below. Default: `draft` |
| `effort_hours` | INTEGER | YES | Estimated person-hours |
| `effort_story_points` | INTEGER | YES | Agile alternative |
| `complexity` | ENUM | YES | `low`, `medium`, `high`, `very_high` |
| `created_by_id` | UUID | NO | FK -> user |
| `created_by_name` | VARCHAR(100) | YES | |
| `approved_by_id` | UUID | YES | FK -> user |
| `approved_by_name` | VARCHAR(100) | YES | |
| `approved_at` | TIMESTAMP | YES | |
| `process_area` | VARCHAR(5) | YES | Denormalized |
| `wave` | INTEGER | YES | Denormalized |
| `alm_id` | VARCHAR(50) | YES | Cloud ALM item ID |
| `alm_synced` | BOOLEAN | NO | Default: false |
| `alm_synced_at` | TIMESTAMP | YES | |
| `alm_sync_status` | ENUM | YES | `pending`, `synced`, `sync_error`, `out_of_sync` |
| `deferred_to_phase` | VARCHAR(50) | YES | |
| `rejection_reason` | TEXT | YES | |
| `created_at` | TIMESTAMP | NO | |
| `updated_at` | TIMESTAMP | NO | |

**Requirement Status Lifecycle:**

```
                    +------------+
                    |   draft    | <-- Created in workshop or manually
                    +-----+------+
                          | submit_for_review
                    +-----v------+
               +----+under_review+----+
               |    +------------+    |
          approve                   reject
               |                      |
        +------v-----+         +------v-----+
        |  approved  |         |  rejected  | (terminal)
        +------+-----+         +------------+
               | push_to_alm
        +------v-----+    +------------+
        | in_backlog |    |  deferred  | (can re-enter at draft)
        +------+-----+    +------------+
               | mark_realized
        +------v-----+
        |  realized  |
        +------+-----+
               | verify
        +------v-----+
        |  verified  | (terminal)
        +------------+
```

**Valid Status Transitions:**

| From | To | Action | Permission |
|------|-----|--------|------------|
| draft | under_review | submit_for_review | Creator, PM |
| draft | deferred | defer | PM, Steering |
| under_review | approved | approve | Module Lead, PM |
| under_review | rejected | reject | Module Lead, PM |
| under_review | draft | return_to_draft | Module Lead |
| approved | in_backlog | push_to_alm | PM, Tech Lead |
| approved | deferred | defer | PM, Steering |
| in_backlog | realized | mark_realized | Developer, Tech Lead |
| realized | verified | verify | Business Tester, Module Lead |
| deferred | draft | reactivate | PM |

**Indexes:**
- `idx_req_project_status` ON (`project_id`, `status`)
- `idx_req_project_priority` ON (`project_id`, `priority`)
- `idx_req_project_area` ON (`project_id`, `process_area`)
- `idx_req_workshop` ON (`workshop_id`)
- `idx_req_scope_item` ON (`scope_item_id`)
- `idx_req_alm` ON (`alm_id`) WHERE alm_id IS NOT NULL
- `idx_req_code` UNIQUE ON (`project_id`, `code`)

---

#### 2.2.10 `requirement_open_item_link`

N:M between requirements and open items.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `requirement_id` | UUID | NO | FK -> requirement |
| `open_item_id` | UUID | NO | FK -> open_item |
| `link_type` | ENUM | NO | `blocks` (OI blocks REQ), `related`, `triggers` |
| `created_at` | TIMESTAMP | NO | |

Unique: (requirement_id, open_item_id)

---

#### 2.2.11 `requirement_dependency`

Self-referential N:M for requirement-to-requirement dependencies.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `requirement_id` | UUID | NO | FK -> requirement (dependent) |
| `depends_on_id` | UUID | NO | FK -> requirement (dependency) |
| `dependency_type` | ENUM | NO | `blocks`, `related`, `extends` |
| `created_at` | TIMESTAMP | NO | |

Unique: (requirement_id, depends_on_id). No self-reference.

---

#### 2.2.12 `open_item_comment`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `open_item_id` | UUID | NO | FK -> open_item |
| `user_id` | UUID | NO | FK -> user |
| `type` | ENUM | NO | `comment`, `status_change`, `reassignment`, `due_date_change` |
| `content` | TEXT | NO | |
| `created_at` | TIMESTAMP | NO | |

---

#### 2.2.13 `cloud_alm_sync_log`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `requirement_id` | UUID | NO | FK -> requirement |
| `sync_direction` | ENUM | NO | `push`, `pull` |
| `sync_status` | ENUM | NO | `success`, `error`, `partial` |
| `alm_item_id` | VARCHAR(50) | YES | |
| `error_message` | TEXT | YES | |
| `payload` | JSON | YES | |
| `created_at` | TIMESTAMP | NO | |

---

## 3. API Specification

### 3.1 Process Hierarchy API

**GET /api/projects/{projectId}/process-levels**
Returns L1-L4 tree with computed fit summaries.

Query params: `level`, `scope_status`, `fit_status`, `process_area`, `wave`, `flat` (boolean), `include_stats` (boolean)

Response (tree mode) includes nested children with fit_summary aggregates.

**GET /api/projects/{projectId}/process-levels/{id}**
Single process level with children.

**PUT /api/projects/{projectId}/process-levels/{id}**
Update scope_status, fit_status, description, etc.

**GET /api/projects/{projectId}/scope-matrix**
Flat L3 scope item list with workshop/requirement/OI stats per row.

---

### 3.2 Workshop API

**GET /api/projects/{projectId}/workshops**

Query params:
| Param | Type | Description |
|-------|------|-------------|
| `status` | string | draft, scheduled, in_progress, completed, cancelled |
| `process_area` | string | Area code |
| `wave` | integer | Wave filter |
| `facilitator_id` | UUID | |
| `date_from` | date | |
| `date_to` | date | |
| `scope_item_code` | string | |
| `search` | string | Full-text on code, name, scope item |
| `sort_by` | string | date, code, name, status, process_area, wave |
| `sort_dir` | string | asc, desc |
| `page` | integer | Default: 1 |
| `per_page` | integer | Default: 50. Max: 200 |

Response includes stats per workshop: steps_total, fit_count, gap_count, partial_count, decisions_count, open_items_open, requirements_count.

**GET /api/projects/{projectId}/workshops/{id}**
Full detail: agenda, attendees, process_steps with nested decisions/OIs/requirements.

**POST /api/projects/{projectId}/workshops**
Create new workshop.

**PUT /api/projects/{projectId}/workshops/{id}**
Update fields.

**POST /api/projects/{projectId}/workshops/{id}/start**
Transition: scheduled -> in_progress.
Side effects:
1. Set status, started_at
2. For each linked scope item's L4 children -> create process_step records
3. Return created steps

**POST /api/projects/{projectId}/workshops/{id}/complete**
Transition: in_progress -> completed.
Validation: All steps must have fit_decision set.
Side effects:
1. Set status, completed_at
2. Propagate fit_decision to process_level.fit_status on L4 nodes
3. Recalculate L3 fit_status, L2/L1 fit_summary

**GET /api/projects/{projectId}/workshops/capacity**
Facilitator capacity analysis: weekly load, overloaded weeks.

---

### 3.3 Process Step API

**PUT /api/projects/{projectId}/process-steps/{id}**
Update fit_decision, notes.

**POST /api/projects/{projectId}/process-steps/{id}/decisions**
Add decision. Request: text, decided_by, category, rationale.

**POST /api/projects/{projectId}/process-steps/{id}/open-items**
Create OI linked to step. Auto-assigns workshop_id, process_level_id, process_area, wave. Generates OI-{seq}.

**POST /api/projects/{projectId}/process-steps/{id}/requirements**
Create requirement linked to step. Auto-assigns all context fields. Generates REQ-{seq}. Sets status=draft.

---

### 3.4 Requirement API

**GET /api/projects/{projectId}/requirements**

Query params: `status`, `priority`, `type`, `process_area`, `wave`, `scope_item_code`, `workshop_id`, `alm_synced`, `search`, `group_by`, `sort_by`, `sort_dir`, `page`, `per_page`

**GET /api/projects/{projectId}/requirements/{id}**
Full detail with audit trail, linked OIs, dependencies.

**PUT /api/projects/{projectId}/requirements/{id}**
Update fields.

**POST /api/projects/{projectId}/requirements/{id}/transition**
Execute status transition.
Request: { action, comment, approved_by_id }
Valid actions: submit_for_review, approve, reject, return_to_draft, defer, push_to_alm, mark_realized, verify, reactivate

Transition side effects:
| Action | Side Effects |
|--------|-------------|
| approve | Set approved_by, approved_at |
| reject | Set rejection_reason |
| push_to_alm | Call Cloud ALM API, set alm_id, alm_synced=true |
| defer | Set deferred_to_phase |

**POST /api/projects/{projectId}/requirements/{id}/link-open-item**
Request: { open_item_id, link_type }

**POST /api/projects/{projectId}/requirements/{id}/add-dependency**
Request: { depends_on_id, dependency_type }

**POST /api/projects/{projectId}/requirements/bulk-sync-alm**
Bulk push approved requirements to Cloud ALM.

**GET /api/projects/{projectId}/requirements/stats**
Aggregated KPI data: by_status, by_priority, by_type, by_area, total_effort, alm_synced_count.

---

### 3.5 Open Item API

**GET /api/projects/{projectId}/open-items**
Query params: `status`, `priority`, `category`, `process_area`, `wave`, `assignee_id`, `workshop_id`, `overdue` (boolean), `search`, `group_by`, `sort_by`, `page`, `per_page`

**PUT /api/projects/{projectId}/open-items/{id}**
Update fields.

**POST /api/projects/{projectId}/open-items/{id}/transition**
Valid actions and transitions:
| Action | From | To | Notes |
|--------|------|----|-------|
| start_progress | open | in_progress | |
| mark_blocked | open, in_progress | blocked | Requires blocked_reason |
| unblock | blocked | in_progress | |
| close | open, in_progress | closed | Requires resolution. Checks linked REQs. |
| cancel | open, in_progress, blocked | cancelled | Requires comment |
| reopen | closed, cancelled | open | |

Close side effects: If OI has 'blocks' link to REQ -> check if all blocking OIs closed -> notify REQ owner.

**POST /api/projects/{projectId}/open-items/{id}/reassign**
Request: { assignee_id, comment }

**POST /api/projects/{projectId}/open-items/{id}/comments**
Add to activity log.

**GET /api/projects/{projectId}/open-items/stats**
Aggregated: by_status, by_priority, overdue_count, p1_open_count, avg_resolution_days, by_assignee, by_category.

---

## 4. Frontend Component Specification

### 4.1 Module A: Process Hierarchy Manager

**Route:** `/projects/{id}/explore/hierarchy`

**State:**
```typescript
interface ProcessHierarchyState {
  viewMode: 'hierarchy' | 'workshops' | 'matrix';
  expandedNodes: Set<string>;
  selectedNodeId: string | null;
  searchQuery: string;
  fitStatusFilter: FitStatus | 'all';
  scopeStatusFilter: ScopeStatus | 'all';
  detailPanelTab: 'overview' | 'fit_analysis' | 'requirements' | 'workshop';
}
```

**Components:**
| Component | Description |
|-----------|-------------|
| ProcessTree | Recursive tree. Each node: level badge, code, name, fit badge, fit distribution bar, workshop indicator |
| ProcessNodeRow | Single row. Indentation = level * 24px. Click=select, chevron=expand |
| FitDistributionBar | Stacked bar: green(fit) + amber(partial) + red(gap) + indigo(pending) |
| ScopeMatrix | Flat L3 table. Columns: code, name, area, wave, fit, workshop status, REQ count, OI count |
| DetailPanel | Right sidebar 350px. Tabs: Overview, Fit Analysis, Requirements, Workshop |
| KpiDashboard | Total processes, fit/gap/partial/pending counts and percentages |

---

### 4.2 Module B: Workshop Hub

**Route:** `/projects/{id}/explore/workshops`

**State:**
```typescript
interface WorkshopHubState {
  viewMode: 'table' | 'kanban' | 'capacity';
  filters: {
    search: string;
    status: WorkshopStatus | 'all';
    wave: number;             // 0 = all
    processArea: string;      // 'all' or area code
    facilitatorId: string;    // 'all' or user ID
    dateFrom: string | null;
    dateTo: string | null;
  };
  groupBy: 'none' | 'wave' | 'area' | 'facilitator' | 'status' | 'date';
  sortKey: string;
  sortDir: 'asc' | 'desc';
  collapsedGroups: Set<string>;
  page: number;
}
```

**Components:**
| Component | Description |
|-----------|-------------|
| WorkshopTable | Sortable, groupable. Columns: code, scope item, name, area, wave, date, status, facilitator, fit bar, DEC/OI/REQ counts |
| WorkshopKanban | 4-column: Draft/Scheduled/In Progress/Completed |
| CapacityView | Card grid per facilitator. Weekly load bars, overloaded warning |
| FilterBar | Search + status + wave + area + facilitator chips |
| KpiStrip | Total, progress%, active, scheduled, draft, open items, gaps, requirements |

---

### 4.3 Module C: Workshop Detail

**Route:** `/projects/{id}/explore/workshops/{workshopId}`

**State:**
```typescript
interface WorkshopDetailState {
  activeTab: 'steps' | 'decisions' | 'openItems' | 'requirements' | 'agenda' | 'attendees';
  expandedStepId: string | null;
  editingFitDecision: string | null;
}
```

**Components:**
| Component | Description |
|-----------|-------------|
| WorkshopHeader | Code, name, status, type, date/time, facilitator, scope items, actions |
| SummaryStrip | Fit/Partial/Gap + Decisions/OI/Req counts |
| ProcessStepList | Expandable cards per L4 step |
| ProcessStepCard | Step#, code, name, fit badge, counts. Expand: notes, fit selector, decisions, OIs, reqs |
| FitDecisionSelector | 3-radio: Fit/Partial Fit/Gap with descriptions |
| DecisionCard | Purple accent: text, decided_by, category |
| OpenItemCard | Orange accent: ID, priority, status, assignee, due date |
| RequirementCard | Blue accent: ID, priority, type, status, effort |
| InlineAddForm | Collapsible form for adding DEC/OI/REQ within step |
| AgendaTimeline | Time-ordered agenda items |
| AttendeeList | Name, role, org badge, attendance |

**Key Interactions:**
- "Start Workshop" -> creates process steps from linked scope item L4 children
- Set fit decision -> propagates to process_level
- Inline add DEC/OI/REQ -> created within step context, auto-linked
- "Complete Workshop" -> validates all steps assessed, propagates fit statuses

---

### 4.4 Module D: Requirement & Open Item Hub

**Route:** `/projects/{id}/explore/requirements`

**State:**
```typescript
interface RequirementRegistryState {
  filters: {
    search: string; status: string; priority: string;
    type: string; processArea: string; wave: number;
    scopeItemCode: string; workshopId: string; almSynced: boolean | null;
  };
  groupBy: 'status'|'priority'|'area'|'type'|'scopeItem'|'wave'|'workshop'|'none';
  sortKey: string; sortDir: 'asc'|'desc';
  collapsedGroups: Set<string>;
  selectedId: string | null;
}

interface OpenItemTrackerState {
  filters: {
    search: string; status: string; priority: string;
    category: string; processArea: string; wave: number;
    assigneeId: string; workshopId: string; overdueOnly: boolean;
  };
  groupBy: 'status'|'assignee'|'priority'|'category'|'area'|'wave'|'workshop'|'none';
  collapsedGroups: Set<string>;
  selectedId: string | null;
}
```

**Requirement Components:**
| Component | Description |
|-----------|-------------|
| RequirementKpiStrip | Total, P1, draft, review, approved, backlog, realized, ALM synced, effort |
| RequirementRow | ID, priority pill, type pill, fit pill, title, scope item, area, effort, status flow, ALM icon |
| RequirementExpandedDetail | Traceability (workshop, scope, step, created/approved by, ALM ID). Linked OIs. Dependencies. Actions |
| StatusFlowIndicator | Horizontal lifecycle dots/pills. Active highlighted |
| RequirementActionButtons | Context-sensitive: Submit, Approve, Reject, Push to ALM, etc. |

**Open Item Components:**
| Component | Description |
|-----------|-------------|
| OpenItemKpiStrip | Total, open, in progress, blocked, closed, overdue, P1 open |
| OpenItemRow | ID, priority, status, category, title, assignee, due date (red if overdue), area |
| OpenItemExpandedDetail | Traceability. Linked REQ. Blocked reason. Resolution. Actions |
| OverdueToggle | Red filter toggle for overdue-only view |
| AssigneeDropdown | Filter by unique assignees |

---

## 5. Business Rules

### 5.1 Fit Status Propagation

When fit decision set at L4 (via process step):
1. **L4 node** gets fit_status from process_step.fit_decision
2. **L3 node** recalculates: any gap -> partial_fit (or gap if all gap); any partial -> partial_fit; all fit -> fit; any pending -> worst non-pending status
3. **L2/L1** store aggregate fit_summary counts only

### 5.2 Code Generation

```
Workshop: WS-{AREA}-{SEQ}{SESSION}
  - SEQ: 2-digit zero-padded per area
  - SESSION: A/B/C if total_sessions > 1
  Examples: WS-SD-01, WS-FI-03A

Requirement: REQ-{SEQ} (3-digit, project-wide)
Open Item:   OI-{SEQ}  (3-digit, project-wide)
Decision:    DEC-{SEQ} (3-digit, project-wide)
```

### 5.3 Workshop Completion Validation

- **Blocking:** All process_steps must have fit_decision != NULL
- **Warning:** Open items with status 'open' exist
- **Warning:** Any step has empty notes

### 5.4 Overdue Logic

Open item is overdue when: status IN ('open', 'in_progress') AND due_date < CURRENT_DATE

### 5.5 OI-to-Requirement Blocking

When OI has link_type='blocks' to a requirement:
- REQ cannot transition under_review -> approved while blocking OI is not closed
- When blocking OI closed -> check all linked OIs -> if all closed -> notify REQ stakeholders
- UI shows "Blocked by N open items" badge

### 5.6 Cloud ALM Sync

- Only approved requirements can be pushed
- Push creates ALM backlog item, returns alm_id
- alm_sync_status: pending -> synced | sync_error
- Retry on error with exponential backoff

### 5.7 Facilitator Capacity

- Each facilitator has weekly_capacity (max WS/week)
- Week = Mon-Fri, from date field
- Overloaded = any week with assigned > capacity
- Warning only, does not block scheduling

---

## 6. Enumerations

```typescript
type ProcessLevel = 1 | 2 | 3 | 4;
type ScopeStatus = 'in_scope' | 'out_of_scope' | 'under_review';
type FitStatus = 'fit' | 'gap' | 'partial_fit' | 'pending';

type WorkshopType = 'fit_to_standard' | 'deep_dive' | 'follow_up' | 'delta_design';
type WorkshopStatus = 'draft' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled';
type AgendaItemType = 'session' | 'break' | 'demo' | 'discussion' | 'wrap_up';
type AttendanceStatus = 'confirmed' | 'tentative' | 'declined' | 'present' | 'absent';
type AttendeeOrganization = 'customer' | 'consultant' | 'partner' | 'vendor';

type DecisionCategory = 'process' | 'technical' | 'scope' | 'organizational' | 'data';
type DecisionStatus = 'active' | 'superseded' | 'revoked';

type RequirementStatus = 'draft' | 'under_review' | 'approved' | 'in_backlog' | 'realized' | 'verified' | 'deferred' | 'rejected';
type RequirementType = 'development' | 'configuration' | 'integration' | 'migration' | 'enhancement' | 'workaround';
type Complexity = 'low' | 'medium' | 'high' | 'very_high';
type ALMSyncStatus = 'pending' | 'synced' | 'sync_error' | 'out_of_sync';

type OpenItemStatus = 'open' | 'in_progress' | 'blocked' | 'closed' | 'cancelled';
type OpenItemCategory = 'clarification' | 'technical' | 'scope' | 'data' | 'process' | 'organizational';

type Priority = 'P1' | 'P2' | 'P3' | 'P4';
type LinkType = 'blocks' | 'related' | 'triggers';
type DependencyType = 'blocks' | 'related' | 'extends';
type ProcessArea = 'FI' | 'CO' | 'SD' | 'MM' | 'PP' | 'QM' | 'PM' | 'WM' | 'HR' | 'PS';
```

---

## 7. Integration Points

### 7.1 SAP Cloud ALM

Direction: Push requirements ProjektCoPilot -> Cloud ALM backlog items

| ProjektCoPilot Field | Cloud ALM Field |
|---------------------|-----------------|
| code | External Reference |
| title | Summary |
| description | Description |
| priority | Priority (P1=Critical, P2=High, P3=Medium, P4=Low) |
| type | Category |
| process_area | Process Area Tag |
| scope_item_code | Scope Item Reference |
| effort_hours | Story Points (converted) |

### 7.2 SAP Signavio

Direction: Import process hierarchy Signavio -> ProjektCoPilot
- L1-L4 process structure
- BPMN diagram references (URLs)
- Scope item codes and descriptions
- Implementation: Manual JSON/Excel import, or API (future)

### 7.3 Existing ProjektCoPilot Modules

- `project` table -> project_id FK
- `user` table -> facilitator, assignee, created_by
- `RequirementProcessMapping` (v1.2) -> replaced by direct FK requirement.process_level_id
- Existing Workshop model -> extended with new fields or migrated
- Existing OpenItem model (v1.2) -> extended or migrated

---

## 8. Performance Considerations

### 8.1 Queries to Optimize

1. **Process tree with fit summaries**: Recursive CTE. Cache at L1/L2. Invalidate on L4 change.
2. **Workshop list with stats**: Denormalize stats into workshop or use materialized view.
3. **Open item overdue**: Index on due_date, or scheduled flagging job.
4. **Cross-workshop counts**: Index on workshop_id.

### 8.2 Expected Data Volumes

| Entity | Expected per Project |
|--------|---------------------|
| ProcessLevel L1 | 3-5 |
| ProcessLevel L2 | 8-12 |
| ProcessLevel L3 | 50-100 |
| ProcessLevel L4 | 200-500 |
| Workshop | 150-400 |
| ProcessStep | 800-2000 |
| Decision | 1500-4000 |
| OpenItem | 100-300 |
| Requirement | 150-500 |

---

## 9. UI/UX Design Tokens

```typescript
const DesignTokens = {
  bg: "#0B0F1A", surface: "#111827", surfaceAlt: "#1A2035",
  surfaceHover: "#1F2B42", border: "#1E293B", borderActive: "#3B82F6",

  text: "#E2E8F0", textMuted: "#94A3B8", textDim: "#64748B",

  fit: "#10B981", gap: "#EF4444", partial: "#F59E0B", pending: "#6366F1",
  p1: "#EF4444", p2: "#F59E0B", p3: "#3B82F6", p4: "#64748B",
  openItem: "#F97316", decision: "#8B5CF6",
  l1: "#8B5CF6", l2: "#3B82F6", l3: "#10B981", l4: "#F59E0B",
  wave1: "#3B82F6", wave2: "#8B5CF6", wave3: "#EC4899", wave4: "#14B8A6",

  areaColors: {
    FI: "#3B82F6", CO: "#6366F1", SD: "#10B981", MM: "#F59E0B", PP: "#EF4444",
    QM: "#EC4899", PM: "#14B8A6", WM: "#F97316", HR: "#8B5CF6", PS: "#06B6D4",
  },

  fontFamily: "'DM Sans', -apple-system, sans-serif",
  fontMono: "'JetBrains Mono', 'Fira Code', monospace",
};
```

---

## 10. File Structure

```
src/
  modules/
    explore/
      api/
        processLevelApi.ts
        workshopApi.ts
        processStepApi.ts
        requirementApi.ts
        openItemApi.ts
        types.ts              # All interfaces and enums
      components/
        hierarchy/
          ProcessTree.tsx
          ProcessNodeRow.tsx
          FitDistributionBar.tsx
          ScopeMatrix.tsx
          DetailPanel.tsx
          HierarchyKpiDashboard.tsx
        workshop-hub/
          WorkshopTable.tsx
          WorkshopKanban.tsx
          CapacityView.tsx
          WorkshopFilterBar.tsx
          WorkshopKpiStrip.tsx
          GroupBySelector.tsx
        workshop-detail/
          WorkshopHeader.tsx
          SummaryStrip.tsx
          ProcessStepList.tsx
          ProcessStepCard.tsx
          FitDecisionSelector.tsx
          DecisionCard.tsx
          OpenItemCard.tsx
          RequirementCard.tsx
          InlineAddForm.tsx
          AgendaTimeline.tsx
          AttendeeList.tsx
        requirements/
          RequirementRegistry.tsx
          RequirementRow.tsx
          RequirementExpandedDetail.tsx
          RequirementKpiStrip.tsx
          RequirementFilterBar.tsx
          StatusFlowIndicator.tsx
          RequirementActionButtons.tsx
        open-items/
          OpenItemTracker.tsx
          OpenItemRow.tsx
          OpenItemExpandedDetail.tsx
          OpenItemKpiStrip.tsx
          OpenItemFilterBar.tsx
          OverdueToggle.tsx
        shared/
          Pill.tsx
          FitBadge.tsx
          FitBarMini.tsx
          KpiBlock.tsx
          FilterGroup.tsx
          ActionButton.tsx
          CountChip.tsx
          Icon.tsx
      hooks/
        useProcessLevels.ts
        useWorkshops.ts
        useWorkshopDetail.ts
        useRequirements.ts
        useOpenItems.ts
        useFilters.ts
      pages/
        ProcessHierarchyPage.tsx    # Module A
        WorkshopHubPage.tsx         # Module B
        WorkshopDetailPage.tsx      # Module C
        RequirementHubPage.tsx      # Module D
      utils/
        fitCalculations.ts
        codeGenerators.ts
        statusTransitions.ts
        overdueCalculations.ts
  models/
    processLevel.ts
    workshop.ts
    workshopScopeItem.ts
    workshopAttendee.ts
    workshopAgendaItem.ts
    processStep.ts
    decision.ts
    openItem.ts
    openItemComment.ts
    requirement.ts
    requirementOpenItemLink.ts
    requirementDependency.ts
    cloudAlmSyncLog.ts
  migrations/
    20260209_explore_phase_tables.ts
```

---

## 11. Migration Notes

### From Existing Platform

1. **Existing Workshop model** -> Extend or migrate to new schema
2. **Existing OpenItem model (v1.2)** -> Migrate with category, blocking, activity log
3. **Existing RequirementProcessMapping (v1.2, N:M)** -> Simplified to direct FK
4. **Existing Scenario/Process hierarchy** -> Map to process_level:
   - Scenario -> L1
   - ProcessL2 -> L2
   - ProcessL3 -> L3
   - Sub-process -> L4 (new level)

### Data Seeding

For new projects, seed L1-L3 from SAP Best Practice scope item catalog (JSON/Excel import).
L4 created from BPMN breakdown or manually during workshop prep.

---

## 12. Acceptance Criteria

### Module A - Process Hierarchy Manager
- [ ] Display L1-L4 tree with expand/collapse
- [ ] Fit status badge and distribution bar per node
- [ ] Three views: hierarchy, workshops, matrix
- [ ] Search and filter by fit/scope status
- [ ] Detail panel with tabs
- [ ] Navigation links to workshops and requirements

### Module B - Workshop Hub
- [ ] Display 300+ workshops in sortable/groupable table
- [ ] Filter by status, wave, area, facilitator, date, search
- [ ] Group by wave, area, facilitator, status, date
- [ ] Kanban view with 4 columns
- [ ] Capacity view with overload warnings
- [ ] KPI strip with filtered aggregations

### Module C - Workshop Detail
- [ ] Workshop header with metadata and actions
- [ ] Expandable process steps
- [ ] Fit decision selector per step
- [ ] Inline add for decisions, OIs, requirements
- [ ] Cross-step tabs
- [ ] Start/Complete transitions with validation
- [ ] Fit status propagation on completion

### Module D - Requirement & Open Item Hub
- [ ] Tab-switched REQ/OI views
- [ ] Requirements: full lifecycle (draft -> verified)
- [ ] Requirements: filter/group/sort 200+ items
- [ ] Requirements: traceability to workshop/scope/step
- [ ] Requirements: Cloud ALM sync
- [ ] Requirements: dependency and OI linking
- [ ] Open Items: overdue highlighting
- [ ] Open Items: assignee filter and reassignment
- [ ] Open Items: blocking relationship to REQs
- [ ] Open Items: activity log
- [ ] KPI dashboards on both tabs

---

*Document Version: 1.0*
*Created: 2026-02-10*
*Author: ProjektCoPilot Development Team*


---

## 13. Gap Analysis Addendum — 10 Eksik Alan

> Bu bölüm, v1.0 FS/TS'in akış kontrolü sonucunda tespit edilen 10 eksik alanı kapsar.
> Her alan mevcut dokümanın ilgili bölümüne referans verir ve yeni tablo/API/component/rule ekler.
> Implementation sırasında Phase 0 (kritik), Phase 1 (önemli), Phase 2 (iyileştirme) olarak fazlandırılabilir.

---

### 13.1 L4 Sub-Process Seeding Mekanizması

**Problem:** Workshop "Start" edildiğinde L4 process_step kayıtları oluşturuluyor, ancak bunların kaynak L4 `process_level` kayıtları nasıl yaratılacağı tanımsız. L4 olmadan workshop başlatılamaz.

**Implementation Priority:** CRITICAL — Phase 0

#### 13.1.1 Üç Kaynak Modu

| Mod | Açıklama | Tetikleyici |
|-----|----------|------------|
| `catalog_import` | SAP Best Practice scope item kataloğundan toplu L4 import | Proje kurulumunda veya scope item eklendiğinde |
| `bpmn_import` | Signavio BPMN'den sub-process extraction | L3 node'da "Import from BPMN" aksiyonu |
| `manual_entry` | Facilitator workshop öncesi manuel giriş | L3 node'da "Add Sub-Process" aksiyonu |

#### 13.1.2 Yeni Tablo: `l4_seed_catalog`

SAP Best Practice'ten gelen referans L4 tanımları. Proje bağımsız, global catalog.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `scope_item_code` | VARCHAR(10) | NO | L3 scope item code (J58, BD9, etc.) |
| `sub_process_code` | VARCHAR(20) | NO | Standard L4 code (J58.01, BD9.03) |
| `sub_process_name` | VARCHAR(200) | NO | Standard name |
| `description` | TEXT | YES | |
| `standard_sequence` | INTEGER | NO | Default ordering |
| `bpmn_activity_id` | VARCHAR(100) | YES | Signavio activity reference |
| `sap_release` | VARCHAR(20) | YES | e.g., "2402", "2311" — hangi SAP release |

**Index:** UNIQUE ON (`scope_item_code`, `sub_process_code`)

#### 13.1.3 Yeni API Endpoint'ler

**POST /api/projects/{projectId}/process-levels/{l3Id}/seed-from-catalog**
L3 scope item code'una göre catalog'dan L4 kayıtlarını otomatik oluşturur.

Business Logic:
1. `l4_seed_catalog` tablosundan `scope_item_code` matching kayıtları çek
2. Her biri için `process_level` tablosuna L4 kayıt oluştur (parent_id = l3Id)
3. Var olan L4'leri skip et (idempotent)
4. Oluşturulan kayıt sayısını dön

**POST /api/projects/{projectId}/process-levels/{l3Id}/seed-from-bpmn**
Signavio BPMN XML/JSON'dan sub-process extraction.

Request:
```json
{
  "bpmn_source": "url" | "upload",
  "bpmn_url": "https://signavio.sap.com/...",
  "bpmn_file": "<base64 encoded BPMN XML>"
}
```

Business Logic:
1. BPMN parse et — task/subprocess element'leri çıkar
2. Her activity için L4 process_level oluştur
3. Sequence flow'dan sort_order belirle
4. `bpmn_activity_id` referansını kaydet

**POST /api/projects/{projectId}/process-levels/{l3Id}/children**
Manuel L4 ekleme (mevcut API'de parent altına child ekleme zaten olmalı).

#### 13.1.4 Workshop Start Güncelleme

Mevcut `POST /workshops/{id}/start` endpoint'ine validation ekle:

```
PRE-CONDITION CHECK:
1. Workshop'un linked scope item'ları (workshop_scope_item) var mı?
2. Her scope item'ın en az 1 L4 child'ı var mı?
3. Yoksa → HTTP 422: "Scope item {code} has no sub-processes. Seed L4 first."
```

#### 13.1.5 Yeni Component: `L4SeedingDialog`

Workshop Hub veya Process Hierarchy'den erişilen dialog:
- Scope item seçili gelir
- 3 seçenek gösterir: Catalog / BPMN / Manual
- Catalog seçilirse → preview listesi + "Import" butonu
- BPMN seçilirse → file upload veya URL input
- Manual seçilirse → inline form (code + name + description)

---

### 13.2 BPMN Görüntüleme

**Problem:** Facilitator workshop'ta SAP standardını anlatırken BPMN diyagramı gösteremiyor. `bpmn_available` ve `bpmn_reference` alanları var ama render eden component yok.

**Implementation Priority:** Phase 2 (iyileştirme)

#### 13.2.1 Yaklaşım

Tam bir BPMN editor gerekmiyor. İki mod yeterli:

| Mod | Açıklama | Kütüphane |
|-----|----------|-----------|
| `iframe_embed` | Signavio URL'ini iframe'de göster | Yok — sadece iframe |
| `bpmn_viewer` | BPMN XML'i client-side render et | bpmn.io/bpmn-js (viewer-only, MIT license) |

#### 13.2.2 Yeni Tablo: `bpmn_diagram`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `process_level_id` | UUID | NO | FK -> process_level (L3 or L4) |
| `type` | ENUM | NO | `signavio_embed`, `bpmn_xml`, `image` |
| `source_url` | VARCHAR(500) | YES | Signavio URL for iframe |
| `bpmn_xml` | TEXT | YES | Raw BPMN 2.0 XML content |
| `image_path` | VARCHAR(500) | YES | Uploaded PNG/SVG path |
| `version` | INTEGER | NO | Default: 1. Increment on update |
| `uploaded_by` | UUID | YES | FK -> user |
| `created_at` | TIMESTAMP | NO | |

#### 13.2.3 Yeni Component'ler

| Component | Yer | Açıklama |
|-----------|-----|----------|
| `BpmnViewer` | Module A Detail Panel + Module C Workshop Detail | Tab veya expandable section. Iframe veya bpmn-js viewer |
| `BpmnUploadDialog` | Module A Process Node action | BPMN XML upload veya Signavio URL input |

#### 13.2.4 API

**GET /api/projects/{projectId}/process-levels/{id}/bpmn**
BPMN diagram bilgisini dön (url veya xml).

**POST /api/projects/{projectId}/process-levels/{id}/bpmn**
Upload BPMN XML veya Signavio URL kaydet.

---

### 13.3 Workshop Arası Bağımlılık Yönetimi

**Problem:** Cross-module bağımlılıklar var (SD workshop'unda "bunu MM ile konuşalım" çıkar). Workshop seviyesinde dependency tracking yok.

**Implementation Priority:** Phase 1 (önemli)

#### 13.3.1 Yeni Tablo: `workshop_dependency`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `workshop_id` | UUID | NO | FK -> workshop (dependent) |
| `depends_on_workshop_id` | UUID | NO | FK -> workshop (dependency) |
| `dependency_type` | ENUM | NO | `must_complete_first`, `information_needed`, `cross_module_review`, `shared_decision` |
| `description` | TEXT | YES | Neden bağımlı |
| `status` | ENUM | NO | `active`, `resolved`. Default: `active` |
| `created_by` | UUID | NO | FK -> user |
| `created_at` | TIMESTAMP | NO | |
| `resolved_at` | TIMESTAMP | YES | |

**Constraint:** No self-reference. Unique: (workshop_id, depends_on_workshop_id)

#### 13.3.2 Yeni Tablo: `cross_module_flag`

Workshop step'inde "bu konu başka modülü ilgilendiriyor" işaretlemesi.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `process_step_id` | UUID | NO | FK -> process_step (kaynak) |
| `target_process_area` | VARCHAR(5) | NO | Hangi alanı ilgilendiriyor (MM, FI, etc.) |
| `target_scope_item_code` | VARCHAR(10) | YES | Spesifik scope item varsa |
| `description` | TEXT | NO | Ne hakkında |
| `status` | ENUM | NO | `open`, `discussed`, `resolved`. Default: `open` |
| `resolved_in_workshop_id` | UUID | YES | FK -> workshop (hangi workshop'ta çözüldü) |
| `created_at` | TIMESTAMP | NO | |

#### 13.3.3 API

**GET /api/projects/{projectId}/workshops/{id}/dependencies**
Workshop'un bağımlılık listesi (hem bağımlı olduğu hem bağımlı olunan).

**POST /api/projects/{projectId}/workshops/{id}/dependencies**
Yeni bağımlılık ekle.

**POST /api/projects/{projectId}/process-steps/{id}/cross-module-flags**
Step'te cross-module flag oluştur.

**GET /api/projects/{projectId}/cross-module-flags?status=open**
Tüm açık cross-module konularını listele (proje geneli).

#### 13.3.4 Workshop Hub Güncellemesi

- Table view'a `dependencies` kolonu ekle (bağımlılık sayısı, kırmızı badge eğer unresolved varsa)
- Workshop Detail header'a "Dependencies" section ekle
- Yeni view: "Cross-Module Issues" — tüm açık cross-module flag'lerin listesi

#### 13.3.5 Business Rule

```
Workshop Complete Validation (güncelleme):
- WARNING: Unresolved cross-module flags exist
- WARNING: Workshop depends on incomplete workshops (must_complete_first)
```

---

### 13.4 Workshop Reopen / Revision Mekanizması

**Problem:** Completed workshop'taki bir fit kararının değişmesi gerektiğinde yol yok. completed terminal durum.

**Implementation Priority:** Phase 1 (önemli)

#### 13.4.1 Status Transition Güncellemesi

Mevcut workshop status flow'a ekleme:

```
completed --reopen--> in_progress   (requires reason + PM approval flag)
completed --revise--> creates new "delta_design" workshop linked to original
```

İki yol:

| Yol | Ne Zaman | Mekanizma |
|-----|----------|-----------|
| Reopen | Küçük düzeltme (1-2 step'te karar değişikliği) | Aynı workshop tekrar açılır |
| Delta Design | Büyük değişiklik veya yeni gereksinim | Yeni workshop, original'e linked |

#### 13.4.2 Yeni Alanlar: `workshop` tablosuna

| Column | Type | Description |
|--------|------|-------------|
| `original_workshop_id` | UUID, YES | FK -> workshop. Delta design workshop'lar için orijinal WS |
| `reopen_count` | INTEGER, default 0 | Kaç kez reopen edildi |
| `reopen_reason` | TEXT, YES | Son reopen sebebi |
| `revision_number` | INTEGER, default 1 | 1 = orijinal, 2+ = revision |

#### 13.4.3 Yeni Tablo: `workshop_revision_log`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `workshop_id` | UUID | NO | FK -> workshop |
| `action` | ENUM | NO | `reopened`, `delta_created`, `fit_decision_changed` |
| `previous_value` | TEXT | YES | Eski değer (JSON) |
| `new_value` | TEXT | YES | Yeni değer (JSON) |
| `reason` | TEXT | NO | Neden değişti |
| `changed_by` | UUID | NO | FK -> user |
| `created_at` | TIMESTAMP | NO | |

#### 13.4.4 API

**POST /api/projects/{projectId}/workshops/{id}/reopen**
Request: { reason, approved_by_id }
- Status: completed -> in_progress
- reopen_count++, reopen_reason set
- Revision log entry oluştur
- Fit status propagation geri alınmaz (manual override gerekir)

**POST /api/projects/{projectId}/workshops/{id}/create-delta**
Request: { reason, scope_items (optional subset), facilitator_id, date }
- Yeni workshop oluştur (type: delta_design, original_workshop_id: current)
- Orijinal workshop'un step'lerini kopyala (sadece belirtilen scope item'lar için)
- Fit kararları boş gelir (yeniden değerlendirilecek)

#### 13.4.5 Fit Decision Change Tracking

ProcessStep'te fit_decision değiştiğinde:
1. `workshop_revision_log`'a eski ve yeni değer yaz
2. L4 process_level.fit_status güncelle
3. L3 ve üstü recalculate

---

### 13.5 Role-Based Approval Workflow

**Problem:** Requirement lifecycle'da approve/reject aksiyonları var ama kim yapabilir tanımsız. Herkes her şeyi yapabiliyor.

**Implementation Priority:** CRITICAL — Phase 0

#### 13.5.1 Yeni Tablo: `project_role`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `user_id` | UUID | NO | FK -> user |
| `role` | ENUM | NO | See role definitions below |
| `process_area` | VARCHAR(5) | YES | NULL = all areas. Set = area-specific (e.g., SD module lead) |
| `created_at` | TIMESTAMP | NO | |

**Unique:** (project_id, user_id, role, process_area)

#### 13.5.2 Role Definitions

| Role | Code | Permissions |
|------|------|------------|
| Project Manager | `pm` | All actions. Workshop schedule approval. Requirement defer. Scope change. |
| Module Lead | `module_lead` | Approve/reject requirements in their area. Workshop reopen. Verify requirements. |
| Facilitator | `facilitator` | Start/complete workshops they facilitate. Set fit decisions. Create REQ/OI/DEC. |
| Business Process Owner | `bpo` | View all. Approve requirements (co-sign with module lead). Scope matrix decisions. |
| Developer / Tech Lead | `tech_lead` | Push to ALM. Mark realized. Effort estimation. |
| Business Tester | `tester` | Verify realized requirements. |
| Viewer | `viewer` | Read-only access to all screens. |

#### 13.5.3 Permission Matrix

| Action | pm | module_lead | facilitator | bpo | tech_lead | tester |
|--------|-----|------------|------------|-----|-----------|--------|
| Workshop: schedule | ✓ | ✓ (own area) | ✗ | ✗ | ✗ | ✗ |
| Workshop: start | ✓ | ✓ | ✓ (own WS) | ✗ | ✗ | ✗ |
| Workshop: complete | ✓ | ✓ | ✓ (own WS) | ✗ | ✗ | ✗ |
| Workshop: reopen | ✓ | ✓ (own area) | ✗ | ✗ | ✗ | ✗ |
| Fit decision: set | ✓ | ✓ | ✓ (own WS) | ✓ | ✗ | ✗ |
| REQ: create | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| REQ: submit_for_review | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| REQ: approve | ✓ | ✓ (own area) | ✗ | ✓ | ✗ | ✗ |
| REQ: reject | ✓ | ✓ (own area) | ✗ | ✗ | ✗ | ✗ |
| REQ: push_to_alm | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| REQ: mark_realized | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| REQ: verify | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| REQ: defer | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| OI: create | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| OI: reassign | ✓ | ✓ | ✓ (own WS) | ✗ | ✗ | ✗ |
| OI: close | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| Scope: change | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |

#### 13.5.4 API Middleware

Her protected endpoint'te:

```python
def check_permission(project_id, user_id, action, context=None):
    """
    context = { process_area: "SD", workshop_id: "uuid", requirement_id: "uuid" }
    Returns: True/False
    """
    roles = get_user_roles(project_id, user_id)
    for role in roles:
        if action in PERMISSION_MATRIX[role.role]:
            if role.process_area is None or role.process_area == context.get('process_area'):
                return True
    return False
```

HTTP 403 response when denied: `{ "error": "insufficient_permission", "required_role": "module_lead", "action": "approve_requirement" }`

#### 13.5.5 Batch Approval

**POST /api/projects/{projectId}/requirements/batch-transition**
Request:
```json
{
  "requirement_ids": ["uuid1", "uuid2", "uuid3"],
  "action": "approve",
  "comment": "Batch approved after module review meeting"
}
```

Business Logic:
- Permission check per requirement (area-based)
- Partial success allowed: returns { succeeded: [...], failed: [...] }
- Each transition logged individually

---

### 13.6 Meeting Minutes & Export

**Problem:** Workshop'ta alınan kararlar, open item'lar ve requirement'lar toplantı tutanağı olarak export edilemiyor.

**Implementation Priority:** Phase 2 (iyileştirme)

#### 13.6.1 Minutes Template Yapısı

```
WORKSHOP MEETING MINUTES
========================
Workshop: {code} — {name}
Date: {date} | Time: {start_time} - {end_time}
Facilitator: {facilitator_name}
Location: {location}

ATTENDEES
---------
[Name] | [Role] | [Org] | [Present/Absent]

AGENDA
------
[Time] | [Item] | [Duration]

PROCESS STEP OUTCOMES
---------------------
For each step:
  Step: {code} — {name}
  Fit Decision: {FIT / PARTIAL FIT / GAP}
  Discussion Notes: {notes}
  Decisions:
    - DEC-001: {text} (by {decided_by})
  Open Items:
    - OI-001: {title} → {assignee} by {due_date}
  Requirements:
    - REQ-001: {title} [{priority}] [{type}]

SUMMARY
-------
Total Steps: {n} | Fit: {n} | Partial: {n} | Gap: {n}
Decisions: {n} | Open Items: {n} | Requirements: {n}

NEXT STEPS
----------
{Free text or auto-generated from open items}
```

#### 13.6.2 Yeni Tablo: `workshop_document`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `workshop_id` | UUID | NO | FK -> workshop |
| `type` | ENUM | NO | `meeting_minutes`, `ai_summary`, `custom_report` |
| `format` | ENUM | NO | `markdown`, `docx`, `pdf` |
| `content` | TEXT | YES | Markdown content (for md format) |
| `file_path` | VARCHAR(500) | YES | Generated file path (for docx/pdf) |
| `generated_by` | ENUM | NO | `manual`, `template`, `ai` |
| `generated_at` | TIMESTAMP | NO | |
| `created_by` | UUID | NO | FK -> user |

#### 13.6.3 API

**POST /api/projects/{projectId}/workshops/{id}/generate-minutes**
Request: { format: "markdown" | "docx" | "pdf", include_sections: ["attendees","agenda","outcomes","summary"] }

Business Logic:
1. Collect workshop data (steps, decisions, OIs, requirements, attendees, agenda)
2. Apply template
3. If format = docx/pdf → generate file, save path
4. Store in workshop_document
5. Return content or download URL

**POST /api/projects/{projectId}/workshops/{id}/ai-summary**
Request: { prompt_context: "..." }

Business Logic:
1. Collect all notes, decisions, OIs from workshop
2. Call AI API (Claude/GPT) with structured prompt
3. Generate executive summary + key takeaways + risk highlights
4. Store in workshop_document (type: ai_summary)
5. Return generated text

---

### 13.7 Attachment / Doküman Yönetimi

**Problem:** Workshop'lara, requirement'lara, open item'lara dosya eklenemiyor.

**Implementation Priority:** Phase 1 (önemli)

#### 13.7.1 Yeni Tablo: `attachment`

Generic polymorphic attachment — herhangi bir entity'ye bağlanabilir.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `entity_type` | ENUM | NO | `workshop`, `process_step`, `requirement`, `open_item`, `decision`, `process_level` |
| `entity_id` | UUID | NO | İlgili kaydın ID'si |
| `file_name` | VARCHAR(255) | NO | Orijinal dosya adı |
| `file_path` | VARCHAR(500) | NO | Storage path |
| `file_size` | INTEGER | NO | Bytes |
| `mime_type` | VARCHAR(100) | NO | e.g., application/pdf, image/png |
| `category` | ENUM | YES | `screenshot`, `bpmn_export`, `as_is_document`, `to_be_document`, `spec`, `test_evidence`, `other` |
| `description` | TEXT | YES | |
| `uploaded_by` | UUID | NO | FK -> user |
| `created_at` | TIMESTAMP | NO | |

**Indexes:**
- `idx_attachment_entity` ON (`entity_type`, `entity_id`)
- `idx_attachment_project` ON (`project_id`)

#### 13.7.2 API

**POST /api/projects/{projectId}/attachments**
Multipart file upload.
Request: form-data with file + entity_type + entity_id + category + description

**GET /api/projects/{projectId}/attachments?entity_type=workshop&entity_id={id}**
List attachments for entity.

**GET /api/projects/{projectId}/attachments/{id}/download**
File download.

**DELETE /api/projects/{projectId}/attachments/{id}**

#### 13.7.3 Storage

File system based: `uploads/{project_id}/{entity_type}/{entity_id}/{uuid}_{filename}`
Future: S3/Azure Blob migration path.

#### 13.7.4 UI Integration

Her card/detail view'da attachment section:
- Upload dropzone
- Attachment list (icon + name + size + date + category badge)
- Preview for images, download for others
- Maximum 50MB per file, 500MB per project (configurable)

---

### 13.8 Dashboard & Reporting

**Problem:** Anlık KPI'lar var ama trend analizi, burndown, comparative reporting yok.

**Implementation Priority:** Phase 2 (iyileştirme)

#### 13.8.1 Yeni Tablo: `daily_snapshot`

Günlük otomatik snapshot — trend analizi için.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `snapshot_date` | DATE | NO | |
| `metrics` | JSON | NO | Günün tüm metrikleri (aşağıda detay) |
| `created_at` | TIMESTAMP | NO | |

**Unique:** (project_id, snapshot_date)

**Metrics JSON structure:**
```json
{
  "workshops": {
    "total": 287, "draft": 20, "scheduled": 45, "in_progress": 8, "completed": 210, "cancelled": 4
  },
  "fit_distribution": {
    "fit": 120, "partial_fit": 45, "gap": 30, "pending": 145
  },
  "requirements": {
    "total": 200, "draft": 30, "under_review": 24, "approved": 60, "in_backlog": 40,
    "realized": 20, "verified": 10, "deferred": 10, "rejected": 6,
    "total_effort_hours": 4500, "alm_synced": 60
  },
  "open_items": {
    "total": 150, "open": 52, "in_progress": 38, "blocked": 15, "closed": 38,
    "overdue": 18, "avg_age_days": 4.2
  },
  "by_wave": {
    "1": { "total_ws": 60, "completed_ws": 55, "pct": 91.6 },
    "2": { "total_ws": 80, "completed_ws": 40, "pct": 50.0 },
    "3": { "total_ws": 70, "completed_ws": 10, "pct": 14.3 },
    "4": { "total_ws": 77, "completed_ws": 0, "pct": 0.0 }
  }
}
```

#### 13.8.2 Scheduled Job

Daily cron (veya app startup + 24h interval):
```
POST /api/internal/snapshots/capture
→ For each active project: calculate metrics, insert daily_snapshot
```

#### 13.8.3 Yeni Component: Module E — Explore Dashboard

**Route:** `/projects/{id}/explore/dashboard`

| Widget | Type | Data Source |
|--------|------|------------|
| Workshop Completion Burndown | Area chart (completed over time) | daily_snapshot.workshops |
| Wave Progress Bars | Horizontal bars per wave | daily_snapshot.by_wave |
| Fit/Gap Trend | Stacked area (fit/partial/gap/pending over time) | daily_snapshot.fit_distribution |
| Requirement Pipeline | Funnel chart (draft→review→approved→backlog→realized→verified) | daily_snapshot.requirements |
| Open Item Aging | Bar chart (0-3d, 4-7d, 8-14d, 15+d) | open_items with age calculation |
| Overdue Trend | Line chart (overdue count over time) | daily_snapshot.open_items.overdue |
| Gap Density Heatmap | Cells = process area x wave, color = gap count | Cross-query |
| Facilitator Load Comparison | Grouped bar per facilitator | Workshop query |
| Scope Coverage | Donut (assessed vs pending L4 nodes) | process_level query |
| Top 10 Open Items by Age | Table | open_item sorted by created_at |

#### 13.8.4 Export

**GET /api/projects/{projectId}/reports/steering-committee**
Request: { format: "pptx" | "pdf", date_range: { from, to } }

Generates a steering committee summary deck:
- Slide 1: Executive Summary (completion %, key metrics)
- Slide 2: Wave Progress
- Slide 3: Fit/Gap Distribution by Area
- Slide 4: Requirement Pipeline Status
- Slide 5: Top Risks (overdue OIs, blocked REQs)
- Slide 6: Next Steps & Timeline

---

### 13.9 Scope Change Management

**Problem:** Scope status değişikliklerinin audit trail'i yok. Kim, ne zaman, neden değiştirdi bilinmiyor.

**Implementation Priority:** Phase 1 (önemli)

#### 13.9.1 Yeni Tablo: `scope_change_request`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `code` | VARCHAR(10) | NO | Auto: SCR-{seq} |
| `process_level_id` | UUID | NO | FK -> process_level (affected scope item) |
| `change_type` | ENUM | NO | `add_to_scope`, `remove_from_scope`, `change_wave`, `split_scope_item`, `merge_scope_items` |
| `current_value` | TEXT | NO | JSON: current state |
| `proposed_value` | TEXT | NO | JSON: proposed state |
| `justification` | TEXT | NO | Neden bu değişiklik gerekli |
| `impact_assessment` | TEXT | YES | Etki analizi (kaç workshop etkilenir, effort değişimi) |
| `status` | ENUM | NO | `requested`, `under_review`, `approved`, `rejected`, `implemented`. Default: `requested` |
| `requested_by` | UUID | NO | FK -> user |
| `reviewed_by` | UUID | YES | FK -> user |
| `approved_by` | UUID | YES | FK -> user |
| `created_at` | TIMESTAMP | NO | |
| `decided_at` | TIMESTAMP | YES | |
| `implemented_at` | TIMESTAMP | YES | |

#### 13.9.2 Yeni Tablo: `scope_change_log`

Her scope_status değişikliğinin otomatik logu.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `process_level_id` | UUID | NO | FK -> process_level |
| `field_changed` | VARCHAR(50) | NO | `scope_status`, `wave`, `fit_status` |
| `old_value` | VARCHAR(100) | YES | |
| `new_value` | VARCHAR(100) | NO | |
| `scope_change_request_id` | UUID | YES | FK -> scope_change_request (if via formal SCR) |
| `changed_by` | UUID | NO | FK -> user |
| `created_at` | TIMESTAMP | NO | |

#### 13.9.3 API

**POST /api/projects/{projectId}/scope-change-requests**
Create SCR. Auto-calculates impact (affected workshops, requirements, open items).

**POST /api/projects/{projectId}/scope-change-requests/{id}/transition**
Request: { action: "approve" | "reject", comment }

**POST /api/projects/{projectId}/scope-change-requests/{id}/implement**
Apply the approved change:
1. Update process_level.scope_status / wave
2. Log to scope_change_log
3. Cancel affected draft/scheduled workshops (if removing from scope)
4. Notify stakeholders

**GET /api/projects/{projectId}/scope-change-requests**
List with filters (status, change_type, area).

**GET /api/projects/{projectId}/process-levels/{id}/change-history**
Audit trail for a specific scope item.

#### 13.9.4 UI Integration

- Process Hierarchy: scope_status değiştiğinde otomatik log (arka planda)
- Scope Matrix: "Request Scope Change" butonu per row
- Yeni tab veya view: "Scope Change Log" — tüm SCR'ların listesi

---

### 13.10 Multi-Session Workshop Continuity

**Problem:** WS-FI-03A ve WS-FI-03B arasında veri sürekliliği tanımsız.

**Implementation Priority:** Phase 1 (önemli)

#### 13.10.1 Business Rules

**Session A kapanışında:**
1. `completed` yerine `session_completed` status'ü kullanılabilir (veya completed kalır)
2. Kararı verilemeyen step'ler `fit_decision = NULL` kalabilir (session A kapanışında zorunlu değil — sadece son session'da zorunlu)
3. Open item'lar otomatik olarak session B'ye taşınmaz — workshop'tan bağımsız zaten yaşıyorlar

**Session B başlatıldığında:**
1. Aynı scope item'ın L4 step'leri yeniden oluşturulur (yeni process_step kayıtları)
2. Session A'daki fit kararları, notes, decisions READ-ONLY olarak gösterilir (referans)
3. Session B'de:
   - A'da fit olan step'ler tekrar gösterilir ama "Previously assessed: Fit" label'ı ile
   - A'da NULL kalan step'ler açık gelir (öncelikli gündem)
   - A'da gap/partial olan step'ler tekrar tartışmaya açıktır (kararlar değişebilir)

#### 13.10.2 Yeni Alanlar: `process_step` tablosuna

| Column | Type | Description |
|--------|------|-------------|
| `previous_session_step_id` | UUID, YES | FK -> process_step. Önceki session'daki aynı L4 step |
| `carried_from_session` | INTEGER, YES | Hangi session'dan taşındı |

#### 13.10.3 API Güncellemesi

`POST /workshops/{id}/start` endpoint'ine ekleme:

```
IF workshop.session_number > 1:
    1. Find previous session workshop (same scope items, session_number - 1)
    2. For each new process_step:
        a. Find matching step in previous session (same process_level_id)
        b. Set previous_session_step_id = that step's ID
        c. Set carried_from_session = previous session number
    3. Return steps with previous session data embedded
```

**GET /api/projects/{projectId}/workshops/{id}** response update:

process_steps array'de ek alan:
```json
{
  "id": "uuid",
  "process_level": { "code": "J58.02", "name": "IC Reconciliation" },
  "fit_decision": null,
  "previous_session": {
    "session_number": 1,
    "workshop_code": "WS-FI-03A",
    "fit_decision": "gap",
    "notes": "IC netting logic tartışıldı, 3+ entity senaryosu karşılanmıyor",
    "decisions": [...],
    "open_items": [...]
  }
}
```

#### 13.10.4 Workshop Complete Validation Güncellemesi

```
IF workshop.session_number < workshop.total_sessions:
    - fit_decision NULL olan step'ler ALLOWED (sonraki session'da değerlendirilecek)
    - Sadece WARNING: "N steps not assessed — will carry to next session"
ELSE (son session):
    - Tüm step'lerde fit_decision REQUIRED (mevcut kural)
```

#### 13.10.5 Fit Propagation Güncellemesi

```
Fit status L4'e propagation SADECE son session'da yapılır.
IF workshop.session_number == workshop.total_sessions AND status == 'completed':
    → Propagate fit decisions to process_level
ELSE:
    → Do NOT propagate (ara session, kararlar değişebilir)
```

---

## 14. Updated Acceptance Criteria (v1.1)

### GAP-01: L4 Seeding [Phase 0]
- [ ] L4 seed catalog table populated with SAP Best Practice data
- [ ] Catalog import creates L4 process_level records under L3
- [ ] BPMN import parses activities into L4 records
- [ ] Manual L4 creation via UI form
- [ ] Workshop start validates L4 existence

### GAP-02: BPMN Viewer [Phase 2]
- [ ] BPMN diagram table stores URL/XML/image per process level
- [ ] Iframe embed for Signavio URLs
- [ ] bpmn-js viewer for uploaded BPMN XML
- [ ] Upload dialog for BPMN files
- [ ] Viewer shown in Process Hierarchy detail + Workshop Detail

### GAP-03: Workshop Dependencies [Phase 1]
- [ ] Workshop dependency table with 4 types
- [ ] Cross-module flag per process step
- [ ] Dependency list in Workshop Detail header
- [ ] Cross-module issues view (project-wide)
- [ ] Warning on complete if unresolved dependencies

### GAP-04: Workshop Reopen/Revision [Phase 1]
- [ ] Reopen action: completed -> in_progress with reason
- [ ] Delta design creation linked to original workshop
- [ ] Revision log tracks all fit decision changes
- [ ] Process level fit_status updated on re-assessment

### GAP-05: Role-Based Permissions [Phase 0]
- [ ] project_role table with 7 roles
- [ ] Permission check middleware on all write endpoints
- [ ] Area-scoped permissions for module leads
- [ ] HTTP 403 with actionable error message
- [ ] Batch approval for requirements (partial success support)

### GAP-06: Meeting Minutes [Phase 2]
- [ ] Template-based minutes generation (markdown)
- [ ] DOCX export via docx-js
- [ ] AI summary generation (API integration)
- [ ] workshop_document table stores generated documents
- [ ] Download/view from Workshop Detail

### GAP-07: Attachments [Phase 1]
- [ ] Polymorphic attachment table
- [ ] File upload via multipart form
- [ ] Attachment list on workshop, requirement, open item, process step
- [ ] File download endpoint
- [ ] Category-based organization
- [ ] File size limits enforced

### GAP-08: Dashboard & Reporting [Phase 2]
- [ ] Daily snapshot capture (scheduled or on-demand)
- [ ] Workshop burndown chart
- [ ] Fit/gap trend over time
- [ ] Requirement pipeline funnel
- [ ] Open item aging distribution
- [ ] Gap density heatmap (area x wave)
- [ ] Steering committee export (PPTX/PDF)

### GAP-09: Scope Change Management [Phase 1]
- [ ] Scope change request table with lifecycle
- [ ] Impact assessment auto-calculation
- [ ] Approval workflow for scope changes
- [ ] Implementation action (updates process_level + cancels workshops)
- [ ] Scope change audit log
- [ ] Change history per scope item

### GAP-10: Multi-Session Continuity [Phase 1]
- [ ] Previous session data carried to next session
- [ ] Read-only previous session display in Workshop Detail
- [ ] Relaxed validation for non-final sessions
- [ ] Fit propagation only on final session completion
- [ ] Session handoff tracking (previous_session_step_id)

---

## 15. Implementation Phase Summary

| Phase | Items | Priority | Estimated Effort |
|-------|-------|----------|-----------------|
| **Phase 0 — Critical** | GAP-01 (L4 Seeding), GAP-05 (Roles) | Must have for MVP | 3-4 sprints |
| **Phase 1 — Important** | GAP-03 (WS Dependencies), GAP-04 (Reopen), GAP-07 (Attachments), GAP-09 (Scope Change), GAP-10 (Multi-Session) | Required for production use | 5-6 sprints |
| **Phase 2 — Enhancement** | GAP-02 (BPMN), GAP-06 (Minutes), GAP-08 (Dashboard) | Nice to have, high impact | 4-5 sprints |

**Total: ~12-15 sprints additional on top of base 4-module implementation.**

---

## 16. Data Model Summary (Complete — v1.1)

### Original Tables (Section 2)
1. process_level
2. workshop
3. workshop_scope_item
4. workshop_attendee
5. workshop_agenda_item
6. process_step
7. decision
8. open_item
9. requirement
10. requirement_open_item_link
11. requirement_dependency
12. open_item_comment
13. cloud_alm_sync_log

### New Tables (Section 13)
14. l4_seed_catalog (13.1)
15. bpmn_diagram (13.2)
16. workshop_dependency (13.3)
17. cross_module_flag (13.3)
18. workshop_revision_log (13.4)
19. project_role (13.5)
20. workshop_document (13.6)
21. attachment (13.7)
22. daily_snapshot (13.8)
23. scope_change_request (13.9)
24. scope_change_log (13.9)

**Total: 24 tables**

### Modified Tables (Section 13)
- workshop: +original_workshop_id, +reopen_count, +reopen_reason, +revision_number (13.4)
- process_step: +previous_session_step_id, +carried_from_session (13.10)

---

*Document Version: 1.1*
*Updated: 2026-02-10*
*Change: Added 10 gap analysis items (Sections 13-16)*


---

### 13.11 L3 Consolidated Fit View (Business Abstraction Layer)

**Problem:** Teknik mimari L4 process_step seviyesinde karar alıyor. Doğru ve gerekli — çünkü fit/gap granülaritesi oradadır. Ancak business stakeholder'lar L3 scope item seviyesinde düşünür. "Sales Order Management fit mi?" sorusuna cevap ararlar, "BD9.03 gap" demezler.

Bu, iki risk yaratır:
- İletişim kopukluğu: Workshop çıktı raporu L4 detayında, steering committee L3 özetinde konuşuyor
- Onay belirsizliği: L3 scope item'ın "tamamlandı" sayılması için ne gerekiyor net değil

**Implementation Priority:** Phase 0 (CRITICAL — business adoption için)

#### 13.11.1 L3 Consolidated Fit Status Hesaplama

L3 node'un fit_status'ü artık sadece aggregation değil, formal bir business kararı taşıyacak:

```
L3 fit_status hesaplama kuralı:
  1. Tüm L4 çocuklarının fit_decision'larından OTOMATIK hesapla:
     - Hepsi fit → L3 = fit
     - En az 1 gap → L3 = partial_fit (gap olan L4 var ama L3 toplam olarak partial)
     - Hepsi gap → L3 = gap
     - Herhangi biri pending → L3 = pending (assessment tamamlanmamış)
  
  2. Ama bu otomatik hesaplama ÖNERI niteliğindedir.
     Business Process Owner veya Module Lead, L3 seviyesinde OVERRIDE yapabilir.
     Örnek: 5 L4'ten 4'ü fit, 1'i partial → otomatik L3 = partial_fit
             Ama BPO diyor ki "o partial workaround ile çözülür, L3'ü fit sayıyorum"
             → L3 override = fit, override_reason kaydedilir
```

#### 13.11.2 Yeni Alanlar: `process_level` tablosuna (L3 kayıtları için)

| Column | Type | Description |
|--------|------|-------------|
| `fit_status_calculated` | ENUM, YES | Otomatik hesaplanan: fit, gap, partial_fit, pending |
| `fit_status_override` | ENUM, YES | BPO/Module Lead override: fit, gap, partial_fit, NULL=no override |
| `fit_status_override_reason` | TEXT, YES | Neden override edildi |
| `fit_status_override_by` | UUID, YES | FK -> user |
| `fit_status_override_at` | TIMESTAMP, YES | Ne zaman |
| `l3_signoff_status` | ENUM, default 'pending' | `pending`, `ready_for_signoff`, `signed_off`, `reopened` |
| `l3_signoff_by` | UUID, YES | FK -> user (BPO veya Module Lead) |
| `l3_signoff_at` | TIMESTAMP, YES | |
| `l3_signoff_comment` | TEXT, YES | |

#### 13.11.3 L3 Sign-Off Mekanizması

L3 scope item'ın "tamamlandı" sayılması için:

```
PRE-CONDITIONS for L3 sign-off:
  1. Tüm L4 çocuklarda fit_decision != NULL (hepsi değerlendirilmiş)
  2. İlgili workshop(lar) completed durumda
  3. L3'e bağlı tüm P1 open item'lar closed (P2-P4 açık kalabilir, warning)
  4. L3'e bağlı tüm requirement'lar en az "approved" durumda (draft/under_review olanlar bloklar)

SIGN-OFF FLOW:
  pending → ready_for_signoff (otomatik — pre-condition'lar karşılandığında)
  ready_for_signoff → signed_off (BPO veya Module Lead onaylar)
  signed_off → reopened (eğer workshop reopen edilirse veya yeni requirement eklerse)
```

#### 13.11.4 API

**GET /api/projects/{projectId}/process-levels/{l3Id}/consolidated-view**
L3 scope item'ın business-friendly özet görünümü.

Response:
```json
{
  "id": "uuid",
  "code": "BD9",
  "name": "Sales Order Management",
  "fit_status_calculated": "partial_fit",
  "fit_status_override": null,
  "fit_status_effective": "partial_fit",
  "l3_signoff_status": "pending",
  "l4_summary": {
    "total": 5,
    "fit": 3,
    "partial_fit": 1,
    "gap": 1,
    "pending": 0
  },
  "l4_details": [
    { "code": "BD9.01", "name": "Standard Sales Order", "fit_decision": "fit" },
    { "code": "BD9.02", "name": "Pricing", "fit_decision": "fit" },
    { "code": "BD9.03", "name": "ATP Check", "fit_decision": "gap",
      "requirements": ["REQ-042"], "open_items": ["OI-023"] },
    { "code": "BD9.04", "name": "Delivery", "fit_decision": "fit" },
    { "code": "BD9.05", "name": "Billing", "fit_decision": "partial_fit",
      "requirements": ["REQ-044"] }
  ],
  "blocking_items": {
    "open_p1_items": 1,
    "unapproved_requirements": 0,
    "incomplete_workshops": 0
  },
  "workshops": [
    { "code": "WS-SD-01", "status": "completed", "date": "2026-02-10" }
  ],
  "signoff_ready": false,
  "signoff_blockers": ["1 P1 open item not closed: OI-023"]
}
```

**POST /api/projects/{projectId}/process-levels/{l3Id}/override-fit-status**
Request:
```json
{
  "override_status": "fit",
  "reason": "BD9.03 gap will be resolved via workaround — approved by steering committee"
}
```
Permission: BPO, Module Lead (own area), PM

**POST /api/projects/{projectId}/process-levels/{l3Id}/signoff**
Request:
```json
{
  "comment": "All sub-processes assessed, requirements approved, ready for realize"
}
```
Permission: BPO, Module Lead (own area)
Validation: Pre-conditions must be met (or override flag)

#### 13.11.5 Yeni Component'ler

**L3ConsolidatedCard** — Process Hierarchy'de L3 node'a ek görünüm:
- L4 breakdown bar (fit/partial/gap mini bar — mevcut)
- Effective fit status (calculated veya override, override ise ikon)
- Sign-off status badge (pending / ready / signed-off)
- Sign-off blocker list (eğer pending ise neden ready değil)
- "Sign Off" butonu (yetkili kullanıcıda)
- "Override Fit Status" butonu (yetkili kullanıcıda)

**L3SignOffDialog** — Sign-off onay dialog:
- L4 özeti gösterir
- Blocker varsa listeler
- Override ile sign-off seçeneği (blocker'ları kabul ederek)
- Comment alanı

#### 13.11.6 Business Rule: Fit Status Display

UI'da L3 için iki satır gösterilir:

```
BD9 — Sales Order Management
  Assessment: Partial Fit (3 fit, 1 partial, 1 gap)     ← hesaplanan, L4 detayı
  Business Decision: Fit ✓ (override by H. Demir)       ← override varsa
  Sign-off: Ready for Sign-off                           ← sign-off durumu
```

Steering committee raporunda L3'ün "effective" durumu (override varsa override, yoksa calculated) gösterilir. L4 detayı sadece drill-down'da.

---

### 13.12 L2 Process Area Milestone — Scope Confirmation

**Problem:** L2 (Process Area — FI, SD, MM...) workshop dışı bir seviye. Doğru. Ama L2'nin ne zaman "done" sayılacağı belirsiz. Steering committee "Finance bitmiş mi?" diye sorduğunda formal cevap yok.

**Implementation Priority:** Phase 0 (CRITICAL — governance için)

#### 13.12.1 L2 Milestone Hesaplama

```
L2 milestone status = f(child L3 signoff durumları)

  pending:     En az 1 L3 pending (assessment başlamadı veya devam ediyor)
  in_progress: En az 1 L3 signed_off, ama hepsi değil
  ready:       Tüm L3'ler signed_off
  confirmed:   PM veya Steering Committee formal onay verdi
```

#### 13.12.2 Yeni Alanlar: `process_level` tablosuna (L2 kayıtları için)

| Column | Type | Description |
|--------|------|-------------|
| `l2_milestone_status` | ENUM, default 'pending' | `pending`, `in_progress`, `ready`, `confirmed` |
| `l2_milestone_calculated` | ENUM, YES | Otomatik hesaplanan (pending/in_progress/ready) |
| `l2_confirmed_by` | UUID, YES | FK -> user |
| `l2_confirmed_at` | TIMESTAMP, YES | |
| `l2_confirmation_comment` | TEXT, YES | |
| `l2_target_date` | DATE, YES | Hedef tamamlanma tarihi |

#### 13.12.3 Otomatik Hesaplama

```
ON L3 signoff_status change:
  1. Get parent L2
  2. Get all L3 children of L2 (where scope_status = 'in_scope')
  3. Calculate:
     - all pending → L2 = pending
     - any signed_off but not all → L2 = in_progress
     - all signed_off → L2 = ready
  4. Update l2_milestone_calculated
  5. If l2_milestone_status != 'confirmed':
       l2_milestone_status = l2_milestone_calculated
```

#### 13.12.4 L2 Confirmation

```
POST /api/projects/{projectId}/process-levels/{l2Id}/confirm-milestone
Request: { comment }
Permission: PM, Steering Committee member
Pre-condition: l2_milestone_calculated = 'ready'
Side effect: l2_milestone_status = 'confirmed'
```

L2 confirmed olduktan sonra, altındaki L3'lerin sign-off'u değişirse (workshop reopen gibi):
- l2_milestone_status otomatik 'in_progress'a geri döner
- l2_confirmed_by/at korunur (geçmiş kayıt olarak)
- Yeni confirmation gerekir

#### 13.12.5 API

**GET /api/projects/{projectId}/area-milestones**
Tüm L2 process area'larının milestone durumu.

Response:
```json
{
  "data": [
    {
      "id": "uuid",
      "code": "PA-FIN",
      "name": "Finance",
      "process_area": "FI",
      "wave": 1,
      "l2_milestone_status": "in_progress",
      "l2_target_date": "2026-03-15",
      "l3_summary": {
        "total_in_scope": 4,
        "signed_off": 2,
        "ready_for_signoff": 1,
        "pending": 1
      },
      "l3_children": [
        { "code": "J58", "name": "Accounting & Close", "l3_signoff_status": "signed_off" },
        { "code": "BD3", "name": "Accounts Payable", "l3_signoff_status": "signed_off" },
        { "code": "J77", "name": "Cash Management", "l3_signoff_status": "ready_for_signoff" },
        { "code": "BD9", "name": "Credit Management", "l3_signoff_status": "pending" }
      ],
      "completion_pct": 50.0,
      "on_track": true,
      "days_to_target": 33
    }
  ]
}
```

#### 13.12.6 Yeni Component: AreaMilestoneTracker

Workshop Hub veya Dashboard'da gösterilen widget:

```
┌─────────────────────────────────────────────────┐
│  PROCESS AREA MILESTONES                        │
├──────┬─────────┬───────────┬─────────┬──────────┤
│ Area │ Status  │ L3 Ready  │ Target  │ On Track │
├──────┼─────────┼───────────┼─────────┼──────────┤
│ FI   │ ●●○○    │ 2/4       │ Mar 15  │ ✓        │
│ CO   │ ●○○○    │ 1/3       │ Mar 15  │ ✓        │
│ SD   │ ●●●○    │ 3/5       │ Apr 01  │ ⚠        │
│ MM   │ ○○○○    │ 0/4       │ Apr 15  │ ✓        │
│ PP   │ ○○○○    │ 0/6       │ May 01  │ ✓        │
└──────┴─────────┴───────────┴─────────┴──────────┘
```

Her satır:
- Area kodu ve adı
- Progress indicator (filled dots = signed_off L3'ler / total in-scope L3'ler)
- L3 ready count
- Target date
- On track indicator (bugüne göre beklenen ilerleme ile karşılaştırma)
- Tıklama → L3 detayına drill-down

#### 13.12.7 Dashboard Integration

Explore Dashboard'a (Section 13.8) iki widget eklenir:

| Widget | Description |
|--------|-------------|
| Area Milestone Progress | Horizontal bar chart — her area için completion % |
| Milestone Timeline | Gantt-benzeri görünüm — area target dates vs actual completion |

#### 13.12.8 Steering Committee Report Update

Section 13.8'deki PPTX export'a yeni slide:

- **Slide 2 (updated): Area Milestone Status** — her process area'nın milestone durumu, target date, L3 sign-off oranları

---

## 17. Updated Acceptance Criteria (v1.2)

### GAP-11: L3 Consolidated Fit View [Phase 0]
- [ ] L3 fit_status otomatik L4'lerden hesaplanır
- [ ] BPO/Module Lead fit_status override yapabilir (sebep zorunlu)
- [ ] L3 sign-off pre-condition kontrolü (tüm L4 assessed, P1 OI closed, REQ approved)
- [ ] Sign-off flow: pending -> ready_for_signoff -> signed_off
- [ ] L3ConsolidatedCard component: effective status + sign-off badge + blocker list
- [ ] Consolidated view API: L4 breakdown + blocking items + sign-off status
- [ ] Workshop reopen L3 sign-off'u otomatik geri alır

### GAP-12: L2 Area Milestone [Phase 0]
- [ ] L2 milestone otomatik L3 sign-off'lardan hesaplanır
- [ ] pending -> in_progress -> ready -> confirmed flow
- [ ] PM/Steering formal confirmation aksiyonu
- [ ] Target date tracking ve on-track hesaplama
- [ ] AreaMilestoneTracker widget (Hub + Dashboard)
- [ ] Area milestone progress bar chart
- [ ] Milestone timeline (Gantt) widget
- [ ] L2 confirmation geri dönüşü (L3 sign-off değişirse)
- [ ] Steering committee slide'ına area milestone eklenmesi

---

## 18. Data Model Summary (Complete — v1.2)

### All Tables (26 total)

**Original (Section 2):** 13 tables
1. process_level *(updated: +6 L3 fields, +5 L2 fields)*
2. workshop *(updated: +4 fields from 13.4)*
3. workshop_scope_item
4. workshop_attendee
5. workshop_agenda_item
6. process_step *(updated: +2 fields from 13.10)*
7. decision
8. open_item
9. requirement
10. requirement_open_item_link
11. requirement_dependency
12. open_item_comment
13. cloud_alm_sync_log

**Gap Analysis (Section 13):** 13 new tables
14. l4_seed_catalog (13.1)
15. bpmn_diagram (13.2)
16. workshop_dependency (13.3)
17. cross_module_flag (13.3)
18. workshop_revision_log (13.4)
19. project_role (13.5)
20. workshop_document (13.6)
21. attachment (13.7)
22. daily_snapshot (13.8)
23. scope_change_request (13.9)
24. scope_change_log (13.9)

**No new tables for 13.11 and 13.12** — fields added to existing process_level table.

### Updated Implementation Phases

| Phase | Items | Priority |
|-------|-------|----------|
| **Phase 0** | GAP-01 (L4 Seeding), GAP-05 (Roles), GAP-11 (L3 Consolidated), GAP-12 (L2 Milestone) | Must have |
| **Phase 1** | GAP-03 (WS Deps), GAP-04 (Reopen), GAP-07 (Attachments), GAP-09 (Scope Change), GAP-10 (Multi-Session) | Important |
| **Phase 2** | GAP-02 (BPMN), GAP-06 (Minutes), GAP-08 (Dashboard) | Enhancement |

---

*Document Version: 1.2*
*Updated: 2026-02-10*
*Change: Added L3 Consolidated Fit View (13.11) and L2 Area Milestone (13.12)*


---

### 13.11 L3 Konsolide Fit Kararı (Business-Level Decision)

**Problem:** Fit kararları L4 process_step seviyesinde alınıyor. Teknik olarak doğru ama business "ben BD9 için karar verdim" diyor, "BD9.03 için" demiyor. Steering committee'ye giden raporda L3 seviyesinde net bir karar olması gerekiyor. Ayrıca L4 toplamı bazen business kararıyla örtüşmüyor — 4/5 fit, 1/5 partial olan bir scope item business tarafından "Fit" kabul edilebiliyor.

**Implementation Priority:** Phase 0 — CRITICAL

#### 13.11.1 Konsept

İki katmanlı karar modeli:

```
L4 Detay Kararları (teknik doğruluk)
    BD9.01 = Fit
    BD9.02 = Fit
    BD9.03 = Gap
    BD9.04 = Fit
    BD9.05 = Partial Fit
        |
        v
L3 Konsolide Karar (business algısı)
    BD9 = Partial Fit (system suggestion)
    BD9 = Fit (business override — "gap minimal, workaround kabul edildi")
```

Sistem L4 kararlarından L3 önerisini hesaplar. Business bunu kabul eder veya override eder.

#### 13.11.2 Yeni Alanlar: `process_level` tablosuna (L3 kayıtlar için)

| Column | Type | Description |
|--------|------|-------------|
| `consolidated_fit_decision` | ENUM('fit','gap','partial_fit'), YES | Business-level konsolide karar. NULL = henüz verilmedi |
| `system_suggested_fit` | ENUM('fit','gap','partial_fit'), YES | Sistem önerisi (L4'lerden hesaplanan) |
| `consolidated_decision_override` | BOOLEAN, default false | true = business, sistem önerisini override etti |
| `consolidated_decision_rationale` | TEXT, YES | Override sebebi veya karar notu |
| `consolidated_decided_by` | UUID, YES | FK -> user. Kararı veren kişi |
| `consolidated_decided_at` | TIMESTAMP, YES | Karar tarihi |

#### 13.11.3 Hesaplama Kuralı (System Suggestion)

```
all_l4_decisions = [child.fit_status for child in l3.children where child.fit_status is not null]

if len(all_l4_decisions) == 0:
    system_suggested_fit = null  # henüz hiç karar yok

elif all(d == 'fit' for d in all_l4_decisions):
    system_suggested_fit = 'fit'

elif any(d == 'gap' for d in all_l4_decisions):
    gap_ratio = count('gap') / len(all_l4_decisions)
    if gap_ratio > 0.5:
        system_suggested_fit = 'gap'
    else:
        system_suggested_fit = 'partial_fit'

else:  # mix of fit and partial, no gap
    system_suggested_fit = 'partial_fit'
```

Bu hesaplama, workshop complete olduğunda otomatik çalışır ve `system_suggested_fit` alanına yazılır.

#### 13.11.4 Karar Akışı

```
Workshop Complete
    |
    v
Sistem L4'lerden L3 önerisini hesaplar
    -> system_suggested_fit = "partial_fit"
    |
    v
Facilitator / Module Lead / BPO, Workshop Detail'de L3 kararını görür:
    "Sistem önerisi: Partial Fit (4 Fit, 1 Gap)"
    [Onayla: Partial Fit]  [Override: Fit]  [Override: Gap]
    |
    v
Override seçilirse -> rationale zorunlu
    "Gap minimal — BD9.03 workaround ile çözülecek, REQ-042 oluşturuldu"
    |
    v
consolidated_fit_decision = 'fit'
consolidated_decision_override = true
consolidated_decision_rationale = "..."
consolidated_decided_by = user_id
consolidated_decided_at = now()
```

#### 13.11.5 API

**POST /api/projects/{projectId}/process-levels/{l3Id}/consolidate-fit**
Request:
```json
{
  "decision": "fit",
  "rationale": "Gap minimal, workaround accepted",
  "decided_by_id": "uuid"
}
```

Validation:
- process_level.level must be 3
- All L4 children must have fit_status set (no pending)
- Permission: PM, Module Lead (own area), BPO

Business Logic:
1. Set consolidated_fit_decision
2. Compare with system_suggested_fit -> set override flag
3. If override -> rationale required
4. Log to scope_change_log (field: consolidated_fit_decision)
5. Recalculate parent L2 readiness (see 13.12)

#### 13.11.6 Raporlama Etkisi

Steering committee sunumunda ve scope matrix'te:
- `consolidated_fit_decision` gösterilir (business kararı)
- Override varsa küçük uyarı ikonu: "Business override — detay için tıklayın"
- Dashboard'daki fit/gap dağılımı `consolidated_fit_decision` üzerinden hesaplanır
- L4 detay kararları drill-down'da görünür

Bu sayede:
- Business "BD9 = Fit" der, steering committee bunu görür
- Teknik ekip "BD9.03 = Gap, REQ-042 var" detayına drill-down eder
- İki katman birbirini tamamlar, çelişmez

#### 13.11.7 Workshop Detail UI Güncellemesi

Workshop Complete sonrası, Workshop Detail'de yeni bir section:

```
+-------------------------------------------------------+
| L3 CONSOLIDATED DECISION                               |
+-------------------------------------------------------+
| Scope Item: BD9 — Sales Order Management               |
|                                                        |
| L4 Breakdown:                                          |
|   BD9.01 Std Sales Order    [FIT]                      |
|   BD9.02 Pricing            [FIT]                      |
|   BD9.03 ATP Check          [GAP]    -> REQ-042        |
|   BD9.04 Delivery           [FIT]                      |
|   BD9.05 Billing            [PARTIAL] -> REQ-043       |
|                                                        |
| System Suggestion: PARTIAL FIT                         |
|                                                        |
| Business Decision:                                     |
|   ( ) Accept: Partial Fit                              |
|   (x) Override: Fit                                    |
|   ( ) Override: Gap                                    |
|                                                        |
| Rationale (required for override):                     |
| [Gap minimal — BD9.03 workaround kabul edildi,         |
|  REQ-042 ile çözülecek. BPO H. Demir onayladı.]       |
|                                                        |
| [Confirm Decision]                                     |
+-------------------------------------------------------+
```

---

### 13.12 L2 Scope Confirmation Milestone

**Problem:** L2 process area'nın tamamlanma durumu hiçbir yerde formal olarak onaylanmıyor. SAP Activate governance'ta alan bazlı sign-off kritik milestone. "Finance alanı explore tamamdır" resmi kararı yok.

**Implementation Priority:** Phase 0 — CRITICAL

#### 13.12.1 Konsept

L2, kendi altındaki tüm L3 scope item'lar konsolide fit kararı aldığında otomatik olarak "ready for confirmation" durumuna geçer. Module lead bu noktada formal sign-off verir.

```
L2: PA-FIN (Finance)
    |
    +-- L3: J58 Accounting  -> consolidated: Fit       ✓
    +-- L3: BD3 Accounts Payable -> consolidated: Fit  ✓
    +-- L3: J77 Cash Management -> consolidated: Partial ✓
    +-- L3: BDX Asset Mgmt -> consolidated: null       ✗ (henüz karar yok)
    |
    Status: NOT READY (1/4 pending)

--- after BDX workshop completes and consolidates ---

    +-- L3: BDX Asset Mgmt -> consolidated: Fit        ✓
    |
    Status: READY FOR CONFIRMATION
    -> Module Lead sign-off required
```

#### 13.12.2 Yeni Alanlar: `process_level` tablosuna (L2 kayıtlar için)

| Column | Type | Description |
|--------|------|-------------|
| `confirmation_status` | ENUM('not_ready','ready','confirmed','confirmed_with_risks'), YES | NULL for non-L2 |
| `confirmation_note` | TEXT, YES | Sign-off notu |
| `confirmed_by` | UUID, YES | FK -> user (Module Lead) |
| `confirmed_at` | TIMESTAMP, YES | |
| `readiness_pct` | DECIMAL(5,2), YES | Computed: (assessed L3 count / total in-scope L3 count) * 100 |

#### 13.12.3 Readiness Hesaplama

```
in_scope_l3_children = [c for c in l2.children if c.scope_status == 'in_scope']
assessed_l3 = [c for c in in_scope_l3_children if c.consolidated_fit_decision is not null]

readiness_pct = (len(assessed_l3) / len(in_scope_l3_children)) * 100

if readiness_pct == 100:
    confirmation_status = 'ready'
else:
    confirmation_status = 'not_ready'
```

Bu hesaplama her L3 consolidated karar sonrası otomatik güncellenir.

#### 13.12.4 Confirmation Akışı

```
L2 readiness_pct reaches 100%
    -> confirmation_status = 'ready'
    -> Module Lead notification: "Finance area ready for confirmation"
    |
    v
Module Lead reviews:
    - Tüm L3 konsolide kararları
    - Toplam requirement sayısı ve effort
    - Açık open item sayısı
    - Override kararları (varsa)
    |
    v
İki seçenek:
    [Confirm]                    [Confirm with Risks]
    confirmation_status =        confirmation_status =
      'confirmed'                  'confirmed_with_risks'
    confirmation_note =          confirmation_note =
      "Finance explore complete"   "3 open items remaining,
                                    accepted risk"
```

#### 13.12.5 API

**GET /api/projects/{projectId}/process-levels/l2-readiness**
Tüm L2'lerin readiness durumunu döner.

Response:
```json
{
  "data": [
    {
      "id": "uuid",
      "code": "PA-FIN",
      "name": "Finance",
      "readiness_pct": 100.0,
      "confirmation_status": "ready",
      "total_l3": 4,
      "assessed_l3": 4,
      "total_requirements": 12,
      "total_effort_hours": 340,
      "open_items_remaining": 3,
      "fit_summary": { "fit": 2, "partial_fit": 1, "gap": 1 },
      "confirmed_by": null,
      "confirmed_at": null
    },
    {
      "id": "uuid",
      "code": "PA-SD",
      "name": "Sales & Distribution",
      "readiness_pct": 60.0,
      "confirmation_status": "not_ready",
      "total_l3": 5,
      "assessed_l3": 3,
      "pending_l3": ["BD9", "BDX"]
    }
  ]
}
```

**POST /api/projects/{projectId}/process-levels/{l2Id}/confirm**
Request:
```json
{
  "status": "confirmed" | "confirmed_with_risks",
  "note": "Finance explore complete. 3 open items accepted as risk.",
  "confirmed_by_id": "uuid"
}
```

Validation:
- process_level.level must be 2
- readiness_pct must be 100 (tüm L3'ler assessed)
- Permission: PM, Module Lead (own area)
- Open items warning (count shown, not blocking)

#### 13.12.6 Explore Fazı Kapanış Gate'i

Explore fazının resmi kapanışı için:

```
ALL L2 areas confirmation_status IN ('confirmed', 'confirmed_with_risks')
    -> Explore phase = READY TO CLOSE
    -> PM sign-off required
    -> Steering committee approval
```

Bu, dashboard'da gösterilir:

```
EXPLORE PHASE READINESS
=======================
Finance (PA-FIN)        [██████████] 100%  ✓ Confirmed
Sales (PA-SD)           [██████░░░░]  60%  ✗ Not Ready
Materials (PA-MM)       [████████░░]  80%  ✗ Not Ready
Production (PA-PP)      [██░░░░░░░░]  20%  ✗ Not Ready
...
Overall:                [██████░░░░]  62%  ✗ Not Ready
```

#### 13.12.7 Yeni Tablo: `phase_gate`

Explore fazı kapanış onayını formal olarak kaydetmek için:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `phase` | ENUM | NO | `explore`, `realize`, `deploy` |
| `gate_type` | ENUM | NO | `area_confirmation`, `phase_closure` |
| `process_level_id` | UUID | YES | FK -> process_level (L2, for area confirmation) |
| `status` | ENUM | NO | `pending`, `approved`, `approved_with_conditions`, `rejected` |
| `conditions` | TEXT | YES | Koşullar (varsa) |
| `approved_by` | UUID | YES | FK -> user |
| `approved_at` | TIMESTAMP | YES | |
| `notes` | TEXT | YES | |
| `created_at` | TIMESTAMP | NO | |

#### 13.12.8 Process Hierarchy UI Güncellemesi

L2 node'lar yeni görsel:

```
L2 node (before confirmation):
[PA-FIN] Finance  [████░░ 75%]  ⏳ Not Ready

L2 node (ready):
[PA-FIN] Finance  [██████ 100%]  🟡 Ready for Confirmation

L2 node (confirmed):
[PA-FIN] Finance  [██████ 100%]  ✅ Confirmed — A. Schmidt, 15 Feb

L2 node (confirmed with risks):
[PA-FIN] Finance  [██████ 100%]  ⚠️ Confirmed with Risks — 3 OIs open
```

---

### Updated Section References

#### Section 5.1 Fit Status Propagation — REVISED

Previous rule (L3 calculated from worst L4) is now REPLACED:

```
L4 -> fit_status set directly from process_step.fit_decision (unchanged)

L3 -> TWO values:
    1. system_suggested_fit: calculated from L4 children (algorithm in 13.11.3)
    2. consolidated_fit_decision: business decision (may override system suggestion)
    
    Reporting and dashboard use consolidated_fit_decision.
    If consolidated_fit_decision is null, system_suggested_fit shown as "pending confirmation".

L2 -> THREE values:
    1. fit_summary: aggregate counts from L3 consolidated decisions
    2. readiness_pct: % of in-scope L3 with consolidated decision
    3. confirmation_status: formal sign-off state

L1 -> fit_summary aggregated from L2 fit_summaries (unchanged)
```

#### Section 12 Acceptance Criteria — ADDITIONS

### GAP-11: L3 Consolidated Fit Decision [Phase 0]
- [ ] L3 stores both system_suggested_fit and consolidated_fit_decision
- [ ] System suggestion auto-calculated from L4 children on workshop complete
- [ ] Override option with mandatory rationale
- [ ] Permission check: PM, Module Lead (area), BPO
- [ ] Steering committee reports use consolidated decision
- [ ] Override indicator visible in scope matrix and hierarchy

### GAP-12: L2 Scope Confirmation Milestone [Phase 0]
- [ ] L2 readiness_pct auto-calculated from L3 consolidated decisions
- [ ] Automatic status transition: not_ready -> ready when 100%
- [ ] Confirm / Confirm with Risks sign-off action
- [ ] Module Lead notification on readiness
- [ ] Phase gate table for formal closure tracking
- [ ] Explore phase closure requires all L2 confirmed
- [ ] Dashboard shows L2 readiness progress per area

---

### Updated Phase Summary (v1.2)

| Phase | Items | Notes |
|-------|-------|-------|
| **Phase 0** | GAP-01 (L4 Seeding), GAP-05 (Roles), **GAP-11 (L3 Consolidated)**, **GAP-12 (L2 Confirmation)** | +2 items, now 4 critical items |
| **Phase 1** | GAP-03, GAP-04, GAP-07, GAP-09, GAP-10 | Unchanged |
| **Phase 2** | GAP-02, GAP-06, GAP-08 | Unchanged |

### Updated Table Count (v1.2)

Original: 13 tables
Gap Analysis (13.1-13.10): +11 tables
Gap Analysis (13.11-13.12): +1 table (phase_gate)
Modified tables: +2 (process_level extended, process_step extended)

**Total: 25 tables**
