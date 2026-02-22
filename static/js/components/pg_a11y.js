/* ============================================================
   Perga Design System — pg_a11y.js
   UI-S09-T02: Accessibility utilities
   - Focus trap for modals/panels (WCAG 2.1 SC 2.1.2)
   - Auto-wiring via MutationObserver on #modalOverlay
   ============================================================ */
const PGa11y = (() => {
    const FOCUSABLE = [
        'a[href]',
        'button:not([disabled])',
        'input:not([disabled])',
        'select:not([disabled])',
        'textarea:not([disabled])',
        '[tabindex]:not([tabindex="-1"])',
    ].join(',');

    /**
     * Trap keyboard focus inside containerEl.
     * Tab wraps to first; Shift+Tab wraps to last.
     * Auto-cleans when container leaves DOM.
     *
     * @param {HTMLElement} containerEl - The element to trap focus within.
     * @returns {Function} Cleanup function to remove the trap manually.
     */
    function trapFocus(containerEl) {
        const focusable = Array.from(containerEl.querySelectorAll(FOCUSABLE))
            .filter(el => el.offsetParent !== null); // visible only

        if (!focusable.length) return () => {};

        const first = focusable[0];
        const last  = focusable[focusable.length - 1];

        // Focus first element
        requestAnimationFrame(() => first.focus());

        function handler(e) {
            if (e.key !== 'Tab') return;
            if (e.shiftKey) {
                if (document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                }
            } else {
                if (document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        }

        containerEl.addEventListener('keydown', handler);

        return function cleanup() {
            containerEl.removeEventListener('keydown', handler);
        };
    }

    /**
     * Auto-wire focus trap to #modalOverlay via MutationObserver.
     * Activates whenever the modal becomes visible, cleans up on close.
     */
    function initModalFocusTrap() {
        const overlay = document.getElementById('modalOverlay');
        if (!overlay) return;

        let cleanup = null;

        const observer = new MutationObserver(() => {
            const isVisible = overlay.classList.contains('active') ||
                              overlay.style.display === 'flex' ||
                              overlay.style.display === 'block';

            if (isVisible && !cleanup) {
                const container = overlay.querySelector('.modal') || overlay;
                cleanup = trapFocus(container);
            } else if (!isVisible && cleanup) {
                cleanup();
                cleanup = null;
            }
        });

        observer.observe(overlay, { attributes: true, attributeFilter: ['class', 'style'] });
    }

    /**
     * Initialize theme toggle — reads localStorage.pg_theme and
     * sets data-theme on <html>. Wires #themeToggle button.
     *
     * @param {string} [defaultTheme='light'] - 'light' | 'dark'
     */
    function initThemeToggle(defaultTheme = 'light') {
        const stored = localStorage.getItem('pg_theme') || defaultTheme;
        _applyTheme(stored);

        const btn = document.getElementById('themeToggle');
        if (!btn) return;

        btn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme') || 'light';
            const next = current === 'dark' ? 'light' : 'dark';
            _applyTheme(next);
            localStorage.setItem('pg_theme', next);
        });
    }

    function _applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const btn = document.getElementById('themeToggle');
        if (!btn) return;
        if (typeof PGIcon !== 'undefined') {
            btn.innerHTML = theme === 'dark'
                ? PGIcon.html('sun', 14)
                : PGIcon.html('moon', 14);
        }
        btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
        btn.setAttribute('title', theme === 'dark' ? 'Light mode' : 'Dark mode');
    }

    return { trapFocus, initModalFocusTrap, initThemeToggle };
})();
