# UI-S01 — Design System Foundation

**Sprint:** UI-S01 / 9
**Süre:** 2 hafta
**Effort:** L
**Durum:** ✅ Tamamlandı — 2026-02-22
**Bağımlılık:** Yok — ilk sprint
**Sonraki:** [UI-S02](./UI-S02-COMPONENT-LIBRARY-COMPLETION.md)

---

## Amaç

Tüm token'ları tek sistemde birleştir, component standardını tanımla.
Bu sprint bitmeden görsel iyileştirme sprint'lerine başlamak yanlış — her değişiklik
token tutarsızlığı nedeniyle diğer ekranları bozar.

## Neden Önce Bu?

| Sorun | Etki |
|-------|------|
| `main.css` (`--sap-*`) + `design-tokens.css` (`--tm-*`) çakışması | Bir rengi değiştirmek 2 dosyada iş |
| `backlog.js` kendi `_statusBadge()` fonksiyonunu tanımlıyor | `TMStatusBadge` ile 3. bir renk sistemi var |
| Sidebar emoji icon'ları (📊🏗️📋) | Retina'da bulanık, mesleki görünmüyor |
| `btn btn-primary` / `tm-btn` / inline style | 3 farklı button sistemi |

---

## Görevler

### UI-S01-T01 — Token Konsolidasyonu

**Dosya:** `static/css/pg-tokens.css` (yeni dosya)

`main.css`'deki `--sap-*` ve `design-tokens.css`'deki `--tm-*` değişkenlerini
`--pg-*` (Perga) prefix altında birleştir. Yeni token hiyerarşisi:

```css
/* ── Primitive tokens ─────────────────────────────────── */
--pg-color-blue-50:   #ebf5ff;
--pg-color-blue-100:  #dbeafe;
--pg-color-blue-600:  #0070f2;
--pg-color-blue-700:  #0054b5;
--pg-color-slate-50:  #f8fafc;
--pg-color-slate-100: #f1f5f9;
--pg-color-slate-200: #e2e8f0;
--pg-color-slate-400: #94a3b8;
--pg-color-slate-500: #64748b;
--pg-color-slate-700: #334155;
--pg-color-slate-800: #1e293b;
--pg-color-slate-900: #0f172a;
--pg-color-green-50:  #f0fdf4;
--pg-color-green-600: #16a34a;
--pg-color-red-50:    #fef2f2;
--pg-color-red-600:   #dc2626;
--pg-color-yellow-50: #fefce8;
--pg-color-yellow-600:#ca8a04;

/* ── Semantic tokens ──────────────────────────────────── */
--pg-color-primary:          var(--pg-color-blue-600);
--pg-color-primary-hover:    var(--pg-color-blue-700);
--pg-color-primary-light:    var(--pg-color-blue-50);
--pg-color-surface:          #ffffff;
--pg-color-bg:               #f5f6f7;
--pg-color-border:           #d9d9d9;
--pg-color-border-strong:    #c4c9d0;
--pg-color-text:             #32363a;
--pg-color-text-secondary:   #6a6d70;
--pg-color-text-tertiary:    #9aa0a6;
--pg-color-positive:         var(--pg-color-green-600);
--pg-color-negative:         var(--pg-color-red-600);
--pg-color-warning:          #e76500;

/* ── Component tokens ─────────────────────────────────── */
--pg-btn-primary-bg:         var(--pg-color-primary);
--pg-btn-primary-hover:      var(--pg-color-primary-hover);
--pg-sidebar-bg:             #1d2d3e;
--pg-sidebar-text:           #bdc3c7;
--pg-sidebar-hover:          #2c3e50;
--pg-sidebar-active:         var(--pg-color-primary);
--pg-sidebar-width:          260px;
--pg-sidebar-collapsed:      56px;
--pg-header-bg:              #354a5f;
--pg-header-height:          48px;

/* ── Spacing (4px base grid) ──────────────────────────── */
--pg-sp-1:  4px;
--pg-sp-2:  8px;
--pg-sp-3:  12px;
--pg-sp-4:  16px;
--pg-sp-5:  20px;
--pg-sp-6:  24px;
--pg-sp-8:  32px;
--pg-sp-10: 40px;
--pg-sp-12: 48px;

/* ── Border Radius ────────────────────────────────────── */
--pg-radius-sm: 3px;
--pg-radius-md: 6px;
--pg-radius-lg: 10px;
--pg-radius-xl: 16px;

/* ── Shadow ───────────────────────────────────────────── */
--pg-shadow-sm: 0 1px 2px rgba(15,23,42,0.06);
--pg-shadow-md: 0 4px 14px rgba(15,23,42,0.08);
--pg-shadow-lg: 0 10px 30px rgba(15,23,42,0.12);
--pg-shadow-xl: 0 20px 60px rgba(15,23,42,0.16);

/* ── Z-index ──────────────────────────────────────────── */
--pg-z-dropdown:      100;
--pg-z-sidebar:        90;
--pg-z-header:        100;
--pg-z-modal-bg:      200;
--pg-z-modal:         210;
--pg-z-toast:         300;
--pg-z-palette:       400;

/* ── Transition ───────────────────────────────────────── */
--pg-t-fast:   100ms ease;
--pg-t-normal: 150ms ease;
--pg-t-slow:   250ms ease;
```

**Backward compat:** `design-tokens.css` içine `--tm-accent: var(--pg-color-primary)` gibi
alias'lar ekle. Eski `--sap-*`  ve `--tm-*` değişkenlerini bu sprint süresince `/* @deprecated */`
comment ile tut — UI-S02'de kaldırılır.

**`index.html`'de yükleme sırası:**
```html
<link rel="stylesheet" href="/static/css/pg-tokens.css">   <!-- 1. önce -->
<link rel="stylesheet" href="/static/css/design-tokens.css">
<link rel="stylesheet" href="/static/css/main.css">
```

---

### UI-S01-T02 — Status Registry (Merkezi Renk Sistemi)

**Dosya:** `static/js/components/pg_status_registry.js`

Tüm statüs → renk map'leri tek yerde. `TMStatusBadge` bu registry'den beslenecek.

```javascript
const PGStatusRegistry = (() => {
    /**
     * Merkezi statüs renk kaydı.
     * Her domain'in kendi statüsleri + genel statüsler burada.
     * Renk çiftleri: { bg, fg } — WCAG 4.5:1 kontrastı karşılamalı.
     */
    const MAP = {
        // ── WRICEF / Backlog ─────────────────────
        new:         { bg: '#dbeafe', fg: '#1e40af' },
        design:      { bg: '#e0e7ff', fg: '#3730a3' },
        build:       { bg: '#fef3c7', fg: '#92400e' },
        test:        { bg: '#fce7f3', fg: '#9d174d' },
        deploy:      { bg: '#d1fae5', fg: '#065f46' },
        blocked:     { bg: '#fee2e2', fg: '#991b1b' },
        cancelled:   { bg: '#f1f5f9', fg: '#475569' },

        // ── Requirement lifecycle ─────────────────
        draft:       { bg: '#f1f5f9', fg: '#475569' },
        in_review:   { bg: '#fef9c3', fg: '#713f12' },
        approved:    { bg: '#dcfce7', fg: '#14532d' },
        implemented: { bg: '#dbeafe', fg: '#1e3a8a' },
        verified:    { bg: '#d1fae5', fg: '#064e3b' },

        // ── Test execution ────────────────────────
        pass:        { bg: '#dcfce7', fg: '#14532d' },
        fail:        { bg: '#fee2e2', fg: '#991b1b' },
        not_run:     { bg: '#f1f5f9', fg: '#475569' },
        deferred:    { bg: '#f3e8ff', fg: '#581c87' },
        skipped:     { bg: '#f1f5f9', fg: '#475569' },
        ready:       { bg: '#dbeafe', fg: '#1e3a8a' },
        deprecated:  { bg: '#fee2e2', fg: '#7f1d1d' },

        // ── Priority ──────────────────────────────
        critical:    { bg: '#fee2e2', fg: '#991b1b' },
        high:        { bg: '#ffedd5', fg: '#9a3412' },
        medium:      { bg: '#fef9c3', fg: '#713f12' },
        low:         { bg: '#f0fdf4', fg: '#14532d' },

        // ── Severity ──────────────────────────────
        s1:          { bg: '#fee2e2', fg: '#991b1b' },
        s2:          { bg: '#ffedd5', fg: '#9a3412' },
        s3:          { bg: '#dbeafe', fg: '#1e3a8a' },
        s4:          { bg: '#f1f5f9', fg: '#475569' },

        // ── RAID ──────────────────────────────────
        risk:        { bg: '#fee2e2', fg: '#991b1b' },
        assumption:  { bg: '#dbeafe', fg: '#1e3a8a' },
        issue:       { bg: '#ffedd5', fg: '#9a3412' },
        dependency:  { bg: '#f3e8ff', fg: '#581c87' },

        // ── General ───────────────────────────────
        active:      { bg: '#dcfce7', fg: '#14532d' },
        inactive:    { bg: '#f1f5f9', fg: '#475569' },
        open:        { bg: '#dbeafe', fg: '#1e3a8a' },
        closed:      { bg: '#f1f5f9', fg: '#475569' },
        pending:     { bg: '#fef9c3', fg: '#713f12' },
        completed:   { bg: '#dcfce7', fg: '#14532d' },
        in_progress: { bg: '#dbeafe', fg: '#1e3a8a' },
    };

    /** Statüse göre renk döndür. Bilinmeyen statüs → nötr gri. */
    function colors(status) {
        const key = (status || '').toLowerCase().replace(/[\s\-]/g, '_');
        return MAP[key] || { bg: '#f1f5f9', fg: '#475569' };
    }

    /** HTML badge string döndür. */
    function badge(status, opts = {}) {
        const { bg, fg } = colors(status);
        const label = opts.label || status || 'unknown';
        const size  = opts.size === 'lg' ? 'font-size:13px;padding:3px 10px' : 'font-size:11px;padding:2px 8px';
        return `<span style="display:inline-block;${size};border-radius:4px;font-weight:600;background:${bg};color:${fg};white-space:nowrap">${_esc(label)}</span>`;
    }

    function _esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    return { colors, badge, MAP };
})();
```

**Sonraki adım:** `TMStatusBadge.html()` → `PGStatusRegistry.badge()` wrapper olarak güncelle.
`backlog.js`'deki `_statusBadge()` ve `_priorityBadge()` fonksiyonlarını sil.

---

### UI-S01-T03 — Button Component Standardizasyonu

**Dosyalar:** `static/js/components/pg_button.js` + `static/css/pg-button.css`

```javascript
const PGButton = (() => {
    /**
     * Standart buton HTML helper.
     * Tüm view'larda btn-primary / tm-btn yerine bu kullanılır.
     *
     * @param {string} label
     * @param {'primary'|'secondary'|'ghost'|'danger'|'icon'} variant
     * @param {{ size?: 'sm'|'md'|'lg', loading?: bool, disabled?: bool,
     *           onclick?: string, icon?: string, id?: string }} opts
     */
    function html(label, variant = 'secondary', opts = {}) {
        const cls = `pg-btn pg-btn--${variant}${opts.size ? ` pg-btn--${opts.size}` : ''}`;
        const disabled = opts.disabled || opts.loading ? 'disabled' : '';
        const onclick  = opts.onclick ? `onclick="${opts.onclick}"` : '';
        const id       = opts.id ? `id="${opts.id}"` : '';
        const inner    = opts.loading
            ? `<span class="pg-btn__spinner"></span>${label}`
            : (opts.icon ? `${opts.icon} ${label}` : label);
        return `<button class="${cls}" ${disabled} ${onclick} ${id}>${inner}</button>`;
    }

    return { html };
})();
```

```css
/* static/css/pg-button.css */
.pg-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 1px solid transparent;
    border-radius: var(--pg-radius-md);
    font-family: var(--font-family, 'Inter', sans-serif);
    font-weight: 500;
    font-size: 13px;
    line-height: 1;
    padding: 7px 14px;
    cursor: pointer;
    transition: all var(--pg-t-normal, 150ms ease);
    white-space: nowrap;
    text-decoration: none;
}
.pg-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Sizes */
.pg-btn--sm { font-size: 12px; padding: 5px 10px; }
.pg-btn--lg { font-size: 14px; padding: 9px 18px; }

/* Variants */
.pg-btn--primary  { background: var(--pg-color-primary); color: #fff; }
.pg-btn--primary:hover:not(:disabled)  { background: var(--pg-color-primary-hover); transform: translateY(-1px); }

.pg-btn--secondary { background: #fff; color: var(--pg-color-text, #32363a); border-color: var(--pg-color-border, #d9d9d9); }
.pg-btn--secondary:hover:not(:disabled) { background: var(--pg-color-bg, #f5f6f7); border-color: #b0b7c0; }

.pg-btn--ghost { background: transparent; color: var(--pg-color-text, #32363a); }
.pg-btn--ghost:hover:not(:disabled) { background: var(--pg-color-bg, #f5f6f7); }

.pg-btn--danger  { background: #dc2626; color: #fff; }
.pg-btn--danger:hover:not(:disabled)  { background: #b91c1c; }

.pg-btn--icon { padding: 6px; background: transparent; border: none; color: var(--pg-color-text-secondary, #6a6d70); }
.pg-btn--icon:hover:not(:disabled) { background: var(--pg-color-bg, #f5f6f7); color: var(--pg-color-text, #32363a); }

/* Loading spinner */
.pg-btn__spinner {
    width: 12px; height: 12px;
    border: 2px solid rgba(255,255,255,0.4);
    border-top-color: currentColor;
    border-radius: 50%;
    animation: pg-spin 0.6s linear infinite;
    display: inline-block;
}
@keyframes pg-spin { to { transform: rotate(360deg); } }
```

---

### UI-S01-T04 — Emoji Icon'larını SVG ile Değiştir

**Dosya:** `static/js/components/pg_icon.js`

[Lucide Icons](https://lucide.dev/) (MIT lisans) — inline SVG string olarak tanımla,
CDN bağımlılığı yok.

```javascript
const PGIcon = (() => {
    // Lucide icon SVG path'leri (24x24 viewBox, stroke-based)
    const ICONS = {
        dashboard:    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>`,
        programs:     `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>`,
        explore:      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>`,
        hierarchy:    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9h18M3 15h18M8 3v18M16 3v18"/></svg>`,
        workshops:    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
        requirements: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`,
        backlog:      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`,
        test:         `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v11m0 0H5m4 0h10m-6 7h.01M12 21a9 9 0 1 1 0-18 9 9 0 0 1 0 18z"/></svg>`,
        test_execute: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>`,
        defect:       `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
        approvals:    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
        raid:         `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
        integration:  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h16M4 15h16M10 3 8 21M14 3l-2 18"/></svg>`,
        data:         `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>`,
        cutover:      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>`,
        ai:           `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg>`,
        reports:      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
        cockpit:      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
        setup:        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>`,
        bell:         `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>`,
        search:       `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
        chevron_left: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>`,
        chevron_right:`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>`,
        plus:         `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>`,
        edit:         `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`,
        trash:        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`,
        export:       `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>`,
        filter:       `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>`,
        columns:      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="8" height="18"/><rect x="13" y="3" width="8" height="18"/></svg>`,
        eye:          `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`,
        eye_off:      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`,
        sun:          `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`,
        moon:         `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`,
    };

    /**
     * SVG HTML string döndür.
     * @param {string} name — ICONS map key
     * @param {number} size — px cinsinden genişlik/yükseklik (default: 16)
     * @returns {string} SVG HTML
     */
    function html(name, size = 16) {
        const svg = ICONS[name];
        if (!svg) return '';
        return svg.replace('<svg ', `<svg width="${size}" height="${size}" `);
    }

    return { html, ICONS };
})();
```

**`index.html`'de sidebar item'ları güncelleyin:**
```html
<!-- Önce -->
<span class="sidebar__item-icon">📊</span>

<!-- Sonra -->
<span class="sidebar__item-icon">${PGIcon.html('dashboard', 16)}</span>
```

---

### UI-S01-T05 — CSS Architecture Refactor (Kısmi)

Bu sprint'te sadece `pg-tokens.css` ve `pg-layout.css` çıkarılır.

**`static/css/pg-layout.css`** — shell, sidebar, main-content layout styles:
- `main.css`'den `.shell-header`, `.sidebar`, `.main-content`, `.modal-overlay`, `.toast-container`
  bloklarını bu dosyaya taşı
- `main.css`'de bu bloklar `/* moved to pg-layout.css */` comment ile kalır (backward compat)
- `index.html`'e `<link rel="stylesheet" href="/static/css/pg-layout.css">` ekle

---

## Deliverables Kontrol Listesi

- [x] `static/css/pg-tokens.css` oluşturuldu, `index.html`'e eklendi
- [x] `static/js/components/pg_status_registry.js` oluşturuldu, `index.html`'e eklendi
- [x] `static/js/components/pg_button.js` oluşturuldu
- [x] `static/css/pg-button.css` oluşturuldu, `index.html`'e eklendi
- [x] `static/js/components/pg_icon.js` oluşturuldu, `index.html`'e eklendi
- [x] `static/css/pg-layout.css` oluşturuldu
- [x] `templates/index.html` sidebar emoji → SVG icon güncellendi (data-pg-icon + init script)
- [x] `static/js/views/backlog.js` `_statusBadge()` + `_priorityBadge()` kaldırıldı, `PGStatusRegistry.badge()` kullanıyor
- [x] `static/js/components/tm_status_badge.js` `PGStatusRegistry`'den beslenecek şekilde güncellendi
- [x] `design-tokens.css` eski `--tm-*` değişkenleri `pg-tokens.css`'den alias alıyor
- [x] `main.css` `--sap-*` değişkenleri `/* @deprecated */` ile işaretlendi

## Bağımlılık

```
UI-S01 ✅ → UI-S02 başlayabilir
```

## Kodlama Kuralları

- Yeni dosya oluştururken: `index.html`'e `<script>` / `<link>` ekle
- Hardcoded renk/boyut yasak — sadece `--pg-*` token'ları
- `TMStatusBadge.html()` → `PGStatusRegistry.badge()` wrapper olarak güncelle
- `backlog.js`'e dokunurken test et: board, list, sprints, config tab'ları hepsini kontrol et

---

*← [Master Plan](./UI-MODERNIZATION-MASTER-PLAN.md) | Sonraki: [UI-S02 →](./UI-S02-COMPONENT-LIBRARY-COMPLETION.md)*
