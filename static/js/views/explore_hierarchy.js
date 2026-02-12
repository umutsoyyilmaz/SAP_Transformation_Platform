/**
 * Explore Phase — Module A: Process Hierarchy Manager
 * F-001: ProcessHierarchyPage  F-002: ProcessTree  F-003: ProcessNodeRow
 * F-004: FitDistributionBar    F-005: ScopeMatrix  F-006: DetailPanel
 * F-007: KpiDashboard          F-008: L3ConsolidatedCard
 * F-009: L3SignOffDialog        F-010: L4SeedingDialog
 *
 * Route: /explore/hierarchy (via App.navigate)
 */
const ExploreHierarchyView = (() => {
    'use strict';

    const esc = ExpUI.esc;

    // ── State ────────────────────────────────────────────────────────
    let _pid = null;
    let _viewMode = 'tree';          // tree | scope-matrix
    let _expandedNodes = new Set();
    let _selectedNodeId = null;
    let _selectedNodeLevel = null;
    let _searchQuery = '';
    let _detailPanelTab = 'overview';
    let _filters = { fit: null, wave: null, area: null };

    // Data
    let _l1List = [];
    let _l2List = [];
    let _l3List = [];
    let _l4List = [];
    let _tree = [];             // built tree structure

    // ── API ──────────────────────────────────────────────────────────
    async function fetchAll() {
        const [l1, l2, l3, l4] = await Promise.all([
            ExploreAPI.levels.listL1(_pid),
            ExploreAPI.levels.listL2(_pid),
            ExploreAPI.levels.listL3(_pid),
            ExploreAPI.levels.listL4(_pid),
        ]);
        _l1List = l1 || [];
        _l2List = l2 || [];
        _l3List = l3 || [];
        _l4List = l4 || [];
        _tree = buildTree();
    }

    // ── Tree Builder ─────────────────────────────────────────────────
    function buildTree() {
        const l4ByL3 = groupBy(_l4List, 'parent_id');
        const l3ByL2 = groupBy(_l3List, 'parent_id');
        const l2ByL1 = groupBy(_l2List, 'parent_id');

        return _l1List.map(l1 => ({
            ...l1, level: 'L1',
            children: (l2ByL1[l1.id] || []).map(l2 => ({
                ...l2, level: 'L2',
                children: (l3ByL2[l2.id] || []).map(l3 => ({
                    ...l3, level: 'L3',
                    children: (l4ByL3[l3.id] || []).map(l4 => ({
                        ...l4, level: 'L4', children: [],
                    })),
                })),
            })),
        }));
    }

    function groupBy(arr, key) {
        const m = {};
        (arr || []).forEach(item => {
            const k = item[key];
            if (!m[k]) m[k] = [];
            m[k].push(item);
        });
        return m;
    }

    // ── Aggregation Helpers ──────────────────────────────────────────
    function aggregateFit(node) {
        if (node.level === 'L4') {
            return { fit: node.fit_status === 'fit' ? 1 : 0,
                     gap: node.fit_status === 'gap' ? 1 : 0,
                     partial_fit: node.fit_status === 'partial_fit' ? 1 : 0,
                     pending: (!node.fit_status || node.fit_status === 'pending') ? 1 : 0 };
        }
        const agg = { fit: 0, gap: 0, partial_fit: 0, pending: 0 };
        (node.children || []).forEach(c => {
            const ca = aggregateFit(c);
            agg.fit += ca.fit;
            agg.gap += ca.gap;
            agg.partial_fit += ca.partial_fit;
            agg.pending += ca.pending;
        });
        return agg;
    }

    function workshopIndicator(node) {
        if (node.level !== 'L3') return '';
        const ws = node.workshops_count || node.workshop_count || 0;
        if (ws > 0) return `<span style="font-size:11px;color:var(--sap-text-secondary)" title="${ws} workshop(s)">📋${ws}</span>`;
        return '';
    }

    // ── Filter & Search ──────────────────────────────────────────────
    function matchesSearch(node) {
        if (!_searchQuery) return true;
        const q = _searchQuery.toLowerCase();
        if ((node.name || '').toLowerCase().includes(q)) return true;
        if ((node.code || '').toLowerCase().includes(q)) return true;
        if ((node.sap_code || '').toLowerCase().includes(q)) return true;
        return (node.children || []).some(c => matchesSearch(c));
    }

    function matchesFilter(node) {
        // Apply filter to leaf level, but show parent if any child matches
        if (node.children && node.children.length) {
            return node.children.some(c => matchesFilter(c));
        }
        if (_filters.fit && node.fit_status !== _filters.fit) return false;
        if (_filters.wave && node.wave !== _filters.wave) return false;
        if (_filters.area && node.area !== _filters.area && node.area_code !== _filters.area) return false;
        return true;
    }

    // ── KPI Dashboard (F-007) ────────────────────────────────────────
    function renderKpiDashboard() {
        const total = _l4List.length || 1;
        const fitC  = _l4List.filter(l => l.fit_status === 'fit').length;
        const gapC  = _l4List.filter(l => l.fit_status === 'gap').length;
        const partC = _l4List.filter(l => l.fit_status === 'partial_fit').length;
        const pendC = total - fitC - gapC - partC;
        return `<div class="exp-kpi-strip exp-kpi-strip--compact">
            ${ExpUI.kpiBlock({ value: _l1List.length, label: 'L1 Areas', accent: 'var(--exp-l1, #8b5cf6)' })}
            ${ExpUI.kpiBlock({ value: _l2List.length, label: 'L2 Groups', accent: 'var(--exp-l2, #3b82f6)' })}
            ${ExpUI.kpiBlock({ value: _l3List.length, label: 'L3 Scope Items', accent: 'var(--exp-l3, #10b981)' })}
            ${ExpUI.kpiBlock({ value: _l4List.length, label: 'L4 Steps', accent: 'var(--exp-l4, #f59e0b)' })}
        </div>
        ${ExpUI.metricBar({
            label: 'Fit Distribution',
            total: total || 1,
            segments: [
                { value: fitC, label: 'Fit', color: 'var(--exp-fit)' },
                { value: gapC, label: 'Gap', color: 'var(--exp-gap)' },
                { value: partC, label: 'Partial', color: 'var(--exp-partial)' },
                { value: pendC, label: 'Pending', color: 'var(--exp-pending)' },
            ],
        })}`;
    }

    // ── Fit Distribution Bar (F-004) ─────────────────────────────────
    function renderFitDistBar(counts) {
        return ExpUI.fitBarMini(counts, { height: 8, width: 120 });
    }

    // ── Process Node Row (F-003) ─────────────────────────────────────
    function renderNodeRow(node, depth) {
        const hasChildren = node.children && node.children.length > 0;
        const isExpanded  = _expandedNodes.has(node.id);
        const isSelected  = _selectedNodeId === node.id;
        const indent = depth * parseInt(getComputedStyle(document.documentElement).getPropertyValue('--exp-tree-indent') || '24');
        const fitAgg = aggregateFit(node);

        const chevronCls = hasChildren
            ? `exp-tree-node__chevron${isExpanded ? ' exp-tree-node__chevron--open' : ''}`
            : 'exp-tree-node__chevron exp-tree-node__chevron--leaf';

        const highlightMatch = _searchQuery && (node.name || '').toLowerCase().includes(_searchQuery.toLowerCase());
        const nameHtml = highlightMatch
            ? (node.name || '').replace(new RegExp(`(${_searchQuery.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')})`, 'gi'), '<mark>$1</mark>')
            : esc(node.name || '');

        return `<div class="exp-tree-node${isSelected ? ' exp-tree-node--active' : ''}"
                     style="padding-left:${indent + 12}px"
                     data-node-id="${node.id}" data-level="${node.level}">
            <span class="${chevronCls}" onclick="ExploreHierarchyView.toggleNode('${node.id}',event)">▶</span>
            ${ExpUI.levelBadge(node.level)}
            <span class="exp-tree-node__code">${esc(node.code || node.sap_code || '')}</span>
            <span class="exp-tree-node__name" onclick="ExploreHierarchyView.selectNode('${node.id}','${node.level}')">${nameHtml}</span>
            <span class="exp-tree-node__meta">
                ${ExpUI.fitBadge(node.effective_fit_status || node.fit_status || 'pending', { compact: true })}
                ${renderFitDistBar(fitAgg)}
                ${workshopIndicator(node)}
            </span>
            <span class="exp-tree-node__actions" onclick="event.stopPropagation()">
                <button class="btn-icon" title="Details" onclick="ExploreHierarchyView.selectNode('${node.id}','${node.level}')">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                        <path d="M8 3c-3.2 0-5.8 2-6.7 5 0.9 3 3.5 5 6.7 5s5.8-2 6.7-5C13.8 5 11.2 3 8 3z" stroke="currentColor" stroke-width="1.4"/>
                        <circle cx="8" cy="8" r="2.2" stroke="currentColor" stroke-width="1.4"/>
                    </svg>
                </button>
                ${node.level === 'L3' ? `
                <button class="btn-icon" title="Scope Change" onclick="ExploreHierarchyView.requestScopeChange('${node.id}')">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8h10M8 3v10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
                    </svg>
                </button>
                <button class="btn-icon" title="Sign Off" onclick="ExploreHierarchyView.openSignOffDialog('${node.id}')">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8l3 3 7-7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
                ` : ''}
            </span>
        </div>`;
    }

    // ── Process Tree (F-002) — recursive ─────────────────────────────
    function renderTree(nodes, depth = 0) {
        let html = '';
        for (const node of nodes) {
            if (!matchesSearch(node) || !matchesFilter(node)) continue;
            html += renderNodeRow(node, depth);
            if (_expandedNodes.has(node.id) && node.children && node.children.length) {
                html += renderTree(node.children, depth + 1);
            }
        }
        return html;
    }

    // ── Scope Matrix (F-005) — L3 flat table ─────────────────────────
    function renderScopeMatrix() {
        const rows = _l3List.filter(l3 => matchesSearch(l3) && matchesFilter(l3));
        if (!rows.length) {
            return `<div class="exp-empty"><div class="exp-empty__icon">📋</div><div class="exp-empty__title">No scope items found</div></div>`;
        }
        const header = `<thead><tr>
            <th onclick="ExploreHierarchyView.sortMatrix('code')">Code <span class="sort-icon">⇅</span></th>
            <th onclick="ExploreHierarchyView.sortMatrix('name')">Name</th>
            <th>Area</th>
            <th>Wave</th>
            <th>Fit Status</th>
            <th>Workshop Status</th>
            <th>REQ</th>
            <th>OI</th>
            <th>Actions</th>
        </tr></thead>`;

        const body = rows.map(l3 => {
            const fitAgg = aggregateFit({ level: 'L3', children: (_l4List || []).filter(l4 => l4.l3_scope_item_id === l3.id).map(l4 => ({ ...l4, level: 'L4', children: [] })) });
            return `<tr class="exp-expandable-row" onclick="ExploreHierarchyView.selectNode('${l3.id}','L3')">
                <td><code style="font-family:var(--exp-font-mono);font-size:12px">${esc(l3.code || l3.sap_code || '')}</code></td>
                <td class="exp-truncate" style="max-width:250px">${esc(l3.name || '')}</td>
                <td>${ExpUI.areaPill(l3.area || l3.area_code || '')}</td>
                <td>${ExpUI.wavePill(l3.wave)}</td>
                <td>${ExpUI.fitBadge(l3.effective_fit_status || l3.fit_status || 'pending')} ${ExpUI.fitBarMini(fitAgg, { height: 4, width: 60 })}</td>
                <td>${ExpUI.workshopStatusPill(l3.workshop_status || 'draft')}</td>
                <td>${ExpUI.countChip(l3.requirement_count || 0, { variant: 'requirement' })}</td>
                <td>${ExpUI.countChip(l3.open_item_count || 0, { variant: 'open_item' })}</td>
                <td>
                    ${ExpUI.actionButton({ label: 'Scope Change', variant: 'ghost', size: 'sm', onclick: `ExploreHierarchyView.requestScopeChange('${l3.id}')` })}
                </td>
            </tr>`;
        }).join('');

        return `<div class="exp-card"><div class="exp-card__body" style="overflow-x:auto">
            <table class="exp-table">${header}<tbody>${body}</tbody></table>
        </div></div>`;
    }

    // ── Detail Panel (F-006) ─────────────────────────────────────────
    function renderDetailPanel() {
        if (!_selectedNodeId) return renderDetailPanelEmpty();

        const node = findNode(_selectedNodeId);
        if (!node) return renderDetailPanelEmpty();

        const tabs = ['overview', 'fit', 'requirements', 'workshop'];
        const tabsHtml = tabs.map(t =>
            `<button class="exp-tab${_detailPanelTab === t ? ' exp-tab--active' : ''}"
                     onclick="ExploreHierarchyView.setDetailTab('${t}')">${t.charAt(0).toUpperCase() + t.slice(1)}</button>`
        ).join('');

        let content = '';
        switch (_detailPanelTab) {
            case 'overview': content = renderDetailOverview(node); break;
            case 'fit':      content = renderDetailFit(node); break;
            case 'requirements': content = renderDetailRequirements(node); break;
            case 'workshop': content = renderDetailWorkshop(node); break;
        }

        return `<div class="exp-layout-split__panel" id="expDetailPanel">
            <div style="padding:var(--exp-space-md) var(--exp-space-lg);border-bottom:1px solid #e2e8f0;display:flex;align-items:center;justify-content:space-between">
                <div>
                    ${ExpUI.levelBadge(node.level)}
                    <strong style="margin-left:8px">${esc(node.code || node.sap_code || '')}</strong>
                </div>
                <button onclick="ExploreHierarchyView.closePanel()" style="background:none;border:none;cursor:pointer;font-size:18px;color:var(--sap-text-secondary)">✕</button>
            </div>
            <div class="exp-tabs" style="padding:0 var(--exp-space-md)">${tabsHtml}</div>
            <div>${content}</div>
        </div>`;
    }

    function renderDetailPanelEmpty() {
        return `<div class="exp-layout-split__panel exp-layout-split__panel--collapsed" id="expDetailPanel"></div>`;
    }

    function renderDetailOverview(node) {
        const fitAgg = aggregateFit(node);
        const total = fitAgg.fit + fitAgg.gap + fitAgg.partial_fit + fitAgg.pending;
        return `<div class="exp-detail-section">
            <div class="exp-detail-section__title">General</div>
            <div class="exp-detail-row"><span class="exp-detail-row__label">Name</span><span class="exp-detail-row__value">${esc(node.name || '')}</span></div>
            <div class="exp-detail-row"><span class="exp-detail-row__label">Level</span><span class="exp-detail-row__value">${ExpUI.levelBadge(node.level)}</span></div>
            <div class="exp-detail-row"><span class="exp-detail-row__label">Code</span><span class="exp-detail-row__value"><code>${esc(node.code || node.sap_code || '')}</code></span></div>
            ${node.area || node.area_code ? `<div class="exp-detail-row"><span class="exp-detail-row__label">Area</span><span class="exp-detail-row__value">${ExpUI.areaPill(node.area || node.area_code)}</span></div>` : ''}
            ${node.wave ? `<div class="exp-detail-row"><span class="exp-detail-row__label">Wave</span><span class="exp-detail-row__value">${ExpUI.wavePill(node.wave)}</span></div>` : ''}
            ${node.description ? `<div class="exp-detail-row"><span class="exp-detail-row__label">Description</span><span class="exp-detail-row__value" style="text-align:left">${esc(node.description)}</span></div>` : ''}
        </div>
        <div class="exp-detail-section">
            <div class="exp-detail-section__title">Fit Analysis (${total} items)</div>
            ${ExpUI.fitBarMini(fitAgg, { height: 10 })}
            <div style="display:flex;gap:12px;margin-top:8px;font-size:12px">
                <span style="color:var(--exp-fit)">● Fit ${fitAgg.fit}</span>
                <span style="color:var(--exp-partial)">◐ Partial ${fitAgg.partial_fit}</span>
                <span style="color:var(--exp-gap)">● Gap ${fitAgg.gap}</span>
                <span style="color:var(--exp-pending)">○ Pending ${fitAgg.pending}</span>
            </div>
        </div>
        ${node.level === 'L3' ? renderL3ConsolidatedCard(node) : ''}`;
    }

    function renderDetailFit(node) {
        const children = node.children || [];
        if (!children.length) return `<div class="exp-detail-section"><p style="color:var(--sap-text-secondary)">No child items to show fit analysis.</p></div>`;
        return `<div class="exp-detail-section">
            <div class="exp-detail-section__title">Child Fit Breakdown</div>
            ${children.map(c => `<div class="exp-detail-row" style="padding:4px 0">
                <span class="exp-detail-row__label" style="font-family:var(--exp-font-mono);font-size:11px">${esc(c.code || c.sap_code || '')}</span>
                <span style="flex:1;margin:0 8px">${esc(c.name || '')}</span>
                ${ExpUI.fitBadge(c.effective_fit_status || c.fit_status || 'pending', { compact: true })}
            </div>`).join('')}
        </div>`;
    }

    function renderDetailRequirements(node) {
        return `<div class="exp-detail-section">
            <div class="exp-detail-section__title">Related Requirements</div>
            <p style="color:var(--sap-text-secondary);font-size:13px">
                ${ExpUI.countChip(node.requirement_count || 0, { variant: 'requirement', label: 'REQ' })}
                ${ExpUI.countChip(node.open_item_count || 0, { variant: 'open_item', label: 'OI' })}
            </p>
            <div style="margin-top:8px">
                ${ExpUI.actionButton({ label: 'View Requirements', variant: 'ghost', size: 'sm', onclick: `App.navigate('explore-requirements')` })}
            </div>
        </div>`;
    }

    function renderDetailWorkshop(node) {
        const count = node.workshops_count || node.workshop_count || 0;
        return `<div class="exp-detail-section">
            <div class="exp-detail-section__title">Workshops</div>
            <p style="font-size:13px;color:var(--sap-text-secondary)">
                ${count ? `${count} workshop(s) linked` : 'No workshops linked to this item'}
            </p>
            <div style="margin-top:8px">
                ${ExpUI.actionButton({ label: 'View Workshops', variant: 'ghost', size: 'sm', onclick: `App.navigate('explore-workshops')` })}
            </div>
        </div>`;
    }

    // ── L3 Consolidated Card (F-008) ─────────────────────────────────
    function renderL3ConsolidatedCard(node) {
        const signoff = node.signoff_status || 'not_started';
        const signoffBadge = signoff === 'signed_off'
            ? ExpUI.pill({ label: '✓ Signed Off', variant: 'success' })
            : signoff === 'override'
            ? ExpUI.pill({ label: '⚠ Override', variant: 'warning' })
            : ExpUI.pill({ label: 'Pending Sign-Off', variant: 'draft' });

        const blockers = (node.blockers || []);
        const blockerHtml = blockers.length
            ? `<div style="margin-top:8px"><strong style="font-size:12px;color:var(--exp-gap)">Blockers (${blockers.length}):</strong>
               <ul style="margin:4px 0 0 16px;font-size:12px">${blockers.map(b => `<li>${esc(b)}</li>`).join('')}</ul></div>`
            : '';

        return `<div class="exp-detail-section" style="border:1px solid #e2e8f0;border-radius:var(--exp-radius-md);margin:8px;padding:12px;background:#fafbfc">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
                <div class="exp-detail-section__title" style="margin-bottom:0">L3 Consolidated Status</div>
                ${signoffBadge}
            </div>
            <div class="exp-detail-row">
                <span class="exp-detail-row__label">Effective Fit</span>
                <span class="exp-detail-row__value">${ExpUI.fitBadge(node.effective_fit_status || 'pending')}</span>
            </div>
            ${blockerHtml}
            <div style="display:flex;gap:8px;margin-top:12px">
                ${signoff !== 'signed_off' ? ExpUI.actionButton({ label: 'Sign Off', variant: 'success', size: 'sm', onclick: `ExploreHierarchyView.openSignOffDialog('${node.id}')` }) : ''}
                ${signoff !== 'signed_off' ? ExpUI.actionButton({ label: 'Override', variant: 'warning', size: 'sm', onclick: `ExploreHierarchyView.openSignOffDialog('${node.id}',true)` }) : ''}
            </div>
        </div>`;
    }

    // ── L3 Sign-Off Dialog (F-009) ───────────────────────────────────
    function openSignOffDialog(l3Id, isOverride = false) {
        const node = findNodeAcross(l3Id, 'L3');
        if (!node) return;
        const fitAgg = aggregateFit(node);
        const title = isOverride ? 'Override L3 Decision' : 'Sign Off L3 Scope Item';

        const html = `<div class="modal-content" style="max-width:500px;padding:24px">
            <h2 style="margin-bottom:16px">${title}</h2>
            <div style="margin-bottom:12px">
                ${ExpUI.levelBadge('L3')} <strong>${esc(node.code || '')} — ${esc(node.name || '')}</strong>
            </div>
            <div style="margin-bottom:12px">
                <div style="font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-bottom:4px">L4 Breakdown</div>
                ${ExpUI.fitBarMini(fitAgg, { height: 8 })}
                <div style="display:flex;gap:8px;margin-top:4px;font-size:11px">
                    <span>Fit: ${fitAgg.fit}</span><span>Gap: ${fitAgg.gap}</span>
                    <span>Partial: ${fitAgg.partial_fit}</span><span>Pending: ${fitAgg.pending}</span>
                </div>
            </div>
            ${isOverride ? `<div style="margin-bottom:12px">
                <label style="font-size:12px;font-weight:600;display:block;margin-bottom:4px">Override Status</label>
                <select id="signoffOverrideStatus" style="width:100%;padding:8px;border:1px solid var(--sap-border);border-radius:var(--exp-radius-md)">
                    <option value="fit">Fit</option>
                    <option value="partial_fit">Partial Fit</option>
                    <option value="gap">Gap</option>
                </select>
            </div>` : ''}
            <div style="margin-bottom:12px">
                <label style="font-size:12px;font-weight:600;display:block;margin-bottom:4px">Comment</label>
                <textarea id="signoffComment" rows="3" style="width:100%;padding:8px;border:1px solid var(--sap-border);border-radius:var(--exp-radius-md);resize:vertical" placeholder="Add comment..."></textarea>
            </div>
            <div style="display:flex;gap:8px;justify-content:flex-end">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: isOverride ? 'Override' : 'Sign Off', variant: isOverride ? 'warning' : 'success', onclick: `ExploreHierarchyView.submitSignOff('${l3Id}',${isOverride})` })}
            </div>
        </div>`;
        App.openModal(html);
    }

    async function submitSignOff(l3Id, isOverride) {
        try {
            const comment = document.getElementById('signoffComment')?.value || '';
            const data = { comment };
            if (isOverride) {
                data.override_status = document.getElementById('signoffOverrideStatus')?.value;
            }
            await ExploreAPI.signoff.performL3(_pid, l3Id, data);
            App.closeModal();
            App.toast('Sign-off submitted successfully', 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Sign-off failed', 'error');
        }
    }

    // ── L4 Seeding Dialog (F-010) ────────────────────────────────────
    function openSeedingDialog() {
        const html = `<div class="modal-content" style="max-width:600px;padding:24px">
            <h2 style="margin-bottom:16px">Import L4 Process Steps</h2>
            <div class="exp-tabs" style="margin-bottom:16px">
                <button class="exp-tab exp-tab--active" onclick="ExploreHierarchyView._setSeedMode('catalog',this)">📚 From Catalog</button>
                <button class="exp-tab" onclick="ExploreHierarchyView._setSeedMode('bpmn',this)">🔄 From BPMN</button>
                <button class="exp-tab" onclick="ExploreHierarchyView._setSeedMode('manual',this)">✍️ Manual</button>
            </div>
            <div id="seedDialogContent">
                ${renderSeedCatalogMode()}
            </div>
            <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;padding-top:12px;border-top:1px solid #e2e8f0">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Import Selected', variant: 'primary', onclick: 'ExploreHierarchyView.submitSeedImport()', id: 'seedImportBtn' })}
            </div>
        </div>`;
        App.openModal(html);
    }

    function renderSeedCatalogMode() {
        return `<div style="max-height:300px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:var(--exp-radius-md);padding:8px">
            <div style="margin-bottom:8px">
                <input type="text" placeholder="Search catalog..." class="exp-search__input" style="padding-left:12px" oninput="ExploreHierarchyView._filterCatalog(this.value)">
            </div>
            <div id="seedCatalogList" style="font-size:13px">
                <p style="color:var(--sap-text-secondary);padding:12px;text-align:center">Loading catalog…</p>
            </div>
        </div>`;
    }

    function _setSeedMode(mode, btn) {
        document.querySelectorAll('#seedDialogContent').forEach(el => {
            if (mode === 'catalog') el.innerHTML = renderSeedCatalogMode();
            else if (mode === 'bpmn') el.innerHTML = renderSeedBpmnMode();
            else el.innerHTML = renderSeedManualMode();
        });
        // Update active tab
        btn.closest('.exp-tabs').querySelectorAll('.exp-tab').forEach(t => t.classList.remove('exp-tab--active'));
        btn.classList.add('exp-tab--active');
    }

    function renderSeedBpmnMode() {
        return `<div style="padding:16px;text-align:center;border:2px dashed #e2e8f0;border-radius:var(--exp-radius-md)">
            <div style="font-size:32px;margin-bottom:8px">📄</div>
            <p style="font-weight:600">Drop BPMN File Here</p>
            <p style="font-size:12px;color:var(--sap-text-secondary)">Or connect to Signavio to import process definitions</p>
            <div style="margin-top:12px">
                ${ExpUI.actionButton({ label: 'Browse File', variant: 'secondary', size: 'sm' })}
                ${ExpUI.actionButton({ label: 'Connect Signavio', variant: 'ghost', size: 'sm' })}
            </div>
        </div>`;
    }

    function renderSeedManualMode() {
        return `<div class="exp-inline-form">
            <div class="exp-inline-form__row">
                <div class="exp-inline-form__field"><label>L3 Scope Item</label>
                    <select id="seedManualL3"><option value="">Select scope item…</option>${_l3List.map(l3 => `<option value="${l3.id}">${esc(l3.code || '')} — ${esc(l3.name || '')}</option>`).join('')}</select>
                </div>
            </div>
            <div class="exp-inline-form__row">
                <div class="exp-inline-form__field"><label>Step Name</label><input id="seedManualName" type="text" placeholder="Process step name"></div>
                <div class="exp-inline-form__field" style="max-width:120px"><label>Code</label><input id="seedManualCode" type="text" placeholder="Auto"></div>
            </div>
            <div class="exp-inline-form__row">
                <div class="exp-inline-form__field"><label>Description</label><textarea id="seedManualDesc" rows="2" placeholder="Optional description"></textarea></div>
            </div>
        </div>`;
    }

    async function submitSeedImport() {
        App.closeModal();
        App.toast('Import started — this is a placeholder', 'info');
    }

    function _filterCatalog() { /* placeholder for catalog search */ }

    // ── Node Lookup ──────────────────────────────────────────────────
    function findNode(id, nodes) {
        nodes = nodes || _tree;
        for (const n of nodes) {
            if (n.id === id) return n;
            if (n.children) {
                const found = findNode(id, n.children);
                if (found) return found;
            }
        }
        return null;
    }

    function findNodeAcross(id, level) {
        if (level === 'L1') return _l1List.find(x => x.id === id);
        if (level === 'L2') return _l2List.find(x => x.id === id);
        if (level === 'L4') return _l4List.find(x => x.id === id);
        // L3: return from tree for children access
        const flat = findNode(id);
        if (flat) return flat;
        return _l3List.find(x => x.id === id);
    }

    // ── Scope Change Request (F-005 gap) ─────────────────────────────
    function requestScopeChange(l3Id) {
        const node = findNodeAcross(l3Id, 'L3');
        const html = `<div class="modal-content" style="max-width:480px;padding:24px">
            <h2 style="margin-bottom:16px">Request Scope Change</h2>
            <p style="margin-bottom:12px">Scope item: <strong>${esc(node?.code || '')} — ${esc(node?.name || '')}</strong></p>
            <div class="exp-inline-form">
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Change Type</label>
                        <select id="scrType"><option value="add">Add to Scope</option><option value="remove">Remove from Scope</option><option value="modify">Modify</option></select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Justification</label><textarea id="scrJustification" rows="3" placeholder="Describe the reason…"></textarea></div>
                </div>
            </div>
            <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Submit Request', variant: 'primary', onclick: `ExploreHierarchyView.submitScopeChange('${l3Id}')` })}
            </div>
        </div>`;
        App.openModal(html);
    }

    async function submitScopeChange(l3Id) {
        try {
            await ExploreAPI.scopeChangeRequests.create(_pid, {
                l3_scope_item_id: l3Id,
                change_type: document.getElementById('scrType')?.value,
                justification: document.getElementById('scrJustification')?.value,
            });
            App.closeModal();
            App.toast('Scope change request submitted', 'success');
        } catch (err) {
            App.toast(err.message || 'Failed to submit', 'error');
        }
    }

    // ── View Mode Switch ─────────────────────────────────────────────
    function renderViewToggle() {
        return `<div class="exp-toolbar__group">
            ${ExpUI.actionButton({ label: '🌲 Tree', variant: _viewMode === 'tree' ? 'primary' : 'secondary', size: 'sm', onclick: `ExploreHierarchyView.setViewMode('tree')` })}
            ${ExpUI.actionButton({ label: '📊 Matrix', variant: _viewMode === 'scope-matrix' ? 'primary' : 'secondary', size: 'sm', onclick: `ExploreHierarchyView.setViewMode('scope-matrix')` })}
        </div>`;
    }

    // ── Filter Bar ───────────────────────────────────────────────────
    function renderFilterBar() {
        const areas = [...new Set(_l3List.map(l => l.area || l.area_code).filter(Boolean))].sort();
        const waves = [...new Set(_l3List.map(l => l.wave).filter(Boolean))].sort();

        return ExpUI.filterBar({
            id: 'hierarchyFB',
            searchPlaceholder: 'Search processes…',
            searchValue: _searchQuery,
            onSearch: "ExploreHierarchyView.setSearch(this.value)",
            onChange: "ExploreHierarchyView.onFilterBarChange",
            filters: [
                {
                    id: 'fit', label: 'Fit Status', icon: '◐', type: 'single',
                    color: 'var(--exp-fit)',
                    options: [
                        {value: 'fit', label: 'Fit'},
                        {value: 'gap', label: 'Gap'},
                        {value: 'partial_fit', label: 'Partial Fit'},
                        {value: 'pending', label: 'Pending'},
                    ],
                    selected: _filters.fit || '',
                },
                {
                    id: 'area', label: 'Area / Module', icon: '📁', type: 'multi',
                    color: 'var(--exp-l2)',
                    options: areas.map(a => ({value: a, label: a})),
                    selected: _filters.area ? [_filters.area] : [],
                },
                {
                    id: 'wave', label: 'Wave', icon: '🌊', type: 'single',
                    color: 'var(--exp-l4)',
                    options: waves.map(w => ({value: String(w), label: `Wave ${w}`})),
                    selected: _filters.wave ? String(_filters.wave) : '',
                },
            ],
            actionsHtml: `
                <div style="display:flex;gap:8px;align-items:center">
                    ${renderViewToggle()}
                    ${ExpUI.actionButton({ label: '+ Import L4', variant: 'primary', size: 'sm', icon: '📥', onclick: 'ExploreHierarchyView.openSeedingDialog()' })}
                </div>
            `,
        });
    }

    // ── Main Page Render (F-001) ─────────────────────────────────────
    function renderPage() {
        const main = document.getElementById('mainContent');
        const content = _viewMode === 'tree'
            ? `<div class="exp-layout-split">
                   <div class="exp-layout-split__main">
                       <div class="exp-tree" id="expTree">${renderTree(_tree)}</div>
                   </div>
                   ${renderDetailPanel()}
               </div>`
            : renderScopeMatrix();

        main.innerHTML = `<div class="explore-page">
            <div class="explore-page__header">
                <div>
                    <h1 class="explore-page__title">Process Hierarchy</h1>
                    <p class="explore-page__subtitle">Manage L1 → L4 process structure, fit/gap analysis, and sign-off</p>
                </div>
            </div>
            ${renderKpiDashboard()}
            ${renderFilterBar()}
            ${content}
        </div>`;
    }

    // ── Public Actions ───────────────────────────────────────────────
    function toggleNode(id, e) {
        if (e) e.stopPropagation();
        if (_expandedNodes.has(id)) _expandedNodes.delete(id);
        else _expandedNodes.add(id);
        renderPage();
    }

    function selectNode(id, level) {
        _selectedNodeId = id;
        _selectedNodeLevel = level;
        _detailPanelTab = 'overview';
        renderPage();
    }

    function closePanel() {
        _selectedNodeId = null;
        renderPage();
    }

    function setDetailTab(tab) {
        _detailPanelTab = tab;
        renderPage();
    }

    function setViewMode(mode) {
        _viewMode = mode;
        renderPage();
    }

    function setSearch(q) {
        _searchQuery = q;
        renderPage();
    }

    function setFilter(groupId, value) {
        _filters[groupId] = value || null;
        renderPage();
    }

    function onFilterBarChange(update) {
        if (update._clearAll) {
            _filters = { fit: null, wave: null, area: null };
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    _filters[key] = null;
                } else if (Array.isArray(val)) {
                    _filters[key] = val[0];
                } else {
                    _filters[key] = val;
                }
            });
        }
        renderPage();
    }

    function sortMatrix() {
        // Simple toggle — full sort implementation in future
        _l3List.reverse();
        renderPage();
    }

    // ── Entry Point ──────────────────────────────────────────────────
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        if (!prog) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">📋</div><div class="exp-empty__title">Select a program first</div></div>`;
            return;
        }
        _pid = prog.id;

        main.innerHTML = `<div class="explore-page" style="display:flex;align-items:center;justify-content:center;min-height:300px">
            <div style="text-align:center;color:var(--sap-text-secondary)"><div style="font-size:28px;margin-bottom:8px">⏳</div>Loading hierarchy…</div>
        </div>`;

        try {
            await fetchAll();
            // Auto-expand L1 nodes
            _l1List.forEach(l1 => _expandedNodes.add(l1.id));
            renderPage();
        } catch (err) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Error loading hierarchy</div><p class="exp-empty__text">${esc(err.message)}</p></div>`;
        }
    }

    return {
        render,
        toggleNode, selectNode, closePanel, setDetailTab,
        setViewMode, setSearch, setFilter, onFilterBarChange, sortMatrix,
        openSignOffDialog, submitSignOff,
        openSeedingDialog, submitSeedImport,
        requestScopeChange, submitScopeChange,
        _setSeedMode, _filterCatalog,
    };
})();
