/**
 * Process Hierarchy View — Signavio L1→L2→L3→L4 tree
 * SAP Transformation Management Platform
 *
 * Shows the full 4-level process hierarchy with Fit/Gap colour coding,
 * Activate output badges, and cross-links to Requirements / WRICEF / Tests.
 */
const ProcessHierarchyView = (() => {
    'use strict';

    // ── Helpers ──────────────────────────────────────────────────────────
    const esc = s => {
        const d = document.createElement('div');
        d.textContent = s ?? '';
        return d.innerHTML;
    };

    const FIT_GAP_COLORS = {
        fit:         { bg: '#c8e6c9', fg: '#1b5e20', icon: '🟢', label: 'Fit' },
        partial_fit: { bg: '#fff9c4', fg: '#f57f17', icon: '🟡', label: 'Partial' },
        gap:         { bg: '#ffcdd2', fg: '#b71c1c', icon: '🔴', label: 'Gap' },
        standard:    { bg: '#e3f2fd', fg: '#0d47a1', icon: '🔵', label: 'Standard' },
    };

    const LEVEL_BADGES = {
        L2: { bg: '#1a73e8', label: 'L2 – Process Area' },
        L3: { bg: '#e76500', label: 'L3 – E2E Process' },
        L4: { bg: '#8b5cf6', label: 'L4 – Sub Process' },
    };

    const VALUE_CHAIN_MAP = {
        yonetimsel: { icon: '🏛️', label: 'Yönetimsel' },
        cekirdek:   { icon: '⚙️', label: 'Çekirdek' },
        destek:     { icon: '🔧', label: 'Destek' },
    };

    const ACTIVATE_OUTPUT_LABELS = {
        configuration:  '⚙️ Konfigürasyon',
        wricef:         '🔧 WRICEF',
        std_process:    '📋 Std Process',
        workflow_config:'🔄 Workflow Config',
        custom_logic:   '💻 Custom Logic',
        enhancement:    '🔌 Enhancement',
        report:         '📊 Report',
        form:           '📝 Form',
        interface:      '🔗 Interface',
    };

    const TEST_LEVEL_LABELS = {
        unit: 'Unit', sit: 'SIT', uat: 'UAT',
    };

    let hierarchyData = [];
    let selectedScenarioId = null;
    let expandedNodes = new Set();
    let _pid = null;

    // ── API ──────────────────────────────────────────────────────────────
    async function fetchHierarchy() {
        try {
            hierarchyData = await API.get(`/programs/${_pid}/process-hierarchy`);
        } catch (e) {
            console.error('fetchHierarchy error:', e);
            hierarchyData = [];
        }
    }

    async function fetchStats() {
        try {
            return await API.get(`/programs/${_pid}/process-hierarchy/stats`);
        } catch (e) {
            console.error('fetchStats error:', e);
            return null;
        }
    }

    // ── Main Render ─────────────────────────────────────────────────────
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        _pid = prog ? prog.id : null;

        if (!_pid) {
            main.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">🗺️</div>
                    <div class="empty-state__title">Process Hierarchy</div>
                    <p>Go to <a href="#" onclick="App.navigate('programs');return false">Programs</a> to select one first.</p>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="view-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem">
                <div>
                    <h1 class="view-title">🗺️ Process Hierarchy</h1>
                    <p class="view-subtitle">Signavio L1→L2→L3→L4 Süreç Ağacı</p>
                </div>
                <div style="display:flex;gap:.5rem">
                    <button class="btn btn--secondary" onclick="ProcessHierarchyView.expandAll()">Expand All</button>
                    <button class="btn btn--secondary" onclick="ProcessHierarchyView.collapseAll()">Collapse All</button>
                </div>
            </div>
            <div id="ph-stats" style="margin-bottom:1.5rem"></div>
            <div style="display:flex;gap:1.5rem">
                <div id="ph-scenario-list" style="min-width:280px;max-width:320px"></div>
                <div id="ph-tree-panel" style="flex:1;min-width:0"></div>
            </div>
        `;
        await fetchHierarchy();
        const stats = await fetchStats();
        renderStats(stats);
        renderScenarioList();
        if (hierarchyData.length > 0) {
            selectedScenarioId = hierarchyData[0].id;
            renderTree();
        } else {
            document.getElementById('ph-tree-panel').innerHTML =
                '<div class="empty-state">Henüz süreç tanımlanmamış.</div>';
        }
    }

    // ── Stats Banner ────────────────────────────────────────────────────
    function renderStats(stats) {
        const el = document.getElementById('ph-stats');
        if (!stats) { el.innerHTML = ''; return; }
        const bg = stats.by_fit_gap || {};
        const bl = stats.by_level || {};
        el.innerHTML = `
            <div style="display:flex;gap:1rem;flex-wrap:wrap">
                ${_kpiCard('Total', stats.total_processes, '#1a73e8')}
                ${_kpiCard('L2', bl.L2 || 0, '#1a73e8')}
                ${_kpiCard('L3', bl.L3 || 0, '#e76500')}
                ${_kpiCard('L4', bl.L4 || 0, '#8b5cf6')}
                ${_kpiCard('Fit', bg.fit || 0, '#1b5e20')}
                ${_kpiCard('Partial', bg.partial_fit || 0, '#f57f17')}
                ${_kpiCard('Gap', bg.gap || 0, '#b71c1c')}
            </div>
        `;
    }

    function _kpiCard(label, value, color) {
        return `<div style="background:var(--fiori-shell-bg,#f5f6f7);border-radius:12px;padding:.75rem 1.25rem;
            min-width:90px;text-align:center;border-left:4px solid ${color}">
            <div style="font-size:1.5rem;font-weight:700;color:${color}">${value}</div>
            <div style="font-size:.75rem;color:var(--fiori-text-secondary,#556b82)">${esc(label)}</div>
        </div>`;
    }

    // ── Scenario Sidebar (L1) ───────────────────────────────────────────
    function renderScenarioList() {
        const el = document.getElementById('ph-scenario-list');
        if (hierarchyData.length === 0) {
            el.innerHTML = '<div class="empty-state">No scenarios</div>';
            return;
        }
        el.innerHTML = `
            <div style="background:var(--fiori-shell-bg,#f5f6f7);border-radius:12px;padding:1rem">
                <h3 style="margin:0 0 .75rem;font-size:.875rem;color:var(--fiori-text-secondary)">
                    L1 – Value Chain (Scenarios)
                </h3>
                ${hierarchyData.map(s => {
                    const vc = VALUE_CHAIN_MAP[s.value_chain_category] || { icon: '📁', label: s.value_chain_category || 'Other' };
                    const isActive = s.id === selectedScenarioId;
                    const st = s.stats || {};
                    return `
                        <div class="ph-scenario-card ${isActive ? 'ph-scenario-card--active' : ''}"
                             onclick="ProcessHierarchyView.selectScenario(${s.id})"
                             style="padding:.75rem;margin-bottom:.5rem;border-radius:8px;cursor:pointer;
                                    background:${isActive ? 'var(--fiori-accent,#1a73e8)' : '#fff'};
                                    color:${isActive ? '#fff' : 'inherit'};
                                    border:1px solid ${isActive ? 'transparent' : '#e0e0e0'};
                                    transition:all .2s">
                            <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.25rem">
                                <span>${vc.icon}</span>
                                <strong style="font-size:.875rem">${esc(s.name)}</strong>
                            </div>
                            ${s.signavio_code ? `<div style="font-size:.7rem;opacity:.7">${esc(s.signavio_code)} · ${esc(vc.label)}</div>` : ''}
                            <div style="font-size:.7rem;margin-top:.25rem;opacity:.8">
                                L2:${st.total_l2 || 0} · L3:${st.total_l3 || 0} · L4:${st.total_l4 || 0}
                                ${st.gap_count ? ` · <span style="color:${isActive ? '#ffcdd2' : '#b71c1c'}">Gap:${st.gap_count}</span>` : ''}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    // ── Tree Panel (L2→L3→L4) ───────────────────────────────────────────
    function renderTree() {
        const el = document.getElementById('ph-tree-panel');
        const scenario = hierarchyData.find(s => s.id === selectedScenarioId);
        if (!scenario) {
            el.innerHTML = '<div class="empty-state">Senaryo seçin</div>';
            return;
        }

        const processes = scenario.processes || [];
        if (processes.length === 0) {
            el.innerHTML = `
                <div class="empty-state" style="padding:2rem;text-align:center">
                    <p>Bu senaryoda henüz L2 süreç tanımlanmamış.</p>
                    <p style="font-size:.8rem;color:var(--fiori-text-secondary)">
                        Scope ekranından veya API ile süreç ekleyebilirsiniz.
                    </p>
                </div>`;
            return;
        }

        el.innerHTML = `
            <div style="background:#fff;border-radius:12px;padding:1rem;border:1px solid #e0e0e0">
                ${processes.map(l2 => renderL2Node(l2)).join('')}
            </div>
        `;
    }

    function renderL2Node(l2) {
        const key = `l2-${l2.id}`;
        const expanded = expandedNodes.has(key);
        const children = l2.children || [];
        const confirmBadge = l2.scope_confirmation
            ? `<span style="font-size:.65rem;padding:2px 6px;border-radius:4px;
                background:${l2.scope_confirmation === 'confirmed' ? '#c8e6c9' : l2.scope_confirmation === 'excluded' ? '#ffcdd2' : '#fff9c4'};
                color:${l2.scope_confirmation === 'confirmed' ? '#1b5e20' : l2.scope_confirmation === 'excluded' ? '#b71c1c' : '#f57f17'}">
                ${esc(l2.scope_confirmation)}
              </span>` : '';

        return `
            <div class="ph-node ph-node--l2" style="margin-bottom:.75rem">
                <div onclick="ProcessHierarchyView.toggle('${key}')"
                     style="display:flex;align-items:center;gap:.5rem;padding:.75rem;
                            background:linear-gradient(135deg,#e8f0fe,#f5f6f7);border-radius:8px;
                            cursor:pointer;border:1px solid #d0d5dd;transition:all .2s">
                    <span style="font-size:.8rem;transition:transform .2s;transform:rotate(${expanded ? '90' : '0'}deg)">▶</span>
                    <span style="background:${LEVEL_BADGES.L2.bg};color:#fff;font-size:.6rem;padding:2px 6px;border-radius:4px;font-weight:600">L2</span>
                    <strong style="flex:1;font-size:.9rem">${esc(l2.name)}</strong>
                    ${confirmBadge}
                    ${l2.module ? `<span style="font-size:.7rem;padding:2px 6px;border-radius:4px;background:#e3f2fd;color:#0d47a1">${esc(l2.module)}</span>` : ''}
                    <span style="font-size:.7rem;color:var(--fiori-text-secondary)">${children.length} E2E</span>
                </div>
                ${expanded ? `<div style="margin-left:1.5rem;margin-top:.5rem">
                    ${children.length > 0 ? children.map(l3 => renderL3Node(l3)).join('') : '<div style="padding:.5rem;font-size:.8rem;color:#999">Henüz L3 yok</div>'}
                </div>` : ''}
            </div>
        `;
    }

    function renderL3Node(l3) {
        const key = `l3-${l3.id}`;
        const expanded = expandedNodes.has(key);
        const children = l3.children || [];
        const fg = FIT_GAP_COLORS[l3.fit_gap] || { bg: '#f5f5f5', fg: '#666', icon: '⬜', label: '-' };
        const scopeBadge = l3.scope_decision
            ? `<span style="font-size:.6rem;padding:2px 5px;border-radius:3px;
                background:${l3.scope_decision === 'in_scope' ? '#e8f5e9' : l3.scope_decision === 'out_of_scope' ? '#fce4ec' : '#fff3e0'};
                color:${l3.scope_decision === 'in_scope' ? '#2e7d32' : l3.scope_decision === 'out_of_scope' ? '#c62828' : '#ef6c00'}">
                ${esc(l3.scope_decision.replace('_',' '))}
              </span>` : '';

        return `
            <div class="ph-node ph-node--l3" style="margin-bottom:.5rem">
                <div onclick="ProcessHierarchyView.toggle('${key}')"
                     style="display:flex;align-items:center;gap:.5rem;padding:.6rem .75rem;
                            background:#fff;border-radius:8px;cursor:pointer;
                            border-left:4px solid ${fg.bg};border:1px solid #e8e8e8;
                            border-left:4px solid ${fg.fg};transition:all .2s">
                    <span style="font-size:.7rem;transition:transform .2s;transform:rotate(${expanded ? '90' : '0'}deg)">
                        ${children.length > 0 ? '▶' : ''}
                    </span>
                    <span style="background:${LEVEL_BADGES.L3.bg};color:#fff;font-size:.55rem;padding:2px 5px;border-radius:3px;font-weight:600">L3</span>
                    <span style="font-size:.875rem;flex:1;font-weight:500">${esc(l3.name)}</span>
                    ${scopeBadge}
                    <span title="Fit/Gap" style="font-size:.7rem;padding:2px 6px;border-radius:4px;background:${fg.bg};color:${fg.fg};font-weight:600">
                        ${fg.icon} ${fg.label}
                    </span>
                    ${l3.test_scope ? `<span style="font-size:.6rem;padding:2px 5px;border-radius:3px;background:#ede7f6;color:#4527a0">${esc(l3.test_scope.toUpperCase())}</span>` : ''}
                    ${children.length > 0 ? `<span style="font-size:.65rem;color:var(--fiori-text-secondary)">${children.length} sub</span>` : ''}
                </div>
                ${expanded ? `<div style="margin-left:1.5rem;margin-top:.4rem">
                    ${children.length > 0 ? children.map(l4 => renderL4Node(l4)).join('') : '<div style="padding:.4rem;font-size:.75rem;color:#999">Henüz L4 yok</div>'}
                </div>` : ''}
            </div>
        `;
    }

    function renderL4Node(l4) {
        const fg = FIT_GAP_COLORS[l4.fit_gap] || { bg: '#f5f5f5', fg: '#666', icon: '⬜', label: '-' };
        const outputLabel = ACTIVATE_OUTPUT_LABELS[l4.activate_output] || l4.activate_output || '';
        const testBadges = (l4.test_levels || '').split(',').filter(Boolean).map(t =>
            `<span style="font-size:.55rem;padding:1px 4px;border-radius:3px;background:#e8eaf6;color:#283593;margin-left:2px">${esc((TEST_LEVEL_LABELS[t.trim()] || t.trim()).toUpperCase())}</span>`
        ).join('');

        return `
            <div class="ph-node ph-node--l4" style="margin-bottom:.35rem">
                <div style="display:flex;align-items:center;gap:.5rem;padding:.5rem .75rem;
                            background:#fafafa;border-radius:6px;
                            border-left:3px solid ${fg.fg};border:1px solid #f0f0f0;
                            border-left:3px solid ${fg.fg}">
                    <span style="background:${LEVEL_BADGES.L4.bg};color:#fff;font-size:.5rem;padding:1px 4px;border-radius:3px;font-weight:600">L4</span>
                    <span style="font-size:.8rem;flex:1">${esc(l4.name)}</span>
                    <span title="Fit/Gap" style="font-size:.65rem;padding:2px 5px;border-radius:3px;background:${fg.bg};color:${fg.fg};font-weight:600">
                        ${fg.icon} ${fg.label}
                    </span>
                    ${outputLabel ? `<span title="Activate Output" style="font-size:.6rem;padding:2px 5px;border-radius:3px;background:#f3e5f5;color:#6a1b9a">${outputLabel}</span>` : ''}
                    ${l4.wricef_type ? `<span title="WRICEF Type" style="font-size:.55rem;padding:1px 4px;border-radius:3px;background:#fff3e0;color:#e65100">WRICEF:${esc(l4.wricef_type)}</span>` : ''}
                    ${testBadges}
                    ${l4.code ? `<span style="font-size:.55rem;color:var(--fiori-text-secondary)">${esc(l4.code)}</span>` : ''}
                </div>
            </div>
        `;
    }

    // ── Interactions ─────────────────────────────────────────────────────
    function selectScenario(id) {
        selectedScenarioId = id;
        expandedNodes.clear();
        renderScenarioList();
        renderTree();
    }

    function toggle(key) {
        if (expandedNodes.has(key)) {
            expandedNodes.delete(key);
        } else {
            expandedNodes.add(key);
        }
        renderTree();
    }

    function expandAll() {
        const scenario = hierarchyData.find(s => s.id === selectedScenarioId);
        if (!scenario) return;
        (scenario.processes || []).forEach(l2 => {
            expandedNodes.add(`l2-${l2.id}`);
            (l2.children || []).forEach(l3 => {
                expandedNodes.add(`l3-${l3.id}`);
            });
        });
        renderTree();
    }

    function collapseAll() {
        expandedNodes.clear();
        renderTree();
    }

    // ── Public API ───────────────────────────────────────────────────────
    return { render, selectScenario, toggle, expandAll, collapseAll };
})();
