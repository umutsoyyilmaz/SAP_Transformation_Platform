/**
 * SAP Transformation Management Platform
 * Program View — CRUD UI for managing SAP transformation programs.
 */

const ProgramView = (() => {
    let programs = [];

    // ── Render ───────────────────────────────────────────────────────────
    async function render() {
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="page-header">
                <h1>Programs</h1>
                <button class="btn btn-primary" onclick="ProgramView.showCreateModal()">
                    + New Program
                </button>
            </div>
            <div class="card">
                <div id="programTableContainer">
                    <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
                </div>
            </div>
        `;

        await loadPrograms();
    }

    // ── Load & Render Table ──────────────────────────────────────────────
    async function loadPrograms() {
        try {
            programs = await API.get('/programs');
            renderTable();
        } catch (err) {
            document.getElementById('programTableContainer').innerHTML =
                `<div class="empty-state"><p>⚠️ ${err.message}</p></div>`;
        }
    }

    function renderTable() {
        const container = document.getElementById('programTableContainer');

        if (programs.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">📋</div>
                    <div class="empty-state__title">No programs found</div>
                    <p>Create your first SAP transformation program.</p>
                    <br>
                    <button class="btn btn-primary" onclick="ProgramView.showCreateModal()">
                        + New Program
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Methodology</th>
                        <th>Status</th>
                        <th>Priority</th>
                        <th>SAP Product</th>
                        <th>Start Date</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${programs.map(p => `
                        <tr>
                            <td>${p.id}</td>
                            <td><strong>${escHtml(p.name)}</strong></td>
                            <td>${p.project_type}</td>
                            <td>${p.methodology}</td>
                            <td><span class="badge badge-${p.status}">${p.status}</span></td>
                            <td>${p.priority}</td>
                            <td>${p.sap_product}</td>
                            <td>${p.start_date || '—'}</td>
                            <td>
                                <button class="btn btn-secondary btn-sm"
                                        onclick="ProgramView.showEditModal(${p.id})">Edit</button>
                                <button class="btn btn-danger btn-sm"
                                        onclick="ProgramView.deleteProgram(${p.id})">Delete</button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    // ── Create Modal ─────────────────────────────────────────────────────
    function showCreateModal() {
        App.openModal(formHtml('Create Program', {}));
    }

    // ── Edit Modal ───────────────────────────────────────────────────────
    function showEditModal(id) {
        const p = programs.find(x => x.id === id);
        if (!p) return;
        App.openModal(formHtml('Edit Program', p));
    }

    // ── Form HTML generator ──────────────────────────────────────────────
    function formHtml(title, p) {
        const isEdit = !!p.id;
        return `
            <div class="modal-header">
                <h2>${title}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <form id="programForm" onsubmit="ProgramView.handleSubmit(event, ${p.id || 'null'})">
                <div class="form-group">
                    <label>Program Name *</label>
                    <input name="name" required value="${escAttr(p.name || '')}"
                           placeholder="e.g. ACME S/4HANA Greenfield">
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" rows="3"
                              placeholder="Brief description of the program...">${escHtml(p.description || '')}</textarea>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Project Type</label>
                        <select name="project_type">
                            ${selectOpts(['greenfield','brownfield','bluefield','selective_data_transition'], p.project_type)}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Methodology</label>
                        <select name="methodology">
                            ${selectOpts(['sap_activate','agile','waterfall','hybrid'], p.methodology)}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Status</label>
                        <select name="status">
                            ${selectOpts(['planning','active','on_hold','completed','cancelled'], p.status)}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Priority</label>
                        <select name="priority">
                            ${selectOpts(['low','medium','high','critical'], p.priority)}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>SAP Product</label>
                        <select name="sap_product">
                            ${selectOpts(['S/4HANA','SuccessFactors','Ariba','BTP','Other'], p.sap_product)}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Deployment</label>
                        <select name="deployment_option">
                            ${selectOpts(['on_premise','cloud','hybrid'], p.deployment_option)}
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Start Date</label>
                        <input name="start_date" type="date" value="${p.start_date || ''}">
                    </div>
                    <div class="form-group">
                        <label>End Date</label>
                        <input name="end_date" type="date" value="${p.end_date || ''}">
                    </div>
                </div>
                <div class="form-group">
                    <label>Go-Live Date</label>
                    <input name="go_live_date" type="date" value="${p.go_live_date || ''}">
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">${isEdit ? 'Update' : 'Create'}</button>
                </div>
            </form>
        `;
    }

    // ── Form Submit ──────────────────────────────────────────────────────
    async function handleSubmit(event, id) {
        event.preventDefault();
        const form = event.target;
        const data = Object.fromEntries(new FormData(form).entries());

        try {
            if (id) {
                await API.put(`/programs/${id}`, data);
                App.toast('Program updated', 'success');
            } else {
                await API.post('/programs', data);
                App.toast('Program created', 'success');
            }
            App.closeModal();
            await loadPrograms();
            App.updateProjectSelector();
        } catch (err) {
            App.toast(err.message, 'error');
        }
    }

    // ── Delete ───────────────────────────────────────────────────────────
    async function deleteProgram(id) {
        const p = programs.find(x => x.id === id);
        if (!confirm(`Delete program "${p?.name}"?`)) return;
        try {
            await API.delete(`/programs/${id}`);
            App.toast('Program deleted', 'success');
            await loadPrograms();
            App.updateProjectSelector();
        } catch (err) {
            App.toast(err.message, 'error');
        }
    }

    // ── Utilities ────────────────────────────────────────────────────────
    function escHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function escAttr(s) {
        return s.replace(/"/g, '&quot;');
    }

    function selectOpts(options, selected) {
        return options.map(o =>
            `<option value="${o}" ${o === selected ? 'selected' : ''}>${o}</option>`
        ).join('');
    }

    // ── Public API ───────────────────────────────────────────────────────
    return { render, showCreateModal, showEditModal, handleSubmit, deleteProgram };
})();
