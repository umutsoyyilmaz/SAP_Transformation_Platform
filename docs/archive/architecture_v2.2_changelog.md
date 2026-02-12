# Architecture Document — v1.3 → v2.2 Changelog

**Kaynak:** `sap_transformation_platform_architecture (2).md` (v1.3, 2255 LOC)  
**Hedef:** v2.2  
**Hazırlayan:** GitHub Copilot (consolidated-review-report.md bulgularına göre)  
**Tarih:** 2026-02-10  
**Referans:** R1 (A-001→A-007), R2 (A-006, B-006), R3 (A-001→A-014), R4 (A-001→A-014)

---

## Özet

v1.3 → v2.2 güncellemesi, 4 review raporunun toplam **47 mimari-ilişkili bulgunun** çözümünü içerir. Temel değişiklikler:

1. **Metrik güncellemesi**: 65 tablo → 71, 295 route → 321, 766 test → 860, 48 commit → 70
2. **Test Hub Domain**: 5 model → 14 model (TS-Sprint 1+2 ürünleri eklendi)
3. **AI Module**: 22 route → 29 route, Gemini provider eklendi
4. **Servis Katmanı** bölümü eklendi (12 servis, doküman eksikliği giderildi)
5. **Revizyon Geçmişi** v2.0, v2.1, v2.2 kayıtları eklendi

---

## 1. Revizyon Geçmişi Tablosu — EKLE

Mevcut tabloya eklenecek satırlar:

```markdown
| 2.0 | 2026-02-09 | **[MAJOR]** TS-Sprint 1: TestSuite, TestStep, TestCaseDependency, TestCycleSuite modelleri. 4 yeni Test Hub tablosu, 11 yeni route, 37 yeni test. **69 tablo, 306 route, 803 test.** |
| 2.1 | 2026-02-09 | **[MAJOR]** TS-Sprint 2: TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink modelleri. 5 yeni Test Hub tablosu, 16 yeni route, 46 yeni test. AI: Gemini provider eklendi, 7 yeni AI route. **71 tablo, 321 route, 860 test.** |
| 2.2 | 2026-02-10 | **[DOCS]** Mimari doküman gerçek duruma hizalandı: Test Hub 14 model, AI 29 route, 12 servis referansı. consolidated-review-report.md bulgularına göre güncellenmiştir. |
```

---

## 2. Section 14 — Güncel Platform Metrikleri — GÜNCELLE

**Eski (v1.3):**

| Metrik | v1.3 Değer |
|--------|-----------|
| DB Tabloları | 65 |
| API Route | 295 |
| Test Sayısı | 766 |
| Alembic Migration | 8 |
| Git Commit | 48+ |

**Yeni (v2.2):**

| Metrik | v2.2 Değer | Delta |
|--------|-----------|-------|
| DB Tabloları | **71** | +6 (TS-Sprint 1: +4, TS-Sprint 2: +5, net: +6 deduplicate) |
| API Route | **321** | +26 (Test: +27, AI: +7, cleanup: -8) |
| Test Sayısı | **860** (848 passed, 11 deselected, 1 xfail) | +94 |
| Model Dosyaları | **13** (12 + testing.py genişledi) | +1 |
| Blueprint Dosyaları | **15** (13 + health_bp + metrics_bp) | +2 |
| Servis Dosyaları | **14** (13 + traceability.py) | +1 |
| Alembic Migration | **10** | +2 (MIG-09 TS-Sprint 1, MIG-10 TS-Sprint 2) |
| Frontend JS Dosyaları | 22 (16 view modülü) | Değişmedi |
| Python LOC | **~41,200** | +5,200 |
| JavaScript LOC | ~9,400 | Değişmedi |
| Git Commit | **70** | +22 |
| Tamamlanan Modüller | 8/12 | Değişmedi |
| Aktif AI Asistan | 3/14 | Değişmedi |

> **Bulgu:** R1 A-005, R4 D-006 — Header metrikleri güncel değildi.

---

## 3. Section 3.1 — Test Hub Domain — GÜNCELLE

**Eski (v1.3, §3.1):**

```
│                         TEST HUB DOMAIN                                 │
│                                                                         │
│  Test Plan ──1:N──▶ Test Cycle ──1:N──▶ Test Execution                 │
│                                                                         │
│  Test Catalog ──1:N──▶ Test Case                                       │
│                          ├── linked_requirements[]                      │
│                          ├── test_layer (Unit/SIT/UAT/Regression/Perf) │
│                          ├── test_data_set                             │
│                          └──1:N──▶ Defect                              │
```

**Yeni (v2.2):**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     TEST HUB DOMAIN (14 Model)                          │
│                                                                         │
│  Test Plan ──1:N──▶ Test Cycle ──M:N──▶ Test Suite (via TestCycleSuite)│
│                       │                    │                            │
│                       │                    └──1:N──▶ Test Case          │
│                       │                               ├── test_layer    │
│                       │                               ├── priority      │
│                       │                               ├── preconditions │
│                       │                               ├──1:N──▶ TestStep│
│                       │                               │  ├── step_order │
│                       │                               │  ├── action     │
│                       │                               │  └── expected   │
│                       │                               │                 │
│                       │                               └──M:N──▶ TestCaseDependency
│                       │                                  ├── dependency_type
│                       │                                  └── (blocks/requires/related)
│                       │                                                 │
│                       └──1:N──▶ Test Execution                         │
│                                   │                                     │
│                                   └──1:N──▶ TestRun                    │
│                                               ├── runner_name          │
│                                               ├── environment          │
│                                               ├── started_at/ended_at  │
│                                               └──1:N──▶ TestStepResult │
│                                                          ├── step_id   │
│                                                          ├── status     │
│                                                          ├── actual     │
│                                                          └── evidence   │
│                                                                         │
│  Test Case ──1:N──▶ Defect                                             │
│                       ├── severity (S1/S2/S3/S4)                       │
│                       ├── priority (Critical/High/Medium/Low)          │
│                       ├── status (7 state: New→...→Closed)             │
│                       ├── aging_days, reopen_count                     │
│                       ├── sla_breach (boolean)                         │
│                       ├──1:N──▶ DefectComment                          │
│                       │           ├── author, content, timestamp       │
│                       │           └── is_internal (boolean)            │
│                       ├──1:N──▶ DefectHistory                          │
│                       │           ├── field_name, old_value, new_value │
│                       │           └── changed_by, changed_at           │
│                       └──1:N──▶ DefectLink                             │
│                                   ├── link_type (duplicate/related/    │
│                                   │              blocks/caused_by)     │
│                                   └── target_defect_id                 │
│                                                                         │
│  14 Tablo: test_plans, test_cycles, test_suites, test_cycle_suites,    │
│            test_cases, test_steps, test_case_dependencies,             │
│            test_executions, test_runs, test_step_results,              │
│            defects, defect_comments, defect_history, defect_links      │
│                                                                         │
│  Traceability Matrix: Requirement ↔ Test Case ↔ Defect (auto-built)   │
│  Regression Set: flagged test cases for upgrade/release cycles          │
└─────────────────────────────────────────────────────────────────────────┘
```

> **Bulgu:** R3 A-001/A-002/A-003 (P1-004) — 9 yeni model doküman'da yoktu.

---

## 4. Section 4.6 — Test Hub Module — GÜNCELLE

Mevcut §4.6'ya eklenecek alt bölümler:

### 4.6.1 Test Suite Yönetimi (TS-Sprint 1)

```
TestSuite
  ├── suite_type (Functional/Regression/Integration/E2E/Performance)
  ├── execution_order (sequential/parallel)
  ├── estimated_duration
  └── M:N ↔ TestCycle (TestCycleSuite junction)

TestStep (Test Case alt adımları)
  ├── step_order (sıra numarası)
  ├── action (yapılacak işlem)
  ├── expected_result
  ├── test_data
  └── belongs_to: TestCase (1:N)

TestCaseDependency (bağımlılık grafiği)
  ├── dependency_type (blocks/requires/related_to)
  ├── source_case_id → target_case_id
  └── dependency graph → topological sort ile execution order
```

### 4.6.2 Test Execution Detail (TS-Sprint 2)

```
TestRun (Execution'ın tek bir koşusu)
  ├── runner_name (tester)
  ├── environment (DEV/QAS/PRD)
  ├── started_at, ended_at
  ├── build_version
  └── 1:N → TestStepResult

TestStepResult (Adım bazlı sonuç)
  ├── step_id → TestStep FK
  ├── status (passed/failed/blocked/skipped)
  ├── actual_result
  ├── evidence_url (screenshot/video)
  └── defect_id (fail → defect oluştur)
```

### 4.6.3 Defect Collaboration (TS-Sprint 2)

```
DefectComment (yorum geçmişi)
  ├── defect_id → Defect FK
  ├── author, content, created_at
  └── is_internal (boolean — iç not vs dış yorum)

DefectHistory (alan değişiklik logu)
  ├── defect_id → Defect FK
  ├── field_name (status/severity/assignee/...)
  ├── old_value, new_value
  └── changed_by, changed_at

DefectLink (defectlar arası ilişki)
  ├── source_defect_id, target_defect_id
  ├── link_type (duplicate_of/related_to/blocks/caused_by)
  └── bidirectional traversal support
```

> **Bulgu:** R3 A-001/A-002/A-003 — Üç model grubu doküman'da hiç yoktu.

---

## 5. Section 10 — AI Katmanı — GÜNCELLE

### 5.1 LLM Gateway Provider Listesi

Mevcut §10.3'e eklenmesi gereken provider:

```
Provider Router güncel durum (v2.2):
  ├── Anthropic Claude (primary) — Haiku/Sonnet/Opus
  ├── OpenAI GPT (fallback) — GPT-4o
  ├── Google Gemini (eklendi: TS-Sprint 2) — gemini-1.5-flash / gemini-1.5-pro
  └── LocalStub (test/dev ortamı)

Gemini endpoint: /api/v1/ai/providers/gemini
Yapılandırma: GEMINI_API_KEY env var
```

> **Bulgu:** R4 A-006 — Gemini provider doküman'da yoktu.

### 5.2 AI Route Güncelleme (22 → 29)

Mevcut §5.1 API ağacına `/ai` altına eklenmesi gereken yeni route'lar:

```
/api/v1/ai/
  ├── (mevcut 22 route)
  ├── GET  /providers                    # Aktif provider listesi
  ├── POST /providers/:name/test         # Provider bağlantı testi
  ├── GET  /providers/:name/models       # Provider model listesi
  ├── GET  /kb-versions                  # Knowledge base versiyonları
  ├── POST /kb-versions                  # Yeni KB versiyon oluştur
  ├── GET  /kb-versions/:id/stats        # KB versiyon istatistikleri
  └── POST /kb-versions/:id/activate     # KB versiyon aktifleştir
```

> **Bulgu:** R4 A-008, A-010 — KB Versioning ve provider API'leri doküman'da eksikti.

### 5.3 SUGGESTION_TYPES Genişletme

Mevcut §10.5'teki `suggestion_type` enum'ına eklenmesi gereken tipler:

```
Mevcut: classify | generate | recommend | alert
Eklenecek: test_generation | spec_draft | risk_signal | impact_report | data_quality
```

> **Bulgu:** R4 A-009 — 9 AI asistan 5 farklı suggestion tipi kullanacak, mevcut 4 tip yetersiz.

---

## 6. YENİ BÖLÜM: §4.X Servis Katmanı — EKLE

> **Bulgu:** R4 A-012 — Mimari doküman'da servis katmanı ayrı bölüm olarak tanımlanmamış.

### 4.12 Servis Katmanı (Service Layer)

Platform modülleri ile veritabanı arasındaki iş mantığını kapsülleyen 14 servis:

| # | Servis | Dosya | Modül | Açıklama |
|---|--------|-------|-------|----------|
| 1 | NotificationService | app/services/notification.py | Cross-cutting | In-app notification oluşturma, okundu işareti |
| 2 | TraceabilityService | app/services/traceability.py | Cross-cutting | Req↔WRICEF↔TestCase↔Defect↔Interface chain |
| 3 | FitPropagationService | app/services/fit_propagation.py | Explore | L3 fit_status → L2/Scenario rollup |
| 4 | WorkshopSessionService | app/services/workshop_session.py | Explore | Workshop CRUD + agenda/decision/action |
| 5 | RequirementLifecycleService | app/services/requirement_lifecycle.py | Explore | Draft→Review→Approved→Implemented→Verified |
| 6 | OpenItemLifecycleService | app/services/open_item_lifecycle.py | Explore | Open item tracking + aging |
| 7 | ScopeChangeService | app/services/scope_change.py | Explore | Change request workflow + impact |
| 8 | SignoffService | app/services/signoff.py | Explore | Multi-level sign-off workflow |
| 9 | MinutesGeneratorService | app/services/minutes_generator.py | Explore | Workshop → toplantı tutanağı (AI-ready) |
| 10 | SnapshotService | app/services/snapshot.py | Explore | Günlük KPI snapshot + trend |
| 11 | LLMGateway | app/ai/gateway.py | AI | Multi-provider LLM routing |
| 12 | RAGPipeline | app/ai/rag.py | AI | Hybrid search (cosine+BM25+RRF) |
| 13 | SuggestionQueue | app/ai/suggestion_queue.py | AI | HITL lifecycle |
| 14 | PromptRegistry | app/ai/prompt_registry.py | AI | YAML template versioning |

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER                               │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ Notification │  │ Traceability │  │ 8 × Explore Services     │ │
│  │ Service      │  │ Service      │  │ (FitProp, Workshop,      │ │
│  │              │  │              │  │  ReqLifecycle, OpenItem, │ │
│  │ • create     │  │ • trace_up   │  │  ScopeChange, Signoff,  │ │
│  │ • mark_read  │  │ • trace_down │  │  Minutes, Snapshot)     │ │
│  │ • list       │  │ • full_chain │  │                          │ │
│  │ • count      │  │ • summary    │  │                          │ │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘ │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ LLM Gateway  │  │ RAG Pipeline │  │ Suggestion Queue         │ │
│  │              │  │              │  │ + Prompt Registry         │ │
│  │ • 4 provider │  │ • hybrid     │  │                          │ │
│  │ • fallback   │  │   search     │  │ • HITL lifecycle         │ │
│  │ • cost track │  │ • re-rank    │  │ • auto-approve rules     │ │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Section 5.1 — API Ağacı Test Hub Güncellemesi

Mevcut §5.1'deki `/testing` bölümüne eklenecek route'lar:

```
├── /testing
│   ├── (mevcut route'lar)
│   │
│   │   # TS-Sprint 1 eklentileri
│   ├── GET    /suites                    # Test suite listesi
│   ├── POST   /suites                    # Suite oluştur
│   ├── GET    /suites/:suiteId           # Suite detay + test case'ler
│   ├── PUT    /suites/:suiteId           # Suite güncelle
│   ├── DELETE /suites/:suiteId           # Suite sil
│   ├── GET    /cases/:caseId/steps       # Test case adımları
│   ├── POST   /cases/:caseId/steps       # Adım ekle
│   ├── PUT    /steps/:stepId             # Adım güncelle
│   ├── DELETE /steps/:stepId             # Adım sil
│   ├── GET    /cases/:caseId/dependencies # Bağımlılıklar
│   ├── POST   /cases/:caseId/dependencies # Bağımlılık ekle
│   │
│   │   # TS-Sprint 2 eklentileri
│   ├── GET    /executions/:execId/runs   # Execution runs
│   ├── POST   /executions/:execId/runs   # Yeni run başlat
│   ├── PUT    /runs/:runId               # Run güncelle
│   ├── GET    /runs/:runId/step-results  # Adım sonuçları
│   ├── POST   /runs/:runId/step-results  # Adım sonucu kaydet
│   ├── GET    /defects/:defectId/comments # Defect yorumları
│   ├── POST   /defects/:defectId/comments # Yorum ekle
│   ├── GET    /defects/:defectId/history  # Defect geçmişi
│   ├── GET    /defects/:defectId/links    # Defect bağlantıları
│   ├── POST   /defects/:defectId/links    # Bağlantı ekle
│   ├── DELETE /defect-links/:linkId       # Bağlantı sil
│   │
│   │   # TS-Sprint 3 planı (⬜ henüz implement edilmedi)
│   ├── POST   /cases/generate-from-wricef  # WRICEF → TestCase auto-gen
│   ├── POST   /cases/generate-from-process # Process → TestCase auto-gen
│   ├── GET    /defects/:defectId/sla       # SLA durumu
│   ├── GET    /go-no-go-scorecard          # Go/No-Go değerlendirme
│   └── GET    /dashboard/daily-snapshot    # Günlük snapshot
```

> **Bulgu:** R3 A-004/A-005 (P1-005/P1-006) — generate endpoint'leri henüz yok, TS-Sprint 3'te planlandı.

---

## 8. Section 11 — Uygulama Yol Haritası — GÜNCELLE

### Phase 1 güncellemesi:

```
✅ Test Hub (14 model, 55 route, 147 test) — TAMAMLANDI (S5 + TS-Sprint 1-2)
   ├── TS-Sprint 1: TestSuite, TestStep, TestCaseDependency, TestCycleSuite
   └── TS-Sprint 2: TestRun, TestStepResult, DefectComment, DefectHistory, DefectLink
```

### Phase 2 güncellemesi:

```
TS-Sprint 3 (planlandı):
  ├── UATSignOff, PerfTestResult, TestDailySnapshot (3 yeni model)
  ├── generate-from-wricef, generate-from-process (2 auto-gen endpoint)
  ├── SLA engine + Go/No-Go scorecard
  └── Defect 9-status lifecycle (assigned + deferred ekleme)
```

---

## 9. Değişiklik Uygulama Kontrol Listesi

| # | Bölüm | Değişiklik | Bulgu | Durum |
|---|-------|-----------|-------|-------|
| 1 | Revizyon tablosu | v2.0, v2.1, v2.2 satırları ekle | — | ⬜ |
| 2 | §14 Metrikler | 65→71, 295→321, 766→860, 48→70 | R1 A-005 | ⬜ |
| 3 | §3.1 Test Hub Domain | 5 model → 14 model ERD | R3 A-001/A-002/A-003 | ⬜ |
| 4 | §4.6 Test Hub Module | 3 alt bölüm ekle | R3 A-001/A-002/A-003 | ⬜ |
| 5 | §10.3 LLM Gateway | Gemini provider ekle | R4 A-006 | ⬜ |
| 6 | §5.1 /ai route'ları | 7 yeni route ekle (22→29) | R4 A-008/A-010 | ⬜ |
| 7 | §10.5 SUGGESTION_TYPES | 5 yeni tip ekle | R4 A-009 | ⬜ |
| 8 | §4.12 Servis Katmanı | YENİ bölüm — 14 servis | R4 A-012 | ⬜ |
| 9 | §5.1 /testing route'ları | 21 yeni route ekle | R3 summary | ⬜ |
| 10 | §11 Yol haritası | Phase 1-2 güncelle | R3 summary | ⬜ |
| 11 | §3.1.1 Explore heading | "25 model" onaylı, değişiklik yok | R2 check | ✅ |

**Toplam değişiklik efor tahmini:** ~4 saat (doküman düzenleme)

---

**Dosya:** `architecture_v2.2_changelog.md`  
**Oluşturan:** GitHub Copilot (Claude Opus 4.6)
