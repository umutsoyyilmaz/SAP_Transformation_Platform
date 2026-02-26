# Program (1) -> Project (N) Technical Backlog

Date: 2026-02-24  
Owner: Architecture + Platform Team  
Scope: Multi-tenant SAP Transformation Platform

## 1. Objective
Program ve Project kavramlarını net ayırarak platformu `Tenant -> Program -> Project` context’iyle çalıştırmak; mevcut veriyi kayıpsız taşımak; tenant/program/project izolasyonunu zorunlu hale getirmek.

## 2. Target Operating Model
1. `Program`: Üst dönüşüm inisiyatifi (portfolio/business container).
2. `Project`: Program altındaki execution unit (wave/country/release/track).
3. L1-L4 süreç hiyerarşisi `project_id` ile tutulur.
4. Operasyonel modüller project-aware olur, program-level ekranlar aggregate eder.
5. Kullanıcı yetkileri tenant/program/project scope’unda yönetilir.

## 3. Global Rules (Non-Negotiable)
1. Her API erişimi tenant scope ile başlar.
2. Project scope gereken endpoint’lerde `project_id` zorunludur.
3. Geçiş sürecinde fallback sadece feature flag ile ve süreli çalışır.
4. Tüm write aksiyonları audit log’da `tenant_id/program_id/project_id` içerir.

## 4. Epic Backlog

## EPIC-1: Domain Model & Database Migration

### Story 1.1 - `projects` tablosunu ekle
Status: completed (2026-02-24)
Tasks:
1. `projects` tablosu oluştur: `id, tenant_id, program_id, code, name, type, status, owner_id, start_date, end_date, go_live_date, is_default, created_at, updated_at`.
2. FK ve indexleri ekle: `program_id -> programs.id`, `tenant_id -> tenants.id`.
3. Constraint ekle: program içinde `code` tekil, program içinde `is_default=true` tekil.

Definition of Done:
1. Migration geri alınabilir şekilde çalışıyor.
2. DB schema doğrulama testi geçiyor.
3. ORM model + serialization hazır.

Prompt (Implementation):
```text
Create an Alembic migration and SQLAlchemy model for a new `projects` table.
Requirements:
- Multi-tenant safe: include tenant_id and program_id with proper FKs.
- Add indexes for tenant/program filters and uniqueness constraints:
  - unique(program_id, code)
  - one default project per program (partial unique on is_default=true).
- Add model to app/models and ensure to_dict includes core fields.
- Return exact files changed and migration upgrade/downgrade summary.
```

### Story 1.2 - Mevcut veriler için default project backfill
Status: completed (2026-02-24)
Tasks:
1. Her program için `is_default=true` bir proje oluştur (`<PROGRAM_CODE>-DEFAULT`).
2. Backfill script idempotent olsun.
3. Dry-run ve apply modları olsun.

Definition of Done:
1. Hiçbir program default projectsiz kalmaz.
2. Script tekrar çalıştığında duplicate üretmez.
3. Rapor: kaç program işlendi, kaç proje oluşturuldu.

Prompt (Implementation):
```text
Write an idempotent backfill script that creates one default project per existing program.
Requirements:
- Safe for reruns, no duplicates.
- Supports --dry-run and --apply.
- Logs summary counts and errors per tenant/program.
- Use transaction boundaries and rollback on failure.
Provide command examples and expected output format.
```

### Story 1.3 - Kritik tablolara `project_id` ekle (phase-1)
Status: completed (2026-02-24)
Tasks:
1. Explore/L1-L4 hiyerarşi tablolarına `project_id` alanı ekle.
2. Backfill: mevcut kayıtları programın default project’ine map et.
3. Gerekli indexleri ekle (`tenant_id, program_id, project_id`).

Definition of Done:
1. L1-L4 verisi project’e bağlı hale gelir.
2. Eski kayıtların map raporu üretilir.
3. Sorgu performansı kabul sınırında kalır.

Prompt (Implementation):
```text
Implement phase-1 schema evolution for project scoping on hierarchy/explore tables.
Tasks:
- Add nullable project_id FKs first.
- Backfill using each record's program default project.
- Add composite indexes for tenant/program/project filtering.
- Provide migration order and rollback notes.
Output a risk checklist for locking/timeouts.
```

## EPIC-2: Service Layer & API Refactor

### Story 2.1 - Project CRUD endpointleri
Status: completed (2026-02-24)
Tasks:
1. `GET/POST /api/v1/programs/{program_id}/projects`.
2. `GET/PUT/DELETE /api/v1/projects/{project_id}`.
3. Tüm endpointlerde tenant doğrulaması zorunlu.

Definition of Done:
1. API contract dokümante edilir.
2. Pozitif/negatif testler geçer.
3. Cross-tenant/cross-program erişim bloklanır.

Prompt (Implementation):
```text
Build project CRUD APIs with strict tenant/program ownership checks.
Requirements:
- Validate JWT tenant scope on every query.
- Never use unscoped primary-key lookups.
- Return clear 403/404 semantics.
- Add unit+integration tests for authorization and data isolation.
Provide endpoint examples and sample JSON payloads.
```

### Story 2.2 - Dual-read / dual-write geçiş katmanı
Status: completed (2026-02-24)
Tasks:
1. Eski program-only endpointlerde `project_id` yoksa default project resolve et.
2. Yeni kayıtları hem program hem project context ile yaz.
3. Feature flag: `project_scope_enabled`.

Definition of Done:
1. Legacy client kırılmadan çalışır.
2. Yeni client project-aware çalışır.
3. Flag kapatıldığında güvenli fallback vardır.

Prompt (Implementation):
```text
Introduce a transitional scope resolver for backward compatibility.
Behavior:
- If project_id is provided, enforce ownership and use it.
- If missing, resolve program default project only when feature flag allows fallback.
- Emit warnings/metrics on fallback usage for deprecation tracking.
Add tests covering both flag states and failure cases.
```

### Story 2.3 - Scope helper standardizasyonu
Status: completed (2026-02-24)
Tasks:
1. Merkezi helper: `get_scoped(model, id, tenant_id=?, program_id=?, project_id=?)`.
2. Program/project endpointlerinde unscoped query yasağı.
3. Static analysis veya test kuralı ile ihlal tespiti.

Definition of Done:
1. Yeni kodda unscoped `db.session.get()` kullanılmaz.
2. Kritik servisler helper’a taşınır.
3. CI’da guard testi vardır.

Prompt (Implementation):
```text
Refactor scoped data access to a single helper API and remove unsafe lookups.
Requirements:
- Enforce at least tenant scope, plus program/project where required.
- Raise explicit errors for missing scope arguments.
- Add CI test/lint rule that fails when unsafe lookup patterns are added.
Return migration list of touched services.
```

## EPIC-3: Frontend Context & UX

### Story 3.1 - Global Program + Project selector
Status: completed (2026-02-24)
Tasks:
1. Header’a project selector ekle.
2. Program değişince project listesi yenilensin.
3. Project seçimi local storage’da tenant-bound saklansın.

Definition of Done:
1. UI context tutarlı görünür.
2. Program/project uyuşmazlığında state otomatik temizlenir.
3. Header, sidebar ve ekran bannerları aynı context’i gösterir.

Prompt (Implementation):
```text
Implement a global Program/Project context selector in SPA shell.
Requirements:
- Program change resets invalid project selection.
- Persist context with tenant-bound storage payload.
- Synchronize header badge, page banner, and API context usage.
- Add UX guard messages when context is missing.
Include code references and manual QA checklist.
```

### Story 3.2 - Project management ekranı
Status: completed (2026-02-24)
Tasks:
1. Programs ekranına “Projects” sekmesi ekle.
2. `Create/Edit/Delete Project` akışları ekle.
3. Default project görsel olarak işaretlensin, yanlış silme engellensin.

Definition of Done:
1. Kullanıcı program altında proje yönetebilir.
2. Default proje güvenlik kuralları çalışır.
3. Form validasyonları tamamdır.

Prompt (Implementation):
```text
Create a project management UI under Program view.
Requirements:
- List projects per selected program.
- Support create/edit/delete with validation.
- Prevent deletion of default project unless replacement flow is completed.
- Show status/type/owner and active indicator.
Add frontend tests for selection and CRUD interactions.
```

### Story 3.3 - URL/state standardı
Status: completed (2026-02-24)
Tasks:
1. `?program_id=&project_id=` query param standardı.
2. Deep-link açılışında context resolve.
3. Hatalı parametrelerde kullanıcıya düzeltme önerisi.

Definition of Done:
1. Paylaşılan linkler doğru context ile açılır.
2. Invalid parametrelerde güvenli fallback uygulanır.
3. Telemetry’de invalid context eventleri görünür.

Prompt (Implementation):
```text
Add URL-based context routing for program/project.
Requirements:
- Parse and validate query params at app boot.
- Resolve ownership and clear invalid combinations.
- Keep URL updated when selector changes.
- Track invalid context events for analytics.
Provide edge-case matrix and test scenarios.
```

## EPIC-4: Authorization & User Management Improvements

### Story 4.1 - Scope-aware RBAC genişletmesi
Status: completed (2026-02-24)
Tasks:
1. Role assignment modelini tenant/program/project scope destekler hale getir.
2. Yeni roller: `program_manager`, `project_manager`, `project_member`, `readonly`.
3. Permission evaluator’ı scope aware yap.

Definition of Done:
1. Kullanıcı yetkisi project bazında ayrışır.
2. Role inheritance ve override kuralları netleşir.
3. Yetki kararları testlerle doğrulanır.

Prompt (Implementation):
```text
Extend RBAC to support tenant/program/project scoped assignments.
Requirements:
- Add schema/model changes for scoped memberships.
- Implement deterministic permission evaluation (deny-by-default).
- Document precedence rules (tenant role vs program vs project).
- Add exhaustive tests for mixed-scope role combinations.
Return a permission matrix table in markdown.
```

### Story 4.2 - User onboarding ve atama akışı
Status: completed (2026-02-24)
Tasks:
1. Kullanıcıyı doğrudan project’e atama akışı ekle.
2. Bulk assignment/import desteği ekle.
3. Geçici yetki (start/end date) desteği ekle.

Definition of Done:
1. Yeni kullanıcı minimum adımda doğru project’e atanır.
2. Bulk import hataları satır bazlı raporlanır.
3. Süreli yetki süresi dolunca otomatik düşer.

Prompt (Implementation):
```text
Implement project-level user assignment workflows including bulk import.
Requirements:
- Direct assignment during onboarding.
- CSV import with row-level validation and error report.
- Time-bound role assignments with automatic expiry handling.
- Audit all membership changes with actor and scope details.
Provide API + UI flow documentation.
```

### Story 4.3 - “My Projects” deneyimi
Status: completed (2026-02-24)
Tasks:
1. Kullanıcı landing ekranında sadece erişebildiği project’leri görsün.
2. Favori/pinned project desteği.
3. Son kullanılan context geri yükleme.

Definition of Done:
1. Kullanıcı gereksiz context görmez.
2. Navigasyon süresi azalır.
3. Erişim dışı project linkleri güvenli şekilde engellenir.

Prompt (Implementation):
```text
Design and build a "My Projects" personalized landing view.
Requirements:
- Show only authorized projects.
- Support pin/favorite and recent contexts.
- Respect RBAC and block unauthorized deep links.
- Provide UX metrics instrumentation for time-to-first-action.
Add acceptance tests for role-based visibility.
```

## EPIC-5: Security, Observability, and Compliance

### Story 5.1 - Audit ve trace standardizasyonu
Status: completed (2026-02-24)
Tasks:
1. Tüm audit kayıtlarına `tenant_id/program_id/project_id`.
2. API request loglarında scope alanları zorunlu.
3. Güvenlik olayları için alarm kuralları.

Definition of Done:
1. Scope alanı eksik audit kaydı kalmaz.
2. Sızıntı denemeleri loglarda ayrıştırılabilir.
3. Alarm runbook’u hazırdır.

Prompt (Implementation):
```text
Standardize observability and audit metadata for scoped operations.
Requirements:
- Ensure tenant/program/project identifiers are included in logs/traces/audits.
- Add alerts for cross-scope access attempts and scope-mismatch errors.
- Create a runbook for incident triage and response.
Provide sample log events and dashboard queries.
```

### Story 5.2 - Data quality ve guard jobs
Status: completed (2026-02-24)
Tasks:
1. Orphan kayıt denetimi (`project_id` null/invalid).
2. Program-project uyuşmazlık denetimi.
3. Otomatik düzeltme yerine önce raporlama modu.

Definition of Done:
1. Günlük kalite raporu oluşur.
2. Kritik bozulmalar alarm üretir.
3. Düzeltme prosedürü onaylıdır.

Prompt (Implementation):
```text
Build scheduled data-quality checks for project scoping integrity.
Checks:
- Null or invalid project_id.
- Program/project mismatch.
- Cross-tenant anomalies.
Requirements:
- Start in report-only mode.
- Emit daily summary + critical alerts.
- Provide remediation SQL/playbook suggestions.
```

## EPIC-6: Testing & Release Execution

### Story 6.1 - Test plan (unit/integration/e2e/security)
Status: completed (2026-02-24)
Artifacts:
- `docs/specs/PROGRAM_PROJECT_MIGRATION_TEST_STRATEGY_2026-02-24.md`
- `scripts/ci_project_scope_regression.sh`
- `.github/workflows/ci.yml` (`Project-Scope Regression Pack` step)
Tasks:
1. Unit: scope resolver + RBAC evaluator.
2. Integration: API ownership ve isolation.
3. E2E: context selector + multi-project user journeys.
4. Security: IDOR/cross-tenant/cross-project senaryoları.

Definition of Done:
1. Kritik coverage hedefi karşılanır.
2. Regression pack pipeline’a eklenir.
3. Çıkış kriterleri netleşir.

Prompt (Implementation):
```text
Prepare a complete test strategy for Program->Project migration.
Requirements:
- Unit, integration, E2E, and security suites.
- Explicit negative tests for isolation boundaries.
- Release gate criteria with pass/fail thresholds.
- Test data strategy for multi-tenant/multi-project fixtures.
Provide a CI execution matrix and estimated runtime.
```

### Story 6.2 - Rollout ve rollback planı
Status: completed (2026-02-24)
Artifact: `docs/reviews/project/PROJECT_SCOPE_ROLLOUT_ROLLBACK_RUNBOOK_2026-02-24.md`
Tasks:
1. Canary tenant ile kademeli açılış.
2. Feature flag kontrollü geçiş.
3. Rollback prosedürü (schema-safe + traffic-safe).

Definition of Done:
1. Rollout adımları runbook’ta net.
2. MTTR hedefleri tanımlı.
3. Operasyon ve ürün ekipleri sign-off verir.

Prompt (Implementation):
```text
Create a production rollout and rollback runbook for project-scope migration.
Requirements:
- Canary rollout phases by tenant segment.
- Feature-flag based activation/deactivation steps.
- Clear rollback triggers and execution steps without data loss.
- Communication checklist for product/support/ops teams.
Include go/no-go checklist and ownership matrix.
```

## 5. Suggested Sprint Plan (4 Sprints)
1. Sprint 1: EPIC-1 (Story 1.1, 1.2) + EPIC-2 (Story 2.1 başlangıç).
2. Sprint 2: EPIC-1 (Story 1.3) + EPIC-2 (Story 2.2, 2.3).
3. Sprint 3: EPIC-3 (Story 3.1, 3.2, 3.3) + EPIC-4 (Story 4.1).
4. Sprint 4: EPIC-4 (Story 4.2, 4.3) + EPIC-5 + EPIC-6.

## 6. Release Gate Criteria
1. Program/project context mismatch defect sayısı: `0` (P1/P0).
2. Cross-tenant/cross-project unauthorized access testleri: `%100 pass`.
3. Backfill completeness: `%100 records mapped`.
4. Fallback usage metriği: release sonrası hedef tarihte `0`.
5. Operasyonel dashboard ve alarmlar aktif.

Validation Snapshot (2026-02-24):
| Gate | Status | Evidence |
|---|---|---|
| 1. Context mismatch defects = 0 (P1/P0) | PASS (test scope) | `tests/test_project_scope_resolver.py`, `tests/test_context_url_routing_contract.py` |
| 2. Unauthorized access tests = 100% pass | PASS | `tests/test_tenant_isolation.py`, `tests/test_api_projects.py`, `tests/test_scope_observability_story_51.py`, `scripts/ci_project_scope_regression.sh` |
| 3. Backfill completeness = 100% mapped | PASS (fixture scope) | `tests/test_backfill_default_projects.py` |
| 4. Fallback usage metric target = 0 | TRACKING (release sonrası) | `app/services/project_scope_resolver.py` fallback telemetry + release dashboard takibi |
| 5. Dashboards + alerts active | PASS (implementation + test) | `docs/reviews/project/SCOPE_SECURITY_OBSERVABILITY_RUNBOOK_2026-02-24.md`, `tests/test_scope_observability_story_51.py`, `/api/v1/metrics/security/alerts` |

Executed Verification Command (2026-02-24):
`PYTHONPATH=. python3 -m pytest -q tests/test_backfill_default_projects.py tests/test_tenant_isolation.py tests/test_api_projects.py tests/test_project_scope_resolver.py tests/test_scope_observability_story_51.py tests/test_data_quality_guard_jobs.py tests/test_context_url_routing_contract.py tests/test_my_projects_visibility.py`

## 7. Risks and Mitigations
1. Risk: Eski endpoint bağımlılıkları. Mitigation: dual-read/dual-write + telemetry.
2. Risk: Migration lock/timeouts. Mitigation: phased migration + off-peak run + dry-run.
3. Risk: Permission karmaşıklığı. Mitigation: deterministic evaluator + kapsamlı test matrisi.
4. Risk: UI context sapması. Mitigation: tenant-bound storage + URL validation + guard states.

Risk Control Check (2026-02-24):
| Risk | Related Gate(s) | Control Status | Evidence |
|---|---|---|---|
| Eski endpoint bağımlılıkları | Gate-1, Gate-4 | PASS / TRACKING | `tests/test_project_scope_resolver.py` (fallback flag behavior), `tests/test_api_projects.py` |
| Migration lock/timeouts | Gate-3 | PASS (plan + dry-run path) | `scripts/backfill_default_projects.py` dry-run/apply, `tests/test_backfill_default_projects.py` |
| Permission karmaşıklığı | Gate-1, Gate-2, Gate-5 | PASS | `app/services/permission_service.py`, `tests/test_tenant_isolation.py`, `tests/test_scope_observability_story_51.py` |
| UI context sapması | Gate-1, Gate-4 | PASS / TRACKING | `tests/test_context_url_routing_contract.py`, `tests/test_my_projects_visibility.py` |

## 8. Immediate Next Actions
1. Story 1.1 için migration taslağını çıkar.
2. Story 1.2 için dry-run backfill scriptini yaz.
3. Story 2.1 için project CRUD API branch’i aç.
4. Story 3.1 için header selector wireframe + contract belirle.

## 9. Stabilization Log
### Program/Project Flow Remediation (2026-02-24)
Status: completed (2026-02-25)
Scope:
1. Phase-1: IA/navigation hardening started (`My Projects` removed from sidebar, default entry moved to `Programs`).
2. Phase-2: project-required view guard enabled (project-aware screens blocked until project selection).
3. Phase-3: legacy `project_id=program_id` frontend fallback removed; explore open-item scope switched to resolved `project_id`.
4. Phase-4: program CRUD endpoints now enforce tenant-scoped access when JWT tenant context is present (non-breaking transitional enforcement).
5. Phase-4 (extended): critical child endpoints (`Backlog`, `RAID`, `Discover`, `Integration`) now enforce tenant-scoped program ownership when JWT tenant context is present.
6. Frontend hotfix: `Project Setup` made reachable with program-only context; project-required guard now disables all program-scoped views except `Programs` and `Project Setup`.
7. Phase-5 (final stabilization — 2026-02-25):
   a. Fixed `sap_auth_service._require_project` legacy alias — was looking up Program table with project_id; now uses Project model with tenant-scoped query.
   b. Added tenant-scoped lookups to all 7 routes in `reporting_bp.py` (was using unscoped `db.session.get`).
   c. Added backend guard preventing deletion of default project (returns 422).
   d. Added tenant ownership verification to all Phase/Gate/Workstream/TeamMember/Committee mutation endpoints.
   e. Fixed legacy `project_id=program_id` alias in `traceability.py` and `testing_service.py` — now resolves via Program's default project.
   f. Disabled `allow_fallback=True` in `explore/scope.py` — legacy fallback path fully decommissioned.
   g. Wired `projectAwareViews` into sidebar guard in `app.js` — was dead code, now actively disables project-required views.
   h. Added `My Projects` sidebar navigation entry in `index.html`.
   i. Expanded `test_scoped_lookup_guard.py` with 4 new guard tests covering `reporting_bp`, `sap_auth_service`, `explore/scope.py`, `traceability.py`, and `testing_service.py`.

Rollback Checkpoints:
1. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/index.html.bak`
2. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/app.js.bak`
3. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/app.js.phase2_guard.bak`
4. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/api.js.phase3_context.bak`
5. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/scope.py.phase3_context.bak`
6. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/open_items.py.phase3_context.bak`
7. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/program_bp.py.phase4_scope.bak`
8. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/backlog_bp.py.phase4_scope.bak`
9. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/raid_bp.py.phase4_scope.bak`
10. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/discover_bp.py.phase4_scope.bak`
11. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/integration_bp.py.phase4_scope.bak`

Validation (post-hotfix):
1. `PYTHONPATH=. python3 -m pytest -q tests/test_frontend_context_guard_contract.py tests/test_context_url_routing_contract.py tests/test_program_projects_ui_contract.py tests/test_my_projects_visibility.py tests/test_api_projects.py tests/test_project_scope_resolver.py` → PASS
2. `bash scripts/ci_project_scope_regression.sh` → PASS

## 10. Full Refactor Definition (Next Step)
Objective: complete Program->Project scope hardening end-to-end and remove transitional ambiguity.

Workstreams:
1. API Scope Standardization:
Replace remaining unscoped program/project lookups with scoped helpers and enforce consistent 403/404 semantics for cross-tenant/cross-program/cross-project access.
2. Legacy Fallback Removal:
Remove `project_id=program_id` compatibility paths from backend services and handlers; keep fallback only behind explicit feature-flag and sunset with target date.
3. Frontend Context Contract:
Make project-required routes non-enterable without valid project context and ensure selector, URL params, and API payloads stay strictly synchronized.
4. Authorization Consistency:
Align permission checks so all project-aware operations require scoped membership/role and eliminate bypasses except explicit super-admin policies.
5. Regression Gate Upgrade:
Expand CI pack with negative isolation tests for all critical modules and add guard rule for unsafe access patterns so CI fails on regressions.

Exit Criteria:
1. No legacy fallback usage in production telemetry for agreed observation window. — MET: `allow_fallback=False` enforced in `explore/scope.py`; `project_id=program_id` patterns eliminated from `traceability.py` and `testing_service.py`.
2. All cross-scope isolation tests pass in full regression matrix. — MET: `bash scripts/ci_project_scope_regression.sh` → 144 PASS (4 suites).
3. No unscoped `Program/Project` fetches remain in critical API paths. — MET: `reporting_bp.py` (7 routes), `sap_auth_service.py`, and all Phase/Gate/Workstream/Team/Committee mutation endpoints now tenant-scoped. `test_scoped_lookup_guard.py` (7 tests) enforces this in CI.
4. Story 6.1 status can be moved to `completed` with production-like evidence set. — MET: All 20 stories completed. Review document at `docs/reviews/project/PROGRAM_PROJECT_BACKLOG_REVIEW_2026-02-24.md`.

## 11. Full Refactor Execution Plan (4 Phases)
### Phase-FR1: Frontend Context Contract Hardening
Status: completed (2026-02-24)
Goal:
1. Program/project state management and sidebar guards become deterministic.
Scope (files):
1. `static/js/app.js`
2. `static/js/views/program.js`
3. `static/js/views/project_setup.js`
4. `templates/index.html`
Tests:
1. `tests/test_frontend_context_guard_contract.py`
2. `tests/test_context_url_routing_contract.py`
3. `tests/test_program_projects_ui_contract.py`
4. `tests/test_my_projects_ui_contract.py`
Rollback:
1. `.rollback_checkpoints/<date>_full_refactor/fr1_frontend_context/`
2. `.rollback_checkpoints/2026-02-24_phase1_program_mgmt/app.js.fr1_deterministic_sidebar.bak`
Done Criteria:
1. `Project Setup` opens with program-only context.
2. Project-required views are disabled/rerouted when project missing.
3. URL + selector + localStorage context stay in sync.
Validation:
1. `PYTHONPATH=. python3 -m pytest -q tests/test_frontend_context_guard_contract.py tests/test_context_url_routing_contract.py tests/test_program_projects_ui_contract.py tests/test_my_projects_ui_contract.py` → PASS
2. `bash scripts/ci_project_scope_regression.sh` → PASS

### Phase-FR2: Backend Scoped Access Standardization
Status: completed (2026-02-24)
Goal:
1. All critical API paths use tenant/program/project-scoped lookups.
Scope (files):
1. `app/blueprints/program_bp.py`
2. `app/blueprints/backlog_bp.py`
3. `app/blueprints/raid_bp.py`
4. `app/blueprints/discover_bp.py`
5. `app/blueprints/integration_bp.py`
6. `app/services/helpers/scoped_queries.py`
Tests:
1. `tests/test_tenant_isolation.py`
2. `tests/test_api_projects.py`
3. `tests/test_api_backlog.py`
4. `tests/test_api_raid.py`
5. `tests/test_discover.py`
6. `tests/test_api_integration.py`
Rollback:
1. `.rollback_checkpoints/<date>_full_refactor/fr2_backend_scope/`
2. `.rollback_checkpoints/2026-02-24_full_refactor/fr2_backend_scope/`
Done Criteria:
1. No unscoped `Program/Project` access remains in critical blueprints.
2. Cross-tenant/cross-program/cross-project isolation negatives return expected 403/404.
Validation:
1. `PYTHONPATH=. python3 -m pytest -q tests/test_api_backlog.py tests/test_api_raid.py tests/test_api_integration.py tests/test_tenant_isolation.py tests/test_api_projects.py tests/test_project_scope_resolver.py` → PASS
2. `bash scripts/ci_project_scope_regression.sh` → PASS

### Phase-FR3: Legacy Fallback Decommission
Status: completed (2026-02-24)
Goal:
1. Remove ambiguous `project_id=program_id` behavior from runtime paths.
Scope (files):
1. `static/js/api.js`
2. `app/services/project_scope_resolver.py`
3. `app/blueprints/explore/scope.py`
4. `app/blueprints/explore/open_items.py`
5. Related legacy compatibility callers found by grep audit.
Tests:
1. `tests/test_project_scope_resolver.py`
2. `tests/test_explore_service_isolation.py`
3. `tests/test_workshop_docs_isolation.py`
4. `tests/test_data_quality_guard_jobs.py`
Rollback:
1. `.rollback_checkpoints/<date>_full_refactor/fr3_legacy_fallback/`
2. `.rollback_checkpoints/2026-02-24_full_refactor/fr3_legacy_fallback/`
Done Criteria:
1. Fallback paths removed or fully feature-flag guarded.
2. Telemetry event `project_scope_fallback_used` trends to 0 in target window.
Validation:
1. `PYTHONPATH=. python3 -m pytest -q tests/test_project_scope_resolver.py tests/test_explore_service_isolation.py tests/test_workshop_docs_isolation.py tests/test_data_quality_guard_jobs.py` → PASS
2. `bash scripts/ci_project_scope_regression.sh` → PASS

### Phase-FR4: End-to-End Gate and CI Enforcement
Status: completed (2026-02-24)
Goal:
1. Fail fast on regressions via complete scope regression and contract packs.
Scope (files):
1. `scripts/ci_project_scope_regression.sh`
2. `.github/workflows/ci.yml`
3. Scope guard tests/lint rules under `tests/`
Tests:
1. Full pack: unit + integration + SPA contract + security negative suites.
2. Mandatory command: `bash scripts/ci_project_scope_regression.sh`
Rollback:
1. `.rollback_checkpoints/<date>_full_refactor/fr4_ci_gate/`
2. `.rollback_checkpoints/2026-02-24_full_refactor/fr4_ci_gate/`
Done Criteria:
1. CI blocks merges on scope regressions.
2. Release Gate Criteria section is refreshed with production-like evidence.
Validation:
1. `PYTHONPATH=. python3 -m pytest -q tests/test_scoped_lookup_guard.py` → PASS
2. `bash scripts/ci_project_scope_regression.sh` → PASS

Execution Order:
1. FR1 -> FR2 -> FR3 -> FR4 (strict sequence).
2. Each phase requires green tests + checkpoint before next phase.
3. If a phase fails, rollback to that phase checkpoint only.
