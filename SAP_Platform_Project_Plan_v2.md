# SAP Transformation Management Platform — Proje Uygulama Planı v2

**Versiyon:** 2.0  
**Tarih:** 10 Şubat 2026  
**Baz Versiyon:** v1.1 → v2.0 delta: consolidated-review-report.md bulgularına göre güncellenmiştir  
**Hazırlayan:** Umut Soyyılmaz  
**Son Commit:** `3c331dd` (TS-Sprint 2 tamamlandı)

> **📌 v2.0 Güncelleme Notları:**
> - Tüm metrikler gerçek duruma hizalandı: **71 DB tablo, 321 API route, 860 test, 74 model, 10 migration, 70 commit**
> - Sprint 22 dış entegrasyon tahmini D14 revizesine göre 18→56 saate güncellendi
> - TS-Sprint 3 scope'u netleştirildi (3 model + 14 endpoint + SLA + Go/No-Go)
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

### ✅ Tamamlanan (Release 1 + 2 + Sprint 9 + Explore Phase + TS-Sprint 1-2)

```
TAMAMLANAN
──────────
✅ Program Setup (6 model, 25 route, 36 test)
✅ Scope & Requirements (3 model, 20 route, 45 test)
✅ Backlog Workbench (5 model, 28 route, 59 test)
✅ Test Hub (14 model, 55 route, 147 test)
   ├── TS-Sprint 1: TestSuite, TestStep, TestCaseDependency, TestCycleSuite (+4 tablo, +11 route)
   └── TS-Sprint 2: TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink (+5 tablo, +16 route)
✅ RAID Module (4 model, 30 route, 46 test)
✅ Integration Factory (5 model, 26 route, 76 test)
✅ AI Altyapı (5 model, 29 route, 141 test)
   ├── LLM Gateway (Anthropic, OpenAI, Gemini, LocalStub — 4 provider)
   ├── RAG Pipeline (8 entity extractor, hybrid search, KB versioning)
   ├── Suggestion Queue (HITL lifecycle)
   └── Prompt Registry (YAML + Jinja2)
✅ AI Phase 1 (3 asistan aktif: NL Query, Requirement Analyst, Defect Triage)
✅ Traceability Engine v1+v2 (Req ↔ WRICEF ↔ TestCase ↔ Defect ↔ Interface)
✅ Notification Service (in-app)
✅ Explore Phase (25 model, 66 route, 192 test, 8 servis, 10 frontend modül)
   ├── Fit/Gap Propagation, Workshop Session, Requirement Lifecycle
   ├── Open Item Lifecycle, Scope Change, Signoff, Snapshot, Minutes Generator
   ├── BPMN Diagram, Workshop Documents, Daily Snapshot
   └── Dashboard & Analytics (KPI kartlar, chart'lar, filtreleme)
✅ Monitoring & Observability (health_bp + metrics_bp, 15 test)

DEVAM EDEN / KISMEN HAZIR                          YAPILACAK
──────────────────────                              ─────────
🟡 Data Factory (S10 planlanıyor)                   ❌ Cutover Hub (S13)
🟡 Reporting Engine (temel KPI var, export eksik)   ❌ Run/Sustain (S17)
🟡 Vue 3 Migration (onaylandı, S10 başlayacak)     ❌ Security Module — JWT, row-level (S14)
🟡 PostgreSQL geçişi (SQLite'da çalışıyor)          ❌ AI Phase 2-5 (11 asistan, S12a→S21)
🟡 Test Mgmt Phase 3 (TS-Sprint 3-6)               ❌ Dış Entegrasyonlar (S22a/S22b)
                                                     ❌ Mobile PWA (S23)
```

### 📊 İlerleme Metrikleri

```
DB Tabloları:    ████████████████████░░░░  71/80+   (%89)
API Route:       ██████████████████████░░  321/200+ (%160 — hedef aşıldı!)
AI Asistanlar:   ████░░░░░░░░░░░░░░░░░░░  3/14     (%21)
Modüller:        ████████████████░░░░░░░░  8/12     (%67)
Testler:         860 (848 passed, 11 deselected, 1 xfail)
Test/Route:      2.7 ortalama (hedef: 3.0)
```

### Veritabanı Şeması (71 Tablo)

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

testing (14)
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
  └── defect_links                   ← TS-Sprint 2

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

### Test Kapsamı (860 test — 16 dosya)

| # | Dosya | Test | Kapsam |
|---|-------|:----:|--------|
| 1 | test_explore.py | 192 | Explore Phase (4 grup) |
| 2 | test_api_testing.py | 147 | Test Management (14 model) |
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
| | **Toplam** | **860** | |

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

### Release 3: Delivery + AI Core (S9-S12) — 🔄 DEVAM EDİYOR

| Sprint | Durum | Çıktı |
|--------|-------|-------|
| S9: Integration Factory | ✅ | 5 model, 26 route, 76 test |
| S9.5: Tech Debt & Hardening | ✅ | P1-P10 iyileştirmeleri, monitoring, Gemini provider |
| Explore Phase (plan dışı) | ✅ | 25 model, 66 route, 192 test, 8 servis, 175/179 task (%98) |
| TS-Sprint 1 | ✅ | TestSuite, TestStep, Dependency, CycleSuite (+4 tablo, +11 route, +37 test) |
| TS-Sprint 2 | ✅ | TestRun, StepResult, DefectComment, History, Link (+5 tablo, +16 route, +46 test) |
| S10: Data Factory + Vue 0 | ⬜ Planlanıyor | Aşağıda detay |
| S11: Reporting + Vue 1 | ⬜ Planlanıyor | |
| S12a: AI Phase 2a | ⬜ Planlanıyor | |
| S12b: Vue Phase 2b | ⬜ Planlanıyor | |

---

## 4. Güncellenmiş Sprint Planı

### TS-Sprint 3 — Test Mgmt Phase 3: UAT, SLA, Go/No-Go (%100 FS/TS hedefli)

> **Scope Netleştirmesi (v2.0):** Consolidated review'dan P1-004/005/006 + P2-C01/C02/C03/C04/C11 bulguları

| # | Task | Açıklama | Effort | Bulgu |
|---|------|----------|:------:|-------|
| TS-3.1 | `UATSignOff` modeli | suite_id, approver, status, criteria JSON | 1.5h | P1-004 |
| TS-3.2 | `PerfTestResult` modeli | test_case_id, response_time, throughput, error_rate | 1.5h | P1-004 |
| TS-3.3 | `TestDailySnapshot` modeli | snapshot_date, totals, defect counts, metrics JSON | 1h | P1-004 |
| TS-3.4 | Alembic migration MIG-11 | 3 yeni tablo + index | 0.5h | |
| TS-3.5 | Defect 9-status lifecycle | `assigned`+`deferred` ekle, transition guard endpoint | 3h | P2-C02 |
| TS-3.6 | `generate-from-wricef` endpoint | WRICEF unit_test_steps → TestCase+Step auto-gen | 6h | P1-005 |
| TS-3.7 | `generate-from-process` endpoint | Explore process_steps → SIT/UAT case auto-gen | 6h | P1-006 |
| TS-3.8 | SLA engine | SLA_HOURS matrix, sla_breach flag, timer pause on deferred | 4h | P2-C03 |
| TS-3.9 | Go/No-Go scorecard endpoint | 10 criteria evaluation + structured response | 3h | P2-C04 |
| TS-3.10 | Entry/exit criteria validation | Cycle start/complete check logic | 4h | P2-C11 |
| TS-3.11 | Severity S1-S4 standardizasyon | Model constants, seed data, dashboard güncelle | 2h | P2-O06 |
| TS-3.12 | UAT Sign-off API (4 endpoint) | initiate/approve/reject/status | 2h | P2-C01 |
| TS-3.13 | Performance test API (3 endpoint) | POST result / GET trend / GET comparison | 1.5h | P2-C01 |
| TS-3.14 | Snapshot cron/trigger | Günlük snapshot + manual trigger endpoint | 2h | P2-C01 |
| TS-3.15 | Seed data — UAT/perf/snapshot | Demo senaryolar | 1h | |
| TS-3.16 | pytest (~60 test) | CRUD + lifecycle + SLA + scorecard + generation | 4h | |

**TS-Sprint 3 Toplam: ~43h** (v1.1'deki 19h → revize: scope genişletildi)

---

### TD-Sprint 1 — Teknik Borç Temizliği (Doküman Odaklı)

> **Yeni sprint** — Consolidated review P1-001, P1-002 ve 16 P2 doküman bulgusu

| # | Task | Açıklama | Effort |
|---|------|----------|:------:|
| TD-1.1 | CHANGELOG güncelle (5 major entry, 33 commit) | P1-001 | 1h |
| TD-1.2 | README kapsamlı güncelle (12 modül, 860 test) | P2-D13 | 2h |
| TD-1.3 | project-inventory.md düzelt (M10, §5.2) | P2-D14 | 0.5h |
| TD-1.4 | D5 başlık + hedef metrikleri güncelle | P2-D04 | 0.5h |
| TD-1.5 | D6 PROGRESS_REPORT güncelle | P2-D09,D10 | 1h |
| TD-1.6 | D10 tarih + tech debt durum güncelle | R1 F-001,F-004 | 0.5h |
| TD-1.7 | D4 (eski architecture) arşivle | R4 D-002 | 0.5h |
| TD-1.8 | Makefile `lint` + `format` hedefleri | P4 | 0.5h |
| TD-1.9 | `.env.example` güncelle (GEMINI_API_KEY) | P4 | 0.5h |

**TD-Sprint 1 Toplam: ~7h** (tek gün tamamlanabilir)

---

### Sprint 10: Data Factory + Vue Phase 0 + Explore Polish

| # | Task | Dosya(lar) | Effort | Kaynak |
|---|------|-----------|:------:|--------|
| 10.1 | DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation modelleri | app/models/data_factory.py | 3h | D5 |
| 10.2 | Data Factory API: DataObject CRUD + Mapping + Cycle lifecycle | app/blueprints/data_factory_bp.py | 4h | D5 |
| 10.3 | Data Factory API: Quality score hesaplama | app/blueprints/data_factory_bp.py | 2h | D5 |
| 10.4 | Data Factory UI | static/js/views/data_factory.js | 4h | D5 |
| 10.5 | Cycle comparison dashboard | static/js/views/data_factory.js | 2h | D5 |
| 10.6 | pytest: data factory testleri | tests/ | 1h | D5 |
| 10.7 | 🟢 Vue 3 Phase 0: Vite + dev/prod config | vite.config.ts, package.json | 0.5h | D12 |
| 10.8 | 🟢 Vue 3 Phase 0: utils.js extract | static/js/utils.js | 0.5h | D12 |
| 10.9 | 🟢 Vue 3 Phase 0: Vue 3 scaffold + VanillaAdapter | src/App.vue | 1h | D12 |
| 10.10 | 🟢 Vue 3 Phase 0: Vitest + Vue Test Utils | vitest.config.ts | 0.5h | D12 |
| 10.11 | 🔧 minutes_generator.py 8 attribute fix | app/services/minutes_generator.py | 2h | P1-003 |
| 10.12 | 🔧 Backend→Frontend field mapping (date, type) | app/models/explore.py | 2h | P2-C07,C08 |
| 10.13 | 🔧 Explore seed (project_roles, phase_gates, l4_catalog) | scripts/seed_data/explore.py | 4h | P2-O07,O08 |
| 10.14 | 🔧 Frontend E2E baseline (5 akış, Playwright) | e2e/ | 5h | P3 |

**Sprint 10 Toplam: ~31.5h** (16h Data Factory + 2.5h Vue + 13h TD resolutions)

---

### Sprint 11: Reporting Engine + Export + Vue Phase 1

(v1.1 ile aynı — değişiklik yok)  
**Sprint 11 Toplam: ~29h** (19h Reporting + 10h Vue Phase 1-2a)

---

### Sprint 12a: AI Phase 2a — 2 Yeni Asistan + Test Artırma

| # | Task | Effort | Kaynak |
|---|------|:------:|--------|
| 12a.1 | Risk Assessment asistan sınıfı + 2 endpoint | 8h | R4 A-001 (P1 prompt ready) |
| 12a.2 | Test Case Generator asistan + prompt template | 10h | R4 A-002 |
| 12a.3 | Change Impact Analyzer asistan (P3) | 12h | D11 P3 |
| 12a.4 | Program modülü test coverage artır (+40 test) | 4h | P3 |
| 12a.5 | RAID modülü test coverage artır (+44 test) | 4h | P3 |
| 12a.6 | SUGGESTION_TYPES genişlet | 0.5h | R4 A-009 |

**Sprint 12a Toplam: ~38.5h** (30h AI + 8.5h test)

### Sprint 12b: Vue Phase 2b

(v1.1 ile aynı — RequirementView, BacklogView, TestingView migration)  
**Sprint 12b Toplam: ~10h**

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
 │    ├─── S10 ────┤  │         │         │         │   (Data Factory + Vue 0 + Explore fix)
 │         │   ├─── S11 ────┤   │         │         │   (Reporting + Vue 1)
 │         │         │  ├── S12a ───┤     │         │   (AI Phase 2a)
 │         │         │  ├── S12b ──┤      │         │   (Vue 2b)
 │         │         │         │  │       │         │
 │         │         │         │  ├── R3 GATE ──┤   │
 │         │         │         │         │         │
 │         │         │         │    ├── S13 ────┤    │   (Cutover + Vue 2c-3)
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
| Frontend 0 test → Vue migration regression | Orta | Orta | S10 Phase 0 + E2E baseline |
| CI'da PG test yok → prod sürpriz | Orta | Yüksek | S14'te PG test + CI pipeline |
| Planlanmamış iş oranı %45-50 | Yüksek | Orta | Buffer hafta eklenmiş, D10 analizi güncel |

---

**Dosya:** `SAP_Platform_Project_Plan_v2.md`  
**v1.1 → v2.0 delta:** Sprint 22 revize (18→56h, S22a/S22b), TS-Sprint 3 scope genişleme (19→43h), TD-Sprint ekleme, tüm metrikler güncellenmiş  
**Oluşturan:** GitHub Copilot (Claude Opus 4.6)  
**Tarih:** 2026-02-10
