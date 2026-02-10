/**
 * Explore Phase — API Client
 * Typed wrappers around API.get/post/put/patch/delete
 * for all /explore endpoints.
 */
const ExploreAPI = (() => {
    'use strict';

    const BASE = '/explore';

    // ── Process Hierarchy (L1 → L4) ───────────────────────────────
    const levels = {
        listL1:   (pid)       => API.get(`/programs/${pid}${BASE}/l1-process-areas`),
        getL1:    (pid, id)   => API.get(`/programs/${pid}${BASE}/l1-process-areas/${id}`),
        listL2:   (pid)       => API.get(`/programs/${pid}${BASE}/l2-process-groups`),
        getL2:    (pid, id)   => API.get(`/programs/${pid}${BASE}/l2-process-groups/${id}`),
        listL3:   (pid)       => API.get(`/programs/${pid}${BASE}/l3-scope-items`),
        getL3:    (pid, id)   => API.get(`/programs/${pid}${BASE}/l3-scope-items/${id}`),
        listL4:   (pid)       => API.get(`/programs/${pid}${BASE}/l4-process-steps`),
        getL4:    (pid, id)   => API.get(`/programs/${pid}${BASE}/l4-process-steps/${id}`),
    };

    // ── Workshops ─────────────────────────────────────────────────
    const workshops = {
        list:     (pid, params) => API.get(`/programs/${pid}${BASE}/workshops${_qs(params)}`),
        get:      (pid, id)     => API.get(`/programs/${pid}${BASE}/workshops/${id}`),
        create:   (pid, data)   => API.post(`/programs/${pid}${BASE}/workshops`, data),
        update:   (pid, id, d)  => API.put(`/programs/${pid}${BASE}/workshops/${id}`, d),
        delete:   (pid, id)     => API.delete(`/programs/${pid}${BASE}/workshops/${id}`),
        transition: (pid, id, d) => API.post(`/programs/${pid}${BASE}/workshops/${id}/transition`, d),
        stats:    (pid)         => API.get(`/programs/${pid}${BASE}/workshops/stats`),
    };

    // ── Workshop Sessions ─────────────────────────────────────────
    const sessions = {
        list:     (pid, wsId)        => API.get(`/programs/${pid}${BASE}/workshops/${wsId}/sessions`),
        get:      (pid, wsId, id)    => API.get(`/programs/${pid}${BASE}/workshops/${wsId}/sessions/${id}`),
        create:   (pid, wsId, data)  => API.post(`/programs/${pid}${BASE}/workshops/${wsId}/sessions`, data),
        update:   (pid, wsId, id, d) => API.put(`/programs/${pid}${BASE}/workshops/${wsId}/sessions/${id}`, d),
    };

    // ── Fit Decisions ─────────────────────────────────────────────
    const fitDecisions = {
        list:     (pid, wsId)        => API.get(`/programs/${pid}${BASE}/workshops/${wsId}/fit-decisions`),
        create:   (pid, wsId, data)  => API.post(`/programs/${pid}${BASE}/workshops/${wsId}/fit-decisions`, data),
        update:   (pid, wsId, id, d) => API.put(`/programs/${pid}${BASE}/workshops/${wsId}/fit-decisions/${id}`, d),
    };

    // ── Decisions ─────────────────────────────────────────────────
    const decisions = {
        list:     (pid, wsId)        => API.get(`/programs/${pid}${BASE}/workshops/${wsId}/decisions`),
        create:   (pid, wsId, data)  => API.post(`/programs/${pid}${BASE}/workshops/${wsId}/decisions`, data),
        update:   (pid, wsId, id, d) => API.put(`/programs/${pid}${BASE}/workshops/${wsId}/decisions/${id}`, d),
        delete:   (pid, wsId, id)    => API.delete(`/programs/${pid}${BASE}/workshops/${wsId}/decisions/${id}`),
    };

    // ── Requirements ──────────────────────────────────────────────
    const requirements = {
        list:       (pid, params)    => API.get(`/programs/${pid}${BASE}/requirements${_qs(params)}`),
        get:        (pid, id)        => API.get(`/programs/${pid}${BASE}/requirements/${id}`),
        create:     (pid, data)      => API.post(`/programs/${pid}${BASE}/requirements`, data),
        update:     (pid, id, d)     => API.put(`/programs/${pid}${BASE}/requirements/${id}`, d),
        delete:     (pid, id)        => API.delete(`/programs/${pid}${BASE}/requirements/${id}`),
        transition: (pid, id, d)     => API.post(`/programs/${pid}${BASE}/requirements/${id}/transition`, d),
        stats:      (pid)            => API.get(`/programs/${pid}${BASE}/requirements/stats`),
    };

    // ── Open Items ────────────────────────────────────────────────
    const openItems = {
        list:       (pid, params)    => API.get(`/programs/${pid}${BASE}/open-items${_qs(params)}`),
        get:        (pid, id)        => API.get(`/programs/${pid}${BASE}/open-items/${id}`),
        create:     (pid, data)      => API.post(`/programs/${pid}${BASE}/open-items`, data),
        update:     (pid, id, d)     => API.put(`/programs/${pid}${BASE}/open-items/${id}`, d),
        delete:     (pid, id)        => API.delete(`/programs/${pid}${BASE}/open-items/${id}`),
        transition: (pid, id, d)     => API.post(`/programs/${pid}${BASE}/open-items/${id}/transition`, d),
        stats:      (pid)            => API.get(`/programs/${pid}${BASE}/open-items/stats`),
    };

    // ── Sign-off ──────────────────────────────────────────────────
    const signoff = {
        getL3:    (pid, l3Id)         => API.get(`/programs/${pid}${BASE}/l3-scope-items/${l3Id}/signoff`),
        performL3:(pid, l3Id, data)   => API.post(`/programs/${pid}${BASE}/l3-scope-items/${l3Id}/signoff`, data),
    };

    // ── Fit Propagation ───────────────────────────────────────────
    const fitPropagation = {
        propagate: (pid)             => API.post(`/programs/${pid}${BASE}/fit-propagation/propagate`),
    };

    // ── Agenda Items ──────────────────────────────────────────────
    const agenda = {
        list:     (pid, wsId)        => API.get(`/programs/${pid}${BASE}/workshops/${wsId}/agenda-items`),
        create:   (pid, wsId, data)  => API.post(`/programs/${pid}${BASE}/workshops/${wsId}/agenda-items`, data),
        update:   (pid, wsId, id, d) => API.put(`/programs/${pid}${BASE}/workshops/${wsId}/agenda-items/${id}`, d),
        delete:   (pid, wsId, id)    => API.delete(`/programs/${pid}${BASE}/workshops/${wsId}/agenda-items/${id}`),
    };

    // ── Attendees ─────────────────────────────────────────────────
    const attendees = {
        list:     (pid, wsId)        => API.get(`/programs/${pid}${BASE}/workshops/${wsId}/attendees`),
        create:   (pid, wsId, data)  => API.post(`/programs/${pid}${BASE}/workshops/${wsId}/attendees`, data),
        update:   (pid, wsId, id, d) => API.put(`/programs/${pid}${BASE}/workshops/${wsId}/attendees/${id}`, d),
        delete:   (pid, wsId, id)    => API.delete(`/programs/${pid}${BASE}/workshops/${wsId}/attendees/${id}`),
    };

    // ── Workshop Dependencies ─────────────────────────────────────
    const dependencies = {
        list:     (pid, wsId)        => API.get(`/programs/${pid}${BASE}/workshops/${wsId}/dependencies`),
        create:   (pid, wsId, data)  => API.post(`/programs/${pid}${BASE}/workshops/${wsId}/dependencies`, data),
        delete:   (pid, wsId, id)    => API.delete(`/programs/${pid}${BASE}/workshops/${wsId}/dependencies/${id}`),
    };

    // ── Scope Change Requests ─────────────────────────────────────
    const scopeChangeRequests = {
        list:     (pid)              => API.get(`/programs/${pid}${BASE}/scope-change-requests`),
        get:      (pid, id)          => API.get(`/programs/${pid}${BASE}/scope-change-requests/${id}`),
        create:   (pid, data)        => API.post(`/programs/${pid}${BASE}/scope-change-requests`, data),
        update:   (pid, id, d)       => API.put(`/programs/${pid}${BASE}/scope-change-requests/${id}`, d),
    };

    // ── Attachments ───────────────────────────────────────────────
    const attachments = {
        list:     (pid, params)      => API.get(`/programs/${pid}${BASE}/attachments${_qs(params)}`),
        get:      (pid, id)          => API.get(`/programs/${pid}${BASE}/attachments/${id}`),
        create:   (pid, data)        => API.post(`/programs/${pid}${BASE}/attachments`, data),
        delete:   (pid, id)          => API.delete(`/programs/${pid}${BASE}/attachments/${id}`),
    };

    // ── Utility ───────────────────────────────────────────────────
    function _qs(params) {
        if (!params) return '';
        const parts = [];
        for (const [k, v] of Object.entries(params)) {
            if (v != null && v !== '') parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
        }
        return parts.length ? '?' + parts.join('&') : '';
    }

// ── Snapshot / Reports ────────────────────────────────────────
        const snapshots = {
            list:    (pid, params) => API.get(`/programs/${pid}/explore/snapshots${_qs(params)}`),
            capture: (pid, data)  => API.post(`/programs/${pid}/explore/snapshots/capture`, data || {}),
        };
        const reports = {
            steeringCommittee: (pid) => API.get(`/programs/${pid}/explore/reports/steering-committee`),
        };
        // ── Workshop Documents ───────────────────────────────────────────
        const documents = {
            list:            (pid, wsId) => API.get(`/programs/${pid}/explore/workshops/${wsId}/documents`),
            generateMinutes: (pid, wsId, data) => API.post(`/programs/${pid}/explore/workshops/${wsId}/generate-minutes`, data || {}),
            generateSummary: (pid, wsId, data) => API.post(`/programs/${pid}/explore/workshops/${wsId}/ai-summary`, data || {}),
        };
        // ── BPMN ─────────────────────────────────────────────────────────
        const bpmn = {
            list:   (pid, levelId) => API.get(`/programs/${pid}/explore/process-levels/${levelId}/bpmn`),
            create: (pid, levelId, data) => API.post(`/programs/${pid}/explore/process-levels/${levelId}/bpmn`, data),
        };

        return {
        levels, workshops, sessions, fitDecisions, decisions,
        requirements, openItems, signoff, fitPropagation,
        agenda, attendees, dependencies, scopeChangeRequests, attachments,
        snapshots, reports, documents, bpmn,
    };
})();
