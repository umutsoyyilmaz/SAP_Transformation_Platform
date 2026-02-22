/**
 * F6 — Environment Matrix View
 * TC × Environment grid showing execution results per environment.
 */
const EnvMatrixView = (() => {
    let environments = [];
    let matrix = [];

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    // ── Render ───────────────────────────────────────────────────────────
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        if (!prog) {
            main.innerHTML = PGEmptyState.html({ icon: 'test', title: 'No Program Selected', description: 'Select a program to view the environment matrix.' });
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Environment Matrix' }])}
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <h2 class="pg-view-title">Environment Matrix</h2>
                    <div style="display:flex;gap:8px;align-items:center">
                        <select id="f6EnvModuleFilter" onchange="EnvMatrixView.loadMatrix()"
                                class="form-select f6-filter-select" style="height:32px;font-size:13px">
                            <option value="">All Modules</option>
                        </select>
                        <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="EnvMatrixView.addEnvironment()">+ Add Environment</button>
                    </div>
                </div>
            </div>
            <div class="f6-env-tabs">
                <button class="f6-env-tab active" data-tab="matrix" onclick="EnvMatrixView.switchTab('matrix')">Matrix</button>
                <button class="f6-env-tab" data-tab="environments" onclick="EnvMatrixView.switchTab('environments')">Environments</button>
            </div>
            <div id="f6EnvContent" class="f6-env-content">Loading...</div>`;

        await loadEnvironments();
        await loadMatrix();
    }

    // ── Tab Switching ────────────────────────────────────────────────────
    function switchTab(tab) {
        document.querySelectorAll('.f6-env-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
        if (tab === 'matrix') loadMatrix();
        else renderEnvironmentsList();
    }

    // ── Load Data ────────────────────────────────────────────────────────
    async function loadEnvironments() {
        const prog = App.getActiveProgram();
        try {
            const resp = await fetch(`/api/v1/programs/${prog.id}/environments`);
            const data = await resp.json();
            environments = data.items || [];
        } catch (e) {
            environments = [];
        }
    }

    async function loadMatrix() {
        const prog = App.getActiveProgram();
        const module = document.getElementById('f6EnvModuleFilter')?.value || '';

        const content = document.getElementById('f6EnvContent');
        try {
            let url = `/api/v1/programs/${prog.id}/environment-matrix`;
            const params = new URLSearchParams();
            if (module) params.set('module', module);
            if (params.toString()) url += '?' + params.toString();

            const resp = await fetch(url);
            const data = await resp.json();
            environments = data.environments || [];
            matrix = data.matrix || [];
            renderMatrix(content);
        } catch (e) {
            content.innerHTML = `<div class="f6-error">Failed to load matrix: ${e.message}</div>`;
        }
    }

    // ── Render Matrix ────────────────────────────────────────────────────
    function renderMatrix(container) {
        if (!environments.length) {
            container.innerHTML = PGEmptyState.html({ icon: 'test', title: 'No Environments Defined', description: 'Add environments to build the test matrix.', action: { label: '+ Add Environment', onclick: 'EnvMatrixView.addEnvironment()' } });
            return;
        }

        if (!matrix.length) {
            container.innerHTML = PGEmptyState.html({ icon: 'reports', title: 'No Execution Data', description: 'Run test executions with environment results to populate the matrix.' });
            return;
        }

        let headerCols = '<th class="f6-mx-tc">Test Case</th><th>Module</th>';
        for (const env of environments) {
            headerCols += `<th class="f6-mx-env" title="${esc(env.env_type)}">${esc(env.name)}</th>`;
        }

        let rows = '';
        for (const row of matrix) {
            rows += `<tr>
                <td class="f6-mx-tc">${esc(row.test_case_title)}</td>
                <td>${esc(row.module)}</td>`;
            for (const env of environments) {
                const status = (row.results && row.results[env.id]) || 'not_run';
                const cls = `f6-mx-cell f6-mx-${status.replace('_', '-')}`;
                const icon = _statusIcon(status);
                rows += `<td class="${cls}" title="${status}">${icon}</td>`;
            }
            rows += '</tr>';
        }

        container.innerHTML = `
            <div class="f6-matrix-summary">
                <span class="f6-mx-legend"><span class="f6-mx-dot f6-mx-pass"></span> Pass</span>
                <span class="f6-mx-legend"><span class="f6-mx-dot f6-mx-fail"></span> Fail</span>
                <span class="f6-mx-legend"><span class="f6-mx-dot f6-mx-blocked"></span> Blocked</span>
                <span class="f6-mx-legend"><span class="f6-mx-dot f6-mx-not-run"></span> Not Run</span>
            </div>
            <div class="f6-matrix-scroll">
                <table class="f6-matrix-table">
                    <thead><tr>${headerCols}</tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>`;
    }

    function _statusIcon(status) {
        switch (status) {
            case 'pass': return '✅';
            case 'fail': return '❌';
            case 'blocked': return '⚠️';
            default: return '⬜';
        }
    }

    // ── Environments List ────────────────────────────────────────────────
    function renderEnvironmentsList() {
        const container = document.getElementById('f6EnvContent');
        if (!environments.length) {
            container.innerHTML = PGEmptyState.html({ icon: 'test', title: 'No Environments', action: { label: '+ Add Environment', onclick: 'EnvMatrixView.addEnvironment()' } });
            return;
        }

        let rows = '';
        for (const env of environments) {
            const props = env.properties ? JSON.stringify(env.properties) : '{}';
            const activeIcon = env.is_active ? '🟢' : '🔴';
            rows += `<tr>
                <td>${env.id}</td>
                <td>${esc(env.name)}</td>
                <td><span class="f6-env-type">${esc(env.env_type)}</span></td>
                <td><code>${esc(props)}</code></td>
                <td>${activeIcon}</td>
                <td>
                    <button class="btn btn-sm" onclick="EnvMatrixView.editEnvironment(${env.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="EnvMatrixView.deleteEnvironment(${env.id})">Delete</button>
                </td>
            </tr>`;
        }

        container.innerHTML = `
            <table class="f6-env-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Properties</th>
                        <th>Active</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>`;
    }

    // ── Environment CRUD ─────────────────────────────────────────────────
    async function addEnvironment() {
        const prog = App.getActiveProgram();
        if (!prog) return;

        const name = prompt('Environment name (e.g. "SAP QAS", "Chrome 120"):');
        if (!name) return;

        const envType = prompt('Environment type (sap_system, browser, os, device, custom):', 'sap_system');

        const resp = await fetch(`/api/v1/programs/${prog.id}/environments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, env_type: envType || 'sap_system' }),
        });
        if (resp.ok) {
            App.showToast?.('Environment created', 'success');
            await loadEnvironments();
            renderEnvironmentsList();
        } else {
            const err = await resp.json();
            App.showToast?.(err.error || 'Failed to create environment', 'error');
        }
    }

    async function editEnvironment(id) {
        const env = environments.find(e => e.id === id);
        if (!env) return;

        const name = prompt('Environment name:', env.name);
        if (!name) return;

        const resp = await fetch(`/api/v1/environments/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        });
        if (resp.ok) {
            App.showToast?.('Environment updated', 'success');
            await loadEnvironments();
            renderEnvironmentsList();
        }
    }

    async function deleteEnvironment(id) {
        if (!confirm('Delete this environment?')) return;

        const resp = await fetch(`/api/v1/environments/${id}`, { method: 'DELETE' });
        if (resp.ok) {
            App.showToast?.('Environment deleted', 'success');
            await loadEnvironments();
            renderEnvironmentsList();
        }
    }

    // ── Public API ───────────────────────────────────────────────────────
    return {
        render,
        switchTab,
        loadMatrix,
        addEnvironment,
        editEnvironment,
        deleteEnvironment,
    };
})();
