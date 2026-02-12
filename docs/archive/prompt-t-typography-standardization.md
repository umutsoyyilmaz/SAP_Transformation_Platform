# PROMPT T — Typography Standardization

**Kapsam:** Proje geneli font tutarlılığı  
**Dosyalar:** `index.html`, `main.css`, `explore-tokens.css`, 5 JS dosyası  
**Effort:** ~3.5h  

---

## 1. Audit Özeti

### Tespit: 5 Ana Sorun

| # | Sorun | Etki |
|---|-------|------|
| **T-1** | Font hiç yüklenmiyor — `'72'` ve `'DM Sans'` ne `@font-face` ne CDN ile tanımlı. Tarayıcı system font'a düşüyor | Tüm platform |
| **T-2** | İki farklı font-family stack: `main.css` → `'72','Segoe UI',Arial` vs `explore-tokens.css` → `'72','DM Sans',-apple-system,'Segoe UI'` | Tüm platform |
| **T-3** | 3 farklı birim karışık: **100 px** + **44 rem** + **24 var()** declaration (CSS) + **241 px** + **18 rem** (JS inline) | Tüm platform |
| **T-4** | 19 farklı rem değeri (0.65–1.5rem) → subpixel render (9.1px, 9.5px, 10.1px, 11.2px, 12.6px vb.) | Bulanık metin |
| **T-5** | font-weight 600 çok baskın (CSS: 44, JS: 50) — normal body text bile semibold | Görsel ağırlık |

### Sayısal Envanter

```
Font-size unique değer:  31 (CSS) + 16 (JS) = ~42 unique
Birim dağılımı:          px: 341  |  rem: 62  |  var(): 24
Font-weight:             400: 2  |  500: 21  |  600: 94  |  700: 39  |  bold: 1
Line-height:             1, 1.3, 1.4, 1.5, 18px  (5 farklı)
Letter-spacing:          0.03em, 0.05em, 0.3px, 0.5px  (4 farklı)
```

---

## 2. Hedef Type Scale

### 2A. CSS Variables — `main.css :root`'a ekle

**Mevcut :root bloğunun sonuna (L45, `--transition: 0.2s ease;` satırından sonra) ekle:**

```css
    /* ── Typography Scale ─────────────────────────────────────────── */
    --font-family:    'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    --font-mono:      'JetBrains Mono', 'Fira Code', 'Consolas', 'Menlo', monospace;

    --fs-2xs:   10px;    /* micro: timestamps, tiny badges, counters */
    --fs-xs:    11px;    /* small: badge labels, captions, meta text */
    --fs-sm:    12px;    /* secondary: table cells, form labels, hints */
    --fs-base:  13px;    /* body: descriptions, list items, paragraphs */
    --fs-md:    14px;    /* default: body baseline (inherited) */
    --fs-lg:    16px;    /* emphasis: section headings, card titles */
    --fs-xl:    18px;    /* heading: modal titles, card headers */
    --fs-2xl:   22px;    /* page: page titles, h2 */
    --fs-3xl:   28px;    /* hero: KPI large numbers */
    --fs-4xl:   48px;    /* display: empty state icons */

    --fw-normal:    400;
    --fw-medium:    500;
    --fw-semibold:  600;
    --fw-bold:      700;

    --lh-tight:     1.2;
    --lh-normal:    1.4;
    --lh-relaxed:   1.5;

    --ls-normal:    0;
    --ls-wide:      0.02em;
    --ls-widest:    0.05em;
```

### 2B. Font Loading — `index.html` `<head>`'e ekle

**`<title>` satırından sonra, `<link rel="stylesheet">` satırlarından önce ekle:**

```html
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

**Neden Inter?**
- `'72'` (SAP proprietary) hiçbir yerde yüklenmemiş — browser zaten system font kullanıyor
- Inter, SaaS/Enterprise UI standardı (Linear, Vercel, Notion, Figma)
- Geniş Unicode desteği (Türkçe karakterler dahil)
- Tabular figures, clear at small sizes (10-12px)
- Ücretsiz, Google Fonts CDN ile hızlı

### 2C. Base Styles Güncelleme — `main.css` L54-60

**FIND (L54-60):**
```css
html, body {
    height: 100%;
    font-family: '72', 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    color: var(--sap-text-primary);
    background: var(--sap-bg);
}
```

**REPLACE:**
```css
html, body {
    height: 100%;
    font-family: var(--font-family);
    font-size: var(--fs-md);
    line-height: var(--lh-relaxed);
    color: var(--sap-text-primary);
    background: var(--sap-bg);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
```

### 2D. explore-tokens.css — Font Variable Sync (L108-116)

**FIND:**
```css
    --exp-font-family:      '72', 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --exp-font-mono:        'JetBrains Mono', 'Fira Code', 'Menlo', monospace;
    --exp-font-size-xs:     11px;
    --exp-font-size-sm:     12px;
    --exp-font-size-md:     14px;
    --exp-font-size-lg:     16px;
    --exp-font-size-xl:     20px;
    --exp-font-size-2xl:    24px;
    --exp-font-size-3xl:    30px;
```

**REPLACE:**
```css
    --exp-font-family:      var(--font-family);
    --exp-font-mono:        var(--font-mono);
    --exp-font-size-xs:     var(--fs-xs);     /* 11px */
    --exp-font-size-sm:     var(--fs-sm);     /* 12px */
    --exp-font-size-md:     var(--fs-md);     /* 14px */
    --exp-font-size-lg:     var(--fs-lg);     /* 16px */
    --exp-font-size-xl:     var(--fs-xl);     /* 18px */
    --exp-font-size-2xl:    var(--fs-2xl);    /* 22px */
    --exp-font-size-3xl:    var(--fs-3xl);    /* 28px */
```

---

## 3. main.css rem → var() Dönüşüm Tablosu (44 değişiklik)

Her satır `font-size: X.XXrem` → `font-size: var(--fs-YY)` olacak.

### Conversion Map

| rem Değeri | ≈ px | Hedef Variable | Scale Step |
|:----------:|:----:|:--------------:|:----------:|
| 0.65rem | 9.1 | `var(--fs-2xs)` | 10px |
| 0.68rem | 9.5 | `var(--fs-2xs)` | 10px |
| 0.7rem | 9.8 | `var(--fs-2xs)` | 10px |
| 0.72rem | 10.1 | `var(--fs-2xs)` | 10px |
| 0.73rem | 10.2 | `var(--fs-2xs)` | 10px |
| 0.75rem | 10.5 | `var(--fs-xs)` | 11px |
| 0.8rem | 11.2 | `var(--fs-xs)` | 11px |
| 0.85rem | 11.9 | `var(--fs-sm)` | 12px |
| 0.9rem | 12.6 | `var(--fs-base)` | 13px |
| 0.95rem | 13.3 | `var(--fs-base)` | 13px |
| 1rem | 14.0 | `var(--fs-md)` | 14px |
| 1.05rem | 14.7 | `var(--fs-md)` | 14px |
| 1.1rem | 15.4 | `var(--fs-lg)` | 16px |
| 1.5rem | 21.0 | `var(--fs-2xl)` | 22px |

### Satır Bazlı Liste

```
L578   .tab-btn                       0.9rem   → var(--fs-base)
L604   .detail-section h3             1rem     → var(--fs-md)
L618   .detail-list dt                0.85rem  → var(--fs-sm)
L624   .detail-list dd                0.85rem  → var(--fs-sm)
L707   .card-header h2                1.1rem   → var(--fs-lg)
L714   @media .tab-btn                0.8rem   → var(--fs-xs)
L754   .scenario-card__header h3      1.05rem  → var(--fs-md)
L759   .scenario-card__desc           0.85rem  → var(--fs-sm)
L779   .meta-label                    0.75rem  → var(--fs-xs)
L821   .workshop-card__type           1.5rem   → var(--fs-2xl)
L835   .workshop-card__body h4        0.95rem  → var(--fs-base)
L842   .workshop-card__meta           0.8rem   → var(--fs-xs)
L849   .workshop-card__counts         0.8rem   → var(--fs-xs)
L893   .form-input--sm                0.85rem  → var(--fs-sm)
L912   .form-input--sm (dup)          0.85rem  → var(--fs-sm)
L921   .matrix-table td               0.8rem   → var(--fs-xs)
L936   .matrix-col-header             0.75rem  → var(--fs-xs)
L949   .matrix-cell                   1rem     → var(--fs-md)
L1486  .heatmap-table td              0.85rem  → var(--fs-sm)
L1532  .tab                           0.9rem   → var(--fs-base)
L1569  .notif-badge                   0.65rem  → var(--fs-2xs)
L1623  .notif-item__icon              1.1rem   → var(--fs-lg)
L1631  .notif-item__title             0.85rem  → var(--fs-sm)
L1637  .notif-item__message           0.8rem   → var(--fs-xs)
L1644  .notif-item__time              0.7rem   → var(--fs-2xs)
L1690  .ai-query-input-area textarea  .95rem   → var(--fs-base)
L1706  .ai-query-toggle               .85rem   → var(--fs-sm)
L1717  .ai-query-hints                .85rem   → var(--fs-sm)
L1729  .hint-chip                     .8rem    → var(--fs-xs)
L1748  .glossary-chip                 .8rem    → var(--fs-xs)
L1764  .sql-code                      .85rem   → var(--fs-sm)
L1776  .ai-query-warning              .9rem    → var(--fs-base)
L1813  .ai-history-query              .85rem   → var(--fs-sm)
L1822  .ai-history-meta               .75rem   → var(--fs-xs)
L1836  .ai-badge                      .75rem   → var(--fs-xs)
L1852  .sugg-badge                    0.65rem  → var(--fs-2xs)
L1887  .sugg-dropdown__title          0.9rem   → var(--fs-base)
L1916  .sugg-item__icon               1rem     → var(--fs-md)
L1926  .sugg-item__title              0.85rem  → var(--fs-sm)
L1936  .sugg-item__meta               0.73rem  → var(--fs-2xs)
L1947  .sugg-tag                      0.68rem  → var(--fs-2xs)
L1955  .sugg-conf                     0.72rem  → var(--fs-2xs)
L1981  (unnamed)                      0.8rem   → var(--fs-xs)
L2009  .sugg-empty                    0.85rem  → var(--fs-sm)
```

---

## 4. JS Inline rem → px Dönüşüm (18 değişiklik)

JS inline style'larda var() kullanmak karmaşıktır; pragmatik çözüm rem→px.

### integration.js (13 rem → px)

| Satır | Mevcut | Yeni |
|:-----:|--------|------|
| 161 | `font-size:.75rem` | `font-size:11px` |
| 174 | `font-size:.85rem` | `font-size:12px` |
| 187 | `font-size:.85rem` | `font-size:12px` |
| 251 | `font-size:.85rem` | `font-size:12px` |
| 255 | `font-size:.85rem` | `font-size:12px` |
| 260 | `font-size:.85rem` | `font-size:12px` |
| 264 | `font-size:.85rem` | `font-size:12px` |
| 269 | `font-size:.85rem` | `font-size:12px` |
| 273 | `font-size:.85rem` | `font-size:12px` |
| 309 | `font-size:.8rem` | `font-size:11px` |
| 313 | `font-size:.8rem` | `font-size:11px` |
| 322 | `font-size:.8rem` | `font-size:11px` |
| 323 | `font-size:.8rem` | `font-size:11px` |

### program.js (5 rem → px)

| Satır | Mevcut | Yeni |
|:-----:|--------|------|
| 133 | `font-size:1.5rem` | `font-size:22px` |
| 246 | `font-size:0.85rem` | `font-size:12px` |
| 247 | `font-size:0.8rem` | `font-size:11px` |
| 254 | `font-size:0.85rem` | `font-size:12px` |
| 258 | `font-size:0.8rem` | `font-size:11px` |

> **Not:** `ai_query.js`, `data_factory.js`, `integration.js`, `notification.js` dosyalarındaki `padding:1rem`, `margin-bottom:1rem` gibi **spacing** rem değerleri font ile ilgili değildir — opsiyonel olarak `16px`/`24px`'e çevrilebilir ama zorunlu değildir.

---

## 5. Opsiyonel İyileştirmeler (İleri Sprint)

### 5A. explore-tokens.css Hardcoded px → var()

Bu değerler zaten scale ile uyumlu. İsteğe bağlı:

```
L248  .exp-kpi-card__value     24px → var(--fs-2xl)
L259  .exp-kpi-card__label     11px → var(--fs-xs)
L268  .exp-kpi-card__sub       11px → var(--fs-xs)
L281  .exp-metric-bar__label   11px → var(--fs-xs)
L293  .exp-metric-bar__legend  11px → var(--fs-xs)
L498  .exp-fb-btn              13px → var(--fs-base)
L512  .exp-fb-chip             12px → var(--fs-sm)
L749  .exp-tree-node__chevron  10px → var(--fs-2xs)
```

### 5B. font-weight Normalizasyonu (Ayrı Sprint)

Mevcut: `600` her yerde baskın (CSS: 44, JS: 50). İdeal kullanım:
- `400`: body text, descriptions, table cells
- `500`: labels, names, navigation
- `600`: headings, buttons, active states
- `700`: page titles, KPI hero numbers

---

## 6. Verification Checklist

- [ ] `index.html <head>`: Inter + JetBrains Mono Google Fonts `<link>` tagları
- [ ] `main.css :root`: `--fs-2xs`..`--fs-4xl` + `--fw-*` + `--lh-*` + `--ls-*` + `--font-family` + `--font-mono`
- [ ] `main.css body`: `var(--font-family)`, `var(--fs-md)`, `var(--lh-relaxed)`, antialiased
- [ ] `main.css`: **0 rem** font-size declaration (44 → 0)
- [ ] `explore-tokens.css`: `--exp-font-family: var(--font-family)`, `--exp-font-mono: var(--font-mono)`
- [ ] `explore-tokens.css`: `--exp-font-size-*` hepsi `var(--fs-*)` referans
- [ ] `integration.js`: 0 rem font-size (13 → 0)
- [ ] `program.js`: 0 rem font-size (5 → 0)
- [ ] Tarayıcı DevTools: Inter font yükleniyor
- [ ] Tüm sayfalar: subpixel blur yok, metin net render

---

## 7. Doğrulama Komutu

```bash
echo "=== Kalan rem (0 olmalı) ==="
grep -c 'font-size:.*rem' static/css/main.css
grep -rc 'font-size:.*rem' static/js/views/integration.js static/js/views/program.js

echo "=== var() kullanımı ==="
grep -c 'font-size:.*var(' static/css/main.css
grep -c 'font-size:.*var(' static/css/explore-tokens.css

echo "=== Font family ==="
grep 'font-family' static/css/main.css static/css/explore-tokens.css | grep -v inherit

echo "=== Font loading ==="
grep 'fonts.googleapis' templates/index.html
```

---

## 8. Sıralama ve Commit

**Bağımlılık:** T bağımsız — diğer prompt'lardan önce uygulanmalı.

| Sıra | Prompt | Effort |
|:----:|:------:|:------:|
| **1** | **T — Typography** | 3.5h |
| 2 | F — KPI Standardization | 3h |
| 3 | H — Hierarchy UI | 2h |
| 4 | G — Backlog Redesign | 4h |

```
chore(typography): Inter font, rem→var(), unified type scale

- Load Inter + JetBrains Mono via Google Fonts CDN
- Add 10-step type scale as CSS custom properties
- Convert 44 rem declarations to var() in main.css
- Sync explore-tokens.css font variables to main.css root
- Convert 18 JS inline rem to px (integration.js, program.js)
- Add font-smoothing for crisp text rendering
```

---
---

# PROMPT T-DOC — Doküman Güncellemeleri (Typography Sonrası)

Bu bölüm, Typography Standardization tamamlandıktan sonra 3 dokümanı günceller.

**Dosyalar:**
- `docs/plans/PROGRESS_REPORT.md`
- `docs/specs/sap_transformation_platform_architecture_v2.md`
- `docs/plans/SAP_Platform_Project_Plan_v2.md`

**Effort:** ~30min

---

## D-1. PROGRESS_REPORT.md Güncellemeleri

### D-1A. Özet Tablosu — CSS LOC güncelle

**FIND (L17):**
```markdown
| CSS LOC | 3,244 |
```

**REPLACE:**
```markdown
| CSS LOC | ~3,300 |
```

> Not: Typography variables ile ~50 satır artış. `wc -l static/css/*.css` ile doğrula.

### D-1B. Yeni Sprint Kaydı

**Mevcut "Release 3 Gate Checklist" bölümünden sonra (L77 civarı), şunu ekle:**

```markdown

### UI-Sprint: Typography & Design Consistency

| Sprint | Açıklama | Durum | Gate |
|--------|----------|-------|------|
| UI-Sprint (T) | Typography Standardization | ✅ Tamamlandı | ✅ |
| UI-Sprint (F) | KPI Dashboard Standardization | ⬜ Bekliyor | — |
| UI-Sprint (G) | Backlog Page Redesign | ⬜ Bekliyor | — |
| UI-Sprint (H) | Process Hierarchy UI İyileştirme | ⬜ Bekliyor | — |

**UI-Sprint (T) Detay:**
- Inter font ailesi yüklendi (Google Fonts CDN)
- 10 basamaklı type scale CSS custom properties olarak tanımlandı
- main.css'deki 44 rem declaration → var() dönüştürüldü
- explore-tokens.css font variables main.css ile senkronize edildi
- JS inline 18 rem → px dönüştürüldü
- Font smoothing eklendi (antialiased)
- Subpixel blur sorunu çözüldü (tüm font-size integer px)
```

### D-1C. Commit Geçmişine Ekle

Mevcut commit tablosunun sonuna:

```markdown
| NN | **UI-Sprint (T)**: Typography Standardization | `XXXXXXX` | 2026-02-XX | Inter font, 44 rem→var(), unified type scale, font smoothing |
```

### D-1D. Görev Detay

```markdown

### UI-Sprint (T): Typography Standardization — Detay

| # | Görev | Dosya(lar) | Çıktı | Durum |
|---|-------|-----------|-------|:-----:|
| T.1 | Google Fonts CDN — Inter + JetBrains Mono | templates/index.html | 3 link tag | ✅ |
| T.2 | Type scale CSS variables (20 var) | static/css/main.css :root | --fs-*, --fw-*, --lh-*, --ls-* | ✅ |
| T.3 | Body base styles update | main.css html,body | var(--font-family), antialiased | ✅ |
| T.4 | main.css rem → var() (44 declaration) | static/css/main.css | 0 rem kaldı | ✅ |
| T.5 | explore-tokens.css font sync | static/css/explore-tokens.css | --exp-font-*: var(--fs-*) | ✅ |
| T.6 | JS inline rem → px (18 değişiklik) | integration.js, program.js | 0 rem kaldı | ✅ |
```

---

## D-2. sap_transformation_platform_architecture_v2.md Güncellemeleri

### D-2A. Revizyon Geçmişi — Yeni Satır (L8 tablosu)

```markdown
| 2.4 | 2026-02-XX | **[REVISED]** §6 UI/UX Mimarisi: Typography standardization. Inter font ailesi, 10-step type scale (CSS custom properties), design token sistemi tanımlandı. §6.4 eklendi. |
```

### D-2B. §6.3'ten sonra yeni bölüm — §6.4 Design Token Sistemi

**§6.3 Global Özellikler bölümünden sonra, `## 7.` bölümünden önce şunu ekle:**

```markdown

### 6.4 Design Token Sistemi (Typography)

Platform, tutarlı görsel dil için CSS Custom Properties tabanlı design token sistemi kullanır.

**Font Ailesi:**
- UI: Inter (Google Fonts CDN — 400/500/600/700 weights)
- Mono: JetBrains Mono (code blokları, process kodları, terminal çıktıları)

**Type Scale (10 basamak):**

| Token | Değer | Kullanım |
|-------|:-----:|----------|
| `--fs-2xs` | 10px | Micro labels, timestamps, counters |
| `--fs-xs` | 11px | Badge labels, captions, meta text |
| `--fs-sm` | 12px | Table cells, form labels, secondary text |
| `--fs-base` | 13px | Body text, descriptions, paragraphs |
| `--fs-md` | 14px | Default body baseline (html root) |
| `--fs-lg` | 16px | Section headings, card titles |
| `--fs-xl` | 18px | Modal titles, card headers |
| `--fs-2xl` | 22px | Page titles (h2) |
| `--fs-3xl` | 28px | KPI hero numbers |
| `--fs-4xl` | 48px | Display (empty state icons) |

**Font Weight:**
- `--fw-normal` (400): Body text, descriptions
- `--fw-medium` (500): Labels, navigation items
- `--fw-semibold` (600): Headings, buttons, active states
- `--fw-bold` (700): Page titles, KPI hero numbers

**Katman Yapısı:**
```
main.css :root          → Temel token'lar (--fs-*, --fw-*, --lh-*, --font-family)
explore-tokens.css      → Alias token'lar (--exp-font-size-* → var(--fs-*))
Component CSS           → Token referansları (font-size: var(--fs-sm))
JS inline styles        → px değerler (scale ile uyumlu: 10, 11, 12, 13, 14px)
```

**Kurallar:**
1. CSS'de rem birimi kullanılmaz — tüm font-size'lar var() veya px
2. Yeni component eklerken type scale dışında font-size tanımlanmaz
3. Font-family her zaman `var(--font-family)` veya `inherit` üzerinden kullanılır
4. JS inline style'larda font-size sadece scale'deki px değerleri kullanır
```

### D-2C. §7.1 veya §7.3 Teknoloji Stack — Yeni Satır

Mevcut tablo satırlarının arasına (Frontend satırından sonra):

```markdown
| Typography | Inter + JetBrains Mono (Google Fonts CDN) | 10-step type scale, CSS custom properties |
```

---

## D-3. SAP_Platform_Project_Plan_v2.md Güncellemeleri

### D-3A. Tamamlanan Bölüme Ekle

**"TAMAMLANAN" bloğunun sonuna (`✅ Monitoring & Observability` satırından sonra) ekle:**

```
✅ UI-Sprint (T): Typography Standardization (Inter font, type scale, rem→var())
```

### D-3B. Sprint Detay — Yeni Section

**FE-Sprint detayı olan bölümden sonra ekle:**

```markdown

### UI-Sprint: Typography & Design Consistency

| Görev | Dosya | Effort | Bağımlılık |
|-------|-------|:------:|-----------|
| T: Typography Standardization | index.html, main.css, explore-tokens.css, 2 JS | 3.5h | — |
| F: KPI Dashboard Standardization | explore-shared.js, 6 view JS, explore-tokens.css | 3h | T |
| H: Process Hierarchy UI İyileştirme | explore_hierarchy.js, explore-tokens.css | 2h | T, F |
| G: Backlog Page Redesign | backlog.js, main.css | 4h | T, F |
| **Toplam** | | **12.5h** | |
```

### D-3C. CSS LOC Güncelle

Mevcut metriklerde CSS LOC referansı varsa:

```markdown
| CSS LOC | ~3,300 |
```

---

## D-4. TECHNICAL_DEBT.md Güncelleme (Opsiyonel)

Mevcut CODE borç listesine:

```markdown
| 26 | CODE-026 | Typography: JS inline rem→px (18 değişiklik) | P3 | 0.5h | UI-Sprint | ✅ | Prompt T |
| 27 | CODE-027 | Typography: CSS rem→var() (44 declaration) | P3 | 1h | UI-Sprint | ✅ | Prompt T |
| 28 | CODE-028 | font-weight normalization (600→400 body text) | P3 | 2h | UI-Sprint+ | ⬜ | Prompt T §5B |
```
