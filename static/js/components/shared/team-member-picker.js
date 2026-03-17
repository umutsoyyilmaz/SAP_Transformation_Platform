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

    function _resolveProjectId(opts) {
        if (opts && Object.prototype.hasOwnProperty.call(opts, 'projectId')) {
            return opts.projectId || null;
        }
        if (typeof App !== 'undefined' && typeof App.getActiveProject === 'function') {
            return App.getActiveProject()?.id || null;
        }
        return null;
    }

    function _cacheKey(programId, projectId) {
        return `${programId}:${projectId || 'all'}`;
    }

    /**
     * Fetch active team members for a program. Results are cached per session.
     * @param {string|number} programId
     * @param {object} [opts]
     * @returns {Promise<Array>}
     */
    async function fetchMembers(programId, opts) {
        if (!programId) return [];
        const projectId = _resolveProjectId(opts);
        const scopedKey = _cacheKey(programId, projectId);
        if (_cache[scopedKey]) return _cache[scopedKey];
        try {
            const scopedUrl = projectId
                ? `/api/v1/programs/${programId}/team?project_id=${encodeURIComponent(projectId)}`
                : `/api/v1/programs/${programId}/team`;
            const resp = await fetch(scopedUrl);
            if (!resp.ok) return [];
            const data = await resp.json();
            let list = Array.isArray(data) ? data : (data.items || data.team_members || []);

            // Transitional fallback: if no project-scoped team exists yet, use
            // program-level members until Sprint 7 hardens project-only constraints.
            if (projectId && list.length === 0) {
                const fallbackResp = await fetch(`/api/v1/programs/${programId}/team`);
                if (fallbackResp.ok) {
                    const fallbackData = await fallbackResp.json();
                    list = Array.isArray(fallbackData)
                        ? fallbackData
                        : (fallbackData.items || fallbackData.team_members || []);
                }
            }

            _cache[scopedKey] = list;
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

    function selectedMemberName(fieldId) {
        const el = document.getElementById(fieldId);
        if (!el || !el.value) return '';
        const option = (el.selectedOptions && el.selectedOptions[0]) || el.options?.[el.selectedIndex];
        if (!option) return '';
        return String(option.textContent || '')
            .replace(/\s+\([^)]*\)\s*$/, '')
            .trim();
    }

    /** Clear cached data. */
    function invalidateCache(programId) {
        if (programId) {
            Object.keys(_cache)
                .filter((k) => k.startsWith(`${programId}:`))
                .forEach((k) => delete _cache[k]);
            return;
        }
        Object.keys(_cache).forEach(k => delete _cache[k]);
    }

    function _esc(s) {
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    return { fetchMembers, renderSelect, selectedMemberName, invalidateCache };
})();
