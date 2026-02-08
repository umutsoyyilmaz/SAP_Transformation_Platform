# SAP Transformation Platform — Progress Report
**Tarih:** 9 Şubat 2026  
**Sprint:** 1-7 Tamamlandı + 2 Revizyon (Release 1 + Release 2 başlangıç)  
**Repo:** [umutsoyyilmaz/SAP_Transformation_Platform](https://github.com/umutsoyyilmaz/SAP_Transformation_Platform)

---

## Özet

| Metrik | Değer |
|--------|-------|
| Tamamlanan Sprint | 7 / 24 |
| Toplam Commit | 11 |
| Toplam Dosya | 85+ |
| Python LOC | 12,500+ |
| JavaScript LOC | 5,600+ |
| CSS LOC | 1,400+ |
| API Endpoint | ~170 |
| Pytest Test | 353 (tümü geçiyor) |
| Veritabanı Modeli | 33 tablo |
| Alembic Migration | 9 |
| Seed Data | 193 kayıt |

---

## Commit Geçmişi

| # | Commit | Hash | Tarih | Değişiklik |
|---|--------|------|-------|------------|
| 1 | Initial commit | `446d6cd` | 2026-02-07 | Repo oluşturma |
| 2 | **Sprint 1**: Repository Bootstrap | `3e42f06` | 2026-02-07 | .gitignore, requirements.txt, README |
| 3 | **Sprint 1**: Flask App Factory | `502e8af` | 2026-02-07 | create_app + config classes |
| 4 | **Sprint 1**: Mimari Refactoring — tüm 12 task | `2736abb` | 2026-02-08 | +1,672 satır — Flask app, Program CRUD, SPA UI, Docker, testler |
| 5 | **Sprint 2**: PostgreSQL migration + Program Setup | `847e785` | 2026-02-08 | +2,933 satır — 6 model, 24 endpoint, Alembic, Dashboard |
| 6 | **Sprint 3**: Scenario Planner + Requirements Base | `a970b82` | 2026-02-08 | +3,026 satır — Senaryo, Gereksinim, İzlenebilirlik matrisi |
| 7 | **Sprint 1-3**: Progress report | `2a90993` | 2026-02-08 | PROGRESS_REPORT.md eklendi |
| 8 | **Sprint 4-6**: RAID + Notification + Backlog + Test Hub + Gate Check | `a995200` | 2026-02-08 | +8,500 satır — Sprint 4 (WRICEF kanban, Sprint planlama), Sprint 5 (Test Hub, Defect), Gate Check (Scope modülü, 9 düzeltme), Sprint 6 (RAID, Notification, Heatmap) |
| 9 | **Sprint 7-7.5**: AI Infrastructure + Gemini | `db9a8a8` | 2026-02-09 | +7,426 satır — LLM Gateway, RAG Pipeline, Suggestion Queue, 3 AI Asistan, Gemini Free-Tier, 33 yeni dosya |
| 10 | **Revizyon R1**: Program Selector → Context-Based | `789d6cc` | 2026-02-09 | +438/-213 satır — Program card grid, sidebar disable, localStorage context, 10 dosya |
| 11 | **Revizyon R2**: Scenario → İş Senaryosu + Workshop | `133edca` | 2026-02-09 | +1,320/-703 satır — Scenario yeniden yazıldı, Workshop eklendi, ScenarioParameter kaldırıldı, 17 dosya |

---

## Sprint 1 — Mimari Refactoring (Hafta 1-2) ✅

**Amaç:** Temel mimari altyapıyı kurmak.

| Task | Açıklama | Durum |
|------|----------|-------|
| 1.1 | Repository Bootstrap (.gitignore, requirements.txt) | ✅ |
| 1.2 | Flask App Factory (create_app + config) | ✅ |
| 1.3 | SQLAlchemy model base (db instance) | ✅ |
| 1.4 | Program model (temel CRUD entity) | ✅ |
| 1.5 | Program Blueprint (REST API) | ✅ |
| 1.6 | SPA Shell (index.html + sidebar nav) | ✅ |
| 1.7 | SAP Fiori Horizon CSS design system | ✅ |
| 1.8 | API Client helper (fetch wrapper) | ✅ |
| 1.9 | Program JS view (list + create/edit/delete) | ✅ |
| 1.10 | Dashboard view (KPI cards + recent programs) | ✅ |
| 1.11 | Docker configs (Dockerfile, docker-compose) | ✅ |
| 1.12 | pytest test suite (10 test) | ✅ |

**Çıktı:** Flask + SQLAlchemy + SPA çalışan temel platform.

---

## Sprint 2 — PostgreSQL Migration + Program Setup (Hafta 3-4) ✅

**Amaç:** Veritabanı genişletme, program yönetimi derinleştirme.

| Task | Açıklama | Durum |
|------|----------|-------|
| 2.1 | pgvector setup script | ✅ |
| 2.2 | Phase / Gate / Workstream / TeamMember / Committee modelleri | ✅ |
| 2.3 | Alembic migration init + ilk migration | ✅ |
| 2.4 | SQLite migration script (ProjektCoPilot → yeni platform) | ✅ |
| 2.5 | Program API genişletme (24 endpoint) | ✅ |
| 2.6 | Program UI — tabbed detail view (5 tab) | ✅ |
| 2.7 | SAP Activate seed data script | ✅ |
| 2.8 | Auto-phase creation (sap_activate metodolojisi) | ✅ |
| 2.9 | Program Health Dashboard (Chart.js) | ✅ |
| 2.10 | pytest genişletme (36 test) | ✅ |

**Çıktı:** 6 model, 24 API endpoint, SAP Activate faz otomatizasyonu, Dashboard.

---

## Sprint 3 — Scenario Planner + Requirements Base (Hafta 5-6) ✅

**Amaç:** What-if analiz ve gereksinim yönetimi modüllerini oluşturmak.

| Task | Açıklama | Durum |
|------|----------|-------|
| 3.1 | Scenario model (what-if analiz container) | ✅ |
| 3.2 | Requirement model + RequirementTrace (izlenebilirlik) | ✅ |
| 3.3 | Alembic migration (4 yeni tablo) | ✅ |
| 3.4 | Scenario API — CRUD + baseline + karşılaştırma (11 endpoint) | ✅ |
| 3.5 | Requirement API — CRUD + filtreleme + trace + matris + istatistik (10 endpoint) | ✅ |
| 3.6 | Scenario UI — grid view, detay, parametre yönetimi, karşılaştırma tablosu | ✅ |
| 3.7 | Requirements UI — filtreleme, detay, traceability matrix, stats dashboard | ✅ |
| 3.8 | SPA router + nav güncelleme | ✅ |
| 3.9 | Sprint 3 testleri (41 yeni → toplam 77) | ✅ |
| 3.10 | Commit + push + progress report | ✅ |

**Çıktı:** Senaryo karşılaştırma, gereksinim yönetimi (MoSCoW + fit/gap), izlenebilirlik matrisi.

> **[REVISED]** Sprint 3 Scenario modeli v1.1'de tamamen yeniden yazıldı — bkz. Revizyon R2.

---

## Sprint 4 — Backlog Workbench (WRICEF) (Hafta 7-8) ✅

**Amaç:** WRICEF geliştirme nesnelerini yönetmek, kanban board ve sprint planlama. Konfigürasyon, FS/TS yönetimi ve izlenebilirlik motoru.

| Task | Açıklama | Durum |
|------|----------|-------|
| 4.1 | BacklogItem + ConfigItem + FunctionalSpec + TechnicalSpec modelleri | ✅ |
| 4.2 | Status akışı: New → Design → Build → Test → Deploy → Closed (+ Blocked, Cancelled) | ✅ |
| 4.3 | Sprint model — iteration container, kapasite + velocity | ✅ |
| 4.4 | Alembic migration (sprints, backlog_items, config_items, functional_specs, technical_specs) | ✅ |
| 4.5 | Backlog API — CRUD + filtreleme + move/patch + include_specs (8 endpoint) | ✅ |
| 4.6 | Config Items API — CRUD (5 endpoint) | ✅ |
| 4.7 | Functional Spec API — create-for-backlog / create-for-config / get / update (4 endpoint) | ✅ |
| 4.8 | Technical Spec API — create / get / update (3 endpoint) | ✅ |
| 4.9 | Sprint API — CRUD (5 endpoint) | ✅ |
| 4.10 | Kanban Board API — status gruplama + özet metrikleri | ✅ |
| 4.11 | Backlog Stats API — WRICEF dağılımı + effort toplamları | ✅ |
| 4.12 | Traceability Engine — `app/services/traceability.py` (chain, linked-items, summary) | ✅ |
| 4.13 | Traceability API — 3 endpoint (chain, requirement-linked, program-summary) | ✅ |
| 4.14 | Backlog UI — 4 sekmeli görünüm (Kanban, Liste, Config Items, Sprints) | ✅ |
| 4.15 | Config Items UI — tablo, oluştur/düzenle/sil modal | ✅ |
| 4.16 | WRICEF badge + CSS kanban stilleri (yeni status akışı ile) | ✅ |
| 4.17 | Sprint planlama UI — oluştur, düzenle, item ata | ✅ |
| 4.18 | Sprint 4 testleri (59 yeni → toplam 136) | ✅ |
| 4.19 | Progress report güncelleme | ✅ |

### Sprint 4 — Gap Analizi ve Düzeltmeler

Master plan (`SAP_Platform_Project_Plan.md`) ve mimari dokümanına (`sap_transformation_platform_architecture.md`) göre doğrulama yapıldı. Tespit edilen 8 ana eksiklik giderildi:

| Gap | Master Plan Referansı | Düzeltme |
|-----|-----------------------|----------|
| ConfigItem modeli eksik | Task 4.1 | `ConfigItem` modeli eklendi (config_key, module, transaction, status) |
| FunctionalSpec/TechnicalSpec eksik | Task 4.1 | `FunctionalSpec` + `TechnicalSpec` modelleri eklendi (1:1 polymorphic FK) |
| Status akışı uyumsuz | Task 4.2 | open→in_progress→done yerine New→Design→Build→Test→Deploy→Closed |
| Config CRUD API'si yok | Task 4.6 | 5 yeni endpoint eklendi (list/create/get/update/delete) |
| FS/TS CRUD API'si yok | Task 4.6 | 7 yeni endpoint eklendi (FS: 4, TS: 3) |
| Traceability motoru yok | Task 4.7 | `app/services/traceability.py` oluşturuldu (chain traversal) |
| Traceability API'si yok | Task 4.8 | 3 yeni endpoint eklendi (chain, linked-items, summary) |
| Config Items UI yok | Task 4.10 | 4. sekme olarak Config Items eklendi (tablo + CRUD modal) |

**Çıktı:** WRICEF kanban board, sprint planlama, konfigürasyon yönetimi, FS/TS doküman yönetimi, izlenebilirlik motoru (Scenario → Requirement → WRICEF/Config → FS → TS zinciri).

---

## Sprint 5 — Test Hub: Catalog & Execution (Hafta 9-10) ✅

**Amaç:** Test planlama, test case kataloğu, test yürütme, defect yönetimi ve KPI dashboard.

| Task | Açıklama | Durum |
|------|----------|-------|
| 5.1 | TestPlan, TestCycle, TestCase, TestExecution, Defect modelleri | ✅ |
| 5.2 | Alembic migration (5 yeni tablo) | ✅ |
| 5.3 | Test Case API: CRUD + filter (layer, status, module, regression, search) + auto-code | ✅ |
| 5.4 | Test Execution API: plan → cycle → execution workflow | ✅ |
| 5.5 | Defect API: CRUD + severity + linked WRICEF/Config + aging calculation | ✅ |
| 5.6 | Traceability extension: TestCase ↔ Requirement, Defect ↔ WRICEF | ✅ |
| 5.7 | Traceability Matrix API: GET /traceability-matrix (Req ↔ TC ↔ Defect) | ✅ |
| 5.8 | Test Hub UI: Catalog list + case detail + create/edit modal | ✅ |
| 5.9 | Test Execution UI: Plans & Cycles view + execution workflow | ✅ |
| 5.10 | Defect UI: Defect list + detail + lifecycle (reopen/resolve) | ✅ |
| 5.11 | Test KPI Dashboard: pass rate, severity dist, aging, burndown, coverage (Chart.js) | ✅ |
| 5.12 | pytest test suite (63 yeni test → toplam 199) | ✅ |

**Gap Fix:** Traceability motoru genişletildi — artık TestCase ve Defect entity'leri de chain traversal'a dahil.

**Çıktı:** Test Plans/Cycles, Test Case Catalog (6 katman: Unit/SIT/UAT/Regression/Performance/Cutover), Test Execution (sonuç kayıt), Defect Lifecycle (P1-P4 severity, aging, reopen tracking), Traceability Matrix, Regression Sets, KPI Dashboard (7 metrik + 3 chart).

---

## Veritabanı Şeması (Sprint 5 sonu — Arşiv)

<details><summary>Genişlet (eski şema)</summary>

```
programs
├── phases
│   └── gates
├── workstreams
│   └── team_members (FK)
├── team_members
├── committees
├── scenarios
│   └── scenario_parameters
├── requirements
│   ├── requirements (self-ref: parent/child hiyerarşi)
│   └── requirement_traces (polymorphic → phase/workstream/scenario/requirement/gate)
├── sprints
│   └── backlog_items (FK)
├── backlog_items
│   ├── sprint (FK → sprints, nullable)
│   ├── requirement (FK → requirements, nullable)
│   └── functional_specs (1:1 FS dokümanı)
│       └── technical_specs (1:1 TS dokümanı)
├── config_items
│   └── functional_specs (1:1 FS dokümanı)
│       └── technical_specs (1:1 TS dokümanı)
├── test_plans
│   └── test_cycles
│       └── test_executions (→ test_cases FK)
├── test_cases (→ requirement FK, backlog_item FK, config_item FK)
│   └── defects (→ test_case FK, backlog_item FK, config_item FK)
└── defects
```

**20 tablo:** programs, phases, gates, workstreams, team_members, committees, scenarios, scenario_parameters, requirements, requirement_traces, sprints, backlog_items, config_items, functional_specs, technical_specs, test_plans, test_cycles, test_cases, test_executions, defects

</details>

---

## API Endpoint Özeti (~148 toplam)

| Modül | Endpoint Sayısı | Yöntem |
|-------|----------------|--------|
| Programs | 5 | CRUD + list filter |
| Phases | 4 | CRUD under program |
| Gates | 3 | CUD under phase |
| Workstreams | 4 | CRUD under program |
| Team Members | 4 | CRUD under program |
| Committees | 4 | CRUD under program |
| Scenarios | 6 | CRUD + filter + stats |
| Workshops | 5 | CRUD under scenario |
| Requirements | 5 | CRUD + filtered list |
| Requirement Traces | 3 | CLD under requirement |
| Traceability Matrix | 1 | GET program matrix |
| Requirement Stats | 1 | GET aggregated stats |
| Processes | 7 | CRUD + tree + stats |
| Scope Items | 6 | CRUD + filter + summary |
| Analyses | 6 | CRUD + summary |
| Backlog Items | 6 | CRUD + move/patch + filtered list |
| Backlog Board | 1 | GET kanban board view |
| Backlog Stats | 1 | GET aggregated stats |
| Config Items | 5 | CRUD under program |
| Functional Specs | 4 | Create (backlog/config) + get + update |
| Technical Specs | 3 | Create + get + update |
| Traceability Engine | 3 | Chain + linked-items + program-summary |
| Sprints | 5 | CRUD under program |
| Test Plans | 5 | CRUD + list filter |
| Test Cycles | 5 | CRUD under plan |
| Test Cases (Catalog) | 5 | CRUD + filter (layer/status/module/regression/search) |
| Test Executions | 5 | CRUD + result recording |
| Defects | 5 | CRUD + severity + lifecycle (reopen/resolve) |
| Traceability Matrix (Test) | 1 | GET Req ↔ TC ↔ Defect matrix |
| Regression Sets | 1 | GET flagged regression cases |
| Test Dashboard | 1 | GET KPI data (pass rate, severity, burndown, coverage) |
| **Risks** | **6** | **CRUD + filter + score recalculate** |
| **Actions** | **6** | **CRUD + status patch + auto-complete date** |
| **Issues** | **6** | **CRUD + filter severity + status patch + auto-resolve date** |
| **Decisions** | **6** | **CRUD + status patch + approval notification** |
| **RAID Stats** | **1** | **GET aggregate stats (open/critical/overdue)** |
| **RAID Heatmap** | **1** | **GET 5×5 probability × impact matrix** |
| **Notifications** | **4** | **List + unread-count + mark-read + mark-all-read** |
| Health | 1 | GET health check |

---

## Test Kapsama

| Test Dosyası | Test Sayısı | Kapsam |
|-------------|-------------|--------|
| test_api_program.py | 36 | Programs, Phases, Gates, Workstreams, Team, Committees |
| test_api_scenario.py | 21 | Scenarios, Parameters, Baseline, Comparison |
| test_api_requirement.py | 20 | Requirements, Filtering, Traces, Matrix, Stats |
| test_api_scope.py | 38 | Processes, ScopeItems, Analyses CRUD + filters |
| test_api_backlog.py | 59 | BacklogItems, WRICEF types, Move/PATCH, Board, Stats, Sprints, Config Items, FS/TS, Traceability |
| test_api_testing.py | 63 | TestPlans, TestCycles, TestCases, TestExecutions, Defects, Traceability Matrix, Regression Sets, Dashboard |
| test_api_raid.py | 46 | Risks, Actions, Issues, Decisions, RAID Stats, Heatmap, Notifications, Risk Scoring |
| **Toplam** | **284** | **Tümü geçiyor (~2.06s)** |

---

## Teknoloji Stack

| Katman | Teknoloji | Versiyon |
|--------|-----------|----------|
| Dil | Python | 3.13.2 |
| Web Framework | Flask | 3.1.0 |
| ORM | SQLAlchemy | 2.0.36 |
| Migration | Flask-Migrate (Alembic) | 4.0.7 |
| CORS | Flask-CORS | 5.0.0 |
| DB Driver | psycopg | 3.2.4 |
| DB (dev) | SQLite | — |
| DB (prod) | PostgreSQL 16 + pgvector | — |
| Frontend | Vanilla JS SPA | — |
| CSS | SAP Fiori Horizon (custom) | — |
| Charts | Chart.js | 4.4.7 |
| Test | pytest | 8.3.4 |
| Container | Docker + Compose | — |

---

---

## 🚩 Gate Check Bulguları (Sprint 1-5 Audit)

**Audit Tarihi:** 8 Şubat 2026  
**Referans:** `SAP_Platform_Project_Plan.md` + `sap_transformation_platform_architecture (2).md`

### Sprint Uyum Skorları (Düzeltme Sonrası)

| Sprint | Eski Skor | Yeni Skor | Durum |
|--------|-----------|-----------|-------|
| Sprint 1 (Mimari Refactoring) | %92 | %92 | ✅ Tam |
| Sprint 2 (Program Setup) | %80 | %90 | ✅ Tam (Gates LIST eklendi) |
| Sprint 3 (Scope & Requirements) | %33 | %100 | ✅ Tam (Process/ScopeItem/Analysis + auto-code + convert) |
| Sprint 4 (Backlog Workbench) | %67 | %100 | ✅ Tam (Detail tabs + traceability badge + config detail) |
| Sprint 5 (Test Hub) | %100 | %100 | ✅ Mükemmel (Environment Stability eklendi) |
| **GENEL** | **%74** | **%96** | **56/58 task** |

### Yapılan Düzeltmeler

**Yeni Dosyalar:**
- `app/models/scope.py` — Process, ScopeItem, Analysis modelleri (230 satır)
- `app/blueprints/scope_bp.py` — 22 Scope API endpoint (290 satır)
- `tests/test_api_scope.py` — 38 test (Process/ScopeItem/Analysis CRUD)
- `migrations/versions/a7ac281a764b_sprint_3_scope_process_analysis_models.py`

**Güncellenen Dosyalar:**
- `app/__init__.py` — scope model + blueprint registrasyonu
- `app/blueprints/requirement_bp.py` — auto-code üretimi + convert endpoint
- `app/blueprints/program_bp.py` — Gates LIST endpoint
- `app/blueprints/testing_bp.py` — Environment Stability KPI
- `app/services/traceability.py` — Process/ScopeItem/Analysis chain traversal (11 entity type)
- `static/js/views/backlog.js` — Tabbed detail (Overview/Specs/Tests/Trace), traceability badge, config detail
- `static/css/main.css` — trace-badge, detail-tab CSS
- `scripts/seed_demo_data.py` — 11 process, 8 scope item, 4 analysis seed data

**Test Sonucu:** 238 test ✅ (200 mevcut + 38 yeni scope test)

### Kritik Bulgular (Düzeltildi ✅)

| # | Bulgu | Sprint | Durum |
|---|-------|--------|-------|
| 1 | Process, ScopeItem, Analysis modelleri eksik | S3 | ✅ Düzeltildi |
| 2 | Requirement auto-code üretimi eksik | S3 | ✅ Düzeltildi |
| 3 | Requirement → WRICEF/Config convert endpoint eksik | S3 | ✅ Düzeltildi |

### Orta Bulgular (Düzeltildi ✅)

| # | Bulgu | Sprint | Durum |
|---|-------|--------|-------|
| 4 | Backlog detail'de FS/TS/Tests/History tab'ları eksik | S4 | ✅ Düzeltildi |
| 5 | Traceability badge UI'da görünmüyor | S4 | ✅ Düzeltildi |
| 6 | Environment Stability KPI eksik | S5 | ✅ Düzeltildi |
| 7 | Config item ayrı detail sayfası eksik | S4 | ✅ Düzeltildi |
| 8 | SAP Best Practice Scope Item seed data eksik | S3 | ✅ Düzeltildi |
| 9 | Gates LIST endpoint eksik | S2 | ✅ Düzeltildi |

---

## Sprint 6 — RAID Module + Notification Foundation (Hafta 11-12) ✅

**Amaç:** Risk, Action, Issue, Decision (RAID) yönetimi ve bildirim altyapısı.

| Task | Açıklama | Durum |
|------|----------|-------|
| 6.1 | Risk, Action, Issue, Decision modelleri (`app/models/raid.py`) | ✅ |
| 6.2 | Notification modeli (`app/models/notification.py`) | ✅ |
| 6.3 | NotificationService (`app/services/notification.py`) | ✅ |
| 6.4 | RAID Blueprint — 26 API endpoint (`app/blueprints/raid_bp.py`) | ✅ |
| 6.5 | Alembic migration (5 yeni tablo: risks, actions, issues, decisions, notifications) | ✅ |
| 6.6 | Seed data — 16 RAID kaydı (5 risk, 5 action, 3 issue, 3 decision) | ✅ |
| 6.7 | RAID UI — Dashboard, Heatmap, Tabbed list views, CRUD modals (`static/js/views/raid.js`) | ✅ |
| 6.8 | Notification UI — Bell badge, dropdown, polling, mark-read (`static/js/components/notification.js`) | ✅ |
| 6.9 | pytest test suite (46 yeni test → toplam 284) | ✅ |

### Sprint 6 — Teknik Detaylar

**Risk Modeli:**
- `probability` × `impact` → `risk_score` (1-25) → `rag_status` (green/amber/orange/red)
- Kategoriler: technical, organisational, commercial, external, schedule, resource, scope
- Yanıtlar: avoid, transfer, mitigate, accept, escalate
- Otomatik kod: RSK-001, RSK-002...

**Action Modeli:**
- `action_type`: preventive, corrective, detective, improvement, follow_up
- `due_date`, `completed_date` (auto-set on complete)
- Linked entity (polymorphic: risk, issue)
- Otomatik kod: ACT-001, ACT-002...

**Issue Modeli:**
- `severity`: minor, moderate, major, critical
- `escalation_path`, `root_cause`, `resolution`, `resolution_date`
- Otomatik notification: severity=critical → NotificationService.notify_critical_issue()
- Otomatik kod: ISS-001, ISS-002...

**Decision Modeli:**
- `alternatives`, `rationale`, `impact_description`, `reversible`
- Status: proposed → under_review → approved/rejected/deferred
- Otomatik notification: status=approved → NotificationService.notify_decision_approved()
- Otomatik kod: DEC-001, DEC-002...

**Notification Service:**
- `create()`, `broadcast()`, `list_for_recipient()`, `unread_count()`, `mark_read()`, `mark_all_read()`
- RAID entegrasyon: `notify_risk_score_change()`, `notify_action_overdue()`, `notify_critical_issue()`, `notify_decision_approved()`

**Heatmap API:**
- 5×5 matris (probability × impact), her hücrede risk listesi
- Tıklanabilir hücreler → risk detay popup

**Çıktı:** RAID Log (Risk/Action/Issue/Decision) + Notification altyapısı, 5×5 risk heatmap, 26 API endpoint, 46 test.

---

## Veritabanı Şeması (Sprint 6 sonu)

```
programs
├── phases
│   └── gates
├── workstreams
│   └── team_members (FK)
├── team_members
├── committees
├── scenarios
│   ├── workshops (analiz oturumları)
│   └── processes (L1/L2/L3)
│       └── scope_items
│           └── analyses (fit-gap workshop)
├── requirements (workshop_id FK — nullable)
│   ├── requirements (self-ref: parent/child hiyerarşi)
│   └── requirement_traces (polymorphic → phase/workstream/scenario/requirement/gate)
├── sprints
│   └── backlog_items (FK)
├── backlog_items
│   ├── sprint (FK → sprints, nullable)
│   ├── requirement (FK → requirements, nullable)
│   └── functional_specs (1:1 FS dokümanı)
│       └── technical_specs (1:1 TS dokümanı)
├── config_items
│   └── functional_specs (1:1 FS dokümanı)
│       └── technical_specs (1:1 TS dokümanı)
├── test_plans
│   └── test_cycles
│       └── test_executions (→ test_cases FK)
├── test_cases (→ requirement FK, backlog_item FK, config_item FK)
│   └── defects (→ test_case FK, backlog_item FK, config_item FK)
├── defects
├── risks (→ program FK) ← YENİ
├── actions (→ program FK) ← YENİ
├── issues (→ program FK) ← YENİ
├── decisions (→ program FK) ← YENİ
└── notifications ← YENİ
```

**28 tablo:** programs, phases, gates, workstreams, team_members, committees, scenarios, **workshops** *(yeni — v1.1)*, requirements, requirement_traces, processes, scope_items, analyses, sprints, backlog_items, config_items, functional_specs, technical_specs, test_plans, test_cycles, test_cases, test_executions, defects, **risks**, **actions**, **issues**, **decisions**, **notifications**, **ai_usage_logs**, **ai_embeddings**, **ai_suggestions**, **ai_audit_logs**\n\n> **Not:** `scenario_parameters` tablosu v1.1 revizyonunda kaldırıldı. `workshops` tablosu eklendi.

---

## Sprint 7 — AI Altyapı Kurulumu (Hafta 13-14) ✅

**Amaç:** LLM gateway, RAG pipeline, öneri kuyruğu ve prompt yönetim altyapısını kurmak.

| Task | Açıklama | Durum |
|------|----------|-------|
| 7.1 | LLM Gateway — Provider Router (Anthropic, OpenAI, Gemini, LocalStub) | ✅ |
| 7.2 | Token tracking & cost monitor (usage log, pricing) | ✅ |
| 7.3 | AI modelleri + Alembic migration (4 yeni tablo) | ✅ |
| 7.4 | RAG Chunking Engine (8 entity extractor) | ✅ |
| 7.5 | RAG Embedding + Hybrid Search (cosine + BM25 + RRF) | ✅ |
| 7.6 | Suggestion Queue model + API (~18 endpoint) | ✅ |
| 7.7 | Suggestion Queue UI (header badge + dropdown) | ✅ |
| 7.8 | Prompt Registry (YAML + built-in defaults) | ✅ |
| 7.9 | SAP Knowledge Base embed script (15 entity type) | ✅ |
| 7.10 | AI Admin Dashboard (5 tab, KPI, grafikler) | ✅ |
| 7.11 | AI Audit Log (immutable trail) | ✅ |
| 7.12 | pytest AI testleri (62 test) | ✅ |
| 7.13 | Google Gemini Free-Tier entegrasyonu (GeminiProvider) | ✅ |
| 7.14 | Default model → Gemini (chat + embeddings) | ✅ |
| 7.15 | Gemini testleri (7 yeni → toplam 69 AI test) | ✅ |

**Yeni Dosyalar:**
- `app/ai/__init__.py` — AI package init
- `app/ai/gateway.py` — LLM Gateway (610 satır — multi-provider, Gemini/Anthropic/OpenAI/LocalStub, retry, logging)
- `app/ai/rag.py` — RAG Pipeline (590 satır — chunking, embedding, hybrid search)
- `app/ai/suggestion_queue.py` — Suggestion Queue service (227 satır)
- `app/ai/prompt_registry.py` — Prompt yönetimi (325 satır)
- `app/models/ai.py` — 4 AI model (286 satır)
- `app/blueprints/ai_bp.py` — AI blueprint ~18 endpoint (427 satır)
- `ai_knowledge/prompts/` — 4 YAML prompt template
- `static/js/views/ai_admin.js` — AI Admin Dashboard (300 satır)
- `static/js/components/suggestion-badge.js` — Header badge bileşeni (120 satır)
- `scripts/embed_knowledge_base.py` — Knowledge base embedding script
- `tests/test_ai.py` — 69 test (62 orijinal + 7 Gemini)
- `.env.example` — AI provider API key referansları güncellendi

**Yeni API Endpoints (18):**
- `GET/POST /api/v1/ai/suggestions` — Listeleme + oluşturma
- `GET /api/v1/ai/suggestions/pending-count` — Bekleyen sayısı
- `GET /api/v1/ai/suggestions/stats` — İstatistikler
- `GET /api/v1/ai/suggestions/<id>` — Detay
- `PATCH /api/v1/ai/suggestions/<id>/approve` — Onayla
- `PATCH /api/v1/ai/suggestions/<id>/reject` — Reddet
- `PATCH /api/v1/ai/suggestions/<id>/modify` — Düzenle
- `GET /api/v1/ai/usage` — Token kullanım istatistikleri
- `GET /api/v1/ai/usage/cost` — Maliyet timeline
- `GET /api/v1/ai/audit-log` — Audit log (filtreli, sayfalı)
- `POST /api/v1/ai/embeddings/search` — Hybrid arama
- `GET /api/v1/ai/embeddings/stats` — Index istatistikleri
- `POST /api/v1/ai/embeddings/index` — Batch embedding
- `GET /api/v1/ai/admin/dashboard` — Dashboard verisi
- `GET /api/v1/ai/prompts` — Kayıtlı şablonlar

---

## Revizyon R1 — Program Selector → Context-Based Program Selection ✅

**Tarih:** 9 Şubat 2026  
**Commit:** `789d6cc`  
**Amaç:** Header'daki program selector dropdown'ı kaldırıp, kart bazlı program seçim modeline geçmek.

| Değişiklik | Dosya | Açıklama |
|------------|-------|----------|
| Program card grid | `static/js/views/program.js` | Grid'de programa tıklayınca `App.setActiveProgram()` ile seçim |
| Sidebar disable state | `static/js/app.js` | Program seçilmeden sidebar menüleri opacity 0.5 + pointer-events:none |
| Program-specific dashboard | `static/js/app.js` | Seçili program bilgisi sidebar'da gösterilir |
| localStorage persist | `static/js/app.js` | `sap_active_program` key ile kalıcı seçim |
| Header cleanup | `templates/index.html` | Program selector dropdown kaldırıldı |
| CSS güncellemesi | `static/css/main.css` | `.sidebar-program-badge`, disabled state stilleri |
| View güncellemeleri | `scenario.js, requirement.js, backlog.js, raid.js, ai_query.js, testing.js` | `App.getActiveProgram()` ile merkezi erişim |

**Etki:** 10 dosya, +438/-213 satır.

---

## Revizyon R2 — Scenario → İş Senaryosu + Workshop Modeli ✅

**Tarih:** 9 Şubat 2026  
**Amaç:** "What-if yaklaşım karşılaştırma" olan Scenario modülünü gerçek "İş Senaryosu" modeline dönüştürmek. Workshop/Analiz Oturumu katmanı ekleyerek requirement akışını Scenario → Workshop → Requirement olarak yapılandırmak.

### Mimari Değişiklik

**Eski model (kaldırıldı):**
```
Scenario (what-if: Greenfield vs Brownfield)
  └── ScenarioParameter (key/value)
```

**Yeni model:**
```
Scenario (İş Senaryosu: Sevkiyat Süreci, Satın Alma, Pricing)
  ├── Workshop (Fit-Gap Workshop, Design Workshop, Demo, Sign-Off, Training)
  │     └── Requirement (workshop_id nullable — doğrudan da eklenebilir)
  └── Process (L1/L2/L3 — mevcut yapı korundu)
```

### Yapılan Değişiklikler

| Kategori | Dosya | Değişiklik |
|----------|-------|------------|
| **Model** | `app/models/scenario.py` | Scenario yeniden yazıldı (sap_module, process_area, priority, owner, workstream). ScenarioParameter → silindi. Workshop modeli eklendi (session_type, status, session_date, facilitator, attendees, agenda, notes, decisions, fit/gap/partial counts) |
| **Model** | `app/models/requirement.py` | `workshop_id` FK eklendi (nullable, SET NULL on delete) |
| **Migration** | `migrations/versions/d1f5a7b3c890_...` | workshops tablosu oluşturuldu, scenario eski kolonlar drop, yeni kolonlar add, scenario_parameters tablosu drop, requirements'a workshop_id eklendi |
| **API** | `app/blueprints/scenario_bp.py` | Tamamen yeniden yazıldı — business scenario CRUD (filtreleme: status, module, process_area, priority) + Workshop CRUD (list/create/get/update/delete) + Stats endpoint |
| **Frontend** | `static/js/views/scenario.js` | Tamamen yeniden yazıldı — business scenario kart grid, filtre bar, scenario detail → workshop listesi, workshop detail → requirement tablosu, CRUD modallar |
| **CSS** | `static/css/main.css` | Workshop card stilleri, session type badge renkleri, fit/gap/partial count stilleri, priority badge'leri |
| **Seed Data** | `scripts/seed_demo_data.py` | 5 approach scenario → 5 iş senaryosu (Sevkiyat, Satın Alma, Üretim Planlama, Finansal Kapanış, İnsan Kaynakları). Workshop seed data eklendi. ScenarioParameter seed kaldırıldı |
| **Tests** | `tests/test_api_scenario.py` | Workshop CRUD testleri eklendi, ScenarioParameter temizlendi |
| **Refs** | `traceability.py, requirement_bp.py, scope_bp.py, nl_query.py, db_status.py, embed_knowledge_base.py` | ScenarioParameter → Workshop import güncellemeleri, şema açıklamaları güncellendi |

### Workshop Session Types

| Tip | Açıklama |
|-----|----------|
| `fit_gap_workshop` | Fit/Gap analiz oturumu — standart SAP süreçleri vs müşteri gereksinimleri |
| `requirement_gathering` | Gereksinim toplama oturumu |
| `process_mapping` | Süreç haritalama (AS-IS → TO-BE) |
| `review` | Gözden geçirme toplantısı |
| `design_workshop` | Tasarım workshop'u (çözüm tasarımı) |
| `demo` | Demo / prototip sunumu |
| `sign_off` | Onay toplantısı (resmi kabul) |
| `training` | Eğitim oturumu |

### Yeni API Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/api/v1/programs/<pid>/scenarios?status=&module=&priority=` | Filtrelenen senaryo listesi |
| GET | `/api/v1/programs/<pid>/scenarios/stats` | İstatistikler (by_status, by_priority, by_module) |
| GET | `/api/v1/scenarios/<sid>/workshops` | Senaryo workshop listesi |
| POST | `/api/v1/scenarios/<sid>/workshops` | Workshop oluştur |
| GET | `/api/v1/workshops/<wid>` | Workshop detay + linked requirements |
| PUT | `/api/v1/workshops/<wid>` | Workshop güncelle |
| DELETE | `/api/v1/workshops/<wid>` | Workshop sil |

**Kaldırılan Endpoints:** `/scenarios/<id>/set-baseline`, `/scenarios/<sid>/parameters`, `/scenario-parameters/<id>`, `/programs/<pid>/scenarios/compare`

**Etki:** 16+ dosya, ~1,200 satır değişiklik.

---

## Sonraki Sprint

**Sprint 8 — AI-Powered Analysis (Hafta 15-16)**
- Gemini API ile gerçek Fit/Gap sınıflandırma
- Defect triage otomasyonu
- NL-to-SQL sorgu motoru
- Risk proaktif analiz
