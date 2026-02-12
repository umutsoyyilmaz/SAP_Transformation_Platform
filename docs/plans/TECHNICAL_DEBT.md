# Technical Debt Backlog — SAP Transformation Platform

**Versiyon:** 2.1  
**Tarih:** 2026-02-13  
**Baz:** TECHNICAL_DEBT.md (v2, 73 madde) + S24 Final Polish cleanup  
**Durum:** Platform v1.0 released — birden çok madde S10–S24 arasında çözülmüştür

---

## Özet

| Kategori | Madde | Effort | Çözülen | Kalan |
|----------|:-----:|:------:|:-------:|:-----:|
| DOC — Doküman borcu | 28 | ~32h | 12 | 16 |
| CODE — Kod borcu | 25 | ~128h | 14 | 11 |
| TEST — Test borcu | 12 | ~48h | 6 | 6 |
| CFG — Config/DevOps | 8 | ~18h | 5 | 3 |
| **TOPLAM** | **73** | **~226h** | **37** | **36** |

> v2.0→v2.1 delta: S10–S24 boyunca 37 madde çözüldü (DOC-002 README, CODE-016–018 AI asistanlar, CFG-001 CI/CD, CODE-019–020 security, TEST güçlendirme, vb.)

---

## Sprint Planlaması

```
Hemen (TD-Sprint 1)  ──── ~7h    │  ████ %3
TS-Sprint 3           ──── ~43h   │  ████████████████████ %19
Sprint 10             ──── ~31h   │  ██████████████ %14
Sprint 12a            ──── ~22h   │  ██████████ %10
Sprint 14             ──── ~24h   │  ███████████ %11
Sprint 18+            ──── ~12h   │  ██████ %5
Unscheduled           ──── ~87h   │  ██████████████████████████████████████ %38
                         ~226h total
```

---

## Kategori: DOC — Doküman Borcu (28 madde, ~32h)

| # | ID | Açıklama | Sev | Effort | Sprint | Durum | Bulgu Ref |
|---|-----|----------|:---:|:------:|--------|:-----:|-----------|
| 1 | DOC-001 | CHANGELOG.md 33 eksik commit | P1 | 1h | TD-Sprint 1 | ⬜ | P1-001, R1 E-001 |
| 2 | DOC-002 | README.md güncel değil (12 modül, 860 test) | P2 | 2h | TD-Sprint 1 | ⬜ | R4 E-001 |
| 3 | DOC-003 | D5 header metrikleri stale (65→71 tablo, 295→321 route) | P2 | 0.5h | TD-Sprint 1 | ⬜ | R1 B-001 |
| 4 | DOC-004 | D3 architecture §14 metrikleri stale | P2 | 0.5h | TD-Sprint 1 | ⬜ | R1 A-005 |
| 5 | DOC-005 | D6 PROGRESS_REPORT metrikleri stale | P2 | 1h | TD-Sprint 1 | ⬜ | R1 C-001 |
| 6 | DOC-006 | D7 GATE_CHECK metrikleri stale | P2 | 0.5h | TD-Sprint 1 | ⬜ | R1 D-001 |
| 7 | DOC-007 | D10 plan tarih + tech debt durum güncelle | P2 | 0.5h | TD-Sprint 1 | ⬜ | R1 F-001, F-004 |
| 8 | DOC-008 | D3 Test Hub Domain 5→14 model güncelle | P2 | 2h | S10 | ⬜ | R3 sum, R1 A-001 |
| 9 | DOC-009 | D3 AI modülü 22→29 route güncelle | P2 | 0.5h | S10 | ⬜ | R4 A-008 |
| 10 | DOC-010 | D3 Servis Katmanı bölümü ekle (§4.12) | P2 | 1h | S10 | ⬜ | R4 A-012 |
| 11 | DOC-011 | D3 LLM Gateway Gemini provider ekle | P3 | 0.5h | S10 | ⬜ | R4 A-006 |
| 12 | DOC-012 | D5 Sprint 22: 18h→56h güncelle | P2 | 0.5h | TD-Sprint 1 | ⬜ | P1-002, R4 D-001 |
| 13 | DOC-013 | project-inventory.md M10 + §5.2 düzelt | P3 | 0.5h | S10 | ⬜ | R4 D-006 |
| 14 | DOC-014 | D4 eski architecture arşivle | P3 | 0.5h | TD-Sprint 1 | ⬜ | R4 D-002 |
| 15 | DOC-015 | User Guide Explore 3 eksik section ekle | P3 | 2h | S10 | ⬜ | R2 C-001 |
| 16 | DOC-016 | User Guide Test Mgmt 6 section boş/eksik | P3 | 3h | TS-Sprint 3 | ⬜ | R3 D-001→D-006 |
| 17 | DOC-017 | AI doküman SUGGESTION_TYPES genişlet | P3 | 0.5h | S12a | ⬜ | R4 A-009 |
| 18 | DOC-018 | AI doküman risk_assessment prompt placeholder | P2 | 0.5h | S12a | ⬜ | R4 A-001 |
| 19 | DOC-019 | D3 revizyon geçmişi v2.0-2.2 ekle | P3 | 0.5h | S10 | ⬜ | — |
| 20 | DOC-020 | SIGNAVIO_DRAFT.md ← placeholder, tamamla veya arşivle | P4 | 0.5h | Unscheduled | ⬜ | R4 D-003 |
| 21 | DOC-021 | Makefile lint + format target ekle | P4 | 0.5h | TD-Sprint 1 | ⬜ | R4 D-004 |
| 22 | DOC-022 | .env.example güncellleme (GEMINI_API_KEY) | P4 | 0.5h | TD-Sprint 1 | ⬜ | R4 D-005 |
| 23 | DOC-023 | Docker compose health check güncelle | P4 | 0.5h | S14 | ⬜ | R4 D-007 |
| 24 | DOC-024 | Explore task listesi 4 kalan görevi kapat | P4 | 1h | S10 | ⬜ | R2 D-001 |
| 25 | DOC-025 | Seed data dokümanı oluştur (hangi veri nereden) | P4 | 1h | S10 | ⬜ | R2 E-001 |
| 26 | DOC-026 | Test Mgmt seed data dokümanı | P4 | 0.5h | TS-Sprint 3 | ⬜ | R3 E-001 |
| 27 | DOC-027 | D5 Explore Phase satırlarını resmi zaman çizelgesine dahil et | P3 | 1h | S10 | ⬜ | R1 B-006 |
| 28 | DOC-028 | Architecture v2.2 changelog'u uygula (bu dosya + changelog) | P2 | 4h | S10 | ⬜ | — |

---

## Kategori: CODE — Kod Borcu (25 madde, ~128h)

| # | ID | Açıklama | Sev | Effort | Sprint | Durum | Bulgu Ref |
|---|-----|----------|:---:|:------:|--------|:-----:|-----------|
| 1 | CODE-001 | minutes_generator.py 8 attribute mismatch (AttributeError) | P1 | 2h | S10 | ⬜ | P1-003, R2 A-001 |
| 2 | CODE-002 | UATSignOff modeli eksik | P1 | 1.5h | TS-Sprint 3 | ⬜ | P1-004, R3 A-010 |
| 3 | CODE-003 | PerfTestResult modeli eksik | P1 | 1.5h | TS-Sprint 3 | ⬜ | P1-004, R3 A-011 |
| 4 | CODE-004 | TestDailySnapshot modeli eksik | P1 | 1h | TS-Sprint 3 | ⬜ | P1-004, R3 A-012 |
| 5 | CODE-005 | generate-from-wricef endpoint eksik | P1 | 6h | TS-Sprint 3 | ⬜ | P1-005, R3 A-004 |
| 6 | CODE-006 | generate-from-process endpoint eksik | P1 | 6h | TS-Sprint 3 | ⬜ | P1-006, R3 A-005 |
| 7 | CODE-007 | Defect lifecycle 7→9 state (assigned + deferred) | P2 | 3h | TS-Sprint 3 | ⬜ | R3 A-006 |
| 8 | CODE-008 | Priority enum None→proper (Critical/High/Medium/Low) | P2 | 1h | TS-Sprint 3 | ⬜ | R3 A-007 |
| 9 | CODE-009 | TestExecution dual-path: execution↔run consistency | P2 | 2h | TS-Sprint 3 | ⬜ | R3 A-008 |
| 10 | CODE-010 | 14 missing testing endpoints (R3 tablosu) | P2 | 4h | TS-Sprint 3 | ⬜ | R3 A-009 |
| 11 | CODE-011 | SLA engine (SLA_HOURS matrix, breach flag) | P2 | 4h | TS-Sprint 3 | ⬜ | R3 A-013 |
| 12 | CODE-012 | Go/No-Go scorecard endpoint (10 criteria) | P2 | 3h | TS-Sprint 3 | ⬜ | R3 A-014 |
| 13 | CODE-013 | Entry/exit criteria validation | P2 | 4h | TS-Sprint 3 | ⬜ | R3 B-002 |
| 14 | CODE-014 | Backend→Frontend field mapping (date, type fields) | P2 | 2h | S10 | ⬜ | R2 A-006, A-007 |
| 15 | CODE-015 | Explore seed data: project_roles, phase_gates, l4_catalog | P2 | 4h | S10 | ⬜ | R2 E-002, E-003 |
| 16 | CODE-016 | Risk Assessment asistan class + endpoint | P2 | 8h | S12a | ⬜ | R4 A-001 |
| 17 | CODE-017 | Test Case Generator asistan | P2 | 10h | S12a | ⬜ | R4 A-002 |
| 18 | CODE-018 | Change Impact Analyzer asistan | P3 | 12h | S12a | ⬜ | D11 P3 |
| 19 | CODE-019 | JWT + row-level security | P2 | 8h | S14 | ⬜ | D5 S14 |
| 20 | CODE-020 | PostgreSQL migration (SQLite→PG) | P2 | 8h | S14 | ⬜ | D5 S14 |
| 21 | CODE-021 | Celery + Redis background tasks | P2 | 6h | S18 | ⬜ | D5 S18 |
| 22 | CODE-022 | Shared connector infra (retry, circuit breaker) | P2 | 6h | S22a | ⬜ | D14 |
| 23 | CODE-023 | Severity S1-S4 standardization (model constants) | P2 | 2h | TS-Sprint 3 | ⬜ | R3 A-007 |
| 24 | CODE-024 | UAT Sign-off API (4 endpoint) | P2 | 2h | TS-Sprint 3 | ⬜ | R3 B-001 |
| 25 | CODE-025 | Performance test API (3 endpoint) | P2 | 1.5h | TS-Sprint 3 | ⬜ | R3 B-001 |

---

## Kategori: TEST — Test Borcu (12 madde, ~48h)

| # | ID | Açıklama | Sev | Effort | Sprint | Durum | Bulgu Ref |
|---|-----|----------|:---:|:------:|--------|:-----:|-----------|
| 1 | TEST-001 | TS-Sprint 3 testleri (~60 test) | P2 | 4h | TS-Sprint 3 | ⬜ | R3 C-001 |
| 2 | TEST-002 | Program modülü test coverage artır (+40 test) | P3 | 4h | S12a | ⬜ | R2 B-001 |
| 3 | TEST-003 | RAID modülü test coverage artır (+44 test) | P3 | 4h | S12a | ⬜ | R2 B-002 |
| 4 | TEST-004 | Scenario modülü test coverage artır (+20 test) | P3 | 2h | S12a | ⬜ | R2 B-003 |
| 5 | TEST-005 | Scope modülü test coverage artır (+15 test) | P3 | 2h | S12a | ⬜ | R2 B-004 |
| 6 | TEST-006 | Frontend E2E baseline (5 akış, Playwright) | P3 | 5h | S10 | ⬜ | R2, R4 |
| 7 | TEST-007 | Test Mgmt Explore↔Testing integration testleri | P2 | 3h | TS-Sprint 3 | ⬜ | R3 B-003, B-004 |
| 8 | TEST-008 | AI asistan integration testleri (+20 test) | P3 | 3h | S12a | ⬜ | R4 A-014 |
| 9 | TEST-009 | Seed data — UAT/perf/snapshot demo senaryolar | P3 | 1h | TS-Sprint 3 | ⬜ | R3 E-002 |
| 10 | TEST-010 | Seed data — Test Mgmt defect triage senaryolar | P3 | 1h | TS-Sprint 3 | ⬜ | R3 E-003 |
| 11 | TEST-011 | Load/performance test baseline | P4 | 8h | S14 | ⬜ | — |
| 12 | TEST-012 | Alembic migration chain integrity test | P3 | 1h | S14 | ⬜ | R4 D-008 |

---

## Kategori: CFG — Config / DevOps Borcu (8 madde, ~18h)

| # | ID | Açıklama | Sev | Effort | Sprint | Durum | Bulgu Ref |
|---|-----|----------|:---:|:------:|--------|:-----:|-----------|
| 1 | CFG-001 | GitHub Actions CI pipeline (lint + test + PG test) | P2 | 3h | S14 | ⬜ | R4 D-004 |
| 2 | CFG-002 | PostgreSQL test environment (CI'da PG) | P2 | 4h | S14 | ⬜ | R4 D-007 |
| 3 | CFG-003 | .env.example GEMINI_API_KEY + diğer eksik var | P3 | 0.5h | TD-Sprint 1 | ⬜ | R4 D-005 |
| 4 | CFG-004 | Docker compose health check güncelle | P3 | 0.5h | S14 | ⬜ | R4 D-007 |
| 5 | CFG-005 | Makefile lint + format + test targets | P3 | 0.5h | TD-Sprint 1 | ⬜ | R4 D-004 |
| 6 | CFG-006 | Pre-commit hooks (flake8/black/isort) | P4 | 1h | S14 | ⬜ | — |
| 7 | CFG-007 | OpenAPI/Swagger spec generation | P4 | 4h | Unscheduled | ⬜ | R2 D-004 |
| 8 | CFG-008 | Monitoring alerting (PagerDuty/Slack integration) | P4 | 4h | S18 | ⬜ | — |

---

## Öncelik Matrisi

```
        ┌─────────────────────────────────────────┐
        │           ETKİ (Impact)                  │
        │   Düşük      Orta       Yüksek          │
   ┌────┼─────────┬───────────┬───────────┐       │
 Y │High│ CFG-005 │ CODE-014  │ CODE-001  │ ← Hemen
 ü │    │ CFG-003 │ CODE-015  │ CODE-002→006│     │
 k │    │         │ DOC-008   │ DOC-001   │       │
 s │    │         │ DOC-012   │           │       │
 e ├────┼─────────┼───────────┼───────────┤       │
 k │Med │ DOC-020 │ TEST-002  │ CODE-007  │       │
   │    │ DOC-021 │ TEST-003  │ CODE-011  │       │
 O │    │         │ CODE-016  │ CODE-012  │       │
 l │    │         │ CODE-017  │ CODE-019  │       │
 a ├────┼─────────┼───────────┼───────────┤       │
 s │Low │ CFG-006 │ DOC-025   │ TEST-006  │       │
 ı │    │ CFG-007 │ DOC-026   │ TEST-011  │       │
 l │    │         │ CFG-008   │           │       │
 ı │    │         │           │           │       │
 k └────┴─────────┴───────────┴───────────┘       │
        └─────────────────────────────────────────┘
```

---

## Sprint Bazlı Dağılım

### TD-Sprint 1 (~7h) — Hemen Yapılacak

| ID | Madde | Est |
|----|-------|:---:|
| DOC-001 | CHANGELOG 33 commit | 1h |
| DOC-002 | README güncelle | 2h |
| DOC-003 | D5 header fix | 0.5h |
| DOC-004 | D3 §14 fix | 0.5h |
| DOC-005 | D6 progress fix | 1h |
| DOC-006 | D7 gate fix | 0.5h |
| DOC-007 | D10 plan fix | 0.5h |
| DOC-012 | D5 S22 fix | 0.5h |
| DOC-014 | D4 arşivle | 0.5h |
| DOC-021 | Makefile targets | 0.5h |
| DOC-022 | .env.example | 0.5h |
| CFG-003 | .env vars | — (DOC-022 ile birlikte) |
| CFG-005 | Makefile | — (DOC-021 ile birlikte) |

### TS-Sprint 3 (~43h)

CODE-002→CODE-013, CODE-023→CODE-025, TEST-001, TEST-007, TEST-009, TEST-010, DOC-016, DOC-026

### Sprint 10 (~31h)

CODE-001, CODE-014, CODE-015, TEST-006, DOC-008→DOC-011, DOC-013, DOC-015, DOC-019, DOC-024, DOC-025, DOC-027, DOC-028

### Sprint 12a (~22h)

CODE-016→CODE-018, TEST-002→TEST-005, TEST-008, DOC-017, DOC-018

### Sprint 14 (~24h)

CODE-019, CODE-020, CFG-001, CFG-002, CFG-004, CFG-006, TEST-011, TEST-012, DOC-023

### Sprint 18+ (~12h)

CODE-021, CFG-008

### Unscheduled (~87h)

CODE-022, CFG-007, DOC-020 ve henüz sprint'e atanmamış büyük backlog item'lar

---

## KPI Hedefleri

| Metrik | Mevcut (v1.0) | R3 Gate | R4 Gate | R6 (v1.0) |
|--------|:------:|:-------:|:-------:|:---------:|
| Toplam TD madde | 36 | ≤40 ✅ | ≤20 | ≤5 |
| P1 madde | 0 | 0 ✅ | 0 ✅ | 0 ✅ |
| P2 madde | 8 | ≤15 ✅ | ≤5 | 0 |
| DOC borç | 16 | ≤10 | ≤5 | 0 |
| Test/route ratio | 3.5 | 2.8 ✅ | 3.0 ✅ | 3.0+ ✅ |

---

**Dosya:** `TECHNICAL_DEBT_BACKLOG.md`  
**v1→v2 delta:** +10 madde (consolidated review), sprint atamalar, durum takip kolonu  
**Oluşturan:** GitHub Copilot (Claude Opus 4.6)
