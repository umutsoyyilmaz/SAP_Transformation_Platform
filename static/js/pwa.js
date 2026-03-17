/**
 * SAP Transformation Platform — PWA Manager
 * Sprint 23: Service Worker registration, install prompt, online/offline detection.
 */

const PWA = (() => {
    let _deferredPrompt = null;
    let _swRegistration = null;

    function _isLocalRuntime() {
        const host = window.location.hostname || '';
        return host === 'localhost' || host === '127.0.0.1';
    }

    async function _clearDevServiceWorkers() {
        if (!('serviceWorker' in navigator)) return;
        try {
            const registrations = await navigator.serviceWorker.getRegistrations();
            await Promise.all(registrations.map((registration) => registration.unregister()));
        } catch (err) {
            console.warn('[PWA] Failed to unregister service workers:', err);
        }

        if (!('caches' in window)) return;
        try {
            const keys = await caches.keys();
            const pwaKeys = keys.filter((key) => key.startsWith('sap-transform-'));
            await Promise.all(pwaKeys.map((key) => caches.delete(key)));
        } catch (err) {
            console.warn('[PWA] Failed to clear local PWA caches:', err);
        }
    }

    // ── Service Worker Registration ────────────────────────────────────

    async function register() {
        if (!('serviceWorker' in navigator)) {
            console.log('[PWA] Service workers not supported');
            return;
        }

        if (_isLocalRuntime()) {
            await _clearDevServiceWorkers();
            console.log('[PWA] Local runtime detected; service worker disabled');
            return;
        }

        try {
            _swRegistration = await navigator.serviceWorker.register('/static/sw.js', {
                scope: '/',
            });
            console.log('[PWA] Service worker registered:', _swRegistration.scope);

            // Listen for updates
            _swRegistration.addEventListener('updatefound', () => {
                const newWorker = _swRegistration.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'activated') {
                        _showUpdateToast();
                    }
                });
            });
        } catch (err) {
            console.warn('[PWA] SW registration failed:', err);
        }
    }

    // ── Install Prompt ─────────────────────────────────────────────────

    function _listenForInstallPrompt() {
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            _deferredPrompt = e;
            _showInstallBanner();
        });

        window.addEventListener('appinstalled', () => {
            _deferredPrompt = null;
            _hideInstallBanner();
            console.log('[PWA] App installed');
        });
    }

    async function promptInstall() {
        if (!_deferredPrompt) return false;
        _deferredPrompt.prompt();
        const { outcome } = await _deferredPrompt.userChoice;
        _deferredPrompt = null;
        _hideInstallBanner();
        return outcome === 'accepted';
    }

    function _showInstallBanner() {
        let banner = document.getElementById('pwaInstallBanner');
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'pwaInstallBanner';
            banner.className = 'pwa-install-banner';
            banner.innerHTML = `
                <div class="pwa-install-banner__content">
                    <span class="pwa-install-banner__icon">📱</span>
                    <span class="pwa-install-banner__text">Install this app for quick access</span>
                    <button class="pwa-install-banner__btn" onclick="PWA.promptInstall()">Install</button>
                    <button class="pwa-install-banner__close" onclick="PWA.dismissInstall()">✕</button>
                </div>
            `;
            document.body.appendChild(banner);
        }
        banner.classList.add('visible');
    }

    function _hideInstallBanner() {
        const banner = document.getElementById('pwaInstallBanner');
        if (banner) banner.classList.remove('visible');
    }

    function dismissInstall() {
        _hideInstallBanner();
        sessionStorage.setItem('pwa_install_dismissed', '1');
    }

    // ── Online/Offline Detection ───────────────────────────────────────

    function _listenForConnectivity() {
        function _update() {
            const indicator = document.getElementById('offlineIndicator');
            if (navigator.onLine) {
                document.body.classList.remove('is-offline');
                if (indicator) indicator.classList.remove('visible');
            } else {
                document.body.classList.add('is-offline');
                if (indicator) indicator.classList.add('visible');
            }
        }

        window.addEventListener('online', _update);
        window.addEventListener('offline', _update);
        _update(); // initial state
    }

    // ── Update Toast ───────────────────────────────────────────────────

    function _showUpdateToast() {
        if (typeof App !== 'undefined' && App.toast) {
            App.toast('A new version is available. Refresh to update.', 'info');
        }
    }

    // ── Init ───────────────────────────────────────────────────────────

    function init() {
        register();
        _listenForInstallPrompt();
        _listenForConnectivity();

        // Create offline indicator
        if (!document.getElementById('offlineIndicator')) {
            const el = document.createElement('div');
            el.id = 'offlineIndicator';
            el.className = 'offline-indicator';
            el.innerHTML = '<span>⚡ Offline Mode</span>';
            document.body.appendChild(el);
        }
    }

    // ── Public API ─────────────────────────────────────────────────────

    return {
        init,
        register,
        promptInstall,
        dismissInstall,
        isOnline: () => navigator.onLine,
        isInstalled: () => window.matchMedia('(display-mode: standalone)').matches,
    };
})();

// Auto-init when DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', PWA.init);
} else {
    PWA.init();
}
