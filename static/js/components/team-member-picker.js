/**
 * TeamMemberPicker — reusable team member select component (ADR-4)
 *
 * Usage:
 *   const members = await TeamMemberPicker.fetchMembers(programId);
 *   const html    = TeamMemberPicker.renderSelect('fieldId', members, currentValue);
 */
const TeamMemberPicker = (() => {
    'use strict';

    const _cache = {};

    /**
     * Fetch active team members for a program. Results are cached per session.
     * @param {string|number} programId
     * @returns {Promise<Array>}
     */
    async function fetchMembers(programId) {
        if (!programId) return [];
        if (_cache[programId]) return _cache[programId];
        try {
            const resp = await fetch(`/api/v1/programs/${programId}/team`);
            if (!resp.ok) return [];
            const data = await resp.json();
            const list = Array.isArray(data) ? data : (data.items || data.team_members || []);
            _cache[programId] = list;
            return list;
        } catch {
            return [];
        }
    }

    /**
     * Render a <select> element with team members.
     * @param {string}       fieldId      — HTML id attribute
     * @param {Array}        members      — result of fetchMembers()
     * @param {string|number} currentValue — id or name to pre-select
     * @param {object}       [opts]       — { placeholder, cssClass }
     * @returns {string} HTML string
     */
    function renderSelect(fieldId, members, currentValue, opts) {
        const placeholder = (opts && opts.placeholder) || '— Unassigned —';
        const cssClass = (opts && opts.cssClass) || '';
        const cv = String(currentValue || '');

        const active = members.filter(m => m.is_active !== false);

        const options = active.map(m => {
            // Match by id or by name (backward compat with old free-text values)
            const sel = (String(m.id) === cv || (m.name || '').toLowerCase() === cv.toLowerCase()) ? ' selected' : '';
            const label = `${m.name || m.email || m.id}${m.role ? ' (' + m.role + ')' : ''}`;
            return `<option value="${m.id}"${sel}>${_esc(label)}</option>`;
        }).join('');

        return `<select id="${fieldId}"${cssClass ? ` class="${cssClass}"` : ''}>
            <option value="">${_esc(placeholder)}</option>
            ${options}
        </select>`;
    }

    /** Clear cached data. */
    function invalidateCache(programId) {
        if (programId) delete _cache[programId];
        else Object.keys(_cache).forEach(k => delete _cache[k]);
    }

    function _esc(s) {
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    return { fetchMembers, renderSelect, invalidateCache };
})();
