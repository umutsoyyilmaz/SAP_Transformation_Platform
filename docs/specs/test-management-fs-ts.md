# ProjektCoPilot — Test Management System
## Functional & Technical Specification v1.0

---

## 1. Document Overview

### 1.1 Purpose
This document defines the complete Functional Specification (FS) and Technical Specification (TS) for the **Test Management System** within the ProjektCoPilot platform. It covers test planning, 6 test levels (Unit, String, SIT, UAT, Regression, Performance), defect management, Cloud ALM synchronization, and full traceability from Explore Phase requirements through test execution to go-live readiness.

### 1.2 Relationship to Explore Phase

The Test Management System consumes outputs from the Explore Phase (FS/TS v1.1):

```
EXPLORE PHASE OUTPUT                    TEST MANAGEMENT INPUT
──────────────────                      ────────────────────
Requirement (approved)
  ├── type: configuration ──────────►   Config Item ──► Unit Test Case
  ├── type: development ────────────►   WRICEF Item ──► Unit Test Case
  └── type: integration ───────────►   WRICEF Item ──► Unit Test Case

Process Step (L4 with fit decision)
  └── Fit/Partial/Gap chain ────────►   SIT Scenario Steps
                                        UAT Scenario Steps

Scope Item (L3)
  └── Process Area ────────────────►   String Test Chain
                                        Regression Test Suite

Workshop Decisions ─────────────────►   Test Data Requirements
Open Item Resolutions ──────────────►   Test Acceptance Criteria
```

### 1.3 Module Map

```
+------------------------------------------------------------------------+
|                       TEST MANAGEMENT SYSTEM                            |
+----------------+----------------+----------------+---------------------+
|  Module T1     |  Module T2     |  Module T3     |  Module T4          |
|  Test Plan     |  Test Suite    |  Test          |  Defect             |
|  & Strategy    |  Manager       |  Execution     |  Tracker            |
+----------------+----------------+----------------+---------------------+
| Strategy doc   | Suite/Case     | Run sessions   | Lifecycle mgmt     |
| Test calendar  | 6 test levels  | Pass/Fail/Block| Severity/Priority  |
| Entry/Exit     | Step authoring | Evidence upload| SLA tracking       |
| Env planning   | Traceability   | Sign-off       | Root cause         |
+----------------+----------------+----------------+---------------------+
         |              |                |                  |
+------------------------------------------------------------------------+
|  Module T5: Test Dashboard & Reporting                                  |
|  Progress tracking | Go/No-Go scorecard | Trend analysis | Export      |
+------------------------------------------------------------------------+
         |              |                |                  |
+------------------------------------------------------------------------+
|  Module T6: Traceability Matrix                                         |
|  Requirement → WRICEF/Config → Test Case → Execution → Defect          |
+------------------------------------------------------------------------+
         |
+------------------------------------------------------------------------+
|           SHARED: Explore Phase Data + Cloud ALM Sync                   |
+------------------------------------------------------------------------+
```

### 1.4 Navigation Flow

```
Module T1: Test Plan & Strategy
    +- Click test level in plan -> Module T2 (filtered to that level)
    +- Click calendar entry -> Module T3 (test cycle execution)

Module T2: Test Suite Manager
    +- Click test case -> Module T3 (execute that case)
    +- Click WRICEF/Config link -> Explore Phase Module D
    +- Click scope item -> Explore Phase Module A

Module T3: Test Execution
    +- Mark step as Fail -> Auto-prompt defect creation -> Module T4
    +- Complete execution -> Updates T5 dashboard
    +- Upload evidence -> Attached to execution record

Module T4: Defect Tracker
    +- Click source test case -> Module T2
    +- Click related WRICEF -> Explore Phase Module D
    +- Click related requirement -> Explore Phase Module D
    +- Resolve defect -> Triggers retest in Module T3

Module T5: Test Dashboard
    +- Click any metric -> Drills to Module T2/T3/T4
    +- Go/No-Go card -> Shows all criteria status

Module T6: Traceability Matrix
    +- Click any cell -> Opens related entity (REQ/WRICEF/TestCase/Defect)
```

---

## 2. Data Model

### 2.1 Entity Relationship Diagram

```
TestPlan (project-level)
+-- 1:N -> TestCycle (wave/phase grouping)
+-- 1:N -> TestSuite (level-based grouping)

TestSuite
+-- N:1 -> TestPlan
+-- 1:N -> TestCase
+-- test_level: unit | string | sit | uat | regression | performance

TestCase
+-- N:1 -> TestSuite
+-- 1:N -> TestStep (ordered)
+-- N:1 -> Requirement (Explore FK, optional)
+-- N:1 -> WRICEF Item (existing FK, optional)
+-- N:1 -> Config Item (existing FK, optional)
+-- N:1 -> ProcessLevel (Explore FK, L3/L4)
+-- 1:N -> TestExecution
+-- N:M -> TestCase (dependencies)

TestStep
+-- N:1 -> TestCase
+-- 1:N -> TestStepResult (per execution)

TestCycle
+-- N:1 -> TestPlan
+-- 1:N -> TestRun (execution sessions)
+-- N:M -> TestSuite (suites in this cycle)

TestRun
+-- N:1 -> TestCycle
+-- 1:N -> TestExecution

TestExecution
+-- N:1 -> TestRun
+-- N:1 -> TestCase
+-- 1:N -> TestStepResult
+-- 1:N -> Defect (defects found)

TestStepResult
+-- N:1 -> TestExecution
+-- N:1 -> TestStep

Defect
+-- N:1 -> TestExecution (source)
+-- N:1 -> TestCase (source)
+-- N:1 -> TestStep (source step, optional)
+-- N:1 -> Requirement (Explore FK)
+-- N:1 -> WRICEF/Config Item (related)
+-- N:1 -> ProcessLevel (scope item)
+-- 1:N -> DefectComment
+-- 1:N -> DefectHistory
+-- N:M -> Defect (linked defects)

UATSignOff
+-- N:1 -> TestSuite (UAT suite)
+-- N:1 -> TestCycle
+-- N:1 -> User (BPO who signs off)
```

### 2.2 Table Definitions

#### 2.2.1 `test_plan`

Project-level test strategy and plan container.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `name` | VARCHAR(200) | NO | e.g., "S/4HANA Implementation Test Plan" |
| `version` | VARCHAR(20) | NO | e.g., "1.0", "2.1" |
| `status` | ENUM | NO | `draft`, `approved`, `active`, `completed`. Default: `draft` |
| `strategy_document` | TEXT | YES | Markdown — test strategy content |
| `environments` | JSON | YES | { "DEV": {...}, "QAS": {...}, "PRD": {...} } |
| `entry_criteria` | JSON | YES | Per test level entry criteria |
| `exit_criteria` | JSON | YES | Per test level exit criteria |
| `approved_by` | UUID | YES | FK -> user |
| `approved_at` | TIMESTAMP | YES | |
| `created_by` | UUID | NO | FK -> user |
| `created_at` | TIMESTAMP | NO | |
| `updated_at` | TIMESTAMP | NO | |

---

#### 2.2.2 `test_cycle`

A time-boxed execution window (e.g., "Wave 1 SIT Cycle 1", "UAT Cycle 2").

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `test_plan_id` | UUID | NO | FK -> test_plan |
| `code` | VARCHAR(20) | NO | Auto: TC-{seq}. e.g., TC-001 |
| `name` | VARCHAR(200) | NO | e.g., "Wave 1 — SIT Cycle 1" |
| `test_level` | ENUM | NO | `unit`, `string`, `sit`, `uat`, `regression`, `performance` |
| `wave` | INTEGER | YES | Wave number (from Explore) |
| `status` | ENUM | NO | `planned`, `in_progress`, `completed`, `aborted`. Default: `planned` |
| `planned_start` | DATE | YES | |
| `planned_end` | DATE | YES | |
| `actual_start` | DATE | YES | |
| `actual_end` | DATE | YES | |
| `entry_criteria_met` | BOOLEAN | NO | Default: false |
| `exit_criteria_met` | BOOLEAN | NO | Default: false |
| `created_at` | TIMESTAMP | NO | |
| `updated_at` | TIMESTAMP | NO | |

**Indexes:**
- `idx_tc_project_level` ON (`project_id`, `test_level`)
- `idx_tc_plan` ON (`test_plan_id`)
- `idx_tc_code` UNIQUE ON (`project_id`, `code`)

---

#### 2.2.3 `test_cycle_suite`

N:M between test cycles and test suites.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `test_cycle_id` | UUID | NO | FK -> test_cycle |
| `test_suite_id` | UUID | NO | FK -> test_suite |
| `sort_order` | INTEGER | NO | Default: 0 |

**Unique:** (test_cycle_id, test_suite_id)

---

#### 2.2.4 `test_suite`

Logical grouping of test cases by level, area, or scenario.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `test_plan_id` | UUID | NO | FK -> test_plan |
| `code` | VARCHAR(20) | NO | Auto: TS-{level_prefix}-{seq}. e.g., TS-UT-001, TS-SIT-003 |
| `name` | VARCHAR(200) | NO | |
| `description` | TEXT | YES | |
| `test_level` | ENUM | NO | `unit`, `string`, `sit`, `uat`, `regression`, `performance` |
| `process_area` | VARCHAR(5) | YES | FI, SD, MM, etc. |
| `wave` | INTEGER | YES | |
| `scope_item_id` | UUID | YES | FK -> process_level (L3) |
| `e2e_scenario` | VARCHAR(100) | YES | O2C, P2P, R2R, H2R, etc. (for SIT/UAT) |
| `risk_level` | ENUM | YES | `critical`, `high`, `medium`, `low` (for regression) |
| `automation_status` | ENUM | NO | `manual`, `partial`, `automated`. Default: `manual` |
| `status` | ENUM | NO | `draft`, `ready`, `in_progress`, `completed`. Default: `draft` |
| `owner_id` | UUID | YES | FK -> user |
| `created_at` | TIMESTAMP | NO | |
| `updated_at` | TIMESTAMP | NO | |

**Indexes:**
- `idx_ts_project_level` ON (`project_id`, `test_level`)
- `idx_ts_project_area` ON (`project_id`, `process_area`)
- `idx_ts_scope_item` ON (`scope_item_id`)
- `idx_ts_code` UNIQUE ON (`project_id`, `code`)

**Suite Code Prefixes:**
| Level | Prefix | Example |
|-------|--------|---------|
| unit | UT | TS-UT-001 |
| string | ST | TS-ST-001 |
| sit | SIT | TS-SIT-001 |
| uat | UAT | TS-UAT-001 |
| regression | REG | TS-REG-001 |
| performance | PRF | TS-PRF-001 |

---

#### 2.2.5 `test_case`

Individual test case with metadata and traceability.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `test_suite_id` | UUID | NO | FK -> test_suite |
| `code` | VARCHAR(20) | NO | Auto: {level_prefix}-{seq}. e.g., UT-001, SIT-042, UAT-015 |
| `title` | VARCHAR(500) | NO | |
| `description` | TEXT | YES | |
| `test_level` | ENUM | NO | Denormalized from suite |
| `priority` | ENUM | NO | `P1`, `P2`, `P3`, `P4`. Default: `P2` |
| `status` | ENUM | NO | `draft`, `ready`, `approved`, `deprecated`. Default: `draft` |
| `preconditions` | TEXT | YES | What must be true before test runs |
| `test_data` | TEXT | YES | Input data description or reference |
| `expected_duration_min` | INTEGER | YES | Estimated minutes to execute |
| `automation_status` | ENUM | NO | `manual`, `automated`, `to_automate`. Default: `manual` |
| `automation_script_ref` | VARCHAR(500) | YES | Path/URL to automation script |
| `requirement_id` | UUID | YES | FK -> requirement (Explore) |
| `wricef_item_id` | UUID | YES | FK -> wricef_items (existing) |
| `config_item_id` | UUID | YES | FK -> config_items (existing) |
| `process_level_id` | UUID | YES | FK -> process_level (L3/L4 from Explore) |
| `scope_item_code` | VARCHAR(10) | YES | Denormalized |
| `process_area` | VARCHAR(5) | YES | Denormalized |
| `wave` | INTEGER | YES | Denormalized |
| `uat_category` | ENUM | YES | Only for UAT: `happy_path`, `exception`, `negative`, `day_in_life`, `period_end` |
| `regression_risk` | ENUM | YES | Only for regression: `critical`, `high`, `medium`, `low` |
| `perf_test_type` | ENUM | YES | Only for performance: `load`, `stress`, `volume`, `endurance`, `spike` |
| `perf_target_response_ms` | INTEGER | YES | Target response time in ms (performance) |
| `perf_target_users` | INTEGER | YES | Target concurrent users (performance) |
| `perf_transaction_code` | VARCHAR(50) | YES | SAP transaction code (performance) |
| `created_by` | UUID | NO | FK -> user |
| `created_at` | TIMESTAMP | NO | |
| `updated_at` | TIMESTAMP | NO | |

**Indexes:**
- `idx_tcase_suite` ON (`test_suite_id`)
- `idx_tcase_project_level` ON (`project_id`, `test_level`)
- `idx_tcase_requirement` ON (`requirement_id`)
- `idx_tcase_wricef` ON (`wricef_item_id`)
- `idx_tcase_config` ON (`config_item_id`)
- `idx_tcase_process_level` ON (`process_level_id`)
- `idx_tcase_code` UNIQUE ON (`project_id`, `code`)

---

#### 2.2.6 `test_step`

Ordered steps within a test case.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `test_case_id` | UUID | NO | FK -> test_case |
| `step_number` | INTEGER | NO | Sequential order |
| `action` | TEXT | NO | What the tester does |
| `expected_result` | TEXT | NO | What should happen |
| `test_data` | TEXT | YES | Specific data for this step |
| `sap_transaction` | VARCHAR(50) | YES | T-code if applicable |
| `module` | VARCHAR(5) | YES | Module if cross-module step |
| `is_checkpoint` | BOOLEAN | NO | Critical verification point. Default: false |
| `notes` | TEXT | YES | |

**Unique:** (test_case_id, step_number)

---

#### 2.2.7 `test_case_dependency`

Test case ordering/dependency.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `test_case_id` | UUID | NO | FK -> test_case (dependent) |
| `depends_on_id` | UUID | NO | FK -> test_case (must run first) |
| `dependency_type` | ENUM | NO | `must_pass`, `must_run`, `data_dependency` |
| `created_at` | TIMESTAMP | NO | |

**Unique:** (test_case_id, depends_on_id). No self-reference.

---

#### 2.2.8 `test_run`

A single execution session within a cycle.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `test_cycle_id` | UUID | NO | FK -> test_cycle |
| `code` | VARCHAR(20) | NO | Auto: TR-{seq} |
| `name` | VARCHAR(200) | YES | e.g., "SIT Run 1 — O2C Flow" |
| `environment` | ENUM | NO | `dev`, `qas`, `prd`, `sandbox`. Default: `qas` |
| `status` | ENUM | NO | `not_started`, `in_progress`, `completed`, `aborted`. Default: `not_started` |
| `executed_by` | UUID | YES | FK -> user |
| `started_at` | TIMESTAMP | YES | |
| `completed_at` | TIMESTAMP | YES | |
| `notes` | TEXT | YES | |
| `created_at` | TIMESTAMP | NO | |

**Indexes:**
- `idx_trun_cycle` ON (`test_cycle_id`)
- `idx_trun_code` UNIQUE ON (`project_id`, `code`)

---

#### 2.2.9 `test_execution`

Individual test case execution result within a run.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `test_run_id` | UUID | NO | FK -> test_run |
| `test_case_id` | UUID | NO | FK -> test_case |
| `execution_number` | INTEGER | NO | 1st, 2nd, 3rd attempt. Default: 1 |
| `status` | ENUM | NO | `not_run`, `in_progress`, `pass`, `fail`, `blocked`, `skipped`. Default: `not_run` |
| `executed_by` | UUID | YES | FK -> user |
| `started_at` | TIMESTAMP | YES | |
| `completed_at` | TIMESTAMP | YES | |
| `duration_minutes` | INTEGER | YES | Actual duration |
| `notes` | TEXT | YES | |
| `defects_found` | INTEGER | NO | Count. Default: 0 |
| `alm_execution_id` | VARCHAR(50) | YES | Cloud ALM execution ID |
| `created_at` | TIMESTAMP | NO | |

**Indexes:**
- `idx_texec_run` ON (`test_run_id`)
- `idx_texec_case` ON (`test_case_id`)
- `idx_texec_status` ON (`project_id`, `status`)

---

#### 2.2.10 `test_step_result`

Per-step result within an execution.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `test_execution_id` | UUID | NO | FK -> test_execution |
| `test_step_id` | UUID | NO | FK -> test_step |
| `status` | ENUM | NO | `not_run`, `pass`, `fail`, `blocked`, `skipped`. Default: `not_run` |
| `actual_result` | TEXT | YES | What actually happened |
| `evidence_path` | VARCHAR(500) | YES | Screenshot/log file path |
| `notes` | TEXT | YES | |
| `executed_at` | TIMESTAMP | YES | |

**Unique:** (test_execution_id, test_step_id)

---

#### 2.2.11 `defect`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `code` | VARCHAR(15) | NO | Auto: DEF-{seq}. Project-wide. |
| `title` | VARCHAR(500) | NO | |
| `description` | TEXT | NO | Steps to reproduce + details |
| `severity` | ENUM | NO | `S1_showstopper`, `S2_critical`, `S3_major`, `S4_minor`. Default: `S3_major` |
| `priority` | ENUM | NO | `P1_immediate`, `P2_high`, `P3_medium`, `P4_low`. Default: `P3_medium` |
| `status` | ENUM | NO | `new`, `assigned`, `in_progress`, `resolved`, `retest`, `closed`, `reopened`, `deferred`, `rejected`. Default: `new` |
| `category` | ENUM | NO | `functional`, `integration`, `performance`, `configuration`, `data`, `authorization`, `ui`, `documentation`. Default: `functional` |
| `root_cause` | ENUM | YES | `code_error`, `config_error`, `data_issue`, `spec_gap`, `env_issue`, `user_error`, `design_flaw` |
| `test_execution_id` | UUID | YES | FK -> test_execution (where found) |
| `test_case_id` | UUID | YES | FK -> test_case |
| `test_step_id` | UUID | YES | FK -> test_step (specific step) |
| `test_level` | ENUM | YES | Which level found: unit, string, sit, uat, regression, performance |
| `requirement_id` | UUID | YES | FK -> requirement (Explore) |
| `wricef_item_id` | UUID | YES | FK -> wricef_items |
| `config_item_id` | UUID | YES | FK -> config_items |
| `process_level_id` | UUID | YES | FK -> process_level (scope item) |
| `process_area` | VARCHAR(5) | YES | Denormalized |
| `wave` | INTEGER | YES | Denormalized |
| `environment` | ENUM | YES | `dev`, `qas`, `prd`, `sandbox` |
| `assigned_to` | UUID | YES | FK -> user |
| `assigned_to_name` | VARCHAR(100) | YES | |
| `reported_by` | UUID | NO | FK -> user |
| `reported_by_name` | VARCHAR(100) | YES | |
| `resolution` | TEXT | YES | How it was fixed |
| `resolution_type` | ENUM | YES | `code_fix`, `config_change`, `data_correction`, `workaround`, `by_design`, `duplicate`, `cannot_reproduce` |
| `due_date` | DATE | YES | Based on SLA |
| `resolved_at` | TIMESTAMP | YES | |
| `closed_at` | TIMESTAMP | YES | |
| `retest_by` | UUID | YES | FK -> user |
| `retested_at` | TIMESTAMP | YES | |
| `sla_breach` | BOOLEAN | NO | Default: false |
| `alm_defect_id` | VARCHAR(50) | YES | Cloud ALM defect ID |
| `alm_synced` | BOOLEAN | NO | Default: false |
| `created_at` | TIMESTAMP | NO | |
| `updated_at` | TIMESTAMP | NO | |

**Defect Status Lifecycle:**

```
           +-------+
           |  new  | <-- Found during test execution
           +---+---+
               | assign
           +---v------+
           | assigned  |
           +---+------+
               | start_work
           +---v---------+
           | in_progress  |
           +---+---------+
               | resolve
           +---v--------+     +-----------+
           |  resolved  |     |  deferred | (backlog)
           +---+--------+     +-----------+
               | send_to_retest
           +---v------+
           |  retest  |
           +---+------+
          /           \
    pass /             \ fail
   +----v----+    +-----v-----+
   |  closed |    |  reopened | ---> assigned
   +---------+    +-----------+

   Also: new/assigned -> rejected (not a defect)
```

**Indexes:**
- `idx_def_project_status` ON (`project_id`, `status`)
- `idx_def_project_severity` ON (`project_id`, `severity`)
- `idx_def_assigned` ON (`assigned_to`, `status`)
- `idx_def_test_case` ON (`test_case_id`)
- `idx_def_requirement` ON (`requirement_id`)
- `idx_def_wricef` ON (`wricef_item_id`)
- `idx_def_code` UNIQUE ON (`project_id`, `code`)

---

#### 2.2.12 `defect_comment`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `defect_id` | UUID | NO | FK -> defect |
| `user_id` | UUID | NO | FK -> user |
| `type` | ENUM | NO | `comment`, `status_change`, `assignment`, `resolution`, `retest_result` |
| `content` | TEXT | NO | |
| `created_at` | TIMESTAMP | NO | |

---

#### 2.2.13 `defect_history`

Full audit trail of defect field changes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `defect_id` | UUID | NO | FK -> defect |
| `field_changed` | VARCHAR(50) | NO | e.g., `status`, `severity`, `assigned_to` |
| `old_value` | VARCHAR(200) | YES | |
| `new_value` | VARCHAR(200) | NO | |
| `changed_by` | UUID | NO | FK -> user |
| `created_at` | TIMESTAMP | NO | |

---

#### 2.2.14 `defect_link`

Defect-to-defect linking (duplicate, related, caused_by).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `defect_id` | UUID | NO | FK -> defect |
| `linked_defect_id` | UUID | NO | FK -> defect |
| `link_type` | ENUM | NO | `duplicate_of`, `related_to`, `caused_by`, `blocks` |
| `created_at` | TIMESTAMP | NO | |

**Unique:** (defect_id, linked_defect_id)

---

#### 2.2.15 `uat_sign_off`

Business Process Owner sign-off for UAT scenarios.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `test_suite_id` | UUID | NO | FK -> test_suite (UAT suite) |
| `test_cycle_id` | UUID | NO | FK -> test_cycle |
| `scope_item_id` | UUID | YES | FK -> process_level (L3) |
| `process_area` | VARCHAR(5) | YES | |
| `signed_off_by` | UUID | NO | FK -> user (BPO) |
| `signed_off_by_name` | VARCHAR(100) | NO | |
| `sign_off_status` | ENUM | NO | `pending`, `approved`, `approved_with_conditions`, `rejected`. Default: `pending` |
| `conditions` | TEXT | YES | If approved with conditions |
| `usability_score` | INTEGER | YES | 1-5 scale |
| `feedback` | TEXT | YES | BPO comments |
| `signed_at` | TIMESTAMP | YES | |
| `created_at` | TIMESTAMP | NO | |

---

#### 2.2.16 `perf_test_result`

Performance test metrics per execution.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `test_execution_id` | UUID | NO | FK -> test_execution |
| `test_case_id` | UUID | NO | FK -> test_case |
| `concurrent_users` | INTEGER | NO | |
| `avg_response_ms` | INTEGER | NO | Average response time |
| `p95_response_ms` | INTEGER | YES | 95th percentile |
| `p99_response_ms` | INTEGER | YES | 99th percentile |
| `max_response_ms` | INTEGER | YES | |
| `throughput_tps` | DECIMAL | YES | Transactions per second |
| `error_rate_pct` | DECIMAL | YES | Percentage of errors |
| `target_met` | BOOLEAN | NO | avg_response_ms <= target |
| `cpu_usage_pct` | DECIMAL | YES | |
| `memory_usage_pct` | DECIMAL | YES | |
| `notes` | TEXT | YES | |
| `created_at` | TIMESTAMP | NO | |

---

#### 2.2.17 `test_daily_snapshot`

Daily metrics for dashboard trend analysis.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | UUID | NO | PK |
| `project_id` | UUID | NO | FK -> project |
| `snapshot_date` | DATE | NO | |
| `metrics` | JSON | NO | See structure below |
| `created_at` | TIMESTAMP | NO | |

**Unique:** (project_id, snapshot_date)

**Metrics JSON:**
```json
{
  "test_cases": {
    "total": 500, "draft": 30, "ready": 120, "approved": 350,
    "by_level": {
      "unit": 200, "string": 40, "sit": 80, "uat": 100, "regression": 60, "performance": 20
    }
  },
  "executions": {
    "total": 1200, "pass": 950, "fail": 120, "blocked": 30, "not_run": 100,
    "pass_rate": 79.2
  },
  "defects": {
    "total": 180, "new": 12, "assigned": 25, "in_progress": 40,
    "resolved": 35, "retest": 18, "closed": 45, "reopened": 5,
    "open_s1": 0, "open_s2": 3, "sla_breached": 2,
    "opened_today": 8, "closed_today": 6
  },
  "by_wave": {
    "1": { "cases": 200, "pass": 180, "fail": 15, "blocked": 5 },
    "2": { "cases": 150, "pass": 80, "fail": 30, "blocked": 10 }
  },
  "go_no_go": {
    "unit_pass_rate": 97.5,
    "sit_pass_rate": 93.2,
    "uat_happy_path_pass": true,
    "open_s1_s2": 3,
    "open_s3_lte_5": true,
    "regression_pass_rate": 100,
    "perf_targets_met": 95.0,
    "bpo_sign_offs": { "total": 12, "approved": 8, "pending": 4 }
  }
}
```

---

## 3. API Specification

### 3.1 Test Plan API

**GET /api/projects/{projectId}/test-plans**
**GET /api/projects/{projectId}/test-plans/{id}**
**POST /api/projects/{projectId}/test-plans**
**PUT /api/projects/{projectId}/test-plans/{id}**

**POST /api/projects/{projectId}/test-plans/{id}/approve**
Request: { approved_by_id }
Transition: draft -> approved

---

### 3.2 Test Cycle API

**GET /api/projects/{projectId}/test-cycles**
Query params: `test_level`, `wave`, `status`

**POST /api/projects/{projectId}/test-cycles**
**PUT /api/projects/{projectId}/test-cycles/{id}**

**POST /api/projects/{projectId}/test-cycles/{id}/start**
Validation: entry_criteria_met must be true (or override with force=true)
Side effects: status -> in_progress, actual_start = now

**POST /api/projects/{projectId}/test-cycles/{id}/complete**
Validation: checks exit criteria
Side effects: status -> completed, actual_end = now, exit_criteria_met calculated

---

### 3.3 Test Suite API

**GET /api/projects/{projectId}/test-suites**
Query params: `test_level`, `process_area`, `wave`, `scope_item_code`, `e2e_scenario`, `status`, `search`

**POST /api/projects/{projectId}/test-suites**
**PUT /api/projects/{projectId}/test-suites/{id}**

**POST /api/projects/{projectId}/test-suites/{id}/generate-from-wricef**
Auto-generates test cases from linked WRICEF/Config items' unit_test_steps.
Request: { wricef_item_ids: [...], config_item_ids: [...] }

**POST /api/projects/{projectId}/test-suites/{id}/generate-from-process**
Auto-generates SIT/UAT test cases from Explore Phase L3/L4 process steps.
Request: { scope_item_ids: [...], uat_categories: [...] }

**GET /api/projects/{projectId}/test-suites/{id}/stats**
Returns: total_cases, by_status, by_priority, pass_rate, defect_count

---

### 3.4 Test Case API

**GET /api/projects/{projectId}/test-cases**
Query params: `test_suite_id`, `test_level`, `priority`, `status`, `process_area`, `wave`, `requirement_id`, `wricef_item_id`, `uat_category`, `regression_risk`, `automation_status`, `search`, `sort_by`, `page`, `per_page`

**GET /api/projects/{projectId}/test-cases/{id}**
Full detail: steps, execution history, linked defects, traceability.

**POST /api/projects/{projectId}/test-cases**
**PUT /api/projects/{projectId}/test-cases/{id}**

**POST /api/projects/{projectId}/test-cases/{id}/steps**
Batch create/update steps.
Request: { steps: [{ step_number, action, expected_result, test_data, sap_transaction }] }

**POST /api/projects/{projectId}/test-cases/{id}/clone**
Create copy with new code. Useful for regression suite building.

**POST /api/projects/{projectId}/test-cases/{id}/approve**
Transition: draft -> ready -> approved.

---

### 3.5 Test Execution API

**POST /api/projects/{projectId}/test-runs**
Create a test run within a cycle.
Request: { test_cycle_id, name, environment, test_case_ids: [...] }
Creates test_execution records for each case (status: not_run).

**POST /api/projects/{projectId}/test-runs/{runId}/start**
Status: not_started -> in_progress, started_at = now.

**GET /api/projects/{projectId}/test-runs/{runId}/executions**
All executions in this run with status.

**PUT /api/projects/{projectId}/test-executions/{id}**
Update execution status and step results.
Request:
```json
{
  "status": "pass" | "fail" | "blocked" | "skipped",
  "notes": "...",
  "step_results": [
    {
      "test_step_id": "uuid",
      "status": "pass" | "fail" | "blocked",
      "actual_result": "...",
      "evidence_path": "..."
    }
  ]
}
```

Side effects:
- If any step fails → execution status = fail
- If status = fail → prompt defect creation
- Updates test_daily_snapshot metrics

**POST /api/projects/{projectId}/test-executions/{id}/create-defect**
Auto-creates defect linked to this execution, case, and failed step.
Auto-populates: requirement_id, wricef/config, process_area, wave from test case.

**POST /api/projects/{projectId}/test-runs/{runId}/complete**

---

### 3.6 Defect API

**GET /api/projects/{projectId}/defects**
Query params: `status`, `severity`, `priority`, `category`, `test_level`, `process_area`, `wave`, `assigned_to`, `reported_by`, `overdue`, `sla_breach`, `search`, `sort_by`, `page`, `per_page`

**GET /api/projects/{projectId}/defects/{id}**
Full detail: comments, history, linked defects, execution source, traceability.

**POST /api/projects/{projectId}/defects**
**PUT /api/projects/{projectId}/defects/{id}**

**POST /api/projects/{projectId}/defects/{id}/transition**
Request: { action, comment, assigned_to (for assign), resolution, resolution_type (for resolve) }

Valid transitions:

| Action | From | To | Required Fields |
|--------|------|----|----------------|
| assign | new, reopened | assigned | assigned_to |
| start_work | assigned | in_progress | — |
| resolve | in_progress | resolved | resolution, resolution_type |
| send_to_retest | resolved | retest | — |
| pass_retest | retest | closed | retest_by |
| fail_retest | retest | reopened | comment |
| defer | new, assigned, in_progress | deferred | comment |
| reject | new, assigned | rejected | comment |
| reopen | closed, deferred | reopened | comment |

Side effects:
- assign → calculate due_date from SLA (severity + priority)
- resolve → set resolved_at
- pass_retest → set closed_at, retested_at, retest_by
- fail_retest → increment execution_number on related test execution
- Any transition → defect_history record + defect_comment record

**POST /api/projects/{projectId}/defects/{id}/comments**
**GET /api/projects/{projectId}/defects/{id}/history**

**POST /api/projects/{projectId}/defects/{id}/link**
Request: { linked_defect_id, link_type }

**GET /api/projects/{projectId}/defects/stats**
Returns: by_status, by_severity, by_priority, by_category, by_level, by_area, open_count, sla_breach_count, avg_resolution_days, defect_density (defects per test case), daily_open_close_rate

---

### 3.7 UAT Sign-Off API

**GET /api/projects/{projectId}/uat-sign-offs**
Query params: `test_cycle_id`, `process_area`, `sign_off_status`

**POST /api/projects/{projectId}/uat-sign-offs**
Request: { test_suite_id, test_cycle_id, scope_item_id, sign_off_status, conditions, usability_score, feedback }

Only users with `bpo` or `pm` role can create sign-offs.

---

### 3.8 Performance Test API

**GET /api/projects/{projectId}/perf-results**
Query params: `test_case_id`, `target_met`

**POST /api/projects/{projectId}/perf-results**
Auto-created when performance test execution is completed.

---

### 3.9 Dashboard & Reporting API

**GET /api/projects/{projectId}/test-dashboard**
Returns: current aggregated metrics (not from snapshot — real-time).

**GET /api/projects/{projectId}/test-dashboard/trends**
Query params: `date_from`, `date_to`
Returns: array of daily snapshots for trend charts.

**GET /api/projects/{projectId}/test-dashboard/go-no-go**
Returns: structured scorecard with all criteria and pass/fail status.

**GET /api/projects/{projectId}/test-dashboard/traceability-matrix**
Returns: REQ → WRICEF/Config → TestCase → Execution → Defect cross-reference.
Query params: `process_area`, `wave`, `scope_item_code`

**POST /api/projects/{projectId}/test-dashboard/export**
Request: { format: "pptx" | "pdf" | "xlsx", report_type: "progress" | "go_no_go" | "defect_analysis" | "traceability" }

---

### 3.10 Cloud ALM Test Sync API

**POST /api/projects/{projectId}/test-cases/{id}/sync-to-alm**
Push test case to Cloud ALM.

**POST /api/projects/{projectId}/test-cases/bulk-sync-alm**
Request: { test_case_ids: [...] }

**POST /api/projects/{projectId}/defects/{id}/sync-to-alm**
Push defect to Cloud ALM.

**POST /api/projects/{projectId}/test-executions/{id}/sync-result-to-alm**
Push execution result.

---

## 4. Frontend Component Specification

### 4.1 Module T1: Test Plan & Strategy

**Route:** `/projects/{id}/testing/plan`

**State:**
```typescript
interface TestPlanState {
  activeTab: 'strategy' | 'calendar' | 'environments' | 'criteria';
  selectedCycleId: string | null;
}
```

**Components:**
| Component | Description |
|-----------|-------------|
| TestPlanHeader | Plan name, version, status, approve button |
| StrategyEditor | Markdown editor for strategy document |
| TestCalendar | Gantt-like view of test cycles across timeline |
| EnvironmentMatrix | Table: environment × level → configuration |
| EntryCriteria | Per-level entry criteria checklist |
| ExitCriteria | Per-level exit criteria with current status indicators |

---

### 4.2 Module T2: Test Suite Manager

**Route:** `/projects/{id}/testing/suites`

**State:**
```typescript
interface TestSuiteState {
  viewMode: 'table' | 'by_level';
  filters: {
    search: string;
    testLevel: TestLevel | 'all';
    processArea: string;
    wave: number;
    status: string;
    e2eScenario: string;
  };
  selectedSuiteId: string | null;
  selectedCaseId: string | null;
}
```

**Components:**
| Component | Description |
|-----------|-------------|
| SuiteLevelTabs | 6 tabs: Unit, String, SIT, UAT, Regression, Performance |
| SuiteTable | Sortable: code, name, area, wave, case count, pass rate |
| TestCaseTable | Within suite: code, title, priority, status, automation, traceability links |
| TestCaseDetail | Expandable: steps, preconditions, test data, execution history, defects |
| TestStepEditor | Inline step editing with action/expected/data/transaction fields |
| GenerateFromWRICEF | Dialog: select WRICEF/Config items → auto-generate cases |
| GenerateFromProcess | Dialog: select scope items → auto-generate SIT/UAT cases |
| TraceabilityBadge | Shows REQ → WRICEF → TestCase chain |
| SuiteKpiStrip | Total cases, ready, approved, pass rate |

---

### 4.3 Module T3: Test Execution

**Route:** `/projects/{id}/testing/execution`

**State:**
```typescript
interface TestExecutionState {
  selectedCycleId: string | null;
  selectedRunId: string | null;
  activeExecutionId: string | null;
  stepResults: Map<string, StepResultInput>;
}
```

**Components:**
| Component | Description |
|-----------|-------------|
| CycleSelector | Dropdown: active cycles |
| RunList | Runs within cycle: code, name, env, status, progress bar |
| ExecutionGrid | Cases in run: code, title, status badge, executed_by, duration |
| ExecutionWorkspace | Active test execution: case info + step-by-step runner |
| StepRunner | Sequential steps: action, expected, data, T-code. Per step: pass/fail/blocked + actual result + evidence upload |
| DefectQuickCreate | Auto-populated from failed step, inline defect creation |
| ExecutionProgress | Circular/bar progress: pass/fail/blocked/remaining |
| EvidenceUploader | Screenshot/file upload attached to step result |

---

### 4.4 Module T4: Defect Tracker

**Route:** `/projects/{id}/testing/defects`

**State:**
```typescript
interface DefectTrackerState {
  viewMode: 'table' | 'kanban';
  filters: {
    search: string;
    status: string;
    severity: string;
    priority: string;
    category: string;
    testLevel: string;
    processArea: string;
    assignedTo: string;
    overdue: boolean;
    slaBreach: boolean;
  };
  groupBy: 'status' | 'severity' | 'priority' | 'area' | 'assignee' | 'level' | 'none';
  selectedDefectId: string | null;
}
```

**Components:**
| Component | Description |
|-----------|-------------|
| DefectTable | Sortable/groupable: code, severity pill, priority pill, title, status, assigned, age, SLA indicator |
| DefectKanban | Columns: New, Assigned, In Progress, Resolved, Retest, Closed |
| DefectDetail | Full view: description, source test case, traceability, comments, history, linked defects |
| DefectForm | Create/edit: title, description, severity, priority, category, assignment |
| DefectTimeline | Activity log: comments, status changes, reassignments |
| SLAIndicator | Green (on track), yellow (warning), red (breached) |
| DefectKpiStrip | Open, S1/S2 open, SLA breached, avg resolution days, defect density |

---

### 4.5 Module T5: Test Dashboard

**Route:** `/projects/{id}/testing/dashboard`

**Components:**
| Widget | Type | Question Answered |
|--------|------|-------------------|
| Test Execution Progress | Stacked bar per level | How much testing is done? |
| Pass Rate Trend | Line chart over time | Is quality improving? |
| Defect Open/Close Rate | Dual line chart | Are we closing faster than opening? |
| Defect Funnel | Horizontal funnel | Where are defects stuck? |
| Severity Distribution | Donut chart | How critical are our defects? |
| Defect Aging | Bar chart (0-3d, 4-7d, 8-14d, 15+d) | How old are open defects? |
| Test Coverage Map | Heatmap (area × level) | What's tested, what's not? |
| Go/No-Go Scorecard | Checklist with green/red | Are we ready for go-live? |
| Wave Readiness | Multi-bar per wave | Which wave is ready? |
| Top 10 Open Defects | Table | What needs attention now? |

---

### 4.6 Module T6: Traceability Matrix

**Route:** `/projects/{id}/testing/traceability`

**Components:**
| Component | Description |
|-----------|-------------|
| TraceabilityTable | Columns: Requirement → WRICEF/Config → Test Cases → Executions (last result) → Defects (open count) |
| CoverageIndicator | Green (tested+pass), Yellow (tested+issues), Red (not tested), Gray (no test case) |
| GapHighlight | Rows with no test case or no execution highlighted |
| FilterBar | Area, wave, scope item, test level |
| ExportButton | Excel/PDF export of full matrix |

---

## 5. Business Rules

### 5.1 Test Level Dependencies

```
Unit Test PASS ──► String Test eligible
String Test PASS ──► SIT eligible
SIT PASS ──► UAT eligible
UAT PASS + Sign-off ──► Go-Live eligible

Regression: runs parallel, triggered by any change
Performance: runs parallel, typically during SIT/UAT
```

Dependency enforcement: configurable (strict vs. warning-only).

### 5.2 Test Case Generation from Explore Phase

**Unit Test from WRICEF/Config:**
1. Read WRICEF/Config item's `unit_test_steps` (JSON array from existing model)
2. For each step → create test_step record
3. Set test_case.requirement_id from WRICEF/Config's source requirement
4. Set traceability fields (process_area, wave, scope_item)

**SIT from Process Steps:**
1. For each E2E scenario (O2C, P2P, etc.) → create test_suite
2. From Explore's process_steps across multiple workshops → create sequential test_steps
3. Each step includes: L4 process name, SAP transaction, expected outcome
4. Interface points get special checkpoint steps (is_checkpoint = true)

**UAT from Workshop Decisions:**
1. For each L3 scope item → create UAT test_suite
2. Happy Path: process steps where fit_decision = 'fit' → standard flow test
3. Exception: process steps where fit_decision = 'partial_fit' → exception scenarios
4. Negative: derive from workshop decisions and business rules

### 5.3 Defect SLA Calculation

```
SLA_HOURS = {
  "S1+P1": { response: 1, resolution: 4 },
  "S1+P2": { response: 2, resolution: 8 },
  "S2+P1": { response: 2, resolution: 8 },
  "S2+P2": { response: 4, resolution: 24 },
  "S3+P3": { response: 8, resolution: 72 },
  "S4+P4": { response: 16, resolution: 120 }
}
```

SLA timer starts at assignment. Paused when status = deferred. sla_breach = true when current_time > assigned_at + resolution_hours.

### 5.4 Go/No-Go Scorecard Rules

| Criterion | Formula | Target |
|-----------|---------|--------|
| Unit Test Pass Rate | unit_pass / unit_total * 100 | ≥ 95% |
| SIT Pass Rate | sit_pass / sit_total * 100 | ≥ 95% |
| UAT Happy Path | All happy_path cases pass | 100% |
| UAT BPO Sign-Off | All required sign-offs approved | 100% |
| Open S1 Defects | Count where severity=S1, status NOT IN (closed, rejected, deferred) | = 0 |
| Open S2 Defects | Count where severity=S2, status NOT IN (closed, rejected, deferred) | = 0 |
| Open S3 Defects | Count where severity=S3, status NOT IN (closed, rejected, deferred) | ≤ 5 |
| Regression Suite | regression_pass / regression_total * 100 | 100% |
| Performance Targets | perf_target_met / perf_total * 100 | ≥ 95% |
| All Critical Defects Closed | S1+S2 defects with status=closed | 100% |

### 5.5 Code Generation

```
Test Cycle:    TC-{seq}         (project-wide, 3-digit)
Test Suite:    TS-{level}-{seq} (per level, 3-digit)
Test Case:     {level}-{seq}    (per level, 3-digit)
Test Run:      TR-{seq}         (project-wide, 3-digit)
Defect:        DEF-{seq}        (project-wide, 4-digit)
```

Level prefixes: UT, ST, SIT, UAT, REG, PRF

### 5.6 Test Execution Status Calculation

```
IF all steps pass → execution = pass
IF any step fails → execution = fail
IF any step blocked AND no step failed → execution = blocked
IF no steps executed → execution = not_run
```

### 5.7 Regression Risk Assignment

When a WRICEF/Config item is changed (defect fix, enhancement):
1. Find all test cases linked to that item
2. Find all test cases in the same process area
3. Assign risk: `critical` if same item, `high` if same area, `medium` if dependent area, `low` otherwise
4. Build regression suite from critical + high risk cases (mandatory) + medium (recommended)

---

## 6. Enumerations

```typescript
type TestLevel = 'unit' | 'string' | 'sit' | 'uat' | 'regression' | 'performance';

type TestPlanStatus = 'draft' | 'approved' | 'active' | 'completed';
type TestCycleStatus = 'planned' | 'in_progress' | 'completed' | 'aborted';
type TestSuiteStatus = 'draft' | 'ready' | 'in_progress' | 'completed';
type TestCaseStatus = 'draft' | 'ready' | 'approved' | 'deprecated';
type TestRunStatus = 'not_started' | 'in_progress' | 'completed' | 'aborted';
type ExecutionStatus = 'not_run' | 'in_progress' | 'pass' | 'fail' | 'blocked' | 'skipped';
type StepResultStatus = 'not_run' | 'pass' | 'fail' | 'blocked' | 'skipped';

type AutomationStatus = 'manual' | 'partial' | 'automated' | 'to_automate';
type TestEnvironment = 'dev' | 'qas' | 'prd' | 'sandbox';

type UATCategory = 'happy_path' | 'exception' | 'negative' | 'day_in_life' | 'period_end';
type RegressionRisk = 'critical' | 'high' | 'medium' | 'low';
type PerfTestType = 'load' | 'stress' | 'volume' | 'endurance' | 'spike';

type DefectStatus = 'new' | 'assigned' | 'in_progress' | 'resolved' | 'retest' | 'closed' | 'reopened' | 'deferred' | 'rejected';
type DefectSeverity = 'S1_showstopper' | 'S2_critical' | 'S3_major' | 'S4_minor';
type DefectPriority = 'P1_immediate' | 'P2_high' | 'P3_medium' | 'P4_low';
type DefectCategory = 'functional' | 'integration' | 'performance' | 'configuration' | 'data' | 'authorization' | 'ui' | 'documentation';
type RootCause = 'code_error' | 'config_error' | 'data_issue' | 'spec_gap' | 'env_issue' | 'user_error' | 'design_flaw';
type ResolutionType = 'code_fix' | 'config_change' | 'data_correction' | 'workaround' | 'by_design' | 'duplicate' | 'cannot_reproduce';
type DefectLinkType = 'duplicate_of' | 'related_to' | 'caused_by' | 'blocks';

type SignOffStatus = 'pending' | 'approved' | 'approved_with_conditions' | 'rejected';

type TestCaseDependencyType = 'must_pass' | 'must_run' | 'data_dependency';
```

---

## 7. Integration Points

### 7.1 Explore Phase Integration

| Explore Entity | Test Management Usage | FK |
|---------------|----------------------|-----|
| requirement | Source traceability for test cases | test_case.requirement_id |
| wricef_items | Unit test case source + defect link | test_case.wricef_item_id |
| config_items | Unit test case source + defect link | test_case.config_item_id |
| process_level (L3) | Scope item context for suites and defects | test_suite.scope_item_id, test_case.process_level_id |
| process_level (L4) | SIT/UAT step derivation | via process_step |
| process_step | Test step generation (fit decisions, notes) | Queried during generation |
| decision | Test acceptance criteria source | Referenced in test_data |
| workshop | Source context for UAT scenarios | Referenced in description |

### 7.2 Cloud ALM Sync

| ProjektCoPilot Entity | Direction | Cloud ALM Entity |
|----------------------|-----------|-----------------|
| test_case | Push → | ALM Test Case |
| test_step | Push → | ALM Test Step |
| test_execution | Push → | ALM Test Run Result |
| defect | Bidirectional ↔ | ALM Defect |

**Field Mapping — Test Case:**
| ProjektCoPilot | Cloud ALM |
|---------------|-----------|
| code | External Reference |
| title | Summary |
| description | Description |
| priority | Priority |
| test_level | Test Type |
| process_area | Process Area Tag |
| steps[].action | Step Action |
| steps[].expected_result | Step Expected Result |

**Field Mapping — Defect:**
| ProjektCoPilot | Cloud ALM |
|---------------|-----------|
| code | External Reference |
| title | Summary |
| description | Description |
| severity | Severity |
| priority | Priority |
| status | Status (mapped) |
| category | Category |
| resolution | Resolution |

### 7.3 Existing ProjektCoPilot Modules

- `project` table → project_id FK
- `user` table → executed_by, assigned_to, reported_by
- `wricef_items` table → unit_test_steps field used for test case generation
- `config_items` table → unit_test_steps field used for test case generation
- `attachment` table (from Explore v1.1) → reused for test evidence

---

## 8. Performance Considerations

### 8.1 Expected Data Volumes

| Entity | Expected per Project |
|--------|---------------------|
| Test Plan | 1 |
| Test Cycle | 10-20 |
| Test Suite | 30-80 |
| Test Case | 300-800 |
| Test Step | 2000-6000 |
| Test Run | 50-200 |
| Test Execution | 2000-8000 |
| Test Step Result | 15000-50000 |
| Defect | 100-500 |
| Defect Comment | 500-2000 |
| UAT Sign-Off | 20-60 |
| Perf Test Result | 50-200 |

### 8.2 Query Optimization

1. **Execution status aggregation**: Materialized view or cached counts per suite/cycle
2. **Defect stats**: Indexed on (project_id, status, severity) for fast scorecard queries
3. **Traceability matrix**: Pre-computed join or view: requirement → test_case → last_execution → open_defects
4. **Step results**: Indexed on (test_execution_id) for fast execution detail loading
5. **Daily snapshot**: Prevents expensive real-time aggregation for trend charts

---

## 9. UI/UX Design Tokens (Test Management Extension)

```typescript
const TestDesignTokens = {
  // Extends Explore Phase tokens

  // Test level colors
  levelColors: {
    unit: "#8B5CF6",       // Purple
    string: "#06B6D4",     // Cyan
    sit: "#3B82F6",        // Blue
    uat: "#10B981",        // Green
    regression: "#F59E0B", // Amber
    performance: "#EF4444" // Red
  },

  // Execution status
  executionColors: {
    pass: "#10B981",    // Green
    fail: "#EF4444",    // Red
    blocked: "#F59E0B", // Amber
    not_run: "#64748B", // Gray
    skipped: "#94A3B8", // Light gray
    in_progress: "#3B82F6" // Blue
  },

  // Defect severity
  severityColors: {
    S1: "#EF4444",  // Red — showstopper
    S2: "#F97316",  // Orange — critical
    S3: "#F59E0B",  // Amber — major
    S4: "#64748B"   // Gray — minor
  },

  // SLA status
  slaColors: {
    on_track: "#10B981",
    warning: "#F59E0B",
    breached: "#EF4444"
  },

  // Go/No-Go
  goNoGo: {
    go: "#10B981",
    no_go: "#EF4444",
    conditional: "#F59E0B"
  }
};
```

---

## 10. File Structure

```
src/
  modules/
    testing/
      api/
        testPlanApi.ts
        testCycleApi.ts
        testSuiteApi.ts
        testCaseApi.ts
        testExecutionApi.ts
        defectApi.ts
        uatSignOffApi.ts
        perfResultApi.ts
        dashboardApi.ts
        almSyncApi.ts
        types.ts
      components/
        plan/
          TestPlanHeader.tsx
          StrategyEditor.tsx
          TestCalendar.tsx
          EnvironmentMatrix.tsx
          EntryCriteria.tsx
          ExitCriteria.tsx
        suites/
          SuiteLevelTabs.tsx
          SuiteTable.tsx
          TestCaseTable.tsx
          TestCaseDetail.tsx
          TestStepEditor.tsx
          GenerateFromWRICEF.tsx
          GenerateFromProcess.tsx
          TraceabilityBadge.tsx
          SuiteKpiStrip.tsx
        execution/
          CycleSelector.tsx
          RunList.tsx
          ExecutionGrid.tsx
          ExecutionWorkspace.tsx
          StepRunner.tsx
          DefectQuickCreate.tsx
          ExecutionProgress.tsx
          EvidenceUploader.tsx
        defects/
          DefectTable.tsx
          DefectKanban.tsx
          DefectDetail.tsx
          DefectForm.tsx
          DefectTimeline.tsx
          SLAIndicator.tsx
          DefectKpiStrip.tsx
        dashboard/
          TestExecutionProgress.tsx
          PassRateTrend.tsx
          DefectOpenCloseRate.tsx
          DefectFunnel.tsx
          SeverityDistribution.tsx
          DefectAging.tsx
          TestCoverageMap.tsx
          GoNoGoScorecard.tsx
          WaveReadiness.tsx
          TopOpenDefects.tsx
        traceability/
          TraceabilityTable.tsx
          CoverageIndicator.tsx
          GapHighlight.tsx
        shared/
          TestLevelBadge.tsx
          SeverityPill.tsx
          PriorityPill.tsx
          StatusBadge.tsx
          PassFailBar.tsx
      hooks/
        useTestPlan.ts
        useTestSuites.ts
        useTestCases.ts
        useTestExecution.ts
        useDefects.ts
        useDashboard.ts
        useTraceability.ts
      pages/
        TestPlanPage.tsx         # Module T1
        TestSuiteManagerPage.tsx # Module T2
        TestExecutionPage.tsx    # Module T3
        DefectTrackerPage.tsx    # Module T4
        TestDashboardPage.tsx    # Module T5
        TraceabilityPage.tsx     # Module T6
      utils/
        slaCalculations.ts
        goNoGoEvaluator.ts
        testCaseGenerator.ts
        codeGenerators.ts
        statusTransitions.ts
  models/
    testPlan.ts
    testCycle.ts
    testCycleSuite.ts
    testSuite.ts
    testCase.ts
    testStep.ts
    testCaseDependency.ts
    testRun.ts
    testExecution.ts
    testStepResult.ts
    defect.ts
    defectComment.ts
    defectHistory.ts
    defectLink.ts
    uatSignOff.ts
    perfTestResult.ts
    testDailySnapshot.ts
  migrations/
    20260210_test_management_tables.ts
```

---

## 11. Role Permissions (Test Management Extension)

Extends Explore Phase project_role system.

| Action | PM | Module Lead | Facilitator | BPO | Tech Lead | Tester | Test Lead | Viewer |
|--------|:--:|:----------:|:----------:|:---:|:---------:|:------:|:---------:|:------:|
| Test Plan: create/edit | ✓ | — | — | — | — | — | ✓ | — |
| Test Plan: approve | ✓ | — | — | — | — | — | — | — |
| Test Suite: create/edit | ✓ | ✓ (own area) | — | — | — | — | ✓ | — |
| Test Case: create/edit | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — |
| Test Case: approve | ✓ | ✓ (own area) | — | — | — | — | ✓ | — |
| Test Execution: run | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Defect: create | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Defect: assign | ✓ | ✓ (own area) | — | — | — | — | ✓ | — |
| Defect: resolve | ✓ | ✓ | ✓ | — | ✓ | — | — | — |
| Defect: retest | ✓ | ✓ | — | — | — | ✓ | ✓ | — |
| Defect: close | ✓ | ✓ | — | — | — | — | ✓ | — |
| UAT: sign-off | ✓ | — | — | ✓ | — | — | — | — |
| Go/No-Go: view | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Dashboard: export | ✓ | ✓ | — | ✓ | — | — | ✓ | — |

**New role: `test_lead`** — manages test plan, suites, cycles, defect triage, go/no-go assessment.

---

## 12. Data Model Summary

### Test Management Tables (17)
1. test_plan
2. test_cycle
3. test_cycle_suite
4. test_suite
5. test_case
6. test_step
7. test_case_dependency
8. test_run
9. test_execution
10. test_step_result
11. defect
12. defect_comment
13. defect_history
14. defect_link
15. uat_sign_off
16. perf_test_result
17. test_daily_snapshot

### Explore Phase Tables Referenced (from v1.1)
- project, user, project_role
- requirement, wricef_items, config_items
- process_level, process_step
- attachment (reused for evidence)

**Combined Total: 24 (Explore) + 17 (Test) = 41 tables**

---

## 13. Acceptance Criteria

### Module T1 — Test Plan & Strategy
- [ ] Create and edit test plan with strategy document
- [ ] Define entry/exit criteria per test level
- [ ] Test calendar with cycle timeline view
- [ ] Environment matrix
- [ ] Plan approval workflow

### Module T2 — Test Suite Manager
- [ ] 6-level tab navigation (Unit, String, SIT, UAT, Regression, Performance)
- [ ] Suite CRUD with area/wave/scenario filtering
- [ ] Test case CRUD with step editing
- [ ] Auto-generate unit tests from WRICEF/Config items
- [ ] Auto-generate SIT/UAT tests from Explore process steps
- [ ] Test case approval workflow
- [ ] Clone test case for regression suite building
- [ ] Traceability badges showing REQ → WRICEF → TestCase chain

### Module T3 — Test Execution
- [ ] Create test runs within cycles
- [ ] Step-by-step execution with pass/fail/blocked per step
- [ ] Actual result and evidence upload per step
- [ ] Auto-create defect from failed step
- [ ] Execution progress visualization
- [ ] Multiple execution attempts (retest support)

### Module T4 — Defect Tracker
- [ ] Defect CRUD with full lifecycle (9 statuses)
- [ ] Severity/Priority classification
- [ ] SLA calculation and breach tracking
- [ ] Assignment and reassignment
- [ ] Resolution with root cause and resolution type
- [ ] Retest workflow (resolve → retest → close/reopen)
- [ ] Activity timeline (comments + history)
- [ ] Defect linking (duplicate, related, caused_by, blocks)
- [ ] Table and Kanban views
- [ ] Traceability to test case, requirement, WRICEF

### Module T5 — Test Dashboard
- [ ] 10 dashboard widgets
- [ ] Go/No-Go Scorecard with all criteria
- [ ] Trend analysis from daily snapshots
- [ ] Export to PPTX/PDF/XLSX
- [ ] Drill-down from any metric to detail view

### Module T6 — Traceability Matrix
- [ ] Full chain: REQ → WRICEF/Config → Test Case → Execution → Defect
- [ ] Coverage gap highlighting
- [ ] Filter by area, wave, scope item
- [ ] Export

### Cloud ALM Integration
- [ ] Push test cases to ALM
- [ ] Push execution results to ALM
- [ ] Bidirectional defect sync
- [ ] Bulk sync support

---

*Document Version: 1.0*
*Created: 2026-02-10*
*Author: ProjektCoPilot Development Team*
*Companion to: Explore Phase FS/TS v1.1*
