/**
 * SAP Transformation Platform — WR-3.1
 * Role-Based Navigation Controller
 *
 * Manages current user context and permission-based UI controls:
 *   - Gets active user from Auth module (JWT-based) or sessionStorage fallback
 *   - Fetches permissions from the backend
 *   - Provides helpers for conditional button rendering and disable/hide
 *
 * Usage:
 *   const can = await RoleNav.can('req_approve');
 *   const html = RoleNav.guardedButton('Approve', 'req_approve', { onclick: '...' });
 */
const RoleNav = (() => {
    'use strict';

    const STORAGE_KEY = 'sap_active_user';
    let _cache = {}; // keyed by "pid:uid"

    // ── User context ────────────────────────────────────────────────

    function getUser() {
        // Primary: read from sessionStorage (set by app.js from Auth module)
        try {
            const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
            if (stored) return stored;
        } catch { /* ignore */ }

        // Fallback: read from Auth module directly
        if (typeof Auth !== 'undefined') {
            const jwtUser = Auth.getUser();
            if (jwtUser) {
                return {
                    id: String(jwtUser.id),
                    name: jwtUser.full_name || jwtUser.email || 'User',
                    default_role: (jwtUser.roles && jwtUser.roles[0]) || 'viewer',
                };
            }
        }

        return null;
    }

    function setUser(user) {
        if (user) {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
                id: user.id,
                name: user.name || user.id,
                default_role: user.default_role || 'viewer',
            }));
        } else {
            sessionStorage.removeItem(STORAGE_KEY);
        }
        _cache = {};
    }

    // ── Permission fetch ────────────────────────────────────────────

    async function _fetchPermissions(pid, uid) {
        const key = `${pid}:${uid}`;
        if (_cache[key]) return _cache[key];
        try {
            const res = await API.get(`/explore/user-permissions?project_id=${pid}&user_id=${uid}`);
            const permSet = new Set(res.permissions || []);
            _cache[key] = { roles: res.roles || [], permissions: permSet };
            return _cache[key];
        } catch {
            return { roles: [], permissions: new Set() };
        }
    }

    /**
     * Check if the current user has a specific permission.
     * @param {string} action - e.g. 'req_approve', 'workshop_complete'
     * @returns {Promise<boolean>}
     */
    async function can(action) {
        const user = getUser();
        const prog = App.getActiveProgram();
        if (!user || !prog) return false;
        const ctx = await _fetchPermissions(prog.id, user.id);
        return ctx.permissions.has(action);
    }

    /**
     * Synchronous permission check (uses cache, returns false if not yet loaded).
     */
    function canSync(action) {
        const user = getUser();
        const prog = App.getActiveProgram();
        if (!user || !prog) return false;
        const key = `${prog.id}:${user.id}`;
        const ctx = _cache[key];
        if (!ctx) return false;
        return ctx.permissions.has(action);
    }

    /**
     * Pre-load permissions for the current user and program.
     */
    async function preload() {
        const user = getUser();
        const prog = App.getActiveProgram();
        if (user && prog) {
            await _fetchPermissions(prog.id, user.id);
        }
    }

    // ── UI helpers ──────────────────────────────────────────────────

    /**
     * Render a button that is disabled when the user lacks the required permission.
     * @param {string} label - Button text
     * @param {string} action - Required permission
     * @param {Object} opts - { class, onclick, icon, title }
     * @returns {string} HTML string
     */
    function guardedButton(label, action, opts = {}) {
        const allowed = canSync(action);
        const cls = opts.class || 'btn btn-primary btn-sm';
        const disabled = allowed ? '' : 'disabled';
        const title = allowed
            ? (opts.title || label)
            : `Permission required: ${action}`;
        const icon = opts.icon ? `${opts.icon} ` : '';
        const onclick = allowed && opts.onclick ? `onclick="${opts.onclick}"` : '';
        const dataAttr = opts.dataId ? `data-id="${opts.dataId}"` : '';

        return `<button class="${cls}" ${onclick} ${disabled} title="${title}" ${dataAttr}>${icon}${label}</button>`;
    }

    /**
     * Apply permission-based disable/hide to existing DOM elements.
     * Elements should have data-perm="action_name" attribute.
     */
    function applyToDOM() {
        document.querySelectorAll('[data-perm]').forEach(el => {
            const action = el.dataset.perm;
            const allowed = canSync(action);
            if (el.tagName === 'BUTTON' || el.tagName === 'A') {
                el.disabled = !allowed;
                if (!allowed) {
                    el.title = `Permission required: ${action}`;
                    el.classList.add('btn--perm-blocked');
                } else {
                    el.classList.remove('btn--perm-blocked');
                }
            } else {
                el.style.display = allowed ? '' : 'none';
            }
        });
    }

    /**
     * Get current user display string for headers.
     */
    function getUserDisplay() {
        const u = getUser();
        if (!u) return 'Guest';
        return `${u.name} (${u.default_role})`;
    }

    /**
     * Reset permission cache (call on program switch).
     */
    function resetCache() {
        _cache = {};
    }

    return {
        getUser, setUser, can, canSync, preload,
        guardedButton, applyToDOM, getUserDisplay, resetCache,
    };
})();
