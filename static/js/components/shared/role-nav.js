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
    const DEFAULT_PERMISSION_SOURCE = 'projectPermissions';
    const PLATFORM_PERMISSION_SOURCE = 'platformPermissions';
    const _cache = new Map(); // keyed by "source:pid:projectId:uid"
    const _permissionSources = new Map();

    registerPermissionSource(DEFAULT_PERMISSION_SOURCE, {
        requireProgram: true,
        fetcher: async (pid, uid) => {
            const res = await API.get(`/explore/user-permissions?project_id=${pid}&user_id=${uid}`);
            return {
                roles: res.roles || [],
                permissions: new Set(res.permissions || []),
                raw: res,
            };
        },
    });

    registerPermissionSource(PLATFORM_PERMISSION_SOURCE, {
        requireProgram: false,
        fetcher: async (_pid, _uid, ctx) => {
            const params = new URLSearchParams();
            if (ctx?.prog?.id) params.set('program_id', String(ctx.prog.id));
            if (ctx?.project?.id) params.set('project_id', String(ctx.project.id));
            const query = params.toString();
            const res = await API.get(`/auth/permission-snapshot${query ? `?${query}` : ''}`);
            return {
                roles: res.roles || [],
                permissions: new Set(res.permissions || []),
                raw: res,
            };
        },
    });

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
        resetCache();
    }

    // ── Permission fetch ────────────────────────────────────────────

    function _contextKey(source, pid, projectId, uid) {
        return `${source}:${pid}:${projectId ?? 'none'}:${uid}`;
    }

    function _resolveContext(source = DEFAULT_PERMISSION_SOURCE) {
        const user = getUser();
        const prog = App.getActiveProgram();
        const project = App.getActiveProject ? App.getActiveProject() : null;
        const provider = _permissionSources.get(source);
        const requireProgram = provider?.requireProgram !== false;
        if (!user) return null;
        if (requireProgram && !prog) return null;
        return { user, prog, project };
    }

    function registerPermissionSource(name, config) {
        if (!name || typeof config?.fetcher !== 'function') {
            throw new Error('Permission source requires a name and fetcher');
        }
        _permissionSources.set(name, {
            requireProgram: true,
            normalize: (payload) => payload,
            ...config,
        });
    }

    function _getCachedSourceContext(source, pid, projectId, uid) {
        return _cache.get(_contextKey(source, pid, projectId, uid)) || null;
    }

    function getPermissionSnapshot(source = DEFAULT_PERMISSION_SOURCE) {
        const ctx = _resolveContext(source);
        if (!ctx) return null;
        return _getCachedSourceContext(source, ctx.prog.id, ctx.project?.id, ctx.user.id);
    }

    async function _preloadSource(source = DEFAULT_PERMISSION_SOURCE, options = {}) {
        const provider = _permissionSources.get(source);
        if (!provider) {
            throw new Error(`Unknown permission source: ${source}`);
        }
        const ctx = _resolveContext(source);
        if (!ctx) return null;

        const key = _contextKey(source, ctx.prog.id, ctx.project?.id, ctx.user.id);
        if (!options.forceRefresh && _cache.has(key)) {
            return _cache.get(key);
        }
        try {
            const payload = await provider.fetcher(ctx.prog.id, ctx.user.id, ctx);
            const normalized = provider.normalize(payload) || payload;
            _cache.set(key, normalized);
            return normalized;
        } catch {
            const fallback = { roles: [], permissions: new Set() };
            _cache.set(key, fallback);
            return fallback;
        }
    }

    /**
     * Check if the current user has a specific permission.
     * @param {string} action - e.g. 'req_approve', 'workshop_complete'
     * @returns {Promise<boolean>}
     */
    async function can(action) {
        return canInSource(DEFAULT_PERMISSION_SOURCE, action);
    }

    async function canInSource(source, action) {
        const ctx = await _preloadSource(source);
        return Boolean(ctx?.permissions?.has(action));
    }

    /**
     * Synchronous permission check (uses cache, returns false if not yet loaded).
     */
    function canSync(action) {
        return canSyncInSource(DEFAULT_PERMISSION_SOURCE, action);
    }

    function canSyncInSource(source, action) {
        const ctx = getPermissionSnapshot(source);
        if (!ctx) return false;
        return Boolean(ctx.permissions?.has(action));
    }

    /**
     * Pre-load permissions for the current user and program.
     */
    async function preload() {
        await _preloadSource(DEFAULT_PERMISSION_SOURCE);
    }

    async function preloadSource(source, options = {}) {
        return _preloadSource(source, options);
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
        const onclick = allowed && opts.onclick ? `onclick="${escAttr(opts.onclick)}"` : '';
        const dataAttr = opts.dataId ? `data-id="${escAttr(opts.dataId)}"` : '';

        return `<button class="${cls}" ${onclick} ${disabled} title="${escAttr(title)}" ${dataAttr}>${icon}${label}</button>`;
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

    function escAttr(str) {
        return String(str ?? '')
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    /**
     * Reset permission cache (call on program switch).
     */
    function resetCache() {
        _cache.clear();
    }

    return {
        getUser, setUser,
        can, canSync, preload,
        canInSource, canSyncInSource, preloadSource,
        registerPermissionSource, getPermissionSnapshot,
        DEFAULT_PERMISSION_SOURCE, PLATFORM_PERMISSION_SOURCE,
        guardedButton, applyToDOM, getUserDisplay, resetCache,
    };
})();
