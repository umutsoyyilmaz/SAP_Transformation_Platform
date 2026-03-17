/**
 * pg_command_palette.js — UI-S07-T01
 *
 * PGCommandPalette — Global command palette opened with ⌘K / Ctrl+K.
 * Combines Navigation, Action, and Search commands.
 */
const PGCommandPalette = (() => {
    'use strict';

    const SMART_SEARCH_QUERY_KEY = 'pg.aiSmartSearchQuery';

    const COMMANDS = [
        // Navigation
        { id: 'nav-dashboard',    label: 'Go to Dashboard',        icon: 'dashboard',    action: () => App.navigate('dashboard'),            category: 'Navigation', shortcut: 'G D' },
        { id: 'nav-programs',     label: 'Programs',               icon: 'programs',     action: () => App.navigate('programs'),             category: 'Navigation', shortcut: 'G P' },
        { id: 'nav-requirements', label: 'Requirements',           icon: 'requirements', action: () => App.navigate('explore-requirements'), category: 'Navigation', shortcut: 'G R' },
        { id: 'nav-backlog',      label: 'WRICEF Backlog',         icon: 'backlog',      action: () => App.navigate('backlog'),              category: 'Navigation', shortcut: 'G W' },
        { id: 'nav-test',         label: 'Test Management',        icon: 'test',         action: () => App.navigate('test-overview'),        category: 'Navigation', shortcut: 'G T' },
        { id: 'nav-defects',      label: 'Defect List',            icon: 'defect',       action: () => App.navigate('defect-management'),    category: 'Navigation', shortcut: 'G B' },
        { id: 'nav-raid',         label: 'RAID Log',               icon: 'raid',         action: () => App.navigate('raid'),                 category: 'Navigation', shortcut: 'G L' },
        { id: 'nav-ai-insights',  label: 'AI Insights',            icon: 'search',       action: () => App.navigate('ai-insights'),          category: 'Navigation' },
        // Actions
        { id: 'new-requirement', label: 'Create New Requirement',  icon: 'plus', action: () => { App.navigate('explore-requirements'); setTimeout(() => { if (typeof ExploreRequirementHubView !== 'undefined' && ExploreRequirementHubView.createRequirement) ExploreRequirementHubView.createRequirement(); }, 300); }, category: 'Action' },
        { id: 'new-wricef',      label: 'Create New WRICEF',      icon: 'plus', action: () => { App.navigate('backlog'); setTimeout(() => { if (typeof BacklogView !== 'undefined' && BacklogView.showCreateSelector) BacklogView.showCreateSelector(); }, 300); }, category: 'Action' },
        { id: 'new-defect',      label: 'Report New Defect',      icon: 'plus', action: () => { App.navigate('defect-management'); setTimeout(() => { if (typeof DefectManagementView !== 'undefined' && DefectManagementView.showDefectModal) DefectManagementView.showDefectModal(); }, 300); }, category: 'Action' },
        { id: 'new-test-case',   label: 'New Test Case',          icon: 'plus', action: () => { App.navigate('test-planning'); setTimeout(() => { if (typeof TestPlanningView !== 'undefined' && TestPlanningView.showCaseModal) TestPlanningView.showCaseModal(); }, 300); }, category: 'Action' },
    ];

    let _el = null;
    let _query = '';
    let _selectedIdx = 0;
    let _visible = false;
    let _visibleResults = [];

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
        _visibleResults = _buildResults('');
        _el.innerHTML = `
            <div class="pg-palette" role="dialog" aria-modal="true" aria-label="Command Palette">
                <div class="pg-palette__search">
                    <svg class="pg-palette__search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    <input
                        class="pg-palette__input"
                        id="paletteInput"
                        type="text"
                        placeholder="Command, view, or search..."
                        autocomplete="off"
                        value=""
                    >
                    <kbd class="pg-palette__esc">ESC</kbd>
                </div>
                <div class="pg-palette__results" id="paletteResults">
                    ${_renderResults('')}
                </div>
                <div class="pg-palette__footer">
                    <span><kbd>↑↓</kbd> Select</span>
                    <span><kbd>↵</kbd> Run</span>
                    <span><kbd>ESC</kbd> Close</span>
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

    function _buildResults(q) {
        const query = (q || '').trim();
        const filtered = query
            ? COMMANDS.filter(c =>
                c.label.toLowerCase().includes(query.toLowerCase()) ||
                c.category.toLowerCase().includes(query.toLowerCase())
              )
            : [...COMMANDS];

        if (query.length >= 2) {
            filtered.unshift({
                id: 'ai-smart-search',
                label: `AI Smart Search: ${query}`,
                icon: 'search',
                action: () => _runSmartSearch(query),
                category: 'AI',
                shortcut: 'Enter',
            });
        }

        return filtered;
    }

    function _renderResults(q) {
        _visibleResults = _buildResults(q);

        if (!_visibleResults.length) {
            return `<div class="pg-palette__empty">
                <p>No results found for "${_escHtml(q)}"</p>
                <p style="font-size:11px;color:var(--pg-color-text-tertiary)">Type at least 2 characters to run AI Smart Search</p>
            </div>`;
        }

        // Group by category headers
        const grouped = {};
        _visibleResults.forEach(c => {
            (grouped[c.category] = grouped[c.category] || []).push(c);
        });

        let html = '';
        let absIdx = 0;
        Object.entries(grouped).forEach(([cat, cmds]) => {
            html += `<div class="pg-palette__group-header">${_escHtml(cat)}</div>`;
            cmds.forEach(c => {
                const isSelected = absIdx === _selectedIdx;
                html += `
                    <div class="pg-palette__item${isSelected ? ' pg-palette__item--selected' : ''}"
                         data-idx="${absIdx}"
                         onclick="PGCommandPalette._execute(${absIdx})">
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
        const cmd = _visibleResults[idx];
        if (cmd) { close(); cmd.action(); }
    }

    function _runSmartSearch(query) {
        const term = (query || '').trim();
        if (!term) return;

        if (!App.getActiveProgram()) {
            App.toast('Select a program first to run AI Smart Search', 'warning');
            return;
        }

        try {
            sessionStorage.setItem(SMART_SEARCH_QUERY_KEY, term);
        } catch {
            // Ignore sessionStorage issues; navigation still works.
        }

        App.navigate('ai-insights');
    }

    // ── Keyboard navigation ──────────────────────────────────────────────

    function _keyHandler(e) {
        const results = document.querySelectorAll('.pg-palette__item');
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            _selectedIdx = Math.min(_selectedIdx + 1, Math.max(results.length - 1, 0));
            _refreshSelection(results);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            _selectedIdx = Math.max(_selectedIdx - 1, 0);
            _refreshSelection(results);
        } else if (e.key === 'Enter') {
            const selected = _visibleResults[_selectedIdx];
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
