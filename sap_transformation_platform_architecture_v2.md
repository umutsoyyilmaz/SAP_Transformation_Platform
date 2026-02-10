# SAP Transformation Management Platform — Uygulama Mimarisi

**Versiyon:** 2.1  
**Tarih:** 2026-02-10  
**Hazırlayan:** Umut Soyyılmaz  
**Kaynak:** SAP Transformation PM Playbook (S/4HANA + Public Cloud)

### Revizyon Geçmişi

| Versiyon | Tarih | Değişiklik |
|----------|-------|------------|
| 2.0 | 2026-02-10 | İlk v2 yayın — Explore Phase (24 tablo) + Test Management FS/TS v1.0 (17 tablo hedef) entegre |
| 2.1 | 2026-02-10 | **[REVISED]** Test Management bölümü codebase ile senkronize edildi. Mevcut implementasyon: 5 tablo, 28 route. Kalan 12 tablo Phase 3 roadmap'ine taşındı. Modül 4.6 ve API bölümü güncellendi. Implementation Status bölümü eklendi. |

**v2.1 Değişiklik Özeti:**
- Scope & Requirements Domain → Explore Phase FS/TS v1.1 ile entegre (24 tablo, 50+ API endpoint) — **tam implement**
- Test Hub Domain → Temel CRUD implement (5 tablo, 28 route). FS/TS v1.0 hedef (17 tablo, 40+ endpoint) Phase 3'te tamamlanacak
- Domain Model → Mevcut: **29 tablo** (Explore 24 + Test Management 5). Hedef: 41 tablo (+ Test Management kalan 12)
- Traceability zinciri Requirement→TestCase→TestExecution→Defect olarak çalışır durumda
- Modül Mimarisi Bölüm 4.6 mevcut implementasyonu yansıtacak şekilde güncellendi
- API yapısı gerçek route'larla senkronize edildi
- Implementation Status bölümü eklendi (implement edilen vs planlanan tablo/feature ayrımı)

---

## 1. Vizyon ve Tasarım İlkeleri

### 1.1 Amaç

SAP dönüşüm programlarının (Greenfield, Brownfield, Selective, Public Cloud) uçtan uca yönetimi, takibi ve raporlanması için tek bir platform. Playbook'taki şu akışı dijitalleştirir:

```
Project → Scenario → Analysis → Requirement (Fit/Partial Fit/Gap)
    → WRICEF Item / Configuration Item → FS/TS → Unit Evidence
    → SIT/UAT Test Cases → Defects → Cutover Tasks → Hypercare Incidents/RFC
```

### 1.2 Tasarım İlkeleri

| # | İlke | Açıklama |
|---|-------|----------|
| 1 | **Traceability-First** | Her artefact, üst ve alt seviyeye izlenebilir olmalı (requirement → test case → defect → cutover task) |
| 2 | **Phase-Gate Driven** | SAP Activate fazları ve kalite-gate'leri platformun omurgasını oluşturur |
| 3 | **Workstream-Centric** | Her modül workstream bazlı filtrelenebilir, raporlanabilir |
| 4 | **Configurable, Not Custom** | Proje tipi (Greenfield/Brownfield/Selective/Cloud) seçimine göre modüller ve şablonlar otomatik adapte olur |
| 5 | **Dashboard-Native** | Her modülün kendi KPI seti ve görsel dashboard'u olmalı |
| 6 | **Minimum Standart + Genişletilebilir** | Temel yapı sabittir; kurum ölçeğine göre alanlar, workflow'lar, raporlar eklenebilir |
| 7 | **Offline-Capable** | Kritik workstream verileri offline erişilebilir, senkronize edilebilir |

---

## 2. Üst Seviye Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────────┐ │
│  │ Web App  │ │ Mobile   │ │ Executive│ │ External Portal        │ │
│  │ (SPA)    │ │ (PWA)    │ │ Dashboard│ │ (Vendor/Client Access) │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────────┐
│                         API GATEWAY                                 │
│  Auth / Rate Limiting / Versioning / Audit Logging                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │
│  │ Program     │ │ Explore     │ │ Backlog     │ │ Integration  │ │
│  │ Setup       │ │ Phase Mgr   │ │ Workbench   │ │ Factory      │ │
│  │ Service     │ │ Service     │ │ Service     │ │ Service      │ │
│  │             │ │ (24 tables) │ │             │ │              │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘ │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │
│  │ Data        │ │ Test Mgmt   │ │ Cutover     │ │ Run/Sustain  │ │
│  │ Factory     │ │ System      │ │ Hub Service │ │ Service      │ │
│  │ Service     │ │ (17 tables) │ │             │ │              │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘ │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │
│  │ RAID        │ │ Reporting   │ │ Notification│ │ AI/Analytics │ │
│  │ Service     │ │ Engine      │ │ Service     │ │ Service      │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘ │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────────┐
│                        DATA LAYER                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────────┐ │
│  │ Primary  │ │ Document │ │ Cache    │ │ Event Store /          │ │
│  │ DB       │ │ Store    │ │ (Redis)  │ │ Audit Log              │ │
│  │(Postgres)│ │ (S3/Blob)│ │          │ │                        │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Domain Model (Veri Modeli)

### 3.1 Core Entity İlişki Diyagramı

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PROGRAM SETUP DOMAIN                           │
│                                                                         │
│  Organization ──1:N──▶ Program ──1:N──▶ Project                        │
│                                           │                             │
│                                           ├──1:N──▶ Phase (Activate)   │
│                                           │           └──1:1──▶ Gate   │
│                                           ├──1:N──▶ Workstream         │
│                                           ├──1:N──▶ Team Member (RACI) │
│                                           └──1:N──▶ Committee          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                EXPLORE PHASE DOMAIN (FS/TS v1.1 — 24 tablo)                    │
│                                                                                  │
│  ► Detay: explore-phase-fs-ts.md                                                │
│                                                                                  │
│  Project ──1:N──▶ process_level (4 seviyeli hiyerarşi)                         │
│                     ├── L1: Value Chain (Core, Management, Support)              │
│                     ├── L2: Process Area (FI, SD, MM, PP, QM...)               │
│                     ├── L3: Scope Item (J58, BD9, J45... SAP BP)               │
│                     │   ├── scope_status: in_scope | out_of_scope | under_review│
│                     │   └── wave: 1, 2, 3, 4                                   │
│                     └── L4: Sub-Process (J58.01, J58.02...)                     │
│                           └── l4_seed_catalog (3 seeding mode)                  │
│                                                                                  │
│  process_level (L3) ──1:N──▶ workshop                                          │
│    ├── workshop_attendee (1:N)                                                  │
│    ├── workshop_agenda_item (1:N)                                               │
│    ├── workshop_scope_item (N:M — workshop ↔ L3)                               │
│    ├── workshop_dependency (N:M — 4 bağımlılık tipi)                           │
│    ├── workshop_document (1:N — meeting minutes)                                │
│    └── workshop_revision_log (1:N — reopen audit)                              │
│                                                                                  │
│  workshop ──1:N──▶ process_step (L4 evaluation in workshop context)             │
│    ├── fit_decision: fit | partial_fit | gap | null                              │
│    ├── discussion_notes, bpmn_reference                                         │
│    ├── multi-session: previous_session_step_id, carried_from_session            │
│    ├── ──1:N──▶ decision (category: process|technical|scope|org|data)           │
│    ├── ──1:N──▶ open_item (priority: P1-P4, lifecycle: 5 status)               │
│    │              └── open_item_comment (1:N)                                   │
│    ├── ──1:N──▶ requirement                                                     │
│    │   ├── status: draft→under_review→approved→in_backlog→realized→verified     │
│    │   ├── type: development|configuration|integration|migration|enhancement    │
│    │   ├── requirement_dependency (N:M)                                         │
│    │   ├── requirement_open_item_link (N:M — blocking relationship)            │
│    │   └── ──1:1──▶ WRICEF Item  (Gap/Partial → development)                  │
│    │       ──1:1──▶ Config Item  (Fit/Partial → configuration)                 │
│    └── ──1:N──▶ cross_module_flag (target_process_area)                        │
│                                                                                  │
│  scope_change_request + scope_change_log (SCR lifecycle)                        │
│  bpmn_diagram (per process_level — Signavio URL or BPMN XML)                   │
│  attachment (polymorphic — workshop, step, req, OI, decision, process_level)    │
│  daily_snapshot (Explore KPI metrics for dashboard trends)                       │
│  cloud_alm_sync_log (requirement → ALM backlog push audit)                     │
│  project_role (7 roles: PM, Module Lead, Facilitator, BPO, Tech, Tester, View) │
│                                                                                  │
│  ► Fit Propagation: L4 fit_decision → L3 → L2 → L1 (auto-calculated)          │
│  ► 50+ API endpoints, 40+ React components, 5 modules (A/B/C/D/E)             │
└──────────────────────────────────────────────────────────────────────────────────┘
                        │                            │
                        ▼                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        BACKLOG WORKBENCH DOMAIN                         │
│                                                                         │
│  WRICEF Item / Config Item (sourced from Explore Phase requirement)    │
│    ├──1:1──▶ Functional Spec (FS)                                      │
│    │           └──1:1──▶ Technical Spec (TS)                           │
│    ├──1:N──▶ Acceptance Criteria                                       │
│    ├──1:1──▶ Status Flow (New→Design→Build→Test→Deploy→Closed)        │
│    ├──1:N──▶ Transport Request                                         │
│    ├──1:N──▶ unit_test_steps (→ TestCase generation source)            │
│    └──1:N──▶ Code Review / ATC Finding                                 │
│               └── Unit Test Evidence                                    │
└─────────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│               TEST MANAGEMENT DOMAIN (FS/TS v1.0 — 17 tablo)                    │
│                                                                                  │
│  ► Detay: test-management-fs-ts.md                                              │
│                                                                                  │
│  test_plan (project-level strategy container)                                    │
│    ├── strategy_document (markdown)                                              │
│    ├── entry_criteria / exit_criteria (per level, JSON)                          │
│    └── environments (DEV/QAS/PRD config, JSON)                                  │
│                                                                                  │
│  test_plan ──1:N──▶ test_cycle (time-boxed execution window)                   │
│    ├── test_level: unit|string|sit|uat|regression|performance                    │
│    ├── wave, planned_start/end, actual_start/end                                │
│    ├── entry_criteria_met / exit_criteria_met                                    │
│    └── ──N:M──▶ test_suite (via test_cycle_suite)                              │
│                                                                                  │
│  test_plan ──1:N──▶ test_suite (level-based grouping)                          │
│    ├── test_level, process_area, wave, e2e_scenario                             │
│    ├── risk_level (regression), automation_status                                │
│    └── ──1:N──▶ test_case                                                      │
│                                                                                  │
│  test_case (6 test levels in one table)                                         │
│    ├── Traceability FKs: requirement_id, wricef_item_id, config_item_id,        │
│    │   process_level_id (all from Explore Phase)                                │
│    ├── Level-specific: uat_category, regression_risk, perf_test_type            │
│    ├── ──1:N──▶ test_step (action, expected_result, sap_transaction)            │
│    ├── ──N:M──▶ test_case_dependency (must_pass, must_run, data_dependency)     │
│    └── ──1:N──▶ test_execution                                                 │
│                                                                                  │
│  test_cycle ──1:N──▶ test_run (execution session)                              │
│    └── ──1:N──▶ test_execution (case-level result)                             │
│                   ├── status: not_run|in_progress|pass|fail|blocked|skipped      │
│                   ├── ──1:N──▶ test_step_result (per-step pass/fail + evidence) │
│                   └── ──1:N──▶ defect (defects found during execution)          │
│                                                                                  │
│  defect (9-status lifecycle)                                                     │
│    ├── severity: S1_showstopper→S4_minor                                        │
│    ├── priority: P1_immediate→P4_low                                            │
│    ├── category: functional|integration|performance|config|data|auth|ui|doc      │
│    ├── root_cause, resolution, resolution_type                                   │
│    ├── SLA: due_date (auto-calculated), sla_breach                              │
│    ├── Traceability: test_case_id, requirement_id, wricef/config_item_id        │
│    ├── ──1:N──▶ defect_comment (type: comment|status_change|resolution)         │
│    ├── ──1:N──▶ defect_history (full field-level audit trail)                   │
│    └── ──N:M──▶ defect_link (duplicate_of|related_to|caused_by|blocks)          │
│                                                                                  │
│  uat_sign_off (BPO sign-off per UAT suite + usability_score 1-5)               │
│  perf_test_result (avg/p95/p99 response_ms, throughput, error_rate)             │
│  test_daily_snapshot (daily metrics JSON for trend dashboard)                    │
│                                                                                  │
│  ► 6 modules (T1-T6): Plan, Suite Manager, Execution, Defect, Dashboard, Trace │
│  ► Go/No-Go Scorecard: 10 criteria auto-evaluated                               │
│  ► Cloud ALM sync: test_case push, execution results, bidirectional defect      │
│  ► New role: test_lead (extends Explore project_role)                           │
└──────────────────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTEGRATION FACTORY DOMAIN                           │
│                                                                         │
│  Interface Catalog ──1:N──▶ Interface                                  │
│                               ├── type (Inbound/Outbound/Bidirectional)│
│                               ├── protocol (IDoc/RFC/OData/API/File)   │
│                               ├── source_system / target_system        │
│                               ├── wave (build/test wave assignment)    │
│                               ├── connectivity_status                  │
│                               ├── mock_service_available               │
│                               ├──1:N──▶ SIT Evidence                   │
│                               └──1:1──▶ Cutover Switch Plan            │
│                                                                         │
│  Monitoring Readiness Checklist per interface                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       DATA FACTORY DOMAIN                               │
│                                                                         │
│  Data Object List ──1:N──▶ Data Object                                 │
│                              ├── object_type (Master/Transaction/Config)│
│                              ├── source_system                         │
│                              ├── owner (business + technical)          │
│                              ├── volume (record count)                 │
│                              ├──1:N──▶ Field Mapping                   │
│                              ├──1:N──▶ Cleansing Task                  │
│                              │           └── quality_score             │
│                              ├──1:N──▶ Load Cycle                      │
│                              │           ├── cycle_number              │
│                              │           ├── status                    │
│                              │           ├── loaded_count              │
│                              │           ├── error_count               │
│                              │           └── reconciliation_result     │
│                              └──1:1──▶ Reconciliation Report           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       CUTOVER HUB DOMAIN                                │
│                                                                         │
│  Cutover Plan ──1:N──▶ Cutover Scope Item                              │
│                          ├── owner                                     │
│                          ├── category (Data/Interface/Auth/Job/Recon)  │
│                          └──1:N──▶ Runbook Task                        │
│                                      ├── sequence_number               │
│                                      ├── planned_start / planned_end   │
│                                      ├── actual_start / actual_end     │
│                                      ├── responsible (RACI)            │
│                                      ├── status                        │
│                                      ├── dependency[]                  │
│                                      └── rollback_action               │
│                                                                         │
│  Rehearsal ──1:N──▶ Rehearsal Report                                   │
│                       ├── plan_vs_actual_duration                       │
│                       ├── issues[]                                      │
│                       └── runbook_revision_needed                       │
│                                                                         │
│  Go/No-Go Pack: aggregated readiness from all domains                  │
│  Rollback Plan: decision points + rollback tasks                       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       RUN / SUSTAIN DOMAIN                              │
│                                                                         │
│  Hypercare Period                                                       │
│    ├──1:N──▶ Incident                                                  │
│    │           ├── severity / priority                                  │
│    │           ├── support_level (L1/L2/L3)                            │
│    │           ├── SLA_target / SLA_actual                             │
│    │           ├── linked_defect                                       │
│    │           └── resolution / workaround                             │
│    ├──1:N──▶ Problem                                                   │
│    │           └── root_cause / knowledge_article                      │
│    ├──1:N──▶ RFC (Request for Change)                                  │
│    │           ├── type (Enhancement/Bug/Optimization)                 │
│    │           ├── backlog_priority                                    │
│    │           └── linked_requirement                                  │
│    └──1:N──▶ KPI Measurement                                          │
│               ├── kpi_definition_ref                                   │
│               ├── measured_value / target_value                        │
│               └── measurement_date                                     │
│                                                                         │
│  Knowledge Base: known error/solution articles                          │
│  Sustain Handover Checklist                                             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     CROSS-CUTTING: RAID DOMAIN                          │
│                                                                         │
│  RAID Register                                                          │
│    ├──1:N──▶ Risk     (probability, impact, mitigation, owner, status) │
│    ├──1:N──▶ Action   (due_date, owner, status, linked_deliverable)    │
│    ├──1:N──▶ Issue    (severity, escalation_path, resolution)          │
│    └──1:N──▶ Decision (decision_date, alternatives, rationale, owner)  │
│                                                                         │
│  Her kayıt: workstream, phase, gate ile ilişkilendirilebilir            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    CROSS-CUTTING: SECURITY DOMAIN                       │
│                                                                         │
│  Role Concept ──1:N──▶ Authorization Role                              │
│                          ├── role_type (Single/Composite/Master)        │
│                          ├── SoD_rule_violations[]                     │
│                          └──1:N──▶ Access Assignment                   │
│                                      ├── user / team                   │
│                                      ├── environment                   │
│                                      └── valid_from / valid_to         │
│                                                                         │
│  SoD Rule Matrix: conflict definitions                                  │
│  UAT Access Readiness Checklist                                         │
│  Go-Live Access Checklist                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Uçtan Uca İzlenebilirlik Zinciri (Traceability Chain)

```
EXPLORE PHASE (24 tablo)                    TEST MANAGEMENT (17 tablo)
────────────────────────                    ──────────────────────────
process_level (L1: Value Chain)
  └─▶ process_level (L2: Process Area, e.g., FI, SD)
       └─▶ process_level (L3: Scope Item, e.g., J58, BD9)
            ├── scope_status: in_scope | out_of_scope | under_review
            ├── wave: 1, 2, 3, 4
            ├── bpmn_diagram (Signavio URL / BPMN XML)
            │
            └─▶ process_level (L4: Sub-Process, e.g., J58.01)
                 │   ├── l4_seed_catalog (SAP BP / Signavio / manual)
                 │   │
                 │   └─▶ workshop (300+ per project)
                 │        ├── workshop_scope_item (N:M)
                 │        ├── workshop_dependency (cross-module)
                 │        ├── workshop_attendee
                 │        ├── workshop_document (minutes)
                 │        │
                 │        └─▶ process_step (L4 in workshop context)
                 │             ├── fit_decision: fit | partial_fit | gap
                 │             ├── multi-session continuity
                 │             │
                 │             ├─▶ decision (formal workshop decisions)
                 │             │
                 │             ├─▶ open_item (action items, P1-P4)
                 │             │    └── open_item_comment
                 │             │
                 │             └─▶ requirement
                 │                  ├── status lifecycle (8 states)
                 │                  ├── requirement_dependency (N:M)
                 │                  ├── requirement_open_item_link (blocking)
                 │                  │
                 │                  ├─▶ WRICEF Item ──▶ FS ──▶ TS
                 │                  │     └── unit_test_steps ──────────▶ test_case (Unit)
                 │                  │                                        │
                 │                  ├─▶ Config Item ──▶ Config Log          │
                 │                  │     └── unit_test_steps ──────────▶ test_case (Unit)
                 │                  │                                        │
                 │                  └───────────────────────────────────▶ test_case (SIT/UAT)
                 │                                                           │
                 │                                                           ├─▶ test_step
                 │                                                           ├─▶ test_execution
                 │                                                           │    ├─▶ test_step_result
                 │                                                           │    └─▶ defect
                 │                                                           │         ├── severity (S1-S4)
                 │                                                           │         ├── priority (P1-P4)
                 │                                                           │         ├── SLA tracking
                 │                                                           │         ├─▶ defect_comment
                 │                                                           │         ├─▶ defect_history
                 │                                                           │         └─▶ defect_link
                 │                                                           │
                 │                                                           └─▶ uat_sign_off (BPO)
                 │
                 └── cross_module_flag, attachment, scope_change_request

CROSS-CUTTING:
  daily_snapshot (Explore) + test_daily_snapshot (Test) → Dashboard trends
  cloud_alm_sync_log → requirement push + test_case push + defect sync
  project_role (7+1 roles) → Permission matrix across both domains
```

Platform herhangi bir noktadan, zincirin tamamını yukarı ve aşağı gezebilmelidir.
**Toplam tablo sayısı:** Explore 24 + Test Management 17 = **41 tablo**
(Backlog, Integration, Data, Cutover, Run, RAID, Security domain tabloları hariç)

---

## 4. Modül Mimarisi (Detay)

### 4.1 Program Setup Module

**Amaç:** Proje tanımı, faz takvimi, gate yapılandırması, RACI, komite kurulumu.

| Özellik | Detay |
|---------|-------|
| Proje tipi seçimi | Greenfield / Brownfield / Selective / Public Cloud — seçime göre faz süreleri, varsayılan workstream'ler ve şablonlar otomatik yüklenir |
| SAP Activate fazları | Discover → Prepare → Explore → Realize → Deploy → Run; her fazda takvim, deliverable listesi, gate kriterleri |
| Gate yönetimi | Gate 0–4 + proje kapanış; her gate için checklist, sign-off workflow, steering karar kaydı |
| RACI matrisi | Workstream × Role × Deliverable bazlı; toplu import/export |
| Komiteler | Steering, PMO, Technical, Change Board — toplantı takvimi, katılımcılar, karar kaydı |
| Rollout / Wave planlama | Çoklu wave (ülke, tesis, iş birimi) için master plan; bağımlılık yönetimi |
| Bütçe & kaynak | Workstream bazlı FTE planı, bütçe takibi, forecast vs actual |

**Proje Tipi Bazlı Otomatik Konfigürasyon:**

```
Greenfield seçildi →
  ✓ Explore fazında Fit-to-Standard workshop şablonları aktif
  ✓ Data Migration modülü "full load" modunda
  ✓ Change Management workstream zorunlu
  ✓ Custom Code workstream → BTP extensibility odaklı

Brownfield seçildi →
  ✓ Readiness Check + ATC remediation backlog aktif
  ✓ Custom Code workstream → remediation/retirement odaklı
  ✓ Cutover Hub → rollback stratejisi zorunlu alan
  ✓ Test Management System → regresyon ağırlıklı (17 tablo, 6 test seviyesi)

Public Cloud seçildi →
  ✓ Fit-to-Standard → scope item bazlı (SAP Best Practices)
  ✓ Extension → in-app + BTP side-by-side ayrımı
  ✓ Release/Upgrade takvimi entegrasyonu aktif
  ✓ Regression set yönetimi zorunlu
```

### 4.2 Scope & Requirements Module → **Explore Phase Manager**

**Amaç:** SAP Activate Explore fazının uçtan uca yönetimi — süreç hiyerarşisi, Fit-to-Standard workshop'ları, requirement yaşam döngüsü, Cloud ALM aktarımı.

**FS/TS Referansı:** `explore-phase-fs-ts.md` v1.1 (71KB, 16 bölüm, 24 tablo)

**5 Alt Modül (Ekran):**

| Modül | Ekran | Tablo Sayısı | Birincil İşlev |
|-------|-------|-------------|----------------|
| **A** | Process Hierarchy Manager | 4 (process_level, l4_seed_catalog, bpmn_diagram, scope_change_*) | L1→L2→L3→L4 ağaç, scope matrix, fit dağılımı |
| **B** | Workshop Hub | 5 (workshop, workshop_scope_item, workshop_attendee, workshop_dependency, workshop_agenda_item) | 300+ workshop planlama, kanban/kapasite görünümü |
| **C** | Workshop Detail | 7 (process_step, decision, open_item, requirement, cross_module_flag, workshop_document, workshop_revision_log) | Tek workshop yürütme, 6 tab, fit kararı, REQ/OI/Decision oluşturma |
| **D** | Requirement & Open Item Hub | 4 (requirement, open_item, requirement_dependency, requirement_open_item_link) | Cross-workshop lifecycle, batch approval, ALM push |
| **E** | Explore Dashboard | 1 (daily_snapshot) | 10 widget, trend analizi, steering committee export |

**Veri Modeli Özeti (24 tablo):**

| Kategori | Tablolar |
|----------|---------|
| Süreç Hiyerarşisi | process_level, l4_seed_catalog, bpmn_diagram |
| Workshop | workshop, workshop_scope_item, workshop_attendee, workshop_agenda_item, workshop_dependency, workshop_document, workshop_revision_log |
| Workshop Çıktıları | process_step, decision, open_item, open_item_comment, cross_module_flag |
| Requirement | requirement, requirement_dependency, requirement_open_item_link |
| Scope Değişiklik | scope_change_request, scope_change_log |
| Cross-Cutting | attachment, project_role, daily_snapshot, cloud_alm_sync_log |

**Kritik Business Rule'lar:**
- **Fit propagation:** L4 kararları otomatik L3→L2→L1'e yansır (majority/weighted)
- **Workshop start validation:** L4 sub-process olmazsa workshop başlatılamaz
- **Multi-session continuity:** WS-FI-03A → WS-FI-03B arası veri taşıma, son session'da fit zorunlu
- **Blocking OI:** Requirement onayı → bağlı OI'ların tümü kapalı olmalı
- **Scope change lifecycle:** requested → under_review → approved → implemented (etki analizi otomatik)
- **Code generation:** WS-{area}-{seq}, REQ-{seq}, OI-{seq}, DEC-{seq}

**API Gruplaması:** 5 grup, 50+ endpoint (detay: explore-phase-fs-ts.md §3)

**Dashboard KPI'ları:**
- Workshop burndown (planned vs actual completion)
- Wave progress bars
- Fit/Gap/Partial trend (stacked area)
- Requirement pipeline funnel (Draft → Verified)
- OI aging distribution
- Gap density heatmap (area × wave)
- Facilitator load comparison
- Scope coverage donut

### 4.3 Backlog Workbench Module

**Amaç:** Requirement'tan türeyen WRICEF ve config item'larının yaşam döngüsü yönetimi.

**WRICEF Item Status Flow:**

```
New → Analysis → Design (FS) → Technical Design (TS) → Build
  → Unit Test → Integration Ready → SIT Pass → UAT Pass → Deploy Ready → Closed
```

**Özellikler:**
- Requirement'tan otomatik WRICEF/Config item oluşturma (gap → WRICEF, partial fit → config/WRICEF)
- FS/TS doküman yönetimi (versiyon, onay workflow)
- Unit test evidence yükleme ve onay
- ATC finding takibi (brownfield)
- Code review workflow
- Transport request takibi (DEV → QAS → PRD)
- BTP extension ayrımı (in-app vs side-by-side) — Public Cloud projelerinde

### 4.4 Integration Factory Module

**Amaç:** Interface envanteri, wave planı, connectivity, test kanıtları, cutover switch planı.

**Interface kayıt yapısı:**

| Alan | Açıklama |
|------|----------|
| interface_id | Benzersiz ID |
| name | Açıklayıcı isim |
| direction | Inbound / Outbound / Bidirectional |
| protocol | IDoc / RFC / OData / REST API / File / CPI Flow |
| source_system | Kaynak sistem |
| target_system | Hedef sistem |
| middleware | CPI / PI/PO / Direct |
| build_wave | Geliştirme dalgası |
| test_wave | Test dalgası |
| connectivity_status | Not Started / In Progress / Connected / Verified |
| mock_available | Boolean |
| sit_evidence | Dosya referansları |
| monitoring_ready | Boolean |
| cutover_switch_plan | Referans |

**Factory Dashboard:**
- Wave bazlı ilerleme (build + test)
- Connectivity status heat map
- Mock availability oranı
- SIT pass/fail dağılımı
- Cutover readiness skoru

### 4.5 Data Factory Module

**Amaç:** Veri nesneleri, mapping, cleansing, yükleme döngüleri, mutabakat.

**Load Cycle Yönetimi:**

```
Cycle 0 (Trial)  → Cycle 1 (Volume) → Cycle 2 (Dress Rehearsal) → Cycle 3 (Cutover)
     │                   │                      │                        │
     ▼                   ▼                      ▼                        ▼
  Profiling         Quality Check          Reconciliation           Final Load
  & Mapping         & Correction           & Sign-off               & Go-Live
```

**KPI'lar:**
- Object bazlı yükleme başarı oranı
- Error rate trendi (cycle bazlı)
- Cleansing task completion
- Reconciliation sonucu (kaynak vs hedef)
- Data readiness skoru (ağırlıklı ortalama)

### 4.6 Test Hub Module → **Test Management System**

**Amaç:** 6 test seviyesinin yaşam döngüsü, defect yönetimi, Go/No-Go scorecard, traceability matrix.

**FS/TS Referansı:** `test-management-fs-ts.md` v1.0 (54KB, 13 bölüm, 17 tablo)

**6 Alt Modül (Ekran):**

| Modül | Ekran | Birincil İşlev |
|-------|-------|----------------|
| **T1** | Test Plan & Strategy | Strateji dokümanı, entry/exit criteria, ortam matrix, takvim |
| **T2** | Test Suite Manager | 6 seviye tab, case authoring, WRICEF/process'ten otomatik üretim |
| **T3** | Test Execution | Step-by-step runner, pass/fail/blocked, evidence upload, defect quick-create |
| **T4** | Defect Tracker | 9 status lifecycle, severity/priority, SLA, root cause, kanban/table |
| **T5** | Test Dashboard | 10 widget, Go/No-Go Scorecard (10 kriter), trend, export |
| **T6** | Traceability Matrix | REQ→WRICEF/Config→TestCase→Execution→Defect zinciri, coverage gap |

**Test Seviyeleri ve Explore Phase Bağlantısı:**

| Seviye | Kaynak (Explore'dan) | Test Edilen | Çıkış Kriteri |
|--------|---------------------|------------|---------------|
| **Unit** | WRICEF/Config Item → unit_test_steps | Tekil nesne | Pass ≥95%, critical=0 |
| **String** | L2 Process Area → L3/L4 chain | Modül içi zincir | Zincir kırılması=0 |
| **SIT** | E2E Scenario → process_step cross-module | Modüller arası | P1/P2=0, coverage ≥90% |
| **UAT** | Workshop decisions + L3 scope items | İş perspektifi | BPO sign-off, critical=0 |
| **Regression** | Changed WRICEF/Config → risk-based subset | Mevcut süreçler | 100% pass |
| **Performance** | Kritik transaction'lar | Yük altında | Response < threshold |

**Otomatik Test Case Üretimi (Explore→Test köprüsü):**
- `generate-from-wricef` → WRICEF/Config unit_test_steps'den Unit Test Case üretir
- `generate-from-process` → Explore process_step'lerden SIT/UAT senaryosu üretir

**Defect Lifecycle:** new → assigned → in_progress → resolved → retest → closed (+ reopened, deferred, rejected)

**SLA:** S1+P1: 1h/4h | S2+P2: 4h/1d | S3+P3: 1d/3d | S4+P4: 2d/sprint

**Go/No-Go Scorecard:** 10 kriter (unit≥95%, SIT≥95%, UAT happy path 100%, BPO sign-off, S1=0, S2=0, S3≤5, regression 100%, perf≥95%, all critical closed)

**Veri Modeli:** 17 tablo (test_plan, test_cycle, test_cycle_suite, test_suite, test_case, test_step, test_case_dependency, test_run, test_execution, test_step_result, defect, defect_comment, defect_history, defect_link, uat_sign_off, perf_test_result, test_daily_snapshot)

**Role Extension:** Mevcut 7 Explore rolüne ek olarak `test_lead` rolü

**API:** 10 grup, 40+ endpoint (detay: test-management-fs-ts.md §3)

### 4.7 Cutover Hub Module

**Amaç:** Runbook, rehearsal takibi, issue log, Go/No-Go paketi, hypercare kurulumu.

**Runbook Task Yapısı:**

```json
{
  "task_id": "CUT-047",
  "category": "Data Load",
  "description": "Customer Master - Final Load",
  "sequence": 47,
  "planned_start": "2026-06-15T02:00:00",
  "planned_end": "2026-06-15T04:30:00",
  "planned_duration_min": 150,
  "actual_start": null,
  "actual_end": null,
  "responsible": "Data Team Lead",
  "accountable": "Migration Manager",
  "dependency": ["CUT-045", "CUT-046"],
  "rollback_action": "Restore from backup snapshot #3",
  "rollback_decision_point": "Error rate > 5%",
  "status": "Not Started",
  "environment": "PRD"
}
```

**Rehearsal Tracking:**
- Rehearsal # → plan vs actual süre (saat-saat karşılaştırma Gantt)
- Başarısız adımlar ve revizyon kaydı
- Delta raporu (Rehearsal N vs N-1)

**Go/No-Go Pack (otomatik aggregation):**

| Alan | Kaynak | Durum |
|------|--------|-------|
| Open P1/P2 Defects | Test Management (T5) | ✅ 0 |
| Data Load Reconciliation | Data Factory | ✅ Pass |
| Interface Connectivity | Integration Factory | ⚠️ 1 pending |
| Authorization Readiness | Security Module | ✅ Complete |
| Training Completion | Change Mgmt | ✅ > 90% |
| Cutover Rehearsal | Cutover Hub | ✅ Within tolerance |
| Steering Sign-off | Program Setup | ⏳ Pending |

### 4.8 Run/Sustain Module

**Amaç:** War room yönetimi, incident/problem, KPI tracking, RFC/change workflow, handover.

**Incident Lifecycle:**

```
New → Triaged (L1/L2/L3) → In Progress → Resolved → Closed
                                │
                                └── Workaround Applied → Permanent Fix (RFC)
```

**Hypercare Dashboard:**
- Open incident count by severity (real-time)
- SLA compliance rate
- Daily resolution rate
- Top 5 affected processes
- War room schedule and escalation matrix
- Trend: new vs resolved (daily)

**Sustain Handover Checklist:**
- [ ] Açık incident'ların L1/L2/L3 aktarımı
- [ ] Knowledge base makaleleri tamamlandı
- [ ] Kritik KPI'lar izleme modunda
- [ ] RFC/change workflow aktif
- [ ] Backlog grooming süreci tanımlandı
- [ ] Support team eğitimi tamamlandı

### 4.9 RAID Module (Cross-Cutting)

**Amaç:** Risk, Action, Issue, Decision yönetimi — tüm modüllerle entegre.

**Risk Kayıt Yapısı (Playbook Section 8 bazlı):**

| Risk Alanı | Erken Uyarı Sinyali (Otomatik) | Varsayılan Mitigation |
|-------------|--------------------------------|----------------------|
| Scope Creep | Backlog büyüme oranı > threshold | Scope baseline alert; RFC zorunlu |
| Data Readiness | Mapping completion < plan; quality score düşük | Data profiling alert; cycle plan review |
| Custom Code | ATC finding artışı; remediation kuyruk uzaması | Code quality gate; retirement önerisi |
| Integration | Connectivity failure; mock availability düşük | Factory wave review; SIT escalation |
| Security | UAT erişim reddedilme oranı yüksek | Role design sprint trigger |
| Performance | Job failure; response time > threshold | Sizing review; tuning backlog |
| Change Mgmt | Training katılım < target | Sponsor alert; ek session planla |

**Otomatik Risk Sinyalleri:** Platform, modüllerden gelen KPI verilerini izleyerek risk skorlarını otomatik güncelleyebilir.

### 4.10 Reporting Engine

**Amaç:** Tüm modüllerden veri çekerek role-based dashboard ve raporlar üretmek.

**Rapor Katmanları:**

```
Executive Layer (Steering)
  ├── Program Health Scorecard (RAG)
  ├── Phase & Gate Progress
  ├── Budget vs Actual
  ├── Top Risks & Escalations
  └── Go-Live Readiness Index

PMO Layer
  ├── Workstream Status Matrix
  ├── Deliverable Completion Tracker
  ├── RAID Summary
  ├── Resource Utilization
  └── Cross-Workstream Dependencies

Workstream Layer
  ├── Requirement Coverage (Fit/PFit/Gap)
  ├── Backlog Burndown
  ├── Test Execution & Defect KPIs
  ├── Data Migration Cycle Progress
  └── Integration Factory Status

Operational Layer
  ├── Daily Standup Dashboard
  ├── Defect Triage Board
  ├── Cutover Runbook Live View
  └── Hypercare War Room Dashboard
```

---

## 5. API Tasarımı

> **Not:** Aşağıdaki API yapısı üst seviye organizasyondur. Explore Phase (50+ endpoint) ve Test Management (40+ endpoint) detaylı API spesifikasyonları için ilgili FS/TS dokümanlarına bakınız:
> - `explore-phase-fs-ts.md` §3 — Process Hierarchy, Workshop, Process Step, Requirement, Open Item API'leri
> - `test-management-fs-ts.md` §3 — Test Plan, Cycle, Suite, Case, Execution, Defect, UAT Sign-Off, Dashboard API'leri

### 5.1 API Organizasyonu

```
/api/v1/
├── /programs
│   ├── GET    /                          # List programs
│   ├── POST   /                          # Create program
│   ├── GET    /:programId                # Get program details
│   └── ...
│
├── /projects
│   ├── GET    /                          # List projects (filterable)
│   ├── POST   /                          # Create project
│   ├── GET    /:projectId
│   ├── PUT    /:projectId
│   ├── GET    /:projectId/phases         # SAP Activate phases
│   ├── GET    /:projectId/gates          # Quality gates
│   ├── GET    /:projectId/workstreams
│   ├── GET    /:projectId/raci
│   └── GET    /:projectId/dashboard      # Aggregated KPIs
│
├── /explore                                # Explore Phase Manager (detay: explore-phase-fs-ts.md §3)
│   ├── GET    /process-levels               # L1→L2→L3→L4 hierarchy
│   ├── POST   /process-levels/import        # Scope item catalog import
│   ├── GET    /process-levels/:id/tree      # Subtree with fit stats
│   ├── PUT    /process-levels/:id           # Update scope status, wave
│   ├── POST   /process-levels/:id/seed-l4   # L4 seeding (catalog/BPMN/manual)
│   ├── GET    /workshops                    # Workshop Hub (filter: wave, area, status)
│   ├── POST   /workshops                    # Create workshop
│   ├── POST   /workshops/:id/start          # Start (validates L4 exists)
│   ├── POST   /workshops/:id/complete       # Complete (validates fit decisions)
│   ├── POST   /workshops/:id/reopen         # Reopen (PM/Module Lead only)
│   ├── GET    /workshops/:id/process-steps  # Steps in workshop
│   ├── PUT    /process-steps/:id            # Update fit decision, notes
│   ├── POST   /process-steps/:id/decisions  # Add decision
│   ├── POST   /process-steps/:id/open-items # Add open item
│   ├── POST   /process-steps/:id/requirements # Add requirement
│   ├── GET    /requirements                 # REQ Hub (filter: status, priority, area)
│   ├── POST   /requirements/:id/approve     # Approve (role-checked)
│   ├── POST   /requirements/:id/push-alm    # Push to Cloud ALM
│   ├── GET    /open-items                   # OI Tracker
│   ├── POST   /open-items/:id/transition    # Status transition
│   ├── GET    /scope-changes                # SCR management
│   ├── POST   /scope-changes                # Create SCR
│   ├── GET    /dashboard                    # Explore Dashboard (10 widgets)
│   └── GET    /dashboard/trends             # Daily snapshot trends
│
├── /backlog
│   ├── GET    /wricef?filters...
│   ├── POST   /wricef
│   ├── PUT    /wricef/:itemId
│   ├── GET    /wricef/:itemId/specs      # FS/TS documents
│   ├── GET    /config?filters...
│   ├── POST   /config
│   └── GET    /burndown                  # Burndown chart data
│
├── /integration
│   ├── GET    /interfaces?filters...
│   ├── POST   /interfaces
│   ├── PUT    /interfaces/:ifId
│   ├── GET    /interfaces/:ifId/evidence
│   ├── GET    /waves                     # Build/test waves
│   └── GET    /dashboard                 # Factory KPIs
│
├── /data-migration
│   ├── GET    /objects?filters...
│   ├── POST   /objects
│   ├── GET    /objects/:objId/mappings
│   ├── GET    /objects/:objId/cycles
│   ├── POST   /objects/:objId/cycles     # Start new cycle
│   ├── PUT    /cycles/:cycleId           # Update cycle result
│   └── GET    /dashboard                 # Migration KPIs
│
├── /testing                                 # Test Management System (detay: test-management-fs-ts.md §3)
│   ├── GET    /plans                        # Test plan
│   ├── POST   /plans                        # Create/approve plan
│   ├── GET    /cycles                       # Test cycles (filter: level, wave)
│   ├── POST   /cycles                       # Create cycle
│   ├── POST   /cycles/:id/start             # Start (entry criteria check)
│   ├── POST   /cycles/:id/complete          # Complete (exit criteria eval)
│   ├── GET    /suites                       # Test suites (6 level tabs)
│   ├── POST   /suites/:id/generate-from-wricef   # Auto-gen unit tests
│   ├── POST   /suites/:id/generate-from-process  # Auto-gen SIT/UAT
│   ├── GET    /cases                        # Test cases (filter: level, area, priority)
│   ├── POST   /cases/:id/steps              # Batch create/update steps
│   ├── POST   /runs                         # Create test run
│   ├── PUT    /executions/:id               # Update execution + step results
│   ├── POST   /executions/:id/create-defect # Auto-create defect from fail
│   ├── GET    /defects                      # Defect tracker (filter: severity, SLA)
│   ├── POST   /defects/:id/transition       # Lifecycle transition (9 states)
│   ├── GET    /uat-sign-offs                # UAT BPO sign-offs
│   ├── POST   /uat-sign-offs                # Create sign-off
│   ├── GET    /dashboard                    # Test Dashboard (10 widgets)
│   ├── GET    /dashboard/go-no-go           # Go/No-Go Scorecard (10 criteria)
│   ├── GET    /dashboard/traceability-matrix # Full REQ→Defect chain
│   ├── POST   /cases/:id/sync-to-alm       # Push test case to ALM
│   ├── POST   /defects/:id/sync-to-alm     # Push defect to ALM
│   └── POST   /dashboard/export             # PPTX/PDF/XLSX export
│
├── /cutover
│   ├── GET    /plans
│   ├── POST   /plans
│   ├── GET    /runbook/:planId           # Runbook tasks
│   ├── POST   /runbook/:planId/tasks
│   ├── PUT    /tasks/:taskId             # Update (start/complete)
│   ├── GET    /rehearsals
│   ├── POST   /rehearsals
│   ├── GET    /go-no-go                  # Aggregated readiness
│   └── GET    /live-view                 # Real-time cutover
│
├── /run
│   ├── GET    /incidents?filters...
│   ├── POST   /incidents
│   ├── PUT    /incidents/:incId
│   ├── GET    /problems
│   ├── GET    /rfcs
│   ├── POST   /rfcs
│   ├── GET    /kpis                      # KPI measurements
│   ├── GET    /knowledge-base
│   └── GET    /dashboard                 # Hypercare dashboard
│
├── /raid
│   ├── GET    /?type=risk|action|issue|decision
│   ├── POST   /
│   ├── PUT    /:raidId
│   └── GET    /dashboard
│
├── /security
│   ├── GET    /roles
│   ├── GET    /sod-matrix
│   ├── GET    /access-assignments
│   └── GET    /readiness-checklist
│
└── /reports
    ├── GET    /executive-scorecard
    ├── GET    /steering-pack
    ├── GET    /workstream-status
    └── POST   /export                    # PDF/Excel export
```

### 5.2 Ortak API Pattern'leri

**Filtreleme:** `?workstream=O2C&phase=Realize&status=Open&severity=P1`

**Sayfalama:** `?page=1&pageSize=50&sortBy=created_at&sortDir=desc`

**İzlenebilirlik:** Her endpoint `/:id/traceability` ile üst/alt zincire erişim sağlar.

**Bulk operasyonlar:** `POST /api/v1/{resource}/bulk` — toplu import/update.

**Audit:** Her değişiklik `audit_log` tablosuna otomatik yazılır (who, when, what, old_value, new_value).

---

## 6. UI/UX Mimarisi

### 6.1 Navigation Yapısı

```
┌────────────────────────────────────────────────────────────┐
│  [Logo]  Program Seçici ▾   Faz: Realize ▾    🔔  👤     │
├──────────┬─────────────────────────────────────────────────┤
│          │                                                 │
│ Dashboard│  ┌─────────────────────────────────────────┐   │
│ ────────►│  │         MAIN CONTENT AREA               │   │
│ Program  │  │                                         │   │
│  Setup   │  │  Contextual based on selected module    │   │
│ ────────►│  │                                         │   │
│ Explore  │  │  ┌──────┐ ┌──────┐ ┌──────┐            │   │
│  Phase   │  │  │ KPI  │ │ KPI  │ │ KPI  │            │   │
│ ────────►│  │  │ Card │ │ Card │ │ Card │            │   │
│ Backlog  │  │  └──────┘ └──────┘ └──────┘            │   │
│ ────────►│  │                                         │   │
│ Integr.  │  │  ┌─────────────────────────────────┐   │   │
│  Factory │  │  │                                 │   │   │
│ ────────►│  │  │     Data Table / Board View     │   │   │
│ Data     │  │  │     (switchable)                │   │   │
│  Factory │  │  │                                 │   │   │
│ ────────►│  │  └─────────────────────────────────┘   │   │
│ Test Mgmt│  │                                         │   │
│ (6 sub)  │  │  [+ Create]  [Filter ▾]  [Export]      │   │
│ Cutover  │  └─────────────────────────────────────────┘   │
│ ────────►│                                                 │
│ Run/     │  ┌─────────────────────────────────────────┐   │
│  Sustain │  │     DETAIL / SIDE PANEL                 │   │
│ ────────►│  │     (opens on row click)                │   │
│ RAID     │  │     - Full record view                  │   │
│ ────────►│  │     - Traceability chain                │   │
│ Reports  │  │     - Activity log                      │   │
│ ────────►│  │     - Related items                     │   │
│ Settings │  └─────────────────────────────────────────┘   │
│          │                                                 │
└──────────┴─────────────────────────────────────────────────┘
```

### 6.2 Temel View Pattern'leri

| View | Kullanım | Örnek |
|------|----------|-------|
| **Board (Kanban)** | Status flow takibi | Backlog Workbench, Defect Triage |
| **Table (Grid)** | Detaylı listeleme, filtreleme | Requirements, Interfaces, Test Cases |
| **Gantt** | Zaman planlaması | Cutover Runbook, Phase Plan, Wave Plan |
| **Matrix** | Cross-reference | Traceability, RACI, SoD |
| **Dashboard** | KPI aggregation | Her modülün özet sayfası |
| **Tree** | Hiyerarşik yapı | Process hierarchy, Org structure |
| **Timeline** | Kronolojik olaylar | Audit trail, Incident timeline |
| **Live View** | Gerçek zamanlı | Cutover execution, War room |

### 6.3 Global Özellikler

- **Workstream filtresi:** Her sayfada kalıcı filtre — seçilen workstream tüm modüllerde geçerli
- **Phase context:** Aktif fazın görsel göstergesi; faz değiştiğinde ilgili deliverable'lar öne çıkar
- **Quick search:** Tüm entity'lerde global arama (ID, başlık, açıklama)
- **Traceability drill-down:** Herhangi bir kayıttan tek tıkla bağlı üst/alt kayıtlara erişim
- **Inline editing:** Tablo satırlarında hızlı düzenleme
- **Bulk actions:** Çoklu seçim + toplu status değişikliği
- **Export:** Her tablo/dashboard → Excel, PDF, PowerPoint

---

## 7. Teknoloji Stack Önerisi

### 7.1 Seçenek A: Modern Web Stack (ProjektCoPilot ile uyumlu)

| Katman | Teknoloji | Gerekçe |
|--------|-----------|---------|
| Frontend | React + TypeScript | Bileşen zenginliği, SPA, offline PWA desteği |
| UI Library | Shadcn/UI + Tailwind | Hızlı geliştirme, tutarlı tasarım |
| Charts | Recharts + AG Grid | Dashboard'lar + gelişmiş tablo |
| Backend | Python Flask / FastAPI | Mevcut ProjektCoPilot deneyimi; async desteği (FastAPI) |
| Database | PostgreSQL | Relational, JSON support, enterprise-grade |
| Cache | Redis | Session, dashboard cache, real-time |
| File Storage | MinIO / S3 | Doküman, evidence, export dosyaları |
| Search | PostgreSQL FTS / MeiliSearch | Full-text search |
| Auth | Keycloak / Auth0 | SSO, RBAC, SAML (SAP IAS entegrasyonu) |
| CI/CD | GitHub Actions | Mevcut workflow |
| Hosting | Docker + K8s veya BTP | Esnek dağıtım |

### 7.2 Seçenek B: SAP Ekosistem Odaklı

| Katman | Teknoloji |
|--------|-----------|
| Frontend | SAP Fiori / UI5 |
| Backend | SAP CAP (Node.js/Java) |
| Database | SAP HANA Cloud |
| Platform | SAP BTP |
| Auth | SAP IAS/IPS |
| Integration | SAP Integration Suite |

### 7.3 Hibrit Yaklaşım (Önerilen)

Core platform → Seçenek A (hız, esneklik, bağımsızlık); SAP entegrasyon noktaları → BTP side-by-side (CPI connector'lar, Solution Manager/Cloud ALM data sync).

---

## 8. Entegrasyon Mimarisi

```
┌──────────────────────────────────────────────────────────────┐
│                    PLATFORM                                   │
│                                                               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │ REST API │    │ Webhook  │    │ Event    │               │
│  │ (inbound)│    │ (outbound│    │ Bus      │               │
│  │          │    │  notif.) │    │          │               │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘               │
└───────┼───────────────┼───────────────┼──────────────────────┘
        │               │               │
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ SAP Ecosystem │ │ Collaboration │ │ DevOps / ALM  │
│               │ │               │ │               │
│ • Cloud ALM   │ │ • MS Teams    │ │ • Jira        │
│ • Sol. Mgr    │ │ • Slack       │ │ • Azure DevOps│
│ • Signavio    │ │ • Email       │ │ • GitHub      │
│ • S/4HANA     │ │ • SharePoint  │ │ • ServiceNow  │
│ • BTP / CPI   │ │               │ │               │
└───────────────┘ └───────────────┘ └───────────────┘
```

**Kritik entegrasyon senaryoları:**

| Senaryo | Yön | Açıklama |
|---------|-----|----------|
| Cloud ALM ↔ Platform | Bidirectional | Task, defect, requirement sync |
| Jira ↔ Platform | Bidirectional | WRICEF/defect eşleme |
| Signavio → Platform | Import | Süreç modelleri → Process hierarchy |
| MS Teams ← Platform | Outbound | Gate kararları, risk alert, daily digest |
| S/4HANA → Platform | Import | Transport status, job monitoring |
| ServiceNow ↔ Platform | Bidirectional | Incident sync (hypercare) |

---

## 9. Güvenlik ve Yetkilendirme Modeli

### 9.1 Role-Based Access Control (RBAC)

| Rol | Erişim kapsamı |
|-----|---------------|
| Program Director | Tüm modüller, tüm projeler — read/write |
| PMO Lead | Tüm modüller, atanmış program — read/write |
| Workstream Lead | Kendi workstream'i — full; diğerleri — read |
| Consultant | Atanmış modüller — write; diğerleri — read |
| Test Lead | Test Management System full; diğerleri — read |
| Business Process Owner | Explore Phase — approve; Test Management — execute/sign-off |
| Steering Member | Executive dashboard — read only |
| External Vendor | Kısıtlı modül/workstream — read/write |

### 9.2 Data Security

- Row-level security: workstream, proje, program bazlı
- Document classification: Internal / Confidential / Restricted
- Audit trail: tüm değişiklikler loglı
- Data retention: proje kapanış sonrası arşivleme politikası

---

## 10. AI Katmanı: 14 Asistan — Mimari, Teknoloji ve Uygulama Detayları

### 10.1 AI Altyapı Mimarisi

Tüm 14 AI asistan 4 temel bileşen üzerine inşa edilir. Bu bileşenler bir kez kurulduğunda
her asistan aynı altyapıyı paylaşır.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AI ORCHESTRATION LAYER                             │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  LLM        │  │  RAG /      │  │  Rule        │  │  Graph           │ │
│  │  Gateway    │  │  Embedding  │  │  Engine      │  │  Analyzer        │ │
│  │             │  │  Engine     │  │              │  │                  │ │
│  │ Claude API  │  │ pgvector   │  │ Threshold +  │  │ Traceability     │ │
│  │ OpenAI API  │  │ + Chunking │  │ Workflow     │  │ chain traversal  │ │
│  │ Fallback    │  │ + Retrieval│  │ triggers     │  │ + dependency     │ │
│  │ Router      │  │            │  │              │  │ analysis         │ │
│  └──────┬──────┘  └──────┬─────┘  └──────┬───────┘  └────────┬─────────┘ │
│         │                │               │                    │            │
│  ┌──────┴────────────────┴───────────────┴────────────────────┴─────────┐ │
│  │                     SHARED SERVICES                                   │ │
│  │                                                                       │ │
│  │  Prompt Registry │ SAP Knowledge Base │ Suggestion Queue │ Audit Log  │ │
│  │  (versioned      │ (Best Practices,   │ (pending human   │ (every AI  │ │
│  │   templates per  │  module catalog,   │  review items)   │  action    │ │
│  │   assistant)     │  FS/TS patterns)   │                  │  logged)   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
         │                │               │                    │
         ▼                ▼               ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PLATFORM APPLICATION MODULES                            │
│  Explore Phase │ Backlog │ Test Mgmt │ Cutover │ Run/Sustain │ RAID │ Reports │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Temel AI Bileşenleri: Build vs. Integrate Kararı

| Bileşen | Karar | Teknoloji | Gerekçe |
|---------|-------|-----------|---------|
| **LLM Gateway** | INTEGRATE | Anthropic Claude API (primary), OpenAI API (fallback) | LLM eğitmek gereksiz; API ile en güncel modeller kullanılır. Gateway katmanı provider bağımsızlığı sağlar |
| **RAG / Embedding Engine** | BUILD + INTEGRATE | pgvector (PostgreSQL extension) + Claude/OpenAI Embeddings API | Embedding API entegre, vektör DB ve retrieval pipeline kendimiz inşa. SAP knowledge base'i bizim domain |
| **Rule Engine** | BUILD | Python celery + custom rule DSL | SAP Activate faz kuralları, KPI threshold'ları, workflow tetikleyicileri tamamen domain'e özel |
| **Graph Analyzer** | BUILD | PostgreSQL recursive CTE + NetworkX | Traceability zinciri platformun veri modelinde yaşıyor; graph traversal ve CPM analizi kendimiz inşa |
| **Prompt Registry** | BUILD | PostgreSQL + versioning | Her asistanın prompt şablonları, SAP terminolojisi, modül bağlamı — tamamen domain'e özel |
| **SAP Knowledge Base** | BUILD | Markdown/JSON corpus + pgvector | SAP Best Practice scope items, modül kataloğu, FS/TS şablonları, hata pattern'leri |
| **Suggestion Queue** | BUILD | PostgreSQL + WebSocket | Human-in-the-loop pattern: tüm AI önerileri burada bekler, onay/ret akışı |
| **STT (Speech-to-Text)** | INTEGRATE | OpenAI Whisper API veya Google Cloud STT | Toplantı transkripsiyon; build etmek gereksiz, API yeterli |

### 10.3 LLM Gateway Detay Tasarımı

```
┌──────────────────────────────────────────────────────────────┐
│                      LLM GATEWAY                              │
│                                                               │
│  Request                                                      │
│    │                                                          │
│    ▼                                                          │
│  ┌──────────────────┐                                        │
│  │ Prompt Builder   │ ← Prompt Registry (versioned templates)│
│  │                  │ ← SAP Context Injector (module, phase) │
│  │                  │ ← RAG Retriever (relevant docs/history)│
│  └────────┬─────────┘                                        │
│           ▼                                                   │
│  ┌──────────────────┐                                        │
│  │ Provider Router  │                                        │
│  │                  │                                        │
│  │  Task Type → Provider mapping:                            │
│  │  ├─ Classification → Claude Haiku (hızlı, ucuz)          │
│  │  ├─ Generation    → Claude Sonnet (dengeli)               │
│  │  ├─ Complex Reasoning → Claude Opus (en yetenekli)       │
│  │  ├─ Embeddings    → OpenAI text-embedding-3-large        │
│  │  └─ Fallback      → OpenAI GPT-4o (provider down durumu) │
│  └────────┬─────────┘                                        │
│           ▼                                                   │
│  ┌──────────────────┐                                        │
│  │ Response Handler │                                        │
│  │  ├─ Parse & validate structured output                    │
│  │  ├─ Token usage tracking (cost monitoring)                │
│  │  ├─ Latency logging                                       │
│  │  └─ Audit trail (prompt + response hash)                  │
│  └────────┬─────────┘                                        │
│           ▼                                                   │
│  Suggestion Queue (pending human review)                      │
└──────────────────────────────────────────────────────────────┘
```

**API Maliyet Yönetimi:**

| Model | Kullanım | Tahmini Birim Maliyet | Aylık Hacim Tahmini |
|-------|----------|----------------------|---------------------|
| Claude Haiku | Sınıflandırma, triage, kısa analiz | ~$0.25/1M input token | 5-10M token |
| Claude Sonnet | FS taslağı, test case, rapor üretme | ~$3/1M input token | 2-5M token |
| Claude Opus | Karmaşık analiz, etki değerlendirme | ~$15/1M input token | 0.5-1M token |
| OpenAI Embeddings | Vektör oluşturma | ~$0.13/1M token | 1-3M token |
| Whisper API | Toplantı transkripsiyon | ~$0.006/dakika | 100-300 dakika |

**Tahmini aylık AI API maliyeti: $50-200** (orta ölçekli proje, 50-100 kullanıcı)

### 10.4 RAG Pipeline Detay Tasarımı

```
┌──────────────────────────────────────────────────────────────────┐
│                        RAG PIPELINE                               │
│                                                                   │
│  INDEXING (Arka plan, sürekli)                                   │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │ Kaynak   │    │ Chunker      │    │ Embedding +          │   │
│  │ Veriler  │───▶│              │───▶│ pgvector Store       │   │
│  │          │    │ SAP-aware    │    │                      │   │
│  │• Req'ler │    │ chunking:    │    │ Her chunk:           │   │
│  │• FS/TS   │    │ • Requirement│    │ • embedding vector   │   │
│  │• Defect  │    │   başına     │    │ • source_type        │   │
│  │• KB art. │    │ • FS section │    │ • module             │   │
│  │• Meeting │    │   başına     │    │ • workstream         │   │
│  │  notes   │    │ • Defect     │    │ • phase              │   │
│  │• SAP BP  │    │   başına     │    │ • project_id         │   │
│  │  catalog │    │ • KB article │    │ • timestamp          │   │
│  └──────────┘    │   başına     │    └──────────────────────┘   │
│                  └──────────────┘                                 │
│                                                                   │
│  RETRIEVAL (Sorgu zamanı)                                        │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │ Kullanıcı│    │ Query        │    │ Hybrid Search        │   │
│  │ Sorusu / │───▶│ Embedding    │───▶│                      │   │
│  │ AI Ctx   │    │              │    │ 1. Semantic (cosine) │   │
│  └──────────┘    └──────────────┘    │ 2. Keyword (FTS)     │   │
│                                      │ 3. Metadata filter   │   │
│                                      │    (module, phase,   │   │
│                                      │     workstream)      │   │
│                                      │ 4. Re-rank (cross-   │   │
│                                      │    encoder)          │   │
│                                      └──────────┬───────────┘   │
│                                                  ▼               │
│                                      ┌──────────────────────┐   │
│                                      │ Top-K Chunks         │   │
│                                      │ → LLM Context Window │   │
│                                      └──────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

**PostgreSQL + pgvector kurulumu:**

```sql
-- pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Ana embedding tablosu
CREATE TABLE ai_embeddings (
    id              BIGSERIAL PRIMARY KEY,
    source_type     VARCHAR(50) NOT NULL,  -- 'requirement','wricef_fs','defect','kb_article','sap_bp'
    source_id       BIGINT NOT NULL,        -- İlgili kaydın ID'si
    chunk_index     INT DEFAULT 0,
    chunk_text      TEXT NOT NULL,
    embedding       vector(3072),           -- OpenAI text-embedding-3-large boyutu
    module          VARCHAR(20),            -- 'FI','MM','SD','PP' vb.
    workstream      VARCHAR(50),
    project_id      BIGINT,
    phase           VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW indeks (hızlı similarity search)
CREATE INDEX idx_embeddings_hnsw ON ai_embeddings 
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Metadata filtreleme için
CREATE INDEX idx_embeddings_source ON ai_embeddings (source_type, project_id, module);

-- Hybrid search: full-text search indeksi
ALTER TABLE ai_embeddings ADD COLUMN tsv tsvector 
    GENERATED ALWAYS AS (to_tsvector('simple', chunk_text)) STORED;
CREATE INDEX idx_embeddings_fts ON ai_embeddings USING gin(tsv);
```

### 10.5 Human-in-the-Loop Pattern: Suggestion Queue

Tüm 14 asistan aynı onay mekanizmasını kullanır:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SUGGESTION QUEUE                               │
│                                                                   │
│  AI Asistan                                                       │
│    │                                                              │
│    ▼                                                              │
│  ┌──────────────────┐                                            │
│  │ Suggestion       │                                            │
│  │ {                │                                            │
│  │   id,            │                                            │
│  │   assistant_type,│  ← Hangi asistan üretti                    │
│  │   target_module, │  ← Hangi modüle ait                       │
│  │   target_entity, │  ← Hangi kayıt (req, defect, vb.)         │
│  │   suggestion_type│  ← classify / generate / recommend / alert │
│  │   content,       │  ← AI'ın ürettiği içerik (JSON)           │
│  │   confidence,    │  ← 0.0 - 1.0 güven skoru                  │
│  │   context,       │  ← Kullanılan RAG kaynakları               │
│  │   status,        │  ← pending / approved / rejected / modified│
│  │   reviewer_id,   │  ← Kim review edecek                      │
│  │   reviewed_at,   │                                            │
│  │   reviewer_note  │  ← Neden kabul/ret edildi                  │
│  │ }                │                                            │
│  └────────┬─────────┘                                            │
│           │                                                       │
│    ┌──────┴──────────────────────────────┐                       │
│    │            │            │            │                       │
│    ▼            ▼            ▼            ▼                       │
│  APPROVE     REJECT      MODIFY      AUTO-APPROVE               │
│  (kayıt      (log +      (düzelt +   (confidence > 0.95         │
│   oluşur)    feedback    kayıt       + düşük risk               │
│              → model     oluşur)     → sadece read-only         │
│              iyileşir)               sorgularda)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### 10.6 Asistan Detayları: Faz 1 — Foundation AI (Platform ile paralel)

> **Altyapı:** LLM Gateway + RAG Pipeline + Suggestion Queue bu fazda kurulur.
> Tüm sonraki fazlardaki asistanlar bu altyapıyı kullanır.

#### 10.6.1 — Natural Language Query Assistant

| Özellik | Detay |
|---------|-------|
| **Modül** | Cross-cutting (tüm modüller) |
| **Ne Yapar** | Kullanıcı doğal dilde soru sorar → AI soruyu API sorgusuna/SQL'e çevirir → sonucu görselleştirir |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── Text-to-SQL converter
│   ├── Platform DB şeması → LLM context olarak verilir
│   ├── Doğal dil → SQL dönüşümü (LLM)
│   ├── SQL validation & sanitization (injection koruması)
│   └── Sonuç → doğal dil açıklama + tablo/chart
│
├── SAP terminoloji sözlüğü
│   ├── "WRICEF" → wricef_items tablosu
│   ├── "P1 defect" → defects WHERE severity = 'P1'
│   ├── "O2C" → workstream = 'O2C'
│   └── Türkçe-İngilizce karma sorgulama desteği
│
└── Query güvenlik katmanı
    ├── Sadece SELECT sorguları (read-only)
    ├── Row-level security (kullanıcının yetkili olduğu veriler)
    └── Karmaşık sorgularda "Bu doğru mu?" onay adımı

INTEGRATE (API):
├── Claude Haiku API → hızlı text-to-SQL dönüşüm
├── Claude Sonnet API → karmaşık sorgularda fallback
└── OpenAI Embeddings → semantik sorgularda RAG retrieval
```

**Teknik Akış:**

```python
# Örnek: "O2C'de kaç open P1 defect var?"
async def nl_query(user_question: str, user_context: dict):
    # 1. Schema context hazırla
    schema_ctx = get_relevant_tables(user_question)  # embeddings ile
    
    # 2. LLM'e gönder
    response = await llm_gateway.call(
        model="claude-haiku",
        system_prompt=NL_QUERY_PROMPT_TEMPLATE,
        context={
            "schema": schema_ctx,
            "sap_glossary": SAP_TERM_MAP,
            "user_permissions": user_context["allowed_projects"],
            "question": user_question
        }
    )
    
    # 3. SQL çıktısını validate et
    sql = validate_readonly_sql(response.sql)
    
    # 4. Karmaşık mı? Onay iste
    if response.complexity == "high":
        return SuggestionQueue.create(
            type="query_confirmation",
            content={"sql": sql, "explanation": response.explanation},
            auto_approve=False
        )
    
    # 5. Çalıştır ve sonuç döndür
    result = await db.execute(sql)
    return format_response(result, response.explanation)
```

#### 10.6.2 — Requirement Analyst Copilot

| Özellik | Detay |
|---------|-------|
| **Modül** | Explore Phase Manager |
| **Ne Yapar** | Workshop notları/açıklamadan Fit/Partial Fit/Gap ön sınıflandırması + benzer geçmiş requirement önerileri |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── SAP Best Practice Scope Item veritabanı
│   ├── S/4HANA scope item kataloğu (JSON/YAML)
│   ├── Modül bazlı sınıflandırma kuralları
│   ├── Sektöre özel şablonlar (kimya, otomotiv, perakende)
│   └── Her scope item için "standart kapsam" açıklaması
│
├── Classification pipeline
│   ├── Input: requirement açıklaması + scope item ref
│   ├── LLM classification: Fit / Partial Fit / Gap
│   ├── Confidence score hesaplama
│   ├── Gap ise → WRICEF tipi önerisi (W/R/I/C/E/F)
│   └── Output → Suggestion Queue (pending review)
│
├── Similarity search
│   ├── Yeni requirement embedding → pgvector search
│   ├── Aynı/farklı projelerden benzer requirement'lar
│   └── "Bu requirement'a benzer 3 geçmiş karar" önerisi
│
└── Feedback loop
    ├── Onay/ret verileri → fine-tuning dataset
    ├── Proje bazlı accuracy tracking
    └── Confidence threshold otomatik ayarlama

INTEGRATE (API):
├── Claude Sonnet API → sınıflandırma + açıklama üretme
├── OpenAI Embeddings API → requirement vektörleri
└── (Opsiyonel) SAP Signavio API → süreç modeli referansı
```

**Prompt Şablonu (Prompt Registry'de versiyonlanır):**

```yaml
assistant: requirement_analyst
version: 1.2
model: claude-sonnet
template: |
  Sen bir SAP S/4HANA dönüşüm uzmanısın. Aşağıdaki requirement açıklamasını
  analiz et ve SAP Best Practice scope item'ı ile karşılaştır.
  
  ## Scope Item Bilgisi
  {scope_item_name}: {scope_item_description}
  SAP Standard Kapsam: {scope_item_standard_coverage}
  
  ## Requirement Açıklaması
  {requirement_description}
  
  ## Benzer Geçmiş Requirement'lar
  {similar_requirements_from_rag}
  
  ## Görevin
  1. Bu requirement'ı sınıflandır: Fit / Partial Fit / Gap
  2. Sınıflandırma gerekçeni açıkla (2-3 cümle)
  3. Partial Fit veya Gap ise: eksik olan kısmı tanımla
  4. Gap ise: WRICEF tipi öner (W/R/I/C/E/F) ve kısa gerekçe
  5. Güven skorun (0.0-1.0) ne?
  
  JSON formatında yanıt ver.
```

#### 10.6.3 — Defect Triage Assistant

| Özellik | Detay |
|---------|-------|
| **Modül** | Test Management System |
| **Ne Yapar** | Yeni defect → severity önerisi + duplicate tespiti + root cause tahmini + ilgili WRICEF bağlama |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── Defect classification pipeline
│   ├── Input: defect title + description + screenshot (opsiyonel)
│   ├── Severity önerisi (P1/P2/P3/P4) — geçmiş defect'lerden pattern
│   ├── SAP modül/workstream routing
│   ├── SAP transaction code tanıma (regexp + NER)
│   └── Output → "AI Suggestion" badge ile defect formunda göster
│
├── Duplicate detection
│   ├── Yeni defect embedding → mevcut açık defect'ler ile cosine similarity
│   ├── Threshold > 0.85 → "Possible duplicate" uyarısı
│   ├── Benzer defect'lerin link'leri gösterilir
│   └── Merge kararı her zaman insanda
│
├── Root cause suggestion
│   ├── Defect açıklaması + hata mesajı → RAG ile KB search
│   ├── Aynı WRICEF/config item'daki geçmiş defect'ler
│   ├── SAP known error patterns (OSS notes referansı)
│   └── "Olası root cause" ve "önerilen çözüm adımı"
│
└── Auto-enrichment
    ├── Eksik alan tespiti ("Description çok kısa, lütfen adımları ekleyin")
    ├── Otomatik tag önerisi (module, process area, interface)
    └── İlgili WRICEF/config item bağlama önerisi

INTEGRATE (API):
├── Claude Haiku API → hızlı sınıflandırma (severity, routing)
├── Claude Sonnet API → root cause analizi
├── OpenAI Embeddings API → duplicate detection, similarity
└── (Opsiyonel) Claude Vision API → screenshot'tan hata mesajı okuma
```

---

### 10.7 Asistan Detayları: Faz 2 — Core AI (Modüller olgunlaştıkça)

#### 10.7.1 — Steering Pack Generator

| Özellik | Detay |
|---------|-------|
| **Modül** | Reporting Engine |
| **Ne Yapar** | Tüm modüllerden KPI çeker → RAG status → narrative özet → sunum paketi |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── KPI Aggregation Engine
│   ├── Her modülden haftalık/aylık snapshot
│   ├── RAG (Red/Amber/Green) hesaplama kuralları
│   │   ├── RED: P1 defect > 0, milestone miss, budget overrun > 10%
│   │   ├── AMBER: trend kötüleşiyor, risk score artıyor
│   │   └── GREEN: plan dahilinde
│   └── Trend grafiği veri hazırlama
│
├── Narrative Generator
│   ├── KPI verileri + RAG status → LLM'e gönder
│   ├── Structured output: executive summary, key risks,
│   │   decisions needed, achievements, next steps
│   └── Tutarlı format: her hafta karşılaştırılabilir
│
├── Steering Pack Formatter
│   ├── PPTX/PDF şablon (kurumsal branding)
│   ├── Grafik/chart otomatik oluşturma (matplotlib/plotly)
│   └── Export: PowerPoint, PDF, e-posta HTML
│
└── PMO Review workflow
    ├── Taslak → PMO Lead inbox
    ├── Inline editing
    ├── RAG status override (insanın final kararı)
    └── Onay → dağıtım

INTEGRATE (API):
├── Claude Sonnet API → narrative üretme, risk özeti
├── python-pptx → PowerPoint oluşturma
└── (Opsiyonel) MS Teams/Slack API → otomatik dağıtım
```

#### 10.7.2 — Risk Sentinel

| Özellik | Detay |
|---------|-------|
| **Modül** | RAID (Cross-cutting) |
| **Ne Yapar** | Tüm modüllerin KPI'larını izler → risk sinyalleri → trend analizi → proaktif uyarı |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── Rule Engine (Phase 1 — kural tabanlı)
│   ├── Playbook §8 risk pattern'leri:
│   │   ├── backlog_growth_rate > 15%/hafta → Scope Creep sinyali
│   │   ├── defect_aging_avg(P1) > 5 gün → Go-Live Risk
│   │   ├── data_quality_score < 80% → Data Readiness
│   │   ├── interface_connectivity_fail > 10% → Integration Risk
│   │   ├── training_attendance < 70% → Change Mgmt Risk
│   │   ├── atc_finding_growth > 20%/hafta → Custom Code Risk
│   │   └── cutover_rehearsal_delta > 20% → Cutover Risk
│   ├── Threshold'lar proje tipine göre ayarlanabilir
│   └── Faz bazlı ağırlıklandırma (Realize'da test riski > Explore'da)
│
├── Anomaly Detection (Phase 2 — ML ile zenginleştirme)
│   ├── Time-series anomaly (isolation forest / prophet)
│   ├── Geçmiş proje verileriyle karşılaştırma
│   └── "Normal dışı trend" erken uyarısı
│
├── Risk Report Generator
│   ├── Haftalık risk özeti (LLM ile narrative)
│   ├── Trend grafiği (risk score timeline)
│   ├── Mitigation önerisi (Playbook'tan kural bazlı)
│   └── PMO Lead inbox'a teslim
│
└── Alert & Notification
    ├── Risk skoru değişikliğinde (Med→High) → PMO Lead onay gerekir
    ├── Kritik risk → Slack/Teams notification
    └── Steering pack'e otomatik ekleme

INTEGRATE (API):
├── Claude Haiku API → risk sinyali açıklama metni
├── Claude Sonnet API → haftalık risk narrative
├── (İleri faz) scikit-learn/prophet → anomaly detection
└── Slack/Teams API → alert notification
```

#### 10.7.3 — AI Work Breakdown Engine (YENİ — Benchmark gap'inden eklendi)

| Özellik | Detay |
|---------|-------|
| **Modül** | Explore Phase Manager + Backlog Workbench |
| **Ne Yapar** | Scenario → workshop planı → Fit-Gap item → WRICEF görev otomatik kırılımı |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── SAP Process Hierarchy Template DB
│   ├── O2C, P2P, RTR, SCM, PP/QM/PM süreç ağaçları
│   ├── Her L1 süreç için tipik L2/L3 kırılım
│   ├── Sektöre özel varyasyonlar (kimya → batch mgmt, otomotiv → kanban)
│   └── SAP Best Practice scope item → süreç eşlemesi
│
├── Breakdown Generator
│   ├── Input: Scenario seçimi (örn. "O2C") + proje tipi + sektör
│   ├── LLM + template DB → workshop planı önerisi
│   ├── Workshop başına tahmini Fit-Gap item listesi
│   ├── Gap item'lar için WRICEF tipi + effort tahmini
│   └── Output → Suggestion Queue (workstream lead review)
│
└── Effort Estimation
    ├── Geçmiş projelerden WRICEF tipi bazlı effort ortalaması
    ├── Kompleksite faktörleri (interface sayısı, data volume)
    └── Confidence interval ile tahmini FTE/saat

INTEGRATE (API):
├── Claude Sonnet API → kırılım üretme, estimation
└── OpenAI Embeddings → geçmiş proje pattern retrieval
```

#### 10.7.4 — WRICEF Spec Drafter

| Özellik | Detay |
|---------|-------|
| **Modül** | Backlog Workbench |
| **Ne Yapar** | Gap requirement'tan FS (Functional Spec) taslağı + TS anahatlığı oluşturur |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── FS Template Engine
│   ├── WRICEF tipine göre FS şablonu (Report, Interface, Enhancement, Form, Workflow)
│   ├── Standart bölümler: Amaç, Tetikleyici, Ön Koşullar,
│   │   İş Kuralları, Veri Akışı, Hata Yönetimi, Test Senaryoları
│   ├── SAP modül bazlı teknik referanslar
│   │   ├── FI: BAPI_*, posting logic, clearing rules
│   │   ├── MM: procurement flow, GR/IR, batch determination
│   │   ├── SD: pricing, output, delivery, billing
│   │   └── PP: routing, BOM, MRP, production order
│   └── Şablon versiyonlama ve kurum bazlı özelleştirme
│
├── Spec Generation Pipeline
│   ├── Input: requirement desc + gap desc + scope item context
│   ├── RAG: benzer geçmiş FS'ler retrieve et
│   ├── LLM: şablon + context + similar specs → FS taslağı
│   ├── Otomatik cross-reference: ilgili config, interface, auth
│   └── Output → Draft statüsünde Backlog'a ekle
│
├── TS Outline Generator
│   ├── FS onaylandıktan sonra → TS anahatlığı
│   ├── Teknik yaklaşım önerisi (enhancement, BAdI, BTP extension)
│   └── Development effort re-estimation
│
└── Quality Check
    ├── Eksik bölüm tespiti ("Hata yönetimi bölümü boş")
    ├── İç tutarlılık kontrolü
    └── Spec Reviewer (Asana referansı) → belirsiz gereksinim tespiti

INTEGRATE (API):
├── Claude Opus API → karmaşık FS üretimi (en yetenekli model gerekli)
├── Claude Sonnet API → TS outline, quality check
├── OpenAI Embeddings → benzer FS retrieval
└── python-docx / Markdown → doküman export
```

---

### 10.8 Asistan Detayları: Faz 3 — Quality AI (Test ve veri odaklı)

#### 10.8.1 — Test Scenario Generator

| Özellik | Detay |
|---------|-------|
| **Modül** | Test Management System |
| **Ne Yapar** | Requirement + WRICEF'ten test case taslakları üretir; pozitif/negatif/boundary case önerir |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── Test Case Template Engine
│   ├── Test katmanı bazlı şablonlar (Unit, SIT, UAT, Regression)
│   ├── SAP E2E süreç akış bilgisi
│   │   ├── O2C: Sales Order → Delivery → Billing → Payment
│   │   ├── P2P: PR → PO → GR → Invoice → Payment
│   │   └── RTR: Journal Entry → Clearing → Closing → Report
│   ├── Her adım için tipik test senaryoları (happy path + edge case)
│   └── Interface test pattern'leri (inbound/outbound)
│
├── Scenario Generation Pipeline
│   ├── Input: requirement + WRICEF FS + acceptance criteria
│   ├── LLM: pozitif, negatif, boundary case üretimi
│   ├── SIT chaining: E2E akış boyunca test case'leri zincirle
│   ├── Coverage gap analizi: "Bu requirement için X senaryosu eksik"
│   └── Output → Suggested statüsünde Test Catalog'a ekle
│
└── Traceability auto-link
    ├── Her test case → kaynak requirement otomatik bağlantı
    ├── Coverage oranı hesaplama
    └── Eksik coverage raporu

INTEGRATE (API):
├── Claude Sonnet API → test case üretme
└── OpenAI Embeddings → benzer test case retrieval
```

#### 10.8.2 — Data Quality Guardian

| Özellik | Detay |
|---------|-------|
| **Modül** | Data Factory |
| **Ne Yapar** | Load cycle sonrası veri kalite analizi, cleansing önerisi, trend raporu |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── Data Profiling Engine (tamamen build — domain'e özel)
│   ├── Completeness: boş/null alan oranı (alan bazlı)
│   ├── Uniqueness: duplikasyon tespiti (fuzzy matching)
│   ├── Format validation: SAP alan formatları
│   │   ├── Material number (MATNR) format kontrolü
│   │   ├── Customer/Vendor number format
│   │   ├── GL Account yapısı
│   │   └── Date format, currency codes
│   ├── Referential integrity: FK ilişkileri
│   │   ├── Customer → Company Code
│   │   ├── Material → Plant
│   │   └── Vendor → Purchasing Organization
│   ├── Business rule validation
│   │   ├── Negatif fiyat kontrolü
│   │   ├── Mandatory field combinations
│   │   └── Cross-field consistency
│   └── Sonuç: alan bazlı kalite skoru (0-100)
│
├── Cleansing Recommender
│   ├── Kalite raporu + hata pattern'leri → LLM
│   ├── Cleansing önerisi (düzeltme tavsiyesi, asla otomatik düzeltme)
│   ├── Öncelik sıralaması (iş etkisine göre)
│   └── Data Owner'a sunum
│
├── Cycle Comparison Dashboard
│   ├── Cycle N vs Cycle N-1 trend grafiği
│   ├── İyileşme/kötüleşme vurgulama
│   └── Readiness skoru (ağırlıklı ortalama)
│
└── Reconciliation Helper
    ├── Kaynak vs hedef karşılaştırma
    ├── Fark raporu (eksik/fazla/uyumsuz kayıtlar)
    └── Business sign-off workflow

INTEGRATE (API):
├── Claude Haiku API → cleansing öneri metni
├── pandas / Great Expectations → veri profiling (Python library, API değil)
└── (Opsiyonel) SAP LTMC API → load sonuç verisi çekme
```

#### 10.8.3 — Impact Analyzer

| Özellik | Detay |
|---------|-------|
| **Modül** | Backlog Workbench + Test Management System (Cross-cutting) |
| **Ne Yapar** | Bir requirement/WRICEF değiştiğinde traceability zinciri boyunca etki raporu |
| **Build vs. Integrate** | |

```
BUILD (kendimiz — tamamen platform veri modeli üzerine):
├── Graph Traversal Engine
│   ├── Traceability zinciri: Req → WRICEF → FS → Test Case → Defect → Cutover
│   ├── Yukarı (upstream) ve aşağı (downstream) traversal
│   ├── PostgreSQL recursive CTE ile uygulama
│   └── NetworkX ile görselleştirme (dependency graph)
│
├── Direct Impact Analysis
│   ├── Değişen entity'den doğrudan bağlı entity'ler
│   ├── Her bağlı entity için impact tipi:
│   │   ├── Test Case → "Re-execute gerekli"
│   │   ├── FS/TS → "Revision gerekli"
│   │   ├── Cutover Task → "Güncelleme gerekli"
│   │   └── Training Material → "Revize edilmeli"
│   └── Otomatik mail/notification → ilgili owner'lara
│
├── Indirect Impact Analysis (LLM destekli)
│   ├── Aynı interface'i kullanan diğer süreçler
│   ├── Aynı master data'yı paylaşan diğer modüller
│   ├── Aynı authorization role'ünü kullanan kullanıcılar
│   └── LLM: "Bu değişikliğin dolaylı etkisi olabilecek alanlar"
│
└── Impact Report
    ├── Workstream lead'lerine etki raporu
    ├── Her etkilenen item için: acknowledge / not applicable
    ├── Regression test kapsamı önerisi
    └── Hiçbir şey otomatik değiştirilmez — sadece görünürlük

INTEGRATE (API):
├── Claude Sonnet API → dolaylı etki analizi (semantik reasoning)
└── NetworkX (Python library) → graph analizi ve görselleştirme
```

---

### 10.9 Asistan Detayları: Faz 4 — Go-Live AI (Cutover ve operasyon)

#### 10.9.1 — Cutover Runbook Optimizer

| Özellik | Detay |
|---------|-------|
| **Modül** | Cutover Hub |
| **Ne Yapar** | Runbook bağımlılık analizi, kritik yol, paralelize edilebilirlik, rehearsal'dan öğrenme |
| **Build vs. Integrate** | |

```
BUILD (kendimiz — tamamen algoritmik + domain):
├── Critical Path Engine
│   ├── CPM (Critical Path Method) algoritması
│   ├── Task bağımlılıkları → DAG (Directed Acyclic Graph)
│   ├── Kritik yol vurgulama + slack time hesaplama
│   └── Gantt chart otomatik oluşturma
│
├── Parallelization Analyzer
│   ├── Bağımsız task gruplarını tespit et
│   ├── Kaynak çakışması kontrolü (aynı kişi 2 task'ta mı?)
│   ├── "Bu 3 task paralel çalışabilir → 4 saat kazanım" önerisi
│   └── What-if analizi: "X task'ı 2 saat kısalırsa ne olur?"
│
├── Rehearsal Learning Engine
│   ├── Rehearsal N: plan vs actual → delta analizi
│   ├── Sürekli yavaş kalan task'ları işaretle
│   ├── Süre tahminlerini güncelle (geçmiş rehearsal ortalaması)
│   └── Rehearsal N+1 için optimize edilmiş plan öner
│
├── SAP Cutover Pattern DB
│   ├── Standart SAP cutover sırası bilgisi:
│   │   1. System prep → 2. Config transport → 3. Master data load
│   │   4. Open item migration → 5. Interface switch → 6. Auth activation
│   │   7. Job scheduling → 8. Reconciliation → 9. Go/No-Go
│   └── Her adım için tipik süre ve risk faktörleri
│
└── Rollback Decision Support
    ├── Her decision point için rollback impact analizi
    ├── "Point of no return" açık işaretleme
    └── Otomatik karar ALINMAZ — insana görünürlük sağlar

INTEGRATE (API):
├── Claude Sonnet API → rehearsal delta açıklama, what-if narrative
└── NetworkX / graphlib → DAG analizi, CPM hesaplama
```

#### 10.9.2 — Hypercare War Room Assistant

| Özellik | Detay |
|---------|-------|
| **Modül** | Run/Sustain |
| **Ne Yapar** | Incident sınıflandırma, pattern tespiti, çözüm önerisi, executive günlük rapor |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── Incident Triage Engine (Defect Triage #4 üzerine genişletilir)
│   ├── Severity önerisi + SAP modül routing
│   ├── Benzer geçmiş incident → çözüm önerisi
│   ├── Knowledge base RAG → "Bu hata için bilinen çözüm"
│   └── SLA tracking + escalation alert
│
├── Pattern Detection
│   ├── Clustering: son 24 saatteki incident'lar → grupla
│   ├── "SD modülünde delivery ile ilgili 8 incident — cluster mı?"
│   ├── Aynı root cause → toplu çözüm önerisi
│   └── Trend analizi: artış/azalış tespiti
│
├── Executive Daily Report Generator
│   ├── Günlük KPI'lar: açık/kapatılan/yeni incident
│   ├── SLA compliance oranı
│   ├── Top 5 etkilenen süreç
│   ├── Kritik aksiyonlar ve owner'lar
│   └── Support Lead review → gönderim
│
└── Knowledge Base Builder
    ├── Çözülen incident'lardan otomatik KB article taslağı
    ├── Support ekibi review → yayınlama
    └── SAP OSS note referans bağlama

INTEGRATE (API):
├── Claude Haiku API → incident sınıflandırma (hızlı triage)
├── Claude Sonnet API → pattern analizi, KB article, daily report
├── OpenAI Embeddings → incident similarity, KB search
├── scikit-learn (kmeans/dbscan) → incident clustering
└── (Opsiyonel) ServiceNow API → incident sync
```

---

### 10.10 Asistan Detayları: Faz 5 — Advanced AI (Olgunlaşma)

#### 10.10.1 — Meeting Intelligence Agent

| Özellik | Detay |
|---------|-------|
| **Modül** | Cross-cutting |
| **Ne Yapar** | Toplantı transkript → aksiyon item, karar, risk sinyali çıkarma → ilgili modüllere dağıtım |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── Transcript Processing Pipeline
│   ├── Audio → STT (Whisper API)
│   ├── Diarization (konuşmacı ayrımı)
│   ├── SAP terminoloji tanıma (custom vocabulary)
│   └── Türkçe/İngilizce karma metin desteği
│
├── Extraction Engine
│   ├── Aksiyon item'ları çıkarma → RAID Action'a
│   ├── Kararları çıkarma → RAID Decision'a
│   ├── Risk sinyalleri → RAID Risk'e
│   ├── Requirement mentions → Scope modülüne bağla
│   ├── Defect mentions → Test Management'a bağla
│   └── Her extracted item: confidence score + source timestamp
│
├── Entity Resolution (en zor kısım)
│   ├── "O2C'deki şu interface sorunu" → hangi interface?
│   ├── "Ahmet'in bakacağı konu" → hangi team member?
│   ├── Ambiguous referanslar → "Eşleşme bulunamadı, lütfen belirtin"
│   └── Platform entity'leri ile fuzzy matching
│
└── Dağıtım
    ├── Çıkarılan item'lar → Pending Review statüsünde ilgili modüle
    ├── Toplantı sahibi review → onay/ret/düzeltme
    └── Toplantı özeti → katılımcılara e-posta

INTEGRATE (API):
├── OpenAI Whisper API → transkripsiyon ($0.006/dakika)
├── Claude Sonnet API → extraction, entity resolution
├── (Opsiyonel) Microsoft Teams API → toplantı kaydı alma
├── (Opsiyonel) Google Meet API → toplantı kaydı alma
└── (Opsiyonel) pyannote-audio → speaker diarization (self-hosted)
```

#### 10.10.2 — Natural Language Workflow Builder (YENİ — Benchmark gap'inden eklendi)

| Özellik | Detay |
|---------|-------|
| **Modül** | Cross-cutting (Otomasyon katmanı) |
| **Ne Yapar** | Doğal dille otomasyon kuralı tanımlama → platform workflow'a dönüştürme |
| **Build vs. Integrate** | |

```
BUILD (kendimiz):
├── NL-to-Workflow Compiler
│   ├── Input: "Fit-Gap item Approved olduğunda WRICEF görevi oluştur,
│   │   Technical Lead'e ata, 5 iş günü deadline belirle"
│   ├── LLM parse: trigger + condition + action(s) çıkar
│   ├── Platform workflow DSL'e dönüştür:
│   │   {
│   │     trigger: { entity: "requirement", event: "status_change", value: "Approved" },
│   │     conditions: [{ field: "fit_status", operator: "in", values: ["Gap","Partial Fit"] }],
│   │     actions: [
│   │       { type: "create_wricef", copy_fields: ["title","description","workstream"] },
│   │       { type: "assign", role: "technical_lead", workstream: "$source.workstream" },
│   │       { type: "set_deadline", business_days: 5 }
│   │     ]
│   │   }
│   └── Önizleme: "Bu kural şunu yapacak: ..." → kullanıcı onayı
│
├── Workflow Execution Engine
│   ├── Event-driven: entity değişikliği → rule evaluation
│   ├── Celery task queue ile asenkron çalışma
│   ├── Her çalışma loglarda görünür
│   └── Hata durumunda → notification, retry policy
│
└── Güvenlik
    ├── Admin onayı: yeni kural → admin review → aktif
    ├── Dry-run modu: "Bu kural son 7 günde 12 kez tetiklenirdi"
    ├── Rate limiting: runaway rule koruması
    └── Rollback: kuralı devre dışı bırak + geri al

INTEGRATE (API):
├── Claude Sonnet API → NL parsing, rule generation
└── Celery + Redis → async workflow execution
```

---

### 10.11 Teknoloji Stack Özeti: AI Katmanı

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AI TECHNOLOGY STACK                               │
│                                                                     │
│  EXTERNAL APIs (INTEGRATE)                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ Anthropic    │ │ OpenAI       │ │ Cloud STT    │               │
│  │ Claude API   │ │ API          │ │              │               │
│  │              │ │              │ │ Whisper API  │               │
│  │ • Haiku      │ │ • Embeddings │ │ veya         │               │
│  │   (classify) │ │   (3072-dim) │ │ Google STT   │               │
│  │ • Sonnet     │ │ • GPT-4o     │ │              │               │
│  │   (generate) │ │   (fallback) │ │              │               │
│  │ • Opus       │ │              │ │              │               │
│  │   (complex)  │ │              │ │              │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  SELF-HOSTED / BUILD                                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ pgvector     │ │ Celery +     │ │ NetworkX     │               │
│  │ (PostgreSQL) │ │ Redis        │ │              │               │
│  │              │ │              │ │ Graph        │               │
│  │ Vector store │ │ Async task   │ │ analysis,    │               │
│  │ + hybrid     │ │ queue,       │ │ CPM, impact  │               │
│  │ search       │ │ workflow     │ │ traversal    │               │
│  │              │ │ execution    │ │              │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ scikit-learn │ │ pandas /     │ │ python-pptx  │               │
│  │              │ │ Great Expect.│ │ / WeasyPrint │               │
│  │ Clustering,  │ │              │ │              │               │
│  │ anomaly      │ │ Data         │ │ Report       │               │
│  │ detection    │ │ profiling,   │ │ export:      │               │
│  │              │ │ quality      │ │ PPTX, PDF    │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  SAP DOMAIN KNOWLEDGE (BUILD — en kritik farklılaşma)             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • SAP Best Practice Scope Item Kataloğu                     │   │
│  │ • S/4HANA Modül Yapısı (FI, CO, MM, SD, PP, QM, PM, EWM)  │   │
│  │ • SAP E2E Süreç Akışları (O2C, P2P, RTR, SCM)             │   │
│  │ • WRICEF FS/TS Şablonları (modül ve tip bazlı)             │   │
│  │ • SAP Cutover Pattern'leri                                  │   │
│  │ • SAP Data Migration Kuralları (alan formatları, FK ilişki) │   │
│  │ • SAP Known Error Pattern DB                                │   │
│  │ • SAP Activate Faz/Gate Kuralları                          │   │
│  │ • Sektöre Özel SAP Konfigürasyon Şablonları                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 10.12 API Endpoints: AI Katmanı

```
/api/v1/ai/
├── /query
│   ├── POST   /natural-language        # NL Query Assistant
│   └── GET    /query-history            # Geçmiş sorgular
│
├── /suggestions
│   ├── GET    /?status=pending&module=  # Bekleyen öneriler
│   ├── PUT    /:suggestionId/approve    # Onayla
│   ├── PUT    /:suggestionId/reject     # Reddet
│   ├── PUT    /:suggestionId/modify     # Düzenle + onayla
│   └── GET    /stats                    # Onay/ret oranları
│
├── /requirements
│   ├── POST   /classify                 # Requirement Analyst
│   ├── POST   /find-similar             # Benzer requirement ara
│   └── POST   /breakdown                # Work Breakdown Engine
│
├── /backlog
│   ├── POST   /draft-spec               # WRICEF Spec Drafter
│   ├── POST   /quality-check            # Spec quality kontrol
│   └── POST   /impact-analysis          # Impact Analyzer
│
├── /testing
│   ├── POST   /generate-scenarios       # Test Scenario Generator
│   ├── POST   /triage-defect            # Defect Triage
│   ├── POST   /find-duplicates          # Duplicate detection
│   └── GET    /coverage-gaps            # Coverage gap raporu
│
├── /risk
│   ├── GET    /signals                  # Risk Sentinel aktif sinyaller
│   ├── GET    /risk-report              # Haftalık risk raporu
│   └── PUT    /signals/:id/acknowledge  # Sinyal onaylama
│
├── /data-quality
│   ├── POST   /profile/:cycleId         # Data Quality Guardian
│   ├── GET    /quality-report/:cycleId   # Kalite raporu
│   └── GET    /trend/:objectId           # Cycle-over-cycle trend
│
├── /cutover
│   ├── POST   /optimize-runbook         # Cutover Optimizer
│   ├── GET    /critical-path            # Kritik yol analizi
│   └── POST   /what-if                  # What-if senaryosu
│
├── /hypercare
│   ├── POST   /triage-incident          # War Room triage
│   ├── GET    /patterns                 # Incident pattern'ler
│   ├── GET    /daily-report             # Günlük rapor
│   └── POST   /suggest-resolution       # Çözüm önerisi
│
├── /reports
│   ├── POST   /generate-steering-pack   # Steering Pack Generator
│   └── GET    /steering-pack/:id        # Oluşturulan pack
│
├── /meetings
│   ├── POST   /process-transcript       # Meeting Intelligence
│   ├── GET    /extracted-items/:meetingId # Çıkarılan item'lar
│   └── PUT    /extracted-items/:id/review # Review
│
├── /workflows
│   ├── POST   /parse-rule               # NL Workflow Builder
│   ├── GET    /rules                    # Aktif kurallar
│   ├── PUT    /rules/:id/activate       # Kural aktifleştir
│   └── POST   /rules/:id/dry-run       # Test çalıştırma
│
└── /admin
    ├── GET    /usage-stats              # Token kullanımı, maliyet
    ├── GET    /model-performance        # Model accuracy metrikleri
    ├── PUT    /prompts/:assistantId     # Prompt güncelleme
    └── GET    /audit-log                # AI aksiyon logları
```

---

## 11. Güncellenmiş Uygulama Fazları (Platform + AI Entegre Roadmap)

### Phase 1 — Foundation + Foundation AI (10 hafta)

**Platform Modülleri:**
- Program Setup modülü (proje tipi, fazlar, gate'ler, workstream'ler, RACI)
- **Explore Phase Manager** — 5 modül, 24 tablo (referans: `explore-phase-fs-ts.md` v1.1)
  - Module A: Process Hierarchy Manager (L1-L4 ağaç, scope matrix, fit propagation)
  - Module B: Workshop Hub (300+ workshop planlama, kanban/kapasite)
  - Module C: Workshop Detail (workshop yürütme, 6 tab, fit kararı)
  - Module D: Requirement & Open Item Hub (lifecycle, batch approval, ALM push)
  - Module E: Explore Dashboard (10 widget, trend, steering export)
- RAID modülü (temel CRUD)
- Kullanıcı yönetimi ve RBAC (7 rol: PM, Module Lead, Facilitator, BPO, Tech Lead, Tester, Viewer)
- Temel dashboard (program health)

**AI Altyapı (tüm sonraki fazların temeli):**
- LLM Gateway kurulumu (Claude API + OpenAI fallback + provider router)
- RAG Pipeline kurulumu (pgvector + embedding + chunking + retrieval)
- Suggestion Queue altyapısı (pending/approve/reject akışı)
- Prompt Registry (versiyonlama + A/B test altyapısı)
- SAP Knowledge Base v1 (scope item kataloğu, modül listesi, temel terminoloji)
- AI audit logging

**AI Asistanlar:**
- ✅ **NL Query Assistant** — platform verileri üzerinde doğal dille sorgulama
- ✅ **Requirement Analyst Copilot** — Fit/PFit/Gap sınıflandırma + benzer requirement önerisi
- ✅ **Defect Triage Assistant** (temel versiyon — severity önerisi + duplicate detection)

### Phase 2 — Core Delivery + Core AI (12 hafta)

**Platform Modülleri:**
- Backlog Workbench (WRICEF lifecycle, FS/TS, status flow)
- Integration Factory (interface inventory, wave planning)
- Data Factory (object list, mapping, cycle management)
- Traceability engine (requirement ↔ backlog ↔ test ↔ defect)
- Workstream bazlı filtreleme

**AI Knowledge Base Genişletme:**
- SAP E2E süreç akış şablonları (O2C, P2P, RTR)
- WRICEF FS/TS şablonları (modül ve tip bazlı)
- Sektöre özel konfigürasyon pattern'leri

**AI Asistanlar:**
- ✅ **Steering Pack Generator** — haftalık rapor otomasyonu
- ✅ **Risk Sentinel** — kural tabanlı risk izleme + KPI threshold alert'leri
- ✅ **Work Breakdown Engine** — scenario'dan workshop/Fit-Gap/WRICEF kırılımı
- ✅ **WRICEF Spec Drafter** — FS taslak üretimi

### Phase 3 — Quality & Testing + Quality AI (10 hafta)

**Platform Modülleri:**
- **Test Management System** — 6 modül, 17 tablo (referans: `test-management-fs-ts.md` v1.0)
  - Module T1: Test Plan & Strategy (strateji, entry/exit criteria, takvim)
  - Module T2: Test Suite Manager (6 seviye, case authoring, auto-generate from WRICEF/process)
  - Module T3: Test Execution (step-by-step runner, evidence, defect quick-create)
  - Module T4: Defect Tracker (9 status lifecycle, SLA, severity/priority, kanban)
  - Module T5: Test Dashboard (10 widget, Go/No-Go Scorecard, trend)
  - Module T6: Traceability Matrix (REQ→WRICEF→TestCase→Execution→Defect)
- Role extension: `test_lead` rolü eklenir
- Explore↔Test entegrasyonu: generate-from-wricef, generate-from-process endpoints
- Cloud ALM test sync: test case push, execution results, bidirectional defect

**AI Asistanlar:**
- ✅ **Test Scenario Generator** — requirement'tan test case üretimi
- ✅ **Data Quality Guardian** — load cycle kalite analizi + cleansing önerisi
- ✅ **Impact Analyzer** — traceability zinciri boyunca etki raporu
- ⬆️ **Defect Triage Assistant** (genişletme — root cause suggestion, auto-enrichment)

### Phase 4 — Go-Live Readiness + Go-Live AI (8 hafta)

**Platform Modülleri:**
- Cutover Hub (runbook, rehearsal tracking, live view)
- Go/No-Go pack (aggregated readiness)
- Security & authorization module
- Performance test tracking

**AI Knowledge Base Genişletme:**
- SAP cutover pattern'leri (standard sequence, timing, dependencies)
- SAP known error pattern DB (go-live tipik hataları)

**AI Asistanlar:**
- ✅ **Cutover Runbook Optimizer** — CPM analizi, paralelize, rehearsal learning
- ✅ **Hypercare War Room Assistant** — incident triage, pattern detection, daily report
- ⬆️ **Risk Sentinel** (genişletme — ML bazlı anomaly detection ekleme)

### Phase 5 — Operations & Advanced AI (8 hafta)

**Platform Modülleri:**
- Run/Sustain modülü (incident, problem, RFC, KPI tracking)
- Hypercare dashboard (war room)
- Reporting engine (steering pack, export)

**AI Asistanlar:**
- ✅ **Meeting Intelligence Agent** — toplantı transkript → aksiyon/karar çıkarma
- ✅ **NL Workflow Builder** — doğal dille otomasyon kuralı tanımlama
- ⬆️ **NL Query Assistant** (genişletme — cross-module karmaşık sorgular, trend analizi)
- ⬆️ **Steering Pack Generator** (genişletme — PPTX/PDF export, otomatik dağıtım)

### Phase 6 — Integration, Scale & AI Maturity (Ongoing)

**Platform:**
- Dış sistem entegrasyonları (Jira, Cloud ALM, Teams, ServiceNow)
- Mobile PWA
- Multi-program / multi-wave support

**AI Olgunlaştırma:**
- Model fine-tuning (proje verileriyle)
- Confidence threshold otomatik kalibrasyon
- Cross-project learning (anonim pattern paylaşımı)
- AI performance dashboard (accuracy, token cost, user satisfaction)
- Otonom agent exploration (yüksek güvenli asistanlar → daha fazla otonom aksiyon)

---

## 12. Özet: Playbook → Platform → AI Eşleme

| Playbook Bölümü | Platform Modülü | FS/TS Ref | AI Asistanı | Faz |
|-----------------|-----------------|-----------|-------------|-----|
| §1 Dönüşüm Yaklaşımı | Program Setup | — | — | 1 |
| §4 SAP Activate Fazları | Program Setup | — | Risk Sentinel (gate readiness) | 2 |
| §5 Scope & Requirements | **Explore Phase Manager** (24 tablo) | explore-phase-fs-ts.md v1.1 | Requirement Analyst + Work Breakdown | 1-2 |
| §5 Data Migration | Data Factory | — | Data Quality Guardian | 3 |
| §5 Integration | Integration Factory | — | Impact Analyzer (interface etki) | 3 |
| §5 Custom/Extensions | Backlog Workbench | — | WRICEF Spec Drafter + Impact Analyzer | 2-3 |
| §5 Security | Security Module | — | — | 4 |
| §5 Testing & Quality | **Test Management System** (17 tablo) | test-management-fs-ts.md v1.0 | Test Scenario Generator + Defect Triage | 1-3 |
| §5 Change & Training | Change Module | — | Meeting Intelligence | 5 |
| §6 Test Yönetimi KPI | Test Dashboard (T5) + Go/No-Go | test-management-fs-ts.md §5.4 | NL Query + Steering Pack | 1-2 |
| §7 Cutover & Go-Live | Cutover Hub | — | Cutover Optimizer + War Room Assistant | 4 |
| §8 Risk & Kalite | RAID Module | — | Risk Sentinel | 2 |
| §9 Platform Blueprint | Tüm mimari | Bu doküman (v2.0) | 14 AI Asistan | 1-5 |
| — Cross-cutting | Reporting | — | Steering Pack Generator | 2 |
| — Cross-cutting | Tüm modüller | — | NL Query Assistant | 1 |
| — Cross-cutting | Tüm modüller | — | Meeting Intelligence | 5 |
| — Cross-cutting | Otomasyon | — | NL Workflow Builder | 5 |

---

## 13. AI Maliyet ve ROI Özet Projeksiyonu

| Kalem | Aylık Tahmini Maliyet | Aylık Tahmini Tasarruf |
|-------|----------------------|----------------------|
| Claude API (Haiku+Sonnet+Opus) | $100-400 | — |
| OpenAI Embeddings API | $15-50 | — |
| Whisper STT API | $5-20 | — |
| pgvector hosting (PostgreSQL dahilinde) | $0 (ek maliyet yok) | — |
| Redis (Celery queue) | $20-50 | — |
| **Toplam AI altyapı maliyeti** | **$140-520/ay** | — |
| | | |
| Requirement sınıflandırma hızlanması | — | 40-60 saat/ay |
| FS taslak yazım hızlanması | — | 80-120 saat/ay |
| Test case oluşturma hızlanması | — | 60-100 saat/ay |
| Defect triage hızlanması | — | 40-80 saat/ay |
| Steering pack hazırlama | — | 16-32 saat/ay |
| Risk erken tespiti (gecikme önleme) | — | Hesaplanamaz (kritik) |
| **Toplam tahmini tasarruf** | — | **236-392 saat/ay** |

> Orta ölçekli SAP projesi (50-100 kişi, 12-18 ay) baz alınmıştır.
> Consultant saat ücreti €80-150 ile hesaplandığında aylık €19K-59K tasarruf potansiyeli.
> AI altyapı maliyeti tasarrufun %1-3'ü seviyesindedir.

---

*Bu mimari doküman, SAP Transformation PM Playbook'undaki tüm domain'leri, deliverable'ları ve KPI'ları kapsayan bir uygulama temelini oluşturur. Her modül bağımsız geliştirilebilir ancak traceability zinciri ile birbirine bağlıdır. AI katmanı 14 asistan ile platform'un her modülüne zeka ekler; tüm asistanlar human-in-the-loop pattern'iyle çalışır ve aynı 4 temel bileşeni (LLM Gateway, RAG Engine, Rule Engine, Graph Analyzer) paylaşır.*
