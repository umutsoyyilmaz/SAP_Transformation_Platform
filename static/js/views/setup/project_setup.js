/**
 * SAP Transformation Management Platform
 * Project Setup View — Professional UI (v2).
 */

const ProjectSetupView = (() => {
    'use strict';

    const esc = ExpUI.esc;
    const _shell = () => (typeof ProjectSetupShell !== 'undefined' ? ProjectSetupShell : null);

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
    let _l4ByL3 = {};
    let _hierarchyMeta = { total: 0, unfilteredTotal: 0 };
    let _hierarchyStats = { total: 0, l1: 0, l2: 0, l3: 0, l4: 0, in_scope: 0 };
    let _hierarchyReloadTimer = null;
    let _bulkMode = 'grid';
    let _gridRows = [];
    let _pasteText = '';
    let _parsedRows = [];
    let _projectWorkstreams = [];
    let _projectCommittees = [];
    let _workstreamEditingId = null;
    let _committeeEditingId = null;
    let _pendingConfirmAction = null;

    const MODULES = ['FI', 'CO', 'MM', 'SD', 'PP', 'QM', 'EWM', 'HR', 'BC'];

    function _openConfirmModal({ title, message, confirmLabel = 'Confirm', onConfirm = null, danger = true }) {
        _pendingConfirmAction = typeof onConfirm === 'function' ? onConfirm : null;
        App.openModal(`
            <div data-testid="project-setup-confirm-modal">
                <div class="modal-header">
                    <h2>${esc(title || 'Confirm action')}</h2>
                    <button class="modal-close" onclick="ProjectSetupView._cancelConfirmModal()" title="Close">&times;</button>
                </div>
                <div style="padding:20px 24px 8px">
                    <p style="margin:0;font-size:14px;color:var(--pg-color-text-secondary);line-height:1.6">${esc(message || 'Please confirm this action.')}</p>
                </div>
                <div class="form-actions" style="padding:16px 24px 24px">
                    <button type="button" class="btn btn-secondary" data-testid="project-setup-confirm-cancel" onclick="ProjectSetupView._cancelConfirmModal()">Cancel</button>
                    <button
                        type="button"
                        class="btn ${danger ? 'btn-danger' : 'btn-primary'}"
                        data-testid="project-setup-confirm-submit"
                        onclick="ProjectSetupView._runConfirmAction()"
                    >${esc(confirmLabel)}</button>
                </div>
            </div>
        `);
    }

    function _cancelConfirmModal() {
        _pendingConfirmAction = null;
        App.closeModal();
    }

    async function _runConfirmAction() {
        const action = _pendingConfirmAction;
        _pendingConfirmAction = null;
        App.closeModal();
        if (typeof action === 'function') {
            await action();
        }
    }

    const TEMPLATE_L1 = [
        { code: 'L1-OTC', name: 'Order to Cash', module: 'SD', desc: 'End-to-end sales processes', stats: '2 L2 · 10 L3 · 40 L4' },
        { code: 'L1-PTP', name: 'Procure to Pay', module: 'MM', desc: 'Procurement and invoice cycle', stats: '2 L2 · 10 L3 · 40 L4' },
        { code: 'L1-RTR', name: 'Record to Report', module: 'FI', desc: 'Financial close and reporting', stats: '2 L2 · 10 L3 · 40 L4' },
        { code: 'L1-PTD', name: 'Plan to Deliver', module: 'PP', desc: 'Production planning and delivery', stats: '2 L2 · 10 L3 · 40 L4' },
        { code: 'L1-HCM', name: 'Hire to Retire', module: 'HR', desc: 'Talent lifecycle and payroll', stats: '2 L2 · 10 L3 · 40 L4' },
    ];

    const HIERARCHY_MUTATION_CONTEXT = 'project_setup';

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
            <div data-testid="project-setup-page">
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Program Management' }, { label: 'Project Setup' }])}
                <h2 class="pg-view-title">Project Setup</h2>
                <p class="project-setup-subtitle">Program selected, project-specific setup tabs below</p>
            </div>
            <div id="projectSetupContextCard" data-testid="project-setup-context" class="card project-setup-context-card">
                <div class="project-setup-context-card__row">
                    <div class="project-setup-context-card__field">
                        <div class="project-setup-context-card__label">Program</div>
                        <div class="project-setup-context-card__value">${esc(_activeProgram?.name || '—')}</div>
                    </div>
                    <div class="project-setup-context-card__field project-setup-context-card__field--project">
                        <label for="projectSetupProjectSelect" class="project-setup-context-card__label">Project</label>
                        <select id="projectSetupProjectSelect" class="pg-input" onchange="ProjectSetupView.selectProject(this.value)">
                            <option value="">Select project...</option>
                        </select>
                    </div>
                </div>
                <div id="projectSetupContextMeta" class="project-setup-context-card__meta"></div>
            </div>
            <div id="projectSetupProfile"></div>
            ${_shell() ? _shell().renderTabs(_currentTab) : ''}
            <div id="setupContent">
                <div class="pg-loading-state"><div class="spinner"></div></div>
            </div>
            </div>`;

        _loadProgramContext().then(() => {
            _renderContextCard();
            loadCurrentTab();
        });
    }

    function switchTab(tab) {
        _currentTab = _shell() ? _shell().normalizeTab(tab) : tab;
        document.querySelectorAll('.exp-tab').forEach((button) => {
            button.classList.toggle('exp-tab--active', button.dataset.setupTab === _currentTab);
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
        _currentTab = _shell() ? _shell().normalizeTab(_currentTab) : _currentTab;
    }

    function _renderContextCard() {
        const select = document.getElementById('projectSetupProjectSelect');
        const meta = document.getElementById('projectSetupContextMeta');
        const profile = document.getElementById('projectSetupProfile');
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
        if (profile) {
            const full = _activeProject
                ? _programProjects.find((p) => Number(p.id) === Number(_activeProject.id))
                : null;
            profile.innerHTML = _shell() ? _shell().renderProfileStrip(full) : '';
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
        _currentTab = _shell() ? _shell().normalizeTab(_currentTab) : _currentTab;
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
        if (_currentTab === 'workstreams') {
            renderWorkstreamsTab();
            return;
        }
        if (_currentTab === 'committees') {
            renderCommitteesTab();
            return;
        }
        if (_currentTab === 'timeline') {
            renderTimelineTab();
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
        ProjectSetupInfo.renderView({ container: c, project, activeProgram: _activeProgram });
    }

    function _openProjectInfoEdit() {
        const project = _programProjects.find((p) => Number(p.id) === Number(_activeProject?.id));
        if (!project) return;
        const c = document.getElementById('setupContent');
        if (!c) return;
        ProjectSetupInfo.renderEdit({ container: c, project });
    }

    async function _saveProjectInfo() {
        const project = _programProjects.find((p) => Number(p.id) === Number(_activeProject?.id));
        if (!project) return;
        const formState = ProjectSetupInfo.readEditState();
        if (formState.error) {
            App.toast(formState.error, 'error');
            return;
        }

        const btn = document.getElementById('piSaveBtn');
        if (btn) { btn.textContent = 'Saving…'; btn.disabled = true; }

        try {
            const updated = await API.put(`/projects/${project.id}`, formState.payload);
            // Update local cache
            const idx = _programProjects.findIndex(p => Number(p.id) === Number(project.id));
            if (idx >= 0) _programProjects[idx] = { ..._programProjects[idx], ...updated };
            // Update active project name in context if changed
            if (updated.name !== project.name || updated.code !== project.code) {
                App.setActiveProject({ ...App.getActiveProject(), name: updated.name, code: updated.code });
                _activeProject = App.getActiveProject();
                _renderContextCard();
            }
            App.toast('Project saved successfully', 'success');
            renderProjectInfoTab();
        } catch (err) {
            App.toast(err.message || 'Save failed', 'error');
            if (btn) { btn.textContent = '💾 Save'; btn.disabled = false; }
        }
    }



    /* ─── Methodology Tab state ─── */
    let _methodPhases = [];
    let _methEditingPhaseId = null;

    async function renderMethodologyTab() {
        const c = document.getElementById('setupContent');
        if (!c || !_activeProject) { renderProjectRequiredGuard(); return; }
        c.innerHTML = `<div class="pg-loading-state"><div class="spinner"></div></div>`;

        try {
            const res = await API.get(`/programs/${_pid}/phases?project_id=${_activeProject.id}`);
            _methodPhases = Array.isArray(res) ? res : [];
        } catch {
            _methodPhases = [];
        }
        _methEditingPhaseId = null;
        _renderMethodologyContent(c);
    }

    function _renderMethodologyContent(c) {
        const proj = _programProjects.find(p => Number(p.id) === Number(_activeProject?.id)) || {};

        /* ── Methodology config labels ── */
        const methLabels = {
            sap_activate: 'SAP Activate', agile: 'Agile', waterfall: 'Waterfall', hybrid: 'Hybrid',
        };
        const typeLabels = {
            greenfield: 'Greenfield', brownfield: 'Brownfield',
            bluefield: 'Bluefield', selective_data_transition: 'Selective Data Transition',
        };
        const methColor = { sap_activate: '#0070f3', agile: '#22c55e', waterfall: '#6366f1', hybrid: '#f59e0b' };
        const meth = proj.methodology || 'sap_activate';
        const pType = proj.project_type || 'greenfield';

        /* ── Phase status config ── */
        const phaseStatusColor = {
            not_started: '#9ca3af', in_progress: '#3b82f6', completed: '#22c55e', skipped: '#f59e0b',
        };
        const phaseStatusLabel = {
            not_started: 'Not Started', in_progress: 'In Progress', completed: 'Completed', skipped: 'Skipped',
        };

        const totalPhases = _methodPhases.length;
        const completedPhases = _methodPhases.filter(p => p.status === 'completed').length;
        const overallPct = totalPhases > 0 ? Math.round((completedPhases / totalPhases) * 100) : 0;

        c.innerHTML = `
            <!-- ── Methodology Config Card ── -->
            <div class="card" style="padding:20px;margin-bottom:16px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <h3 style="margin:0">Methodology & Approach</h3>
                    <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ProjectSetupView._toggleMethEdit()" id="methEditBtn">✏️ Edit</button>
                </div>

                <!-- View Mode -->
                <div id="methViewMode">
                    <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start">
                        <div style="flex:1;min-width:200px">
                            <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--pg-color-text-secondary);margin-bottom:8px">Methodology</div>
                            <div style="display:flex;align-items:center;gap:8px">
                                <span style="width:12px;height:12px;border-radius:50%;background:${methColor[meth] || '#9ca3af'};flex-shrink:0"></span>
                                <span style="font-size:15px;font-weight:600">${esc(methLabels[meth] || meth)}</span>
                            </div>
                        </div>
                        <div style="flex:1;min-width:200px">
                            <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--pg-color-text-secondary);margin-bottom:8px">Project Type</div>
                            <div style="font-size:14px;font-weight:500">${esc(typeLabels[pType] || pType)}</div>
                        </div>
                        <div style="flex:1;min-width:200px">
                            <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--pg-color-text-secondary);margin-bottom:8px">SAP Product</div>
                            <div style="font-size:14px;font-weight:500">${esc(proj.sap_product || '—')}</div>
                        </div>
                        <div style="flex:1;min-width:200px">
                            <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--pg-color-text-secondary);margin-bottom:8px">Deployment</div>
                            <div style="font-size:14px;font-weight:500">${esc(proj.deployment_option || '—')}</div>
                        </div>
                    </div>
                </div>

                <!-- Edit Mode (hidden by default) -->
                <div id="methEditMode" style="display:none">
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                        <div class="form-group">
                            <label class="form-label">Methodology</label>
                            <select id="meth_methodology" class="pg-input" style="width:100%">
                                ${['sap_activate', 'agile', 'waterfall', 'hybrid'].map(o =>
            `<option value="${o}" ${meth === o ? 'selected' : ''}>${methLabels[o] || o}</option>`
        ).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Project Type</label>
                            <select id="meth_project_type" class="pg-input" style="width:100%">
                                ${['greenfield', 'brownfield', 'bluefield', 'selective_data_transition'].map(o =>
            `<option value="${o}" ${pType === o ? 'selected' : ''}>${typeLabels[o] || o}</option>`
        ).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">SAP Product</label>
                            <select id="meth_sap_product" class="pg-input" style="width:100%">
                                ${['S/4HANA', 'SuccessFactors', 'Ariba', 'BTP', 'Other'].map(o =>
            `<option value="${o}" ${(proj.sap_product || 'S/4HANA') === o ? 'selected' : ''}>${o}</option>`
        ).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Deployment Option</label>
                            <select id="meth_deployment_option" class="pg-input" style="width:100%">
                                ${['on_premise', 'cloud', 'hybrid'].map(o =>
            `<option value="${o}" ${(proj.deployment_option || 'on_premise') === o ? 'selected' : ''}>${o.replace('_', ' ')}</option>`
        ).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="project-setup-actions-row">
                        <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ProjectSetupView._toggleMethEdit()">Cancel</button>
                        <button class="pg-btn pg-btn--primary pg-btn--sm" id="methSaveBtn" onclick="ProjectSetupView._saveMethConfig()">💾 Save</button>
                    </div>
                </div>
            </div>

            <!-- ── Overall Phase Progress ── -->
            ${totalPhases > 0 ? `
            <div class="card project-setup-card project-setup-progress-card project-setup-card--spaced">
                <div class="project-setup-progress-card__header">
                    <span class="project-setup-progress-card__label">Overall Phase Progress</span>
                    <span class="project-setup-progress-card__meta">${completedPhases}/${totalPhases} phases completed</span>
                </div>
                <div class="project-setup-progress-card__track">
                    <div class="project-setup-progress-card__fill" style="width:${overallPct}%"></div>
                </div>
                <div class="project-setup-progress-card__value">${overallPct}%</div>
            </div>` : ''}

            <!-- ── Phases Card ── -->
            <div class="card project-setup-card" data-testid="project-setup-team">
                <div class="project-setup-card__header">
                    <div>
                        <h3 class="project-setup-card__title">Lifecycle Phases</h3>
                        <p class="project-setup-card__subtitle">${totalPhases} phase${totalPhases !== 1 ? 's' : ''} defined</p>
                    </div>
                    <div class="project-setup-card__actions">
                        ${meth === 'sap_activate' ? `<button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ProjectSetupView._seedSAPActivatePhases()" title="Create SAP Activate default phases">⚡ SAP Activate Phases</button>` : ''}
                        <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="ProjectSetupView._openPhaseForm(null)">+ Add Phase</button>
                    </div>
                </div>

                ${totalPhases === 0 ? `
                    <div class="project-setup-empty project-setup-empty--lg">
                        <div class="project-setup-empty__icon project-setup-empty__icon--lg">🗓️</div>
                        <div class="project-setup-empty__title">No phases defined</div>
                        <div class="project-setup-empty__copy" style="margin-bottom:16px">Define project lifecycle phases to track progress.</div>
                        ${meth === 'sap_activate' ? `<button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ProjectSetupView._seedSAPActivatePhases()">⚡ Auto-create SAP Activate Phases</button>` : ''}
                    </div>` : `
                <div class="project-setup-phase-list">
                    ${_methodPhases.map((ph, idx) => {
            const pct = Math.min(100, Math.max(0, ph.completion_pct || 0));
            const statusColor = phaseStatusColor[ph.status] || '#9ca3af';
            const statusLabel = phaseStatusLabel[ph.status] || ph.status;
            const isLate = ph.planned_end && new Date(ph.planned_end) < new Date() && ph.status !== 'completed';
            return `
                        <div class="project-setup-phase-row ${isLate ? 'project-setup-phase-row--late' : ''}">
                            <div class="project-setup-phase-row__index" style="background:${statusColor}22;color:${statusColor}">${idx + 1}</div>
                            <div class="project-setup-phase-row__body">
                                <div class="project-setup-phase-row__top">
                                    <span class="project-setup-phase-row__name">${esc(ph.name)}</span>
                                    <span class="project-setup-phase-row__badge" style="background:${statusColor}22;color:${statusColor}">${statusLabel}</span>
                                    ${isLate ? '<span class="project-setup-phase-row__late">⚠ Late</span>' : ''}
                                </div>
                                <div class="project-setup-phase-row__track">
                                    <div class="project-setup-phase-row__fill" style="width:${pct}%;background:${statusColor}"></div>
                                </div>
                                <div class="project-setup-phase-row__meta">
                                    <span>${pct}% complete</span>
                                    ${ph.planned_start ? `<span>Start: ${esc(ph.planned_start)}</span>` : ''}
                                    ${ph.planned_end ? `<span>End: ${esc(ph.planned_end)}</span>` : ''}
                                </div>
                            </div>
                            <div class="project-setup-phase-row__actions">
                                <button class="btn-icon project-setup-icon-btn" title="Edit" onclick="ProjectSetupView._openPhaseForm(${ph.id})">✏️</button>
                                <button class="btn-icon btn-icon--danger project-setup-icon-btn" title="Delete" onclick="ProjectSetupView._confirmDeletePhase(${ph.id},'${esc(ph.name)}')">🗑</button>
                            </div>
                        </div>`;
        }).join('')}
                </div>`}
            </div>

            <!-- ── Phase Form Modal ── -->
            <div id="phaseModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;align-items:center;justify-content:center">
                <div class="card project-setup-modal-surface" onclick="event.stopPropagation()">
                    <h3 id="phaseModalTitle" style="margin:0 0 20px">Add Phase</h3>
                    <div class="project-setup-modal-grid">
                        <div class="form-group project-setup-modal-grid__full">
                            <label class="form-label">Phase Name *</label>
                            <input id="ph_name" class="pg-input" placeholder="e.g. Explore">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Order</label>
                            <input id="ph_order" type="number" class="pg-input" min="0" value="0">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Status</label>
                            <select id="ph_status" class="pg-input">
                                ${['not_started', 'in_progress', 'completed', 'skipped'].map(s =>
            `<option value="${s}">${phaseStatusLabel[s] || s}</option>`
        ).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Planned Start</label>
                            <input id="ph_planned_start" type="date" class="pg-input">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Planned End</label>
                            <input id="ph_planned_end" type="date" class="pg-input">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Actual Start</label>
                            <input id="ph_actual_start" type="date" class="pg-input">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Actual End</label>
                            <input id="ph_actual_end" type="date" class="pg-input">
                        </div>
                        <div class="form-group project-setup-modal-grid__full">
                            <label class="form-label">Completion % (0–100)</label>
                            <input id="ph_completion_pct" type="range" min="0" max="100" value="0" style="width:100%" oninput="document.getElementById('ph_pct_label').textContent=this.value+'%'">
                            <span id="ph_pct_label" style="font-size:12px;color:var(--pg-color-text-secondary)">0%</span>
                        </div>
                        <div class="form-group project-setup-modal-grid__full">
                            <label class="form-label">Description</label>
                            <textarea id="ph_description" class="pg-input" rows="2" style="resize:vertical" placeholder="Optional description..."></textarea>
                        </div>
                    </div>
                    <div class="project-setup-modal-actions">
                        <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ProjectSetupView._closePhaseModal()">Cancel</button>
                        <button class="pg-btn pg-btn--primary pg-btn--sm" id="phaseSaveBtn" onclick="ProjectSetupView._savePhase()">💾 Save</button>
                    </div>
                </div>
            </div>`;
    }

    function _toggleMethEdit() {
        const viewEl = document.getElementById('methViewMode');
        const editEl = document.getElementById('methEditMode');
        const btn = document.getElementById('methEditBtn');
        if (!viewEl || !editEl) return;
        const isEditing = editEl.style.display !== 'none';
        viewEl.style.display = isEditing ? '' : 'none';
        editEl.style.display = isEditing ? 'none' : '';
        if (btn) btn.textContent = isEditing ? '✏️ Edit' : 'Cancel';
    }

    async function _saveMethConfig() {
        const proj = _programProjects.find(p => Number(p.id) === Number(_activeProject?.id));
        if (!proj) return;
        const btn = document.getElementById('methSaveBtn');
        if (btn) { btn.textContent = 'Saving…'; btn.disabled = true; }
        const payload = {
            methodology: document.getElementById('meth_methodology')?.value,
            project_type: document.getElementById('meth_project_type')?.value,
            sap_product: document.getElementById('meth_sap_product')?.value,
            deployment_option: document.getElementById('meth_deployment_option')?.value,
        };
        try {
            const updated = await API.put(`/projects/${proj.id}`, payload);
            const idx = _programProjects.findIndex(p => Number(p.id) === Number(proj.id));
            if (idx >= 0) _programProjects[idx] = { ..._programProjects[idx], ...updated };
            App.toast('Methodology settings saved', 'success');
            const c = document.getElementById('setupContent');
            if (c) _renderMethodologyContent(c);
        } catch (err) {
            App.toast(err.message || 'Save failed', 'error');
            if (btn) { btn.textContent = '💾 Save'; btn.disabled = false; }
        }
    }

    function _seedSAPActivatePhases() {
        _openConfirmModal({
            title: 'Create SAP Activate phases',
            message: 'This will create the 6 standard SAP Activate phases: Discover, Prepare, Explore, Realize, Deploy, and Run.',
            confirmLabel: 'Create phases',
            danger: false,
            onConfirm: async () => {
                const sapPhases = [
                    { name: 'Discover', order: 1 },
                    { name: 'Prepare', order: 2 },
                    { name: 'Explore', order: 3 },
                    { name: 'Realize', order: 4 },
                    { name: 'Deploy', order: 5 },
                    { name: 'Run', order: 6 },
                ];
                let created = 0;
                for (const ph of sapPhases) {
                    try {
                        const res = await API.post(`/programs/${_pid}/phases`, { ...ph, project_id: _activeProject?.id });
                        _methodPhases.push(res);
                        created++;
                    } catch { /* skip duplicate */ }
                }
                App.toast(`${created} SAP Activate phases created`, 'success');
                const c = document.getElementById('setupContent');
                if (c) _renderMethodologyContent(c);
            },
        });
    }

    function _openPhaseForm(phaseId) {
        _methEditingPhaseId = phaseId;
        const modal = document.getElementById('phaseModal');
        const title = document.getElementById('phaseModalTitle');
        if (!modal) return;

        // Reset
        const fields = ['ph_name', 'ph_order', 'ph_planned_start', 'ph_planned_end', 'ph_actual_start', 'ph_actual_end', 'ph_description'];
        fields.forEach(id => { const el = document.getElementById(id); if (el) el.value = id === 'ph_order' ? '0' : ''; });
        const statusEl = document.getElementById('ph_status');
        if (statusEl) statusEl.value = 'not_started';
        const pctEl = document.getElementById('ph_completion_pct');
        if (pctEl) { pctEl.value = 0; document.getElementById('ph_pct_label').textContent = '0%'; }

        if (phaseId) {
            const ph = _methodPhases.find(p => p.id === phaseId);
            if (ph) {
                if (title) title.textContent = `Edit: ${ph.name}`;
                if (document.getElementById('ph_name')) document.getElementById('ph_name').value = ph.name || '';
                if (document.getElementById('ph_order')) document.getElementById('ph_order').value = ph.order ?? 0;
                if (statusEl) statusEl.value = ph.status || 'not_started';
                if (document.getElementById('ph_planned_start')) document.getElementById('ph_planned_start').value = ph.planned_start || '';
                if (document.getElementById('ph_planned_end')) document.getElementById('ph_planned_end').value = ph.planned_end || '';
                if (document.getElementById('ph_actual_start')) document.getElementById('ph_actual_start').value = ph.actual_start || '';
                if (document.getElementById('ph_actual_end')) document.getElementById('ph_actual_end').value = ph.actual_end || '';
                if (document.getElementById('ph_description')) document.getElementById('ph_description').value = ph.description || '';
                if (pctEl) {
                    pctEl.value = ph.completion_pct || 0;
                    const lbl = document.getElementById('ph_pct_label');
                    if (lbl) lbl.textContent = (ph.completion_pct || 0) + '%';
                }
            }
        } else {
            if (title) title.textContent = 'Add Phase';
            // Auto-set next order
            const maxOrder = _methodPhases.reduce((m, p) => Math.max(m, p.order || 0), 0);
            if (document.getElementById('ph_order')) document.getElementById('ph_order').value = maxOrder + 1;
        }
        modal.style.display = 'flex';
    }

    function _closePhaseModal() {
        const modal = document.getElementById('phaseModal');
        if (modal) modal.style.display = 'none';
        _methEditingPhaseId = null;
    }

    async function _savePhase() {
        const name = (document.getElementById('ph_name')?.value || '').trim();
        if (!name) { App.toast('Phase name is required', 'error'); return; }

        const btn = document.getElementById('phaseSaveBtn');
        if (btn) { btn.textContent = 'Saving…'; btn.disabled = true; }

        const payload = {
            project_id: _activeProject?.id,
            name,
            order: parseInt(document.getElementById('ph_order')?.value || '0', 10),
            status: document.getElementById('ph_status')?.value || 'not_started',
            planned_start: document.getElementById('ph_planned_start')?.value || null,
            planned_end: document.getElementById('ph_planned_end')?.value || null,
            actual_start: document.getElementById('ph_actual_start')?.value || null,
            actual_end: document.getElementById('ph_actual_end')?.value || null,
            completion_pct: parseInt(document.getElementById('ph_completion_pct')?.value || '0', 10),
            description: document.getElementById('ph_description')?.value || '',
        };

        try {
            if (_methEditingPhaseId) {
                const updated = await API.put(`/phases/${_methEditingPhaseId}`, payload);
                const idx = _methodPhases.findIndex(p => p.id === _methEditingPhaseId);
                if (idx >= 0) _methodPhases[idx] = { ..._methodPhases[idx], ...updated };
                App.toast('Phase updated', 'success');
            } else {
                const created = await API.post(`/programs/${_pid}/phases`, payload);
                _methodPhases.push(created);
                App.toast('Phase created', 'success');
            }
            _closePhaseModal();
            const c = document.getElementById('setupContent');
            if (c) _renderMethodologyContent(c);
        } catch (err) {
            App.toast(err.message || 'Save failed', 'error');
            if (btn) { btn.textContent = '💾 Save'; btn.disabled = false; }
        }
    }

    function _confirmDeletePhase(phaseId, phaseName) {
        _openConfirmModal({
            title: 'Delete phase',
            message: `Delete phase "${phaseName}"? This will also remove any gates under it.`,
            confirmLabel: 'Delete phase',
            onConfirm: () => _deletePhase(phaseId),
        });
    }

    async function _deletePhase(phaseId) {
        try {
            await API.delete(`/phases/${phaseId}`);
            _methodPhases = _methodPhases.filter(p => p.id !== phaseId);
            App.toast('Phase deleted', 'success');
            const c = document.getElementById('setupContent');
            if (c) _renderMethodologyContent(c);
        } catch (err) {
            App.toast(err.message || 'Delete failed', 'error');
        }
    }



    /* ─── Team Tab state ─── */
    let _teamMembers = [];
    let _teamEditingId = null;

    async function renderTeamTab() {
        const c = document.getElementById('setupContent');
        if (!c || !_activeProject) { renderProjectRequiredGuard(); return; }
        c.innerHTML = `<div class="pg-loading-state"><div class="spinner"></div></div>`;
        try {
            const [members, workstreams] = await Promise.all([
                API.get(`/programs/${_pid}/team?project_id=${_activeProject.id}`),
                API.get(`/programs/${_pid}/workstreams?project_id=${_activeProject.id}`),
            ]);
            _teamMembers = Array.isArray(members) ? members : [];
            _projectWorkstreams = Array.isArray(workstreams) ? workstreams : [];
        } catch {
            _teamMembers = [];
            _projectWorkstreams = [];
        }
        _teamEditingId = null;
        _renderTeamContent(c);
    }

    function _renderTeamContent(c) {
        const roleBadge = (r) => {
            const map = {
                program_manager: '#6366f1', project_lead: '#3b82f6',
                stream_lead: '#8b5cf6', consultant: '#f59e0b',
                developer: '#22c55e', team_member: '#9ca3af',
            };
            return `<span class="project-setup-badge" style="background:${map[r] || '#9ca3af'}22;color:${map[r] || '#9ca3af'}">${esc(r || '—')}</span>`;
        };
        const raciBadge = (r) => {
            const map = { responsible: '#22c55e', accountable: '#6366f1', consulted: '#f59e0b', informed: '#9ca3af' };
            return `<span class="project-setup-badge" style="background:${map[r] || '#eee'}22;color:${map[r] || '#9ca3af'}">${esc((r || '').toUpperCase())}</span>`;
        };

        c.innerHTML = `
            <div class="card project-setup-card">
                <div class="project-setup-card__header">
                    <div>
                        <h3 class="project-setup-card__title">Project Team</h3>
                        <p class="project-setup-card__subtitle">
                            Members scoped to: <strong>${esc(_activeProject?.name || '—')}</strong>
                            · ${_teamMembers.length} member${_teamMembers.length !== 1 ? 's' : ''}
                        </p>
                    </div>
                    ${ExpUI.actionButton({ label: '+ Add Member', variant: 'primary', size: 'sm', onclick: 'ProjectSetupView._openTeamMemberForm(null)' })}
                </div>

                ${_teamMembers.length === 0 ? `
                    <div class="project-setup-empty project-setup-empty--lg">
                        <div class="project-setup-empty__icon project-setup-empty__icon--lg">👥</div>
                        <div class="project-setup-empty__title">No team members yet</div>
                        <div class="project-setup-empty__copy">Add the first team member for this project.</div>
                    </div>` : `
                <div class="table-wrap" data-testid="project-setup-team-table">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Role</th>
                                <th>Workstream</th>
                                <th>RACI</th>
                                <th>Email</th>
                                <th>Organization</th>
                                <th>Status</th>
                                <th style="width:80px">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${_teamMembers.map((m) => `
                            <tr class="${!m.is_active ? 'project-setup-team-row--inactive' : ''}">
                                <td><strong>${esc(m.name || '—')}</strong></td>
                                <td>${roleBadge(m.role)}</td>
                                <td>${esc((_projectWorkstreams.find((w) => Number(w.id) === Number(m.workstream_id)) || {}).name || '—')}</td>
                                <td>${raciBadge(m.raci)}</td>
                                <td>${m.email ? `<a href="mailto:${esc(m.email)}" class="project-setup-link">${esc(m.email)}</a>` : '—'}</td>
                                <td>${esc(m.organization || '—')}</td>
                                <td><span class="project-setup-status ${m.is_active ? 'project-setup-status--active' : 'project-setup-status--inactive'}">${m.is_active ? '● Active' : '○ Inactive'}</span></td>
                                <td>
                                    <div class="project-setup-table-actions">
                                        <button class="btn-icon project-setup-icon-btn" title="Edit" onclick="ProjectSetupView._openTeamMemberForm(${m.id})">✏️</button>
                                        <button class="btn-icon btn-icon--danger project-setup-icon-btn" title="Remove" onclick="ProjectSetupView._confirmDeleteTeamMember(${m.id}, '${esc(m.name || '')}')">🗑</button>
                                    </div>
                                </td>
                            </tr>`).join('')}
                        </tbody>
                    </table>
                </div>`}
            </div>

            <!-- Team Member Form Modal -->
            <div id="teamMemberModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;align-items:center;justify-content:center">
                <div class="card" style="width:560px;max-height:90vh;overflow-y:auto;padding:24px;border-radius:12px" onclick="event.stopPropagation()">
                    <h3 id="teamModalTitle" style="margin:0 0 20px">Add Team Member</h3>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                        <div class="form-group" style="grid-column:1/-1">
                            <label class="form-label">Full Name *</label>
                            <input id="tm_name" class="pg-input" placeholder="e.g. John Smith" style="width:100%">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Email</label>
                            <input id="tm_email" type="email" class="pg-input" placeholder="john@company.com" style="width:100%">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Organization</label>
                            <input id="tm_organization" class="pg-input" placeholder="Company / partner name" style="width:100%">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Role</label>
                            <select id="tm_role" class="pg-input" style="width:100%">
                                ${['program_manager', 'project_lead', 'stream_lead', 'consultant', 'developer', 'team_member'].map(r => `<option value="${r}">${r.replace(/_/g, ' ')}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">RACI</label>
                            <select id="tm_raci" class="pg-input" style="width:100%">
                                ${['responsible', 'accountable', 'consulted', 'informed'].map(r => `<option value="${r}">${r}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Workstream</label>
                            <select id="tm_workstream_id" class="pg-input" style="width:100%">
                                <option value="">— None —</option>
                                ${_projectWorkstreams.map((w) => `<option value="${w.id}">${esc(w.name || '')}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-group" style="grid-column:1/-1;display:flex;align-items:center;gap:8px">
                            <input id="tm_is_active" type="checkbox" checked style="width:16px;height:16px">
                            <label for="tm_is_active" class="form-label" style="margin:0">Active member</label>
                        </div>
                    </div>
                    <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:20px;padding-top:16px;border-top:1px solid var(--pg-color-border)">
                        ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', size: 'sm', onclick: 'ProjectSetupView._closeTeamModal()' })}
                        ${ExpUI.actionButton({ label: '💾 Save', variant: 'primary', size: 'sm', id: 'tmSaveBtn', onclick: 'ProjectSetupView._saveTeamMember()' })}
                    </div>
                </div>
            </div>`;
    }

    function _openTeamMemberForm(memberId) {
        _teamEditingId = memberId;
        const modal = document.getElementById('teamMemberModal');
        const title = document.getElementById('teamModalTitle');
        if (!modal) return;

        // Reset form
        ['tm_name', 'tm_email', 'tm_organization'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        const roleEl = document.getElementById('tm_role');
        const raciEl = document.getElementById('tm_raci');
        const workstreamEl = document.getElementById('tm_workstream_id');
        const activeEl = document.getElementById('tm_is_active');
        if (roleEl) roleEl.value = 'team_member';
        if (raciEl) raciEl.value = 'informed';
        if (workstreamEl) workstreamEl.value = '';
        if (activeEl) activeEl.checked = true;

        if (memberId) {
            const member = _teamMembers.find(m => m.id === memberId);
            if (member) {
                if (title) title.textContent = `Edit: ${member.name}`;
                if (document.getElementById('tm_name')) document.getElementById('tm_name').value = member.name || '';
                if (document.getElementById('tm_email')) document.getElementById('tm_email').value = member.email || '';
                if (document.getElementById('tm_organization')) document.getElementById('tm_organization').value = member.organization || '';
                if (roleEl) roleEl.value = member.role || 'team_member';
                if (raciEl) raciEl.value = member.raci || 'informed';
                if (workstreamEl) workstreamEl.value = member.workstream_id || '';
                if (activeEl) activeEl.checked = member.is_active !== false;
            }
        } else {
            if (title) title.textContent = 'Add Team Member';
        }

        modal.style.display = 'flex';
    }

    function _closeTeamModal() {
        const modal = document.getElementById('teamMemberModal');
        if (modal) modal.style.display = 'none';
        _teamEditingId = null;
    }

    async function _saveTeamMember() {
        const name = (document.getElementById('tm_name')?.value || '').trim();
        if (!name) { App.toast('Name is required', 'error'); return; }

        const payload = {
            name,
            email: document.getElementById('tm_email')?.value?.trim() || '',
            organization: document.getElementById('tm_organization')?.value?.trim() || '',
            role: document.getElementById('tm_role')?.value || 'team_member',
            raci: document.getElementById('tm_raci')?.value || 'informed',
            workstream_id: document.getElementById('tm_workstream_id')?.value
                ? parseInt(document.getElementById('tm_workstream_id').value, 10)
                : null,
            is_active: document.getElementById('tm_is_active')?.checked !== false,
            project_id: _activeProject?.id,
        };

        const btn = document.getElementById('tmSaveBtn');
        if (btn) { btn.textContent = 'Saving…'; btn.disabled = true; }

        try {
            if (_teamEditingId) {
                const updated = await API.put(`/team/${_teamEditingId}`, payload);
                const idx = _teamMembers.findIndex(m => m.id === _teamEditingId);
                if (idx >= 0) _teamMembers[idx] = { ..._teamMembers[idx], ...updated };
                App.toast('Team member updated', 'success');
            } else {
                const created = await API.post(`/programs/${_pid}/team`, payload);
                _teamMembers.push(created);
                App.toast('Team member added', 'success');
            }
            if (typeof TeamMemberPicker !== 'undefined' && typeof TeamMemberPicker.invalidateCache === 'function') {
                TeamMemberPicker.invalidateCache(_pid);
            }
            _closeTeamModal();
            const c = document.getElementById('setupContent');
            if (c) _renderTeamContent(c);
        } catch (err) {
            App.toast(err.message || 'Save failed', 'error');
            if (btn) { btn.textContent = '💾 Save'; btn.disabled = false; }
        }
    }

    function _confirmDeleteTeamMember(memberId, memberName) {
        _openConfirmModal({
            title: 'Remove team member',
            message: `Remove "${memberName}" from the project team?`,
            confirmLabel: 'Remove member',
            onConfirm: () => _deleteTeamMember(memberId),
        });
    }

    async function _deleteTeamMember(memberId) {
        try {
            await API.delete(`/team/${memberId}`);
            _teamMembers = _teamMembers.filter(m => m.id !== memberId);
            if (typeof TeamMemberPicker !== 'undefined' && typeof TeamMemberPicker.invalidateCache === 'function') {
                TeamMemberPicker.invalidateCache(_pid);
            }
            App.toast('Team member removed', 'success');
            const c = document.getElementById('setupContent');
            if (c) _renderTeamContent(c);
        } catch (err) {
            App.toast(err.message || 'Delete failed', 'error');
        }
    }



    /* ─── Timeline Tab ─── */

    async function renderTimelineTab() {
        const c = document.getElementById('setupContent');
        if (!c || !_activeProject) { renderProjectRequiredGuard(); return; }
        c.innerHTML = `<div class="pg-loading-state"><div class="spinner"></div></div>`;

        let tlData;
        try {
            tlData = await API.get(`/programs/${_pid}/timeline?project_id=${_activeProject.id}`);
        } catch (e) {
            c.innerHTML = `<div class="card" style="padding:20px;color:var(--pg-color-danger)">Failed to load timeline: ${esc(e.message || 'unknown error')}</div>`;
            return;
        }

        const phases = tlData?.phases || [];
        const sprints = tlData?.sprints || [];
        const milestones = tlData?.milestones || [];
        const today = tlData?.today ? new Date(tlData.today) : new Date();

        /* ── Determine chart date range ── */
        const allDates = [];
        phases.forEach(p => {
            if (p.start_date) allDates.push(new Date(p.start_date));
            if (p.end_date) allDates.push(new Date(p.end_date));
            if (p.planned_start) allDates.push(new Date(p.planned_start));
            if (p.planned_end) allDates.push(new Date(p.planned_end));
        });
        sprints.forEach(s => {
            if (s.start_date) allDates.push(new Date(s.start_date));
            if (s.end_date) allDates.push(new Date(s.end_date));
        });

        const hasData = allDates.length > 0;

        if (!hasData) {
            c.innerHTML = `
                <div class="card" style="padding:20px;margin-bottom:16px">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                        <h3 style="margin:0">📅 Timeline</h3>
                    </div>
                    <div style="text-align:center;padding:40px;color:var(--pg-color-text-secondary)">
                        <div style="font-size:40px;margin-bottom:12px">📆</div>
                        <div style="font-weight:600;font-size:16px;margin-bottom:8px">No date-based phases yet</div>
                        <div style="font-size:13px;margin-bottom:20px;max-width:400px;margin-left:auto;margin-right:auto">
                            Add planned start/end dates to your phases in the <strong>Methodology</strong> tab to see the Gantt chart here.
                        </div>
                        <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="ProjectSetupView.switchTab('methodology')">Go to Methodology & Phases</button>
                    </div>
                </div>`;
            return;
        }

        allDates.push(today);
        const chartStart = new Date(Math.min(...allDates));
        const chartEnd = new Date(Math.max(...allDates));
        // Pad by 1 month each side
        chartStart.setDate(1);
        chartEnd.setMonth(chartEnd.getMonth() + 1, 1);

        const totalMs = chartEnd - chartStart;
        const dayMs = 86400000;

        /* ── Layout constants ── */
        const ROW_H = 40;
        const LABEL_W = 160;
        const CHART_W = Math.max(700, Math.min(1400, Math.floor(totalMs / dayMs) * 4));
        const HEADER_H = 40;
        const phaseRows = phases.length;
        const sprintRows = sprints.length > 0 ? sprints.length + 1 : 0; // +1 for header
        const totalRows = phaseRows + sprintRows;
        const SVG_H = HEADER_H + totalRows * ROW_H + 20;
        const SVG_W = LABEL_W + CHART_W;

        /* ── Helpers ── */
        const dateX = (d) => {
            const dt = typeof d === 'string' ? new Date(d) : d;
            return LABEL_W + Math.round(((dt - chartStart) / totalMs) * CHART_W);
        };
        const esc2 = (s) => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

        /* ── Month ruler ── */
        let rulerSvg = '';
        {
            const cur = new Date(chartStart);
            while (cur < chartEnd) {
                const x = dateX(cur);
                const label = cur.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
                rulerSvg += `<line x1="${x}" y1="0" x2="${x}" y2="${SVG_H}" stroke="var(--pg-color-border)" stroke-width="0.5"/>`;
                rulerSvg += `<text x="${x + 4}" y="14" font-size="10" fill="var(--pg-color-text-secondary)">${esc2(label)}</text>`;
                cur.setMonth(cur.getMonth() + 1);
            }
        }

        /* ── Today line ── */
        const todayX = dateX(today);
        const todaySvg = `
            <line x1="${todayX}" y1="${HEADER_H}" x2="${todayX}" y2="${SVG_H}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="4,3"/>
            <rect x="${todayX - 16}" y="2" width="32" height="16" rx="3" fill="#ef4444"/>
            <text x="${todayX}" y="13" font-size="9" fill="white" text-anchor="middle" font-weight="600">TODAY</text>`;

        /* ── Phase rows ── */
        let phasesSvg = '';
        phases.forEach((ph, i) => {
            const y = HEADER_H + i * ROW_H;
            const barY = y + 8;
            const barH = ROW_H - 16;
            const color = ph.color || '#6366f1';
            const lighter = color + '33';

            const x1 = ph.start_date ? dateX(ph.start_date) : null;
            const x2 = ph.end_date ? dateX(ph.end_date) : null;
            const px1 = ph.planned_start ? dateX(ph.planned_start) : null;
            const px2 = ph.planned_end ? dateX(ph.planned_end) : null;

            // Strip background
            phasesSvg += `<rect x="${LABEL_W}" y="${y}" width="${CHART_W}" height="${ROW_H}" fill="${i % 2 === 0 ? 'var(--pg-color-surface)' : 'transparent'}"/>`;

            // Label
            phasesSvg += `<text x="${LABEL_W - 8}" y="${y + ROW_H / 2 + 4}" font-size="12" fill="var(--pg-color-text)" text-anchor="end"
                style="font-weight:${ph.status === 'in_progress' ? '600' : '400'}">${esc2((ph.name || '').substring(0, 22))}</text>`;

            // Planned bar (ghost)
            if (px1 !== null && px2 !== null && px2 > px1) {
                phasesSvg += `<rect x="${px1}" y="${barY + barH / 2 - 2}" width="${px2 - px1}" height="4" rx="2" fill="${color}" opacity="0.25"/>`;
            }

            // Actual bar
            if (x1 !== null && x2 !== null && x2 > x1) {
                const barW = x2 - x1;
                phasesSvg += `<rect x="${x1}" y="${barY}" width="${barW}" height="${barH}" rx="4" fill="${lighter}"/>`;
                // Completion fill
                const filled = Math.round(barW * (ph.completion_pct || 0) / 100);
                if (filled > 0) {
                    phasesSvg += `<rect x="${x1}" y="${barY}" width="${filled}" height="${barH}" rx="4" fill="${color}" opacity="0.85"/>`;
                }
                // Border
                phasesSvg += `<rect x="${x1}" y="${barY}" width="${barW}" height="${barH}" rx="4" fill="none" stroke="${color}" stroke-width="1.5"/>`;
                // % label inside bar
                if (barW > 40) {
                    phasesSvg += `<text x="${x1 + barW / 2}" y="${barY + barH / 2 + 4}" font-size="10" fill="${color}" text-anchor="middle" font-weight="600">${ph.completion_pct || 0}%</text>`;
                }
            }

            // Gate diamonds
            (ph.gates || []).forEach(gt => {
                if (!gt.planned_date) return;
                const gx = dateX(gt.planned_date);
                const gy = y + ROW_H / 2;
                const gColor = gt.status === 'passed' ? '#22c55e' : gt.status === 'blocked' ? '#ef4444' : '#f59e0b';
                phasesSvg += `<polygon points="${gx},${gy - 7} ${gx + 7},${gy} ${gx},${gy + 7} ${gx - 7},${gy}" fill="${gColor}"/>`;
                phasesSvg += `<title>${esc2(gt.name)}</title>`;
            });
        });

        /* ── Sprint rows ── */
        let sprintsSvg = '';
        if (sprints.length > 0) {
            const sectionY = HEADER_H + phaseRows * ROW_H;
            sprintsSvg += `<rect x="0" y="${sectionY}" width="${SVG_W}" height="${ROW_H}" fill="var(--pg-color-border)20"/>`;
            sprintsSvg += `<text x="8" y="${sectionY + ROW_H / 2 + 4}" font-size="11" fill="var(--pg-color-text-secondary)" font-weight="700">SPRINTS</text>`;

            sprints.forEach((s, i) => {
                const y = sectionY + ROW_H + i * ROW_H;
                const x1 = s.start_date ? dateX(s.start_date) : null;
                const x2 = s.end_date ? dateX(s.end_date) : null;
                sprintsSvg += `<rect x="${LABEL_W}" y="${y}" width="${CHART_W}" height="${ROW_H}" fill="${i % 2 === 0 ? 'var(--pg-color-surface)' : 'transparent'}"/>`;
                sprintsSvg += `<text x="${LABEL_W - 8}" y="${y + ROW_H / 2 + 4}" font-size="11" fill="var(--pg-color-text-secondary)" text-anchor="end">${esc2((s.name || 'Sprint').substring(0, 20))}</text>`;
                if (x1 !== null && x2 !== null && x2 > x1) {
                    const spColor = s.status === 'completed' ? '#22c55e' : s.status === 'active' ? '#3b82f6' : '#9ca3af';
                    sprintsSvg += `<rect x="${x1}" y="${y + 8}" width="${x2 - x1}" height="${ROW_H - 16}" rx="3" fill="${spColor}" opacity="0.25"/>`;
                    sprintsSvg += `<rect x="${x1}" y="${y + 8}" width="${x2 - x1}" height="${ROW_H - 16}" rx="3" fill="none" stroke="${spColor}" stroke-width="1"/>`;
                    if ((x2 - x1) > 30) {
                        sprintsSvg += `<text x="${x1 + (x2 - x1) / 2}" y="${y + ROW_H / 2 + 4}" font-size="10" fill="${spColor}" text-anchor="middle">${esc2((s.name || '').substring(0, 14))}</text>`;
                    }
                }
            });
        }

        /* ── Milestones legend ── */
        const milestoneLegend = milestones.slice(0, 8).map(m =>
            `<span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;color:var(--pg-color-text-secondary)">
                <svg width="10" height="10"><polygon points="5,0 10,5 5,10 0,5" fill="#f59e0b"/></svg>
                ${esc(m.name)}
            </span>`
        ).join('');

        /* ── Assemble ── */
        const statusSummary = phases.map(ph => {
            const sc = { not_started: '#9ca3af', in_progress: '#3b82f6', completed: '#22c55e', skipped: '#f59e0b' };
            return `<span style="display:inline-flex;align-items:center;gap:5px;font-size:12px">
                <span style="width:8px;height:8px;border-radius:50%;background:${sc[ph.status] || '#9ca3af'}"></span>
                ${esc(ph.name)}
            </span>`;
        }).join('');

        c.innerHTML = `
            <div class="card" style="padding:20px;margin-bottom:12px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                    <h3 style="margin:0">📅 Project Timeline</h3>
                    <button class="pg-btn pg-btn--secondary pg-btn--sm" onclick="ProjectSetupView.renderTimelineTab()">↻ Refresh</button>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:4px">${statusSummary}</div>
            </div>

            <div class="card" style="padding:0;overflow:hidden">
                <div style="overflow-x:auto;-webkit-overflow-scrolling:touch">
                    <svg width="${SVG_W}" height="${SVG_H}" xmlns="http://www.w3.org/2000/svg" style="display:block;font-family:inherit">
                        <!-- Month grid -->
                        ${rulerSvg}
                        <!-- Phases -->
                        ${phasesSvg}
                        <!-- Sprints -->
                        ${sprintsSvg}
                        <!-- Today -->
                        ${todaySvg}
                        <!-- Left label column border -->
                        <line x1="${LABEL_W}" y1="0" x2="${LABEL_W}" y2="${SVG_H}" stroke="var(--pg-color-border)" stroke-width="1"/>
                        <!-- Bottom border -->
                        <line x1="0" y1="${SVG_H - 1}" x2="${SVG_W}" y2="${SVG_H - 1}" stroke="var(--pg-color-border)" stroke-width="1"/>
                    </svg>
                </div>
            </div>

            ${milestones.length > 0 ? `
            <div class="card" style="padding:12px 16px;margin-top:12px">
                <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:var(--pg-color-text-secondary);margin-bottom:8px">Gate Milestones</div>
                <div style="display:flex;flex-wrap:wrap;gap:12px">${milestoneLegend}</div>
            </div>` : ''}`;
    }

    async function _loadOperatingModelData() {
        const [committeesRes, workstreamsRes, teamRes] = await Promise.all([
            API.get(`/programs/${_pid}/committees?project_id=${_activeProject.id}`),
            API.get(`/programs/${_pid}/workstreams?project_id=${_activeProject.id}`),
            API.get(`/programs/${_pid}/team?project_id=${_activeProject.id}`),
        ]);
        _projectCommittees = Array.isArray(committeesRes) ? committeesRes : [];
        _projectWorkstreams = Array.isArray(workstreamsRes) ? workstreamsRes : [];
        _teamMembers = Array.isArray(teamRes) ? teamRes : [];
    }

    function renderWorkstreamsTab() {
        const c = document.getElementById('setupContent');
        if (!c || !_activeProject) { renderProjectRequiredGuard(); return; }
        c.innerHTML = `<div class="pg-loading-state"><div class="spinner"></div></div>`;
        _loadOperatingModelData().then(() => {
            _renderWorkstreamsContent(c);
        }).catch((err) => {
            c.innerHTML = `<div class="card project-setup-card project-setup-error-card">Failed to load workstreams: ${esc(err.message || 'unknown error')}</div>`;
        });
    }

    function renderCommitteesTab() {
        const c = document.getElementById('setupContent');
        if (!c || !_activeProject) { renderProjectRequiredGuard(); return; }
        c.innerHTML = `<div class="pg-loading-state"><div class="spinner"></div></div>`;
        _loadOperatingModelData().then(() => {
            _renderCommitteesContent(c);
        }).catch((err) => {
            c.innerHTML = `<div class="card project-setup-card project-setup-error-card">Failed to load committees: ${esc(err.message || 'unknown error')}</div>`;
        });
    }

    function _renderWorkstreamsContent(c) {
        const workstreamRows = _projectWorkstreams.length
            ? `
                <div class="table-wrap">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Lead</th>
                                <th>Status</th>
                                <th style="width:80px">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${_projectWorkstreams.map((ws) => `
                                <tr>
                                    <td><strong>${esc(ws.name || '—')}</strong></td>
                                    <td>${esc(ws.ws_type || 'functional')}</td>
                                    <td>${esc(ws.lead_name || '—')}</td>
                                    <td>${esc(ws.status || 'active')}</td>
                                    <td>
                                        <div class="project-setup-table-actions">
                                            <button class="btn-icon project-setup-icon-btn" title="Edit" onclick="ProjectSetupView._openWorkstreamForm(${ws.id})">✏️</button>
                                            <button class="btn-icon btn-icon--danger project-setup-icon-btn" title="Delete" onclick="ProjectSetupView._confirmDeleteWorkstream(${ws.id}, '${esc(ws.name || '')}')">🗑</button>
                                        </div>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>`
            : `<div class="project-setup-empty">
                    <div class="project-setup-empty__icon">🔧</div>
                    <div class="project-setup-empty__title">No workstreams defined</div>
                    <div class="project-setup-empty__copy">Create project-owned workstreams before assigning team members and RAID owners.</div>
                    <div style="margin-top:12px">${ExpUI.actionButton({ label: 'Open Team', variant: 'ghost', size: 'sm', onclick: "ProjectSetupView.switchTab('team')" })}</div>
                </div>`;

        const assignedMembers = _teamMembers.filter((m) => m.workstream_id).length;
        c.innerHTML = `
            <div data-testid="project-setup-workstreams-page">
            <div class="exp-kpi-strip project-setup-section-shell">
                ${ExpUI.kpiBlock({ value: _projectWorkstreams.length, label: 'Workstreams', icon: '🔧' })}
                ${ExpUI.kpiBlock({ value: assignedMembers, label: 'Members Assigned', icon: '👥' })}
                ${ExpUI.kpiBlock({ value: _projectWorkstreams.filter((ws) => ws.status === 'active').length, label: 'Active Streams', icon: '✅' })}
            </div>
            <div class="card project-setup-card project-setup-card--spaced">
                <div class="project-setup-card__header--top">
                    <div>
                        <h3 class="project-setup-card__title" style="margin:0 0 6px">Project Workstreams</h3>
                        <p class="project-setup-card__copy">
                            Workstreams define execution ownership for team setup, RAID routing, RACI mapping, and downstream delivery reporting.
                        </p>
                    </div>
                    <div class="project-setup-card__actions">
                        ${ExpUI.actionButton({ label: '+ Workstream', variant: 'primary', size: 'sm', onclick: 'ProjectSetupView._openWorkstreamForm(null)' })}
                        ${ExpUI.actionButton({ label: 'Open Team', variant: 'secondary', size: 'sm', onclick: "ProjectSetupView.switchTab('team')" })}
                    </div>
                </div>
            </div>
            <div class="card detail-section project-setup-card" data-testid="project-setup-workstreams">
                ${workstreamRows}
            </div>
            </div>
        `;
    }

    function _renderCommitteesContent(c) {
        const committeeRows = _projectCommittees.length
            ? `
                <div class="table-wrap">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Frequency</th>
                                <th>Chair</th>
                                <th style="width:80px">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${_projectCommittees.map((comm) => `
                                <tr>
                                    <td><strong>${esc(comm.name || '—')}</strong></td>
                                    <td>${esc(comm.committee_type || 'steering')}</td>
                                    <td>${esc(comm.meeting_frequency || 'weekly')}</td>
                                    <td>${esc(comm.chair_name || '—')}</td>
                                    <td>
                                        <div class="project-setup-table-actions">
                                            <button class="btn-icon project-setup-icon-btn" title="Edit" onclick="ProjectSetupView._openCommitteeForm(${comm.id})">✏️</button>
                                            <button class="btn-icon btn-icon--danger project-setup-icon-btn" title="Delete" onclick="ProjectSetupView._confirmDeleteCommittee(${comm.id}, '${esc(comm.name || '')}')">🗑</button>
                                        </div>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>`
            : `<div class="project-setup-empty">
                    <div class="project-setup-empty__icon">🏛️</div>
                    <div class="project-setup-empty__title">No committees defined</div>
                    <div class="project-setup-empty__copy">Define the steering and review cadence for this project or wave.</div>
                </div>`;

        c.innerHTML = `
            <div data-testid="project-setup-committees-page">
            <div class="exp-kpi-strip project-setup-section-shell">
                ${ExpUI.kpiBlock({ value: _projectCommittees.length, label: 'Committees', icon: '🏛️' })}
                ${ExpUI.kpiBlock({ value: _projectCommittees.filter((comm) => (comm.meeting_frequency || '').toLowerCase() === 'weekly').length, label: 'Weekly Cadence', icon: '🗓️' })}
                ${ExpUI.kpiBlock({ value: _projectCommittees.filter((comm) => comm.chair_name).length, label: 'Chaired', icon: '🎯' })}
            </div>
            <div class="card project-setup-card project-setup-card--spaced">
                <div class="project-setup-card__header--top">
                    <div>
                        <h3 class="project-setup-card__title" style="margin:0 0 6px">Project Committees</h3>
                        <p class="project-setup-card__copy">
                            Committees capture the governance cadence for steering, design authority, review forums, and project escalation paths.
                        </p>
                    </div>
                    <div class="project-setup-card__actions">
                        ${ExpUI.actionButton({ label: '+ Committee', variant: 'primary', size: 'sm', onclick: 'ProjectSetupView._openCommitteeForm(null)' })}
                        ${ExpUI.actionButton({ label: 'Open Workstreams', variant: 'secondary', size: 'sm', onclick: "ProjectSetupView.switchTab('workstreams')" })}
                    </div>
                </div>
            </div>
            <div class="card detail-section project-setup-card" data-testid="project-setup-committees">
                ${committeeRows}
            </div>
            </div>
        `;
    }

    function renderGovernanceTab() {
        _currentTab = 'workstreams';
        renderWorkstreamsTab();
    }

    function _openWorkstreamForm(workstreamId) {
        _workstreamEditingId = workstreamId;
        const ws = workstreamId ? _projectWorkstreams.find((item) => Number(item.id) === Number(workstreamId)) : null;
        const isEdit = !!ws;
        App.openModal(`
            <div class="modal-header">
                <h2>${isEdit ? 'Edit Workstream' : 'Add Workstream'}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <div class="form-group"><label>Workstream Name *</label><input id="ps_ws_name" class="form-input" value="${esc(ws?.name || '')}" placeholder="e.g. Finance, Basis, Integration"></div>
            <div class="form-group"><label>Description</label><textarea id="ps_ws_description" class="form-input" rows="2">${esc(ws?.description || '')}</textarea></div>
            <div class="form-row">
                <div class="form-group"><label>Type</label><select id="ps_ws_type" class="form-input">${['functional', 'technical', 'cross_cutting'].map((opt) => `<option value="${opt}" ${opt === (ws?.ws_type || 'functional') ? 'selected' : ''}>${opt.replace(/_/g, ' ')}</option>`).join('')}</select></div>
                <div class="form-group"><label>Status</label><select id="ps_ws_status" class="form-input">${['active', 'on_hold', 'completed'].map((opt) => `<option value="${opt}" ${opt === (ws?.status || 'active') ? 'selected' : ''}>${opt.replace(/_/g, ' ')}</option>`).join('')}</select></div>
            </div>
            <div class="form-group"><label>Lead Name</label><input id="ps_ws_lead" class="form-input" value="${esc(ws?.lead_name || '')}" placeholder="Optional lead"></div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button type="button" class="btn btn-primary" onclick="ProjectSetupView._saveWorkstream()">${isEdit ? 'Update' : 'Create'}</button>
            </div>
        `);
    }

    async function _saveWorkstream() {
        const name = (document.getElementById('ps_ws_name')?.value || '').trim();
        if (!name) { App.toast('Workstream name is required', 'error'); return; }
        const payload = {
            name,
            description: document.getElementById('ps_ws_description')?.value?.trim() || '',
            ws_type: document.getElementById('ps_ws_type')?.value || 'functional',
            status: document.getElementById('ps_ws_status')?.value || 'active',
            lead_name: document.getElementById('ps_ws_lead')?.value?.trim() || '',
            project_id: _activeProject?.id,
        };
        try {
            if (_workstreamEditingId) {
                const updated = await API.put(`/workstreams/${_workstreamEditingId}`, payload);
                const idx = _projectWorkstreams.findIndex((item) => Number(item.id) === Number(_workstreamEditingId));
                if (idx >= 0) _projectWorkstreams[idx] = { ..._projectWorkstreams[idx], ...updated };
                App.toast('Workstream updated', 'success');
            } else {
                const created = await API.post(`/programs/${_pid}/workstreams`, payload);
                _projectWorkstreams.push(created);
                App.toast('Workstream created', 'success');
            }
            App.closeModal();
            _workstreamEditingId = null;
            if (_currentTab === 'workstreams') _renderWorkstreamsContent(document.getElementById('setupContent'));
        } catch (err) {
            App.toast(err.message || 'Save failed', 'error');
        }
    }

    function _confirmDeleteWorkstream(workstreamId, workstreamName) {
        _openConfirmModal({
            title: 'Delete workstream',
            message: `Delete workstream "${workstreamName}"? Team member references will be cleared.`,
            confirmLabel: 'Delete workstream',
            onConfirm: () => _deleteWorkstream(workstreamId),
        });
    }

    async function _deleteWorkstream(workstreamId) {
        try {
            await API.delete(`/workstreams/${workstreamId}`);
            _projectWorkstreams = _projectWorkstreams.filter((item) => Number(item.id) !== Number(workstreamId));
            _teamMembers = _teamMembers.map((member) => (
                Number(member.workstream_id) === Number(workstreamId)
                    ? { ...member, workstream_id: null }
                    : member
            ));
            App.toast('Workstream deleted', 'success');
            if (_currentTab === 'workstreams') _renderWorkstreamsContent(document.getElementById('setupContent'));
        } catch (err) {
            App.toast(err.message || 'Delete failed', 'error');
        }
    }

    function _openCommitteeForm(committeeId) {
        _committeeEditingId = committeeId;
        const comm = committeeId ? _projectCommittees.find((item) => Number(item.id) === Number(committeeId)) : null;
        const isEdit = !!comm;
        App.openModal(`
            <div class="modal-header">
                <h2>${isEdit ? 'Edit Committee' : 'Add Committee'}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <div class="form-group"><label>Committee Name *</label><input id="ps_comm_name" class="form-input" value="${esc(comm?.name || '')}" placeholder="e.g. SteerCo"></div>
            <div class="form-group"><label>Description</label><textarea id="ps_comm_description" class="form-input" rows="2">${esc(comm?.description || '')}</textarea></div>
            <div class="form-row">
                <div class="form-group"><label>Type</label><select id="ps_comm_type" class="form-input">${['steering', 'advisory', 'review', 'working_group'].map((opt) => `<option value="${opt}" ${opt === (comm?.committee_type || 'steering') ? 'selected' : ''}>${opt.replace(/_/g, ' ')}</option>`).join('')}</select></div>
                <div class="form-group"><label>Frequency</label><select id="ps_comm_frequency" class="form-input">${['daily', 'weekly', 'biweekly', 'monthly', 'ad_hoc'].map((opt) => `<option value="${opt}" ${opt === (comm?.meeting_frequency || 'weekly') ? 'selected' : ''}>${opt.replace(/_/g, ' ')}</option>`).join('')}</select></div>
            </div>
            <div class="form-group"><label>Chair</label><input id="ps_comm_chair" class="form-input" value="${esc(comm?.chair_name || '')}" placeholder="Optional chair"></div>
            <div class="form-actions">
                <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button type="button" class="btn btn-primary" onclick="ProjectSetupView._saveCommittee()">${isEdit ? 'Update' : 'Create'}</button>
            </div>
        `);
    }

    async function _saveCommittee() {
        const name = (document.getElementById('ps_comm_name')?.value || '').trim();
        if (!name) { App.toast('Committee name is required', 'error'); return; }
        const payload = {
            name,
            description: document.getElementById('ps_comm_description')?.value?.trim() || '',
            committee_type: document.getElementById('ps_comm_type')?.value || 'steering',
            meeting_frequency: document.getElementById('ps_comm_frequency')?.value || 'weekly',
            chair_name: document.getElementById('ps_comm_chair')?.value?.trim() || '',
            project_id: _activeProject?.id,
        };
        try {
            if (_committeeEditingId) {
                const updated = await API.put(`/committees/${_committeeEditingId}`, payload);
                const idx = _projectCommittees.findIndex((item) => Number(item.id) === Number(_committeeEditingId));
                if (idx >= 0) _projectCommittees[idx] = { ..._projectCommittees[idx], ...updated };
                App.toast('Committee updated', 'success');
            } else {
                const created = await API.post(`/programs/${_pid}/committees`, payload);
                _projectCommittees.push(created);
                App.toast('Committee created', 'success');
            }
            App.closeModal();
            _committeeEditingId = null;
            if (_currentTab === 'committees') _renderCommitteesContent(document.getElementById('setupContent'));
        } catch (err) {
            App.toast(err.message || 'Save failed', 'error');
        }
    }

    function _confirmDeleteCommittee(committeeId, committeeName) {
        _openConfirmModal({
            title: 'Delete committee',
            message: `Delete committee "${committeeName}"?`,
            confirmLabel: 'Delete committee',
            onConfirm: () => _deleteCommittee(committeeId),
        });
    }

    async function _deleteCommittee(committeeId) {
        try {
            await API.delete(`/committees/${committeeId}`);
            _projectCommittees = _projectCommittees.filter((item) => Number(item.id) !== Number(committeeId));
            App.toast('Committee deleted', 'success');
            if (_currentTab === 'committees') _renderCommitteesContent(document.getElementById('setupContent'));
        } catch (err) {
            App.toast(err.message || 'Delete failed', 'error');
        }
    }

    async function loadHierarchyTab() {
        const c = document.getElementById('setupContent');
        if (!_activeProject) {
            renderProjectRequiredGuard();
            return;
        }
        c.innerHTML = HierarchyUI.loading({ label: 'Loading project baseline…' });

        try {
            const treeResponse = _shouldUseLazyHierarchy()
                ? await ExploreAPI.levels.listTree(_activeProject.id, { max_depth: 2 })
                : await ExploreAPI.levels.listTree(_activeProject.id, _currentHierarchyQuery());
            _hierarchyMeta = {
                total: treeResponse?.total || 0,
                unfilteredTotal: treeResponse?.unfiltered_total || 0,
            };
            _hierarchyStats = Object.assign(
                { total: 0, l1: 0, l2: 0, l3: 0, l4: 0, in_scope: 0 },
                treeResponse?.stats || {}
            );
            _tree = treeResponse?.items || [];
            _flatList = flattenTree(_tree);
            _l1List = _flatList.filter((n) => Number(n.level) === 1);
            _l2List = _flatList.filter((n) => Number(n.level) === 2);
            _l3List = _flatList.filter((n) => Number(n.level) === 3);
            _l4List = _flatList.filter((n) => Number(n.level) === 4);
            _l4ByL3 = groupBy(_l4List, 'parent_id');
            if (_shouldUseLazyHierarchy()) {
                _expandedNodes = new Set(_tree.map((node) => node.id));
            }

            if (_flatList.length === 0 && _hierarchyMeta.unfilteredTotal === 0 && !_hasHierarchyQuery()) {
                renderEmptyState(c);
                return;
            }

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
            ${renderExecutionBridge()}
            ${renderToolbar()}
            <div id="hierarchyContent">
                ${_viewMode === 'tree' ? renderTreeContent() : renderTableView()}
            </div>
        `;
    }

    function renderExecutionBridge() {
        const baselineReady = (_hierarchyMeta.unfilteredTotal || _flatList.length) > 0;
        return HierarchyUI.bridgeCard({
            testId: 'project-setup-baseline-bridge',
            eyebrow: 'Bootstrap Owner',
            title: 'Project Setup owns the baseline structure',
            body: 'Import templates, bulk create process levels, and maintain the baseline here. Once the hierarchy is ready, execution continues in <strong>Scope &amp; Process</strong> for fit-gap review, workshops, sign-off, and governed scope changes.',
            actionsHtml: `
                ${ExpUI.actionButton({ label: 'Open Scope & Process', variant: baselineReady ? 'primary' : 'secondary', size: 'sm', onclick: "ProjectSetupView.openExecutionScope()" })}
                ${ExpUI.actionButton({ label: 'Open Workshop Hub', variant: 'ghost', size: 'sm', onclick: "ProjectSetupView.openWorkshopHub()" })}
            `,
        });
    }

    function renderKpiRow() {
        const inScopeCount = _hierarchyStats.in_scope || _flatList.filter(n => n.scope_status === 'in_scope').length;
        const totalCount = _hierarchyStats.total || _flatList.length || 0;
        const inScopePct = totalCount > 0 ? Math.round(inScopeCount / totalCount * 100) : 0;

        return `<div class="exp-kpi-strip" style="margin-bottom:16px">
            ${ExpUI.kpiBlock({ value: _hierarchyStats.l1 || _l1List.length, label: 'L1 Areas', icon: '🏛' })}
            ${ExpUI.kpiBlock({ value: _hierarchyStats.l2 || _l2List.length, label: 'L2 Groups', icon: '📁' })}
            ${ExpUI.kpiBlock({ value: _hierarchyStats.l3 || _l3List.length, label: 'L3 Scope Items', icon: '📋' })}
            ${ExpUI.kpiBlock({ value: _hierarchyStats.l4 || _l4List.length, label: 'L4 Steps', icon: '⚙' })}
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

        return HierarchyWidgets.filterToolbar({
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
            testId: 'project-setup-hierarchy-toolbar',
            actionsHtml: HierarchyUI.actionCluster(`
                <div style="display:flex;border:1px solid var(--pg-color-border);border-radius:var(--exp-radius-md);overflow:hidden">
                    <button class="view-toggle-btn${_viewMode === 'tree' ? ' active' : ''}" onclick="ProjectSetupView.setViewMode('tree')">🌳 Tree</button>
                    <button class="view-toggle-btn${_viewMode === 'table' ? ' active' : ''}" onclick="ProjectSetupView.setViewMode('table')">📊 Table</button>
                </div>

                ${ExpUI.actionButton({ label: '🤖 AI Suggested', variant: 'ghost', size: 'sm', onclick: 'ProjectSetupView.openAISuggested()' })}
                ${ExpUI.actionButton({ label: '📚 Import Template', variant: 'secondary', size: 'sm', onclick: 'ProjectSetupView.openTemplateImport()' })}
                ${ExpUI.actionButton({ label: '➕ Add L1 Area', variant: 'primary', size: 'sm', onclick: "ProjectSetupView.openCreateDialog(1, null)" })}
                ${ExpUI.actionButton({ label: '▶ Start Workshops', variant: 'ghost', size: 'sm', onclick: "ProjectSetupView.openWorkshopHub()" })}
            `),
        });
    }

    function renderTreeContent() {
        const nodes = _tree
            .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
            .map(n => renderTreeNode(n, 0))
            .filter(Boolean)
            .join('');

        return HierarchyWidgets.treeShell({
            testId: 'project-setup-hierarchy-tree',
            bodyHtml: nodes,
            emptyText: 'No results found.',
            footerHtml: HierarchyUI.actionCluster(`
                ${ExpUI.actionButton({ label: '➕ Add L1 Area', variant: 'secondary', size: 'sm', onclick: 'ProjectSetupView.openCreateDialog(1, null)' })}
                ${ExpUI.actionButton({ label: 'Open Scope & Process', variant: 'ghost', size: 'sm', onclick: 'ProjectSetupView.openExecutionScope()' })}
            `),
        });
    }

    function renderTreeNode(node, depth) {
        const lvl = node.level || depth + 1;
        const children = (node.children || []).sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
        const isExpanded = _expandedNodes.has(node.id);
        const indent = 16 + depth * 28;
        const levelColor = `var(--exp-l${lvl})`;
        const levelBg = `var(--exp-l${lvl}-bg)`;
        const hasChildren = Boolean(children.length || node.has_children);

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

        return HierarchyRenderers.treeRow({
            wrapperClass: 'setup-node',
            attrs: `data-id="${esc(node.id)}" data-level="${lvl}"`,
            rowClass: 'setup-node__row',
            rowStyle: `--setup-indent:${indent}px;--level-color:${levelColor};--level-bg:${levelBg}`,
            chevronHtml: HierarchyRenderers.treeChevron({
                hasChildren,
                expanded: isExpanded,
                onclick: `event.stopPropagation();ProjectSetupView.toggleNode('${node.id}')`,
                className: 'setup-chevron',
                openClass: 'setup-chevron--open',
                leafClass: 'setup-node__spacer',
            }),
            leadingHtml: HierarchyRenderers.levelToken({
                label: `L${lvl}`,
                className: 'setup-node__level',
                labelClass: 'setup-node__level-label',
            }),
            codeHtml: esc(node.code || ''),
            codeClass: 'setup-node__code',
            codeTag: 'code',
            nameHtml: esc(node.name || ''),
            nameClass: `setup-node__name ${lvl <= 2 ? 'setup-node__name--strong' : ''}`,
            nameAttrs: `onclick="ProjectSetupView.openEditDialog('${node.id}',${lvl})" title="${esc(node.name || '')}"`,
            metaHtml: `
                ${scopeBadge}
                ${node.process_area_code ? `<span class="setup-node__process">${esc(node.process_area_code)}</span>` : ''}
                ${node.wave ? `<span class="setup-node__wave">W${node.wave}</span>` : ''}
            `,
            metaClass: 'setup-node__meta',
            actionsHtml: `
                ${lvl < 4 ? `<button class="btn-icon" title="Add L${lvl + 1}" onclick="event.stopPropagation();ProjectSetupView.openCreateDialog(${lvl + 1},'${node.id}')">+</button>` : ''}
                <button class="btn-icon" title="Edit" onclick="event.stopPropagation();ProjectSetupView.openEditDialog('${node.id}',${lvl})">✏️</button>
                <button class="btn-icon btn-icon--danger" title="Delete" onclick="event.stopPropagation();ProjectSetupView.confirmDelete('${node.id}','${esc(node.name || '')}')">🗑️</button>
            `,
            actionsClass: 'setup-node__actions',
            childrenHtml: filteredChildren && isExpanded ? filteredChildren : '',
        });
    }

    function renderTableView() {
        const flat = flattenTree(_tree);
        const tableHtml = `
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
        `;

        return HierarchyRenderers.tableCard({
            testId: 'project-setup-hierarchy-table',
            tableHtml,
        });
    }

    function renderTableRow(node) {
        const lvl = node.level || 1;
        const levelColor = `var(--exp-l${lvl})`;
        const levelBg = `var(--exp-l${lvl}-bg)`;
        const parentNode = _flatList.find(n => n.id === node.parent_id);

        if (!matchesFilters(node) || !matchesSearch(node)) return '';

        return HierarchyRenderers.tableRow({
            rowClass: 'hierarchy-table-row--interactive',
            onclick: `ProjectSetupView.openEditDialog('${node.id}',${lvl})`,
            cells: [
                {
                    html: HierarchyRenderers.levelToken({
                        label: `L${lvl}`,
                        style: `--hierarchy-level-bg:${levelBg};--hierarchy-level-color:${levelColor};width:26px;height:20px;border-radius:4px;font-size:11px;font-weight:700;`,
                    }),
                },
                { html: esc(node.code || ''), className: 'hierarchy-table-cell--mono', tag: 'td' },
                { html: esc(node.name || ''), attrs: `style="font-weight:${lvl <= 2 ? 600 : 400}"` },
                { html: esc(node.process_area_code || '—'), className: 'hierarchy-table-cell--muted' },
                {
                    html: ExpUI.pill({
                        label: (node.scope_status || 'pending').replace(/_/g, ' '),
                        variant: node.scope_status === 'in_scope' ? 'success' : node.scope_status === 'out_of_scope' ? 'danger' : 'warning',
                        size: 'sm',
                    }),
                },
                { html: node.wave ? `W${node.wave}` : '—', className: 'hierarchy-table-cell--muted' },
                { html: parentNode ? esc(parentNode.code || '') : '—', className: 'hierarchy-table-cell--muted-soft' },
                {
                    html: `
                        <button class="btn-icon" onclick="ProjectSetupView.openEditDialog('${node.id}',${lvl})">✏️</button>
                        <button class="btn-icon btn-icon--danger" onclick="ProjectSetupView.confirmDelete('${node.id}','${esc(node.name || '')}')">🗑️</button>
                    `,
                    attrs: 'style="text-align:right" onclick="event.stopPropagation()"',
                },
            ],
        });
    }

    function renderEmptyState(container) {
        container.innerHTML = `
            <div style="padding:60px 20px;text-align:center;max-width:800px;margin:0 auto">
                <div style="font-size:56px;margin-bottom:12px">🏗️</div>
                <h2 style="margin-bottom:8px;font-size:22px">No Process Hierarchy Defined</h2>
                <p style="color:var(--pg-color-text-secondary);margin-bottom:32px;font-size:14px">
                    Build your L1 → L4 process structure to start your SAP project
                </p>
                ${HierarchyWidgets.choiceGrid({
                    testId: 'project-setup-hierarchy-choice-grid',
                    cards: [
                        {
                            icon: '📚',
                            title: 'Import SAP Template',
                            body: 'Pre-built L1→L4 hierarchy from SAP Best Practice catalog. Select areas to import.',
                            footerHtml: ExpUI.pill({ label: '5 areas · 265 items', variant: 'info', size: 'sm' }),
                            onclick: 'ProjectSetupView.openTemplateImport()',
                        },
                        {
                            icon: '🤖',
                            title: 'AI-Suggested Hierarchy',
                            body: 'AI generates a customized hierarchy based on your industry, SAP modules, and company profile.',
                            footerHtml: ExpUI.pill({ label: 'Powered by AI', variant: 'decision', size: 'sm' }),
                            badge: 'Coming Soon',
                            comingSoon: true,
                            onclick: 'ProjectSetupView.openAISuggested()',
                        },
                        {
                            icon: '✍️',
                            title: 'Start from Scratch',
                            body: 'Grid entry or paste from Excel. Add multiple levels at once.',
                            footerHtml: ExpUI.pill({ label: 'Flexible', variant: 'draft', size: 'sm' }),
                            onclick: 'ProjectSetupView.openBulkEntry()',
                        },
                    ],
                })}
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

        App.openModal(HierarchyWidgets.modalFrame({
            testId: 'project-setup-bulk-modal',
            title: '✍️ Start from Scratch',
            subtitle: 'Add process levels manually — one at a time or through bulk entry.',
            maxWidth: '820px',
            bodyHtml: `
                <div class="hierarchy-modal__toggle-group">
                    <button class="view-toggle-btn${_bulkMode === 'grid' ? ' active' : ''}" onclick="ProjectSetupView._setBulkMode('grid')">📊 Grid Entry</button>
                    <button class="view-toggle-btn${_bulkMode === 'paste' ? ' active' : ''}" onclick="ProjectSetupView._setBulkMode('paste')">📋 Paste from Excel</button>
                </div>
                <div id="bulkContent">${_bulkMode === 'grid' ? renderGridMode() : renderPasteMode()}</div>
            `,
            footerHtml: `
                <div id="bulkStatus" class="hierarchy-modal__meta">
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
            `,
        }));
    }

    function openExecutionScope() {
        App.navigate('explore-scope');
    }

    function openWorkshopHub() {
        App.navigate('explore-workshops');
    }

    function renderGridMode() {
        const existingCodes = _flatList.map(n => ({ code: n.code, name: n.name, level: n.level }));

        return `
            <div class="hierarchy-modal__table-wrap">
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
                <div class="hierarchy-modal__note" style="font-family:var(--exp-font-mono)">
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
            <div class="card hierarchy-modal__surface">
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
            const result = await ExploreAPI.levels.bulkCreate(_activeProject.id, rows, {
                mutation_context: HIERARCHY_MUTATION_CONTEXT,
            });
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

        App.openModal(HierarchyWidgets.modalFrame({
            testId: 'project-setup-create-level-modal',
            title: `Create L${level}`,
            subtitle: 'Add a new baseline node to the project-owned hierarchy.',
            maxWidth: '640px',
            compact: true,
            bodyHtml: `
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
            `,
            footerHtml: `
                <div></div>
                <div style="display:flex;gap:8px">
                    ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                    ${ExpUI.actionButton({ label: 'Create', variant: 'primary', onclick: `ProjectSetupView.submitCreate(${level}, ${parentId ? `'${parentId}'` : 'null'})` })}
                </div>
            `,
        }));
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
            mutation_context: HIERARCHY_MUTATION_CONTEXT,
        };

        try {
            await ExploreAPI.levels.create(_activeProject.id, payload);
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

        App.openModal(HierarchyWidgets.modalFrame({
            testId: 'project-setup-edit-level-modal',
            title: `Edit ${esc(node.code || 'Process Level')}`,
            subtitle: 'Update baseline metadata before execution starts.',
            maxWidth: '640px',
            compact: true,
            bodyHtml: `
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
            `,
            footerHtml: `
                <div></div>
                <div style="display:flex;gap:8px">
                    ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                    ${ExpUI.actionButton({ label: 'Save', variant: 'primary', onclick: `ProjectSetupView.submitEdit('${id}')` })}
                </div>
            `,
        }));
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
                mutation_context: HIERARCHY_MUTATION_CONTEXT,
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
            preview = await ExploreAPI.levels.remove(id, false, {
                mutation_context: HIERARCHY_MUTATION_CONTEXT,
            });
        } catch (err) {
            App.toast(err.message || 'Delete preview failed', 'error');
            return;
        }

        if (!preview || !preview.preview) {
            App.toast('Unable to load delete preview', 'error');
            return;
        }

        const byLevel = preview.by_level || {};
        App.openModal(HierarchyWidgets.modalFrame({
            testId: 'project-setup-delete-level-modal',
            title: 'Delete Process Level',
            subtitle: `This will delete ${esc(name || preview.target.name)} and its descendants.`,
            maxWidth: '560px',
            compact: true,
            bodyHtml: `
                <div class="card hierarchy-modal__surface hierarchy-modal__surface--danger">
                    <p style="color:var(--pg-color-negative)"><strong>Warning:</strong> This action cannot be undone.</p>
                    <p>Will delete ${preview.descendants_count} descendants (${Object.keys(byLevel).map(k => `${k}: ${byLevel[k]}`).join(', ')}).</p>
                </div>
            `,
            footerHtml: `
                <div></div>
                <div style="display:flex;gap:8px">
                    ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                    ${ExpUI.actionButton({ label: 'Delete', variant: 'danger', onclick: `ProjectSetupView.executeDelete('${id}')` })}
                </div>
            `,
        }));
    }

    async function executeDelete(id) {
        try {
            await ExploreAPI.levels.remove(id, true, {
                mutation_context: HIERARCHY_MUTATION_CONTEXT,
            });
            App.toast('Deleted', 'success');
            App.closeModal();
            await loadHierarchyTab();
        } catch (err) {
            App.toast(err.message || 'Delete failed', 'error');
        }
    }

    function openTemplateImport() {
        App.openModal(HierarchyWidgets.modalFrame({
            testId: 'project-setup-template-import-modal',
            title: '📚 Import SAP Template',
            subtitle: 'Select L1 areas to import from SAP Best Practice.',
            maxWidth: '720px',
            bodyHtml: `
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                    <input type="checkbox" id="tplSelectAll" onchange="ProjectSetupView.toggleTemplateAll()">
                    <label for="tplSelectAll"><strong>Select All</strong></label>
                </div>
                <div class="hierarchy-modal__stack">
                    ${TEMPLATE_L1.map((t, idx) => `
                        <label class="hierarchy-modal__surface" style="display:flex;gap:10px;align-items:flex-start">
                            <input type="checkbox" class="tplCheck" data-code="${t.code}" data-index="${idx}">
                            <div>
                                <div><strong>${t.name}</strong> <span style="color:var(--pg-color-text-secondary)">(${t.code} · ${t.module})</span></div>
                                <div style="color:var(--pg-color-text-secondary);font-size:12px">${t.desc}</div>
                                <div style="color:var(--pg-color-text-secondary);font-size:12px">${t.stats}</div>
                            </div>
                        </label>
                    `).join('')}
                </div>
            `,
            footerHtml: `
                <div></div>
                <div style="display:flex;gap:8px">
                    ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', onclick: 'App.closeModal()' })}
                    ${ExpUI.actionButton({ label: 'Import', variant: 'primary', id: 'tplImportBtn', onclick: 'ProjectSetupView.submitTemplateImport()' })}
                </div>
            `,
        }));
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
            const res = await ExploreAPI.levels.importTemplate(_activeProject.id, {
                mutation_context: HIERARCHY_MUTATION_CONTEXT,
                selected_l1_codes: selected,
            });
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
        App.openModal(HierarchyWidgets.modalFrame({
            testId: 'project-setup-ai-hierarchy-modal',
            title: '🤖 AI-Suggested Hierarchy',
            subtitle: "AI will analyze your project's industry, SAP modules, and company profile to generate a customized L1→L2→L3 process hierarchy.",
            maxWidth: '480px',
            bodyHtml: `
                <div class="hierarchy-modal__surface hierarchy-modal__surface--center">
                    <div style="font-size:48px;margin-bottom:16px">🤖</div>
                    <div class="hierarchy-modal__surface-title">What AI will do</div>
                    <div class="hierarchy-modal__surface-copy" style="text-align:left">
                        ✦ Analyze your industry & company profile<br>
                        ✦ Map relevant SAP modules to processes<br>
                        ✦ Generate L1→L2→L3 hierarchy with SAP Best Practice codes<br>
                        ✦ Preview before import — you review & edit first
                    </div>
                </div>
                <div style="display:flex;justify-content:center;margin-top:16px">
                    ${ExpUI.pill({ label: 'Coming in Sprint 13', variant: 'info', size: 'md' })}
                </div>
            `,
            footerHtml: `
                <div></div>
                <div>${ExpUI.actionButton({ label: 'Close', variant: 'secondary', onclick: 'App.closeModal()' })}</div>
            `,
        }));
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
            mutation_context: HIERARCHY_MUTATION_CONTEXT,
        };

        try {
            await ExploreAPI.levels.create(_activeProject.id, payload);
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

    async function toggleNode(id) {
        const node = findHierarchyNode(id);
        if (_expandedNodes.has(id)) {
            _expandedNodes.delete(id);
            rerenderContent();
            return;
        }
        if (_shouldUseLazyHierarchy() && node?.has_children && !node?.children_loaded) {
            await _loadHierarchyChildren(id);
        }
        _expandedNodes.add(id);
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
        _scheduleHierarchyReload();
    }

    function setFilter(groupId, value) {
        const nextVal = value || null;
        _filters[groupId] = _filters[groupId] === nextVal ? null : nextVal;
        _scheduleHierarchyReload();
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
        _scheduleHierarchyReload();
    }

    function setViewMode(mode) {
        if (_viewMode === mode) return;
        _viewMode = mode;
        if (_currentTab === 'scope-hierarchy') {
            loadHierarchyTab();
            return;
        }
        rerenderContent();
    }

    function rerenderContent() {
        const el = document.getElementById('hierarchyContent');
        if (!el) return;
        el.innerHTML = _viewMode === 'tree' ? renderTreeContent() : renderTableView();
    }

    function _currentHierarchyQuery() {
        return {
            q: _searchQuery || '',
            process_area: _filters.area || '',
            scope_status: _filters.scope || '',
        };
    }

    function _shouldUseLazyHierarchy() {
        return _viewMode === 'tree' && !_hasHierarchyQuery();
    }

    function _hasHierarchyQuery() {
        return Boolean(_searchQuery || _filters.area || _filters.scope);
    }

    function findHierarchyNode(id, nodes = _tree) {
        for (const node of nodes || []) {
            if (String(node.id) === String(id)) return node;
            const found = findHierarchyNode(id, node.children || []);
            if (found) return found;
        }
        return null;
    }

    async function _loadHierarchyChildren(id) {
        const node = findHierarchyNode(id);
        if (!node) return;
        const response = await ExploreAPI.levels.listChildren(_activeProject.id, id);
        node.children = response?.items || [];
        node.children_loaded = true;
    }

    function _scheduleHierarchyReload() {
        clearTimeout(_hierarchyReloadTimer);
        _hierarchyReloadTimer = setTimeout(() => {
            if (_currentTab === 'scope-hierarchy') loadHierarchyTab();
        }, 220);
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

    function groupBy(arr, key) {
        const grouped = {};
        (arr || []).forEach((item) => {
            const groupKey = item?.[key];
            if (groupKey == null) return;
            if (!grouped[groupKey]) grouped[groupKey] = [];
            grouped[groupKey].push(item);
        });
        return grouped;
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
        // Project Info CRUD
        renderProjectInfoTab,
        _openProjectInfoEdit,
        _saveProjectInfo,
        // Team CRUD
        renderTeamTab,
        _openTeamMemberForm,
        _closeTeamModal,
        _saveTeamMember,
        _confirmDeleteTeamMember,
        _cancelConfirmModal,
        _runConfirmAction,
        // Operating model tabs
        renderWorkstreamsTab,
        renderCommitteesTab,
        renderGovernanceTab,
        _openWorkstreamForm,
        _saveWorkstream,
        _confirmDeleteWorkstream,
        _openCommitteeForm,
        _saveCommittee,
        _confirmDeleteCommittee,
        // Methodology & Phases
        renderMethodologyTab,
        _toggleMethEdit,
        _saveMethConfig,
        _seedSAPActivatePhases,
        _openPhaseForm,
        _closePhaseModal,
        _savePhase,
        _confirmDeletePhase,
        // Timeline
        renderTimelineTab,
        // Scope & Hierarchy
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
        openExecutionScope,
        openWorkshopHub,
    };
})();
