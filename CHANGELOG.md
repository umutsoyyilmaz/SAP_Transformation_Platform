# CHANGELOG — SAP Transformation Platform

Tüm önemli değişiklikler bu dosyada belgelenir.
Format: [Conventional Commits](https://www.conventionalcommits.org/) uyumlu.

> **⚠ Mega commit açıklaması:** Sprint 4-6 (`a995200`) ve Sprint 7-8 (`db9a8a8`) 
> tek commit halinde atıldı. Aşağıda bu commit'lerin içindeki gerçek task'lar 
> listesi geriye dönük belgeleme amacıyla sunulmuştur.

---

## [Unreleased]

### Sprint 10 — Data Factory (Planlanmış)
- DataObject, MigrationWave, DataQualityRule, LoadExecution modelleri
- Data Factory API: Data object CRUD + migration wave planning
- Data Factory UI: 4-tab view

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
- `scripts/collect_metrics.py`: Otomatik metrik toplama + `--check` doğrulama modu

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
