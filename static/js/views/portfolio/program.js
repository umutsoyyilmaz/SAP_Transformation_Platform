/**
 * SAP Transformation Management Platform
 * Program View — portfolio/governance view for a program.
 *
 * Tabs: Overview | Projects
 */

const ProgramView = (() => {
    const PLATFORM_PERMISSION_SOURCE = 'platformPermissions';
    let programs = [];
    let currentProgram = null;
    let currentProjects = [];
    let currentTab = 'overview';

    async function _preloadPlatformPermissions() {
        if (typeof RoleNav === 'undefined' || typeof RoleNav.preloadSource !== 'function') {
            return null;
        }
        return RoleNav.preloadSource(PLATFORM_PERMISSION_SOURCE);
    }

    function _can(permission) {
        return typeof RoleNav !== 'undefined'
            && typeof RoleNav.canSyncInSource === 'function'
            && RoleNav.canSyncInSource(PLATFORM_PERMISSION_SOURCE, permission);
    }

    function _canCreateProgram() {
        return _can('programs.create');
    }

    function _canEditProgram() {
        return _can('programs.edit');
    }

    function _canDeleteProgram() {
        return _can('programs.delete');
    }

    function _canCreateProject() {
        return _can('projects.create');
    }

    function _canEditProject() {
        return _can('projects.edit');
    }

    function _canDeleteProject() {
        return _can('projects.delete');
    }

    function _guardPlatformPermission(permission, message) {
        if (_can(permission)) return true;
        App.toast(message, 'warning');
        return false;
    }

    // ── Render program list ──────────────────────────────────────────────
    async function render() {
        currentProgram = null;
        currentTab = 'overview';
        const main = document.getElementById('mainContent');
        const activeProgram = App.getActiveProgram();
        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Programs' }])}
                <div class="pg-view-header__row program-header-spacer">
                    <h2 class="pg-view-title program-title-reset">Programs</h2>
                    ${_canCreateProgram()
                        ? '<button class="pg-btn pg-btn--primary" onclick="ProgramView.showCreateModal()">+ New Program</button>'
                        : '<span class="program-card__active-label">Programs are read only</span>'}
                </div>
            </div>
            ${activeProgram ? `<div class="program-active-banner">
                <span>✅ Active: <strong>${escHtml(activeProgram.name)}</strong></span>
                <button class="btn btn-secondary btn-sm" onclick="ProgramView.clearActiveProgram()">Clear Selection</button>
            </div>` : `<div class="program-select-banner">
                <span>⚠️ No program selected — choose one below to get started</span>
            </div>`}
            <div class="program-filters">
                <input type="text" id="programSearchInput" class="pg-input program-search" placeholder="Search programs..."
                       oninput="ProgramView._filterCards()">
                <select id="programStatusFilter" class="pg-select program-status-filter" onchange="ProgramView._filterCards()">
                    <option value="">All statuses</option>
                    <option value="planning">Planning</option>
                    <option value="active">Active</option>
                    <option value="on_hold">On Hold</option>
                    <option value="completed">Completed</option>
                    <option value="cancelled">Cancelled</option>
                </select>
            </div>
            <div id="programCardContainer">
                <div class="program-loading"><div class="spinner"></div></div>
            </div>
        `;
        await _preloadPlatformPermissions();
        await loadPrograms();
    }

    async function loadPrograms() {
        try {
            programs = await API.get('/programs');
            renderCards();
        } catch (err) {
            document.getElementById('programCardContainer').innerHTML =
                PGEmptyState.html({ icon: 'programs', title: 'Failed to load', description: err.message });
        }
    }

    function renderCards() {
        const container = document.getElementById('programCardContainer');
        const activeProgram = App.getActiveProgram();

        if (programs.length === 0) {
            container.innerHTML = PGEmptyState.html({
                icon: 'programs',
                title: 'No programs yet',
                description: 'Create your first SAP transformation program.',
                action: _canCreateProgram() ? { label: '+ New Program', onclick: 'ProgramView.showCreateModal()' } : undefined,
            });
            return;
        }

        container.innerHTML = `
            <div class="program-card-grid">
                ${programs.map(p => {
                    const isActive = activeProgram && activeProgram.id === p.id;
                    return `
                    <div class="program-card program-card--interactive ${isActive ? 'program-card--active' : ''}" onclick="ProgramView.openDetail(${p.id})">
                    <div class="program-card__header">
                            <div class="program-card__title">${escHtml(p.name)}</div>
                            ${PGStatusRegistry.badge(p.status)}
                        </div>
                        <div class="program-card__body">
                            <div class="program-card__meta">
                                <span>🏢 ${escHtml(p.customer_name || 'Customer not set')}</span>
                                <span>👤 ${escHtml(p.sponsor_name || 'Sponsor not set')}</span>
                                <span>🧭 ${escHtml(p.code || 'No code')}</span>
                            </div>
                            <div class="program-card__desc">${escHtml(p.description || 'No description')}</div>
                            <div class="program-card__timeline">
                                ${p.start_date ? `<span>📅 ${p.start_date}</span>` : ''}
                                ${p.go_live_date ? `<span>🚀 Go-Live: ${p.go_live_date}</span>` : ''}
                            </div>
                        </div>
                        <div class="program-card__actions" onclick="event.stopPropagation()">
                            ${isActive
                                ? '<span class="program-card__active-label">✅ Active Program</span>'
                                : `<button class="btn btn-primary btn-sm" onclick="ProgramView.selectProgram(${p.id})">Select & Open</button>`
                            }
                            ${_canDeleteProgram() ? `<button class="btn btn-danger btn-sm" onclick="ProgramView.deleteProgram(${p.id})">Delete</button>` : ''}
                        </div>
                    </div>`;
                }).join('')}
            </div>`;
    }

    function _filterCards() {
        const search = (document.getElementById('programSearchInput')?.value || '').toLowerCase();
        const statusFilter = document.getElementById('programStatusFilter')?.value || '';
        const cards = document.querySelectorAll('.program-card');
        cards.forEach(card => {
            const title = (card.querySelector('.program-card__title')?.textContent || '').toLowerCase();
            const desc = (card.querySelector('.program-card__desc')?.textContent || '').toLowerCase();
            const matchesSearch = !search || title.includes(search) || desc.includes(search);
            const badge = card.querySelector('.pg-badge');
            const cardStatus = badge ? badge.textContent.trim().toLowerCase().replace(/\s+/g, '_') : '';
            const matchesStatus = !statusFilter || cardStatus === statusFilter;
            card.style.display = (matchesSearch && matchesStatus) ? '' : 'none';
        });
    }

    async function selectProgram(id) {
        const p = programs.find(x => x.id === id);
        if (!p) return;
        App.setActiveProgram(p);
        App.toast(`Program "${p.name}" selected`, 'success');
        await render();
    }

    async function clearActiveProgram() {
        App.setActiveProgram(null);
        App.toast('Program selection cleared', 'info');
        await render();
    }

    // ═════════════════════════════════════════════════════════════════════
    // DETAIL VIEW (tabbed)
    // ═════════════════════════════════════════════════════════════════════

    async function openDetail(id) {
        await _preloadPlatformPermissions();
        try {
            currentProgram = await API.get(`/programs/${id}`);
        } catch (err) {
            App.toast(err.message, 'error');
            return;
        }
        try {
            currentProjects = await API.get(`/programs/${id}/projects`);
        } catch {
            currentProjects = [];
        }
        renderDetail();
    }

    function renderDetail() {
        const p = currentProgram;
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div data-testid="program-detail-page">
            <div class="page-header program-detail-header">
                <div class="program-detail-heading">
                    <button class="btn btn-secondary btn-sm program-back-btn" onclick="ProgramView.render()">← Back</button>
                    <span class="program-detail-title">${escHtml(p.name)}</span>
                    <span class="badge badge-${p.status} program-badge-spacer">${p.status}</span>
                </div>
                <div class="program-detail-header__actions">
                    <button class="btn btn-secondary" onclick="App.navigate('timeline')">📅 Portfolio Timeline</button>
                    ${_canEditProgram() ? `<button class="btn btn-primary" onclick="ProgramView.showEditModal(${p.id})">Edit Program</button>` : '<span class="program-card__active-label">Program profile is read only</span>'}
                </div>
            </div>

            <div class="tabs" id="programTabs" data-testid="program-detail-tabs">
                <button class="tab-btn ${currentTab === 'overview' ? 'active' : ''}" data-tab="overview">Overview</button>
                <button class="tab-btn ${currentTab === 'projects' ? 'active' : ''}" data-tab="projects">Projects</button>
            </div>
            <div id="tabContent" class="card program-tab-card"></div>
            </div>
        `;

        // Tab click handlers
        document.querySelectorAll('#programTabs .tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                currentTab = btn.dataset.tab;
                document.querySelectorAll('#programTabs .tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderTab();
            });
        });

        renderTab();
    }

    function renderTab() {
        const container = document.getElementById('tabContent');
        switch (currentTab) {
            case 'overview':    renderOverviewTab(container); break;
            case 'projects':    renderProjectsTab(container); break;
            default:
                currentTab = 'overview';
                renderOverviewTab(container);
                break;
        }
    }

    // ── Overview Tab ─────────────────────────────────────────────────────
    function renderOverviewTab(container) {
        const p = currentProgram;
        const projects = currentProjects || [];
        const activeProject = App.getActiveProject();
        const defaultProject = projects.find(project => project.is_default);
        const activeProjects = projects.filter(project => project.status === 'active');
        container.innerHTML = `
            <div class="kpi-row">
                <div class="kpi-card">
                    <div class="kpi-card__value">${projects.length}</div>
                    <div class="kpi-card__label">Projects</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${projects.filter(project => project.status === 'active').length}</div>
                    <div class="kpi-card__label">Active Projects</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${defaultProject ? escHtml(defaultProject.code || defaultProject.name || 'Yes') : '—'}</div>
                    <div class="kpi-card__label">Default Project</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-card__value">${activeProject && activeProject.program_id === p.id ? escHtml(activeProject.code || activeProject.name || 'Set') : '—'}</div>
                    <div class="kpi-card__label">Selected Project</div>
                </div>
            </div>
            <div class="context-guard-banner program-section-stack">
                <span>
                    This page is now focused on <strong>program portfolio</strong> data.
                    Execution setup such as phases, workstreams, team, and committees lives inside each project.
                </span>
                <button class="btn btn-primary btn-sm" onclick="ProgramView.openProjectsTab()">Open Projects</button>
            </div>
            <div class="detail-grid program-section-stack">
                <div class="detail-section">
                    <h3>Execution Setup Ownership</h3>
                    <dl class="detail-list">
                        <dt>Canonical Workspace</dt><dd>Project Setup</dd>
                        <dt>Setup Scope</dt><dd>Project / Wave owned</dd>
                        <dt>Portfolio Role</dt><dd>Program summary and project launchpad</dd>
                        <dt>Open From</dt><dd>Projects tab → “Open Setup”</dd>
                    </dl>
                </div>
                <div class="detail-section">
                    <h3>Project Readiness Lens</h3>
                    ${projects.length === 0 ? `
                        <div class="program-muted-copy">Create the first project to start execution setup.</div>
                    ` : `
                        <dl class="detail-list">
                            <dt>Default Project</dt><dd>${defaultProject ? `${escHtml(defaultProject.code || '')} ${escHtml(defaultProject.name || '')}` : '—'}</dd>
                            <dt>Active Projects</dt><dd>${activeProjects.length}</dd>
                            <dt>Selected Project</dt><dd>${activeProject && activeProject.program_id === p.id ? `${escHtml(activeProject.code || '')} ${escHtml(activeProject.name || '')}` : '—'}</dd>
                            <dt>Next Action</dt><dd>${activeProject && activeProject.program_id === p.id ? 'Open selected project setup' : 'Select a project from the Projects tab'}</dd>
                        </dl>
                    `}
                </div>
            </div>
            <div class="detail-grid">
                <div class="detail-section">
                    <h3>Program Profile & Governance</h3>
                    <dl class="detail-list">
                        <dt>Description</dt><dd>${escHtml(p.description || '—')}</dd>
                        <dt>Program Code</dt><dd>${escHtml(p.code || '—')}</dd>
                        <dt>Customer</dt><dd>${escHtml(p.customer_name || '—')}</dd>
                        <dt>Industry</dt><dd>${escHtml(p.customer_industry || '—')}</dd>
                        <dt>Country</dt><dd>${escHtml(p.customer_country || '—')}</dd>
                        <dt>Sponsor</dt><dd>${escHtml(p.sponsor_name || '—')}</dd>
                        <dt>Sponsor Title</dt><dd>${escHtml(p.sponsor_title || '—')}</dd>
                        <dt>Program Director</dt><dd>${escHtml(p.program_director || '—')}</dd>
                    </dl>
                </div>
                <div class="detail-section">
                    <h3>Portfolio Health</h3>
                    <dl class="detail-list">
                        <dt>Priority</dt><dd><span class="badge badge-${p.priority}">${p.priority}</span></dd>
                        <dt>SteerCo</dt><dd>${escHtml(humanizeOption(p.steerco_frequency || 'monthly'))}</dd>
                        <dt>Overall RAG</dt><dd>${p.overall_rag ? escHtml(humanizeOption(p.overall_rag)) : '—'}</dd>
                        <dt>Budget</dt><dd>${formatBudget(p.total_budget, p.currency)}</dd>
                        <dt>Start Date</dt><dd>${p.start_date || '—'}</dd>
                        <dt>End Date</dt><dd>${p.end_date || '—'}</dd>
                        <dt>Go-Live Date</dt><dd>${p.go_live_date || '—'}</dd>
                        <dt>Created</dt><dd>${p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}</dd>
                    </dl>
                </div>
            </div>
            <div class="detail-grid program-section-stack--top">
                <div class="detail-section">
                    <h3>How To Use This Page</h3>
                    <ul class="program-list-copy">
                        <li>Use <strong>Projects</strong> to create rollout waves, countries, or release tracks.</li>
                        <li>Open a project to manage execution setup like methodology, product scope, phases, team, workstreams, and governance.</li>
                        <li>Keep customer, sponsor, budget, and steering context here at program level.</li>
                        <li>Use the portfolio timeline here when you want a cross-project view of the program.</li>
                    </ul>
                </div>
                <div class="detail-section">
                    <h3>Project Focus</h3>
                    ${projects.length === 0 ? `
                        <div class="program-muted-copy">No projects created yet. Add the first project to start execution planning.</div>
                    ` : `
                        <dl class="detail-list">
                            <dt>Default Project</dt><dd>${defaultProject ? `${escHtml(defaultProject.code || '')} ${escHtml(defaultProject.name || '')}` : '—'}</dd>
                            <dt>Selected Project</dt><dd>${activeProject && activeProject.program_id === p.id ? `${escHtml(activeProject.code || '')} ${escHtml(activeProject.name || '')}` : '—'}</dd>
                            <dt>Project Setup</dt><dd>Available from the Projects tab via “Open Setup”.</dd>
                        </dl>
                    `}
                </div>
            </div>
        `;
    }

    function renderProjectsTab(container) {
        const projects = currentProjects || [];
        if (projects === null) {
            container.innerHTML = '<div class="program-loading-block"><div class="spinner"></div><p>Loading projects...</p></div>';
            return;
        }
        const activeProject = App.getActiveProject();
        const hasDefault = projects.some(p => p.is_default);
        const teamMembers = currentProgram?.team_members || [];
        container.innerHTML = `
            <div data-testid="program-projects-tab">
            <div class="program-projects-head">
                <div>
                    <h3 class="program-section-title">Projects</h3>
                    <p class="program-projects-subcopy">
                        Create projects here, then open each one in <strong>Project Setup</strong> to manage methodology, project type, SAP product, deployment, phases, team, workstreams, committees, and hierarchy.
                    </p>
                </div>
                ${_canCreateProject() ? '<button class="btn btn-primary btn-sm" onclick="ProgramView.showProjectModal()">+ Add Project</button>' : '<span class="program-card__active-label">Projects are read only</span>'}
            </div>
            ${hasDefault ? '' : '<div class="context-guard-banner"><span>No default project configured for this program.</span></div>'}
            ${projects.length === 0
                ? '<div class="empty-state program-empty-state"><div class="empty-state__icon">📦</div><div class="empty-state__title">No projects yet</div></div>'
                : `<table class="data-table" data-testid="program-projects-table">
                    <thead><tr><th>Code</th><th>Name</th><th>Type</th><th>Methodology</th><th>Status</th><th>Owner</th><th>Flags</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${projects.map(p => {
                            const isActive = activeProject && activeProject.id === p.id;
                            const flags = [
                                p.is_default ? '<span class="badge badge-active">DEFAULT</span>' : '',
                                isActive ? '<span class="badge badge-info">ACTIVE</span>' : '',
                            ].filter(Boolean).join(' ');
                            const ownerMember = p.owner_id ? teamMembers.find(m => m.id === p.owner_id) : null;
                            const ownerDisplay = ownerMember ? escHtml(ownerMember.name) : (p.owner_id ? `User #${p.owner_id}` : '—');
                            return `
                                <tr class="${isActive ? 'program-project-row--active' : ''}">
                                    <td><code>${escHtml(p.code || '')}</code></td>
                                    <td><strong>${escHtml(p.name || '')}</strong></td>
                                    <td>${escHtml(p.type || 'implementation')}</td>
                                    <td>${escHtml(p.methodology || '—')}</td>
                                    <td><span class="badge badge-${escHtml((p.status || 'active').toLowerCase())}">${escHtml(p.status || 'active')}</span></td>
                                    <td>${ownerDisplay}</td>
                                    <td>${flags || '—'}</td>
                                    <td>
                                        <div class="program-project-actions">
                                        <button class="btn btn-primary btn-sm" onclick="ProgramView.selectProject(${p.id})">${isActive ? 'Setup' : 'Open'}</button>
                                        ${_canEditProject() ? `<button class="btn btn-secondary btn-sm btn--icon" title="Edit Project" onclick="ProgramView.showProjectModal(${p.id})">✏️</button>` : ''}
                                        ${_canDeleteProject() ? `<button class="btn btn-danger btn-sm btn--icon" title="Delete Project" onclick="ProgramView.deleteProject(${p.id})">🗑</button>` : ''}
                                        </div>
                                    </td>
                                </tr>`;
                        }).join('')}
                    </tbody>
                </table>`
            }
            </div>
        `;
    }


    // ═════════════════════════════════════════════════════════════════════
    // MODALS
    // ═════════════════════════════════════════════════════════════════════

    // ── Program Modal ────────────────────────────────────────────────────
    function showCreateModal() {
        if (!_guardPlatformPermission('programs.create', 'You do not have permission to create programs')) return;
        App.openModal(programFormHtml('Create Program', {}));
    }

    function showEditModal(id) {
        if (!_guardPlatformPermission('programs.edit', 'You do not have permission to edit programs')) return;
        const p = currentProgram || programs.find(x => x.id === id);
        if (!p) return;
        App.openModal(programFormHtml('Edit Program', p));
    }

    function programFormHtml(title, p) {
        const isEdit = !!p.id;
        return `
            <div class="modal-header">
                <h2>${title}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <form id="programForm" onsubmit="ProgramView.handleSubmit(event, ${p.id || 'null'})">
                <div class="form-group">
                    <label>Program Name *</label>
                    <input name="name" required value="${escAttr(p.name || '')}" placeholder="e.g. Meridian Global Transformation">
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Program Code</label>
                        <input name="code" maxlength="20" value="${escAttr(p.code || '')}" placeholder="PGM-001">
                    </div>
                    <div class="form-group">
                        <label>Status</label>
                        <select name="status">
                            ${selectOpts(['planning','active','on_hold','completed','cancelled'], p.status || 'planning')}
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" rows="3" placeholder="Program purpose, transformation scope, and executive context...">${escHtml(p.description || '')}</textarea>
                    <div class="program-form-hint">
                        Capture program-level governance context here. Project-specific setup lives in each project or wave.
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Customer Name</label>
                        <input name="customer_name" maxlength="255" value="${escAttr(p.customer_name || '')}" placeholder="Meridian Industries A.S.">
                    </div>
                    <div class="form-group">
                        <label>Industry</label>
                        <input name="customer_industry" maxlength="100" value="${escAttr(p.customer_industry || '')}" placeholder="Manufacturing">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Customer Country</label>
                        <input name="customer_country" maxlength="100" value="${escAttr(p.customer_country || '')}" placeholder="Turkey">
                    </div>
                    <div class="form-group">
                        <label>Priority</label>
                        <select name="priority">
                            ${selectOpts(['low','medium','high','critical'], p.priority || 'medium')}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Sponsor Name</label>
                        <input name="sponsor_name" maxlength="255" value="${escAttr(p.sponsor_name || '')}" placeholder="Executive Sponsor">
                    </div>
                    <div class="form-group">
                        <label>Sponsor Title</label>
                        <input name="sponsor_title" maxlength="200" value="${escAttr(p.sponsor_title || '')}" placeholder="CIO / Transformation Sponsor">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Program Director</label>
                        <input name="program_director" maxlength="255" value="${escAttr(p.program_director || '')}" placeholder="Program Director">
                    </div>
                    <div class="form-group">
                        <label>SteerCo Frequency</label>
                        <select name="steerco_frequency">
                            ${selectOpts(['weekly','biweekly','monthly','quarterly'], p.steerco_frequency || 'monthly')}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Total Budget</label>
                        <input name="total_budget" type="number" step="0.01" min="0" value="${escAttr(p.total_budget ?? '')}" placeholder="0.00">
                    </div>
                    <div class="form-group">
                        <label>Currency</label>
                        <input name="currency" maxlength="3" value="${escAttr(p.currency || 'EUR')}" placeholder="EUR">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Overall RAG</label>
                        <select name="overall_rag">
                            ${selectOpts(['','green','amber','red'], p.overall_rag || '', { '': 'Not set' })}
                        </select>
                    </div>
                    <div class="form-group"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Start Date</label><input name="start_date" type="date" value="${p.start_date || ''}"></div>
                    <div class="form-group"><label>End Date</label><input name="end_date" type="date" value="${p.end_date || ''}"></div>
                </div>
                <div class="form-group"><label>Go-Live Date</label><input name="go_live_date" type="date" value="${p.go_live_date || ''}"></div>
                <div class="form-group"><label>Strategic Objectives</label><textarea name="strategic_objectives" rows="3" placeholder="What is the transformation trying to achieve?">${escHtml(p.strategic_objectives || '')}</textarea></div>
                <div class="form-group"><label>Success Criteria</label><textarea name="success_criteria" rows="3" placeholder="How will success be measured?">${escHtml(p.success_criteria || '')}</textarea></div>
                <div class="form-group"><label>Key Assumptions</label><textarea name="key_assumptions" rows="3" placeholder="Critical assumptions, constraints, or dependencies">${escHtml(p.key_assumptions || '')}</textarea></div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? 'Update' : 'Create'}</button>
                </div>
            </form>`;
    }

    async function handleSubmit(event, id) {
        event.preventDefault();
        if (id) {
            if (!_guardPlatformPermission('programs.edit', 'You do not have permission to edit programs')) return;
        } else if (!_guardPlatformPermission('programs.create', 'You do not have permission to create programs')) {
            return;
        }
        const data = Object.fromEntries(new FormData(event.target).entries());
        try {
            if (id) {
                const updated = await API.put(`/programs/${id}`, data);
                App.toast('Program updated', 'success');
                // Sync active program badge if this is the active one
                const active = App.getActiveProgram();
                if (active && active.id === id) {
                    App.setActiveProgram(updated);
                }
            } else {
                await API.post('/programs', data);
                App.toast('Program created', 'success');
            }
            App.closeModal();
            if (currentProgram && id) {
                await openDetail(id);
            } else {
                await loadPrograms();
            }
        } catch (err) { App.toast(err.message, 'error'); }
    }

    async function deleteProgram(id) {
        if (!_guardPlatformPermission('programs.delete', 'You do not have permission to delete programs')) return;
        const p = programs.find(x => x.id === id);
        const confirmed = await App.confirmDialog({
            title: 'Delete Program',
            message: `Delete program "${p?.name || 'this program'}"?`,
            confirmLabel: 'Delete',
            testId: 'program-delete-modal',
            confirmTestId: 'program-delete-submit',
            cancelTestId: 'program-delete-cancel',
        });
        if (!confirmed) return;
        try {
            await API.delete(`/programs/${id}`);
            App.toast('Program deleted', 'success');
            // Clear active program if it was the deleted one
            const active = App.getActiveProgram();
            if (active && active.id === id) {
                App.setActiveProgram(null);
            }
            await loadPrograms();
        } catch (err) { App.toast(err.message, 'error'); }
    }


    function showProjectModal(projectId) {
        const permission = projectId ? 'projects.edit' : 'projects.create';
        const message = projectId ? 'You do not have permission to edit projects' : 'You do not have permission to create projects';
        if (!_guardPlatformPermission(permission, message)) return;
        const p = projectId ? (currentProjects || []).find(x => x.id === projectId) : {};
        const isEdit = !!(p && p.id);
        App.openModal(`
            <div class="modal-header">
                <h2>${isEdit ? 'Edit Project' : 'Add Project'}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <form onsubmit="ProgramView.handleProjectSubmit(event, ${p.id || 'null'})">
                <div class="form-row">
                    <div class="form-group"><label>Code *</label><input name="code" required maxlength="50" value="${escAttr(p.code || '')}" placeholder="TR-W1"></div>
                    <div class="form-group"><label>Name *</label><input name="name" required maxlength="200" value="${escAttr(p.name || '')}" placeholder="Turkey Wave 1"></div>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" rows="3" placeholder="Project or wave scope, country, release, or rollout notes...">${escHtml(p.description || '')}</textarea>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Type</label><select name="type">${selectOpts(['implementation','rollout','pilot','template','support'], p.type)}</select></div>
                    <div class="form-group"><label>Status</label><select name="status">${selectOpts(['active','on_hold','completed','cancelled'], p.status || 'active')}</select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Project Type</label><select name="project_type">${selectOpts(['greenfield','brownfield','bluefield','selective_data_transition'], p.project_type || 'greenfield')}</select></div>
                    <div class="form-group"><label>Methodology</label><select name="methodology">${selectOpts(['sap_activate','agile','waterfall','hybrid'], p.methodology || 'sap_activate')}</select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>SAP Product</label><select name="sap_product">${selectOpts(['S/4HANA','SuccessFactors','Ariba','BTP','Other'], p.sap_product || 'S/4HANA')}</select></div>
                    <div class="form-group"><label>Deployment</label><select name="deployment_option">${selectOpts(['on_premise','cloud','hybrid'], p.deployment_option || 'on_premise')}</select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Priority</label><select name="priority">${selectOpts(['low','medium','high','critical'], p.priority || 'medium')}</select></div>
                    <div class="form-group"><label>Wave Number</label><input name="wave_number" type="number" min="1" value="${escAttr(p.wave_number || '')}" placeholder="1"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Owner ID</label><input name="owner_id" type="number" min="1" value="${p.owner_id || ''}" placeholder="optional"></div>
                    <div class="form-group"><label class="program-checkbox-label">Default Project</label><label><input type="checkbox" name="is_default" value="true" ${p.is_default ? 'checked' : ''}> Mark as default</label></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Start Date</label><input name="start_date" type="date" value="${p.start_date || ''}"></div>
                    <div class="form-group"><label>End Date</label><input name="end_date" type="date" value="${p.end_date || ''}"></div>
                </div>
                <div class="form-group"><label>Go-Live Date</label><input name="go_live_date" type="date" value="${p.go_live_date || ''}"></div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? 'Update' : 'Create'}</button>
                </div>
            </form>`);
    }

    async function handleProjectSubmit(event, projectId) {
        event.preventDefault();
        if (projectId) {
            if (!_guardPlatformPermission('projects.edit', 'You do not have permission to edit projects')) return;
        } else if (!_guardPlatformPermission('projects.create', 'You do not have permission to create projects')) {
            return;
        }
        const fd = new FormData(event.target);
        const data = Object.fromEntries(fd.entries());
        data.is_default = fd.has('is_default');
        data.owner_id = data.owner_id ? parseInt(data.owner_id, 10) : null;
        data.code = String(data.code || '').trim().toUpperCase();
        data.name = String(data.name || '').trim();
        if (!data.code || !data.name) {
            App.toast('Code and name are required', 'warning');
            return;
        }
        try {
            if (projectId) {
                await API.put(`/projects/${projectId}`, data);
                App.toast('Project updated', 'success');
            } else {
                await API.post(`/programs/${currentProgram.id}/projects`, data);
                App.toast('Project created', 'success');
            }
            App.closeModal();
            await openDetail(currentProgram.id);
            if (App.getActiveProgram() && App.getActiveProgram().id === currentProgram.id) {
                App.setActiveProgram(App.getActiveProgram(), { silent: true });
            }
        } catch (err) {
            App.toast(err.message, 'error');
        }
    }

    async function selectProject(projectId) {
        const selected = (currentProjects || []).find(p => p.id === projectId);
        if (!selected) return;
        App.setActiveProject({
            id: selected.id,
            name: selected.name,
            code: selected.code,
            program_id: selected.program_id || currentProgram.id,
            tenant_id: selected.tenant_id,
        });
        App.toast(`Project "${selected.name}" selected`, 'success');
        App.navigate('project-setup');
    }

    function openProjectsTab() {
        currentTab = 'projects';
        const active = document.querySelector('#programTabs .tab-btn[data-tab="projects"]');
        document.querySelectorAll('#programTabs .tab-btn').forEach(btn => btn.classList.remove('active'));
        if (active) active.classList.add('active');
        renderTab();
    }

    async function deleteProject(projectId) {
        if (!_guardPlatformPermission('projects.delete', 'You do not have permission to delete projects')) return;
        const project = (currentProjects || []).find(p => p.id === projectId);
        if (!project) return;

        if (project.is_default) {
            const replacements = (currentProjects || []).filter(p => p.id !== projectId);
            if (replacements.length === 0) {
                App.toast('Default project cannot be deleted without a replacement project.', 'warning');
                return;
            }
            const options = replacements.map(p => `<option value="${p.id}">${escHtml((p.code || '') + ' - ' + (p.name || ''))}</option>`).join('');
            App.openModal(`
                <div class="modal-header">
                    <h2>Replace Default Project</h2>
                    <button class="modal-close" onclick="App.closeModal()">&times;</button>
                </div>
                <form onsubmit="ProgramView.confirmDefaultProjectReplacement(event, ${projectId})">
                    <div class="form-group">
                        <label>Current default project</label>
                        <div><strong>${escHtml(project.code)} - ${escHtml(project.name)}</strong></div>
                    </div>
                    <div class="form-group">
                        <label>Replacement default project *</label>
                        <select name="replacement_project_id" required>
                            <option value="">Select replacement</option>
                            ${options}
                        </select>
                    </div>
                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                        <button type="submit" class="btn btn-danger">Replace and Delete</button>
                    </div>
                </form>
            `);
            return;
        }

        const confirmed = await App.confirmDialog({
            title: 'Delete Project',
            message: `Delete project "${project.name}"?`,
            confirmLabel: 'Delete',
            testId: 'project-delete-modal',
            confirmTestId: 'project-delete-submit',
            cancelTestId: 'project-delete-cancel',
        });
        if (!confirmed) return;
        try {
            await API.delete(`/projects/${projectId}`);
            const activeProject = App.getActiveProject();
            if (activeProject && activeProject.id === projectId) {
                App.setActiveProject(null);
            }
            App.toast('Project deleted', 'success');
            await openDetail(currentProgram.id);
            if (App.getActiveProgram() && App.getActiveProgram().id === currentProgram.id) {
                App.setActiveProgram(App.getActiveProgram(), { silent: true });
            }
        } catch (err) {
            App.toast(err.message, 'error');
        }
    }

    async function confirmDefaultProjectReplacement(event, defaultProjectId) {
        event.preventDefault();
        if (!_guardPlatformPermission('projects.delete', 'You do not have permission to delete projects')) return;
        if (!_guardPlatformPermission('projects.edit', 'You do not have permission to change the default project')) return;
        const replacementId = Number(new FormData(event.target).get('replacement_project_id'));
        if (!replacementId) {
            App.toast('Replacement project is required', 'warning');
            return;
        }
        try {
            await API.put(`/projects/${replacementId}`, { is_default: true });
            await API.delete(`/projects/${defaultProjectId}`);
            const activeProject = App.getActiveProject();
            if (activeProject && activeProject.id === defaultProjectId) {
                const replacement = (currentProjects || []).find(p => p.id === replacementId);
                if (replacement) {
                    App.setActiveProject({
                        id: replacement.id,
                        name: replacement.name,
                        code: replacement.code,
                        program_id: replacement.program_id || currentProgram.id,
                    });
                } else {
                    App.setActiveProject(null);
                }
            }
            App.closeModal();
            App.toast('Default project replaced and old default deleted', 'success');
            await openDetail(currentProgram.id);
            if (App.getActiveProgram() && App.getActiveProgram().id === currentProgram.id) {
                App.setActiveProgram(App.getActiveProgram(), { silent: true });
            }
        } catch (err) {
            App.toast(err.message, 'error');
        }
    }


    // ═════════════════════════════════════════════════════════════════════
    // UTILITIES
    // ═════════════════════════════════════════════════════════════════════

    function escHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }
    function escAttr(s) { return (s || '').replace(/"/g, '&quot;'); }
    function humanizeOption(value) {
        return String(value || '')
            .replace(/_/g, ' ')
            .replace(/\b\w/g, c => c.toUpperCase());
    }
    function selectOpts(options, selected, labels = {}) {
        return options.map(o =>
            `<option value="${o}" ${o === selected ? 'selected' : ''}>${escHtml(labels[o] || humanizeOption(o) || '—')}</option>`
        ).join('');
    }
    function formatBudget(amount, currency) {
        if (amount === null || amount === undefined || amount === '') return '—';
        const numeric = Number(amount);
        if (Number.isNaN(numeric)) return `${escHtml(String(amount))} ${escHtml(currency || '')}`.trim();
        return `${numeric.toLocaleString()} ${escHtml(currency || 'EUR')}`.trim();
    }

    // ── Public API ───────────────────────────────────────────────────────
    return {
        render, openDetail, selectProgram, clearActiveProgram,
        showCreateModal, showEditModal, handleSubmit, deleteProgram,
        showProjectModal, handleProjectSubmit, deleteProject,
        confirmDefaultProjectReplacement, selectProject, openProjectsTab,
        _filterCards,
    };
})();
