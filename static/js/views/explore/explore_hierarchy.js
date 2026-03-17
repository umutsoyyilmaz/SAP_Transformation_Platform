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
    let _l4ByL3 = {};
    let _scopeMatrixRows = [];
    let _tree = [];             // built tree structure
    let _hierarchyMeta = { total: 0, unfilteredTotal: 0 };
    let _hierarchyStats = { total: 0, l1: 0, l2: 0, l3: 0, l4: 0, in_scope: 0 };
    let _filterOptions = { areas: [], waves: [] };
    let _matrixMeta = { total: 0, page: 1, pages: 0, per_page: 25 };
    let _reloadTimer = null;

    function openProjectSetupBaseline() {
        App.navigate('project-setup');
        setTimeout(() => {
            if (typeof ProjectSetupView !== 'undefined' && ProjectSetupView?.switchTab) {
                ProjectSetupView.switchTab('scope-hierarchy');
            }
        }, 0);
    }

    // ── API ──────────────────────────────────────────────────────────
    async function fetchAll() {
        const treeResponse = _shouldUseLazyTree()
            ? await ExploreAPI.levels.listTree(_pid, { max_depth: 2 })
            : await ExploreAPI.levels.listTree(_pid, _currentTreeQuery());
        const matrixResponse = _viewMode === 'scope-matrix'
            ? await ExploreAPI.levels.scopeMatrix(_pid, _currentMatrixQuery())
            : null;
        _hierarchyMeta = {
            total: treeResponse?.total || 0,
            unfilteredTotal: treeResponse?.unfiltered_total || 0,
        };
        _hierarchyStats = Object.assign(
            { total: 0, l1: 0, l2: 0, l3: 0, l4: 0, in_scope: 0 },
            treeResponse?.stats || {}
        );
        _filterOptions = {
            areas: treeResponse?.filter_options?.areas || [],
            waves: treeResponse?.filter_options?.waves || [],
        };
        _tree = normalizeTreeLevels(treeResponse?.items || []);
        const flat = flattenTree(_tree);
        _l1List = flat.filter((item) => item.level === 'L1');
        _l2List = flat.filter((item) => item.level === 'L2');
        _l3List = flat.filter((item) => item.level === 'L3');
        _l4List = flat.filter((item) => item.level === 'L4');
        _l4ByL3 = groupBy(_l4List, 'parent_id');
        _scopeMatrixRows = matrixResponse?.items || [];
        _matrixMeta = {
            total: matrixResponse?.total || 0,
            page: matrixResponse?.page || 1,
            pages: matrixResponse?.pages || 0,
            per_page: matrixResponse?.per_page || 25,
        };
        if (_shouldUseLazyTree()) {
            _expandedNodes = new Set(_tree.map((node) => node.id));
        }
        if (_selectedNodeId && !flat.some((item) => item.id === _selectedNodeId)) {
            _selectedNodeId = null;
            _selectedNodeLevel = null;
        }
    }

    // ── Tree Normalization ───────────────────────────────────────────
    function normalizeTreeLevels(nodes) {
        return (nodes || []).map((node) => ({
            ...node,
            level: typeof node.level === 'number' ? `L${node.level}` : node.level,
            children: normalizeTreeLevels(node.children || []),
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

    function flattenTree(nodes, result = []) {
        for (const node of nodes || []) {
            result.push(node);
            if (node.children && node.children.length) flattenTree(node.children, result);
        }
        return result;
    }

    // ── Aggregation Helpers ──────────────────────────────────────────
    function aggregateFit(node) {
        if (node?.fit_summary) {
            return {
                fit: Number(node.fit_summary.fit || 0),
                gap: Number(node.fit_summary.gap || 0),
                partial_fit: Number(node.fit_summary.partial_fit || 0),
                pending: Number(node.fit_summary.pending || 0),
            };
        }
        if (node.level === 'L4') {
            return {
                fit: node.fit_status === 'fit' ? 1 : 0,
                gap: node.fit_status === 'gap' ? 1 : 0,
                partial_fit: node.fit_status === 'partial_fit' ? 1 : 0,
                pending: (!node.fit_status || node.fit_status === 'pending') ? 1 : 0
            };
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
        const total = _hierarchyStats.l4 || _l4List.length || 1;
        const fitDist = _hierarchyStats.fit_distribution || {};
        const fitC = fitDist.fit ?? _l4List.filter(l => l.fit_status === 'fit').length;
        const gapC = fitDist.gap ?? _l4List.filter(l => l.fit_status === 'gap').length;
        const partC = fitDist.partial_fit ?? _l4List.filter(l => l.fit_status === 'partial_fit').length;
        const pendC = total - fitC - gapC - partC;
        return `<div class="exp-kpi-strip exp-kpi-strip--compact">
            ${ExpUI.kpiBlock({ value: _hierarchyStats.l1 || _l1List.length, label: 'L1 Areas', accent: 'var(--exp-l1, #8b5cf6)' })}
            ${ExpUI.kpiBlock({ value: _hierarchyStats.l2 || _l2List.length, label: 'L2 Groups', accent: 'var(--exp-l2, #3b82f6)' })}
            ${ExpUI.kpiBlock({ value: _hierarchyStats.l3 || _l3List.length, label: 'L3 Scope Items', accent: 'var(--exp-l3, #10b981)' })}
            ${ExpUI.kpiBlock({ value: _hierarchyStats.l4 || _l4List.length, label: 'L4 Steps', accent: 'var(--exp-l4, #f59e0b)' })}
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

    function renderExecutionGovernanceBanner() {
        return HierarchyUI.bridgeCard({
            testId: 'explore-scope-governance-bridge',
            eyebrow: 'Execution Workspace',
            title: 'Scope &amp; Process reviews the baseline, it does not redefine it',
            body: 'Use this workspace for fit-gap review, workshop readiness, sign-off, and governed scope change requests. Structural baseline changes belong in <strong>Project Setup &gt; Scope &amp; Hierarchy</strong>.',
            actionsHtml: `
                ${ExpUI.actionButton({ label: 'Open Project Setup', variant: 'secondary', size: 'sm', onclick: 'ExploreHierarchyView.openProjectSetupBaseline()' })}
                ${ExpUI.actionButton({ label: 'Scope Change Queue', variant: 'primary', size: 'sm', onclick: 'ExploreHierarchyView.openScopeChangeQueue()' })}
            `,
        });
    }

    // ── Fit Distribution Bar (F-004) ─────────────────────────────────
    function renderFitDistBar(counts) {
        return ExpUI.fitBarMini(counts, { height: 8, width: 120 });
    }

    // ── Process Node Row (F-003) ─────────────────────────────────────
    function renderNodeRow(node, depth) {
        const hasChildren = Boolean((node.children && node.children.length > 0) || node.has_children);
        const isExpanded = _expandedNodes.has(node.id);
        const isSelected = _selectedNodeId === node.id;
        const indent = depth * parseInt(getComputedStyle(document.documentElement).getPropertyValue('--exp-tree-indent') || '24');
        const fitAgg = aggregateFit(node);

        const highlightMatch = _searchQuery && (node.name || '').toLowerCase().includes(_searchQuery.toLowerCase());
        const nameHtml = highlightMatch
            ? (node.name || '').replace(new RegExp(`(${_searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'), '<mark>$1</mark>')
            : esc(node.name || '');

        return HierarchyRenderers.treeRow({
            attrs: `data-node-id="${node.id}" data-level="${node.level}"`,
            rowClass: `exp-tree-node${isSelected ? ' exp-tree-node--active' : ''}`,
            rowStyle: `padding-left:${indent + 12}px`,
            chevronHtml: HierarchyRenderers.treeChevron({
                hasChildren,
                expanded: isExpanded,
                onclick: `ExploreHierarchyView.toggleNode('${node.id}',event)`,
                className: 'exp-tree-node__chevron',
                openClass: 'exp-tree-node__chevron--open',
                leafClass: 'exp-tree-node__chevron exp-tree-node__chevron--leaf',
            }),
            leadingHtml: ExpUI.levelBadge(node.level),
            codeHtml: esc(node.code || node.sap_code || ''),
            codeClass: 'exp-tree-node__code',
            codeTag: 'span',
            nameHtml,
            nameClass: 'exp-tree-node__name',
            nameAttrs: `onclick="ExploreHierarchyView.selectNode('${node.id}','${node.level}')"`,
            metaHtml: `
                ${ExpUI.fitBadge(node.effective_fit_status || node.fit_status || 'pending', { compact: true })}
                ${renderFitDistBar(fitAgg)}
                ${workshopIndicator(node)}
            `,
            metaClass: 'exp-tree-node__meta',
            actionsHtml: `
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
            `,
            actionsClass: 'exp-tree-node__actions',
        });
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
        const rows = _scopeMatrixRows;
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
            const fitAgg = l3.fit_summary || { fit: 0, gap: 0, partial_fit: 0, pending: 0 };
            return HierarchyRenderers.tableRow({
                rowClass: 'exp-expandable-row hierarchy-table-row--interactive',
                onclick: `ExploreHierarchyView.selectNode('${l3.id}','L3')`,
                cells: [
                    { html: esc(l3.code || l3.sap_code || ''), className: 'hierarchy-table-cell--mono' },
                    { html: esc(l3.name || ''), className: 'exp-truncate hierarchy-table-cell--truncate' },
                    { html: ExpUI.areaPill(l3.area || l3.area_code || '') },
                    { html: ExpUI.wavePill(l3.wave) },
                    { html: `${ExpUI.fitBadge(l3.effective_fit_status || l3.fit_status || 'pending')} ${ExpUI.fitBarMini(fitAgg, { height: 4, width: 60 })}` },
                    { html: ExpUI.workshopStatusPill(l3.workshop_status || 'draft') },
                    { html: ExpUI.countChip(l3.requirement_count || 0, { variant: 'requirement' }) },
                    { html: ExpUI.countChip(l3.open_item_count || 0, { variant: 'open_item' }) },
                    {
                        html: ExpUI.actionButton({ label: 'Scope Change', variant: 'ghost', size: 'sm', onclick: `ExploreHierarchyView.requestScopeChange('${l3.id}')` }),
                        attrs: 'onclick="event.stopPropagation()"',
                    },
                ],
            });
        }).join('');

        const pagination = _matrixMeta.pages > 1 ? `
            <div class="exp-table__footer" style="display:flex;justify-content:space-between;align-items:center;padding:12px 0 0">
                <div style="font-size:12px;color:var(--sap-text-secondary)">Page ${_matrixMeta.page} / ${_matrixMeta.pages} · ${_matrixMeta.total} items</div>
                <div style="display:flex;gap:8px">
                    ${ExpUI.actionButton({ label: 'Prev', variant: 'secondary', size: 'sm', onclick: `ExploreHierarchyView.setMatrixPage(${_matrixMeta.page - 1})`, disabled: _matrixMeta.page <= 1 })}
                    ${ExpUI.actionButton({ label: 'Next', variant: 'secondary', size: 'sm', onclick: `ExploreHierarchyView.setMatrixPage(${_matrixMeta.page + 1})`, disabled: _matrixMeta.page >= _matrixMeta.pages })}
                </div>
            </div>
        ` : '';

        return HierarchyRenderers.tableCard({
            wrapperClass: 'exp-card hierarchy-table-card',
            bodyClass: 'exp-card__body hierarchy-table-card__scroll',
            tableHtml: `<table class="exp-table">${header}<tbody>${body}</tbody></table>${pagination}`,
            testId: 'explore-scope-matrix',
        });
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
            case 'fit': content = renderDetailFit(node); break;
            case 'requirements': content = renderDetailRequirements(node); break;
            case 'workshop': content = renderDetailWorkshop(node); break;
        }

        return HierarchyWidgets.detailPanel({
            testId: 'explore-scope-detail-panel',
            headerHtml: `
                <div>
                    ${ExpUI.levelBadge(node.level)}
                    <strong style="margin-left:8px">${esc(node.code || node.sap_code || '')}</strong>
                </div>
                <button onclick="ExploreHierarchyView.closePanel()" style="background:none;border:none;cursor:pointer;font-size:18px;color:var(--sap-text-secondary)">✕</button>
            `,
            tabsHtml,
            contentHtml: content,
        });
    }

    function renderDetailPanelEmpty() {
        return HierarchyWidgets.detailPanel({
            collapsed: true,
            testId: 'explore-scope-detail-panel',
        });
    }

    function renderDetailOverview(node) {
        const fitAgg = aggregateFit(node);
        const total = fitAgg.fit + fitAgg.gap + fitAgg.partial_fit + fitAgg.pending;
        return `
            ${HierarchyRenderers.detailSection({
                title: 'General',
                bodyHtml: `
                    ${HierarchyRenderers.detailRow({ label: 'Name', valueHtml: esc(node.name || '') })}
                    ${HierarchyRenderers.detailRow({ label: 'Level', valueHtml: ExpUI.levelBadge(node.level) })}
                    ${HierarchyRenderers.detailRow({ label: 'Code', valueHtml: `<code>${esc(node.code || node.sap_code || '')}</code>` })}
                    ${node.area || node.area_code ? HierarchyRenderers.detailRow({ label: 'Area', valueHtml: ExpUI.areaPill(node.area || node.area_code) }) : ''}
                    ${node.wave ? HierarchyRenderers.detailRow({ label: 'Wave', valueHtml: ExpUI.wavePill(node.wave) }) : ''}
                    ${node.description ? HierarchyRenderers.detailRow({ label: 'Description', valueHtml: esc(node.description), valueClass: ' hierarchy-detail-row__value--start' }) : ''}
                `,
            })}
            ${HierarchyRenderers.detailSection({
                title: `Fit Analysis (${total} items)`,
                bodyHtml: `
                    ${ExpUI.fitBarMini(fitAgg, { height: 10 })}
                    ${HierarchyRenderers.detailLegend({
                        items: [
                            { tone: 'fit', label: `● Fit ${fitAgg.fit}` },
                            { tone: 'partial', label: `◐ Partial ${fitAgg.partial_fit}` },
                            { tone: 'gap', label: `● Gap ${fitAgg.gap}` },
                            { tone: 'pending', label: `○ Pending ${fitAgg.pending}` },
                        ],
                    })}
                `,
            })}
            ${node.level === 'L3' ? renderL3ConsolidatedCard(node) : ''}
        `;
    }

    function renderDetailFit(node) {
        const children = node.children || [];
        if (!children.length) {
            return HierarchyRenderers.detailSection({
                bodyHtml: HierarchyRenderers.detailCopy({
                    text: 'No child items to show fit analysis.',
                    className: ' hierarchy-detail-copy--muted',
                }),
            });
        }
        return HierarchyRenderers.detailSection({
            title: 'Child Fit Breakdown',
            bodyHtml: children.map((c) => HierarchyRenderers.detailRow({
                label: `<code>${esc(c.code || c.sap_code || '')}</code>`,
                valueHtml: `
                    <div class="hierarchy-detail-actions hierarchy-detail-actions--compact">
                        <span class="hierarchy-detail-copy">${esc(c.name || '')}</span>
                        ${ExpUI.fitBadge(c.effective_fit_status || c.fit_status || 'pending', { compact: true })}
                    </div>
                `,
                className: ' hierarchy-detail-row--compact',
                labelClass: ' hierarchy-table-cell--mono',
                valueClass: ' hierarchy-detail-row__value--start',
            })).join(''),
        });
    }

    function renderDetailRequirements(node) {
        return HierarchyRenderers.detailSection({
            title: 'Related Requirements',
            bodyHtml: `
                ${HierarchyRenderers.detailCopy({
                    text: `
                        ${ExpUI.countChip(node.requirement_count || 0, { variant: 'requirement', label: 'REQ' })}
                        ${ExpUI.countChip(node.open_item_count || 0, { variant: 'open_item', label: 'OI' })}
                    `,
                    className: ' hierarchy-detail-copy--muted',
                })}
                ${HierarchyRenderers.detailActions({
                    actionsHtml: ExpUI.actionButton({ label: 'View Handoff', variant: 'ghost', size: 'sm', onclick: `App.navigate('explore-traceability')` }),
                })}
            `,
        });
    }

    function renderDetailWorkshop(node) {
        const count = node.workshops_count || node.workshop_count || 0;
        return HierarchyRenderers.detailSection({
            title: 'Workshops',
            bodyHtml: `
                ${HierarchyRenderers.detailCopy({
                    text: count ? `${count} workshop(s) linked` : 'No workshops linked to this item',
                    className: ' hierarchy-detail-copy--muted',
                })}
                ${HierarchyRenderers.detailActions({
                    actionsHtml: `
                        ${ExpUI.actionButton({ label: 'View Workshops', variant: 'ghost', size: 'sm', onclick: `App.navigate('explore-workshops')` })}
                        ${ExpUI.actionButton({ label: 'View Outcomes', variant: 'ghost', size: 'sm', onclick: `App.navigate('explore-outcomes')` })}
                    `,
                })}
            `,
        });
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
            ? `
                ${HierarchyRenderers.detailCopy({
                    text: `<strong>Blockers (${blockers.length}):</strong>`,
                    className: ' hierarchy-detail-copy--muted',
                })}
                <ul class="hierarchy-detail-copy hierarchy-detail-copy--muted hierarchy-detail-list">
                    ${blockers.map((b) => `<li>${esc(b)}</li>`).join('')}
                </ul>
            `
            : '';

        return HierarchyRenderers.detailSection({
            title: 'L3 Consolidated Status',
            className: 'hierarchy-detail-section--callout',
            bodyHtml: `
                ${HierarchyRenderers.detailRow({ label: 'Status', valueHtml: signoffBadge })}
                ${HierarchyRenderers.detailRow({ label: 'Effective Fit', valueHtml: ExpUI.fitBadge(node.effective_fit_status || 'pending') })}
                ${blockerHtml}
                ${HierarchyRenderers.detailActions({
                    actionsHtml: `
                        ${signoff !== 'signed_off' ? ExpUI.actionButton({ label: 'Sign Off', variant: 'success', size: 'sm', onclick: `ExploreHierarchyView.openSignOffDialog('${node.id}')` }) : ''}
                        ${signoff !== 'signed_off' ? ExpUI.actionButton({ label: 'Override', variant: 'warning', size: 'sm', onclick: `ExploreHierarchyView.openSignOffDialog('${node.id}',true)` }) : ''}
                    `,
                })}
            `,
        });
    }

    // ── L3 Sign-Off Dialog (F-009) ───────────────────────────────────
    function openSignOffDialog(l3Id, isOverride = false) {
        const node = findNodeAcross(l3Id, 'L3');
        if (!node) return;
        const fitAgg = aggregateFit(node);
        const title = isOverride ? 'Override L3 Decision' : 'Sign Off L3 Scope Item';

        App.openModal(HierarchyWidgets.modalFrame({
            testId: 'explore-scope-signoff-modal',
            title,
            subtitle: `${esc(node.code || '')} — ${esc(node.name || '')}`,
            maxWidth: '500px',
            compact: true,
            bodyHtml: `
                <div class="hierarchy-modal__surface">
                    <div class="hierarchy-modal__surface-title">L4 Breakdown</div>
                    ${ExpUI.fitBarMini(fitAgg, { height: 8 })}
                    <div style="display:flex;gap:8px;margin-top:4px;font-size:11px">
                        <span>Fit: ${fitAgg.fit}</span><span>Gap: ${fitAgg.gap}</span>
                        <span>Partial: ${fitAgg.partial_fit}</span><span>Pending: ${fitAgg.pending}</span>
                    </div>
                </div>
                ${isOverride ? `<div style="margin-top:12px">
                    <label style="font-size:12px;font-weight:600;display:block;margin-bottom:4px">Override Status</label>
                    <select id="signoffOverrideStatus" style="width:100%;padding:8px;border:1px solid var(--sap-border);border-radius:var(--exp-radius-md)">
                        <option value="fit">Fit</option>
                        <option value="partial_fit">Partial Fit</option>
                        <option value="gap">Gap</option>
                    </select>
                </div>` : ''}
                <div style="margin-top:12px">
                    <label style="font-size:12px;font-weight:600;display:block;margin-bottom:4px">Comment</label>
                    <textarea id="signoffComment" rows="3" style="width:100%;padding:8px;border:1px solid var(--sap-border);border-radius:var(--exp-radius-md);resize:vertical" placeholder="Add comment..."></textarea>
                </div>
            `,
            footerHtml: `
                <div></div>
                <div style="display:flex;gap:8px">
                    ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                    ${ExpUI.actionButton({ label: isOverride ? 'Override' : 'Sign Off', variant: isOverride ? 'warning' : 'success', onclick: `ExploreHierarchyView.submitSignOff('${l3Id}',${isOverride})` })}
                </div>
            `,
        }));
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
        const l3Options = _l3List.map(l3 =>
            `<option value="${l3.id}">${esc(l3.code || '')} — ${esc(l3.name || '')}</option>`
        ).join('');

        return `<div>
            <div style="margin-bottom:12px">
                <label style="font-weight:600;font-size:13px;display:block;margin-bottom:4px">Select L3 Scope Item</label>
                <select id="seedCatalogL3" style="width:100%;padding:8px;border-radius:var(--exp-radius-md);border:1px solid #e2e8f0">
                    <option value="">— Select scope item to import L4s —</option>
                    ${l3Options}
                </select>
            </div>
            <div style="padding:16px;text-align:center;border:1px solid #e2e8f0;border-radius:var(--exp-radius-md);background:var(--sap-bg)">
                <div style="font-size:24px;margin-bottom:8px">📚</div>
                <p style="font-size:13px;color:var(--sap-text-secondary)">Selecting an L3 item will import all standard L4 process steps from the SAP Best Practice catalog.</p>
                <p style="font-size:12px;color:var(--sap-text-secondary);margin-top:4px">Already existing steps will be skipped automatically.</p>
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
        // Detect active seed mode
        const catalogTab = document.querySelector('.exp-tab--active');
        const mode = catalogTab?.textContent?.includes('Manual') ? 'manual'
            : catalogTab?.textContent?.includes('BPMN') ? 'bpmn'
                : 'catalog';

        if (mode === 'bpmn') {
            App.toast('BPMN import is not yet implemented', 'info');
            return;
        }

        if (mode === 'manual') {
            return _submitManualSeed();
        }

        // Catalog mode — seed L4s from catalog for selected L3
        return _submitCatalogSeed();
    }

    async function _submitCatalogSeed() {
        const l3Select = document.getElementById('seedCatalogL3');
        const l3Id = l3Select?.value;
        if (!l3Id) {
            App.toast('Please select an L3 scope item first', 'warning');
            return;
        }

        const btn = document.getElementById('seedImportBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Importing…'; }

        try {
            const result = await ExploreAPI.levels.seedFromCatalog(l3Id);
            App.closeModal();

            const count = result.created_count || 0;
            const skipped = result.skipped_count || 0;

            if (count === 0 && skipped > 0) {
                App.toast(`All ${skipped} L4 steps already exist — nothing to import`, 'info');
            } else {
                App.toast(`${count} L4 process step${count !== 1 ? 's' : ''} imported successfully${skipped ? ` (${skipped} skipped)` : ''}`, 'success');
            }

            // Refresh and show the new items
            await _postImportRefresh(l3Id, result.created || []);
        } catch (err) {
            App.toast(err.message || 'Import failed', 'error');
            if (btn) { btn.disabled = false; btn.textContent = 'Import Selected'; }
        }
    }

    async function _submitManualSeed() {
        const l3Id = document.getElementById('seedManualL3')?.value;
        const name = document.getElementById('seedManualName')?.value?.trim();
        const code = document.getElementById('seedManualCode')?.value?.trim();
        const desc = document.getElementById('seedManualDesc')?.value?.trim();

        if (!l3Id) { App.toast('Please select an L3 scope item', 'warning'); return; }
        if (!name) { App.toast('Step name is required', 'warning'); return; }

        const btn = document.getElementById('seedImportBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Adding…'; }

        try {
            const data = { name, description: desc };
            if (code) data.code = code;
            else data.code = `L4-${Date.now()}`;

            await ExploreAPI.levels.addChild(l3Id, data);
            App.closeModal();
            App.toast(`L4 step "${name}" added successfully`, 'success');
            await _postImportRefresh(l3Id, [data.code]);
        } catch (err) {
            App.toast(err.message || 'Failed to add step', 'error');
            if (btn) { btn.disabled = false; btn.textContent = 'Import Selected'; }
        }
    }

    /** After import: refresh data, expand parent chain, highlight new items */
    async function _postImportRefresh(l3Id, newCodes) {
        const oldL4Ids = new Set(_l4List.map(l => l.id));

        await fetchAll();

        // Expand parent chain up to L1 so imported L4s are visible
        const l3Node = _l3List.find(l => String(l.id) === String(l3Id));
        if (l3Node) {
            _expandedNodes.add(l3Node.id);
            // Find L2 parent
            const l2 = _l2List.find(l => l.id === l3Node.parent_id);
            if (l2) {
                _expandedNodes.add(l2.id);
                // Find L1 parent
                const l1 = _l1List.find(l => l.id === l2.parent_id);
                if (l1) _expandedNodes.add(l1.id);
            }
        }

        renderPage();

        // Highlight newly added L4 nodes
        const newL4Ids = _l4List
            .filter(l => !oldL4Ids.has(l.id))
            .map(l => l.id);

        requestAnimationFrame(() => {
            newL4Ids.forEach(id => {
                const el = document.querySelector(`[data-node-id="${id}"]`);
                if (el) {
                    el.classList.add('highlight-new');
                    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            });
            // Remove highlight after animation
            setTimeout(() => {
                document.querySelectorAll('.highlight-new').forEach(el => {
                    el.classList.remove('highlight-new');
                });
            }, 5000);
        });
    }

    function _filterCatalog(q) {
        const items = document.querySelectorAll('#seedCatalogList .seed-catalog-item');
        const query = (q || '').toLowerCase();
        items.forEach(el => {
            el.style.display = el.textContent.toLowerCase().includes(query) ? '' : 'none';
        });
    }

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
        App.openModal(HierarchyWidgets.modalFrame({
            testId: 'explore-scope-change-modal',
            title: 'Request Scope Change',
            subtitle: `Scope item: ${esc(node?.code || '')} — ${esc(node?.name || '')}`,
            maxWidth: '480px',
            compact: true,
            bodyHtml: `
                <div class="exp-inline-form">
                    <div class="exp-inline-form__row">
                        <div class="exp-inline-form__field"><label>Change Type</label>
                            <select id="scrType"><option value="add_to_scope">Add to Scope</option><option value="remove_from_scope">Remove from Scope</option><option value="change_fit_status">Change Fit Status</option><option value="change_wave">Change Wave</option><option value="change_priority">Change Priority</option></select>
                        </div>
                    </div>
                    <div class="exp-inline-form__row">
                        <div class="exp-inline-form__field"><label>Justification</label><textarea id="scrJustification" rows="3" placeholder="Describe the reason…"></textarea></div>
                    </div>
                </div>
            `,
            footerHtml: `
                <div></div>
                <div style="display:flex;gap:8px">
                    ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                    ${ExpUI.actionButton({ label: 'Submit Request', variant: 'primary', onclick: `ExploreHierarchyView.submitScopeChange('${l3Id}')` })}
                </div>
            `,
        }));
    }

    async function submitScopeChange(l3Id) {
        const activeProject = App.getActiveProject();
        if (!activeProject?.id) {
            App.toast('Please select a project first before submitting a scope change', 'error');
            return;
        }
        try {
            await ExploreAPI.scopeChangeRequests.create(_pid, {
                l3_scope_item_id: l3Id,
                process_level_id: l3Id,
                project_id: activeProject.id,
                change_type: document.getElementById('scrType')?.value,
                justification: document.getElementById('scrJustification')?.value,
            });
            App.closeModal();
            App.toast('Scope change request submitted', 'success');
        } catch (err) {
            App.toast(err.message || 'Failed to submit', 'error');
        }
    }

    async function openScopeChangeQueue() {
        try {
            const requests = await ExploreAPI.scopeChangeRequests.list(_pid);
            const rows = (requests || [])
                .slice()
                .sort((a, b) => String(b.requested_at || b.created_at || '').localeCompare(String(a.requested_at || a.created_at || '')));
            const content = rows.length
                ? `
                    <div style="display:flex;flex-direction:column;gap:10px;max-height:420px;overflow:auto">
                        ${rows.map((item) => `
                            <div class="card" style="padding:12px 14px">
                                <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">
                                    <div>
                                        <div style="font-weight:700">${esc(item.code || item.id || 'Scope Change')}</div>
                                        <div style="font-size:12px;color:var(--pg-color-text-secondary);margin-top:4px">${esc((item.change_type || 'change').replace(/_/g, ' '))}</div>
                                    </div>
                                    ${ExpUI.pill({
                                        label: (item.status || 'requested').replace(/_/g, ' '),
                                        variant: item.status === 'implemented' ? 'success' : item.status === 'approved' ? 'info' : item.status === 'rejected' ? 'danger' : 'warning',
                                        size: 'sm',
                                    })}
                                </div>
                                <div style="font-size:13px;color:var(--pg-color-text-secondary);margin-top:8px">${esc(item.justification || 'No justification captured.')}</div>
                            </div>
                        `).join('')}
                    </div>
                `
                : `<div class="exp-empty"><div class="exp-empty__icon">🗂️</div><div class="exp-empty__title">No scope change requests</div><p class="exp-empty__text">Use the Scope Change action on an L3 scope item to submit the first request.</p></div>`;

            App.openModal(HierarchyWidgets.modalFrame({
                testId: 'explore-scope-change-queue-modal',
                title: 'Scope Change Queue',
                subtitle: 'Project-owned change requests for the active execution scope.',
                maxWidth: '720px',
                bodyHtml: content,
                footerHtml: `
                    <div></div>
                    <div>${ExpUI.actionButton({ label: 'Close', variant: 'secondary', onclick: 'App.closeModal()' })}</div>
                `,
            }));
        } catch (err) {
            App.toast(err.message || 'Failed to load scope change queue', 'error');
        }
    }


    // ── View Mode Switch ─────────────────────────────────────────────
    function renderViewToggle() {
        return `<div class="exp-toolbar__group">
            ${ExpUI.actionButton({ label: '🌲 Tree', variant: _viewMode === 'tree' ? 'primary' : 'secondary', size: 'sm', onclick: `ExploreHierarchyView.setViewMode('tree')` })}
            ${ExpUI.actionButton({ label: '📊 Matrix', variant: _viewMode === 'scope-matrix' ? 'primary' : 'secondary', size: 'sm', onclick: `ExploreHierarchyView.setViewMode('scope-matrix')` })}
        </div>`;
    }

    // ── Quick Start — Catalog Seed Wizard (F-011, FDD-I07) ──────────────
    async function openCatalogSeedWizard() {
        let modules = [];
        ExpUI.modal({
            title: '🌱 Quick Start from SAP Catalog',
            contentHtml: `<div style="text-align:center;padding:24px"><div style="font-size:20px">⏳</div><p>Loading modules…</p></div>`,
            footerHtml: '',
            id: 'catalogWizardModal',
        });
        try {
            modules = await ExploreAPI.catalog.modules();
        } catch (err) {
            document.querySelector('#catalogWizardModal .modal-body').innerHTML =
                `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Failed to load catalog</div><p>${esc(err.message)}</p></div>`;
            return;
        }
        if (!modules.length) {
            document.querySelector('#catalogWizardModal .modal-body').innerHTML =
                `<div class="exp-empty"><div class="exp-empty__icon">⚠️</div><div class="exp-empty__title">Catalog is empty</div><p>Catalog data must be loaded first.</p></div>`;
            return;
        }
        let checkboxHtml = '';
        for (const l1 of modules) {
            checkboxHtml += `<div style="margin-bottom:12px"><div style="font-weight:600;color:var(--sap-text);margin-bottom:4px">${esc(l1.name)} <span style="font-size:11px;color:var(--sap-text-secondary)">(${esc(l1.sap_module_group)})</span></div>`;
            for (const l2 of (l1.modules || [])) {
                checkboxHtml += `<label style="display:flex;align-items:center;gap:8px;padding:4px 0;cursor:pointer">
                    <input type="checkbox" name="catalogModule" value="${esc(l2.sap_module)}" style="width:15px;height:15px">
                    <span>${esc(l2.name)}</span>
                    <span style="margin-left:auto;font-size:11px;color:var(--sap-text-secondary);background:var(--sap-surface-2);padding:2px 6px;border-radius:10px">${l2.step_count} steps</span>
                </label>`;
            }
            checkboxHtml += `</div>`;
        }
        document.querySelector('#catalogWizardModal .modal-body').innerHTML = `
            <p style="color:var(--sap-text-secondary);margin-bottom:16px">Select the SAP modules you want to import. The full L1→L4 process hierarchy of selected modules will be added to the project.</p>
            <div id="catalogModuleList" style="max-height:360px;overflow-y:auto;border:1px solid var(--sap-border);border-radius:var(--exp-radius-md);padding:12px">
                ${checkboxHtml}
            </div>
        `;
        document.querySelector('#catalogWizardModal .modal-footer').innerHTML = `
            <button class="btn btn-secondary" onclick="ExpUI.closeModal('catalogWizardModal')">Cancel</button>
            <button class="btn btn-primary" onclick="ExploreHierarchyView._submitCatalogSeed()">Import Selected</button>
        `;
    }

    async function _submitCatalogSeed() {
        const checked = [...document.querySelectorAll('input[name="catalogModule"]:checked')].map(el => el.value);
        if (!checked.length) {
            ExpUI.toast({ message: 'Select at least one module.', type: 'warning' });
            return;
        }
        const btn = document.querySelector('#catalogWizardModal .modal-footer .btn-primary');
        if (btn) { btn.disabled = true; btn.textContent = 'Importing…'; }
        try {
            const tenantId = App.getActiveTenant ? App.getActiveTenant().id : (window._tenantId || 1);
            const result = await ExploreAPI.catalog.seedProject(_pid, {
                tenant_id: tenantId,
                modules: checked,
            });
            ExpUI.closeModal('catalogWizardModal');
            const c = result.created || {};
            ExpUI.toast({
                message: `Import completed — L1:${c.l1} L2:${c.l2} L3:${c.l3} L4:${c.l4} created (${result.elapsed_ms}ms)`,
                type: 'success', duration: 6000,
            });
            await fetchAll();
            _l1List.forEach(l1 => _expandedNodes.add(l1.id));
            renderPage();
        } catch (err) {
            ExpUI.toast({ message: `Error: ${err.message}`, type: 'error' });
            if (btn) { btn.disabled = false; btn.textContent = 'Import Selected'; }
        }
    }

    // ── Filter Bar ───────────────────────────────────────────────────
    function renderFilterBar() {
        const areas = (_filterOptions.areas && _filterOptions.areas.length)
            ? _filterOptions.areas
            : [...new Set(_l3List.map(l => l.area || l.area_code).filter(Boolean))].sort();
        const waves = (_filterOptions.waves && _filterOptions.waves.length)
            ? _filterOptions.waves
            : [...new Set(_l3List.map(l => l.wave).filter(Boolean))].sort();

        return HierarchyWidgets.filterToolbar({
            id: 'hierarchyFB',
            searchPlaceholder: 'Search processes…',
            searchValue: _searchQuery,
            onSearch: "ExploreHierarchyView.setSearch(this.value)",
            onChange: "ExploreHierarchyView.onFilterBarChange",
            testId: 'explore-scope-filter-toolbar',
            filters: [
                {
                    id: 'fit', label: 'Fit Status', icon: '◐', type: 'single',
                    color: 'var(--exp-fit)',
                    options: [
                        { value: 'fit', label: 'Fit' },
                        { value: 'gap', label: 'Gap' },
                        { value: 'partial_fit', label: 'Partial Fit' },
                        { value: 'pending', label: 'Pending' },
                    ],
                    selected: _filters.fit || '',
                },
                {
                    id: 'area', label: 'Area / Module', icon: '📁', type: 'multi',
                    color: 'var(--exp-l2)',
                    options: areas.map(a => ({ value: a, label: a })),
                    selected: _filters.area ? [_filters.area] : [],
                },
                {
                    id: 'wave', label: 'Wave', icon: '🌊', type: 'single',
                    color: 'var(--exp-l4)',
                    options: waves.map(w => ({ value: String(w), label: `Wave ${w}` })),
                    selected: _filters.wave ? String(_filters.wave) : '',
                },
            ],
            actionsHtml: HierarchyUI.actionCluster(`
                ${renderViewToggle()}
                ${ExpUI.actionButton({ label: 'Scope Change Queue', variant: 'primary', size: 'sm', icon: '🗂️', onclick: 'ExploreHierarchyView.openScopeChangeQueue()' })}
                ${ExpUI.actionButton({ label: 'Open Project Setup', variant: 'secondary', size: 'sm', icon: '🏗️', onclick: 'ExploreHierarchyView.openProjectSetupBaseline()' })}
            `),
        });
    }

    // ── Main Page Render (F-001) ─────────────────────────────────────
    function renderPage() {
        const main = document.getElementById('mainContent');
        const hasBaseline = _hierarchyMeta.unfilteredTotal || _l1List.length || _l2List.length || _l3List.length || _l4List.length;
        const content = !hasBaseline
            ? HierarchyUI.emptyState({
                testId: 'explore-scope-empty',
                icon: '🏗️',
                title: 'No scoped baseline is available yet',
                text: 'Create the project baseline in Project Setup, then return here for fit-gap review, workshops, and sign-off.',
                actionsHtml: ExpUI.actionButton({ label: 'Open Project Setup', variant: 'primary', size: 'sm', onclick: 'ExploreHierarchyView.openProjectSetupBaseline()' }),
            })
            : _viewMode === 'tree'
            ? `<div class="exp-layout-split">
                   <div class="exp-layout-split__main">
                       ${HierarchyWidgets.treeShell({
                           testId: 'explore-scope-tree',
                           bodyHtml: `<div class="exp-tree" id="expTree">${renderTree(_tree)}</div>`,
                           emptyText: 'No scope items found.',
                       })}
                   </div>
                   ${renderDetailPanel()}
               </div>`
            : renderScopeMatrix();

        main.innerHTML = `<div class="explore-page" data-testid="explore-scope-page">
            <div class="explore-page__header">
                <div>
                    <h1 class="explore-page__title">Scope &amp; Process</h1>
                    <p class="explore-page__subtitle">Review the scoped baseline, run fit-gap analysis, manage workshop readiness, and govern scope changes.</p>
                </div>
            </div>
            ${ExpUI.exploreStageNav({ current: 'explore-scope' })}
            ${renderKpiDashboard()}
            ${renderExecutionGovernanceBanner()}
            ${renderFilterBar()}
            ${content}
        </div>`;
    }

    // ── Public Actions ───────────────────────────────────────────────
    async function toggleNode(id, e) {
        if (e) e.stopPropagation();
        if (_expandedNodes.has(id)) {
            _expandedNodes.delete(id);
            renderPage();
            return;
        }
        const node = findNode(id);
        if (_shouldUseLazyTree() && node?.has_children && !node?.children_loaded) {
            await _loadChildren(id);
        }
        _expandedNodes.add(id);
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

    async function setViewMode(mode) {
        _viewMode = mode;
        if (mode === 'scope-matrix') _matrixMeta.page = 1;
        await fetchAll();
        renderPage();
    }

    function setSearch(q) {
        _searchQuery = q;
        _matrixMeta.page = 1;
        _scheduleReload();
    }

    function setFilter(groupId, value) {
        _filters[groupId] = value || null;
        _matrixMeta.page = 1;
        _scheduleReload();
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
        _scheduleReload();
    }

    function sortMatrix() {
        // Simple toggle — full sort implementation in future
        _scopeMatrixRows.reverse();
        renderPage();
    }

    async function setMatrixPage(page) {
        const nextPage = Math.max(1, Math.min(page, _matrixMeta.pages || 1));
        if (nextPage === _matrixMeta.page) return;
        _matrixMeta.page = nextPage;
        await fetchAll();
        renderPage();
    }

    // ── Entry Point ──────────────────────────────────────────────────
    async function render() {
        const main = document.getElementById('mainContent');
        const project = App.getActiveProject();
        if (!project) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">📋</div><div class="exp-empty__title">Select a project first</div></div>`;
            return;
        }
        _pid = project.id;

        main.innerHTML = HierarchyUI.loading({ label: 'Loading execution scope…' });

        try {
            await fetchAll();
            // Auto-expand L1 nodes
            _l1List.forEach(l1 => _expandedNodes.add(l1.id));
            renderPage();
        } catch (err) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Error loading hierarchy</div><p class="exp-empty__text">${esc(err.message)}</p></div>`;
        }
    }

    function _currentTreeQuery() {
        return {
            q: _searchQuery || '',
            fit_status: _filters.fit || '',
            wave: _filters.wave || '',
            process_area: _filters.area || '',
        };
    }

    function _currentMatrixQuery() {
        return Object.assign({}, _currentTreeQuery(), {
            page: _matrixMeta.page || 1,
            per_page: _matrixMeta.per_page || 25,
        });
    }

    function _hasTreeQuery() {
        return Boolean(_searchQuery || _filters.fit || _filters.wave || _filters.area);
    }

    function _shouldUseLazyTree() {
        return _viewMode === 'tree' && !_hasTreeQuery();
    }

    async function _loadChildren(id) {
        const response = await ExploreAPI.levels.listChildren(_pid, id);
        const node = findNode(id);
        if (!node) return;
        node.children = normalizeTreeLevels(response?.items || []);
        node.children_loaded = true;
    }

    function _scheduleReload() {
        clearTimeout(_reloadTimer);
        _reloadTimer = setTimeout(async () => {
            const main = document.getElementById('mainContent');
            if (main) main.innerHTML = HierarchyUI.loading({ label: 'Refreshing execution scope…' });
            try {
                await fetchAll();
                renderPage();
            } catch (err) {
                if (main) {
                    main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">❌</div><div class="exp-empty__title">Error loading hierarchy</div><p class="exp-empty__text">${esc(err.message)}</p></div>`;
                }
            }
        }, 220);
    }

    return {
        render,
        toggleNode, selectNode, closePanel, setDetailTab,
        setViewMode, setSearch, setFilter, onFilterBarChange, sortMatrix, setMatrixPage,
        openSignOffDialog, submitSignOff,
        openProjectSetupBaseline, openScopeChangeQueue,
        requestScopeChange, submitScopeChange,
        _setSeedMode, _filterCatalog,
    };
})();
