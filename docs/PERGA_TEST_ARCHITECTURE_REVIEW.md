# PERGA — Test Yapısı Mimari İnceleme Dokümanı

**NAVIGATE COMPLEXITY**

*Test Architecture Review Input — Tüm Katmanlar, Modeller, Akışlar*

**Versiyon 1.0 — Şubat 2026**

Univer Yazılım ve Danışmanlık A.Ş.

---

## İçindekiler

1. [Genel Bakış ve Sayılar](#1-genel-bakış-ve-sayılar)
2. [Katmanlı Mimari](#2-katmanlı-mimari)
3. [Data Model — Testing Entity'leri](#3-data-model--testing-entityleri)
4. [API Endpoint Haritası](#4-api-endpoint-haritası)
5. [Servis Katmanı](#5-servis-katmanı)
6. [Frontend Yapısı](#6-frontend-yapısı)
7. [Test Suite Envanteri (Unit / Integration)](#7-test-suite-envanteri)
8. [E2E Test Yapısı](#8-e2e-test-yapısı)
9. [Test Modül Detayları — Fonksiyonel Anlatım](#9-test-modül-detayları--fonksiyonel-anlatım)
10. [Traceability & Cross-Module Akışlar](#10-traceability--cross-module-akışlar)
11. [Test Konfigurasyon Altyapısı](#11-test-konfigurasyon-altyapısı)
12. [Kapsam Matrisi](#12-kapsam-matrisi)
13. [Bilinen Sınırlamalar ve Notlar](#13-bilinen-sınırlamalar-ve-notlar)

---

## 1. Genel Bakış ve Sayılar

| Metrik | Değer |
|--------|-------|
| Toplam test fonksiyonu (`def test_*`) | **2.358** |
| Test dosyası sayısı | **43** (+ 3 arşiv) |
| Test sınıfı (class) sayısı | **~280** |
| Backend model dosyası | 24 dosya, **~130 class** |
| Backend servis dosyası | 44 dosya |
| Blueprint (API katmanı) | 31 kayıtlı blueprint |
| Frontend JS view | 21 dosya (4.653 satır sadece test modülleri) |
| E2E (Playwright) spec | 6 dosya |
| Test framework | **pytest** + Flask test client |
| E2E framework | **Playwright** (TypeScript) |
| DB (test ortamı) | SQLite in-memory (`:memory:`) |
| Fixture strateji | Session-scoped app, function-scoped rollback+recreate |

---

## 2. Katmanlı Mimari

```
┌──────────────────────────────────────────────────────────────────────┐
│                      E2E Tests (Playwright)                         │
│   6 spec dosyası — API smoke + browser interaction                  │
├──────────────────────────────────────────────────────────────────────┤
│                    Integration / API Tests (pytest)                  │
│   43 dosya, 2.358 test — Flask test client → Blueprint → DB         │
├──────────────────────────────────────────────────────────────────────┤
│                         Service Layer Tests                         │
│   test_api_test_planning_services.py (27 test)                      │
│   test_governance_metrics.py, test_traceability_unified.py vb.      │
├──────────────────────────────────────────────────────────────────────┤
│                         Model / Unit Tests                          │
│   test_explore.py model classes, test_auth.py crypto/JWT            │
│   test_ai_performance.py constants, test_tenant_migration.py schema │
├──────────────────────────────────────────────────────────────────────┤
│                      Infrastructure Tests                           │
│   test_monitoring.py, test_pwa.py, test_performance.py              │
│   test_final_polish.py, test_sprint9_10.py (security audit)         │
└──────────────────────────────────────────────────────────────────────┘
```

**Test piramidi dağılımı:**

| Katman | Test Sayısı | Oran |
|--------|-------------|------|
| Unit / Model | ~350 | %15 |
| Service | ~120 | %5 |
| API Integration | ~1.650 | %70 |
| Cross-module Flow | ~120 | %5 |
| Infrastructure + Security | ~120 | %5 |

> **Gözlem:** Piramit ağırlığı API Integration katmanında. Bu, blueprint route'larının tam CRUD lifecycle testi yapıldığını gösterir. Service-layer izole testleri daha az ağırlıktadır.

---

## 3. Data Model — Testing Entity'leri

### 3.1 Core Testing Models (`app/models/testing.py` — 2.028 satır, 21 class)

```
TestPlan (164)
  ├── TestCycle (260)
  │     ├── TestExecution (548)
  │     │     ├── TestStepResult (1283)
  │     │     └── derive_result_from_steps()
  │     ├── TestRun (1182)
  │     ├── CycleDataSet (1806)
  │     ├── TestCycleSuite (1125)
  │     └── UATSignOff (1512)
  ├── PlanScope (1867)
  ├── PlanTestCase (1942)
  ├── PlanDataSet (1747)
  └── TestDailySnapshot (1663)

TestCase (363)
  ├── TestStep (1002)
  ├── TestCaseDependency (1061)
  ├── PerfTestResult (1590)
  └── FK Traceability:
        ├── requirement_id → requirements.id (legacy)
        ├── explore_requirement_id → explore_requirements.id
        ├── backlog_item_id → backlog_items.id (WRICEF)
        ├── config_item_id → config_items.id
        ├── process_level_id → process_levels.id (L3/L4)
        └── suite_id → test_suites.id

TestSuite (909)
  └── TestCase (M:N via suite_id)

Defect (682)
  ├── DefectComment (1348)
  ├── DefectHistory (1399)
  └── DefectLink (1448)
```

### 3.2 Explore Models (Process Hierarchy + Requirements)

| Model | Dosya | Satır | Açıklama |
|-------|-------|-------|----------|
| ProcessLevel | explore/process.py | 36 | L1–L4 proses hiyerarşisi |
| ProcessStep | explore/process.py | 202 | L3 altındaki proses adımları |
| L4SeedCatalog | explore/process.py | 313 | L4 şablon kataloğu |
| ExploreWorkshop | explore/workshop.py | 41 | Fit-to-Standard workshop |
| WorkshopScopeItem | explore/workshop.py | 194 | Workshop → Scope Item M:N |
| ExploreRequirement | explore/requirement.py | 289 | Explore fazı requirement |
| ExploreDecision | explore/requirement.py | 41 | Workshop kararları |
| ExploreOpenItem | explore/requirement.py | 107 | Açık noktalar |

### 3.3 Supporting Models

| Model | Dosya | Class Sayısı | Açıklama |
|-------|-------|-------------|----------|
| Backlog (WRICEF) | backlog.py | 6 | BacklogItem, ConfigItem, Sprint, Board... |
| Integration | integration.py | 5 | Interface, Wave, ConnectivityTest, SwitchPlan |
| Cutover | cutover.py | 8 | CutoverPlan, RunbookTask, Rehearsal, GoNoGo, HypercareIncident |
| RAID | raid.py | 4 | Risk, Action, Issue, Decision |
| Data Factory | data_factory.py | 7 | DataObject, MigrationWave, CleansingTask... |
| Run & Sustain | run_sustain.py | 3 | KnowledgeTransfer, HandoverItem, StabilizationMetric |
| AI | ai.py | 11 | AIConversation, AITask, AIFeedbackMetric... |
| Auth | auth.py | 10 | Tenant, User, Role, Permission, Session... |
| Notification | notification.py + scheduling.py | 4 | Notification, ScheduledJob, EmailLog... |

### 3.4 Entity İlişki Haritası (Testing Odağı)

```
Program
  └── TestPlan
        ├── PlanScope ──────────────→ [Requirement | ExploreRequirement | ProcessLevel | Scenario]
        ├── PlanTestCase ───────────→ TestCase
        ├── PlanDataSet
        └── TestCycle
              ├── TestExecution ────→ TestCase
              │     ├── TestStepResult → TestStep
              │     └── status: pass/fail/blocked/not_run
              ├── TestRun
              ├── CycleDataSet
              ├── TestCycleSuite ──→ TestSuite
              └── UATSignOff

TestCase
  ├── process_level_id ────────────→ ProcessLevel (L3)
  ├── explore_requirement_id ──────→ ExploreRequirement
  ├── backlog_item_id ─────────────→ BacklogItem (WRICEF)
  ├── config_item_id ──────────────→ ConfigItem
  ├── suite_id ────────────────────→ TestSuite
  └── TestStep[] ──────────────────→ step_order, action, expected_result

Defect
  ├── execution_id ────────────────→ TestExecution
  ├── test_case_id ────────────────→ TestCase
  └── 9-Status Lifecycle: new → confirmed → in_progress → fixed → retest_ready → retested → verified → closed / reopened
```

---

## 4. API Endpoint Haritası

### 4.1 Testing Blueprint (`/api/v1/testing` — 2.320 satır, 80+ route)

| Grup | Endpoint | Methods | Açıklama |
|------|----------|---------|----------|
| **Test Plans** | `/programs/{pid}/testing/plans` | GET, POST | Program altında plan listele/oluştur |
| | `/testing/plans/{id}` | GET, PUT, DELETE | Plan detay/güncelle/sil |
| **Test Cycles** | `/testing/plans/{id}/cycles` | GET, POST | Plan altında cycle listele/oluştur |
| | `/testing/cycles/{id}` | GET, PUT, DELETE | Cycle detay/güncelle/sil |
| **Test Cases (Catalog)** | `/programs/{pid}/testing/catalog` | GET, POST | Test case listele/oluştur |
| | `/testing/catalog/{id}` | GET, PUT, DELETE | Case detay/güncelle/sil |
| **Test Steps** | `/testing/catalog/{id}/steps` | GET, POST | Yapılandırılmış test adımları |
| | `/testing/steps/{id}` | PUT, DELETE | Adım güncelle/sil |
| **Test Executions** | `/testing/cycles/{id}/executions` | GET, POST | Cycle'daki execution'lar |
| | `/testing/executions/{id}` | GET, PUT, DELETE | Execution detay/güncelle/sil |
| **Step Results** | `/testing/executions/{id}/step-results` | GET, POST | Adım bazlı sonuç kaydet |
| | `/testing/step-results/{id}` | PUT, DELETE | Sonuç güncelle/sil |
| | `/testing/executions/{id}/derive-result` | POST | Adımlardan otomatik sonuç türet |
| **Test Runs** | `/testing/cycles/{id}/runs` | GET, POST | Cycle run'ları |
| | `/testing/runs/{id}` | GET, PUT, DELETE | Run detay/güncelle/sil |
| **Test Suites** | `/programs/{pid}/testing/suites` | GET, POST | Suite listele/oluştur |
| | `/testing/suites/{id}` | GET, PUT, DELETE | Suite detay/güncelle/sil |
| | `/testing/suites/{id}/generate-from-wricef` | POST | WRICEF'den TC oluştur |
| | `/testing/suites/{id}/generate-from-process` | POST | Process'ten TC oluştur |
| **Cycle Suites** | `/testing/cycles/{id}/suites` | POST | Cycle'a suite ata |
| | `/testing/cycles/{id}/suites/{sid}` | DELETE | Suite kaldır |
| **Defects** | `/programs/{pid}/testing/defects` | GET, POST | Defect listele/oluştur |
| | `/testing/defects/{id}` | GET, PUT, DELETE | Defect detay/güncelle/sil |
| | `/testing/defects/{id}/comments` | GET, POST | Yorum listele/ekle |
| | `/testing/defects/{id}/history` | GET | Durum geçmişi |
| | `/testing/defects/{id}/links` | GET, POST | Defect bağlantıları |
| | `/testing/defects/{id}/sla` | GET | SLA hesaplama |
| **UAT Sign-Off** | `/testing/cycles/{id}/uat-signoffs` | GET, POST | UAT onay kaydı |
| | `/testing/uat-signoffs/{id}` | GET, PUT | Onay detay/güncelle |
| **Perf Results** | `/testing/catalog/{id}/perf-results` | GET, POST | Performans test sonuçları |
| **Dependencies** | `/testing/catalog/{id}/dependencies` | GET, POST | Case bağımlılıkları |
| **Clone** | `/testing/test-cases/{id}/clone` | POST | TC klonla |
| | `/testing/test-suites/{id}/clone-cases` | POST | Suite case'lerini klonla |
| **Plan Scope** | `/testing/plans/{id}/scopes` | GET, POST | Plan kapsam tanımı |
| | `/testing/plan-scopes/{id}` | PUT, DELETE | Kapsam güncelle/sil |
| **Plan Test Cases** | `/testing/plans/{id}/test-cases` | GET, POST | Plana TC ata |
| | `/testing/plans/{id}/test-cases/bulk` | POST | Toplu TC ata |
| | `/testing/plan-test-cases/{id}` | PUT, DELETE | Atama güncelle/sil |
| **Plan Data Sets** | `/testing/plans/{id}/data-sets` | GET, POST | Plan veri seti |
| **Cycle Data Sets** | `/testing/cycles/{id}/data-sets` | GET, POST | Cycle veri seti |
| **Snapshots** | `/programs/{pid}/testing/snapshots` | GET, POST | Günlük anlık görüntü |
| **Dashboard** | `/programs/{pid}/testing/dashboard` | GET | Test metrikleri dashboard |
| | `/programs/{pid}/testing/dashboard/go-no-go` | GET | Go/No-Go scorecard |
| **Traceability** | `/programs/{pid}/testing/traceability-matrix` | GET | İzlenebilirlik matrisi |
| **Regression** | `/programs/{pid}/testing/regression-sets` | GET | Regression set'leri |
| **Entry/Exit** | `/testing/cycles/{id}/validate-entry` | POST | Cycle giriş kriterleri |
| | `/testing/cycles/{id}/validate-exit` | POST | Cycle çıkış kriterleri |
| **Smart Services** | `/testing/plans/{id}/suggest-test-cases` | POST | AI destekli TC öneri |
| | `/testing/plans/{id}/import-suite/{sid}` | POST | Suite'den import |
| | `/testing/cycles/{id}/populate` | POST | Plan'dan cycle'a doldur |
| | `/testing/cycles/{id}/populate-from-previous/{prev}` | POST | Önceki cycle'dan doldur |
| | `/testing/plans/{id}/coverage` | GET | Kapsam oranı |
| | `/testing/cycles/{id}/data-check` | GET | Veri hazırlık kontrolü |
| | `/testing/plans/{id}/evaluate-exit` | POST | Çıkış kriterlerini değerlendir |

### 4.2 Diğer İlgili Blueprint'ler

| Blueprint | Prefix | Test Dosyası | Route Sayısı (Tahmini) |
|-----------|--------|-------------|----------------------|
| explore_bp | `/api/v1/explore` | test_explore.py (192) | ~60 |
| backlog_bp | `/api/v1` | test_api_backlog.py (79) | ~30 |
| integration_bp | `/api/v1` | test_api_integration.py (76) | ~40 |
| cutover_bp | `/api/v1` | test_api_cutover.py (79) | ~35 |
| raid_bp | `/api/v1` | test_api_raid.py (46) | ~20 |
| data_factory_bp | `/api/v1` | test_api_data_factory.py (44) | ~25 |
| auth_bp | `/api/v1/auth` | test_auth.py (52) | ~15 |
| admin_bp | `/admin` | test_admin_api.py (35) | ~20 |
| platform_admin_bp | `/platform-admin` | test_platform_admin.py (65) | ~25 |
| sso_bp | `/api/v1/sso` | test_sso.py (84) | ~15 |
| ai_bp | `/api/v1/ai` | test_ai*.py (436 toplam) | ~50 |
| traceability_bp | `/api/v1` | test_traceability_unified.py (14) | ~5 |
| audit_bp | `/api/v1` | test_audit_trace.py (24) | ~10 |
| reporting_bp | `/api/v1/reports` | test_reporting.py (8) | ~5 |
| run_sustain_bp | `/api/v1/run-sustain` | test_run_sustain.py (69) | ~20 |
| notification_bp | `/api/v1` | test_notification_scheduling.py (81) | ~25 |

---

## 5. Servis Katmanı

### 5.1 Testing Servisleri

| Servis | Dosya | Fonksiyonel Sorumluluk |
|--------|-------|----------------------|
| **test_planning_service** | `app/services/test_planning_service.py` | Smart plan servisleri: suggest TC, import from suite, populate cycle, calculate coverage, check data readiness, evaluate exit criteria |
| **testing_service** | `app/services/testing_service.py` | Auto-code generation, SLA hesaplama, defect lifecycle (9-status), clone TC/suite, snapshot, dashboard compute, Go/No-Go scorecard, traceability matrix, generate TC from WRICEF/Process |
| **traceability** | `app/services/traceability.py` | Cross-entity chain building: requirement → backlog → test_case → defect → process. Upstream/downstream traversal |

### 5.2 Test Planning Service — Detaylı Fonksiyonlar

```python
suggest_test_cases(plan_id)
    # PlanScope'ları analiz eder
    # Her scope item için requirement/process/scenario izler
    # Varolan TC'leri eşleştirir, yoksa yeni TC önerir
    # Dönüş: [{test_case, reason, scope_ref}]

import_from_suite(plan_id, suite_id)
    # Suite'deki tüm TC'leri PlanTestCase olarak import eder
    # Dublikasyon kontrolü yapar

populate_cycle_from_plan(cycle_id)
    # Plan'daki tüm PlanTestCase'leri TestExecution olarak cycle'a kopyalar

populate_cycle_from_previous(cycle_id, prev_cycle_id, filter_status)
    # Önceki cycle'daki failed/blocked execution'ları yeni cycle'a kopyalar

calculate_scope_coverage(plan_id)
    # PlanScope başına TC kapsam oranı hesaplar
    # Dönüş: {scopes: [{scope, coverage_pct, test_cases}], overall_coverage}

check_data_readiness(plan_id)
    # PlanDataSet → CycleDataSet uyumunu kontrol eder

evaluate_exit_criteria(plan_id)
    # Pass rate ≥ 95%, critical defect = 0, UAT sign-off, kapsam ≥ 80% kontrol
```

### 5.3 Testing Service — Defect 9-Status Lifecycle

```
new → confirmed → in_progress → fixed → retest_ready → retested → verified → closed
                                                                        ↓
                                                                    reopened → confirmed (tekrar döngü)
```

**Geçerli geçişler (validate edilir):**

```python
VALID_TRANSITIONS = {
    "new": ["confirmed", "closed"],
    "confirmed": ["in_progress", "closed"],
    "in_progress": ["fixed", "closed"],
    "fixed": ["retest_ready"],
    "retest_ready": ["retested"],
    "retested": ["verified", "reopened"],
    "verified": ["closed"],
    "closed": ["reopened"],
    "reopened": ["confirmed"],
}
```

---

## 6. Frontend Yapısı

### 6.1 Testing İle İlgili JS View'lar

| Dosya | Satır | Sorumluluk |
|-------|-------|-----------|
| `test_planning.js` | 1.452 | Test katalog (CRUD), suite yönetimi, TC oluşturma (traceability picker'lar dahil), AI üretimi |
| `test_plan_detail.js` | 940 | Plan detay: scope, cycle, coverage tab'ları |
| `test_execution.js` | 1.209 | Execution yönetimi: adım-adım test, step result, defect kayıt |
| `defect_management.js` | 639 | Defect listesi, filtre, durum geçişi |
| `testing_shared.js` | 33 | Ortak util: program ID, escape fonksiyonu |
| `executive_cockpit.js` | 380 | Yönetici dashboard: Go/No-Go, metrikler |

### 6.2 Frontend → API Bağlantı Akışları

```
test_planning.js
  ├── renderCatalog()        → GET /programs/{pid}/testing/catalog
  ├── showCaseModal()        → Modal: Title, Layer, Module, Priority, Suite,
  │                             Traceability (L3 Process, Requirement, WRICEF, Config),
  │                             Description, Steps, Expected Result, Data Set
  ├── saveCase(id)           → POST/PUT /testing/catalog/{id}
  │                             Payload: title, test_layer, module, priority,
  │                             process_level_id, explore_requirement_id,
  │                             backlog_item_id, config_item_id, suite_id, ...
  ├── _loadTraceabilityOptions()
  │     ├── GET /explore/process-levels?level=3&flat=true
  │     ├── GET /explore/requirements?project_id={pid}
  │     ├── GET /programs/{pid}/backlog
  │     └── GET /programs/{pid}/config-items
  ├── renderSuites()         → GET /programs/{pid}/testing/suites
  ├── generateFromWricef()   → POST /testing/suites/{id}/generate-from-wricef
  └── generateFromProcess()  → POST /testing/suites/{id}/generate-from-process

test_plan_detail.js
  ├── renderScopes()         → GET /testing/plans/{id}/scopes
  ├── addScopeItem()         → POST /testing/plans/{id}/scopes
  │     └── Picker: L3 Process (level=3&flat=true), Scenario (workshops)
  ├── renderCoverage()       → GET /testing/plans/{id}/coverage
  ├── renderCycles()         → GET /testing/plans/{id}/cycles
  ├── suggestTestCases()     → POST /testing/plans/{id}/suggest-test-cases
  └── evaluateExit()         → POST /testing/plans/{id}/evaluate-exit

test_execution.js
  ├── loadExecutions()       → GET /testing/cycles/{id}/executions
  ├── executeStep()          → POST /testing/executions/{id}/step-results
  ├── deriveResult()         → POST /testing/executions/{id}/derive-result
  ├── logDefect()            → POST /programs/{pid}/testing/defects
  └── updateStatus()         → PUT /testing/executions/{id}

defect_management.js
  ├── loadDefects()          → GET /programs/{pid}/testing/defects
  ├── transitionDefect()     → PUT /testing/defects/{id} (status change)
  ├── addComment()           → POST /testing/defects/{id}/comments
  └── viewSLA()              → GET /testing/defects/{id}/sla
```

---

## 7. Test Suite Envanteri

### 7.1 Dosya Bazlı Test Dağılımı

#### Testing Module (Doğrudan Test Yönetimi)

| Dosya | Test | Class | Kapsam |
|-------|------|-------|--------|
| `test_api_testing.py` | **207** | 27 | Core CRUD: Plan, Cycle, Case, Execution, Defect, Suite, Step, Run, StepResult, Dependency, Traceability, Regression, Dashboard, UAT SignOff, Perf Results, Snapshots, Go/No-Go, Entry/Exit Criteria, Generate from WRICEF/Process |
| `test_api_test_planning.py` | **46** | 6 | PlanScope, PlanTestCase, PlanDataSet, CycleDataSet, TestDataSet, TestDataSetItem |
| `test_api_test_planning_services.py` | **27** | 7 | SuggestTestCases, ImportFromSuite, PopulateCycle, PopulateFromPrevious, Coverage, DataReadiness, ExitCriteria |
| `test_traceability_unified.py` | **14** | 3 | Unified trace chain: standard + explore + lateral entity linking |

**Alt toplam: 294 test** — doğrudan test yönetimi modülü

#### Explore Module (Process + Requirement + Workshop)

| Dosya | Test | Class | Kapsam |
|-------|------|-------|--------|
| `test_explore.py` | **192** | 25 | ProcessLevel L1-L4 CRUD, Workshop CRUD, ProcessStep, Requirement CRUD, OpenItem, Transitions, FitPropagation, Signoff, CodeGeneration, Lifecycle integration |
| `test_requirement_lifecycle.py` | **24** | 5 | Requirement state machine: draft → review → approved → deferred/rejected, ADR-1 convert-before-push |
| `test_workshop_integration_mapping.py` | **25** | 9 | Workshop creation, inline form (decision/OI/requirement), fit decision flow, delta workshop, full lifecycle |
| `test_governance_metrics.py` | **53** | 8 | Workshop completion rules, requirement approval, L3 signoff, escalation, metrics |

**Alt toplam: 294 test** — explore modülü

#### Backlog / Integration / Cutover / RAID / Data Factory / Run & Sustain

| Dosya | Test | Kapsam |
|-------|------|--------|
| `test_api_backlog.py` | **79** | BacklogItem WRICEF CRUD, ConfigItem, Sprint, Board, filtering, status transitions |
| `test_api_integration.py` | **76** | Interface CRUD, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist, cascade delete, traceability |
| `test_api_cutover.py` | **79** | CutoverPlan lifecycle, ScopeItem, RunbookTask, TaskDependency, Rehearsal, GoNoGo, Progress, HypercareIncident, SLA |
| `test_api_raid.py` | **46** | Risk/Action/Issue/Decision CRUD, aggregate, notification, risk scoring |
| `test_api_data_factory.py` | **44** | DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation, Dashboard |
| `test_run_sustain.py` | **69** | KnowledgeTransfer, HandoverItem, StabilizationMetric, Dashboard, SLA compliance |
| `test_api_program.py` | **36** | Program CRUD, project CRUD, team members, program dashboard |

**Alt toplam: 429 test**

#### Auth / Admin / Multi-Tenant / SSO

| Dosya | Test | Kapsam |
|-------|------|--------|
| `test_auth.py` | **52** | Crypto (bcrypt), JWT (create/verify/refresh), Auth models, User service, Auth API (login/register/profile), backward compat |
| `test_admin_api.py` | **35** | Admin dashboard, user CRUD, invite, role management, permissions, UI routes, authorization |
| `test_platform_admin.py` | **65** | Platform admin tenant CRUD, dashboard, blueprint permissions, explore permissions, legacy auth fallthrough, superuser bypass |
| `test_tenant_isolation.py` | **42** | Permission service, tenant context, require_permission decorator, project access, cross-tenant isolation, superuser roles |
| `test_tenant_migration.py` | **40** | tenant_id schema presence on all tables, global tables no tenant_id, CRUD with tenant_id, audit log fields, indexes, cross-model consistency |
| `test_sso.py` | **84** | SSO models, config CRUD, domain resolution, OIDC flow, SAML flow, user provisioning, public endpoints, admin config API, admin domain API, UI, permission guard |
| `test_sprint8.py` | **80** | SCIM token mgmt, SCIM user CRUD, SCIM filter/pagination, SCIM auth, bulk import (template/parse/execute), custom roles CRUD/permissions/protection, roles admin UI, SSO E2E (OIDC + SAML) |
| `test_sprint9_10.py` | **99** | Feature flags, cache service, tenant rate limiting, dashboard metrics, onboarding wizard, tenant export, soft delete, schema-per-tenant, performance tests, security audit (OWASP Top 10) |

**Alt toplam: 497 test**

#### AI Module

| Dosya | Test | Kapsam |
|-------|------|--------|
| `test_ai.py` | **69** | Cost calculation, AI models, Suggestion API, Usage API, Audit API, Embeddings API, Admin dashboard, Prompts API, LLM Gateway, Suggestion Queue, Prompt Registry |
| `test_ai_assistants.py` | **72** | SQL validation, SAP glossary, NL Query assistant, Requirement analyst, Defect triage, Assistant integration |
| `test_ai_performance.py` | **67** | Constants, response cache service, model selector, token budget service, cache/budget models, usage audit, gateway, performance/cache/budget endpoints |
| `test_ai_phase3.py` | **56** | Cutover optimizer (unit + gateway), meeting minutes (unit + gateway), prompt YAML loading, cutover AI endpoints, meeting minutes endpoints, edge cases |
| `test_ai_phase4.py` | **88** | AI conversation model/message, conversation manager, steering pack generator, WRICEF spec drafter, data quality guardian, doc-gen API, conversation API, doc-gen prompts |
| `test_ai_phase5.py` | **81** | AI task model, feedback metric model, data migration advisor, integration analyst, feedback pipeline, task runner, AI doc exporter, AI orchestrator, RAG entity extractors, endpoint coverage |
| `test_ai_accuracy.py` | **3** | Requirement analyst accuracy, NL query accuracy, defect triage accuracy |

**Alt toplam: 436 test**

#### Infrastructure / Quality

| Dosya | Test | Kapsam |
|-------|------|--------|
| `test_monitoring.py` | **15** | Health endpoints, request timing, metrics endpoints |
| `test_pwa.py` | **68** | Manifest, service worker, icons, offline page, PWA status API, index.html PWA, mobile CSS, PWA JS, mobile JS, SPA integration |
| `test_performance.py` | **8** | API response time benchmarks |
| `test_final_polish.py` | **31** | Error handlers (404/405/500/429), no deprecated query.get, rate limiter, infra files, JS error handler, fit propagation cache, readme quality, boolean filter, SPA fallback, skip_permission, Docker, PWA regression |
| `test_notification_scheduling.py` | **81** | Notification preference, scheduled job, email log models, email service, scheduler service, job execution, notification CRUD, preferences API, scheduler API, email log API, delivery integration, edge cases |
| `test_api_contracts.py` | **16** | Error shape, required fields, enum validation, convert contract, response shape, idempotent GET |
| `test_kb_versioning.py` | **27** | KB version model, AI embedding versioning, content hash, AI suggestion KB version, RAG versioned indexing, index stats, KB version API, stale API, diff API |
| `test_audit_trace.py` | **24** | Audit log model, audit API, audit integration, AI execution log, traceability service, traceability API |
| `test_reporting.py` | **8** | Reporting, program health, export |

**Alt toplam: 278 test**

#### Cross-Module / Flow Tests

| Dosya | Test | Kapsam |
|-------|------|--------|
| `test_integration_flows.py` | **5** | Requirement-to-defect flow, process hierarchy with requirement mapping, interface traceability, RAID notification flow, dashboard aggregation |
| `test_demo_flow.py` | **20** | User permissions, testing metrics bridge, executive cockpit, traceability UI, E2E demo flow |

**Alt toplam: 25 test**

---

## 8. E2E Test Yapısı

| Spec Dosyası | Kapsam |
|-------------|--------|
| `01-health.spec.ts` | `/api/v1/health` endpoint erişilebilirliği |
| `02-dashboard.spec.ts` | Dashboard API smoke test |
| `03-explore.spec.ts` | Explore API (process levels, workshops) smoke |
| `04-data-factory.spec.ts` | Data Factory API smoke |
| `05-testing.spec.ts` | Test plans, cycles, defects API smoke |
| `06-fe-sprint3-smoke.spec.ts` | Frontend Sprint 3 browser interaction |

**Konfigürasyon:** `playwright.config.ts` — base URL: `http://localhost:5001`

---

## 9. Test Modül Detayları — Fonksiyonel Anlatım

### 9.1 TestTestPlans (test_api_testing.py)

**Ne test eder:** Test planı CRUD lifecycle
- Plan oluşturma (`POST /programs/{pid}/testing/plans`) — title, plan_type, test_layer, module
- Listeleme, filtreleme, sayfalama
- Plan güncelleme — durum geçişleri (draft → active → completed)
- Silme — cascade silme kontrolü (cycles, scopes, data sets dahil)
- Plan `to_dict()` çıktı şeması doğrulama

### 9.2 TestTestCycles (test_api_testing.py)

**Ne test eder:** Test cycle CRUD lifecycle
- Plan altında cycle oluşturma — start_date, end_date, status
- Cycle → Plan ilişkisi (FK bütünlüğü)
- Durum geçişleri: planned → active → completed
- Entry/Exit criteria validation endpoint'leri

### 9.3 TestTestCases (test_api_testing.py)

**Ne test eder:** Test case katalog yönetimi
- TC oluşturma — auto-code generation (`TC-{MODULE}-{SEQUENCE}`)
- Tüm alanlar: title, test_layer, module, priority, description, preconditions, expected_result
- Traceability FK'ları: `process_level_id`, `explore_requirement_id`, `backlog_item_id`, `config_item_id`
- Filtreleme: layer, module, priority, suite_id, status
- Edit mode: tüm alanların güncellenmesi

### 9.4 TestTestExecutions (test_api_testing.py)

**Ne test eder:** Test execution (çalıştırma) yönetimi
- Cycle altında execution oluşturma (test_case_id → execution)
- Durum güncelleme: not_run → pass / fail / blocked
- `include_step_results` query param ile adım sonuçlarını dahil etme
- Execution → TestCase → TestStep zinciri

### 9.5 TestStepResults (test_api_testing.py)

**Ne test eder:** Adım bazlı test sonuçları
- Execution altında step result oluşturma (`POST /executions/{id}/step-results`)
- Status: pass / fail / blocked / not_run
- `derive-result` endpoint: tüm adım sonuçlarından execution durumunu otomatik türetme
  - Tüm pass → execution pass
  - Herhangi fail → execution fail
  - Herhangi blocked (fail yok) → execution blocked

### 9.6 TestDefects (test_api_testing.py)

**Ne test eder:** Hata yönetimi
- Defect oluşturma: severity (critical/high/medium/low), priority (P1-P4)
- 9-status lifecycle tam geçiş testi
- Comment CRUD
- History kaydı (her durum değişikliğinde otomatik)
- DefectLink (defect↔defect ilişkisi): duplicate_of, related_to, caused_by
- SLA hesaplama (`/defects/{id}/sla`): severity+priority bazlı due date

### 9.7 TestTraceabilityMatrix (test_api_testing.py)

**Ne test eder:** Program genelinde izlenebilirlik matrisi
- TC → Requirement / WRICEF / Process eşleştirme raporu
- Her TC'nin `source` bilgisi (both/requirement/backlog)
- Coverage yüzdesi hesaplama

### 9.8 TestDashboard (test_api_testing.py)

**Ne test eder:** Test dashboard metrikleri
- Toplam TC, execution, defect sayıları
- Pass/fail/blocked dağılımı
- Pass rate hesaplama
- Severity dağılımı
- Module bazlı breakdown
- Suite bazlı istatistikler

### 9.9 TestGoNoGoScorecard (test_api_testing.py)

**Ne test eder:** Go/No-Go karar desteği
- Her test layer (SIT/UAT/E2E/Regression) için pass rate
- Critical defect sayısı
- UAT sign-off durumu
- Genel RAG durumu (Red/Amber/Green)
- Toplam skor hesaplama

### 9.10 TestTestSuites (test_api_testing.py)

**Ne test eder:** Test suite yönetimi
- Suite CRUD (SIT/UAT/Regression/E2E/Performance/Custom)
- Suite status: draft → active → locked → archived
- Suite → TestCase ilişkisi
- Suite istatistikleri (case count, layer breakdown)

### 9.11 TestGenerateFromWricef (test_api_testing.py)

**Ne test eder:** WRICEF'den otomatik TC üretimi
- BacklogItem veya ConfigItem listesi verildiğinde:
  - Her item için bir TC oluşturulur
  - TC kodu: `{WRICEF_CODE}-TC-001` formatında
  - TC'ye backlog_item_id veya config_item_id FK set edilir
  - Description ve test_steps otomatik populate edilir

### 9.12 TestGenerateFromProcess (test_api_testing.py)

**Ne test eder:** Process hiyerarşisinden otomatik TC üretimi
- Scope item (L3 ProcessLevel) verildiğinde:
  - L3'ün altındaki L4 process step'leri belirlenir
  - Her L4 adımı için bir TC oluşturulur
  - TC'ye process_level_id FK set edilir

### 9.13 PlanScope / PlanTestCase / DataSets (test_api_test_planning.py)

**Ne test eder:**
- **PlanScope:** Plan'a kapsam öğesi ekleme (scope_type: requirement/explore_requirement/process_level/scenario, ref_id, ref_name)
- **PlanTestCase:** Plan'a TC ekleme — tekil ve bulk, dublikasyon kontrolü, priority override
- **PlanDataSet / CycleDataSet:** Test veri setleri yönetimi, plan/cycle seviyesinde tanım ve referans

### 9.14 Smart Services (test_api_test_planning_services.py)

**Ne test eder:**
- **SuggestTestCases:** PlanScope → ilgili TC'leri bul veya öner
- **ImportFromSuite:** Suite'deki TC'leri plan'a import et
- **PopulateCycle:** Plan'daki TC'leri cycle'a execution olarak doldur
- **PopulateFromPrevious:** Önceki cycle'daki failed/blocked'ları yeni cycle'a kopyala
- **Coverage:** Scope bazlı kapsam oranı hesaplama
- **DataReadiness:** Plan veri seti ↔ cycle veri seti uyumu
- **ExitCriteria:** Pass rate, defect, sign-off, kapsam kontrolü

---

## 10. Traceability & Cross-Module Akışlar

### 10.1 Test Case Traceability Zinciri

```
ProcessLevel (L3/L4)
  ↓ process_level_id
TestCase ←── explore_requirement_id ── ExploreRequirement
  ↓ backlog_item_id                       ↑ process_level_id
BacklogItem (WRICEF)                  ProcessLevel
  ↓ config_item_id
ConfigItem

TestCase → TestExecution → TestStepResult
            ↓ execution_id
         Defect → DefectComment + DefectHistory + DefectLink
```

### 10.2 PlanScope → Coverage Akışı

```
1. Plan oluştur
2. PlanScope ekle (type=process_level, ref_id=L3_ID)
3. PlanScope ekle (type=explore_requirement, ref_id=REQ_ID)
4. suggest-test-cases çağır → scope'lara match eden TC'ler bulunur
5. PlanTestCase olarak import et (tekil veya bulk)
6. coverage hesapla → scope başına TC sayısı / hedef
```

### 10.3 Execution → Defect → Resolution Akışı

```
1. Cycle oluştur, populate et (plan'dan veya önceki cycle'dan)
2. TestExecution'ı başlat (status: in_progress)
3. Her TestStep için StepResult kaydet (pass/fail/blocked)
4. derive-result çağır → execution status otomatik set
5. Fail durumunda → Defect oluştur (execution_id, test_case_id)
6. Defect 9-status lifecycle: new → confirmed → ... → closed
7. Go/No-Go scorecard → tüm defect/pass oranlarını değerlendir
```

### 10.4 Cross-Module Traceability Service

`app/services/traceability.py` — Entity'ler arası zincir oluşturma:

```python
get_chain("test_case", tc_id) → {
    upstream: [requirement, process_level, backlog_item],
    entity: {test_case details},
    downstream: [execution, defect]
}

get_chain("requirement", req_id) → {
    upstream: [process, workshop],
    entity: {requirement details},
    downstream: [backlog_item, config_item, test_case]
}

get_chain("defect", defect_id) → {
    upstream: [execution, test_case, requirement, process],
    entity: {defect details},
    downstream: []
}
```

Desteklenen entity türleri: `test_case`, `defect`, `requirement`, `backlog_item`, `config_item`, `process`, `scenario`, `interface`, `analysis`

---

## 11. Test Konfigurasyon Altyapısı

### 11.1 conftest.py — Fixture Pipeline

```python
@pytest.fixture(scope="session")
def app():
    # Flask app oluştur ("testing" config)
    # SESSION-scoped: tüm testler boyunca tek instance

@pytest.fixture(scope="session")
def _setup_db(app):
    # Tüm tabloları bir kez oluştur
    # Session sonunda drop

@pytest.fixture(autouse=True)
def session(app, _setup_db):
    # HER TEST SONRASI:
    #   1. Rollback
    #   2. Drop all tables
    #   3. Recreate all tables
    # Bu sayede her test izole çalışır

@pytest.fixture()
def client(app):
    # Flask test client

@pytest.fixture()
def program(client):
    # POST /api/v1/programs ile test program oluştur
```

**Kritik tasarım kararları:**
- Session-scoped `app` → hız optimizasyonu (1 kez app oluştur)
- Function-scoped `session` (autouse) → tam izolasyon (drop+recreate tabloları)
- SQLite in-memory → CI/CD hızı, dosya I/O overhead yok
- `client` fixture her testte fresh → stateless test client

### 11.2 Test Config

```python
class TestingConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # JWT secret, CORS, rate limit disabled etc.
```

### 11.3 Test Çalıştırma Komutları

```bash
# Tüm testler
pytest tests/ -q

# Sadece testing modülü
pytest tests/test_api_testing.py -q

# Spesifik class
pytest tests/test_api_testing.py::TestDefects -q

# Verbose + kısa traceback
pytest tests/test_api_testing.py -v --tb=short

# İlk hata'da dur
pytest tests/test_api_testing.py -x

# Performans (süre)
pytest tests/ -q --durations=20
```

---

## 12. Kapsam Matrisi

### 12.1 SAP Activate Faz ↔ Test Kapsam Eşleştirmesi

| SAP Activate Fazı | Platform Modülü | Test Dosyası | Test Sayısı |
|-------------------|-----------------|-------------|-------------|
| **Discover** | Program, Project | test_api_program.py | 36 |
| **Explore** | Process Hierarchy (L1-L4), Workshop, Requirement, OpenItem, Decision, FitPropagation, Signoff | test_explore.py, test_requirement_lifecycle.py, test_workshop_integration_mapping.py, test_governance_metrics.py | 294 |
| **Realize — Backlog** | WRICEF, ConfigItem, Sprint, Board | test_api_backlog.py | 79 |
| **Realize — Integration** | Interface, Wave, ConnectivityTest, SwitchPlan | test_api_integration.py | 76 |
| **Realize — Testing** | TestPlan, TestCycle, TestCase, TestExecution, TestStep, TestRun, TestSuite, Defect, Dashboard, Traceability, Go/No-Go | test_api_testing.py, test_api_test_planning.py, test_api_test_planning_services.py | 280 |
| **Realize — Data** | DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation | test_api_data_factory.py | 44 |
| **Realize — Cutover** | CutoverPlan, RunbookTask, Rehearsal, GoNoGo, HypercareIncident, SLA | test_api_cutover.py | 79 |
| **Deploy / Run** | KnowledgeTransfer, HandoverItem, StabilizationMetric | test_run_sustain.py | 69 |
| **Cross-Cutting: RAID** | Risk, Action, Issue, Decision, Notification | test_api_raid.py | 46 |
| **Cross-Cutting: AI** | AI assistants, NL Query, Defect Triage, Doc Gen, Conversation, Feedback, RAG | test_ai*.py (7 dosya) | 436 |
| **Cross-Cutting: Auth/Admin** | JWT, RBAC, Tenant isolation, SSO, SCIM, Platform Admin | test_auth.py, test_admin_api.py, test_platform_admin.py, test_tenant_*.py, test_sso.py, test_sprint8.py, test_sprint9_10.py | 497 |
| **Cross-Cutting: Traceability** | Entity chain, coverage matrix | test_traceability_unified.py, test_audit_trace.py | 38 |
| **Infrastructure** | Monitoring, PWA, Performance, Notifications, KB versioning, API contracts, Final polish | test_monitoring.py — test_final_polish.py (9 dosya) | 278 |

### 12.2 CRUD Kapsam Özeti

| Entity | Create | Read | Update | Delete | List+Filter | Lifecycle |
|--------|--------|------|--------|--------|-------------|-----------|
| TestPlan | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ draft→active→completed |
| TestCycle | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ planned→active→completed |
| TestCase | ✅ | ✅ | ✅ | ✅ | ✅ filter | ✅ auto-code |
| TestExecution | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ not_run→pass/fail/blocked |
| TestStep | ✅ | ✅ | ✅ | ✅ | — | ✅ order management |
| TestStepResult | ✅ | ✅ | ✅ | ✅ | — | ✅ derive-result |
| TestRun | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| TestSuite | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ draft→active→locked→archived |
| Defect | ✅ | ✅ | ✅ | ✅ | ✅ filter | ✅ 9-status lifecycle |
| DefectComment | ✅ | ✅ | — | ✅ | — | — |
| DefectHistory | — | ✅ | — | — | — | auto-generated |
| DefectLink | ✅ | ✅ | — | ✅ | — | — |
| UATSignOff | ✅ | ✅ | ✅ | — | ✅ | — |
| PerfTestResult | ✅ | ✅ | — | ✅ | — | — |
| DailySnapshot | ✅ | ✅ | — | — | — | auto-compute |
| PlanScope | ✅ | ✅ | ✅ | ✅ | — | — |
| PlanTestCase | ✅ | ✅ | ✅ | ✅ | — | bulk support |
| PlanDataSet | ✅ | ✅ | ✅ | ✅ | — | — |
| CycleDataSet | ✅ | ✅ | ✅ | ✅ | — | — |
| CycleSuite | ✅ | — | — | ✅ | — | — |
| CaseDependency | ✅ | ✅ | — | ✅ | — | — |

---

## 13. Bilinen Sınırlamalar ve Notlar

### 13.1 Test Altyapısı

| # | Husus | Detay |
|---|-------|-------|
| 1 | **DB backend farkı** | Testler SQLite in-memory, production PostgreSQL. JSON field, ARRAY field, FTS davranışları farklı olabilir |
| 2 | **Auth bypass** | API testleri auth middleware'i bypass eder (test config'de disabled). Gerçek JWT validation bunlarla test edilmez |
| 3 | **Drop+Recreate** | Her test sonrası tüm tablolar drop+recreate edilir. Bu yaklaşım izolasyon sağlar ancak migration testlerini desteklemez |
| 4 | **Mock kullanımı** | AI testlerinde LLM çağrıları mock'lanır. Gerçek model yanıtları test edilmez (test_ai_accuracy.py hariç) |
| 5 | **E2E coverage** | E2E testler minimal smoke level — sadece API erişilebilirliği, UI interaction testi sınırlı |
| 6 | **Concurrent access** | Multi-user concurrent test senaryoları bulunmamakta (test_performance.py sadece latency) |
| 7 | **Legacy requirement_id** | TestCase'de `requirement_id` FK mevcut ama deprecated. Frontend'de sadece `explore_requirement_id` kullanılıyor |

### 13.2 Fonksiyonel Boşluklar

| # | Husus | Detay |
|---|-------|-------|
| 1 | **TestDataSet CRUD** | Model var (`PlanDataSet`, `CycleDataSet`) ama frontend'de data set yönetim UI eksik |
| 2 | **UAT SignOff UI** | Backend endpoint mevcut, frontend integration minimal |
| 3 | **Clone + Template** | Clone endpoint test edilmiş ama template-based TC üretimi (reusable template library) mevcut değil |
| 4 | **Notification on defect** | RAID notification testi var ama defect status change notification entegrasyonu test edilmemiş |
| 5 | **Batch execution** | Çoklu execution toplu güncelleme endpoint'i yok |

### 13.3 Mimari Güçlü Yönler

| # | Husus | Detay |
|---|-------|-------|
| 1 | **Tam CRUD coverage** | 21 testing entity'nin tamamında Create/Read/Update/Delete test edilmiş |
| 2 | **Lifecycle testleri** | Defect 9-status, Plan/Cycle/Suite status geçişleri kapsamlı |
| 3 | **Traceability derinliği** | TC → Requirement → Process → Workshop zinciri hem servis hem endpoint seviyesinde test edilmiş |
| 4 | **Smart services** | suggest-TC, populate-cycle, coverage, exit-criteria gibi akıllı servisler izole test edilmiş |
| 5 | **Security audit** | OWASP Top 10 pattern testleri (Sprint 10) — injection, XSS, SSRF, traversal |
| 6 | **Multi-tenant isolation** | 42 test ile cross-tenant veri sızıntısı kontrol ediliyor |
| 7 | **API contract tests** | Error shape, required fields, enum validation, response shape standart kontrolü |

---

*Doküman Sonu — Perga Test Architecture Review Input v1.0*
