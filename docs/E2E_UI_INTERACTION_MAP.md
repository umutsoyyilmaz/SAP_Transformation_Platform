# SAP Transformation Platform — Comprehensive UI Interaction Map

> **Purpose:** Complete mapping of every screen, button, filter, modal, navigation action, and user interaction for building a comprehensive E2E test suite.
>
> **Generated from:** ~30 frontend JS files (views + components), ~15,000 lines of code.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Global Infrastructure](#global-infrastructure)
3. [Programs View](#1-programs-view)
4. [Project Setup View](#2-project-setup-view)
5. [Explore Dashboard](#3-explore-dashboard)
6. [Explore Hierarchy](#4-explore-hierarchy)
7. [Explore Workshops](#5-explore-workshops)
8. [Explore Workshop Detail](#6-explore-workshop-detail)
9. [Explore Requirements](#7-explore-requirements)
10. [Backlog View](#8-backlog-view)
11. [Integration Factory](#9-integration-factory)
12. [Test Planning](#10-test-planning)
13. [Test Execution](#11-test-execution)
14. [Defect Management](#12-defect-management)
15. [Cutover Hub](#13-cutover-hub)
16. [Data Factory](#14-data-factory)
17. [RAID Log](#15-raid-log)
18. [Reports View](#16-reports-view)
19. [Executive Cockpit](#17-executive-cockpit)
20. [AI Query Assistant](#18-ai-query-assistant)
21. [AI Admin Dashboard](#19-ai-admin-dashboard)
22. [Components](#components)

---

## Architecture Overview

| Aspect | Detail |
|--------|--------|
| **Framework** | Vanilla JS SPA — no React/Vue/Angular |
| **Module Pattern** | IIFE (Immediately Invoked Function Expression) per view |
| **Routing** | Hash-based via `App.navigate(viewName)` |
| **API Client** | `API` object (api.js) — wraps fetch with auto-injected user/project context |
| **Explore API** | `ExploreAPI` object — typed wrappers for all explore-phase endpoints |
| **Charts** | Chart.js for all visualizations |
| **Auth** | `RoleNav` component — sessionStorage-based user context, permission-based button guards |
| **Notifications** | `NotificationPanel` — bell icon with unread count, 30s polling |
| **AI Suggestions** | `SuggestionBadge` — 💡 icon badge with 60s polling, approve/reject |
| **Program Context** | `localStorage` key `sap_active_program` — required by most views |

### View Registry (app.js)
```
dashboard, executive-cockpit, programs, backlog, test-planning,
test-execution, defect-management, integration, data-factory,
cutover, raid, reports, project-setup, ai-query, ai-admin,
explore-dashboard, explore-hierarchy, explore-workshops,
explore-workshop-detail, explore-requirements
```

---

## Global Infrastructure

### app.js — SPA Router & Dashboard

**Route:** `dashboard` (default)

#### Navigation
| Action | Trigger | Target |
|--------|---------|--------|
| Sidebar click | `.sidebar-item` click | `App.navigate(viewName)` |
| Program guard | View requires program | Redirects to `programs` if none selected |
| Quick nav buttons | Dashboard buttons | 9 views: programs, explore-dashboard, explore-hierarchy, explore-workshops, explore-requirements, backlog, test-planning, test-execution, defect-management |

#### Dashboard KPI Cards
| KPI | API Call |
|-----|----------|
| Workshops | `GET /explore/workshops/stats` |
| WS Completion % | `GET /explore/workshops/stats` |
| Requirements | `GET /explore/requirements/stats` |
| Open Items | `GET /explore/open-items/stats` |
| Backlog Items | `GET /programs/{pid}/backlog/stats` |
| Open Defects | `GET /programs/{pid}/testing/defects` |

#### Global Utilities
| Function | Description |
|----------|-------------|
| `App.toast(message, type)` | Toast notification (success/error/info/warning) |
| `App.openModal(html)` | Opens modal overlay |
| `App.closeModal()` | Closes modal overlay |
| `App.getActiveProgram()` | Returns active program from localStorage |
| `App.setActiveProgram(prog)` | Sets active program + updates badge |

### api.js — Fetch Wrapper

| Method | Auto-injected Fields |
|--------|---------------------|
| `API.get(url)` | — |
| `API.post(url, body)` | `user_id`, `user_name`, `created_by`, `project_id` |
| `API.put(url, body)` | `user_id`, `user_name`, `changed_by`, `project_id` |
| `API.patch(url, body)` | `user_id`, `user_name`, `changed_by`, `project_id` |
| `API.delete(url)` | — |

---

## 1. Programs View

**Route:** `programs` | **Module:** `ProgramsView` | **File:** program.js (817 lines)

### Navigation Flow
```
Card Grid → Card Click → Detail View (tabbed)
Detail View ← Back button → Card Grid
```

### Buttons
| Button | Location | Action |
|--------|----------|--------|
| `+ New Program` | Page header | Opens create modal |
| `Select & Open` | Card footer | Sets active program, navigates to dashboard |
| `Clear Selection` | Card footer | Clears active program |
| `Delete` | Card footer | Deletes program (confirm dialog) |
| `Edit Program` | Detail header | Opens edit modal |
| `← Back` | Detail header | Returns to card grid |

### Tabs (Detail View)
| Tab | Content | Actions |
|-----|---------|---------|
| **Overview** | Program metadata display | — |
| **Phases & Gates** | Phase table with nested gate sub-table | + Phase, Edit/Delete Phase, + Gate, Edit/Delete Gate |
| **Workstreams** | Workstream table | + Workstream, Edit/Delete |
| **Team** | Team member table | + Member, Edit/Delete |
| **Committees** | Committee table | + Committee, Edit/Delete |

### Modals/Forms
| Modal | Required Fields | Notable Fields |
|-------|-----------------|----------------|
| **Program Create/Edit** | name | project_type (greenfield/brownfield/bluefield/selective_data_transition), methodology, status, priority, sap_product, deployment_option, start/end dates |
| **Phase Create/Edit** | name | status, planned_start/end |
| **Gate Create/Edit** | name | type, status, planned_date |
| **Workstream Create/Edit** | name | status, lead |
| **Team Member Create/Edit** | name | role, email, is_active |
| **Committee Create/Edit** | name | type, frequency, chair |

### API Calls
```
GET    /programs
POST   /programs
GET    /programs/{id}
PUT    /programs/{id}
DELETE /programs/{id}
GET    /programs/{id}/phases
POST   /programs/{id}/phases
PUT    /phases/{id}
DELETE /phases/{id}
POST   /phases/{id}/gates
PUT    /gates/{id}
DELETE /gates/{id}
GET    /programs/{id}/workstreams
POST   /programs/{id}/workstreams
PUT    /workstreams/{id}
DELETE /workstreams/{id}
GET    /programs/{id}/team-members
POST   /programs/{id}/team-members
PUT    /team-members/{id}
DELETE /team-members/{id}
GET    /programs/{id}/committees
POST   /programs/{id}/committees
PUT    /committees/{id}
DELETE /committees/{id}
```

---

## 2. Project Setup View

**Route:** `project-setup` | **Module:** `ProjectSetupView` | **File:** project_setup.js (1143 lines)

### Tabs
| Tab | Content |
|-----|---------|
| **Process Hierarchy** | Tree/Table view of L1→L4 process levels |
| Team | Placeholder |
| Phases | Placeholder |
| Settings | Placeholder |

### View Modes
| Mode | Description |
|------|-------------|
| **Tree View** | Expandable tree nodes, split layout |
| **Table View** | Flat table with inline add row |

### KPI Strip
`L1 Areas` · `L2 Groups` · `L3 Scope Items` · `L4 Steps` · `In Scope %`

### Filters
| Filter | Type | Options |
|--------|------|---------|
| Search | Text input | Free text |
| Area | Dropdown | FI/CO/MM/SD/PP/HR/QM/EWM/BC |
| Scope | Dropdown | in_scope/out_of_scope/deferred |

### Buttons
| Button | Action |
|--------|--------|
| `+ Add L1 Area` | Opens create modal for L1 |
| `📚 Import Template` | Opens template import modal |
| `🤖 AI Suggested` | Coming soon (placeholder) |
| `✍️ Start from Scratch` | Opens bulk entry modal |
| `+ Add L{N+1}` per parent | Opens create modal for child level |
| Edit/Delete per node | Edit/Delete process level |

### Modals
| Modal | Description |
|-------|-------------|
| **Create/Edit Process Level** | Name, code, description, area, scope, parent |
| **Template Import** | 5 SAP templates: S/4HANA Finance, S/4HANA Logistics, S/4HANA HR, SuccessFactors, Ariba |
| **AI Suggested** | Placeholder (toast: "coming soon") |
| **Bulk Entry** | Two modes: Grid (8-row table) + Paste (TSV preview), Download Template button |

### API Calls
```
ExploreAPI.levels.list/create/update/delete
ExploreAPI.levels.bulkCreate
ExploreAPI.levels.importTemplate
```

---

## 3. Explore Dashboard

**Route:** `explore-dashboard` | **Module:** `ExploreDashboardView` | **File:** explore_dashboard.js (551 lines)

### KPI Strip
`Workshops` · `WS Completion %` · `Requirements` · `Open Items` · `Overdue OIs` · `Go-Live Readiness %`

### Charts (10 total)
| Chart | Type | Data |
|-------|------|------|
| Workshop Completion Trend | Line | Over time |
| Fit/Gap/Partial Trend | Stacked area | Over time |
| Wave Progress | Bar | Per wave |
| Requirement Pipeline | Bar | By status |
| Go-Live Readiness | Gauge | Single metric |
| Impact Distribution | Doughnut | By impact level |
| Area Coverage Matrix | Table | Per area |
| Open Items by Assignee | Bar | By assignee |
| Scope Coverage | Donut | In/out scope |
| Gap Density Heatmap | Color matrix | By area |

### Quick Nav Buttons
| Button | Target |
|--------|--------|
| 🏗️ Hierarchy | `explore-hierarchy` |
| 📋 Workshops | `explore-workshops` |
| 📝 Requirements | `explore-requirements` |
| 📸 Capture Snapshot | `ExploreAPI.snapshots.create()` |

### API Calls
```
ExploreAPI.snapshots.list
ExploreAPI.levels.list (multiple levels)
ExploreAPI.workshops.stats
ExploreAPI.requirements.stats
ExploreAPI.openItems.stats
ExploreAPI.levels.scopeMatrix
```

---

## 4. Explore Hierarchy

**Route:** `explore-hierarchy` | **Module:** `ExploreHierarchyView` | **File:** explore_hierarchy.js (899 lines)

### View Modes
| Mode | Layout |
|------|--------|
| **Tree View** | Split layout: left tree + right detail panel |
| **Scope Matrix** | Flat L3 table with sortable columns |

### KPI Strip
`L1 Areas` · `L2 Groups` · `L3 Scope Items` · `L4 Steps` + Fit Distribution bar

### Filters
| Filter | Type | Options |
|--------|------|---------|
| Search | Text | Free text |
| Fit Status | Multi-select | fit/gap/partial_fit/pending |
| Area/Module | Multi-select | Dynamic from data |
| Wave | Dropdown | Dynamic from data |

### Tree Interactions
| Action | Trigger |
|--------|---------|
| Expand/collapse node | Click arrow |
| Select node | Click node → shows detail panel |
| Node actions | Context buttons per level |

### Detail Panel Tabs (right side)
| Tab | Content |
|-----|---------|
| Overview | Process level metadata |
| Fit | Fit/gap status, override |
| Requirements | Linked requirements |
| Workshop | Linked workshop info |

### Scope Matrix Table
| Feature | Description |
|---------|-------------|
| Sortable columns | Click header to sort |
| Scope Change action | Opens scope change request modal |

### Modals
| Modal | Fields |
|-------|--------|
| **L3 Sign-Off** | Override status, comment |
| **L4 Seeding** | 3 modes: Catalog/BPMN/Manual |
| **Scope Change Request** | Type, justification |

### API Calls
```
ExploreAPI.levels.list (L1-L4)
ExploreAPI.levels.scopeMatrix
ExploreAPI.levels.consolidateFit
ExploreAPI.levels.overrideFitStatus
ExploreAPI.signoff.performL3
ExploreAPI.levels.seedFromCatalog
ExploreAPI.scopeChangeRequests.create
```

---

## 5. Explore Workshops

**Route:** `explore-workshops` | **Module:** `ExploreWorkshopsView` | **File:** explore_workshops.js (670 lines)

### View Modes
| Mode | Description |
|------|-------------|
| **Table** | Sortable data table, row click → workshop detail |
| **Kanban** | 4 columns: Draft/Scheduled/In Progress/Completed |
| **Capacity** | Per-facilitator load cards |

### KPI Strip
`Workshops count` · `Progress %` · `Active` · `Open Items` · `Gaps` + Status Distribution bar

### Filters
| Filter | Options |
|--------|---------|
| Search | Free text |
| Status | draft/scheduled/in_progress/completed |
| Area | Dynamic |
| Wave | Dynamic |
| Facilitator | Dynamic |

### Group By
`none` · `wave` · `area` · `facilitator` · `status`

### Area Milestone Tracker
Per-area progress dots showing completion status

### Create Workshop Modal
| Field | Type | Required |
|-------|------|----------|
| Name | Text | ✅ |
| Type | Select | initial/delta/review |
| Date | Date | — |
| Facilitator | TeamMemberPicker | — |
| Area | Select | — |
| Wave | Select | — |
| L3 Scope Items | Custom multi-select w/ search & chips | — |
| Description | Textarea | — |

### API Calls
```
ExploreAPI.workshops.list/create/stats
ExploreAPI.levels.listL3
```

---

## 6. Explore Workshop Detail

**Route:** `explore-workshop-detail` | **Module:** `ExploreWorkshopDetailView` | **File:** explore_workshop_detail.js (1253 lines)

### Header Actions (context-dependent)
| Button | Visible When | Action |
|--------|-------------|--------|
| ▶ Start | draft/scheduled | Start workshop, creates process steps |
| ✓ Complete | in_progress | Complete (with force option for unassessed) |
| ↩ Reopen | completed | Reopen (requires mandatory reason) |
| ➕ Delta | completed | Create delta workshop, navigates to new |
| 🎬 Demo Flow | Always | Starts 3-step guided demo flow |
| ← Back | Always | Navigate to workshop list |

### KPI Strip
`Assessed/Total` · `Fit` · `Partial` · `Gap` · `Decisions` · `Open Items` · `Requirements`

### 8 Tabs
| Tab | Key Interactions |
|-----|------------------|
| **Process Steps** | Grouped by L3, expandable cards, Fit Decision radios (Fit/Partial/Gap), checkboxes (Demo shown, BPMN reviewed), inline child forms |
| **Decisions** | Table (Code, Decision, Category, Decided By, Status, Step) |
| **Open Items** | Table with transition buttons (Start/Resolve/Block/Unblock) |
| **Requirements** | Table with Convert/Move to Backlog/Trace actions |
| **Agenda** | Timeline, + Add form (Time, Title, Duration, Type), Edit/Delete |
| **Attendees** | Avatar list with status pills, + Add form (Name, Role, Org), Delete |
| **Sessions** | Session cards, click switches via localStorage |
| **Documents** | Generate buttons (Minutes/Summary/Traceability), view in modal |

### Inline Forms (Steps Tab)
| Form | Fields |
|------|--------|
| Decision | text, decided_by, category |
| Open Item | title, priority, assignee, due_date, description |
| Requirement | title, priority, type, effort, description |
| Cross-Module Flag | target area, target scope item, description |

### Fit Decision Flow
- Select Fit/Partial/Gap radio on step card (only when workshop `in_progress`)
- On Gap/Partial: prompt to create requirement
- Calls `ExploreAPI.fitDecisions.create`

### Convert Modal (Requirements tab)
| Field | Options |
|-------|---------|
| Target Type | Auto-detect/WRICEF/Config |
| WRICEF Type | Workflow/Report/Interface/Conversion/Enhancement/Form |
| Module Override | Optional |

### Document Generation
| Button | Generates |
|--------|-----------|
| 📝 Meeting Minutes | Markdown document |
| 📊 Workshop Summary | Markdown document |
| 🔗 Traceability Report | Markdown document |

### Workshop Lifecycle Transitions
```
draft → start → in_progress → complete → completed → reopen → in_progress
completed → createDelta → new delta workshop (draft)
```

### API Calls
```
ExploreAPI.workshops.getFull/start/complete/reopen/createDelta
ExploreAPI.fitDecisions.create
ExploreAPI.processSteps.update/addDecision/addOpenItem/addRequirement
ExploreAPI.crossModuleFlags.create
ExploreAPI.requirements.transition/convert
ExploreAPI.openItems.transition
ExploreAPI.agenda.list/create/update/delete
ExploreAPI.attendees.list/create/delete
ExploreAPI.documents.generate/list
ExploreAPI.signoff.performL3
```

---

## 7. Explore Requirements

**Route:** `explore-requirements` | **Module:** `ExploreRequirementsView` | **File:** explore_requirements.js (805 lines)

### Tabs
| Tab | Count Chip |
|-----|------------|
| **Requirements** | Total count |
| **Open Items** | Total count |

### Requirements Tab

#### KPI Strip
Count of requirements by status groups

#### Status Distribution Bar
Visual bar showing requirement status breakdown

#### Filters
| Filter | Options |
|--------|---------|
| Search | Free text |
| Status | draft/under_review/approved/in_backlog/realized/verified/deferred/rejected |
| Priority | P1/P2/P3/P4 |
| Type | functional/technical/integration/data/security/reporting |

#### Table
- Sortable columns
- Expandable rows → traceability detail
- Status-based action buttons per row

#### Status-Based Actions
| Current Status | Available Actions |
|---------------|-------------------|
| draft | Submit, Defer |
| under_review | Approve, Reject |
| approved | Convert, Move to Backlog |
| in_backlog | Realize |
| realized | Verify |
| verified | — |
| deferred | Reactivate |
| rejected | Reactivate |
| Any | Push to ALM, Trace |

#### Modals
| Modal | Fields |
|-------|--------|
| **Create Requirement** | title*, priority, type, effort, description |
| **Convert Modal** | Target: Auto-detect/WRICEF/Config, WRICEF Type, Module Override |
| **Batch Convert** | Checkbox list of convertible requirements |

### Open Items Tab

#### KPI Strip
Count of open items by status

#### Filters
| Filter | Options |
|--------|---------|
| Search | Free text |
| Status | open/in_progress/blocked/resolved/closed |
| Priority | P1/P2/P3/P4 |
| Assignee | Dynamic |
| Overdue | Toggle |

#### Table with Status Transitions
| Current Status | Available Actions |
|---------------|-------------------|
| open | Start Progress, Block |
| in_progress | Resolve, Block |
| blocked | Unblock |
| resolved | Close |

#### Create Open Item Modal
Fields: title*, priority, assignee, due_date, description

### API Calls
```
ExploreAPI.requirements.list/create/transition/convert/batchConvert/stats
ExploreAPI.openItems.list/create/transition/stats
```

---

## 8. Backlog View

**Route:** `backlog` | **Module:** `BacklogView` | **File:** backlog.js (1365 lines)

### 4 Tabs
| Tab | Description |
|-----|-------------|
| **Kanban Board** | 5-column drag board |
| **WRICEF List** | Sortable/filterable table |
| **Config Items** | Config item table + CRUD |
| **Sprints** | Sprint cards with assigned items |

### Kanban Board Tab
| Column | Status |
|--------|--------|
| New | new |
| Design | design |
| Build | build |
| Test | test |
| Deploy | deploy |

- **Draggable cards** with WRICEF type badge (Workflow/Report/Interface/Conversion/Enhancement/Form)
- Priority badge, trace link count
- **KPI Strip:** Items, Story Points, Done, Complete %
- Click card → detail view

### WRICEF List Tab
| Filter | Options |
|--------|---------|
| Type | Workflow/Report/Interface/Conversion/Enhancement/Form (multi-select) |
| Status | new/design/build/test/deploy (multi-select) |
| Priority | P1/P2/P3/P4 (multi-select) |
| Module | FI/CO/MM/SD/PP etc. (multi-select) |
| Search | Free text |

- Sortable table: Type, Code, Title, Module, Status, Priority, SP, Assigned
- View/Delete buttons per row

### Config Items Tab
| Feature | Description |
|---------|-------------|
| Table | Code, Title, Module, Config Key, Status, Priority, Assigned |
| Filters | Status, Priority, Module, Search |
| Actions | + New, Edit, Delete per row |

#### Config Item Form
Fields: Title*, Code, Module, Config Key/IMG Path, Description, Priority, Assigned To (TeamMemberPicker)

#### Config Item Detail View
Classification section, Description, Functional Spec card, Technical Spec card, Back button

### Sprints Tab
| Feature | Description |
|---------|-------------|
| Sprint cards | Name, goal, metrics (items, points, done, capacity, velocity) |
| Items table per sprint | Assigned backlog items |
| Unassigned Backlog section | Items not in any sprint |
| Actions | + New Sprint, Edit/Delete sprint |

#### Sprint Form
Fields: Name*, Goal, Status (planning/active/completed/cancelled), Capacity (SP), Start/End dates, Velocity

### Backlog Item Detail View (4 sub-tabs)
| Sub-Tab | Content |
|---------|---------|
| 📋 Overview | Classification, Estimation, SAP Details, Description, Acceptance Criteria, Technical Notes |
| 📑 Specs | Functional Spec card, Technical Spec card |
| 🧪 Tests | Linked Test Cases table, Linked Defects table |
| 🔗 Traceability | TraceChain component or fallback table |

### Create Item Flow
1. Selector modal: "WRICEF Item" vs "Config Item"
2. Opens respective form

### WRICEF Item Form
| Field | Required | Notes |
|-------|----------|-------|
| Title | ✅ | |
| WRICEF Type | ✅ | Workflow/Report/Interface/Conversion/Enhancement/Form |
| Code | — | |
| Description | — | Textarea |
| Module | — | Dropdown |
| Sub Type | — | |
| Priority | — | P1-P4 |
| Complexity | — | |
| Story Points | — | Number |
| Estimated Hours | — | Number |
| Assigned To | — | TeamMemberPicker |
| Sprint | — | Dropdown |
| Transaction Code | — | |
| Package | — | |
| Acceptance Criteria | — | Textarea |
| Technical Notes | — | Textarea |

### Move Modal
Status dropdown + Sprint dropdown → `PATCH /backlog/{id}/move`

### Stats Modal
WRICEF by Type table, WRICEF by Status table, Config by Status table, Config by Priority table, grand totals

### API Calls
```
GET    /programs/{pid}/backlog/board
GET    /programs/{pid}/backlog
POST   /programs/{pid}/backlog
GET    /backlog/{id}
PUT    /backlog/{id}
DELETE /backlog/{id}
PATCH  /backlog/{id}/move
GET    /programs/{pid}/sprints
POST   /programs/{pid}/sprints
PUT    /sprints/{id}
DELETE /sprints/{id}
GET    /programs/{pid}/config-items
POST   /programs/{pid}/config-items
GET    /config-items/{id}
PUT    /config-items/{id}
DELETE /config-items/{id}
GET    /traceability/backlog_item/{id}
```

---

## 9. Integration Factory

**Route:** `integration` | **Module:** `IntegrationView` | **File:** integration.js (774 lines)

### 4 Tabs
| Tab | Description |
|-----|-------------|
| 📋 Interface Inventory | Interface table with click → detail modal |
| 🌊 Wave Planning | Wave cards with assigned interfaces |
| 🔗 Connectivity | Table with checklist + test buttons |
| 📈 Stats | KPI cards + distribution bars |

### Interface Inventory Tab
Table columns: Code, Name, Direction, Protocol, Module, Systems, Status, Checklist, Priority

### Interface Detail Modal
| Section | Content |
|---------|---------|
| Header info grid | Direction, Protocol, Middleware, Source/Target System, Module, Status, Priority, Wave, Frequency, Volume, Message Type, Complexity, Est/Actual Hours |
| Description & Notes | Text areas |
| ✅ Readiness Checklist | Checkbox items with evidence |
| 🔗 Connectivity Tests | Table (Result, Environment, Response, Tester, Date, Error) |
| 🔀 Switch Plan | Table (Sequence, Action, Description, Responsible, Duration, Status, Execute button) |

### Interface Create/Edit Form
| Field | Required | Notable Options |
|-------|----------|-----------------|
| Name | ✅ | |
| Direction | — | inbound/outbound/bidirectional |
| Protocol | — | rfc/idoc/odata/soap/rest/file/pi_po/cpi/bapi/ale/other |
| Interface Type | — | master_data/transactional/reference/control |
| Status | — | identified→live→decommissioned |
| Assigned To | — | TeamMemberPicker |

### Wave Planning Tab
- Wave cards with assigned interfaces
- Unassigned pool with wave assignment dropdown
- + New Wave, Edit/Delete wave

### Connectivity Tab
- Table with checklist progress
- 🔍 Tests button per interface → shows tests
- + Test button per interface → add test form

### Stats Tab
KPI cards: Total, Live, Go-Live Ready, Unassigned, Est. Hours, Actual Hours
Distribution bars: By Status, By Direction, By Protocol

### Additional Forms
| Form | Fields |
|------|--------|
| **Wave** | Name*, Description, Status, Order, Planned Start/End, Notes |
| **Connectivity Test** | Environment (dev/qas/pre_prod/prod), Result (success/partial/failed/pending), Response Time, Tested By, Error, Notes |
| **Switch Plan** | Sequence #, Action (activate/deactivate/redirect/verify/rollback), Description, Responsible, Duration |
| **Checklist** | Toggle checkbox, + Custom Item (prompt for title) |

### API Calls
```
GET/POST   /programs/{pid}/interfaces
GET/PUT/DELETE /interfaces/{id}
GET/POST   /programs/{pid}/waves
PUT/DELETE /waves/{id} (via /programs/{pid}/waves)
GET/POST   /interfaces/{id}/connectivity-tests
GET/POST   /interfaces/{id}/switch-plans
POST       /switch-plans/{id}/execute
GET/PUT    /interfaces/{id}/checklist
PATCH      /interfaces/{id}/assign-wave
```

---

## 10. Test Planning

**Route:** `test-planning` | **Module:** `TestPlanningView` | **File:** test_planning.js (1055 lines)

### 2 Tabs
| Tab | Description |
|-----|-------------|
| 📋 Test Cases | Test catalog table + CRUD |
| 📦 Test Suites | Suite management + test case generation |

### Test Cases Tab

#### Filters
| Filter | Options |
|--------|---------|
| Layer | unit/sit/uat/e2e/regression/performance/cutover_rehearsal |
| Status | draft/ready/in_review/approved/deprecated |
| Search | Free text |

#### Table
Columns: Code, Title, Layer, Module, Status, Priority, Deps, Regression
Actions: + New Test Case, Delete per row, Click → edit modal

### Test Case Modal (3 sub-tabs)
| Sub-Tab | Content |
|---------|---------|
| 📝 Details | Core fields + structured test steps |
| ⚡ Performance | Results table + trend chart + add result form |
| 🔗 Dependencies | Blocked By/Blocks tables + add dependency form |

#### Details Sub-Tab Fields
| Field | Required | Notes |
|-------|----------|-------|
| Title | ✅ | |
| Test Layer | — | unit/sit/uat/e2e/regression/performance/cutover_rehearsal |
| Module | — | |
| Priority | — | |
| Suite | — | Dropdown of existing suites |
| Description | — | Textarea |
| Preconditions | — | Textarea |
| **Test Steps** | — | Structured list: step_no, action, expected_result, test_data |
| Expected Result | — | Textarea |
| Test Data Set | — | |
| Assigned To | — | TeamMemberPicker |
| Regression Set | — | Checkbox |

#### Test Steps (inline CRUD)
- Add step: + Add Step button → inline form (action, expected_result, test_data)
- Edit step: Edit button → inline edit
- Delete step: Delete button
- Auto-numbering by step_no

#### Performance Sub-Tab
| Feature | Description |
|---------|-------------|
| Results table | Date, Response ms, Target ms, Pass/Fail, Throughput, Users, Env |
| Performance trend chart | Chart.js line chart over time |
| Add Result form | Response Time*, Target*, Throughput, Concurrent Users, Environment, Notes |

#### Dependencies Sub-Tab
| Feature | Description |
|---------|-------------|
| Blocked By table | List of blocking test cases |
| Blocks table | Test cases this blocks |
| Add Dependency form | Other Case ID*, Direction (blocked_by/blocks), Type (blocks/related/data_feeds) |

### Test Suites Tab

#### Filters
| Filter | Options |
|--------|---------|
| Type | SIT/UAT/Regression/E2E/Performance/Custom |
| Status | draft/active/locked/archived |
| Search | Free text |

#### Table
Columns: Name, Type, Status, Module, Owner, Tags
Actions: + New Suite, Edit/Delete per row

#### Suite Create/Edit Form
Fields: Name*, Suite Type, Status, Module, Owner, Description, Tags

#### Suite Detail Modal
- Suite info display
- Test Cases table (linked cases)
- **Generate from WRICEF**: Checkbox list of backlog items, Select All, generates test cases
- **Generate from Process**: Checkbox list of L3 items, Test Level select, UAT Category, generates test cases

### API Calls
```
GET/POST   /programs/{pid}/testing/catalog
GET/PUT/DELETE /testing/catalog/{id}
POST/PUT/DELETE /testing/catalog/{id}/steps
PUT/DELETE /testing/steps/{id}
GET/POST   /testing/catalog/{id}/perf-results
POST/DELETE /testing/catalog/{id}/dependencies
GET/POST   /programs/{pid}/testing/suites
GET/PUT/DELETE /testing/suites/{id}
POST       /testing/suites/{id}/generate-from-wricef
POST       /testing/suites/{id}/generate-from-process
```

---

## 11. Test Execution

**Route:** `test-execution` | **Module:** `TestExecutionView` | **File:** test_execution.js (1018 lines)

### 2 Tabs
| Tab | Description |
|-----|-------------|
| 📅 Plans & Cycles | Test plan management with nested cycles |
| 🔗 Traceability | Requirements × Test Cases coverage matrix |

### Plans & Cycles Tab

#### Test Plans
- Plan cards with cycle tables nested inside
- **+ New Test Plan** button
- Delete plan

#### Test Plan Form
Fields: Name*, Description, Start/End Date, Entry/Exit Criteria

#### Test Cycles (nested in plan)
- **+ Cycle** button per plan
- Delete cycle
- Click → opens cycle executions modal

#### Test Cycle Form
Fields: Name*, Test Layer (sit/uat/unit/regression/performance/cutover_rehearsal), Start/End Date, Description

### Cycle Executions Modal
| Feature | Description |
|---------|-------------|
| Execution table | Test Case, Result, Tester, Duration, Notes |
| + Add Execution | Opens execution form |
| Edit/Delete | Per execution |
| ▶ Test Runs | Opens test runs view |
| Validate Entry | Validates entry criteria (with Force override) |
| Validate Exit | Validates exit criteria (with Force override) |

#### Entry/Exit Criteria
- Criteria checklist display (✅/❌ per criterion)
- Force override button when criteria not met

#### Execution Form
Fields: Test Case ID*, Result (not_run/pass/fail/blocked/deferred), Executed By (TeamMemberPicker), Duration, Notes

### UAT Sign-off Section
| Feature | Description |
|---------|-------------|
| Sign-off table | Process Area, Signed By, Role, Status (pending/approved/rejected), Date |
| Approve/Reject buttons | Per sign-off |
| + Initiate Sign-off | Opens sign-off form |
| Delete sign-off | Per sign-off |

#### Sign-off Form
Fields: Process Area*, Signed Off By*, Role (BPO/PM), Comments

### Test Runs View (modal)
| Feature | Description |
|---------|-------------|
| Runs table | Run #, Test Case, Type, Status, Result, Tester, Environment, Actions |
| + New Run | Opens new run modal |
| ▶ Execute | Opens step-by-step execution UI |
| Delete run | Per run |

#### New Run Form
Fields: Test Case ID*, Run Type (manual/automated/exploratory), Tester, Environment, Notes

#### Run Execution UI
| Feature | Description |
|---------|-------------|
| Header | Run info (type, tester, environment, started/finished) |
| Status actions | ▶ Start Run / ✅ Complete (Pass) / ❌ Complete (Fail) / ⛔ Abort |
| Step Results table | #, Action, Expected, Result (dropdown), Actual Result, Notes |
| + Add Step Row | Adds new step row |
| 💾 Save Step Results | Saves all step results |

Step Result options: not_run/pass/fail/blocked/skipped

### Traceability Tab
| Feature | Description |
|---------|-------------|
| KPI Strip | Requirements, With Tests, Coverage %, Test Cases, Defects |
| Matrix table | Requirement → Test Cases count → Defects count → Covered/Uncovered |
| Trace button | Opens TraceChain for requirement |

### Go/No-Go Scorecard
| Feature | Description |
|---------|-------------|
| Overall verdict | ✅ GO or 🛑 NO-GO with color |
| Scorecard table | Criterion, Target, Actual, Status (green/yellow/red) |

### Daily Snapshots
| Feature | Description |
|---------|-------------|
| Snapshot table | Date, Total, Passed, Failed, Blocked, Pass Rate, Open Defects |
| Trend chart | Pass Rate % + Open Defects dual-axis line chart |
| Capture Snapshot button | Creates new snapshot |

### API Calls
```
GET/POST   /programs/{pid}/testing/plans
GET/DELETE /testing/plans/{id}
GET/POST   /testing/plans/{id}/cycles
GET/DELETE /testing/cycles/{id}
GET/POST   /testing/cycles/{id}/executions
PUT/DELETE /testing/executions/{id}
POST       /testing/cycles/{id}/validate-entry
POST       /testing/cycles/{id}/validate-exit
GET/POST   /testing/uat-signoffs
PUT/DELETE /testing/uat-signoffs/{id}
GET/POST   /testing/cycles/{id}/runs
GET/PUT/DELETE /testing/runs/{id}
GET/POST   /testing/runs/{id}/step-results
PUT        /testing/step-results/{id}
GET        /programs/{pid}/testing/traceability-matrix
GET        /programs/{pid}/testing/dashboard/go-no-go
GET/POST   /programs/{pid}/testing/snapshots
```

---

## 12. Defect Management

**Route:** `defect-management` | **Module:** `DefectManagementView` | **File:** defect_management.js (575 lines)

### Defect List

#### Filters
| Filter | Options |
|--------|---------|
| Severity | P1/P2/P3/P4 |
| Status | new/open/in_progress/fixed/retest/closed/rejected/reopened |
| Search | Free text |

#### Table
Columns: Code, Title, Severity, Status, SLA, Module, Aging, Reopen count
Actions: + Report Defect, Delete per row, Click → edit modal

### Defect Modal (5 sub-tabs)
| Sub-Tab | Content |
|---------|---------|
| 📝 Details | Core defect fields |
| ⏱ SLA | SLA status display |
| 💬 Comments | Comment list + add/delete |
| 📜 History | Change history table |
| 🔗 Links | Outgoing/incoming defect links + add/delete |

#### Details Sub-Tab
| Field | Options/Notes |
|-------|---------------|
| Title* | |
| Severity | P1/P2/P3/P4 |
| Status | 8 states: new/open/in_progress/fixed/retest/closed/rejected/reopened |
| Module | |
| Description | Textarea |
| Steps to Reproduce | Textarea |
| Reported By | |
| Assigned To | |
| Environment | |
| Linked Test Case ID | |
| Linked WRICEF Item ID | |
| Linked Config Item ID | |
| Resolution | Textarea |
| Root Cause | Textarea |
| Transport Request | |

#### SLA Sub-Tab (read-only)
SLA Status (On Track/Warning/Breached), Severity, Priority, Due Date, Response/Resolution Target hours, Time Remaining

#### Comments Sub-Tab
- Comment list with author/date
- Add Comment form: Author, Comment
- Delete comment button

#### History Sub-Tab
Change history table: Date, Changed By, Field, Old Value, New Value

#### Links Sub-Tab
- Outgoing links table (Type, Target Defect)
- Incoming links table (Type, Source Defect)
- Add Link form: Target Defect ID*, Link Type (related/duplicate/blocks), Notes
- Delete link button

### 🤖 AI Triage Button
| Feature | Description |
|---------|-------------|
| Location | Modal footer |
| Action | Calls `POST /ai/triage/defect/{id}` |
| Result display | Suggested Severity, Module, Reasoning, Assign to, Root Cause Hint |
| Potential Duplicates | List with similarity % |
| Similar Defects | List with similarity % |
| ✅ Apply Suggestions | Auto-fills severity + module in form |

### API Calls
```
GET/POST   /programs/{pid}/testing/defects
GET/PUT/DELETE /testing/defects/{id}
GET        /testing/defects/{id}/sla
GET/POST   /testing/defects/{id}/comments
DELETE     /testing/defects/{id}/comments/{cid}
GET        /testing/defects/{id}/history
GET/POST   /testing/defects/{id}/links
DELETE     /testing/defects/{id}/links/{lid}
POST       /ai/triage/defect/{id}
```

---

## 13. Cutover Hub

**Route:** `cutover` | **Module:** `CutoverView` | **File:** cutover.js (1118 lines)

### 5 Tabs
| Tab | Description |
|-----|-------------|
| 📋 Plans | Cutover plan cards + detail |
| 📖 Runbook | Scope items + tasks |
| 🔄 Rehearsals | Rehearsal tracking |
| ✅ Go / No-Go | Decision pack |
| 🏥 Hypercare | Incidents + SLA |

### Plans Tab
| Feature | Description |
|---------|-------------|
| Plan cards | Selectable, show code, status, manager, env, dates, counts |
| Active plan detail | Header with transitions, edit, delete |
| + New Plan | Opens create form |

#### Plan Status Transitions
```
draft → approved → rehearsal/ready → executing → completed/rolled_back
rolled_back → draft
```

#### Plan Create/Edit Form
Fields: Name*, Description, Cutover Manager (TeamMemberPicker), Environment (PRD/QAS/Sandbox), Planned Start/End, Rollback Deadline, Rollback Decision By, Hypercare Manager, Hypercare Duration Weeks

### Runbook Tab (requires active plan)
| Feature | Description |
|---------|-------------|
| Progress bar | Total task completion % |
| Scope Item cards | Category icon, name, status, task count, owner |
| Tasks table per scope item | Seq, Code, Title, Status, Responsible, Planned/Actual duration |
| + Scope Item | Opens create form |
| + Task | Opens create form per scope item |

#### Scope Item Form
Fields: Name*, Category (data_load/interface/authorization/job_scheduling/reconciliation/custom), Owner (TeamMemberPicker), Description, Order

#### Task Form
Fields: Title*, Description, Sequence, Planned Duration (min), Responsible (TeamMemberPicker), Accountable, Rollback Action, Notes

#### Task Status Transitions
```
not_started → in_progress/skipped
in_progress → completed/failed/rolled_back
completed → rolled_back
failed → in_progress/rolled_back/skipped
skipped → not_started
rolled_back → not_started
```

### Rehearsals Tab (requires active plan)
| Feature | Description |
|---------|-------------|
| Rehearsal cards | Number, name, env, planned/actual duration, variance %, task counts |
| + New Rehearsal | Opens create form |
| Status transitions | planned → in_progress → completed/cancelled |
| 📊 Metrics button | Computes metrics (completed only) |
| Delete | Per rehearsal |

#### Rehearsal Form
Fields: Name*, Description, Environment (QAS/PRD/Sandbox), Planned Duration (min)

### Go/No-Go Tab (requires active plan)
| Feature | Description |
|---------|-------------|
| KPI cards | Overall recommendation, Go/No-Go/Pending/Waived counts |
| Criteria table | Source, Criterion, Verdict, Evidence, Evaluated, Actions |
| Verdict dropdown | inline: pending/go/no_go/waived |
| 🌱 Seed Defaults | Seeds standard 7-item checklist |
| + New Item | Opens create form |

#### Go/No-Go Create Form
Fields: Criterion*, Description, Source Domain (8 options), Evidence, Evaluated By

### Hypercare Tab (requires active plan)
| Feature | Description |
|---------|-------------|
| KPI cards | Total, Open, Resolved, SLA Breach, SLA Compliance % |
| Severity breakdown | P1-P4 distribution |
| SLA Targets | Collapsible table (Severity, Response/Resolution target, Escalation) |
| Incidents table | Code, Title, Severity, Category, Status, Assigned, SLA, Actions |
| + New Incident | Opens create form |
| 🌱 Seed SLA | Seeds default SLA targets |

#### Incident Status Transitions
```
open → investigating/resolved/closed
investigating → resolved/closed
resolved → closed/open
closed → open
```

#### Incident Create Form
Fields: Title*, Description, Severity (P1-P4), Category (functional/technical/data/authorization/performance/other), Reported By, Assigned To, Notes

### API Calls
```
GET/POST   /cutover/plans
GET/PUT/DELETE /cutover/plans/{id}
POST       /cutover/plans/{id}/transition
GET/POST   /cutover/plans/{id}/scope-items
DELETE     /cutover/scope-items/{id}
GET/POST   /cutover/scope-items/{id}/tasks
POST       /cutover/tasks/{id}/transition
DELETE     /cutover/tasks/{id}
GET/POST   /cutover/plans/{id}/rehearsals
POST       /cutover/rehearsals/{id}/transition
POST       /cutover/rehearsals/{id}/compute-metrics
DELETE     /cutover/rehearsals/{id}
GET/POST   /cutover/plans/{id}/go-no-go
GET        /cutover/plans/{id}/go-no-go/summary
POST       /cutover/plans/{id}/go-no-go/seed
PUT/DELETE /cutover/go-no-go/{id}
GET/POST   /cutover/plans/{id}/incidents
POST       /cutover/incidents/{id}/transition
DELETE     /cutover/incidents/{id}
GET/POST   /cutover/plans/{id}/sla-targets
POST       /cutover/plans/{id}/sla-targets/seed
DELETE     /cutover/sla-targets/{id}
GET        /cutover/plans/{id}/hypercare/metrics
```

---

## 14. Data Factory

**Route:** `data-factory` | **Module:** `DataFactoryView` | **File:** data_factory.js (1042 lines)

### 5 Tabs
| Tab | Description |
|-----|-------------|
| 📦 Data Objects | Master list + CRUD + quality badges |
| 🌊 Migration Waves | Wave cards with progress |
| 🧹 Cleansing | Rules per object + run simulation |
| 🔄 Load Cycles | ETL executions + reconciliation |
| 📊 Dashboard | Quality score + environment comparison charts |

### Data Objects Tab
| Feature | Description |
|---------|-------------|
| KPI Strip | Objects count, Avg Quality %, Total Records, Ready/Migrated ratio |
| Table | Name, Source, Target Table, Records, Quality badge, Status, Owner |
| + New Data Object | Opens create form |
| Row click | Opens detail modal |
| Delete | Per row |

#### Object Status Flow
`draft → profiled → cleansed → ready → migrated → archived`

#### Object Create Form
Fields: Name*, Source System*, Target Table, Record Count, Owner (TeamMemberPicker), Description

#### Object Detail Modal
- Metadata display
- Update Status buttons (inline, 6 states)

### Migration Waves Tab
| Feature | Description |
|---------|-------------|
| Wave cards | Status-colored left border, planned/actual dates |
| + New Wave | Opens create form |
| Card click | Opens detail modal |
| Delete | Per card |

#### Wave Create Form
Fields: Wave Number*, Name*, Description, Planned Start/End

#### Wave Detail Modal
- Metadata display
- Update Status buttons (planned/in_progress/completed/cancelled)

### Cleansing Tab
| Feature | Description |
|---------|-------------|
| Object selector dropdown | Switches active object |
| Summary badges | Passed/Failed/Pending counts |
| Rules table | Rule Type (6 icons), Expression, Description, Pass/Fail counts, Status, Last Run |
| ▶ Run | Executes rule |
| + New Rule | Opens create form |
| Delete | Per rule |

#### Rule Types
`not_null (🔒)` · `unique (🔑)` · `range (📏)` · `regex (🔤)` · `lookup (🔍)` · `custom (⚙️)`

#### Cleansing Rule Form
Fields: Rule Type*, Expression*, Description

### Load Cycles Tab
| Feature | Description |
|---------|-------------|
| Object selector dropdown | Switches active object |
| Cycles table | ID, Environment, Load Type, Records Loaded/Failed, Status, Started/Completed |
| ▶ Start | Starts pending load |
| ✓ Complete | Opens completion form (Records Loaded, Failed, Error Log) |
| Recon button | Opens reconciliation modal |
| + New Load Cycle | Opens create form |

#### Load Cycle Form
Fields: Environment (DEV/QAS/PRE/PRD), Load Type (initial/delta/full_reload/mock), Wave (optional)

#### Reconciliation Modal
- Source/Target/Match/Variance/Variance %/Status table
- Calc button per row
- + Add Reconciliation form: Source Count, Target Count, Match Count → auto-calc

### Dashboard Tab
| Feature | Description |
|---------|-------------|
| Quality overview card | Avg Quality % + bar chart per object |
| Status breakdown card | Counts per status |
| Environment comparison | Table + bar chart (Records Loaded vs Failed per env) |

### API Calls
```
GET/POST   /data-factory/objects?program_id={pid}
GET/PUT/DELETE /data-factory/objects/{id}
GET/POST   /data-factory/waves?program_id={pid}
GET/PUT/DELETE /data-factory/waves/{id}
GET/POST   /data-factory/objects/{id}/tasks
POST       /data-factory/tasks/{id}/run
DELETE     /data-factory/tasks/{id}
GET/POST   /data-factory/objects/{id}/loads
POST       /data-factory/loads/{id}/start
POST       /data-factory/loads/{id}/complete
GET/POST   /data-factory/loads/{id}/recons
POST       /data-factory/recons/{id}/calculate
GET        /data-factory/quality-score?program_id={pid}
GET        /data-factory/cycle-comparison?program_id={pid}
```

---

## 15. RAID Log

**Route:** `raid` | **Module:** `RaidView` | **File:** raid.js (800 lines)

### Dashboard Section
| Feature | Description |
|---------|-------------|
| KPI Strip | Open Risks (+ critical), Open Actions (+ overdue), Open Issues (+ critical), Pending Decisions (+ total) |
| Risk Heatmap | 5×5 matrix (Probability × Impact), clickable cells show risk list |

### 4 Tabs
| Tab | Description |
|-----|-------------|
| Risks | Risk table with filters |
| Actions | Action table with filters |
| Issues | Issue table with filters |
| Decisions | Decision table with filters |

### + New Menu (dropdown)
- Risk · Action · Issue · Decision → opens respective create form

### Filters (per tab)
| Tab | Filters |
|-----|---------|
| Risks | Status (5), Priority (4), RAG (4) |
| Actions | Status (4), Priority (4), Type (4) |
| Issues | Status (4), Severity (4) |
| Decisions | Status (4) |

All tabs have free-text search.

### Table Columns per Tab
| Tab | Columns |
|-----|---------|
| Risks | Code, Title, Status, Priority, Score, RAG, Owner |
| Actions | Code, Title, Status, Priority, Type, Due, Owner |
| Issues | Code, Title, Status, Severity, Priority, Owner |
| Decisions | Code, Title, Status, Priority, Owner, Reversible |

### Row Actions
- Click row → Detail modal (all fields displayed)
- Edit button → Edit form
- Delete button → Confirm delete

### Detail Modal
All entity fields displayed in table format, Edit button, Close button

### Create/Edit Forms
| Type | Shared Fields | Specific Fields |
|------|--------------|-----------------|
| **All** | Title*, Description, Owner (TeamMemberPicker), Priority | — |
| **Risk** | — | Probability (1-5), Impact (1-5), Category (7 options), Response (5 options), Mitigation Plan, Contingency Plan |
| **Action** | — | Due Date, Type (preventive/corrective/detective/improvement/follow_up) |
| **Issue** | — | Severity (4 options), Escalation Path, Root Cause |
| **Decision** | — | Decision Owner (TeamMemberPicker), Alternatives, Rationale, Reversible (yes/no) |

### Heatmap Cell Modal
Shows list of risks in selected probability × impact cell

### API Calls
```
GET        /programs/{pid}/raid/stats
GET        /programs/{pid}/raid/heatmap
GET/POST   /programs/{pid}/risks
GET/POST   /programs/{pid}/actions
GET/POST   /programs/{pid}/issues
GET/POST   /programs/{pid}/decisions
GET/PUT/DELETE /risks/{id}
GET/PUT/DELETE /actions/{id}
GET/PUT/DELETE /issues/{id}
GET/PUT/DELETE /decisions/{id}
```

---

## 16. Reports View

**Route:** `reports` | **Module:** `ReportsView` | **File:** reports.js (180 lines)

### Features
| Feature | Description |
|---------|-------------|
| Overall Status Banner | RAG badge, current phase, days to go-live |
| Area Health Cards | Explore, Backlog, Testing, RAID, Integration — each with RAG + metrics |
| Phase Timeline table | Phase name, status, completion %, planned start/end |
| Export buttons | 📥 Excel, 📄 Print Report |

### Area Cards Metrics
| Area | Metrics |
|------|---------|
| Explore | Workshops completed/total, Requirements approved %, Overdue OIs |
| Backlog | Items done/total, completion % |
| Testing | Pass rate, test cases, open defects, S1 open |
| RAID | Open risks, red risks, overdue actions |
| Integration | Interfaces live/total, completion % |

### Export Actions
| Button | Action |
|--------|--------|
| 📥 Excel | Opens `/api/v1/reports/export/xlsx/{pid}` in new tab |
| 📄 Print Report | Opens `/api/v1/reports/export/pdf/{pid}` in new tab |

### API Calls
```
GET /reports/program-health/{pid}
GET /reports/export/xlsx/{pid}  (browser download)
GET /reports/export/pdf/{pid}   (browser download)
```

---

## 17. Executive Cockpit

**Route:** `executive-cockpit` | **Module:** `ExecutiveCockpitView` | **File:** executive_cockpit.js (~300 lines)

### Sections
| Section | Description |
|---------|-------------|
| Top KPI Strip | Overall Status, Go-Live countdown, Workshops, Test Pass Rate, Open Defects |
| Area RAG Grid | 5 area cards: Explore, Backlog/Build, Testing, RAID, Integration |
| Explore Deep Dive | Gap Ratio, OI Aging, Req Coverage, Overall Explore RAG |
| Charts Row | Fit/Gap Distribution (doughnut), Test Results (doughnut), Defect Severity (bar) |
| Phase Timeline | Phase progress bars with dates |
| Quick Actions | 5 navigation buttons: Explore Dashboard, Test Execution, Defect Management, RAID, Reports |

### Charts (3)
| Chart | Type |
|-------|------|
| Fit/Gap Distribution | Doughnut (Fit/Gap/Partial/Pending) |
| Test Results | Doughnut (Pass/Fail) |
| Defect Severity | Bar (S1 Critical/Other Open/Closed) |

### API Calls
```
GET /reports/program-health/{pid}
GET /reports/program/{pid}/health
```

---

## 18. AI Query Assistant

**Route:** `ai-query` | **Module:** `AIQueryView` | **File:** ai_query.js (~250 lines)

### Layout
- Query panel (left) + History sidebar (right)

### Input Area
| Element | Description |
|---------|-------------|
| Textarea | Multi-line NL query input with placeholder examples |
| Auto-execute toggle | Checkbox, default on |
| 🔍 Query button | Submits query |

### Hint Chips (5)
Pre-built queries: "How many open defects?", "List all P1 defects in FI", "Requirements by fit/gap status", "WRICEF items by module", "Test execution pass rate"

### Result Display
| Section | Description |
|---------|-------------|
| SAP Terms Detected | Glossary matches as chips |
| Explanation | AI-generated explanation |
| Generated SQL | Code block with confidence badge (high/medium/low) |
| ▶ Execute button | Manual SQL execution (when auto-execute off) |
| Results table | Dynamic columns and rows |

### History Sidebar
- Last 20 queries
- Click to replay (fills input)
- Shows timestamp and row count

### API Calls
```
POST /ai/query/natural-language
POST /ai/query/execute-sql
```

---

## 19. AI Admin Dashboard

**Route:** `ai-admin` | **Module:** `AIAdminView` | **File:** ai_admin.js (~350 lines)

### KPI Cards (6)
Total API Calls · Total Tokens · Total Cost (USD) · Avg Latency (ms) · Error Rate · Pending Suggestions

### Charts (2)
| Chart | Type |
|-------|------|
| Cost by Provider | Doughnut |
| Suggestions by Status | Doughnut |

### 5 Tabs
| Tab | Content |
|-----|---------|
| 💡 Suggestions | Table (ID, Type, Entity, Title, Confidence, Status, Created, Actions), Approve/Reject per pending |
| 📊 Usage Log | KPIs (30d), By Model table, By Purpose table |
| 📋 Audit Log | Table (Time, Action, Provider, Model, Tokens, Cost, Latency, Status) |
| 🔍 Embeddings | KPIs (Chunks, With/Without Vectors), By Entity Type table, Semantic Search test |
| 📝 Prompts | Table (Name, Version, Description, A/B Test, System Preview) |

### Semantic Search Test (Embeddings tab)
- Input field + Search button
- Results table: Score %, Entity, Module, Text preview

### API Calls
```
GET    /ai/admin/dashboard
GET    /ai/suggestions?per_page=50
PATCH  /ai/suggestions/{id}/approve
PATCH  /ai/suggestions/{id}/reject
GET    /ai/usage?days=30
GET    /ai/audit-log?per_page=50
GET    /ai/embeddings/stats
POST   /ai/embeddings/search
GET    /ai/prompts
```

---

## Components

### RoleNav (role-nav.js)
| Feature | Description |
|---------|-------------|
| User context | `setUser({id, name, default_role})` in sessionStorage |
| Permission check | `can(action)` async, `canSync(action)` sync |
| Guarded buttons | `guardedButton(label, action, opts)` — disabled when lacking permission |
| DOM enforcement | `applyToDOM()` — disables/hides elements with `data-perm` attribute |
| Cache | Per `pid:uid`, cleared on `resetCache()` or `setUser()` |
| API | `GET /explore/user-permissions?project_id={pid}&user_id={uid}` |

### TeamMemberPicker (team-member-picker.js)
| Feature | Description |
|---------|-------------|
| Fetch members | `fetchMembers(programId)` — cached per program |
| Render select | `renderSelect(fieldId, members, currentValue, opts)` |
| Cache | `invalidateCache(programId)` |
| API | `GET /api/programs/{pid}/team-members` |

### ExpUI / Explore Shared (explore-shared.js)
Pure render functions returning HTML strings:
| Component | Description |
|-----------|-------------|
| `pill(opts)` | Generic pill/tag with 17 variants |
| `fitBadge(status)` | Fit/gap/partial/pending badge |
| `fitBarMini(counts)` | Mini stacked bar |
| `kpiBlock(opts)` | KPI card with trend |
| `metricBar(opts)` | Distribution bar with segments |
| `filterGroup(opts)` | Filter chip group |
| `filterBar(opts)` | Full filter bar with dropdown menus |
| `actionButton(opts)` | Styled action button (6 variants) |
| `countChip(count, opts)` | Inline count indicator |
| `levelBadge(level)` | L1/L2/L3/L4 badge |
| `priorityPill(priority)` | Priority pill |
| `workshopStatusPill(status)` | Workshop status pill |
| `wavePill(wave)` | Wave number pill |
| `areaPill(area)` | SAP area color pill |
| `statusFlowIndicator(status)` | 6-step requirement lifecycle dots |
| `oiStatusPill(status)` | Open item status pill |

### DemoFlow (demo-flow.js)
3-step guided demo flow:
| Step | Label | View |
|------|-------|------|
| 1 | Workshop Review | explore-workshop-detail |
| 2 | Requirements | explore-requirements |
| 3 | Convert & Trace | explore-requirements |

| Function | Description |
|----------|-------------|
| `start(workshopId)` | Enters step 1 |
| `nextStep()` | Advances |
| `prevStep()` | Goes back |
| `goToStep(idx)` | Jump to step |
| `finish()` | Ends flow |
| `breadcrumbHTML()` | Returns breadcrumb bar HTML |
| `startButton(workshopId)` | Returns start button HTML |
| `isActive()` | Check if flow running |

State stored in `sessionStorage` key `sap_demo_flow`.

### NotificationPanel (notification.js)
| Feature | Description |
|---------|-------------|
| Bell icon badge | Unread count |
| Dropdown panel | List of 20 notifications |
| Mark all read | Clears all |
| Click notification | Marks read + navigates to source entity (RAID items) |
| Polling | Every 30 seconds |
| API | `GET /notifications/unread-count`, `GET /notifications?limit=20`, `POST /notifications/mark-all-read`, `PATCH /notifications/{id}/read` |

### SuggestionBadge (suggestion-badge.js)
| Feature | Description |
|---------|-------------|
| 💡 icon badge | Pending suggestion count |
| Dropdown panel | Top 10 pending suggestions |
| Approve/Reject | Per suggestion |
| Polling | Every 60 seconds |
| Navigate | "View All" → ai-admin |
| API | `GET /ai/suggestions/pending-count`, `GET /ai/suggestions?status=pending&per_page=10`, `PATCH /ai/suggestions/{id}/approve`, `PATCH /ai/suggestions/{id}/reject` |

### TraceChain (trace-chain.js)
| Feature | Description |
|---------|-------------|
| `show(entityType, entityId)` | Modal with full trace diagram |
| `renderInTab(entityType, entityId, container)` | Inline trace in tab |
| Supports 16 entity types | Process L1-L4, Step, Workshop, Scenario, Requirement, Backlog Item, Config Item, Func/Tech Spec, Test Case, Defect, Open Item, Decision, Interface |
| Visual elements | Entity header, Depth bar (chain depth/6), Flow diagram (upstream → current → downstream), Lateral links, Gaps & warnings |
| Navigation | Click node → navigates to relevant view |
| API | `GET /traceability/{entity_type}/{entity_id}` |

### TraceView (trace-view.js)
| Feature | Description |
|---------|-------------|
| `showForRequirement(reqId)` | Modal with requirement-centric trace |
| `renderInline(reqId)` | Returns HTML string |
| Visual | Coverage badges → layered chain: Requirement → Backlog/Config → Test → Defect + Open Items |
| API | `GET /trace/requirement/{id}` |

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Views** | 20 |
| **Tabs across all views** | ~40 |
| **Unique modal types** | ~50 |
| **Form types** | ~35 |
| **Filter configurations** | ~25 |
| **API endpoints referenced** | ~120+ |
| **Chart instances** | ~15 |
| **Status transition systems** | 8 (Workshop, Requirement, Open Item, Defect, Backlog/Kanban, Cutover Plan, Task, Incident) |
| **Shared components** | 8 |
| **Drag & drop interactions** | 1 (Kanban board) |
| **Polling systems** | 2 (Notifications 30s, Suggestions 60s) |
| **Export actions** | 2 (Excel, PDF) |
| **AI-powered features** | 3 (NL Query, Defect Triage, Suggestions) |
