# SAP Transformation Platform — Project Inventory

**Oluşturulma Tarihi:** 2026-02-11  
**Son Commit:** `h7c8d9e` (TS-Sprint 3 tamamlandı)  
**Branch:** main  
**Toplam Dosya:** ~140 (kaynak + doküman + config)  
**Toplam LOC:** ~76,100

---

## 1. Özet Metrikler

| Metrik | Değer |
|--------|-------|
| Python Backend LOC | ~36,000 (app: 21,700 · scripts: 4,600 · tests: 9,800) |
| JavaScript Frontend LOC | 11,413 |
| CSS LOC | 3,234 (main.css 2,285 + explore-tokens.css 949) |
| Markdown Doküman LOC | ~17,500 |
| API Routes | 336 (12 blueprint) |
| DB Modeli (class) | 77 (14 domain modül) |
| DB Tablosu (runtime) | 77 |
| Alembic Migration | 11 |
| Pytest Test | 916 (16 test dosyası) |
| AI Asistan | 6 aktif (NL Query, Requirement Analyst, Defect Triage, Risk Assess, TestGen, ChangeImpact) |
| Servis Katmanı | 12 servis, 3,052 LOC |
| Seed Data | 6 modül, ~820 LOC |

---

## 2. Doküman Envanteri

### 2.1 Spesifikasyonlar (FS/TS)

| # | Dosya | Tip | Versiyon | Tarih | LOC | Dil | Açıklama |
|---|-------|-----|----------|-------|-----|-----|----------|
| D1 | [explore-phase-fs-ts.md](explore-phase-fs-ts.md) | FS/TS | v1.0 | — | 2,787 | EN | Explore Phase Management — 4 modül (A-D), 25 tablo, 50+ endpoint tanımı |
| D2 | [test-management-fs-ts.md](test-management-fs-ts.md) | FS/TS | v1.0 | — | 1,558 | EN | Test Management — 6 test seviyesi, 17 tablo / 45 endpoint hedef, Cloud ALM sync |

### 2.2 Mimari Dokümanlar

| # | Dosya | Tip | Versiyon | Tarih | LOC | Dil | Açıklama |
|---|-------|-----|----------|-------|-----|-----|----------|
| D3 | [sap_transformation_platform_architecture_v2.md](sap_transformation_platform_architecture_v2.md) | Architecture | v2.1 | 2026-02-10 | 2,435 | TR | **AKTİF** — Ana mimari doküman. Explore + Test entegre, 7 tasarım ilkesi |
| D4 | [sap_transformation_platform_architecture (2).md](sap_transformation_platform_architecture%20(2).md) | Architecture | v1.3 | 2025-06 | 2,254 | TR | **ESKİ** — v2.1 ile süpersede edildi. 65 tablo, 295 route dönemi |

### 2.3 Proje Yönetimi

| # | Dosya | Tip | Versiyon | Tarih | LOC | Dil | Açıklama |
|---|-------|-----|----------|-------|-----|-----|----------|
| D5 | [SAP_Platform_Project_Plan.md](SAP_Platform_Project_Plan.md) | Project Plan | — | — | 1,191 | TR/EN | Sprint 1-16 + TS-Sprint 1-6 detaylı plan, Release gate'leri |
| D6 | [PROGRESS_REPORT.md](PROGRESS_REPORT.md) | Progress Report | — | 2026-02-11 | 562 | TR | 336 route, 77 tablo, 916 test — commit geçmişi + sprint durumu |
| D7 | [GATE_CHECK_REPORT.md](GATE_CHECK_REPORT.md) | Gate Check | — | 2025-06 | 311 | TR | Release 1-2 gate kriterleri, 5/8 sprint sonuçları |
| D8 | [CHANGELOG.md](CHANGELOG.md) | Changelog | — | — | 238 | TR | Conventional Commits formatında değişiklik kaydı |
| D9 | [EXPLORE_PHASE_TASK_LIST.md](EXPLORE_PHASE_TASK_LIST.md) | Task List | — | 2026-02-10 | 1,216 | TR | Explore Phase 175/179 task, %98 tamamlanma |

### 2.4 Analiz & Karar Dokümanları

| # | Dosya | Tip | Versiyon | Tarih | LOC | Dil | Açıklama |
|---|-------|-----|----------|-------|-----|-----|----------|
| D10 | [PLAN_REVISION.md](PLAN_REVISION.md) | Analysis | — | 2025-02-09 | 219 | TR | Buffer analizi, S12/S15 bölünme planı, %35 planlanmamış iş tespiti |
| D11 | [AI_PRIORITY.md](AI_PRIORITY.md) | Analysis | — | 2025-02-09 | 187 | TR | 14 AI asistan önceliklendirme matrisi, P1→P5 sıralama |
| D12 | [FRONTEND_DECISION.md](FRONTEND_DECISION.md) | Decision | ❌ Cancelled | 2026-02-11 | 281 | EN | Vue migration cancelled — vanilla JS SPA retained |
| D13 | [SIGNAVIO_DRAFT.md](SIGNAVIO_DRAFT.md) | Design Draft | v0.1 🟡 PARKED | 2026-02-09 | 285 | EN | SAP Signavio BPMN 2.0 integration tasarımı — onay bekliyor |
| D14 | [INTEGRATION_ESTIMATES.md](INTEGRATION_ESTIMATES.md) | Estimate | — | 2025-02-09 | 161 | TR | Dış entegrasyon maliyet analizi: 18 saat plan → 56 saat revize (3.1×) |
| D15 | [DB_CONSISTENCY.md](DB_CONSISTENCY.md) | Analysis | — | 2025-02-09 | 59 | EN | SQLite/PostgreSQL tutarlılık analizi, 8 bulgu (5 çözüldü) |
| D16 | [KB_VERSIONING.md](KB_VERSIONING.md) | Design | — | 2025-02-09 | 139 | EN | Knowledge Base versiyonlama tasarımı, content hash + stale detection |

### 2.5 Kullanıcı Kılavuzları

| # | Dosya | Tip | Versiyon | Tarih | LOC | Dil | Açıklama |
|---|-------|-----|----------|-------|-----|-----|----------|
| D17 | [User Guide/explore-phase-user-guide.md](User%20Guide/explore-phase-user-guide.md) | User Guide | v1.0 | — | 1,047 | TR | Explore Phase — 5 ekran, 13 bölüm, rol bazlı rehber |
| D18 | [User Guide/explore-phase-user-guide-en.md](User%20Guide/explore-phase-user-guide-en.md) | User Guide | v1.0 | — | 1,047 | EN | D17'nin İngilizce çevirisi |
| D19 | [User Guide/test-management-user-guide.md](User%20Guide/test-management-user-guide.md) | User Guide | v1.0 | 2026-02-10 | 950 | TR | Test Management — 6 modül (T1-T6), rol bazlı rehber |
| D20 | [User Guide/test-management-user-guide-en.md](User%20Guide/test-management-user-guide-en.md) | User Guide | v1.0 | 2026-02-10 | 950 | EN | D19'un İngilizce çevirisi |

### 2.6 Diğer

| # | Dosya | Tip | LOC | Açıklama |
|---|-------|-----|-----|----------|
| D21 | [README.md](README.md) | README | 142 | Proje tanıtımı, kurulum, Makefile hedefleri |

---

## 3. Kaynak Kod Envanteri

### 3.1 Model Katmanı (app/models/)

| # | Dosya | LOC | Class | Tablo | Domain |
|---|-------|----:|------:|------:|--------|
| M1 | [app/models/program.py](app/models/program.py) | 448 | 6 | 6 | Program, Phase, Gate, Workstream, TeamMember, Committee |
| M2 | [app/models/scenario.py](app/models/scenario.py) | 317 | 3 | 3 | Scenario, Workshop, WorkshopDocument |
| M3 | [app/models/scope.py](app/models/scope.py) | 337 | 3 | 3 | Process, RequirementProcessMapping, Analysis |
| M4 | [app/models/requirement.py](app/models/requirement.py) | 294 | 3 | 3 | Requirement, RequirementTrace, OpenItem |
| M5 | [app/models/backlog.py](app/models/backlog.py) | 531 | 5 | 5 | BacklogItem, ConfigItem, Sprint, FunctionalSpec, TechnicalSpec |
| M6 | [app/models/testing.py](app/models/testing.py) | 1,151 | 17 | 17 | TestPlan, TestCycle, TestCase, TestExecution, Defect, TestSuite, TestStep, TestCaseDependency, TestCycleSuite, TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink, UATSignOff, PerfTestResult, TestDailySnapshot |
| M7 | [app/models/raid.py](app/models/raid.py) | 382 | 4 | 4 | Risk, Action, Issue, Decision |
| M8 | [app/models/integration.py](app/models/integration.py) | 504 | 5 | 5 | Interface, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist |
| M9 | [app/models/explore.py](app/models/explore.py) | 1,889 | 25 | 25 | Explore Phase — ProcessLevel, FitGapItem, ExploreWorkshop, RequirementItem, OpenItem, Decision, vb. |
| M10 | [app/models/ai.py](app/models/ai.py) | 381 | 5 | 5 | AISuggestion, AIAuditLog, AIEmbedding, KBVersion, AIConversation |
| M11 | [app/models/notification.py](app/models/notification.py) | 72 | 1 | 1 | Notification |
| | **Toplam** | **6,306** | **77** | **77** | |

### 3.2 Blueprint Katmanı (app/blueprints/)

| # | Dosya | LOC | Route | Domain |
|---|-------|----:|------:|--------|
| B1 | [app/blueprints/program_bp.py](app/blueprints/program_bp.py) | 716 | 25 | Program CRUD, Phase, Gate, Workstream, Team, Committee |
| B2 | [app/blueprints/scenario_bp.py](app/blueprints/scenario_bp.py) | 593 | 17 | Scenario, Workshop CRUD |
| B3 | [app/blueprints/scope_bp.py](app/blueprints/scope_bp.py) | 779 | 20 | Process hierarchy, Analysis, Requirement convert |
| B4 | [app/blueprints/requirement_bp.py](app/blueprints/requirement_bp.py) | 696 | 18 | Requirement CRUD, Traceability, OpenItem |
| B5 | [app/blueprints/backlog_bp.py](app/blueprints/backlog_bp.py) | 837 | 28 | BacklogItem, ConfigItem, Sprint, FS/TS CRUD |
| B6 | [app/blueprints/testing_bp.py](app/blueprints/testing_bp.py) | 1,667 | 71 | Test Plans/Cycles/Cases/Runs/Executions, Defects, Suites, Steps, Comments, History, Links |
| B7 | [app/blueprints/raid_bp.py](app/blueprints/raid_bp.py) | 805 | 30 | Risk, Action, Issue, Decision CRUD + scoring |
| B8 | [app/blueprints/integration_bp.py](app/blueprints/integration_bp.py) | 730 | 26 | Interface, Wave, Connectivity, SwitchPlan |
| B9 | [app/blueprints/explore_bp.py](app/blueprints/explore_bp.py) | 2,524 | 66 | Explore Phase tüm API'ler (ProcessLevel, Workshop, Requirement, OI, Scope Change, Dashboard, vb.) |
| B10 | [app/blueprints/ai_bp.py](app/blueprints/ai_bp.py) | 821 | 29 | AI Gateway, Suggestion Queue, NL Query, Defect Triage, KB Admin |
| B11 | [app/blueprints/health_bp.py](app/blueprints/health_bp.py) | 86 | 2 | Health check (ready/live) |
| B12 | [app/blueprints/metrics_bp.py](app/blueprints/metrics_bp.py) | 188 | 4 | Request metrics, errors, slow queries, AI usage |
| | **Toplam** | **10,442** | **336** | |

> **Not:** 336 registred route (1 static route dahil).

### 3.3 Servis Katmanı (app/services/)

| # | Dosya | LOC | Sorumluluk |
|---|-------|----:|-----------|
| S1 | [app/services/traceability.py](app/services/traceability.py) | 574 | Entity chain traversal, matrix, upstream/downstream |
| S2 | [app/services/workshop_session.py](app/services/workshop_session.py) | 301 | Workshop kilitleme, PDF export, session yönetimi |
| S3 | [app/services/open_item_lifecycle.py](app/services/open_item_lifecycle.py) | 279 | Open item durum makinesi |
| S4 | [app/services/signoff.py](app/services/signoff.py) | 278 | Workshop/scope sign-off akışı |
| S5 | [app/services/fit_propagation.py](app/services/fit_propagation.py) | 277 | Fit kararı yukarı/aşağı propagasyon |
| S6 | [app/services/cloud_alm.py](app/services/cloud_alm.py) | 258 | SAP Cloud ALM sync (stub) |
| S7 | [app/services/requirement_lifecycle.py](app/services/requirement_lifecycle.py) | 243 | Requirement durum makinesi |
| S8 | [app/services/minutes_generator.py](app/services/minutes_generator.py) | 239 | Workshop toplantı tutanağı |
| S9 | [app/services/snapshot.py](app/services/snapshot.py) | 206 | Günlük snapshot (test/defect istatistik) |
| S10 | [app/services/notification.py](app/services/notification.py) | 190 | In-app notification servisi |
| S11 | [app/services/permission.py](app/services/permission.py) | 116 | Rol bazlı yetki kontrolü |
| S12 | [app/services/code_generator.py](app/services/code_generator.py) | 91 | Auto-code üreteci (REQ-001, DEF-001 vb.) |
| | **Toplam** | **3,052** | |

### 3.4 AI Katmanı (app/ai/)

| # | Dosya | LOC | Sorumluluk |
|---|-------|----:|-----------|
| A1 | [app/ai/rag.py](app/ai/rag.py) | 684 | Hybrid RAG pipeline (semantic + keyword search) |
| A2 | [app/ai/gateway.py](app/ai/gateway.py) | 622 | LLM Gateway (4 provider + stub), token tracking |
| A3 | [app/ai/assistants/nl_query.py](app/ai/assistants/nl_query.py) | 594 | Doğal dil → SQL asistanı |
| A4 | [app/ai/prompt_registry.py](app/ai/prompt_registry.py) | 327 | YAML template + versioning |
| A5 | [app/ai/assistants/defect_triage.py](app/ai/assistants/defect_triage.py) | 325 | Defect severity + duplicate detection |
| A6 | [app/ai/assistants/requirement_analyst.py](app/ai/assistants/requirement_analyst.py) | 256 | Fit/PFit/Gap classification |
| A7 | [app/ai/assistants/risk_assessment.py](app/ai/assistants/risk_assessment.py) | 219 | Risk assessment scoring |
| A8 | [app/ai/assistants/test_case_generator.py](app/ai/assistants/test_case_generator.py) | 189 | Test case generation assistant |
| A9 | [app/ai/assistants/change_impact.py](app/ai/assistants/change_impact.py) | 274 | Change impact analysis assistant |
| A10 | [app/ai/suggestion_queue.py](app/ai/suggestion_queue.py) | 227 | HITL suggestion lifecycle |
| | **Toplam** | **3,747** | |

### 3.5 Test Dosyaları (tests/)

| # | Dosya | LOC | Test # | Kapsam |
|---|-------|----:|-------:|--------|
| T1 | [tests/test_explore.py](tests/test_explore.py) | 2,090 | 192 | Explore Phase tüm API'ler |
| T2 | [tests/test_api_testing.py](tests/test_api_testing.py) | 1,438 | 203 | TestPlan/Cycle/Case/Execution/Defect/Suite/Step/Run/StepResult/Comment/History/Link |
| T3 | [tests/test_api_integration.py](tests/test_api_integration.py) | 927 | 76 | Interface/Wave/Connectivity/SwitchPlan/Checklist |
| T4 | [tests/test_ai.py](tests/test_ai.py) | 775 | 69 | AI Gateway, RAG, Suggestion Queue |
| T5 | [tests/test_ai_assistants.py](tests/test_ai_assistants.py) | 688 | 72 | NL Query, Requirement Analyst, Defect Triage |
| T6 | [tests/test_api_backlog.py](tests/test_api_backlog.py) | 784 | 59 | Backlog/Config/Sprint/FS/TS |
| T7 | [tests/test_api_scope.py](tests/test_api_scope.py) | 631 | 45 | Process/Analysis/Scope |
| T8 | [tests/test_api_requirement.py](tests/test_api_requirement.py) | 584 | 36 | Requirement/Trace/OpenItem |
| T9 | [tests/test_api_raid.py](tests/test_api_raid.py) | 492 | 46 | Risk/Action/Issue/Decision |
| T10 | [tests/test_api_program.py](tests/test_api_program.py) | 489 | 36 | Program/Phase/Gate/Workstream/Team |
| T11 | [tests/test_kb_versioning.py](tests/test_kb_versioning.py) | 404 | 27 | KB version lifecycle |
| T12 | [tests/test_api_scenario.py](tests/test_api_scenario.py) | 389 | 24 | Scenario/Workshop |
| T13 | [tests/test_integration_flows.py](tests/test_integration_flows.py) | 330 | 5 | Cross-module integration testleri |
| T14 | [tests/test_ai_accuracy.py](tests/test_ai_accuracy.py) | 212 | 3 | AI accuracy benchmark |
| T15 | [tests/test_monitoring.py](tests/test_monitoring.py) | 173 | 15 | Health/Metrics endpoint'leri |
| T16 | [tests/test_performance.py](tests/test_performance.py) | 157 | 8 | Response time benchmark |
| | **Toplam** | **10,563** | **916** | |

### 3.6 Frontend (static/)

| # | Dosya | LOC | Sorumluluk |
|---|-------|----:|-----------|
| F1 | static/js/views/backlog.js | 1,058 | Backlog Workbench (WRICEF/Config/Sprint) |
| F2 | static/js/views/testing.js | 1,047 | Test Hub UI (plan/cycle/case/execution/defect) |
| F3 | static/js/views/requirement.js | 931 | Requirement listesi + filtre + classification |
| F4 | static/js/views/scenario.js | 842 | Scenario + Workshop yönetimi |
| F5 | static/js/views/program.js | 817 | Program setup (5 tab) |
| F6 | static/js/views/integration.js | 764 | Interface inventory + wave kanban |
| F7 | static/js/views/explore_hierarchy.js | 706 | L1-L4 process tree |
| F8 | static/js/views/explore_workshop_detail.js | 645 | Workshop detail (steps/fit/decisions) |
| F9 | static/js/views/explore_requirements.js | 582 | Explore requirement hub |
| F10 | static/js/views/analysis.js | 532 | Analysis (4-tab view) |
| F11 | static/js/views/explore_workshops.js | 445 | Workshop hub (list/table/kanban) |
| F12 | static/js/views/raid.js | 447 | RAID module UI |
| F13 | static/js/views/ai_admin.js | 390 | AI admin dashboard |
| F14 | static/js/views/process_hierarchy.js | 350 | Process hierarchy (eski scope view) |
| F15 | static/js/views/explore_dashboard.js | 322 | Explore dashboard |
| F16 | static/js/views/ai_query.js | 293 | NL Query chat UI |
| F17 | static/js/app.js | 346 | SPA router + program selector |
| F18 | static/js/explore-api.js | 165 | Explore module API client |
| F19 | static/js/api.js | 40 | Core API helper |
| F20 | static/js/components/explore-shared.js | 367 | Shared explore components |
| F21 | static/js/components/suggestion-badge.js | 163 | AI suggestion badge |
| F22 | static/js/components/notification.js | 161 | Notification bell |
| F23 | static/css/main.css | 2,285 | Ana CSS |
| F24 | static/css/explore-tokens.css | 949 | Explore design tokens |
| F25 | templates/index.html | 160 | SPA shell template |
| | **JS Toplam** | **11,413** | |

### 3.7 Migration Dosyaları (migrations/versions/)

| # | Revision | Dosya | Tablo Sayısı | Açıklama |
|---|----------|-------|:------------:|----------|
| MIG1 | `25890e807851` | 25890e807851_new_hierarchy_v1.py | — | Hiyerarşi refactoring |
| MIG2 | `c75811018b4d` | c75811018b4d_workshop_documents_table.py | 1 | WorkshopDocument |
| MIG3 | `d5a1f9b2c301` | d5a1f9b2c301_signavio_l4_hierarchy.py | — | L4 sub-process + Signavio alanları |
| MIG4 | `d9f1a2b3c401` | d9f1a2b3c401_sprint_9_integration_factory.py | 5 | Interface/Wave/CT/SP/Checklist |
| MIG5 | `9017f5b06e47` | 9017f5b06e47_explore_phase_0_16_tables.py | 16 | Explore Phase 0 |
| MIG6 | `a3b4c5d6e702` | a3b4c5d6e702_explore_phase_1_6_tables.py | 6 | Explore Phase 1 |
| MIG7 | `b4c5d6e7f803` | b4c5d6e7f803_explore_phase_2_3_tables.py | 3 | Explore Phase 2 |
| MIG8 | `e7b2c3d4f501` | e7b2c3d4f501_kb_versioning.py | — | KB versioning alanları |
| MIG9 | `f5a6b7c8d904` | f5a6b7c8d904_ts_sprint1_test_suite_step.py | 4 | TS-Sprint 1 (Suite/Step/Dependency/CycleSuite) |
| MIG10 | `g6b7c8d9e005` | g6b7c8d9e005_ts_sprint2_run_defect_enrich.py | 5 | TS-Sprint 2 (Run/StepResult/Comment/History/Link) |
| MIG11 | `h7c8d9e0f106` | h7c8d9e0f106_ts_sprint3_uat_sla_gonogo.py | 3 | TS-Sprint 3 (UATSignOff/PerfTestResult/TestDailySnapshot) |

### 3.8 Script & Seed Dosyaları (scripts/)

| # | Dosya | LOC | Sorumluluk |
|---|-------|----:|-----------|
| SC1 | scripts/seed_demo_data.py | 826 | Ana seed orkestratör (Anadolu Gıda senaryo) |
| SC2 | scripts/seed_data/specs_testing.py | 720 | FS/TS + TestPlan/Cycle/Case/Suite/Step/Run/Defect/Comment/History/Link seed |
| SC3 | scripts/seed_data/explore.py | 503 | Explore Phase seed data |
| SC4 | scripts/seed_data/l4_catalog.py | 409 | L4 process catalog |
| SC5 | scripts/seed_data/processes.py | 371 | L2-L3-L4 process hierarchy |
| SC6 | scripts/seed_data/raid.py | 281 | Risk/Action/Issue/Decision |
| SC7 | scripts/seed_data/scenarios.py | 223 | Scenario + Workshop data |
| SC8 | scripts/seed_data/backlog.py | 219 | Sprint + BacklogItem + ConfigItem |
| SC9 | scripts/seed_data/requirements.py | 145 | Requirement + Trace + RPM + OpenItem |
| SC10 | scripts/seed_data/project_roles.py | 63 | Team/role tanımlama |
| SC11 | scripts/embed_knowledge_base.py | 384 | KB embedding script |
| SC12 | scripts/seed_sap_knowledge.py | 345 | SAP domain knowledge seed |
| SC13 | scripts/collect_metrics.py | 177 | Otomatik metrik toplayıcı |
| SC14 | scripts/migrate_from_sqlite.py | 156 | SQLite → PostgreSQL göç |
| SC15 | scripts/setup_pgvector.py | 73 | pgvector kurulum |

### 3.9 Konfigürasyon & DevOps

| # | Dosya | LOC | Sorumluluk |
|---|-------|----:|-----------|
| C1 | requirements.txt | 41 | Python bağımlılıkları (Flask 3.1, SQLAlchemy 2.0, vb.) |
| C2 | pyproject.toml | 14 | Pytest konfigürasyonu |
| C3 | Makefile | 187 | 20+ hedef (dev, test, deploy, seed, migrate, vb.) |
| C4 | wsgi.py | 12 | Gunicorn entry point |
| C5 | app/config.py | 79 | Flask config (Dev/Test/Prod) |
| C6 | app/__init__.py | 157 | Flask app factory |
| C7 | app/auth.py | 235 | Auth middleware (JWT placeholder) |
| C8 | docker/Dockerfile | 19 | Multi-stage Docker build |
| C9 | docker/docker-compose.yml | 53 | Prod: Flask + PostgreSQL + Redis |
| C10 | docker/docker-compose.dev.yml | 31 | Dev: hot-reload + volume mount |
| C11 | .env / .env.example | 32/41 | Environment değişkenleri |
| C12 | .gitignore | 49 | Git ignore kuralları |

### 3.10 AI Knowledge (ai_knowledge/)

| # | Dosya | LOC | Açıklama |
|---|-------|----:|----------|
| K1 | ai_knowledge/prompts/nl_query.yaml | 109 | NL Query prompt template |
| K2 | ai_knowledge/prompts/defect_triage.yaml | 51 | Defect Triage prompt |
| K3 | ai_knowledge/prompts/requirement_analyst.yaml | 48 | Requirement Analyst prompt |
| K4 | ai_knowledge/prompts/risk_assessment.yaml | 47 | Risk Assessment prompt (henüz aktif değil) |

---

## 4. Dosyalar Arası Cross-Reference Haritası

### 4.1 FS/TS → Implementasyon Eşleşmesi

```
explore-phase-fs-ts.md (D1)
  ├── Modeller   → app/models/explore.py (M9) — 25/25 tablo ✅
  ├── API        → app/blueprints/explore_bp.py (B9) — 66 route ✅
  ├── Servisler  → app/services/ (S2-S9) — 8 servis ✅
  ├── Frontend   → static/js/views/explore_*.js (F7-F11, F15) + explore-shared.js (F20)
  ├── Seed       → scripts/seed_data/explore.py (SC3) + l4_catalog.py (SC4)
  ├── Migration  → MIG5 + MIG6 + MIG7
  ├── Test       → tests/test_explore.py (T1) — 192 test ✅
  ├── User Guide → D17 (TR) + D18 (EN)
  └── Task List  → EXPLORE_PHASE_TASK_LIST.md (D9) — 175/179 ✅

test-management-fs-ts.md (D2)
  ├── Modeller   → app/models/testing.py (M6) — 17/17 tablo ✅
  ├── API        → app/blueprints/testing_bp.py (B6) — 71 route (hedef 45)
  ├── Frontend   → static/js/views/testing.js (F2)
  ├── Seed       → scripts/seed_data/specs_testing.py (SC2)
  ├── Migration  → MIG9 + MIG10 + MIG11
  ├── Test       → tests/test_api_testing.py (T2) — 203 test ✅
  ├── User Guide → D19 (TR) + D20 (EN)
  └── Sprint Plan → SAP_Platform_Project_Plan.md (D5) → TS-Sprint 1-6 bölümü
```

### 4.2 Doküman Bağımlılık Grafiği

```
SAP_Platform_Project_Plan.md (D5) — ANA PLAN
  ├──► PROGRESS_REPORT.md (D6) — ilerleme takibi
  ├──► GATE_CHECK_REPORT.md (D7) — gate doğrulama
  ├──► PLAN_REVISION.md (D10) — plan revizyonu
  ├──► AI_PRIORITY.md (D11) — AI sprint sıralaması
  └──► FRONTEND_DECISION.md (D12) — Vue migration cancelled

sap_transformation_platform_architecture_v2.md (D3) — ANA MİMARİ
  ├──► explore-phase-fs-ts.md (D1) — Explore detay
  ├──► test-management-fs-ts.md (D2) — Testing detay
  ├──► SIGNAVIO_DRAFT.md (D13) — Signavio entegrasyon
  └──► DB_CONSISTENCY.md (D15) — DB analiz

sap_transformation_platform_architecture (2).md (D4) — ESKİ
  └──► ❌ Süpersede edildi (D3 v2.1 ile)

CHANGELOG.md (D8)
  └──► commit geçmişi ile senkron tutulmalı
```

### 4.3 Model → Blueprint → Test Zinciri

```
app/models/program.py     → app/blueprints/program_bp.py     → tests/test_api_program.py      (36 test)
app/models/scenario.py    → app/blueprints/scenario_bp.py    → tests/test_api_scenario.py     (24 test)
app/models/scope.py       → app/blueprints/scope_bp.py       → tests/test_api_scope.py        (45 test)
app/models/requirement.py → app/blueprints/requirement_bp.py → tests/test_api_requirement.py  (36 test)
app/models/backlog.py     → app/blueprints/backlog_bp.py     → tests/test_api_backlog.py      (59 test)
app/models/testing.py     → app/blueprints/testing_bp.py     → tests/test_api_testing.py      (203 test)
app/models/raid.py        → app/blueprints/raid_bp.py        → tests/test_api_raid.py         (46 test)
app/models/integration.py → app/blueprints/integration_bp.py → tests/test_api_integration.py  (76 test)
app/models/explore.py     → app/blueprints/explore_bp.py     → tests/test_explore.py          (192 test)
app/models/ai.py          → app/blueprints/ai_bp.py          → tests/test_ai.py + test_ai_assistants.py (141 test)
```

### 4.4 Seed Data → Model Bağlantıları

```
scripts/seed_demo_data.py (SC1) — Orkestratör
  ├── seed_data/scenarios.py      → Scenario, Workshop
  ├── seed_data/processes.py      → Process (L2/L3/L4)
  ├── seed_data/requirements.py   → Requirement, Trace, RPM, OpenItem
  ├── seed_data/backlog.py        → Sprint, BacklogItem, ConfigItem
  ├── seed_data/specs_testing.py  → FS, TS, TestPlan, TestCycle, TestCase, TestSuite,
  │                                  TestStep, TestExecution, Defect, CycleSuite,
  │                                  TestRun, StepResult, DefectComment, DefectHistory, DefectLink
  ├── seed_data/raid.py           → Risk, Action, Issue, Decision
  └── seed_data/explore.py        → (Explore Phase ayrı seed)
```

---

## 5. Tutarsızlık & Güncellik Analizi

### 5.1 Güncel Olmayan Dokümanlar

| # | Dosya | Sorun | Önem | Önerilen Aksiyon |
|---|-------|-------|------|-----------------|
| 1 | **D4** — architecture (2).md | v1.3 — D3 v2.1 ile süpersede edildi | 🟡 LOW | Silmek veya "ARCHIVED" etiketlemek |
| 2 | **D3** — architecture_v2.md | v2.1 test management bölümü TS-Sprint 2 güncellemesi yok (5→14 tablo, 28→55 route) | 🟠 MED | Modül 4.6 + Implementation Status güncelle |
| 3 | **D7** — GATE_CHECK_REPORT.md | Sprint 1-5 dönemi — Sprint 6-9 + TS-Sprint 1-2 eksik | 🟠 MED | Release 2 gate sonuçlarını ekle veya yeni gate raporu yaz |
| 4 | **D8** — CHANGELOG.md | Son entry: Monitoring (`da954ec`) — TS-Sprint 1-2 kayıtları yok | 🟠 MED | TS-Sprint 1-2 commit'lerini ekle |
| 5 | **D6** — PROGRESS_REPORT.md | TS-Sprint 2 güncellendi ✅ ama Explore Phase metrikleri eski (65 tablo → 71 tablo) bazı satırlarda | 🟡 LOW | Minor sayı uyumsuzluklarını düzelt |
| 6 | **D9** — EXPLORE_PHASE_TASK_LIST.md | "296 route" yazıyor, gerçekte 321 | 🟡 LOW | Raporun Explore odaklı olması normal, ama metrik güncelle |
| 7 | **D2** — test-management-fs-ts.md | 17 tablo / 45 endpoint hedef — mevcut 14/55. Sprint planı tracking eksik | 🟡 LOW | FS/TS v1.1 yazılabilir veya status footer ekle |

### 5.2 Bak Dosya Temizliği ✅ TAMAMLANDI

Tüm .bak dosyaları TD-Sprint 1 kapsamında silinmiştir (2026-02-10).

### 5.3 Codebase → FS/TS Uyum Durumu

| FS/TS Hedefi | Mevcut | Yüzde | Kalan |
|-------------|--------|------:|-------|
| Explore: 25 tablo | 25 tablo | **100%** | — |
| Explore: 50+ endpoint | 66 endpoint | **132%** | — |
| Test Mgmt: 17 tablo | 17 tablo | **100%** | — |
| Test Mgmt: 45 endpoint | 55 endpoint | **122%** | — |

---

## 6. Önerilen Aksiyonlar (Öncelik Sırasına Göre)

| # | Aksiyon | Öncelik | İlgili Dosya |
|---|--------|---------|-------------|
| 1 | D4 (architecture v1.3) arşivle veya sil | 🟢 Quick | D4 |
| 2 | 7 .bak dosyayı temizle | 🟢 Quick | *.bak |
| 3 | CHANGELOG.md'ye TS-Sprint 1-2 entry'leri ekle | 🟡 MED | D8 |
| 4 | architecture_v2.md test management bölümünü güncelle | 🟡 MED | D3 |
| 5 | GATE_CHECK_REPORT.md Release 2 gate sonuçlarını ekle | 🟡 MED | D7 |
| 6 | TS-Sprint 3'e geç (UATSignOff, PerfTestResult, Snapshot) | 🔵 PLAN | D5, M6, B6 |
| 7 | SIGNAVIO_DRAFT.md onay sürecini netleştir | 🟡 MED | D13 |

---

**Dosya:** `project-inventory.md`  
**Oluşturan:** GitHub Copilot (Claude Opus 4.6)  
**Tarih:** 2026-02-10
