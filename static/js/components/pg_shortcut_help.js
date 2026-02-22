/**
 * pg_shortcut_help.js — UI-S07-T03
 *
 * PGShortcutHelp — Klavye kısayolları yardım diyaloğu.
 * ? tuşu veya PGShortcutHelp.toggle() ile açılır.
 */
const PGShortcutHelp = (() => {
    'use strict';

    let _visible = false;

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
            { key: '?',   label: 'Bu yardımı göster/gizle' },
            { key: 'ESC', label: 'Modal / Panel kapat' },
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
            title: 'Klavye Kısayolları',
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
