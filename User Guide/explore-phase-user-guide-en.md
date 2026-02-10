# ProjektCoPilot — Explore Phase Manager
# User Guide v1.0

---

## About This Guide

This guide is intended for all project team members who will use the **Explore Phase Manager** module of the ProjektCoPilot platform. It covers the end-to-end management of the SAP Activate Explore phase — from building the process hierarchy and running workshops to managing requirements and delivering steering committee reports.

**Target audience:**
- Program/Project Managers
- SAP Consultants (Facilitators)
- Module Leads
- Business Process Owners (BPOs)
- Technical Leads and Developers
- Business Analysts and Testers

**Prerequisites:**
- ProjektCoPilot account with project access
- Browser: Chrome, Edge, or Firefox (latest version)
- Assigned project role (see Section 2)

---

## Table of Contents

1. System Overview
2. Roles and Permissions
3. Project Setup
4. Screen 1: Process Hierarchy Manager
5. Screen 2: Workshop Hub
6. Screen 3: Workshop Detail
7. Screen 4: Requirement & Open Item Hub
8. Screen 5: Explore Dashboard
9. Scope Change Management
10. Cloud ALM Integration
11. Reporting and Export
12. Frequently Asked Questions
13. Shortcuts and Tips

---

## 1. System Overview

### 1.1 What Is the Explore Phase?

In the SAP Activate methodology, the Explore phase is the stage where the customer's existing business processes are compared against SAP S/4HANA standards. For each process, one of three decisions is made:

- **Fit** — the SAP standard is sufficient; no changes are needed
- **Partial Fit** — can be resolved with minor configuration or a workaround
- **Gap** — the SAP standard does not cover the requirement; development is needed

These decisions are made during **Fit-to-Standard workshops**. The decisions taken, requirements created, and action items raised in each workshop determine the workload for the project's Realize phase.

### 1.2 Five Main Screens

The Explore Phase Manager consists of five screens, each serving a different purpose:

| Screen | Purpose | Primary Users | Frequency |
|--------|---------|---------------|-----------|
| **Process Hierarchy** | Displays the process tree; provides the big picture | PM, BPO, Module Lead | Weekly review |
| **Workshop Hub** | Plans and tracks 300+ workshops | PM, Facilitator | Daily |
| **Workshop Detail** | Executes a single workshop | Facilitator | On workshop day |
| **REQ & OI Hub** | Manages requirements and action items | All team members | Daily |
| **Explore Dashboard** | Trend analysis and reporting | PM, Steering Committee | Weekly |

### 1.3 Navigating Between Screens

The screens are interconnected. You can navigate from any screen to another:

- Click a scope item in Process Hierarchy → opens its workshop
- Click a row in Workshop Hub → opens Workshop Detail
- Click a requirement code in Workshop Detail → goes to that requirement in REQ Hub
- Click a workshop code in REQ Hub → returns to Workshop Detail
- Click an area on a Dashboard chart → navigates to the relevant screen with filters applied

All five screens are accessible under "Explore" in the left sidebar.

---

## 2. Roles and Permissions

### 2.1 Role Assignment

Each project team member is assigned one or more roles. Your role determines which actions you can perform. Roles are assigned by the Project Manager.

To view your role: click the profile icon in the top-right corner → select "My Project Roles."

### 2.2 Role Definitions

**Project Manager (PM)**
Can perform all actions. Workshop planning, requirement approval, scope changes, ALM synchronization — all are authorized. Typically 1–2 people per project hold this role.

**Module Lead**
Manages workshops and requirements within their own process area (FI, SD, MM, etc.). An SD Module Lead can only approve or reject requirements in the SD area. They can view other areas' requirements but cannot modify them.

**Facilitator**
Starts, runs, and completes assigned workshops. During a workshop, the facilitator makes fit decisions and creates decisions, open items, and requirements. Cannot modify workshops they are not assigned to.

**Business Process Owner (BPO)**
The customer-side process owner. Has authority to approve requirements (together with the Module Lead), make scope decisions, and participate in fit decisions. Typically department managers in the customer organization.

**Tech Lead**
Has authority to push requirements to Cloud ALM, mark them as realized, and provide effort estimates. Typically the development team lead.

**Business Tester**
Has authority to verify realized requirements. Confirms that requirements are accepted during the UAT process.

**Viewer**
Can see all screens but cannot make any changes. Typically granted to senior management or external stakeholders.

### 2.3 Permission Matrix — Quick Reference

| Action | PM | Module Lead | Facilitator | BPO | Tech Lead | Tester | Viewer |
|--------|:--:|:----------:|:----------:|:---:|:---------:|:------:|:------:|
| Plan workshop | ✓ | Own area | — | — | — | — | — |
| Start workshop | ✓ | ✓ | Own WS | — | — | — | — |
| Make fit decision | ✓ | ✓ | Own WS | ✓ | — | — | — |
| Create REQ | ✓ | ✓ | ✓ | ✓ | — | — | — |
| Approve REQ | ✓ | Own area | — | ✓ | — | — | — |
| Reject REQ | ✓ | Own area | — | — | — | — | — |
| Push to ALM | ✓ | — | — | — | ✓ | — | — |
| Mark realized | ✓ | — | — | — | ✓ | — | — |
| Verify | ✓ | ✓ | — | ✓ | — | ✓ | — |
| Change scope | ✓ | — | — | ✓ | — | — | — |
| Create OI | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| Close OI | ✓ | ✓ | ✓ | — | ✓ | — | — |
| Attach file | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| View dashboard | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**"Own area"** = the process area to which they are assigned (FI, SD, MM, etc.)
**"Own WS"** = workshops to which they are assigned as facilitator

---

## 3. Project Setup

### 3.1 Loading the Process Tree

The first step after creating a project is to load the process tree.

**Step 1:** Go to "Explore" → "Process Hierarchy" in the left sidebar.

**Step 2:** Click "Import Scope Items" in the top right.

**Step 3:** Select the SAP Best Practice scope item catalog:
- **JSON/Excel import:** Upload the scope item list obtained from SAP.
- Each row represents an L3 scope item (with codes like J58, BD9, J45).

**Step 4:** The system automatically creates:
- 3 L1 nodes (Value Chain): Core Business Processes, Management Processes, Support Processes
- 8–12 L2 nodes (Process Area): the process area to which each scope item belongs
- 50–100 L3 nodes (Scope Item): each imported row

**Step 5:** Verify the import result. The Process Hierarchy screen should display an L1→L2→L3 tree structure.

### 3.2 Creating L4 Sub-Processes

L4 sub-processes must be added beneath L3 scope items. L4 nodes must exist before a workshop can be started.

**Option 1 — Import from catalog (recommended):**
1. Click an L3 node in Process Hierarchy (e.g., J58).
2. Switch to the "Sub-Processes" tab in the right panel.
3. Click "Import from Catalog."
4. The standard sub-processes from the SAP Best Practice catalog are listed.
5. Select the applicable ones → "Import Selected" → L4 nodes are created.

**Option 2 — Import from BPMN:**
1. Click "Import from BPMN" on the L3 node.
2. Paste a Signavio URL or upload a BPMN XML file.
3. The system parses activities in the BPMN and proposes them as L4 nodes.
4. Confirm → L4 nodes are created.

**Option 3 — Manual entry:**
1. Click "Add Sub-Process" on the L3 node.
2. Enter a code (e.g., J58.01), name, and description.
3. Save → L4 node is created.

### 3.3 Defining Scope

**Step 1:** Switch to "Matrix" view in Process Hierarchy. All L3 scope items are listed in a flat table.

**Step 2:** For each row, select a value from the "Scope" column dropdown:
- **In Scope** — included in the project; workshops will be conducted
- **Out of Scope** — not included in the project
- **Under Review** — decision pending

**Step 3:** Every change is automatically logged: who changed what, when, and to which value.

### 3.4 Assigning Waves

**Step 1:** In the Matrix view, select a value from the "Wave" column dropdown:
- Wave 1, Wave 2, Wave 3, Wave 4 (or more)

**Step 2:** Recommended sequencing:
- Wave 1: FI + CO (financial foundation)
- Wave 2: SD + MM (operational processes)
- Wave 3: PP + QM (manufacturing)
- Wave 4: Remaining areas

### 3.5 Assigning Project Roles

**Step 1:** Go to "Team & Roles" in project settings.

**Step 2:** For each team member:
- Select the user
- Assign a role (PM, Module Lead, Facilitator, etc.)
- For Module Lead and Facilitator, specify the process area (FI, SD, etc.)

---

## 4. Screen 1: Process Hierarchy Manager

### 4.1 Accessing the Screen

Left sidebar → Explore → Process Hierarchy

### 4.2 Three View Modes

Select the view mode from the tabs at the top of the screen:

**Hierarchy (Tree) View:**
- L1→L2→L3→L4 tree structure
- Expand/collapse each node using the arrow on its left
- Information displayed on each node:
  - Level badge (L1 purple, L2 blue, L3 green, L4 yellow)
  - Process code and name
  - Fit status badge (Fit=green, Partial=yellow, Gap=red, Pending=purple)
  - Fit distribution bar (on L1/L2/L3 — proportional distribution of child processes)
  - Workshop count (if any)

**Workshops View:**
- Same tree structure but workshop-focused
- Workshop cards appear next to each L3 node
- Each card shows the workshop date, facilitator, and status

**Matrix View:**
- All L3 scope items in a flat table
- Columns: Code, Name, Area, Wave, Scope Status, Fit Status, Workshop Count, REQ Count, OI Count
- Sortable and filterable
- Ideal for steering committee presentations

### 4.3 Filters

The filter bar at the top of the screen:

- **Search:** Search by code or name (e.g., "J58" or "Sales Order")
- **Fit Status:** All / Fit / Partial Fit / Gap / Pending
- **Scope:** All / In Scope / Out of Scope / Under Review
- **Area:** FI, SD, MM, etc.
- **Wave:** 1, 2, 3, 4

Multiple filters can be applied simultaneously. The active filter count is shown next to the filter button.

### 4.4 Detail Panel

Clicking a node in the tree opens a detail panel on the right. It contains four tabs:

**Overview tab:**
- Process code, name, description
- Scope status
- Wave
- Sub-process count
- BPMN diagram (if available — displayed as an iframe or viewer)

**Fit Analysis tab:**
- Fit/Partial/Gap/Pending distribution bar and percentages
- List of child processes and their fit status
- Total requirement and open item counts

**Requirements tab:**
- List of requirements linked to this node (and its children)
- Priority, type, and status information
- Clicking a REQ code navigates to REQ Hub

**Workshop tab:**
- List of linked workshop(s)
- Clicking a workshop code opens Workshop Detail

### 4.5 Viewing BPMN Diagrams

If a BPMN diagram exists on an L3 or L4 node:

1. Click the node → open the Overview tab in the detail panel.
2. The BPMN section displays the diagram:
   - If a Signavio URL is linked → Signavio view in an iframe
   - If a BPMN XML is uploaded → interactive BPMN viewer
   - If an image is uploaded → displayed as PNG/SVG
3. Zoom in/out and pan are available.

**To upload a BPMN:**
1. Right-click the node → select "Manage BPMN."
2. Choose the upload method: Signavio URL / BPMN XML file / Image (PNG/SVG)
3. Upload → the diagram is linked to the node.

---

## 5. Screen 2: Workshop Hub

### 5.1 Accessing the Screen

Left sidebar → Explore → Workshop Hub

### 5.2 Three View Modes

**Table View — default:**
- All workshops in a table
- Columns: Code, Scope Item, Name, Area, Wave, Date, Status, Facilitator, Fit Bar, Decision Count, OI Count, REQ Count
- Click any column header to sort
- Click a row to open Workshop Detail

**Kanban View:**
- 4 columns: Draft → Scheduled → In Progress → Completed
- Each workshop appears as a card
- Cards cannot be dragged to change status (status changes are made in Workshop Detail)
- Ideal for a quick overview

**Capacity View:**
- Card grid by facilitator
- Each card shows:
  - Facilitator name and area
  - Completed / active / planned workshop counts
  - Weekly workload bar chart
  - Red warning: if more than 3 workshops per week
  - Open item count

### 5.3 Filtering

Filter bar:
- **Search:** Search by code, name, or scope item
- **Status:** Draft / Scheduled / In Progress / Completed / Cancelled
- **Wave:** 1 / 2 / 3 / 4
- **Area:** FI / SD / MM / etc.
- **Facilitator:** Select from dropdown
- **Date Range:** Start and end date

### 5.4 Grouping

From the "Group By" selector, you can group workshops by:
- **Wave** — by wave (most common)
- **Area** — by process area
- **Facilitator** — by person
- **Status** — by status
- **Date** — by week
- **None** — flat list

Group headers are sticky — you can see which group you're in while scrolling. Groups can be collapsed and expanded.

### 5.5 KPI Bar

Metrics at the top of the screen, updated based on applied filters:
- Total workshop count
- Completion percentage
- Active workshop count
- Scheduled workshop count
- Open item count
- Gap count
- Requirement count

### 5.6 Creating a Workshop

1. Click "New Workshop" in the top right.
2. Fill in the form:
   - Name (e.g., "Sales Order Management")
   - Type: Fit-to-Standard / Deep Dive / Follow-up / Delta Design
   - Process Area: SD, FI, MM, etc.
   - Wave
   - Date and time
   - Facilitator (select from dropdown)
   - Location or meeting link
3. Link scope items: select which L3 scope item(s) will be covered in this workshop.
4. "Create" → Workshop is created in "Draft" status.

### 5.7 Workshop Dependencies

Some workshops depend on others. To add a dependency:

1. From the three-dot menu on the workshop row, select "Manage Dependencies."
2. Choose a dependency type:
   - **Must Complete First** — the other workshop must be completed before this one starts
   - **Information Needed** — information is expected from the other workshop
   - **Cross-Module Review** — shared topics require joint evaluation
   - **Shared Decision** — the same decision affects both workshops
3. Select the target workshop → "Add Dependency"

Workshops with dependencies display a yellow badge. Workshops with incomplete dependencies can be started but a warning is shown.

---

## 6. Screen 3: Workshop Detail

### 6.1 Accessing the Screen

Click a row in Workshop Hub, or access directly via URL.

### 6.2 Workshop Header

At the top of the screen:
- Workshop code and name (e.g., WS-SD-01 — Sales Order Management)
- Status badge (Draft / Scheduled / In Progress / Completed)
- Type badge (Fit-to-Standard / Deep Dive / etc.)
- Date, time, and location
- Facilitator name
- Linked scope items
- Action buttons (vary by status)

### 6.3 Workshop Lifecycle

**Draft → Scheduled:**
- When date, facilitator, and attendees are assigned, the workshop is marked "Scheduled."
- It has not yet started.

**Scheduled → In Progress (Starting a Workshop):**
- Click "Start Workshop."
- The system checks:
  - Do the scope items have L4 sub-processes? If not, error message: "Create sub-processes first."
  - If L4s exist → a process step record is created for each one.
  - Workshop becomes "In Progress."
- If this is session 2+ of a multi-session workshop, data from the previous session is automatically loaded.

**In Progress → Completed (Completing a Workshop):**
- Click "Complete Workshop."
- The system checks:
  - Single session or last session: all steps must have a fit decision. Otherwise, completion is blocked.
  - Intermediate session: steps without fit decisions may remain — a "will be addressed in the next session" warning is shown.
  - If open items exist: a warning is shown but does not block completion.
  - If unresolved cross-module flags exist: a warning is shown.
- If you confirm:
  - Workshop becomes "Completed."
  - If it is the last session: fit decisions propagate automatically from L4→L3→L2→L1.

**Completed → Reopen (if needed):**
- Click "Reopen Workshop" (PM and Module Lead only).
- A reason is required.
- Workshop returns to "In Progress."
- Changes are recorded in the revision log.

### 6.4 Six Tabs

Workshop Detail contains six tabs:

#### Tab 1: Process Steps

This is the workshop's main working area.

Each L4 sub-process is listed as a card. The card displays:
- Step number and code (e.g., 1. BD9.01)
- Sub-process name
- Fit decision badge (blank if not yet decided)
- Decision count, OI count, REQ count

**Clicking a card opens the detail area:**

**A) Previous Session Info (for multi-session workshops):**
- The previous session's fit decision, notes, and decisions are shown read-only.
- Blue info box: "Previous Session (WS-FI-03A): Gap — IC netting logic was discussed"

**B) BPMN Viewer:**
- If a BPMN diagram exists for this step, it is displayed here.

**C) Discussion Notes:**
- Free-text field. Enter discussion notes during the workshop.

**D) Fit Decision Selector:**
- Three options: Fit / Partial Fit / Gap
- A brief description beneath each option:
  - Fit: "The SAP standard fully covers this process"
  - Partial Fit: "Can be resolved with configuration or a workaround"
  - Gap: "The SAP standard does not cover this; development is required"
- Select one → the decision is saved and the badge updates.

**E) Adding a Decision:**
- Click "Add Decision."
- Enter the decision text (e.g., "Custom order type ZOR will be replaced with standard OR")
- Select the decision maker
- Choose a category: Process / Technical / Scope / Organizational / Data
- Save → a purple card is added beneath the step.

**F) Adding an Open Item:**
- Click "Add Open Item."
- Enter a title (e.g., "Schedule a meeting with SAP to evaluate the aATP scenario")
- Select priority: P1 (Critical) / P2 (High) / P3 (Medium) / P4 (Low)
- Choose a category: Clarification / Technical / Scope / Data / Process / Organizational
- Select the assignee
- Set a due date
- Save → an orange card is added beneath the step.
- The OI also appears automatically in the OI Hub.

**G) Adding a Requirement:**
- Click "Add Requirement" (active only when a Partial Fit or Gap decision has been made).
- Enter a title (e.g., "Multi-plant ATP with priority-based allocation")
- Priority: P1 / P2 / P3 / P4
- Type: Development / Configuration / Integration / Migration / Enhancement / Workaround
- Estimated effort (hours)
- Description
- Save → a blue card is added beneath the step.
- The REQ is created in "Draft" status and also appears in REQ Hub.

**H) Cross-Module Flag:**
- Click "Flag for Another Module."
- Select the target process area (e.g., MM)
- Enter a description (e.g., "ATP configuration impacts the procurement process")
- Save → a yellow flag is added to the step.

**I) Attaching a File:**
- Click "Attach File."
- Select a file (max 50 MB) — screenshot, document, BPMN export, etc.
- Choose a category: Screenshot / BPMN Export / AS-IS Document / TO-BE Document / Spec / Other
- Upload → the file is linked to the step.

#### Tab 2: Decisions

A consolidated list of all decisions across all steps.
- Grouped by source step
- Each card: decision code, text, decision maker, category
- This tab is view-only — decisions are added from within steps.

#### Tab 3: Open Items

A list of all OIs arising from the workshop.
- Priority, status, assignee, due date information
- Clicking an OI code navigates to the OI Hub
- Overdue items appear in red

#### Tab 4: Requirements

A list of all requirements arising from the workshop.
- Priority, type, status, effort information
- Clicking a REQ code navigates to REQ Hub

#### Tab 5: Agenda

Workshop agenda:
- Time, agenda item, duration, type (Session / Break / Demo / Discussion / Wrap-up)
- Agenda items are editable

#### Tab 6: Attendees

Attendee list:
- Name, role, organization (Customer / Consultant / Partner / Vendor)
- Attendance status: Confirmed / Tentative / Declined / Present / Absent
- Mark attendees as "Present" / "Absent" for workshop-day attendance tracking

### 6.5 Post-Workshop Actions

**Generating Meeting Minutes:**
1. In the completed workshop, click "Generate Minutes."
2. Select a format: Markdown / Word (DOCX) / PDF
3. Choose which sections to include: Attendees / Agenda / Step Results / Summary
4. "Generate" → the document is created and available for download.

**AI Summary:**
1. Click "AI Summary."
2. The system analyzes all notes, decisions, and OIs from the workshop.
3. An executive summary, key takeaways, and risk highlights are generated.
4. The summary is saved to the workshop and can be accessed later.

### 6.6 Multi-Session Workshops

Large scope items may require multiple sessions.

**Example:** WS-FI-03A (Session 1/2) and WS-FI-03B (Session 2/2)

**When Session A is closed:**
- Fit decisions for evaluated steps are saved
- Unevaluated steps remain blank
- Fit decisions are not yet propagated to L4 (propagation occurs in the final session)

**When Session B starts:**
- The same L4 steps are reloaded
- Each step shows Session A information alongside it:
  - "Previous Session: Fit" or "Previous Session: Not Evaluated"
  - Previous notes and decisions are read-only
- Steps left blank in Session A are listed with priority
- Decisions from Session A can be re-evaluated (may change)

**When Session B is closed (final session):**
- All steps must have a fit decision
- Decisions propagate L4→L3→L2→L1

---

## 7. Screen 4: Requirement & Open Item Hub

### 7.1 Accessing the Screen

Left sidebar → Explore → Requirements & Open Items

### 7.2 Two Tabs

Two main tabs at the top of the screen:
- **Requirements Registry** — all requirements
- **Open Item Tracker** — all open items

Each tab has its own filters, grouping options, KPIs, and action buttons.

### 7.3 Requirements Registry

#### KPI Bar
- Total requirement count
- P1 (Critical) count
- Draft / Under Review / Approved / In Backlog / Realized counts
- Synced to Cloud ALM count
- Total estimated effort (hours)

Counts update based on applied filters.

#### Filters
- **Search:** Search by REQ code, title, or scope item
- **Status:** Draft / Under Review / Approved / In Backlog / Realized / Verified / Deferred / Rejected
- **Priority:** P1 / P2 / P3 / P4
- **Type:** Development / Configuration / Integration / Migration / Enhancement / Workaround
- **Area:** FI / SD / MM / etc.
- **Wave:** 1 / 2 / 3 / 4
- **ALM Synced:** Yes / No

#### Grouping
- Status / Priority / Area / Type / Scope Item / Wave / Workshop / None

#### Requirement Row
Each row displays:
- REQ code (clickable)
- Priority pill (P1=red, P2=orange, P3=blue, P4=gray)
- Type pill
- Fit status pill (Gap=red, Partial=yellow)
- Title
- Scope item code
- Area
- Effort (hours)
- Status flow indicator (position in the lifecycle)
- Cloud ALM icon (if synced)

#### Requirement Detail (clicking a row)
The row expands to show a detail panel beneath:

**Traceability Block:**
- Source workshop code (click to open Workshop Detail)
- Scope item code (click to go to Process Hierarchy)
- Process step code
- Created by and date
- Approved by and date (if applicable)
- Cloud ALM ID (if synced)

**Linked Open Items:**
- List of OIs that block this requirement
- OI status is shown — green checkmark if all are closed, warning if any remain open

**Dependencies:**
- Other requirements this requirement depends on
- Dependency status (completed or not?)

**Attachments:**
- Files linked to this requirement

**Action Buttons:**
Vary by status:
| Current Status | Visible Buttons |
|---------------|----------------|
| Draft | Submit for Review, Edit, Defer |
| Under Review | Approve, Reject, Return to Draft, Edit |
| Approved | Push to Cloud ALM, Defer, Edit |
| In Backlog | Mark Realized, Edit |
| Realized | Verify, Edit |
| Deferred | Reactivate |

A comment field opens when any button is clicked. Buttons are grayed out and disabled if you lack the required permissions.

#### Batch Operations
Select multiple requirements using the checkbox on the left of each row. Then choose from the "Batch Actions" menu at the top:
- Batch Approve — approve all selected requirements
- Batch Defer — defer all selected requirements
- Export — export selected to Excel

During batch approval, area permissions are checked for each requirement individually. Requirements in areas you are not authorized for will fail; others will be processed.

### 7.4 Open Item Tracker

#### KPI Bar
- Total open item count
- Open / In Progress / Blocked / Closed counts
- Overdue count — red warning if greater than 10
- Open P1 count

#### Filters
- **Search:** Search by OI code, title, or assignee
- **Status:** Open / In Progress / Blocked / Closed / Cancelled
- **Priority:** P1 / P2 / P3 / P4
- **Category:** Clarification / Technical / Scope / Data / Process / Organizational
- **Assignee:** Dropdown (populated from all assignees)
- **Area and Wave**
- **Overdue Toggle:** Red button — shows only overdue OIs

#### Open Item Row
- OI code
- Priority pill
- Status pill
- Category pill
- Title
- Assignee
- Due date (red if overdue)
- Scope item
- Area

Overdue OI rows are highlighted with a red tint.

#### Open Item Detail (clicking a row)

**Traceability:** Workshop, scope item, and process step references.

**Linked Requirement:**
- If this OI blocks a requirement, a blue info box is shown:
  "Linked Requirement: REQ-042 — Once this OI is closed, the requirement approval process can proceed"

**Blocked Reason:**
- If status is "Blocked," the reason is displayed.

**Resolution:**
- If status is "Closed," the resolution text is displayed.

**Activity Log:**
- All status changes, reassignments, and comments in chronological order

**Action Buttons:**
| Current Status | Visible Buttons |
|---------------|----------------|
| Open | Start Progress, Mark Blocked, Close, Cancel, Edit |
| In Progress | Close, Mark Blocked, Cancel, Edit |
| Blocked | Unblock, Cancel |
| Closed | Reopen |
| Cancelled | Reopen |

A resolution text is required when clicking "Close."
A reason is required when clicking "Mark Blocked."

**Reassignment:**
- Click "Reassign" → select the new person → write a comment → save.

### 7.5 OI Closure and Requirement Impact

When an open item is closed, and it blocks a requirement, the system automatically checks:

1. Have all OIs linked to the blocked requirement been closed?
2. Yes → the requirement owner is notified: "All blockers are resolved; REQ-042 can now be approved"
3. No → open OIs remain; the requirement is still blocked

This check is automatic; no additional user action is required.

---

## 8. Screen 5: Explore Dashboard

### 8.1 Accessing the Screen

Left sidebar → Explore → Dashboard

### 8.2 Widgets

The dashboard contains 10 widgets. Each answers a specific question:

**1. Workshop Completion Burndown**
- Question: "Where are we relative to the plan?"
- Display: Area chart — workshop completion count over time
- Ideal line vs. actual line

**2. Wave Progress Bars**
- Question: "How far along is each wave?"
- Display: Horizontal bars — Wave 1: 92%, Wave 2: 50%, Wave 3: 14%, Wave 4: 0%

**3. Fit/Gap Trend**
- Question: "Is the gap count increasing or decreasing?"
- Display: Stacked area chart — fit/partial/gap/pending distribution over time

**4. Requirement Pipeline**
- Question: "What stage are requirements at?"
- Display: Funnel — Draft → Review → Approved → Backlog → Realized → Verified

**5. Open Item Aging**
- Question: "How long have OIs been open?"
- Display: Bar chart — 0–3 days, 4–7 days, 8–14 days, 15+ days

**6. Overdue Trend**
- Question: "Are delays increasing?"
- Display: Line chart — overdue OI count over time

**7. Gap Density Heatmap**
- Question: "Which area-wave intersection has the most gaps?"
- Display: Heatmap — rows = process areas, columns = waves, color = gap density

**8. Facilitator Load Comparison**
- Question: "Is the workload balanced?"
- Display: Grouped bars — completed/active/planned workshops per facilitator

**9. Scope Coverage**
- Question: "What percentage of L4s have been assessed?"
- Display: Donut chart — assessed vs. pending

**10. Top 10 Open Items by Age**
- Question: "Which are the oldest open OIs?"
- Display: Table — OI code, title, age (days), assignee, priority

### 8.3 Date Range

The date picker at the top of the dashboard allows you to change the displayed period:
- Last 1 week / Last 2 weeks / Last 1 month / Entire project
- Custom date range

### 8.4 Data Source

Dashboard data comes from daily snapshots. All project metrics are automatically recorded every day. This enables "what changed compared to last week" visibility.

---

## 9. Scope Change Management

### 9.1 When Is It Needed?

Scope may need to change during Explore:
- A new scope item needs to be added
- An existing scope item needs to be removed
- A gap is too large and the scope is under discussion
- A wave change is required

### 9.2 Creating a Scope Change Request (SCR)

1. Go to Process Hierarchy → Matrix view.
2. Click "Request Scope Change" on the relevant scope item row.
3. Fill in the form:
   - Change type: Add to Scope / Remove from Scope / Change Wave / Split / Merge
   - Proposed value (new scope status or wave)
   - Justification (why this change is needed)
4. "Submit" → the SCR is created.

### 9.3 Impact Analysis

The system automatically calculates:
- How many workshops are affected (cancellation/replanning)
- How many requirements are affected
- How many open items are affected
- Estimated effort change

This information is displayed in the SCR detail.

### 9.4 Approval Process

1. SCR is created → status: "Requested"
2. PM or BPO reviews → status: "Under Review"
3. Approved → status: "Approved" / Rejected → status: "Rejected"
4. An approved SCR is implemented:
   - Scope status is updated
   - Affected draft workshops are cancelled
   - All changes are written to the audit log

### 9.5 Viewing History

To view the history of any scope item in Process Hierarchy:
1. Click the node → Detail panel
2. "Change History" tab → all changes in chronological order
   - Who changed it, when, old value → new value, SCR reference (if applicable)

---

## 10. Cloud ALM Integration

### 10.1 General Flow

```
Requirement "Approved" → "Push to Cloud ALM" → ALM Backlog Item is created → Worked on in the Realize phase
```

### 10.2 Pushing a Single Requirement

1. Open an approved requirement in REQ Hub.
2. Click "Push to Cloud ALM" (PM or Tech Lead only).
3. The system connects to the ALM API and creates a backlog item.
4. If successful:
   - Requirement status changes to "In Backlog"
   - ALM ID is written back (e.g., ALM-0234)
   - A sync icon appears
5. If an error occurs:
   - Error message is displayed
   - A retry button becomes active

### 10.3 Bulk Push

1. Apply a filter in REQ Hub: Status = Approved
2. Click "Sync All to Cloud ALM" at the top.
3. Confirmation dialog: "N requirements will be pushed to ALM. Continue?"
4. "Confirm" → bulk push begins.
5. Results report: N successful, M failed (with error details).

### 10.4 Sync Statuses

| Status | Meaning | Icon |
|--------|---------|------|
| — | Not yet pushed | Empty |
| Synced | Successfully pushed | Green cloud |
| Sync Error | Push failed | Red cloud |
| Out of Sync | Changed in ProjektCoPilot but ALM not updated | Yellow cloud |

---

## 11. Reporting and Export

### 11.1 Meeting Minutes

After workshop completion → Workshop Detail → "Generate Minutes"
- Format: Markdown / Word / PDF
- Content: Attendees + Agenda + Step Results + Summary

### 11.2 AI Summary

Workshop Detail → "AI Summary"
- Auto-generated executive summary
- Key takeaways, risk highlights, next steps

### 11.3 Steering Committee Presentation

Dashboard → "Export Report" → select format (PPTX / PDF)
- 6-slide auto-generated presentation
- Executive summary, wave progress, fit/gap distribution, requirement pipeline, risks, next steps

### 11.4 Excel Export

REQ Hub or OI Hub → "Export" button
- Data filtered according to current filters
- Downloaded in Excel (XLSX) format
- All fields included

---

## 12. Frequently Asked Questions

**Q: I accidentally made the wrong fit decision in a workshop. How do I fix it?**

A: If the workshop is still "In Progress" → click the relevant step → change the fit decision. If the workshop is "Completed" → the PM or Module Lead reopens the workshop with the "Reopen Workshop" button and provides a reason. Make the change, then close it again. All changes remain in the revision log.

**Q: Can a requirement originate from multiple workshops?**

A: No. Each requirement originates from a single process step in a single workshop. However, a requirement can depend on other requirements (dependency). Requirements from different workshops are connected via dependencies.

**Q: How do I reassign an open item to someone else?**

A: In the OI Hub, click the relevant OI → click "Reassign" → select the new person → write a comment → save. The assignment change is recorded in the activity log.

**Q: I accidentally set a scope item to "Out of Scope." Can I undo it?**

A: Yes. In Process Hierarchy → Matrix → change the scope to "In Scope" on the relevant row. Or the formal route: open an SCR via "Request Scope Change" and go through the approval process. In either case, the change is logged.

**Q: Why is the "Approve" button disabled?**

A: Three possible reasons:
1. You lack permission — only PM, Module Lead (own area), and BPO can approve.
2. The requirement is outside your area — you have the SD Module Lead role but are trying to approve an FI requirement.
3. A blocking OI exists — this requirement has open items blocking it. Close the OIs first.

**Q: The Cloud ALM sync failed. What should I do?**

A: Check the error message in the REQ detail. It's usually a connection error or a permissions issue on the ALM side. Try again with the "Retry" button. If the problem persists, contact your system administrator.

**Q: Is the dashboard data current?**

A: The dashboard is fed by daily snapshots. The latest snapshot is typically from this morning. For real-time data, use the KPI bars in REQ Hub and OI Hub — those are real-time.

**Q: What is the file upload limit?**

A: Single file maximum: 50 MB. Per-project total: 500 MB. Supported formats: PDF, DOCX, XLSX, PNG, JPG, SVG, BPMN, XML, TXT.

**Q: What does a cross-module flag mean?**

A: It means "this topic also concerns another module" for a workshop step. For example, in an SD workshop, you flag that the ATP configuration impacts MM's procurement process. This flag is visible when the MM workshop is planned and is addressed in that workshop.

**Q: Can I generate meeting minutes for a completed workshop after the fact?**

A: Yes. Workshop Detail → the "Generate Minutes" button is always active. You can regenerate at any time.

---

## 13. Shortcuts and Tips

### 13.1 Quick Navigation

- `Ctrl + K` or `/` → Global search (find any REQ, OI, Workshop, or scope item by code)
- The last 5 visited pages are listed under "Recent" in the left sidebar

### 13.2 Efficient Workshop Execution

- Complete L4 seeding before the workshop — it cannot be started without L4s.
- Prepare the agenda in advance — assign an estimated duration for each step.
- Upload the BPMN diagram — it accelerates discussion.
- Write notes in real time — they are hard to recall later.
- Create at least one decision record per step — so decisions are not lost.
- Keep OIs specific — instead of "investigate," write "H. Demir to investigate topic X by date Y."

### 13.3 Requirement Management Tips

- Submit P1 requirements for review immediately — don't let them sit.
- Estimate effort generously — it's easier to reduce later than to increase.
- Write at least one sentence of description per requirement.
- Track blocking OIs — a REQ cannot be approved while an OI is open.
- Hold a weekly batch approval meeting — approving one by one is inefficient.

### 13.4 Open Item Tracking Tips

- Never create an OI without a due date — dateless OIs get forgotten.
- Check the overdue toggle daily.
- Specifically track blocked OIs — regularly ask why they are blocked.
- Write detailed resolution text when closing an OI — it serves as a future reference.

### 13.5 Reporting Tips

- Review the Dashboard trend charts before the steering committee.
- Generate an automatic presentation with "Export Report," then customize it.
- The gap density heatmap is the most eye-catching widget — be prepared to explain the red zones.

---

## Glossary

| Term | Description |
|------|-------------|
| **L1** | Value Chain — top-level process tier (Core, Management, Support) |
| **L2** | Process Area — functional area (FI, SD, MM, etc.) |
| **L3** | Scope Item — SAP Best Practice process definition (J58, BD9, etc.) |
| **L4** | Sub-Process — detail step beneath L3 (J58.01, BD9.03, etc.) |
| **Fit** | The SAP standard covers this process |
| **Partial Fit** | Can be resolved with configuration or a workaround |
| **Gap** | The SAP standard does not cover this; development is required |
| **Fit-to-Standard** | Workshop comparing against the SAP standard |
| **Scope Item** | Process definition in the SAP Best Practice catalog |
| **Wave** | Implementation wave — determines workshop sequencing |
| **Requirement** | A need arising from a Gap or Partial Fit decision |
| **Open Item** | An action item requiring investigation or follow-up |
| **Decision** | A formal decision made in a workshop |
| **Process Step** | An L4 sub-process evaluated in the context of a workshop |
| **SCR** | Scope Change Request |
| **Cloud ALM** | SAP Application Lifecycle Management — backlog management system |
| **BPMN** | Business Process Model and Notation — process diagramming standard |
| **Facilitator** | SAP consultant who runs the workshop |
| **BPO** | Business Process Owner — customer-side process owner |
| **UAT** | User Acceptance Testing |
| **Realize** | SAP Activate's build/configuration phase (follows Explore) |
| **Signavio** | SAP's process modeling tool |

---

*ProjektCoPilot — Explore Phase Manager User Guide v1.0*
*Last updated: February 10, 2026*
