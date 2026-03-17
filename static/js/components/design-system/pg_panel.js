/**
 * Perga Design System — PGPanel
 * UI-S05-T03: Slide-in detail panel component.
 *
 * API:
 *   PGPanel.open({ title, content, onClose?, variant? })
 *   PGPanel.close()
 */
const PGPanel = (() => {
    let _panelEl = null;

    function _removePanel(el, { invokeOnClose = false } = {}) {
        if (!el) return;
        if (invokeOnClose && typeof el._onClose === 'function') el._onClose();
        if (el.parentNode) el.parentNode.removeChild(el);
        const mainEl = document.getElementById('mainContent');
        if (mainEl) mainEl.classList.remove('has-panel');
    }

    /**
     * Open the slide-in panel.
     *
     * @param {object} opts
     * @param {string} opts.title   - Panel header title.
     * @param {string} opts.content - HTML string for the panel body.
     * @param {Function} [opts.onClose] - Callback invoked when panel closes.
     * @param {string} [opts.variant] - 'drawer' | 'dialog'
     */
    function open({ title, content, onClose, variant = 'drawer' }) {
        if (_panelEl) {
            const existing = _panelEl;
            _panelEl = null;
            _removePanel(existing, { invokeOnClose: true });
            document.removeEventListener('keydown', _escHandler);
        }

        _panelEl = document.createElement('div');
        _panelEl.className = `pg-panel pg-panel--open pg-panel--${variant}`;
        _panelEl.setAttribute('role', 'complementary');
        _panelEl.setAttribute('aria-label', title);
        _panelEl.onclick = (event) => {
            if (variant === 'dialog' && event.target === _panelEl) close();
        };
        _panelEl.innerHTML = `
            <div class="pg-panel__sheet">
                <div class="pg-panel__header">
                    <h3 class="pg-panel__title">${title}</h3>
                    <button class="pg-btn pg-btn--icon pg-panel__close" onclick="PGPanel.close()" aria-label="Close">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                            <line x1="18" y1="6" x2="6" y2="18"/>
                            <line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>
                <div class="pg-panel__body">${content}</div>
            </div>
        `;

        document.body.appendChild(_panelEl);

        const mainEl = document.getElementById('mainContent');
        if (mainEl && variant === 'drawer') {
            mainEl.classList.add('has-panel');
        }

        if (typeof onClose === 'function') _panelEl._onClose = onClose;
        document.addEventListener('keydown', _escHandler);
    }

    /**
     * Close and remove the panel.
     */
    function close() {
        if (!_panelEl) return;
        if (typeof _panelEl._onClose === 'function') _panelEl._onClose();

        _panelEl.classList.remove('pg-panel--open');
        const el = _panelEl;
        _panelEl = null;

        setTimeout(() => {
            _removePanel(el);
        }, 200);

        document.removeEventListener('keydown', _escHandler);
    }

    function _escHandler(e) {
        if (e.key === 'Escape') close();
    }

    return { open, close };
})();
