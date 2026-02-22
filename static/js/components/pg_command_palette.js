/**
 * pg_command_palette.js — UI-S07-T01
 *
 * PGCommandPalette — ⌘K / Ctrl+K ile açılan global komut paleti.
 * Navigation, Action ve Search komutlarını birleştirir.
 */
const PGCommandPalette = (() => {
    'use strict';

    const COMMANDS = [
        // Navigation
        { id: 'nav-dashboard',    label: "Dashboard'a git",       icon: 'dashboard',    action: () => navigate('dashboard'),         category: 'Navigasyon', shortcut: 'G D' },
        { id: 'nav-programs',     label: 'Programlar',             icon: 'programs',     action: () => navigate('programs'),          category: 'Navigasyon', shortcut: 'G P' },
        { id: 'nav-requirements', label: 'Gereksinimler',          icon: 'requirements', action: () => navigate('requirements'),      category: 'Navigasyon', shortcut: 'G R' },
        { id: 'nav-backlog',      label: 'WRICEF Backlog',         icon: 'backlog',      action: () => navigate('backlog'),           category: 'Navigasyon', shortcut: 'G W' },
        { id: 'nav-test',         label: 'Test Yönetimi',          icon: 'test',         action: () => navigate('test-management'),   category: 'Navigasyon', shortcut: 'G T' },
        { id: 'nav-defects',      label: 'Defect Listesi',         icon: 'defect',       action: () => navigate('defects'),           category: 'Navigasyon', shortcut: 'G B' },
        { id: 'nav-raid',         label: 'RAID Log',               icon: 'raid',         action: () => navigate('raid'),              category: 'Navigasyon', shortcut: 'G L' },
        // Actions
        { id: 'new-requirement', label: 'Yeni Gereksinim Oluştur', icon: 'plus', action: () => { navigate('requirements'); setTimeout(() => document.getElementById('createRequirementBtn')?.click(), 300); }, category: 'Aksiyon' },
        { id: 'new-wricef',      label: 'Yeni WRICEF Oluştur',    icon: 'plus', action: () => { navigate('backlog'); setTimeout(() => document.getElementById('createItemBtn')?.click(), 300); },            category: 'Aksiyon' },
        { id: 'new-defect',      label: 'Yeni Defect Bildir',     icon: 'plus', action: () => { navigate('defects'); setTimeout(() => document.getElementById('createDefectBtn')?.click(), 300); },          category: 'Aksiyon' },
        { id: 'new-test-case',   label: 'Yeni Test Case',         icon: 'plus', action: () => { navigate('test-management'); setTimeout(() => document.getElementById('createTCBtn')?.click(), 300); },      category: 'Aksiyon' },
    ];

    let _el = null;
    let _query = '';
    let _selectedIdx = 0;
    let _visible = false;

    // ── Public API ───────────────────────────────────────────────────────

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
        if (_el) { _el.remove(); _el = null; }
        document.removeEventListener('keydown', _keyHandler);
    }

    function toggle() { _visible ? close() : open(); }

    // ── Render ───────────────────────────────────────────────────────────

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
                        value=""
                    >
                    <kbd class="pg-palette__esc">ESC</kbd>
                </div>
                <div class="pg-palette__results" id="paletteResults">
                    ${_renderResults('')}
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
        if (input) {
            input.focus();
            input.addEventListener('input', e => {
                _query = e.target.value;
                _selectedIdx = 0;
                const resultsEl = document.getElementById('paletteResults');
                if (resultsEl) resultsEl.innerHTML = _renderResults(_query);
            });
        }

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
                <p>"${_escHtml(q)}" için sonuç bulunamadı</p>
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
            html += `<div class="pg-palette__group-header">${_escHtml(cat)}</div>`;
            cmds.forEach(c => {
                const isSelected = absIdx === _selectedIdx;
                const globalIdx = COMMANDS.indexOf(c);
                html += `
                    <div class="pg-palette__item${isSelected ? ' pg-palette__item--selected' : ''}"
                         data-idx="${absIdx}"
                         onclick="PGCommandPalette._execute(${globalIdx})">
                        <span class="pg-palette__item-icon">${typeof PGIcon !== 'undefined' ? PGIcon.html(c.icon || 'dashboard', 14) : ''}</span>
                        <span class="pg-palette__item-label">${_highlight(c.label, q)}</span>
                        ${c.shortcut ? `<kbd class="pg-palette__item-shortcut">${_escHtml(c.shortcut)}</kbd>` : ''}
                    </div>
                `;
                absIdx++;
            });
        });
        return html;
    }

    function _highlight(label, q) {
        if (!q) return _escHtml(label);
        const idx = label.toLowerCase().indexOf(q.toLowerCase());
        if (idx === -1) return _escHtml(label);
        return _escHtml(label.substring(0, idx))
            + `<mark class="pg-palette__match">${_escHtml(label.substring(idx, idx + q.length))}</mark>`
            + _escHtml(label.substring(idx + q.length));
    }

    function _escHtml(s) {
        const d = document.createElement('div');
        d.textContent = s ?? '';
        return d.innerHTML;
    }

    function _execute(idx) {
        const cmd = COMMANDS[idx];
        if (cmd) { close(); cmd.action(); }
    }

    // ── Keyboard navigation ──────────────────────────────────────────────

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
            const filtered = _query
                ? COMMANDS.filter(c =>
                    c.label.toLowerCase().includes(_query.toLowerCase()) ||
                    c.category.toLowerCase().includes(_query.toLowerCase())
                  )
                : COMMANDS;
            const selected = filtered[_selectedIdx];
            if (selected) { close(); selected.action(); }
        } else if (e.key === 'Escape') {
            close();
        }
    }

    function _refreshSelection(items) {
        items.forEach((el, i) => {
            el.classList.toggle('pg-palette__item--selected', i === _selectedIdx);
        });
        if (items[_selectedIdx]) {
            items[_selectedIdx].scrollIntoView({ block: 'nearest' });
        }
    }

    // ── Global Ctrl+K / ⌘K ──────────────────────────────────────────────

    document.addEventListener('keydown', e => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            toggle();
        }
    });

    return { open, close, toggle, _execute };
})();
