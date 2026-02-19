/* F1 — TMToast: Non-blocking stacking notifications with auto-dismiss */
var TMToast = (() => {
    let _containerEl = null;
    let _counter = 0;

    const ICONS = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ',
    };

    function _ensureContainer() {
        if (_containerEl) return;
        _containerEl = document.createElement('div');
        _containerEl.className = 'tm-toast-container';
        document.body.appendChild(_containerEl);
    }

    /**
     * Show a toast notification.
     * @param {string} message
     * @param {string} [type='info'] — 'success'|'error'|'warning'|'info'
     * @param {number} [duration=4000] — auto-dismiss ms (0 = no auto)
     */
    function show(message, type, duration) {
        _ensureContainer();
        type = type || 'info';
        duration = duration !== undefined ? duration : 4000;
        _counter += 1;
        const id = `tm-toast-${_counter}`;

        const el = document.createElement('div');
        el.className = `tm-toast tm-toast--${type}`;
        el.id = id;
        el.innerHTML = `
            <span class="tm-toast__icon">${ICONS[type] || 'ℹ'}</span>
            <span class="tm-toast__message">${_esc(message)}</span>
            <button class="tm-toast__close" data-dismiss="${id}">×</button>
        `;

        _containerEl.appendChild(el);

        // Trigger enter animation
        requestAnimationFrame(() => el.classList.add('is-visible'));

        // Dismiss button
        el.querySelector('[data-dismiss]').addEventListener('click', () => _dismiss(el));

        // Auto dismiss
        if (duration > 0) {
            setTimeout(() => _dismiss(el), duration);
        }
    }

    function _dismiss(el) {
        el.classList.remove('is-visible');
        el.classList.add('is-leaving');
        setTimeout(() => {
            if (el.parentNode) el.parentNode.removeChild(el);
        }, 200);
    }

    function _esc(str) {
        const d = document.createElement('div');
        d.textContent = str ?? '';
        return d.innerHTML;
    }

    return { show };
})();
