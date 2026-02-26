/**
 * SAP Transformation Platform — Service Worker
 * Sprint 23: PWA Offline Support
 *
 * Strategy: Network-first with cache fallback for API calls,
 *           Cache-first for static assets.
 */

const CACHE_VERSION = 'sap-transform-v4';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const API_CACHE = `${CACHE_VERSION}-api`;

// Static assets to pre-cache on install
const PRECACHE_URLS = [
    '/',
    '/static/css/main.css',
    '/static/css/design-tokens.css',
    '/static/css/test-management-f1.css',
    '/static/css/explore-tokens.css',
    '/static/css/mobile.css',
    '/static/js/api.js',
    '/static/js/app.js',
    '/static/js/pwa.js',
    '/static/js/mobile.js',
    '/static/js/views/testing_shared.js',
    '/static/js/views/test_planning.js',
    '/static/js/views/test_execution.js',
    '/static/js/views/test_plan_detail.js',
    '/static/js/views/test_case_detail.js',
    '/static/js/views/defect_management.js',
    '/static/js/components/tm_tab_bar.js',
    '/static/js/components/tm_data_grid.js',
    '/static/js/components/tm_tree_panel.js',
    '/static/js/components/tm_split_pane.js',
    '/static/js/components/tm_toolbar.js',
    '/static/js/components/tm_property_panel.js',
    '/static/js/components/tm_status_badge.js',
    '/static/js/components/tm_context_menu.js',
    '/static/js/components/tm_toast.js',
    '/static/js/components/tm_modal.js',
    '/static/js/components/tm_dropdown_select.js',
    '/static/js/components/tm_chart_widget.js',
    '/static/js/components/tm_step_editor.js',
    '/static/js/components/tm_rich_text_editor.js',
    '/static/js/components/tm_breadcrumb.js',
    '/static/manifest.json',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
    '/offline',
];

// API paths that should be cached for offline read
const CACHEABLE_API_PATTERNS = [
    /\/api\/v1\/health/,
    /\/api\/v1\/programs/,
    /\/api\/v1\/ai\/prompts$/,
    /\/api\/v1\/ai\/usage/,
    /\/api\/v1\/programs\/\d+\/phases/,
    /\/api\/v1\/programs\/\d+\/workstreams/,
    /\/api\/v1\/dashboard/,
    /\/api\/v1\/explore\//,
    /\/api\/v1\/backlog/,
    /\/api\/v1\/testing\//,
    /\/api\/v1\/cutover\//,
    /\/api\/v1\/raid\//,
    /\/api\/v1\/metrics\//,
    /\/api\/v1\/traceability\//,
];

// ── Install ────────────────────────────────────────────────────────────

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(PRECACHE_URLS).catch((err) => {
                console.warn('[SW] Pre-cache failed for some assets:', err);
            });
        })
    );
    // Activate immediately
    self.skipWaiting();
});

// ── Activate ───────────────────────────────────────────────────────────

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(
                keyList.map((key) => {
                    if (key !== STATIC_CACHE && key !== API_CACHE) {
                        console.log('[SW] Removing old cache:', key);
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    // Claim all open clients
    self.clients.claim();
});

// ── Fetch ──────────────────────────────────────────────────────────────

self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Only handle same-origin
    if (url.origin !== location.origin) return;

    // Skip non-GET requests (POST, PATCH, DELETE → always network)
    if (request.method !== 'GET') return;

    // API requests → network-first, cache fallback for reads
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirstApi(request));
        return;
    }

    // Static assets → stale-while-revalidate (always fetches update in background)
    if (url.pathname.startsWith('/static/') || url.pathname === '/') {
        event.respondWith(staleWhileRevalidate(request));
        return;
    }

    // Navigation requests → network with offline fallback
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).catch(() => caches.match('/offline'))
        );
        return;
    }
});

// ── Strategies ─────────────────────────────────────────────────────────

/**
 * Stale-while-revalidate: serve from cache immediately, then update
 * cache from network in the background.  Next load gets fresh content.
 */
async function staleWhileRevalidate(request) {
    const cache = await caches.open(STATIC_CACHE);
    const cached = await cache.match(request);

    const networkPromise = fetch(request)
        .then((networkResponse) => {
            if (networkResponse.ok) {
                cache.put(request, networkResponse.clone());
            }
            return networkResponse;
        })
        .catch(() => null);

    // If we have a cached copy, return it immediately and update in background
    if (cached) {
        // Fire-and-forget: update cache in background
        networkPromise;
        return cached;
    }

    // No cache — must wait for network
    const networkResponse = await networkPromise;
    if (networkResponse) return networkResponse;

    return new Response('Offline — asset not cached', {
        status: 503,
        headers: { 'Content-Type': 'text/plain' },
    });
}

async function cacheFirstStatic(request) {
    const cached = await caches.match(request);
    if (cached) return cached;

    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch {
        return new Response('Offline — asset not cached', {
            status: 503,
            headers: { 'Content-Type': 'text/plain' },
        });
    }
}

async function networkFirstApi(request) {
    const isCacheable = CACHEABLE_API_PATTERNS.some((re) => re.test(new URL(request.url).pathname));

    try {
        const networkResponse = await fetch(request);
        // Cache successful GET responses for cacheable endpoints
        if (networkResponse.ok && isCacheable) {
            const cache = await caches.open(API_CACHE);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch {
        // Offline — try cache
        if (isCacheable) {
            const cached = await caches.match(request);
            if (cached) return cached;
        }
        return new Response(JSON.stringify({
            error: 'offline',
            message: 'No network connection. Cached data not available for this endpoint.',
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
        });
    }
}

// ── Background Sync (future: queue offline mutations) ──────────────────

self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-pending-changes') {
        event.waitUntil(syncPendingChanges());
    }
});

async function syncPendingChanges() {
    // Future: read from IndexedDB and replay POST/PATCH requests
    console.log('[SW] Background sync triggered — no pending changes.');
}

// ── Push Notifications (future) ────────────────────────────────────────

self.addEventListener('push', (event) => {
    if (!event.data) return;
    const data = event.data.json();
    event.waitUntil(
        self.registration.showNotification(data.title || 'SAP Platform', {
            body: data.body || '',
            icon: '/static/icons/icon-192.png',
            badge: '/static/icons/icon-72.png',
            tag: data.tag || 'default',
            data: { url: data.url || '/' },
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = event.notification.data?.url || '/';
    event.waitUntil(
        self.clients.matchAll({ type: 'window' }).then((clients) => {
            for (const client of clients) {
                if (client.url.includes(url) && 'focus' in client) {
                    return client.focus();
                }
            }
            return self.clients.openWindow(url);
        })
    );
});
