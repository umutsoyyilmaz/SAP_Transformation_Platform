const ReportsView = (() => {
    let healthData = null;
    let presets = [];
    let activeTab = 'catalog';
    let chartInstances = [];
    let lastRunContext = null;
    let programProjects = [];
    let activeProgramReport = null;
    const PLATFORM_PERMISSION_SOURCE = 'platformPermissions';

    const CATEGORY_LABELS = {
        coverage: 'Coverage',
        execution: 'Execution',
        defect: 'Defect',
        traceability: 'Traceability',
        ai_insights: 'AI Insights',
        plan: 'Plan / Release',
        custom: 'Custom',
    };
    const CATEGORY_KEYS = ['coverage', 'execution', 'defect', 'traceability', 'ai_insights', 'plan'];
    const GOVERNANCE_RAG = {
        green: { bg: '#dcfce7', fg: '#14532d', label: 'Green' },
        amber: { bg: '#fef3c7', fg: '#92400e', label: 'Amber' },
        red: { bg: '#fee2e2', fg: '#991b1b', label: 'Red' },
    };
    const REPORT_STATUS_LABELS = {
        draft: 'Draft',
        in_review: 'In Review',
        approved: 'Approved',
        presented: 'Presented',
        archived: 'Archived',
    };

    function esc(value) {
        const d = document.createElement('div');
        d.textContent = value || '';
        return d.innerHTML;
    }

    function formatDate(value) {
        if (!value) return 'No date';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString();
    }

    function excerpt(text, max = 140) {
        const clean = String(text || '').trim();
        if (!clean) return '';
        if (clean.length <= max) return clean;
        return `${clean.slice(0, max - 1).trim()}…`;
    }

    function pctBar(pct, color) {
        const safe = Math.max(0, Math.min(Number(pct) || 0, 100));
        return `
            <span class="governance-progress" style="--governance-progress-color:${color || '#0070f3'};--governance-progress-pct:${safe}%">
                <span class="governance-progress__track">
                    <span class="governance-progress__fill"></span>
                </span>
                <span class="governance-progress__label">${safe}%</span>
            </span>
        `;
    }

    function ragBadge(value) {
        const key = String(value || '').trim().toLowerCase();
        const palette = GOVERNANCE_RAG[key];
        if (!palette) {
            return `<span class="governance-pill governance-pill--muted">RAG not set</span>`;
        }
        return `<span class="governance-pill governance-pill--${esc(key)}">${palette.label}</span>`;
    }

    function statusBadge(status) {
        const key = String(status || 'draft').trim().toLowerCase();
        return PGStatusRegistry.badge(key, { label: REPORT_STATUS_LABELS[key] || status || 'Draft' });
    }

    function reportMeta(report) {
        const parts = [];
        if (report.report_number != null) parts.push(`Report #${report.report_number}`);
        if (report.report_date) parts.push(formatDate(report.report_date));
        return parts.join(' · ') || 'Draft report';
    }

    function _statePanel(message, variant = 'muted') {
        return `<div class="card governance-panel governance-panel--${variant}">${esc(message)}</div>`;
    }

    function _statePanelWithBody(title, message, variant = 'error') {
        return `
            <div class="card governance-panel governance-panel--${variant}">
                <div class="governance-empty-state governance-empty-state--panel">
                    <div class="governance-empty-state__title">${esc(title)}</div>
                    <p class="governance-empty-state__copy">${esc(message)}</p>
                </div>
            </div>
        `;
    }

    function _activeProjectName() {
        if (typeof App.getActiveProject !== 'function') return 'Program-wide';
        return App.getActiveProject()?.name || 'Program-wide';
    }

    function _destroyCharts() {
        chartInstances.forEach((c) => {
            try {
                c.destroy();
            } catch (_) {
                // noop
            }
        });
        chartInstances = [];
    }

    async function _loadProgramProjects(programId) {
        if (!programId) return [];
        try {
            const data = await API.get(`/programs/${programId}/projects`);
            return Array.isArray(data) ? data : [];
        } catch (_) {
            return [];
        }
    }

    async function _metricsSnapshotForProgram(programId) {
        try {
            return JSON.stringify(await API.get(`/reports/program-health/${programId}`));
        } catch (_) {
            return null;
        }
    }

    function _currentProgram() {
        return App.getActiveProgram();
    }

    async function _preloadPlatformPermissions() {
        try {
            await RoleNav.preloadSource(PLATFORM_PERMISSION_SOURCE);
        } catch (_) {
            // noop: server-side enforcement remains authoritative
        }
    }

    function _can(permission) {
        return !!RoleNav.canSyncInSource(PLATFORM_PERMISSION_SOURCE, permission);
    }

    function _guardPlatformPermission(permission, message) {
        if (_can(permission)) {
            return true;
        }
        App.toast(message, 'warning');
        return false;
    }

    function _baseActionsHtml() {
        return `
            <div class="workspace-action-buttons">
                <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.showAISteeringPackModal()">AI Steering Pack</button>
                <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.exportXlsx()">Excel</button>
                <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.exportPdf()">Print</button>
            </div>
        `;
    }

    function _tabButton(id, label) {
        return `
            <button class="governance-tab ${activeTab === id ? 'governance-tab--active' : ''}" onclick="ReportsView.switchTab('${id}')">
                ${esc(label)}
            </button>
        `;
    }

    function _openReportsModal({
        title,
        body,
        footer,
        closeAction = 'App.closeModal()',
        modalClass = 'governance-modal',
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

    async function render() {
        _destroyCharts();
        const main = document.getElementById('mainContent');
        const prog = _currentProgram();

        if (!prog) {
            main.innerHTML = PGEmptyState.html({
                icon: 'reports',
                title: 'No Program Selected',
                description: 'Select a program first to view governance reporting.',
                action: { label: 'Go to Programs', onclick: "App.navigate('programs')" },
            });
            return;
        }

        await _preloadPlatformPermissions();

        main.innerHTML = GovernanceUI.shell({
            current: 'reports',
            testId: 'governance-reports-page',
            breadcrumbs: [{ label: 'Governance' }, { label: 'Reports' }],
            eyebrow: 'Governance',
            title: 'Reports',
            subtitle: 'Curated report library, saved runs, program snapshots, and SteerCo reporting lifecycle.',
            context: {
                program: prog.name,
                project: _activeProjectName(),
                status: prog.status || 'active',
                phase: 'Governance reporting',
            },
            actionsHtml: _baseActionsHtml(),
            bodyHtml: `
                <div class="workspace-section-stack governance-stack">
                    <div class="card governance-panel">
                        <div class="governance-tab-strip" data-testid="governance-reports-tabs">
                            ${_tabButton('catalog', 'Report Library')}
                            ${_tabButton('saved', 'Saved Reports')}
                            ${_tabButton('steerco', 'SteerCo Reports')}
                            ${_tabButton('snapshot', 'Program Snapshot')}
                        </div>
                    </div>
                    <div id="reportContent"></div>
                </div>
            `,
        });

        try {
            if (activeTab === 'snapshot') {
                healthData = await API.get(`/reports/program-health/${prog.id}`);
                renderHealth();
                return;
            }
            if (activeTab === 'catalog') {
                await renderCatalog();
                return;
            }
            if (activeTab === 'saved') {
                await renderSaved();
                return;
            }
            if (activeTab === 'steerco') {
                await renderSteerco();
                return;
            }
        } catch (err) {
            document.getElementById('reportContent').innerHTML = _statePanelWithBody('Unable to load reports', err.message || 'Unknown error');
        }
    }

    function switchTab(tab) {
        activeTab = tab;
        render();
    }

    function renderHealth() {
        if (!healthData) return;
        const h = healthData;
        const a = h.areas || {};

        const container = document.getElementById('reportContent');
        container.innerHTML = `
            <div class="workspace-section-stack" data-testid="governance-program-snapshot">
                <div class="card governance-panel">
                    <div class="governance-panel__header">
                        <div>
                            <div class="governance-panel__eyebrow">Program snapshot</div>
                            <h3 class="governance-panel__title">Health Summary</h3>
                            <p class="governance-panel__description">Current program health, phase progress, and governance-ready export view.</p>
                        </div>
                        <div class="governance-summary-inline">
                            ${ragBadge(h.overall_rag)}
                            <span class="governance-summary-inline__meta">${h.generated_at ? new Date(h.generated_at).toLocaleString() : ''}</span>
                        </div>
                    </div>
                </div>

                <div class="governance-snapshot-grid">
                    ${renderAreaCard('Explore', a.explore, [
                        { label: 'Workshops', value: `${a.explore?.workshops?.completed || 0}/${a.explore?.workshops?.total || 0}`, pct: a.explore?.workshops?.pct },
                        { label: 'Requirements Approved', pct: a.explore?.requirements?.pct },
                        { label: 'Overdue OIs', value: a.explore?.open_items?.overdue || 0, alert: (a.explore?.open_items?.overdue || 0) > 0 },
                    ])}
                    ${renderAreaCard('Backlog', a.backlog, [
                        { label: 'Items Done', value: `${a.backlog?.items?.done || 0}/${a.backlog?.items?.total || 0}`, pct: a.backlog?.items?.pct },
                    ])}
                    ${renderAreaCard('Testing', a.testing, [
                        { label: 'Pass Rate', pct: a.testing?.pass_rate },
                        { label: 'Test Cases', value: a.testing?.test_cases || 0 },
                        { label: 'Open Defects', value: a.testing?.defects?.open || 0, alert: (a.testing?.defects?.s1_open || 0) > 0 },
                        { label: 'S1 Open', value: a.testing?.defects?.s1_open || 0, alert: (a.testing?.defects?.s1_open || 0) > 0 },
                    ])}
                    ${renderAreaCard('RAID', a.raid, [
                        { label: 'Open Risks', value: a.raid?.risks_open || 0 },
                        { label: 'Red Risks', value: a.raid?.risks_red || 0, alert: (a.raid?.risks_red || 0) > 0 },
                        { label: 'Overdue Actions', value: a.raid?.actions_overdue || 0, alert: (a.raid?.actions_overdue || 0) > 0 },
                    ])}
                    ${renderAreaCard('Integration', a.integration, [
                        { label: 'Interfaces Live', value: `${a.integration?.interfaces?.live || 0}/${a.integration?.interfaces?.total || 0}`, pct: a.integration?.interfaces?.pct },
                    ])}
                </div>

                <div class="card governance-panel">
                    <div class="governance-panel__header governance-panel__header--compact">
                        <div>
                            <div class="governance-panel__eyebrow">Readiness timeline</div>
                            <h3 class="governance-panel__title">Phase Timeline</h3>
                        </div>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Phase</th>
                                <th>Status</th>
                                <th>Completion</th>
                                <th>Planned Start</th>
                                <th>Planned End</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${(h.phases || []).map((phase) => `
                                <tr>
                                    <td><strong>${esc(phase.name)}</strong></td>
                                    <td>${PGStatusRegistry.badge(phase.status)}</td>
                                    <td>${pctBar(phase.completion_pct, _pctColor(phase.completion_pct))}</td>
                                    <td>${phase.planned_start || '—'}</td>
                                    <td>${phase.planned_end || '—'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    async function renderCatalog() {
        const container = document.getElementById('reportContent');
        try {
            const resp = await API.get('/reports/presets');
            presets = resp.presets || [];
        } catch (_) {
            presets = [];
        }

        const grouped = {};
        CATEGORY_KEYS.forEach((key) => { grouped[key] = []; });
        presets.forEach((preset) => {
            const category = preset.category || 'custom';
            if (!grouped[category]) grouped[category] = [];
            grouped[category].push(preset);
        });

        container.innerHTML = `
            <div class="workspace-section-stack">
                <div class="card governance-panel">
                    <div class="governance-panel__header">
                        <div>
                            <div class="governance-panel__eyebrow">Preset catalog</div>
                            <h3 class="governance-panel__title">Run Curated Reports</h3>
                            <p class="governance-panel__description">Execute supported report presets, inspect the result, then save useful ones into your shared library.</p>
                        </div>
                    </div>
                    <div class="f5-catalog-grid">
                        ${CATEGORY_KEYS.map((cat) => `
                            <div class="card f5-category-card">
                                <h3 class="governance-mini-title">${esc(CATEGORY_LABELS[cat] || cat)}</h3>
                                <div class="governance-list-stack">
                                    ${(grouped[cat] || []).map((preset) => `
                                        <button class="f5-preset-btn" data-testid="reports-preset-button-${esc(preset.key)}" onclick="ReportsView.runPreset('${preset.key}')">
                                            <span class="f5-chart-icon">${chartIcon(preset.chart_type)}</span>
                                            <span>${esc(preset.name)}</span>
                                        </button>
                                    `).join('')}
                                    ${(grouped[cat] || []).length === 0 ? '<span class="governance-muted">No reports in this category.</span>' : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div id="presetResult"></div>
            </div>
        `;
    }

    function chartIcon(type) {
        const icons = {
            bar: '▤',
            line: '╱',
            pie: '◔',
            donut: '◎',
            gauge: '◜',
            heatmap: '▦',
            kpi: '#',
            table: '≣',
            treemap: '▥',
        };
        return icons[type] || '▤';
    }

    async function runPreset(key) {
        const prog = _currentProgram();
        if (!prog) return;
        const resultDiv = document.getElementById('presetResult');
        resultDiv.innerHTML = _statePanel('Running report…');
        try {
            const data = await API.get(`/reports/presets/${key}/${prog.id}`);
            const presetMeta = presets.find((preset) => preset.key === key) || {};
            lastRunContext = {
                source: 'preset',
                key,
                title: data.title || presetMeta.name || 'Untitled Report',
                category: presetMeta.category || 'custom',
                chart_type: data.chart_type || presetMeta.chart_type || 'table',
                chart_config: data.chart_config || {},
            };
            renderPresetResult(data);
        } catch (err) {
            lastRunContext = null;
            resultDiv.innerHTML = _statePanel(`Error: ${err.message}`, 'error');
        }
    }

    function renderPresetResult(report) {
        const resultDiv = document.getElementById('presetResult');
        _destroyCharts();

        const title = report.title || 'Report Result';
        const chartType = report.chart_type;
        const summaryHtml = renderSummaryBlock(report.summary);
        const actionsHtml = lastRunContext?.source === 'preset'
            ? `
                <div class="governance-action-row">
                    <button class="pg-btn pg-btn--secondary pg-btn--sm" data-testid="reports-save-current-report-trigger" onclick="ReportsView.openSaveCurrentReportModal()">Save to Library</button>
                </div>
            `
            : '';

        if (chartType === 'table') {
            const columns = report.columns || (report.data && report.data.length ? Object.keys(report.data[0]) : []);
            const rows = report.data || [];
            resultDiv.innerHTML = `
                <div class="card governance-panel">
                    <div class="governance-panel__header governance-panel__header--compact">
                        <div>
                            <div class="governance-panel__eyebrow">Preset result</div>
                            <h3 class="governance-panel__title">${esc(title)}</h3>
                        </div>
                    </div>
                    ${actionsHtml}
                    ${summaryHtml}
                    <div class="governance-table-wrap">
                        <table class="data-table">
                            <thead><tr>${columns.map((column) => `<th>${esc(column)}</th>`).join('')}</tr></thead>
                            <tbody>${rows.slice(0, 100).map((row) => `<tr>${columns.map((column) => `<td>${esc(String(row[column] ?? ''))}</td>`).join('')}</tr>`).join('')}</tbody>
                        </table>
                    </div>
                    <span class="governance-muted governance-result-meta">${rows.length} rows</span>
                </div>
            `;
            return;
        }

        if (chartType === 'kpi') {
            resultDiv.innerHTML = `
                <div class="card governance-panel governance-panel--center">
                    <div class="governance-panel__header governance-panel__header--compact">
                        <div>
                            <div class="governance-panel__eyebrow">Preset result</div>
                            <h3 class="governance-panel__title">${esc(title)}</h3>
                        </div>
                    </div>
                    ${actionsHtml}
                    ${summaryHtml}
                </div>
            `;
            return;
        }

        resultDiv.innerHTML = `
            <div class="card governance-panel">
                <div class="governance-panel__header governance-panel__header--compact">
                    <div>
                        <div class="governance-panel__eyebrow">Preset result</div>
                        <h3 class="governance-panel__title">${esc(title)}</h3>
                    </div>
                </div>
                ${actionsHtml}
                ${summaryHtml}
                <div class="governance-chart-wrap"><canvas id="f5ReportChart"></canvas></div>
            </div>
        `;

        if (typeof Chart === 'undefined') return;

        const ctx = document.getElementById('f5ReportChart');
        if (!ctx) return;

        const labels = report.labels || [];
        const datasets = (report.datasets || []).map((dataset, index) => {
            const colors = ['#0070f3', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
            const base = {
                label: dataset.label || `Dataset ${index + 1}`,
                data: dataset.data || [],
            };
            if (['pie', 'donut'].includes(chartType)) {
                base.backgroundColor = colors;
            } else {
                base.backgroundColor = dataset.color || colors[index % colors.length];
                base.borderColor = dataset.color || colors[index % colors.length];
                if (chartType === 'line') base.fill = false;
            }
            return base;
        });

        const chartJsType = chartType === 'donut' ? 'doughnut' : (chartType === 'gauge' ? 'doughnut' : chartType);
        const options = { responsive: true, maintainAspectRatio: false };
        if (chartType === 'gauge') {
            options.circumference = 180;
            options.rotation = -90;
            options.cutout = '75%';
        }

        const chart = new Chart(ctx, {
            type: chartJsType,
            data: { labels, datasets },
            options,
        });
        chartInstances.push(chart);
    }

    function renderSummaryBlock(summary) {
        if (!summary) return '';
        if (summary.value !== undefined) {
            return `
                <div class="f5-kpi-card">
                    <span class="f5-kpi-value">${esc(String(summary.value))}${esc(summary.unit || '')}</span>
                    <span class="f5-kpi-label">${esc(summary.label || '')}</span>
                </div>
            `;
        }
        return `<div class="governance-summary-text">${Object.entries(summary).map(([key, value]) => `<strong>${esc(key)}:</strong> ${esc(String(value))}`).join(' · ')}</div>`;
    }

    async function renderSaved() {
        const container = document.getElementById('reportContent');
        const prog = _currentProgram();
        try {
            const resp = await API.get(`/reports/definitions?program_id=${prog.id}`);
            const definitions = resp.definitions || [];
            if (definitions.length === 0) {
                container.innerHTML = PGEmptyState.html({
                    icon: 'reports',
                    title: 'No Saved Reports',
                    description: 'Open the Report Library, run a preset, and save it here for repeat use.',
                    action: { label: 'Open Library', onclick: "ReportsView.switchTab('catalog')" },
                });
                return;
            }
            container.innerHTML = `
                <div class="workspace-section-stack">
                    <div class="card governance-panel">
                        <div class="governance-panel__header">
                            <div>
                                <div class="governance-panel__eyebrow">Saved library</div>
                                <h3 class="governance-panel__title">Reusable Reports</h3>
                                <p class="governance-panel__description">Run or prune the report definitions your team relies on repeatedly.</p>
                            </div>
                        </div>
                        <div class="governance-report-grid">
                            ${definitions.map((definition) => `
                                <div class="card governance-report-card">
                                    <div class="governance-report-card__header">
                                        <div>
                                            <h4 class="governance-report-card__title">${esc(definition.name)}</h4>
                                            <div class="governance-report-card__meta">${esc(CATEGORY_LABELS[definition.category] || definition.category)} · ${esc(definition.chart_type)}</div>
                                        </div>
                                        <div class="governance-report-card__actions">
                                            <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.runDefinition(${definition.id})">Run</button>
                                            <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.openDeleteDefinitionModal(${definition.id})">Delete</button>
                                        </div>
                                    </div>
                                    ${definition.description ? `<p class="governance-report-card__summary">${esc(definition.description)}</p>` : '<p class="governance-report-card__summary governance-report-card__summary--muted">No description added yet.</p>'}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div id="presetResult"></div>
                </div>
            `;
        } catch (err) {
            container.innerHTML = _statePanel(`Error: ${err.message}`, 'error');
        }
    }

    async function runDefinition(id) {
        const resultDiv = document.getElementById('presetResult');
        if (!resultDiv) return;
        resultDiv.innerHTML = _statePanel('Running…');
        try {
            const data = await API.get(`/reports/definitions/${id}/run`);
            lastRunContext = null;
            renderPresetResult(data);
        } catch (err) {
            lastRunContext = null;
            resultDiv.innerHTML = _statePanel(`Error: ${err.message}`, 'error');
        }
    }

    function openDeleteDefinitionModal(id) {
        _openReportsModal({
            title: 'Delete Saved Report',
            testId: 'reports-delete-definition-modal',
            body: `
                <div class="governance-modal__stack">
                    <p class="governance-modal__intro">This removes the saved definition from the shared library. Historical preset results are not affected.</p>
                </div>
            `,
            footer: `
                <button class="btn btn-danger" data-testid="reports-delete-definition-confirm" onclick="ReportsView.deleteDefinitionConfirmed(${id})">Delete</button>
                <button class="btn" onclick="App.closeModal()">Cancel</button>
            `,
        });
    }

    async function deleteDefinitionConfirmed(id) {
        try {
            await API.delete(`/reports/definitions/${id}`);
            App.closeModal();
            App.toast('Saved report deleted', 'success');
            renderSaved();
        } catch (err) {
            App.toast(`Error: ${err.message || 'Unknown'}`, 'error');
        }
    }

    function openSaveCurrentReportModal() {
        const prog = _currentProgram();
        if (!prog || lastRunContext?.source !== 'preset') return;
        const defaultName = lastRunContext.title || 'Saved Report';
        _openReportsModal({
            title: 'Save Report',
            testId: 'reports-save-definition-modal',
            body: `
                <div class="governance-modal__stack">
                    <div class="form-group">
                        <label for="reportSaveName">Name</label>
                        <input id="reportSaveName" class="form-control" value="${esc(defaultName)}" maxlength="200" />
                    </div>
                    <div class="form-group">
                        <label for="reportSaveDescription">Description</label>
                        <textarea id="reportSaveDescription" class="form-control" rows="3" placeholder="What should this saved report be used for?"></textarea>
                    </div>
                </div>
            `,
            footer: `
                <button class="btn btn-primary" data-testid="reports-save-definition-confirm" onclick="ReportsView.saveCurrentReport()">Save</button>
                <button class="btn" onclick="App.closeModal()">Cancel</button>
            `,
        });
    }

    async function saveCurrentReport() {
        const prog = _currentProgram();
        if (!prog || lastRunContext?.source !== 'preset') return;

        const name = document.getElementById('reportSaveName')?.value?.trim() || '';
        const description = document.getElementById('reportSaveDescription')?.value?.trim() || '';
        if (!name) {
            App.toast('Report name is required', 'error');
            return;
        }

        try {
            await API.post('/reports/definitions', {
                program_id: prog.id,
                name,
                description,
                category: lastRunContext.category || 'custom',
                query_type: 'preset',
                query_config: { preset_key: lastRunContext.key },
                chart_type: lastRunContext.chart_type || 'table',
                chart_config: lastRunContext.chart_config || {},
            });
            App.closeModal();
            App.toast('Report saved to library', 'success');
            activeTab = 'saved';
            await render();
        } catch (err) {
            App.toast(`Error: ${err.message || 'Unknown'}`, 'error');
        }
    }

    async function renderSteerco() {
        const container = document.getElementById('reportContent');
        const prog = _currentProgram();
        const canEditGovernance = _can('programs.edit');
        const canDeleteGovernance = _can('programs.delete');

        const [reports, projects] = await Promise.all([
            API.get(`/programs/${prog.id}/reports`),
            _loadProgramProjects(prog.id),
        ]);
        const steercoReports = Array.isArray(reports) ? reports : [];
        programProjects = Array.isArray(projects) ? projects : [];

        const counts = {
            draft: steercoReports.filter((report) => report.status === 'draft').length,
            inReview: steercoReports.filter((report) => report.status === 'in_review').length,
            approved: steercoReports.filter((report) => report.status === 'approved').length,
            presented: steercoReports.filter((report) => report.status === 'presented').length,
        };
        const latest = steercoReports[0] || null;

        container.innerHTML = `
            <div class="workspace-section-stack">
                <div class="workspace-spotlight-grid">
                    ${GovernanceUI.spotlightCard({ value: steercoReports.length, label: 'SteerCo Reports', sub: latest ? `Latest: ${formatDate(latest.report_date)}` : 'No reports yet' })}
                    ${GovernanceUI.spotlightCard({ value: counts.draft + counts.inReview, label: 'Open Workflow', sub: `${counts.draft} draft · ${counts.inReview} in review` })}
                    ${GovernanceUI.spotlightCard({ value: counts.approved, label: 'Approved', sub: counts.presented ? `${counts.presented} presented` : 'Awaiting presentation' })}
                    ${GovernanceUI.spotlightCard({ value: programProjects.length, label: 'Program Projects', sub: 'Available for report status capture' })}
                </div>

                <div class="card governance-panel">
                    <div class="governance-panel__header">
                        <div>
                            <div class="governance-panel__eyebrow">Steering committee</div>
                            <h3 class="governance-panel__title">SteerCo Report Lifecycle</h3>
                            <p class="governance-panel__description">Create the governance pack, capture per-project commentary, approve it, then mark it as presented.</p>
                        </div>
                        ${canEditGovernance ? '<button class="pg-btn pg-btn--primary pg-btn--sm" data-testid="reports-open-steerco-modal" onclick="ReportsView.openProgramReportModal()">New SteerCo Report</button>' : '<span class="governance-muted">Read-only governance access</span>'}
                    </div>
                    ${steercoReports.length ? `
                        <div class="governance-report-grid" data-testid="program-report-grid">
                            ${steercoReports.map((report) => `
                                <div class="card governance-report-card" data-testid="program-report-card">
                                    <div class="governance-report-card__header">
                                        <div>
                                            <div class="governance-report-card__title-row">
                                                <h4 class="governance-report-card__title">${esc(report.title)}</h4>
                                                ${statusBadge(report.status)}
                                            </div>
                                            <div class="governance-report-card__meta">${esc(reportMeta(report))}</div>
                                        </div>
                                        <div class="governance-report-card__actions">
                                            <button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.openProgramReportModal(${report.id})">${['approved', 'presented', 'archived'].includes(report.status) || !canEditGovernance ? 'View' : 'Edit'}</button>
                                            ${canEditGovernance && ['draft', 'in_review'].includes(report.status) ? `<button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.approveProgramReport(${report.id})">Approve</button>` : ''}
                                            ${canEditGovernance && report.status === 'approved' ? `<button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.presentProgramReport(${report.id})">Present</button>` : ''}
                                            ${canDeleteGovernance && report.status === 'draft' ? `<button class="pg-btn pg-btn--ghost pg-btn--sm" onclick="ReportsView.openDeleteProgramReportModal(${report.id})">Delete</button>` : ''}
                                        </div>
                                    </div>
                                    <div class="governance-report-card__meta-row">
                                        ${ragBadge(report.overall_rag)}
                                        <span class="governance-muted">${report.approved_at ? `Approved ${formatDate(report.approved_at)}` : 'Awaiting approval'}</span>
                                    </div>
                                    <p class="governance-report-card__summary">${esc(excerpt(report.executive_summary || report.key_accomplishments || report.upcoming_activities || 'No executive summary captured yet.'))}</p>
                                </div>
                            `).join('')}
                        </div>
                    ` : `
                        <div class="governance-empty-state">
                            <div class="governance-empty-state__title">No SteerCo reports yet</div>
                            <p>Start a first report to capture leadership summary, escalations, and per-project status for this program.</p>
                        </div>
                    `}
                </div>
            </div>
        `;
    }

    async function openProgramReportModal(reportId = null) {
        const prog = _currentProgram();
        if (!prog) return;
        if (!reportId && !_guardPlatformPermission('programs.edit', 'You do not have permission to create SteerCo reports.')) return;

        const [projects, report] = await Promise.all([
            _loadProgramProjects(prog.id),
            reportId ? API.get(`/program-reports/${reportId}?include_details=true`) : Promise.resolve(null),
        ]);
        programProjects = projects;
        activeProgramReport = report;

        const locked = ['approved', 'presented', 'archived'].includes(report?.status || '') || !_can('programs.edit');
        const statusOptions = locked
            ? [[report?.status || 'draft', REPORT_STATUS_LABELS[report?.status || 'draft'] || 'Draft']]
            : [['draft', 'Draft'], ['in_review', 'In Review']];
        const projectStatuses = new Map((report?.project_statuses || []).map((row) => [Number(row.project_id), row]));
        const footerButtons = report?.status === 'approved'
            ? `
                <button class="btn btn-primary" onclick="ReportsView.presentProgramReport(${report.id}, true)">Mark Presented</button>
                <button class="btn" onclick="App.closeModal()">Close</button>
            `
            : locked
                ? `<button class="btn" onclick="App.closeModal()">Close</button>`
                : `
                    <button class="btn btn-primary" data-testid="reports-save-steerco-report" onclick="ReportsView.saveProgramReport()">Save Report</button>
                    <button class="btn btn-secondary" data-testid="reports-save-approve-steerco-report" onclick="ReportsView.saveProgramReport('approve')">${reportId ? 'Save & Approve' : 'Create & Approve'}</button>
                    <button class="btn" onclick="App.closeModal()">Cancel</button>
                `;

        _openReportsModal({
            title: reportId ? (report?.title || 'Edit Report') : 'New SteerCo Report',
            testId: 'reports-steerco-modal',
            body: `
                <div class="governance-modal__stack governance-modal__stack--spacious">
                    <input type="hidden" id="programReportId" value="${report?.id || ''}" />
                    <div class="governance-form-grid">
                        <div class="form-group">
                            <label for="programReportTitle">Title</label>
                            <input id="programReportTitle" class="form-control" maxlength="300" value="${esc(report?.title || '')}" ${locked ? 'disabled' : ''} />
                        </div>
                        <div class="form-group">
                            <label for="programReportStatus">Status</label>
                            <select id="programReportStatus" class="form-control" ${locked ? 'disabled' : ''}>
                                ${selectOptions(statusOptions, report?.status || 'draft')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="programReportDate">Report Date</label>
                            <input id="programReportDate" type="date" class="form-control" value="${esc(report?.report_date || '')}" ${locked ? 'disabled' : ''} />
                        </div>
                        <div class="form-group">
                            <label for="programReportRag">Overall RAG</label>
                            <select id="programReportRag" class="form-control" ${locked ? 'disabled' : ''}>
                                ${selectOptions([
                                    ['', 'Not set'],
                                    ['Green', 'Green'],
                                    ['Amber', 'Amber'],
                                    ['Red', 'Red'],
                                ], report?.overall_rag || '')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="programReportPeriodStart">Reporting Period Start</label>
                            <input id="programReportPeriodStart" type="date" class="form-control" value="${esc(report?.reporting_period_start || '')}" ${locked ? 'disabled' : ''} />
                        </div>
                        <div class="form-group">
                            <label for="programReportPeriodEnd">Reporting Period End</label>
                            <input id="programReportPeriodEnd" type="date" class="form-control" value="${esc(report?.reporting_period_end || '')}" ${locked ? 'disabled' : ''} />
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="programReportExecutiveSummary">Executive Summary</label>
                        <textarea id="programReportExecutiveSummary" class="form-control" rows="4" ${locked ? 'disabled' : ''}>${esc(report?.executive_summary || '')}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="programReportAccomplishments">Key Accomplishments</label>
                        <textarea id="programReportAccomplishments" class="form-control" rows="3" ${locked ? 'disabled' : ''}>${esc(report?.key_accomplishments || '')}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="programReportUpcoming">Upcoming Activities</label>
                        <textarea id="programReportUpcoming" class="form-control" rows="3" ${locked ? 'disabled' : ''}>${esc(report?.upcoming_activities || '')}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="programReportEscalations">Escalations</label>
                        <textarea id="programReportEscalations" class="form-control" rows="3" ${locked ? 'disabled' : ''}>${esc(report?.escalations || '')}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="programReportRiskSummary">Risks & Issues Summary</label>
                        <textarea id="programReportRiskSummary" class="form-control" rows="3" ${locked ? 'disabled' : ''}>${esc(report?.risks_and_issues_summary || '')}</textarea>
                    </div>

                    <div class="governance-project-section">
                        <div class="governance-panel__header governance-panel__header--compact">
                            <div>
                                <div class="governance-panel__eyebrow">Project coverage</div>
                                <h3 class="governance-panel__title">Per-Project Status</h3>
                            </div>
                        </div>
                        ${reportId ? `
                            <div class="governance-project-status-grid">
                                ${projects.map((project) => {
                                    const projectStatus = projectStatuses.get(Number(project.id));
                                    return `
                                        <div class="governance-project-status-card">
                                            <div class="governance-project-status-card__header">
                                                <div>
                                                    <div class="governance-project-status-card__title">${esc(project.name || project.code || `Project ${project.id}`)}</div>
                                                    <div class="governance-project-status-card__meta">${esc(project.code || 'Program project')}</div>
                                                </div>
                                                ${projectStatus ? ragBadge(projectStatus.project_rag) : '<span class="governance-pill governance-pill--muted">Not captured</span>'}
                                            </div>
                                            <p class="governance-project-status-card__summary">${esc(excerpt(projectStatus?.summary || 'No report-specific project summary captured yet.', 120))}</p>
                                            ${locked ? '' : `<button class="pg-btn pg-btn--ghost pg-btn--sm" data-testid="reports-open-project-status-${project.id}" onclick="ReportsView.openProjectStatusModal(${report.id}, ${project.id})">${projectStatus ? 'Edit Status' : 'Add Status'}</button>`}
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        ` : `
                            <div class="governance-empty-state governance-empty-state--inline">
                                <div class="governance-empty-state__title">Save the report first</div>
                                <p>Create the report once, then add per-project steering status entries from this section.</p>
                            </div>
                        `}
                    </div>
                </div>
            `,
            footer: footerButtons,
        });
    }

    async function saveProgramReport(afterSave = '') {
        const prog = _currentProgram();
        if (!prog) return;
        if (!_guardPlatformPermission('programs.edit', 'You do not have permission to modify SteerCo reports.')) return;

        const reportId = document.getElementById('programReportId')?.value || '';
        const payload = {
            title: document.getElementById('programReportTitle')?.value?.trim() || '',
            status: document.getElementById('programReportStatus')?.value || 'draft',
            report_date: document.getElementById('programReportDate')?.value || null,
            overall_rag: document.getElementById('programReportRag')?.value || null,
            reporting_period_start: document.getElementById('programReportPeriodStart')?.value || null,
            reporting_period_end: document.getElementById('programReportPeriodEnd')?.value || null,
            executive_summary: document.getElementById('programReportExecutiveSummary')?.value?.trim() || '',
            key_accomplishments: document.getElementById('programReportAccomplishments')?.value?.trim() || '',
            upcoming_activities: document.getElementById('programReportUpcoming')?.value?.trim() || '',
            escalations: document.getElementById('programReportEscalations')?.value?.trim() || '',
            risks_and_issues_summary: document.getElementById('programReportRiskSummary')?.value?.trim() || '',
        };

        if (!payload.title) {
            App.toast('Report title is required', 'error');
            return;
        }

        try {
            const report = reportId
                ? await API.put(`/program-reports/${reportId}`, payload)
                : await API.post(`/programs/${prog.id}/reports`, payload);
            if (afterSave === 'approve') {
                const metricsSnapshot = await _metricsSnapshotForProgram(prog.id);
                await API.post(`/program-reports/${report.id}/approve`, metricsSnapshot ? { metrics_snapshot: metricsSnapshot } : {});
                App.toast('SteerCo report approved', 'success');
            } else {
                App.toast(reportId ? 'SteerCo report updated' : 'SteerCo report created', 'success');
            }
            App.closeModal();
            activeProgramReport = null;
            renderSteerco();
        } catch (err) {
            App.toast(`Error: ${err.message || 'Unknown'}`, 'error');
        }
    }

    async function approveProgramReport(id) {
        const prog = _currentProgram();
        if (!prog) return;
        if (!_guardPlatformPermission('programs.edit', 'You do not have permission to approve SteerCo reports.')) return;
        try {
            const metricsSnapshot = await _metricsSnapshotForProgram(prog.id);
            await API.post(`/program-reports/${id}/approve`, metricsSnapshot ? { metrics_snapshot: metricsSnapshot } : {});
            App.toast('SteerCo report approved', 'success');
            renderSteerco();
        } catch (err) {
            App.toast(`Error: ${err.message || 'Unknown'}`, 'error');
        }
    }

    async function presentProgramReport(id, closeModal = false) {
        if (!_guardPlatformPermission('programs.edit', 'You do not have permission to present SteerCo reports.')) return;
        try {
            await API.post(`/program-reports/${id}/present`, {});
            if (closeModal) App.closeModal();
            App.toast('SteerCo report marked as presented', 'success');
            renderSteerco();
        } catch (err) {
            App.toast(`Error: ${err.message || 'Unknown'}`, 'error');
        }
    }

    function openDeleteProgramReportModal(id) {
        if (!_guardPlatformPermission('programs.delete', 'You do not have permission to delete SteerCo reports.')) return;
        _openReportsModal({
            title: 'Delete SteerCo Report',
            testId: 'reports-delete-steerco-modal',
            body: `
                <div class="governance-modal__stack">
                    <p class="governance-modal__intro">Only draft reports can be deleted. This action removes the report and its project status coverage.</p>
                </div>
            `,
            footer: `
                <button class="btn btn-danger" data-testid="reports-delete-steerco-confirm" onclick="ReportsView.deleteProgramReportConfirmed(${id})">Delete</button>
                <button class="btn" onclick="App.closeModal()">Cancel</button>
            `,
        });
    }

    async function deleteProgramReportConfirmed(id) {
        if (!_guardPlatformPermission('programs.delete', 'You do not have permission to delete SteerCo reports.')) return;
        try {
            await API.delete(`/program-reports/${id}`);
            App.closeModal();
            App.toast('SteerCo report deleted', 'success');
            renderSteerco();
        } catch (err) {
            App.toast(`Error: ${err.message || 'Unknown'}`, 'error');
        }
    }

    function openProjectStatusModal(reportId, projectId) {
        const report = activeProgramReport;
        const project = programProjects.find((item) => Number(item.id) === Number(projectId));
        if (!report || !project) return;

        const current = (report.project_statuses || []).find((item) => Number(item.project_id) === Number(projectId)) || {};
        const locked = ['approved', 'presented', 'archived'].includes(report.status || '') || !_can('programs.edit');

        _openReportsModal({
            title: project.name || project.code || 'Project Status',
            closeAction: `ReportsView.openProgramReportModal(${reportId})`,
            testId: 'reports-project-status-modal',
            body: `
                <div class="governance-modal__stack governance-modal__stack--spacious">
                    <div class="governance-form-grid">
                        <div class="form-group">
                            <label for="reportProjectRag">Overall RAG</label>
                            <select id="reportProjectRag" class="form-control" ${locked ? 'disabled' : ''}>
                                ${selectOptions([
                                    ['', 'Not set'],
                                    ['Green', 'Green'],
                                    ['Amber', 'Amber'],
                                    ['Red', 'Red'],
                                ], current.project_rag || '')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="reportProjectScopeRag">Scope RAG</label>
                            <select id="reportProjectScopeRag" class="form-control" ${locked ? 'disabled' : ''}>
                                ${selectOptions([
                                    ['', 'Not set'],
                                    ['Green', 'Green'],
                                    ['Amber', 'Amber'],
                                    ['Red', 'Red'],
                                ], current.rag_scope || '')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="reportProjectTimelineRag">Timeline RAG</label>
                            <select id="reportProjectTimelineRag" class="form-control" ${locked ? 'disabled' : ''}>
                                ${selectOptions([
                                    ['', 'Not set'],
                                    ['Green', 'Green'],
                                    ['Amber', 'Amber'],
                                    ['Red', 'Red'],
                                ], current.rag_timeline || '')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="reportProjectBudgetRag">Budget RAG</label>
                            <select id="reportProjectBudgetRag" class="form-control" ${locked ? 'disabled' : ''}>
                                ${selectOptions([
                                    ['', 'Not set'],
                                    ['Green', 'Green'],
                                    ['Amber', 'Amber'],
                                    ['Red', 'Red'],
                                ], current.rag_budget || '')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="reportProjectQualityRag">Quality RAG</label>
                            <select id="reportProjectQualityRag" class="form-control" ${locked ? 'disabled' : ''}>
                                ${selectOptions([
                                    ['', 'Not set'],
                                    ['Green', 'Green'],
                                    ['Amber', 'Amber'],
                                    ['Red', 'Red'],
                                ], current.rag_quality || '')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="reportProjectResourcesRag">Resources RAG</label>
                            <select id="reportProjectResourcesRag" class="form-control" ${locked ? 'disabled' : ''}>
                                ${selectOptions([
                                    ['', 'Not set'],
                                    ['Green', 'Green'],
                                    ['Amber', 'Amber'],
                                    ['Red', 'Red'],
                                ], current.rag_resources || '')}
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="reportProjectSummary">Summary</label>
                        <textarea id="reportProjectSummary" class="form-control" rows="3" ${locked ? 'disabled' : ''}>${esc(current.summary || '')}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="reportProjectNextSteps">Next Steps</label>
                        <textarea id="reportProjectNextSteps" class="form-control" rows="3" ${locked ? 'disabled' : ''}>${esc(current.next_steps || '')}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="reportProjectBlockers">Blockers</label>
                        <textarea id="reportProjectBlockers" class="form-control" rows="3" ${locked ? 'disabled' : ''}>${esc(current.blockers || '')}</textarea>
                    </div>
                </div>
            `,
            footer: `
                ${locked ? '' : `<button class="btn btn-primary" data-testid="reports-save-project-status" onclick="ReportsView.saveProgramReportProjectStatus(${reportId}, ${projectId})">Save Status</button>`}
                <button class="btn" onclick="ReportsView.openProgramReportModal(${reportId})">${locked ? 'Back' : 'Cancel'}</button>
            `,
        });
    }

    async function saveProgramReportProjectStatus(reportId, projectId) {
        if (!_guardPlatformPermission('programs.edit', 'You do not have permission to update project steering statuses.')) return;
        const payload = {
            project_id: projectId,
            project_rag: document.getElementById('reportProjectRag')?.value || null,
            rag_scope: document.getElementById('reportProjectScopeRag')?.value || null,
            rag_timeline: document.getElementById('reportProjectTimelineRag')?.value || null,
            rag_budget: document.getElementById('reportProjectBudgetRag')?.value || null,
            rag_quality: document.getElementById('reportProjectQualityRag')?.value || null,
            rag_resources: document.getElementById('reportProjectResourcesRag')?.value || null,
            summary: document.getElementById('reportProjectSummary')?.value?.trim() || '',
            next_steps: document.getElementById('reportProjectNextSteps')?.value?.trim() || '',
            blockers: document.getElementById('reportProjectBlockers')?.value?.trim() || '',
        };

        try {
            await API.post(`/program-reports/${reportId}/project-statuses`, payload);
            App.toast('Project report status saved', 'success');
            await openProgramReportModal(reportId);
        } catch (err) {
            App.toast(`Error: ${err.message || 'Unknown'}`, 'error');
        }
    }

    function selectOptions(options, selected) {
        return options.map(([value, label]) => `
            <option value="${esc(value)}" ${String(value) === String(selected || '') ? 'selected' : ''}>${esc(label)}</option>
        `).join('');
    }

    function renderAreaCard(title, area, metrics) {
        if (!area) return '';
        return `
            <div class="card governance-panel governance-panel--compact">
                <div class="governance-report-card__header">
                    <h3 class="governance-panel__title">${esc(title)}</h3>
                    ${ragBadge(area.rag)}
                </div>
                <div class="governance-metric-stack">
                    ${metrics.map((metric) => `
                        <div class="governance-metric-row">
                            <span class="governance-metric-row__label">${esc(metric.label)}</span>
                            <span class="${metric.alert ? 'governance-metric-row__value governance-metric-row__value--alert' : 'governance-metric-row__value'}">
                                ${metric.pct != null ? pctBar(metric.pct, _pctColor(metric.pct)) : esc(String(metric.value ?? '—'))}
                            </span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    function _pctColor(pct) {
        if (pct >= 70) return '#27AE60';
        if (pct >= 40) return '#F39C12';
        return '#E74C3C';
    }

    function exportXlsx() {
        const prog = _currentProgram();
        if (!prog) return;
        window.open(`/api/v1/reports/export/xlsx/${prog.id}`, '_blank');
    }

    function exportPdf() {
        const prog = _currentProgram();
        if (!prog) return;
        window.open(`/api/v1/reports/export/pdf/${prog.id}`, '_blank');
    }

    function showAISteeringPackModal() {
        ReportsAI.openSteeringPackModal({ program: _currentProgram() });
    }

    async function runAISteeringPack() {
        return ReportsAI.runSteeringPack();
    }

    return {
        render,
        switchTab,
        runPreset,
        runDefinition,
        openDeleteDefinitionModal,
        deleteDefinitionConfirmed,
        exportXlsx,
        exportPdf,
        showAISteeringPackModal,
        runAISteeringPack,
        openSaveCurrentReportModal,
        saveCurrentReport,
        openProgramReportModal,
        saveProgramReport,
        approveProgramReport,
        presentProgramReport,
        openDeleteProgramReportModal,
        deleteProgramReportConfirmed,
        openProjectStatusModal,
        saveProgramReportProjectStatus,
    };
})();
