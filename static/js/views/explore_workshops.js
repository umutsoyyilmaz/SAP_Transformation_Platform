/**
 * Explore Phase — Module B: Workshop Hub
 * F-011: WorkshopHubPage      F-012: WorkshopTable
 * F-013: WorkshopKanban       F-014: CapacityView
 * F-015: FilterBar             F-016: KpiStrip
 * F-017: AreaMilestoneTracker
 *
 * Route: /explore/workshops (via App.navigate)
 */
const ExploreWorkshopHubView = (() => {
    'use strict';

    const esc = ExpUI.esc;

    // ── State ────────────────────────────────────────────────────────
    let _pid = null;
    let _viewMode = 'table';         // table | kanban | capacity
    let _workshops = [];
    let _stats = {};
    let _l3Items = [];
    let _filters = { status: '', wave: '', area: '', facilitator: '', search: '' };
    let _groupBy = 'none';           // none | wave | area | facilitator | status | date
    let _sortKey = 'code';
    let _sortDir = 'asc';
    let _page = 1;
    const PAGE_SIZE = 25;

    // ── API ──────────────────────────────────────────────────────────
    async function fetchAll() {
        const [workshops, stats, l3Items] = await Promise.all([
            ExploreAPI.workshops.list(_pid),
            ExploreAPI.workshops.stats(_pid).catch(() => ({})),
            ExploreAPI.levels.listL3(_pid).catch(() => []),
        ]);
        _workshops = workshops || [];
        _stats = stats || {};
        _l3Items = l3Items || [];
    }

    // ── Filtering & Sorting ──────────────────────────────────────────
    function getFiltered() {
        let list = [..._workshops];
        if (_filters.status) list = list.filter(w => w.status === _filters.status);
        if (_filters.wave) list = list.filter(w => String(w.wave) === _filters.wave);
        if (_filters.area) list = list.filter(w => (w.process_area || w.area || w.area_code) === _filters.area);
        if (_filters.facilitator) list = list.filter(w => (w.facilitator || w.facilitator_id || '') === _filters.facilitator);
        if (_filters.search) {
            const q = _filters.search.toLowerCase();
            list = list.filter(w =>
                (w.code || '').toLowerCase().includes(q) ||
                (w.name || '').toLowerCase().includes(q) ||
                (w.scope_item_name || '').toLowerCase().includes(q)
            );
        }
        // Sort
        list.sort((a, b) => {
            let va = a[_sortKey] ?? '', vb = b[_sortKey] ?? '';
            if (typeof va === 'string') va = va.toLowerCase();
            if (typeof vb === 'string') vb = vb.toLowerCase();
            if (va < vb) return _sortDir === 'asc' ? -1 : 1;
            if (va > vb) return _sortDir === 'asc' ? 1 : -1;
            return 0;
        });
        return list;
    }

    function getGrouped(list) {
        if (_groupBy === 'none') return { '': list };
        const groups = {};
        list.forEach(w => {
            const key = w[_groupBy] || w[`${_groupBy}_code`] || 'Unassigned';
            if (!groups[key]) groups[key] = [];
            groups[key].push(w);
        });
        return groups;
    }

    // ── KPI Strip (F-016) ────────────────────────────────────────────
    function renderKpiStrip() {
        const total = _workshops.length;
        const draft = _workshops.filter(w => w.status === 'draft').length;
        const scheduled = _workshops.filter(w => w.status === 'scheduled').length;
        const active = _workshops.filter(w => w.status === 'in_progress').length;
        const completed = _workshops.filter(w => w.status === 'completed').length;
        const pct = total ? Math.round(completed / total * 100) : 0;

        const totalOI = _stats.total_open_items || _workshops.reduce((s, w) => s + (w.oi_count || w.open_item_count || 0), 0);
        const totalGaps = _stats.total_gaps || _workshops.reduce((s, w) => s + (w.gap_count || 0), 0);
        return `<div class="exp-kpi-strip">
            ${ExpUI.kpiBlock({ value: total, label: 'Workshops', accent: 'var(--exp-l2, #3b82f6)' })}
            ${ExpUI.kpiBlock({ value: pct, suffix: '%', label: 'Progress', accent: pct >= 80 ? 'var(--exp-fit)' : pct >= 50 ? '#f59e0b' : 'var(--exp-gap)' })}
            ${ExpUI.kpiBlock({ value: active, label: 'Active', accent: '#3b82f6' })}
            ${ExpUI.kpiBlock({ value: totalOI, label: 'Open Items', accent: 'var(--exp-open-item)' })}
            ${ExpUI.kpiBlock({ value: totalGaps, label: 'Gaps', accent: 'var(--exp-gap)' })}
        </div>
        ${ExpUI.metricBar({
            label: 'Workshop Status',
            total: total || 1,
            segments: [
                {value: completed || 0, label: 'Completed', color: 'var(--exp-fit)'},
                {value: active || 0, label: 'Active', color: '#3b82f6'},
                {value: scheduled || 0, label: 'Scheduled', color: '#f59e0b'},
                {value: draft || 0, label: 'Draft', color: '#94a3b8'},
            ],
        })}`;
    }

    // ── Filter Bar (F-015) ───────────────────────────────────────────
    function renderFilterBar() {
        const areas = [...new Set(_workshops.map(w => w.process_area || w.area || w.area_code).filter(Boolean))].sort();
        const waves = [...new Set(_workshops.map(w => w.wave).filter(Boolean))].sort();
        const facilitators = [...new Set(_workshops.map(w => w.facilitator || w.facilitator_id).filter(Boolean))].sort();

        const groupByOpts = ['none','wave','area','facilitator','status'].map(g =>
            `<option value="${g}"${_groupBy === g ? ' selected' : ''}>${g === 'none' ? 'No Grouping' : g.charAt(0).toUpperCase() + g.slice(1)}</option>`
        ).join('');

        return ExpUI.filterBar({
            id: 'workshopFB',
            searchPlaceholder: 'Search workshops…',
            searchValue: _filters.search,
            onSearch: "ExploreWorkshopHubView.setFilter('search',this.value)",
            onChange: "ExploreWorkshopHubView.onFilterBarChange",
            filters: [
                {
                    id: 'status', label: 'Status', icon: '', type: 'single',
                    color: 'var(--exp-partial)',
                    options: [
                        { value: 'draft', label: 'Draft' },
                        { value: 'scheduled', label: 'Scheduled' },
                        { value: 'in_progress', label: 'In Progress' },
                        { value: 'completed', label: 'Completed' },
                    ],
                    selected: _filters.status || '',
                },
                {
                    id: 'area', label: 'Area', icon: '', type: 'single',
                    color: 'var(--exp-l2)',
                    options: areas.map(a => ({ value: a, label: a })),
                    selected: _filters.area || '',
                },
                {
                    id: 'wave', label: 'Wave', icon: '', type: 'single',
                    color: 'var(--exp-l4)',
                    options: waves.map(w => ({ value: String(w), label: `Wave ${w}` })),
                    selected: _filters.wave || '',
                },
                {
                    id: 'facilitator', label: 'Facilitator', icon: '', type: 'single',
                    color: 'var(--exp-requirement)',
                    options: facilitators.map(f => ({ value: f, label: f })),
                    selected: _filters.facilitator || '',
                },
            ],
            actionsHtml: `
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                    <select style="padding:4px 8px;border:1px solid #d1d5db;border-radius:var(--exp-radius-md);font-size:12px" onchange="ExploreWorkshopHubView.setGroupBy(this.value)">
                        ${groupByOpts}
                    </select>
                    <div class="exp-toolbar__group">
                        ${ExpUI.actionButton({ label: 'Table', variant: _viewMode === 'table' ? 'primary' : 'secondary', size: 'sm', onclick: `ExploreWorkshopHubView.setViewMode('table')`, title: 'Table view' })}
                        ${ExpUI.actionButton({ label: 'Kanban', variant: _viewMode === 'kanban' ? 'primary' : 'secondary', size: 'sm', onclick: `ExploreWorkshopHubView.setViewMode('kanban')`, title: 'Kanban view' })}
                        ${ExpUI.actionButton({ label: 'Capacity', variant: _viewMode === 'capacity' ? 'primary' : 'secondary', size: 'sm', onclick: `ExploreWorkshopHubView.setViewMode('capacity')`, title: 'Capacity view' })}
                    </div>
                    ${ExpUI.actionButton({ label: '+ New Workshop', variant: 'primary', size: 'sm', onclick: 'ExploreWorkshopHubView.createWorkshop()' })}
                </div>
            `,
        });
    }

    // ── Workshop Table (F-012) ───────────────────────────────────────
    function renderTable() {
        const filtered = getFiltered();
        const grouped = getGrouped(filtered);
        if (!filtered.length) {
            return `<div class="exp-empty"><div class="exp-empty__icon">-</div><div class="exp-empty__title">No workshops found</div><p class="exp-empty__text">Create your first workshop or adjust filters</p></div>`;
        }

        const sortIcon = (key) => _sortKey === key ? (_sortDir === 'asc' ? ' ▲' : ' ▼') : ' ⇅';
        const th = (label, key) => `<th onclick="ExploreWorkshopHubView.sort('${key}')">${label}<span class="sort-icon${_sortKey === key ? ' sort-icon--active' : ''}">${sortIcon(key)}</span></th>`;

        const header = `<thead><tr>
            ${th('Code','code')}
            ${th('Scope Item','scope_item_name')}
            ${th('Name','name')}
            <th>Area</th>
            <th>Wave</th>
            ${th('Date','scheduled_date')}
            <th>Status</th>
            <th>Facilitator</th>
            <th>Fit</th>
            <th>DEC</th>
            <th>OI</th>
            <th>REQ</th>
        </tr></thead>`;

        let bodyHtml = '';
        for (const [group, items] of Object.entries(grouped)) {
            if (group && _groupBy !== 'none') {
                bodyHtml += `<tr><td colspan="12" style="background:#f1f5f9;font-weight:600;font-size:13px;padding:8px 12px">${esc(group)} (${items.length})</td></tr>`;
            }
            bodyHtml += items.map(w => {
                const fitCounts = { fit: w.fit_count || 0, gap: w.gap_count || 0, partial_fit: w.partial_count || w.partial_fit_count || 0, pending: w.pending_count || 0 };
                return `<tr class="exp-expandable-row" onclick="ExploreWorkshopHubView.openWorkshop('${w.id}')" style="cursor:pointer">
                    <td><code style="font-family:var(--exp-font-mono);font-size:12px">${esc(w.code || '')}</code></td>
                    <td class="exp-truncate" style="max-width:160px">${esc(w.scope_item_name || w.scope_item_code || '')}</td>
                    <td class="exp-truncate" style="max-width:200px">${esc(w.name || '')}</td>
                    <td>${ExpUI.areaPill(w.process_area || w.area || w.area_code || '')}</td>
                    <td>${ExpUI.wavePill(w.wave)}</td>
                    <td style="font-size:12px">${w.scheduled_date ? esc(w.scheduled_date) : '—'}</td>
                    <td>${ExpUI.workshopStatusPill(w.status)}</td>
                    <td style="font-size:12px">${esc(w.facilitator || w.facilitator_id || '—')}</td>
                    <td>${ExpUI.fitBarMini(fitCounts, { height: 4, width: 60 })}</td>
                    <td>${ExpUI.countChip(w.decision_count || 0, { variant: 'decision' })}</td>
                    <td>${ExpUI.countChip(w.oi_count || w.open_item_count || 0, { variant: 'open_item' })}</td>
                    <td>${ExpUI.countChip(w.req_count || w.requirement_count || 0, { variant: 'requirement' })}</td>
                </tr>`;
            }).join('');
        }

        return `<div class="exp-card"><div class="exp-card__body" style="overflow-x:auto">
            <table class="exp-table">${header}<tbody>${bodyHtml}</tbody></table>
        </div></div>`;
    }

    // ── Workshop Kanban (F-013) ──────────────────────────────────────
    function renderKanban() {
        const columns = [
            { key: 'draft',       label: 'Draft',       color: 'var(--exp-ws-draft)' },
            { key: 'scheduled',   label: 'Scheduled',   color: 'var(--exp-ws-scheduled)' },
            { key: 'in_progress', label: 'In Progress', color: 'var(--exp-ws-in-progress)' },
            { key: 'completed',   label: 'Completed',   color: 'var(--exp-ws-completed)' },
        ];
        const filtered = getFiltered();

        return `<div class="exp-kanban">
            ${columns.map(col => {
                const items = filtered.filter(w => w.status === col.key);
                return `<div class="exp-kanban__column">
                    <div class="exp-kanban__col-header">
                        <span style="color:${col.color}">${col.label}</span>
                        <span class="exp-kanban__col-count">${items.length}</span>
                    </div>
                    ${items.length ? items.map(w => renderKanbanCard(w, col.color)).join('') : '<p style="color:var(--sap-text-secondary);text-align:center;font-size:12px;padding:12px">No items</p>'}
                </div>`;
            }).join('')}
        </div>`;
    }

    function renderKanbanCard(w, borderColor) {
        return `<div class="exp-kanban__card" style="border-left-color:${borderColor}" onclick="ExploreWorkshopHubView.openWorkshop('${w.id}')">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
                <code style="font-family:var(--exp-font-mono);font-size:11px;color:var(--sap-text-secondary)">${esc(w.code || '')}</code>
                ${ExpUI.areaPill(w.process_area || w.area || w.area_code || '')}
            </div>
            <div style="font-weight:600;font-size:13px;margin-bottom:6px" class="exp-truncate">${esc(w.name || '')}</div>
            <div style="font-size:12px;color:var(--sap-text-secondary);margin-bottom:8px" class="exp-truncate">${esc(w.scope_item_name || '')}</div>
            <div style="display:flex;gap:4px;flex-wrap:wrap;font-size:11px">
                ${w.wave ? ExpUI.wavePill(w.wave) : ''}
                ${w.facilitator ? `<span style="color:var(--sap-text-secondary)">${esc(w.facilitator)}</span>` : ''}
            </div>
            <div style="display:flex;gap:4px;margin-top:8px">
                ${ExpUI.countChip(w.decision_count || 0, { variant: 'decision', label: 'DEC' })}
                ${ExpUI.countChip(w.oi_count || w.open_item_count || 0, { variant: 'open_item', label: 'OI' })}
                ${ExpUI.countChip(w.req_count || w.requirement_count || 0, { variant: 'requirement', label: 'REQ' })}
            </div>
        </div>`;
    }

    // ── Capacity View (F-014) ────────────────────────────────────────
    function renderCapacityView() {
        const facilitators = [...new Set(_workshops.map(w => w.facilitator).filter(Boolean))].sort();
        if (!facilitators.length) {
            return `<div class="exp-empty"><div class="exp-empty__icon">-</div><div class="exp-empty__title">No facilitators assigned</div></div>`;
        }

        // Get unique ISO weeks
        const weeks = getWeeks();

        return `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:var(--exp-space-md)">
            ${facilitators.map(fac => {
                const facWs = _workshops.filter(w => w.facilitator === fac);
                const active = facWs.filter(w => w.status === 'in_progress' || w.status === 'scheduled').length;
                const completed = facWs.filter(w => w.status === 'completed').length;
                const total = facWs.length;
                const loadPct = total ? Math.min(Math.round(active / Math.max(total, 4) * 100), 100) : 0;
                const loadClass = loadPct >= 80 ? 'over' : loadPct >= 50 ? 'warning' : 'ok';

                return `<div class="exp-card" style="padding:var(--exp-space-lg)">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
                        <div class="exp-attendee__avatar">${esc(fac.charAt(0).toUpperCase())}</div>
                        <div>
                            <div style="font-weight:600">${esc(fac)}</div>
                            <div style="font-size:12px;color:var(--sap-text-secondary)">${total} workshops · ${active} active</div>
                        </div>
                    </div>
                    <div style="margin-bottom:8px">
                        <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px">
                            <span>Load</span>
                            <span style="font-weight:600">${loadPct}%</span>
                        </div>
                        <div class="exp-capacity-bar">
                            <div class="exp-capacity-bar__fill exp-capacity-bar__fill--${loadClass}" style="width:${loadPct}%"></div>
                        </div>
                    </div>
                    ${loadPct >= 80 ? '<div style="font-size:11px;color:var(--exp-gap);font-weight:600">Overloaded</div>' : ''}
                    <div style="display:flex;gap:4px;margin-top:8px">
                        ${ExpUI.countChip(completed, { variant: 'fit', label: 'Done' })}
                        ${ExpUI.countChip(active, { variant: 'pending', label: 'Active' })}
                    </div>
                </div>`;
            }).join('')}
        </div>`;
    }

    function getWeeks() {
        const dates = _workshops.map(w => w.date || w.scheduled_date).filter(Boolean).sort();
        if (!dates.length) return [];
        return [...new Set(dates.map(d => d.substring(0, 10)))].sort();
    }

    // ── Area Milestone Tracker (F-017) ───────────────────────────────
    function renderAreaMilestoneTracker() {
        const areas = [...new Set(_workshops.map(w => w.process_area || w.area || w.area_code).filter(Boolean))].sort();
        if (!areas.length) return '';

        const rows = areas.map(area => {
            const areaWs = _workshops.filter(w => (w.process_area || w.area || w.area_code) === area);
            const total = areaWs.length;
            const completed = areaWs.filter(w => w.status === 'completed').length;
            const l3Ready = areaWs.filter(w => w.status === 'completed' && w.l3_signed_off).length;
            const pct = total ? Math.round(completed / total * 100) : 0;
            const onTrack = pct >= 50;

            const progressDots = areaWs.slice(0, 12).map(w => {
                const colors = { draft: '#94a3b8', scheduled: '#3b82f6', in_progress: '#f59e0b', completed: '#10b981' };
                return `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${colors[w.status] || '#94a3b8'}" title="${esc(w.code || '')} — ${w.status}"></span>`;
            }).join('');

            return `<div style="display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid #f1f5f9">
                <div style="width:60px">${ExpUI.areaPill(area)}</div>
                <div style="display:flex;gap:3px;flex:1">${progressDots}</div>
                <div style="font-size:12px;min-width:60px;text-align:center">${ExpUI.countChip(l3Ready, { variant: 'fit', label: 'L3' })}</div>
                <div style="font-size:12px;min-width:50px;text-align:right;font-weight:600;color:${onTrack ? 'var(--exp-fit)' : 'var(--exp-gap)'}">${onTrack ? 'On Track' : 'Behind'}</div>
            </div>`;
        }).join('');

        return `<div class="exp-card" style="margin-top:var(--exp-space-md)">
            <div class="exp-card__header"><h3 class="exp-card__title">Area Milestone Tracker</h3></div>
            <div class="exp-card__body">${rows}</div>
        </div>`;
    }

    // ── Create Workshop Dialog ───────────────────────────────────────
    function createWorkshop() {
        const areas = [...new Set([
            ..._workshops.map(w => w.process_area || w.area || w.area_code),
            ..._l3Items.map(l3 => l3.process_area_code || l3.area_code),
        ].filter(Boolean))].sort();
        const facilitators = [...new Set(_workshops.map(w => w.facilitator || w.facilitator_id).filter(Boolean))].sort();
        const l3Options = _l3Items
            .map(l3 => ({
                id: l3.id,
                label: `${l3.code || l3.sap_code || ''} ${l3.name || ''}`.trim() || l3.id,
            }))
            .sort((a, b) => a.label.localeCompare(b.label));

        const html = `<div class="modal-content" style="max-width:560px;padding:24px">
            <h2 style="margin-bottom:16px">Create Workshop</h2>
            <div class="exp-inline-form">
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Name</label><input id="wsName" type="text" placeholder="Workshop name"></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Workshop Type</label>
                        <select id="wsType"><option value="initial">Initial</option><option value="delta">Delta</option><option value="review">Review</option></select>
                    </div>
                    <div class="exp-inline-form__field"><label>Scheduled Date</label><input id="wsDate" type="date"></div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Facilitator</label>
                        <select id="wsFacilitator"><option value="">—</option>${facilitators.map(f => `<option value="${esc(f)}">${esc(f)}</option>`).join('')}</select>
                    </div>
                    <div class="exp-inline-form__field"><label>Area</label>
                        <select id="wsArea"><option value="">—</option>${areas.map(a => `<option value="${esc(a)}">${esc(a)}</option>`).join('')}</select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Wave</label><input id="wsWave" type="number" min="1" max="10" placeholder="1"></div>
                    <div class="exp-inline-form__field"><label>L3 Scope Item</label>
                        <select id="wsL3"><option value="">—</option>${l3Options.map(o => `<option value="${o.id}">${esc(o.label)}</option>`).join('')}</select>
                    </div>
                </div>
                <div class="exp-inline-form__row">
                    <div class="exp-inline-form__field"><label>Description</label><textarea id="wsDesc" rows="2" placeholder="Optional description"></textarea></div>
                </div>
            </div>
            <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Create', variant: 'primary', onclick: 'ExploreWorkshopHubView.submitCreate()' })}
            </div>
        </div>`;
        App.openModal(html);
    }

    async function submitCreate() {
        try {
            const scopeItemId = document.getElementById('wsL3')?.value || null;
            const name = document.getElementById('wsName')?.value?.trim();
            const area = document.getElementById('wsArea')?.value || null;
            const waveRaw = document.getElementById('wsWave')?.value;
            const waveVal = waveRaw ? parseInt(waveRaw, 10) : null;
            if (!name) {
                App.toast('Name is required', 'error');
                return;
            }
            if (!area) {
                App.toast('Area is required', 'error');
                return;
            }
            if (waveVal != null && (Number.isNaN(waveVal) || waveVal < 1 || waveVal > 10)) {
                App.toast('Wave must be between 1 and 10', 'error');
                return;
            }
            const data = {
                name,
                type: document.getElementById('wsType')?.value || 'initial',
                date: document.getElementById('wsDate')?.value || null,
                facilitator_id: document.getElementById('wsFacilitator')?.value || null,
                process_area: area,
                wave: waveVal,
                scope_item_ids: scopeItemId ? [scopeItemId] : [],
                notes: document.getElementById('wsDesc')?.value || null,
            };
            await ExploreAPI.workshops.create(_pid, data);
            App.closeModal();
            App.toast('Workshop created', 'success');
            await fetchAll();
            renderPage();
        } catch (err) {
            App.toast(err.message || 'Failed to create workshop', 'error');
        }
    }

    // ── Navigation ───────────────────────────────────────────────────
    function openWorkshop(id) {
        // Store selected workshop ID for detail view
        localStorage.setItem('exp_selected_workshop', id);
        App.navigate('explore-workshop-detail');
    }

    // ── Main Render (F-011) ──────────────────────────────────────────
    function renderPage() {
        const main = document.getElementById('mainContent');
        let content = '';
        switch (_viewMode) {
            case 'table':    content = renderTable(); break;
            case 'kanban':   content = renderKanban(); break;
            case 'capacity': content = renderCapacityView(); break;
        }

        main.innerHTML = `<div class="explore-page">
            <div class="explore-page__header">
                <div>
                    <h1 class="explore-page__title">Workshop Hub</h1>
                    <p class="explore-page__subtitle">Plan, schedule, and track Explore workshops across all scope items</p>
                </div>
            </div>
            ${renderKpiStrip()}
            ${renderFilterBar()}
            ${content}
            ${renderAreaMilestoneTracker()}
        </div>`;
    }

    // ── Public Actions ───────────────────────────────────────────────
    function setViewMode(m) { _viewMode = m; renderPage(); }
    function setFilter(key, val) { _filters[key] = val || ''; _page = 1; renderPage(); }
    function onFilterBarChange(update) {
        if (update._clearAll) {
            _filters = { status: '', wave: '', area: '', facilitator: '', search: _filters.search || '' };
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    _filters[key] = '';
                } else if (Array.isArray(val)) {
                    _filters[key] = val[0];
                } else {
                    _filters[key] = val;
                }
            });
        }
        _page = 1;
        renderPage();
    }
    function setGroupBy(g) { _groupBy = g; renderPage(); }
    function sort(key) {
        if (_sortKey === key) _sortDir = _sortDir === 'asc' ? 'desc' : 'asc';
        else { _sortKey = key; _sortDir = 'asc'; }
        renderPage();
    }

    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        if (!prog) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">-</div><div class="exp-empty__title">Select a program first</div></div>`;
            return;
        }
        _pid = prog.id;
        main.innerHTML = `<div class="explore-page" style="display:flex;align-items:center;justify-content:center;min-height:300px">
            <div style="text-align:center;color:var(--sap-text-secondary)"><div style="font-size:28px;margin-bottom:8px">-</div>Loading workshops…</div>
        </div>`;
        try {
            await fetchAll();
            renderPage();
        } catch (err) {
            main.innerHTML = `<div class="exp-empty"><div class="exp-empty__icon">-</div><div class="exp-empty__title">Error loading workshops</div><p class="exp-empty__text">${esc(err.message)}</p></div>`;
        }
    }

    return {
        render, setViewMode, setFilter, onFilterBarChange, setGroupBy, sort,
        openWorkshop, createWorkshop, submitCreate,
    };
})();
