/**
 * SAP Transformation Platform — Auth Module
 *
 * Manages JWT authentication lifecycle:
 *   - Token storage (localStorage)
 *   - Silent token refresh
 *   - Auth guard (redirect to /login if unauthenticated)
 *   - User context (current user from JWT)
 *   - Logout
 *
 * Loaded BEFORE api.js and app.js.
 */
const Auth = (() => {
    'use strict';

    const TOKEN_KEY     = 'sap_access_token';
    const REFRESH_KEY   = 'sap_refresh_token';
    const USER_KEY      = 'sap_user';

    // Refresh access token 2 minutes before expiry
    const REFRESH_MARGIN_MS = 2 * 60 * 1000;
    let _refreshTimer = null;

    // ── Token Storage ───────────────────────────────────────────────

    function getAccessToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function getRefreshToken() {
        return localStorage.getItem(REFRESH_KEY);
    }

    function getUser() {
        try {
            return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
        } catch { return null; }
    }

    function setTokens(accessToken, refreshToken, user) {
        localStorage.setItem(TOKEN_KEY, accessToken);
        localStorage.setItem(REFRESH_KEY, refreshToken);
        if (user) {
            localStorage.setItem(USER_KEY, JSON.stringify(user));
        }
        _scheduleRefresh(accessToken);
    }

    function clearTokens() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        localStorage.removeItem(USER_KEY);
        if (_refreshTimer) {
            clearTimeout(_refreshTimer);
            _refreshTimer = null;
        }
    }

    // ── Token Parsing ───────────────────────────────────────────────

    function _parseJwt(token) {
        try {
            const base64 = token.split('.')[1]
                .replace(/-/g, '+')
                .replace(/_/g, '/');
            const json = decodeURIComponent(
                atob(base64).split('').map(c =>
                    '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                ).join('')
            );
            return JSON.parse(json);
        } catch { return null; }
    }

    function isTokenExpired(token) {
        const payload = _parseJwt(token);
        if (!payload || !payload.exp) return true;
        return Date.now() >= payload.exp * 1000;
    }

    function _getTokenExpiry(token) {
        const payload = _parseJwt(token);
        if (!payload || !payload.exp) return 0;
        return payload.exp * 1000; // ms
    }

    // ── Auth Check ─────────────────────────────────────────────────

    function isAuthenticated() {
        const token = getAccessToken();
        if (!token) return false;
        return !isTokenExpired(token);
    }

    // ── Token Refresh ──────────────────────────────────────────────

    function _scheduleRefresh(accessToken) {
        if (_refreshTimer) clearTimeout(_refreshTimer);

        const expiryMs = _getTokenExpiry(accessToken);
        if (!expiryMs) return;

        const delay = Math.max(expiryMs - Date.now() - REFRESH_MARGIN_MS, 10_000);
        _refreshTimer = setTimeout(() => _doRefresh(), delay);
    }

    async function _doRefresh() {
        const refreshToken = getRefreshToken();
        if (!refreshToken) {
            _handleSessionExpired();
            return;
        }

        try {
            const res = await fetch('/api/v1/auth/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: refreshToken }),
            });

            if (!res.ok) {
                _handleSessionExpired();
                return;
            }

            const data = await res.json();
            setTokens(data.access_token, data.refresh_token, getUser());
        } catch {
            // Network error — retry in 30s
            _refreshTimer = setTimeout(() => _doRefresh(), 30_000);
        }
    }

    function _handleSessionExpired() {
        clearTokens();
        window.location.href = '/login';
    }

    // ── Logout ─────────────────────────────────────────────────────

    async function logout() {
        const refreshToken = getRefreshToken();

        // Call logout API (best-effort)
        if (refreshToken) {
            try {
                await fetch('/api/v1/auth/logout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${getAccessToken()}`,
                    },
                    body: JSON.stringify({ refresh_token: refreshToken }),
                });
            } catch { /* ignore */ }
        }

        clearTokens();
        // Clear session storage (RoleNav cache etc.)
        sessionStorage.clear();
        window.location.href = '/login';
    }

    // ── Fetch User Profile ─────────────────────────────────────────

    async function fetchUserProfile() {
        const token = getAccessToken();
        if (!token) return null;

        try {
            const res = await fetch('/api/v1/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!res.ok) return null;
            const data = await res.json();
            // Update stored user
            if (data.user) {
                localStorage.setItem(USER_KEY, JSON.stringify(data.user));
            }
            return data;
        } catch { return null; }
    }

    // ── Auth Guard (call on SPA load) ─────────────────────────────

    function guard() {
        const token = getAccessToken();
        if (!token) {
            window.location.href = '/login';
            return false;
        }

        if (isTokenExpired(token)) {
            // Try refresh synchronously — if refresh token exists, try it
            const refreshTk = getRefreshToken();
            if (refreshTk) {
                _doRefresh(); // async, but we'll let it proceed
                return true;  // optimistic — the page will load
            }
            window.location.href = '/login';
            return false;
        }

        // Schedule refresh for later
        _scheduleRefresh(token);
        return true;
    }

    // ── Public API ─────────────────────────────────────────────────

    return {
        getAccessToken,
        getRefreshToken,
        getUser,
        setTokens,
        clearTokens,
        isAuthenticated,
        isTokenExpired,
        logout,
        fetchUserProfile,
        guard,
    };
})();
