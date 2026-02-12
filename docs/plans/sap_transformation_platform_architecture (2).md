# SAP Transformation Management Platform — Uygulama Mimarisi

**Versiyon:** 2.0  
**Tarih:** 12 Şubat 2026  
**Baz Versiyon:** v1.3 → v2.0 (Kapsamlı güncelleme: Release 3.5 tamamlandı, tüm modüller ve sprint roadmap entegre edildi)  
**Hazırlayan:** Umut Soyyılmaz  
**Kaynak:** SAP Transformation PM Playbook (S/4HANA + Public Cloud)

### Revizyon Geçmişi

| Versiyon | Tarih | Değişiklik |
|----------|-------|------------|
| 1.0 | 2026-02-07 | İlk yayın |
| 1.1 | 2026-02-09 | Context-Based Program Selection, Workshop CRUD |
| 1.2 | 2026-02-09 | Hiyerarşi refactoring, scope/fit-gap alanları Process L3'e absorbe |
| 1.3 | Haziran 2025 | Explore Phase: 25 model, 66 route, 8 servis. Release 1+2 tamamlandı |
| **2.0** | **12 Şubat 2026** | **Kapsamlı güncelleme:** Release 3.5 tamamlandı (WR-0→WR-4). 85 model, 359 route, 985 test. Workshop Rebuild, Governance Engine, Audit Trail, Demo Flow, Multi-Tenant, Productization. 6 AI asistan aktif. Sprint Roadmap (R4-R6) entegre edildi. |

---

## 1. Vizyon ve Tasarım İlkeleri

### 1.1 Amaç

SAP dönüşüm programlarının (Greenfield, Brownfield, Selective, Public Cloud) uçtan uca yönetimi, takibi ve raporlanması için tek bir platform. Playbook'taki şu akışı dijitalleştirir:

```
Program → ProcessLevel L1 (Value Chain) → L2 (Process Area) → L3 (E2E Process) → L4 (Sub-Process)
    → ExploreWorkshop (Fit-to-Standard Session)
        → ProcessStep (L4 assessment: Fit / Partial Fit / Gap)
            → ExploreDecision + ExploreOpenItem + ExploreRequirement
                → BacklogItem (WRICEF) / ConfigItem
                    → FunctionalSpec → TechnicalSpec
                        → TestCase → TestExecution → Defect
                            → Cutover Tasks → Hypercare Incidents

Traceability Chain: Requirement ↔ BacklogItem ↔ TestCase ↔ Defect ↔ Interface
Cross-cutting: RAID (Risk, Action, Issue, Decision) + Notification + AI + Audit + Governance
```

### 1.2 Tasarım İlkeleri

| # | İlke | Açıklama |
|---|-------|----------|
| 1 | **Traceability-First** | Her artefact, üst ve alt seviyeye izlenebilir olmalı (requirement → test case → defect → cutover task) |
| 2 | **Phase-Gate Driven** | SAP Activate fazları ve kalite-gate'leri platformun omurgasını oluşturur |
| 3 | **Workstream-Centric** | Her modül workstream bazlı filtrelenebilir, raporlanabilir |
| 4 | **Configurable, Not Custom** | Proje tipi seçimine göre modüller ve şablonlar otomatik adapte olur |
| 5 | **Dashboard-Native** | Her modülün kendi KPI seti ve görsel dashboard'u olmalı |
| 6 | **Human-in-the-Loop AI** | Tüm AI asistanları öneri üretir, nihai karar her zaman insanda kalır |
| 7 | **Multi-Tenant Ready** | Database-per-tenant izolasyonu ile müşteriler arası veri güvenliği |
| 8 | **Governance-Driven** | Merkezi kurallar, threshold'lar ve RACI template'leri ile PM governance |

---

## 2. Üst Seviye Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────────┐ │
│  │ Web SPA  │ │ Executive│ │ Demo     │ │ Role-Based             │ │
│  │(Vanilla  │ │ Cockpit  │ │ Flow     │ │ Navigation             │ │
│  │ JS+CSS)  │ │(Chart.js)│ │ Engine   │ │ (7 Rol)                │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────────┘ │
│  28 JS modül (15,810 LOC) + 2 CSS dosyası (4,419 LOC)             │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST JSON API
┌────────────────────────────┴────────────────────────────────────────┐
│                    APPLICATION LAYER (Flask)                         │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │
│  │ Program     │ │ Explore     │ │ Backlog     │ │ Test Hub     │ │
│  │ Setup       │ │ Phase       │ │ Workbench   │ │ (17 model)   │ │
│  │ (25 route)  │ │ (97 route)  │ │ (28 route)  │ │ (74 route)   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘ │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │
│  │ RAID        │ │ Integration │ │ Data        │ │ Reporting    │ │
│  │ Module      │ │ Factory     │ │ Factory     │ │ + Export     │ │
│  │ (30 route)  │ │ (26 route)  │ │ (31 route)  │ │ (5 route)    │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘ │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │
│  │ AI Engine   │ │ Governance  │ │ Audit       │ │ Notification │ │
│  │ 6 Asistan   │ │ + Metrics   │ │ + Trace     │ │ + Health     │ │
│  │ (34 route)  │ │ (4 route)   │ │ (3 route)   │ │ (2 route)    │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────────┘ │
│                                                                     │
│  18 Servis Dosyası (5,513 LOC) + 3 Middleware + Multi-Tenant       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────────┐
│                        DATA LAYER                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────────┐ │
│  │ SQLite/  │ │ pgvector │ │ Redis    │ │ AuditLog               │ │
│  │ Postgres │ │ (RAG)    │ │ (Cache/  │ │ + AIAuditLog           │ │
│  │ 85 tablo │ │          │ │ Rate-lim)│ │ (İzlenebilirlik)       │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ AI LAYER                                                     │   │
│  │ LLM Gateway (Anthropic/OpenAI/Gemini) + RAG Pipeline        │   │
│  │ Prompt Registry (6 YAML) + Suggestion Queue                 │   │
│  │ 6 Asistan: NL Query, Req Analyst, Defect Triage,           │   │
│  │            Risk Assessment, Test Gen, Change Impact          │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Domain Model (Veri Modeli) — 85 Tablo, 12 Model Dosyası

### 3.1 Model Dosyaları ve Tablo Dağılımı

| Model Dosyası | Tablo Sayısı | LOC | Ana Domain |
|---------------|:------------:|:---:|------------|
| `explore.py` | 25 | 1,956 | Fit-to-Standard: ProcessLevel, Workshop, ProcessStep, Decision, OpenItem, Requirement, Attachment, BPMN, Snapshot |
| `testing.py` | 17 | 1,470 | Test yönetimi: TestPlan, TestCycle, TestCase, TestSuite, TestStep, TestRun, Defect, UAT, SLA |
| `backlog.py` | 5 | 545 | WRICEF: Sprint, BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec |
| `integration.py` | 5 | 504 | Interface: Interface, Wave, ConnectivityTest, SwitchPlan, Checklist |
| `program.py` | 6 | 448 | Program: Program, Phase, Gate, Workstream, TeamMember, Committee |
| `raid.py` | 4 | 414 | RAID: Risk, Action, Issue, Decision |
| `ai.py` | 5 | 382 | AI: UsageLog, Embedding, KBVersion, Suggestion, AuditLog |
| `scope.py` | 3 | 337 | Scope: Process, RequirementProcessMapping, Analysis |
| `scenario.py` | 3 | 317 | Senaryo: Scenario, Workshop, WorkshopDocument |
| `data_factory.py` | 5 | 287 | Veri: DataObject, MigrationWave, CleansingTask, LoadCycle, Reconciliation |
| `requirement.py` | 3 | 294 | Gereksinim: Requirement, OpenItem, RequirementTrace |
| `audit.py` | 1 | 165 | Audit: AuditLog |
| `notification.py` | 1 | 72 | Bildirim: Notification |
| `cutover.py` | 6 | ~880 | **S13 Planlandı:** CutoverPlan, CutoverScopeItem, RunbookTask, TaskDependency, Rehearsal, GoNoGoItem |

### 3.2 Core Entity İlişki Diyagramı

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PROGRAM SETUP DOMAIN (6 model)                 │
│                                                                         │
│  Program ──1:N──▶ Phase (SAP Activate)                                 │
│     │                └──1:1──▶ Gate                                     │
│     ├──1:N──▶ Workstream                                               │
│     ├──1:N──▶ TeamMember (RACI)                                        │
│     └──1:N──▶ Committee                                                │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────────────┐
│                    EXPLORE PHASE DOMAIN (25 model)                      │
│                                                                         │
│  ProcessLevel (L1→L2→L3→L4, self-referential tree, 28 kolon)          │
│     │                                                                   │
│     └── L3 ──1:N──▶ WorkshopScopeItem ──N:1──▶ ExploreWorkshop        │
│              │         (26 kolon, lifecycle: draft→scheduled→           │
│              │          in_progress→completed)                          │
│              │                                                          │
│              └── L4 ──1:N──▶ ProcessStep (workshop-scoped L4 assess.)  │
│                                  │ fit_decision: fit|gap|partial_fit    │
│                                  │                                      │
│                                  ├──1:N──▶ ExploreDecision             │
│                                  ├──1:N──▶ ExploreOpenItem             │
│                                  └──1:N──▶ ExploreRequirement (39 col) │
│                                              │                          │
│                                              ├──N:M──▶ RequirementOILink│
│                                              ├──1:N──▶ ReqDependency   │
│                                              └──1:1──▶ BacklogItem     │
│                                                         (convert)       │
│                                                                         │
│  + PhaseGate, ProjectRole, WorkshopDependency, CrossModuleFlag,        │
│    WorkshopRevisionLog, Attachment, ScopeChangeRequest/Log,            │
│    BPMNDiagram, ExploreWorkshopDocument, DailySnapshot, L4SeedCatalog  │
│    CloudALMSyncLog, OpenItemComment                                    │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────────────┐
│                    DELIVERY DOMAIN                                       │
│                                                                         │
│  BacklogItem (WRICEF) ──1:1──▶ FunctionalSpec ──1:1──▶ TechnicalSpec  │
│     └──1:N──▶ TestCase                         │                        │
│                  └──1:N──▶ TestExecution        │                        │
│                  └──N:M──▶ Defect               │                        │
│                                                 │                        │
│  Interface ──1:N──▶ ConnectivityTest            │                        │
│     │       ──1:N──▶ SwitchPlan                 │                        │
│     └───────────N:M (InterfaceChecklist)        │                        │
│                                                 │                        │
│  DataObject ──1:N──▶ LoadCycle ──1:N──▶ Reconciliation                 │
│     └──1:N──▶ CleansingTask    MigrationWave                           │
│                                                                         │
│  RAID: Risk, Action, Issue, Decision (4 model, cross-cutting)          │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────────────┐
│                    CUTOVER & GO-LIVE DOMAIN (S13 — Planlandı, 6 model)  │
│                                                                         │
│  CutoverPlan ──1:N──▶ CutoverScopeItem ──1:N──▶ RunbookTask           │
│     │                  (data_load, interface,     │ (sequence, timing,  │
│     │                   authorization, ...)       │  RACI, rollback)    │
│     │                                             │                     │
│     │                                 RunbookTask ──N:M──▶ TaskDependency│
│     │                                 (F2S, S2S, F2F + lag, DFS cycle)  │
│     │                                                                   │
│     ├──1:N──▶ Rehearsal (timing variance, findings, revision flag)      │
│     └──1:N──▶ GoNoGoItem (7 domain: test, data, interface, security,   │
│                            training, rehearsal, steering)               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Fit-to-Standard (Explore) Veri Akışı

```
ProcessLevel L3 (scope_status: in_scope)
    │
    ▼
WorkshopScopeItem (N:M bridge)
    │
    ▼
ExploreWorkshop (draft → scheduled → in_progress → completed)
    │ start → finds L4 children of each L3 scope item
    ▼
ProcessStep (L4 assessment)
    │ fit_decision: fit | gap | partial_fit | NULL (pending)
    │
    ├──▶ ExploreDecision (DEC-001, DEC-002...)
    ├──▶ ExploreOpenItem (OI-001, lifecycle: open → in_progress → resolved → closed)
    └──▶ ExploreRequirement (REQ-001, lifecycle: draft → submitted → approved → in_backlog → realized → verified)
              │
              ├── convert to BacklogItem (WRICEF) or ConfigItem
              └── convert to RAID item (Risk/Action/Issue/Decision)
```

### 3.4 L3 Consolidated Fit Decision (GAP-11)

```
L4 Steps:   ● Fit    ◐ Partial    ● Gap    ○ Pending
              │           │          │          │
              ▼           ▼          ▼          ▼
System Suggestion: auto-calculated from L4 children
              │
              ▼
L3 consolidated_fit_decision: Accept (system) or Override (business)
    └── consolidated_decision_override: bool
    └── consolidated_decision_rationale: text
    └── consolidated_decided_by / consolidated_decided_at
```

---

## 4. Modül Mimarisi (Detay) — 12 Blueprint, 359 Route

### 4.1 Program Setup (`program_bp.py` — 25 route, 716 LOC)

| Alan | Detay |
|------|-------|
| **Modeller** | Program (14 col), Phase (13), Gate (11), Workstream (9), TeamMember (11), Committee (9) |
| **Özellikler** | Proje tipi (Greenfield/Brownfield/Selective/Cloud), SAP Activate fazları, RACI matrisi, workstream yönetimi |
| **Key Routes** | `POST /programs`, `GET /programs/:id`, `POST /programs/:id/phases`, `POST /programs/:id/workstreams` |

### 4.2 Explore Phase (`explore/` — 6 dosya, 97 route, 3,885 LOC)

| Dosya | Route | LOC | Kapsam |
|-------|:-----:|:---:|--------|
| `workshops.py` | 25 | 1,028 | Workshop CRUD, lifecycle (start/complete/reopen), delta sessions, attendees, agenda, decisions |
| `process_levels.py` | 21 | 923 | L1-L4 hierarchy CRUD, scope management, L3 signoff, L2 readiness, BPMN |
| `requirements.py` | 15 | 625 | Requirement CRUD, lifecycle transitions, convert to WRICEF/Config/RAID, ALM sync |
| `process_steps.py` | 9 | 358 | L4 assessment, fit decision, propagation, flags |
| `open_items.py` | 8 | 362 | Open item CRUD, lifecycle, reassign |
| `supporting.py` | 19 | 589 | Health, dependencies, attachments, documents, snapshots, scope changes |

**Servisler (8 dosya):**

| Servis | LOC | Görev |
|--------|:---:|-------|
| `fit_propagation.py` | 277 | L4 fit → L3 consolidated → L2/L1 cascade propagation |
| `requirement_lifecycle.py` | 386 | Status transition (draft→submitted→approved→in_backlog→realized→verified) |
| `open_item_lifecycle.py` | 298 | OI status transition + reassign + validation |
| `workshop_session.py` | 301 | Multi-session continuity, delta sessions, step carry-over |
| `workshop_docs.py` | 523 | Minutes, status report, action list document generation |
| `signoff.py` | 278 | L3 formal sign-off with precondition checks |
| `code_generator.py` | 118 | Auto-sequential code generation (WS-SD-01, DEC-001, OI-001, REQ-001) |
| `cloud_alm.py` | 258 | SAP Cloud ALM push/pull requirement sync |

### 4.3 Backlog Workbench (`backlog_bp.py` — 28 route, 887 LOC)

| Alan | Detay |
|------|-------|
| **Modeller** | Sprint (12 col), BacklogItem/WRICEF (28), ConfigItem (21), FunctionalSpec (14), TechnicalSpec (15) |
| **Lifecycle** | identified → in_analysis → approved → in_development → dev_complete → in_testing → deployed → cancelled |
| **Features** | WRICEF tipi (W/R/I/C/E/F), effort estimation, backlog-to-sprint, FS/TS lifecycle, requirement convert target |

### 4.4 Test Hub (`testing_bp.py` — 74 route, 2,620 LOC)

| Alan | Detay |
|------|-------|
| **Modeller (17)** | TestPlan, TestCycle, TestCase (22 col), TestSuite, TestStep, TestCaseDependency, TestCycleSuite, TestRun (15), TestStepResult, TestExecution, Defect (29 col), DefectComment, DefectHistory, DefectLink, UATSignOff, PerfTestResult, TestDailySnapshot |
| **Test Katmanları** | Unit, SIT, UAT, Regression, Performance |
| **SLA Tracking** | Priority-based SLA hesaplama, dashboard snapshot, Go/No-Go gate |
| **Features** | Test plan/cycle/suite hierarchy, step-level results, defect lifecycle (open→investigating→fixing→fixed→verified→closed), UAT signoff |

### 4.5 RAID Module (`raid_bp.py` — 30 route, 817 LOC)

| Alan | Detay |
|------|-------|
| **Modeller (4)** | Risk (23 col), Action (17), Issue (19), Decision (18) |
| **Risk Scoring** | probability × impact matrisi |
| **Features** | RAG status, workstream filter, escalation, owner tracking |

### 4.6 Integration Factory (`integration_bp.py` — 26 route, 730 LOC)

| Alan | Detay |
|------|-------|
| **Modeller (5)** | Interface (28 col), Wave (13), ConnectivityTest (10), SwitchPlan (13), InterfaceChecklist (11) |
| **Features** | Interface inventory, wave planning, connectivity test tracking, go-live switch plan |

### 4.7 Data Factory (`data_factory_bp.py` — 31 route, 543 LOC)

| Alan | Detay |
|------|-------|
| **Modeller (5)** | DataObject (12 col), MigrationWave (12), CleansingTask (10), LoadCycle (12), Reconciliation (11) |
| **Features** | Object list, mapping, cycle management, quality tracking |

### 4.8 AI Engine (`ai_bp.py` — 34 route, 951 LOC)

| Bileşen | Dosya | LOC | Görev |
|---------|-------|:---:|-------|
| LLM Gateway | `app/ai/gateway.py` | 642 | Multi-provider router (Anthropic Claude, OpenAI, Google Gemini, LocalStub) |
| RAG Pipeline | `app/ai/rag.py` | 684 | Entity chunking + hybrid search (semantic + keyword + RRF) |
| Prompt Registry | `app/ai/prompt_registry.py` | 327 | YAML-based version-controlled prompt templates |
| Suggestion Queue | `app/ai/suggestion_queue.py` | 227 | AI suggestion lifecycle (pending → accept/reject) |

**6 Aktif Asistan:**

| Asistan | Dosya | LOC | Görev |
|---------|-------|:---:|-------|
| NL Query | `nl_query.py` | 594 | Doğal dil → SQL sorgulama |
| Requirement Analyst | `requirement_analyst.py` | 256 | Fit/Gap sınıflandırma |
| Defect Triage | `defect_triage.py` | 325 | Severity + duplicate detection |
| Risk Assessment | `risk_assessment.py` | 219 | Risk scoring |
| Test Case Generator | `test_case_generator.py` | 189 | Requirement → test case |
| Change Impact | `change_impact.py` | 274 | Cross-module etki analizi |

### 4.9 Governance + Metrics Engine

| Bileşen | Dosya | LOC | Görev |
|---------|-------|:---:|-------|
| Governance Rules | `governance_rules.py` | 389 | 3 gate, 17 threshold, 4 RACI template, merkezi kural yönetimi |
| Metrics Engine | `metrics.py` | 501 | gap_ratio, oi_aging, requirement_coverage, fit_distribution, testing metrics |
| Escalation | `escalation.py` | 275 | Threshold-triggered alerts + MD5 dedup |
| Error Handling | `utils/errors.py` | 95 | 11 error code, standart `api_error(E.*, msg)` formatı |

### 4.10 Audit + Traceability

| Bileşen | Dosya | LOC | Görev |
|---------|-------|:---:|-------|
| AuditLog Model | `models/audit.py` | 165 | `write_audit()` + paginated list/filter API |
| Audit Blueprint | `audit_bp.py` | 104 | `/api/v1/audit` + `/api/v1/trace/requirement/:id` |
| Traceability Service | `traceability.py` | 732 | FK chain traverse (Req→WRICEF→Test→Defect), yeni tablo YOK |

### 4.11 Destekleyici Servisler

| Servis | LOC | Görev |
|--------|:---:|-------|
| `reporting.py` | 204 | KPI aggregation, program health |
| `export_service.py` | 219 | Excel/XLSX export (openpyxl) |
| `notification.py` | 190 | In-app notification CRUD + broadcast |
| `snapshot.py` | 206 | Daily metrics snapshot for trend dashboards |
| `permission.py` | 116 | RBAC — area-scoped role permission checks |
| `minutes_generator.py` | 242 | Workshop meeting minutes (Markdown/HTML) |

### 4.12 Multi-Tenant Engine

| Bileşen | Dosya | Görev |
|---------|-------|-------|
| Tenant Engine | `app/tenant.py` | resolve, registry, URI builder |
| Tenant CLI | `scripts/manage_tenants.py` | list, create, remove, init, seed, status |
| Tenant Registry | `tenants.json` | Tenant metadata |
| Migration | `scripts/migrate_tenants.py` | Alembic migration + schema verification (85 tablo) |
| Docker Compose | `docker/docker-compose.tenant.yml` | Multi-tenant production compose |

---

## 5. API Tasarımı — 359 Route, 12 Blueprint

### 5.1 Route Dağılımı

| Blueprint | Prefix | Route | LOC |
|-----------|--------|:-----:|:---:|
| `explore_bp` | `/api/v1/explore/` | 97 | 3,885 |
| `testing_bp` | `/api/v1/testing/` | 74 | 2,620 |
| `ai_bp` | `/api/v1/ai/` | 34 | 951 |
| `data_factory_bp` | `/api/v1/data-factory/` | 31 | 543 |
| `raid_bp` | `/api/v1/raid/` | 30 | 817 |
| `backlog_bp` | `/api/v1/backlog/` | 28 | 887 |
| `integration_bp` | `/api/v1/integration/` | 26 | 730 |
| `program_bp` | `/api/v1/programs/` | 25 | 716 |
| `reporting_bp` | `/api/v1/reports/` | 5 | 82 |
| `metrics_bp` | `/api/v1/metrics/` | 4 | 188 |
| `audit_bp` | `/api/v1/audit/` | 3 | 104 |
| `health_bp` | `/api/v1/health/` | 2 | 86 |

### 5.2 Standart Response Formatları

```python
# Başarılı
{"id": "uuid", "field": "value", ...}

# Hata
{"error": "Human-readable message", "code": "E_GOVERNANCE_BLOCK"}  # 11 error code

# Liste
[{"id": "uuid", ...}, ...]

# Health check
{"status": "ok", "governance_warnings": [...], "metrics": {...}}
```

### 5.3 Key API Endpoints (Explore Phase)

```
/api/v1/explore/projects/:pid/
├── /workshops
│   ├── GET    /                      # List workshops
│   ├── POST   /                      # Create workshop (multi-L3 scope)
│   ├── GET    /:id/full              # Full detail (steps + decisions + OI + req)
│   ├── POST   /:id/start             # Start → create ProcessSteps from L4s
│   ├── POST   /:id/complete          # Complete + governance gate check
│   ├── POST   /:id/reopen            # Reopen (reason required)
│   ├── POST   /:id/delta             # Create delta session
│   └── DELETE /:id                   # Delete workshop
│
├── /process-levels
│   ├── GET    /                      # Hierarchy tree
│   ├── POST   /:id/signoff           # L3 formal sign-off
│   ├── GET    /:id/readiness         # L2 readiness check
│   └── GET    /:id/consolidated-fit  # L3 consolidated decision
│
├── /process-steps
│   ├── PUT    /:id                   # Update fit decision
│   └── POST   /:id/propagate         # Trigger L4→L3→L2→L1 propagation
│
├── /requirements
│   ├── POST   /                      # Create requirement
│   ├── POST   /:id/transition        # Status transition
│   ├── POST   /:id/convert           # Convert to WRICEF/Config/RAID
│   └── GET    /:id/trace             # Traceability chain
│
└── /open-items
    ├── POST   /                      # Create open item
    └── POST   /:id/transition        # Status transition
```

---

## 6. UI/UX Mimarisi — Vanilla JS SPA

### 6.1 Frontend Teknoloji

| Bileşen | Teknoloji |
|---------|-----------|
| Framework | Vanilla JavaScript (ES Modules, IIFE pattern) |
| Styling | CSS Custom Properties (Fiori Horizon theme) |
| Charting | Chart.js (executive cockpit) |
| State | Module-scoped variables + localStorage |
| Routing | Hash-based SPA router (`app.js`) |
| API Client | `api.js` (generic) + `explore-api.js` (78 method, 17 resource group) |

### 6.2 Frontend Modül Haritası (28 dosya, 15,810 LOC)

```
static/js/
├── app.js                    (403 LOC)  — SPA shell, router, modal, toast
├── api.js                    (40 LOC)   — Generic REST client
├── explore-api.js            (225 LOC)  — Explore API client (78 method)
│
├── components/
│   ├── explore-shared.js     (622 LOC)  — ExpUI: badges, chips, cards, forms
│   ├── trace-view.js         (220 LOC)  — Traceability chain visualization
│   ├── demo-flow.js          (165 LOC)  — Demo flow controller + breadcrumb
│   ├── suggestion-badge.js   (163 LOC)  — AI suggestion display
│   ├── notification.js       (161 LOC)  — Notification panel
│   └── role-nav.js           (159 LOC)  — Role-based navigation + user switcher
│
└── views/
    ├── backlog.js            (1,352 LOC) — WRICEF backlog management
    ├── explore_workshop_detail.js (1,176 LOC) — Workshop detail (L3/L4 grouped steps)
    ├── project_setup.js      (1,142 LOC) — Program configuration
    ├── test_planning.js      (1,051 LOC) — Test plan/cycle/suite management
    ├── data_factory.js       (1,042 LOC) — Data migration management
    ├── test_execution.js     (1,007 LOC) — Test execution + defect tracking
    ├── program.js            (816 LOC)  — Program dashboard
    ├── explore_requirements.js (768 LOC) — Requirement management
    ├── explore_hierarchy.js  (764 LOC)  — L1→L4 process tree
    ├── integration.js        (764 LOC)  — Interface management
    ├── raid.js               (727 LOC)  — RAID dashboard
    ├── explore_workshops.js  (650 LOC)  — Workshop hub (table/kanban/capacity)
    ├── defect_management.js  (574 LOC)  — Defect lifecycle management
    ├── explore_dashboard.js  (550 LOC)  — Explore KPI dashboard
    ├── ai_admin.js           (390 LOC)  — AI admin panel
    ├── executive_cockpit.js  (377 LOC)  — Executive KPI cockpit (Chart.js)
    ├── ai_query.js           (293 LOC)  — NL Query interface
    ├── reports.js            (176 LOC)  — Reporting views
    └── testing_shared.js     (33 LOC)   — Testing shared utilities
```

### 6.3 CSS Design System (4,419 LOC)

| Dosya | LOC | İçerik |
|-------|:---:|--------|
| `main.css` | 3,088 | SAP Fiori Horizon tema, layout, form, table, modal, sidebar |
| `explore-tokens.css` | 1,331 | Explore tokens (fit/gap/partial renkleri, level badges, KPI cards, inline forms, multi-select dropdown, kanban, capacity) |

**Öne Çıkan UI Bileşenleri:**
- **Custom Multi-Select Dropdown:** `.exp-multiselect` — L3 process seçimi için search, chips, checkboxes ile özel dropdown
- **Kanban Board:** Workshop lifecycle kanban view
- **Capacity Bar:** Workshop capacity visualization
- **Inline Edit Forms:** Workshop detail inline forms

### 6.4 Rol Bazlı Kullanıcılar (Demo)

| Rol | Yetki | Demo Kullanıcı |
|-----|-------|----------------|
| `admin` | Tüm modüller | Umut (Admin) |
| `pmo_lead` | Program, Reporting, Governance | Mehmet (PMO Lead) |
| `module_lead` | Explore, Backlog, Test | Ayse (Module Lead) |
| `consultant` | Workshop, Requirements | Emre (Consultant) |
| `developer` | Backlog, Test | Fatma (Developer) |
| `tester` | Test Hub, Defect | Ali (Tester) |
| `viewer` | Read-only | Zeynep (Viewer) |

---

## 7. Teknoloji Stack

### 7.1 Backend

| Bileşen | Teknoloji | Versiyon |
|---------|-----------|---------|
| Runtime | Python | 3.11+ |
| Framework | Flask | 3.x |
| ORM | SQLAlchemy + Flask-SQLAlchemy | 2.0 |
| Migration | Alembic + Flask-Migrate | 15 migration |
| DB (Dev) | SQLite | — |
| DB (Prod) | PostgreSQL + pgvector | 15+ |
| Cache/Queue | Redis | 7.x |
| WSGI | Gunicorn | — |
| Container | Docker + docker-compose | — |

### 7.2 AI Stack

| Bileşen | Teknoloji |
|---------|-----------|
| LLM Provider 1 | Anthropic Claude (Haiku/Sonnet/Opus) |
| LLM Provider 2 | OpenAI (GPT-4o, Embeddings) |
| LLM Provider 3 | Google Gemini (Pro) |
| Vector Store | pgvector (PostgreSQL extension) |
| Embeddings | OpenAI text-embedding-3-large (3072-dim) |
| Prompt Templates | 6 YAML dosyası (ai_knowledge/prompts/) |
| RAG | Hybrid search: semantic + keyword + RRF |

### 7.3 Frontend

| Bileşen | Teknoloji |
|---------|-----------|
| JS | Vanilla JavaScript (ES Modules) |
| CSS | CSS Custom Properties (SAP Fiori Horizon) |
| Charting | Chart.js |
| E2E Test | Playwright (6 spec dosyası) |

### 7.4 DevOps & Tooling

| Bileşen | Teknoloji |
|---------|-----------|
| Build | Makefile (22 target) |
| Test | pytest (985 test) |
| Linting | ruff |
| Docker | 4 compose dosyası + Dockerfile |
| VCS | Git + GitHub |
| Dev Tools | VS Code + GitHub Copilot + Claude |

---

## 8. Entegrasyon Mimarisi

### 8.1 Mevcut Entegrasyonlar

| Sistem | Yön | Durum |
|--------|-----|-------|
| SAP Cloud ALM | Bi-directional requirement sync | ✅ Servis mevcut |
| SAP Signavio | BPMN import reference | ✅ Model mevcut |
| AI Providers (3) | Outbound API calls | ✅ Gateway aktif |

### 8.2 Planlanan Entegrasyonlar (R6)

| Sistem | Sprint | Yön |
|--------|--------|-----|
| Jira | S22a | Bi-directional backlog sync |
| SAP Cloud ALM (genişletme) | S22a | Full lifecycle sync |
| ServiceNow | S22b | Incident management sync |
| MS Teams | S22b | Notification + meeting integration |

---

## 9. Güvenlik ve Yetkilendirme Modeli

### 9.1 Mevcut (v2.0)

| Bileşen | Durum |
|---------|-------|
| RBAC (Role-Based Access Control) | ✅ `permission.py` — area-scoped role checks |
| Role-Based UI Navigation | ✅ `role-nav.js` — buton disable/hide |
| API Error Standardization | ✅ 11 error code, `api_error()` formatı |
| Audit Trail | ✅ `AuditLog` model — tüm kritik aksiyonlar loglanıyor |
| AI Audit | ✅ `AIAuditLog` — prompt, model, tokens, cost loglanıyor |
| Multi-Tenant DB Isolation | ✅ DB-per-tenant strategy |

### 9.2 Planlanan (S14)

| Bileşen | Sprint |
|---------|--------|
| JWT Authentication | S14 |
| Row-Level Security | S14 |
| GitHub Actions CI | S14 |
| Rate Limiting (Redis-backed) | S14 |

---

## 10. AI Katmanı: 14 Asistan — Mimari, Teknoloji ve Uygulama Detayları

### 10.1 Genel AI Mimari Blok Diyagramı

```
┌────────────────────────────────────────────────────────────────┐
│                    AI İSTEK AKIŞI                               │
│                                                                 │
│  Kullanıcı  ──▶  API Endpoint  ──▶  Asistan Pipeline           │
│                                       │                         │
│                                       ├─▶ RAG Retrieval         │
│                                       │   (pgvector hybrid)     │
│                                       │                         │
│                                       ├─▶ Prompt Registry       │
│                                       │   (YAML template)       │
│                                       │                         │
│                                       ├─▶ LLM Gateway           │
│                                       │   (Anthropic/OpenAI/    │
│                                       │    Gemini/LocalStub)    │
│                                       │                         │
│                                       ├─▶ Suggestion Queue      │
│                                       │   (pending → approve/   │
│                                       │    reject/modify)       │
│                                       │                         │
│                                       └─▶ AI Audit Log          │
│                                           (prompt, tokens, cost)│
│                                                                 │
│  4 Paylaşılan Bileşen:                                         │
│  ┌──────────────┐ ┌──────────────┐                              │
│  │ LLM Gateway  │ │ RAG Pipeline │                              │
│  │ (642 LOC)    │ │ (684 LOC)    │                              │
│  └──────────────┘ └──────────────┘                              │
│  ┌──────────────┐ ┌──────────────┐                              │
│  │ Prompt       │ │ Suggestion   │                              │
│  │ Registry     │ │ Queue        │                              │
│  │ (327 LOC)    │ │ (227 LOC)    │                              │
│  └──────────────┘ └──────────────┘                              │
└────────────────────────────────────────────────────────────────┘
```

### 10.2 Asistan Durumu (6/14 Aktif)

| # | Asistan | Faz | Durum | Dosya | LOC |
|---|---------|:---:|:-----:|-------|:---:|
| 1 | NL Query Assistant | 1 | ✅ Aktif | `nl_query.py` | 594 |
| 2 | Requirement Analyst Copilot | 1 | ✅ Aktif | `requirement_analyst.py` | 256 |
| 3 | Defect Triage Assistant | 1 | ✅ Aktif | `defect_triage.py` | 325 |
| 4 | Risk Assessment | 2 | ✅ Aktif | `risk_assessment.py` | 219 |
| 5 | Test Case Generator | 2 | ✅ Aktif | `test_case_generator.py` | 189 |
| 6 | Change Impact Analyzer | 2 | ✅ Aktif | `change_impact.py` | 274 |
| 7 | Steering Pack Generator | 2 | ⬜ Planlandı | — | S15 |
| 8 | Risk Sentinel | 2 | ⬜ Planlandı | — | S16 |
| 9 | Work Breakdown Engine | 2 | ⬜ Planlandı | — | S15 |
| 10 | WRICEF Spec Drafter | 2 | ⬜ Planlandı | — | S15 |
| 11 | Test Scenario Generator (genişletme) | 3 | ⬜ Planlandı | — | S19 |
| 12 | Data Quality Guardian | 3 | ⬜ Planlandı | — | S19 |
| 13 | Cutover Runbook Optimizer | 4 | ⬜ Planlandı | — | S19 |
| 14 | Meeting Intelligence Agent | 5 | ⬜ Planlandı | — | S21 |

### 10.3 Prompt Templates (6 YAML)

| Dosya | Asistan | Model |
|-------|---------|-------|
| `nl_query.yaml` | NL Query | Claude Haiku/Sonnet |
| `requirement_analyst.yaml` | Requirement Analyst | Claude Sonnet |
| `defect_triage.yaml` | Defect Triage | Claude Haiku |
| `risk_assessment.yaml` | Risk Assessment | Claude Sonnet |
| `test_case_generator.yaml` | Test Case Gen | Claude Sonnet |
| `change_impact.yaml` | Change Impact | Claude Sonnet |

---

## 11. Uygulama Fazları ve Sprint Roadmap

> **Kaynak:** SAP_Platform_Project_Plan_v2.2.md  
> **Toplam Effort:** ~812h, 7 Release, 28+ Sprint  
> **Çalışma Modeli:** Solo developer + AI araçları, haftada 15-20 saat

### 11.1 Release Durumu Özeti

| Release | Sprint | Effort | Durum |
|---------|--------|:------:|:-----:|
| **R1: Foundation** | S1-S4 | 109h | ✅ KAPANDI |
| **R2: Testing + AI** | S5-S8 | 112h | ✅ KAPANDI |
| **R3: Delivery + AI** | S9-S12 + TS + TD | 131h | ✅ KAPANDI |
| **R3.5: Workshop Rebuild + Governance** | WR-0 → WR-4 | 177h | ✅ KAPANDI |
| **R4: GoLive Readiness** | S13-S16 | 90h | ⬜ Planlandı |
| **R5: Operations** | S17-S20 | 76h | ⬜ Planlandı |
| **R6: Advanced** | S21-S24 | 117h | ⬜ Planlandı |

### 11.2 Tamamlanan Release'ler

#### Release 1: Foundation & Core (S1-S4) — ✅

| Sprint | Çıktı |
|--------|-------|
| S1: Mimari Refactoring | Flask App Factory, Program CRUD, Docker |
| S2: PostgreSQL + Program | 6 model, 24 endpoint |
| S3: Scope & Requirements | Senaryo, Gereksinim, İzlenebilirlik |
| S4: Backlog + Traceability | WRICEF lifecycle, Traceability v1 |

#### Release 2: Testing + AI (S5-S8) — ✅

| Sprint | Çıktı |
|--------|-------|
| S5: Test Hub | TestPlan/Cycle/Case/Execution/Defect (28 route) |
| S6: RAID + Notification | 4 model, 30 route, notification service |
| S7: AI Altyapı | LLM Gateway, RAG, Suggestion Queue, Prompt Registry |
| S8: AI Phase 1 | NL Query, Requirement Analyst, Defect Triage |

#### Release 3: Delivery + AI Core (S9-S12) — ✅

| Sprint | Çıktı |
|--------|-------|
| S9: Integration Factory | 5 model, 26 route, 76 test |
| S9.5: Tech Debt | P1-P10, monitoring, Gemini provider |
| Explore Phase | 25 model, 97 route, 871+ test, 8 servis, 10 frontend modül |
| TS-Sprint 1-3 | +17 model, +43 route, UAT/SLA/Go-NoGo |
| S10: Data Factory | 5 model, 31 route |
| S11: Reporting Engine | KPI aggregation, export |
| S12a: AI Phase 2a | Risk Assessment, Test Case Gen, Change Impact |

#### Release 3.5: Workshop Rebuild + Governance + Productization (WR-0 → WR-4) — ✅

> **Neden eklendi:** Explore Phase hızla inşa edilmişti ancak 7 critical bug, monolitik blueprint (3,671 satır), ve FE field mapping hataları tespit edildi.

| Sprint | Task | Effort | Çıktı |
|--------|:----:|:------:|-------|
| **WR-0: Hybrid Workshop Rebuild** | 12 | ~55h | 6 dosyaya split (3,885 LOC), 66 smoke test, 93 FE↔BE match, eski monolitik dosya silindi |
| **WR-1: Governance + Metrics** | 7 | ~32h | governance_rules.py, metrics.py, escalation.py, 11 error code, 53 yeni test |
| **WR-2: Audit + Traceability** | 6 | ~23h | AuditLog model, audit hooks, AI execution bridge, traceability service, 24 test |
| **WR-3: Demo Flow UI** | 7 | ~40h | role-nav.js, executive_cockpit.js, demo-flow.js, trace-view.js, testing metrics bridge, 20 test |
| **WR-4: Productization** | 7 | ~27h | Multi-tenant engine, seed_quick_demo.py, PILOT_ONBOARDING.md, DEMO_SCRIPT.md, INVESTOR_PITCH.md |

**WR-0 Dosya Yapısı (Backend Split):**
```
app/blueprints/explore/           (3,885 LOC toplam)
├── __init__.py              # Blueprint registration
├── workshops.py             # 25 endpoint — CRUD + lifecycle + attendees + agenda
├── process_levels.py        # 21 endpoint — Hierarchy, signoff, readiness, BPMN
├── process_steps.py         # 9 endpoint  — Fit decisions + propagation
├── requirements.py          # 15 endpoint — CRUD + transitions + convert + ALM
├── open_items.py            # 8 endpoint  — CRUD + transitions + reassign
└── supporting.py            # 19 endpoint — Health, deps, attachments, docs, snapshots
```

### 11.3 Planlanan Release'ler

#### Release 4: GoLive Readiness (S13-S16) — 90h

| Sprint | Açıklama | Est. | Bağımlılık |
|--------|----------|:----:|------------|
| **S13: Cutover Hub** | **6 model, ~30 route, ~60 test (detay aşağıda)** | **20h** | WR-4 |
| S14: Security + CI | JWT/RBAC, row-level security, GitHub Actions | 25h | S13 |

##### S13: Cutover Hub — Sprint Detayı

**Domain Modeli (6 tablo, ~880 LOC):**

| Model | Tablo | Kolon | Lifecycle |
|-------|-------|:-----:|-----------|
| `CutoverPlan` | `cutover_plans` | 16 | draft→approved→rehearsal→ready→executing→completed→rolled_back |
| `CutoverScopeItem` | `cutover_scope_items` | 8 | Computed from children (data_load, interface, authorization, job_scheduling, reconciliation, custom) |
| `RunbookTask` | `runbook_tasks` | 22 | not_started→in_progress→completed→failed→skipped→rolled_back |
| `TaskDependency` | `task_dependencies` | 5 | F2S, S2S, F2F + lag_minutes. DFS cycle detection |
| `Rehearsal` | `rehearsals` | 18 | planned→in_progress→completed→cancelled |
| `GoNoGoItem` | `go_no_go_items` | 10 | pending→go/no_go/waived (7 standart item seed) |

**Mimari:**
```
Program ──1:N──▶ CutoverPlan ──1:N──▶ CutoverScopeItem ──1:N──▶ RunbookTask
                     │                                          ──N:M──▶ TaskDependency
                     ├──1:N──▶ Rehearsal (timing variance, findings)
                     └──1:N──▶ GoNoGoItem (7 domain checklist)
```

**Planlanan Dosya Yapısı:**
```
app/models/cutover.py          — 6 model + lifecycle guards + DFS cycle check + seed helper (~880 LOC)
app/blueprints/cutover_bp.py   — CRUD + lifecycle + deps + rehearsal + Go/No-Go (~25-30 route, ~900 LOC)
app/services/cutover_service.py — Code gen, metrics, aggregation, validation (~400 LOC)
static/js/views/cutover.js     — Plan dashboard, runbook timeline, rehearsal, Go/No-Go pack (~800 LOC)
tests/test_api_cutover.py      — ~50-60 test
```

**Task Breakdown (20h):**

| # | Task | Est. |
|:-:|------|:----:|
| 1 | Model: `cutover.py` — 6 model + guards + cycle detection + seed | 3h |
| 2 | Blueprint: `cutover_bp.py` — ~30 route | 5h |
| 3 | Service: `cutover_service.py` — code gen, metrics, Go/No-Go aggregation | 3h |
| 4 | Frontend: `cutover.js` — plan dashboard, runbook, rehearsal, Go/No-Go | 4h |
| 5 | Tests: `test_api_cutover.py` — ~60 test | 3h |
| 6 | Migration + seed + registration + CSS | 2h |

**Cross-Domain:** RunbookTask → {BacklogItem, Interface, DataObject, ConfigItem, TestCase}. GoNoGoItem → {test_mgmt, data_factory, integration, security, training, rehearsal, steering}.
| S15: AI Phase 3 | Sprint Planner, Scope Advisor, Meeting Minutes | 20h | S14 |
| S16: AI Risk Sentinel | ML-based risk scoring | 25h | S15 |

#### Release 5: Operations (S17-S20) — 76h

| Sprint | Açıklama | Est. | Bağımlılık |
|--------|----------|:----:|------------|
| S17: Run/Sustain | Hypercare, incident management | 18h | S16 |
| S18: Notification + Celery | Async tasks, email, scheduled jobs | 16h | S14 |
| S19: AI Phase 4 | Advanced AI assistants | 22h | S18 |
| S20: AI Perf + Polish | Performance optimization | 20h | S19 |

#### Release 6: Advanced (S21-S24) — 117h

| Sprint | Açıklama | Est. | Bağımlılık |
|--------|----------|:----:|------------|
| S21: AI Phase 5 | Meeting Intelligence, NL Workflow Builder | 41h | S20 |
| S22a: Ext Integrations P1 | Jira + Cloud ALM genişletme | 36h | S14 |
| S22b: Ext Integrations P2 | ServiceNow + Teams | 20h | S22a |
| S23: Mobile PWA | Progressive web app | 18h | S22b |
| S24: Final Polish | Platform v1.0 release | 20h | All |

### 11.4 Bağımlılık Zinciri (Critical Path)

```
TAMAMLANDI                    RELEASE 3.5 (TAMAMLANDI)             RELEASE 4+
─────────                     ──────────────────────               ──────────

R1-R3 ──→ WR-0 ──→ WR-1 ──→ WR-2 ──→ WR-3 ──→ WR-4 ──→ S13 (Cutover)
  ✅        ✅       ✅       ✅       ✅       ✅        │
                                                          ├──→ S14 (JWT) ──→ S18 ──→ S22a
                                                          │
                                                          └──→ S15 (AI P3) ──→ S16 ──→ S17 ──→ ...
```

### 11.5 Zaman Çizelgesi (Gantt)

```
2026
FEB           MAR           APR           MAY           JUN
 │             │             │             │             │
 ├── WR-0 ✅──┤             │             │             │
 │        ├── WR-1 ✅──┤    │             │             │
 │             │  ├── WR-2 ✅┤            │             │
 │             │       ├── WR-3 ✅──┤     │             │
 │             │             │ ├── WR-4 ✅┤             │
 │             │             │        ├── R3.5 GATE ✅──┤
 │             │             │             │ ├── S13 ───┤   Cutover Hub
 │             │             │             │        ├── S14  Security + CI

JUL           AUG           SEP           OCT           NOV           DEC
 │             │             │             │             │             │
 ├── S15 ─────┤             │             │             │             │   AI P3
 │        ├── S16 ────┤     │             │             │             │   AI Risk
 │             ├── R4 GATE ─┤             │             │             │
 │             │        ├── S17 ────┤     │             │             │   Run/Sustain
 │             │             │ ├── S18 ───┤             │             │   Celery
 │             │             │        ├── S19 ────┤     │             │   AI P4
 │             │             │             │  ├── S20 ──┤             │   AI Polish
 │             │             │             │  ├── R5 GATE┤            │
 │             │             │             │        ├── S21 ────┤     │   AI P5
 │             │             │             │             │ ├── S22a ──┤   Jira+ALM
 │             │             │             │             │        S22b│   SNow+Teams
 │             │             │             │             │         S23│   Mobile PWA
 │             │             │             │             │          S24   Final
 ▼             ▼             ▼             ▼             ▼         ⭐ R6 = v1.0
```

### 11.6 Effort Dağılımı

| Release | Platform | AI | TD/Gov | Toplam |
|---------|:--------:|:--:|:------:|:------:|
| R1: Foundation | 109h | 0 | — | 109h |
| R2: Testing+AI | 55h | 57h | — | 112h |
| R3: Delivery+AI | 51h | 30h | 50h | 131h |
| **R3.5: WS Rebuild+Gov** | **~140h** | **0** | **~37h** | **~177h** |
| R4: GoLive+AI | 37h | 45h | 8h | 90h |
| R5: Operations | 34h | 42h | — | 76h |
| R6: Advanced | 76h | 41h | — | 117h |
| **TOPLAM** | **502h** | **215h** | **95h** | **~812h** |

---

## 12. Özet: Playbook → Platform → AI Eşleme

| Playbook Bölümü | Platform Modülü | AI Asistanı | Release |
|-----------------|-----------------|-------------|:-------:|
| §1 Dönüşüm Yaklaşımı | Program Setup | — | R1 |
| §4 SAP Activate Fazları | Program Setup + PhaseGate | Risk Sentinel | R1+R4 |
| §5 Scope & Requirements | Explore Phase | Requirement Analyst + Work Breakdown | R3+R3.5 |
| §5 Data Migration | Data Factory | Data Quality Guardian | R3 |
| §5 Integration | Integration Factory | Impact Analyzer (interface etki) | R3 |
| §5 Custom/Extensions | Backlog Workbench | WRICEF Spec Drafter + Impact Analyzer | R2+R4 |
| §5 Security | Security Module (JWT) | — | R4 |
| §5 Testing & Quality | Test Hub (17 model) | Test Scenario Generator + Defect Triage | R2+R3 |
| §5 Change & Training | Change Module | Meeting Intelligence | R6 |
| §6 Test Yönetimi KPI | Test Hub Dashboard + Metrics | NL Query + Steering Pack | R2+R3.5 |
| §7 Cutover & Go-Live | Cutover Hub | Cutover Optimizer + War Room Assistant | R4 |
| §8 Risk & Kalite | RAID Module + Governance | Risk Sentinel | R2+R3.5 |
| §9 Platform Blueprint | Tüm mimari (85 model, 359 route) | 14 AI Asistan | R1-R6 |
| — Cross-cutting | Reporting + Executive Cockpit | Steering Pack Generator | R3+R3.5 |
| — Cross-cutting | Tüm modüller | NL Query Assistant | R2 |
| — Cross-cutting | Audit + Traceability | — | R3.5 |
| — Cross-cutting | Multi-Tenant | — | R3.5 |
| — Cross-cutting | Otomasyon | NL Workflow Builder | R6 |

---

## 13. AI Maliyet ve ROI Özet Projeksiyonu

| Kalem | Aylık Tahmini Maliyet | Aylık Tahmini Tasarruf |
|-------|----------------------|----------------------|
| Claude API (Haiku+Sonnet+Opus) | $100-400 | — |
| OpenAI Embeddings API | $15-50 | — |
| Whisper STT API | $5-20 | — |
| pgvector hosting (PostgreSQL dahilinde) | $0 | — |
| Redis (Cache + Rate limiter) | $20-50 | — |
| **Toplam AI altyapı maliyeti** | **$140-520/ay** | — |
| | | |
| Requirement sınıflandırma hızlanması | — | 40-60 saat/ay |
| FS taslak yazım hızlanması | — | 80-120 saat/ay |
| Test case oluşturma hızlanması | — | 60-100 saat/ay |
| Defect triage hızlanması | — | 40-80 saat/ay |
| Steering pack hazırlama | — | 16-32 saat/ay |
| Risk erken tespiti (gecikme önleme) | — | Hesaplanamaz |
| **Toplam tahmini tasarruf** | — | **236-392 saat/ay** |

> Orta ölçekli SAP projesi (50-100 kişi, 12-18 ay) baz alınmıştır.

---

## 14. Güncel Platform Metrikleri (v2.0 — Şubat 2026)

| Metrik | Değer |
|--------|-------|
| **DB Tabloları** | **85** |
| **API Route** | **359** |
| **Test Sayısı** | **985** (0 fail, 2 skipped, 1 xfail) |
| **Model Dosyaları** | 12 (+1 audit) |
| **Blueprint Dosyaları** | 12 (explore: 6 sub-module) |
| **Servis Dosyaları** | 18 (5,513 LOC) |
| **AI Asistan** | 6 aktif / 14 planlı |
| **AI Core Bileşen** | 4 (Gateway, RAG, Prompt Registry, Queue) |
| **Prompt Template** | 6 YAML |
| **Alembic Migration** | 15 |
| **Frontend JS Dosyaları** | 28 (15,810 LOC) |
| **CSS Dosyaları** | 2 (4,419 LOC) |
| **Python LOC (app/)** | ~31,291 |
| **Test LOC** | ~14,196 |
| **Makefile Target** | 22 |
| **Docker Dosyası** | 4 + 1 shell |
| **Script** | 14 |
| **E2E Spec (Playwright)** | 6 |
| **Doküman** | 14+ (plan, spec, guide, review, pitch) |
| **Tamamlanan Release** | 4/7 (R1, R2, R3, R3.5) |
| **Tamamlanan Sprint** | 20+ / 28+ |
| **Git Commit** | 60+ |

### 14.1 Modül Tamamlanma Durumu

| Modül | Durum | Model | Route | Test |
|-------|:-----:|:-----:|:-----:|:----:|
| Program Setup | ✅ | 6 | 25 | 36 |
| Explore Phase | ✅ | 25 | 97 | 192+ |
| Backlog Workbench | ✅ | 5 | 28 | 59 |
| Test Hub | ✅ | 17 | 74 | 203 |
| RAID Module | ✅ | 4 | 30 | 46 |
| Integration Factory | ✅ | 5 | 26 | 76 |
| Data Factory | ✅ | 5 | 31 | 44 |
| AI Engine | ✅ | 5 | 34 | 141+ |
| Reporting + Export | ✅ | — | 5 | 8 |
| Governance + Metrics | ✅ | — | 4 | 53 |
| Audit + Traceability | ✅ | 1 | 3 | 24 |
| Notification + Health | ✅ | 1 | 2 | — |
| Cutover Hub | ⏳ S13 | 6 | ~30 | ~60 |
| Security (JWT) | ⬜ | — | — | S14 |
| Run/Sustain | ⬜ | — | — | S17 |

### 14.2 İlerleme Grafikleri

```
DB Tabloları:    █████████████████████░░░  85/90        (%94)
API Route:       ███████████████████████░  359/500      (%72)
AI Asistanlar:   ██████████░░░░░░░░░░░░░  6/14         (%43)
Release:         ████████████████░░░░░░░░  4/7          (%57)
Testler:         ██████████████████████░░  985/1300     (%76)
```

---

## 15. Başarı Metrikleri (Hedefler)

| Metrik | R3 Gerçek | R3.5 Gerçek | R4 Hedef | R6 Hedef |
|--------|:---------:|:-----------:|:--------:|:--------:|
| API route | 336 | **359** | 400+ | 500+ |
| DB tablo | 77 | **85** | 90+ | 90+ (net) |
| Pytest | 916 | **985** | 1100+ | 1300+ |
| AI asistan | 6 | **6** | 11 | 14 |
| Test/route | 2.7 | **2.7** | 2.8 | 3.0+ |
| Governance | ❌ | **✅** | ✅ | ✅ |
| Audit trail | ❌ | **✅** | ✅ | ✅ |
| Traceability | v1 | **v2** (API endpoint) | v2 | v3 (UI) |
| Demo flow | 🔴 | **✅** 10 dk | ✅ | ✅ |
| Pilot ready | ❌ | **✅** | ✅ | ✅ |
| JWT Auth | ❌ | ❌ | **✅** | ✅ |
| Cutover Hub | ❌ | ❌ | **✅** | ✅ |
| Mobile PWA | ❌ | ❌ | ❌ | **✅** |

---

*Bu mimari doküman, SAP Transformation PM Playbook'undaki tüm domain'leri, deliverable'ları ve KPI'ları kapsayan bir uygulama temelini oluşturur. Her modül bağımsız geliştirilebilir ancak traceability zinciri ile birbirine bağlıdır. AI katmanı 14 asistan ile platformun her modülüne zeka ekler; tüm asistanlar human-in-the-loop pattern'iyle çalışır ve aynı 4 temel bileşeni (LLM Gateway, RAG Engine, Prompt Registry, Suggestion Queue) paylaşır.*

---

**Dosya:** `sap_transformation_platform_architecture (2).md`  
**v1.3 → v2.0 delta:** Tüm bölümler güncel verilere göre sıfırdan güncellendi. Sprint roadmap (R4-R6) entegre edildi. 85 model, 359 route, 985 test, 6 AI asistan, 18 servis, 28 frontend modül, multi-tenant, governance, audit trail yansıtıldı.  
**Tarih:** 2026-02-12
