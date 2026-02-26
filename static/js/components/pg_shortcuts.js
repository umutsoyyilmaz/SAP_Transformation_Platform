/**
 * pg_shortcuts.js — UI-S07-T02
 *
 * PGShortcuts — Global keyboard shortcut registry.
 * Adds shortcuts when views are mounted, removes them when unmounted.
 *
 * Usage:
 *   PGShortcuts.register('ctrl+s', () => saveForm(), 'Save');
 *   PGShortcuts.unregister('ctrl+s');
 */
const PGShortcuts = (() => {
    'use strict';

    const _map = new Map(); // key combo → { callback, description }

    function register(combo, callback, description) {
        _map.set(combo.toLowerCase(), { callback, description: description || '' });
    }

    function unregister(combo) {
        _map.delete(combo.toLowerCase());
    }

    function _comboFrom(e) {
        const parts = [];
        if (e.ctrlKey || e.metaKey) parts.push('ctrl');
        if (e.altKey) parts.push('alt');
        if (e.shiftKey) parts.push('shift');
        parts.push(e.key.toLowerCase());
        return parts.join('+');
    }

    document.addEventListener('keydown', e => {
        // Do not run in input fields or when command palette is open
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
        if (document.querySelector('.pg-palette')) return;

        const combo = _comboFrom(e);
        const entry = _map.get(combo);
        if (entry) { e.preventDefault(); entry.callback(e); }
    });

    return { register, unregister };
})();

// ── Default shortcuts ────────────────────────────────────────────────────
PGShortcuts.register('g',       () => { /* sequence prefix — handled by pg_command_palette */ }, 'G — Navigation prefix');
PGShortcuts.register('g d',     () => navigate('dashboard'),       'G D — Dashboard');
PGShortcuts.register('g p',     () => navigate('programs'),        'G P — Programs');
PGShortcuts.register('g r',     () => navigate('requirements'),    'G R — Requirements');
PGShortcuts.register('g w',     () => navigate('backlog'),         'G W — WRICEF Backlog');
PGShortcuts.register('g t',     () => navigate('test-management'), 'G T — Test Management');
PGShortcuts.register('g b',     () => navigate('defects'),         'G B — Defect Tracker');
PGShortcuts.register('g l',     () => navigate('raid'),            'G L — RAID Log');
PGShortcuts.register('?',       () => typeof PGShortcutHelp !== 'undefined' && PGShortcutHelp.toggle(), '? — Shortcut help');
