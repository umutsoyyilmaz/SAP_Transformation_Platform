# SAP Transformation Management Platform — Proje Uygulama Planı

**Versiyon:** 1.1
**Tarih:** 7 Şubat 2026 (Güncelleme: Haziran 2025)
**Hazırlayan:** Umut Soyyılmaz
**Proje Adı:** ProjektCoPilot → SAP Transformation Management Platform
**Başlangıç Noktası:** ProjektCoPilot (Flask + SQLite + Vanilla JS, Phase 3 ~40%)

> **📌 Son Güncelleme Notu (v1.1):** Release 1 ve Release 2 tamamlandı, Release 3 Sprint 9 tamamlandı.
> Ek olarak Explore Phase (179 görev) büyük ölçüde tamamlandı (%98).
> Güncel metrikler: 65 DB tablosu, 295 API route, 766 test, 8 Alembic migration, 48+ commit.

---

## 1. Yönetici Özeti

Bu plan, mevcut ProjektCoPilot prototipini baz alarak SAP Transformation Management Platform'un tam kapsamlı uygulamasını detaylandırır. Plan 6 ana Release, 24 Sprint (her biri 2 hafta) üzerinden 48 haftalık (~12 ay) bir zaman çizelgesinde yapılandırılmıştır.

**Geliştirme Yöntemi:** Claude (mimari, modelleme, karmaşık logic) + GitHub Codespaces (geliştirme ortamı) + GitHub Copilot (coding assistant) + Codex Agent (otonom görevler, ihtiyaç halinde)

**Çalışma Modeli:** Solo developer + AI araçları. Haftada 15-20 saat geliştirme kapasitesi varsayılmıştır.

### Mevcut Durum (ProjektCoPilot)

> **⚠️ Aşağıdaki bölüm başlangıç durumunu gösterir. Güncel durum için "Güncel Platform Durumu" bölümüne bakın.**

```
TAMAMLANAN                           KISMEN HAZIR                    YAPILACAK
──────────────                       ────────────                    ─────────
✅ Proje Yönetimi (CRUD, 5-tab)     🟡 Requirements (API var,       ❌ Integration Factory
✅ Analysis Workspace (9-tab)           UI eksik)                    ❌ Data Factory
✅ Scenario Management               🟡 WRICEF (DB+API var,          ❌ Cutover Hub
✅ Dashboard (Chart.js)                 UI eksik)                    ❌ Run/Sustain
✅ Sidebar Navigation                🟡 Config Items (DB+API var,    ❌ RAID Module
✅ Global Proje Seçici                  UI eksik)                    ❌ Reporting Engine
✅ RBAC Temel Yapı                   🟡 Test Management (DB var,     ❌ AI Katmanı (14 asistan)
✅ SAP Fiori Horizon UI                 API kısmi)                   ❌ Traceability Engine
                                                                     ❌ Notification Service
Tech Stack: Flask + SQLite + Vanilla JS (SPA)                        ❌ Dış Entegrasyonlar
Kod: app.py (~1927 satır), index.html (~5800 satır), 17 DB tablosu
```

### ✅ Güncel Platform Durumu (Haziran 2025)

```
TAMAMLANAN (Release 1 + 2 + Sprint 9 + Explore Phase)
──────────────────────────────────────────────────────
✅ Program Setup (CRUD, 5-tab, Phase/Gate/Workstream/Team/Committee, Dashboard)
✅ Scope & Requirements (Scenario → Process L2/L3 → ScopeItem → Analysis → Requirement)
✅ Backlog Workbench (WRICEF + Config + FS/TS, Status Flow, Kanban)
✅ Test Hub (TestPlan, TestCycle, TestCase, TestExecution, Defect, Traceability Matrix)
✅ RAID Module (Risk, Action, Issue, Decision — CRUD + Scoring + Dashboard)
✅ Integration Factory (Interface, Wave, Connectivity, SIT Evidence)
✅ AI Altyapı (LLM Gateway, RAG Pipeline, Suggestion Queue, Prompt Registry)
✅ AI Phase 1 (NL Query, Requirement Analyst, Defect Triage — 3 asistan aktif)
✅ Traceability Engine v1 (Req ↔ WRICEF/Config ↔ TestCase ↔ Defect)
✅ Notification Service (in-app notifications)
✅ Explore Phase (25 model, 66 route, 8 servis, 10 frontend modül)
   ├── Fit/Gap Propagation, Workshop Session, Requirement Lifecycle
   ├── Open Item Lifecycle, Scope Change, Signoff, Snapshot, Minutes Generator
   ├── BPMN Diagram, Workshop Documents, Daily Snapshot
   └── Dashboard & Analytics (KPI kartlar, chart'lar, filtreleme)

DEVAM EDEN / KISMEN HAZIR                          YAPILACAK
──────────────────────                              ─────────
🟡 Data Factory (planlanıyor)                       ❌ Cutover Hub
🟡 Reporting Engine (temel KPI var, export eksik)   ❌ Run/Sustain
🟡 Vue 3 Migration (onaylandı, başlanmadı)          ❌ Security Module (JWT, row-level)
🟡 PostgreSQL geçişi (SQLite'da çalışıyor)          ❌ AI Phase 2-5 (11 asistan)
                                                     ❌ Dış Entegrasyonlar
                                                     ❌ Mobile PWA

Tech Stack: Flask 3.1 + SQLAlchemy 2.0 + SQLite (→PostgreSQL planlanıyor)
            Vanilla JS SPA (modüler, 22 JS dosya) + CSS tokens
Kod: 12 model dosyası, 13 blueprint, 13 servis, 8 migration
     65 DB tablosu, 295 API route, 766 test (0 fail), 48+ commit
     ~36K Python LOC, ~9.4K JS LOC
```

### Hedef Platform

```
12 Modül + 14 AI Asistan + Traceability Engine + Reporting Engine
80+ DB tablosu, 200+ API endpoint, AI altyapısı (LLM Gateway, RAG, Rule Engine)

📊 İlerleme (Haziran 2025):
   DB Tabloları:  ████████████████████░░░░  65/80+  (%81)
   API Endpoint:  ██████████████████████░░  295/200+ (%147 — hedef aşıldı!)
   AI Asistanlar: ████░░░░░░░░░░░░░░░░░░░  3/14    (%21)
   Modüller:      ████████████████░░░░░░░░  8/12    (%67)
   Testler:       766 (0 fail)
```

---

## 2. Stratejik Kararlar

### 2.1 Tech Stack Evrimi

ProjektCoPilot'un mevcut Flask+SQLite yapısı prototip için uygun ancak hedef platform için yetersiz. **Aşamalı geçiş** stratejisi izlenecektir:

| Karar | Mevcut | Release 1-2 | Release 3+ |
|-------|--------|-------------|------------|
| **Backend** | Flask (tek dosya) | Flask + Blueprints (modüler) | Flask + Blueprints (olgunlaşmış) |
| **Veritabanı** | SQLite | PostgreSQL + pgvector | PostgreSQL + pgvector (optimize) |
| **Frontend** | Vanilla JS SPA (tek HTML) | Vanilla JS (modüler JS dosyaları) | React veya Vue.js geçiş (opsiyonel) |
| **Cache** | Yok | Redis (AI queue + session) | Redis (genişletilmiş) |
| **AI** | Yok | Claude API + pgvector | Tam AI Orchestration Layer |
| **Dosya Depolama** | Yok | Local filesystem | S3/MinIO |
| **Auth** | Basit RBAC | Flask-Login + JWT | OAuth2 + RBAC tam |

**Neden PostgreSQL'e geçiş zorunlu?**
pgvector extension'ı AI asistanlar için kritik (embedding storage + similarity search). SQLite'da bu yetenek yok. Ayrıca row-level security, concurrent access ve JSON/JSONB desteği gerekli.

**Neden Frontend'i hemen değiştirmiyoruz?**
5800 satırlık index.html'den ders çıkardık — büyük monolitik değişiklikler risk. Release 1-2'de Vanilla JS'i modüler dosyalara böleriz (scenarios.js, requirements.js vb.), React/Vue geçişi ancak Release 4+ sonrasında değerlendirilir.

### 2.2 Monorepo Yapısı (Release 1 Hedef)

```
/SAP-Transformation-Platform
├── AGENTS.md                    # Codex agent talimatları
├── MASTER_PLAN.md               # Bu doküman
├── README.md
├── requirements.txt
├── .env.example
│
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Config (dev/test/prod)
│   ├── models/                  # SQLAlchemy modeller
│   │   ├── __init__.py
│   │   ├── program.py           # Project, Phase, Gate, Workstream
│   │   ├── scope.py             # Scenario, Process, ScopeItem, Analysis, Requirement
│   │   ├── backlog.py           # WRICEF, ConfigItem, FS, TS
│   │   ├── testing.py           # TestPlan, TestCase, TestExecution, Defect
│   │   ├── integration.py       # Interface, Wave
│   │   ├── data_factory.py      # DataObject, FieldMapping, LoadCycle
│   │   ├── cutover.py           # CutoverPlan, RunbookTask, Rehearsal
│   │   ├── raid.py              # Risk, Action, Issue, Decision
│   │   ├── run_sustain.py       # Incident, Problem, RFC
│   │   └── ai.py                # AISuggestion, AIEmbedding, PromptTemplate
│   │
│   ├── blueprints/              # Flask Blueprints (modüler route'lar)
│   │   ├── __init__.py
│   │   ├── program_bp.py
│   │   ├── scope_bp.py
│   │   ├── backlog_bp.py
│   │   ├── testing_bp.py
│   │   ├── integration_bp.py
│   │   ├── data_factory_bp.py
│   │   ├── cutover_bp.py
│   │   ├── raid_bp.py
│   │   ├── run_sustain_bp.py
│   │   ├── reporting_bp.py
│   │   └── ai_bp.py
│   │
│   ├── services/                # İş mantığı katmanı
│   │   ├── traceability.py      # Traceability engine
│   │   ├── notification.py      # Notification service
│   │   └── export.py            # PDF/PPTX/Excel export
│   │
│   └── ai/                      # AI katmanı
│       ├── __init__.py
│       ├── gateway.py           # LLM Gateway (Claude/OpenAI router)
│       ├── rag.py               # RAG pipeline (embed, retrieve, rerank)
│       ├── rule_engine.py       # Rule-based risk/threshold engine
│       ├── graph_analyzer.py    # Traceability graph traversal
│       ├── suggestion_queue.py  # Human-in-the-loop queue
│       ├── prompt_registry.py   # Versioned prompt templates
│       └── assistants/          # Her asistan ayrı modül
│           ├── nl_query.py
│           ├── requirement_analyst.py
│           ├── defect_triage.py
│           ├── steering_pack.py
│           ├── risk_sentinel.py
│           ├── work_breakdown.py
│           ├── wricef_drafter.py
│           ├── test_generator.py
│           ├── data_guardian.py
│           ├── impact_analyzer.py
│           ├── cutover_optimizer.py
│           ├── hypercare_warroom.py
│           ├── meeting_intel.py
│           └── workflow_builder.py
│
├── static/
│   ├── css/
│   │   └── main.css             # SAP Fiori Horizon tema
│   └── js/
│       ├── app.js               # Ana SPA router
│       ├── api.js               # API client helper
│       ├── components/          # Reusable UI bileşenleri
│       │   ├── table.js
│       │   ├── modal.js
│       │   ├── chart.js
│       │   ├── sidebar.js
│       │   └── suggestion-badge.js  # AI öneri rozeti
│       └── views/               # Her modülün JS'i
│           ├── program.js
│           ├── scope.js
│           ├── backlog.js
│           ├── testing.js
│           ├── integration.js
│           ├── data_factory.js
│           ├── cutover.js
│           ├── raid.js
│           ├── reports.js
│           └── ai_query.js
│
├── templates/
│   ├── base.html                # Ana layout (sidebar + header)
│   └── index.html               # SPA entry point
│
├── migrations/                  # Alembic DB migrations
├── tests/                       # Pytest test'ler
│   ├── test_models.py
│   ├── test_api_program.py
│   ├── test_api_scope.py
│   └── test_ai_gateway.py
│
├── ai_knowledge/                # SAP domain bilgi tabanı
│   ├── scope_items/             # SAP Best Practice scope items (JSON)
│   ├── fs_templates/            # FS şablonları (modül bazlı)
│   ├── process_flows/           # E2E süreç akışları (O2C, P2P, RTR)
│   ├── cutover_patterns/        # Cutover sıralamaları
│   ├── risk_rules/              # Risk threshold kuralları
│   └── prompts/                 # AI prompt templates (YAML)
│
├── scripts/
│   ├── migrate_from_sqlite.py   # ProjektCoPilot SQLite → PostgreSQL migration
│   ├── seed_sap_knowledge.py    # SAP knowledge base yükleme
│   └── setup_pgvector.py        # pgvector extension kurulumu
│
└── docker/
    ├── Dockerfile
    ├── docker-compose.yml       # App + PostgreSQL + Redis
    └── docker-compose.dev.yml   # Dev ortamı (Codespaces için)
```

---

## 3. Geliştirme Metodolojisi — Altın Kurallar

ProjektCoPilot deneyiminden çıkarılan dersler, bu projenin temel kurallarıdır:

### 3.1 AI Araç Kullanım Matrisi

| Araç | Ne İçin Kullan | Ne İçin Kullanma |
|------|----------------|------------------|
| **Claude (claude.ai)** | Mimari kararlar, veri modeli tasarımı, karmaşık iş mantığı, prompt engineering, code review, hata analizi | Rutin CRUD kodu, basit UI değişiklikleri |
| **GitHub Copilot** | Günlük coding (autocomplete), boilerplate kod, test yazma, refactoring | Mimari kararlar, karmaşık algoritma tasarımı |
| **Codex Agent** | Tek dosyalık, net kapsamlı görevler (bir model ekle, bir API endpoint yaz), test çalıştırma | Çok dosyalı değişiklikler, UI overhaul, mimari değişiklik |
| **Claude Code** | Kompleks multi-file refactoring, debugging, büyük göçler | Basit tek dosya değişiklikleri |

### 3.2 Sohbet/Session Kuralları (ProjektCoPilot'tan miras)

```
KURAL 1: BİR SESSION = BİR MODÜL = BİR İŞ
         Asla aynı session'da 2+ modüle dokunma

KURAL 2: BACKEND ÖNCE, FRONTEND EN SON
         Sıra: model → migration → API → test → UI

KURAL 3: HER BAŞARILI ADIMDA COMMIT
         Atomik commit'ler, net mesajlar

KURAL 4: MONOLITHIC HTML/JS YASAK
         Modüler dosyalar, hedefli değişiklikler

KURAL 5: HER SESSİON'IN BAŞINDA CONTEXT VER
         Mevcut durum + hedef + kapsam + sınırlar

KURAL 6: TEST OLMADAN İLERLEME YASAK
         curl/pytest ile API test, browser'da UI test
```

### 3.3 Sohbet Başlangıç Şablonu (Güncellenmiş)

```markdown
## PROJE: SAP Transformation Management Platform
- Tech: Flask + PostgreSQL + pgvector + Vanilla JS (modüler SPA)
- Ortam: GitHub Codespaces, port 8080
- Repo yapısı: Flask Blueprints + SQLAlchemy models
- Son commit: [HASH — AÇIKLAMA]
- Mimari doc: sap_transformation_platform_architecture.md

## MEVCUT DURUM
- Release: [X.Y]
- Son tamamlanan sprint: [Sprint N]
- Çalışan modüller: [liste]
- Çalışan AI asistanlar: [liste]

## BU SESSION'DA YAPILACAK
- Sprint: [Sprint N, Task X.Y]
- Modül: [TEK BİR MODÜL]
- Dosya(lar): [LİSTE — en fazla 2-3 ilişkili dosya]
- Scope: [NET KAPSAM]

## KURALLAR
1. SADECE belirtilen dosyaları değiştir
2. Mevcut çalışan kodu bozma
3. Her değişiklik sonrası test komutunu çalıştır
4. Commit mesajı öner
```

### 3.4 Branch Stratejisi

```
main ─────────────────────────────────────────────────────▶
  │
  ├── release/1.0 ──────────────────────────────▶ merge → main (tag: v1.0)
  │     │
  │     ├── sprint/S01-foundation-refactor ──▶ merge → release/1.0
  │     ├── sprint/S02-postgresql-migration ──▶ merge → release/1.0
  │     ├── sprint/S03-scope-requirements ──▶ merge → release/1.0
  │     └── sprint/S04-backlog-workbench ──▶ merge → release/1.0
  │
  ├── release/2.0 ──────────────────────────────▶ merge → main (tag: v2.0)
  │     ├── sprint/S05-... ──▶ merge → release/2.0
  │     ...
```

---

## 4. Release ve Sprint Planı

### Genel Bakış

```
RELEASE 1: Foundation & Core (Sprint 1-4, 8 hafta)
├── Mimari refactoring + PostgreSQL geçişi
├── Program Setup + Scope & Requirements tamamlama
├── Backlog Workbench tamamlama
└── Traceability Engine v1

RELEASE 2: Testing & Quality + AI Foundation (Sprint 5-8, 8 hafta)
├── Test Hub tam implementasyon
├── RAID Module
├── AI altyapı: LLM Gateway + RAG + Suggestion Queue
└── AI Phase 1: NL Query + Requirement Analyst + Defect Triage

RELEASE 3: Delivery Modules + AI Core (Sprint 9-12, 8 hafta)
├── Integration Factory
├── Data Factory
├── Reporting Engine + Steering Pack
├── AI Phase 2: Risk Sentinel + Work Breakdown + WRICEF Drafter + Steering Pack Gen.

RELEASE 4: Go-Live Readiness + AI Quality (Sprint 13-16, 8 hafta)
├── Cutover Hub
├── Go/No-Go Readiness Pack
├── AI Phase 3: Test Generator + Data Guardian + Impact Analyzer
└── AI Phase 2 genişletme: Risk Sentinel ML

RELEASE 5: Operations + AI Go-Live (Sprint 17-20, 8 hafta)
├── Run/Sustain Module
├── Hypercare Dashboard
├── AI Phase 4: Cutover Optimizer + Hypercare War Room
└── Notification Service + Email/Slack

RELEASE 6: Advanced + AI Maturity (Sprint 21-24, 8 hafta)
├── AI Phase 5: Meeting Intelligence + NL Workflow Builder
├── Dış entegrasyonlar (Jira, Teams, ServiceNow)
├── Mobile PWA
├── Multi-program / multi-wave support
└── AI performance optimization + cross-project learning
```

---

### RELEASE 1: Foundation & Core (Hafta 1-8)

**Hedef:** ProjektCoPilot'u profesyonel yapıya dönüştür, core modülleri tamamla
**Gate Kriteri:** Program Setup, Scope & Requirements, Backlog Workbench çalışır durumda, PostgreSQL aktif

---

#### Sprint 1: Mimari Refactoring (Hafta 1-2) ✅ TAMAMLANDI

**Amaç:** Monolitik yapıyı modüler yapıya dönüştür, geliştirme ortamını hazırla

| # | Task | Dosya(lar) | Araç | Tahmini Süre | Bağımlılık |
|---|------|-----------|------|-------------|-----------|
| 1.1 | Repo oluştur, `.gitignore`, `requirements.txt`, `README.md` | root | Copilot | 1 saat | — |
| 1.2 | Flask App Factory pattern oluştur (`app/__init__.py`, `config.py`) | app/ | Claude + Copilot | 2 saat | 1.1 |
| 1.3 | SQLAlchemy model base + `Program` modeli yaz (ProjektCoPilot projects tablosu referans) | app/models/ | Claude + Copilot | 3 saat | 1.2 |
| 1.4 | `program_bp.py` Blueprint — mevcut proje API'lerini taşı | app/blueprints/ | Copilot | 3 saat | 1.3 |
| 1.5 | Docker Compose hazırla (Flask + PostgreSQL + Redis) | docker/ | Claude | 2 saat | 1.1 |
| 1.6 | Codespaces devcontainer.json güncelle (PostgreSQL, Redis, pgvector) | .devcontainer/ | Copilot | 1 saat | 1.5 |
| 1.7 | Alembic migration altyapısı kur | migrations/ | Copilot | 1 saat | 1.3 |
| 1.8 | Mevcut ProjektCoPilot CSS'i `static/css/main.css`'e taşı | static/css/ | Copilot | 1 saat | 1.1 |
| 1.9 | `base.html` layout (sidebar + header) oluştur | templates/ | Claude + Copilot | 2 saat | 1.8 |
| 1.10 | `static/js/app.js` (SPA router) + `api.js` (fetch helper) | static/js/ | Claude + Copilot | 3 saat | 1.9 |
| 1.11 | Program modülü UI: `static/js/views/program.js` | static/js/views/ | Copilot | 3 saat | 1.10 |
| 1.12 | End-to-end test: proje CRUD çalışıyor mu? | — | Manual | 1 saat | 1.11 |

**Sprint 1 Toplam: ~23 saat**
**Çıktı:** Modüler Flask app, Docker Compose, PostgreSQL bağlantısı hazır, proje CRUD çalışır
**Commit Stratejisi:** Her task = 1 commit

**Codex Agent Uygun Task'lar:** 1.1, 1.5, 1.6, 1.7 (net kapsamlı, tek dosyalık)
**Claude Gerekli Task'lar:** 1.2, 1.3, 1.9, 1.10 (mimari kararlar içeriyor)

---

#### Sprint 2: PostgreSQL Migration + Program Setup Tamamlama (Hafta 3-4) ✅ TAMAMLANDI (PostgreSQL geçişi hariç — SQLite'da çalışıyor)

**Amaç:** SQLite verilerini PostgreSQL'e taşı, Program Setup modülünü genişlet

| # | Task | Dosya(lar) | Araç | Tahmini Süre | Bağımlılık |
|---|------|-----------|------|-------------|-----------|
| 2.1 | PostgreSQL + pgvector extension kurulumu (Codespaces) | scripts/ | Claude | 1 saat | S1 |
| 2.2 | `Phase`, `Gate`, `Workstream`, `TeamMember`, `Committee` modelleri | app/models/program.py | Claude + Copilot | 3 saat | 2.1 |
| 2.3 | Alembic migration: program domain tabloları | migrations/ | Copilot | 1 saat | 2.2 |
| 2.4 | ProjektCoPilot SQLite → PostgreSQL data migration scripti | scripts/migrate_from_sqlite.py | Claude | 3 saat | 2.3 |
| 2.5 | Program Setup API genişletme: Phase/Gate CRUD, Workstream CRUD, Team RACI | app/blueprints/program_bp.py | Copilot | 4 saat | 2.3 |
| 2.6 | Program Setup UI genişletme: Phases tab, Workstreams tab, Team tab | static/js/views/program.js | Copilot | 4 saat | 2.5 |
| 2.7 | SAP Activate faz şablonları (Discover→Explore→Realize→Deploy→Run) seed data | scripts/seed_sap_knowledge.py | Claude | 2 saat | 2.3 |
| 2.8 | Proje tipi seçiminde otomatik faz/gate oluşturma | app/blueprints/program_bp.py | Copilot | 2 saat | 2.7 |
| 2.9 | Program Health Dashboard (KPI kartları + Chart.js) | static/js/views/program.js | Copilot | 2 saat | 2.5 |
| 2.10 | pytest: program API endpoint testleri | tests/test_api_program.py | Copilot | 2 saat | 2.5 |

**Sprint 2 Toplam: ~24 saat**
**Çıktı:** PostgreSQL aktif, veri migrate edildi, Program Setup tam fonksiyonel
**Risk:** SQLite→PostgreSQL migration sırasında veri kaybı → Çözüm: migration öncesi backup zorunlu

---

#### Sprint 3: Scope & Requirements Modülü (Hafta 5-6) ✅ TAMAMLANDI

**Amaç:** Requirement-centric data modeli tam implementasyon

| # | Task | Dosya(lar) | Araç | Tahmini Süre | Bağımlılık |
|---|------|-----------|------|-------------|-----------|
| 3.1 | `Scenario`, `Process`, `ScopeItem`, `Analysis`, `Requirement` modelleri | app/models/scope.py | Claude | 4 saat | S2 |
| 3.2 | Alembic migration: scope domain tabloları | migrations/ | Copilot | 1 saat | 3.1 |
| 3.3 | Mevcut ProjektCoPilot scenario/analysis/requirement verilerini migrate et | scripts/migrate_from_sqlite.py | Claude | 2 saat | 3.2 |
| 3.4 | Scope API: Scenario CRUD, Process hierarchy CRUD, ScopeItem CRUD | app/blueprints/scope_bp.py | Copilot | 4 saat | 3.2 |
| 3.5 | Analysis API: Analysis CRUD + mevcut workshop verileri migration | app/blueprints/scope_bp.py | Copilot | 3 saat | 3.4 |
| 3.6 | Requirement API: CRUD + classification (Fit/PFit/Gap) + auto-code | app/blueprints/scope_bp.py | Copilot | 3 saat | 3.5 |
| 3.7 | Requirement → WRICEF/Config "convert" endpoint | app/blueprints/scope_bp.py | Claude + Copilot | 2 saat | 3.6 |
| 3.8 | Scope UI: Scenario listesi, process tree, scope item yönetimi | static/js/views/scope.js | Copilot | 4 saat | 3.6 |
| 3.9 | Analysis UI: Workshop detay sayfası (ProjektCoPilot 9-tab taşıma) | static/js/views/scope.js | Copilot | 3 saat | 3.8 |
| 3.10 | Requirements UI: Tablo + filter + inline classification | static/js/views/scope.js | Copilot | 3 saat | 3.9 |
| 3.11 | SAP Best Practice Scope Item seed data (JSON) | ai_knowledge/scope_items/ | Claude | 2 saat | 3.2 |
| 3.12 | pytest: scope API testleri | tests/test_api_scope.py | Copilot | 2 saat | 3.6 |

**Sprint 3 Toplam: ~33 saat** (yoğun sprint — 2 hafta + hafta sonu)
**Çıktı:** Scenario → Process → ScopeItem → Analysis → Requirement tam akış
**Codex Agent Uygun:** 3.2, 3.12

---

#### Sprint 4: Backlog Workbench + Traceability v1 (Hafta 7-8) ✅ TAMAMLANDI

**Amaç:** WRICEF/Config lifecycle tamamlama, temel traceability zinciri

| # | Task | Dosya(lar) | Araç | Tahmini Süre | Bağımlılık |
|---|------|-----------|------|-------------|-----------|
| 4.1 | `WricefItem`, `ConfigItem`, `FunctionalSpec`, `TechnicalSpec` modelleri | app/models/backlog.py | Claude | 4 saat | S3 |
| 4.2 | Status flow engine: New→Design→Build→Test→Deploy→Closed | app/models/backlog.py | Claude + Copilot | 2 saat | 4.1 |
| 4.3 | Alembic migration: backlog domain tabloları | migrations/ | Copilot | 1 saat | 4.1 |
| 4.4 | Mevcut ProjektCoPilot WRICEF/Config verilerini migrate et | scripts/migrate_from_sqlite.py | Copilot | 1 saat | 4.3 |
| 4.5 | Backlog API: WRICEF CRUD + filter (type, status, workstream) | app/blueprints/backlog_bp.py | Copilot | 3 saat | 4.3 |
| 4.6 | Backlog API: Config CRUD + FS/TS CRUD | app/blueprints/backlog_bp.py | Copilot | 3 saat | 4.5 |
| 4.7 | Traceability engine v1: Requirement ↔ WRICEF/Config link tablosu + API | app/services/traceability.py | Claude + Copilot | 3 saat | 4.5 |
| 4.8 | Traceability API: GET /traceability/chain/:entityType/:id | app/services/traceability.py | Copilot | 2 saat | 4.7 |
| 4.9 | Backlog UI: WRICEF listesi + detay (tabs: Overview, FS, TS, Tests, History) | static/js/views/backlog.js | Copilot | 4 saat | 4.6 |
| 4.10 | Config Items UI: Liste + detay | static/js/views/backlog.js | Copilot | 2 saat | 4.9 |
| 4.11 | Traceability badge: her entity'de "linked items" rozeti | static/js/components/ | Copilot | 2 saat | 4.8 |
| 4.12 | pytest: backlog + traceability testleri | tests/ | Copilot | 2 saat | 4.8 |

**Sprint 4 Toplam: ~29 saat**
**Çıktı:** WRICEF lifecycle çalışır, Requirement → WRICEF/Config → FS/TS akışı, traceability v1

### 🚩 RELEASE 1 GATE (Hafta 8 Sonu) — ✅ GEÇTİ

```
✅ Kontrol Listesi:
⚠️ PostgreSQL + pgvector aktif → SQLite ile çalışıyor, PostgreSQL geçişi ertelendi
✅ Program Setup: proje, faz, gate, workstream, team CRUD çalışıyor (25 route)
✅ Scope & Requirements: tam hiyerarşi çalışıyor (Scenario→Process→Req) (20+ route)
✅ Backlog Workbench: WRICEF + Config + FS/TS lifecycle çalışıyor (28 route)
✅ Traceability engine: Req ↔ WRICEF/Config link çalışıyor
✅ 295 API endpoint aktif (hedef 50+ — 5x aşıldı)
✅ 766 test (0 fail)
⚠️ ProjektCoPilot verileri migrate edilmedi (SQLite devam)
✅ Docker Compose ile tek komutla ayağa kalkıyor
```

---

### RELEASE 2: Testing & Quality + AI Foundation (Hafta 9-16)

**Hedef:** Test Hub tam implementasyon, RAID modülü, AI altyapısı kurulumu, ilk 3 AI asistan

---

#### Sprint 5: Test Hub — Catalog & Execution (Hafta 9-10) ✅ TAMAMLANDI

| # | Task | Dosya(lar) | Araç | Tahmini Süre | Bağımlılık |
|---|------|-----------|------|-------------|-----------|
| 5.1 | `TestPlan`, `TestCycle`, `TestCase`, `TestExecution`, `Defect` modelleri | app/models/testing.py | Claude | 4 saat | S4 |
| 5.2 | Alembic migration: test domain tabloları | migrations/ | Copilot | 1 saat | 5.1 |
| 5.3 | Test Case API: CRUD + filter (layer, status, linked_req) + auto-code | app/blueprints/testing_bp.py | Copilot | 3 saat | 5.2 |
| 5.4 | Test Execution API: plan → cycle → execution workflow | app/blueprints/testing_bp.py | Copilot | 3 saat | 5.3 |
| 5.5 | Defect API: CRUD + severity + linked WRICEF/Config + aging hesaplama | app/blueprints/testing_bp.py | Copilot | 3 saat | 5.4 |
| 5.6 | Traceability genişletme: TestCase ↔ Requirement, Defect ↔ WRICEF | app/services/traceability.py | Copilot | 2 saat | 5.5 |
| 5.7 | Traceability Matrix API: GET /traceability/matrix?project_id=X | app/services/traceability.py | Claude | 2 saat | 5.6 |
| 5.8 | Test Hub UI: Test catalog listesi + case detay | static/js/views/testing.js | Copilot | 4 saat | 5.5 |
| 5.9 | Test Execution UI: cycle workflow + execute + result entry | static/js/views/testing.js | Copilot | 3 saat | 5.8 |
| 5.10 | Defect UI: defect listesi + detay + linked items | static/js/views/testing.js | Copilot | 3 saat | 5.9 |
| 5.11 | Test KPI Dashboard: pass rate, defect velocity, aging chart | static/js/views/testing.js | Copilot | 2 saat | 5.10 |
| 5.12 | pytest: testing API testleri | tests/test_api_testing.py | Copilot | 2 saat | 5.5 |

**Sprint 5 Toplam: ~32 saat**

---

#### Sprint 6: RAID Module + Notification Foundation (Hafta 11-12) ✅ TAMAMLANDI

| # | Task | Dosya(lar) | Araç | Tahmini Süre | Bağımlılık |
|---|------|-----------|------|-------------|-----------|
| 6.1 | `Risk`, `Action`, `Issue`, `Decision` modelleri | app/models/raid.py | Claude | 3 saat | S5 |
| 6.2 | RAID API: CRUD + filter (type, status, severity, owner, workstream) | app/blueprints/raid_bp.py | Copilot | 4 saat | 6.1 |
| 6.3 | Risk scoring logic: probability × impact matrix + auto-RAG | app/blueprints/raid_bp.py | Claude | 2 saat | 6.2 |
| 6.4 | RAID Dashboard: risk heatmap, action aging, issue trend | static/js/views/raid.js | Copilot | 3 saat | 6.2 |
| 6.5 | RAID UI: liste + filtreler + detay modal | static/js/views/raid.js | Copilot | 3 saat | 6.4 |
| 6.6 | Notification service foundation (in-app notifications) | app/services/notification.py | Claude + Copilot | 3 saat | — |
| 6.7 | Notification UI: bell icon + dropdown + mark-read | static/js/components/ | Copilot | 2 saat | 6.6 |
| 6.8 | RAID ↔ Notification: risk status değişikliğinde bildirim | app/blueprints/raid_bp.py | Copilot | 1 saat | 6.6 |
| 6.9 | pytest: RAID + notification testleri | tests/ | Copilot | 2 saat | 6.2 |

**Sprint 6 Toplam: ~23 saat**

---

#### Sprint 7: AI Altyapı Kurulumu (Hafta 13-14) ✅ TAMAMLANDI

**Bu sprint kritik — tüm sonraki AI asistanların temeli burada kurulur**

| # | Task | Dosya(lar) | Araç | Tahmini Süre | Bağımlılık |
|---|------|-----------|------|-------------|-----------|
| 7.1 | LLM Gateway: provider router (Claude Haiku/Sonnet/Opus + OpenAI fallback) | app/ai/gateway.py | Claude | 4 saat | S6 |
| 7.2 | Gateway: token tracking, cost monitoring, latency logging | app/ai/gateway.py | Claude + Copilot | 2 saat | 7.1 |
| 7.3 | pgvector setup: `ai_embeddings` tablosu, HNSW indeks, FTS indeks | scripts/setup_pgvector.py | Claude | 2 saat | 7.1 |
| 7.4 | RAG pipeline: chunking engine (entity-aware chunks) | app/ai/rag.py | Claude | 3 saat | 7.3 |
| 7.5 | RAG pipeline: embedding (OpenAI API) + hybrid search (semantic + keyword) | app/ai/rag.py | Claude | 3 saat | 7.4 |
| 7.6 | Suggestion Queue: model + API (create, list pending, approve, reject, modify) | app/ai/suggestion_queue.py | Claude + Copilot | 3 saat | 7.1 |
| 7.7 | Suggestion Queue UI: pending suggestions panel + approve/reject buttons | static/js/components/suggestion-badge.js | Copilot | 2 saat | 7.6 |
| 7.8 | Prompt Registry: YAML template loading + versioning + A/B test flag | app/ai/prompt_registry.py | Claude | 2 saat | 7.1 |
| 7.9 | SAP Knowledge Base v1: scope items + modül kataloğu embed et | scripts/seed_sap_knowledge.py | Claude | 2 saat | 7.5 |
| 7.10 | AI admin dashboard: token usage, cost, suggestion stats | app/blueprints/ai_bp.py | Copilot | 2 saat | 7.6 |
| 7.11 | AI audit log: her AI çağrısı loglanır | app/ai/gateway.py | Copilot | 1 saat | 7.1 |
| 7.12 | pytest: gateway, RAG, suggestion queue testleri | tests/test_ai_gateway.py | Claude + Copilot | 2 saat | 7.6 |

**Sprint 7 Toplam: ~28 saat**
**Çıktı:** LLM Gateway + RAG Pipeline + Suggestion Queue + Prompt Registry çalışır

---

#### Sprint 8: AI Phase 1 — İlk 3 Asistan (Hafta 15-16) ✅ TAMAMLANDI

| # | Task | Dosya(lar) | Araç | Tahmini Süre | Bağımlılık |
|---|------|-----------|------|-------------|-----------|
| 8.1 | **NL Query Assistant**: text-to-SQL converter + SAP glossary | app/ai/assistants/nl_query.py | Claude | 4 saat | S7 |
| 8.2 | NL Query: SQL validation, sanitization, read-only enforcement | app/ai/assistants/nl_query.py | Claude | 2 saat | 8.1 |
| 8.3 | NL Query UI: chat-style query input + results display | static/js/views/ai_query.js | Copilot | 3 saat | 8.2 |
| 8.4 | NL Query API: POST /api/v1/ai/query/natural-language | app/blueprints/ai_bp.py | Copilot | 1 saat | 8.2 |
| 8.5 | **Requirement Analyst**: classification pipeline (Fit/PFit/Gap) | app/ai/assistants/requirement_analyst.py | Claude | 4 saat | S7 |
| 8.6 | Requirement Analyst: similarity search (benzer geçmiş requirements) | app/ai/assistants/requirement_analyst.py | Claude | 2 saat | 8.5 |
| 8.7 | Requirement Analyst: Scope modülüne entegrasyon (suggestion badge) | app/blueprints/scope_bp.py + UI | Copilot | 2 saat | 8.6 |
| 8.8 | **Defect Triage**: severity suggestion + module routing | app/ai/assistants/defect_triage.py | Claude | 3 saat | S7 |
| 8.9 | Defect Triage: duplicate detection (embedding similarity) | app/ai/assistants/defect_triage.py | Claude | 2 saat | 8.8 |
| 8.10 | Defect Triage: Test Hub'a entegrasyon (suggestion badge) | app/blueprints/testing_bp.py + UI | Copilot | 2 saat | 8.9 |
| 8.11 | Prompt templates: 3 asistan için YAML prompt'lar | ai_knowledge/prompts/ | Claude | 2 saat | 8.5 |
| 8.12 | End-to-end test: 3 asistanın suggestion akışı | — | Manual + pytest | 2 saat | 8.10 |

**Sprint 8 Toplam: ~29 saat**
**Çıktı:** İlk 3 AI asistan aktif, suggestion queue akışı çalışır

### 🚩 RELEASE 2 GATE (Hafta 16 Sonu) — ✅ GEÇTİ

```
✅ Kontrol Listesi:
✅ Test Hub: TestCase, TestExecution, Defect tam lifecycle (28 route)
✅ Traceability Matrix: Req ↔ TestCase ↔ Defect otomatik
✅ RAID Module: Risk, Action, Issue, Decision CRUD + scoring (30 route)
✅ AI altyapı: LLM Gateway + RAG + Suggestion Queue çalışıyor
✅ NL Query Assistant: doğal dille sorgulama çalışıyor
✅ Requirement Analyst: Fit/PFit/Gap önerisi çalışıyor
✅ Defect Triage: severity + duplicate detection çalışıyor
✅ 295 API endpoint aktif (hedef 100+ — 3x aşıldı)
✅ 766 test (0 fail)
✅ AI test modunda
```

---

### RELEASE 3: Delivery Modules + AI Core (Hafta 17-24)

---

#### Sprint 9: Integration Factory (Hafta 17-18) ✅ TAMAMLANDI

| # | Task | Dosya(lar) | Araç | Tahmini Süre |
|---|------|-----------|------|-------------|
| 9.1 | `Interface`, `Wave`, `ConnectivityTest`, `SwitchPlan` modelleri | app/models/integration.py | Claude | 3 saat |
| 9.2 | Integration API: Interface CRUD + Wave planning + connectivity status | app/blueprints/integration_bp.py | Copilot | 4 saat |
| 9.3 | Traceability genişletme: Interface ↔ WRICEF ↔ TestCase | app/services/traceability.py | Copilot | 2 saat |
| 9.4 | Integration UI: Interface inventory + wave kanban + connectivity dashboard | static/js/views/integration.js | Copilot | 4 saat |
| 9.5 | Interface readiness checklist (per interface) | app/blueprints/integration_bp.py + UI | Copilot | 2 saat |
| 9.6 | pytest: integration testleri | tests/ | Copilot | 1 saat |

**Sprint 9 Toplam: ~16 saat** (daha hafif sprint — dengeleme)

---

#### Sprint 10: Data Factory + Vue 3 Migration Phase 0 (Hafta 19-20)

| # | Task | Dosya(lar) | Araç | Tahmini Süre |
|---|------|-----------|------|-------------|
| 10.1 | `DataObject`, `FieldMapping`, `CleansingTask`, `LoadCycle`, `Reconciliation` modelleri | app/models/data_factory.py | Claude | 3 saat |
| 10.2 | Data Factory API: DataObject CRUD + Mapping + Cycle lifecycle | app/blueprints/data_factory_bp.py | Copilot | 4 saat |
| 10.3 | Data Factory API: Quality score hesaplama (field-level) | app/blueprints/data_factory_bp.py | Claude + Copilot | 2 saat |
| 10.4 | Data Factory UI: Object inventory + mapping editor + cycle tracker | static/js/views/data_factory.js | Copilot | 4 saat |
| 10.5 | Cycle comparison dashboard: N vs N-1 trend | static/js/views/data_factory.js | Copilot | 2 saat |
| 10.6 | pytest: data factory testleri | tests/ | Copilot | 1 saat |
| 10.7 | 🟢 **Vue 3 Phase 0:** Vite build tool kurulumu + dev/prod config | vite.config.ts, package.json | Copilot | 0.5 saat |
| 10.8 | 🟢 **Vue 3 Phase 0:** Tekrarlanan yardımcı fonksiyonları `utils.js`'e çıkar (esc, formatDate, formatters) | static/js/utils.js | Copilot | 0.5 saat |
| 10.9 | 🟢 **Vue 3 Phase 0:** Vue 3 + vue-router + Pinia scaffold + `VanillaAdapter` bileşeni | src/App.vue, src/router/ | Copilot | 1 saat |
| 10.10 | 🟢 **Vue 3 Phase 0:** Vitest + Vue Test Utils frontend test altyapısı | vitest.config.ts, src/__tests__/ | Copilot | 0.5 saat |

**Sprint 10 Toplam: ~18.5 saat** (16 Data Factory + 2.5 Vue Phase 0)

---

#### Sprint 11: Reporting Engine + Export + Vue 3 Phase 1 (Hafta 21-22)

| # | Task | Dosya(lar) | Araç | Tahmini Süre |
|---|------|-----------|------|-------------|
| 11.1 | KPI Aggregation Engine: her modülden haftalık snapshot | app/services/reporting.py | Claude | 3 saat |
| 11.2 | RAG (Red/Amber/Green) hesaplama kuralları | app/services/reporting.py | Claude | 2 saat |
| 11.3 | Reporting API: GET /reports/weekly, /reports/program-health | app/blueprints/reporting_bp.py | Copilot | 3 saat |
| 11.4 | PPTX export: python-pptx ile steering pack template | app/services/export.py | Claude + Copilot | 3 saat |
| 11.5 | PDF export: WeasyPrint ile rapor çıktısı | app/services/export.py | Copilot | 2 saat |
| 11.6 | Excel export: openpyxl ile traceability matrix, defect list | app/services/export.py | Copilot | 2 saat |
| 11.7 | Reporting UI: executive dashboard + export buttons | static/js/views/reports.js | Copilot | 3 saat |
| 11.8 | pytest: reporting + export testleri | tests/ | Copilot | 1 saat |
| 11.9 | 🟢 **Vue 3 Phase 1:** `app.js` → `App.vue` shell + `AppSidebar.vue` + vue-router | src/App.vue, src/components/ | Copilot | 2 saat |
| 11.10 | 🟢 **Vue 3 Phase 1:** Program selector → Pinia `programStore` + Toast/Modal composables | src/stores/, src/composables/ | Copilot | 1.5 saat |
| 11.11 | 🟢 **Vue 3 Phase 1:** `notification.js` → `NotificationBell.vue` + `suggestion-badge.js` → `SuggestionBadge.vue` | src/components/ | Copilot | 1.5 saat |
| 11.12 | 🟢 **Vue 3 Phase 2a:** `program.js` (817 LOC) → `ProgramView.vue` (~500 LOC) | src/views/ProgramView.vue | Copilot | 3 saat |
| 11.13 | 🟢 **Vue 3 Phase 2a:** `raid.js` (447 LOC) → `RaidView.vue` (~300 LOC) | src/views/RaidView.vue | Copilot | 2 saat |

**Sprint 11 Toplam: ~29 saat** (19 Reporting + 10 Vue Phase 1-2a)

---

#### Sprint 12: AI Phase 2 — Core AI Asistanlar + Vue 3 Phase 2b (Hafta 23-24)

| # | Task | Dosya(lar) | Araç | Tahmini Süre |
|---|------|-----------|------|-------------|
| 12.1 | **Steering Pack Generator**: KPI aggregate → LLM narrative → draft | app/ai/assistants/steering_pack.py | Claude | 4 saat |
| 12.2 | Steering Pack: PPTX otomatik oluşturma + PMO review workflow | app/ai/assistants/steering_pack.py | Claude + Copilot | 3 saat |
| 12.3 | **Risk Sentinel**: rule engine (7 Playbook risk pattern) + threshold alerts | app/ai/assistants/risk_sentinel.py | Claude | 4 saat |
| 12.4 | Risk Sentinel: RAID modülüne entegrasyon + notification | app/ai/assistants/risk_sentinel.py | Copilot | 2 saat |
| 12.5 | **Work Breakdown Engine**: scenario → workshop/Fit-Gap/WRICEF kırılım | app/ai/assistants/work_breakdown.py | Claude | 4 saat |
| 12.6 | Work Breakdown: SAP process template DB (E2E flows) | ai_knowledge/process_flows/ | Claude | 2 saat |
| 12.7 | **WRICEF Spec Drafter**: requirement → FS taslağı üretimi | app/ai/assistants/wricef_drafter.py | Claude | 4 saat |
| 12.8 | WRICEF Drafter: modül bazlı FS templates + few-shot RAG | ai_knowledge/fs_templates/ | Claude | 2 saat |
| 12.9 | 4 asistan UI entegrasyonu (suggestion badges + review panels) | static/js/ | Copilot | 3 saat |
| 12.10 | Prompt templates: 4 asistan için YAML prompt'lar | ai_knowledge/prompts/ | Claude | 2 saat |
| 12.11 | 🟢 **Vue 3 Phase 2b:** `requirement.js` (931 LOC) → `RequirementView.vue` (~600 LOC) | src/views/RequirementView.vue | Copilot | 3 saat |
| 12.12 | 🟢 **Vue 3 Phase 2b:** `backlog.js` (1058 LOC) → `BacklogView.vue` (~650 LOC) — Kanban reactivity | src/views/BacklogView.vue | Copilot | 3.5 saat |
| 12.13 | 🟢 **Vue 3 Phase 2b:** `testing.js` (1047 LOC) → `TestingView.vue` (~650 LOC) | src/views/TestingView.vue | Copilot | 3.5 saat |

**Sprint 12 Toplam: ~40 saat** (30 AI Phase 2 + 10 Vue Phase 2b)

> ⚠️ **Not:** PLAN_REVISION.md'deki S12a/S12b bölünmesi uygulanırsa, Vue 3 Phase 2b task'ları S12b'ye taşınabilir.

### 🚩 RELEASE 3 GATE (Hafta 24 Sonu) — 🔄 DEVAM EDİYOR (Sprint 9 ✅, Sprint 10-12 bekliyor)

```
✅ Kontrol Listesi:
✅ Integration Factory: Interface + Wave + Connectivity çalışıyor (26 route)
□ Data Factory: DataObject + Mapping + LoadCycle + QualityScore — PLANLANMIŞ
□ Reporting Engine: KPI aggregation + RAG status + export (PPTX/PDF/Excel) — PLANLANMIŞ
□ Steering Pack Generator: otomatik draft oluşturma — PLANLANMIŞ
□ Risk Sentinel: 7 kural bazlı risk pattern — PLANLANMIŞ
□ Work Breakdown Engine: scenario kırılım önerisi — PLANLANMIŞ
□ WRICEF Spec Drafter: FS taslağı üretimi — PLANLANMIŞ
□ 7 AI asistan aktif (3 + 4) — Şu an 3 aktif
□ 🟢 Vue 3 migration — Onaylandı ama başlanmadı
□ 🟢 Frontend testleri — Kısmen (jest/vitest planlanıyor)
✅ 295 API endpoint aktif (hedef 150+ — 2x aşıldı)
✅ 766 test (0 fail)
```

> **📌 Ek Not:** Explore Phase (planda bulunmayan) büyük ölçüde tamamlandı:
> 25 model, 66 route, 8 servis, 192 test, 10 frontend modül, 175/179 görev (%98)

---

### 📋 TEST SUITE SPRINT PLAN (Test Management FS/TS Genişletme)

> **Kapsam:** Test Management FS/TS dokümanındaki 17 tablo / 45 endpoint hedefine ulaşmak için 6 sprint planı.
> Mevcut durum: 5/17 tablo, 28/45 endpoint — **Hedef: Tam uyum (%100)**

#### Özet Tablo

| Sprint | Odak | Yeni Tablo | Yeni Route | Yeni Test | Task |
|--------|------|-----------|------------|-----------|------|
| TS-1 | Test Suite & Step Altyapısı | +4 | +11 | ~40 | 12 |
| TS-2 | TestRun & Defect Zenginleştirme | +5 | +15 | ~50 | 15 |
| TS-3 | UAT Sign-off, SLA & Go/No-Go | +3 | +9 | ~35 | 12 |
| TS-4 | Cloud ALM Sync & URL Standardizasyonu | 0 | +3 | ~20 | 10 |
| TS-5 | Legacy Model Sunset & Veri Taşıma | 0 | 0 | ~10 | 10 |
| TS-6 | Final Temizlik, Performans & Dokümantasyon | -9 (legacy drop) | 0 | ~5 | 10 |
| **Toplam** | | **+12 / -9 net** | **+38** | **~160** | **69** |

---

#### TS-Sprint 1 — Test Suite & Step Altyapısı (Kısa Vade)

| # | Task | Açıklama | Tahmini Süre |
|---|------|----------|-------------|
| TS-1.1 | `TestSuite` modeli oluştur | suite_type (SIT/UAT/Regression), status FSM, program_id FK | 2 saat |
| TS-1.2 | `TestStep` modeli oluştur | test_case_id FK, step_no, action, expected, test_data | 1.5 saat |
| TS-1.3 | `TestCaseDependency` modeli | predecessor/successor ilişkisi, dependency_type | 1 saat |
| TS-1.4 | `TestCycleSuite` junction modeli | cycle ↔ suite N:M ilişkisi | 1 saat |
| TS-1.5 | Alembic migration — 4 yeni tablo | Mevcut testing.py'ye entegre | 0.5 saat |
| TS-1.6 | TestSuite CRUD API (5 endpoint) | POST/GET/PUT/DELETE/list + filtreleme | 2 saat |
| TS-1.7 | TestStep CRUD API (4 endpoint) | case/:id/steps altında nested | 1.5 saat |
| TS-1.8 | TestCycleSuite assign/remove (2 endpoint) | cycle ↔ suite bağlama | 1 saat |
| TS-1.9 | TestCase.steps eager loading | Mevcut case endpoint'lerini güncelle | 0.5 saat |
| TS-1.10 | Seed data — suite & step demo verisi | seed_demo_data.py genişlet | 1 saat |
| TS-1.11 | pytest — suite/step/dependency testleri (~40 test) | CRUD + FSM + edge case | 2 saat |
| TS-1.12 | Mevcut TestCase modelini TestSuite FK ile güncelle | suite_id nullable FK ekle | 0.5 saat |

**TS-Sprint 1 Toplam: ~14.5 saat**

---

#### TS-Sprint 2 — TestRun & Defect Zenginleştirme (Kısa Vade)

| # | Task | Açıklama | Tahmini Süre |
|---|------|----------|-------------|
| TS-2.1 | `TestRun` modeli oluştur | execution bağımsız — run_type (manual/automated), environment, started/finished | 2 saat |
| TS-2.2 | `TestStepResult` modeli | run_id + step_id → step-level pass/fail/blocked, screenshot_url | 1.5 saat |
| TS-2.3 | `DefectComment` modeli | defect_id FK, author, body, created_at | 1 saat |
| TS-2.4 | `DefectHistory` modeli | defect_id FK, field, old/new, changed_by, timestamp | 1 saat |
| TS-2.5 | `DefectLink` modeli | source_defect / target_defect, link_type (duplicate/related/blocks) | 1 saat |
| TS-2.6 | Alembic migration — 5 yeni tablo | Tek migration, FK constraint'ler | 0.5 saat |
| TS-2.7 | TestRun lifecycle API (5 endpoint) | start, progress, complete, abort, get | 2 saat |
| TS-2.8 | TestStepResult API (4 endpoint) | run/:id/steps altında CRUD | 1.5 saat |
| TS-2.9 | DefectComment API (3 endpoint) | defect/:id/comments altında | 1 saat |
| TS-2.10 | DefectHistory otomatik kayıt | Defect PUT hook → history insert (event-driven) | 1.5 saat |
| TS-2.11 | DefectLink API (3 endpoint) | link CRUD + duplicate chain traversal | 1 saat |
| TS-2.12 | Defect modelini genişlet | root_cause, resolution, environment, linked_requirement alanları | 1 saat |
| TS-2.13 | TestExecution → TestRun migration bridge | Mevcut execution verilerini run'a map'le | 1 saat |
| TS-2.14 | Seed data — run & defect enrichment | Demo senaryolar | 1 saat |
| TS-2.15 | pytest — run/step-result/defect testleri (~50 test) | Lifecycle + history + linking | 2.5 saat |

**TS-Sprint 2 Toplam: ~19.5 saat**

---

#### TS-Sprint 3 — UAT Sign-off, SLA Engine & Go/No-Go (Orta Vade)

| # | Task | Açıklama | Tahmini Süre |
|---|------|----------|-------------|
| TS-3.1 | `UATSignOff` modeli | suite_id, approver, status (pending/approved/rejected), criteria JSON | 1.5 saat |
| TS-3.2 | `PerfTestResult` modeli | test_case_id, response_time, throughput, error_rate, environment | 1.5 saat |
| TS-3.3 | `TestDailySnapshot` modeli | snapshot_date, total/passed/failed/blocked, defect_open/closed | 1 saat |
| TS-3.4 | Alembic migration — 3 yeni tablo | FK constraint'ler + index'ler | 0.5 saat |
| TS-3.5 | UAT Sign-off API (4 endpoint) | initiate / approve / reject / status | 2 saat |
| TS-3.6 | Performance test result API (3 endpoint) | POST result / GET trend / GET comparison | 1.5 saat |
| TS-3.7 | Snapshot cron/trigger servisi | Günlük snapshot oluşturma + manual trigger endpoint | 2 saat |
| TS-3.8 | SLA engine — cycle deadline & defect SLA | sla_config JSON, overdue hesaplama, dashboard kırmızı flag | 2.5 saat |
| TS-3.9 | Go/No-Go readiness aggregation | Suite pass rate + critical defect count + sign-off status → readiness score | 2 saat |
| TS-3.10 | Dashboard endpoint genişletme | Burn-down chart data + SLA compliance + trend verisi | 1.5 saat |
| TS-3.11 | Seed data — UAT & perf senaryoları | 3 UAT suite + 10 perf result + 30 gün snapshot | 1 saat |
| TS-3.12 | pytest — UAT/SLA/snapshot testleri (~35 test) | Sign-off flow + SLA overdue + aggregation | 2 saat |

**TS-Sprint 3 Toplam: ~19 saat**

---

#### TS-Sprint 4 — Cloud ALM Sync & URL Standardizasyonu (Orta Vade)

| # | Task | Açıklama | Tahmini Süre |
|---|------|----------|-------------|
| TS-4.1 | Cloud ALM test case sync servisi | Explore'daki CloudALMSyncLog pattern'ini kullan | 2 saat |
| TS-4.2 | Cloud ALM defect sync servisi | Bidirectional sync stub + webhook receiver | 2 saat |
| TS-4.3 | Cloud ALM sync status API (3 endpoint) | trigger-sync / status / history | 1.5 saat |
| TS-4.4 | URL pattern standardizasyonu | `/api/testing/*` prefix'ini FS/TS ile hizala | 1.5 saat |
| TS-4.5 | Regression set endpoint genişletme | Auto-select by module, risk priority, last-failed | 1.5 saat |
| TS-4.6 | Export endpoint'leri | CSV/Excel export for test cases, defects, results | 2 saat |
| TS-4.7 | Bulk operations API | Bulk status update, bulk assign, bulk re-run | 1.5 saat |
| TS-4.8 | Webhook notification entegrasyonu | Test fail → notification, defect critical → alert | 1.5 saat |
| TS-4.9 | API documentation (OpenAPI spec) | Testing modülü Swagger tanımları | 1.5 saat |
| TS-4.10 | pytest — sync/export/bulk testleri (~20 test) | Sync mock + export format + bulk ops | 2 saat |

**TS-Sprint 4 Toplam: ~17 saat**

---

#### TS-Sprint 5 — Legacy Model Sunset & Veri Taşıma (Uzun Vade)

| # | Task | Açıklama | Tahmini Süre |
|---|------|----------|-------------|
| TS-5.1 | TestExecution → TestRun veri taşıma scripti | Mevcut execution kayıtlarını run + step_result'a dönüştür | 2 saat |
| TS-5.2 | TestExecution deprecation flag'i | Soft-delete, API uyarı header'ı | 1 saat |
| TS-5.3 | Eski testing endpoint'lerini yeni yapıya yönlendir | 301 redirect veya alias route | 1.5 saat |
| TS-5.4 | Dashboard SQL sorgularını yeni tablolara güncelle | Aggregate sorgular test_run + step_result kullanacak | 2 saat |
| TS-5.5 | Traceability servisini güncelle | Suite → Case → Step → Run → Defect zinciri | 2 saat |
| TS-5.6 | AI Defect Triage asistanını güncelle | Yeni DefectHistory + DefectLink verilerini kullan | 1.5 saat |
| TS-5.7 | AI Test Generator asistanını güncelle | TestSuite + TestStep yapısına uyumlu output | 1.5 saat |
| TS-5.8 | Regression test — tüm mevcut 64 testing testi güncelle | Yeni model referanslarına geçir | 2 saat |
| TS-5.9 | Seed data güncelle | seed_demo_data.py yeni yapıya uyumlu hale getir | 1 saat |
| TS-5.10 | Integration test — cross-module doğrulama | Requirement → Suite → Case → Run → Defect → ALM zinciri | 1.5 saat |

**TS-Sprint 5 Toplam: ~16 saat**

---

#### TS-Sprint 6 — Final Temizlik, Performans & Dokümantasyon (Uzun Vade)

| # | Task | Açıklama | Tahmini Süre |
|---|------|----------|-------------|
| TS-6.1 | Legacy tablo drop migration | TestExecution + eski scope/scenario tabloları kaldır (-9 tablo) | 1 saat |
| TS-6.2 | Orphan foreign key temizliği | Eski FK referanslarını kontrol et ve temizle | 1.5 saat |
| TS-6.3 | Index optimizasyonu | Yeni tablolar için composite index + partial index | 1.5 saat |
| TS-6.4 | Query performans testi | 1000 test case + 500 defect ile yük testi | 2 saat |
| TS-6.5 | API response time benchmark | Her endpoint <200ms hedefi | 1 saat |
| TS-6.6 | FS/TS compliance final check | 17/17 tablo, 45/45 endpoint kontrol listesi | 1 saat |
| TS-6.7 | Mimari doküman güncellemesi | architecture_v2.md Test Management bölümünü güncelle | 1.5 saat |
| TS-6.8 | Progress report güncellemesi | Tüm metrikleri final değerlerle güncelle | 1 saat |
| TS-6.9 | Test coverage raporu | pytest --cov ile coverage analizi + eksik coverage doldur | 1.5 saat |
| TS-6.10 | Gate check — Test Management modülü final | FS/TS tam uyum onayı | 0.5 saat |

**TS-Sprint 6 Toplam: ~13 saat**

---

> **📌 Test Suite Sprint Plan Toplam Effort:** ~99 saat (69 task)
> **Hedef:** testing.py 5 tablo → 17 tablo, testing_bp.py 28 route → 66 route, testler 64 → 224+

---

### RELEASE 4: Go-Live Readiness + AI Quality (Hafta 25-32)

#### Sprint 13: Cutover Hub + Vue 3 Phase 2c & 3 (Hafta 25-26)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 13.1 | `CutoverPlan`, `RunbookTask`, `Rehearsal`, `GoNoGo` modelleri | Claude | 3 saat |
| 13.2 | Cutover API: Runbook CRUD + task dependency + rehearsal tracking | Copilot | 4 saat |
| 13.3 | Go/No-Go readiness aggregation: tüm modüllerden status toplama | Claude | 3 saat |
| 13.4 | Cutover UI: runbook Gantt, rehearsal comparison, live view | Copilot | 5 saat |
| 13.5 | Go/No-Go pack UI: readiness dashboard + checklist + sign-off | Copilot | 3 saat |
| 13.6 | pytest: cutover testleri | Copilot | 1 saat |
| 13.7 | 🟢 **Vue 3 Phase 2c:** `scenario.js` (842 LOC) → `ScenarioView.vue` + `integration.js` (764 LOC) → `IntegrationView.vue` | src/views/ | Copilot | 4 saat |
| 13.8 | 🟢 **Vue 3 Phase 2c:** `analysis.js` + `process_hierarchy.js` + `ai_query.js` + `ai_admin.js` → Vue views | src/views/ | Copilot | 4 saat |
| 13.9 | 🟢 **Vue 3 Phase 3:** Eski vanilla JS dosyalarını kaldır + cleanup | static/js/ → src/ | Copilot | 1 saat |
| 13.10 | 🟢 **Vue 3 Phase 3:** Component test coverage (Vitest + Vue Test Utils) — 5 kritik view | src/__tests__/ | Copilot | 3 saat |
| 13.11 | 🟢 **Vue 3 Phase 3:** E2E testleri (Playwright — 5 kritik akış) | e2e/ | Copilot | 3 saat |
| 13.12 | 🟢 **Vue 3 Phase 3:** Responsive / accessibility / Lighthouse audit | src/ | Copilot | 1 saat |

**Sprint 13 Toplam: ~35 saat** (19 Cutover Hub + 16 Vue Phase 2c-3)

#### Sprint 14: Security Module + Platform Hardening (Hafta 27-28)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 14.1 | RBAC genişletme: row-level security (workstream, proje bazlı) | Claude | 4 saat |
| 14.2 | JWT authentication + refresh token | Claude + Copilot | 3 saat |
| 14.3 | Audit trail: tüm entity değişiklikleri loglanır | Copilot | 3 saat |
| 14.4 | Document classification (Internal/Confidential/Restricted) | Copilot | 2 saat |
| 14.5 | API rate limiting + input validation genişletme | Copilot | 2 saat |
| 14.6 | Security UI: user management, role assignment | Copilot | 3 saat |
| 14.7 | Performance optimization: N+1 query fix, index optimization | Claude + Copilot | 2 saat |

**Sprint 14 Toplam: ~19 saat**

#### Sprint 15: AI Phase 3 — Quality AI Asistanlar (Hafta 29-30)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 15.1 | **Test Scenario Generator**: req + WRICEF → test case taslakları | Claude | 4 saat |
| 15.2 | Test Generator: SAP E2E flow bilgisi + SIT chaining | Claude | 3 saat |
| 15.3 | **Data Quality Guardian**: load cycle → profiling → cleansing önerisi | Claude | 4 saat |
| 15.4 | Data Guardian: field-level quality scoring + trend | Claude + Copilot | 2 saat |
| 15.5 | **Impact Analyzer**: traceability chain traversal + impact report | Claude | 4 saat |
| 15.6 | Impact Analyzer: notification to affected owners | Copilot | 2 saat |
| 15.7 | **Defect Triage genişletme**: root cause suggestion + auto-enrichment | Claude | 3 saat |
| 15.8 | 4 asistan UI entegrasyonu | Copilot | 3 saat |
| 15.9 | Prompt templates + SAP knowledge base genişletme | Claude | 2 saat |

**Sprint 15 Toplam: ~27 saat**

#### Sprint 16: AI Risk Sentinel ML + End-to-End Polish (Hafta 31-32)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 16.1 | Risk Sentinel genişletme: time-series anomaly detection (scikit-learn) | Claude | 4 saat |
| 16.2 | Risk Sentinel: geçmiş proje baseline karşılaştırma | Claude + Copilot | 2 saat |
| 16.3 | AI dashboard genişletme: accuracy tracking per assistant | Copilot | 2 saat |
| 16.4 | Confidence threshold kalibrasyon altyapısı | Claude | 2 saat |
| 16.5 | Cross-module UI tutarlılığı gözden geçirme + fix | Copilot | 3 saat |
| 16.6 | Performance test: 1000 requirement, 500 defect, 100 WRICEF ile yük testi | Claude + Manual | 3 saat |
| 16.7 | Tüm modüllerin entegrasyon testi | Manual | 2 saat |

**Sprint 16 Toplam: ~18 saat**

### 🚩 RELEASE 4 GATE (Hafta 32 Sonu)

```
✅ Kontrol Listesi:
□ Cutover Hub: Runbook + Rehearsal + Go/No-Go çalışıyor
□ Security: RBAC + JWT + Audit Trail aktif
□ Test Generator: requirement → test case önerisi çalışıyor
□ Data Guardian: quality profiling + cleansing önerisi çalışıyor
□ Impact Analyzer: change → impact report çalışıyor
□ Risk Sentinel ML: anomaly detection aktif
□ 11 AI asistan aktif (3 + 4 + 4)
□ 180+ API endpoint
□ pytest coverage > 75%
□ 1000 kayıt ile performans testi geçti
```

---

### RELEASE 5: Operations + AI Go-Live (Hafta 33-40)

#### Sprint 17: Run/Sustain Module (Hafta 33-34)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 17.1 | `Incident`, `Problem`, `RFC`, `KnowledgeBase` modelleri | Claude | 3 saat |
| 17.2 | Run/Sustain API: Incident lifecycle, SLA tracking, escalation rules | Copilot | 4 saat |
| 17.3 | Problem management: incident clustering → problem creation | Claude + Copilot | 3 saat |
| 17.4 | Run/Sustain UI: incident list, SLA dashboard, problem tracker | Copilot | 4 saat |
| 17.5 | Hypercare dashboard: war room view (live KPIs) | Copilot | 3 saat |
| 17.6 | Knowledge base UI: article CRUD + search | Copilot | 2 saat |

**Sprint 17 Toplam: ~19 saat**

#### Sprint 18: Notification Service + External Comms (Hafta 35-36)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 18.1 | Email notification (SMTP / SendGrid) | Copilot | 3 saat |
| 18.2 | Slack webhook integration | Copilot | 2 saat |
| 18.3 | Teams webhook integration | Copilot | 2 saat |
| 18.4 | Notification preferences UI: per-user, per-channel, per-event type | Copilot | 3 saat |
| 18.5 | Scheduled reports: weekly email digest | Copilot | 2 saat |
| 18.6 | Celery + Redis setup: async task processing | Claude + Copilot | 3 saat |

**Sprint 18 Toplam: ~15 saat**

#### Sprint 19: AI Phase 4 — Go-Live AI Asistanlar (Hafta 37-38)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 19.1 | **Cutover Optimizer**: CPM analizi (NetworkX) + critical path | Claude | 4 saat |
| 19.2 | Cutover Optimizer: parallelization analysis + what-if | Claude | 3 saat |
| 19.3 | Cutover Optimizer: rehearsal learning (actual vs plan delta) | Claude + Copilot | 3 saat |
| 19.4 | SAP cutover pattern DB yükleme | Claude | 2 saat |
| 19.5 | **Hypercare War Room**: incident triage + pattern detection (clustering) | Claude | 4 saat |
| 19.6 | War Room: daily report generator + KB article draft | Claude + Copilot | 3 saat |
| 19.7 | War Room: SAP known error pattern DB | Claude | 2 saat |
| 19.8 | 2 asistan UI entegrasyonu (cutover + hypercare) | Copilot | 3 saat |

**Sprint 19 Toplam: ~24 saat**

#### Sprint 20: AI Performance + Platform Polish (Hafta 39-40)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 20.1 | AI performance dashboard: accuracy per assistant, user satisfaction | Copilot | 3 saat |
| 20.2 | Feedback loop: onay/ret verileri → prompt optimization | Claude | 3 saat |
| 20.3 | Token cost optimization: caching, prompt compression | Claude | 2 saat |
| 20.4 | Global search: cross-module entity search | Copilot | 3 saat |
| 20.5 | User preferences: dashboard customization, default filters | Copilot | 2 saat |
| 20.6 | Help system: in-app tooltips + getting started guide | Copilot | 2 saat |
| 20.7 | Full regression test: tüm modüller + tüm AI asistanlar | Manual | 3 saat |

**Sprint 20 Toplam: ~18 saat**

### 🚩 RELEASE 5 GATE (Hafta 40 Sonu)

```
✅ Kontrol Listesi:
□ Run/Sustain: Incident + Problem + RFC + KB çalışıyor
□ Hypercare War Room dashboard aktif
□ Notification: in-app + email + Slack/Teams
□ Cutover Optimizer: CPM + parallelization + rehearsal learning aktif
□ Hypercare War Room AI: triage + pattern + daily report çalışıyor
□ 13 AI asistan aktif
□ 200+ API endpoint
□ pytest coverage > 75%
□ Token cost tracking aktif
```

---

### RELEASE 6: Advanced + AI Maturity (Hafta 41-48)

#### Sprint 21: AI Phase 5 — Advanced AI Asistanlar (Hafta 41-42)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 21.1 | **Meeting Intelligence**: Whisper API entegrasyonu (audio → transcript) | Claude | 3 saat |
| 21.2 | Meeting Intel: action/decision/risk extraction pipeline | Claude | 4 saat |
| 21.3 | Meeting Intel: entity resolution (fuzzy match to platform entities) | Claude | 3 saat |
| 21.4 | Meeting Intel UI: upload + extracted items review | Copilot | 3 saat |
| 21.5 | **NL Workflow Builder**: NL → workflow rule parser | Claude | 4 saat |
| 21.6 | Workflow Builder: Celery execution engine + dry-run | Claude + Copilot | 3 saat |
| 21.7 | Workflow Builder UI: rule definition + preview + activate | Copilot | 3 saat |

**Sprint 21 Toplam: ~23 saat**

#### Sprint 22: Dış Sistem Entegrasyonları (Hafta 43-44)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 22.1 | Jira integration: bidirectional sync (defect/requirement) | Claude + Copilot | 4 saat |
| 22.2 | SAP Cloud ALM integration: test case sync | Claude + Copilot | 4 saat |
| 22.3 | ServiceNow integration: incident sync (hypercare) | Claude + Copilot | 3 saat |
| 22.4 | Microsoft Teams: meeting recording fetch (Meeting Intelligence) | Copilot | 2 saat |
| 22.5 | Integration management UI: connection status, sync logs | Copilot | 3 saat |
| 22.6 | Webhook framework: inbound/outbound webhooks | Claude + Copilot | 2 saat |

**Sprint 22 Toplam: ~18 saat**

#### Sprint 23: Mobile PWA + Multi-Program (Hafta 45-46)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 23.1 | PWA manifest + service worker (offline capability) | Copilot | 3 saat |
| 23.2 | Responsive design: mobile-first dashboard layouts | Copilot | 4 saat |
| 23.3 | Multi-program support: Organization → Program → Project hierarchy | Claude | 3 saat |
| 23.4 | Multi-wave support: wave-based filtering ve raporlama | Copilot | 2 saat |
| 23.5 | Cross-project AI learning: anonim pattern paylaşımı altyapısı | Claude | 3 saat |
| 23.6 | Data export/import: project template export → new project import | Claude + Copilot | 3 saat |

**Sprint 23 Toplam: ~18 saat**

#### Sprint 24: Final Polish + Launch Prep (Hafta 47-48)

| # | Task | Araç | Tahmini Süre |
|---|------|------|-------------|
| 24.1 | AI fine-tuning: tüm prompt'ları proje feedback'ine göre optimize et | Claude | 4 saat |
| 24.2 | UI/UX final review: tutarlılık, accessibility, loading states | Copilot | 3 saat |
| 24.3 | Documentation: API docs (OpenAPI/Swagger), user guide | Claude + Copilot | 4 saat |
| 24.4 | Docker production build: multi-stage, optimized | Copilot | 2 saat |
| 24.5 | Deployment script: cloud provider setup (Railway/Render/AWS) | Copilot | 2 saat |
| 24.6 | End-to-end demo: tam proje lifecycle (Explore → Go-Live → Hypercare) | Manual | 3 saat |
| 24.7 | Performance benchmark: final yük testi + optimizasyon | Claude + Manual | 2 saat |

**Sprint 24 Toplam: ~20 saat**

### 🚩 RELEASE 6 GATE / PLATFORM v1.0 (Hafta 48 Sonu)

```
✅ Final Kontrol Listesi:
□ 12 platform modülü tam fonksiyonel
□ 14 AI asistan aktif
□ 200+ API endpoint
□ Traceability: Req → WRICEF → FS → TestCase → Defect → Cutover tam zincir
□ Export: PPTX, PDF, Excel
□ Dış entegrasyonlar: Jira, Cloud ALM, ServiceNow, Teams
□ Mobile PWA çalışıyor
□ Multi-program desteği
□ pytest coverage > 80%
□ Docker ile tek komutla deploy
□ API documentation (Swagger)
□ User guide hazır
□ Demo senaryosu başarılı
```

---

## 5. Zaman Çizelgesi Özeti

```
2026
FEB  MAR  APR  MAY  JUN  JUL  AUG  SEP  OCT  NOV  DEC  2027 JAN
 │    │    │    │    │    │    │    │    │    │    │    │
 ├─R1─┤    │    │    │    │    │    │    │    │    │    │
 │S1-S4│   │    │    │    │    │    │    │    │    │    │
 │ Foundation & Core   │    │    │    │    │    │    │    │
 │    │    │    │    │    │    │    │    │    │    │    │
 │    ├──R2──┤   │    │    │    │    │    │    │    │    │
 │    │S5-S8 │   │    │    │    │    │    │    │    │    │
 │    │Testing+AI Foundation │    │    │    │    │    │    │
 │    │    │    │    │    │    │    │    │    │    │    │
 │    │    ├──R3──┤   │    │    │    │    │    │    │    │
 │    │    │S9-S12│   │    │    │    │    │    │    │    │
 │    │    │Delivery+AI Core  │    │    │    │    │    │    │
 │    │    │    │    │    │    │    │    │    │    │    │
 │    │    │    ├──R4──┤   │    │    │    │    │    │    │
 │    │    │    │S13-16│   │    │    │    │    │    │    │
 │    │    │    │GoLive+AI Quality │    │    │    │    │    │
 │    │    │    │    │    │    │    │    │    │    │    │
 │    │    │    │    ├──R5──┤   │    │    │    │    │    │
 │    │    │    │    │S17-20│   │    │    │    │    │    │
 │    │    │    │    │Ops+AI GoLive  │    │    │    │    │
 │    │    │    │    │    │    │    │    │    │    │    │
 │    │    │    │    │    ├──R6──┤   │    │    │    │    │
 │    │    │    │    │    │S21-24│   │    │    │    │    │
 │    │    │    │    │    │Advanced+AI Maturity  │    │    │
 │    │    │    │    │    │    │    │    │    │    │    │
 ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼

Milestones:
🟢 R1 Gate: Hafta 8  — Core platform çalışır
🟡 R2 Gate: Hafta 16 — Test Hub + İlk 3 AI asistan
🔵 R3 Gate: Hafta 24 — Tam delivery + 7 AI asistan
🟠 R4 Gate: Hafta 32 — Go-live ready + 11 AI asistan
🔴 R5 Gate: Hafta 40 — Operations + 13 AI asistan
⭐ R6 Gate: Hafta 48 — Platform v1.0 Complete — 14 AI asistan
```

---

## 6. Effort Özeti

| Release | Sprint'ler | Platform Saat | AI Saat | Toplam | Haftalık Ort. |
|---------|-----------|---------------|---------|--------|--------------|
| R1: Foundation & Core | S1-S4 | 109 | 0 | 109 | ~14 saat/hafta |
| R2: Testing + AI Foundation | S5-S8 | 55 | 57 | 112 | ~14 saat/hafta |
| R3: Delivery + AI Core | S9-S12 | 51 | 30 | 81 | ~10 saat/hafta |
| R4: Go-Live + AI Quality | S13-S16 | 37 | 45 | 82 | ~10 saat/hafta |
| R5: Operations + AI Go-Live | S17-S20 | 34 | 42 | 76 | ~10 saat/hafta |
| R6: Advanced + AI Maturity | S21-S24 | 38 | 41 | 79 | ~10 saat/hafta |
| **TOPLAM** | **24 sprint** | **324 saat** | **215 saat** | **539 saat** | **~11 saat/hafta** |

**Ortalama haftalık yük: ~11 saat** — haftada 15-20 saat kapasiteyle uyumlu, buffer dahil.

---

## 7. Risk Yönetimi

| Risk | Olasılık | Etki | Mitigation |
|------|----------|------|------------|
| ProjektCoPilot → PostgreSQL migration veri kaybı | Orta | Yüksek | Migration öncesi SQLite backup, her tablo için verify script |
| AI API maliyet beklenenden yüksek | Düşük | Orta | Haiku/Sonnet/Opus tier routing, caching, token limit per request |
| Monolitik frontend (5800 satır HTML) refactoring riski | Yüksek | Yüksek | Aşamalı geçiş — önce JS modüler, HTML kademeli bölme, asla toplu sed |
| Claude API veya OpenAI API erişim sorunu | Düşük | Orta | Dual provider (Claude primary, OpenAI fallback), graceful degradation |
| Sprint'ler arası bağımlılık gecikmesi | Orta | Orta | Her sprint bağımsız test edilebilir, feature flag ile kademeli açma |
| Tek geliştirici burnout | Orta | Yüksek | Hafif sprint'ler (S9, S10, S18) ile dengeleme, buffer hafta planı |
| pgvector performans sorunu (büyük embedding hacmi) | Düşük | Orta | HNSW indeks parametreleri tune, partition by project_id |

---

## 8. Başarı Metrikleri

| Metrik | R1 Hedef | R1 Gerçekleşen | R3 Hedef | R6 Hedef |
|--------|----------|----------------|----------|----------|
| Çalışan API endpoint sayısı | 50+ | **295** ✅ | 150+ | 200+ |
| pytest coverage | >60% | **766 test** ✅ | >70% | >80% |
| DB Tablo sayısı | ~30 | **65** ✅ | ~50 | 80+ |
| Çalışan AI asistan sayısı | 0 | **3** ✅ | 7 | 14 |
| Ortalama API response time | <200ms | ✅ | <300ms | <500ms (AI dahil) |
| AI suggestion acceptance rate | — | — | >40% | >65% |
| Aylık AI API maliyeti | $0 | $0 (test) | <$200 | <$500 |
| Traceability chain completeness | Req→WRICEF | **Req→WRICEF** ✅ | Req→Test→Defect | Full chain |
| Kullanıcı sayısı (demo) | 1 (geliştirici) | 1 ✅ | 3-5 (pilot) | 10-20 (gerçek proje) |

---

## 9. Hızlı Başlangıç Checklist

Sprint 1'e başlamadan önce:

```
✅ 1. GitHub repo oluştur: SAP-Transformation-Platform — TAMAMLANDI
✅ 2. ProjektCoPilot repo'sunu fork/archive et (referans olarak sakla) — TAMAMLANDI
✅ 3. Codespaces devcontainer hazırla — TAMAMLANDI (lokal .venv + Docker da mevcut)
✅ 4. Bu proje planını repo'ya commit et (MASTER_PLAN.md) — TAMAMLANDI
✅ 5. AGENTS.md dosyasını güncelle — TAMAMLANDI
✅ 6. Mimari dokümanı repo'ya ekle — TAMAMLANDI
✅ 7. Sprint 1, Task 1.1'den başla — TAMAMLANDI (Sprint 1-9 tamamlandı)
```

---

*Bu plan, ProjektCoPilot deneyiminden çıkarılan dersleri, benchmarked AI capabilities'i ve SAP domain uzmanlığını birleştirerek uygulanabilir, takip edilebilir bir yol haritası sunar. Her sprint bağımsız test edilebilir, her release bir gate kriteri ile kontrol edilir.*
