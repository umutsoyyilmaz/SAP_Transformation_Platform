/**
 * SAP Transformation Platform — Mobile Touch Components
 * Sprint 23: Hamburger menu, bottom nav, pull-to-refresh, sidebar overlay.
 */

const MobileUI = (() => {
    let _sidebarOpen = false;

    // ── Hamburger Toggle ───────────────────────────────────────────────

    function _initHamburger() {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        // Create hamburger button
        let btn = document.getElementById('hamburgerBtn');
        if (!btn) {
            btn = document.createElement('button');
            btn.id = 'hamburgerBtn';
            btn.className = 'hamburger-btn';
            btn.setAttribute('aria-label', 'Toggle navigation menu');
            btn.setAttribute('aria-expanded', 'false');
            btn.innerHTML = '☰';
            const logo = document.querySelector('.shell-header__logo');
            if (logo) {
                logo.parentNode.insertBefore(btn, logo);
            }
        }

        // Create backdrop
        let backdrop = document.getElementById('sidebarBackdrop');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.id = 'sidebarBackdrop';
            backdrop.className = 'sidebar-backdrop';
            document.body.appendChild(backdrop);
        }

        btn.addEventListener('click', toggleSidebar);
        backdrop.addEventListener('click', closeSidebar);

        // Close sidebar on nav item click (mobile)
        sidebar.querySelectorAll('.sidebar__item').forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    closeSidebar();
                }
            });
        });
    }

    function toggleSidebar() {
        _sidebarOpen ? closeSidebar() : openSidebar();
    }

    function openSidebar() {
        const sidebar = document.getElementById('sidebar');
        const backdrop = document.getElementById('sidebarBackdrop');
        const btn = document.getElementById('hamburgerBtn');
        if (!sidebar) return;

        sidebar.classList.add('open');
        if (backdrop) backdrop.classList.add('visible');
        if (btn) {
            btn.setAttribute('aria-expanded', 'true');
            btn.innerHTML = '✕';
        }
        _sidebarOpen = true;
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        const backdrop = document.getElementById('sidebarBackdrop');
        const btn = document.getElementById('hamburgerBtn');
        if (!sidebar) return;

        sidebar.classList.remove('open');
        if (backdrop) backdrop.classList.remove('visible');
        if (btn) {
            btn.setAttribute('aria-expanded', 'false');
            btn.innerHTML = '☰';
        }
        _sidebarOpen = false;
        document.body.style.overflow = '';
    }

    // ── Bottom Navigation Bar ──────────────────────────────────────────

    function _initBottomNav() {
        if (document.getElementById('bottomNav')) return;

        const nav = document.createElement('nav');
        nav.id = 'bottomNav';
        nav.className = 'bottom-nav';
        nav.setAttribute('aria-label', 'Main navigation');
        nav.innerHTML = `
            <div class="bottom-nav__items">
                <button class="bottom-nav__item active" data-view="dashboard" aria-label="Dashboard">
                    <span class="bottom-nav__item-icon">📊</span>
                    <span class="bottom-nav__item-label">Dashboard</span>
                </button>
                <button class="bottom-nav__item" data-view="backlog" aria-label="Build">
                    <span class="bottom-nav__item-icon">⚙️</span>
                    <span class="bottom-nav__item-label">Build</span>
                </button>
                <button class="bottom-nav__item" data-view="test-planning" aria-label="Testing">
                    <span class="bottom-nav__item-icon">📋</span>
                    <span class="bottom-nav__item-label">Testing</span>
                </button>
                <button class="bottom-nav__item" data-view="ai-query" aria-label="AI">
                    <span class="bottom-nav__item-icon">🤖</span>
                    <span class="bottom-nav__item-label">AI</span>
                </button>
                <button class="bottom-nav__item" data-view="more-menu" aria-label="More">
                    <span class="bottom-nav__item-icon">☰</span>
                    <span class="bottom-nav__item-label">More</span>
                </button>
            </div>
        `;
        document.body.appendChild(nav);

        // Wire up navigation
        nav.querySelectorAll('.bottom-nav__item').forEach(item => {
            item.addEventListener('click', () => {
                const view = item.getAttribute('data-view');
                if (view === 'more-menu') {
                    openSidebar();
                    return;
                }
                if (typeof App !== 'undefined' && App.navigate) {
                    App.navigate(view);
                }
                _updateBottomNavActive(view);
            });
        });
    }

    function _updateBottomNavActive(viewName) {
        const nav = document.getElementById('bottomNav');
        if (!nav) return;
        nav.querySelectorAll('.bottom-nav__item').forEach(item => {
            const v = item.getAttribute('data-view');
            item.classList.toggle('active', v === viewName);
        });
    }

    // ── Pull-to-Refresh ────────────────────────────────────────────────

    function _initPullToRefresh() {
        const main = document.getElementById('mainContent');
        if (!main) return;

        let startY = 0;
        let pulling = false;

        main.addEventListener('touchstart', (e) => {
            if (main.scrollTop === 0) {
                startY = e.touches[0].clientY;
                pulling = true;
            }
        }, { passive: true });

        main.addEventListener('touchmove', (e) => {
            if (!pulling) return;
            const delta = e.touches[0].clientY - startY;
            if (delta > 80 && main.scrollTop === 0) {
                let indicator = document.getElementById('pullRefreshIndicator');
                if (!indicator) {
                    indicator = document.createElement('div');
                    indicator.id = 'pullRefreshIndicator';
                    indicator.className = 'pull-refresh active';
                    indicator.textContent = '↻ Release to refresh';
                    main.insertBefore(indicator, main.firstChild);
                }
            }
        }, { passive: true });

        main.addEventListener('touchend', () => {
            if (!pulling) return;
            pulling = false;
            const indicator = document.getElementById('pullRefreshIndicator');
            if (indicator) {
                indicator.textContent = 'Refreshing...';
                // Trigger current view reload
                if (typeof App !== 'undefined' && App.renderCurrentView) {
                    App.renderCurrentView();
                } else {
                    window.location.reload();
                }
                setTimeout(() => indicator.remove(), 600);
            }
        }, { passive: true });
    }

    // ── Swipe-to-Navigate (back gesture) ───────────────────────────────

    function _initSwipeBack() {
        let touchStartX = 0;
        let touchStartY = 0;
        const SWIPE_THRESHOLD = 80;

        document.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            const deltaX = e.changedTouches[0].clientX - touchStartX;
            const deltaY = Math.abs(e.changedTouches[0].clientY - touchStartY);

            // Swipe right from left edge → open sidebar
            if (deltaX > SWIPE_THRESHOLD && deltaY < 50 && touchStartX < 30) {
                openSidebar();
            }
            // Swipe left → close sidebar if open
            if (deltaX < -SWIPE_THRESHOLD && deltaY < 50 && _sidebarOpen) {
                closeSidebar();
            }
        }, { passive: true });
    }

    // ── Resize Handler ─────────────────────────────────────────────────

    function _initResizeHandler() {
        let resizeTimer;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {
                if (window.innerWidth > 768 && _sidebarOpen) {
                    closeSidebar();
                }
            }, 150);
        });
    }

    // ── View Change Hook ───────────────────────────────────────────────

    function onViewChange(viewName) {
        _updateBottomNavActive(viewName);
        // Close sidebar on mobile after navigation
        if (window.innerWidth <= 768 && _sidebarOpen) {
            closeSidebar();
        }
    }

    // ── Init ───────────────────────────────────────────────────────────

    function init() {
        _initHamburger();
        _initBottomNav();
        _initPullToRefresh();
        _initSwipeBack();
        _initResizeHandler();
    }

    return {
        init,
        toggleSidebar,
        openSidebar,
        closeSidebar,
        onViewChange,
    };
})();

// Auto-init when DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', MobileUI.init);
} else {
    MobileUI.init();
}
