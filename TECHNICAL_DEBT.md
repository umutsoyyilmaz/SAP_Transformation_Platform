# SAP Transformation Platform — Technical Debt Registry

**Oluşturulma Tarihi:** 2026-02-10  
**Kaynak:** 4 review raporu (architecture-and-plan-review, explore-review, test-mgmt-review, other-docs-review)  
**Commit:** `3c331dd` (TS-Sprint 2)  
**Toplam Teknik Borç:** ~199 saat

---

## 1. Kategorize Teknik Borç

### 1.1 DOKÜMAN BORCU (24 madde, ~28 saat)

| # | Madde | Kaynak Finding | Severity | Effort | Sprint Önerisi |
|---|-------|----------------|:--------:|:------:|----------------|
| DOC-01 | README.md kapsamlı güncelleme (Sprint 4'te kalmış → 321 route, 860 test, 12 modül) | E-001 | 🟠 HIGH | 2h | Hemen |
| DOC-02 | README.md modül listesi ekle (12 blueprint + route sayıları) | E-002 | 🟡 MED | 1h | Hemen |
| DOC-03 | README.md Docker/PG kurulum + env variable bölümü ekle | E-003 | 🟢 LOW | 1h | S10 |
| DOC-04 | README.md lisans belirle (MIT / Apache 2.0 / proprietary) | E-004 | 🟢 LOW | 0.5h | Hemen |
| DOC-05 | project-inventory.md M10 sınıf adları düzelt (AIConversation→AIUsageLog) | A-004/A-005 | 🟠 HIGH | 0.5h | Hemen |
| DOC-06 | project-inventory.md §5.2 .bak dosya notunu güncelle (temizlendi) | D-001 | 🟢 LOW | 0.5h | Hemen |
| DOC-07 | D3 (architecture v2.md) Test Management bölümünü güncelle (5→14 tablo, 28→55 route) | Arch-Review | 🟡 MED | 2h | S10 |
| DOC-08 | D3 AI modülü endpoint sayısını 22→29 güncelle | A-006 | 🟡 MED | 0.5h | Hemen |
| DOC-09 | D3'e Gemini provider bilgisi ekle (4 provider) | A-008 | 🟢 LOW | 0.5h | S10 |
| DOC-10 | D4 (architecture v1.3) arşivle veya sil | D-002 | 🟢 LOW | 0.5h | Hemen |
| DOC-11 | D5 Sprint 22'yi 18→56 saat olarak güncelle (D14 revisyon) | C-003 | 🔴 CRIT | 0.5h | Hemen |
| DOC-12 | D7 (GATE_CHECK_REPORT) Release 2 gate sonuçları ekle (Sprint 6-9 + TS-Sprint 1-2) | Inv-§5.1 | 🟡 MED | 3h | S10 |
| DOC-13 | D8 (CHANGELOG) TS-Sprint 1-2 entry'leri ekle | Inv-§5.1 | 🟡 MED | 1h | Hemen |
| DOC-14 | D11 başlığa "(3 aktif + 11 planlı)" notu, §1 endpoint sayısını 22→29 güncelle | A-003/A-006 | 🟢 LOW | 0.5h | S10 |
| DOC-15 | D12 metrikleri güncelle (15 JS→22 JS, 8,174→11,964 LOC) + Faz 2 revize | B-002 | 🟡 MED | 1h | S10 |
| DOC-16 | D13 (Signavio) Explore Phase implementasyonuyla reconcile et | C-001 | 🟠 HIGH | 2h | D13 review |
| DOC-17 | D13 ScopeItem kararını Explore Phase çözümüyle align et | C-002 | 🟡 MED | 1h | D13 review |
| DOC-18 | Explore FS/TS — 8 uyumsuzluk düzeltimi (explore-review findings) | Explore-Review | 🟡 MED | 3h | S10 |
| DOC-19 | Test Mgmt FS/TS — 14 eksik endpoint, 3 eksik tablo, status uyumsuzlukları belge | Test-Review | 🟡 MED | 2h | TS-Sprint 3 |
| DOC-20 | User Guide (TR/EN) — 12+ henüz olmayan özellik belgelemiş, uyarı notu ekle | Test-Review D | 🟡 MED | 1h | TS-Sprint 3 |
| DOC-21 | Explore User Guide — 5 gap (workshop generate-minutes, dashboard heatmap) | Explore-Review D | 🟡 MED | 1h | S10 |
| DOC-22 | D6 (PROGRESS_REPORT) minor sayı uyumsuzlukları düzelt | Inv-§5.1 | 🟢 LOW | 0.5h | Hemen |
| DOC-23 | D9 (EXPLORE_TASK_LIST) "296 route" → "321 route" güncelle | Inv-§5.1 | 🟢 LOW | 0.5h | Hemen |
| DOC-24 | SUGGESTION_TYPES set'ine docstring veya yeni asistan tipleri ekle | A-009 | 🟢 LOW | 0.5h | S12a |
| | **Doküman Borcu Toplamı** | | | **~28h** | |

---

### 1.2 KOD BORCU (22 madde, ~116 saat)

| # | Madde | Kaynak Finding | Severity | Effort | Sprint Önerisi |
|---|-------|----------------|:--------:|:------:|----------------|
| CODE-01 | Risk Assessment asistan sınıfı implement et (P1) | A-001 | 🟡 MED | 8h | S12a |
| CODE-02 | Test Case Generator asistan sınıfı implement et (P2) | A-002 | 🟡 MED | 10h | S12a |
| CODE-03 | 3 eksik Test Mgmt model: UATSignOff, PerfTestResult, TestDailySnapshot | Test-A-001 | 🔴 CRIT | 6h | TS-Sprint 3 |
| CODE-04 | 14 eksik Test Mgmt endpoint (generate-from-wricef, approve, transition, ALM sync, go-no-go) | Test-A | 🔴 CRIT | 16h | TS-Sprint 3-4 |
| CODE-05 | Defect 9-status lifecycle (model'de 8, FS/TS'de 9, "assigned" eksik) | Test-A-006 | 🟠 HIGH | 3h | TS-Sprint 3 |
| CODE-06 | Defect SLA hesaplama engine'i | Test-A | 🟡 MED | 4h | TS-Sprint 3 |
| CODE-07 | Entry/exit criteria check logic'i (test cycle start/complete) | Test-A | 🟡 MED | 4h | TS-Sprint 3 |
| CODE-08 | Testing servis katmanı: DefectLifecycleService, TestExecutionService | D-007 | 🟡 MED | 8h | TS-Sprint 3-4 |
| CODE-09 | cost_summary granularity parametresini düzelt (weekly/monthly) | A-013 | 🟢 LOW | 1h | S12a |
| CODE-10 | Vue 3 Phase 0 başlat (Vite + utils.js + scaffold) | B-001 | 🟠 HIGH | 2.5h | S10 |
| CODE-11 | Explore Phase: 4 eksik servis (PDF export, heatmap, auto-code) | Explore-Review | 🟡 MED | 10h | S10 |
| CODE-12 | Explore Phase: workshop generate-minutes endpoint | Explore-Review | 🟡 MED | 3h | S10 |
| CODE-13 | Explore Phase: dashboard heatmap widget | Explore-Review | 🟡 MED | 2h | S10 |
| CODE-14 | JSON kolonları db.Text → db.JSON migration (PG optimization) | D-005 | 🟢 LOW | 3h | S14 |
| CODE-15 | Makefile'a `make lint` ve `make format` hedeflerini ekle | D-008 | 🟢 LOW | 0.5h | Hemen |
| CODE-16 | Severity notation standardize et: S1-S4 ↔ P1-P4 uyumsuzluğu çöz | Test-A-009 | 🟡 MED | 2h | TS-Sprint 3 |
| CODE-17 | Integer PK → UUID migration (FS/TS UUID tanımlıyor, kod Integer) | Test-A-003 | 🟢 LOW | 8h | S14+ |
| CODE-18 | Explore Phase: UUID PK uyumsuzluğu (26 model Integer, FS/TS UUID) | Explore-A | 🟢 LOW | 8h | S14+ |
| CODE-19 | Defect link_type'a "caused_by" ekle (FS/TS 4, kod 3) | Test-A | 🟢 LOW | 0.5h | TS-Sprint 3 |
| CODE-20 | Test plan_status "approved" ekle (FS/TS 5, kod 4) | Test-A | 🟢 LOW | 0.5h | TS-Sprint 3 |
| CODE-21 | TestCase code auto-generation (TC-FI-001 pattern) | Test-A | 🟡 MED | 2h | TS-Sprint 3 |
| CODE-22 | Change Impact Analyzer asistan (P3, S12b) | D11 | 🟡 MED | 12h | S12b |
| | **Kod Borcu Toplamı** | | | **~116h** | |

---

### 1.3 TEST BORCU (10 madde, ~40 saat)

| # | Madde | Kaynak Finding | Severity | Effort | Sprint Önerisi |
|---|-------|----------------|:--------:|:------:|----------------|
| TEST-01 | CI'ya PostgreSQL test environment ekle (Docker + pytest marker) | D-006 | 🟠 HIGH | 4h | S14 |
| TEST-02 | Program modülü test coverage artır (1.4→3.0: ~40 ek test) | D-004 | 🟡 MED | 4h | S12 |
| TEST-03 | Scenario modülü test coverage artır (1.4→3.0: ~27 ek test) | D-004 | 🟡 MED | 3h | S12 |
| TEST-04 | RAID modülü test coverage artır (1.5→3.0: ~44 ek test) | D-004 | 🟡 MED | 4h | S12 |
| TEST-05 | Frontend E2E baseline testler (5 kritik akış Playwright) | B-004 | 🟡 MED | 5h | S10 |
| TEST-06 | Explore Phase: workshop CRUD happy+edge testleri (%86 coverage gap) | Explore-C | 🟡 MED | 4h | S10 |
| TEST-07 | Explore Phase: scope change advanced test (veto, deadline, multi-comment) | Explore-C | 🟡 MED | 3h | S10 |
| TEST-08 | Testing module: FS/TS iş kuralları testleri (SLA, entry/exit criteria, go-no-go) | Test-C | 🟡 MED | 6h | TS-Sprint 3 |
| TEST-09 | AI accuracy benchmark genişlet (3→10 test senaryosu) | — | 🟢 LOW | 3h | S12a |
| TEST-10 | Migration verification test (`flask db upgrade` against fresh SQLite) | D15 | 🟡 MED | 2h | S14 |
| | **Test Borcu Toplamı** | | | **~40h** | |

---

### 1.4 CONFIG / DEVOPS BORCU (7 madde, ~15 saat)

| # | Madde | Kaynak Finding | Severity | Effort | Sprint Önerisi |
|---|-------|----------------|:--------:|:------:|----------------|
| CFG-01 | Celery + Redis asenkron altyapı kurulumu (S18 blocker) | D14 §4 | 🟠 HIGH | 4h | S18 |
| CFG-02 | OAuth2/JWT token exchange altyapısı (S14 → S22 blocker) | D14 §4 | 🟠 HIGH | 4h | S14 |
| CFG-03 | Docker-compose prod environment doğrulama | D15 #7 | 🟢 LOW | 1h | S14 |
| CFG-04 | GitHub Actions CI pipeline (lint + test + PG test + coverage) | D-006, D-008 | 🟡 MED | 3h | S14 |
| CFG-05 | .env.example güncelle (GEMINI_API_KEY, yeni config'ler) | E-003 | 🟢 LOW | 0.5h | Hemen |
| CFG-06 | Alembic migration chain integrity test (auto-run on CI) | D15 | 🟡 MED | 1h | S14 |
| CFG-07 | Log rotation + structured logging (JSON format) | — | 🟢 LOW | 2h | S14 |
| | **Config Borcu Toplamı** | | | **~15h** | |

---

## 2. Toplam Teknik Borç Özeti

| Kategori | Madde Sayısı | Tahmini Effort |
|----------|:------------:|:--------------:|
| Doküman Borcu | 24 | ~28 saat |
| Kod Borcu | 22 | ~116 saat |
| Test Borcu | 10 | ~40 saat |
| Config / DevOps Borcu | 7 | ~15 saat |
| **TOPLAM** | **63** | **~199 saat** |

---

## 3. Severity Dağılımı

| Severity | Sayı | Toplam Effort |
|----------|:----:|:-------------:|
| 🔴 CRITICAL | 3 | ~22.5h |
| 🟠 HIGH | 8 | ~27.5h |
| 🟡 MEDIUM | 31 | ~116h |
| 🟢 LOW | 21 | ~33h |
| **Toplam** | **63** | **~199h** |

---

## 4. Sprint Bazlı Çözüm Planı

### Sprint "Hemen" — Quick Wins (Doküman temizliği, ~8.5 saat)

| # | Madde | Effort |
|---|-------|:------:|
| DOC-01 | README kapsamlı güncelle | 2h |
| DOC-02 | README modül listesi | 1h |
| DOC-04 | Lisans belirle | 0.5h |
| DOC-05 | Envanter M10 düzelt | 0.5h |
| DOC-06 | Envanter .bak güncelle | 0.5h |
| DOC-08 | D3 AI 22→29 | 0.5h |
| DOC-10 | D4 arşivle | 0.5h |
| DOC-11 | D5 S22 18→56h güncelle | 0.5h |
| DOC-13 | CHANGELOG TS-Sprint 1-2 ekle | 1h |
| DOC-22 | PROGRESS_REPORT düzelt | 0.5h |
| DOC-23 | TASK_LIST düzelt | 0.5h |
| CODE-15 | Makefile lint/format | 0.5h |
| CFG-05 | .env.example güncelle | 0.5h |
| | **Toplam** | **~8.5h** |

### S10 — Data Factory + Vue Phase 0 + Explore Polish (~25 saat TD)

| # | Madde | Effort |
|---|-------|:------:|
| CODE-10 | Vue 3 Phase 0 (Vite + scaffold) | 2.5h |
| CODE-11 | Explore eksik servisler | 10h |
| CODE-12 | Workshop minutes endpoint | 3h |
| CODE-13 | Dashboard heatmap | 2h |
| DOC-07 | D3 Test Mgmt güncelle | 2h |
| DOC-12 | Gate check report güncelle | 3h |
| TEST-05 | Frontend E2E baseline | 5h |
| TEST-06 | Explore workshop testleri | 4h |
| | Diğer DOC / LOW items | ~3h |
| | **Toplam** | **~25h** (S10 ayrılan süre ~18.5h, +6.5h TD ek) |

### S12a — AI Phase 2a + Test Artırma (~22 saat TD)

| # | Madde | Effort |
|---|-------|:------:|
| CODE-01 | Risk Assessment asistan | 8h |
| CODE-02 | Test Case Generator asistan | 10h |
| TEST-02 | Program test coverage | 4h |
| TEST-03 | Scenario test coverage | 3h |
| TEST-04 | RAID test coverage | 4h |
| | **Toplam** | **~22h** (örtüşen S12a task'larıyla paylaşılır) |

### TS-Sprint 3 — Test Mgmt Phase 3 (~28 saat TD)

| # | Madde | Effort |
|---|-------|:------:|
| CODE-03 | 3 eksik model (UATSignOff, PerfTestResult, Snapshot) | 6h |
| CODE-04 | 14 eksik endpoint | 16h |
| CODE-05 | Defect 9-status lifecycle | 3h |
| CODE-06 | SLA hesaplama | 4h |
| CODE-07 | Entry/exit criteria | 4h |
| CODE-08 | Testing servis katmanı | 8h |
| CODE-16 | Severity standardize | 2h |
| TEST-08 | İş kuralı testleri | 6h |
| DOC-19/20 | FS/TS + User Guide güncelle | 3h |
| | **Toplam** | **~28h** (TS-Sprint 3 planına ek) |

### S14 — Security & Platform Hardening (~16 saat TD)

| # | Madde | Effort |
|---|-------|:------:|
| CFG-02 | OAuth2/JWT altyapı | 4h |
| CFG-04 | GitHub Actions CI | 3h |
| TEST-01 | PostgreSQL test env | 4h |
| TEST-10 | Migration verify test | 2h |
| CODE-14 | JSON kolonu migration | 3h |
| CFG-06 | Alembic chain test | 1h |
| | **Toplam** | **~16h** |

### S18+ — İleri Sprint'ler (~12 saat TD)

| # | Madde | Effort |
|---|-------|:------:|
| CFG-01 | Celery + Redis | 4h |
| CODE-17/18 | UUID migration (opsiyonel) | 8h |
| | **Toplam** | **~12h** |

---

## 5. Risk Matrisi

| Risk | Olasılık | Etki | Azaltma |
|------|:--------:|:----:|---------|
| D5 plandaki 38 saatlik eksik tahmin (S22: 18h→56h) proje timeline'ı kaydırır | Yüksek | Yüksek | **Hemen** D5 güncelle |
| CI'da PG test yokluğu → prod deployment sürprizi | Orta | Yüksek | S14'te PG test ekle |
| README güncel değil → contributor/evaluator yanılır | Yüksek | Orta | **Hemen** güncelle |
| Test Mgmt 14 eksik endpoint → FS/TS scope tamamlanmaz | Orta | Yüksek | TS-Sprint 3-4 planla |
| Vue 3 migration başlamadan frontend technical debt büyür | Orta | Orta | S10 Phase 0 başlat |
| 3 modülde <2 test/route → regression invisible | Orta | Orta | S12'de test artır |

---

## 6. Borç Ödeme Yol Haritası (Gantt Özet)

```
Sprint "Hemen"  ██████████░░░░░░░░░░░░░░░░░░░░░░  ~8.5h (doküman temizliği)
S10             ░░░░░░████████████████░░░░░░░░░░░░  ~25h (Explore + Vue + test)
S12a            ░░░░░░░░░░░░░░░░████████████░░░░░░  ~22h (AI + test coverage)
TS-Sprint 3     ░░░░░░░░░░░░░░░░░░░░████████████░░  ~28h (Test Mgmt completion)
S14             ░░░░░░░░░░░░░░░░░░░░░░░░░░████████  ~16h (security + CI + PG)
S18+            ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░████  ~12h (async + UUID optional)
                                                      ─────
                                              Toplam: ~199h
```

---

**Dosya:** `TECHNICAL_DEBT.md`  
**Oluşturan:** GitHub Copilot (Claude Opus 4.6)  
**Tarih:** 2026-02-10  
**Kaynak Review Raporları:**  
- `architecture-and-plan-review.md` (38 finding)  
- `explore-review-findings.md` (24 finding)  
- `test-mgmt-review-findings.md` (33 finding)  
- `other-docs-review-findings.md` (38 finding)  
**Toplam Finding:** 133 → **63 teknik borç maddesi**, **~199 saat**
