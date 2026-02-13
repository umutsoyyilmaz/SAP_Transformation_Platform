/**
 * SAP Transformation Platform — Unified TraceChain Component
 *
 * Full traceability flow diagram for ANY entity type.
 * Calls: GET /api/v1/traceability/<entity_type>/<entity_id>
 *
 * Usage:
 *   TraceChain.show('backlog_item', 42);           // modal
 *   TraceChain.show('explore_requirement', 'uuid'); // modal
 *   TraceChain.renderInTab('backlog_item', 42, containerEl); // inline
 */
const TraceChain = (() => {
    'use strict';

    /* ── helpers ────────────────────────────────────────────────────── */
    const esc = (s) => {
        const d = document.createElement('div');
        d.textContent = s ?? '';
        return d.innerHTML;
    };

    /* ── entity type style map ─────────────────────────────────────── */
    const STYLES = {
        process_l1:           { icon: '🏢', color: '#3B82F6', label: 'Process L1' },
        process_l2:           { icon: '📂', color: '#3B82F6', label: 'Process L2' },
        process_l3:           { icon: '📁', color: '#3B82F6', label: 'Process L3' },
        process_l4:           { icon: '📄', color: '#3B82F6', label: 'Process L4' },
        process_step:         { icon: '🔹', color: '#6366F1', label: 'Process Step' },
        workshop:             { icon: '🏛️', color: '#8B5CF6', label: 'Workshop' },
        scenario:             { icon: '🎯', color: '#3B82F6', label: 'Scenario' },
        requirement:          { icon: '📝', color: '#0070f2', label: 'Requirement' },
        explore_requirement:  { icon: '📝', color: '#0070f2', label: 'Requirement' },
        backlog_item:         { icon: '⚙️', color: '#C08B5C', label: 'WRICEF Item' },
        config_item:          { icon: '🔧', color: '#C08B5C', label: 'Config Item' },
        functional_spec:      { icon: '📑', color: '#6B7280', label: 'Func Spec' },
        technical_spec:       { icon: '📑', color: '#6B7280', label: 'Tech Spec' },
        test_case:            { icon: '🧪', color: '#10B981', label: 'Test Case' },
        defect:               { icon: '🐛', color: '#EF4444', label: 'Defect' },
        open_item:            { icon: '📌', color: '#F97316', label: 'Open Item' },
        decision:             { icon: '⚖️', color: '#8B5CF6', label: 'Decision' },
        interface:            { icon: '🔌', color: '#06B6D4', label: 'Interface' },
    };

    function _style(type) {
        return STYLES[type] || { icon: '📦', color: '#6B7280', label: type };
    }

    /* ── status color class ────────────────────────────────────────── */
    function _statusCls(status) {
        if (!status) return '';
        const s = (status + '').toLowerCase();
        if (['approved', 'pass', 'closed', 'done', 'verified', 'resolved', 'completed', 'active', 'fit'].includes(s))
            return 'tc-status--green';
        if (['in_progress', 'in_backlog', 'retest', 'assigned', 'in_review', 'under_review', 'partial_fit', 'new'].includes(s))
            return 'tc-status--amber';
        if (['rejected', 'fail', 'blocked', 'reopened', 'deferred', 'gap', 'critical', 'high'].includes(s))
            return 'tc-status--red';
        return '';
    }

    /* ── dynamic color for special entities ─────────────────────────── */
    function _nodeColor(node) {
        const type = node.type || '';
        // requirement: color by fit status
        if (type.includes('requirement') && node.fit_status) {
            if (node.fit_status === 'fit') return '#10B981';
            if (node.fit_status === 'gap') return '#EF4444';
            if (node.fit_status === 'partial_fit') return '#F59E0B';
        }
        // test: color by result
        if (type === 'test_case' && node.result) {
            if (node.result === 'pass') return '#10B981';
            if (node.result === 'fail') return '#EF4444';
            return '#6B7280';
        }
        // defect: color by severity
        if (type === 'defect' && node.severity) {
            if (node.severity === 'critical') return '#EF4444';
            if (node.severity === 'high') return '#F59E0B';
            return '#3B82F6';
        }
        return _style(type).color;
    }

    /* ══════════════════════════════════════════════════════════════════
     *  PUBLIC: show(entityType, entityId)  — modal
     * ══════════════════════════════════════════════════════════════════ */
    async function show(entityType, entityId) {
        App.openModal(`
            <div style="min-width:660px;max-width:960px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                    <h2 style="margin:0;font-size:18px">🔗 Traceability Chain</h2>
                    <button class="btn btn-sm" onclick="App.closeModal()" style="color:var(--sap-text-secondary)">✕</button>
                </div>
                <div id="tcModalBody" style="text-align:center;padding:30px;color:var(--sap-text-secondary)">
                    <div class="spinner" style="margin:0 auto 8px"></div>
                    Loading trace data…
                </div>
            </div>
        `);

        try {
            const data = await _fetch(entityType, entityId);
            const el = document.getElementById('tcModalBody');
            if (el) el.innerHTML = _renderFull(data, entityType);
        } catch (err) {
            const el = document.getElementById('tcModalBody');
            if (el) el.innerHTML = `<div style="color:var(--sap-negative);padding:12px">Error: ${esc(err.message || 'Unknown error')}</div>`;
        }
    }

    /* ══════════════════════════════════════════════════════════════════
     *  PUBLIC: renderInTab(entityType, entityId, container)  — inline
     * ══════════════════════════════════════════════════════════════════ */
    async function renderInTab(entityType, entityId, container) {
        if (!container) container = document.getElementById('detailTabContent');
        if (!container) return;
        container.innerHTML = '<div style="text-align:center;padding:40px"><div class="spinner"></div></div>';

        try {
            const data = await _fetch(entityType, entityId);
            container.innerHTML = _renderFull(data, entityType);
        } catch (err) {
            container.innerHTML = `<div class="card" style="margin-top:12px"><p style="color:var(--sap-negative)">Could not load traceability data.</p></div>`;
        }
    }

    /* ══════════════════════════════════════════════════════════════════
     *  PUBLIC: close()
     * ══════════════════════════════════════════════════════════════════ */
    function close() { App.closeModal(); }

    /* ── API call ──────────────────────────────────────────────────── */
    async function _fetch(entityType, entityId) {
        return API.get(`/traceability/${entityType}/${entityId}`);
    }

    /* ══════════════════════════════════════════════════════════════════
     *  RENDER — full component layout
     * ══════════════════════════════════════════════════════════════════ */
    function _renderFull(data, entityType) {
        const isExplore = entityType === 'explore_requirement';
        return `
            <div class="tc-root">
                ${_renderEntity(data, entityType)}
                ${_renderDepthBar(data, isExplore)}
                ${_renderFlowDiagram(data, entityType)}
                ${_renderLateral(data, isExplore)}
                ${_renderGaps(data, isExplore)}
            </div>`;
    }

    /* ── Entity header ────────────────────────────────────────────── */
    function _renderEntity(data, entityType) {
        const e = data.entity || data.requirement || {};
        const st = _style(entityType);
        const code = e.code || '';
        const title = e.title || entityType;
        const status = e.status || '';
        return `
            <div class="tc-entity-header" style="border-left:4px solid ${st.color}">
                <span class="tc-entity-icon">${st.icon}</span>
                <span class="tc-entity-code">${esc(code)}</span>
                <span class="tc-entity-title">${esc(title)}</span>
                ${status ? `<span class="tc-status ${_statusCls(status)}">${esc(status)}</span>` : ''}
                ${e.priority ? `<span class="tc-entity-extra">${esc(e.priority)}</span>` : ''}
                ${e.type ? `<span class="tc-entity-extra">${esc(e.type)}</span>` : ''}
            </div>`;
    }

    /* ── Depth bar ────────────────────────────────────────────────── */
    function _renderDepthBar(data, isExplore) {
        const depth = data.chain_depth || 0;
        const max = isExplore ? 6 : 6;
        const pct = Math.min(100, Math.round((depth / max) * 100));
        const color = pct >= 80 ? '#10B981' : pct >= 50 ? '#F59E0B' : '#EF4444';
        const segments = [];
        for (let i = 1; i <= max; i++) {
            segments.push(`<div class="tc-depth-seg${i <= depth ? ' tc-depth-seg--filled' : ''}" style="${i <= depth ? `background:${color}` : ''}"></div>`);
        }
        return `
            <div class="tc-depth-bar">
                <span class="tc-depth-label">Chain Depth</span>
                <div class="tc-depth-track">${segments.join('')}</div>
                <span class="tc-depth-value" style="color:${color}">${depth}/${max}</span>
            </div>`;
    }

    /* ── Flow diagram ─────────────────────────────────────────────── */
    function _renderFlowDiagram(data, entityType) {
        const isExplore = entityType === 'explore_requirement';
        const upstream = data.upstream || [];
        const downstream = data.downstream || [];
        const entity = data.entity || data.requirement || {};

        // Build node list: upstream → current → downstream
        const nodes = [];

        // Upstream (reversed so flow goes from top-level → detail)
        // upstream is already ordered from closest to farthest, so reverse for display
        const upReversed = [...upstream].reverse();
        upReversed.forEach(u => {
            nodes.push({ ...u, _role: 'upstream' });
        });

        // Current entity node
        nodes.push({
            type: entityType,
            id: entity.id,
            code: entity.code,
            title: entity.title,
            status: entity.status,
            priority: entity.priority,
            _role: 'current',
        });

        // Downstream
        downstream.forEach(d => {
            nodes.push({ ...d, _role: 'downstream' });
        });

        // Explore requirement: also add coverage items as downstream
        if (isExplore) {
            (data.backlog_items || []).forEach(b => nodes.push({ ...b, type: 'backlog_item', _role: 'downstream' }));
            (data.config_items || []).forEach(c => nodes.push({ ...c, type: 'config_item', _role: 'downstream' }));
            (data.test_cases || []).forEach(t => nodes.push({ ...t, type: 'test_case', _role: 'downstream' }));
            (data.defects || []).forEach(d => nodes.push({ ...d, type: 'defect', _role: 'downstream' }));
        }

        if (nodes.length === 0) {
            return '<div class="tc-empty">No trace data available</div>';
        }

        const nodesHtml = nodes.map((n, idx) => {
            const connector = idx > 0 ? _connector() : '';
            return connector + _renderNode(n);
        }).join('');

        return `<div class="tc-flow">${nodesHtml}</div>`;
    }

    function _connector() {
        return `<div class="tc-connector">
            <div class="tc-connector-line"></div>
            <span class="tc-connector-arrow">▼</span>
        </div>`;
    }

    function _renderNode(n) {
        const st = _style(n.type);
        const color = _nodeColor(n);
        const isCurrent = n._role === 'current';
        const statusText = n.status || n.fit_status || n.fit_decision || '';
        const extra = n.scope_status || n.process_area || n.category || n.priority || n.severity || n.result || '';
        const code = n.code || '';
        const title = n.title || n.text || 'Untitled';
        const level = n.level ? `L${n.level}` : '';

        return `
            <div class="tc-node${isCurrent ? ' tc-node--current' : ''}" style="border-color:${color}"
                 title="${esc(st.label)}: ${esc(title)}"
                 ${n.id ? `onclick="TraceChain._navigate('${n.type}', '${n.id}')"` : ''}>
                <div class="tc-node-header" style="background:${color}12">
                    <span class="tc-node-icon">${st.icon}</span>
                    <span class="tc-node-type">${esc(st.label)}${level ? ' ' + level : ''}</span>
                    ${code ? `<span class="tc-node-code">${esc(code)}</span>` : ''}
                </div>
                <div class="tc-node-body">
                    <div class="tc-node-title">${esc(title)}</div>
                    <div class="tc-node-meta">
                        ${statusText ? `<span class="tc-status ${_statusCls(statusText)}">${esc(statusText)}</span>` : ''}
                        ${extra ? `<span class="tc-node-extra">${esc(extra)}</span>` : ''}
                    </div>
                </div>
            </div>`;
    }

    /* ── Lateral links (open items, decisions, interfaces) ─────────── */
    function _renderLateral(data, isExplore) {
        const lateral = data.lateral || {};
        const sections = [];

        if (isExplore) {
            // open items
            const oi = lateral.open_items || data.open_items || [];
            if (oi.length) {
                sections.push(_lateralSection('📌 Open Items', oi.map(o =>
                    `<span class="tc-lat-tag" style="border-color:#F97316">${esc(o.code || '')} ${esc(o.title || '')} <span class="tc-status ${_statusCls(o.status)}">${esc(o.status || '')}</span></span>`
                )));
            }
            // decisions
            const dec = lateral.decisions || [];
            if (dec.length) {
                sections.push(_lateralSection('⚖️ Decisions', dec.map(d =>
                    `<span class="tc-lat-tag" style="border-color:#8B5CF6">${esc(d.code || '')} ${esc(d.text || d.title || '')} <span class="tc-status ${_statusCls(d.status)}">${esc(d.status || '')}</span></span>`
                )));
            }
        } else {
            // standard lateral: interfaces, connectivity tests, etc.
            const ifaces = lateral.interfaces || [];
            if (ifaces.length) {
                sections.push(_lateralSection('🔌 Interfaces', ifaces.map(i =>
                    `<span class="tc-lat-tag" style="border-color:#06B6D4">${esc(i.code || '')} ${esc(i.title || i.name || '')}</span>`
                )));
            }
            const connTests = lateral.connectivity_tests || [];
            if (connTests.length) {
                sections.push(_lateralSection('🧪 Conn. Tests', connTests.map(t =>
                    `<span class="tc-lat-tag" style="border-color:#10B981">${esc(t.name || '')} <span class="tc-status ${_statusCls(t.status)}">${esc(t.status || '')}</span></span>`
                )));
            }
        }

        if (sections.length === 0) return '';
        return `<div class="tc-lateral"><h4 class="tc-section-title">Lateral Links</h4>${sections.join('')}</div>`;
    }

    function _lateralSection(title, items) {
        return `<div class="tc-lat-section">
            <span class="tc-lat-heading">${title} (${items.length})</span>
            <div class="tc-lat-items">${items.join('')}</div>
        </div>`;
    }

    /* ── Gaps / warnings ──────────────────────────────────────────── */
    function _renderGaps(data, isExplore) {
        const gaps = data.gaps || [];
        if (gaps.length === 0) return '';

        const items = gaps.map(g => {
            const level = g.level !== undefined ? ` (L${g.level})` : (g.type ? ` [${g.type}]` : '');
            return `<div class="tc-gap-item">⚠️ ${esc(g.message)}${level}</div>`;
        }).join('');

        return `<div class="tc-gaps">
            <h4 class="tc-section-title" style="color:#EF4444">⚠️ Gaps & Warnings (${gaps.length})</h4>
            ${items}
        </div>`;
    }

    /* ── Navigation helper ─────────────────────────────────────────── */
    function _navigate(entityType, entityId) {
        // Map entity types to SPA views
        const viewMap = {
            scenario: 'scenarios',
            requirement: 'requirements',
            explore_requirement: 'explore-requirements',
            backlog_item: 'backlog',
            config_item: 'backlog',
            test_case: 'test-execution',
            defect: 'defect-management',
            interface: 'integration',
        };
        const view = viewMap[entityType];
        if (view && typeof App !== 'undefined' && App.navigate) {
            App.navigate(view);
        }
    }

    /* ── return public API ─────────────────────────────────────────── */
    return { show, renderInTab, close, _navigate };
})();
