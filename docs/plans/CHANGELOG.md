# CHANGELOG — SAP Transformation Platform

Tüm önemli değişiklikler bu dosyada belgelenir.
Format: [Conventional Commits](https://www.conventionalcommits.org/) uyumlu.

> **⚠ Mega commit açıklaması:** Sprint 4-6 (`a995200`) ve Sprint 7-8 (`db9a8a8`)
> tek commit halinde atıldı. Aşağıda bu commit'lerin içindeki gerçek task'lar
> listesi geriye dönük belgeleme amacıyla sunulmuştur.

> **📌 v2 Güncelleme (2026-02-10):** `da954ec` sonrası 33 eksik commit geriye dönük eklendi.
> (P1-001 bulgusu — consolidated-review-report.md)

---

## [Unreleased]

### Sprint S24 — Final Polish & Platform v1.0 (Tamamlandı)
- **Query.get() Migration**: All 27 deprecated `Model.query.get()` calls across 9 files migrated to `db.session.get()` (app + test files)
- **Error Handlers**: Flask 404/500/405/429 error handlers with API (JSON) vs browser (SPA fallback) differentiation
- **Rate Limiter Fix**: `storage_uri` now reads `REDIS_URL` env var; falls back to `memory://` in dev
- **skip_permission Documentation**: TODO removed, annotated with rationale (API key auth enforced)
- **Boolean Filter Fix**: `== False` → `.is_(False)` in `ai_bp.py` (SQLAlchemy best practice)
- **N+1 Query Fix**: Pre-loaded `levels_cache` / `parent_cache` in `fit_propagation.propagate_from_workshop()` eliminates per-step DB queries
- **JS Error Handler** (`static/js/error-handler.js`): `window.onerror` + `unhandledrejection` → toast notification + console.error + optional beacon to `/api/v1/client-errors`
- **error-handler.js linked** in `index.html` before all other scripts
- **LICENSE**: MIT License (Copyright 2026 Umut Soyyilmaz)
- **.env.example**: Enhanced with REQUIRED markers and descriptions
- **Docker Production Compose** (`docker/docker-compose.prod.yml`): No source mount, enforced env vars, resource limits (2CPU/2G app, 1CPU/1G pg, 0.5CPU/256M redis), json-file logging
- **DB Backup Script** (`scripts/backup_db.sh`): pg_dump with gzip, timestamp naming, auto-cleanup (keeps last 10)
- **README v2**: English Quick Start section, Docker instructions, updated metrics (103 tables, ~450 routes, 1593+ tests, 17 modules, 13 AI assistants), module list refreshed to 17, current status table updated through S24, LICENSE reference added
- **GitHub Actions CI**: Confirmed existing from S14 (175 lines, lint → test → build → deploy)
- 31 yeni test (`tests/test_final_polish.py`) — toplam: 1593+ test ✅

### Sprint S23 — Mobile PWA: Progressive Web App (Tamamlandı)
- **PWA Manifest** (`static/manifest.json`): name, short_name, display:standalone, theme_color:#354a5f, 8 icon sizes (72-512px), 3 shortcuts (Dashboard, AI, Backlog), orientation:any
- **Service Worker** (`static/sw.js`): Cache-first for static, network-first for API, pre-cache 12 URLs, offline fallback to `/offline`, skip-waiting + clients-claim, version-based cache invalidation
- **PWA Icons** (`static/icons/icon-{72-512}.png`): 8 PNG icons auto-generated via `scripts/infrastructure/gen_icons.py`
- **Mobile CSS** (`static/css/mobile.css`, ~350 LOC): PWA install banner, offline indicator, hamburger button, sidebar mobile overlay with backdrop, bottom tab bar (56px, 5 items), pull-to-refresh indicator, touch-target 44px utility, breakpoints at 1024px/768px/480px, safe-area inset support, touch pointer optimizations, dark mode support, reduced motion, print optimization, standalone display-mode detection
- **PWA Manager** (`static/js/pwa.js`, ~130 LOC): SW registration with update detection, beforeinstallprompt install banner, online/offline indicator with body class toggle, public API (promptInstall, dismissInstall, isOnline, isInstalled)
- **Mobile Touch Components** (`static/js/mobile.js`, ~220 LOC): hamburger toggle for sidebar (ARIA-aware), sidebar backdrop overlay, bottom navigation bar (Dashboard, Build, Testing, AI, More), pull-to-refresh with touch events, swipe-to-navigate (left-edge swipe → open sidebar), resize handler (auto-close sidebar > 768px), onViewChange hook
- **PWA Blueprint** (`app/blueprints/pwa_bp.py`): `/offline` fallback page, `/api/pwa/status` (feature flags), `/api/pwa/manifest` (inspect), `/api/pwa/cache-info` (list cacheable static assets)
- **index.html updates**: manifest link, theme-color meta, apple-touch-icon, apple-mobile-web-app-capable, mobile.css, pwa.js, mobile.js scripts
- 75 yeni test (10 sınıf) — toplam: 1562 test ✅ (103 tablo, 13 AI asistan, 17 blueprint)

### Sprint S21 — AI Phase 5: Final AI Capabilities (Tamamlandı)
- **AIFeedbackMetric** modeli: assistant_type (indexed), period_start/end, total_suggestions, approved/rejected/modified_count, accuracy_score, avg_confidence, common_rejection_reasons (JSON), prompt_improvement_hints (JSON)
- **AITask** modeli: task_type (indexed), status (CheckConstraint: pending/running/completed/failed/cancelled), progress_pct, input_json, result_json, error_message, user, program_id FK, workflow_name, started_at, completed_at
- **DataMigrationAdvisor** assistant (~270 LOC): analyze (full migration strategy), optimize_waves (parallel wave sequencing), reconciliation_check (data reconciliation checklist), _gather_context (DataObject+MigrationWave+LoadCycle+RAG)
- **IntegrationAnalyst** assistant (~220 LOC): analyze_dependencies (interface dependency mapping), validate_switch_plan (cutover switch plan validation), _gather_context (Interface+Wave+ConnectivityTest+RAG)
- **FeedbackPipeline** service (~145 LOC): compute_accuracy_scores (per-assistant approve/reject ratios), save_metrics (persist to DB), get_feedback_stats, generate_prompt_recommendations (low-accuracy detection)
- **TaskRunner** service (~160 LOC): submit (create AITask, optional background thread execution), get_status, cancel, list_tasks, update_progress, _execute_in_background (Flask app context aware)
- **AIDocExporter** service (~170 LOC): export_markdown (9 doc types w/ custom renderers), export_json, list_exportable_types
- **AIOrchestrator** service (~230 LOC): 4 predefined workflows (requirement_to_spec, risk_to_mitigation, migration_full_analysis, integration_validation), execute (sync chain), execute_async (via TaskRunner), JSON path output mapping
- **RAG genişletme**: 3 yeni entity extractor (interface, data_object, migration_wave) — toplam 11 extractor
- **PURPOSE_MODEL_MAP** +4 giriş: data_migration (balanced), integration_analyst (balanced), feedback (fast), orchestrator (strong)
- **LocalStub** +2 pattern: migration/wave/reconciliation + integration/dependency/switch stubs
- 2 yeni prompt YAML: data_migration.yaml, integration_analyst.yaml
- 26 yeni API endpoint: migration (3), integration (2), feedback (4), tasks (4), export (2), workflows (3) + budget/perf (existing)
- 81 yeni test (10 sınıf) — toplam: 1487 test ✅ (103 tablo, 13 AI asistan)

### Sprint S20 — AI Perf + Polish: Performance Optimization (Tamamlandı)
- **AIResponseCache** modeli: prompt_hash (unique indexed), model, purpose, response_json, prompt_tokens, completion_tokens, hit_count, expires_at, last_hit_at, is_expired(), to_dict()
- **AITokenBudget** modeli: program_id FK, user, period (daily/monthly CheckConstraint), token_limit (1M default), cost_limit_usd ($10 default), tokens_used, cost_used_usd, request_count, period_start, reset_at, is_exceeded(), remaining_tokens(), remaining_cost()
- **AIUsageLog** +2 alan: cache_hit (Boolean), fallback_provider (String)
- **AIAuditLog** +2 alan: cache_hit (Boolean), fallback_used (Boolean)
- **MODEL_TIERS** constant: fast/balanced/strong × 3 model (9 toplam)
- **PURPOSE_MODEL_MAP** constant: 12 assistant purpose → tier mapping
- **ResponseCacheService** (~200 LOC): Two-tier cache (in-memory TTLCache + DB), compute_hash, get/set/invalidate/cleanup_expired, stats, memory eviction (MAX=500)
- **ModelSelector** (~130 LOC): Purpose→tier→model routing, fallback chain builder, provider availability check
- **TokenBudgetService** (~170 LOC): check_budget, record_usage, create_or_update, reset, list, delete, auto-reset on period expiry
- **LLMGateway** S20 entegrasyonu: cache lookup/store, smart model selection, budget enforcement, fallback chain on provider failure
- 10 yeni API endpoint: performance/dashboard, performance/by-assistant, cache/stats, cache/clear, budgets CRUD+reset+status
- 67 yeni test (9 sınıf) — toplam: 1407 test ✅ (101 tablo)

### Sprint S19 — AI Phase 4: Doc Gen + Multi-turn Conversations (Tamamlandı)
- **AIConversation** modeli: title, assistant_type (12 tip), status (active/closed/archived), program_id FK, user, context_json, message_count, total_tokens, total_cost_usd
- **AIConversationMessage** modeli: conversation_id FK, seq (unique pair), role (user/assistant/system), content, model, prompt_tokens, completion_tokens, cost_usd, latency_ms
- **ConversationManager** service (~210 LOC): create_session, send_message (multi-turn w/ history), close_session, list_sessions (filterable), get_session
  - MAX_HISTORY_MESSAGES = 20, system message always retained
- **SteeringPackGenerator** assistant (~230 LOC): executive_summary, workstream_status, kpi_highlights, risk_escalations, decisions_needed, next_steps
- **WRICEFSpecDrafter** assistant (~210 LOC): overview, functional_requirements, technical_details, integration_points, data_mapping, test_approach
- **DataQualityGuardian** assistant (~210 LOC): quality_score, completeness_pct, issues, recommendations, cleansing_actions, migration_readiness
- 3 yeni prompt YAML: steering_pack.yaml, wricef_spec.yaml, data_quality.yaml
- LocalStub extended: steering/wricef/data_quality pattern match stubs
- 8 yeni API endpoint: doc-gen/steering-pack, doc-gen/wricef-spec, doc-gen/data-quality, conversations CRUD (create/list/get/send/close)
- RATELIMIT_ENABLED = False for TestingConfig
- Toplam 11 AI asistanı, 99 tablo, 1340 test

### 🚫 S22a/S22b — Dış Entegrasyonlar İPTAL EDİLDİ
- **S22a** (Jira + Cloud ALM, 36h) ve **S22b** (ServiceNow + Teams, 20h) iptal edildi
- Toplam 56 saat kapsam dışı bırakıldı — platform kendi başına yeterli, dış entegrasyon ihtiyacı ileri tarihe ertelendi
- S23 bağımlılığı S22b → S17'ye güncellendi
- Proje planı v2.5'e güncellendi

### Sprint S17 — Run/Sustain: Hypercare Exit & BAU Handover (Tamamlandı)
- **KnowledgeTransfer** modeli: cutover_plan FK, title, topic_area (6 alan), format (6 format), trainer, audience, duration, status (planned→completed), materials_url
- **HandoverItem** modeli: cutover_plan FK, title, category (8 alan), responsible, reviewer, status (pending→completed), priority (high/medium/low), target_date
- **StabilizationMetric** modeli: cutover_plan FK, metric_name, metric_type (system/business/process/user_adoption), target/current/baseline values, trend, is_within_target
- **run_sustain_service** (~310 LOC): compute_kt_progress, compute_handover_readiness, compute_stabilization_dashboard, evaluate_hypercare_exit (5 SAP kriterleri), generate_weekly_report, compute_support_summary, seed_handover_items (10 standart madde)
- **run_sustain_bp** blueprint (~330 LOC): ~24 endpoint — KT CRUD + progress, Handover CRUD + seed + readiness, Stabilization CRUD + dashboard, combined dashboard, exit-readiness, weekly-report, support-summary
- **SLA compliance job düzeltme**: 5 alan uyumsuzluğu giderildi (severity_level→severity, response_time_hours→response_target_min, acknowledged_at→response_time_min, incident_number→code, is_active kaldırıldı), resolution SLA breach kontrolü eklendi
- **Cockpit Chart.js CSP düzeltme**: CDN whitelist (cdn.jsdelivr.net, fonts.googleapis.com, fonts.gstatic.com), Chart undefined guard'ları
- 69 yeni test (10 sınıf) — toplam: 1252 test ✅ (97 tablo)

### Sprint S16 — Notification + Scheduling (Tamamlandı)
- **NotificationPreference** modeli: user_id, category, channel (in_app/email/both), digest_frequency, unique constraint
- **ScheduledJob** modeli: job_name, schedule_type (cron/interval/once), schedule_config (JSON), run stats tracking
- **EmailLog** modeli: email gönderim audit trail (recipient, template, status, error)
- **EmailService** (~280 LOC): 4 HTML template (notification_alert, daily_digest, weekly_digest, overdue_alert), SMTP + dev-mode logging
- **SchedulerService** (~210 LOC): decorator-based `@register_job`, DB persistence, thread execution
- **6 Scheduled Jobs** (~300 LOC): overdue_scanner, escalation_check, daily_digest, weekly_digest, stale_notification_cleanup, sla_compliance_check
- **notification_bp** blueprint (~330 LOC): ~19 endpoint — notification CRUD, broadcast, preferences, scheduler management, email logs
- 81 yeni test (12 sınıf) — toplam: 1183 test ✅
- Release 4 Gate: ✅ GEÇTİ

### Sprint S15 — AI Phase 3: Cutover AI + Meeting Minutes (Tamamlandı)
- **CutoverOptimizer** asistanı: `optimize_runbook()` + `assess_go_nogo()` (~470 LOC)
- **MeetingMinutesAssistant** asistanı: `generate_minutes()` + `extract_actions()` (~290 LOC)
- 4 yeni prompt YAML: cutover_optimizer, cutover_gonogo, meeting_minutes, meeting_actions
- 4 yeni AI endpoint (ai_bp.py): cutover/optimize, cutover/go-nogo, meeting-minutes/generate, meeting-minutes/extract-actions
- 56 yeni test (8 sınıf) — toplam: 1102 test ✅
- Toplam AI asistan: 8 (was 6)

### Sprint S14 — CI/CD + Security Hardening (Tamamlandı)
- **GitHub Actions CI:** `.github/workflows/ci.yml` — 4-job pipeline (lint → test → Docker build → deploy)
- **Docker:** Multi-stage optimized Dockerfile
- **Security Headers:** `app/middleware/security_headers.py` — CSP, HSTS, X-Frame-Options
- **Rate Limiter:** `app/middleware/rate_limiter.py` — per-blueprint limits (disabled in TESTING)
- **Deploy:** `scripts/infrastructure/deploy.sh` + `Procfile` + `ruff.toml`
- Toplam: 1046 test, 0 regresyon

### Sprint S13 — Cutover Hub + Hypercare (Tamamlandı)
- **8 yeni model:** CutoverPlan, CutoverScopeItem, RunbookTask, TaskDependency, Rehearsal, GoNoGoItem, HypercareIncident, HypercareSLA
- **~45 endpoint** cutover_bp.py: Plan CRUD, lifecycle, scope items, runbook tasks, dependencies, rehearsals, Go/No-Go, hypercare
- **cutover_service.py:** Code gen, runbook metrics, Go/No-Go aggregation, dependency validation
- **Frontend:** 5-tab SPA (Plans, Runbook, Rehearsals, Go/No-Go, Hypercare)
- **79 test** — toplam: 1046 test ✅
- **71 seed kaydı** (scripts/seed_data/cutover.py)

### UI-Sprint — Arayüz Standardizasyonu (Tamamlandı)
- **Prompt T:** Inter font + type scale (--fs-xs..3xl) + 44 rem→var() + 18 JS rem→px
- **Prompt F-REV:** KPI standardization — emoji removal, metricBar component, max 5 primary KPIs, flex-nowrap
- **Prompt H:** Hierarchy UI — compact KPI + hover actions
- **Prompt G:** Backlog redesign — filterBar + badges + 4 tabs
- **Fix:** Open Items metricBar eklendi, Turkish uppercase İ bug düzeltildi (lang="en"), Effort suffix fix

### TD-Sprint 1 — Teknik Borç Temizliği (Tamamlandı)
- CHANGELOG 33 commit güncellemesi ✅
- README kapsamlı güncelleme (77 tablo, 336 route, 916 test) ✅
- project-inventory.md düzeltme (M10, .bak temizliği) ✅
- Plan v2 başlık metrikleri güncelleme ✅
- PROGRESS_REPORT metrikleri güncelleme ✅
- TECHNICAL_DEBT tarih güncelleme ✅
- Eski architecture arşivleme ✅
- Makefile lint + format hedefleri ✅
- .env.example GEMINI_API_KEY ✅

### TS-Sprint 3 — Test Mgmt Phase 3: UAT, SLA, Go/No-Go (Tamamlandı)
- UATSignOff, PerfTestResult, TestDailySnapshot modelleri
- `generate-from-wricef` ve `generate-from-process` auto-gen endpoint'leri
- Defect 9-status lifecycle (assigned + deferred)
- SLA engine + Go/No-Go scorecard
- Entry/exit criteria validation

### Sprint 10 — Data Factory (Tamamlandi)
- DataObject, MigrationWave, DataQualityRule, LoadExecution modelleri
- Data Factory API: Data object CRUD + migration wave planning
- Data Factory UI: 5-tab view
- minutes_generator attribute fix (P1-003)

---

## [2026-02-10] TS-Sprint 2 — Test Execution Detail Layer — `d180bd5` → `3c331dd`

> 5 yeni model, 16 yeni endpoint, 46 yeni test. Toplam: 71 tablo, 321 route, 860 test.

### TS-2.1→2.5: Models — `d180bd5`
- TestRun modeli (runner_name, environment, started_at, ended_at, build_version)
- TestStepResult modeli (step→result mapping, evidence_url)
- DefectComment modeli (threaded comments, is_internal flag)
- DefectHistory modeli (field-level change audit)
- DefectLink modeli (duplicate/related/blocks/caused_by graph)
- Defect.linked_requirement_id FK eklendi

### TS-2.6: Migration — `0f92711`
- Alembic MIG-10: 5 yeni tablo + defects.linked_requirement_id FK

### TS-2.7→2.11: API — `7c97796`
- TestRun lifecycle: POST create → PUT update (start/complete) → GET list
- TestStepResult: POST record → GET by run
- DefectComment: POST add → GET list (kronolojik)
- DefectHistory: auto-record on field change → GET audit trail
- DefectLink: POST create → GET list → DELETE remove
- 14 yeni endpoint (321 toplam route)

### TS-2.13: Seed Data — `1bb9c4e`
- 6 test run, 8 step result, 6 defect comment, 6 history entry, 3 defect link

### TS-2.14: Tests — `b52a24f`
- 46 yeni pytest (TestRun CRUD, StepResult, DefectComment, DefectHistory, DefectLink)
- 147 toplam testing test, 848 toplam platform test (860 with deselected)

### Docs — `3c331dd`
- PROGRESS_REPORT güncellendi

---

## [2026-02-09] TS-Sprint 1 — Test Suite & Step Layer — `0271aa8` → `28535f8`

> 4 yeni model, 11 yeni endpoint, 37 yeni test. Toplam: 69 tablo, 306 route, 803 test.

### TS-1.1→1.4: Models — `0271aa8`
- TestSuite modeli (suite_type, execution_order, estimated_duration)
- TestStep modeli (step_order, action, expected_result, test_data)
- TestCaseDependency modeli (blocks/requires/related_to graph)
- TestCycleSuite junction (M:N Cycle↔Suite)
- TestCase.suite_id FK eklendi

### TS-1.5: Migration — `26107f0`
- Alembic MIG-09: 4 yeni tablo + test_cases.suite_id FK

### TS-1.6→1.9: API — `5a3756a`
- TestSuite CRUD (5 endpoint) + filter (type, status)
- TestStep CRUD (4 endpoint) per TestCase
- CycleSuite assign/remove (2 endpoint)
- TestCase.steps eager load

### TS-1.10: Seed Data — `22ed08c`
- 3 TestSuite, 32 TestStep, 4 CycleSuite

### TS-1.11: Tests — `28535f8`
- 37 yeni pytest (Suite CRUD/filter, Step CRUD, CycleSuite, suite_id)
- 101 toplam testing test

### Docs — `26e0b37`
- PROGRESS_REPORT TS-Sprint 1 güncelleme
- TS Sprint Plan dokümanına ekleme — `c44bc8f`

---

## [2026-02-09] Architecture v2 Updates — `e538e7d` → `151e119`

### Doküman Güncellemeleri
- `e538e7d` — Architecture: bump v2.0→2.1, revision history
- `6336cdd` — Architecture: TEST MANAGEMENT DOMAIN box güncellemesi
- `7f6292f` — Architecture: Module 4.6 rewrite with actual status
- `7e1f088` — Architecture: API /testing section actual 28 routes
- `151e119` — Architecture: roadmap Phase 3, Playbook mapping, Bölüm 14

---

## [2026-02-09] Explore Phase — Frontend + Phase 2 Backend — `1f59207`

### Eklenenler
- 10 yeni JS/CSS dosyası (view modülleri + dashboard)
- 3 yeni model (Phase 2 backend)
- 1 Alembic migration
- 2 yeni servis
- 9 API endpoint
- 175/179 görev tamamlandı (%98)
- `c2bac66` — Task listesi güncelleme
- `f47cd7e` — Project plan v1.1 + architecture v1.3 senkronizasyonu

---

## [2026-02-09] Explore Phase — Test Suite — `c3e304d`

### Eklenenler
- 192 kapsamlı explore test (4 test grubu: services, API, integration, edge cases)
- `f5cd2c7` — Task listesi güncelleme (92/150)
- `17e1778` — Progress report güncelleme (48 commit, 765 test, 62 tablo, 287 route)

---

## [2026-02-09] Explore Phase — Seed Data — `c8bcaa1`

### Eklenenler
- L4 catalog: 90 SAP Best Practice seed entry
- Explore demo data: 265 process levels, 20 workshop, 100 step, 40 requirement, 30 open item
- Project roles: 14 assignment

---

## [2026-02-09] Explore Phase 1 — Services + API — `ccc7438` → `28de926`

### Phase 0 + 1 Backend
- `f2eff2c` — Phase 0: 16 model, migration, services, blueprint
- `8bff07a` — Task list update (19 tasks done)
- `ccc7438` — Phase 1: 6 model, migration, 15 API endpoint, WorkshopSessionService
- `28de926` — Phase 0 complete: 5 services + 40 API endpoints (58 routes total)
- `6aa3e70` — Task list update (75/150)

---

## [2026-02-09] Explore Phase — Planning — `409b053`

### Eklenenler
- Explore Phase FS/TS detaylı task listesi (150+ görev)

---

## [2026-02-09] Vue 3 Migration Decision — `7ba4449` → `6c9c2ae`

### Eklenenler
- `7ba4449` — Frontend karar: Vue 3 migration onaylandı
- `6c9c2ae` — Vue 3 migration planı proje planına eklendi

### Durum
- 2026-02-11: Vue migration cancelled — vanilla JS SPA retained

---

## [2026-02-09] Sprint 9.5 — Hardening & Improvements — `198311d` → `ff3a129`

### P1-P9 İyileştirmeleri
- `198311d` — P2: Git workflow hooks, commit template, CHANGELOG
- `701f094` — Sprint 9.4: Test strategy genişletme
- `6e156d7` — P1: Frontend technology decision analysis dokümanı
- `e03ec2c` — P3: Dev/Prod DB tutarlılık düzeltmeleri
- `7efb17c` — P6: Plan revision with buffer analysis
- `272a5b6` — P7: AI assistant prioritization dokümanı
- `450cd63` — P4: External integration estimate revision (18h→56h)
- `ff3a129` — P9: KB versioning with content hashing

---

## [2026-02-09] Monitoring & Observability — `da954ec`

### Eklenenler
- `app/middleware/logging_config.py`: Structured logging (JSON prod, colored dev)
- `app/middleware/timing.py`: Request timing + in-memory metrics buffer
- `app/middleware/diagnostics.py`: Startup health banner
- `app/blueprints/health_bp.py`: `/health/ready` (load balancer), `/health/live` (detaylı)
- `app/blueprints/metrics_bp.py`: `/metrics/requests`, `/errors`, `/slow`, `/ai/usage`
- `tests/test_monitoring.py`: 15 yeni test
- Response headers: `X-Request-Duration-Ms`, `X-Request-ID`

---

## [2026-02-09] Progress Report Düzeltmeleri — `b8b8e4e`

### Düzeltilenler
- Özet tablosu tüm metrikleri gerçek değerlerle güncellendi (27 commit, 117 dosya, 216 endpoint, 527 test)
- Sprint 8 durumu: "🔄 devam ediyor" → "✅ tamamlandı"
- DB şema başlığı: 35 → 40 tablo
- Release 1/2 gate metrikleri güncellendi

### Eklenenler
- `scripts/analysis/collect_metrics.py`: Otomatik metrik toplama + `--check` doğrulama modu

---

## [2026-02-09] Code Review & Hardening — `5552f12`

### Güvenlik (CRITICAL)
- SQL injection: `execute-sql` endpoint'e 5-katmanlı güvenlik
- DB hata mesajı sızıntısı → generic response + logging
- `SECRET_KEY` → `secrets.token_hex(32)`
- `app/auth.py`: API key auth + role-based access (admin/editor/viewer)
- CSRF: Content-Type enforcement middleware

### Güvenlik (HIGH)
- Race condition: auto-code → MAX(id) + FOR UPDATE
- `approval_rate` operatör önceliği düzeltmesi
- Flask-Limiter: AI endpoint'lere 30/dk rate limit
- RAID notification: 6 noktaya eksik commit eklendi

### Performans (MEDIUM)
- Dashboard: O(N*M) → SQL aggregate sorgular
- `process_hierarchy`: N+1 → tek sorgu + in-memory ağaç
- RAG: pgvector `<=>` operatörü (Python fallback)
- BM25 `avg_dl`: O(N²) → O(N)
- Pagination: `paginate_query()` helper + 6 list endpoint

### Hata Yönetimi (MEDIUM)
- 111 `except` bloğuna `logger.exception()` eklendi
- `sprint_id` ValueError guard
- Workshop count autoflush düzeltmesi
- Input length (2MB) + Content-Type validation middleware

### Kod Kalitesi
- Global singleton → `current_app`-scoped lazy init
- Gateway: `time.sleep()` → `threading.Event().wait()` (4s cap)
- 8 `.bak` dosyası silindi
- 10 test dosyasında cleanup: `drop_all/create_all` pattern
- `pytest.skip` → `pytest.xfail`
- 8 FK kolonuna `index=True`

---

## [2026-02-10] Sprint 9 — Integration Factory — `289a5af` → `2920660`

### 9.1-9.2: Models + API — `289a5af`
- Interface, Wave, ConnectivityTest, SwitchPlan, InterfaceChecklist modelleri (5 tablo)
- Integration API: 26 endpoint (Interface CRUD, Wave planning, connectivity status)
- 66 yeni test

### 9.3: Traceability v2 — `365e817`
- Interface ↔ WRICEF ↔ TestCase chain traversal
- 8 yeni trace function + program summary
- 10 yeni test (512 toplam)

### 9.4-9.5: UI + Readiness — `a7edd8a`
- `integration.js`: 520+ satır, 4-tab view
- Interface/Wave CRUD, connectivity test, switch plan
- Readiness checklist toggle UI

### 9.6: Progress Report — `2920660`
- PROGRESS_REPORT.md Sprint 9 güncelleme

---

## [2026-02-09] Sprint 8 — AI Phase 1: İlk 3 Asistan — `d0c743c`

### Eklenenler
- NL Query Assistant: text-to-SQL + SAP glossary + chat UI
- Requirement Analyst: Fit/Gap classification + similarity search + 🤖 AI Analyze butonu
- Defect Triage: severity + module routing + duplicate detection + 🤖 AI Triage butonu
- 4 prompt template (YAML)

---

## [2026-02-09] Revizyonlar & Refactoring

### Hierarchy Refactoring — `5428088`
- ScopeItem ayrı tablo kaldırıldı → scope alanları L3'e taşındı
- Scenario = L1, 4-katman: Scenario → Process L2 → Process L3
- RequirementProcessMapping: N:M junction table
- OpenItem modeli eklendi

### Workshop Enhancements — `b2fd202`
- WorkshopDocument modeli + belge yükleme/silme
- Workshop'tan requirement ekleme
- Requirement'tan L3 oluşturma

### Analysis Hub — `65de96b`
- 4-tab analiz merkezi: Workshop Planner, Process Tree, Scope Matrix, Dashboard
- 5 yeni API endpoint

### Revizyon R2 — `133edca`
- Scenario → İş Senaryosu + Workshop modeli

### Revizyon R1 — `789d6cc`
- Program selector dropdown → kart tıklama

---

## [2026-02-08] Sprint 4-6 — ⚠ MEGA COMMIT — `a995200`

> Bu commit Sprint 4, 5 ve 6'yı birlikte içerir (+8,500 satır).
> Gelecekte her task ayrı commit olarak atılacaktır.

### Sprint 4: Backlog Workbench + Traceability v1
| Task | Açıklama |
|------|----------|
| 4.1 | WricefItem, ConfigItem, FunctionalSpec, TechnicalSpec modelleri |
| 4.2 | Status flow: New→Design→Build→Test→Deploy→Closed |
| 4.3 | Alembic migration: backlog domain (5 tablo) |
| 4.5-4.6 | Backlog API: WRICEF + Config CRUD (20 endpoint) |
| 4.7-4.8 | Traceability engine v1 + API |
| 4.9-4.10 | Backlog UI: Kanban + Liste + Config Items |
| 4.12 | 59 test |

### Sprint 5: Test Hub
| Task | Açıklama |
|------|----------|
| 5.1 | TestPlan, TestCycle, TestCase, TestExecution, Defect modelleri |
| 5.3-5.5 | Test Case, Execution, Defect API |
| 5.6-5.7 | Traceability genişletme + Matrix API |
| 5.8-5.11 | Test Hub UI: Catalog, Execution, Defect, Dashboard |
| 5.12 | 63 test |

### Sprint 6: RAID Module + Notification
| Task | Açıklama |
|------|----------|
| 6.1 | Risk, Action, Issue, Decision modelleri |
| 6.2 | RAID API: 26 endpoint |
| 6.3-6.4 | Risk scoring heatmap + dashboard |
| 6.5-6.8 | RAID UI + Notification service + bell icon |
| 6.9 | 46 test |

---

## [2026-02-09] Sprint 7-7.5 — ⚠ MEGA COMMIT — `db9a8a8`

> Bu commit Sprint 7 ve Sprint 8'in bir kısmını içerir (+7,426 satır).

### Sprint 7: AI Altyapı
| Task | Açıklama |
|------|----------|
| 7.1 | LLM Gateway: provider router (Anthropic, OpenAI, Gemini, LocalStub) |
| 7.2 | Token tracking + cost monitoring |
| 7.3 | AI modelleri + migration (4 tablo) |
| 7.4-7.5 | RAG pipeline: chunking + hybrid search (cosine + BM25 + RRF) |
| 7.6-7.7 | Suggestion Queue: model + API + badge UI |
| 7.8 | Prompt Registry: YAML template + versioning |
| 7.9 | SAP Knowledge Base v1 |
| 7.10-7.11 | AI admin dashboard + audit log |
| 7.12 | 69 test |

---

## [2026-02-08] Sprint 1-3 — Foundation

### Sprint 1: Mimari Refactoring — `2736abb`
- Flask App Factory, Program CRUD, SPA UI, Docker, 10 test

### Sprint 2: PostgreSQL + Program Setup — `847e785`
- 6 model, 24 endpoint, Alembic, Dashboard, 36 test

### Sprint 3: Scope & Requirements — `a970b82`
- Senaryo, Gereksinim, İzlenebilirlik matrisi, 38 test

---

## Commit Kuralları (Sprint 10+)

1. **Her task = 1 commit** (veya küçük task'lar birleştirilebilir)
2. **Format:** `[Sprint X.Y] Kısa açıklama` veya `[Fix]` / `[Docs]` / `[Feat]` / `[Refactor]` / `[Test]` / `[Chore]`
3. **Maks 72 karakter** ilk satır
4. **Test:** Her commit'te tüm testler geçmeli
5. **15+ dosya** veya **500+ satır** değişiklikte uyarı (hook)

### Task → Commit Mapping (Sprint 10 Örnek)
```
[Sprint 10.1] DataObject + MigrationWave modelleri       ← 1 commit (modeller)
[Sprint 10.2] Data Factory API: object CRUD               ← 1 commit (API - part 1)
[Sprint 10.2] Data Factory API: wave planning              ← 1 commit (API - part 2, çok büyükse)
[Sprint 10.3] Data quality scoring + rules                 ← 1 commit
[Sprint 10.4] Data Factory UI: object inventory tab        ← 1 commit (UI - part 1)
[Sprint 10.4] Data Factory UI: wave + quality dashboard    ← 1 commit (UI - part 2)
[Sprint 10.5] ETL pipeline status tracking                 ← 1 commit
[Sprint 10.6] pytest: data factory testleri                ← 1 commit (veya her API commit'ine dahil)
```

### Ne Zaman Birleştirmek OK?
- Model + migration → tek commit OK (birlikte anlamlı)
- 2-3 küçük fix → tek `[Fix]` commit OK
- Docs güncellemeleri → tek `[Docs]` commit OK

### Ne Zaman Kırmak Gerekli?
- API + UI → ayrı commit (farklı katman)
- 500+ satır → bölmeyi düşün
- Farklı modüller → ayrı commit

---

## Commit İstatistikleri

| Dönem | Commit | Tablo | Route | Test |
|-------|:------:|:-----:|:-----:|:----:|
| Sprint 1-3 (Foundation) | 3 | 12 | 44 | 84 |
| Sprint 4-6 (Mega) | 1 | +18 = 30 | +74 = 118 | +168 = 252 |
| Sprint 7-8 (Mega) | 2 | +9 = 39 | +57 = 175 | +141 = 393 |
| Revizyonlar | 5 | +1 = 40 | +25 = 200 | +44 = 437 |
| Hardening (S9.5) | 2 | 0 | +16 = 216 | +90 = 527 |
| Sprint 9 | 4 | +5 = 45 | +26 = 242 | +76 = 603 |
| Monitoring | 1 | 0 | +12 = 254 | +15 = 618 |
| P1-P9 Improvements | 8 | 0 | 0 | 0 |
| Vue Migration (cancelled) | 2 | 0 | 0 | 0 |
| Explore Phase | 11 | +20 = 65 | +66 = 295 | +192 = 766 |
| Architecture v2 | 5 | 0 | 0 | 0 |
| TS-Sprint Plan | 1 | 0 | 0 | 0 |
| TS-Sprint 1 | 6 | +4 = 69 | +11 = 306 | +37 = 803 |
| TS-Sprint 2 | 6 | +5(-3 net) = 71* | +16(-1) = 321 | +46 = 849→860** |
| **TOPLAM** | **57 entries (70 commits)** | **71** | **321** | **860** |

> *Net tablo artışı: TS-Sprint 2'de 5 yeni tablo eklendi, ancak bazı deduplicate
> **860 = 848 passed + 11 deselected + 1 xfail
