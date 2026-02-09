/**
 * SAP Transformation Management Platform
 * API Client Helper — fetch wrapper for all backend calls.
 */

const API = (() => {
    const BASE = '/api/v1';

    async function request(method, path, body = null) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
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
