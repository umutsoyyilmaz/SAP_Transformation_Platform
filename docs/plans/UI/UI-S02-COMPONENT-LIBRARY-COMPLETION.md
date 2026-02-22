# UI-S02 — Component Library Completion

**Sprint:** UI-S02 / 9
**Süre:** 2 hafta
**Effort:** L
**Durum:** ✅ Tamamlandı — 2026-02-22
**Bağımlılık:** [UI-S01](./UI-S01-DESIGN-SYSTEM-FOUNDATION.md) tamamlanmış olmalı
**Sonraki:** [UI-S03](./UI-S03-LOGIN-SHELL-REDESIGN.md)

---

## Amaç

23 component'in eksik parçalarını tamamla, `pg-tokens.css`'e tam geçişi yap.
Her component `pg_*` tokenları kullanmalı; inline style ve hardcoded renk yasak.
Bu sprint bitmeden ekranlar üzerinde çalışmak tutarsız sonuçlar doğurur.

---

## Görevler

### UI-S02-T01 — Component Token Migration

Mevcut her `tm_*.js` component'i `--pg-*` tokenlarına geçir.

**Öncelik sırası (sorun büyüklüğüne göre):**

| Component | Sorun | Çözüm |
|---|---|---|
| `tm_status_badge.js` | Inline `style=` renk | `PGStatusRegistry.badge()` wrapper |
| `tm_data_grid.js` | `--sap-*` border rengi | `--pg-color-border` |
| `tm_toolbar.js` | Hardcoded `#f5f6f7` bg | `--pg-color-bg` |
| `tm_tab_bar.js` | Hardcoded `#0070f2` active | `--pg-color-primary` |
| `tm_modal.js` | Hardcoded `#fff` overlay bg | `--pg-color-surface` |
| `tm_toast.js` | Hardcoded renk çiftleri | `PGStatusRegistry.colors()` kullan |
| `tm_context_menu.js` | Hardcoded `#fff` bg | `--pg-color-surface` + shadow token |

**Geçiş template'i:**
```javascript
// ÖNCE
element.style.background = '#f5f6f7';

// SONRA
const style = getComputedStyle(document.documentElement);
element.style.background = style.getPropertyValue('--pg-color-bg').trim() || '#f5f6f7';
```

Daha iyisi: CSS class kullan, inline style değil.

---

### UI-S02-T02 — Form Component Ailesi

**Dosya:** `static/js/components/pg_form.js` + `static/css/pg-form.css`

Mevcut `<input>` / `<select>` elemanları her view'da farklı stil alıyor.
Bu component tek kaynağa bağlar.

```javascript
const PGForm = (() => {
    /**
     * Standart form input HTML helper'ları.
     * Her view'da `<input class="pg-input">` gibi doğrudan kullanılır
     * VEYA aşağıdaki helper fonksiyonlar ile.
     */

    /** Tek satır metin inputu */
    function input({ name, label, value = '', placeholder = '', required = false, disabled = false, type = 'text', helpText = '', errorText = '' }) {
        const id = `pg-input-${name}`;
        return `
            <div class="pg-field${errorText ? ' pg-field--error' : ''}">
                ${label ? `<label class="pg-label" for="${id}">${label}${required ? '<span class="pg-label__req">*</span>' : ''}</label>` : ''}
                <input
                    class="pg-input"
                    id="${id}" name="${name}" type="${type}"
                    value="${_esc(String(value))}"
                    placeholder="${_esc(placeholder)}"
                    ${required ? 'required' : ''}
                    ${disabled ? 'disabled' : ''}
                >
                ${helpText && !errorText ? `<p class="pg-hint">${_esc(helpText)}</p>` : ''}
                ${errorText ? `<p class="pg-error-msg">${_esc(errorText)}</p>` : ''}
            </div>
        `;
    }

    /** Textarea */
    function textarea({ name, label, value = '', rows = 3, required = false, disabled = false, helpText = '' }) {
        const id = `pg-textarea-${name}`;
        return `
            <div class="pg-field">
                ${label ? `<label class="pg-label" for="${id}">${label}${required ? '<span class="pg-label__req">*</span>' : ''}</label>` : ''}
                <textarea class="pg-input pg-input--textarea" id="${id}" name="${name}" rows="${rows}" ${required ? 'required' : ''} ${disabled ? 'disabled' : ''}>${_esc(String(value))}</textarea>
                ${helpText ? `<p class="pg-hint">${_esc(helpText)}</p>` : ''}
            </div>
        `;
    }

    /** Select dropdown */
    function select({ name, label, value = '', options = [], required = false, disabled = false, placeholder = 'Seç...' }) {
        const id = `pg-select-${name}`;
        const opts = [
            placeholder ? `<option value="" disabled ${!value ? 'selected' : ''}>${_esc(placeholder)}</option>` : '',
            ...options.map(o => {
                const v = typeof o === 'object' ? o.value : o;
                const l = typeof o === 'object' ? o.label : o;
                return `<option value="${_esc(String(v))}" ${String(v) === String(value) ? 'selected' : ''}>${_esc(l)}</option>`;
            })
        ].join('');
        return `
            <div class="pg-field">
                ${label ? `<label class="pg-label" for="${id}">${label}${required ? '<span class="pg-label__req">*</span>' : ''}</label>` : ''}
                <select class="pg-select" id="${id}" name="${name}" ${required ? 'required' : ''} ${disabled ? 'disabled' : ''}>${opts}</select>
            </div>
        `;
    }

    /** Checkbox */
    function checkbox({ name, label, checked = false, disabled = false }) {
        return `
            <label class="pg-checkbox">
                <input type="checkbox" name="${name}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''}>
                <span class="pg-checkbox__label">${_esc(label)}</span>
            </label>
        `;
    }

    function _esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    return { input, textarea, select, checkbox };
})();
```

```css
/* static/css/pg-form.css */
.pg-field { display: flex; flex-direction: column; gap: 4px; }
.pg-field--error .pg-input,
.pg-field--error .pg-select { border-color: var(--pg-color-negative); }

.pg-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--pg-color-text-secondary);
    letter-spacing: 0.4px;
}
.pg-label__req { color: var(--pg-color-negative); margin-left: 2px; }

.pg-input,
.pg-select {
    width: 100%;
    border: 1px solid var(--pg-color-border);
    border-radius: var(--pg-radius-md);
    background: var(--pg-color-surface);
    color: var(--pg-color-text);
    font-size: 13px;
    padding: 7px 10px;
    transition: border-color var(--pg-t-normal), box-shadow var(--pg-t-normal);
    outline: none;
    box-sizing: border-box;
}
.pg-input:focus,
.pg-select:focus {
    border-color: var(--pg-color-primary);
    box-shadow: 0 0 0 3px rgba(0, 112, 242, 0.12);
}
.pg-input:disabled,
.pg-select:disabled { background: var(--pg-color-bg); color: var(--pg-color-text-tertiary); cursor: not-allowed; }

.pg-input--textarea { resize: vertical; min-height: 72px; line-height: 1.5; }

.pg-hint { font-size: 11px; color: var(--pg-color-text-tertiary); margin: 0; }
.pg-error-msg { font-size: 11px; color: var(--pg-color-negative); margin: 0; }

.pg-checkbox { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.pg-checkbox input[type=checkbox] { width: 14px; height: 14px; accent-color: var(--pg-color-primary); }
.pg-checkbox__label { font-size: 13px; color: var(--pg-color-text); }
```

---

### UI-S02-T03 — Empty State Component

**Dosya:** `static/js/components/pg_empty_state.js`

```javascript
const PGEmptyState = (() => {
    /**
     * Standart boş durum UI.
     * İkon + başlık + açıklama + opsiyonel CTA butonu.
     *
     * @param {{ icon?: string, title: string, description?: string,
     *           action?: { label: string, onclick: string } }} opts
     */
    function html({ icon = 'folder', title, description = '', action = null } = {}) {
        const iconHtml = PGIcon ? PGIcon.html(icon, 48) : '';
        const actionHtml = action
            ? `<button class="pg-btn pg-btn--primary" onclick="${action.onclick}">${action.label}</button>`
            : '';
        return `
            <div class="pg-empty-state">
                ${iconHtml ? `<div class="pg-empty-state__icon">${iconHtml}</div>` : ''}
                <h3 class="pg-empty-state__title">${title}</h3>
                ${description ? `<p class="pg-empty-state__desc">${description}</p>` : ''}
                ${actionHtml}
            </div>
        `;
    }

    return { html };
})();
```

```css
/* static/css/pg-empty-state.css */
.pg-empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--pg-sp-12) var(--pg-sp-8);
    text-align: center;
    color: var(--pg-color-text-secondary);
    gap: var(--pg-sp-3);
}
.pg-empty-state__icon { color: var(--pg-color-text-tertiary); margin-bottom: var(--pg-sp-2); }
.pg-empty-state__title { font-size: 14px; font-weight: 600; color: var(--pg-color-text); margin: 0; }
.pg-empty-state__desc  { font-size: 13px; margin: 0; max-width: 340px; line-height: 1.5; }
```

---

### UI-S02-T04 — Skeleton Loader Component

**Dosya:** `static/js/components/pg_skeleton.js`

```javascript
const PGSkeleton = (() => {
    /** Tek satır skeleton */
    function line(widthPct = 100, heightPx = 14) {
        return `<div class="pg-skeleton" style="width:${widthPct}%;height:${heightPx}px;border-radius:3px"></div>`;
    }

    /** Tablo satır skeleton'ı (N satır, M kolon) */
    function table(rows = 5, cols = 4) {
        const header = `<div class="pg-skeleton-row">${Array(cols).fill(line(80, 12)).join('')}</div>`;
        const rowHtml = Array(rows).fill(0).map(() =>
            `<div class="pg-skeleton-row">${Array(cols).fill(0).map(() => line(Math.random() * 40 + 50, 12)).join('')}</div>`
        ).join('');
        return `<div class="pg-skeleton-table">${header}${rowHtml}</div>`;
    }

    /** Card skeleton */
    function card() {
        return `
            <div class="pg-skeleton-card">
                ${line(40, 16)}
                ${line(100, 12)}
                ${line(75, 12)}
                ${line(55, 12)}
            </div>
        `;
    }

    return { line, table, card };
})();
```

```css
/* static/css/pg-skeleton.css */
.pg-skeleton {
    display: block;
    background: linear-gradient(90deg,
        var(--pg-color-bg) 0%,
        var(--pg-color-border) 50%,
        var(--pg-color-bg) 100%
    );
    background-size: 200% 100%;
    animation: pg-shimmer 1.4s ease infinite;
    border-radius: var(--pg-radius-sm);
}
@keyframes pg-shimmer {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
.pg-skeleton-row  { display: flex; gap: var(--pg-sp-4); padding: var(--pg-sp-2) 0; }
.pg-skeleton-table { display: flex; flex-direction: column; }
.pg-skeleton-card {
    display: flex;
    flex-direction: column;
    gap: var(--pg-sp-3);
    padding: var(--pg-sp-6);
    background: var(--pg-color-surface);
    border-radius: var(--pg-radius-lg);
    border: 1px solid var(--pg-color-border);
    box-shadow: var(--pg-shadow-sm);
}
```

---

### UI-S02-T05 — Breadcrumb Component (Tüm View'lara Ekle)

**Dosya:** `static/js/components/pg_breadcrumb.js`

```javascript
const PGBreadcrumb = (() => {
    /**
     * Standardize breadcrumb.
     * Her view'ın en üstünde `.pg-breadcrumb` render edilmeli.
     *
     * @param {Array<{ label: string, onclick?: string }>} items
     *   Son item tıklanamaz (current page).
     */
    function html(items = []) {
        if (!items.length) return '';
        const parts = items.map((item, i) => {
            const isLast = i === items.length - 1;
            const el = isLast
                ? `<span class="pg-breadcrumb__current">${_esc(item.label)}</span>`
                : `<a class="pg-breadcrumb__link" href="#" onclick="${item.onclick || ''};return false">${_esc(item.label)}</a>`;
            const sep = isLast ? '' : `<span class="pg-breadcrumb__sep" aria-hidden="true">/</span>`;
            return el + sep;
        });
        return `<nav class="pg-breadcrumb" aria-label="Breadcrumb">${parts.join('')}</nav>`;
    }

    function _esc(str) {
        const d = document.createElement('div'); d.textContent = str; return d.innerHTML;
    }

    return { html };
})();
```

```css
/* static/css/pg-breadcrumb.css */
.pg-breadcrumb {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
    font-size: 12px;
    color: var(--pg-color-text-tertiary);
    margin-bottom: var(--pg-sp-4);
    padding: var(--pg-sp-1) 0;
}
.pg-breadcrumb__link {
    color: var(--pg-color-text-secondary);
    text-decoration: none;
    padding: 2px 4px;
    border-radius: var(--pg-radius-sm);
    transition: background var(--pg-t-fast), color var(--pg-t-fast);
}
.pg-breadcrumb__link:hover { background: var(--pg-color-bg); color: var(--pg-color-primary); }
.pg-breadcrumb__current { color: var(--pg-color-text); font-weight: 500; }
.pg-breadcrumb__sep { color: var(--pg-color-border-strong); user-select: none; }
```

---

### UI-S02-T06 — Deprecated Token Cleanup

Tüm `--sap-*` ve `--tm-*` kullanımlarını `grep -r` ile bul → `--pg-*` ile değiştir.

```bash
# Kullanımları listele
grep -r "var(--sap-" static/css/ --include="*.css" | wc -l
grep -r "var(--tm-"  static/css/ --include="*.css" | wc -l

# UI-S02 sonu hedef:
# sap- references: 0
# tm-  references: backward-compat alias satırları dışında 0
```

---

## Deliverables Kontrol Listesi

- [x] Tüm `tm_*.js` component'leri `--pg-*` tokenlarına geçirildi (test-management-f1.css hardcoded değerleri temizlendi)
- [x] `pg_form.js` + `pg-form.css` oluşturuldu
- [x] `pg_empty_state.js` + `pg-empty-state.css` oluşturuldu
- [x] `pg_skeleton.js` + `pg-skeleton.css` oluşturuldu
- [x] `pg_breadcrumb.js` + `pg-breadcrumb.css` oluşturuldu
- [x] `--sap-*` token kullanımı sıfırlandı (explore-tokens.css, login.css, mobile.css temizlendi)
- [x] Tüm component'ler `index.html`'e eklendi
- [x] Mevcut 5 view (dashboard, backlog, requirements, test, defect) `PGBreadcrumb.html()` ekli

---

*← [UI-S01](./UI-S01-DESIGN-SYSTEM-FOUNDATION.md) | [Master Plan](./UI-MODERNIZATION-MASTER-PLAN.md) | Sonraki: [UI-S03 →](./UI-S03-LOGIN-SHELL-REDESIGN.md)*
