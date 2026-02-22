# UI-S10 — Technical Debt Cleanup Sprint

**Sprint:** UI-S10 / 10
**Süre:** 1 hafta
**Effort:** S
**Durum:** ✅ Tamamlandı — 2026-02-22
**Bağımlılık:** UI-S01–UI-S09 tamamlanmış olmalı
**Önceki:** UI-S09 — Accessibility, Dark Mode & Polish
**Sonraki:** UI-S11 (planlı değil — S10 UI modernizasyonunu kapatır)

---

## Amaç

S01–S09 sonrası geride kalan teknik borcu temizle:

- `page-header` CSS class → `pg-view-header` migration
- Hardcoded inline renk (`#64748b`, `#94a3b8`, `--sap-*`) → `var(--pg-*)` token
- `empty-state__icon` emoji pattern → `PGEmptyState.html()` component
- Kullanılmayan `--sap-accent` alias kaldır

---

## Görevler

### UI-S10-T01 — data_factory.js Migration

**Kapsam:** Renk sabitleri silinir, tüm badge'ler PGStatusRegistry'e taşınır.

- Silinen sabitler: `STATUS_COLORS`, `WAVE_COLORS`, `LOAD_COLORS`, `RECON_COLORS`
- Eklendi: `_badge(status)` yardımcı fonksiyon → `PGStatusRegistry.badge()`
- `PGStatusRegistry.MAP` genişletildi (10 yeni statü: `profiled`, `cleansed`, `migrated`, `archived`, `planned`, `running`, `failed`, `aborted`, `matched`, `variance`)
- No-program → `PGEmptyState.html({ icon: 'data', ... })`
- `page-header` → `pg-view-header` + `PGBreadcrumb`
- Hardcoded renkler → `var(--pg-color-positive)`, `var(--pg-color-warning)`, `var(--pg-color-negative)`, `var(--pg-color-surface)`, `var(--pg-color-text-secondary)`
- Tab button emoji kaldırıldı (`📦 Data Objects` → `Data Objects`)

**Dosyalar:**
- `static/js/components/pg_status_registry.js` — 10 yeni statü eklendi
- `static/js/views/data_factory.js` — komple badge/header/token migration

---

### UI-S10-T02 — discover.js + suite_folders.js Migration

- `discover.js`: `page-header` → `pg-view-header`, empty state → `PGEmptyState`, tab emoji kaldır
- `suite_folders.js`: no-program → `PGEmptyState`, header → `pg-view-header`, 2 iç empty state → `PGEmptyState`

**Dosyalar:**
- `static/js/views/discover.js`
- `static/js/views/suite_folders.js`

---

### UI-S10-T03 — backlog.js + testing_shared.js + timeline.js Migration

- `backlog.js`: no-program, list/sprint/config empty state'ler → `PGEmptyState`; detail `page-header` → `pg-view-header`; emoji buton labelleri temizlendi
- `testing_shared.js`: `noProgramHtml()` → tek satır `PGEmptyState.html()`
- `timeline.js`: `renderSkeleton()` / `renderError()` / `renderNoProgram()` → `pg-view-header` / `PGEmptyState`

**Dosyalar:**
- `static/js/views/backlog.js`
- `static/js/views/testing_shared.js`
- `static/js/views/timeline.js`

---

### UI-S10-T04 — dashboard.js + executive_cockpit.js + env_matrix.js Migration

- `dashboard.js`: no-program, error, empty gadgets → `PGEmptyState`; header → `pg-view-header`
- `executive_cockpit.js`: 4 `page-header` / empty state → `pg-view-header` / `PGEmptyState`; `console.error` kaldırıldı
- `env_matrix.js`: no-program, 3 empty state → `PGEmptyState`; header → `pg-view-header`

**Dosyalar:**
- `static/js/views/dashboard.js`
- `static/js/views/executive_cockpit.js`
- `static/js/views/env_matrix.js`

---

### UI-S10-T05 — project_setup.js Inline Color Tokenization

30+ inline hardcoded renk → `var(--pg-*)`:

| Eski | Yeni |
|------|------|
| `color:#64748b` | `color:var(--pg-color-text-secondary)` |
| `color:#6b7280` | `color:var(--pg-color-text-secondary)` |
| `color:#94a3b8` | `color:var(--pg-color-text-tertiary)` |
| `color:#dc2626` / `#b91c1c` | `color:var(--pg-color-negative)` |
| `background:#f8fafc` | `background:var(--pg-color-bg)` |
| `background:#fef2f2` | `background:var(--pg-color-red-50)` |
| `background:#fff5f5;border:1px solid #f6caca` | `background:var(--pg-color-red-50);border:1px solid var(--pg-color-negative)` |
| `#e2e8f0` / `#e5e7eb` (border) | `var(--pg-color-border)` |
| `border-top:1px solid #f1f5f9` | `border-top:1px solid var(--pg-color-border)` |
| `var(--sap-text-secondary)` | `var(--pg-color-text-secondary)` |
| `borderColor='var(--sap-blue)'` | `borderColor='var(--pg-color-primary)'` |

Ayrıca:
- `loadHierarchyTab` hata state → `PGEmptyState.html({ icon: 'warning', ... })`
- `renderPlaceholder()` `empty-state__icon` → `PGEmptyState.html()`

**Dosya:**
- `static/js/views/project_setup.js`

---

### UI-S10-T06 — main.css --sap-* Phase-Out (Partial)

- `--sap-accent` kaldırıldı (0 referans kalmıştı — T01'de data_factory.js'den temizlenmişti)
- Tüm diğer `--sap-*` alias'ları korundu (hâlâ 300+ referans; tam migration sonraki sprint'lere)
- Deprecation yorumu güncellendi: "UI-S02'de silinecek" → doğru durum belgelendi

**Dosya:**
- `static/css/main.css`

---

## Deliverables

- [x] `pg_status_registry.js` — 10 yeni Data Factory statüsü eklendi
- [x] `data_factory.js` — `STATUS_COLORS`/`WAVE_COLORS`/`LOAD_COLORS`/`RECON_COLORS` kaldırıldı; `_badge()` eklendi; tüm renkler pg token
- [x] `discover.js` — `pg-view-header` + `PGEmptyState`
- [x] `suite_folders.js` — `pg-view-header` + `PGEmptyState`
- [x] `backlog.js` — tüm empty state'ler `PGEmptyState`; detail header'lar `pg-view-header`
- [x] `testing_shared.js` — `noProgramHtml()` → `PGEmptyState.html()`
- [x] `timeline.js` — `renderSkeleton/Error/NoProgram()` → `pg-view-header` / `PGEmptyState`
- [x] `dashboard.js` — no-program/error/empty → `PGEmptyState`; header → `pg-view-header`
- [x] `executive_cockpit.js` — 4 `page-header` → `pg-view-header`/`PGEmptyState`
- [x] `env_matrix.js` — header + 4 empty state migration
- [x] `project_setup.js` — 30+ inline renk → `var(--pg-*)` token
- [x] `main.css` — `--sap-accent` kaldırıldı; deprecation yorumu güncellendi

---

## Kalan Teknik Borç (UI-S10 Sonrası)

Aşağıdaki dosyalar henüz tam `--pg-*` migration'ına geçmedi (S11 kapsamı):

| Dosya | Kalan Sorun |
|-------|-------------|
| `explore_requirements.js` | `var(--sap-*)` inline stil kullanımları |
| `explore_workshops.js` | `var(--sap-*)` inline stil kullanımları |
| `explore_workshop_detail.js` | `var(--sap-*)` inline stil kullanımları |
| `explore_hierarchy.js` | `var(--sap-*)` inline stil kullanımları |
| `explore_dashboard.js` | `var(--sap-*)` inline stil kullanımları |
| `explore-shared.js` | `var(--sap-*)` component template |
| `test_planning.js` | `var(--sap-*)` inline stil kullanımları |
| `cutover.js` | `var(--sap-*)` bazı inline stil artıkları |
| `backlog.js` | `var(--sap-*)` bazı inline stil artıkları |
| `main.css` | 300+ `var(--sap-*)` iç kullanım — gradual migration |
