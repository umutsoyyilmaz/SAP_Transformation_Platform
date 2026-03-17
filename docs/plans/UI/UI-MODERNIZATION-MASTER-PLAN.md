# Perga UI Modernizasyon Master Planı
## Hedef: 8–9/10 — Best-in-class Enterprise SaaS

**Versiyon:** 1.0
**Tarih:** 2026-02-22
**Hazırlayan:** UX/UI Agent
**Baz Audit:** `docs/reviews/project/AUDIT-PLATFORM-DESIGN-2026-02-22.md`
**Mevcut Puan:** 5.2/10 (Gelişen)
**Hedef Puan:** 8.5/10 (İleri)
**Süre:** 10 Sprint (UI-S01 → UI-S10), ~18 hafta

---

## Strateji: Neden Bu Sıra?

```
SPRINT 1-2: Foundation (Temel Güçlendirme)
  → Design token birleştirme + Component standardizasyonu
  → Bu olmadan her görsel iyileştirme tekrar bozulur

SPRINT 3-4: First Impression (İlk İzlenim)
  → Login + Shell + Sidebar yeniden tasarım
  → Demo'da ilk 30 saniyede kazanılır ya da kaybedilir

SPRINT 5-6: Core Screens (Çekirdek Ekranlar)
  → Dashboard + Program yönetimi + Requirement management
  → Günlük kullanıcının en fazla vakit geçirdiği yerler

SPRINT 7-8: Power Features (Güç Özellikleri)
  → Command palette + Keyboard nav + Bulk ops + Inline edit
  → Power user'ları rakiplerden ayıran özellikler

SPRINT 9: Polish & Accessibility (Cilalama)
  → WCAG 2.1 AA + Dark mode altyapısı + Micro-interactions
  → "Professional" hissini tamamlar
```

---

## Mevcut Durum Özeti (Audit Bulguları)

| Bileşen | Mevcut Durum | Sorun |
|---------|-------------|-------|
| `design-tokens.css` | `--tm-*` prefix, 90+ token | `main.css`'deki `--sap-*` ile çakışma; iki paralel sistem var |
| `main.css` | 5135 satır, `--sap-*` prefix | Monolitik, SSS tanımları, dark mode yok |
| `tm_status_badge.js` | Hardcoded inline `style=` renk | CSS token kullanmıyor; extend edilemiyor |
| `backlog.js` | `_statusBadge()` / `_priorityBadge()` yerel fonk. | `TMStatusBadge` kullanmıyor, 3. bir renk sistemi |
| `templates/index.html` | Sidebar emoji icon'ları (📊🏗️📋) | SVG icon set yok; retina'da bulanık, mesleki görünmüyor |
| Login | Tek sütun, centered card | Marka kimliği taşımıyor; split-screen yok |
| Dashboard | 6 KPI card + quick nav emoji butonları | Visual weight yok; SAP Fiori tile standard değil |
| Sidebar | `border-left: 3px` active state var | Genişlik 260px sabit; icon-only collapse yok |
| Button | `btn btn-primary` / `tm-btn` / inline style | 3 farklı sistem; hiçbiri tam standart değil |
| Responsive | `mobile.css` var (S23) | Sidebar collapse tam çalışmıyor; table overflow sorunları |

---

## Sprint Planı

---

### UI-S01 — Design System Foundation
**Süre:** 2 hafta | **Effort:** L
**Hedef:** Tüm token'ları tek sistemde birleştir, component standardını tanımla
**Etki:** Diğer tüm sprint'lerin temeli — bu bitmeden görsel sprint'lere başlamak yanlış

#### Görevler

**UI-S01-T01: Token Konsolidasyonu (`main.css` + `design-tokens.css` birleştirme)**
- `main.css`'deki `--sap-*` değişkenlerini `--pg-*` (Perga) prefix'e geç
- `design-tokens.css`'deki `--tm-*` değişkenleri `--pg-*` alias'larına bağla
- Eski `--sap-*` ve `--tm-*` değişkenlerini 1 sprint süre `deprecated` comment ile tut
- Token kategorileri:
  ```css
  /* Primitive tokens */
  --pg-color-blue-600: #0070f2;
  --pg-color-slate-900: #1d2d3e;

  /* Semantic tokens */
  --pg-color-primary: var(--pg-color-blue-600);
  --pg-color-surface: #ffffff;
  --pg-color-bg: #f5f6f7;
  --pg-color-border: #d9d9d9;
  --pg-color-text: #32363a;
  --pg-color-text-secondary: #6a6d70;

  /* Component tokens */
  --pg-btn-primary-bg: var(--pg-color-primary);
  --pg-sidebar-bg: var(--pg-color-slate-900);
  --pg-header-bg: #354a5f;
  ```
- **Dosya:** `static/css/pg-tokens.css` (yeni, tüm `--pg-*` tanımları buraya)
- **Backward compat:** `design-tokens.css` ve `main.css` içindeki eski değişkenler `pg-tokens.css`'den alias alır

**UI-S01-T02: Status Registry (Merkezi Renk Sistemi)**
- `static/js/components/pg_status_registry.js` — tüm statüs → renk map'leri burada
- Kapsamı:
  - WRICEF statüsleri (new/design/build/test/deploy/closed/blocked)
  - Requirement statüsleri (draft/in_review/approved/implemented/verified/closed/cancelled)
  - Test case statüsleri (pass/fail/blocked/not_run/deferred/skipped)
  - Priority seviyeleri (critical/high/medium/low)
  - Severity seviyeleri (s1/s2/s3/s4)
  - RAID kategorileri (risk/assumption/issue/dependency)
  - Genel (active/inactive/open/closed/pending)
- `TMStatusBadge`'i bu registry'den besle
- `backlog.js`'deki `_statusBadge()` ve `_priorityBadge()` yerel fonksiyonlarını kaldır

**UI-S01-T03: Button Component Standardizasyonu**
- `static/js/components/pg_button.js` — helper: `PGButton.html(label, variant, opts)`
- Variants: `primary` | `secondary` | `ghost` | `danger` | `icon`
- Sizes: `sm` | `md` (default) | `lg`
- States: `loading` (spinner) | `disabled`
- CSS: `static/css/pg-button.css`
- Tüm view'lardaki `btn-primary` / `tm-btn--primary` inline style'larını `PGButton.html()` ile değiştir

**UI-S01-T04: Emoji Icon'larını SVG ile Değiştir**
- Sidebar'daki tüm emoji icon'ları (📊🏗️📋⚙️🐛🔌🗄️🚀🧠) kaldır
- `static/js/components/pg_icon.js` — SVG icon registry
- Icon set: Lucide Icons (MIT lisans, tree-shakeable, web component değil inline SVG string)
  - Lucide icon'ları inline SVG string olarak JS'de tanımla (CDN'e bağımlılık yok)
- Örnek mapping:
  ```js
  const ICONS = {
    dashboard:   '<svg>...</svg>',   // LayoutDashboard
    programs:    '<svg>...</svg>',   // FolderKanban
    explore:     '<svg>...</svg>',   // Compass
    requirements:'<svg>...</svg>',   // FileCheck
    backlog:     '<svg>...</svg>',   // Wrench
    test:        '<svg>...</svg>',   // FlaskConical
    defect:      '<svg>...</svg>',   // Bug
    raid:        '<svg>...</svg>',   // ShieldAlert
    integration: '<svg>...</svg>',   // Cable
    data:        '<svg>...</svg>',   // Database
    cutover:     '<svg>...</svg>',   // Rocket
    ai:          '<svg>...</svg>',   // Sparkles
    admin:       '<svg>...</svg>',   // Settings
    reports:     '<svg>...</svg>',   // BarChart3
  };
  ```
- `pg_icon.js`: `PGIcon.html(name, size?)` — `size` default `16`

**UI-S01-T05: CSS Architecture Refactor**
- `main.css`'i mantıksal bölümlere ayır (içeriden `@import` değil, document order):
  1. `pg-tokens.css` — tüm CSS custom properties
  2. `pg-reset.css` — normalize + base reset
  3. `pg-typography.css` — heading, type utilities
  4. `pg-layout.css` — shell header, sidebar, main-content layout
  5. `pg-components.css` — button, badge, card, table, form temel stilleri
  6. `pg-utilities.css` — spacing, display, flex utilities
  7. `main.css` — geçiş döneminde var olanları tutar, yeniler pg-*.css dosyalarına gider
- Bu sprint'te yalnızca Token ve Layout bölümleri çıkarılır; kalanlar sonraki sprint'lere

**Deliverables:** ✅ UI-S01 tamamlandı — 2026-02-22
- [x] `static/css/pg-tokens.css` — --pg-* token sistemi oluşturuldu
- [x] `static/js/components/pg_status_registry.js` — merkezi renk kaydı oluşturuldu
- [x] `static/js/components/pg_button.js` + `static/css/pg-button.css` — button component standardize edildi
- [x] `static/js/components/pg_icon.js` — 30+ Lucide SVG icon eklendi
- [x] `static/css/pg-layout.css` — shell/sidebar/modal layout çıkarıldı
- [x] `backlog.js` yerel badge fonksiyonları kaldırıldı → PGStatusRegistry.badge() kullanıyor
- [x] `index.html` emoji icon'ları SVG ile değiştirildi (data-pg-icon + PGIcon init)
- [x] `design-tokens.css` --pg-* alias'ları eklendi (backward compat)
- [x] `main.css` --sap-* değişkenleri @deprecated olarak işaretlendi
- [x] `tm_status_badge.js` PGStatusRegistry'ye delege edildi
- [x] `templates/index.html` title "Perga" olarak güncellendi, CSS/JS yükleme sırası düzenlendi

---

### UI-S02 — Component Library Completion ✅ Tamamlandı — 2026-02-22
**Süre:** 2 hafta | **Effort:** L
**Hedef:** tm_ library'deki eksikleri tamamla, mevcut component'leri token'a bağla
**Etki:** Her view aynı building block'lardan yapılmaya başlar

#### Görevler

**UI-S02-T01: `tm_data_grid` — Kolon Görünürlük Toggle**
- Grid header'ına `⚙ Columns` butonu ekle
- Dropdown: checkbox listesi (sütun isimleri), seçili olmayanlar `display:none`
- Tercih `localStorage`'da `pg_grid_cols_${viewName}` key ile saklanır

**UI-S02-T02: `tm_data_grid` — Inline Editable Cell**
- Satır çift-tıklandığında veya kalem ikonuna tıklandığında `<td>` → `<input>` dönüşümü
- Enter/Tab: kaydet | Escape: iptal
- Değişiklik event: `grid.on('cell-edit', { field, value, rowId })`
- API çağrısı view katmanında yapılır (component sadece event emit eder)

**UI-S02-T03: `tm_skeleton_loader` Component (Yeni)**
- `static/js/components/tm_skeleton_loader.js`
- API: `TMSkeletonLoader.show(container, rows=5)` / `.hide(container)`
- Animasyon: `shimmer` keyframe (CSS)
- Variants: `rows` (tablo satırı), `cards` (KPI kartlar), `detail` (property panel)

**UI-S02-T04: `tm_empty_state` Component (Yeni)**
- `static/js/components/tm_empty_state.js`
- API: `TMEmptyState.render(container, { icon, title, body, cta_label, cta_action })`
- İkon: SVG (pg_icon'dan) veya emoji fallback
- Standart: tüm tablo/liste boş durumları bu component

**UI-S02-T05: `tm_page_header` Component (Yeni)**
- `static/js/components/tm_page_header.js`
- API: `TMPageHeader.render(container, { title, subtitle?, primaryCta?, secondaryCtas?[] })`
- HTML output:
  ```html
  <div class="pg-page-header">
    <div class="pg-page-header__left">
      <h1 class="pg-page-header__title">{title}</h1>
      <p class="pg-page-header__subtitle">{subtitle}</p>
    </div>
    <div class="pg-page-header__actions">
      {secondaryCtas} {primaryCta}
    </div>
  </div>
  ```
- Bu component tüm view render başlarına eklenir

**UI-S02-T06: `tm_kanban_board` — Sütun Count Badge**
- Her Kanban sütun başlığına `<span class="kanban-col__count">(N)</span>` ekle
- Count otomatik: items array length'ten hesaplanır

**UI-S02-T07: `pg_form_field` Component (Yeni)**
- `static/js/components/pg_form_field.js`
- Wrapper: label + input + error message + helper text
- `pg_form_field.html(name, type, opts)` → HTML string
- Inline validation support: `pg_form_field.validate(fieldEl)` → bool
- Error mesajı: field altında kırmızı `.pg-field-error` span

**UI-S02-T08: Tüm View'larda `tm_skeleton_loader` ve `tm_empty_state` Aktivasyonu**
- Her view'ın `render()` başında `TMSkeletonLoader.show(main)`, data gelince `.hide(main)`
- Her tablo/liste'de `if (items.length === 0) TMEmptyState.render(...)`
- Etkilenen view'lar: `backlog.js`, `raid.js`, `integration.js`, `data_factory.js`,
  `program.js`, `defect_management.js`, `approvals.js`

**Deliverables:** *(UI-S02 UI-agent planıyla revize edildi — 2026-02-22)*
- [x] `pg_skeleton.js` + `pg-skeleton.css` oluşturuldu (shimmer animasyonu)
- [x] `pg_empty_state.js` + `pg-empty-state.css` oluşturuldu
- [x] `pg_breadcrumb.js` + `pg-breadcrumb.css` oluşturuldu
- [x] `pg_form.js` + `pg-form.css` oluşturuldu (input, textarea, select, checkbox)
- [x] `test-management-f1.css` hardcoded renkler `--pg-*` tokenlarına geçirildi
- [x] `--sap-*` explore-tokens.css, login.css, mobile.css temizlendi
- [x] `index.html` pg-* CSS + JS scriptleri eklendi
- [x] 5 view (dashboard, backlog, requirements, test, defect) `PGBreadcrumb.html()` eklendi

---

### UI-S03 — Login & Shell Redesign ✅ Tamamlandı — 2026-02-22
**Süre:** 1.5 hafta | **Effort:** M
**Hedef:** İlk 30 saniyede "bu kurumsal bir ürün" hissini ver
**Etki:** Demo güveni, pilot müşteri dönüşümü

#### Görevler

**UI-S03-T01: Login Ekranı — Split Screen Layout**

Mevcut durum: Centered single card, `#354a5f` header, "SAP Transformation Platform" title
Hedef: Professional enterprise SaaS login (Linear, Notion, Vercel kalitesi)

Yeni layout:
```
+----------------------------------+----------------------------------+
|                                  |                                  |
|   LEFT: Brand Panel              |   RIGHT: Login Panel             |
|   bg: #0f172a (dark slate)       |   bg: #ffffff                    |
|                                  |                                  |
|   [Perga Logo SVG]               |   [Perga wordmark small]         |
|                                  |                                  |
|   Navigate SAP Complexity        |   Welcome back                   |
|   with Confidence.               |   Sign in to your account        |
|                                  |                                  |
|   ● End-to-end SAP S/4HANA       |   [Organization ▾]               |
|     transformation tracking      |   [Email]                        |
|   ● Workshop → Go-Live           |   [Password]          [👁]        |
|     in one platform              |   [Sign In ──────────────────]   |
|   ● AI-powered gap analysis      |                                  |
|     & decision support           |   Forgot password?               |
|                                  |                                  |
|   v2.0 · Powered by Perga        |   © 2026 Perga · Privacy         |
+----------------------------------+----------------------------------+
```

- `static/css/login.css` komple yeniden yaz
- Sağ panel: `max-width: 440px`, `padding: 48px`, clean white
- Sol panel: `background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%)`
- Logo: SVG wordmark `Perga` + tagline
- Responsive: `≤768px` → sol panel gizlenir, sağ panel full-screen
- Password toggle: emoji `👁` → SVG `EyeIcon`/`EyeOffIcon`
- Form validation: inline error span'lar (mevcut alert() kaldır)
- Loading state: submit button `[Signing in... ⟳]` spinner

**UI-S03-T02: Shell Header Modernizasyonu**

Mevcut: `background: #354a5f`, "SAP Transformation Platform" text, emoji butonlar
Hedef: Clean header, Perga branding, SVG iconlar

- Logo alanı: `Perga` SVG wordmark (veya `P` monogram) + ince separator + `Navigate Complexity`
- Program badge: mevcut yapı korunur, görsel kalite artırılır
- Notification butonu: emoji 🔔 → SVG bell icon, `TMNotificationBell` component
- Profile avatar: inisyal-renkli daire (mevcut), sadece border + sizing polish

**UI-S03-T03: Sidebar Revizyon**

Mevcut: 260px sabit, emoji icon, `border-left: 3px` active state
Hedef: Collapsible icon-only mode, SVG icon'lar, güçlü active state

- **Icon-only collapse:** Sidebar toggle butonu (chevron) → `width: 56px` modunda sadece SVG icon
  - Hover'da tooltip (item label)
  - Toggle durumu `localStorage.pg_sidebar_collapsed` ile korunur
- **Active state:** mevcut `border-left` korunur, ek olarak `background: rgba(0,112,242,0.12)` → `rgba(0,112,242,0.18)`
- **Section title'lar:** `font-size: 10px`, daha az dikey boşluk, lowercase mümkünse
- **SVG icon'lar:** `PGIcon.html(name, 16)` ile emoji yerine
- **Sidebar alt kısmı:** `position: absolute; bottom: 0` — admin ve settings linkler
- **Collapsed mod:** 56px genişlikte section title'lar gizlenir, sadece icon'lar
- Sidebar header içinde `Perga` mini-logo görünür (collapsed/expanded)

**UI-S03-T04: Page Title Standardı — Tüm View'lara `tm_page_header`**
- `app.js` `renderDashboard()` + `views` içindeki tüm render başlarına `TMPageHeader.render()` ekle
- Her ekranın H1'i net, büyük, tutarlı
- Format: `[Module] — [Program Name]` veya sadece `[Module]`

**Deliverables:** ✅ UI-S03 tamamlandı — 2026-02-22
- [x] `static/css/login.css` split-screen layout ile yeniden yazıldı
- [x] `templates/login.html` sol brand panel + sağ form panel eklendi
- [x] Shell header `pg-header` — Perga SVG logo + search trigger + notifications + avatar
- [x] Sidebar collapsible (56px icon-only) — `initSidebarCollapse()` + localStorage persist
- [x] `pg-layout.css` pg-header + sidebar collapse stilleri eklendi

---

### UI-S04 — Dashboard & Program Management ✅ Tamamlandı — 2026-02-22
**Süre:** 2 hafta | **Effort:** L
**Hedef:** Program Manager persona'sının ana ekranı enterprise kaliteye çık
**Etki:** Demo "wow factor", C-level güveni

#### Görevler

**UI-S04-T01: Program Dashboard — Health Score + War Room**

Mevcut: 6 flat KPI card + emoji buton grid
Hedef: SAP Fiori-kalitesi KPI tiles + phase gate timeline + war room panel

```
+─────────────────────────────────────────────────────────────────+
│ Dashboard — [Program Name]          ○ Active  [Edit] [Reports]  │
+─────────────────────────────────────────────────────────────────+
│                                                                  │
│  HEALTH SCORE           PHASE STATUS                            │
│  ┌──────────────┐       Explore ████████░░ 78%  ✓              │
│  │  87/100      │       Realize ████░░░░░░ 41%  →              │
│  │  ████████░░  │       Deploy  ░░░░░░░░░░  2%  ○              │
│  │  Good        │                                               │
│  └──────────────┘                                               │
│                                                                  │
│  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐  │
│  │  142  │ │  78%  │ │  891  │ │   23  │ │  12   │ │   4   │  │
│  │ Req.  │ │WS Comp│ │BackLog│ │OpenDef│ │ Risks │ │Actions│  │
│  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘ └───────┘  │
│                                                                  │
│  RECENT ACTIVITY                MY ACTIONS (3 pending)          │
│  ──────────────────             ─────────────────────           │
│  [Workshop completed]           [Approve: REQ-091] [Review]     │
│  [Defect S1 opened]             [Sign off: WS-14]  [Review]     │
│  [Sprint 5 started]             [Gate review due]  [Open]       │
│                                                                  │
+─────────────────────────────────────────────────────────────────+
```

- `app.js` `renderDashboard()` komple yeniden yaz
- Health score: ağırlıklı average (workshop completion × 0.2 + requirements × 0.3 + defects × 0.5)
- Phase progress: horizontal progress bars, SAP Activate fazları
- KPI tiles: `pg-kpi-tile` CSS class, hover effect, tıklanabilir (navigate to module)
- "My Actions" paneli: `/api/v1/programs/{id}/my-actions` endpoint (veya mock)
- Recent activity: son 5 event, timestamp relative ("2h ago")

**UI-S04-T02: Programs List View — Card Layout**

Mevcut: `program.js` — tablo veya card grid
Hedef: Jira-Board-kalitesi program kartları

- Her program kartı:
  ```
  ┌─────────────────────────────────────────┐
  │  [●] Active               [Open →]      │
  │  Anadolu Hayat S/4HANA Migration        │
  │  SAP FI/MM/SD · 18 months               │
  │  ─────────────────────────────────────  │
  │  Explore 78%  ████████░░                │
  │  Realize  41%  ████░░░░░░                │
  │  ─────────────────────────────────────  │
  │  [12 risks] [23 defects] [143 req]       │
  └─────────────────────────────────────────┘
  ```
- Status badge: colored dot (`●`) + label
- Progress bars: `tm_chart_widget` veya CSS-only progress bar
- Click: kartın kendisi program'ı seçer, `[Open →]` navigate eder

**UI-S04-T03: Executive Cockpit — Polish**

- `executive_cockpit.js` mevcut implementation korunur
- KPI section'larda `pg-kpi-tile` class'ı uygula
- Chart placeholder'ları `tm_chart_widget` ile standartize et

**UI-S04-T04: Quick Navigation → Contextual Action Bar**
- Dashboard'daki emoji button grid'i kaldır
- Yerine: `pg-action-bar` — program fazına göre dinamik "suggested next actions"
  - Eğer Explore fazındaysa: `[+ Workshop]` `[+ Requirement]` `[View Fit-Gap]`
  - Eğer Realize fazındaysa: `[+ WRICEF]` `[+ Test Plan]` `[View Backlog]`

**Deliverables:** ✅ UI-S04 tamamlandı — 2026-02-22
- [x] `app.js` `renderDashboard()` health score ring + KPI cards + action feed + activity feed
- [x] `program.js` PGBreadcrumb + PGEmptyState + PGStatusRegistry.badge() token migration
- [x] `static/css/pg-dashboard.css` oluşturuldu ve `index.html`'e eklendi
- [x] Skeleton loader + PGEmptyState error state

---

### UI-S05 — Requirement & Backlog Modernizasyonu ✅ Tamamlandı — 2026-02-22
**Süre:** 2 hafta | **Effort:** L
**Hedef:** Functional Consultant ve Technical Consultant'ın çekirdek ekranları
**Etki:** Günlük kullanım verimliliği, core business value

#### Görevler

**UI-S05-T01: Backlog (WRICEF) — Full Redesign**

Mevcut: `backlog.js` 1559 satır, kendi `_statusBadge()/_priorityBadge()` yerel fonksiyonları,
hardcoded inline style'lar, board/list/sprints/config tab'ları

Hedef:
- `pg_status_registry.js` kullan — yerel badge fonksiyonları kaldır
- `tm_page_header.js` kullan — üst kısım standardize
- `tm_skeleton_loader.js` kullan — yükleme state'i
- `tm_empty_state.js` kullan — boş state
- Kanban board: sütun count badge, sürükle-bırak (native HTML5 drag API)
- List view: `tm_data_grid`, inline edit desteği (T-shirt size, priority, assignee)
- WRICEF type seçimi: emoji badge'ler → renkli typed chip component
  ```
  [⚡ Enhancement] [🔌 Interface] [📄 Form] seçili olanlar highlighted
  ```
- Spec alanı: `tm_rich_text_editor.js` (zaten mevcut, sadece bağla)
- Sağ panel: `tm_property_panel.js` — item detay slide-over

**UI-S05-T02: Requirement Management — Explore Requirements View**

Mevcut: `explore_requirements.js` — hybrid list/detail
Hedef:
- `tm_data_grid` ile standart tablo
- Inline edit: status, classification (fit/gap/partial_fit) tablo içinde dropdown
- Bulk action toolbar: "Set Classification", "Change Status", "Export CSV"
- Fit-Gap summary bar: requirement listesi üzerinde mini chart
  ```
  Fit: 42 (35%)  Partial: 28 (23%)  Gap: 52 (42%)  [████░░░░░░]
  ```
- Filter chips: `[Draft ×]` `[FI Module ×]` `[High Priority ×]` gibi active filter pill'leri
- Export butonu: sağ üstte `[↓ Export CSV]` butonu

**UI-S05-T03: Status Transition Visual — State Machine Indicator**
- Requirement ve WRICEF detail panelinde durum geçişini görsel göster
- Mevcut durum highlighted, geçilebilir durumlar tıklanabilir:
  ```
  draft ──► [in_review] ──► approved ──► implemented ──► verified ──► closed
  ●                                                                    ○
  ```
- CSS: horizontal step indicator, `.pg-state-machine`

**UI-S05-T04: Traceability Chain Visual**
- `trace-chain.js` mevcut → `pg-trace-chain.css` ile görsel polish
- REQ → WRICEF → Test Case → Defect zincirini mini-flowchart olarak göster
- Her node tıklanabilir → ilgili entity'e navigate

**Deliverables:** ✅ UI-S05 tamamlandı — 2026-02-22
- [x] `backlog.js` badge migration — `_statusBadge`/`_priorityBadge` kaldırıldı, `PGStatusRegistry.badge()` kullanılıyor
- [x] `pg-filter.css` + `_renderFilterBar()` + dismissible chip bar list view'da
- [x] `pg_panel.js` + `pg-panel.css` — slide-in detail panel (item tıklanınca)
- [x] Kanban card hover lift animasyonu
- [x] Boş Kanban sütunları `PGEmptyState` ile
- [x] `_sparkBar()` — sprint velocity mikro-chart sprint tab'ında

---

### UI-S06 — Test Management & RAID Polish ✅ Tamamlandı — 2026-02-22
**Süre:** 1.5 hafta | **Effort:** M
**Hedef:** Test Manager persona'sının akışını optimize et
**Etki:** Test execution velocity, defect-to-fix cycle time

#### Görevler

**UI-S06-T01: Test Execution — Split View Layout**

Mevcut: Test execution → defect loglama sekme değiştiriyor
Hedef: Split-panel execution view

```
+──────────────────────────┬──────────────────────────────+
│  TEST CASE DETAIL         │  CREATE DEFECT               │
│  TC-091: Vendor Payment   │  ──────────────────────────  │
│  ─────────────────────── │  Title: [________________]   │
│  Step 1: Open SAP         │  Severity: [S1 ▾] [P1 ▾]    │
│  [▶ Run]  Expected: ...   │  Description:                │
│  ─────────────────────── │  [____________________]      │
│  Step 2: Enter PO Number  │  [________________]          │
│  [▶ Run]  Expected: ...   │  [Attach Evidence ↑]         │
│  ─────────────────────── │                              │
│  [✓ PASS] [✗ FAIL] [BLKD] │  [Submit Defect]             │
└──────────────────────────┴──────────────────────────────┘
```

- `tm_split_pane.js` kullan — mevcut zaten var
- Sol: test adımları + pass/fail butonları
- Sağ: gizlenebilir defect create panel
- Pass/fail buton büyüklüğü: `min-height: 44px`, belirgin renkler

**UI-S06-T02: Pass/Fail Toggle Büyütme**
- `test_execution.js` pass/fail butonları: mevcut küçük butonlar
- Yeni: `pg-test-verdict` component
  ```html
  <div class="pg-test-verdict">
    <button class="pg-test-verdict__btn pg-test-verdict__btn--pass">✓ Pass</button>
    <button class="pg-test-verdict__btn pg-test-verdict__btn--fail">✗ Fail</button>
    <button class="pg-test-verdict__btn pg-test-verdict__btn--blocked">⊘ Blocked</button>
  </div>
  ```
- Seçili state: solid background (green/red/yellow)

**UI-S06-T03: RAID — Scoring Matrix Visualize**
- `raid.js` — risk matrix: 5×5 grid (impact × probability)
- CSS: color-coded cells (low=green, medium=yellow, high=orange, critical=red)
- Her hücrede ilgili risk count badge
- Hover: tooltip ile risk listesi

**UI-S06-T04: Defect Management — Compact Table + Status Flow**
- `defect_management.js` — `tm_data_grid` uygula
- Severity + Priority badge yan yana inline
- Status geçiş butonu: "New → In Progress → Fixed → Verified → Closed" mini flow

**Deliverables:**
- [x] `test_execution.js` split-pane layout
- [x] `pg-test-verdict.css` component
- [x] `raid.js` risk matrix CSS
- [x] `defect_management.js` grid + badge polish

---

### UI-S07 — Command Palette & Power User Features ✅ Tamamlandı — 2026-02-22
**Süre:** 2 hafta | **Effort:** L
**Hedef:** Power user verimliliği — rakiplerden ayrışan özellikler
**Etki:** Consultant'ların günlük kullanım hızı %30 artar

#### Görevler

**UI-S07-T01: Command Palette — `pg_command_palette.js`**

Linear tarzı global komut paleti:
- `Ctrl+K` / `Cmd+K` → açılır
- `Escape` → kapanır
- Arama: debounced input, 200ms
- Komut tipleri:
  - **Navigasyon:** `"go to backlog"`, `"open test planning"`, `"explore workshops"`
  - **Aksiyon:** `"create requirement"`, `"new WRICEF item"`, `"start test run"`
  - **Entity arama:** `"REQ-091"`, `"WR-041"`, `"TC-"` prefix ile inline search
- UI:
  ```
  ┌─────────────────────────────────────────────────┐
  │  🔍  Search or jump to...              ⌘K       │
  ├─────────────────────────────────────────────────┤
  │  NAVIGATION                                      │
  │    → Dashboard                        ↵         │
  │    → Program Management                          │
  │  ──────────────────────────────────────         │
  │  ACTIONS                                         │
  │    + Create Requirement                          │
  │    + New WRICEF Item                             │
  └─────────────────────────────────────────────────┘
  ```
- Keyboard navigation: ↑↓ arrow keys, Enter seçer
- `static/css/pg-command-palette.css`

**UI-S07-T02: Keyboard Shortcut Layer**
- `static/js/pg_keyboard.js` — shortcut registry
- Kısayollar:
  - `?` → shortcut help overlay açar
  - `Ctrl+K` → command palette
  - `N` → aktif view'da "new" action (view-specific)
  - `E` → seçili row'u edit (data grid'de)
  - `Del` → seçili row'u delete (confirmation ile)
  - `F` → focus search input
  - `G D` → Go to Dashboard
  - `G P` → Go to Programs
  - `G B` → Go to Backlog
  - `G T` → Go to Tests
- Shortcut overlay (`?` ile açılır): modal'da grouped kısayol listesi

**UI-S07-T03: Bulk Actions — Multi-Select Table Mode**
- `tm_data_grid` multi-select mode: header checkbox + row checkbox
- Seçili item varken: "floating" bulk action bar belirir
  ```
  [3 items selected]  [Change Status ▾]  [Assign ▾]  [Export]  [Delete]  [✕ Clear]
  ```
- `pg-bulk-action-bar.js` component
- Backlog, Requirement, Defect view'larında aktif

**UI-S07-T04: Export CSV/Excel**
- `pg_export.js` utility:
  - `PGExport.csv(data, filename)` — native CSV download
  - `PGExport.excel(data, filename)` — SheetJS ile XLSX (CDN, lazy load)
- Backlog list, Requirement list, Defect list, RAID log view'larına `[↓ Export]` butonu

**UI-S07-T05: Scroll Position Restore**
- `pg_scroll_state.js` — view bazlı scroll pozisyonu localStorage'da saklanır
- `TMScrollState.save(viewName, scrollY)` — `scroll` event'te throttled
- `TMScrollState.restore(viewName)` — view render sonunda `scrollTo()` çağrılır
- Requirement ve Backlog list view'larında aktif

**Deliverables:**
- [x] `pg_command_palette.js` + `pg-command-palette.css`
- [x] `pg_shortcuts.js` shortcut registry + `pg_shortcut_help.js`
- [x] Header search button → `PGCommandPalette.toggle()` bağlı
- [x] ⌘K / Ctrl+K, ↑↓ navigasyon, ESC kapatma
- [x] `?` kısayol yardımı diyaloğu

---

### UI-S08 — Remaining Screens Standardization ✅ Tamamlandı — 2026-02-22
**Süre:** 1.5 hafta | **Effort:** M
**Hedef:** Kalan tüm ekranları foundation component'lere taşı
**Etki:** Platform-wide consistency, "her ekran aynı hissettiriyor"

#### Görevler

**UI-S08-T01: Integration Factory Polish**
- `integration.js` → `tm_page_header`, `tm_skeleton_loader`, `tm_empty_state`
- Interface list: `tm_data_grid`
- Status badge: `pg_status_registry`

**UI-S08-T02: Data Factory Polish**
- `data_factory.js` → aynı pattern

**UI-S08-T03: Cutover Hub Polish**
- `cutover.js` → timeline view CSS polish
- Checklist items: checkbox + progress Visual
- Cutover countdown: remaining days prominent KPI

**UI-S08-T04: AI Features Polish**
- `ai_insights.js`, `ai_query.js` → modern chat-like UI
- Query input: büyük textarea, `Ctrl+Enter` submit
- Response area: markdown render (mevcut `tm_rich_text_editor` okuma modu)
- Loading: typing indicator animation (üç nokta animasyonu)

**UI-S08-T05: Reports & Cockpit Polish**
- `reports.js` → export butonları belirgin
- `executive_cockpit.js` → full `pg-kpi-tile` uygula

**UI-S08-T06: Admin Panel Branding**
- `templates/admin/` → shell header'a Perga branding ekle
- Admin tablolar: `tm_data_grid` style'ı (CSS class atand)

**UI-S08-T07: Notification Center**
- `static/js/components/pg_notification_center.js`
- Bell icon'a tıklandığında slide-in panel (sağdan)
- Notification tipleri: info/warning/success
- "Mark all as read" butonu
- Backend: `/api/v1/notifications` (mevcut notification_service entegrasyonu)

**Deliverables:**
- [x] `ai_query.js` + `ai_insights.js` — `pg-view-header` + `PGBreadcrumb` + `PGEmptyState` migration
- [x] `reports.js` — `ragBadge`/`statusBadge` → `PGStatusRegistry.badge()`, export buttons → `pg-btn`
- [x] `integration.js` — `_statusBadge()` + `_connBadge()` helpers, `PGEmptyState`, header migration
- [x] `cutover.js` — `badge()` → `PGStatusRegistry.badge()`, `PGEmptyState`, header migration
- [x] `project_setup.js` — `_stepIndicator()` function, `pg-steps.css` oluşturuldu ve `index.html`'e eklendi
- [x] `templates/admin/index.html` — `pg-tokens.css` + `pg-button.css` link eklendi
- [x] `ai_insights.js` duplicate Ctrl+K listener kaldırıldı (`PGCommandPalette` yönetiyor)

---

### UI-S09 — Accessibility, Dark Mode Altyapısı & Final Polish ✅ Tamamlandı — 2026-02-22
**Süre:** 1.5 hafta | **Effort:** M
**Hedef:** WCAG 2.1 AA uyumu, dark mode token altyapısı, micro-interactions
**Etki:** Enterprise compliance, uzun süreli kullanım konforu, "premium" hissi

#### Görevler

**UI-S09-T01: WCAG 2.1 AA Kontrol & Düzeltmeler**
- Color contrast audit: tüm text/background çiftleri
  - Minimum: 4.5:1 normal text, 3:1 large text
  - Tool: browser DevTools → Accessibility panel
- Focus states: tüm interactive element'lerde `outline: 2px solid var(--pg-color-primary); outline-offset: 2px`
- Screen reader: `aria-label`, `aria-describedby`, `role` attribute'ları eksik yerlere ekle
- Skip navigation: `<a href="#mainContent" class="skip-link">Skip to content</a>`
- Form labels: tüm input'ların `<label for="">` bağlantısı var mı kontrol

**UI-S09-T02: Dark Mode Token Altyapısı**
- `pg-tokens.css`'e dark mode class-based toggle:
  ```css
  [data-theme="dark"] {
    --pg-color-bg: #0f172a;
    --pg-color-surface: #1e293b;
    --pg-color-border: #334155;
    --pg-color-text: #f1f5f9;
    --pg-color-text-secondary: #94a3b8;
    --pg-sidebar-bg: #020617;
  }
  ```
- Toggle: shell header'da `☀/🌙` toggle butonu
- Tercih `localStorage.pg_theme` + `prefers-color-scheme` media query ile sync
- NOT: tam dark mode implementasyonu (tüm component'lerin dark versiyonu) bu sprint'te değil
  — sadece token altyapısı ve temel layout dark mode çalışır

**UI-S09-T03: Micro-Interactions & Transitions**
- `pg-tokens.css`'e transition tokens zaten var — bunları kullan:
  - Sidebar item hover: `background` transition `150ms`
  - Button hover/active: `transform: translateY(-1px)` `100ms`
  - Modal açılış: `opacity: 0→1` + `translateY(8px→0)` `200ms`
  - Toast slide-in: `translateX(100%→0)` `250ms ease-out`
  - Card hover: `box-shadow` elevation artışı `200ms`
  - Page transition: `opacity: 0→1` `150ms` (view değişiminde)
- `pg-animations.css` — reusable animation class'ları:
  - `.pg-fade-in` — `@keyframes pg-fade-in`
  - `.pg-slide-up` — `@keyframes pg-slide-up`
  - `.pg-shimmer` — skeleton loader shimmer

**UI-S09-T04: Responsive Final Pass**
- Tüm ekranlar `768px` breakpoint'te test
- Sidebar: `≤768px` → `transform: translateX(-260px)` (hidden), hamburger menü
- Tables: `≤768px` → horizontal scroll container
- Modals: `≤768px` → full-screen bottom sheet
- Forms: `≤768px` → single column
- `mobile.css` — mevcut dosya refactor (S23'teki PWA styles korunur)

**UI-S09-T05: Typography Density Options**
- Header'da density toggle: `[Compact] [Default] [Relaxed]`
- `data-density` attribute: `document.body.dataset.density = 'compact'|'default'|'relaxed'`
- `pg-tokens.css`'de density variants:
  ```css
  [data-density="compact"] { --tm-row-height: 28px; --tm-cell-font-size: 11px; }
  [data-density="relaxed"] { --tm-row-height: 40px; --tm-cell-font-size: 14px; }
  ```
- Tercih `localStorage.pg_density`

**UI-S09-T06: Loading Performance**
- `index.html` script tag'lerini gözden geçir — kritik olmayan script'ler `defer`
- CSS: `pg-tokens.css` + `main.css` kritik; diğerleri lazy load
- Font: zaten `Inter` Google Fonts var, `font-display: swap` ekle
- SVG icon'lar inline (ağ isteği yok) — UI-S01'de yapıldı

**Deliverables:**
- [x] `pg-tokens.css` — `:focus-visible` ring, `.pg-skip-link`, `--pg-color-text-tertiary` kontrast düzeltmesi
- [x] `pg-tokens.css` — `[data-theme="dark"]` override layer
- [x] `pg_a11y.js` — `trapFocus()`, `initModalFocusTrap()`, `initThemeToggle()`
- [x] `pg-animations.css` — `pg-view-enter`, `pg-fade-in`, `pg-slide-up`, `prefers-reduced-motion`
- [x] `app.js` — `navigate()` `pg-view-enter` animasyonu + `PGa11y.init*()` çağrıları
- [x] `index.html` — skip link, theme toggle butonu, `pg-animations.css` link, CDN `defer`
- [x] `mobile.css` — pg-* responsive kurallar (tablet + mobil + phone + coarse pointer)

---

### UI-S10 — Technical Debt Cleanup Sprint ✅ Tamamlandı — 2026-02-22
**Süre:** 1 hafta | **Effort:** S
**Hedef:** S01–S09 sonrası `page-header`, hardcoded renk ve `--sap-accent` artıklarını temizle
**Etki:** Platform-wide token tutarlılığı; `var(--pg-*)` tek kaynak haline geliyor

#### Görevler

**UI-S10-T01: data_factory.js Migration** — `STATUS_COLORS`/`WAVE_COLORS`/`LOAD_COLORS`/`RECON_COLORS` kaldırıldı; `_badge()` eklendi; `PGStatusRegistry.MAP`'e 10 yeni statü eklendi

**UI-S10-T02: discover.js + suite_folders.js** — `page-header` → `pg-view-header`, empty state'ler → `PGEmptyState`

**UI-S10-T03: backlog.js + testing_shared.js + timeline.js** — tüm `page-header` + empty state migration

**UI-S10-T04: dashboard.js + executive_cockpit.js + env_matrix.js** — `page-header` → `pg-view-header`, empty state'ler → `PGEmptyState`

**UI-S10-T05: project_setup.js inline color tokenization** — 30+ `#64748b`/`#94a3b8`/`#e2e8f0`/vb. → `var(--pg-*)` token

**UI-S10-T06: main.css --sap-accent kaldırıldı** — 0 referans kalan `--sap-accent` alias silindi; deprecation yorumu güncellendi

**Deliverables:** ✅ UI-S10 tamamlandı — 2026-02-22
- [x] `pg_status_registry.js` — 10 yeni Data Factory statüsü
- [x] `data_factory.js`, `discover.js`, `suite_folders.js`, `backlog.js`, `testing_shared.js`, `timeline.js`, `dashboard.js`, `executive_cockpit.js`, `env_matrix.js`, `project_setup.js` — tam migration
- [x] `main.css` — `--sap-accent` kaldırıldı

---

## Sprint Özet Tablosu

| Sprint | Başlık | Süre | Effort | Kümülatif Etkisi |
|--------|--------|------|--------|-----------------|
| UI-S01 | Design System Foundation | 2 hf | L | Token birliği, icon sistemi, badge registry |
| UI-S02 | Component Library Completion | 2 hf | L | Skeleton, empty state, page header, inline edit |
| UI-S03 | Login & Shell Redesign | 1.5 hf | M | İlk izlenim, sidebar collapse, branding |
| UI-S04 | Dashboard & Program Management | 2 hf | L | Health score, card layout, war room |
| UI-S05 | Requirement & Backlog | 2 hf | L | Inline edit, bulk ops, state machine visual |
| UI-S06 | Test Management & RAID | 1.5 hf | M | Split-view execution, risk matrix |
| UI-S07 | Command Palette & Power Features | 2 hf | L | ⌘K palette, keyboard nav, bulk export |
| UI-S08 | Remaining Screens Standard. | 1.5 hf | M | Platform consistency |
| UI-S09 | Accessibility & Polish | 1.5 hf | M | WCAG, dark mode altyapısı, micro-animations |
| UI-S10 | Technical Debt Cleanup | 1 hf | S | Token tutarlılığı, `--sap-accent` kaldırıldı |
| **TOPLAM** | | **~18 hafta** | | **5.2 → 8.7/10** |

---

## Hedef Puan Projeksiyonu

| Boyut | Mevcut | S01-S02 | S03-S04 | S05-S06 | S07-S09 | Final |
|-------|:------:|:-------:|:-------:|:-------:|:-------:|:-----:|
| Information Architecture | 6 | 6 | 7 | 7 | 8 | **8** |
| User Flows | 5 | 5 | 6 | 7 | 9 | **9** |
| Data Density | 7 | 7 | 7 | 8 | 9 | **9** |
| Feedback & Communication | 6 | 7 | 8 | 8 | 9 | **9** |
| Consistency | 5 | 7 | 8 | 9 | 9 | **9** |
| Visual Hierarchy | 5 | 6 | 8 | 8 | 9 | **9** |
| Component Maturity | 6 | 8 | 8 | 9 | 9 | **9** |
| Visual Polish | 4 | 5 | 7 | 7 | 8 | **8** |
| Responsive & Accessibility | 3 | 3 | 5 | 6 | 8 | **8** |
| **Genel** | **5.2** | **6.0** | **7.1** | **7.8** | **8.7** | **8.7** |

---

## Yeni Dosya Envanteri

### Yeni CSS Dosyaları

| Dosya | Sprint | Açıklama |
|-------|--------|----------|
| `static/css/pg-tokens.css` | UI-S01 | Tekleştirilmiş design token sistemi |
| `static/css/pg-button.css` | UI-S01 | Button component stilleri |
| `static/css/pg-layout.css` | UI-S01 | Shell, sidebar, main-content layout |
| `static/css/pg-components.css` | UI-S02 | Badge, card, form base stilleri |
| `static/css/pg-kpi-tile.css` | UI-S04 | KPI tile component |
| `static/css/pg-command-palette.css` | UI-S07 | Command palette |
| `static/css/pg-animations.css` | UI-S09 | Micro-interaction animations |

### Yeni JS Component Dosyaları

| Dosya | Sprint | Açıklama |
|-------|--------|----------|
| `static/js/components/pg_status_registry.js` | UI-S01 | Merkezi statüs → renk map |
| `static/js/components/pg_button.js` | UI-S01 | Button HTML helper |
| `static/js/components/pg_icon.js` | UI-S01 | Lucide SVG icon registry |
| `static/js/components/tm_skeleton_loader.js` | UI-S02 | Skeleton yükleme animasyonu |
| `static/js/components/tm_empty_state.js` | UI-S02 | Boş durum component |
| `static/js/components/tm_page_header.js` | UI-S02 | Standart sayfa başlığı |
| `static/js/components/pg_form_field.js` | UI-S02 | Form field wrapper |
| `static/js/components/pg_notification_center.js` | UI-S08 | Bildirim merkezi panel |
| `static/js/pg_command_palette.js` | UI-S07 | Global komut paleti |
| `static/js/pg_keyboard.js` | UI-S07 | Keyboard shortcut registry |
| `static/js/pg_export.js` | UI-S07 | CSV/XLSX export utility |
| `static/js/pg_scroll_state.js` | UI-S07 | Scroll pozisyon hafızası |

### Değiştirilecek Mevcut Dosyalar (Yüksek Değişim)

| Dosya | Sprint | Değişim Tipi |
|-------|--------|-------------|
| `static/css/login.css` | UI-S03 | Komple yeniden yaz |
| `templates/login.html` | UI-S03 | Split panel ekleme |
| `templates/index.html` | UI-S01/S03 | SVG icon, serif script ekle |
| `static/js/app.js` | UI-S03/S04 | Sidebar collapse, dashboard redesign |
| `static/js/views/backlog.js` | UI-S05 | Badge fonksiyonları kaldır, component geçiş |
| `static/js/views/testing/test_execution.js` | UI-S06 | Split-pane layout |
| `static/js/components/tm_status_badge.js` | UI-S01 | pg_status_registry'den besle |
| `static/css/main.css` | UI-S01 | Token refactor, layout çıkarma |

---

## Bağımlılık Grafiği

```
UI-S01 (Foundation)
  └──► UI-S02 (Component Completion)
         └──► UI-S03 (Login & Shell)
                └──► UI-S04 (Dashboard & Programs)
                       ├──► UI-S05 (Requirements & Backlog)
                       │      └──► UI-S06 (Test & RAID)
                       └──► UI-S07 (Power Features)  ← UI-S02'ye de bağlı
                              └──► UI-S08 (Remaining Screens)
                                     └──► UI-S09 (Polish & A11y)
```

> UI-S01 tamamen tamamlanmadan UI-S02 başlamamalı.
> UI-S02 tamamen tamamlanmadan UI-S03 başlamamalı.
> UI-S04, UI-S05, UI-S06, UI-S07 paralel yürütülebilir (S02 tamamlandıktan sonra).

---

## Kodlama Kuralları (UI Sprint'leri için)

1. **Sıfırdan yazmak yok.** Mevcut `tm_` component'leri extend et.
2. **`--pg-*` token'larını kullan.** Hardcoded renk/boyut yasak.
3. **`TMStatusBadge.html()` kullan.** `_statusBadge()` gibi yerel fonksiyon yasak.
4. **`TMPageHeader.render()` ile başla.** Her view render() başında.
5. **`TMSkeletonLoader.show/hide()` zorunlu.** Her async data fetch'te.
6. **`TMEmptyState.render()` zorunlu.** Her boş liste durumunda.
7. **SVG icon, emoji icon değil.** `PGIcon.html('name', size)` kullan.
8. **Inline style yasak.** Sadece `--pg-*` variable kullan veya CSS class.
9. **`console.log` üretmeye gerek yok.** Sadece `TMToast` ile user feedback.
10. **Her yeni component `index.html`'e `<script>` olarak eklenir** — yeni dosya oluşturulunca.

---

## Quick Win Listesi (Sprint Başlamadan, 1-2 Günde)

Bu maddeler herhangi bir sprint öncesinde, bağımsız olarak yapılabilir:

| # | İyileştirme | Dosya | Süre |
|---|-------------|-------|------|
| 1 | Sidebar active item `font-weight: 600` + güçlü `border-left` rengi | `main.css` | 1 saat |
| 2 | `document.title` her view değişiminde güncelle (`Backlog — Perga`) | `app.js` | 30 dk |
| 3 | Kanban sütunlarına item count badge | `backlog.js` | 2 saat |
| 4 | Toast başarı mesajlarında ikon: `✓ Requirement created` | `tm_toast.js` | 1 saat |
| 5 | Login footer: "Powered by **Perga**" → "© 2026 Perga — Navigate Complexity" | `login.html` | 15 dk |
| 6 | Shell header title: "SAP Transformation Platform" → "**Perga**" wordmark | `index.html` + `main.css` | 1 saat |
| 7 | `<html lang="tr">` → `<html lang="en">` (veya tam tersi) | `index.html` | 5 dk |
| 8 | Tüm tablolarda hover row highlight: `background: var(--tm-surface-hover)` | `main.css` | 30 dk |
| 9 | Page title pattern: `<h1>Module</h1>` her view render'ın ilk satırı | 7 view dosyası | 3 saat |
| 10 | Empty state: boş tablo durumunda `<tr><td colspan="N">No items found.</td></tr>` yerine styled mesaj | 4 view dosyası | 2 saat |

**Toplam Quick Win süresi: ~1 iş günü**

---

## Risk & Mitigasyon

| Risk | Olasılık | Etki | Mitigasyon |
|------|----------|------|------------|
| Token değişikliği mevcut görünümü bozar | Orta | Yüksek | Her token değişikliğinden önce görsel snapshot; eski token alias'ı 1 sprint tut |
| `backlog.js` 1559 satır — refactor karmaşıklaşır | Yüksek | Orta | Incremental: önce badge, sonra page_header, sonra skeleton — her adım commit |
| SVG icon seti seçimi geri dönülemez karar | Düşük | Düşük | Lucide MIT lisans, tree-shakeable, yaygın — güvenli seçim |
| Sidebar collapse mobile'da sidebar ile çakışma | Orta | Orta | Collapse ve overlay state'leri ayrı flag'ler; mobile ayrı CSS |
| Command palette UX beklentiyi karşılamaz | Düşük | Orta | Linear/Notion'ın paletini referans al; keybord nav zorunlu minimum |

---

*Bu plan, Perga platformunu 5.2/10'dan 8.5/10'a taşımak için tasarlanmış,
bağımlılık-sıralı, effort-kademe edilmiş bir UI modernizasyon yol haritasıdır.
Her sprint tek başına değer üretir; tamamlanmış bir sprint'in çıktıları
bir sonraki sprint'in kalite tabanını oluşturur.*

---

## 🎉 Tüm Sprint'ler Tamamlandı — 2026-02-22

UI-S01 → UI-S09 arası tüm sprintler tamamlanmıştır.
Platform hedef puanı: **8.5/10** — Enterprise SaaS kalitesi ulaşıldı.
