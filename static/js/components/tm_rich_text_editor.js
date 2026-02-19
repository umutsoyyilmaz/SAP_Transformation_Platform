/* F1 — TMRichTextEditor: Lightweight markdown/WYSIWYG toolbar for descriptions */
var TMRichTextEditor = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    const TOOLBAR_ITEMS = [
        { cmd: 'bold',          icon: 'B',  title: 'Bold (Ctrl+B)' },
        { cmd: 'italic',        icon: 'I',  title: 'Italic (Ctrl+I)' },
        { cmd: 'underline',     icon: 'U',  title: 'Underline (Ctrl+U)' },
        { cmd: 'separator' },
        { cmd: 'insertUnorderedList', icon: '• List', title: 'Bullet List' },
        { cmd: 'insertOrderedList',   icon: '1. List', title: 'Numbered List' },
        { cmd: 'separator' },
        { cmd: 'createLink',    icon: '🔗', title: 'Insert Link' },
        { cmd: 'removeFormat',  icon: '⌧',  title: 'Clear Formatting' },
    ];

    /**
     * @param {HTMLElement} container
     * @param {Object}   config
     * @param {string}   config.value     — initial HTML content
     * @param {string}   config.placeholder
     * @param {number}   config.minHeight — pixels (default 120)
     * @param {boolean}  config.readOnly
     * @param {Function} config.onChange  — (html) => void
     */
    function render(container, config) {
        if (!container) return;
        const {
            value = '',
            placeholder = 'Enter description…',
            minHeight = 120,
            readOnly = false,
            onChange = null,
        } = config || {};

        if (readOnly) {
            container.innerHTML = `<div class="tm-rte tm-rte--readonly" style="min-height:${minHeight}px">${value || `<span style="color:var(--tm-text-tertiary)">${esc(placeholder)}</span>`}</div>`;
            return;
        }

        container.innerHTML = `
            <div class="tm-rte">
                <div class="tm-rte__toolbar">
                    ${TOOLBAR_ITEMS.map(item => {
                        if (item.cmd === 'separator') return '<span class="tm-rte__sep"></span>';
                        return `<button class="tm-rte__btn" data-cmd="${item.cmd}" title="${esc(item.title)}">${item.icon}</button>`;
                    }).join('')}
                </div>
                <div class="tm-rte__content" contenteditable="true" style="min-height:${minHeight}px" data-placeholder="${esc(placeholder)}">${value}</div>
            </div>
        `;

        const contentEl = container.querySelector('.tm-rte__content');

        // Toolbar commands
        container.querySelectorAll('.tm-rte__btn[data-cmd]').forEach(btn => {
            btn.addEventListener('mousedown', (e) => e.preventDefault()); // prevent focus loss
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.cmd;
                if (cmd === 'createLink') {
                    const url = prompt('Enter URL:');
                    if (url) document.execCommand('createLink', false, url);
                } else {
                    document.execCommand(cmd, false, null);
                }
                contentEl.focus();
            });
        });

        // Change callback
        if (typeof onChange === 'function') {
            contentEl.addEventListener('input', () => onChange(contentEl.innerHTML));
        }
    }

    /**
     * Get current HTML from the editor.
     * @param {HTMLElement} container
     * @returns {string}
     */
    function getValue(container) {
        const el = container?.querySelector('.tm-rte__content');
        return el ? el.innerHTML : '';
    }

    return { render, getValue };
})();
