# Frontend Architecture

## Genel Bakis

Vanilla JavaScript SPA. Framework yok (React/Vue/Angular yok).
IIFE modul pattern, HTML string render, `pg_*` component system.

```
templates/index.html          # Shell: header, sidebar, mainContent
  |
  +-- static/js/auth.js       # JWT auth (localStorage)
  +-- static/js/api.js        # API client (auto-inject context)
  +-- static/js/components/   # pg_*.js reusable bilesenler (12 adet)
  +-- static/js/views/        # 44+ view modulu
  +-- static/js/app.js        # SPA router + context yonetimi
```

**Script yukleme sirasi kritik:** `auth.js` -> `api.js` -> components -> views -> `app.js`

---

## SPA Routing

**Dosya:** `static/js/app.js`

```javascript
// View registry
const views = {
    'dashboard':     () => DashboardView.render(),
    'programs':      () => ProgramView.render(),
    'backlog':       () => BacklogView.render(),
    'test-planning': () => TestPlanningView.render(),
    // ... 44+ view
};

// Navigasyon
App.navigate('dashboard');  // -> DashboardView.render() cagirir
```

### Context Guard'lar
```javascript
const programRequiredViews = new Set([
    'dashboard', 'backlog', 'test-planning', 'cutover', ...
]);
// Program secilmemisse -> uyari goster, 'programs' view'ina yonlendir

const projectAwareViews = new Set([
    'project-setup', 'explore-dashboard', ...
]);
// Project secilmemisse -> uyari goster
```

### Program/Project Context
```javascript
App.getActiveProgram()      // -> { id, name, status, tenant_id }
App.setActiveProgram(prog)  // -> localStorage + sidebar + header guncelle
App.getActiveProject()
App.setActiveProject(proj)
App.toast(message, type)    // 'info' | 'success' | 'warning' | 'error'
```

- localStorage'da saklanir (tenant_id ile cross-tenant leak onlenir)
- URL'de yansitilir: `/dashboard?program_id=1&project_id=10`
- Sayfa yuklendiginde: URL params > localStorage > bos

---

## Component System (`pg_*`)

**Pattern:** Fonksiyon tabanli HTML string generator'lar (Web Component degil).

| Component | Dosya | Kullanim |
|-----------|-------|----------|
| **Button** | `pg_button.js` | `PGButton.html(label, variant, opts)` |
| **Form** | `pg_form.js` | `PGForm.input({name, label, ...})` |
| **Icon** | `pg_icon.js` | `PGIcon.html(name, size)` — Lucide SVG |
| **Empty State** | `pg_empty_state.js` | `PGEmptyState.html({icon, title, ...})` |
| **Breadcrumb** | `pg_breadcrumb.js` | `PGBreadcrumb.html(items)` |
| **Panel** | `pg_panel.js` | `PGPanel.open({title, content, onClose})` |
| **Skeleton** | `pg_skeleton.js` | `PGSkeleton.line()`, `.table()`, `.cards(n)` |
| **Command Palette** | `pg_command_palette.js` | `PGCommandPalette.toggle()` (Cmd+K) |
| **Status Registry** | `pg_status_registry.js` | `PGStatusRegistry.badge(status)` |
| **Accessibility** | `pg_a11y.js` | `PGa11y.trapFocus()`, `.initThemeToggle()` |
| **Shortcuts** | `pg_shortcuts.js` | Global keyboard shortcut registry |
| **Shortcut Help** | `pg_shortcut_help.js` | Shortcut yardim overlay'i |

### Kullanim Ornegi
```javascript
// Component HTML string doner, DOM manipulasyonu yapmaz
const html = PGButton.html('Kaydet', 'primary', { onclick: "save()" });
document.getElementById('actions').innerHTML = html;

// Form input
const field = PGForm.input({
    name: 'title',
    label: 'Baslik',
    required: true,
    helpText: 'Maks 255 karakter',
});
```

---

## View Pattern

Her view bir IIFE modulu. `render()` giris noktasi.

```javascript
const MyView = (() => {
    let _data = [];  // Private state

    async function render() {
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{label:'Ana Sayfa'}, {label:'Gorunum'}])}
                <h2 class="pg-view-title">Gorunum Adi</h2>
            </div>
            <div id="content">${PGSkeleton.table()}</div>
        `;
        await _loadData();
    }

    async function _loadData() {
        const prog = App.getActiveProgram();
        if (!prog) {
            document.getElementById('content').innerHTML =
                PGEmptyState.html({ icon: 'programs', title: 'Program Secin' });
            return;
        }
        try {
            _data = await API.get(`/items?program_id=${prog.id}`);
            _renderTable();
        } catch (err) {
            App.toast(`Hata: ${err.message}`, 'error');
        }
    }

    function _renderTable() { /* innerHTML ile render */ }
    function openDetail(id) { PGPanel.open({ title: '...', content: '...' }); }

    return { render, openDetail };
})();
```

### View Kurallari
1. **Tek `render()` giris noktasi** — `App.navigate()` tarafindan cagirilir
2. **Her view program kontrolu yapar** — `App.getActiveProgram()` null ise EmptyState goster
3. **API cagirilari `API.get/post/...` ile** — asla dogrudan `fetch` kullanma
4. **Hatalar try/catch ile** — `App.toast(msg, 'error')` ile kullaniciya goster
5. **DOM islemleri innerHTML ile** — Component'ler HTML string doner

---

## API Client

**Dosya:** `static/js/api.js`

```javascript
API.get('/items?program_id=1')
API.post('/items', { title: 'Yeni' })
API.put('/items/1', { title: 'Guncellenmis' })
API.delete('/items/1')
```

Otomatik davranislar:
- JWT token `Authorization` header'a eklenir
- POST/PUT/PATCH'te `program_id`, `project_id`, `user_id`, `user_name` auto-inject edilir
- 401 yaniti -> otomatik `/login` yonlendirmesi
- Hata yaniti -> `Error` nesnesi ile `err.status`, `err.code`, `err.details`

---

## CSS Design System

### Token Hiyerarsisi

**Dosya:** `static/css/pg-tokens.css` (tum CSS dosyalarindan ONCE yuklenmeli)

```css
:root {
    /* Renkler */
    --pg-color-primary: #0070f2;
    --pg-color-text: #32363a;
    --pg-color-text-secondary: #6a6d70;
    --pg-color-bg: #f8f9fa;
    --pg-color-surface: #ffffff;
    --pg-color-border: #e5e7eb;

    /* Spacing (4px grid) */
    --pg-sp-1: 4px;   --pg-sp-2: 8px;   --pg-sp-3: 12px;
    --pg-sp-4: 16px;  --pg-sp-6: 24px;

    /* Border radius */
    --pg-radius-sm: 3px;  --pg-radius-md: 6px;

    /* Golge */
    --pg-shadow-sm: 0 1px 2px rgba(15,23,42,0.06);
    --pg-shadow-md: 0 4px 14px rgba(15,23,42,0.08);

    /* Z-index */
    --pg-z-sidebar: 90;   --pg-z-header: 100;
    --pg-z-modal-bg: 200;  --pg-z-modal: 210;
    --pg-z-toast: 300;     --pg-z-palette: 400;

    /* Transition */
    --pg-t-fast: 100ms ease;     /* Button hover */
    --pg-t-normal: 150ms ease;   /* Input focus */
    --pg-t-slow: 250ms ease;     /* Panel slide */
}
```

### Dark Mode
```css
[data-theme="dark"] {
    --pg-color-surface: #1e2433;
    --pg-color-bg: #161b27;
    --pg-color-text: #e2e8f0;
    /* ... diger override'lar */
}
```
Toggle: `PGa11y.initThemeToggle()` — localStorage key: `pg_theme`

### CSS Dosya Yapisi

| Dosya | Icerik |
|-------|--------|
| `pg-tokens.css` | Tum design token'lar (ILKI YUKLENMELI) |
| `main.css` | Base reset + legacy `--sap-*` alias'lari |
| `pg-button.css` | Button variant'lari (primary, secondary, ghost, danger) |
| `pg-form.css` | Input, textarea, select, checkbox |
| `pg-layout.css` | Grid, flexbox layout helper'lar |
| `pg-panel.css` | Slide-in detail panel (420px) |
| `pg-empty-state.css` | "Veri yok" state'i |
| `pg-skeleton.css` | Loading placeholder'lar |
| `pg-breadcrumb.css` | Breadcrumb navigasyon |
| `pg-animations.css` | Keyframe tanimlari + reduced-motion |
| `pg-command-palette.css` | Cmd+K overlay |
| `pg-dashboard.css` | Dashboard-ozel layout |
| `mobile.css` | Responsive override'lar |

### CSS Isimlendirme (BEM-style)
```css
.pg-button                    /* Component */
.pg-button--primary           /* Variant */
.pg-button--danger            /* Variant */
.pg-button:disabled           /* State */
.pg-form__input               /* Element */
.pg-form__input--error        /* Element + State */
```

### Status Renkleri (Tek Kaynak)

`PGStatusRegistry` (`pg_status_registry.js`) tum status renklerini yonetir.
74+ status tanimli. WCAG 2.1 AA uyumlu (4.5:1 kontrast).

```javascript
PGStatusRegistry.badge('pass')   // -> <span style="bg:#dcfce7;fg:#14532d">pass</span>
PGStatusRegistry.colors('fail')  // -> { bg: '#fee2e2', fg: '#991b1b' }
```

**Renk ekleme/degistirme:** Sadece `pg_status_registry.js` dosyasini guncelle.

---

## Erisebilirlik (WCAG 2.1 AA)

- **Skip link:** `<a href="#mainContent" class="pg-skip-link">`
- **Focus trap:** `PGa11y.trapFocus(modalEl)` — modal/panel'lerde tab dongusu
- **Focus ring:** `:focus-visible` ile sadece klavye kullanicilarinda gorunur
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` tum animasyonlari durdurur
- **Kontrast:** Tum text >= 4.5:1

---

## Kirmizi Cizgiler

1. **Renk hardcode YASAK** — her zaman `var(--pg-*)` token kullan
2. **Component DOM degistirmez** — sadece HTML string doner
3. **View'da dogrudan `fetch` YASAK** — `API.get/post/...` kullan
4. **Auth token sessionStorage'da SAKLANMAZ** — sadece localStorage
5. **View'da program/project kontrol zorunlu** — guard yoksa EmptyState goster
