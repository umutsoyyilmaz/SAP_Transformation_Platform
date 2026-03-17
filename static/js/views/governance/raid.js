/**
 * SAP Transformation Platform — RAID View (Sprint 6)
 *
 * Dashboard with risk heatmap, RAID stats, action aging
 * + tabbed list views (Risks / Actions / Issues / Decisions) with filters
 * + detail modals for create/edit
 */
const RaidView = (() => {
    let _programId = null;
    let _currentTab = 'risks';
    let _allItems = [];
    let _heatmapCells = [];
    let _scopeOptionsCache = {};
    let _tabState = {
        risks: { filters: {}, search: '' },
        actions: { filters: {}, search: '' },
        issues: { filters: {}, search: '' },
        decisions: { filters: {}, search: '' },
    };

    function _stateFor(tab = _currentTab) {
        if (!_tabState[tab]) {
            _tabState[tab] = { filters: {}, search: '' };
        }
        return _tabState[tab];
    }

    function _activeProjectId() {
        if (typeof App.getActiveProject !== 'function') return null;
        return App.getActiveProject()?.id || null;
    }

    function _activeProjectName() {
        if (typeof App.getActiveProject !== 'function') return '';
        return App.getActiveProject()?.name || '';
    }

    function esc(value) {
        const d = document.createElement('div');
        d.textContent = value ?? '';
        return d.innerHTML;
    }

    function _scopedUrl(path) {
        const params = new URLSearchParams();
        const projectId = _activeProjectId();
        if (projectId) params.set('project_id', String(projectId));
        const query = params.toString();
        return query ? `${path}?${query}` : path;
    }

    function _openRaidModal({
        title,
        body,
        footer = '<button class="btn" onclick="App.closeModal()">Close</button>',
        closeAction = 'App.closeModal()',
        modalClass = 'raid-modal',
        testId = '',
    }) {
        const testAttr = testId ? ` data-testid="${esc(testId)}"` : '';
        App.openModal(`
            <div class="modal ${modalClass}"${testAttr}>
                <div class="modal__header">
                    <h3>${esc(title)}</h3>
                    <button class="modal-close" onclick="${closeAction}" title="Close">&times;</button>
                </div>
                <div class="modal__body governance-modal__body">
                    ${body}
                </div>
                <div class="modal__footer governance-modal__footer">
                    ${footer}
                </div>
            </div>
        `);
    }

    async function _loadSetupOptions() {
        const projectId = _activeProjectId();
        const cacheKey = `${_programId || 'na'}:${projectId || 'all'}`;
        if (_scopeOptionsCache[cacheKey]) return _scopeOptionsCache[cacheKey];

        const fetchScoped = async (resource) => {
            const base = `/programs/${_programId}/${resource}`;
            const scopedPath = projectId ? `${base}?project_id=${projectId}` : base;
            let list = [];
            try {
                const res = await API.get(scopedPath);
                list = Array.isArray(res) ? res : [];
            } catch {
                list = [];
            }
            if (projectId && list.length === 0) {
                try {
                    const fallback = await API.get(base);
                    list = Array.isArray(fallback) ? fallback : [];
                } catch {
                    list = [];
                }
            }
            return list;
        };

        const [workstreams, phases] = await Promise.all([
            fetchScoped('workstreams'),
            fetchScoped('phases'),
        ]);

        _scopeOptionsCache[cacheKey] = { workstreams, phases };
        return _scopeOptionsCache[cacheKey];
    }

    function _renderScopeSelect(id, items, selectedId, placeholder) {
        return `
            <select id="${id}" class="form-control">
                <option value="">${placeholder}</option>
                ${(items || []).map((item) => `
                    <option value="${item.id}" ${Number(selectedId) === Number(item.id) ? 'selected' : ''}>
                        ${esc(item.name || item.title || `${item.id}`)}
                    </option>
                `).join('')}
            </select>
        `;
    }

    // ── Main Render ──────────────────────────────────────────────────────
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        _programId = prog ? prog.id : null;
        const activeProject = typeof App.getActiveProject === 'function' ? App.getActiveProject() : null;

        if (!_programId) {
            main.innerHTML = PGEmptyState.html({ icon: 'raid', title: 'RAID Log', description: 'Select a program first to continue.', action: { label: 'Go to Programs', onclick: "App.navigate('programs')" } });
            return;
        }

        main.innerHTML = GovernanceUI.shell({
            current: 'raid',
            testId: 'governance-raid-page',
            breadcrumbs: [{ label: 'Governance' }, { label: 'RAID' }],
            eyebrow: 'Governance',
            title: 'RAID',
            subtitle: 'Program governance cockpit for risks, actions, issues, decisions, and escalation signals.',
            context: {
                program: prog.name,
                project: activeProject?.name || 'All scoped projects',
                status: prog.status || 'active',
                phase: 'Governance cockpit',
            },
            actionsHtml: `
                <div class="workspace-action-buttons">
                    <button class="pg-btn pg-btn--ghost pg-btn--sm" data-testid="raid-ai-risk-trigger" onclick="RaidView.runAIRiskAssessment()">AI Risk Assessment</button>
                    <div class="governance-action-anchor" id="raidNewBtnWrap">
                        ${ExpUI.actionButton({ label: '+ New Entry', variant: 'primary', size: 'md', onclick: 'RaidView.toggleNewMenu()' })}
                        <div class="raid-new-menu" id="raidNewMenu">
                            <div class="raid-new-menu__item" onclick="RaidView.openCreate('risk')">
                                <span class="raid-entry-dot raid-entry-dot--risk"></span> Risk
                            </div>
                            <div class="raid-new-menu__item" onclick="RaidView.openCreate('action')">
                                <span class="raid-entry-dot raid-entry-dot--action"></span> Action
                            </div>
                            <div class="raid-new-menu__item" onclick="RaidView.openCreate('issue')">
                                <span class="raid-entry-dot raid-entry-dot--issue"></span> Issue
                            </div>
                            <div class="raid-new-menu__item" onclick="RaidView.openCreate('decision')">
                                <span class="raid-entry-dot raid-entry-dot--decision"></span> Decision
                            </div>
                        </div>
                    </div>
                </div>
            `,
            bodyHtml: `
                <div class="workspace-section-stack governance-stack">
                    <div class="raid-dash-row" id="raidDashRow">
                        <div id="raidStats"></div>
                        <div class="card governance-panel" id="riskHeatmapCard">
                            <div class="governance-panel__header governance-panel__header--compact">
                                <div>
                                    <div class="governance-panel__eyebrow">Risk signal</div>
                                    <h3 class="governance-panel__title">Risk Heatmap</h3>
                                </div>
                            </div>
                            <div id="riskHeatmap" class="raid-heatmap-wrap"></div>
                        </div>
                    </div>

                    <div class="card governance-panel">
                        <div class="governance-tab-strip" data-testid="governance-raid-tabs">
                            <button class="governance-tab ${_currentTab === 'risks' ? 'governance-tab--active' : ''}" data-tab="risks" onclick="RaidView.switchTab('risks')">
                                <span class="raid-entry-dot raid-entry-dot--risk"></span> Risks
                            </button>
                            <button class="governance-tab ${_currentTab === 'actions' ? 'governance-tab--active' : ''}" data-tab="actions" onclick="RaidView.switchTab('actions')">
                                <span class="raid-entry-dot raid-entry-dot--action"></span> Actions
                            </button>
                            <button class="governance-tab ${_currentTab === 'issues' ? 'governance-tab--active' : ''}" data-tab="issues" onclick="RaidView.switchTab('issues')">
                                <span class="raid-entry-dot raid-entry-dot--issue"></span> Issues
                            </button>
                            <button class="governance-tab ${_currentTab === 'decisions' ? 'governance-tab--active' : ''}" data-tab="decisions" onclick="RaidView.switchTab('decisions')">
                                <span class="raid-entry-dot raid-entry-dot--decision"></span> Decisions
                            </button>
                        </div>
                        <div id="raidFilterBar"></div>
                        <div id="raidListContainer"></div>
                    </div>
                </div>
            `,
        });

        await Promise.all([loadStats(), loadHeatmap(), loadList(_currentTab)]);
    }

    // ── Stats ────────────────────────────────────────────────────────────
    async function loadStats() {
        try {
            const s = await API.get(_scopedUrl(`/programs/${_programId}/raid/stats`));
            document.getElementById('raidStats').innerHTML = `
                <div class="exp-kpi-strip">
                    ${ExpUI.kpiBlock({ value: s.risks.open, label: 'Open Risks', accent: '#dc2626', sub: s.risks.critical > 0 ? s.risks.critical + ' critical' : '' })}
                    ${ExpUI.kpiBlock({ value: s.actions.open, label: 'Open Actions', accent: '#3b82f6', sub: s.actions.overdue > 0 ? s.actions.overdue + ' overdue' : '' })}
                    ${ExpUI.kpiBlock({ value: s.issues.open, label: 'Open Issues', accent: '#f59e0b', sub: s.issues.critical > 0 ? s.issues.critical + ' critical' : '' })}
                    ${ExpUI.kpiBlock({ value: s.decisions.pending, label: 'Pending Decisions', accent: '#8b5cf6', sub: s.decisions.total + ' total' })}
                </div>
            `;
        } catch (e) {
            document.getElementById('raidStats').innerHTML =
                `<p class="text-muted">⚠️ Stats unavailable</p>`;
        }
    }

    // ── Heatmap ──────────────────────────────────────────────────────────
    async function loadHeatmap() {
        try {
            const h = await API.get(_scopedUrl(`/programs/${_programId}/raid/heatmap`));
            const impLabels = ['Neg', 'Min', 'Mod', 'Maj', 'Sev'];
            const probLabels = ['VL', 'Low', 'Med', 'High', 'VH'];
            _heatmapCells = [];

            let html = '<table class="heatmap-table heatmap-table--compact"><thead><tr><th></th>';
            impLabels.forEach(l => { html += `<th>${l}</th>`; });
            html += '</tr></thead><tbody>';

            for (let p = 4; p >= 0; p--) {
                html += `<tr><th>${probLabels[p]}</th>`;
                for (let i = 0; i < 5; i++) {
                    const cell = h.matrix[p][i];
                    const score = (p + 1) * (i + 1);
                    const bg = score <= 3 ? '#dcfce7'
                        : score <= 6 ? '#fef9c3'
                        : score <= 12 ? '#fed7aa'
                        : score <= 16 ? '#fecaca'
                        : '#fca5a5';

                    const hasRisks = cell.length > 0;
                    const cellIndex = hasRisks ? _heatmapCells.push(cell) - 1 : -1;
                    const bucketClass = score <= 3 ? 'heatmap-cell--safe'
                        : score <= 6 ? 'heatmap-cell--watch'
                        : score <= 12 ? 'heatmap-cell--high'
                        : score <= 16 ? 'heatmap-cell--critical'
                        : 'heatmap-cell--extreme';

                    html += `<td class="heatmap-cell ${bucketClass}${hasRisks ? ' heatmap-cell--clickable' : ''}"
                              title="${hasRisks ? cell.map(r => r.code + ': ' + r.title).join('\n') : 'Score: ' + score}"
                              ${hasRisks ? `onclick="RaidView.showHeatmapCellByIndex(${cellIndex})"` : ''}>
                        ${hasRisks ? `<span class="heatmap-cell__count">${cell.length}</span>` : ''}
                    </td>`;
                }
                html += '</tr>';
            }
            html += '</tbody></table>';
            document.getElementById('riskHeatmap').innerHTML = html;
        } catch (e) {
            document.getElementById('riskHeatmap').innerHTML =
                `<p class="text-muted">No heatmap data</p>`;
        }
    }

    function toggleNewMenu() {
        const menu = document.getElementById('raidNewMenu');
        if (!menu) return;
        const isOpen = menu.classList.contains('raid-new-menu--open');
        menu.classList.toggle('raid-new-menu--open', !isOpen);
        if (!isOpen) {
            setTimeout(() => {
                const handler = (e) => {
                    if (!e.target.closest('#raidNewBtnWrap')) {
                        menu.classList.remove('raid-new-menu--open');
                        document.removeEventListener('click', handler);
                    }
                };
                document.addEventListener('click', handler);
            }, 10);
        }
    }

    function showHeatmapCell(risks) {
        _openRaidModal({
            title: 'Risks in Cell',
            testId: 'raid-heatmap-cell-modal',
            body: `
                <div class="raid-modal__table-wrap">
                    <table class="data-table" aria-label="Risks in selected heatmap cell">
                        <thead><tr><th>Code</th><th>Title</th><th>RAG</th></tr></thead>
                        <tbody>${risks.map(r => `<tr><td>${r.code}</td><td>${r.title}</td><td>${PGStatusRegistry.badge(r.rag_status)}</td></tr>`).join('')}</tbody>
                    </table>
                </div>
            `,
        });
    }

    function showHeatmapCellByIndex(index) {
        showHeatmapCell(_heatmapCells[index] || []);
    }

    function _renderAIListSection(title, items, renderItem) {
        const list = Array.isArray(items) ? items.filter(Boolean) : [];
        if (!list.length) return '';
        return `
            <div class="raid-ai-section">
                <h3 class="raid-ai-section__title">${esc(title)}</h3>
                <div class="raid-ai-list">
                    ${list.map((item) => `
                        <div class="raid-ai-card">
                            ${renderItem(item)}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    function _formatSignalValue(value) {
        if (value == null) return '—';
        if (typeof value === 'object') return esc(JSON.stringify(value));
        return esc(String(value));
    }

    function _renderRiskAssessmentResult(data) {
        const risks = Array.isArray(data.risks) ? data.risks : [];
        const signalRows = Object.entries(data.signal_summary || {}).map(([key, value]) => `
            <tr>
                <td class="raid-ai-signal-table__key">${esc(key)}</td>
                <td>${_formatSignalValue(value)}</td>
            </tr>
        `).join('');
        return `
            <div class="raid-ai-summary-row">
                ${PGStatusRegistry.badge('ai', { label: `${risks.length} risks identified` })}
                ${data.suggestion_ids?.length ? PGStatusRegistry.badge('pending', { label: `${data.suggestion_ids.length} suggestions` }) : ''}
            </div>
            ${signalRows ? `
                <div class="raid-ai-section">
                    <h3 class="raid-ai-section__title">Signal Summary</h3>
                    <table class="data-table raid-ai-signal-table">
                        <thead><tr><th>Signal</th><th>Value</th></tr></thead>
                        <tbody>${signalRows}</tbody>
                    </table>
                </div>
            ` : ''}
            ${_renderAIListSection('AI Risks', risks, (risk) => {
                const title = risk.title || risk.name || 'Untitled risk';
                const severity = risk.severity || risk.priority || risk.rag_status || 'unknown';
                const probability = risk.probability != null ? `Probability: ${risk.probability}` : '';
                const impact = risk.impact != null ? `Impact: ${risk.impact}` : '';
                const conf = risk.confidence != null ? `Confidence: ${Math.round(risk.confidence * 100)}%` : '';
                const meta = [probability, impact, conf].filter(Boolean).join(' · ');
                return `
                    <div class="raid-ai-risk-card__header">
                        <strong>${esc(title)}</strong>
                        ${PGStatusRegistry.badge(severity, { label: esc(String(severity).replace(/_/g, ' ')) })}
                    </div>
                    ${meta ? `<div class="raid-ai-risk-card__meta">${esc(meta)}</div>` : ''}
                    <div class="raid-ai-risk-card__body">${esc(risk.description || risk.reasoning || risk.mitigation || '')}</div>
                `;
            })}
            ${!risks.length && !data.error ? '<div class="empty-state raid-ai-empty"><p>No new AI risks identified.</p></div>' : ''}
        `;
    }

    async function runAIRiskAssessment() {
        if (!_programId) return;
        _openRaidModal({
            title: 'AI Risk Assessment',
            testId: 'raid-ai-risk-modal',
            modalClass: 'raid-modal raid-ai-modal',
            body: `
                <div id="raidAiRiskResult" class="raid-ai-result">
                    <div class="spinner"></div>
                </div>
            `,
            footer: `
                <button class="btn btn-secondary btn-sm" onclick="App.closeModal()">Close</button>
            `,
        });

        const container = document.getElementById('raidAiRiskResult');
        if (!container) return;

        try {
            const data = await API.post(`/ai/assess/risk/${_programId}`, {
                create_suggestion: true,
            });
            container.innerHTML = _renderRiskAssessmentResult(data);
        } catch (err) {
            container.innerHTML = `<div class="empty-state raid-ai-empty"><p>⚠️ ${esc(err.message)}</p></div>`;
        }
    }

    // ── List Views ───────────────────────────────────────────────────────
    function switchTab(tab) {
        _currentTab = tab;
        document.querySelectorAll('.tabs .tab-btn').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        loadList(tab);
    }

    async function loadList(tab) {
        const container = document.getElementById('raidListContainer');
        try {
            let items = [];
            if (tab === 'risks') items = await API.get(_scopedUrl(`/programs/${_programId}/risks`));
            else if (tab === 'actions') items = await API.get(_scopedUrl(`/programs/${_programId}/actions`));
            else if (tab === 'issues') items = await API.get(_scopedUrl(`/programs/${_programId}/issues`));
            else if (tab === 'decisions') items = await API.get(_scopedUrl(`/programs/${_programId}/decisions`));

            _allItems = Array.isArray(items) ? items : (items.items || []);
            renderFilterBar(tab);

            if (!_allItems.length) {
                container.innerHTML = PGEmptyState.html({ icon: 'raid', title: `No ${tab.charAt(0).toUpperCase() + tab.slice(1)} found` });
                return;
            }
            container.innerHTML = renderTable(tab, _allItems);
            const countEl = document.getElementById('raidItemCount');
            if (countEl) countEl.textContent = `${_allItems.length} items`;
        } catch (e) {
            container.innerHTML = `<div class="empty-state"><p>⚠️ ${e.message}</p></div>`;
        }
    }

    function renderFilterBar(tab) {
        const tabState = _stateFor(tab);
        const filterDefs = {
            risks: [
                { id: 'status', label: 'Status', icon: '📋', type: 'multi',
                    options: [
                        { value: 'identified', label: 'Identified' },
                        { value: 'analysed', label: 'Analysed' },
                        { value: 'mitigating', label: 'Mitigating' },
                        { value: 'closed', label: 'Closed' },
                        { value: 'accepted', label: 'Accepted' },
                    ],
                    selected: tabState.filters.status || [], color: '#3b82f6',
                },
                { id: 'priority', label: 'Priority', icon: '⚡', type: 'multi',
                    options: [
                        { value: 'critical', label: 'Critical' },
                        { value: 'high', label: 'High' },
                        { value: 'medium', label: 'Medium' },
                        { value: 'low', label: 'Low' },
                    ],
                    selected: tabState.filters.priority || [], color: '#dc2626',
                },
                { id: 'rag_status', label: 'RAG', icon: '🚦', type: 'single',
                    options: [
                        { value: 'red', label: '🔴 Red' },
                        { value: 'orange', label: '🟠 Orange' },
                        { value: 'amber', label: '🟡 Amber' },
                        { value: 'green', label: '🟢 Green' },
                    ],
                    selected: tabState.filters.rag_status || '', color: '#f59e0b',
                },
            ],
            actions: [
                { id: 'status', label: 'Status', icon: '📋', type: 'multi',
                    options: [
                        { value: 'open', label: 'Open' },
                        { value: 'in_progress', label: 'In Progress' },
                        { value: 'completed', label: 'Completed' },
                        { value: 'cancelled', label: 'Cancelled' },
                    ],
                    selected: tabState.filters.status || [], color: '#3b82f6',
                },
                { id: 'priority', label: 'Priority', icon: '⚡', type: 'multi',
                    options: [
                        { value: 'critical', label: 'Critical' },
                        { value: 'high', label: 'High' },
                        { value: 'medium', label: 'Medium' },
                        { value: 'low', label: 'Low' },
                    ],
                    selected: tabState.filters.priority || [], color: '#dc2626',
                },
                { id: 'action_type', label: 'Type', icon: '🔧', type: 'multi',
                    options: [
                        { value: 'preventive', label: 'Preventive' },
                        { value: 'corrective', label: 'Corrective' },
                        { value: 'detective', label: 'Detective' },
                        { value: 'improvement', label: 'Improvement' },
                    ],
                    selected: tabState.filters.action_type || [], color: '#8b5cf6',
                },
            ],
            issues: [
                { id: 'status', label: 'Status', icon: '📋', type: 'multi',
                    options: [
                        { value: 'open', label: 'Open' },
                        { value: 'in_progress', label: 'In Progress' },
                        { value: 'resolved', label: 'Resolved' },
                        { value: 'closed', label: 'Closed' },
                    ],
                    selected: tabState.filters.status || [], color: '#f59e0b',
                },
                { id: 'severity', label: 'Severity', icon: '🔥', type: 'multi',
                    options: [
                        { value: 'critical', label: 'Critical' },
                        { value: 'major', label: 'Major' },
                        { value: 'moderate', label: 'Moderate' },
                        { value: 'minor', label: 'Minor' },
                    ],
                    selected: tabState.filters.severity || [], color: '#dc2626',
                },
            ],
            decisions: [
                { id: 'status', label: 'Status', icon: '📋', type: 'multi',
                    options: [
                        { value: 'pending', label: 'Pending' },
                        { value: 'approved', label: 'Approved' },
                        { value: 'rejected', label: 'Rejected' },
                        { value: 'deferred', label: 'Deferred' },
                    ],
                    selected: tabState.filters.status || [], color: '#8b5cf6',
                },
            ],
        };

        const fbContainer = document.getElementById('raidFilterBar');
        if (!fbContainer) return;
        fbContainer.innerHTML = ExpUI.filterBar({
            id: 'raidFB',
            searchPlaceholder: `Search ${tab}…`,
            searchValue: tabState.search,
            onSearch: "RaidView.setSearch(this.value)",
            onChange: "RaidView.onFilterBarChange",
            filters: filterDefs[tab] || [],
            actionsHtml: `
                <span class="raid-filter-count" id="raidItemCount"></span>
            `,
        });
    }

    function setSearch(val) {
        _stateFor().search = val;
        applyFiltersAndRender();
    }

    function onFilterBarChange(update) {
        const tabState = _stateFor();
        if (update._clearAll) {
            tabState.filters = {};
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    delete tabState.filters[key];
                } else {
                    tabState.filters[key] = val;
                }
            });
        }
        renderFilterBar(_currentTab);
        applyFiltersAndRender();
    }

    function applyFiltersAndRender() {
        const tabState = _stateFor();
        let items = [..._allItems];

        if (tabState.search) {
            const q = tabState.search.toLowerCase();
            items = items.filter(it =>
                (it.title || '').toLowerCase().includes(q) ||
                (it.code || '').toLowerCase().includes(q) ||
                (it.owner || '').toLowerCase().includes(q) ||
                (it.description || '').toLowerCase().includes(q)
            );
        }

        Object.entries(tabState.filters).forEach(([key, val]) => {
            if (!val) return;
            const values = Array.isArray(val) ? val : [val];
            if (!values.length) return;
            items = items.filter(it => values.includes(String(it[key])));
        });

        const container = document.getElementById('raidListContainer');
        const countEl = document.getElementById('raidItemCount');
        if (countEl) countEl.textContent = `${items.length} of ${_allItems.length}`;

        if (!items.length) {
            container.innerHTML = PGEmptyState.html({ icon: 'raid', title: `No ${_currentTab} matching the filter` });
            return;
        }
        container.innerHTML = renderTable(_currentTab, items);
    }

    function renderTable(tab, items) {
        const ragDot = (rag) => {
            const labels = { red: 'Critical', orange: 'High', amber: 'Medium', green: 'Low' };
            return `<span class="raid-rag">
                <span class="raid-rag__dot raid-rag__dot--${rag || 'neutral'}"></span>
                <span class="raid-rag__label">${labels[rag] || rag || '—'}</span>
            </span>`;
        };

        const scoreBadge = (score) => {
            if (score == null) return '—';
            const bucket = score >= 16 ? 'critical' : score >= 10 ? 'warning' : score >= 5 ? 'healthy' : 'neutral';
            return `<span class="raid-score-badge raid-score-badge--${bucket}">${score}</span>`;
        };

        const statusBadge = (status) => PGStatusRegistry.badge(status);
        const priorityBadge = (priority) => PGStatusRegistry.badge(priority);
        const codeCell = (value) => `<code class="raid-code-cell">${value}</code>`;
        const titleCell = (value) => `<span class="raid-title-cell">${value}</span>`;
        const ownerCell = (value) => `<span class="raid-owner-cell">${value || '—'}</span>`;
        const dueCell = (value) => {
            if (!value) return '—';
            const isOverdue = new Date(value) < new Date();
            return `<span class="raid-date-cell${isOverdue ? ' raid-date-cell--overdue' : ''}">${value}</span>`;
        };

        const colDefs = {
            risks: [
                { key: 'code', label: 'Code', widthClass: 'raid-data-table__col--code', render: codeCell },
                { key: 'title', label: 'Title', render: titleCell },
                { key: 'status', label: 'Status', widthClass: 'raid-data-table__col--status', render: statusBadge },
                { key: 'priority', label: 'Priority', widthClass: 'raid-data-table__col--priority', render: priorityBadge },
                { key: 'risk_score', label: 'Score', widthClass: 'raid-data-table__col--score', render: scoreBadge },
                { key: 'rag_status', label: 'RAG', widthClass: 'raid-data-table__col--rag', render: ragDot },
                { key: 'owner', label: 'Owner', widthClass: 'raid-data-table__col--owner', render: ownerCell },
            ],
            actions: [
                { key: 'code', label: 'Code', widthClass: 'raid-data-table__col--code', render: codeCell },
                { key: 'title', label: 'Title', render: titleCell },
                { key: 'status', label: 'Status', widthClass: 'raid-data-table__col--status', render: statusBadge },
                { key: 'priority', label: 'Priority', widthClass: 'raid-data-table__col--priority', render: priorityBadge },
                { key: 'action_type', label: 'Type', widthClass: 'raid-data-table__col--type', render: v => statusBadge(v) },
                { key: 'due_date', label: 'Due', widthClass: 'raid-data-table__col--due', render: dueCell },
                { key: 'owner', label: 'Owner', widthClass: 'raid-data-table__col--owner', render: ownerCell },
            ],
            issues: [
                { key: 'code', label: 'Code', widthClass: 'raid-data-table__col--code', render: codeCell },
                { key: 'title', label: 'Title', render: titleCell },
                { key: 'status', label: 'Status', widthClass: 'raid-data-table__col--status', render: statusBadge },
                { key: 'severity', label: 'Severity', widthClass: 'raid-data-table__col--severity', render: priorityBadge },
                { key: 'priority', label: 'Priority', widthClass: 'raid-data-table__col--priority', render: priorityBadge },
                { key: 'owner', label: 'Owner', widthClass: 'raid-data-table__col--owner', render: ownerCell },
            ],
            decisions: [
                { key: 'code', label: 'Code', widthClass: 'raid-data-table__col--code', render: codeCell },
                { key: 'title', label: 'Title', render: titleCell },
                { key: 'status', label: 'Status', widthClass: 'raid-data-table__col--status', render: statusBadge },
                { key: 'priority', label: 'Priority', widthClass: 'raid-data-table__col--priority', render: priorityBadge },
                { key: 'decision_owner', label: 'Owner', widthClass: 'raid-data-table__col--owner', render: ownerCell },
                { key: 'reversible', label: 'Reversible', widthClass: 'raid-data-table__col--reversible', render: v => v ? '✅' : '❌' },
            ],
        };

        const cols = colDefs[tab] || colDefs.risks;
        let html = '<table class="data-table raid-data-table"><thead><tr>';
        cols.forEach(c => {
            html += `<th${c.widthClass ? ` class="${c.widthClass}"` : ''}>${c.label}</th>`;
        });
        html += '<th class="raid-data-table__actions"></th></tr></thead><tbody>';

        items.forEach(item => {
            html += `<tr class="raid-data-table__row" onclick="RaidView.openDetail('${tab}', ${item.id})">`;
            cols.forEach(c => {
                html += `<td>${c.render(item[c.key])}</td>`;
            });
            html += `<td class="raid-data-table__actions" onclick="event.stopPropagation()">
                <button class="btn-icon" onclick="RaidView.openEdit('${tab}', ${item.id})" title="Edit">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
                </button>
                <button class="btn-icon btn-icon--danger" onclick="RaidView.deleteItem('${tab}', ${item.id})" title="Delete">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
                </button>
            </td></tr>`;
        });
        html += '</tbody></table>';
        return html;
    }

    // ── Detail Modal ─────────────────────────────────────────────────────
    async function openDetail(tab, id) {
        const singular = tab.slice(0, -1);  // risks → risk
        try {
            const item = await API.get(`/${tab}/${id}`);
            const fields = Object.entries(item)
                .filter(([k]) => !['id', 'raid_type', 'program_id'].includes(k))
                .map(([k, v]) => {
                    const label = k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    return `<tr><td><strong>${label}</strong></td><td>${v ?? '-'}</td></tr>`;
                }).join('');

            _openRaidModal({
                title: `${item.code} — ${item.title}`,
                testId: 'raid-detail-modal',
                body: `<table class="data-table" aria-label="RAID item details">${fields}</table>`,
                footer: `
                    <button class="btn btn-primary" onclick="RaidView.openEdit('${tab}', ${id})">Edit</button>
                    <button class="btn" onclick="App.closeModal()">Close</button>
                `,
            });
        } catch (e) {
            App.toast(`Error loading ${singular}: ${e.message}`, 'error');
        }
    }

    // ── Create / Edit Forms ──────────────────────────────────────────────
    async function openCreate(type) {
        const title = type.charAt(0).toUpperCase() + type.slice(1);
        const formHtml = await _getForm(type, {});
        _openRaidModal({
            title: `New ${title}`,
            testId: 'raid-create-modal',
            body: formHtml,
            footer: `
                <button class="btn btn-primary" onclick="RaidView.submitCreate('${type}')">Create</button>
                <button class="btn" onclick="App.closeModal()">Cancel</button>
            `,
        });
    }

    async function openEdit(tab, id) {
        const singular = tab.slice(0, -1);
        try {
            const item = await API.get(`/${tab}/${id}`);
            const formHtml = await _getForm(singular, item);
            _openRaidModal({
                title: `Edit ${item.code}`,
                testId: 'raid-edit-modal',
                body: formHtml,
                footer: `
                    <button class="btn btn-primary" onclick="RaidView.submitEdit('${tab}', ${id})">Save</button>
                    <button class="btn" onclick="App.closeModal()">Cancel</button>
                `,
            });
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function _getForm(type, data) {
        const v = (k) => data[k] || '';
        const members = await TeamMemberPicker.fetchMembers(_programId);
        const { workstreams, phases } = await _loadSetupOptions();
        const ownerHtml = TeamMemberPicker.renderSelect('rf_owner', members, data.owner_id || data.owner || '', { cssClass: 'form-control' });
        let common = `
            <div class="form-group"><label>Title *</label>
                <input id="rf_title" class="form-control" value="${v('title')}" required></div>
            <div class="form-group"><label>Description</label>
                <textarea id="rf_description" class="form-control" rows="3">${v('description')}</textarea></div>
            <div class="form-row">
                <div class="form-group"><label>Owner</label>
                    ${ownerHtml}</div>
                <div class="form-group"><label>Priority</label>
                    <select id="rf_priority" class="form-control">
                        ${['low', 'medium', 'high', 'critical'].map(p =>
                            `<option value="${p}" ${v('priority') === p ? 'selected' : ''}>${p}</option>`
                        ).join('')}
                    </select></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Workstream</label>
                    ${_renderScopeSelect('rf_workstream_id', workstreams, data.workstream_id, '— Select Workstream —')}</div>
                <div class="form-group"><label>Phase</label>
                    ${_renderScopeSelect('rf_phase_id', phases, data.phase_id, '— Select Phase —')}</div>
            </div>
            ${_activeProjectId() ? `<div class="form-hint raid-project-scope-hint">Scoped to project: ${esc(_activeProjectName())}</div>` : ''}
        `;

        if (type === 'risk') {
            common += `
                <div class="form-row">
                    <div class="form-group"><label>Probability (1-5)</label>
                        <input id="rf_probability" type="number" min="1" max="5" class="form-control" value="${data.probability || 3}"></div>
                    <div class="form-group"><label>Impact (1-5)</label>
                        <input id="rf_impact" type="number" min="1" max="5" class="form-control" value="${data.impact || 3}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Category</label>
                        <select id="rf_risk_category" class="form-control">
                            ${['technical', 'organisational', 'commercial', 'external', 'schedule', 'resource', 'scope'].map(c =>
                                `<option value="${c}" ${v('risk_category') === c ? 'selected' : ''}>${c}</option>`
                            ).join('')}
                        </select></div>
                    <div class="form-group"><label>Response</label>
                        <select id="rf_risk_response" class="form-control">
                            ${['avoid', 'transfer', 'mitigate', 'accept', 'escalate'].map(r =>
                                `<option value="${r}" ${v('risk_response') === r ? 'selected' : ''}>${r}</option>`
                            ).join('')}
                        </select></div>
                </div>
                <div class="form-group"><label>Mitigation Plan</label>
                    <textarea id="rf_mitigation_plan" class="form-control" rows="2">${v('mitigation_plan')}</textarea></div>
                <div class="form-group"><label>Contingency Plan</label>
                    <textarea id="rf_contingency_plan" class="form-control" rows="2">${v('contingency_plan')}</textarea></div>
            `;
        } else if (type === 'action') {
            common += `
                <div class="form-row">
                    <div class="form-group"><label>Due Date</label>
                        <input id="rf_due_date" type="date" class="form-control" value="${v('due_date')}"></div>
                    <div class="form-group"><label>Type</label>
                        <select id="rf_action_type" class="form-control">
                            ${['preventive', 'corrective', 'detective', 'improvement', 'follow_up'].map(t =>
                                `<option value="${t}" ${v('action_type') === t ? 'selected' : ''}>${t}</option>`
                            ).join('')}
                        </select></div>
                </div>
            `;
        } else if (type === 'issue') {
            common += `
                <div class="form-row">
                    <div class="form-group"><label>Severity</label>
                        <select id="rf_severity" class="form-control">
                            ${['minor', 'moderate', 'major', 'critical'].map(s =>
                                `<option value="${s}" ${v('severity') === s ? 'selected' : ''}>${s}</option>`
                            ).join('')}
                        </select></div>
                    <div class="form-group"><label>Escalation Path</label>
                        <input id="rf_escalation_path" class="form-control" value="${v('escalation_path')}"></div>
                </div>
                <div class="form-group"><label>Root Cause</label>
                    <textarea id="rf_root_cause" class="form-control" rows="2">${v('root_cause')}</textarea></div>
            `;
        } else if (type === 'decision') {
            const decisionOwnerHtml = TeamMemberPicker.renderSelect('rf_decision_owner', members, data.decision_owner_id || data.decision_owner || '', { cssClass: 'form-control' });
            common += `
                <div class="form-group"><label>Decision Owner</label>
                    ${decisionOwnerHtml}</div>
                <div class="form-group"><label>Alternatives</label>
                    <textarea id="rf_alternatives" class="form-control" rows="2">${v('alternatives')}</textarea></div>
                <div class="form-group"><label>Rationale</label>
                    <textarea id="rf_rationale" class="form-control" rows="2">${v('rationale')}</textarea></div>
                <div class="form-group"><label>Reversible</label>
                    <select id="rf_reversible" class="form-control">
                        <option value="true" ${data.reversible !== false ? 'selected' : ''}>Yes</option>
                        <option value="false" ${data.reversible === false ? 'selected' : ''}>No</option>
                    </select></div>
            `;
        }
        return common;
    }

    function _collectFormData(type) {
        const projectId = _activeProjectId();
        const workstreamId = document.getElementById('rf_workstream_id')?.value || '';
        const phaseId = document.getElementById('rf_phase_id')?.value || '';
        const data = {
            title: document.getElementById('rf_title')?.value || '',
            description: document.getElementById('rf_description')?.value || '',
            owner: document.getElementById('rf_owner')?.value || '',
            owner_id: document.getElementById('rf_owner')?.value || null,
            priority: document.getElementById('rf_priority')?.value || 'medium',
            project_id: projectId || null,
            workstream_id: workstreamId ? parseInt(workstreamId, 10) : null,
            phase_id: phaseId ? parseInt(phaseId, 10) : null,
        };
        if (type === 'risk') {
            data.probability = parseInt(document.getElementById('rf_probability')?.value) || 3;
            data.impact = parseInt(document.getElementById('rf_impact')?.value) || 3;
            data.risk_category = document.getElementById('rf_risk_category')?.value || 'technical';
            data.risk_response = document.getElementById('rf_risk_response')?.value || 'mitigate';
            data.mitigation_plan = document.getElementById('rf_mitigation_plan')?.value || '';
            data.contingency_plan = document.getElementById('rf_contingency_plan')?.value || '';
        } else if (type === 'action') {
            data.due_date = document.getElementById('rf_due_date')?.value || null;
            data.action_type = document.getElementById('rf_action_type')?.value || 'corrective';
        } else if (type === 'issue') {
            data.severity = document.getElementById('rf_severity')?.value || 'moderate';
            data.escalation_path = document.getElementById('rf_escalation_path')?.value || '';
            data.root_cause = document.getElementById('rf_root_cause')?.value || '';
        } else if (type === 'decision') {
            data.decision_owner = document.getElementById('rf_decision_owner')?.value || '';
            data.decision_owner_id = document.getElementById('rf_decision_owner')?.value || null;
            data.alternatives = document.getElementById('rf_alternatives')?.value || '';
            data.rationale = document.getElementById('rf_rationale')?.value || '';
            data.reversible = document.getElementById('rf_reversible')?.value === 'true';
        }
        return data;
    }

    async function submitCreate(type) {
        const data = _collectFormData(type);
        if (!data.title) { App.toast('Title is required', 'error'); return; }
        try {
            await API.post(`/programs/${_programId}/${type}s`, data);
            App.closeModal();
            App.toast(`${type} created`, 'success');
            render();
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function submitEdit(tab, id) {
        const singular = tab.slice(0, -1);
        const data = _collectFormData(singular);
        if (!data.title) { App.toast('Title is required', 'error'); return; }
        try {
            await API.put(`/${tab}/${id}`, data);
            App.closeModal();
            App.toast(`${singular} updated`, 'success');
            render();
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    async function deleteItem(tab, id) {
        _openRaidModal({
            title: `Delete ${tab.slice(0, -1)}`,
            testId: 'raid-delete-modal',
            body: `<p class="raid-delete-intro">Delete this ${esc(tab.slice(0, -1))}? This action cannot be undone.</p>`,
            footer: `
                <button class="btn btn-danger" data-testid="raid-delete-confirm" onclick="RaidView.deleteItemConfirmed('${tab}', ${id})">Delete</button>
                <button class="btn" onclick="App.closeModal()">Cancel</button>
            `,
        });
    }

    async function deleteItemConfirmed(tab, id) {
        try {
            await API.delete(`/${tab}/${id}`);
            App.closeModal();
            App.toast('Deleted', 'success');
            loadList(_currentTab);
            loadStats();
        } catch (e) {
            App.toast(`Error: ${e.message}`, 'error');
        }
    }

    // ── RAID Type Badge ──────────────────────────────────────────────────
    function _raidTypeBadge(type) {
        const LABELS = { R: 'Risk', A: 'Assumption', I: 'Issue', D: 'Dependency' };
        const KEYS   = { R: 'risk', A: 'assumption', I: 'issue', D: 'dependency' };
        return PGStatusRegistry.badge(KEYS[type] || type, { label: LABELS[type] || type });
    }

    // ── Public API ───────────────────────────────────────────────────────
    return {
        render, switchTab, openDetail, openCreate, openEdit,
        submitCreate, submitEdit, deleteItem, deleteItemConfirmed, showHeatmapCell,
        showHeatmapCellByIndex, toggleNewMenu, setSearch, onFilterBarChange,
        runAIRiskAssessment,
        _raidTypeBadge,
    };
})();
