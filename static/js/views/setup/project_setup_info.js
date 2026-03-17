const ProjectSetupInfo = (() => {
    const esc = ExpUI.esc;

    const STATUS_OPTS = ['planning', 'active', 'on_hold', 'completed', 'cancelled'];
    const TYPE_OPTS = ['implementation', 'rollout', 'upgrade', 'support', 'pilot'];
    const SAP_OPTS = ['S/4HANA', 'SuccessFactors', 'Ariba', 'BTP', 'Other'];
    const PROJECT_TYPE_OPTS = ['greenfield', 'brownfield', 'bluefield', 'selective_data_transition'];
    const METHODOLOGY_OPTS = ['sap_activate', 'agile', 'waterfall', 'hybrid'];
    const DEPLOYMENT_OPTS = ['on_premise', 'cloud', 'hybrid'];
    const PRIORITY_OPTS = ['low', 'medium', 'high', 'critical'];
    const RAG_OPTS = ['', 'green', 'amber', 'red'];

    function _fmt(value) {
        return value ? esc(String(value)) : '<span style="color:var(--pg-color-text-tertiary)">—</span>';
    }

    function _ragBadge(value) {
        if (!value) return _fmt(null);
        const colors = { green: '#22c55e', amber: '#f59e0b', red: '#ef4444' };
        return `<span style="display:inline-flex;align-items:center;gap:4px"><span style="width:10px;height:10px;border-radius:50%;background:${colors[value.toLowerCase()] || '#aaa'}"></span>${esc(value)}</span>`;
    }

    function _select(name, options, value) {
        return `<select id="pi_${name}" class="pg-input" style="width:100%">
            ${options.map((option) => `<option value="${option}" ${(value || '') === option ? 'selected' : ''}>${option || '—'}</option>`).join('')}
        </select>`;
    }

    function renderView({ container, project, activeProgram }) {
        container.innerHTML = `
            <div class="card" style="padding:20px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <h3 style="margin:0">Project Information</h3>
                    ${ExpUI.actionButton({ label: '✏️ Edit', variant: 'secondary', size: 'sm', onclick: 'ProjectSetupView._openProjectInfoEdit()' })}
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
                    <div>
                        <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--pg-color-text-secondary);margin-bottom:10px">Basic</div>
                        <dl class="detail-list">
                            <dt>Program</dt><dd>${_fmt(activeProgram?.name)}</dd>
                            <dt>Project Name</dt><dd>${_fmt(project.name)}</dd>
                            <dt>Project Code</dt><dd><code>${_fmt(project.code)}</code></dd>
                            <dt>Status</dt><dd>${_fmt(project.status)}</dd>
                            <dt>Type</dt><dd>${_fmt(project.type)}</dd>
                            <dt>Default Project</dt><dd>${project.is_default ? '✅ Yes' : 'No'}</dd>
                            <dt>Wave</dt><dd>${_fmt(project.wave_number)}</dd>
                        </dl>
                    </div>
                    <div>
                        <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--pg-color-text-secondary);margin-bottom:10px">Timeline</div>
                        <dl class="detail-list">
                            <dt>Start Date</dt><dd>${_fmt(project.start_date)}</dd>
                            <dt>End Date</dt><dd>${_fmt(project.end_date)}</dd>
                            <dt>Go-Live Date</dt><dd>${_fmt(project.go_live_date)}</dd>
                        </dl>
                        <div style="display:flex;justify-content:space-between;align-items:center;margin:16px 0 10px">
                            <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--pg-color-text-secondary)">Delivery Profile</div>
                            ${ExpUI.actionButton({ label: 'Open Methodology', variant: 'ghost', size: 'sm', onclick: "ProjectSetupView.switchTab('methodology')" })}
                        </div>
                        <dl class="detail-list">
                            <dt>SAP Product</dt><dd>${_fmt(project.sap_product)}</dd>
                            <dt>Project Type</dt><dd>${_fmt(project.project_type)}</dd>
                            <dt>Methodology</dt><dd>${_fmt(project.methodology)}</dd>
                            <dt>Deployment</dt><dd>${_fmt(project.deployment_option)}</dd>
                            <dt>Priority</dt><dd>${_fmt(project.priority)}</dd>
                        </dl>
                    </div>
                </div>

                ${project.description ? `
                <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--pg-color-border)">
                    <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--pg-color-text-secondary);margin-bottom:6px">Description</div>
                    <p style="margin:0;font-size:13px;color:var(--pg-color-text-secondary);line-height:1.6">${esc(project.description)}</p>
                </div>` : ''}

                ${(project.project_rag || project.rag_scope) ? `
                <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--pg-color-border)">
                    <div style="font-size:11px;font-weight:600;text-transform:uppercase;color:var(--pg-color-text-secondary);margin-bottom:10px">5-Dimensional RAG</div>
                    <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:13px">
                        <span>Overall: ${_ragBadge(project.project_rag)}</span>
                        <span>Scope: ${_ragBadge(project.rag_scope)}</span>
                        <span>Timeline: ${_ragBadge(project.rag_timeline)}</span>
                        <span>Budget: ${_ragBadge(project.rag_budget)}</span>
                        <span>Quality: ${_ragBadge(project.rag_quality)}</span>
                        <span>Resources: ${_ragBadge(project.rag_resources)}</span>
                    </div>
                </div>` : ''}
            </div>`;
    }

    function renderEdit({ container, project }) {
        container.innerHTML = `
            <div class="card" style="padding:20px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
                    <h3 style="margin:0">Edit Project Information</h3>
                    <div style="display:flex;gap:8px">
                        ${ExpUI.actionButton({ label: 'Cancel', variant: 'secondary', size: 'sm', onclick: 'ProjectSetupView.renderProjectInfoTab()' })}
                        ${ExpUI.actionButton({ label: '💾 Save', variant: 'primary', size: 'sm', id: 'piSaveBtn', onclick: 'ProjectSetupView._saveProjectInfo()' })}
                    </div>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
                    <div class="form-group">
                        <label class="form-label">Project Name *</label>
                        <input id="pi_name" class="pg-input" value="${esc(project.name || '')}" style="width:100%">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Project Code *</label>
                        <input id="pi_code" class="pg-input" value="${esc(project.code || '')}" style="width:100%">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Status</label>
                        ${_select('status', STATUS_OPTS, project.status)}
                    </div>
                    <div class="form-group">
                        <label class="form-label">Type</label>
                        ${_select('type', TYPE_OPTS, project.type)}
                    </div>
                    <div class="form-group">
                        <label class="form-label">Start Date</label>
                        <input id="pi_start_date" type="date" class="pg-input" value="${project.start_date || ''}" style="width:100%">
                    </div>
                    <div class="form-group">
                        <label class="form-label">End Date</label>
                        <input id="pi_end_date" type="date" class="pg-input" value="${project.end_date || ''}" style="width:100%">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Go-Live Date</label>
                        <input id="pi_go_live_date" type="date" class="pg-input" value="${project.go_live_date || ''}" style="width:100%">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Wave Number</label>
                        <input id="pi_wave_number" type="number" class="pg-input" value="${project.wave_number || ''}" min="1" style="width:100%">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Priority</label>
                        ${_select('priority', PRIORITY_OPTS, project.priority)}
                    </div>
                    <div class="form-group">
                        <label class="form-label">Overall RAG</label>
                        ${_select('project_rag', RAG_OPTS, project.project_rag)}
                    </div>
                </div>

                <div class="form-group" style="margin-top:16px">
                    <label class="form-label">Description</label>
                    <textarea id="pi_description" class="pg-input" rows="3" style="width:100%;resize:vertical">${esc(project.description || '')}</textarea>
                </div>
            </div>`;
    }

    function readEditState() {
        const get = (id) => document.getElementById(id);
        const name = (get('pi_name')?.value || '').trim();
        const code = (get('pi_code')?.value || '').trim();

        if (!name) return { error: 'Project name is required' };
        if (!code) return { error: 'Project code is required' };

        return {
            payload: {
                name,
                code,
                status: get('pi_status')?.value || undefined,
                type: get('pi_type')?.value || undefined,
                start_date: get('pi_start_date')?.value || null,
                end_date: get('pi_end_date')?.value || null,
                go_live_date: get('pi_go_live_date')?.value || null,
                wave_number: get('pi_wave_number')?.value ? parseInt(get('pi_wave_number').value, 10) : null,
                priority: get('pi_priority')?.value || undefined,
                project_rag: get('pi_project_rag')?.value || null,
                description: get('pi_description')?.value || '',
            },
        };
    }

    return { renderView, renderEdit, readEditState };
})();
