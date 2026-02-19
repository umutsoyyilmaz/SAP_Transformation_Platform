/* F1 — TMModal: Compact modal with header/body/footer, size variants */
var TMModal = (() => {
    let _backdropEl = null;
    let _stack = [];

    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    /**
     * Open a modal.
     * @param {Object} config
     * @param {string} config.title
     * @param {string} config.bodyHtml    — raw HTML for body
     * @param {string} [config.size]      — 'sm'|'md'|'lg'|'xl' (default 'md')
     * @param {Array}  [config.actions]   — [{label, primary?, danger?, onClick}]
     * @param {boolean} [config.closable] — show X button (default true)
     * @param {Function} [config.onClose] — closed callback
     * @param {Function} [config.onMount] — called after DOM insert with modal element
     * @returns {HTMLElement} modal element
     */
    function open(config) {
        const {
            title = '',
            bodyHtml = '',
            size = 'md',
            actions = [],
            closable = true,
            onClose = null,
            onMount = null,
        } = config || {};

        _ensureBackdrop();

        const modal = document.createElement('div');
        modal.className = `tm-modal tm-modal--${size}`;
        modal.innerHTML = `
            <div class="tm-modal__header">
                <span class="tm-modal__title">${esc(title)}</span>
                ${closable ? '<button class="tm-modal__close" data-modal-close>×</button>' : ''}
            </div>
            <div class="tm-modal__body">${bodyHtml}</div>
            ${actions.length ? `
                <div class="tm-modal__footer">
                    ${actions.map((a, i) => {
                        let cls = 'tm-modal__btn';
                        if (a.primary) cls += ' tm-modal__btn--primary';
                        if (a.danger) cls += ' tm-modal__btn--danger';
                        return `<button class="${cls}" data-action-idx="${i}">${esc(a.label)}</button>`;
                    }).join('')}
                </div>
            ` : ''}
        `;

        _backdropEl.appendChild(modal);
        _backdropEl.style.display = 'flex';
        _stack.push({ modal, onClose });

        requestAnimationFrame(() => modal.classList.add('is-visible'));

        // Close button
        const closeBtn = modal.querySelector('[data-modal-close]');
        if (closeBtn) closeBtn.addEventListener('click', () => close(modal));

        // Action buttons
        modal.querySelectorAll('[data-action-idx]').forEach(btn => {
            const idx = Number(btn.dataset.actionIdx);
            const action = actions[idx];
            if (action && typeof action.onClick === 'function') {
                btn.addEventListener('click', () => action.onClick(modal));
            }
        });

        if (typeof onMount === 'function') onMount(modal);

        return modal;
    }

    function close(modalEl) {
        if (!modalEl) {
            // Close topmost
            if (_stack.length) {
                const top = _stack.pop();
                _removeModal(top.modal);
                if (typeof top.onClose === 'function') top.onClose();
            }
        } else {
            const idx = _stack.findIndex(s => s.modal === modalEl);
            if (idx !== -1) {
                const entry = _stack.splice(idx, 1)[0];
                _removeModal(entry.modal);
                if (typeof entry.onClose === 'function') entry.onClose();
            }
        }

        if (_stack.length === 0 && _backdropEl) {
            _backdropEl.style.display = 'none';
        }
    }

    function closeAll() {
        while (_stack.length) close();
    }

    function _removeModal(el) {
        el.classList.remove('is-visible');
        setTimeout(() => { if (el.parentNode) el.parentNode.removeChild(el); }, 200);
    }

    function _ensureBackdrop() {
        if (_backdropEl) return;
        _backdropEl = document.createElement('div');
        _backdropEl.className = 'tm-modal-backdrop';
        _backdropEl.style.display = 'none';
        document.body.appendChild(_backdropEl);

        _backdropEl.addEventListener('click', (e) => {
            if (e.target === _backdropEl) close();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && _stack.length) close();
        });
    }

    return { open, close, closeAll };
})();
