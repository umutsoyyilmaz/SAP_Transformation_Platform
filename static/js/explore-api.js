/**
 * Explore Phase — API Client
 * Typed wrappers around API.get/post/put/patch/delete
 * All URLs match the actual backend at /api/v1/explore/...
 */
const ExploreAPI = (() => {
    'use strict';

    const B = '/explore';

    // ── Utility ───────────────────────────────────────────────────
    function _qs(params) {
        if (!params) return '';
        const parts = [];
        for (const [k, v] of Object.entries(params)) {
            if (v != null && v !== '') parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
        }
        return parts.length ? '&' + parts.join('&') : '';
    }

    /** Extract items array from paginated response {items:[...], total} or return as-is if already an array */
    function _items(promise) {
        return promise.then(r => {
            if (Array.isArray(r)) return r;
            if (r && Array.isArray(r.items)) return r.items;
            return [];
        });
    }

    // ── Process Hierarchy (L1 → L4) ───────────────────────────────
    const levels = {
        listL1:   (pid)       => _items(API.get(`${B}/process-levels?project_id=${pid}&level=1`)),
        getL1:    (pid, id)   => API.get(`${B}/process-levels/${id}`),
        listL2:   (pid)       => _items(API.get(`${B}/process-levels?project_id=${pid}&level=2`)),
        getL2:    (pid, id)   => API.get(`${B}/process-levels/${id}`),
        listL3:   (pid)       => _items(API.get(`${B}/process-levels?project_id=${pid}&level=3`)),
        getL3:    (pid, id)   => API.get(`${B}/process-levels/${id}`),
        listL4:   (pid)       => _items(API.get(`${B}/process-levels?project_id=${pid}&level=4`)),
        getL4:    (pid, id)   => API.get(`${B}/process-levels/${id}`),
        create:         (pid, data) => API.post(`${B}/process-levels`, Object.assign({project_id: pid}, data)),
        bulkCreate:     (pid, levels) => API.post(`${B}/process-levels/bulk`, {project_id: pid, levels}),
        remove:         (id, confirm) => API.delete(`${B}/process-levels/${id}${confirm ? '?confirm=true' : ''}`),
        importTemplate: (pid, data) => API.post(`${B}/process-levels/import-template`, Object.assign({project_id: pid}, data)),
        update:        (id, data) => API.put(`${B}/process-levels/${id}`, data),
        scopeMatrix:   (pid)      => API.get(`${B}/scope-matrix?project_id=${pid}`),
        consolidateFit: (l3Id)    => API.post(`${B}/process-levels/${l3Id}/consolidate-fit`),
        consolidatedView: (l3Id)  => API.get(`${B}/process-levels/${l3Id}/consolidated-view`),
        overrideFitStatus: (l3Id, data) => API.post(`${B}/process-levels/${l3Id}/override-fit-status`, data),
        seedFromCatalog: (l3Id)   => API.post(`${B}/process-levels/${l3Id}/seed-from-catalog`),
        addChild:        (l3Id, data) => API.post(`${B}/process-levels/${l3Id}/children`, data),
        l2Readiness:   (pid)      => API.get(`${B}/process-levels/l2-readiness?project_id=${pid}`),
        areaMilestones: (pid)     => API.get(`${B}/area-milestones?project_id=${pid}`),
        changeHistory: (plId)     => API.get(`${B}/process-levels/${plId}/change-history`),
    };

    // ── Workshops ─────────────────────────────────────────────────
    const workshops = {
        list:     (pid, params) => _items(API.get(`${B}/workshops?project_id=${pid}${_qs(params)}`)),
        get:      (pid, id)     => API.get(`${B}/workshops/${id}`),
        full:     (pid, id)     => API.get(`${B}/workshops/${id}/full`),
        create:   (pid, data)   => API.post(`${B}/workshops`, Object.assign({project_id: pid}, data)),
        update:   (pid, id, d)  => API.put(`${B}/workshops/${id}`, d),
        delete:   (pid, id)     => API.delete(`${B}/workshops/${id}`),
        start:    (pid, id)     => API.post(`${B}/workshops/${id}/start`),
        complete: (pid, id)     => API.post(`${B}/workshops/${id}/complete`),
        transition: (pid, id, d) => {
            const action = d && d.action;
            if (action === 'complete') return API.post(`${B}/workshops/${id}/complete`, d);
            if (action === 'reopen') return API.post(`${B}/workshops/${id}/reopen`, d);
            return API.post(`${B}/workshops/${id}/start`, d);
        },
        capacity: (pid)         => API.get(`${B}/workshops/capacity?project_id=${pid}`),
        stats:    (pid)         => API.get(`${B}/workshops/stats?project_id=${pid}`),
        reopen:   (pid, id, data) => API.post(`${B}/workshops/${id}/reopen`, data || {}),
        createDelta: (pid, id, data)  => API.post(`${B}/workshops/${id}/create-delta`, data || {}),
        steps:    (pid, wsId)   => _items(API.get(`${B}/workshops/${wsId}/steps`)),
    };

    // ── Workshop Sessions ─────────────────────────────────────────
    // Sessions are workshops linked via original_workshop_id.
    // list returns all related workshops (original + deltas).
    const sessions = {
        list:     (pid, wsId)        => API.get(`${B}/workshops/${wsId}/sessions`),
        get:      (pid, wsId, id)    => API.get(`${B}/workshops/${id}`),
        create:   (pid, wsId, data)  => API.post(`${B}/workshops/${wsId}/create-delta`, data || {}),
        update:   (pid, wsId, id, d) => API.put(`${B}/workshops/${id}`, d),
    };

    // ── Fit Decisions ──────────────────────────────────────────────
    // create = bulk upsert via POST /workshops/:wsId/fit-decisions
    // update individual step via PUT /process-steps/:stepId
    const fitDecisions = {
        list:     (pid, wsId)        => API.get(`${B}/workshops/${wsId}/fit-decisions`),
        create:   (pid, wsId, data)  => API.post(`${B}/workshops/${wsId}/fit-decisions`, data),
        update:   (pid, wsId, stepId, d) => API.put(`${B}/process-steps/${stepId}`, d),
    };

    // ── Decisions ─────────────────────────────────────────────────
    const decisions = {
        list:     (pid, wsId)        => API.get(`${B}/workshops/${wsId}/decisions`),
        create:   (pid, wsId, data)  => API.post(`${B}/process-steps/${data.process_step_id}/decisions`, data),
        update:   (pid, wsId, id, d) => API.put(`${B}/decisions/${id}`, d),
        delete:   (pid, wsId, id)    => API.delete(`${B}/decisions/${id}`),
    };

    // ── Requirements ──────────────────────────────────────────────
    const requirements = {
        list:       (pid, params)    => _items(API.get(`${B}/requirements?project_id=${pid}${_qs(params)}`)),
        get:        (pid, id)        => API.get(`${B}/requirements/${id}`),
        create:     (pid, data)      => API.post(`${B}/requirements`, Object.assign({project_id: pid}, data)),
        update:     (pid, id, d)     => API.put(`${B}/requirements/${id}`, Object.assign({project_id: pid}, d || {})),
        delete:     (pid, id)        => Promise.resolve(), // No backend DELETE endpoint — placeholder
        transition: (pid, id, d)     => API.post(`${B}/requirements/${id}/transition`, Object.assign({project_id: pid}, d || {})),
        stats:      (pid)            => API.get(`${B}/requirements/stats?project_id=${pid}`),
        convert:      (pid, id, d)     => API.post(`${B}/requirements/${id}/convert`, Object.assign({project_id: pid}, d || {})),
        batchConvert: (pid, d)         => API.post(`${B}/requirements/batch-convert`, Object.assign({project_id: pid}, d || {})),
        coverageMatrix: (pid, params)  => API.get(`${B}/requirements/coverage-matrix?project_id=${pid}${_qs(params)}`),
    };

    // ── Open Items ────────────────────────────────────────────────
    const openItems = {
        list:       (pid, params)    => _items(API.get(`${B}/open-items?project_id=${pid}${_qs(params)}`)),
        get:        (pid, id)        => API.get(`${B}/open-items/${id}`),
        create:     (pid, data)      => API.post(`${B}/open-items`, Object.assign({project_id: pid}, data)),
        update:     (pid, id, d)     => API.put(`${B}/open-items/${id}`, Object.assign({project_id: pid}, d || {})),
        delete:     (pid, id)        => Promise.resolve(), // No backend DELETE endpoint — placeholder
        transition: (pid, id, d)     => API.post(`${B}/open-items/${id}/transition`, Object.assign({project_id: pid}, d || {})),
        stats:      (pid)            => API.get(`${B}/open-items/stats?project_id=${pid}`),
    };

    // ── Sign-off ──────────────────────────────────────────────────
    const signoff = {
        getL3:    (pid, l3Id)         => API.get(`${B}/process-levels/${l3Id}/consolidated-view`),
        performL3:(pid, l3Id, data)   => API.post(`${B}/process-levels/${l3Id}/signoff`, data),
    };

    // ── Fit Propagation ───────────────────────────────────────────
    const fitPropagation = {
        propagate: (pid)             => API.post(`${B}/fit-propagation/propagate`, {project_id: pid}),
    };

    // ── Agenda Items ──────────────────────────────────────────────
    const agenda = {
        list:     (pid, wsId)        => API.get(`${B}/workshops/${wsId}/agenda-items`),
        create:   (pid, wsId, data)  => API.post(`${B}/workshops/${wsId}/agenda-items`, data),
        update:   (pid, wsId, id, d) => API.put(`${B}/agenda-items/${id}`, d),
        delete:   (pid, wsId, id)    => API.delete(`${B}/agenda-items/${id}`),
    };

    // ── Attendees ────────────────────────────────────────────────
    const attendees = {
        list:     (pid, wsId)        => API.get(`${B}/workshops/${wsId}/attendees`),
        create:   (pid, wsId, data)  => API.post(`${B}/workshops/${wsId}/attendees`, data),
        update:   (pid, wsId, id, d) => API.put(`${B}/attendees/${id}`, d),
        delete:   (pid, wsId, id)    => API.delete(`${B}/attendees/${id}`),
    };

    // ── Workshop Dependencies ─────────────────────────────────────
    const dependencies = {
        list:     (pid, wsId)        => API.get(`${B}/workshops/${wsId}/dependencies`),
        create:   (pid, wsId, data)  => API.post(`${B}/workshops/${wsId}/dependencies`, data),
        delete:   (pid, wsId, id)    => API.put(`${B}/workshop-dependencies/${id}/resolve`),
    };

    // ── Scope Change Requests ─────────────────────────────────────
    const scopeChangeRequests = {
        list:     (pid)              => _items(API.get(`${B}/scope-change-requests?project_id=${pid}`)),
        get:      (pid, id)          => API.get(`${B}/scope-change-requests/${id}`),
        create:   (pid, data)        => API.post(`${B}/scope-change-requests`, Object.assign({project_id: pid}, data)),
        update:   (pid, id, d)       => API.post(`${B}/scope-change-requests/${id}/transition`, d),
    };

    // ── Attachments ───────────────────────────────────────────────
    const attachments = {
        list:     (pid, params)      => _items(API.get(`${B}/attachments?project_id=${pid}${_qs(params)}`)),
        get:      (pid, id)          => API.get(`${B}/attachments/${id}`),
        create:   (pid, data)        => API.post(`${B}/attachments`, Object.assign({project_id: pid}, data)),
        delete:   (pid, id)          => API.delete(`${B}/attachments/${id}`),
    };

    // ── Snapshot / Reports (Phase 2) ──────────────────────────────
    const snapshots = {
        list:    (pid, params) => API.get(`${B}/snapshots?project_id=${pid}${_qs(params)}`),
        capture: (pid, data)  => API.post(`${B}/snapshots/capture`, Object.assign({project_id: pid}, data || {})),
    };
    const reports = {
        steeringCommittee: (pid) => API.get(`${B}/reports/steering-committee?project_id=${pid}`),
    };

    // ── Workshop Documents (Phase 2) ─────────────────────────────
    const documents = {
        list:            (pid, wsId) => API.get(`${B}/workshops/${wsId}/documents`),
        generate:        (pid, wsId, data) => API.post(`${B}/workshops/${wsId}/documents/generate`, data),
        generateMinutes: (pid, wsId, data) => API.post(`${B}/workshops/${wsId}/generate-minutes`, data || {}),
        generateSummary: (pid, wsId, data) => API.post(`${B}/workshops/${wsId}/ai-summary`, data || {}),
    };

    // ── BPMN (Phase 2) ───────────────────────────────────────────
    const bpmn = {
        list:   (pid, levelId) => API.get(`${B}/process-levels/${levelId}/bpmn`),
        create: (pid, levelId, data) => API.post(`${B}/process-levels/${levelId}/bpmn`, data),
    };

    // ── Cross-Module Flags ────────────────────────────────────────
    const crossModuleFlags = {
        list:   (params)           => API.get(`${B}/cross-module-flags${params ? '?' + new URLSearchParams(params) : ''}`),
        create: (stepId, data)     => API.post(`${B}/process-steps/${stepId}/cross-module-flags`, data),
        update: (flagId, data)     => API.put(`${B}/cross-module-flags/${flagId}`, data),
    };

    // ── Process Steps ─────────────────────────────────────────────
    const processSteps = {
        list:           (pid, wsId)    => _items(API.get(`${B}/workshops/${wsId}/steps`)),
        update:         (stepId, data) => API.put(`${B}/process-steps/${stepId}`, data),
        addDecision:    (stepId, data) => API.post(`${B}/process-steps/${stepId}/decisions`, data),
        addOpenItem:    (stepId, data) => API.post(`${B}/process-steps/${stepId}/open-items`, data),
        addRequirement: (stepId, data) => API.post(`${B}/process-steps/${stepId}/requirements`, data),
    };

    return {
        levels, workshops, sessions, fitDecisions, decisions,
        requirements, openItems, signoff, fitPropagation,
        agenda, attendees, dependencies, scopeChangeRequests, attachments,
        snapshots, reports, documents, bpmn,
        crossModuleFlags, processSteps,
    };
})();
