/**
 * pg_shortcut_help.js — UI-S07-T03
 *
 * PGShortcutHelp — Keyboard shortcuts help dialog.
 * Opened with the ? key or PGShortcutHelp.toggle().
 */
const PGShortcutHelp = (() => {
    'use strict';

    let _visible = false;

    const GROUPS = [
        { title: 'Navigation', items: [
            { key: 'G D', label: 'Dashboard' },
            { key: 'G P', label: 'Programs' },
            { key: 'G R', label: 'Requirements' },
            { key: 'G W', label: 'WRICEF Backlog' },
            { key: 'G T', label: 'Test Management' },
            { key: 'G B', label: 'Defect Tracker' },
            { key: 'G L', label: 'RAID Log' },
        ]},
        { title: 'General', items: [
            { key: '⌘K', label: 'Command Palette' },
            { key: '?',   label: 'Show/hide this help' },
            { key: 'ESC', label: 'Close modal / panel' },
        ]},
    ];

    function toggle() { _visible ? close() : open(); }

    function open() {
        _visible = true;

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

        TMModal.show({
            title: 'Keyboard Shortcuts',
            body: `<div class="pg-shortcut-help">${rows}</div>`,
            size: 'md',
        });
    }

    function close() {
        _visible = false;
        if (typeof TMModal !== 'undefined' && TMModal.hide) {
            TMModal.hide();
        }
    }

    return { toggle, open, close };
})();
