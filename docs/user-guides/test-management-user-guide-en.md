# ProjektCoPilot — Test Management System
## User Guide v1.0

---

**Product:** ProjektCoPilot — Test Management System
**Version:** 1.0
**Date:** 2026-02-10
**Target Audience:** Test Lead, Module Lead, Facilitator, BPO, Tester, PM
**Related Documents:** Test Management FS/TS v1.0, Explore Phase FS/TS v1.1

---

## Table of Contents

1. [Introduction and Overview](#1-introduction-and-overview)
2. [System Access and Roles](#2-system-access-and-roles)
3. [Module T1: Test Plan & Strategy](#3-module-t1-test-plan--strategy)
4. [Module T2: Test Suite Manager](#4-module-t2-test-suite-manager)
5. [Module T3: Test Execution](#5-module-t3-test-execution)
6. [Module T4: Defect Tracker](#6-module-t4-defect-tracker)
7. [Module T5: Test Dashboard](#7-module-t5-test-dashboard)
8. [Module T6: Traceability Matrix](#8-module-t6-traceability-matrix)
9. [Transitioning from Explore Phase to Testing](#9-transitioning-from-explore-phase-to-testing)
10. [Cloud ALM Synchronization](#10-cloud-alm-synchronization)
11. [Frequently Asked Questions](#11-frequently-asked-questions)
12. [Abbreviations and Glossary](#12-abbreviations-and-glossary)

---

## 1. Introduction and Overview

### 1.1 Who Is This Guide For?

This guide is intended for all project team members who will use the Test Management System within the ProjektCoPilot platform. Use the table below to identify which sections to prioritize based on your role:

| Your Role | Priority Sections |
|-----------|------------------|
| **Test Lead** | All sections — especially T1, T4, T5 |
| **Module Lead** | T2 (your area), T3 (execution), T4 (defects) |
| **BPO (Business Process Owner)** | T3 (UAT execution), T4 (defect review), T6 (traceability) |
| **Tester** | T3 (execution), T4 (defect creation) |
| **PM (Program Manager)** | T1 (strategy), T5 (dashboard), T6 (traceability) |
| **Facilitator / Consultant** | T2 (test case authoring), T3 (execution) |

### 1.2 What Is the Test Management System?

The Test Management System is the module that ensures all requirements, WRICEF/Config items, and business processes produced during the Explore Phase of an SAP S/4HANA project are systematically tested.

The system covers 6 test levels:

```
┌──────────────────────────────────────────────────────────────────┐
│                      6 TEST LEVELS                                │
│                                                                   │
│  1. UNIT TEST         Individual object validation (WRICEF/Config)│
│  2. STRING TEST       Intra-module process chain                  │
│  3. SIT               Cross-module end-to-end integration         │
│  4. UAT               Business user acceptance testing            │
│  5. REGRESSION         Safeguarding existing processes            │
│  6. PERFORMANCE        System behavior under load                 │
│                                                                   │
│  + DEFECT MANAGEMENT (cross-cutting across all levels)            │
└──────────────────────────────────────────────────────────────────┘
```

### 1.3 Test Management and Explore Phase Relationship

Test Management is the direct continuation of the Explore Phase. Every output created in Explore becomes an input for the testing process:

```
WHAT DID YOU DO IN EXPLORE?                WHAT HAPPENS IN TESTING?
───────────────────────────                ────────────────────────
Made a fit decision in a workshop     →    SIT and UAT scenarios are generated
Created a requirement                 →    Test cases are linked to it
Defined a WRICEF item                 →    Unit tests are auto-generated
Defined a Config item                 →    Unit tests are auto-generated
Drew an E2E process flow              →    SIT scenario tests this flow
Approved a process as BPO             →    You will retest it in UAT
```

### 1.4 Navigation

Access the Test Management System by clicking **Test Mgmt** in the left sidebar. It contains 6 sub-screens:

```
Test Mgmt
  ├── T1: Plan & Strategy       (test plan and strategy)
  ├── T2: Suite Manager          (test case management)
  ├── T3: Execution              (test running)
  ├── T4: Defect Tracker         (defect tracking)
  ├── T5: Dashboard              (KPIs and Go/No-Go)
  └── T6: Traceability           (traceability matrix)
```

---

## 2. System Access and Roles

### 2.1 Roles and Permissions

The Test Management System introduces the **Test Lead** role in addition to the 7 existing Explore Phase roles. The table below shows what each role can and cannot do:

| Action | PM | Module Lead | Test Lead | BPO | Tester | Facilitator | Tech Lead |
|--------|:--:|:----------:|:---------:|:---:|:------:|:----------:|:---------:|
| Create/edit test plan | ✓ | — | ✓ | — | — | — | — |
| Approve test plan | ✓ | — | — | — | — | — | — |
| Create test suite | ✓ | ✓* | ✓ | — | — | — | — |
| Create/edit test case | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Approve test case | ✓ | ✓* | ✓ | — | — | — | — |
| Execute test | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create defect | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Assign defect | ✓ | ✓* | ✓ | — | — | — | — |
| Resolve defect | ✓ | ✓ | — | — | — | ✓ | ✓ |
| Retest defect | ✓ | ✓ | ✓ | — | ✓ | — | — |
| Close defect | ✓ | ✓ | ✓ | — | — | — | — |
| Provide UAT sign-off | ✓ | — | — | ✓ | — | — | — |
| Export dashboard | ✓ | ✓ | ✓ | ✓ | — | — | — |

*\* Module Lead: within their own process area only*

### 2.2 Who Uses Which Screen and When

**Test Lead — Daily routine:**
1. T5 Dashboard → overall status check, Go/No-Go red items
2. T4 Defect Tracker → triage new defects (severity, priority, assignment)
3. T3 Execution → progress of ongoing test runs
4. T1 Plan → update the test calendar

**Module Lead (e.g., FI Lead) — Daily routine:**
1. T4 → defects assigned to their area
2. T2 → test case approval status
3. T3 → test execution progress in their area

**BPO — During UAT period:**
1. T3 → run UAT scenarios
2. T4 → log defects for issues found
3. UAT sign-off → provide the "I accept this process" approval

**Tester — Daily routine:**
1. T3 → run assigned test cases
2. T4 → create defects for failed steps
3. T4 → retest resolved defects

---

## 3. Module T1: Test Plan & Strategy

### 3.1 What Is Done Here?

The Test Plan is the central document for the project's test strategy. A single test plan is created per project. The test plan defines:

- Which test levels will be applied?
- What are the entry and exit criteria for each level?
- Which environments (DEV, QAS, PRD) will be used?
- What is the test calendar?
- Roles and responsibilities

### 3.2 Creating a Test Plan

**Path:** Test Mgmt → T1: Plan & Strategy → "+ Create Test Plan"

**Steps:**

1. **Enter plan information:**
   - Plan name (e.g., "Arçelik S/4HANA Test Plan")
   - Version (e.g., "1.0")

2. **Write the strategy document:** A Markdown editor opens in the Strategy tab. Document your test approach, risks, tools, and out-of-scope areas here.

3. **Fill in the environment matrix:** In the Environments tab, specify which environment will be used for each test level:

   | Test Level | Environment | Notes |
   |-----------|-------------|-------|
   | Unit Test | DEV | Developer's own environment |
   | String Test | QAS | After transport |
   | SIT | QAS | Integration testing |
   | UAT | QAS | Business user environment |
   | Regression | QAS | Can be run automatically |
   | Performance | QAS (or dedicated) | Load testing environment |

4. **Define entry/exit criteria:** In the Criteria tab, specify conditions for each level. The system pre-fills default criteria, which you can customize as needed.

5. **Submit for approval:** Click "Submit for Approval." When the PM approves, the plan moves to `approved` status.

### 3.3 Test Calendar

The Calendar tab shows a timeline of test cycles. This is a Gantt-like view:

```
              Week 1    Week 2    Week 3    Week 4    Week 5    Week 6
Unit Test     ████████████
String Test              ██████████
SIT                               ████████████
UAT                                          ████████████
Regression                                              ████████
Performance                       ████████████████████████████████
```

Each bar represents a test cycle (test_cycle). Click a bar to navigate to that cycle's detail.

### 3.4 Creating a Test Cycle

**Path:** T1: Plan → "+ Create Cycle"

A test cycle is the execution window for a specific test level within a specific time period. For example, "Wave 1 — SIT Cycle 1."

**Fields:**
- **Code:** Auto-assigned (TC-001, TC-002, ...)
- **Name:** Descriptive name (e.g., "Wave 1 — SIT Cycle 1")
- **Test level:** Unit, String, SIT, UAT, Regression, Performance
- **Wave:** Which wave it belongs to (1, 2, 3, 4)
- **Planned start/end:** Calendar selection
- **Assigned suites:** Select the test suites to be run in this cycle

**Starting a cycle:**
When you click "Start," the system checks entry criteria. If criteria are not met, a warning is shown. You can override with `force=true`, but this is logged.

---

## 4. Module T2: Test Suite Manager

### 4.1 Concepts

The building blocks of test management follow this hierarchy:

```
Test Plan (1 per project)
  └── Test Suite (level + area-based grouping)
        └── Test Case (individual test scenario)
              └── Test Step (sequential test steps)
```

**Test Suite** = a logical grouping of test cases. Each suite belongs to a single test level.

**Example suites:**
- TS-UT-001: "FI — Unit Tests — Financial Closing"
- TS-SIT-003: "O2C End-to-End — Order to Cash"
- TS-UAT-008: "SD — Happy Path — Domestic Sales"
- TS-REG-002: "MM — Regression Suite — Procurement"

### 4.2 Creating a Suite

**Path:** Test Mgmt → T2: Suite Manager

The top of the screen has 6 tabs — one for each test level:

```
[Unit] [String] [SIT] [UAT] [Regression] [Performance]
```

Click the desired level, then press "+ Create Suite."

**Fields:**
- **Name:** Descriptive (e.g., "FI — Unit Tests — GL Posting")
- **Test level:** Auto-filled from the selected tab
- **Process area:** FI, SD, MM, PP, QM, ... (dropdown)
- **Wave:** 1, 2, 3, 4
- **Scope item:** Link to an L3 scope item from Explore Phase (optional)
- **E2E scenario:** O2C, P2P, R2R, H2R, ... (for SIT and UAT)
- **Risk level:** Critical, High, Medium, Low (for regression)
- **Owner:** Suite owner (person)

### 4.3 Creating a Test Case — Manual Method

**Path:** T2 → relevant suite → "+ Create Test Case"

**Fields:**

| Field | Description | Required |
|-------|-------------|----------|
| Title | Short description of the test case | Yes |
| Description | Detailed description | No |
| Priority | P1 (highest) — P4 (lowest) | Yes (default: P2) |
| Preconditions | What must be in place before testing? | No |
| Test data | What data will be used? | No |
| Estimated duration | Execution time (minutes) | No |
| UAT category | UAT only: Happy Path, Exception, Negative, Day-in-Life, Period-End | Yes for UAT |
| Regression risk | Regression only: Critical, High, Medium, Low | Yes for Regression |
| Perf. test type | Performance only: Load, Stress, Volume, Endurance, Spike | Yes for Performance |

**Traceability links (critical!):**
- **Requirement:** Which Explore requirement is this linked to?
- **WRICEF Item:** Which WRICEF item is being tested?
- **Config Item:** Which config item is being tested?
- **Process Level:** Which L3/L4 scope item/sub-process is this linked to?

These links are not mandatory but are **strongly recommended**. Missing links appear as gaps in the Traceability Matrix.

### 4.4 Writing Test Steps

After creating a test case, you need to define its steps. For each step:

| # | Field | Description | Example |
|---|-------|-------------|---------|
| 1 | **Action** | What should the tester do? | "Create a sales order using VA01" |
| 2 | **Expected result** | What should happen? | "Order number is generated, status is Open" |
| 3 | **Test data** | What data? | "Customer: 1000001, Material: FG-001, Qty: 100" |
| 4 | **SAP transaction** | T-code | "VA01" |
| 5 | **Module** | If cross-module | "SD" |
| 6 | **Checkpoint?** | Is this a critical validation point? | ☑ Yes |

**Tips for writing steps:**
- Keep each step atomic — one action, one validation.
- Write expected results precisely — not "should work correctly" but "a 10-digit order number should be created with status Open."
- Use the checkpoint flag at integration points (module transitions, interface calls).

### 4.5 Automatic Test Case Generation — From Explore Phase

This is one of the system's most powerful features. You can automatically generate test cases from the WRICEF/Config items and process steps defined in the Explore Phase.

#### 4.5.1 Unit Test Generation from WRICEF/Config

**Path:** T2 → Unit tab → relevant suite → "Generate from WRICEF" button

**What happens:**
1. A dialog opens listing the project's WRICEF and Config items.
2. Select the items for which you want to generate unit tests.
3. Click "Generate."
4. The system reads the `unit_test_steps` field from each WRICEF/Config item (this field was populated during the FS/TS writing in the Explore Phase).
5. At least 1 test case is created per item, with steps auto-filled.
6. Test cases are created in `draft` status — you need to review and approve them.

**Example:**
```
WRICEF Item: WRICEF-042 (Report — GL Trial Balance)
  unit_test_steps:
    1. Run the report (t-code: ZFI_TRIAL)
    2. Apply Company Code filter
    3. Select date range
    4. Verify results — balance consistency

    → Auto-generated Test Case: UT-042
      Title: "Unit Test — GL Trial Balance Report"
      4 steps auto-filled
      requirement_id, wricef_item_id auto-linked
```

#### 4.5.2 SIT/UAT Generation from Process Steps

**Path:** T2 → SIT or UAT tab → relevant suite → "Generate from Process" button

**What happens:**
1. A dialog opens listing the scope items (L3) from the Explore Phase.
2. Select the scope items for which you want to generate test cases.
3. For UAT, additionally select a category (Happy Path, Exception, Negative, ...).
4. Click "Generate."
5. The system reads the process_steps from the selected scope items' workshops.
6. Steps with a fit decision are sequentially converted into test steps.
7. Cross-module transition points are automatically marked as checkpoints.

**Example:**
```
Scope Item: J58 — Domestic Sales (O2C)
  Workshop steps:
    1. Create Sales Order (SD) — fit
    2. Check ATP (MM) — fit
    3. Create Delivery (SD) — fit
    4. Post Goods Issue (WM) — partial_fit
    5. Create Invoice (SD) — fit
    6. Post Accounting (FI) — fit

    → Auto-generated SIT Case: SIT-015
      Title: "SIT — O2C — Domestic Sales E2E"
      6 steps, module transitions marked as checkpoints
      Step 4 has a "partial_fit" note appended
```

### 4.6 Test Case Statuses

A test case progresses through the following statuses:

```
draft ──► ready ──► approved ──► (deprecated)
  │                    │
  └── editing          └── no longer current
```

- **draft:** Newly created, not yet reviewed
- **ready:** Reviewed, ready for approval
- **approved:** Approved, ready to be executed
- **deprecated:** An obsolete case no longer in use

Only test cases in `approved` status can be added to a test run.

### 4.7 Cloning Test Cases

When building a regression suite, you can clone an existing SIT or Unit test case:

**Path:** T2 → relevant test case → "Clone" button

The cloned case is created with a new code (e.g., SIT-015 → REG-008), and all steps are copied. You can then move it to a regression suite and assign a risk level.

---

## 5. Module T3: Test Execution

### 5.1 Test Execution Flow

Test Execution is the screen where test cases are actually run. The flow is:

```
Test Cycle (time window)
  └── Test Run (a single execution session)
        └── Test Execution (per-case result)
              └── Test Step Result (per-step result)
```

### 5.2 Creating a Test Run

**Path:** Test Mgmt → T3: Execution → select a cycle at the top → "+ Create Test Run"

**Fields:**
- **Name:** Descriptive (e.g., "SIT Run 1 — O2C Flow")
- **Environment:** DEV, QAS, PRD, Sandbox
- **Test cases:** Select the cases to run (from a suite or individually)

When you click "Create," a `test_execution` record is created for each selected test case (status: `not_run`).

### 5.3 Running a Test — Step by Step

**Path:** T3 → relevant run → click the case you want to run → "Run" button

The Execution Workspace opens. This area fills your entire screen and guides you step by step:

```
┌────────────────────────────────────────────────────────────┐
│  Test Case: SIT-015 — O2C Domestic Sales E2E               │
│  Suite: TS-SIT-003 | Priority: P1 | Status: In Progress    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1 of 6                                    ⏱ 00:12:34 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ACTION:                                             │   │
│  │ Create a sales order using VA01                      │   │
│  │                                                      │   │
│  │ EXPECTED RESULT:                                     │   │
│  │ 10-digit order number is created, status: Open       │   │
│  │                                                      │   │
│  │ TEST DATA:                                           │   │
│  │ Customer: 1000001, Material: FG-001, Qty: 100        │   │
│  │                                                      │   │
│  │ T-CODE: VA01  |  MODULE: SD  |  ☑ CHECKPOINT         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ACTUAL RESULT:                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [Enter actual result here]                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  EVIDENCE:                                                  │
│  [📎 Upload File]  [📷 Screenshot]                          │
│                                                             │
│  ┌──────┐  ┌──────┐  ┌──────────┐  ┌──────────┐          │
│  │ PASS │  │ FAIL │  │ BLOCKED  │  │ SKIPPED  │          │
│  │  ✓   │  │  ✗   │  │    ⊘     │  │    ⊝     │          │
│  └──────┘  └──────┘  └──────────┘  └──────────┘          │
│                                                             │
│  [◄ Previous]                            [Next ►]          │
└────────────────────────────────────────────────────────────┘
```

**For each step:**

1. **Perform the action in SAP.**
2. **Enter the actual result** — note what happened.
3. **Upload evidence** — screenshot or log file (optional but recommended).
4. **Mark the outcome:**
   - **PASS** ✓ — expected result occurred
   - **FAIL** ✗ — expected result did not occur → defect creation screen opens
   - **BLOCKED** ⊘ — test could not be run (environment issue, missing data, etc.)
   - **SKIPPED** ⊝ — step was skipped (a reason must be provided)

5. **Proceed to the next step.**

### 5.4 Creating a Defect from a Failed Step

When you mark a step as **FAIL**, a quick defect creation form opens at the bottom of the screen:

```
┌────────────────────────────────────────────────────────┐
│  🐛 CREATE DEFECT                                       │
│                                                          │
│  Title: [Auto: "SIT-015 Step 3 Fail — ..."]             │
│  Description: [Auto: step action + actual result]        │
│  Severity: [S1 ▾] [S2 ▾] [S3 ▾] [S4 ▾]                 │
│  Priority: [P1 ▾] [P2 ▾] [P3 ▾] [P4 ▾]                 │
│                                                          │
│  Auto-populated:                                         │
│  • Test Case: SIT-015                                    │
│  • Test Step: Step 3                                     │
│  • Requirement: REQ-042                                  │
│  • WRICEF Item: WRICEF-023                               │
│  • Process Area: SD                                      │
│  • Wave: 1                                               │
│                                                          │
│  [Create Defect]                                         │
└────────────────────────────────────────────────────────┘
```

The system auto-fills all traceability fields from the test case. You only need to select severity, priority, and add a detailed description.

### 5.5 Execution Result Calculation

When a test case execution is complete, the overall result is calculated as follows:

- All steps PASS → Execution = **PASS**
- Any step FAIL → Execution = **FAIL**
- Any step BLOCKED and no steps FAIL → Execution = **BLOCKED**
- No steps were run → Execution = **NOT_RUN**

### 5.6 Retest

When a defect is resolved (transitions to `retest` status), the associated test case must be re-run.

**Path:** T3 → relevant run → previously FAIL case → "Retest" button

The system creates a new execution record (execution_number: 2, 3, ...). Previous execution results are preserved in the history.

### 5.7 Progress Tracking

The top-right of the Execution screen shows a real-time progress indicator:

```
Pass: ████████████████████░░░░ 78%  (156/200)
Fail: ████░░░░░░░░░░░░░░░░░░░  8%   (16/200)
Blocked: ██░░░░░░░░░░░░░░░░░░░  4%   (8/200)
Not Run: ████░░░░░░░░░░░░░░░░░ 10%  (20/200)
```

---

## 6. Module T4: Defect Tracker

### 6.1 What Is a Defect?

A defect is a record of every instance where the expected result did not occur during testing. Defects are independent of test level — they can arise in Unit tests, UAT, Performance tests, or any other level.

### 6.2 Defect Lifecycle

Each defect can transition through 9 statuses:

```
    ┌──────┐
    │ NEW  │ ← Found during testing
    └──┬───┘
       │ assign
    ┌──▼──────┐
    │ASSIGNED │ ← Assigned to developer/consultant
    └──┬──────┘
       │ start_work
    ┌──▼────────┐
    │IN PROGRESS│ ← Fix is being worked on
    └──┬────────┘
       │ resolve
    ┌──▼───────┐
    │ RESOLVED │ ← Fix is done, awaiting retest
    └──┬───────┘
       │ send_to_retest
    ┌──▼──────┐
    │ RETEST  │ ← Test team is verifying the fix
    └──┬──────┘
      / \
   pass   fail
    /       \
┌──▼────┐  ┌▼────────┐
│CLOSED │  │REOPENED │──► Returns to ASSIGNED
└───────┘  └─────────┘

Additional statuses:
• DEFERRED — Not now; added to backlog
• REJECTED — Not a defect (by design, user error)
```

### 6.3 Creating a Defect — Manual

**Path:** Test Mgmt → T4: Defect Tracker → "+ Create Defect"

**Required fields:**
- **Title:** Short and descriptive (bad: "There's a bug"; good: "VA01 — Pricing condition ZPR1 is not calculated")
- **Description:** Steps to reproduce, expected result, actual result
- **Severity:** S1/S2/S3/S4
- **Priority:** P1/P2/P3/P4

**What does severity mean?**

| Severity | Meaning | Example |
|----------|---------|---------|
| **S1 — Showstopper** | System is down, business is stopped | SAP is completely inaccessible |
| **S2 — Critical** | Core function is broken, no workaround | Invoice cannot be created, no workaround |
| **S3 — Major** | Function is broken but workaround exists | Price is calculated incorrectly, can be fixed manually |
| **S4 — Minor** | Minor issue, business is not affected | Typo on screen, report formatting issue |

**What does priority mean?**

| Priority | Meaning | When to fix? |
|----------|---------|-------------|
| **P1 — Immediate** | Must be fixed immediately | Within hours |
| **P2 — High** | Fix as soon as possible | 1–2 business days |
| **P3 — Medium** | Fix within the sprint | 3 business days |
| **P4 — Low** | Can be added to backlog | By sprint end |

### 6.4 SLA (Service Level Agreement)

When a defect is assigned, the system automatically calculates the resolution deadline:

| Severity + Priority | First Response | Resolution Time | Deadline |
|---------------------|---------------|----------------|----------|
| S1 + P1 | 1 hour | 4 hours | Auto-calculated |
| S2 + P2 | 4 hours | 1 business day | Auto-calculated |
| S3 + P3 | 1 business day | 3 business days | Auto-calculated |
| S4 + P4 | 2 business days | Sprint end | Auto-calculated |

SLA status is shown with colors:
- 🟢 **On Track** — sufficient time remaining
- 🟡 **Warning** — time is running out (75% elapsed)
- 🔴 **Breached** — deadline exceeded

### 6.5 Defect Views

The Defect Tracker offers two views:

**Table View** — ideal for filtering and sorting:

```
┌──────┬────┬────┬───────────────────────────────┬──────────┬────────────┬──────┐
│ Code │ S  │ P  │ Title                         │ Status   │ Assignee   │ Age  │
├──────┼────┼────┼───────────────────────────────┼──────────┼────────────┼──────┤
│DEF-001│ S1 │ P1 │ Invoice cannot be created     │Assigned  │ Ali K.     │ 2d   │
│DEF-002│ S3 │ P3 │ Report format is broken       │In Progr. │ Ayse M.    │ 5d   │
│DEF-003│ S2 │ P2 │ Interface timeout error       │Resolved  │ Mehmet B.  │ 3d   │
└──────┴────┴────┴───────────────────────────────┴──────────┴────────────┴──────┘
```

**Kanban View** — ideal for flow tracking:

```
 New (3)     │ Assigned (5) │ In Progress (8) │ Resolved (4) │ Retest (2) │ Closed (45)
─────────────┼──────────────┼─────────────────┼──────────────┼────────────┼────────────
 DEF-047 S3  │ DEF-001 S1 🔴│ DEF-002 S3      │ DEF-003 S2   │ DEF-010 S3 │ DEF-009 S4
 DEF-048 S4  │ DEF-015 S2   │ DEF-005 S3      │ DEF-008 S3   │ DEF-022 S2 │ DEF-011 S3
 DEF-049 S3  │ DEF-017 S3   │ DEF-006 S4      │ DEF-012 S3   │            │ ...
             │ DEF-020 S3   │ DEF-007 S2 🟡   │ DEF-014 S4   │            │
             │ DEF-023 S4   │ DEF-016 S3      │              │            │
```

### 6.6 Resolving a Defect

The person who fixes the defect (developer/consultant) fills in the following:

- **Resolution:** Describe what was done
- **Resolution Type:** Select one of the following:
  - `code_fix` — Code fix
  - `config_change` — Configuration change
  - `data_correction` — Data correction
  - `workaround` — Temporary workaround
  - `by_design` — By design (not a defect)
  - `duplicate` — Duplicate of another defect
  - `cannot_reproduce` — Cannot reproduce
- **Root Cause:** Optional but recommended:
  - `code_error`, `config_error`, `data_issue`, `spec_gap`, `env_issue`, `user_error`, `design_flaw`

### 6.7 Retest and Closure

1. After the defect is `resolved`, the Test Lead clicks "Send to Retest."
2. The defect transitions to `retest` status.
3. A tester re-runs the related test case.
4. Outcome:
   - **Fix successful** → "Retest Passed" → defect becomes `closed`
   - **Fix unsuccessful** → "Retest Failed" → defect becomes `reopened`, returns to assigned

### 6.8 Defect Linking

You can establish relationships between defects:

| Link Type | Meaning | When? |
|-----------|---------|-------|
| **duplicate_of** | This defect is a copy of another | Same bug reported twice |
| **related_to** | Related but independent | Similar defects in the same area |
| **caused_by** | This defect was caused by another | Side effect of a fix |
| **blocks** | This defect must be resolved before the other can be run | Dependency |

---

## 7. Module T5: Test Dashboard

### 7.1 Dashboard Widgets

The Test Dashboard displays the real-time and trend-based status of the testing process with 10 widgets:

| # | Widget | What It Shows | How to Read It |
|---|--------|--------------|----------------|
| 1 | **Test Execution Progress** | Pass/fail/blocked/not_run by level | Horizontal bar per level — green should dominate |
| 2 | **Pass Rate Trend** | Daily pass rate line chart | Upward trend is good |
| 3 | **Defect Open/Close Rate** | Daily opened vs. closed defects | Close line should be above open line |
| 4 | **Defect Funnel** | New→Assigned→InProgress→Resolved→Closed | A narrowing funnel is good |
| 5 | **Severity Distribution** | S1/S2/S3/S4 distribution (donut) | S1/S2 share should be low |
| 6 | **Defect Aging** | Age of open defects (0–3, 4–7, 8–14, 15+ days) | Aged defects should be minimal |
| 7 | **Test Coverage Map** | Process area × test level heatmap | No empty/red cells is ideal |
| 8 | **Go/No-Go Scorecard** | 10-criteria checklist | All green → Go-Live ready |
| 9 | **Wave Readiness** | Summary by wave | Each wave's independent status |
| 10 | **Top 10 Open Defects** | Most critical open defects | Immediate action list |

### 7.2 Go/No-Go Scorecard

This is the ultimate output of the entire test management process. It is presented to the Steering Committee and answers the question: "Can we proceed to Go-Live?"

```
┌──────────────────────────────────────────────────────────────┐
│                    GO / NO-GO SCORECARD                        │
├────────────────────────────────────────┬──────────┬──────────┤
│ Criterion                              │ Target   │ Status   │
├────────────────────────────────────────┼──────────┼──────────┤
│ 1. Unit test pass rate                 │ ≥ 95%    │ 🟢 97.5% │
│ 2. SIT pass rate                       │ ≥ 95%    │ 🟢 96.1% │
│ 3. UAT Happy Path — all pass          │ 100%     │ 🟢 100%  │
│ 4. UAT BPO Sign-off — all approved    │ 100%     │ 🟡 85%   │
│ 5. Open S1 (Showstopper) defects      │ = 0      │ 🟢 0     │
│ 6. Open S2 (Critical) defects         │ = 0      │ 🔴 2     │
│ 7. Open S3 (Major) defects            │ ≤ 5      │ 🟢 3     │
│ 8. Regression suite pass rate          │ 100%     │ 🟢 100%  │
│ 9. Performance target achievement      │ ≥ 95%    │ 🟢 97%   │
│ 10. All critical defects closed        │ 100%     │ 🔴 94%   │
├────────────────────────────────────────┼──────────┼──────────┤
│ OVERALL DECISION                       │          │ 🔴 NO-GO │
│ (All criteria must be green)           │          │          │
└────────────────────────────────────────┴──────────┴──────────┘
```

In the example above, 2 criteria are red, so the decision is NO-GO. The S2 defects must be closed and BPO sign-offs must be completed.

### 7.3 Dashboard Export

Dashboard data can be exported in 3 formats:

- **PPTX** — for Steering Committee presentations
- **PDF** — for archiving
- **XLSX** — for detailed analysis

**Path:** T5 → top right → "Export" → select format → "Download"

---

## 8. Module T6: Traceability Matrix

### 8.1 What Does It Show?

The Traceability Matrix displays the entire chain from the Explore Phase to test management in a single table:

```
┌──────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│Requirement│ WRICEF/Config│ Test Cases   │ Last Run     │ Open Defects │
├──────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│REQ-001   │ WRICEF-023   │ UT-001 ✅    │ PASS (02/08) │ 0            │
│          │              │ SIT-015 ✅   │ PASS (02/09) │ 0            │
│          │              │ UAT-008 ⚠️   │ FAIL (02/10) │ DEF-003 (S2) │
├──────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│REQ-002   │ CFG-018      │ UT-002 ✅    │ PASS (02/07) │ 0            │
│          │              │ —            │ —            │ —            │
│          │              │ ⚫ SIT missing│              │              │
├──────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│REQ-003   │ —            │ ⚫ No tests   │ —            │ —            │
└──────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

### 8.2 Color Codes

- 🟢 **Green:** Tested and passed
- 🟡 **Yellow:** Tested but issues exist (open defect)
- 🔴 **Red:** Tested and failed
- ⚫ **Gray:** No test case exists or never been run

### 8.3 Gap Detection

The most important function of the Traceability Matrix is gap detection:

- Requirements with no test cases (like REQ-003 above) are automatically highlighted.
- Missing test cases at specific levels (like REQ-002 SIT) are shown.
- Closing these gaps is the Test Lead's responsibility.

### 8.4 Filtering

The matrix can be filtered along the following dimensions:
- **Process area:** FI, SD, MM, PP, ...
- **Wave:** 1, 2, 3, 4
- **Scope item:** L3 scope item
- **Test level:** Focus on a specific level

### 8.5 Export

The matrix can be exported in Excel and PDF formats. The Excel format is suitable for pivot analysis.

---

## 9. Transitioning from Explore Phase to Testing

### 9.1 Transition Steps

When the Explore Phase is complete, the transition to testing follows these steps:

**Step 1 — Create the Test Plan (Test Lead):**
Create the test plan in T1, write the strategy, fill in the environment matrix, and define entry/exit criteria. Submit to the PM for approval.

**Step 2 — Plan Test Cycles (Test Lead):**
Create wave-based test cycles in T1. Align the calendar with the Realize phase plan.

**Step 3 — Auto-Generate Unit Test Suites (Module Lead):**
T2 → Unit tab → create a suite for each process area → use "Generate from WRICEF" to auto-create unit test cases.

**Step 4 — Auto-Generate SIT Suites (Test Lead + Module Lead):**
T2 → SIT tab → create suites by E2E scenario → use "Generate from Process" to auto-create SIT cases.

**Step 5 — Prepare UAT Suites (Module Lead + BPO):**
T2 → UAT tab → create a suite for each L3 scope item → use "Generate from Process" to create UAT cases → review Happy Path, Exception, and Negative scenarios with the BPO.

**Step 6 — Build Regression Suite (Test Lead):**
T2 → Regression tab → clone critical test cases from SIT/Unit → assign risk levels.

**Step 7 — Define Performance Test Cases (Tech Lead):**
T2 → Performance tab → create test cases for critical transactions → define target response times and user counts.

**Step 8 — Approve Test Cases (Module Lead / Test Lead):**
T2 → review all draft cases → approve them to `approved` status.

### 9.2 Transition Checklist

| # | Task | Owner | Done? |
|---|------|-------|-------|
| 1 | Test plan created and approved | Test Lead + PM | ☐ |
| 2 | Test cycles planned | Test Lead | ☐ |
| 3 | Unit test cases generated (≥1 per WRICEF/Config) | Module Leads | ☐ |
| 4 | SIT cases generated (per E2E scenario) | Test Lead | ☐ |
| 5 | UAT cases generated (per L3 scope item) | Module Lead + BPO | ☐ |
| 6 | Regression suite built | Test Lead | ☐ |
| 7 | Performance cases defined | Tech Lead | ☐ |
| 8 | All cases in approved status | Test Lead | ☐ |
| 9 | QAS environment ready | Basis/Tech team | ☐ |
| 10 | Test data prepared | Module Leads | ☐ |
| 11 | Cloud ALM sync tested | Test Lead | ☐ |

---

## 10. Cloud ALM Synchronization

### 10.1 What Is Synchronized?

Bidirectional synchronization is available between ProjektCoPilot and SAP Cloud ALM:

| ProjektCoPilot → Cloud ALM | Cloud ALM → ProjektCoPilot |
|---------------------------|---------------------------|
| Test case push | — |
| Test step push | — |
| Execution result push | — |
| Defect push | Defect status update |

### 10.2 How to Use

**Single test case sync:**
T2 → relevant test case → "Push to ALM" button

**Bulk sync:**
T2 → select multiple cases → "Bulk ALM Sync" button

**Defect sync:**
T4 → relevant defect → "Push to ALM" button

**Execution result:**
T3 → when execution is complete → "Push Result to ALM" button

### 10.3 Field Mapping

When a test case is pushed, the following fields are transferred to Cloud ALM:

| ProjektCoPilot Field | Cloud ALM Field |
|---------------------|----------------|
| code | External Reference |
| title | Summary |
| description | Description |
| priority | Priority |
| test_level | Test Type |
| process_area | Process Area Tag |
| steps (action/expected) | Test Steps |

---

## 11. Frequently Asked Questions

**Q: I created a requirement in Explore Phase but I don't see a test case. What should I do?**
A: Test cases are not created automatically — you need to use the "Generate from WRICEF" or "Generate from Process" buttons. First create the relevant test suite, then use the generation button.

**Q: How do I know at which level a defect was found?**
A: Each defect has a `test_level` field that is auto-populated when the defect is created. It appears as "Unit," "SIT," "UAT," etc. in the defect detail.

**Q: Is the SLA duration in business days or calendar days?**
A: For S1+P1 and S2+P2, calendar hours (24/7) are used. For S3+P3 and S4+P4, business days are used.

**Q: Who can provide a UAT sign-off?**
A: Only users with the BPO (Business Process Owner) or PM role can provide a UAT sign-off.

**Q: I want to modify a test case but it's in approved status. What should I do?**
A: You cannot directly edit an approved case. Clone it, edit the new version, and approve it. Mark the old case as "deprecated."

**Q: Which cases should I add to the regression suite?**
A: Use a risk-based approach. Core financial processes and critical interfaces should be marked as `critical` risk; changes within the same module as `high` risk. The system automatically identifies affected test cases when a WRICEF/Config item changes.

**Q: Where do I get the target response time for performance testing?**
A: When creating a performance test case, enter the target time in milliseconds in the `perf_target_response_ms` field. Typical targets: <2000ms for dialog transactions; batch jobs are determined per project.

**Q: Is the Go/No-Go scorecard calculated automatically?**
A: Yes. T5 Dashboard → Go/No-Go Scorecard calculates all 10 criteria in real time. Green/red statuses update automatically.

**Q: When a defect is updated in Cloud ALM, does it update in ProjektCoPilot too?**
A: Yes, defect synchronization is bidirectional. When a defect status changes in Cloud ALM, the corresponding defect in ProjektCoPilot is also updated.

**Q: How are test cycles organized when there are multiple waves?**
A: Independent test cycles are created for each wave. For example: "Wave 1 — Unit Cycle 1," "Wave 1 — SIT Cycle 1," "Wave 2 — Unit Cycle 1," etc. All waves are visible in parallel on the test calendar.

---

## 12. Abbreviations and Glossary

| Abbreviation | Description |
|-------------|-------------|
| ALM | Application Lifecycle Management |
| BPO | Business Process Owner |
| Config | Configuration Item |
| DEF | Defect (bug record) |
| DEV | Development environment |
| E2E | End-to-End |
| FS/TS | Functional Specification / Technical Specification |
| O2C | Order to Cash |
| P2P | Procure to Pay |
| PM | Program/Project Manager |
| PRD | Production environment |
| QAS | Quality Assurance System (test environment) |
| R2R | Record to Report |
| REG | Regression Test |
| REQ | Requirement |
| SIT | System Integration Test |
| SLA | Service Level Agreement |
| UAT | User Acceptance Test |
| UT | Unit Test |
| WRICEF | Workflow, Report, Interface, Conversion, Enhancement, Form |

---

*End of Document*

*This guide was prepared based on ProjektCoPilot Test Management System FS/TS v1.0. For technical details, refer to test-management-fs-ts.md.*
