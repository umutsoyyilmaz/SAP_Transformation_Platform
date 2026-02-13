/**
 * SAP Transformation Management Platform
 * API Client Helper — fetch wrapper for all backend calls.
 */

const API = (() => {
    const BASE = '/api/v1';

    /**
     * Inject current user context into mutating request bodies.
     * Reads from RoleNav (sessionStorage) so every POST/PUT/PATCH
     * carries user_id, user_name, created_by, changed_by automatically.
     */
    function _injectUser(body) {
        if (!body || typeof body !== 'object') return body;
        // RoleNav is loaded before api.js — safe to call
        const user = (typeof RoleNav !== 'undefined') ? RoleNav.getUser() : null;
        if (!user) return body;

        const uid  = user.id   || 'system';
        const uname = user.name || 'System';

        // Only set if NOT already explicitly provided by caller
        if (!body.user_id)       body.user_id       = uid;
        if (!body.user_name)     body.user_name     = uname;
        if (!body.created_by)    body.created_by    = uname;
        if (!body.created_by_id) body.created_by_id = uid;
        if (!body.changed_by)    body.changed_by    = uname;

        return body;
    }

    async function request(method, path, body = null) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        // Auto-inject user info for mutating requests
        if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            body = _injectUser(body);
        }
        if (body) opts.body = JSON.stringify(body);

        const res = await fetch(`${BASE}${path}`, opts);

        let data;
        try {
            data = await res.json();
        } catch {
            if (!res.ok) throw new Error(`Request failed (${res.status})`);
            return null;
        }

        if (!res.ok) {
            const msg = (data && data.error) || `Request failed (${res.status})`;
            throw new Error(msg);
        }
        return data;
    }

    return {
        get:    (path)       => request('GET',    path),
        post:   (path, body) => request('POST',   path, body),
        put:    (path, body) => request('PUT',    path, body),
        patch:  (path, body) => request('PATCH',  path, body),
        delete: (path)       => request('DELETE', path),
    };
})();
