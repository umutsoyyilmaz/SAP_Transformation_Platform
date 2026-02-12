# SAP Transformation Management Platform — Proje Uygulama Planı v2

**Versiyon:** 2.1  
**Tarih:** 11 Şubat 2026  
**Baz Versiyon:** v1.1 → v2.0 delta: consolidated-review-report.md bulgularına göre güncellenmiştir  
**Hazırlayan:** Umut Soyyılmaz  
**Son Commit:** `h7c8d9e` (TS-Sprint 3 tamamlandı)

> **📌 v2.1 Güncelleme Notları:**
> - Tüm metrikler gerçek duruma hizalandı: **77 DB tablo, 336 API route, 916 test, 77 model, 11 migration, 73 commit**
> - Sprint 22 dış entegrasyon tahmini D14 revizesine göre 18→56 saate güncellendi
> - TS-Sprint 3 tamamlandı (UAT Sign-Off + Perf Test + Daily Snapshot + SLA + Go/No-Go)
> - Teknik borç sprint'leri (TD-Sprint) eklenmiştir
> - Tamamlanan sprint'ler kapanış durumuyla işaretlenmiştir
> - Explore Phase (plan dışı) resmi olarak zaman çizelgesine dahil edilmiştir

---

## 1. Yönetici Özeti

Bu plan, mevcut ProjektCoPilot prototipini baz alarak SAP Transformation Management Platform'un tam kapsamlı uygulamasını detaylandırır. Plan 6 ana Release, 24+ Sprint üzerinden yapılandırılmıştır.

**Geliştirme Yöntemi:** Claude + GitHub Copilot + Codex Agent  
**Çalışma Modeli:** Solo developer + AI araçları. Haftada 15-20 saat geliştirme kapasitesi.

---

## 2. Güncel Platform Durumu (Şubat 2026)

### ✅ Tamamlanan (Release 1 + 2 + Sprint 9 + Explore Phase + TS-Sprint 1-3)

```
TAMAMLANAN
──────────
✅ Program Setup (6 model, 25 route, 36 test)
✅ Scope & Requirements (3 model, 20 route, 45 test)
✅ Backlog Workbench (5 model, 28 route, 59 test)
✅ Test Hub (17 model, 71 route, 203 test)
   ├── TS-Sprint 1: TestSuite, TestStep, TestCaseDependency, TestCycleSuite (+4 tablo, +11 route)
   └── TS-Sprint 2: TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink (+5 tablo, +16 route)
  └── TS-Sprint 3: UATSignOff, PerfTestResult, TestDailySnapshot + SLA + Go/No-Go (+3 tablo, +16 route)
✅ RAID Module (4 model, 30 route, 46 test)
✅ Integration Factory (5 model, 26 route, 76 test)
✅ FE-Sprint: Frontend Cleanup & Hardening (10 task, ~12.5h)
✅ Data Factory (5 model, 33 route, UI 1,044 satır)
✅ Reporting Engine + Export (reporting.py, export_service.py, reports.js)
✅ AI Altyapı (5 model, 29 route, 141 test)
   ├── LLM Gateway (Anthropic, OpenAI, Gemini, LocalStub — 4 provider)
   ├── RAG Pipeline (8 entity extractor, hybrid search, KB versioning)
   ├── Suggestion Queue (HITL lifecycle)
   └── Prompt Registry (YAML + Jinja2)
✅ AI Phase 1 (3 asistan aktif: NL Query, Requirement Analyst, Defect Triage)
✅ AI Phase 2 (3 asistan aktif: Risk Assessment, Test Case Generator, Change Impact)
✅ Traceability Engine v1+v2 (Req ↔ WRICEF ↔ TestCase ↔ Defect ↔ Interface)
✅ Notification Service (in-app)
✅ Explore Phase (25 model, 66 route, 192 test, 8 servis, 10 frontend modül)
   ├── Fit/Gap Propagation, Workshop Session, Requirement Lifecycle
   ├── Open Item Lifecycle, Scope Change, Signoff, Snapshot, Minutes Generator
   ├── BPMN Diagram, Workshop Documents, Daily Snapshot
   └── Dashboard & Analytics (KPI kartlar, chart'lar, filtreleme)
✅ Monitoring & Observability (health_bp + metrics_bp, 15 test)
✅ UI-Sprint (T): Typography Standardization (Inter font, type scale, rem->var())
✅ UI-Sprint (F): KPI Dashboard Standardization (kpiBlock v2, metricBar, 6 view)
✅ UI-Sprint (H): Process Hierarchy UI Improvements (compact KPI, hover actions)
✅ UI-Sprint (G): Backlog Page Redesign (filterBar, badges, 4-tab layout)

DEVAM EDEN / KISMEN HAZIR                          YAPILACAK
──────────────────────                              ─────────
🟡 PostgreSQL geçişi (SQLite'da çalışıyor)          ❌ Cutover Hub (S13)
🟡 Test Mgmt Phase 4-6 (TS-Sprint 4-6)             ❌ Run/Sustain (S17)
🟡 AI Phase 3-5 (S15→S21)                          ❌ Security Module — JWT, row-level (S14)
🟡 Dış Entegrasyonlar (S22a/S22b)                  ❌ Mobile PWA (S23)
🟡 Vue migration cancelled — vanilla JS SPA retained
```

### 📊 İlerleme Metrikleri

```
DB Tabloları:    █████████████████████░░░  77/80+   (%96)
API Route:       ███████████████████████░  336/200+ (%168 — hedef aşıldı!)
AI Asistanlar:   ██████░░░░░░░░░░░░░░░░░  6/14     (%43)
Modüller:        ████████████████░░░░░░░░  8/12     (%67)
Testler:         916 (904 passed, 11 deselected, 1 xfail)
Test/Route:      2.7 ortalama (hedef: 3.0)
```

### Veritabanı Şeması (77 Tablo)

```
program (6)
  ├── projects
  ├── phases
  ├── gates
  ├── workstreams
  ├── team_members
  └── committees

scenario (3)
  ├── scenarios
  ├── workshops (scope module)
  └── workshop_documents

scope (3)
  ├── processes
  ├── requirement_process_mappings
  └── analyses

requirement (3)
  ├── requirements
  ├── requirement_traces
  └── open_items

backlog (5)
  ├── backlog_items (WRICEF)
  ├── config_items
  ├── sprints
  ├── functional_specs
  └── technical_specs

testing (17)
  ├── test_plans
  ├── test_cycles
  ├── test_suites                    ← TS-Sprint 1
  ├── test_cases
  ├── test_steps                     ← TS-Sprint 1
  ├── test_case_dependencies         ← TS-Sprint 1
  ├── test_cycle_suites              ← TS-Sprint 1
  ├── test_executions
  ├── test_runs                      ← TS-Sprint 2
  ├── test_step_results              ← TS-Sprint 2
  ├── defects
  ├── defect_comments                ← TS-Sprint 2
  ├── defect_history                 ← TS-Sprint 2
  ├── defect_links                   ← TS-Sprint 2
  ├── uat_signoffs                    ← TS-Sprint 3
  ├── perf_test_results               ← TS-Sprint 3
  └── test_daily_snapshots            ← TS-Sprint 3

raid (4)
  ├── risks
  ├── actions
  ├── issues
  └── decisions

integration (5)
  ├── interfaces
  ├── waves
  ├── connectivity_tests
  ├── switch_plans
  └── interface_checklists

explore (25)
  ├── process_levels (L1-L4)
  ├── explore_workshops
  ├── workshop_scope_items
  ├── workshop_attendees
  ├── workshop_agenda_items
  ├── process_steps
  ├── explore_decisions
  ├── explore_open_items
  ├── explore_requirements
  ├── requirement_oi_links
  ├── requirement_dependencies
  ├── oi_comments
  ├── cloud_alm_sync_log
  ├── l4_seed_catalog
  ├── project_roles
  ├── phase_gates
  ├── workshop_dependencies
  ├── cross_module_flags
  ├── workshop_revision_logs
  ├── attachments
  ├── scope_change_requests
  ├── scope_change_logs
  ├── bpmn_diagrams
  ├── workshop_documents (explore)
  └── daily_snapshots

ai (5)
  ├── ai_usage_logs
  ├── ai_embeddings
  ├── kb_versions
  ├── ai_suggestions
  └── ai_audit_logs

notification (1)
  └── notifications
```

### Test Kapsamı (916 test — 16 dosya)

| # | Dosya | Test | Kapsam |
|---|-------|:----:|--------|
| 1 | test_explore.py | 192 | Explore Phase (4 grup) |
| 2 | test_api_testing.py | 203 | Test Management (17 model) |
| 3 | test_api_integration.py | 76 | Integration Factory |
| 4 | test_ai.py | 69 | AI Gateway, RAG, Suggestion Queue |
| 5 | test_ai_assistants.py | 72 | NL Query, Req Analyst, Defect Triage |
| 6 | test_api_backlog.py | 59 | Backlog/Config/Sprint/FS/TS |
| 7 | test_api_scope.py | 45 | Process/Analysis/Scope |
| 8 | test_api_requirement.py | 36 | Requirement/Trace/OpenItem |
| 9 | test_api_program.py | 35 | Program/Phase/Gate |
| 10 | test_api_raid.py | 46 | Risk/Action/Issue/Decision |
| 11 | test_api_scenario.py | 24 | Scenario/Workshop |
| 12 | test_kb_versioning.py | 27 | KB Version lifecycle |
| 13 | test_monitoring.py | 15 | Health/Metrics endpoints |
| 14 | test_performance.py | 8 | Response time benchmarks |
| 15-16 | conftest + helpers | 9 | Test altyapısı |
| | **Toplam** | **916** | |

---

## 3. Tamamlanan Sprint Özeti

### Release 1: Foundation & Core (S1-S4) — ✅ KAPANDI

| Sprint | Durum | Çıktı |
|--------|-------|-------|
| S1: Mimari Refactoring | ✅ | Flask App Factory, Program CRUD, Docker |
| S2: PostgreSQL + Program | ✅ | 6 model, 24 endpoint (PG ertelenmiş — SQLite) |
| S3: Scope & Requirements | ✅ | Senaryo, Gereksinim, İzlenebilirlik |
| S4: Backlog + Traceability | ✅ | WRICEF lifecycle, Traceability v1 |

### Release 2: Testing + AI (S5-S8) — ✅ KAPANDI

| Sprint | Durum | Çıktı |
|--------|-------|-------|
| S5: Test Hub | ✅ | TestPlan/Cycle/Case/Execution/Defect (28 route) |
| S6: RAID + Notification | ✅ | 4 model, 30 route, notification service |
| S7: AI Altyapı | ✅ | LLM Gateway, RAG, Suggestion Queue, Prompt Registry |
| S8: AI Phase 1 | ✅ | NL Query, Requirement Analyst, Defect Triage |

### Release 3: Delivery + AI Core (S9-S12) — ✅ TAMAMLANDI

| Sprint | Durum | Çıktı |
|--------|-------|-------|
| S9: Integration Factory | ✅ | 5 model, 26 route, 76 test |
| S9.5: Tech Debt & Hardening | ✅ | P1-P10 iyileştirmeleri, monitoring, Gemini provider |
| Explore Phase (plan dışı) | ✅ | 25 model, 66 route, 192 test, 8 servis, 175/179 task (%98) |
| TS-Sprint 1 | ✅ | TestSuite, TestStep, Dependency, CycleSuite (+4 tablo, +11 route, +37 test) |
| TS-Sprint 2 | ✅ | TestRun, StepResult, DefectComment, History, Link (+5 tablo, +16 route, +46 test) |
| TS-Sprint 3 | ✅ | UAT Sign-Off, Perf Test, Daily Snapshot, SLA, Go/No-Go (+3 tablo, +16 route) |
| FE-Sprint: Frontend Cleanup & Hardening | ✅ | Aşağıda detay |
| S10: Data Factory | ✅ | Aşağıda detay |
| S11: Reporting Engine + Export | ✅ | Aşağıda detay |
| S12a: AI Phase 2a | ✅ | Aşağıda detay |
| S12b: Vue Phase 2b | ❌ Cancelled | Vue migration cancelled — vanilla JS SPA retained |

---

## 4. Güncellenmiş Sprint Planı

### TS-Sprint 3 — Test Mgmt Phase 3: UAT, SLA, Go/No-Go ✅ TAMAMLANDI

> **Scope Netleştirmesi (v2.0):** Consolidated review'dan P1-004/005/006 + P2-C01/C02/C03/C04/C11 bulguları

| # | Task | Açıklama | Effort | Bulgu |
|---|------|----------|:------:|-------|
| TS-3.1 | `UATSignOff` modeli | suite_id, approver, status, criteria JSON | ✅ | P1-004 |
| TS-3.2 | `PerfTestResult` modeli | test_case_id, response_time, throughput, error_rate | ✅ | P1-004 |
| TS-3.3 | `TestDailySnapshot` modeli | snapshot_date, totals, defect counts, metrics JSON | ✅ | P1-004 |
| TS-3.4 | Alembic migration MIG-11 | 3 yeni tablo + index | ✅ | |
| TS-3.5 | Defect 9-status lifecycle | `assigned`+`deferred` ekle, transition guard endpoint | ✅ | P2-C02 |
| TS-3.6 | `generate-from-wricef` endpoint | WRICEF unit_test_steps → TestCase+Step auto-gen | ✅ | P1-005 |
| TS-3.7 | `generate-from-process` endpoint | Explore process_steps → SIT/UAT case auto-gen | ✅ | P1-006 |
| TS-3.8 | SLA engine | SLA_HOURS matrix, sla_breach flag, timer pause on deferred | ✅ | P2-C03 |
| TS-3.9 | Go/No-Go scorecard endpoint | 10 criteria evaluation + structured response | ✅ | P2-C04 |
| TS-3.10 | Entry/exit criteria validation | Cycle start/complete check logic | ✅ | P2-C11 |
| TS-3.11 | Severity S1-S4 standardizasyon | Model constants, seed data, dashboard güncelle | ✅ | P2-O06 |
| TS-3.12 | UAT Sign-off API (4 endpoint) | initiate/approve/reject/status | ✅ | P2-C01 |
| TS-3.13 | Performance test API (3 endpoint) | POST result / GET trend / GET comparison | ✅ | P2-C01 |
| TS-3.14 | Snapshot cron/trigger | Günlük snapshot + manual trigger endpoint | ✅ | P2-C01 |
| TS-3.15 | Seed data — UAT/perf/snapshot | Demo senaryolar | ✅ | |
| TS-3.16 | pytest (~60 test) | CRUD + lifecycle + SLA + scorecard + generation | ✅ | |

**TS-Sprint 3 Toplam: ~43h** (tamamlandı)

---

### TD-Sprint 1 — Teknik Borç Temizliği (Doküman Odaklı)

> **Yeni sprint** — Consolidated review P1-001, P1-002 ve 16 P2 doküman bulgusu

| # | Task | Açıklama | Effort | Status |
|---|------|----------|:------:|:------:|
| TD-1.1 | CHANGELOG güncelle | P1-001 | 1h | ✅ |
| TD-1.2 | README kapsamlı güncelle | P2-D13 | 2h | ✅ |
| TD-1.3 | project-inventory.md düzelt | P2-D14 | 0.5h | ✅ |
| TD-1.4 | D5 başlık + hedef metrikleri güncelle | P2-D04 | 0.5h | ✅ |
| TD-1.5 | D6 PROGRESS_REPORT güncelle | P2-D09,D10 | 1h | ✅ |
| TD-1.6 | D10 tarih + tech debt durum güncelle | R1 F-001,F-004 | 0.5h | ✅ |
| TD-1.7 | D4 (eski architecture) arşivle | R4 D-002 | 0.5h | ✅ |
| TD-1.8 | Makefile lint + format hedefleri | P4 | 0.5h | ✅ |
| TD-1.9 | .env.example güncelle (GEMINI_API_KEY) | P4 | 0.5h | ✅ |

**TD-Sprint 1 Toplam: ~7h** (tek gün tamamlanabilir)

---

### FE-Sprint: Frontend Cleanup & Hardening ✅

| # | Task | Effort | Status |
|---|------|:------:|:------:|
| FE.1 | Legacy blueprint cleanup (archive scenario/scope/requirement_bp) | 1h | ✅ |
| FE.2 | Root MD files cleanup (28→1, archived to docs/) | 0.5h | ✅ |
| FE.3 | Sidebar: RAID+Reports to Program Mgmt, Backlog label fix | 0.5h | ✅ |
| FE.4 | testing.js response parsing fixes (defects/runs unwrap) | 1h | ✅ |
| FE.5 | /workshops/stats endpoint + explore-api fix | 1.5h | ✅ |
| FE.6 | Dashboard 6 KPIs from stats endpoints | 1.5h | ✅ |
| FE.7 | testing.js split → test_planning + test_execution + defect_management | 4h | ✅ |
| FE.8 | Integration Factory seed data (8 interfaces, 2 waves) | 1h | ✅ |
| FE.9 | Test layer diversification (sit/uat/e2e/regression) | 0.5h | ✅ |
| FE.10 | Clickable table rows UX improvement | 1h | ✅ |

**FE-Sprint Total: ~12.5h**

### UI-Sprint: Typography & Design Consistency

| Görev | Dosya | Effort | Bağımlılık |
|-------|-------|:------:|-----------|
| T: Typography Standardization | index.html, main.css, explore-tokens.css, 2 JS | 3.5h | — |
| F: KPI Dashboard Standardization | explore-shared.js, 6 view JS, explore-tokens.css | 3h | T |
| H: Process Hierarchy UI İyileştirme | explore_hierarchy.js, explore-tokens.css | 2h | T, F |
| G: Backlog Page Redesign | backlog.js, main.css | 4h | T, F |
| **Toplam** | | **12.5h** | |

---

### Sprint 10: Data Factory ✅ TAMAMLANDI

| # | Task | Dosya(lar) | Effort | Kaynak |
|---|------|-----------|:------:|--------|
| 10.1 | DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation modelleri | app/models/data_factory.py | 3h | D5 |
| 10.2 | Data Factory API: DataObject CRUD + Mapping + Cycle lifecycle | app/blueprints/data_factory_bp.py | 4h | D5 |
| 10.3 | Data Factory API: Quality score hesaplama | app/blueprints/data_factory_bp.py | 2h | D5 |
| 10.4 | Data Factory UI | static/js/views/data_factory.js | 4h | D5 |
| 10.5 | Cycle comparison dashboard | static/js/views/data_factory.js | 2h | D5 |
| 10.6 | pytest: data factory testleri | tests/ | 1h | D5 |
| 10.7 | Vue 3 Phase 0 | CANCELLED — vanilla JS retained | 0h | D12 |
| 10.8 | Vue 3 Phase 0 | CANCELLED — vanilla JS retained | 0h | D12 |
| 10.9 | Vue 3 Phase 0 | CANCELLED — vanilla JS retained | 0h | D12 |
| 10.10 | Vue 3 Phase 0 | CANCELLED — vanilla JS retained | 0h | D12 |
| 10.11 | 🔧 minutes_generator.py 8 attribute fix | app/services/minutes_generator.py | 2h | P1-003 |
| 10.12 | 🔧 Backend→Frontend field mapping (date, type) | app/models/explore.py | 2h | P2-C07,C08 |
| 10.13 | 🔧 Explore seed (project_roles, phase_gates, l4_catalog) | scripts/seed_data/explore.py | 4h | P2-O07,O08 |
| 10.14 | 🔧 Frontend E2E baseline (5 akış, Playwright) | e2e/ | 5h | P3 |

**Sprint 10 Toplam: ~29h** (16h Data Factory + 13h TD resolutions)

---

### Sprint 11: Reporting Engine + Export ✅ TAMAMLANDI

| # | Task | Effort | Kaynak |
|---|------|:------:|--------|
| 11.1 | KPI aggregation engine: program health snapshot | 4h | R3 |
| 11.2 | RAG calculation rules per area | 3h | R3 |
| 11.3 | Reporting API: /reports/program-health, /reports/weekly | 3h | R3 |
| 11.4 | Export: Excel (.xlsx) | 4h | R3 |
| 11.5 | Export: HTML/PDF | 3h | R3 |
| 11.6 | Reports UI: executive dashboard + export buttons | 2h | R3 |
| 11.7 | Tests | 1h | R3 |
| 11.8 | Vue Phase 1-2a | CANCELLED — vanilla JS retained | 0h | D12 |

**Sprint 11 Toplam: ~20h**

---

### Sprint 12a: AI Phase 2a — 3 Yeni Asistan ✅ TAMAMLANDI

| # | Task | Effort | Kaynak |
|---|------|:------:|--------|
| 12a.1 | Risk Assessment asistan sınıfı + 2 endpoint | 8h | R4 A-001 (P1 prompt ready) |
| 12a.2 | Test Case Generator asistan + prompt template | 10h | R4 A-002 |
| 12a.3 | Change Impact Analyzer asistan | 12h | D11 P3 |
| 12a.4 | Program modülü test coverage artır (+40 test) | ⏸ | DEFERRED |
| 12a.5 | RAID modülü test coverage artır (+44 test) | ⏸ | DEFERRED |
| 12a.6 | SUGGESTION_TYPES genişlet | 0.5h | R4 A-009 |

**Sprint 12a Toplam: ~38.5h** (30h AI + 8.5h test)

### Sprint 12b: Vue Phase 2b — ❌ CANCELLED

Vue migration cancelled — vanilla JS SPA retained.

---

### Sprint 13-16: Release 4 (v1.1 ile aynı yapı, minor güncellemeler)

Sprint 14'e eklenen:
- 🔧 GitHub Actions CI pipeline (lint + test + PG test) | 3h
- 🔧 PostgreSQL test environment | 4h
- 🔧 Alembic chain integrity test | 1h

---

### Sprint 22: Dış Sistem Entegrasyonları — **REVİZE (56h)**

> **⚠️ v2.0 MAJOR CHANGE:** D14 analizi doğrultusunda 18h→56h revize edilmiştir.
> Opsiyon A uygulanmıştır: S22a (shared infra + Jira + Cloud ALM) / S22b (ServiceNow + Teams)

#### Sprint 22a: Shared Infra + Jira + Cloud ALM (Hafta 43)

| # | Task | Effort | Bağımlılık |
|---|------|:------:|------------|
| 22a.1 | Shared connector infra (abstract base, retry, circuit breaker) | 6h | S14 (JWT) |
| 22a.2 | OAuth2 token exchange service | 4h | S14 (JWT) |
| 22a.3 | Webhook framework (inbound/outbound) | 4h | S18 (Celery) |
| 22a.4 | Jira integration: bidirectional defect/requirement sync | 12h | 22a.1 |
| 22a.5 | Cloud ALM integration: test case + defect sync | 10h | 22a.1 |

**Sprint 22a Toplam: ~36h**

#### Sprint 22b: ServiceNow + Teams + UI (Hafta 44)

| # | Task | Effort | Bağımlılık |
|---|------|:------:|------------|
| 22b.1 | ServiceNow integration: incident sync (hypercare) | 8h | 22a.1 |
| 22b.2 | Microsoft Teams: webhook + meeting recording fetch | 6h | 22a.3 |
| 22b.3 | Integration management UI: connection status, sync logs | 3h | 22a.4 |
| 22b.4 | pytest: integration testleri (mock HTTP) | 3h | All |

**Sprint 22b Toplam: ~20h**

**Sprint 22 Genel Toplam: ~56h** (eski: 18h, D14 revize: 56h, delta: +38h)

---

## 5. Bağımlılık Zinciri (Critical Path)

```
S14 (JWT/RBAC) ─────→ S18 (Celery+Redis) ─────→ S22a (Connectors)
     │                      │                         │
     └── S12a (AI P2)       └── S19 (AI P4)           └── S22b (ServiceNow+Teams)
```

> **Risk:** S14 gecikmesi → S18 ve S22 kayar. S22 toplam 56 saat, 2 sprint'e bölünmüş.

---

## 6. Güncellenmiş Zaman Çizelgesi

```
2026
FEB       MAR       APR       MAY       JUN       JUL
 │         │         │         │         │         │
 ├─ TD-1 ──┤         │         │         │         │   (1 gün, doküman temizliği)
 ├─ TS-3 ──┤         │         │         │         │   (Test Mgmt Phase 3, ~43h)
 │         │         │         │         │         │
 │    ├─── S10 ────┤  │         │         │         │   (Data Factory + Explore fix)
 │         │   ├─── S11 ────┤   │         │         │   (Reporting Engine + Export)
 │         │         │  ├── S12a ───┤     │         │   (AI Phase 2a)
 │         │         │  ├── S12b ──┤      │         │   (Cancelled)
 │         │         │         │  │       │         │
 │         │         │         │  ├── R3 GATE ──┤   │
 │         │         │         │         │         │
 │         │         │         │    ├── S13 ────┤    │   (Cutover Hub)
 │         │         │         │         │  ├── S14 ┤   (Security + CI)
 │         │         │         │         │         │
 ▼         ▼         ▼         ▼         ▼         ▼

AUG       SEP       OCT       NOV       DEC       2027 JAN
 │         │         │         │         │         │
 ├── S15 ──┤         │         │         │         │   (AI Phase 3)
 │    ├── S16 ──┤    │         │         │         │   (AI Risk Sentinel ML)
 │         │         │         │         │         │
 │         ├── R4 GATE ──┤    │         │         │
 │         │         │         │         │         │
 │         │    ├── S17 ──┤    │         │         │   (Run/Sustain)
 │         │         │ ├── S18 ──┤       │         │   (Notification + Celery)
 │         │         │    ├── S19 ──┤    │         │   (AI Phase 4)
 │         │         │         │ ├── S20 ┤         │   (AI Perf + Polish)
 │         │         │         │         │         │
 │         │         │         ├── R5 GATE ──┤     │
 │         │         │         │         │         │
 │         │         │         │    ├── S21 ──┤     │   (AI Phase 5)
 │         │         │         │         │ ├─ S22a ┤   (Ext Integrations Part 1)
 │         │         │         │         │    ├ S22b│   (Ext Integrations Part 2)
 │         │         │         │         │         │
 │         │         │         │         │    ├ S23 │   (Mobile PWA)
 │         │         │         │         │      S24│   (Final Polish)
 │         │         │         │         │         │
 ▼         ▼         ▼         ▼         ▼     ⭐ R6 = Platform v1.0
```

---

## 7. Effort Özeti (v2.0 Revize)

| Release | Sprint'ler | Platform | AI | TD | Toplam | Haftalık |
|---------|-----------|:--------:|:--:|:--:|:------:|:--------:|
| R1: Foundation | S1-S4 | 109h | 0 | — | 109h | ~14h |
| R2: Testing+AI | S5-S8 | 55h | 57h | — | 112h | ~14h |
| R3: Delivery+AI | S9-S12 + TS + TD | 51h | 30h | 50h | **131h** | ~11h |
| R4: GoLive+AI | S13-S16 | 37h | 45h | 8h | 90h | ~11h |
| R5: Operations | S17-S20 | 34h | 42h | — | 76h | ~10h |
| R6: Advanced | S21-S24 | 38h+38h | 41h | — | **117h** | ~12h |
| **TOPLAM** | | **362h** | **215h** | **58h** | **635h** | **~11h** |

> **v1.1→v2.0 delta:** +96h (S22 +38h, TS-Sprint 3 scope genişlemesi +24h, TD sprints +34h)

---

## 8. Teknik Borç Takip Tablosu

> Detay: `TECHNICAL_DEBT_BACKLOG.md`

| Kategori | Madde | Effort | Planlama |
|----------|:-----:|:------:|----------|
| Doküman borcu | 24 | ~28h | TD-Sprint 1 + S10 |
| Kod borcu | 22 | ~116h | TS-Sprint 3 + S12a + S14 |
| Test borcu | 10 | ~40h | S10 + S12 + S14 |
| Config/DevOps | 7 | ~15h | S14 |
| **TOPLAM** | **63** | **~199h** | Sprint "Hemen"→S18 |

---

## 9. Başarı Metrikleri (v2.0)

| Metrik | R1 Gerçek | R2 Gerçek | R3 Hedef | R4 Hedef | R6 Hedef |
|--------|:---------:|:---------:|:--------:|:--------:|:--------:|
| API route | 109 | 295 | 360+ | 400+ | 500+ |
| DB tablo | 23 | 40 | 77+ | 85+ | 80+ (net) |
| Pytest | 136 | 766 | 960+ | 1100+ | 1300+ |
| AI asistan | 0 | 3 | 5+ | 11 | 14 |
| Test/route | — | 2.6 | 2.7 | 2.8 | 3.0+ |
| AI accept rate | — | — | >40% | >55% | >65% |
| Doküman borç | — | — | ≤10 madde | ≤5 | 0 |

---

## 10. Risk Yönetimi (v2.0 Güncellenmiş)

| Risk | Olasılık | Etki | Mitigation |
|------|:--------:|:----:|------------|
| S22 56 saat → 2 sprint gerekli, timeline uzar | Yüksek | Yüksek | S22a/S22b bölünme uygulandı, shared infra önce |
| S14 JWT gecikmesi → S18/S22 blocker | Orta | Yüksek | S14'ü erken başlat, JWT stub ile development |
| TS-Sprint 3 scope büyük (43h) → uzama riski | Orta | Orta | TS-Sprint 3a/3b bölme opsiyonu hazır |
| minutes_generator crash → Explore demo riskli | Yüksek | Orta | S10'da acil fix (P1-003) |
| Frontend regression risk | Orta | Orta | E2E baseline + vanilla JS retained |
| CI'da PG test yok → prod sürpriz | Orta | Yüksek | S14'te PG test + CI pipeline |
| Planlanmamış iş oranı %45-50 | Yüksek | Orta | Buffer hafta eklenmiş, D10 analizi güncel |

---

**Dosya:** `SAP_Platform_Project_Plan_v2.md`  
**v1.1 → v2.0 delta:** Sprint 22 revize (18→56h, S22a/S22b), TS-Sprint 3 scope genişleme (19→43h), TD-Sprint ekleme, tüm metrikler güncellenmiş  
**Oluşturan:** GitHub Copilot (Claude Opus 4.6)  
**Tarih:** 2026-02-10
