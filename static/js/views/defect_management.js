/**
 * SAP Transformation Management Platform
 * Defect Management View — Defect CRUD, SLA, Comments, History, Links, AI Triage
 * Extracted from testing.js (Sprint refactor)
 */

const DefectManagementView = (() => {
    const esc = TestingShared.esc;

    // State
    let defects = [];
    let _defectSearch = '';
    let _defectFilters = {};

    // ── Main render ───────────────────────────────────────────────────
    async function render() {
        const pid = TestingShared.getProgram();
        const main = document.getElementById('mainContent');

        if (!pid) {
            main.innerHTML = TestingShared.noProgramHtml('Defect Management');
            return;
        }

        main.innerHTML = `
            <div class="page-header"><h1>🐛 Defect Management</h1></div>
            <div class="card" id="testContent">
                <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
            </div>
        `;
        await renderDefects();
    }

    // ═══════════════════════════════════════════════════════════════════════
    // DEFECTS
    // ═══════════════════════════════════════════════════════════════════════
    async function renderDefects() {
        const pid = TestingShared.pid;
        const _res = await API.get(`/programs/${pid}/testing/defects`);
        defects = _res.items || _res || [];
        const container = document.getElementById('testContent');

        if (defects.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">🐛</div>
                    <div class="empty-state__title">No defects logged</div>
                    <p>No defects have been reported for this program.</p><br>
                    <button class="btn btn-primary" onclick="DefectManagementView.showDefectModal()">+ Report Defect</button>
                </div>`;
            return;
        }

        container.innerHTML = `
            <div id="defectFilterBar" style="margin-bottom:8px"></div>
            <div id="defectTableArea"></div>
        `;
        renderDefectFilterBar();
        applyDefectFilter();
    }

    function renderDefectFilterBar() {
        const el = document.getElementById('defectFilterBar');
        if (!el) return;
        el.innerHTML = ExpUI.filterBar({
            id: 'defFB',
            searchPlaceholder: 'Search defects…',
            searchValue: _defectSearch,
            onSearch: 'DefectManagementView.setDefectSearch(this.value)',
            onChange: 'DefectManagementView.onDefectFilterChange',
            filters: [
                {
                    id: 'severity', label: 'Severity', type: 'multi', color: '#ef4444',
                    options: ['P1','P2','P3','P4'].map(s => ({ value: s, label: s })),
                    selected: _defectFilters.severity || [],
                },
                {
                    id: 'status', label: 'Status', type: 'multi', color: '#10b981',
                    options: ['new','open','in_progress','fixed','retest','closed','rejected','reopened'].map(s => ({ value: s, label: s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ') })),
                    selected: _defectFilters.status || [],
                },
                {
                    id: 'module', label: 'Module', type: 'multi', color: '#8b5cf6',
                    options: [...new Set(defects.map(d => d.module).filter(Boolean))].sort().map(m => ({ value: m, label: m })),
                    selected: _defectFilters.module || [],
                },
            ],
            actionsHtml: `<span style="font-size:12px;color:#94a3b8" id="defItemCount"></span>
                <button class="btn btn-primary btn-sm" onclick="DefectManagementView.showDefectModal()">+ Report Defect</button>`,
        });
    }

    function setDefectSearch(val) {
        _defectSearch = val;
        applyDefectFilter();
    }

    function onDefectFilterChange(update) {
        if (update._clearAll) {
            _defectFilters = {};
        } else {
            Object.keys(update).forEach(key => {
                const val = update[key];
                if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                    delete _defectFilters[key];
                } else {
                    _defectFilters[key] = val;
                }
            });
        }
        renderDefectFilterBar();
        applyDefectFilter();
    }

    function applyDefectFilter() {
        let filtered = [...defects];

        if (_defectSearch) {
            const q = _defectSearch.toLowerCase();
            filtered = filtered.filter(d =>
                (d.title || '').toLowerCase().includes(q) ||
                (d.code || '').toLowerCase().includes(q) ||
                (d.module || '').toLowerCase().includes(q) ||
                (d.assigned_to || '').toLowerCase().includes(q)
            );
        }

        Object.entries(_defectFilters).forEach(([key, val]) => {
            if (!val) return;
            const values = Array.isArray(val) ? val : [val];
            if (values.length === 0) return;
            filtered = filtered.filter(d => values.includes(String(d[key])));
        });

        const countEl = document.getElementById('defItemCount');
        if (countEl) countEl.textContent = `${filtered.length} of ${defects.length}`;

        const tableEl = document.getElementById('defectTableArea');
        if (!tableEl) return;
        if (filtered.length === 0) {
            tableEl.innerHTML = '<div class="empty-state" style="padding:40px"><p>No defects match your filters.</p></div>';
            return;
        }
        tableEl.innerHTML = _renderDefectTable(filtered);
    }

    function _renderDefectTable(list) {
        const sevBadge = (s) => {
            const c = { P1: '#c4314b', P2: '#e9730c', P3: '#e5a800', P4: '#888' };
            return `<span class="badge" style="background:${c[s] || '#888'};color:#fff">${s}</span>`;
        };
        const statusBadge = (s) => {
            const c = { new: '#0070f3', open: '#e9730c', in_progress: '#6a4fa0', fixed: '#107e3e', retest: '#e5a800', closed: '#888', rejected: '#555', reopened: '#c4314b' };
            return `<span class="badge" style="background:${c[s] || '#888'};color:#fff">${s}</span>`;
        };
        const slaBadge = (s) => {
            if (!s || s === 'n/a') return '<span class="badge" style="background:#ccc;color:#666">N/A</span>';
            const c = { on_track: '#107e3e', warning: '#e5a800', breached: '#c4314b' };
            const label = { on_track: '✓ On Track', warning: '⚠ Warning', breached: '🔴 Breached' };
            return `<span class="badge" style="background:${c[s] || '#888'};color:#fff">${label[s] || s}</span>`;
        };
        return `<table class="data-table">
                <thead><tr>
                    <th>Code</th><th>Title</th><th>Severity</th><th>Status</th>
                    <th>SLA</th><th>Module</th><th>Aging</th><th>Reopen</th><th>Actions</th>
                </tr></thead>
                <tbody>
                    ${list.map(d => `<tr onclick="DefectManagementView.showDefectDetail(${d.id})" style="cursor:pointer" class="clickable-row">
                        <td><strong>${d.code || '-'}</strong></td>
                        <td>${d.title}</td>
                        <td>${sevBadge(d.severity)}</td>
                        <td>${statusBadge(d.status)}</td>
                        <td>${slaBadge(d.sla_status)}</td>
                        <td>${d.module || '-'}</td>
                        <td>${d.aging_days}d</td>
                        <td>${d.reopen_count || 0}</td>
                        <td>
                            <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();DefectManagementView.deleteDefect(${d.id})">🗑</button>
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>`;
    }

    function showDefectModal(d = null) {
        const isEdit = !!d;
        const title = isEdit ? 'Edit Defect' : 'Report Defect';
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>${title}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body" style="max-height:75vh;overflow-y:auto">
                ${isEdit ? `
                <div style="display:flex;gap:4px;margin-bottom:12px;border-bottom:1px solid #e0e0e0;padding-bottom:8px">
                    <button class="btn btn-sm defect-tab-btn active" data-dtab="form" onclick="DefectManagementView._switchDefectTab('form')">📝 Details</button>
                    <button class="btn btn-sm defect-tab-btn" data-dtab="sla" onclick="DefectManagementView._switchDefectTab('sla')">⏱ SLA</button>
                    <button class="btn btn-sm defect-tab-btn" data-dtab="comments" onclick="DefectManagementView._switchDefectTab('comments')">💬 Comments</button>
                    <button class="btn btn-sm defect-tab-btn" data-dtab="history" onclick="DefectManagementView._switchDefectTab('history')">📜 History</button>
                    <button class="btn btn-sm defect-tab-btn" data-dtab="links" onclick="DefectManagementView._switchDefectTab('links')">🔗 Links</button>
                </div>` : ''}

                <!-- FORM TAB -->
                <div id="defectTabForm" class="defect-tab-panel">
                <div class="form-group"><label>Title *</label>
                    <input id="defTitle" class="form-control" value="${isEdit ? esc(d.title) : ''}"></div>
                <div class="form-row">
                    <div class="form-group"><label>Severity</label>
                        <select id="defSeverity" class="form-control">
                            ${['P1','P2','P3','P4'].map(s =>
                                `<option value="${s}" ${(isEdit && d.severity === s) ? 'selected' : ''}>${s}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Status</label>
                        <select id="defStatus" class="form-control">
                            ${['new','open','in_progress','fixed','retest','closed','rejected','reopened'].map(s =>
                                `<option value="${s}" ${(isEdit && d.status === s) ? 'selected' : ''}>${s}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Module</label>
                        <input id="defModule" class="form-control" value="${isEdit ? esc(d.module || '') : ''}" placeholder="FI, MM, SD..."></div>
                </div>
                <div class="form-group"><label>Description</label>
                    <textarea id="defDesc" class="form-control" rows="2">${isEdit ? esc(d.description || '') : ''}</textarea></div>
                <div class="form-group"><label>Steps to Reproduce</label>
                    <textarea id="defSteps" class="form-control" rows="3">${isEdit ? esc(d.steps_to_reproduce || '') : ''}</textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Reported By</label>
                        <input id="defReporter" class="form-control" value="${isEdit ? esc(d.reported_by || '') : ''}"></div>
                    <div class="form-group"><label>Assigned To</label>
                        <input id="defAssigned" class="form-control" value="${isEdit ? esc(d.assigned_to || '') : ''}"></div>
                    <div class="form-group"><label>Environment</label>
                        <input id="defEnv" class="form-control" value="${isEdit ? esc(d.environment || '') : ''}" placeholder="DEV / QAS / PRD"></div>
                </div>
                <div style="border-top:1px solid #e0e0e0;margin:12px 0 8px;padding-top:8px">
                    <label style="font-weight:600;font-size:13px;color:#666">🔗 Linked Items</label>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Test Case ID</label>
                        <input id="defTestCaseId" class="form-control" type="number" value="${isEdit && d.test_case_id ? d.test_case_id : ''}" placeholder="TC id"></div>
                    <div class="form-group"><label>WRICEF Item ID</label>
                        <input id="defBacklogItemId" class="form-control" type="number" value="${isEdit && d.backlog_item_id ? d.backlog_item_id : ''}" placeholder="Backlog item id"></div>
                    <div class="form-group"><label>Config Item ID</label>
                        <input id="defConfigItemId" class="form-control" type="number" value="${isEdit && d.config_item_id ? d.config_item_id : ''}" placeholder="Config item id"></div>
                </div>
                ${isEdit ? `
                <div class="form-group"><label>Resolution</label>
                    <textarea id="defResolution" class="form-control" rows="2">${esc(d.resolution || '')}</textarea></div>
                <div class="form-group"><label>Root Cause</label>
                    <textarea id="defRootCause" class="form-control" rows="2">${esc(d.root_cause || '')}</textarea></div>
                <div class="form-group"><label>Transport Request</label>
                    <input id="defTransport" class="form-control" value="${esc(d.transport_request || '')}"></div>
                ` : ''}
                <div id="aiTriagePanel" class="ai-assistant-panel" style="margin-top:12px"></div>
                </div>

                ${isEdit ? `
                <!-- SLA TAB -->
                <div id="defectTabSla" class="defect-tab-panel" style="display:none">
                    <div id="defectSlaContent"><div class="spinner" style="margin:16px auto"></div></div>
                </div>

                <!-- COMMENTS TAB -->
                <div id="defectTabComments" class="defect-tab-panel" style="display:none">
                    <div id="defectCommentsContent"><div class="spinner" style="margin:16px auto"></div></div>
                    <div style="border-top:1px solid #e0e0e0;margin-top:12px;padding-top:12px">
                        <h4>Add Comment</h4>
                        <div class="form-group"><label>Author</label>
                            <input id="commentAuthor" class="form-control" placeholder="Your name"></div>
                        <div class="form-group"><label>Comment</label>
                            <textarea id="commentBody" class="form-control" rows="3" placeholder="Write a comment..."></textarea></div>
                        <button class="btn btn-primary btn-sm" onclick="DefectManagementView.addDefectComment(${d.id})">Post Comment</button>
                    </div>
                </div>

                <!-- HISTORY TAB -->
                <div id="defectTabHistory" class="defect-tab-panel" style="display:none">
                    <div id="defectHistoryContent"><div class="spinner" style="margin:16px auto"></div></div>
                </div>

                <!-- LINKS TAB -->
                <div id="defectTabLinks" class="defect-tab-panel" style="display:none">
                    <div id="defectLinksContent"><div class="spinner" style="margin:16px auto"></div></div>
                    <div style="border-top:1px solid #e0e0e0;margin-top:12px;padding-top:12px">
                        <h4>Add Link</h4>
                        <div class="form-row">
                            <div class="form-group"><label>Target Defect ID</label>
                                <input id="linkTargetId" class="form-control" type="number" placeholder="Defect ID"></div>
                            <div class="form-group"><label>Link Type</label>
                                <select id="linkType" class="form-control">
                                    <option value="related">Related</option>
                                    <option value="duplicate">Duplicate</option>
                                    <option value="blocks">Blocks</option>
                                </select></div>
                        </div>
                        <div class="form-group"><label>Notes</label>
                            <input id="linkNotes" class="form-control" placeholder="Optional notes"></div>
                        <button class="btn btn-primary btn-sm" onclick="DefectManagementView.addDefectLink(${d.id})">Add Link</button>
                    </div>
                </div>
                ` : ''}
            </div>
            <div class="modal-footer">
                ${isEdit ? `<button class="btn btn-ai btn-sm" id="btnAITriage" onclick="DefectManagementView.runAITriage(${d.id})">🤖 AI Triage</button>` : ''}
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="DefectManagementView.saveDefect(${isEdit ? d.id : 'null'})">${isEdit ? 'Update' : 'Create'}</button>
            </div>
        `;
        overlay.classList.add('open');

        if (isEdit) {
            _loadDefectSla(d.id);
            _loadDefectComments(d.id);
            _loadDefectHistory(d.id);
            _loadDefectLinks(d.id);
        }
    }

    function _switchDefectTab(tab) {
        document.querySelectorAll('.defect-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.dtab === tab));
        document.querySelectorAll('.defect-tab-panel').forEach(p => p.style.display = 'none');
        const panelId = {form:'defectTabForm',sla:'defectTabSla',comments:'defectTabComments',history:'defectTabHistory',links:'defectTabLinks'}[tab];
        const panel = document.getElementById(panelId);
        if (panel) panel.style.display = '';
    }

    // ── Defect SLA ───────────────────────────────────────────────────────
    async function _loadDefectSla(defectId) {
        try {
            const sla = await API.get(`/testing/defects/${defectId}/sla`);
            const el = document.getElementById('defectSlaContent');
            if (!el) return;
            const statusColor = { on_track: '#107e3e', warning: '#e5a800', breached: '#c4314b' };
            const statusLabel = { on_track: '✓ On Track', warning: '⚠ Warning', breached: '🔴 Breached', n_a: 'N/A' };
            const slaStatus = sla.sla_status || 'n_a';
            const cfg = sla.sla_config || {};

            const now = new Date();
            const dueDate = sla.sla_due_date ? new Date(sla.sla_due_date) : null;
            const remainingHours = dueDate ? Math.round((dueDate - now) / 3600000) : '-';

            el.innerHTML = `
                <div style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap">
                    <div class="kpi-card" style="min-width:120px;text-align:center">
                        <div class="kpi-value" style="color:${statusColor[slaStatus] || '#888'};font-size:16px">${statusLabel[slaStatus] || slaStatus}</div>
                        <div class="kpi-label">SLA Status</div>
                    </div>
                    <div class="kpi-card" style="min-width:100px;text-align:center">
                        <div class="kpi-value">${sla.severity || '-'}</div>
                        <div class="kpi-label">Severity</div>
                    </div>
                    <div class="kpi-card" style="min-width:100px;text-align:center">
                        <div class="kpi-value">${sla.priority || '-'}</div>
                        <div class="kpi-label">Priority</div>
                    </div>
                </div>
                <table class="data-table">
                    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                    <tbody>
                        <tr><td><strong>SLA Due Date</strong></td><td>${sla.sla_due_date ? new Date(sla.sla_due_date).toLocaleString() : 'Not set'}</td></tr>
                        <tr><td><strong>First Response (hours)</strong></td><td>${cfg.first_response_hours || '-'}</td></tr>
                        <tr><td><strong>Resolution Target (hours)</strong></td><td>${cfg.resolution_hours || '-'}</td></tr>
                        <tr><td><strong>Time Remaining</strong></td>
                            <td style="color:${remainingHours !== '-' && remainingHours < 0 ? '#c4314b' : '#107e3e'}">${remainingHours !== '-' ? (remainingHours < 0 ? Math.abs(remainingHours) + 'h overdue' : remainingHours + 'h remaining') : 'N/A'}</td></tr>
                        <tr><td><strong>Current Status</strong></td><td>${esc(sla.status)}</td></tr>
                    </tbody>
                </table>
            `;
        } catch(e) {
            const el = document.getElementById('defectSlaContent');
            if (el) el.innerHTML = `<p style="color:#c4314b">Error loading SLA: ${esc(e.message)}</p>`;
        }
    }

    // ── Defect Comments ──────────────────────────────────────────────────
    async function _loadDefectComments(defectId) {
        try {
            const comments = await API.get(`/testing/defects/${defectId}/comments`);
            const el = document.getElementById('defectCommentsContent');
            if (!el) return;
            if (comments.length === 0) {
                el.innerHTML = '<p style="color:#999;text-align:center">No comments yet.</p>';
                return;
            }
            el.innerHTML = comments.map(c => `
                <div style="border:1px solid #e0e0e0;border-radius:6px;padding:10px;margin-bottom:8px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                        <strong>${esc(c.author)}</strong>
                        <span style="color:#888;font-size:12px">${c.created_at ? new Date(c.created_at).toLocaleString() : ''}</span>
                    </div>
                    <p style="margin:0;white-space:pre-wrap">${esc(c.body)}</p>
                    <button class="btn btn-sm btn-danger" style="margin-top:4px" onclick="DefectManagementView.deleteDefectComment(${c.id}, ${defectId})">🗑</button>
                </div>`).join('');
        } catch(e) {
            const el = document.getElementById('defectCommentsContent');
            if (el) el.innerHTML = `<p style="color:#c4314b">Error loading comments: ${esc(e.message)}</p>`;
        }
    }

    async function addDefectComment(defectId) {
        const author = document.getElementById('commentAuthor')?.value;
        const body = document.getElementById('commentBody')?.value;
        if (!author || !body) return App.toast('Author and comment text required', 'error');
        await API.post(`/testing/defects/${defectId}/comments`, { author, body });
        App.toast('Comment added', 'success');
        document.getElementById('commentBody').value = '';
        await _loadDefectComments(defectId);
    }

    async function deleteDefectComment(commentId, defectId) {
        if (!confirm('Delete this comment?')) return;
        await API.delete(`/testing/defect-comments/${commentId}`);
        App.toast('Comment deleted', 'success');
        await _loadDefectComments(defectId);
    }

    // ── Defect History ───────────────────────────────────────────────────
    async function _loadDefectHistory(defectId) {
        try {
            const history = await API.get(`/testing/defects/${defectId}/history`);
            const el = document.getElementById('defectHistoryContent');
            if (!el) return;
            if (history.length === 0) {
                el.innerHTML = '<p style="color:#999;text-align:center">No change history yet.</p>';
                return;
            }
            el.innerHTML = `
                <table class="data-table">
                    <thead><tr><th>Date</th><th>Changed By</th><th>Field</th><th>Old Value</th><th>New Value</th></tr></thead>
                    <tbody>
                        ${history.map(h => `<tr>
                            <td style="white-space:nowrap;font-size:12px">${h.changed_at ? new Date(h.changed_at).toLocaleString() : '-'}</td>
                            <td>${esc(h.changed_by || '-')}</td>
                            <td><strong>${esc(h.field)}</strong></td>
                            <td style="color:#c4314b">${esc(h.old_value || '—')}</td>
                            <td style="color:#107e3e">${esc(h.new_value || '—')}</td>
                        </tr>`).join('')}
                    </tbody>
                </table>`;
        } catch(e) {
            const el = document.getElementById('defectHistoryContent');
            if (el) el.innerHTML = `<p style="color:#c4314b">Error loading history: ${esc(e.message)}</p>`;
        }
    }

    // ── Defect Links ─────────────────────────────────────────────────────
    async function _loadDefectLinks(defectId) {
        try {
            const data = await API.get(`/testing/defects/${defectId}/links`);
            const el = document.getElementById('defectLinksContent');
            if (!el) return;
            const outgoing = data.outgoing || [];
            const incoming = data.incoming || [];
            if (outgoing.length === 0 && incoming.length === 0) {
                el.innerHTML = '<p style="color:#999;text-align:center">No linked defects.</p>';
                return;
            }
            const linkBadge = (t) => {
                const c = {duplicate:'#e9730c',related:'#0070f3',blocks:'#c4314b'};
                return `<span class="badge" style="background:${c[t]||'#888'};color:#fff">${t}</span>`;
            };
            let html = '';
            if (outgoing.length > 0) {
                html += `<h4 style="margin-bottom:4px">Outgoing Links</h4>
                <table class="data-table"><thead><tr><th>Type</th><th>Target Defect</th><th>Notes</th><th></th></tr></thead><tbody>
                    ${outgoing.map(l => `<tr>
                        <td>${linkBadge(l.link_type)}</td>
                        <td>#${l.target_defect_id}</td>
                        <td>${esc(l.notes || '-')}</td>
                        <td><button class="btn btn-sm btn-danger" onclick="DefectManagementView.deleteDefectLink(${l.id}, ${defectId})">🗑</button></td>
                    </tr>`).join('')}</tbody></table>`;
            }
            if (incoming.length > 0) {
                html += `<h4 style="margin:12px 0 4px">Incoming Links</h4>
                <table class="data-table"><thead><tr><th>Type</th><th>Source Defect</th><th>Notes</th></tr></thead><tbody>
                    ${incoming.map(l => `<tr>
                        <td>${linkBadge(l.link_type)}</td>
                        <td>#${l.source_defect_id}</td>
                        <td>${esc(l.notes || '-')}</td>
                    </tr>`).join('')}</tbody></table>`;
            }
            el.innerHTML = html;
        } catch(e) {
            const el = document.getElementById('defectLinksContent');
            if (el) el.innerHTML = `<p style="color:#c4314b">Error loading links: ${esc(e.message)}</p>`;
        }
    }

    async function addDefectLink(defectId) {
        const targetId = parseInt(document.getElementById('linkTargetId')?.value);
        const linkType = document.getElementById('linkType')?.value;
        const notes = document.getElementById('linkNotes')?.value || '';
        if (!targetId) return App.toast('Target Defect ID required', 'error');
        await API.post(`/testing/defects/${defectId}/links`, { target_defect_id: targetId, link_type: linkType, notes });
        App.toast('Link added', 'success');
        document.getElementById('linkTargetId').value = '';
        document.getElementById('linkNotes').value = '';
        await _loadDefectLinks(defectId);
    }

    async function deleteDefectLink(linkId, defectId) {
        if (!confirm('Remove this link?')) return;
        await API.delete(`/testing/defect-links/${linkId}`);
        App.toast('Link removed', 'success');
        await _loadDefectLinks(defectId);
    }

    async function saveDefect(id) {
        const pid = TestingShared.pid;
        const body = {
            title: document.getElementById('defTitle').value,
            severity: document.getElementById('defSeverity').value,
            status: document.getElementById('defStatus').value,
            module: document.getElementById('defModule').value,
            description: document.getElementById('defDesc').value,
            steps_to_reproduce: document.getElementById('defSteps').value,
            reported_by: document.getElementById('defReporter').value,
            assigned_to: document.getElementById('defAssigned').value,
            environment: document.getElementById('defEnv').value,
            test_case_id: parseInt(document.getElementById('defTestCaseId').value) || null,
            backlog_item_id: parseInt(document.getElementById('defBacklogItemId').value) || null,
            config_item_id: parseInt(document.getElementById('defConfigItemId').value) || null,
        };
        if (id) {
            const res = document.getElementById('defResolution');
            if (res) body.resolution = res.value;
            const rc = document.getElementById('defRootCause');
            if (rc) body.root_cause = rc.value;
            const tr = document.getElementById('defTransport');
            if (tr) body.transport_request = tr.value;
        }
        if (!body.title) return App.toast('Title is required', 'error');

        if (id) {
            await API.put(`/testing/defects/${id}`, body);
            App.toast('Defect updated', 'success');
        } else {
            await API.post(`/programs/${pid}/testing/defects`, body);
            App.toast('Defect reported', 'success');
        }
        App.closeModal();
        await renderDefects();
    }

    async function showDefectDetail(id) {
        const d = await API.get(`/testing/defects/${id}`);
        showDefectModal(d);
    }

    async function deleteDefect(id) {
        if (!confirm('Delete this defect?')) return;
        await API.delete(`/testing/defects/${id}`);
        App.toast('Defect deleted', 'success');
        await renderDefects();
    }

    // ── AI Triage ────────────────────────────────────────────────────────
    async function runAITriage(defectId) {
        const btn = document.getElementById('btnAITriage');
        const panel = document.getElementById('aiTriagePanel');
        if (!btn || !panel) return;

        btn.disabled = true;
        btn.textContent = '⏳ Triaging...';
        panel.innerHTML = '<div class="spinner" style="margin:8px auto"></div>';

        try {
            const data = await API.post(`/ai/triage/defect/${defectId}`, {
                create_suggestion: true,
            });

            const confPct = Math.round((data.confidence || 0) * 100);
            const confClass = confPct >= 80 ? 'high' : confPct >= 50 ? 'medium' : 'low';
            const dupes = data.potential_duplicates || [];
            const similar = data.similar_defects || [];

            panel.innerHTML = `
                <div class="ai-assistant-section">
                    <div class="ai-assistant-header">
                        <span>🤖 AI Triage Result</span>
                        <span class="badge badge-confidence-${confClass}">${confPct}% confidence</span>
                        ${data.suggestion_id ? '<span class="badge badge-pending">📋 Suggestion created</span>' : ''}
                    </div>
                    <div class="ai-result-item">
                        <div class="ai-result-header">
                            <span><strong>Suggested Severity:</strong>
                                <span class="badge badge-severity-${data.suggested_severity || 'P3'}">${data.suggested_severity || '—'}</span>
                            </span>
                            ${data.suggested_module ? `<span><strong>Module:</strong> ${esc(data.suggested_module)}</span>` : ''}
                        </div>
                        <p class="ai-result-reasoning">${esc(data.reasoning || '')}</p>
                        ${data.suggested_assigned_to ? `<p class="ai-result-detail"><strong>Assign to:</strong> ${esc(data.suggested_assigned_to)}</p>` : ''}
                        ${data.root_cause_hint ? `<p class="ai-result-detail"><strong>Root Cause Hint:</strong> ${esc(data.root_cause_hint)}</p>` : ''}
                    </div>
                    ${dupes.length ? `
                    <div class="ai-result-item ai-result--warning">
                        <strong>⚠️ Potential Duplicates (${dupes.length})</strong>
                        <ul>${dupes.map(dp => `<li>#${dp.id} — ${esc(dp.title)} <span class="badge">${Math.round((dp.similarity || 0) * 100)}%</span></li>`).join('')}</ul>
                    </div>` : ''}
                    ${similar.length ? `
                    <div class="ai-result-item">
                        <strong>🔗 Similar Defects (${similar.length})</strong>
                        <ul>${similar.map(s => `<li>#${s.id} — ${esc(s.title)} <span class="badge">${Math.round((s.similarity || 0) * 100)}%</span></li>`).join('')}</ul>
                    </div>` : ''}
                    <div class="ai-result-actions" style="margin-top:8px">
                        <button class="btn btn-sm btn-success" onclick="DefectManagementView.applyTriageSuggestion(${defectId}, '${data.suggested_severity || ''}', '${esc(data.suggested_module || '')}')">✅ Apply Suggestions</button>
                    </div>
                </div>`;
        } catch(e) {
            panel.innerHTML = `<div class="ai-result-item ai-result--error">⚠️ ${esc(e.message)}</div>`;
        } finally {
            btn.disabled = false;
            btn.textContent = '🤖 AI Triage';
        }
    }

    function applyTriageSuggestion(defectId, severity, module) {
        if (severity) {
            const sel = document.getElementById('defSeverity');
            if (sel) sel.value = severity;
        }
        if (module) {
            const inp = document.getElementById('defModule');
            if (inp) inp.value = module;
        }
        App.toast('AI suggestions applied to form. Click Update to save.', 'info');
    }

    // Legacy shim
    async function filterDefects() { applyDefectFilter(); }

    // ── Public API ─────────────────────────────────────────────────────────
    return {
        render,
        showDefectModal, saveDefect, showDefectDetail, deleteDefect, filterDefects,
        setDefectSearch, onDefectFilterChange,
        runAITriage, applyTriageSuggestion,
        _switchDefectTab, addDefectComment, deleteDefectComment,
        addDefectLink, deleteDefectLink,
    };
})();
