/**
 * SAP Transformation Management Platform
 * API Client Helper — fetch wrapper for all backend calls.
 *
 * Auth: Includes JWT Bearer token from Auth module when available.
 * On 401: redirects to /login for re-authentication.
 */

const API = (() => {
    const BASE = '/api/v1';

    /**
     * Inject current user context into mutating request bodies.
     * Reads from Auth module (JWT user) for identity.
     */
    function _injectUser(body) {
        if (!body || typeof body !== 'object') return body;

        // Use JWT-authenticated user from Auth module
        const user = (typeof Auth !== 'undefined') ? Auth.getUser() : null;
        if (!user) return body;

        const uid   = String(user.id || 'system');
        const uname = user.full_name || user.name || 'System';

        // Only set if NOT already explicitly provided by caller
        if (!body.user_id)       body.user_id       = uid;
        if (!body.user_name)     body.user_name     = uname;
        if (!body.created_by)    body.created_by    = uname;
        if (!body.created_by_id) body.created_by_id = uid;
        if (!body.changed_by)    body.changed_by    = uname;

        return body;
    }

    /**
     * Inject project context into mutating request bodies.
     * If body has no project_id/program_id, reads from App global state.
     */
    function _injectProjectContext(body) {
        if (!body || typeof body !== 'object') return body;
        if (body.project_id || body.program_id) return body;

        const prog = (typeof App !== 'undefined' && App.getActiveProgram)
            ? App.getActiveProgram()
            : null;
        if (prog && prog.id) body.project_id = prog.id;

        return body;
    }

    async function request(method, path, body = null) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };

        // ── JWT Authorization Header ────────────────────────────────
        if (typeof Auth !== 'undefined') {
            const token = Auth.getAccessToken();
            if (token) {
                opts.headers['Authorization'] = `Bearer ${token}`;
            }
        }

        // ── Context Middleware (POST/PUT/PATCH only) ────────────────
        if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            body = _injectProjectContext(body);
            body = _injectUser(body);
        }

        if (body) opts.body = JSON.stringify(body);

        const res = await fetch(`${BASE}${path}`, opts);

        // ── 401 → redirect to login ────────────────────────────────
        if (res.status === 401 && !path.startsWith('/auth/')) {
            if (typeof Auth !== 'undefined') {
                Auth.clearTokens();
            }
            window.location.href = '/login';
            throw new Error('Session expired');
        }

        let data;
        try {
            data = await res.json();
        } catch {
            if (!res.ok) throw new Error(`Request failed (${res.status})`);
            return null;
        }

        if (!res.ok) {
            const err = new Error(
                (data && data.error) || `Request failed (${res.status})`
            );
            err.status  = res.status;
            err.code    = data && data.code;       // e.g. "ERR_VALIDATION_REQUIRED"
            err.details = data && data.details;    // e.g. { blocking_oi_ids: [...] }
            throw err;
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
