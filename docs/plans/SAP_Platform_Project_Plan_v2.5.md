# SAP Transformation Management Platform — Proje Uygulama Planı v2.6

**Versiyon:** 2.6
**Tarih:** 13 Şubat 2026
**Baz Versiyon:** v2.5 → v2.6 delta: S19–S24 tamamlandı — Platform v1.0
**Hazırlayan:** Umut Soyyılmaz
**Son Commit:** S24 (Final Polish) tamamlandı

> **📌 v2.6 Güncelleme Notları:**
> - v2.5 → v2.6 delta: S19–S24 tamamlandı — Platform v1.0 release
> - S19: AI Phase 4 — Doc Gen + Multi-turn (2 model, 8 endpoint, 88 test) → 1340 test
> - S20: AI Perf + Polish — Cache, Budget, Fallback (2 model, 10 endpoint, 67 test) → 1407 test
> - S21: AI Phase 5 — Final AI Capabilities (2 model, 26 endpoint, 81 test) → 1487 test
> - S23: Mobile PWA — manifest, SW, mobile CSS, touch components (75 test) → 1562 test
> - S24: Final Polish — Query.get migration, error handlers, N+1 fix, infra (31 test) → 1593+ test
> - Toplam: 1593+ test, 103 tablo, 13 AI asistan, 455+ route, 17 blueprint
> - **Tüm sprintler tamamlandı — v1.0 release ready**

---

## 1. Yönetici Özeti

Bu plan, mevcut ProjektCoPilot prototipini baz alarak SAP Transformation Management Platform'un tam kapsamlı uygulamasını detaylandırır. Plan **7 ana Release, 28+ Sprint** üzerinden yapılandırılmıştır.

**Geliştirme Yöntemi:** Claude + GitHub Copilot + Codex Agent
**Çalışma Modeli:** Solo developer + AI araçları. Haftada 15-20 saat geliştirme kapasitesi.

---

## 2. Güncel Platform Durumu (Şubat 2026)

### ✅ Tamamlanan (Release 1 + 2 + 3)

```
TAMAMLANAN
──────────
✅ Program Setup (6 model, 25 route, 36 test)
✅ Scope & Requirements (3 model, 20 route, 45 test)
✅ Backlog Workbench (5 model, 28 route, 59 test)
✅ Test Hub (17 model, 71 route, 203 test)
   ├── TS-Sprint 1: TestSuite, TestStep, TestCaseDependency, TestCycleSuite
   ├── TS-Sprint 2: TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink
   └── TS-Sprint 3: UATSignOff, PerfTestResult, TestDailySnapshot + SLA + Go/No-Go
✅ RAID Module (4 model, 30 route, 46 test)
✅ Integration Factory (5 model, 26 route, 76 test)
✅ Data Factory (5 model, 33 route, UI 1,044 satır)
✅ Reporting Engine + Export (reporting.py, export_service.py, reports.js)
✅ AI Altyapı + Phase 1 + Phase 2 (6 asistan, 5 model, 29 route, 141 test)
✅ Traceability Engine v1+v2 (Req ↔ WRICEF ↔ TestCase ↔ Defect ↔ Interface)
✅ Notification Service (in-app + email + scheduling)
✅ Explore Phase (25 model, 96 route, 871 test, 8 servis, 10 frontend modül)
✅ Workshop Module Rebuild — WR-0 (6 dosyaya split, 66 smoke test, 93 FE↔BE match)
✅ Monitoring & Observability
✅ UI-Sprint (T/F/H/G): Typography, KPI, Hierarchy, Backlog redesign
✅ FE-Sprint: Frontend Cleanup & Hardening
✅ TD-Sprint 1: Teknik Borç Temizliği (Doküman Odaklı)

TAMAMLANDI (Release 3.5 + Release 4 kısmi)           YAPILACAK
──────────────────────────────────────────           ─────────
✅ Workshop Module Rebuild (WR-0) — 12 Şub 2026     ✅ Run/Sustain (S17) — 1252 test
✅ Governance + Metrics Engine (WR-1) — 924 test     ✅ AI Phase 4: Doc Gen + Multi-turn (S19) — 1340 test
✅ Audit + Traceability Layer (WR-2) — 948 test      ✅ AI Phase 5 (S20→S21) — 1487 test
✅ Demo Flow UI (WR-3) — 969 test                    🚭 Dış Entegrasyonlar (S22a/S22b) — İPTAL
✅ Cutover Hub + Hypercare (S13) — 1046 test         ✅ Mobile PWA (S23) — 1562 test
✅ CI/CD + Security Hardening (S14) — 1046 test      ✅ Final Polish v1.0 (S24) — 1593+ test
✅ AI Phase 3: Cutover AI + Minutes (S15) — 1102 test
✅ Notification + Scheduling (S16) — 1183 test
```

### 📊 İlerleme Metrikleri

```
DB Tabloları:    █████████████████████████ 103/103  (%100) ✅
API Route:       █████████████████████████ 455+/200+ (%228 — hedef aşıldı!) ✅
AI Asistanlar:   █████████████████████████ 13/13    (%100) ✅
Modüller:        █████████████████████████ 17/17    (%100) ✅
Testler:         1593+ passed, 2 skipped, 15 deselected, 1 xfail ✅
Smoke Test:      66 passed, 0 failed (Explore E2E)
Test/Route:      3.5 ortalama (hedef: 3.0) ✅
```

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
| S9.5: Tech Debt & Hardening | ✅ | P1-P10, monitoring, Gemini provider |
| Explore Phase (plan dışı) | ✅ | 25 model, 96 route (6 dosyaya split), 871 test, 8 servis, 10 frontend modül |
| TS-Sprint 1-3 | ✅ | +12 tablo, +43 route, UAT/SLA/Go-NoGo |
| S10: Data Factory | ✅ | 5 model, 33 route |
| S11: Reporting Engine | ✅ | KPI aggregation, export |
| S12a: AI Phase 2a | ✅ | Risk Assessment, Test Case Gen, Change Impact |

---

## 4. 🆕 Release 3.5: Workshop Stabilization + Governance + Productization

> **Neden eklendi:** Explore Phase (25 model, 66 route) hızla inşa edildi ancak 7 critical bug, monolitik blueprint (3,671 satır, 95 endpoint), ve frontend field mapping hataları tespit edildi. Release 4'e geçmeden önce bu modülün stabilize edilmesi ve üstüne governance katmanı eklenmesi gerekiyor.
>
> **Strateji:** Hybrid yaklaşım — Copilot'un güvenli backend split'i + Claude'un frontend rebuild'i + governance/metrics katmanı

### KESİN KORUMA — Dokunulmayacak Dosyalar

| Dosya | Neden |
|-------|-------|
| `app/models/explore.py` (15 model) | Sağlam, tüm FK/relationship'ler doğru |
| `app/models/backlog.py` | BacklogItem + ConfigItem conversion hedefi |
| `app/services/requirement_lifecycle.py` | transition, convert, batch — çalışıyor |
| `app/services/open_item_lifecycle.py` | transition, reassign — çalışıyor |
| `app/services/fit_propagation.py` | propagate, recalculate — çalışıyor |
| `app/services/permission.py` | RBAC — çalışıyor |
| `app/services/signoff.py` | L3 signoff — çalışıyor |
| `app/services/code_generator.py` | Auto-code gen — çalışıyor |
| `app/services/cloud_alm.py` | ALM sync — çalışıyor |
| `app/services/workshop_docs.py` | Doc generation — çalışıyor |
| `app/services/snapshot.py` | Snapshot capture — çalışıyor |

---

### Sprint WR-0: Hybrid Workshop Rebuild — ✅ TAMAMLANDI (12 Şubat 2026)

> **Yaklaşım:** Faz 1-2 Copilot cerrahi split, Faz 3-5 Claude rebuild
> **Kaynak doküman:** HYBRID_REBUILD_PLAN.md
> **Gerçek süre:** ~40h (plan: 55h — %27 erken tamamlandı)

| # | Task | Açıklama | Katman | Est. | Durum | Gerçek Sonuç |
|---|------|----------|--------|:----:|:-----:|--------|
| WR-0.1 | Backend Split F1-1 | `__init__.py` + `workshops.py` (25 endpoint) | Backend | 4h | ✅ | 25 endpoint (plan: 23), import OK |
| WR-0.2 | Backend Split F1-2 | `process_levels.py` (21 endpoint) | Backend | 4h | ✅ | 21 endpoint (plan: 20), import OK |
| WR-0.3 | Backend Split F1-3 | `process_steps.py` + `requirements.py` (24 endpoint) | Backend | 4h | ✅ | 24 endpoint (plan: 20), import OK |
| WR-0.4 | Backend Split F1-4 | `open_items.py` + `supporting.py` + eski dosya sil | Backend | 5h | ✅ | 26 endpoint, eski `explore_bp.py` silindi |
| WR-0.5 | Lifecycle Enhancement F2-1 | Quality gate warnings, reopen enhancement, delta code gen | Backend | 5h | ✅ | Complete→warnings array, reopen→reason zorunlu, delta→suffix code |
| WR-0.6 | Items Enhancement F2-2 | Code gen (DEC/OI/REQ), approve guard, WRICEF mapping | Backend | 5h | ✅ | DEC-/OI-/REQ- code gen, 409 blocking OI, convert type mapping |
| WR-0.7 | Error Response Standardization | Tüm explore endpoint'lerde standart hata formatı | Backend | 3h | ⚠️ | `{"error": "msg"}` + HTTP codes tutarlı; `code` alanı eklenmedi → **WR-1'e taşındı** |
| WR-0.8 | Workshop Detail UI F3-1 | Core: fetchAll, steps, fit, transitions (sıfırdan) | Frontend | 8h | ✅ | 1,173 satır yeniden yazıldı, fetchAll→/full, KPI strip |
| WR-0.9 | Workshop Detail UI F3-2 | Tabs: decisions, OI, req, agenda, attendees, delta | Frontend | 6h | ✅ | 7 tab (steps, decisions, OI, req, fit, agenda, attendees) |
| WR-0.10 | Frontend API Fix F4-1 | `explore-api.js` route düzeltmeleri | Frontend | 3h | ✅ | 225 satır, ~78 API method, 17 resource group |
| WR-0.11 | View Fixes F4-2 | `explore_requirements.js` + `explore_workshops.js` field fix | Frontend | 3h | ✅ | Field adları canonical, 763 + 527 satır |
| WR-0.12 | Smoke Test F5-1 | E2E test + JS syntax + cross-check | QA | 5h | ✅ | 66 passed/0 failed, 93 FE↔BE match, DELETE handler eklendi |

**WR-0 Sonuç: 11/12 tam, 1 kısmi (WR-0.7 → WR-1'e taşındı)**

**Sprint WR-0 Gerçek Yapı:**
```
app/blueprints/explore/           (3,825 satır toplam)
├── __init__.py              # Blueprint registration (18 satır)
├── workshops.py             # 25 endpoint — CRUD + DELETE + lifecycle + attendees + agenda + decisions (985 satır)
├── process_levels.py        # 21 endpoint — Scope hierarchy, signoff, readiness, BPMN (922 satır)
├── process_steps.py         # 9 endpoint  — Steps + fit decisions + propagation + flags (357 satır)
├── requirements.py          # 15 endpoint — Req CRUD + transitions + conversion + ALM + docs (624 satır)
├── open_items.py            # 8 endpoint  — OI CRUD + transitions + reassign (361 satır)
└── supporting.py            # 18 endpoint — Health, deps, attachments, docs, snapshots (558 satır)

static/js/                        (2,688 satır toplam)
├── explore-api.js           # 78 API method, 17 resource group (225 satır)
└── views/
    ├── explore_workshop_detail.js  # Sıfırdan yazıldı (1,173 satır)
    ├── explore_workshops.js        # Field fix (527 satır)
    └── explore_requirements.js     # Field fix (763 satır)
```

**Eski dosya SİLİNDİ:** ~~`app/blueprints/explore_bp.py`~~ (3,671 satır → 0)

**DoD Doğrulaması:**
1. ✅ **96 endpoint** yeni paket yapısında çalışıyor (hedef: 95)
2. ✅ **871 test passed** (3 pre-existing fail, 2 skipped)
3. ✅ Workshop create → start → fit → complete → reopen → delta akışı sorunsuz (66/66 smoke)
4. ✅ Frontend field mapping hataları giderilmiş (93/93 FE↔BE match)
5. ✅ `DELETE /workshops/<id>` eklendi (cross-check'te keşfedildi)

**⚠️ Bilinen Pre-Existing Bug'lar (WR-0 kapsamı dışı):**
- `BacklogItem.project_id` attribute yok (`process_id` kullanıyor) → requirement convert 500
- `ProcessStep.project_id` yok → steering committee report crash (`snapshot.py:146`)
- 3 pre-existing test failure (test_matrix_with_coverage, test_matrix_uncovered_requirements, test_full_requirement_lifecycle)

---

### Sprint WR-1: Governance + Metrics Engine — ✅ TAMAMLANDI

> **Amaç:** Mevcut lifecycle servislerine dokunmadan üstüne PM governance motoru eklemek
> **Claude Revize:** Metrics scope Explore-only (testing modülü bağımlılığı kaldırıldı), RACI template eklendi

| # | Task | Açıklama | Katman | Est. | Durum | Teslim |
|---|------|----------|--------|:----:|:-----:|--------|
| WR-1.1 | Governance Rules Registry | `app/services/governance_rules.py` — 3 gate, 17 threshold, 4 RACI template | Core | 5h | ✅ | `GovernanceRules.evaluate()` çalışıyor |
| WR-1.2 | Metrics Engine (Explore-only) | `app/services/metrics.py` — 5 sub-metric + aggregator | Core | 8h | ✅ | `GET /api/v1/reports/program/{id}/health` HTTP 200 |
| WR-1.3 | Escalation/Alert Logic | `app/services/escalation.py` — alert + MD5 dedup | Core | 6h | ✅ | 3 alert tipi, dedup doğrulandı |
| WR-1.4 | Quality Gate Standardization | `complete_workshop` → `GovernanceRules.evaluate("workshop_complete")` | Core | 3h | ✅ | GOVERNANCE_BLOCK + force override |
| WR-1.5 | Error Handling Genişletme | `app/utils/errors.py` — `api_error(E.*, msg)` + 165 endpoint refactor | Core | 3h | ✅ | 11 error code, 6 explore dosyası, 0 regresyon |
| WR-1.6 | pytest: Governance + Metrics | 53 yeni test: 9 kural + 5 metrik + 3 escalation + api_error + endpoint | QA | 6h | ✅ | 53/53 pass, toplam 924 test |
| WR-1.7 | Seed: Governance demo data | Escalation alerts + threshold snapshot seed | Data | 2h | ✅ | 2 alert + 1 threshold notification |

**WR-1 Gerçekleşen Metrikler:**
- Yeni dosyalar: `governance_rules.py` (~390 satır), `metrics.py` (~389 satır), `escalation.py` (~260 satır), `utils/errors.py` (~95 satır)
- 165 error return yeniden yapılandırıldı (`api_error(E.*, msg)` formatına)
- 53 yeni test → toplam test: 924 (871 → 924)
- Sıfır regresyon (mevcut 871 test'in tamamı geçiyor)

**⚠️ Claude Revize Notları:**
- ~~Defect severity distribution (testing modülüne bağlı)~~ → **Sprint WR-3'e ertelendi** (testing modülü cross-module dependency yaratır)
- `RACI template` WR-1.1'e eklendi — governance_rules.py içinde role-based approval chain tanımı
- Metrics sadece Explore modülü verileri: gap_ratio, oi_aging, requirement_coverage, fit_distribution
- **WR-0.7'den taşınan:** Error response standardization (structured `code` alanı) → WR-1.5'te tamamlandı ✅

**Yeni dosyalar:**
```
app/services/governance_rules.py    # ~200 satır — kurallar, threshold'lar, RACI
app/services/metrics.py             # ~300 satır — KPI hesaplama
```

**DoD:**
1. ✅ Governance rules merkezi dosyadan yönetiliyor
2. ✅ `/reports/program/{id}/health` endpoint çalışıyor
3. ✅ Alert dedup ile spam engellenmiş
4. ✅ Workshop complete → governance warnings gösteriyor

---

### Sprint WR-2: Audit + Traceability — ✅ TAMAMLANDI

> **Amaç:** Kritik aksiyonlar için audit trail + E2E traceability
> **Claude Revize:** DB-per-tenant WR-4'e taşındı, traceability yeni tablo yerine mevcut FK chain traverse
> **Gerçek:** 24 yeni test (948 toplam), 0 regresyon. 3 yeni dosya, 4 dosya hook eklendi.

| # | Task | Açıklama | Katman | Est. | Bağımlılık | Teslim |
|---|------|----------|--------|:----:|------------|--------|
| WR-2.1 | ✅ AuditLog Model + API | `app/models/audit.py` (160 sat) + `app/blueprints/audit_bp.py` (90 sat) — AuditLog tablosu, write_audit(), paginated list/filter API | Data | 5h | WR-1 | `/api/v1/audit` + `/api/v1/audit/<id>` çalışıyor |
| WR-2.2 | ✅ Audit Integration | requirement_lifecycle.py, open_item_lifecycle.py, workshops.py — tüm transition'lara write_audit hook | Data | 4h | WR-2.1 | requirement/OI/workshop aksiyonları audit_logs'a yazılıyor |
| WR-2.3 | ✅ AI Execution Log | gateway.py _log_audit → general audit_logs bridge. prompt_name/model/tokens/cost diff_json'da | Data | 4h | WR-2.1 | AI çağrıları hem ai_audit_logs hem audit_logs'ta |
| WR-2.4 | ✅ Traceability Service | traceability.py'ye trace_explore_requirement() eklendi (~160 sat). FK chain traverse, yeni tablo YOK | Core | 4h | WR-1 | `/api/v1/trace/requirement/{id}` çalışıyor |
| WR-2.5 | ✅ pytest: Audit + Trace | `tests/test_audit_trace.py` — 24 test (6 sınıf: AuditModel, AuditAPI, AuditIntegration, AIExecLog, TraceService, TraceAPI) | QA | 4h | WR-2.1-4 | 24 test, 0 regresyon |
| WR-2.6 | ✅ Seed: Audit demo data | seed_demo_data.py Section 16 — req/OI/workshop/AI audit kayıtları | Data | 2h | WR-2.2 | ~16 demo audit kaydı |

**WR-2 Toplam: ~23h** (~5 iş günü)

**⚠️ Claude Revize Notları:**
- ~~DB-per-tenant (S2-1)~~ → **WR-4'e taşındı** — pilot'a kadar tek DB yeterli, izolasyon productization aşamasında
- ~~Yeni relation tablosu (S2-4)~~ → **Servis tabanlı** — mevcut FK'lar zaten var:
  ```
  ExploreRequirement → BacklogItem (explore_requirement_id FK)
  ExploreRequirement → ConfigItem (explore_requirement_id FK)
  RequirementOpenItemLink (requirement ↔ OI)
  BacklogItem → TestCase (backlog_item_id FK in testing)
  TestCase → Defect (test_case_id FK in defects)
  ```
  `traceability.py` bu chain'i traverse eder, yeni tablo gereksiz.

**Yeni dosyalar:**
```
app/models/audit.py                 # 160 satır — AuditLog model + write_audit()
app/blueprints/audit_bp.py          # 90 satır — Audit list/filter + Trace endpoint
tests/test_audit_trace.py           # 24 test — 6 sınıf
```

**Değiştirilen dosyalar:**
```
app/__init__.py                     # audit model + blueprint kayıt
app/services/requirement_lifecycle.py  # write_audit hook
app/services/open_item_lifecycle.py    # write_audit hook
app/blueprints/explore/workshops.py    # write_audit (complete + reopen)
app/ai/gateway.py                      # general audit bridge
app/services/traceability.py           # +160 satır trace_explore_requirement()
scripts/data/seed/seed_demo_data.py              # Section 16: audit demo data
```

**DoD:**
1. ✅ Kritik aksiyonlar audit log'a yazılıyor
2. ✅ AI çağrıları loglanıyor (prompt, version, tokens)
3. ✅ Requirement → WRICEF → Test → Defect trace görülebilir
4. ✅ Yeni model eklenmedi (traceability için), audit için 1 tablo eklendi

---

### Sprint WR-3: Demo Flow UI — ~40h (8 gün)

> **Amaç:** Partner demo'da "ürün gibi" görünsün, rol bazlı akışlar net olsun
> **Claude Revize:** Mevcut dashboard korunur, ayrı Executive Cockpit eklenir, testing metrics bu sprint'te eklenir

| # | Task | Açıklama | Katman | Est. | Bağımlılık | Teslim |
|---|------|----------|--------|:----:|------------|--------|
| WR-3.1 | ~~Role-Based Navigation~~ | permission.py → UI'da buton disable/hide | UI | 6h | WR-1 | ✅ TAMAMLANDI — role-nav.js + user-switcher + /user-permissions endpoint |
| WR-3.2 | ~~Executive Cockpit (YENİ sayfa)~~ | Gap ratio, OI aging, coverage, risk score — tek ekran | UI | 8h | WR-1.2 | ✅ TAMAMLANDI — executive_cockpit.js + sidebar + 3 Chart.js grafik |
| WR-3.3 | ~~Metrics: Testing Module Bridge~~ | Defect severity, test coverage metriklerini metrics.py'ye ekle | Core | 5h | WR-1.2 | ✅ TAMAMLANDI — compute_testing_metrics() + health entegrasyonu |
| WR-3.4 | ~~Demo Flow: Workshop → Req → Convert~~ | 3 ekranın kesintisiz akışı | UI | 8h | WR-0 | ✅ TAMAMLANDI — demo-flow.js + breadcrumb bar + sessionStorage state |
| WR-3.5 | ~~Demo Flow: Traceability View~~ | Requirement seç → bağlı WRICEF/Test/Defect görüntüle | UI | 6h | WR-2.4 | ✅ TAMAMLANDI — trace-view.js + modal + chain graph |
| WR-3.6 | ~~Demo Polish~~ | Loading states, error handling, transition animations | UI | 4h | WR-3.4 | ✅ TAMAMLANDI — CSS animations, focus rings, skeleton pulse |
| WR-3.7 | ~~E2E Demo Test~~ | Demo akışını baştan sona test et, screenshot listesi | QA | 3h | WR-3.4 | ✅ TAMAMLANDI — 20 test (5 sınıf), 969 toplam test |

**WR-3 Toplam: ~40h** (~8 iş günü)

**⚠️ Claude Revize Notları:**
- ~~Program Cockpit (S3-2) mevcut dashboard'la çakışma~~ → **Ayrı route/sayfa** olarak ekleniyor
  - `explore_dashboard.js` = operasyonel (PM günlük kullanır) — **DOKUNULMAZ**
  - Yeni `executive_cockpit.js` = executive (partner/investor görür)
- Testing modülü metrikleri WR-1'den ertelenerek **WR-3.3'te** ekleniyor (doğal bağlam: demo akışında gösterilecek)

**DoD:**
1. ✅ Rol bazlı UI kontrolleri çalışıyor — role-nav.js + user-switcher + 7 demo kullanıcı
2. ✅ Executive Cockpit tek sayfada tüm KPI'ları gösteriyor — 5 area RAG + 3 Chart.js grafik
3. ✅ Workshop → Requirement → Convert → Trace akışı 10 dk demo'da kesintisiz — DemoFlow controller + breadcrumb
4. ✅ Testing metrikleri health endpoint'e entegre — compute_testing_metrics() + RAG logic
5. ✅ 20 E2E test (5 sınıf) — toplam 969 test geçiyor
6. ✅ Bugfix: code_generator.py BacklogItem.program_id uyumluluğu düzeltildi

---

### Sprint WR-4: Productization + Pilot Readiness — ✅ TAMAMLANDI

> **Amaç:** Demo + pilot onboarding + yatırım anlatısı hazır
> **Claude Revize:** DB-per-tenant buraya taşındı (pilot'a yakın zamanda)
> **Durum:** ✅ 7/7 task tamamlandı — Release 3.5 GATE GEÇTİ

| # | Task | Açıklama | Katman | Est. | Bağımlılık | Teslim | Durum |
|---|------|----------|--------|:----:|------------|--------|-------|
| WR-4.1 | DB-per-Tenant Strategy | Her pilot müşteri için ayrı DB, ENV config, docker-compose | Infra | 5h | WR-2 | Müşteriler arası veri izolasyonu | ✅ |
| WR-4.2 | Migration Script | Yeni tablolar (AuditLog) tenant DB'lerde oluşur | Infra | 2h | WR-4.1 | Tüm tenant DB'leri consistent | ✅ |
| WR-4.3 | Demo Seed Script | OTC/PTP örnek verisi — `make seed-demo` | Data | 5h | WR-3 | 3 dk'da demo hazır | ✅ |
| WR-4.4 | Pilot Onboarding Runbook | DB oluştur → ENV set → admin user → seed (opsiyonel) | Doküman | 3h | WR-4.1 | 1 sayfalık onboarding checklist | ✅ |
| WR-4.5 | Demo Script | Partner demo için adım adım senaryo (10 dk) | Doküman | 3h | WR-3.7 | Demo senaryosu hazır | ✅ |
| WR-4.6 | Investor Pitch Deck | Problem → Solution → Architecture → Market → Revenue | Doküman | 6h | WR-3.2 | 10 dk pitch + 10 dk live demo | ✅ |
| WR-4.7 | Release 3.5 Gate Check | Tüm testler, demo akışı, doküman kontrolü | QA | 3h | WR-4.1-6 | Release 3.5 GATE ✅ | ✅ |

**WR-4 Toplam: ~27h** (~6 iş günü)

**WR-4 Teslim Edilen Artefaktlar:**
1. `app/tenant.py` — Multi-tenant engine (resolve, registry, URI builder)
2. `scripts/manage_tenants.py` — CLI tenant CRUD (list, create, remove, init, seed, status)
3. `tenants.json` — Tenant registry (default tenant)
4. `docker/docker-compose.tenant.yml` — Multi-tenant production compose
5. `docker/init-tenant-dbs.sh` — PostgreSQL entrypoint for tenant DB creation
6. `scripts/data/migrate/migrate_tenants.py` — Tenant migration + schema verification (84 tablo)
7. `scripts/data/seed/seed_quick_demo.py` — Quick OTC+PTP demo seed (8 faz, ~700 satır)
8. `docs/stakeholder-assets/pilot_onboarding.md` — Pilot onboarding runbook (7 adım checklist)
9. `docs/stakeholder-assets/partner_demo_script_10min.md` — 10 dk partner demo senaryosu
10. `docs/stakeholder-assets/investor_pitch.md` — Investor pitch (10 slide + appendix)

**Release 3.5 Gate Check Sonuçları:**
- Testler: 969 passed, 2 failed (pre-existing traceability matrix), 2 skipped, 1 xfailed
- Demo seed: 8/8 faz başarılı (program, process, workshop, req, backlog, test, RAID, audit)
- Tüm dokümanlar: onboarding, demo script, investor pitch oluşturuldu

**DoD:**
1. ✅ `make seed-demo` → 3 dk'da demo environment hazır
2. ✅ Pilot onboarding 1 sayfalık checklist ile yapılabilir
3. ✅ 10 dk partner demo + 10 dk investor pitch hazır
4. ✅ DB-per-tenant izolasyonu test edilmiş

---

### Release 3.5 Özet

| Sprint | Task | Est. | Kümülatif |
|--------|:----:|:----:|:---------:|
| WR-0: Hybrid Rebuild | 12 | ~55h | 55h |
| WR-1: Governance + Metrics | 7 | ~32h | 87h |
| WR-2: Audit + Traceability | 6 | ~23h | 110h |
| WR-3: Demo Flow UI | 7 | ~40h | 150h |
| WR-4: Productization | 7 | ~27h | **~177h** ← Release 3.5 toplam yeni effort (yeni) |

**Tahmini süre:** ~36 iş günü = **~7-8 hafta** (@ 5h/gün, 5 gün/hafta)

**Linear Build Mode — Her sprint sonunda demo yapılabilir:**
```
WR-0 bitti → Workshop tek başına demo yapılabilir ✅
WR-1 bitti → Governance anlatılabilir ✅
WR-2 bitti → Audit trail + trace gösterilebilir ✅
WR-3 bitti → Partner demo-ready ✅
WR-4 bitti → Pilot onboard + Investor pitch ready ✅
```

---

## 5. Release 4-6: Mevcut Plan (Güncellenmiş Bağımlılıklar)

> Release 4-6 yapısı v2.1 ile aynıdır. Tek değişiklik: **bağımlılıklar Release 3.5'e güncellendi.**

### Release 4: GoLive Readiness (S13-S16)

| Sprint | Açıklama | Est. | Bağımlılık | Durum |
|--------|----------|:----:|------------|:-----:|
| **S13: Cutover Hub + Hypercare** | 8 model, ~45 endpoint, 79 test, 5-tab SPA, 71 seed | 20h | WR-4 | ✅ |
| **S14: CI/CD + Security Hardening** | GitHub Actions, Docker, CSP/HSTS, rate limiting | 25h | S13 | ✅ |
| **S15: AI Phase 3** | CutoverOptimizer, MeetingMinutesAssistant, 4 prompt YAML, 56 test | 20h | S14 | ✅ |
| **S16: Notification + Scheduling** | 3 model, ~19 endpoint, 81 test, email service, scheduler | 16h | S14 | ✅ |

**Release 4 Gate: ✅ GEÇTİ** — 1183 test, 94 tablo, 8 AI asistan, 390+ route

---

#### S13: Cutover Hub + Hypercare — ✅ TAMAMLANDI

> **Amaç:** SAP Go-Live sürecini yöneten Cutover Hub + Hypercare modülü
> **Gerçekleşen:** 8 model, ~45 endpoint, 79 test, 5-tab SPA, 71 seed kaydı

**Domain Modeli (8 tablo):**

| Model | Tablo | Kolon | Açıklama |
|-------|-------|:-----:|----------|
| `CutoverPlan` | `cutover_plans` | 16 | Program-scoped plan. Lifecycle: draft→approved→rehearsal→ready→executing→completed→rolled_back |
| `CutoverScopeItem` | `cutover_scope_items` | 8 | Kategori bazlı gruplama. Status: computed from children |
| `RunbookTask` | `runbook_tasks` | 22 | Runbook satırı — sequence, timing, RACI, rollback, cross-domain link |
| `TaskDependency` | `task_dependencies` | 5 | Predecessor→Successor + lag. Cycle detection via DFS |
| `Rehearsal` | `rehearsals` | 18 | Dry-run kayıtları — timing variance, findings |
| `GoNoGoItem` | `go_no_go_items` | 10 | Readiness checklist (7 standart item auto-seed) |
| `HypercareIncident` | `hypercare_incidents` | 14 | Post-go-live incident tracking — severity, SLA, resolution |
| `HypercareSLA` | `hypercare_slas` | 12 | SLA definition + compliance tracking |

**Teslim Edilen Dosyalar:**
```
app/models/cutover.py              # 8 model, ~1200 LOC
app/blueprints/cutover_bp.py       # ~45 endpoint, ~1400 LOC
app/services/cutover_service.py    # Code gen, metrics, Go/No-Go aggregation, ~500 LOC
static/js/views/cutover.js         # 5-tab SPA (Plans, Runbook, Rehearsals, Go/No-Go, Hypercare)
tests/test_api_cutover.py          # 79 test (CRUD, lifecycle, deps, cycle detect, rehearsal, Go/No-Go, hypercare)
scripts/seed_data/cutover.py       # 71 demo records
```

**DoD:** ✅ 1046 test passed (79 new + 967 existing), 0 regresyon

---

#### S14: CI/CD + Security Hardening — ✅ TAMAMLANDI

> **Amaç:** Production-grade CI/CD pipeline ve güvenlik katmanı
> **Gerçekleşen:** GitHub Actions 4-job CI, multi-stage Docker, security headers, rate limiting

**Teslim Edilen Dosyalar:**
```
.github/workflows/ci.yml           # 4-job pipeline: lint → test → Docker build → deploy
docker/Dockerfile                   # Multi-stage optimized build
app/middleware/security_headers.py  # CSP, HSTS, X-Frame-Options, X-Content-Type-Options
app/middleware/rate_limiter.py      # Per-blueprint rate limits (disabled in TESTING)
scripts/infrastructure/deploy.sh                   # Production deployment script
Procfile                            # Heroku/Railway deployment
ruff.toml                           # Linter configuration
```

**DoD:** ✅ 1046 test passed, 0 regresyon, CI pipeline functional

---

#### S15: AI Phase 3 — Cutover AI + Meeting Minutes — ✅ TAMAMLANDI

> **Amaç:** Cutover optimizasyonu ve toplantı tutanağı AI asistanları
> **Gerçekleşen:** 2 yeni asistan, 4 prompt YAML, 4 endpoint, 56 test

**Yeni AI Asistanlar:**

| Asistan | Dosya | Metotlar | Açıklama |
|---------|-------|----------|----------|
| `CutoverOptimizer` | `app/ai/assistants/cutover_optimizer.py` (~470 LOC) | `optimize_runbook()`, `assess_go_nogo()` | Critical path analizi, bottleneck tespiti, Go/No-Go readiness |
| `MeetingMinutesAssistant` | `app/ai/assistants/meeting_minutes.py` (~290 LOC) | `generate_minutes()`, `extract_actions()` | Yapılandırılmış toplantı tutanağı, aksiyon çıkarma |

**Yeni Prompt YAML'lar:**
```
ai_knowledge/prompts/cutover_optimizer.yaml   # Runbook optimization prompt
ai_knowledge/prompts/cutover_gonogo.yaml      # Go/No-Go readiness assessment
ai_knowledge/prompts/meeting_minutes.yaml     # Meeting minutes generation
ai_knowledge/prompts/meeting_actions.yaml     # Action item extraction
```

**Yeni Endpoint'ler (ai_bp.py):**
- `POST /api/v1/ai/cutover/optimize/<plan_id>` — Runbook optimization
- `POST /api/v1/ai/cutover/go-nogo/<plan_id>` — Go/No-Go assessment
- `POST /api/v1/ai/meeting-minutes/generate` — Meeting minutes generation
- `POST /api/v1/ai/meeting-minutes/extract-actions` — Action item extraction

**Test:** `tests/test_ai_phase3.py` — 56 test (8 sınıf)

**DoD:** ✅ 1102 test passed (56 new + 1046 existing), 0 regresyon, 8 AI asistan toplam

---

#### S16: Notification + Scheduling — ✅ TAMAMLANDI

> **Amaç:** Gelişmiş bildirim yönetimi, email servis altyapısı, zamanlanmış görevler
> **Gerçekleşen:** 3 model, ~19 endpoint, 81 test, email service, scheduler service, 6 scheduled job

**Domain Modeli (3 yeni tablo → 94 toplam):**

| Model | Tablo | Kolon | Açıklama |
|-------|-------|:-----:|----------|
| NotificationPreference | notification_preferences | 8 | Kullanıcı bildirim tercihleri (kanal, digest frekansı) |
| ScheduledJob | scheduled_jobs | 14 | Zamanlanmış görev kayıtları (cron/interval config, run stats) |
| EmailLog | email_logs | 11 | Email gönderim audit log (template, status, error) |

**Servisler:**

| Dosya | LOC | Açıklama |
|-------|:---:|----------|
| `app/services/email_service.py` | ~280 | 4 HTML template (notification_alert, daily/weekly_digest, overdue_alert), SMTP + dev-mode |
| `app/services/scheduler_service.py` | ~210 | Decorator-based job registry, DB persistence, thread execution |
| `app/services/scheduled_jobs.py` | ~300 | 6 concrete job: overdue_scanner, escalation_check, daily/weekly_digest, stale_cleanup, sla_compliance |

**Blueprint:** `app/blueprints/notification_bp.py` — ~330 satır, ~19 endpoint:
- Notification CRUD: create, get, delete, broadcast, stats
- Preferences: list, upsert, bulk update, delete
- Scheduler: list jobs, get status, trigger, toggle
- Email logs: list, filter, stats

**Test:** `tests/test_notification_scheduling.py` — 81 test (12 sınıf)

**DoD:** ✅ 1183 test passed (81 new + 1102 existing), 0 regresyon, Release 4 tamamlandı

### Release 5: Operations (S17-S20)

| Sprint | Açıklama | Est. | Bağımlılık | Durum |
|--------|----------|:----:|------------|:-----:|
| S17: Run/Sustain | Hypercare exit, KT, handover, stabilization | 18h | S16 ✅ | ✅ |
| S19: AI Phase 4 | Doc Gen + Multi-turn | 22h | S15 | ✅ |
| S20: AI Perf + Polish | Performance optimization | 20h | S19 | ✅ |

### Release 6: Advanced (S21-S24)

| Sprint | Açıklama | Est. | Bağımlılık | Durum |
|--------|----------|:----:|------------|:-----:|
| S21: AI Phase 5 | Final AI capabilities | 41h | S20 | ✅ |
| ~~S22a: Ext Integrations P1~~ | ~~Jira + Cloud ALM~~ | ~~36h~~ | ~~S14~~ | 🚫 İPTAL |
| ~~S22b: Ext Integrations P2~~ | ~~ServiceNow + Teams~~ | ~~20h~~ | ~~S22a~~ | 🚫 İPTAL |
| S23: Mobile PWA | Progressive web app | 18h | S17 ✅ | ✅ |
| S24: Final Polish | Platform v1.0 release | 20h | All | ✅ |

---

## 6. Bağımlılık Zinciri (Critical Path — v2.3 Güncellenmiş)

```
COMPLETED                     RELEASE 3.5 (✅)                       RELEASE 4+
─────────                     ─────────────────                      ──────────

R1-R3 ──→ WR-0 (Rebuild) ──→ WR-1 (Governance) ──→ WR-2 (Audit) ──→ S13 (Cutover) ✅
          ✅ COMPLETED         │                      │                │
                               ├─→ WR-3 (Demo UI) ←──┘                ├──→ S14 (CI/CD) ✅ ──→ S16 (Notif) ✅ ──→ S17 ✅ ──→ S23
                               │                                      │            (S22a/S22b İPTAL EDİLDİ)
                               └─→ WR-4 (Product) ─── WR-3            └──→ S15 (AI P3) ✅ ──→ S19 (AI P4) ✅ ──→ S20 ✅ ──→ S21
                                    │
                                    └──→ RELEASE 3.5 GATE ✅ ──→ S13 ✅
```

> **Critical Path:** ~~WR-0 → ... → S13~~ → ✅ → ~~S16~~ ✅ → ~~S17~~ ✅ → S23 (platform track) | ~~S19~~ ✅ → ~~S20~~ ✅ → S21 (AI track)
> **S22a/S22b İPTAL EDİLDİ** — Dış entegrasyonlar (Jira, Cloud ALM, ServiceNow, Teams) kapsam dışı bırakıldı. S23 bağımlılığı S17'ye güncellendi.
> **Sonraki Adım:** S23 (Mobile PWA) — S17'ye bağımlı, S17 tamamlandı ✅. S21 tamamlandı ✅

---

## 7. Güncellenmiş Zaman Çizelgesi

```
2026
FEB           MAR           APR           MAY           JUN
 │             │             │             │             │
 ├── WR-0 ────┤             │             │             │   Workshop Rebuild (~2 hafta)
 │        ├── WR-1 ───┤     │             │             │   Governance + Metrics (~1.5 hafta)
 │             │  ├── WR-2 ─┤             │             │   Audit + Trace (~1 hafta)
 │             │       ├── WR-3 ────┤     │             │   Demo Flow UI (~1.5 hafta)
 │             │             │ ├── WR-4 ──┤             │   Productization (~1 hafta)
 │             │             │        │                 │
 │             │             │        ├── R3.5 GATE ──┤ │
 │             │             │             │             │
 │             │             │             │ ├── S13 ───┤│   Cutover Hub
 │             │             │             │        ├── S14   Security + CI
 │             │             │             │             │

JUL           AUG           SEP           OCT           NOV           DEC
 │             │             │             │             │             │
 ├── S15 ─────┤             │             │             │             │   AI Phase 3
 │        ├── S16 ────┤     │             │             │             │   AI Risk Sentinel
 │             │             │             │             │             │
 │             ├── R4 GATE ─┤             │             │             │
 │             │             │             │             │             │
 │             │        ├── S17 ────┤      │             │             │   Run/Sustain
 │             │             │ ├── S18 ───┤│             │             │   Celery + Async
 │             │             │        ├── S19 ✅───┤     │             │   AI Phase 4
 │             │             │             │  ├── S20 ──┤│             │   AI Polish
 │             │             │             │             │             │
 │             │             │             │  ├── R5 GATE┤             │
 │             │             │             │             │             │
 │             │             │             │        ├── S21 ────┤      │   AI Phase 5
 │             │             │             │             │ ├── S22a ──┤│   🚫 İPTAL
 │             │             │             │             │        ├ S22b   🚫 İPTAL
 │             │             │             │             │         ├ S23   Mobile PWA
 │             │             │             │             │          S24│   Final Polish
 │             │             │             │             │             │
 ▼             ▼             ▼             ▼             ▼         ⭐ R6 = Platform v1.0
```

---

## 8. Effort Özeti (v2.2 Revize)

| Release | Sprint'ler | Platform | AI | TD | Toplam | Haftalık |
|---------|-----------|:--------:|:--:|:--:|:------:|:--------:|
| R1: Foundation | S1-S4 | 109h | 0 | — | 109h | ~14h |
| R2: Testing+AI | S5-S8 | 55h | 57h | — | 112h | ~14h |
| R3: Delivery+AI | S9-S12 + TS + TD | 51h | 30h | 50h | 131h | ~11h |
| **R3.5: WS Rebuild+Gov** | **WR-0→WR-4** | **~140h** | **0** | **~37h** | **~177h** | **~23h** ⚠️ |
| R4: GoLive+AI | S13-S16 | 37h | 45h | 8h | 90h | ~11h |
| R5: Operations | S17-S20 | 34h | 42h | — | 76h | ~10h |
| R6: Advanced | S21,S23,S24 | 20h | 41h | — | 61h | ~8h |
| ~~S22a/S22b~~ | ~~İPTAL~~ | ~~-56h~~ | — | — | ~~-56h~~ | — |
| **TOPLAM** | | **446h** | **215h** | **95h** | **~756h** | — |

> **v2.1→v2.2 delta:** +177h (Release 3.5 eklenmesi)
> **⚠️ R3.5 haftalık yükü 23h** — normal kapasitenin (15-20h) üstünde. 8 hafta olarak planlanmış ama 9-10 haftaya uzayabilir.

---

## 9. Başarı Metrikleri (v2.4)

| Metrik | R3 Gerçek | R3.5 Gerçek | R4 Gerçek (S13-S16) | R5 Hedef | R6 Hedef |
|--------|:---------:|:----------:|:-------------------:|:--------:|:--------:|
| API route | 336 | 345+ | 390+ | 420+ | 500+ |
| DB tablo | 77 | 78+ | 94 | 96+ | 95+ |
| Pytest | 916 | 969 | 1183 | 1300+ | 1300+ |
| AI asistan | 6 | 6 | 8 | 11 | 14 |
| Test/route | 2.7 | 2.8 | 3.0 ✅ | 3.0 | 3.0+ |
| CI/CD | ❌ | ❌ | ✅ GitHub Actions | ✅ | ✅ |
| Security | ❌ | ❌ | ✅ CSP/HSTS/Rate | ✅ | ✅ |
| Cutover Hub | ❌ | ❌ | ✅ 8 model, 5-tab | ✅ | ✅ |
| Notification | ❌ | ❌ | ✅ Email + Scheduler | ✅ | ✅ |

---

## 10. Risk Yönetimi (v2.2 Güncellenmiş)

| Risk | Olasılık | Etki | Mitigasyon |
|------|:--------:|:----:|------------|
| WR-0 backend split sırasında import bozulması | Orta | Yüksek | Her prompt sonunda 24 test + import check |
| WR-0 frontend rebuild'de field mapping hatası | Orta | Orta | Canonical field listesi prompt'larda tanımlı |
| WR-1 governance rules mevcut davranışı bozar | Düşük | Yüksek | Additive yaklaşım — mevcut response'lara field ekler |
| WR-2 AuditLog performance etkisi (her transition'da INSERT) | Düşük | Orta | Async yazma (veya batch), index optimization |
| WR-3 testing modülü cross-dependency | Orta | Orta | WR-3.3'te read-only metrik, testing modeline dokunulmaz |
| WR-4 DB-per-tenant migration consistency | Orta | Yüksek | Alembic migration her tenant DB'de test edilir |
| R3.5 genel timeline uzaması (177h / 8 hafta) | Yüksek | Orta | Buffer: 9-10 hafta gerçekçi, WR-3/4 paralelize edilebilir |
| ~~S22 56h → 2 sprint, timeline uzar~~ | — | — | 🚫 S22a/S22b İPTAL EDİLDİ — risk ortadan kalktı |
| ~~S14 JWT gecikmesi → S18/S22 blocker~~ | — | — | 🚫 S22 iptal edildi, S14 tamamlandı ✅ |
| Planlanmamış iş oranı %45-50 | Yüksek | Orta | Buffer hafta eklenmiş |

---

## 11. Sprint Gantt — Task Listesi (Copilot İçin)

```csv
Sprint,Task ID,Task Başlığı,Açıklama,Katman,Öncelik,Est.,Bağımlılık,Teslim Kriteri

Sprint WR-0,WR-0.1,Backend Split F1-1,__init__.py + workshops.py (23 endpoint),Backend,Yüksek,4h,-,Import OK + 24 test passed
Sprint WR-0,WR-0.2,Backend Split F1-2,process_levels.py (20 endpoint),Backend,Yüksek,4h,WR-0.1,Import OK + 24 test passed
Sprint WR-0,WR-0.3,Backend Split F1-3,process_steps.py + requirements.py (20 endpoint),Backend,Yüksek,4h,WR-0.1,Import OK + 24 test passed
Sprint WR-0,WR-0.4,Backend Split F1-4,open_items.py + supporting.py + switch + delete old,Backend,Yüksek,5h,WR-0.1-3,95 endpoint yeni pakette
Sprint WR-0,WR-0.5,Lifecycle Enhancement,Quality gate warnings + reopen + delta code gen,Backend,Yüksek,5h,WR-0.4,Warnings array + reopen reason
Sprint WR-0,WR-0.6,Items Enhancement,Code gen + approve guard + WRICEF mapping,Backend,Yüksek,5h,WR-0.4,DEC/OI/REQ code gen + blocking OI check
Sprint WR-0,WR-0.7,Error Standardization,Standart hata formatı tüm explore endpoint'lerde,Backend,Orta,3h,WR-0.4,error/code/details formatı
Sprint WR-0,WR-0.8,Workshop Detail Core,fetchAll + steps + fit + transitions (sıfırdan),Frontend,Yüksek,8h,WR-0.5,Workshop akışı kesintisiz
Sprint WR-0,WR-0.9,Workshop Detail Tabs,Decisions + OI + Req + Agenda + Attendees + Delta,Frontend,Yüksek,6h,WR-0.8,Tüm tablar render
Sprint WR-0,WR-0.10,Frontend API Fix,explore-api.js route düzeltmeleri,Frontend,Orta,3h,WR-0.8,Doğru route mapping
Sprint WR-0,WR-0.11,View Fixes,explore_requirements.js + explore_workshops.js,Frontend,Orta,3h,WR-0.10,Field adları canonical
Sprint WR-0,WR-0.12,Smoke Test,E2E curl + JS syntax + cross-check,QA,Yüksek,5h,WR-0.11,24 test + demo stabil

Sprint WR-1,WR-1.1,Governance Rules,governance_rules.py — threshold + RACI,Core,Yüksek,5h,WR-0,Rules merkezi
Sprint WR-1,WR-1.2,Metrics Engine,metrics.py — gap ratio + OI aging + coverage (Explore-only),Core,Yüksek,8h,WR-1.1,Health endpoint hazır
Sprint WR-1,WR-1.3,Escalation Logic,Alert üret + dedup key,Core,Yüksek,6h,WR-1.2,Notifications çalışıyor
Sprint WR-1,WR-1.4,Quality Gate Standard,Warning formatını governance'dan al,Core,Orta,3h,WR-1.1,Tutarlı uyarılar
Sprint WR-1,WR-1.5,Error Handling Ext,Governance error code'ları,Core,Düşük,2h,WR-1.1,GOVERNANCE_BLOCK/WARN
Sprint WR-1,WR-1.6,pytest: Gov + Metrics,~30 yeni test,QA,Yüksek,6h,WR-1.1-4,30 test passed
Sprint WR-1,WR-1.7,Seed: Governance,Demo threshold + alert örnekleri,Data,Orta,2h,WR-1.3,Demo'da governance görünür

Sprint WR-2,WR-2.1,AuditLog Model,Yeni tablo + CRUD API,Data,Yüksek,5h,WR-1,/audit çalışıyor
Sprint WR-2,WR-2.2,Audit Integration,Transition + convert + approve → log,Data,Yüksek,4h,WR-2.1,Kritik aksiyonlar loglu
Sprint WR-2,WR-2.3,AI Execution Log,Prompt name/version/token log,Data,Yüksek,4h,WR-2.1,AI log izlenebilir
Sprint WR-2,WR-2.4,Traceability Service,FK chain traverse (yeni tablo YOK),Core,Yüksek,4h,WR-1,/trace/requirement/{id}
Sprint WR-2,WR-2.5,pytest: Audit+Trace,~20 yeni test,QA,Yüksek,4h,WR-2.1-4,20 test passed
Sprint WR-2,WR-2.6,Seed: Audit,Demo audit kayıtları,Data,Orta,2h,WR-2.2,Audit trail görünür

Sprint WR-3,WR-3.1,Role-Based Nav,Permission → UI buton disable/hide,UI,Yüksek,6h,WR-1,Yetkisiz aksiyon gizli
Sprint WR-3,WR-3.2,Executive Cockpit,Yeni sayfa — KPI dashboard (ayrı route),UI,Yüksek,8h,WR-1.2,/cockpit çalışıyor
Sprint WR-3,WR-3.3,Testing Metrics Bridge,Defect + test coverage → metrics.py,Core,Orta,5h,WR-1.2,Health'te testing KPI
Sprint WR-3,WR-3.4,Demo Flow Screens,Workshop → Req → Convert akışı,UI,Yüksek,8h,WR-0,10 dk demo kesintisiz
Sprint WR-3,WR-3.5,Traceability View,Req → WRICEF → Test → Defect UI,UI,Yüksek,6h,WR-2.4,Trace chain görünür
Sprint WR-3,WR-3.6,Demo Polish,Loading + error + animations,UI,Orta,4h,WR-3.4,Professional look
Sprint WR-3,WR-3.7,E2E Demo Test,Screenshot + test,QA,Yüksek,3h,WR-3.4,Demo script ile screenshot

Sprint WR-4,WR-4.1,DB-per-Tenant,Ayrı DB + ENV config + docker-compose,Infra,Yüksek,5h,WR-2,✅ TAMAMLANDI — tenant.py + manage_tenants.py + tenants.json + compose
Sprint WR-4,WR-4.2,Migration Script,AuditLog etc. tenant DB'lerde,Infra,Yüksek,2h,WR-4.1,✅ TAMAMLANDI — migrate_tenants.py + verify (84 tablo)
Sprint WR-4,WR-4.3,Demo Seed Script,make seed-demo → OTC/PTP data,Data,Yüksek,5h,WR-3,✅ TAMAMLANDI — seed_quick_demo.py (8 faz)
Sprint WR-4,WR-4.4,Onboarding Runbook,1 sayfa pilot açılış prosedürü,Doküman,Yüksek,3h,WR-4.1,✅ TAMAMLANDI — docs/stakeholder-assets/pilot_onboarding.md
Sprint WR-4,WR-4.5,Demo Script,10 dk partner demo senaryosu,Doküman,Yüksek,3h,WR-3.7,✅ TAMAMLANDI — docs/stakeholder-assets/partner_demo_script_10min.md
Sprint WR-4,WR-4.6,Investor Pitch,Problem→Solution→Market→Revenue,Doküman,Yüksek,6h,WR-3.2,✅ TAMAMLANDI — docs/stakeholder-assets/investor_pitch.md
Sprint WR-4,WR-4.7,R3.5 Gate Check,Tüm test + demo + doküman,QA,Yüksek,3h,All,✅ TAMAMLANDI — 969 test passed + gate geçti
```

---

**Dosya:** `SAP_Platform_Project_Plan_v2.5.md`
**v2.3 → v2.4 delta:** S16 Notification + Scheduling (3 model, ~19 endpoint, 81 test, email service, scheduler) tamamlandı. Release 4 Gate geçti. Toplam: 1183 test, 94 tablo, 8 AI asistan
**Oluşturan:** Claude Opus 4.6
**Tarih:** 2026-02-13
