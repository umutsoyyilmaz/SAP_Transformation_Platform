/**
 * SAP Transformation Management Platform
 * Project Setup View — Professional UI (v2).
 */

const ProjectSetupView = (() => {
    'use strict';

    const esc = ExpUI.esc;

    let _pid = null;
    let _currentTab = 'project-info';
    let _activeProgram = null;
    let _activeProject = null;
    let _programProjects = [];
    let _programDetail = null;
    let _viewMode = 'tree';
    let _tree = [];
    let _flatList = [];
    let _expandedNodes = new Set();
    let _searchQuery = '';
    let _filters = { area: null, scope: null };
    let _l1List = [];
    let _l2List = [];
    let _l3List = [];
    let _l4List = [];
    let _bulkMode = 'grid';
    let _gridRows = [];
    let _pasteText = '';
    let _parsedRows = [];

    const MODULES = ['FI', 'CO', 'MM', 'SD', 'PP', 'QM', 'EWM', 'HR', 'BC'];

    const TEMPLATE_L1 = [
        { code: 'L1-OTC', name: 'Order to Cash', module: 'SD', desc: 'End-to-end sales processes', stats: '2 L2 · 10 L3 · 40 L4' },
        { code: 'L1-PTP', name: 'Procure to Pay', module: 'MM', desc: 'Procurement and invoice cycle', stats: '2 L2 · 10 L3 · 40 L4' },
        { code: 'L1-RTR', name: 'Record to Report', module: 'FI', desc: 'Financial close and reporting', stats: '2 L2 · 10 L3 · 40 L4' },
        { code: 'L1-PTD', name: 'Plan to Deliver', module: 'PP', desc: 'Production planning and delivery', stats: '2 L2 · 10 L3 · 40 L4' },
        { code: 'L1-HCM', name: 'Hire to Retire', module: 'HR', desc: 'Talent lifecycle and payroll', stats: '2 L2 · 10 L3 · 40 L4' },
    ];

    function render() {
        _activeProgram = App.getActiveProgram();
        _activeProject = App.getActiveProject();
        _pid = _activeProgram ? _activeProgram.id : null;
        const main = document.getElementById('mainContent');

        if (!_pid) {
            main.innerHTML = PGEmptyState.html({
                icon: 'settings',
                title: 'Project Setup',
                description: 'Select a program first to continue.',
                action: { label: 'Go to Programs', onclick: "App.navigate('programs')" },
            });
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Program Management' }, { label: 'Project Setup' }])}
                <h2 class="pg-view-title">Project Setup</h2>
                <p style="font-size:13px;color:var(--pg-color-text-secondary)">Program selected, project-specific setup tabs below</p>
            </div>
            <div id="projectSetupContextCard" class="card" style="margin-bottom:16px;padding:12px 16px">
                <div style="display:flex;gap:16px;align-items:end;flex-wrap:wrap">
                    <div style="min-width:220px">
                        <div style="font-size:11px;color:var(--pg-color-text-secondary);text-transform:uppercase">Program</div>
                        <div style="font-weight:600">${esc(_activeProgram?.name || '—')}</div>
                    </div>
                    <div style="min-width:280px;flex:1">
                        <label for="projectSetupProjectSelect" style="display:block;font-size:11px;color:var(--pg-color-text-secondary);text-transform:uppercase;margin-bottom:4px">Project</label>
                        <select id="projectSetupProjectSelect" class="pg-input" onchange="ProjectSetupView.selectProject(this.value)">
                            <option value="">Select project...</option>
                        </select>
                    </div>
                </div>
                <div id="projectSetupContextMeta" style="margin-top:8px;font-size:12px;color:var(--pg-color-text-secondary)"></div>
            </div>
            <div class="exp-tabs" style="margin-bottom:16px">
                <button class="exp-tab ${_currentTab === 'project-info' ? 'exp-tab--active' : ''}" onclick="ProjectSetupView.switchTab('project-info')">📌 Project Info</button>
                <button class="exp-tab ${_currentTab === 'methodology' ? 'exp-tab--active' : ''}" onclick="ProjectSetupView.switchTab('methodology')">🧭 Methodology</button>
                <button class="exp-tab ${_currentTab === 'team' ? 'exp-tab--active' : ''}" onclick="ProjectSetupView.switchTab('team')">👥 Team</button>
                <button class="exp-tab ${_currentTab === 'scope-hierarchy' ? 'exp-tab--active' : ''}" onclick="ProjectSetupView.switchTab('scope-hierarchy')">🏗️ Scope & Hierarchy</button>
                <button class="exp-tab ${_currentTab === 'governance' ? 'exp-tab--active' : ''}" onclick="ProjectSetupView.switchTab('governance')">🛡 Governance</button>
            </div>
            <div id="setupContent">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>`;

        _loadProgramContext().then(() => {
            _renderContextCard();
            loadCurrentTab();
        });
    }

    function switchTab(tab) {
        _currentTab = tab;
        document.querySelectorAll('.exp-tab').forEach((t, idx) => {
            const tabs = ['project-info', 'methodology', 'team', 'scope-hierarchy', 'governance'];
            t.classList.toggle('exp-tab--active', tabs[idx] === tab);
        });
        loadCurrentTab();
    }

    async function _loadProgramContext() {
        try {
            const [projects, programDetail] = await Promise.all([
                API.get(`/programs/${_pid}/projects`),
                API.get(`/programs/${_pid}`),
            ]);
            _programProjects = Array.isArray(projects) ? projects : [];
            _programDetail = programDetail || null;
        } catch {
            _programProjects = [];
            _programDetail = null;
        }
        _activeProject = App.getActiveProject();
        if (_activeProject && _activeProject.program_id !== _pid) {
            App.setActiveProject(null);
            _activeProject = null;
        }
    }

    function _renderContextCard() {
        const select = document.getElementById('projectSetupProjectSelect');
        const meta = document.getElementById('projectSetupContextMeta');
        if (!select || !meta) return;

        select.innerHTML = [
            '<option value="">Select project...</option>',
            ..._programProjects.map((p) =>
                `<option value="${p.id}" ${_activeProject && Number(_activeProject.id) === Number(p.id) ? 'selected' : ''}>${esc(p.name)} (${esc(p.code || 'PRJ')})</option>`
            ),
        ].join('');

        if (_activeProject) {
            const full = _programProjects.find((p) => Number(p.id) === Number(_activeProject.id));
            meta.innerHTML = full
                ? `Selected project: <strong>${esc(full.name)}</strong> · Status: ${esc(full.status || 'active')} · Type: ${esc(full.type || 'n/a')}`
                : `Selected project id: ${esc(String(_activeProject.id))}`;
        } else {
            meta.innerHTML = 'No project selected yet. Choose one to access project setup tabs.';
        }
    }

    function selectProject(projectId) {
        const pid = Number.parseInt(String(projectId || ''), 10);
        if (!Number.isFinite(pid) || pid <= 0) {
            App.setActiveProject(null);
            _activeProject = null;
            _renderContextCard();
            renderProjectRequiredGuard();
            return;
        }

        const project = _programProjects.find((p) => Number(p.id) === pid);
        if (!project) {
            App.toast('Selected project was not found in this program.', 'error');
            return;
        }

        App.setActiveProject({
            id: project.id,
            name: project.name,
            code: project.code,
            program_id: project.program_id,
            tenant_id: project.tenant_id,
        });
        _activeProject = App.getActiveProject();
        _renderContextCard();
        loadCurrentTab();
    }

    function loadCurrentTab() {
        if (!_activeProject) {
            renderProjectRequiredGuard();
            return;
        }
        if (_currentTab === 'scope-hierarchy') {
            loadHierarchyTab();
            return;
        }
        if (_currentTab === 'project-info') {
            renderProjectInfoTab();
            return;
        }
        if (_currentTab === 'methodology') {
            renderMethodologyTab();
            return;
        }
        if (_currentTab === 'team') {
            renderTeamTab();
            return;
        }
        if (_currentTab === 'governance') {
            renderGovernanceTab();
            return;
        }
        renderPlaceholder();
    }

    function renderProjectRequiredGuard() {
        const c = document.getElementById('setupContent');
        if (!c) return;
        c.innerHTML = PGEmptyState.html({
            icon: 'settings',
            title: 'Project selection required',
            description: 'Program is selected. Choose a project from the selector above to continue.',
            action: { label: 'Go to Programs', onclick: "App.navigate('programs')" },
        });
    }

    function renderProjectInfoTab() {
        const c = document.getElementById('setupContent');
        const project = _programProjects.find((p) => Number(p.id) === Number(_activeProject?.id));
        if (!c || !project) {
            renderProjectRequiredGuard();
            return;
        }
        c.innerHTML = `
            <div class="card" style="padding:16px">
                <h3 style="margin-bottom:12px">Project Information</h3>
                <div class="detail-grid">
                    <div class="detail-section">
                        <dl class="detail-list">
                            <dt>Program</dt><dd>${esc(_activeProgram?.name || '—')}</dd>
                            <dt>Project Name</dt><dd>${esc(project.name || '—')}</dd>
                            <dt>Project Code</dt><dd>${esc(project.code || '—')}</dd>
                            <dt>Status</dt><dd>${esc(project.status || 'active')}</dd>
                            <dt>Type</dt><dd>${esc(project.type || 'n/a')}</dd>
                        </dl>
                    </div>
                    <div class="detail-section">
                        <dl class="detail-list">
                            <dt>Default Project</dt><dd>${project.is_default ? 'Yes' : 'No'}</dd>
                            <dt>Owner ID</dt><dd>${esc(String(project.owner_id || '—'))}</dd>
                            <dt>Start Date</dt><dd>${esc(project.start_date || '—')}</dd>
                            <dt>End Date</dt><dd>${esc(project.end_date || '—')}</dd>
                            <dt>Go-live Date</dt><dd>${esc(project.go_live_date || '—')}</dd>
                        </dl>
                    </div>
                </div>
            </div>
        `;
    }

    function renderMethodologyTab() {
        const c = document.getElementById('setupContent');
        const phases = Array.isArray(_programDetail?.phases) ? _programDetail.phases : [];
        c.innerHTML = `
            <div class="card" style="padding:16px">
                <h3 style="margin-bottom:12px">Project Methodology</h3>
                <div class="detail-grid">
                    <div class="detail-section">
                        <dl class="detail-list">
                            <dt>Methodology</dt><dd>${esc(_programDetail?.methodology || _activeProgram?.methodology || '—')}</dd>
                            <dt>Project Type</dt><dd>${esc(_programDetail?.project_type || _activeProgram?.project_type || '—')}</dd>
                            <dt>Program Status</dt><dd>${esc(_programDetail?.status || _activeProgram?.status || '—')}</dd>
                        </dl>
                    </div>
                    <div class="detail-section">
                        <h4 style="margin-bottom:8px">Lifecycle Phases</h4>
                        ${phases.length
                            ? `<ul style="margin:0;padding-left:18px">${phases.map((p) => `<li>${esc(p.name)} (${esc(p.status || 'n/a')})</li>`).join('')}</ul>`
                            : '<div style="color:var(--pg-color-text-secondary)">No phases defined for this program.</div>'
                        }
                    </div>
                </div>
            </div>
        `;
    }

    function renderTeamTab() {
        const c = document.getElementById('setupContent');
        const team = Array.isArray(_programDetail?.team_members) ? _programDetail.team_members : [];
        c.innerHTML = `
            <div class="card" style="padding:16px">
                <h3 style="margin-bottom:12px">Project Team</h3>
                ${team.length
                    ? `<div class="table-wrap"><table class="table"><thead><tr><th>Name</th><th>Role</th><th>RACI</th><th>Email</th></tr></thead><tbody>
                        ${team.map((m) => `<tr><td>${esc(m.name || '')}</td><td>${esc(m.role || '')}</td><td>${esc(m.raci || '')}</td><td>${esc(m.email || '')}</td></tr>`).join('')}
                    </tbody></table></div>`
                    : '<div style="color:var(--pg-color-text-secondary)">No team members mapped yet.</div>'
                }
            </div>
        `;
    }

    function renderGovernanceTab() {
        const c = document.getElementById('setupContent');
        const committees = Array.isArray(_programDetail?.committees) ? _programDetail.committees : [];
        const workstreams = Array.isArray(_programDetail?.workstreams) ? _programDetail.workstreams : [];
        c.innerHTML = `
            <div class="detail-grid">
                <div class="card detail-section" style="padding:16px">
                    <h3 style="margin-bottom:12px">Governance Committees</h3>
                    ${committees.length
                        ? `<ul style="margin:0;padding-left:18px">${committees.map((x) => `<li>${esc(x.name)} · ${esc(x.committee_type || 'n/a')}</li>`).join('')}</ul>`
                        : '<div style="color:var(--pg-color-text-secondary)">No committees defined.</div>'
                    }
                </div>
                <div class="card detail-section" style="padding:16px">
                    <h3 style="margin-bottom:12px">Workstreams</h3>
                    ${workstreams.length
                        ? `<ul style="margin:0;padding-left:18px">${workstreams.map((x) => `<li>${esc(x.name)} · ${esc(x.ws_type || 'n/a')}</li>`).join('')}</ul>`
                        : '<div style="color:var(--pg-color-text-secondary)">No workstreams defined.</div>'
                    }
                </div>
            </div>
        `;
    }

    async function loadHierarchyTab() {
        const c = document.getElementById('setupContent');
        c.innerHTML = `<div style="text-align:center;padding:40px"><div class="spinner"></div></div>`;

        try {
            const [l1, l2, l3, l4] = await Promise.all([
                ExploreAPI.levels.listL1(_pid),
                ExploreAPI.levels.listL2(_pid),
                ExploreAPI.levels.listL3(_pid),
                ExploreAPI.levels.listL4(_pid),
            ]);

            _l1List = l1;
            _l2List = l2;
            _l3List = l3;
            _l4List = l4;
            _flatList = [...l1, ...l2, ...l3, ...l4];

            if (_flatList.length === 0) {
                renderEmptyState(c);
                return;
            }

            const nodesById = {};
            _flatList.forEach(n => { nodesById[n.id] = Object.assign({ children: [] }, n); });
            _tree = [];
            _flatList.forEach(n => {
                if (n.parent_id && nodesById[n.parent_id]) {
                    nodesById[n.parent_id].children.push(nodesById[n.id]);
                } else if (!n.parent_id) {
                    _tree.push(nodesById[n.id]);
                }
            });

            if (_expandedNodes.size === 0) {
                _tree.forEach(r => _expandedNodes.add(r.id));
            }

            renderHierarchyContent();
        } catch (err) {
            c.innerHTML = PGEmptyState.html({ icon: 'warning', title: 'Load failed', description: esc(err.message || '') });
        }
    }

    function renderHierarchyContent() {
        const c = document.getElementById('setupContent');
        c.innerHTML = `
            ${renderKpiRow()}
            ${renderToolbar()}
            <div id="hierarchyContent">
                ${_viewMode === 'tree' ? renderTreeContent() : renderTableView()}
            </div>
        `;
    }

    function renderKpiRow() {
        const inScopeCount = _flatList.filter(n => n.scope_status === 'in_scope').length;
        const totalCount = _flatList.length || 0;
        const inScopePct = totalCount > 0 ? Math.round(inScopeCount / totalCount * 100) : 0;

        return `<div class="exp-kpi-strip" style="margin-bottom:16px">
            ${ExpUI.kpiBlock({ value: _l1List.length, label: 'L1 Areas', icon: '🏛' })}
            ${ExpUI.kpiBlock({ value: _l2List.length, label: 'L2 Groups', icon: '📁' })}
            ${ExpUI.kpiBlock({ value: _l3List.length, label: 'L3 Scope Items', icon: '📋' })}
            ${ExpUI.kpiBlock({ value: _l4List.length, label: 'L4 Steps', icon: '⚙' })}
            ${ExpUI.kpiBlock({ value: `${inScopePct}%`, label: 'In Scope', icon: '✅' })}
        </div>`;
    }

    function renderToolbar() {
        const areaOptions = ['FI', 'CO', 'MM', 'SD', 'PP', 'HR', 'QM', 'EWM', 'BC']
            .filter(a => _flatList.some(n => n.process_area_code === a))
            .map(a => ({ value: a, label: a }));
        const scopeOpts = [
            { value: 'in_scope', label: 'In Scope' },
            { value: 'out_of_scope', label: 'Out of Scope' },
            { value: 'deferred', label: 'Deferred' },
        ];

        return ExpUI.filterBar({
            id: 'projectSetupFB',
            searchPlaceholder: 'Search processes...',
            searchValue: _searchQuery,
            onSearch: "ProjectSetupView.setSearch(this.value)",
            onChange: "ProjectSetupView.onFilterBarChange",
            filters: [
                {
                    id: 'area', label: 'Area', icon: '📁', type: 'single',
                    color: 'var(--exp-l2)',
                    options: areaOptions,
                    selected: _filters.area || '',
                },
                {
                    id: 'scope', label: 'Scope', icon: '🎯', type: 'single',
                    color: 'var(--exp-l3)',
                    options: scopeOpts,
                    selected: _filters.scope || '',
                },
            ],
            actionsHtml: `
                <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                    <div style="display:flex;border:1px solid var(--pg-color-border);border-radius:var(--exp-radius-md);overflow:hidden">
                        <button class="view-toggle-btn${_viewMode === 'tree' ? ' active' : ''}" onclick="ProjectSetupView.setViewMode('tree')">🌳 Tree</button>
                        <button class="view-toggle-btn${_viewMode === 'table' ? ' active' : ''}" onclick="ProjectSetupView.setViewMode('table')">📊 Table</button>
                    </div>

                    ${ExpUI.actionButton({ label: '🤖 AI Suggested', variant: 'ghost', size: 'sm', onclick: 'ProjectSetupView.openAISuggested()' })}
                    ${ExpUI.actionButton({ label: '📚 Import Template', variant: 'secondary', size: 'sm', onclick: 'ProjectSetupView.openTemplateImport()' })}
                    ${ExpUI.actionButton({ label: '➕ Add L1 Area', variant: 'primary', size: 'sm', onclick: "ProjectSetupView.openCreateDialog(1, null)" })}
                </div>
            `,
        });
    }

    function renderTreeContent() {
        const nodes = _tree
            .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
            .map(n => renderTreeNode(n, 0))
            .filter(Boolean)
            .join('');

        return `
            <div class="card" style="padding:0;overflow:hidden">
                <div style="padding:8px 0">
                    ${nodes || '<div style="padding:16px;color:var(--pg-color-text-secondary)">No results found.</div>'}
                </div>
                <div style="padding:12px;border-top:1px solid var(--pg-color-border)">
                    ${ExpUI.actionButton({ label: '➕ Add L1 Area', variant: 'secondary', size: 'sm', onclick: 'ProjectSetupView.openCreateDialog(1, null)' })}
                </div>
            </div>`;
    }

    function renderTreeNode(node, depth) {
        const lvl = node.level || depth + 1;
        const children = (node.children || []).sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
        const isExpanded = _expandedNodes.has(node.id);
        const indent = 16 + depth * 28;
        const levelColor = `var(--exp-l${lvl})`;
        const levelBg = `var(--exp-l${lvl}-bg)`;

        const filteredChildren = children.map(c => renderTreeNode(c, depth + 1)).filter(Boolean).join('');
        const selfVisible = matchesFilters(node) && matchesSearch(node);
        if (!selfVisible && !filteredChildren) return '';

        const scopeBadge = node.scope_status && node.scope_status !== 'in_scope'
            ? ExpUI.pill({
                label: node.scope_status.replace(/_/g, ' '),
                variant: node.scope_status === 'out_of_scope' ? 'danger' : 'warning',
                size: 'sm',
            })
            : '';

        return `
            <div class="setup-node" data-id="${esc(node.id)}" data-level="${lvl}">
                <div class="setup-node__row" style="padding:0 16px 0 ${indent}px;height:42px;display:flex;align-items:center;gap:8px;--level-color:${levelColor}">
                    ${children.length
                        ? `<span class="setup-chevron${isExpanded ? ' setup-chevron--open' : ''}" onclick="event.stopPropagation();ProjectSetupView.toggleNode('${node.id}')">▶</span>`
                        : '<span style="width:20px"></span>'}

                    <span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:6px;background:${levelBg};margin-right:4px">
                        <span style="font-size:11px;font-weight:700;color:${levelColor}">L${lvl}</span>
                    </span>

                    <code style="font-family:var(--exp-font-mono);font-size:11px;color:var(--pg-color-text-secondary);min-width:80px;margin-right:8px">${esc(node.code || '')}</code>

                    <span style="flex:1;font-weight:${lvl <= 2 ? 600 : 400};font-size:14px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                        onclick="ProjectSetupView.openEditDialog('${node.id}',${lvl})" title="${esc(node.name || '')}">${esc(node.name || '')}</span>

                    ${scopeBadge}

                    ${node.process_area_code
                        ? `<span style="font-size:11px;font-weight:600;color:var(--pg-color-text-tertiary);min-width:28px;text-align:center">${esc(node.process_area_code)}</span>`
                        : ''}

                    ${node.wave ? `<span style="font-size:10px;color:var(--pg-color-text-tertiary);margin-left:4px">W${node.wave}</span>` : ''}

                    <span class="setup-node__actions" style="margin-left:8px">
                        ${lvl < 4 ? `<button class="btn-icon" title="Add L${lvl + 1}" onclick="event.stopPropagation();ProjectSetupView.openCreateDialog(${lvl + 1},'${node.id}')">+</button>` : ''}
                        <button class="btn-icon" title="Edit" onclick="event.stopPropagation();ProjectSetupView.openEditDialog('${node.id}',${lvl})">✏️</button>
                        <button class="btn-icon btn-icon--danger" title="Delete" onclick="event.stopPropagation();ProjectSetupView.confirmDelete('${node.id}','${esc(node.name || '')}')">🗑️</button>
                    </span>
                </div>
                ${filteredChildren && isExpanded ? filteredChildren : ''}
            </div>`;
    }

    function renderTableView() {
        const flat = flattenTree(_tree);

        return `
            <div class="card" style="padding:0;overflow:hidden">
                <table class="data-table" style="font-size:13px;width:100%">
                    <thead>
                        <tr>
                            <th style="width:50px">Level</th>
                            <th style="width:100px">Code</th>
                            <th style="min-width:200px">Name</th>
                            <th style="width:70px">Module</th>
                            <th style="width:80px">Scope</th>
                            <th style="width:50px">Wave</th>
                            <th style="width:120px">Parent</th>
                            <th style="width:80px;text-align:right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${flat.map(node => renderTableRow(node)).join('')}
                    </tbody>
                    <tfoot>
                        <tr id="inlineAddRow" style="background:var(--pg-color-bg)">
                            <td>
                                <select id="addLevel" class="inline-input" style="width:100%">
                                    <option value="1">L1</option>
                                    <option value="2">L2</option>
                                    <option value="3">L3</option>
                                    <option value="4">L4</option>
                                </select>
                            </td>
                            <td><input id="addCode" class="inline-input" placeholder="Auto" style="width:100%"></td>
                            <td><input id="addName" class="inline-input" placeholder="Name *" style="width:100%" onkeydown="if(event.key==='Enter')ProjectSetupView.submitInlineAdd()"></td>
                            <td>
                                <select id="addModule" class="inline-input" style="width:100%">
                                    <option value="">—</option>
                                    ${MODULES.map(m => `<option value="${m}">${m}</option>`).join('')}
                                </select>
                            </td>
                            <td>
                                <select id="addScope" class="inline-input" style="width:100%">
                                    <option value="in_scope">In Scope</option>
                                    <option value="out_of_scope">Out</option>
                                    <option value="deferred">Deferred</option>
                                </select>
                            </td>
                            <td><input id="addWave" class="inline-input" type="number" min="1" max="9" placeholder="1" style="width:100%"></td>
                            <td>
                                <select id="addParent" class="inline-input" style="width:100%">
                                    <option value="">— None (L1) —</option>
                                    ${_flatList.filter(n => n.level < 4).map(n =>
                                        `<option value="${n.id}">${esc(n.code || '')} — ${esc((n.name || '').substring(0, 20))}</option>`
                                    ).join('')}
                                </select>
                            </td>
                            <td style="text-align:right">
                                ${ExpUI.actionButton({ label: '✓ Add', variant: 'success', size: 'sm', onclick: 'ProjectSetupView.submitInlineAdd()' })}
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>`;
    }

    function renderTableRow(node) {
        const lvl = node.level || 1;
        const levelColor = `var(--exp-l${lvl})`;
        const levelBg = `var(--exp-l${lvl}-bg)`;
        const parentNode = _flatList.find(n => n.id === node.parent_id);

        if (!matchesFilters(node) || !matchesSearch(node)) return '';

        return `<tr style="cursor:pointer" onclick="ProjectSetupView.openEditDialog('${node.id}',${lvl})">
            <td>
                <span style="display:inline-flex;align-items:center;justify-content:center;width:26px;height:20px;border-radius:4px;background:${levelBg};color:${levelColor};font-size:11px;font-weight:700">L${lvl}</span>
            </td>
            <td><code style="font-family:var(--exp-font-mono);font-size:11px">${esc(node.code || '')}</code></td>
            <td style="font-weight:${lvl <= 2 ? 600 : 400}">${esc(node.name || '')}</td>
            <td style="font-size:11px;color:var(--pg-color-text-secondary)">${esc(node.process_area_code || '—')}</td>
            <td>${ExpUI.pill({
                label: (node.scope_status || 'pending').replace(/_/g, ' '),
                variant: node.scope_status === 'in_scope' ? 'success' : node.scope_status === 'out_of_scope' ? 'danger' : 'warning',
                size: 'sm',
            })}</td>
            <td style="font-size:12px;color:var(--pg-color-text-secondary)">${node.wave ? 'W' + node.wave : '—'}</td>
            <td style="font-size:11px;color:var(--pg-color-text-tertiary)">${parentNode ? esc(parentNode.code || '') : '—'}</td>
            <td style="text-align:right" onclick="event.stopPropagation()">
                <button class="btn-icon" onclick="ProjectSetupView.openEditDialog('${node.id}',${lvl})">✏️</button>
                <button class="btn-icon btn-icon--danger" onclick="ProjectSetupView.confirmDelete('${node.id}','${esc(node.name || '')}')">🗑️</button>
            </td>
        </tr>`;
    }

    function renderEmptyState(container) {
        container.innerHTML = `
            <div style="padding:60px 20px;text-align:center;max-width:800px;margin:0 auto">
                <div style="font-size:56px;margin-bottom:12px">🏗️</div>
                <h2 style="margin-bottom:8px;font-size:22px">No Process Hierarchy Defined</h2>
                <p style="color:var(--pg-color-text-secondary);margin-bottom:32px;font-size:14px">
                    Build your L1 → L4 process structure to start your SAP project
                </p>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;text-align:left">
                    <div class="card" style="padding:24px;cursor:pointer;border:2px solid transparent;transition:all 0.2s"
                        onclick="ProjectSetupView.openTemplateImport()"
                        onmouseenter="this.style.borderColor='var(--pg-color-primary)';this.style.boxShadow='var(--exp-shadow-md)'"
                        onmouseleave="this.style.borderColor='transparent';this.style.boxShadow=''">
                        <div style="font-size:32px;margin-bottom:12px">📚</div>
                        <div style="font-weight:700;margin-bottom:6px">Import SAP Template</div>
                        <div style="font-size:13px;color:var(--pg-color-text-secondary);line-height:1.5">
                            Pre-built L1→L4 hierarchy from SAP Best Practice catalog.
                            Select areas to import.
                        </div>
                        <div style="margin-top:12px">${ExpUI.pill({ label: '5 areas · 265 items', variant: 'info', size: 'sm' })}</div>
                    </div>

                    <div class="card" style="padding:24px;cursor:pointer;border:2px solid transparent;transition:all 0.2s;position:relative"
                        onclick="ProjectSetupView.openAISuggested()"
                        onmouseenter="this.style.borderColor='#8B5CF6';this.style.boxShadow='var(--exp-shadow-md)'"
                        onmouseleave="this.style.borderColor='transparent';this.style.boxShadow=''">
                        <div style="position:absolute;top:12px;right:12px">${ExpUI.pill({ label: 'Coming Soon', variant: 'pending', size: 'sm' })}</div>
                        <div style="font-size:32px;margin-bottom:12px">🤖</div>
                        <div style="font-weight:700;margin-bottom:6px">AI-Suggested Hierarchy</div>
                        <div style="font-size:13px;color:var(--pg-color-text-secondary);line-height:1.5">
                            AI generates a customized hierarchy based on your industry,
                            SAP modules, and company profile.
                        </div>
                        <div style="margin-top:12px">${ExpUI.pill({ label: 'Powered by AI', variant: 'decision', size: 'sm' })}</div>
                    </div>

                    <div class="card" style="padding:24px;cursor:pointer;border:2px solid transparent;transition:all 0.2s"
                        onclick="ProjectSetupView.openBulkEntry()"
                        onmouseenter="this.style.borderColor='var(--exp-l3)';this.style.boxShadow='var(--exp-shadow-md)'"
                        onmouseleave="this.style.borderColor='transparent';this.style.boxShadow=''">
                        <div style="font-size:32px;margin-bottom:12px">✍️</div>
                        <div style="font-weight:700;margin-bottom:6px">Start from Scratch</div>
                        <div style="font-size:13px;color:var(--pg-color-text-secondary);line-height:1.5">
                            Grid entry or paste from Excel. Add multiple levels at once.
                        </div>
                        <div style="margin-top:12px">${ExpUI.pill({ label: 'Flexible', variant: 'draft', size: 'sm' })}</div>
                    </div>
                </div>
            </div>`;
    }

    function openBulkEntry() {
        _bulkMode = 'grid';
        _gridRows = Array.from({ length: 8 }, () => ({
            level: '', code: '', name: '', module: '', parent_code: '',
        }));
        _pasteText = '';
        _parsedRows = [];
        renderBulkModal();
    }

    function renderBulkModal() {
        const filledCount = _gridRows.filter(r => (r.name || '').trim()).length;
        const parsedCount = _parsedRows.filter(r => !r.error).length;
        const ctaCount = _bulkMode === 'grid' ? filledCount : parsedCount;

        const html = `<div class="modal-content" style="max-width:820px;padding:24px;max-height:85vh;overflow-y:auto">
            <h2 style="margin-bottom:4px">✍️ Start from Scratch</h2>
            <p style="color:var(--pg-color-text-secondary);font-size:13px;margin-bottom:16px">
                Add process levels manually — one at a time or bulk entry
            </p>

            <div style="display:flex;gap:0;margin-bottom:16px;border:1px solid var(--pg-color-border);border-radius:var(--exp-radius-md);overflow:hidden;width:fit-content">
                <button class="view-toggle-btn${_bulkMode === 'grid' ? ' active' : ''}" onclick="ProjectSetupView._setBulkMode('grid')">📊 Grid Entry</button>
                <button class="view-toggle-btn${_bulkMode === 'paste' ? ' active' : ''}" onclick="ProjectSetupView._setBulkMode('paste')">📋 Paste from Excel</button>
            </div>

            <div id="bulkContent">
                ${_bulkMode === 'grid' ? renderGridMode() : renderPasteMode()}
            </div>

            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:16px;padding-top:12px;border-top:1px solid var(--pg-color-border)">
                <div id="bulkStatus" style="font-size:12px;color:var(--pg-color-text-tertiary)">
                    ${_bulkMode === 'grid'
                        ? `Filled: <strong>${filledCount}</strong> / ${_gridRows.length} rows`
                        : `Parsed: <strong>${parsedCount}</strong> rows`}
                </div>
                <div style="display:flex;gap:8px">
                    ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                    ${ExpUI.actionButton({
                        label: _bulkMode === 'grid' ? `💾 Create ${filledCount} Items` : `💾 Import ${parsedCount} Items`,
                        variant: 'primary',
                        disabled: ctaCount === 0,
                        onclick: 'ProjectSetupView._submitBulk()',
                        id: 'bulkSubmitBtn',
                    })}
                </div>
            </div>
        </div>`;

        App.openModal(html);
    }

    function renderGridMode() {
        const existingCodes = _flatList.map(n => ({ code: n.code, name: n.name, level: n.level }));

        return `
            <div style="overflow-x:auto">
                <table class="data-table" style="font-size:13px;width:100%;min-width:700px">
                    <thead>
                        <tr>
                            <th style="width:70px">Level</th>
                            <th style="width:100px">Code</th>
                            <th style="min-width:200px">Name *</th>
                            <th style="width:80px">Module</th>
                            <th style="width:140px">Parent Code</th>
                            <th style="width:40px"></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${_gridRows.map((row, i) => `
                            <tr data-row="${i}" class="${(row.name || '').trim() ? '' : 'grid-row--empty'}">
                                <td>
                                    <select class="inline-input" data-row="${i}" onchange="ProjectSetupView._updateGridRow(${i},'level',this.value)">
                                        <option value="">—</option>
                                        <option value="1" ${(row.level === '1' || row.level === 1) ? 'selected' : ''}>L1</option>
                                        <option value="2" ${(row.level === '2' || row.level === 2) ? 'selected' : ''}>L2</option>
                                        <option value="3" ${(row.level === '3' || row.level === 3) ? 'selected' : ''}>L3</option>
                                        <option value="4" ${(row.level === '4' || row.level === 4) ? 'selected' : ''}>L4</option>
                                    </select>
                                </td>
                                <td><input class="inline-input" value="${esc(row.code || '')}" placeholder="Auto" onchange="ProjectSetupView._updateGridRow(${i},'code',this.value)"></td>
                                <td><input class="inline-input" value="${esc(row.name || '')}" placeholder="Process name..." onchange="ProjectSetupView._updateGridRow(${i},'name',this.value)" style="font-weight:${row.name ? '500' : '400'}"></td>
                                <td>
                                    <select class="inline-input" onchange="ProjectSetupView._updateGridRow(${i},'module',this.value)">
                                        <option value="">—</option>
                                        ${MODULES.map(m => `<option value="${m}" ${row.module === m ? 'selected' : ''}>${m}</option>`).join('')}
                                    </select>
                                </td>
                                <td>
                                    <select class="inline-input" onchange="ProjectSetupView._updateGridRow(${i},'parent_code',this.value)">
                                        <option value="">— None —</option>
                                        ${[...existingCodes, ..._gridRows.slice(0, i).filter(r => r.code && r.name)
                                            .map(r => ({ code: r.code, name: r.name, level: r.level }))
                                        ].map(p =>
                                            `<option value="${esc(p.code)}" ${row.parent_code === p.code ? 'selected' : ''}>${esc(p.code)} — ${esc((p.name || '').substring(0, 20))}</option>`
                                        ).join('')}
                                    </select>
                                </td>
                                <td>
                                    ${(row.name || '').trim() ? `<button class="btn-icon btn-icon--danger" title="Clear row" onclick="ProjectSetupView._clearGridRow(${i})">✕</button>` : ''}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            <div style="margin-top:8px">
                ${ExpUI.actionButton({ label: '➕ Add 5 Rows', variant: 'ghost', size: 'sm', onclick: 'ProjectSetupView._addGridRows(5)' })}
            </div>`;
    }

    function renderPasteMode() {
        return `
            <div style="margin-bottom:12px">
                <div style="font-size:12px;color:var(--pg-color-text-secondary);margin-bottom:8px;font-family:var(--exp-font-mono)">
                    Format: <strong>Level</strong> ⇥ <strong>Code</strong> ⇥ <strong>Name</strong> ⇥ <strong>Module</strong> ⇥ <strong>Parent Code</strong>
                </div>
                <textarea id="pasteArea" rows="10" class="form-input"
                    style="font-family:var(--exp-font-mono);font-size:12px;line-height:1.6;resize:vertical;white-space:pre;overflow-x:auto"
                    placeholder="Paste from Excel here..."
                    oninput="ProjectSetupView._parsePaste(this.value)">${esc(_pasteText)}</textarea>
            </div>

            <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
                ${ExpUI.actionButton({ label: '📥 Download Template (.tsv)', variant: 'ghost', size: 'sm', onclick: 'ProjectSetupView._downloadTemplate()' })}
                <span style="font-size:11px;color:var(--pg-color-text-tertiary)">— or copy this format from your own Excel</span>
            </div>

            <div id="bulkPastePreview">
                ${renderPastePreview()}
            </div>`;
    }

    function renderPastePreview() {
        const validRows = _parsedRows.filter(r => !r.error);
        if (!validRows.length && !_parsedRows.length) return '';

        const summary = ['L1', 'L2', 'L3', 'L4']
            .map(l => {
                const c = _parsedRows.filter(r => `L${r.level}` === l).length;
                return c > 0 ? `${l}:${c}` : '';
            })
            .filter(Boolean)
            .join(' · ');

        return `
            <div class="card" style="padding:12px 16px;background:var(--pg-color-bg)">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                    <span style="color:var(--exp-fit);font-weight:600">✅ ${validRows.length} rows parsed</span>
                    <span style="font-size:12px;color:var(--pg-color-text-secondary)">${summary}</span>
                </div>

                <table class="data-table" style="font-size:12px">
                    <thead>
                        <tr><th>Lvl</th><th>Code</th><th>Name</th><th>Module</th><th>Parent</th><th></th></tr>
                    </thead>
                    <tbody>
                        ${_parsedRows.map(r => `
                            <tr${r.error ? ' style="background:var(--pg-color-red-50)"' : ''}>
                                <td><span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:18px;border-radius:3px;background:var(--exp-l${r.level}-bg);color:var(--exp-l${r.level});font-size:10px;font-weight:700">L${r.level}</span></td>
                                <td><code style="font-size:11px">${esc(r.code || 'Auto')}</code></td>
                                <td>${esc(r.name || '')}</td>
                                <td style="color:var(--pg-color-text-secondary)">${esc(r.module || '—')}</td>
                                <td style="color:var(--pg-color-text-tertiary);font-size:11px">${esc(r.parent_code || '—')}</td>
                                <td>${r.error ? `<span style="color:var(--pg-color-negative);font-size:11px">⚠ ${esc(r.error)}</span>` : '<span style="color:var(--exp-fit)">✓</span>'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>`;
    }

    function _setBulkMode(mode) {
        _bulkMode = mode;
        renderBulkModal();
    }

    function _updateGridRow(i, field, value) {
        if (!_gridRows[i]) return;
        _gridRows[i][field] = value;
        updateBulkContent();
    }

    function _clearGridRow(i) {
        if (!_gridRows[i]) return;
        _gridRows[i] = { level: '', code: '', name: '', module: '', parent_code: '' };
        updateBulkContent();
    }

    function _addGridRows(n) {
        for (let j = 0; j < n; j += 1) {
            _gridRows.push({ level: '', code: '', name: '', module: '', parent_code: '' });
        }
        updateBulkContent();
    }

    function _parsePaste(text) {
        _pasteText = text;
        _parsedRows = [];
        const lines = text.split('\n').filter(l => l.trim());
        for (const line of lines) {
            const cols = line.split('\t');
            if (cols.length < 3) continue;
            const level = parseInt(cols[0], 10);
            if (Number.isNaN(level) || level < 1 || level > 4) {
                _parsedRows.push({ level: cols[0], code: cols[1], name: cols[2] || '', error: 'Invalid level' });
                continue;
            }
            const name = (cols[2] || '').trim();
            _parsedRows.push({
                level: level,
                code: (cols[1] || '').trim(),
                name: name,
                module: (cols[3] || '').trim(),
                parent_code: (cols[4] || '').trim(),
                error: name ? null : 'Name is required',
            });
        }
        updateBulkContent();
    }

    async function _submitBulk() {
        let rows = [];
        if (_bulkMode === 'grid') {
            rows = _gridRows
                .filter(r => (r.name || '').trim())
                .map(r => ({
                    level: parseInt(r.level, 10),
                    code: r.code.trim() || undefined,
                    name: r.name.trim(),
                    process_area_code: r.module || undefined,
                    parent_code: r.parent_code || undefined,
                }));
        } else {
            rows = _parsedRows
                .filter(r => !r.error)
                .map(r => ({
                    level: r.level,
                    code: r.code || undefined,
                    name: r.name,
                    process_area_code: r.module || undefined,
                    parent_code: r.parent_code || undefined,
                }));
        }

        if (!rows.length) {
            App.toast('No valid rows to create', 'error');
            return;
        }

        try {
            const result = await ExploreAPI.levels.bulkCreate(_pid, rows);
            App.closeModal();
            const errMsg = result.errors?.length ? ` (${result.errors.length} errors)` : '';
            App.toast(`Created ${result.created} process levels${errMsg}`, 'success');
            await loadHierarchyTab();
        } catch (err) {
            App.toast(err.message || 'Bulk create failed', 'error');
        }
    }

    function _downloadTemplate() {
        const header = 'Level\tCode\tName\tModule\tParent Code';
        const sample = '1\tL1-FIN\tFinance\tFI\t\n2\tL2-GL\tGeneral Ledger\tFI\tL1-FIN\n2\tL2-AP\tAccounts Payable\tFI\tL1-FIN\n3\tL3-001\tJournal Entry\tFI\tL2-GL\n3\tL3-002\tPeriod-End Closing\tFI\tL2-GL\n3\tL3-003\tVendor Invoice\tFI\tL2-AP';
        const blob = new Blob([header + '\n' + sample], { type: 'text/tab-separated-values' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'process_hierarchy_template.tsv';
        a.click();
        URL.revokeObjectURL(url);
    }

    function updateBulkContent() {
        const contentEl = document.getElementById('bulkContent');
        if (contentEl) {
            contentEl.innerHTML = _bulkMode === 'grid' ? renderGridMode() : renderPasteMode();
        }

        const filledCount = _gridRows.filter(r => (r.name || '').trim()).length;
        const parsedCount = _parsedRows.filter(r => !r.error).length;
        const statusEl = document.getElementById('bulkStatus');
        const submitBtn = document.getElementById('bulkSubmitBtn');

        if (statusEl) {
            statusEl.innerHTML = _bulkMode === 'grid'
                ? `Filled: <strong>${filledCount}</strong> / ${_gridRows.length} rows`
                : `Parsed: <strong>${parsedCount}</strong> rows`;
        }

        if (submitBtn) {
            submitBtn.textContent = _bulkMode === 'grid'
                ? `💾 Create ${filledCount} Items`
                : `💾 Import ${parsedCount} Items`;
            submitBtn.disabled = (_bulkMode === 'grid' ? filledCount : parsedCount) === 0;
        }

        if (_bulkMode === 'paste') {
            const preview = document.getElementById('bulkPastePreview');
            if (preview) preview.innerHTML = renderPastePreview();
        }
    }

    function openCreateDialog(level, parentId) {
        const placeholderMap = {
            1: 'Order to Cash',
            2: 'Sales Management',
            3: 'Standard Sales Order',
            4: 'Create Sales Order',
        };
        const parent = parentId ? _flatList.find(n => n.id === parentId) : null;
        const moduleDefault = parent ? parent.process_area_code : '';

        App.openModal(`
            <h2>Create L${level}</h2>
            <div class="form-row">
                <div class="form-group">
                    <label>Name *</label>
                    <input id="psName" class="form-input" placeholder="${placeholderMap[level] || ''}">
                </div>
                <div class="form-group">
                    <label>Code</label>
                    <input id="psCode" class="form-input" placeholder="Auto" value="">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Module</label>
                    <select id="psModule" class="form-input">
                        <option value="">—</option>
                        ${MODULES.map(m => `<option value="${m}" ${m === moduleDefault ? 'selected' : ''}>${m}</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="psDesc" class="form-input" rows="2"></textarea>
                </div>
            </div>
            <div style="text-align:right;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Create', variant: 'primary', onclick: `ProjectSetupView.submitCreate(${level}, ${parentId ? `'${parentId}'` : 'null'})` })}
            </div>
        `);
    }

    async function submitCreate(level, parentId) {
        const name = document.getElementById('psName')?.value.trim();
        const code = document.getElementById('psCode')?.value.trim();
        const module = document.getElementById('psModule')?.value;
        const description = document.getElementById('psDesc')?.value.trim();

        if (!name) {
            App.toast('Name is required', 'error');
            return;
        }

        const payload = {
            level: level,
            parent_id: parentId,
            name: name,
            code: code || undefined,
            description: description || '',
            process_area_code: module || undefined,
        };

        try {
            await ExploreAPI.levels.create(_pid, payload);
            App.toast('Process level created', 'success');
            App.closeModal();
            await loadHierarchyTab();
        } catch (err) {
            App.toast(err.message || 'Create failed', 'error');
        }
    }

    function openEditDialog(id) {
        const node = _flatList.find(n => n.id === id);
        if (!node) return;

        App.openModal(`
            <h2>Edit ${esc(node.code || 'Process Level')}</h2>
            <div class="form-row">
                <div class="form-group">
                    <label>Name *</label>
                    <input id="psEditName" class="form-input" value="${esc(node.name || '')}">
                </div>
                <div class="form-group">
                    <label>Module</label>
                    <select id="psEditModule" class="form-input">
                        <option value="">—</option>
                        ${MODULES.map(m => `<option value="${m}" ${m === node.process_area_code ? 'selected' : ''}>${m}</option>`).join('')}
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Scope Status</label>
                    <select id="psEditScope" class="form-input">
                        ${['in_scope', 'out_of_scope', 'deferred'].map(s =>
                            `<option value="${s}" ${s === (node.scope_status || 'in_scope') ? 'selected' : ''}>${s.replace('_', ' ')}</option>`
                        ).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="psEditDesc" class="form-input" rows="2">${esc(node.description || '')}</textarea>
                </div>
            </div>
            <div style="text-align:right;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Save', variant: 'primary', onclick: `ProjectSetupView.submitEdit('${id}')` })}
            </div>
        `);
    }

    async function submitEdit(id) {
        const name = document.getElementById('psEditName')?.value.trim();
        const module = document.getElementById('psEditModule')?.value;
        const scope = document.getElementById('psEditScope')?.value;
        const description = document.getElementById('psEditDesc')?.value.trim();

        if (!name) {
            App.toast('Name is required', 'error');
            return;
        }

        try {
            await ExploreAPI.levels.update(id, {
                name: name,
                description: description,
                scope_status: scope,
                process_area_code: module || null,
            });
            App.toast('Process level updated', 'success');
            App.closeModal();
            await loadHierarchyTab();
        } catch (err) {
            App.toast(err.message || 'Update failed', 'error');
        }
    }

    async function confirmDelete(id, name) {
        let preview;
        try {
            preview = await ExploreAPI.levels.remove(id, false);
        } catch (err) {
            App.toast(err.message || 'Delete preview failed', 'error');
            return;
        }

        if (!preview || !preview.preview) {
            App.toast('Unable to load delete preview', 'error');
            return;
        }

        const byLevel = preview.by_level || {};
        App.openModal(`
            <h2>Delete Process Level</h2>
            <p style="margin:8px 0">This will delete <strong>${esc(name || preview.target.name)}</strong> and its descendants.</p>
            <div class="card" style="background:var(--pg-color-red-50);border:1px solid var(--pg-color-negative)">
                <p style="color:var(--pg-color-negative)"><strong>Warning:</strong> This action cannot be undone.</p>
                <p>Will delete ${preview.descendants_count} descendants (${Object.keys(byLevel).map(k => `${k}: ${byLevel[k]}`).join(', ')}).</p>
            </div>
            <div style="text-align:right;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Delete', variant: 'danger', onclick: `ProjectSetupView.executeDelete('${id}')` })}
            </div>
        `);
    }

    async function executeDelete(id) {
        try {
            await ExploreAPI.levels.remove(id, true);
            App.toast('Deleted', 'success');
            App.closeModal();
            await loadHierarchyTab();
        } catch (err) {
            App.toast(err.message || 'Delete failed', 'error');
        }
    }

    function openTemplateImport() {
        App.openModal(`
            <h2>📚 Import SAP Template</h2>
            <p style="margin-bottom:12px">Select L1 areas to import from SAP Best Practice.</p>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                <input type="checkbox" id="tplSelectAll" onchange="ProjectSetupView.toggleTemplateAll()">
                <label for="tplSelectAll"><strong>Select All</strong></label>
            </div>
            <div style="display:flex;flex-direction:column;gap:10px">
                ${TEMPLATE_L1.map((t, idx) => `
                    <label style="display:flex;gap:10px;align-items:flex-start;border:1px solid var(--pg-color-border);border-radius:8px;padding:8px">
                        <input type="checkbox" class="tplCheck" data-code="${t.code}" data-index="${idx}">
                        <div>
                            <div><strong>${t.name}</strong> <span style="color:var(--pg-color-text-secondary)">(${t.code} · ${t.module})</span></div>
                            <div style="color:var(--pg-color-text-secondary);font-size:12px">${t.desc}</div>
                            <div style="color:var(--pg-color-text-secondary);font-size:12px">${t.stats}</div>
                        </div>
                    </label>
                `).join('')}
            </div>
            <div style="text-align:right;margin-top:16px">
                ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                ${ExpUI.actionButton({ label: 'Import', variant: 'primary', id: 'tplImportBtn', onclick: 'ProjectSetupView.submitTemplateImport()' })}
            </div>
        `);
    }

    function toggleTemplateAll() {
        const all = document.getElementById('tplSelectAll');
        document.querySelectorAll('.tplCheck').forEach(c => { c.checked = all.checked; });
    }

    async function submitTemplateImport() {
        const selected = Array.from(document.querySelectorAll('.tplCheck'))
            .filter(c => c.checked)
            .map(c => c.dataset.code);

        if (selected.length === 0) {
            App.toast('Select at least one L1 area', 'warning');
            return;
        }

        const btn = document.getElementById('tplImportBtn');
        if (btn) {
            btn.textContent = 'Importing...';
            btn.disabled = true;
        }

        try {
            const res = await ExploreAPI.levels.importTemplate(_pid, { selected_l1_codes: selected });
            App.toast(`Imported ${res.imported || 0} items`, 'success');
            App.closeModal();
            await loadHierarchyTab();
        } catch (err) {
            App.toast(err.message || 'Import failed', 'error');
        } finally {
            if (btn) {
                btn.textContent = 'Import';
                btn.disabled = false;
            }
        }
    }

    function openAISuggested() {
        const html = `<div class="modal-content" style="max-width:480px;padding:32px;text-align:center">
            <div style="font-size:48px;margin-bottom:16px">🤖</div>
            <h2 style="margin-bottom:8px">AI-Suggested Hierarchy</h2>
            <p style="color:var(--pg-color-text-secondary);margin-bottom:20px;line-height:1.6">
                AI will analyze your project's industry, SAP modules, and company profile to generate
                a customized L1→L2→L3 process hierarchy.
            </p>
            <div style="background:var(--pg-color-bg);border-radius:var(--exp-radius-lg);padding:16px;margin-bottom:20px;text-align:left">
                <div style="font-size:13px;font-weight:600;margin-bottom:8px">What AI will do:</div>
                <div style="font-size:13px;color:var(--pg-color-text-secondary);line-height:1.8">
                    ✦ Analyze your industry & company profile<br>
                    ✦ Map relevant SAP modules to processes<br>
                    ✦ Generate L1→L2→L3 hierarchy with SAP Best Practice codes<br>
                    ✦ Preview before import — you review & edit first
                </div>
            </div>
            ${ExpUI.pill({ label: 'Coming in Sprint 13', variant: 'info', size: 'md' })}
            <div style="margin-top:20px">
                ${ExpUI.actionButton({ label: 'Close', variant: 'secondary', onclick: 'App.closeModal()' })}
            </div>
        </div>`;
        App.openModal(html);
    }

    async function submitInlineAdd() {
        const level = parseInt(document.getElementById('addLevel')?.value, 10);
        const name = document.getElementById('addName')?.value.trim();
        if (!name) {
            App.toast('Name is required', 'error');
            return;
        }

        const parentId = document.getElementById('addParent')?.value || null;
        if (level === 1 && parentId) {
            App.toast('L1 cannot have a parent', 'error');
            return;
        }
        if (level > 1 && !parentId) {
            App.toast(`L${level} requires a parent`, 'error');
            return;
        }
        if (parentId) {
            const parent = _flatList.find(n => n.id === parentId);
            if (!parent) {
                App.toast('Parent not found', 'error');
                return;
            }
            if (parent.level !== level - 1) {
                App.toast(`L${level} parent must be L${level - 1}`, 'error');
                return;
            }
        }

        const payload = {
            level: level,
            name: name,
            parent_id: parentId,
            code: document.getElementById('addCode')?.value.trim() || undefined,
            process_area_code: document.getElementById('addModule')?.value || undefined,
            scope_status: document.getElementById('addScope')?.value || 'in_scope',
            wave: parseInt(document.getElementById('addWave')?.value, 10) || undefined,
        };

        try {
            await ExploreAPI.levels.create(_pid, payload);
            App.toast(`${name} created`, 'success');
            ['addCode', 'addName', 'addWave'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            await loadHierarchyTab();
        } catch (err) {
            App.toast(err.message || 'Creation failed', 'error');
        }
    }

    function toggleNode(id) {
        if (_expandedNodes.has(id)) _expandedNodes.delete(id);
        else _expandedNodes.add(id);
        rerenderContent();
    }

    function matchesSearch(node) {
        if (!_searchQuery) return true;
        const q = _searchQuery.toLowerCase();
        return (node.name || '').toLowerCase().includes(q) || (node.code || '').toLowerCase().includes(q);
    }

    function matchesFilters(node) {
        if (_filters.area && node.process_area_code !== _filters.area) return false;
        if (_filters.scope && node.scope_status !== _filters.scope) return false;
        return true;
    }

    function setSearch(val) {
        _searchQuery = val || '';
        rerenderContent();
    }

    function setFilter(groupId, value) {
        const nextVal = value || null;
        _filters[groupId] = _filters[groupId] === nextVal ? null : nextVal;
        rerenderContent();
    }

    function onFilterBarChange(update) {
        if (update._clearAll) {
            _filters = { area: null, scope: null };
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
        rerenderContent();
    }

    function setViewMode(mode) {
        _viewMode = mode;
        rerenderContent();
    }

    function rerenderContent() {
        const el = document.getElementById('hierarchyContent');
        if (!el) return;
        el.innerHTML = _viewMode === 'tree' ? renderTreeContent() : renderTableView();
    }

    /**
     * Step indicator — for wizard flows.
     * @param {Array<{label: string}>} steps - Step definitions
     * @param {number} activeIdx - Active step index (0-based)
     */
    function _stepIndicator(steps, activeIdx) {
        return `<div class="pg-steps">` + steps.map((s, i) => `
            <div class="pg-steps__item${i === activeIdx ? ' pg-steps__item--active' : i < activeIdx ? ' pg-steps__item--done' : ''}">
                <div class="pg-steps__circle">${i < activeIdx ? '✓' : i + 1}</div>
                <span class="pg-steps__label">${s.label}</span>
                ${i < steps.length - 1 ? '<div class="pg-steps__connector"></div>' : ''}
            </div>
        `).join('') + `</div>`;
    }

    function renderPlaceholder() {
        const c = document.getElementById('setupContent');
        const label = _currentTab.charAt(0).toUpperCase() + _currentTab.slice(1);
        c.innerHTML = PGEmptyState.html({ icon: 'settings', title: `${label} — coming soon`, description: 'This tab will be available in a future sprint.' });
    }

    function flattenTree(nodes, result = []) {
        for (const n of nodes) {
            result.push(n);
            if (n.children && n.children.length) flattenTree(n.children, result);
        }
        return result;
    }

    return {
        render,
        switchTab,
        selectProject,
        toggleNode,
        setSearch,
        setFilter,
        onFilterBarChange,
        setViewMode,
        openCreateDialog,
        submitCreate,
        openEditDialog,
        submitEdit,
        confirmDelete,
        executeDelete,
        openTemplateImport,
        toggleTemplateAll,
        submitTemplateImport,
        openAISuggested,
        submitInlineAdd,
        openBulkEntry,
        _setBulkMode,
        _updateGridRow,
        _clearGridRow,
        _addGridRows,
        _parsePaste,
        _submitBulk,
        _downloadTemplate,
    };
})();
