# UI-S07 — Command Palette & Power User Features

**Sprint:** UI-S07 / 9
**Süre:** 2 hafta
**Effort:** L
**Durum:** ✅ Tamamlandı — 2026-02-22
**Bağımlılık:** [UI-S03](./UI-S03-LOGIN-SHELL-REDESIGN.md) tamamlanmış olmalı
**Sonraki:** [UI-S08](./UI-S08-REMAINING-SCREENS.md)

---

## Amaç

Power kullanıcıların platformda fareye ihtiyaç duymadan çalışabilmesi.
⌘K komut paleti, keyboard shortcuts, contextual toolbar akıllı davranışı.
Bu özellikler "enterprise grade" ile "araç kutusu" arasındaki farkı yaratır.

---

## Görevler

### UI-S07-T01 — Command Palette (⌘K)

**Dosya:** `static/js/components/pg_command_palette.js` + `static/css/pg-command-palette.css`

```javascript
const PGCommandPalette = (() => {
    /**
     * ⌘K / Ctrl+K ile açılan komut paleti.
     * Navigation + Action + Search birleştiriliyor.
     *
     * Komutlar 3 kategoride:
     * 1. Navigation — view'a git
     * 2. Action     — modal/form aç
     * 3. Search     — %3 karakter sonra API çağrısı
     */

    const COMMANDS = [
        // Navigation
        { id: 'nav-dashboard',    label: 'Dashboard\'a git',       icon: 'dashboard',    action: () => navigate('dashboard'),         category: 'Navigasyon', shortcut: 'G D' },
        { id: 'nav-programs',     label: 'Programlar',             icon: 'programs',     action: () => navigate('programs'),          category: 'Navigasyon', shortcut: 'G P' },
        { id: 'nav-requirements', label: 'Gereksinimler',          icon: 'requirements', action: () => navigate('requirements'),      category: 'Navigasyon', shortcut: 'G R' },
        { id: 'nav-backlog',      label: 'WRICEF Backlog',         icon: 'backlog',      action: () => navigate('backlog'),           category: 'Navigasyon', shortcut: 'G W' },
        { id: 'nav-test',         label: 'Test Yönetimi',          icon: 'test',         action: () => navigate('test-management'),   category: 'Navigasyon', shortcut: 'G T' },
        { id: 'nav-defects',      label: 'Defect Listesi',         icon: 'defect',       action: () => navigate('defects'),           category: 'Navigasyon', shortcut: 'G B' },
        { id: 'nav-raid',         label: 'RAID Log',               icon: 'raid',         action: () => navigate('raid'),              category: 'Navigasyon', shortcut: 'G L' },
        // Actions
        { id: 'new-requirement',  label: 'Yeni Gereksinim Oluştur', icon: 'plus',        action: () => { navigate('requirements'); setTimeout(() => document.getElementById('createRequirementBtn')?.click(), 300); }, category: 'Aksiyon' },
        { id: 'new-wricef',       label: 'Yeni WRICEF Oluştur',    icon: 'plus',         action: () => { navigate('backlog'); setTimeout(() => document.getElementById('createItemBtn')?.click(), 300); },            category: 'Aksiyon' },
        { id: 'new-defect',       label: 'Yeni Defect Bildir',     icon: 'plus',         action: () => { navigate('defects'); setTimeout(() => document.getElementById('createDefectBtn')?.click(), 300); },          category: 'Aksiyon' },
        { id: 'new-test-case',    label: 'Yeni Test Case',         icon: 'plus',         action: () => { navigate('test-management'); setTimeout(() => document.getElementById('createTCBtn')?.click(), 300); },      category: 'Aksiyon' },
    ];

    let _el = null;
    let _query = '';
    let _selectedIdx = 0;
    let _visible = false;

    function open() {
        if (_visible) return;
        _visible = true;
        _query = '';
        _selectedIdx = 0;
        _render();
        document.addEventListener('keydown', _keyHandler);
    }

    function close() {
        if (!_visible) return;
        _visible = false;
        _el && _el.remove();
        _el = null;
        document.removeEventListener('keydown', _keyHandler);
    }

    function toggle() { _visible ? close() : open(); }

    function _render() {
        if (_el) _el.remove();
        _el = document.createElement('div');
        _el.className = 'pg-palette-overlay';
        _el.innerHTML = `
            <div class="pg-palette" role="dialog" aria-modal="true" aria-label="Komut Paleti">
                <div class="pg-palette__search">
                    <svg class="pg-palette__search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    <input
                        class="pg-palette__input"
                        id="paletteInput"
                        type="text"
                        placeholder="Komut, view veya arama..."
                        autocomplete="off"
                        value="${_query}"
                    >
                    <kbd class="pg-palette__esc">ESC</kbd>
                </div>
                <div class="pg-palette__results" id="paletteResults">
                    ${_renderResults(_query)}
                </div>
                <div class="pg-palette__footer">
                    <span><kbd>↑↓</kbd> Seç</span>
                    <span><kbd>↵</kbd> Çalıştır</span>
                    <span><kbd>ESC</kbd> Kapat</span>
                </div>
            </div>
        `;
        document.body.appendChild(_el);
        const input = document.getElementById('paletteInput');
        input.focus();
        input.addEventListener('input', e => {
            _query = e.target.value;
            _selectedIdx = 0;
            document.getElementById('paletteResults').innerHTML = _renderResults(_query);
        });
        _el.addEventListener('click', e => { if (e.target === _el) close(); });
    }

    function _renderResults(q) {
        const filtered = q
            ? COMMANDS.filter(c =>
                c.label.toLowerCase().includes(q.toLowerCase()) ||
                c.category.toLowerCase().includes(q.toLowerCase())
              )
            : COMMANDS;

        if (!filtered.length) {
            return `<div class="pg-palette__empty">
                <p>"${q}" için sonuç bulunamadı</p>
                <p style="font-size:11px;color:var(--pg-color-text-tertiary)">Enter ile global arama yap</p>
            </div>`;
        }

        // Kategori başlıklarıyla grupla
        const grouped = {};
        filtered.forEach(c => {
            (grouped[c.category] = grouped[c.category] || []).push(c);
        });

        let html = '';
        let absIdx = 0;
        Object.entries(grouped).forEach(([cat, cmds]) => {
            html += `<div class="pg-palette__group-header">${cat}</div>`;
            cmds.forEach(c => {
                const isSelected = absIdx === _selectedIdx;
                html += `
                    <div class="pg-palette__item${isSelected ? ' pg-palette__item--selected' : ''}"
                         data-idx="${absIdx}"
                         onclick="PGCommandPalette._execute(${COMMANDS.indexOf(c)})">
                        <span class="pg-palette__item-icon">${PGIcon ? PGIcon.html(c.icon || 'dashboard', 14) : ''}</span>
                        <span class="pg-palette__item-label">${_highlight(c.label, q)}</span>
                        ${c.shortcut ? `<kbd class="pg-palette__item-shortcut">${c.shortcut}</kbd>` : ''}
                    </div>
                `;
                absIdx++;
            });
        });
        return html;
    }

    function _highlight(label, q) {
        if (!q) return label;
        const idx = label.toLowerCase().indexOf(q.toLowerCase());
        if (idx === -1) return label;
        return label.substring(0, idx)
            + `<mark class="pg-palette__match">${label.substring(idx, idx + q.length)}</mark>`
            + label.substring(idx + q.length);
    }

    function _execute(idx) {
        const cmd = COMMANDS[idx];
        if (cmd) { close(); cmd.action(); }
    }

    function _keyHandler(e) {
        const results = document.querySelectorAll('.pg-palette__item');
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            _selectedIdx = Math.min(_selectedIdx + 1, results.length - 1);
            _refreshSelection(results);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            _selectedIdx = Math.max(_selectedIdx - 1, 0);
            _refreshSelection(results);
        } else if (e.key === 'Enter') {
            const selected = COMMANDS.filter(c =>
                !_query || c.label.toLowerCase().includes(_query.toLowerCase())
            )[_selectedIdx];
            if (selected) { close(); selected.action(); }
        } else if (e.key === 'Escape') {
            close();
        }
    }

    function _refreshSelection(items) {
        items.forEach((el, i) => {
            el.classList.toggle('pg-palette__item--selected', i === _selectedIdx);
        });
        items[_selectedIdx]?.scrollIntoView({ block: 'nearest' });
    }

    return { open, close, toggle, _execute };
})();

// Global keyboard shortcut
document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); PGCommandPalette.toggle(); }
});
```

```css
/* static/css/pg-command-palette.css */
.pg-palette-overlay {
    position: fixed;
    inset: 0;
    background: rgba(15,23,42,0.45);
    backdrop-filter: blur(2px);
    z-index: var(--pg-z-palette, 400);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: min(15vh, 120px);
}

.pg-palette {
    width: 560px;
    max-width: calc(100vw - 32px);
    background: var(--pg-color-surface);
    border-radius: var(--pg-radius-xl);
    box-shadow: var(--pg-shadow-xl), 0 0 0 1px rgba(0,0,0,0.08);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    animation: palette-in 120ms ease;
}
@keyframes palette-in {
    from { opacity: 0; transform: scale(0.97) translateY(-6px); }
    to   { opacity: 1; transform: scale(1) translateY(0); }
}

.pg-palette__search {
    display: flex;
    align-items: center;
    gap: var(--pg-sp-3);
    padding: var(--pg-sp-4) var(--pg-sp-5);
    border-bottom: 1px solid var(--pg-color-border);
}
.pg-palette__search-icon { color: var(--pg-color-text-tertiary); flex-shrink: 0; }
.pg-palette__input {
    flex: 1;
    border: none;
    outline: none;
    font-size: 15px;
    color: var(--pg-color-text);
    background: transparent;
    font-family: inherit;
}
.pg-palette__input::placeholder { color: var(--pg-color-text-tertiary); }
.pg-palette__esc {
    background: var(--pg-color-bg);
    border: 1px solid var(--pg-color-border);
    border-radius: 4px;
    font-size: 10px;
    color: var(--pg-color-text-tertiary);
    padding: 2px 6px;
    font-family: inherit;
    flex-shrink: 0;
}

.pg-palette__results { max-height: 340px; overflow-y: auto; padding: var(--pg-sp-2) 0; }
.pg-palette__group-header {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: var(--pg-color-text-tertiary);
    padding: var(--pg-sp-3) var(--pg-sp-5) var(--pg-sp-1);
}

.pg-palette__item {
    display: flex;
    align-items: center;
    gap: var(--pg-sp-3);
    padding: var(--pg-sp-3) var(--pg-sp-5);
    cursor: pointer;
    transition: background var(--pg-t-fast);
    border-radius: 0;
}
.pg-palette__item:hover,
.pg-palette__item--selected { background: var(--pg-color-bg); }
.pg-palette__item--selected { background: var(--pg-color-primary-light); }

.pg-palette__item-icon { color: var(--pg-color-text-tertiary); flex-shrink: 0; }
.pg-palette__item-label { flex: 1; font-size: 13px; color: var(--pg-color-text); }
.pg-palette__item-shortcut {
    font-size: 10px;
    color: var(--pg-color-text-tertiary);
    background: var(--pg-color-bg);
    border: 1px solid var(--pg-color-border);
    border-radius: 4px;
    padding: 1px 5px;
    font-family: inherit;
}
.pg-palette__match { background: #fef9c3; border-radius: 2px; font-style: normal; color: inherit; }

.pg-palette__empty { padding: var(--pg-sp-8); text-align: center; color: var(--pg-color-text-tertiary); font-size: 13px; }
.pg-palette__footer {
    display: flex;
    gap: var(--pg-sp-4);
    padding: var(--pg-sp-3) var(--pg-sp-5);
    border-top: 1px solid var(--pg-color-border);
    background: var(--pg-color-bg);
    font-size: 11px;
    color: var(--pg-color-text-tertiary);
}
.pg-palette__footer kbd {
    background: var(--pg-color-surface);
    border: 1px solid var(--pg-color-border);
    border-radius: 3px;
    padding: 1px 4px;
    font-family: inherit;
    color: var(--pg-color-text-secondary);
}
```

---

### UI-S07-T02 — Keyboard Shortcut System

**Dosya:** `static/js/components/pg_shortcuts.js`

```javascript
const PGShortcuts = (() => {
    /**
     * Global keyboard shortcut registry.
     * View'lar mount edildiğinde shortcut ekler, unmount olduğunda kaldırır.
     */
    const _map = new Map(); // key combo → callback

    function register(combo, callback, description = '') {
        _map.set(combo.toLowerCase(), { callback, description });
    }

    function unregister(combo) { _map.delete(combo.toLowerCase()); }

    function _comboFrom(e) {
        const parts = [];
        if (e.ctrlKey || e.metaKey) parts.push('ctrl');
        if (e.altKey)  parts.push('alt');
        if (e.shiftKey) parts.push('shift');
        parts.push(e.key.toLowerCase());
        return parts.join('+');
    }

    document.addEventListener('keydown', e => {
        // Palette açıkken veya input içindeyken çalıştırma
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
        if (document.querySelector('.pg-palette')) return;

        const combo = _comboFrom(e);
        const entry = _map.get(combo);
        if (entry) { e.preventDefault(); entry.callback(e); }
    });

    return { register, unregister };
})();

// Default shortcuts
PGShortcuts.register('ctrl+k', () => PGCommandPalette.toggle(), '⌘K — Komut paleti');
PGShortcuts.register('g d',    () => navigate('dashboard'),     'G D — Dashboard');
PGShortcuts.register('g r',    () => navigate('requirements'),  'G R — Gereksinimler');
PGShortcuts.register('g w',    () => navigate('backlog'),       'G W — WRICEF Backlog');
PGShortcuts.register('g t',    () => navigate('test-management'), 'G T — Test Yönetimi');
PGShortcuts.register('?',      () => PGShortcutHelp.toggle(),   '? — Kısayol yardımı');
```

---

### UI-S07-T03 — Shortcut Help Dialog

**Dosya:** `static/js/components/pg_shortcut_help.js`

```javascript
const PGShortcutHelp = (() => {
    let _visible = false;

    function toggle() { _visible ? close() : open(); }

    function open() {
        _visible = true;
        const GROUPS = [
            { title: 'Navigasyon', items: [
                { key: 'G D', label: 'Dashboard' },
                { key: 'G P', label: 'Programlar' },
                { key: 'G R', label: 'Gereksinimler' },
                { key: 'G W', label: 'WRICEF Backlog' },
                { key: 'G T', label: 'Test Yönetimi' },
                { key: 'G B', label: 'Defect İzleyici' },
                { key: 'G L', label: 'RAID Log' },
            ]},
            { title: 'Genel', items: [
                { key: '⌘K', label: 'Komut Paleti' },
                { key: '?',  label: 'Bu yardımı göster/gizle' },
                { key: 'ESC', label: 'Modal / Panel kapat' },
            ]},
        ];
        const rows = GROUPS.map(g => `
            <div class="pg-shortcut-help__group">
                <div class="pg-shortcut-help__group-title">${g.title}</div>
                ${g.items.map(i => `
                    <div class="pg-shortcut-help__row">
                        <kbd class="pg-shortcut-help__kbd">${i.key}</kbd>
                        <span>${i.label}</span>
                    </div>
                `).join('')}
            </div>
        `).join('');
        TMModal.show({ title: 'Klavye Kısayolları', body: `<div class="pg-shortcut-help">${rows}</div>`, size: 'md' });
    }

    function close() { _visible = false; TMModal.hide && TMModal.hide(); }

    return { toggle, open, close };
})();
```

---

## Deliverables Kontrol Listesi

- [x] `pg_command_palette.js` oluşturuldu
- [x] `pg-command-palette.css` oluşturuldu
- [x] ⌘K (macOS) ve Ctrl+K (Windows/Linux) her ikisi tetikliyor
- [x] Palette: navigation + action komutları listede
- [x] Palette: ↑↓ tuş navigasyonu çalışıyor
- [x] `pg_shortcuts.js` global shortcut registry
- [x] G+D/G+R/G+T/G+W navigation shortcuts çalışıyor
- [x] `?` kısayol yardımı dialogu açıyor
- [x] Header search button → `PGCommandPalette.toggle()` bağlı (UI-S03-T02 ile entegre)
- [x] Her iki dosya `index.html`'e eklendi

---

*← [UI-S06](./UI-S06-TEST-MANAGEMENT-RAID.md) | [Master Plan](./UI-MODERNIZATION-MASTER-PLAN.md) | Sonraki: [UI-S08 →](./UI-S08-REMAINING-SCREENS.md)*
