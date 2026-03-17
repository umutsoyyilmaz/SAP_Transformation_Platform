# Perga — Technical Debt Deep Analysis

**Date:** 2026-02-14  
**Scope:** SAP_Transformation_Platform (main branch)  
**Analyst:** Claude, based on full codebase review  
**Revision:** v1.2 — fact-checked and enriched with additional findings (2026-02-14)

---

## Executive Summary

The Perga codebase has **570 API routes**, **114 SQLAlchemy models**, and **26 registered blueprints**. It has evolved from a rapid prototype into a feature-rich platform, but this growth has introduced structural debt that will increasingly slow development and create reliability risks.

The debt is not catastrophic — the architecture has sound foundations (Blueprint separation, **31 service modules** in `app/services/`, modular JS frontend, well-structured explore blueprints split across 7 files). But several patterns, if left unchecked, will compound. The three most expensive debts are: **fat controllers** (915 direct db.session calls in blueprints — despite having 31 services available), **model duplication** (parallel entity hierarchies), and **incomplete RBAC rollout** (45 of 570 routes protected — 8% coverage, though Basic Auth covers all routes).

---

## Codebase Profile

| Metric | Value | Verified |
|--------|-------|:---:|
| Python (app code) | 49,749 | ✅ |
| JavaScript (frontend) | 19,345 | ✅ |
| Test code | 27,369 | ✅ |
| Model classes | 114 | ✅ |
| API routes | 570 | ✅ |
| Registered blueprints | 26 | ✅ |
| Service modules (`app/services/`) | 31 | ✅ |
| Alembic migrations | 16 | ✅ |
| Test functions | 2,162 | ✅ |

---

## Debt Category 1: Architectural — Fat Controllers

**Severity: HIGH | Impact: Every sprint | Estimated cost to fix: 80-120h**

### The Problem

Blueprints contain **915** direct `db.session` calls. Business logic lives in route handlers instead of the service layer. Only 54 service imports exist across all blueprints, meaning roughly 94% of business logic is embedded in controllers.

> **Önemli bağlam:** `app/services/` altında 31 adet service modülü zaten mevcut (ör. `requirement_lifecycle.py`, `fit_propagation.py`, `code_generator.py`, `cutover_service.py`, `traceability.py`, `permission_service.py`, `workshop_docs.py` vb.). Sorun service katmanının **yokluğu** değil, blueprint'lerin bu servisleri yeterince **kullanmamasıdır**. Altyapı hazır — sadece bağlantı eksik.

### Concrete Example: testing_bp.py

This single file is 2,755 lines with 76 routes and 172 direct `db.session` calls. It has zero service layer — every route handler does its own query building, validation, and state management inline. Compare this to the explore module where `requirement_lifecycle.py`, `fit_propagation.py`, and `code_generator.py` properly encapsulate business logic.

### Why It Matters

Every time you need to change how a test cycle is created — from a route handler, from a convert flow, from an AI assistant, from a bulk import — you're duplicating or referencing logic scattered across a 2,755-line file. Testing is harder because you can't unit-test business logic without spinning up Flask. Refactoring is riskier because route handlers are tightly coupled to database operations.

### Affected Blueprints (db.session calls)

| Blueprint | db.session calls | Has service layer? |
|-----------|:---:|:---:|
| testing_bp.py | 172 | No |
| backlog_bp.py | ~80 | Partial (traceability only) |
| cutover_bp.py | ~70 | Yes (cutover_service) |
| raid_bp.py | ~60 | Partial (notification) |
| integration_bp.py | ~55 | No |
| program_bp.py | ~50 | No |
| data_factory_bp.py | ~40 | No |
| explore/* (combined) | ~100 | Yes (multiple services) |

### Recommended Fix

Don't rewrite everything at once. Apply the "extract service on touch" rule:

1. When you next modify testing_bp.py, extract a `testing_service.py` with the business logic for that specific change
2. Gradually migrate route handlers to thin wrappers: validate input → call service → return response
3. Prioritize the modules you change most frequently
4. **Explore blueprint'i örnek alın** — `app/blueprints/explore/` zaten 7 dosyaya bölünmüş (`workshops.py`, `requirements.py`, `open_items.py`, `process_levels.py`, `process_steps.py`, `supporting.py`) ve `app/services/` altındaki servisleri aktif olarak kullanıyor. Bu yapı diğer fat controller'lar için referans mimari olarak kullanılabilir

---

## Debt Category 2: Model Duplication

**Severity: HIGH | Impact: Data integrity, traceability | Estimated cost to fix: 40-60h**

### The Problem

The codebase has parallel entity hierarchies that represent the same domain concepts:

| Concept | Model A | Model B | Overlap |
|---------|---------|---------|---------|
| Workshop | `Workshop` (scenario.py, 22 cols) | `ExploreWorkshop` (explore.py, 27 cols) | Same concept, different fields |
| Requirement | `Requirement` (requirement.py, 19 cols) | `ExploreRequirement` (explore.py, 40 cols) | ExploreReq is the superset |
| Open Item | `OpenItem` (requirement.py, 14 cols) | `ExploreOpenItem` (explore.py, 23 cols) | Same concept, different structure |

### Root Cause

This appears to be an evolutionary artifact. The original "program domain" (scenario.py, requirement.py) was built first. Then the "explore domain" (explore.py) was built as a richer, more SAP-aware version. Neither was deprecated — they coexist.

### Why It Matters

- Traceability breaks when some requirements are in `Requirement` and others in `ExploreRequirement`
- The traceability service has separate code paths (`get_chain` vs `trace_explore_requirement`) for what should be the same operation
- New developers (or AI assistants) don't know which model to use
- The `explore.py` file is 2,158 lines with 25 classes, **70 foreign keys**, and 33 relationships — it's a God Model file

### Recommended Fix

1. Decide which hierarchy is canonical (likely the Explore versions since they're richer and actively developed)
2. Mark the program-domain models as deprecated with migration path
3. Consolidate gradually — when you next touch `Requirement`, route it through `ExploreRequirement`
4. Split `explore.py` (2,158 lines) into at least 3 files: `workshop.py`, `requirement.py`, `process.py`

---

## Debt Category 3: Incomplete RBAC Rollout

**Severity: HIGH | Impact: Multi-tenant readiness | Estimated cost to fix: 20-40h**

### The Problem

Out of 570 routes, **45** have granular permission checks (via `@require_permission` or similar decorators), spread across 6 blueprint files: `admin_bp` (14), `platform_admin_bp` (9), `sso_bp` (9), `custom_roles_bp` (7), `bulk_import_bp` (3), and `scim_bp` (3). The remaining **525 routes (92%)** rely solely on Basic Auth at the HTTP level.

> **Önemli:** Bu "güvenlik açığı" değil, "RBAC tamamlanmamışlığı"dır. Tüm 570 route Basic Auth ile korunmaktadır — kimlik doğrulama olmadan hiçbir endpoint'e erişilemez. Eksik olan, kullanıcı bazlı yetkilendirme (authorization) katmanıdır. Bu, single-tenant modda kabul edilebilir bir durumdur ancak multi-tenant geçişinden önce mutlaka tamamlanmalıdır.

### What Exists But Isn't Fully Deployed

The codebase has a complete RBAC system ready to go:

- `auth.py` models: `Tenant`, `User`, `Role`, `Permission`, `RolePermission`, `UserRole`, `Session`, `ProjectMember` (8 models)
- `permission.py` service with `check_permission()` and `has_permission()`
- `permission_service.py` with role-based logic (220 lines)
- `permission_required.py` middleware with decorators
- `jwt_service.py` for token-based auth
- `PERMISSION_MATRIX` in explore.py (35 satır — 7 rol ve izin setleri)
- Merkezi hata yöneticileri `app/__init__.py`'de kayıtlı (404, 500, 405, 429)

All of this is built, tested in isolation, but not fully wired to the actual API routes.

### Recommended Fix

This needs a phased approach:

1. **Phase 1 (doğrulanmış):** Basic Auth tüm route'ları production'da kapsıyor ✅
2. **Phase 2 (before multi-tenant):** Wire `@require_permission` to the top 20 most sensitive routes (data mutation endpoints)
3. **Phase 3 (with multi-tenant launch):** Full RBAC activation with tenant isolation

---

## Debt Category 4: Code Duplication

**Severity: MEDIUM | Impact: Maintenance burden | Estimated cost to fix: 8-12h**

### Duplicated Utility Functions

| Function | Duplicate Count | Files |
|----------|:---:|-------|
| `_get_or_404()` | 8 | backlog, testing, cutover, data_factory, archive/*, integration, program |
| `_parse_date()` | 8 | explore/workshops, explore/open_items, backlog, testing, raid, archive/*, integration, program |
| `_auto_code()` | 2 | testing_bp (inline) vs code_generator.py (service) |

### Fix

Extract into a shared utils module:

```python
# app/utils/helpers.py
def get_or_404(model, pk, label="Resource"):
    obj = db.session.get(model, pk)
    if not obj:
        abort(404, description=f"{label} {pk} not found")
    return obj

def parse_date(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
```

Then replace all 16 duplicate definitions with imports. This is a safe, mechanical refactor.

---

## Debt Category 5: Dead and Archived Code

**Severity: LOW | Impact: Cognitive overhead | Estimated cost to fix: 4-6h**

### Inventory

| Item | Size | Status |
|------|------|--------|
| `app/blueprints/archive/` (3 files) | 2,068 lines | Not registered, not imported |
| `tests/archive/` (3 files) | Unknown | Tests for archived blueprints |
| `docs/archive/` (20 files) | ~8,000 lines | Superseded documentation |
| `static/js/views/prompt-g-backlog-redesign.md` | — | Prompt file in JS directory |
| `unified_traceability_prompt.md` (root) | 53K | Development prompt, not app code |

### Fix

Move archive content to a separate branch or tag. Delete from main. The git history preserves everything.

---

## Debt Category 6: Error Handling

**Severity: MEDIUM | Impact: Debugging difficulty | Estimated cost to fix: 16-24h**

### The Problem

**177** generic `except Exception` blocks across blueprints. Most follow this pattern:

```python
try:
    # business logic
    return jsonify(result), 200
except Exception as e:
    return jsonify({"error": str(e)}), 500
```

This catches everything — including programming errors like `AttributeError`, `KeyError`, and `TypeError` — and returns them as 500s with the raw error message. This means:

- Bugs are silently swallowed as "500 errors" instead of surfacing as stack traces during development
- Error messages may leak internal implementation details to clients
- No distinction between "expected" errors (validation, not found) and "unexpected" errors (bugs)

### Mevcut Durum

`app/__init__.py` içinde zaten merkezi error handler'lar kayıtlı:
- `@app.errorhandler(404)` — Not Found
- `@app.errorhandler(500)` — Internal Server Error  
- `@app.errorhandler(405)` — Method Not Allowed
- `@app.errorhandler(429)` — Rate Limit Exceeded

Ayrıca 4 blueprint-seviyesi özel exception handler mevcut (`sso_bp`, `scim_bp`, `bulk_import_bp`, `custom_roles_bp`).

### Fix

Merkezi handler zaten var — sorun blueprint'lerdeki 177 generic catch bloğunun bu handler'a ulaşmasını engellemesi. Replace generic catches with specific ones for expected error types. Let unexpected errors propagate to the already-registered central error handler:

```python
# Kötü (mevcut durum — 177 yerde):
try:
    result = do_business_logic()
    return jsonify(result), 200
except Exception as e:
    return jsonify({"error": str(e)}), 500  # Merkezi handler'ı bypass ediyor!

# İyi (hedef):
try:
    result = do_business_logic()
    return jsonify(result), 200
except ValueError as e:
    return jsonify({"error": str(e)}), 400  # Beklenen hata
# Beklenmeyen hatalar otomatik olarak merkezi handler'a düşer
```

---

## Debt Category 7: Explore Model Complexity

**Severity: MEDIUM | Impact: Onboarding, maintainability | Estimated cost to fix: 12-16h**

### The Problem

`app/models/explore.py` is **2,158 lines** containing:

- 25 model classes
- **70 foreign keys** (önceki analizde 46 olarak raporlanmıştı — gerçek sayı %52 daha fazla)
- 33 relationships
- `PERMISSION_MATRIX` sözlüğü (35 satır — 7 rol tanımı, önceki analizde yanlışlıkla "700+ satır" olarak raporlanmıştı)
- Models ranging from core domain (`ExploreWorkshop`, `ExploreRequirement`) to cross-cutting (`DailySnapshot`, `CloudALMSyncLog`, `Attachment`)

This is the definition of a God Module. Models that have nothing in common (`BPMNDiagram` and `ProjectRole`) share a file purely because they were added during the "explore phase" of development.

### Fix

Split into domain-cohesive files:

- `explore/workshop.py`: ExploreWorkshop, WorkshopScopeItem, WorkshopAttendee, WorkshopAgendaItem, WorkshopDependency, WorkshopRevisionLog, ExploreWorkshopDocument
- `explore/requirement.py`: ExploreRequirement, RequirementOpenItemLink, RequirementDependency, ExploreOpenItem, OpenItemComment, ExploreDecision
- `explore/governance.py`: ProjectRole, PhaseGate, CrossModuleFlag, ScopeChangeRequest, ScopeChangeLog, PERMISSION_MATRIX
- `explore/infrastructure.py`: ProcessStep, ProcessLevel, L4SeedCatalog, CloudALMSyncLog, Attachment, BPMNDiagram, DailySnapshot

---

## Debt Category 8: Test Quality vs Quantity

**Severity: MEDIUM | Impact: False confidence | Estimated cost to fix: ongoing**

### The Positive

**2,162** test functions is impressive — and growing (up from ~1,900 at the time of initial analysis). Tests are well-structured with proper fixtures, use in-memory SQLite, and cover API contracts.

### The Concern

The tests primarily test the happy path of API endpoints (POST returns 201, GET returns 200). Fewer tests cover:

- Business logic edge cases (what happens when you convert an already-converted requirement?)
- Data integrity across entities (does deleting a workshop cascade correctly to requirements?)
- Concurrent access patterns
- Service layer logic in isolation (because there's limited service layer — see Debt #1)

The E2E test suite (Playwright) has only 333 lines across 6 spec files — minimal coverage for a 570-route application.

### Fix

This is not a "fix it all at once" item. Instead, apply the rule: every bug that reaches production gets a regression test. Every new service function gets a unit test. Over time, coverage shifts from "can I call the API" to "does the business logic work correctly."

---

## Debt Category 9: Documentation Drift

**Severity: LOW | Impact: Onboarding confusion | Estimated cost to fix: 8-12h**

### The Problem

The project files in this Claude Project (PROGRESS_REPORT.md, HANDOVER_DOCUMENT.md, etc.) describe a fundamentally different codebase than what exists:

- Handover docs reference SQLite, monolithic index.html, raw SQL endpoints — the actual codebase uses PostgreSQL, modular JS, and SQLAlchemy ORM throughout
- SPRINT_MASTER_PLAN_V2 describes a separate FastAPI+React v2 repo — this adds confusion about which codebase is current
- The repo itself has `docs/plans/` with 12 plan documents and `docs/archive/` with 20 archived documents

The canonical documentation is unclear. Which of these 30+ documents reflects reality?

### Fix

1. Archive the Claude Project docs (PROGRESS_REPORT.md, HANDOVER_DOCUMENT.md, etc.) — they describe a past version
2. Maintain one source of truth: `docs/plans/SAP_Platform_Project_Plan_v2.5.md` (or whichever is most current)
3. Keep the Notion workspace as the living tracker, not markdown files

---

## Priority Matrix

| # | Debt Item | Severity | Effort | ROI | Fix When |
|---|-----------|----------|--------|-----|----------|
| 1 | Code duplication (16 utilities) | MEDIUM | 4-8h | **Very High** | **Hemen — en hızlı kazanım** |
| 2 | Fat controllers (915 db.session) | HIGH | 80-120h | High | Incremental, on touch |
| 3 | RBAC rollout (45/570, Basic Auth mevcut) | HIGH | 20-40h | High | Before multi-tenant |
| 4 | Model duplication (3 pairs) | HIGH | 40-60h | High | Next architecture sprint |
| 5 | Error handling (177 generic) | MEDIUM | 16-24h | Medium | Incremental |
| 6 | Explore model split (2,158 lines, 70 FKs) | MEDIUM | 12-16h | Medium | Next explore sprint |
| 7 | Traceability code path birleştirme | MEDIUM | 8-12h | Medium | Model birleştirme ile birlikte |
| 8 | Test depth | MEDIUM | Ongoing | Medium | With every bug fix |
| 9 | Dead code removal | LOW | 4-6h | Low | Any time |
| 10 | Documentation sync | LOW | 8-12h | Low | After stabilization |

**Total estimated effort:** ~200-310 hours (excluding ongoing items)

> **Öncelik değişikliği notu (v1.2):**
> - Code duplication (#1) en üste çıkarıldı — 4-8 saatte tamamlanabilir, sıfır risk, anında fayda
> - Security gap → RBAC rollout olarak yeniden adlandırıldı (Basic Auth zaten tüm route'ları koruyor)
> - Severity CRITICAL→HIGH'a düşürüldü (authentication mevcut, eksik olan authorization)
> - Traceability code path birleştirme yeni madde olarak eklendi (#7)

---

## What NOT to Fix

Some things look like debt but are actually reasonable trade-offs:

- **570 routes** — this is a lot, but each represents real SAP Activate functionality. The count itself isn't a problem; the lack of service layer behind them is.
- **16 migrations** — normal for a project of this age. Migration quality looks good.
- **Vanilla JS frontend** — the modular view system (`static/js/views/`) is well-organized. Migrating to React would not reduce debt, it would replace one kind of complexity with another.
- **Multiple API clients** (`api.js` + `explore-api.js`) — the explore API client adds type safety and domain-specific helpers. This is a reasonable separation.
- **31 service modülü** — `app/services/` altında zengin bir service katmanı mevcut. Bu bir borç değil, bir güç. Sorun service'lerin varlığında değil, blueprint'lerin bunları yeterince kullanmamasında.
- **Explore blueprint yapısı** (7 dosya) — zaten iyi modülerleştirilmiş. Diğer fat blueprint'ler için örnek mimari olarak korunmalı.
- **Merkezi error handler'lar** (404, 500, 405, 429) — zaten `app/__init__.py`'de kayıtlı. Sorun bunların yokluğu değil, blueprint'lerdeki 177 generic catch bloğunun bunları bypass etmesi.

---

## v1.2 Ek Tespitler

### Olumlu Bulgular (Dokümanda Eksik Kalan)

1. **Service katmanı düşünülenden çok daha gelişmiş** — 31 service modülü mevcut. Bu, "service layer beginnings" değil, olgun bir service altyapısıdır. Blueprint'lerin bu servisleri kullanma oranı artırılmalı.

2. **Explore blueprint iyi yapılandırılmış** — 7 dosyaya bölünmüş, service'leri aktif kullanıyor. Bu yapı diğer monolitik blueprint'ler (testing_bp, backlog_bp, integration_bp) için örnek mimari olarak kullanılabilir.

3. **Merkezi hata yönetimi mevcut** — `app/__init__.py`'de 4 HTTP hata kodu handler'ı + 4 blueprint-seviyesi özel exception handler kayıtlı. Debt #6'daki sorun merkezi handler'ın yokluğu değil, blueprint'lerdeki generic catch bloklarının bu handler'ı bypass etmesidir.

4. **PERMISSION_MATRIX kompakt ve iyi tasarlanmış** — 35 satırda 7 rol tanımı. Önceki analizlerdeki "700+ satır" iddiası yanlıştı. Bu, gerçek bir borç değil.

### Traceability Code Path Birleştirme (Yeni Tespit)

`app/services/traceability.py` (732 satır) dosyasında aynı işlem için iki ayrı kod yolu var:
- `get_chain()` (satır 43) — program-domain modelleri için
- `trace_explore_requirement()` (satır 590) — explore-domain modelleri için

Bu, Debt #2 (Model Duplication) ile doğrudan bağlantılı. Modeller birleştirildiğinde bu iki fonksiyon da tek bir izlenebilirlik zinciri haline getirilmeli.

### En Hızlı Kazanım: helpers.py

`app/utils/helpers.py` henüz oluşturulmamış. `_get_or_404()` (8 dosya) ve `_parse_date()` (8 dosya, 2'si `_parse_date_input` adıyla) toplam 16 duplicate tanımın tek bir modüle taşınması:
- **Süre:** 4-8 saat
- **Risk:** Sıfır (mekanik refactor, davranış değişikliği yok)
- **Fayda:** Anında — her blueprint'te 5-10 satır azalma, tek doğruluk kaynağı

---

## Conclusion

Perga'nın teknik borcu yönetilebilir düzeyde ama büyüyor. **En önemli bulgu: service katmanı düşünülenden çok daha güçlü (31 modül) — asıl sorun blueprint'lerin bu servisleri kullanmaması.** Bu, sorunu daha kolay çözülebilir kılıyor: sıfırdan service yazmak yerine, mevcut servislere bağlantı kurmak yeterli.

En hızlı kazanım `helpers.py` çıkarımı (4-8 saat, sıfır risk). En yüksek kaldıraçlı düzeltme, testing_bp.py ve backlog_bp.py için service extraction. RBAC rollout ise multi-tenant geçişi öncesinde tamamlanmalı — ancak Basic Auth ile tüm route'lar zaten korunduğundan bu bir "güvenlik krizi" değil, bir "yetkilendirme olgunlaştırma" çalışmasıdır.

Test coverage'daki pozitif trend (2.162 fonksiyon, başlangıçtan %15 artış) ve permission decorator'larının 6 blueprint dosyasına yayılması, ekibin doğru yönde ilerlediğini gösteriyor. Explore blueprint'in modüler yapısını diğer bileşenlere yaymak — "extract service on touch" prensibiyle — uzun vadede en yüksek getiriyi sağlayacaktır.
