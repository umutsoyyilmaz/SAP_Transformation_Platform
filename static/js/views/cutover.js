/**
 * Cutover Hub View — Sprint 13
 *
 * Tabs: Plans | Runbook | Rehearsals | Go/No-Go
 *
 * CutoverPlan dashboard ─── scope items / tasks (Runbook) ───
 * Rehearsal tracking ─── Go/No-Go decision pack
 */
const CutoverView = (() => {
    let _pid = null;
    let _plans = [];
    let _activePlan = null;
    let _currentTab = 'plans';

    // ── Helpers ───────────────────────────────────────────────────────
    function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
    function fmtDate(d) { return d ? new Date(d).toLocaleDateString('en-US') : '—'; }
    function fmtDateTime(d) { return d ? new Date(d).toLocaleString('en-US') : '—'; }
    function fmtStatus(s) { return (s||'').replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase()); }

    const STATUS_COLORS = {
        draft:'#5B738B', approved:'#0A6ED1', rehearsal:'#E78C07',
        ready:'#2B7D2B', executing:'#A45EB5', completed:'#2B7D2B',
        rolled_back:'#BB0000', hypercare:'#0854A0', closed:'#6C757D',
        not_started:'#5B738B', in_progress:'#0A6ED1', failed:'#BB0000',
        skipped:'#6C757D',
        planned:'#5B738B', cancelled:'#6C757D',
        pending:'#E78C07', go:'#2B7D2B', no_go:'#BB0000', waived:'#6C757D',
        open:'#E78C07', investigating:'#0A6ED1', resolved:'#2B7D2B',
        P1:'#BB0000', P2:'#E78C07', P3:'#0A6ED1', P4:'#6C757D',
    };

    function badge(status) {
        return PGStatusRegistry.badge(status, { label: fmtStatus(status) });
    }

    // ── Main render ──────────────────────────────────────────────────
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        _pid = prog ? prog.id : null;

        if (!_pid) {
            main.innerHTML = PGEmptyState.html({ icon: 'cutover', title: 'Cutover Hub', description: 'Select a program first to continue.', action: { label: 'Go to Programs', onclick: "App.navigate('programs')" } });
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Cutover Hub' }])}
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <h2 class="pg-view-title">Cutover Hub</h2>
                    <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="CutoverView.showCreatePlan()">+ New Plan</button>
                </div>
            </div>
            <div class="tabs" id="cutTabs" style="margin-bottom:1rem">
                <button class="tab active" data-tab="plans" onclick="CutoverView.switchTab('plans')">📋 Plans</button>
                <button class="tab" data-tab="runbook" onclick="CutoverView.switchTab('runbook')">📖 Runbook</button>
                <button class="tab" data-tab="rehearsals" onclick="CutoverView.switchTab('rehearsals')">🔄 Rehearsals</button>
                <button class="tab" data-tab="gonogo" onclick="CutoverView.switchTab('gonogo')">✅ Go / No-Go</button>
                <button class="tab" data-tab="hypercare" onclick="CutoverView.switchTab('hypercare')">🏥 Hypercare</button>
            </div>
            <div id="cutContent"><div style="text-align:center;padding:40px"><div class="spinner"></div></div></div>
        `;

        await loadPlans();
        renderTab();
    }

    async function loadPlans() {
        try {
            const res = await API.get(`/cutover/plans?program_id=${_pid}`);
            _plans = res.items || res || [];
            if (_plans.length > 0 && !_activePlan) _activePlan = _plans[0];
        } catch(e) { App.toast(e.message,'error'); }
    }

    function switchTab(tab) {
        _currentTab = tab;
        document.querySelectorAll('#cutTabs .tab').forEach(t =>
            t.classList.toggle('active', t.dataset.tab === tab));
        renderTab();
    }

    function renderTab() {
        const c = document.getElementById('cutContent');
        if (!c) return;
        switch(_currentTab) {
            case 'plans':     renderPlansTab(c); break;
            case 'runbook':   renderRunbookTab(c); break;
            case 'rehearsals':renderRehearsalsTab(c); break;
            case 'gonogo':    renderGoNoGoTab(c); break;
            case 'hypercare': renderHypercareTab(c); break;
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  PLANS TAB
    // ═══════════════════════════════════════════════════════════════════
    function renderPlansTab(c) {
        if (_plans.length === 0) {
            c.innerHTML = `<div class="empty-state">
                <div class="empty-state__icon">📋</div>
                <div class="empty-state__title">No cutover plans yet</div>
                <p>Create your first cutover plan to get started.</p>
                <button class="btn btn-primary" onclick="CutoverView.showCreatePlan()">+ New Plan</button>
            </div>`;
            return;
        }
        c.innerHTML = `
            <div class="kpi-row" style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap">
                ${_plans.map(p => `
                    <div class="kpi-card" style="flex:1;min-width:220px;background:var(--card-bg,var(--sap-card-bg,#fff));
                        border-radius:8px;padding:16px;box-shadow:var(--shadow,0 1px 3px rgba(0,0,0,.1));
                        cursor:pointer;border:2px solid ${_activePlan && _activePlan.id===p.id? 'var(--sap-blue,#0A6ED1)':'transparent'}"
                        onclick="CutoverView.selectPlan(${p.id})">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                            <strong>${esc(p.code)}</strong>
                            ${badge(p.status)}
                        </div>
                        <div style="font-size:15px;font-weight:600;margin-bottom:4px">${esc(p.name)}</div>
                        <div style="font-size:12px;color:var(--sap-text-secondary,#666)">
                            Manager: ${esc(p.cutover_manager||'—')} · Env: ${esc(p.environment)}
                        </div>
                        <div style="font-size:12px;color:var(--sap-text-secondary,#666);margin-top:4px">
                            ${fmtDate(p.planned_start)} → ${fmtDate(p.planned_end)}
                        </div>
                        <div style="display:flex;gap:12px;margin-top:8px;font-size:12px;color:var(--sap-text-secondary)">
                            <span>📦 ${p.scope_item_count} scope</span>
                            <span>🔄 ${p.rehearsal_count} rehearsals</span>
                            <span>✅ ${p.go_no_go_count} G/NG</span>
                        </div>
                    </div>
                `).join('')}
            </div>
            ${_activePlan ? renderPlanDetail() : ''}
        `;
    }

    function renderPlanDetail() {
        const p = _activePlan;
        return `
            <div style="background:var(--card-bg,var(--sap-card-bg,#fff));border-radius:8px;padding:20px;
                box-shadow:var(--shadow,0 1px 3px rgba(0,0,0,.1));margin-bottom:16px">
                <div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:12px">
                    <div>
                        <h3 style="margin:0">${esc(p.code)} — ${esc(p.name)}</h3>
                        <p style="color:var(--sap-text-secondary);margin:4px 0 0">${esc(p.description||'')}</p>
                    </div>
                    <div style="display:flex;gap:8px">
                        <button class="btn btn-sm btn-secondary" onclick="CutoverView.editPlan(${p.id})">✏️ Edit</button>
                        <button class="btn btn-sm btn-danger" onclick="CutoverView.deletePlan(${p.id})">🗑️</button>
                    </div>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:16px;font-size:13px;color:var(--sap-text-secondary)">
                    <span>Status: ${badge(p.status)}</span>
                    <span>Version: ${p.version}</span>
                    <span>Env: ${esc(p.environment)}</span>
                    <span>Rollback Deadline: ${fmtDateTime(p.rollback_deadline)}</span>
                </div>
                <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap" id="planTransitions">
                    ${renderTransitionButtons(p)}
                </div>
            </div>
        `;
    }

    function renderTransitionButtons(p) {
        const transitions = {
            draft:      ['approved'],
            approved:   ['rehearsal','ready'],
            rehearsal:  ['approved','ready'],
            ready:      ['executing','approved'],
            executing:  ['completed','rolled_back'],
            rolled_back:['draft'],
        };
        const nexts = transitions[p.status] || [];
        return nexts.map(s =>
            `<button class="btn btn-sm btn-secondary" onclick="CutoverView.transitionPlan(${p.id},'${s}')">
                → ${fmtStatus(s)}
            </button>`
        ).join('');
    }

    function selectPlan(planId) {
        _activePlan = _plans.find(p => p.id === planId) || null;
        renderTab();
    }

    // ═══════════════════════════════════════════════════════════════════
    //  RUNBOOK TAB
    // ═══════════════════════════════════════════════════════════════════
    async function renderRunbookTab(c) {
        if (!_activePlan) {
            c.innerHTML = `<div class="empty-state"><div class="empty-state__icon">📖</div>
                <div class="empty-state__title">Select a plan first</div></div>`;
            return;
        }

        c.innerHTML = `<div style="text-align:center;padding:40px"><div class="spinner"></div></div>`;

        try {
            const res = await API.get(`/cutover/plans/${_activePlan.id}/scope-items`);
            const scopeItems = res.items || [];

            // Load tasks for each scope item
            const withTasks = await Promise.all(scopeItems.map(async si => {
                const tRes = await API.get(`/cutover/scope-items/${si.id}/tasks`);
                si.tasks = tRes.items || [];
                return si;
            }));

            if (withTasks.length === 0) {
                c.innerHTML = `<div class="empty-state">
                    <div class="empty-state__icon">📖</div>
                    <div class="empty-state__title">No scope items yet</div>
                    <button class="btn btn-primary" onclick="CutoverView.showCreateScopeItem()">+ New Scope Item</button>
                </div>`;
                return;
            }

            // Progress bar
            let totalTasks = 0, completedTasks = 0;
            withTasks.forEach(si => si.tasks.forEach(t => {
                totalTasks++;
                if (t.status === 'completed' || t.status === 'skipped') completedTasks++;
            }));
            const pct = totalTasks > 0 ? Math.round(completedTasks / totalTasks * 100) : 0;

            c.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <div>
                        <strong>${esc(_activePlan.code)} Runbook</strong>
                        <span style="margin-left:8px;font-size:13px;color:var(--sap-text-secondary)">${completedTasks}/${totalTasks} tasks (${pct}%)</span>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="CutoverView.showCreateScopeItem()">+ Scope Item</button>
                </div>
                <div style="background:var(--sap-border,#eee);border-radius:4px;height:8px;margin-bottom:20px;overflow:hidden">
                    <div style="width:${pct}%;height:100%;background:var(--sap-blue,#0A6ED1);transition:width .3s"></div>
                </div>
                ${withTasks.map(si => renderScopeItemCard(si)).join('')}
            `;
        } catch(e) { c.innerHTML = `<p class="text-danger">${esc(e.message)}</p>`; }
    }

    function renderScopeItemCard(si) {
        const catIcons = {data_load:'📦',interface:'🔌',authorization:'🔐',job_scheduling:'⏰',reconciliation:'🔢',custom:'⚙️'};
        return `
            <div style="background:var(--card-bg,var(--sap-card-bg,#fff));border-radius:8px;padding:16px;
                box-shadow:var(--shadow,0 1px 3px rgba(0,0,0,.1));margin-bottom:12px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <div>
                        <strong>${catIcons[si.category]||'⚙️'} ${esc(si.name)}</strong>
                        <span style="margin-left:8px">${badge(si.status)}</span>
                        <span style="font-size:12px;color:var(--sap-text-secondary);margin-left:8px">${si.task_count} tasks · Owner: ${esc(si.owner||'—')}</span>
                    </div>
                    <div style="display:flex;gap:4px">
                        <button class="btn btn-sm btn-secondary" onclick="CutoverView.showCreateTask(${si.id})">+ Task</button>
                        <button class="btn btn-sm btn-danger" onclick="CutoverView.deleteScopeItem(${si.id})">🗑️</button>
                    </div>
                </div>
                ${si.tasks.length > 0 ? `
                    <table class="data-table" style="margin-top:8px">
                        <thead><tr>
                            <th>Seq</th><th>Code</th><th>Title</th><th>Status</th>
                            <th>Responsible</th><th>Planned</th><th>Actual</th><th>Actions</th>
                        </tr></thead>
                        <tbody>
                            ${si.tasks.map(t => `
                                <tr>
                                    <td>${t.sequence}</td>
                                    <td><strong>${esc(t.code||'')}</strong></td>
                                    <td>${esc(t.title)}</td>
                                    <td>${badge(t.status)}</td>
                                    <td>${esc(t.responsible||'—')}</td>
                                    <td>${t.planned_duration_min ? t.planned_duration_min+'m' : '—'}</td>
                                    <td>${t.actual_duration_min ? t.actual_duration_min+'m' : '—'}</td>
                                    <td style="white-space:nowrap">
                                        ${renderTaskActions(t)}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<p style="color:var(--sap-text-secondary);font-size:13px;margin:8px 0 0">No tasks yet</p>'}
            </div>
        `;
    }

    function renderTaskActions(t) {
        const transitions = {
            not_started: ['in_progress','skipped'],
            in_progress: ['completed','failed','rolled_back'],
            completed: ['rolled_back'],
            failed: ['in_progress','rolled_back','skipped'],
            skipped: ['not_started'],
            rolled_back: ['not_started'],
        };
        const nexts = transitions[t.status] || [];
        return nexts.map(s =>
            `<button class="btn btn-sm btn-secondary" style="padding:2px 6px;font-size:11px"
                onclick="CutoverView.transitionTask(${t.id},'${s}')">→${fmtStatus(s).substring(0,6)}</button>`
        ).join(' ') + ` <button class="btn btn-sm btn-danger" style="padding:2px 6px;font-size:11px"
            onclick="CutoverView.deleteTask(${t.id})">🗑️</button>`;
    }

    // ═══════════════════════════════════════════════════════════════════
    //  REHEARSALS TAB
    // ═══════════════════════════════════════════════════════════════════
    async function renderRehearsalsTab(c) {
        if (!_activePlan) {
            c.innerHTML = `<div class="empty-state"><div class="empty-state__icon">🔄</div>
                <div class="empty-state__title">Select a plan first</div></div>`;
            return;
        }
        c.innerHTML = `<div style="text-align:center;padding:40px"><div class="spinner"></div></div>`;

        try {
            const res = await API.get(`/cutover/plans/${_activePlan.id}/rehearsals`);
            const items = res.items || [];

            c.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <strong>${esc(_activePlan.code)} Rehearsals</strong>
                    <button class="btn btn-primary btn-sm" onclick="CutoverView.showCreateRehearsal()">+ New Rehearsal</button>
                </div>
                ${items.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-state__icon">🔄</div>
                        <div class="empty-state__title">No rehearsals yet</div>
                        <p>SAP best practice: at least 2-3 rehearsals before go-live</p>
                    </div>
                ` : `
                    <div style="display:flex;gap:16px;flex-wrap:wrap">
                        ${items.map(r => `
                            <div style="flex:1;min-width:280px;background:var(--card-bg,var(--sap-card-bg,#fff));
                                border-radius:8px;padding:16px;box-shadow:var(--shadow,0 1px 3px rgba(0,0,0,.1))">
                                <div style="display:flex;justify-content:space-between;align-items:center">
                                    <strong>#${r.rehearsal_number} — ${esc(r.name)}</strong>
                                    ${badge(r.status)}
                                </div>
                                <div style="font-size:13px;color:var(--sap-text-secondary);margin-top:8px">
                                    <div>Env: ${esc(r.environment)} · Planned: ${r.planned_duration_min||'—'}m</div>
                                    <div>Actual: ${r.actual_duration_min ? r.actual_duration_min+'m' : '—'} · Variance: ${r.duration_variance_pct !== null ? r.duration_variance_pct+'%' : '—'}</div>
                                    <div style="margin-top:4px">Tasks: ${r.completed_tasks}/${r.total_tasks} ✓ · ${r.failed_tasks} ✗ · ${r.skipped_tasks} ⊘</div>
                                    ${r.runbook_revision_needed ? '<div style="color:var(--sap-negative,#BB0000);margin-top:4px">⚠️ Runbook revision needed</div>' : ''}
                                    ${r.findings_summary ? `<div style="margin-top:4px"><em>${esc(r.findings_summary)}</em></div>` : ''}
                                </div>
                                <div style="display:flex;gap:4px;margin-top:8px;flex-wrap:wrap">
                                    ${renderRehearsalActions(r)}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `}
            `;
        } catch(e) { c.innerHTML = `<p class="text-danger">${esc(e.message)}</p>`; }
    }

    function renderRehearsalActions(r) {
        const transitions = {
            planned:    ['in_progress','cancelled'],
            in_progress:['completed','cancelled'],
            cancelled:  ['planned'],
        };
        const nexts = transitions[r.status] || [];
        let btns = nexts.map(s =>
            `<button class="btn btn-sm btn-secondary" onclick="CutoverView.transitionRehearsal(${r.id},'${s}')">→${fmtStatus(s)}</button>`
        ).join('');
        if (r.status === 'completed') {
            btns += `<button class="btn btn-sm btn-secondary" onclick="CutoverView.computeMetrics(${r.id})">📊 Metrics</button>`;
        }
        btns += `<button class="btn btn-sm btn-danger" onclick="CutoverView.deleteRehearsal(${r.id})">🗑️</button>`;
        return btns;
    }

    // ═══════════════════════════════════════════════════════════════════
    //  GO / NO-GO TAB
    // ═══════════════════════════════════════════════════════════════════
    async function renderGoNoGoTab(c) {
        if (!_activePlan) {
            c.innerHTML = `<div class="empty-state"><div class="empty-state__icon">✅</div>
                <div class="empty-state__title">Select a plan first</div></div>`;
            return;
        }
        c.innerHTML = `<div style="text-align:center;padding:40px"><div class="spinner"></div></div>`;

        try {
            const [itemsRes, summaryRes] = await Promise.all([
                API.get(`/cutover/plans/${_activePlan.id}/go-no-go`),
                API.get(`/cutover/plans/${_activePlan.id}/go-no-go/summary`),
            ]);
            const items = itemsRes.items || [];
            const summary = summaryRes;

            const recColors = { go:'#2B7D2B', no_go:'#BB0000', pending:'#E78C07', no_items:'#6C757D' };
            const recColor = recColors[summary.overall_recommendation] || '#5B738B';

            c.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
                    <strong>${esc(_activePlan.code)} Go/No-Go Decision Pack</strong>
                    <div style="display:flex;gap:8px">
                        <button class="btn btn-sm btn-secondary" onclick="CutoverView.seedGoNoGo()">🌱 Seed Defaults</button>
                        <button class="btn btn-primary btn-sm" onclick="CutoverView.showCreateGoNoGo()">+ New Item</button>
                    </div>
                </div>
                <div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap">
                    <div style="flex:1;min-width:140px;background:${recColor}11;border-radius:8px;padding:16px;border:2px solid ${recColor}">
                        <div style="font-size:13px;color:var(--sap-text-secondary)">Overall</div>
                        <div style="font-size:24px;font-weight:700;color:${recColor}">${fmtStatus(summary.overall_recommendation)}</div>
                    </div>
                    <div class="kpi-card" style="flex:1;min-width:100px;background:var(--card-bg,#fff);border-radius:8px;padding:16px">
                        <div style="font-size:13px;color:var(--sap-text-secondary)">Go</div>
                        <div style="font-size:24px;font-weight:700;color:#2B7D2B">${summary.go}</div>
                    </div>
                    <div class="kpi-card" style="flex:1;min-width:100px;background:var(--card-bg,#fff);border-radius:8px;padding:16px">
                        <div style="font-size:13px;color:var(--sap-text-secondary)">No-Go</div>
                        <div style="font-size:24px;font-weight:700;color:#BB0000">${summary.no_go}</div>
                    </div>
                    <div class="kpi-card" style="flex:1;min-width:100px;background:var(--card-bg,#fff);border-radius:8px;padding:16px">
                        <div style="font-size:13px;color:var(--sap-text-secondary)">Pending</div>
                        <div style="font-size:24px;font-weight:700;color:#E78C07">${summary.pending}</div>
                    </div>
                    <div class="kpi-card" style="flex:1;min-width:100px;background:var(--card-bg,#fff);border-radius:8px;padding:16px">
                        <div style="font-size:13px;color:var(--sap-text-secondary)">Waived</div>
                        <div style="font-size:24px;font-weight:700;color:#6C757D">${summary.waived}</div>
                    </div>
                </div>
                ${items.length === 0 ? `
                    <div class="empty-state">
                        <div class="empty-state__icon">✅</div>
                        <div class="empty-state__title">No Go/No-Go items</div>
                        <p>Click "Seed Defaults" to create the standard 7-item checklist.</p>
                    </div>
                ` : `
                    <table class="data-table">
                        <thead><tr><th>Source</th><th>Criterion</th><th>Verdict</th><th>Evidence</th><th>Evaluated</th><th>Actions</th></tr></thead>
                        <tbody>
                            ${items.map(g => `
                                <tr>
                                    <td>${badge(g.source_domain)}</td>
                                    <td><strong>${esc(g.criterion)}</strong><br><span style="font-size:12px;color:var(--sap-text-secondary)">${esc(g.description||'')}</span></td>
                                    <td>${badge(g.verdict)}</td>
                                    <td style="max-width:200px;font-size:12px">${esc(g.evidence||'—')}</td>
                                    <td style="font-size:12px">${esc(g.evaluated_by||'—')}<br>${fmtDate(g.evaluated_at)}</td>
                                    <td style="white-space:nowrap">
                                        <select style="font-size:11px;padding:2px 4px;border-radius:4px;border:1px solid var(--sap-border,#ccc)"
                                            onchange="CutoverView.updateGoNoGoVerdict(${g.id},this.value)">
                                            <option value="pending" ${g.verdict==='pending'?'selected':''}>Pending</option>
                                            <option value="go" ${g.verdict==='go'?'selected':''}>Go</option>
                                            <option value="no_go" ${g.verdict==='no_go'?'selected':''}>No-Go</option>
                                            <option value="waived" ${g.verdict==='waived'?'selected':''}>Waived</option>
                                        </select>
                                        <button class="btn btn-sm btn-danger" style="padding:2px 6px;font-size:11px"
                                            onclick="CutoverView.deleteGoNoGo(${g.id})">🗑️</button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `}
            `;
        } catch(e) { c.innerHTML = `<p class="text-danger">${esc(e.message)}</p>`; }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  HYPERCARE TAB
    // ═══════════════════════════════════════════════════════════════════
    async function renderHypercareTab(c) {
        if (!_activePlan) {
            c.innerHTML = `<div class="empty-state"><div class="empty-state__icon">🏥</div>
                <div class="empty-state__title">Select a plan first</div></div>`;
            return;
        }
        c.innerHTML = `<div style="text-align:center;padding:40px"><div class="spinner"></div></div>`;

        try {
            const [incRes, slaRes, metricsRes] = await Promise.all([
                API.get(`/cutover/plans/${_activePlan.id}/incidents`),
                API.get(`/cutover/plans/${_activePlan.id}/sla-targets`),
                API.get(`/cutover/plans/${_activePlan.id}/hypercare/metrics`),
            ]);
            const incidents = incRes.items || [];
            const slaTargets = slaRes.items || [];
            const m = metricsRes;

            const slaPct = m.sla_compliance_pct !== null ? m.sla_compliance_pct + '%' : '—';
            const slaColor = m.sla_compliance_pct === null ? '#6C757D'
                : m.sla_compliance_pct >= 90 ? '#2B7D2B'
                : m.sla_compliance_pct >= 70 ? '#E78C07' : '#BB0000';

            c.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                    <strong>${esc(_activePlan.code)} Hypercare</strong>
                    <div style="display:flex;gap:8px">
                        <button class="btn btn-sm btn-secondary" onclick="CutoverView.seedSLA()">🌱 Seed SLA</button>
                        <button class="btn btn-primary btn-sm" onclick="CutoverView.showCreateIncident()">+ New Incident</button>
                    </div>
                </div>

                <!-- KPI Cards -->
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:16px">
                    <div style="background:var(--card-bg,#fff);border-radius:8px;padding:12px;box-shadow:var(--shadow,0 1px 3px rgba(0,0,0,.1));text-align:center">
                        <div style="font-size:11px;color:var(--sap-text-secondary);text-transform:uppercase">Total</div>
                        <div style="font-size:22px;font-weight:700">${m.total_incidents}</div>
                    </div>
                    <div style="background:var(--card-bg,#fff);border-radius:8px;padding:12px;box-shadow:var(--shadow,0 1px 3px rgba(0,0,0,.1));text-align:center">
                        <div style="font-size:11px;color:var(--sap-text-secondary);text-transform:uppercase">Open</div>
                        <div style="font-size:22px;font-weight:700;color:#E78C07">${m.open_incidents}</div>
                    </div>
                    <div style="background:var(--card-bg,#fff);border-radius:8px;padding:12px;box-shadow:var(--shadow,0 1px 3px rgba(0,0,0,.1));text-align:center">
                        <div style="font-size:11px;color:var(--sap-text-secondary);text-transform:uppercase">Resolved</div>
                        <div style="font-size:22px;font-weight:700;color:#2B7D2B">${m.resolved_incidents}</div>
                    </div>
                    <div style="background:var(--card-bg,#fff);border-radius:8px;padding:12px;box-shadow:var(--shadow,0 1px 3px rgba(0,0,0,.1));text-align:center">
                        <div style="font-size:11px;color:var(--sap-text-secondary);text-transform:uppercase">SLA Breach</div>
                        <div style="font-size:22px;font-weight:700;color:#BB0000">${m.sla_breached}</div>
                    </div>
                    <div style="background:${slaColor}11;border:2px solid ${slaColor};border-radius:8px;padding:12px;text-align:center">
                        <div style="font-size:11px;color:var(--sap-text-secondary);text-transform:uppercase">SLA Compliance</div>
                        <div style="font-size:22px;font-weight:700;color:${slaColor}">${slaPct}</div>
                    </div>
                </div>

                <!-- Severity Breakdown -->
                ${Object.keys(m.by_severity || {}).length > 0 ? `
                <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
                    ${['P1','P2','P3','P4'].filter(s => m.by_severity[s]).map(s => `
                        <span style="display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:12px;
                            font-size:12px;font-weight:600;background:${STATUS_COLORS[s]}15;color:${STATUS_COLORS[s]}">
                            ${s}: ${m.by_severity[s]}</span>
                    `).join('')}
                </div>` : ''}

                <!-- SLA Targets -->
                ${slaTargets.length > 0 ? `
                <details style="margin-bottom:16px">
                    <summary style="cursor:pointer;font-weight:600;font-size:13px;margin-bottom:8px">📋 SLA Targets (${slaTargets.length})</summary>
                    <table class="data-table" style="font-size:12px">
                        <thead><tr><th>Severity</th><th>Response</th><th>Resolution</th><th>Escalation</th><th>Actions</th></tr></thead>
                        <tbody>
                            ${slaTargets.map(s => `<tr>
                                <td>${badge(s.severity)}</td>
                                <td>${s.response_target_min}m</td>
                                <td>${s.resolution_target_min > 60 ? Math.round(s.resolution_target_min/60)+'h' : s.resolution_target_min+'m'}</td>
                                <td style="font-size:11px">${s.escalation_after_min ? s.escalation_after_min+'m → '+esc(s.escalation_to) : '—'}</td>
                                <td><button class="btn btn-sm btn-danger" style="padding:2px 6px;font-size:11px"
                                    onclick="CutoverView.deleteSLA(${s.id})">🗑️</button></td>
                            </tr>`).join('')}
                        </tbody>
                    </table>
                </details>` : ''}

                <!-- Incidents Table -->
                ${incidents.length === 0 ? `
                    <div class="empty-state" style="padding:24px">
                        <div class="empty-state__icon">🏥</div>
                        <div class="empty-state__title">No incidents yet</div>
                        <p>Create incidents as they arise during the hypercare window.</p>
                    </div>
                ` : `
                    <table class="data-table" style="font-size:12px">
                        <thead><tr><th>Code</th><th>Title</th><th>Severity</th><th>Category</th><th>Status</th><th>Assigned</th><th>SLA</th><th>Actions</th></tr></thead>
                        <tbody>
                            ${incidents.map(i => {
                                const sla = slaTargets.find(s => s.severity === i.severity);
                                let slaInfo = '—';
                                if (i.resolution_time_min !== null && sla) {
                                    const ok = i.resolution_time_min <= sla.resolution_target_min;
                                    slaInfo = `<span style="color:${ok?'#2B7D2B':'#BB0000'};font-weight:600">${i.resolution_time_min}m ${ok?'✓':'✗'}</span>`;
                                } else if (sla && i.status !== 'resolved' && i.status !== 'closed') {
                                    slaInfo = `<span style="color:var(--sap-text-secondary)">${sla.resolution_target_min}m target</span>`;
                                }
                                return `<tr>
                                    <td style="font-weight:600;white-space:nowrap">${esc(i.code)}</td>
                                    <td><strong>${esc(i.title)}</strong>${i.description ? '<br><span style="font-size:11px;color:var(--sap-text-secondary)">'+esc(i.description.substring(0,60))+'</span>':''}</td>
                                    <td>${badge(i.severity)}</td>
                                    <td style="text-transform:capitalize">${esc(i.category)}</td>
                                    <td>${badge(i.status)}</td>
                                    <td style="font-size:11px">${esc(i.assigned_to||'—')}</td>
                                    <td style="white-space:nowrap">${slaInfo}</td>
                                    <td style="white-space:nowrap">${renderIncidentActions(i)}</td>
                                </tr>`;
                            }).join('')}
                        </tbody>
                    </table>
                `}
            `;
        } catch(e) { c.innerHTML = `<p class="text-danger">${esc(e.message)}</p>`; }
    }

    function renderIncidentActions(i) {
        const transitions = {
            open:          ['investigating','resolved','closed'],
            investigating: ['resolved','closed'],
            resolved:      ['closed','open'],
            closed:        ['open'],
        };
        const nexts = transitions[i.status] || [];
        let btns = nexts.map(s =>
            `<button class="btn btn-sm btn-secondary" style="padding:2px 6px;font-size:11px"
                onclick="CutoverView.transitionIncident(${i.id},'${s}')">→${fmtStatus(s).substring(0,6)}</button>`
        ).join(' ');
        btns += ` <button class="btn btn-sm btn-danger" style="padding:2px 6px;font-size:11px"
            onclick="CutoverView.deleteIncident(${i.id})">🗑️</button>`;
        return btns;
    }

    // ═══════════════════════════════════════════════════════════════════
    //  MODAL HELPERS
    // ═══════════════════════════════════════════════════════════════════
    function _modal(title, body, submitFn) {
        App.openModal(`
            <div class="modal modal--lg">
                <div class="modal-header">
                    <h2>${title}</h2>
                    <button class="modal-close" onclick="App.closeModal()" title="Close">&times;</button>
                </div>
                <form id="cutoverModalForm" onsubmit="event.preventDefault();${submitFn}">
                    <div class="modal-body cutover-modal-body">
                        ${body}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                        <button type="submit" class="btn btn-primary">Save</button>
                    </div>
                </form>
            </div>
        `);

        // Keep usability parity with old modal: focus first form field.
        setTimeout(() => {
            const fi = document.querySelector('#cutoverModalForm input, #cutoverModalForm select, #cutoverModalForm textarea');
            if (fi) fi.focus();
        }, 80);
    }

    function _field(label, name, type='text', value='', extra='') {
        return `<div class="fiori-field">
            <label>${label}</label>
            <input type="${type}" name="${name}" value="${esc(value)}" placeholder="${label}" ${extra}>
        </div>`;
    }

    function _memberField(label, selectHtml, nameAttr) {
        const withName = selectHtml.replace('<select ', `<select name="${nameAttr}" `);
        return `<div class="fiori-field"><label>${label}</label>${withName}</div>`;
    }

    function _selectField(label, name, options, selected='') {
        return `<div class="fiori-field">
            <label>${label}</label>
            <select name="${name}">
                ${options.map(o => `<option value="${o[0]}" ${o[0]===selected?'selected':''}>${o[1]}</option>`).join('')}
            </select>
        </div>`;
    }

    function _textareaField(label, name, value='') {
        return `<div class="fiori-field">
            <label>${label}</label>
            <textarea name="${name}" rows="3" placeholder="${label}">${esc(value)}</textarea>
        </div>`;
    }

    function _row(...fields) {
        return `<div class="fiori-row">${fields.join('')}</div>`;
    }

    function _formData(formId='cutoverModalForm') {
        const fd = new FormData(document.getElementById(formId));
        const d = {};
        fd.forEach((v,k) => { d[k] = v; });
        return d;
    }

    // ═══════════════════════════════════════════════════════════════════
    //  CRUD ACTIONS
    // ═══════════════════════════════════════════════════════════════════

    // ── Plan ──
    async function showCreatePlan() {
        const members = await TeamMemberPicker.fetchMembers(_pid);
        const mgrHtml = TeamMemberPicker.renderSelect('cutMgr', members, '', { cssClass: '', placeholder: '— Select Manager —' });
        _modal('New Cutover Plan',
            _field('Plan Name','name','text','','required') +
            _textareaField('Description','description') +
            _row(
                _memberField('Cutover Manager', mgrHtml, 'cutover_manager_id'),
                _selectField('Environment','environment',[['PRD','PRD'],['QAS','QAS'],['Sandbox','Sandbox']])
            ) +
            _row(
                _field('Planned Start','planned_start','datetime-local'),
                _field('Planned End','planned_end','datetime-local')
            ) +
            _row(
                _field('Rollback Deadline','rollback_deadline','datetime-local'),
                _field('Rollback Decision By','rollback_decision_by')
            ),
            'CutoverView.submitCreatePlan()'
        );
    }

    async function submitCreatePlan() {
        const d = _formData();
        d.program_id = _pid;
        d.cutover_manager_id = parseInt(d.cutover_manager_id) || null;
        try {
            await API.post('/cutover/plans', d);
            App.closeModal();
            App.toast('Plan created','success');
            await loadPlans();
            _activePlan = _plans[_plans.length - 1];
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function editPlan(id) {
        const p = _plans.find(x => x.id === id);
        if (!p) return;
        const members = await TeamMemberPicker.fetchMembers(_pid);
        const mgrHtml = TeamMemberPicker.renderSelect('cutMgr', members, p.cutover_manager_id || p.cutover_manager || '', { cssClass: '', placeholder: '— Select Manager —' });
        _modal('Edit Cutover Plan',
            _field('Plan Name','name','text',p.name,'required') +
            _textareaField('Description','description',p.description||'') +
            _row(
                _memberField('Cutover Manager', mgrHtml, 'cutover_manager_id'),
                _selectField('Environment','environment',[['PRD','PRD'],['QAS','QAS'],['Sandbox','Sandbox']],p.environment)
            ) +
            _row(
                _field('Hypercare Manager','hypercare_manager','text',p.hypercare_manager||''),
                _field('Hypercare Weeks','hypercare_duration_weeks','number',p.hypercare_duration_weeks||4)
            ) +
            _field('Rollback Decision By','rollback_decision_by','text',p.rollback_decision_by||''),
            `CutoverView.submitEditPlan(${id})`
        );
    }

    async function submitEditPlan(id) {
        const d = _formData();
        d.cutover_manager_id = parseInt(d.cutover_manager_id) || null;
        try {
            await API.put(`/cutover/plans/${id}`, d);
            App.closeModal();
            App.toast('Plan updated','success');
            await loadPlans();
            _activePlan = _plans.find(p => p.id === id) || _activePlan;
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function deletePlan(id) {
        if (!confirm('Delete this cutover plan and all children?')) return;
        try {
            await API.delete(`/cutover/plans/${id}`);
            App.toast('Plan deleted','success');
            _activePlan = null;
            await loadPlans();
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function transitionPlan(id, status) {
        try {
            const res = await API.post(`/cutover/plans/${id}/transition`, { status });
            App.toast(res.message,'success');
            await loadPlans();
            _activePlan = _plans.find(p => p.id === id) || _activePlan;
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    // ── Scope Item ──
    async function showCreateScopeItem() {
        const members = await TeamMemberPicker.fetchMembers(_pid);
        const ownerHtml = TeamMemberPicker.renderSelect('siOwner', members, '', { cssClass: '', placeholder: '— Select Owner —' });
        _modal('New Scope Item',
            _field('Name','name','text','','required') +
            _row(
                _selectField('Category','category',[
                    ['data_load','Data Load'],['interface','Interface'],['authorization','Authorization'],
                    ['job_scheduling','Job Scheduling'],['reconciliation','Reconciliation'],['custom','Custom']
                ]),
                _memberField('Owner', ownerHtml, 'owner_id')
            ) +
            _textareaField('Description','description') +
            _field('Order','order','number','0'),
            'CutoverView.submitCreateScopeItem()'
        );
    }

    async function submitCreateScopeItem() {
        const d = _formData();
        d.order = parseInt(d.order) || 0;
        d.owner_id = parseInt(d.owner_id) || null;
        try {
            await API.post(`/cutover/plans/${_activePlan.id}/scope-items`, d);
            App.closeModal();
            App.toast('Scope item created','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function deleteScopeItem(id) {
        if (!confirm('Delete this scope item and all tasks?')) return;
        try {
            await API.delete(`/cutover/scope-items/${id}`);
            App.toast('Scope item deleted','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    // ── Task ──
    async function showCreateTask(siId) {
        const members = await TeamMemberPicker.fetchMembers(_pid);
        const respHtml = TeamMemberPicker.renderSelect('taskResp', members, '', { cssClass: '', placeholder: '— Select Responsible —' });
        _modal('New Runbook Task',
            _field('Title','title','text','','required') +
            _textareaField('Description','description') +
            _row(
                _field('Sequence','sequence','number','0'),
                _field('Planned Duration (min)','planned_duration_min','number')
            ) +
            _row(
                _memberField('Responsible', respHtml, 'responsible_id'),
                _field('Accountable','accountable')
            ) +
            _textareaField('Rollback Action','rollback_action') +
            _field('Notes','notes') +
            `<input type="hidden" name="_si_id" value="${siId}">`,
            'CutoverView.submitCreateTask()'
        );
    }

    async function submitCreateTask() {
        const d = _formData();
        const siId = d._si_id;
        delete d._si_id;
        d.sequence = parseInt(d.sequence) || 0;
        d.planned_duration_min = parseInt(d.planned_duration_min) || null;
        d.responsible_id = parseInt(d.responsible_id) || null;
        try {
            await API.post(`/cutover/scope-items/${siId}/tasks`, d);
            App.closeModal();
            App.toast('Task created','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function transitionTask(id, status) {
        try {
            const res = await API.post(`/cutover/tasks/${id}/transition`, { status });
            App.toast(res.message,'success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function deleteTask(id) {
        if (!confirm('Delete this task?')) return;
        try {
            await API.delete(`/cutover/tasks/${id}`);
            App.toast('Task deleted','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    // ── Rehearsal ──
    function showCreateRehearsal() {
        _modal('New Rehearsal',
            _field('Name','name','text','','required') +
            _textareaField('Description','description') +
            _row(
                _selectField('Environment','environment',[['QAS','QAS'],['PRD','PRD'],['Sandbox','Sandbox']]),
                _field('Planned Duration (min)','planned_duration_min','number')
            ),
            'CutoverView.submitCreateRehearsal()'
        );
    }

    async function submitCreateRehearsal() {
        const d = _formData();
        d.planned_duration_min = parseInt(d.planned_duration_min) || null;
        try {
            await API.post(`/cutover/plans/${_activePlan.id}/rehearsals`, d);
            App.closeModal();
            App.toast('Rehearsal created','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function transitionRehearsal(id, status) {
        try {
            const res = await API.post(`/cutover/rehearsals/${id}/transition`, { status });
            App.toast(res.message,'success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function computeMetrics(id) {
        try {
            const res = await API.post(`/cutover/rehearsals/${id}/compute-metrics`);
            App.toast('Metrics computed','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function deleteRehearsal(id) {
        if (!confirm('Delete this rehearsal?')) return;
        try {
            await API.delete(`/cutover/rehearsals/${id}`);
            App.toast('Rehearsal deleted','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    // ── Go/No-Go ──
    function showCreateGoNoGo() {
        _modal('New Go/No-Go Item',
            _field('Criterion','criterion','text','','required') +
            _textareaField('Description','description') +
            _selectField('Source Domain','source_domain',[
                ['test_management','Test Management'],['data_factory','Data Factory'],
                ['integration_factory','Integration Factory'],['security','Security'],
                ['training','Training'],['cutover_rehearsal','Cutover Rehearsal'],
                ['steering_signoff','Steering Sign-off'],['custom','Custom']
            ]) +
            _row(
                _field('Evidence','evidence'),
                _field('Evaluated By','evaluated_by')
            ),
            'CutoverView.submitCreateGoNoGo()'
        );
    }

    async function submitCreateGoNoGo() {
        const d = _formData();
        try {
            await API.post(`/cutover/plans/${_activePlan.id}/go-no-go`, d);
            App.closeModal();
            App.toast('Go/No-Go item created','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function seedGoNoGo() {
        try {
            await API.post(`/cutover/plans/${_activePlan.id}/go-no-go/seed`);
            App.toast('Default Go/No-Go items seeded','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function updateGoNoGoVerdict(id, verdict) {
        try {
            await API.put(`/cutover/go-no-go/${id}`, { verdict });
            App.toast('Verdict updated','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function deleteGoNoGo(id) {
        if (!confirm('Delete this Go/No-Go item?')) return;
        try {
            await API.delete(`/cutover/go-no-go/${id}`);
            App.toast('Item deleted','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    // ── Incident ──
    function showCreateIncident() {
        _modal('New Hypercare Incident',
            _field('Title','title','text','','required') +
            _textareaField('Description','description') +
            _row(
                _selectField('Severity','severity',[['P1','P1 — Critical'],['P2','P2 — High'],['P3','P3 — Medium'],['P4','P4 — Low']],'P3'),
                _selectField('Category','category',[
                    ['functional','Functional'],['technical','Technical'],['data','Data'],
                    ['authorization','Authorization'],['performance','Performance'],['other','Other']
                ])
            ) +
            _row(
                _field('Reported By','reported_by'),
                _field('Assigned To','assigned_to')
            ) +
            _textareaField('Notes','notes'),
            'CutoverView.submitCreateIncident()'
        );
    }

    async function submitCreateIncident() {
        const d = _formData();
        try {
            await API.post(`/cutover/plans/${_activePlan.id}/incidents`, d);
            App.closeModal();
            App.toast('Incident created','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function transitionIncident(id, status) {
        try {
            const res = await API.post(`/cutover/incidents/${id}/transition`, { status });
            App.toast(res.message,'success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function deleteIncident(id) {
        if (!confirm('Delete this incident?')) return;
        try {
            await API.delete(`/cutover/incidents/${id}`);
            App.toast('Incident deleted','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    // ── SLA ──
    async function seedSLA() {
        try {
            await API.post(`/cutover/plans/${_activePlan.id}/sla-targets/seed`);
            App.toast('SLA targets seeded','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    async function deleteSLA(id) {
        if (!confirm('Delete this SLA target?')) return;
        try {
            await API.delete(`/cutover/sla-targets/${id}`);
            App.toast('SLA target deleted','success');
            renderTab();
        } catch(e) { App.toast(e.message,'error'); }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  WAR ROOM — Cutover Clock (FDD-I03 / S5-03)
    // ═══════════════════════════════════════════════════════════════════

    let _warRoomTimer = null;

    /** Start 30-second polling for the war-room live status panel. */
    function startWarRoomPolling(planId, programId, tenantId) {
        stopWarRoomPolling();
        _refreshWarRoom(planId, programId, tenantId);
        _warRoomTimer = setInterval(
            () => _refreshWarRoom(planId, programId, tenantId),
            30_000
        );
    }

    /** Stop the 30-second war-room polling timer. */
    function stopWarRoomPolling() {
        if (_warRoomTimer) {
            clearInterval(_warRoomTimer);
            _warRoomTimer = null;
        }
    }

    /** Resolve and validate war-room scope from active plan + app tenant context. */
    function _resolveWarRoomScope() {
        if (!_activePlan) return null;
        const planId = _activePlan.id;
        const programId = Number(_activePlan.program_id) || null;
        const tenantRaw = App.currentTenantId?.() ?? _activePlan.tenant_id;
        const tenantId = Number(tenantRaw) || null;
        if (!programId || !tenantId) {
            App.toast('War-room scope missing: program_id/tenant_id is required', 'error');
            return null;
        }
        return { planId, programId, tenantId };
    }

    /** Fetch live-status snapshot and re-render the war-room panel. */
    async function _refreshWarRoom(planId, programId, tenantId) {
        try {
            const data = await API.get(
                `/cutover/plans/${planId}/live-status?program_id=${programId}&tenant_id=${tenantId}`
            );
            _renderWarRoomPanel(data);
        } catch (e) {
            console.error('War room refresh failed:', e.message);
        }
    }

    /** Render the war-room HTML panel from a live-status snapshot. */
    function _renderWarRoomPanel(snap) {
        const container = document.getElementById('warRoomPanel');
        if (!container) return;

        const clock = snap.clock || {};
        const tasks = snap.tasks || {};
        const gng   = snap.go_no_go || {};
        const ws    = snap.workstreams || {};

        const elapsed   = clock.elapsed_minutes != null ? `${clock.elapsed_minutes} min` : '--';
        const delay     = clock.total_delay_minutes > 0
            ? `<span class="badge" style="background:var(--sap-negative);color:#fff;margin-left:8px">+${clock.total_delay_minutes} min behind</span>`
            : `<span class="badge" style="background:var(--sap-positive);color:#fff;margin-left:8px">On schedule</span>`;

        // Workstream rows
        let wsRows = '';
        for (const [name, counts] of Object.entries(ws)) {
            const pct = counts.total > 0 ? Math.round((counts.completed / counts.total) * 100) : 0;
            wsRows += `
            <tr>
                <td style="text-transform:capitalize">${name}</td>
                <td>${counts.total}</td>
                <td>${counts.completed}</td>
                <td>${counts.in_progress}</td>
                <td>
                  <div style="height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden;">
                    <div style="width:${pct}%;height:100%;background:var(--sap-blue)"></div>
                  </div>
                  <small>${pct}%</small>
                </td>
            </tr>`;
        }

        // Critical path tasks
        let cpRows = '';
        for (const t of (snap.critical_path_tasks || [])) {
            const statusColor = t.status === 'completed'
                ? 'var(--sap-positive)'
                : t.status === 'in_progress'
                    ? 'var(--sap-blue)'
                    : '#6a6d70';
            const delayBadge = t.delay_minutes > 0
                ? `<span class="badge" style="background:var(--sap-negative);color:#fff;margin-left:4px">+${t.delay_minutes}m</span>`
                : '';
            const issueBadge = t.issue_note
                ? `<span class="badge" style="background:var(--sap-warning);color:#fff;margin-left:4px" title="${t.issue_note}">⚠️ Issue</span>`
                : '';
            cpRows += `
            <tr>
                <td><code>${t.code || '#'}</code></td>
                <td>${t.title}</td>
                <td><span class="badge" style="background:${statusColor};color:#fff">${t.status}</span>${delayBadge}${issueBadge}</td>
            </tr>`;
        }

        container.innerHTML = `
        <div class="card" style="margin-bottom:12px;border:1px solid ${clock.is_behind_schedule ? 'var(--sap-negative)' : 'var(--sap-positive)'};">
          <div class="card-header" style="display:flex;align-items:center;gap:8px;">
            <strong>⏱ Cutover Clock</strong>
            ${delay}
            <span style="margin-left:auto;color:var(--sap-text-secondary);font-size:12px">Auto-refresh: 30s</span>
          </div>
          <div style="padding:12px 0;display:grid;grid-template-columns:repeat(4,minmax(100px,1fr));gap:8px;text-align:center;">
            <div>
              <div style="font-size:1.5rem;font-weight:700">${elapsed}</div>
              <small class="text-muted">Elapsed</small>
            </div>
            <div>
              <div style="font-size:1.5rem;font-weight:700">${tasks.completed || 0}/${tasks.total || 0}</div>
              <small class="text-muted">Tasks Done</small>
            </div>
            <div>
              <div style="font-size:1.5rem;font-weight:700;color:var(--sap-warning)">${tasks.in_progress || 0}</div>
              <small class="text-muted">In Progress</small>
            </div>
            <div>
              <div style="font-size:1.5rem;font-weight:700;color:var(--sap-negative)">${tasks.blocked || 0}</div>
              <small class="text-muted">Blocked</small>
            </div>
          </div>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:12px">
          <div>
            <h6>Go / No-Go</h6>
            <span class="badge" style="background:var(--sap-positive);color:#fff;margin-right:4px">✅ ${gng.passed || 0} Passed</span>
            <span class="badge" style="background:var(--sap-warning);color:#fff;margin-right:4px">⏳ ${gng.pending || 0} Pending</span>
            <span class="badge" style="background:var(--sap-negative);color:#fff;margin-right:4px">❌ ${gng.failed || 0} Failed</span>
          </div>
          <div style="margin-left:auto">
            <button class="btn btn-sm btn-secondary"
              onclick="CutoverView.refreshCriticalPath()">
              Recalculate Critical Path
            </button>
          </div>
        </div>

        <h6>Workstreams</h6>
        <table class="data-table" style="font-size:13px">
          <thead><tr><th>Workstream</th><th>Total</th><th>Done</th><th>Active</th><th>Progress</th></tr></thead>
          <tbody>${wsRows || '<tr><td colspan="5" class="text-muted text-center">No workstreams assigned</td></tr>'}</tbody>
        </table>

        <h6>Critical Path Tasks</h6>
        <table class="data-table" style="font-size:13px">
          <thead><tr><th>Code</th><th>Title</th><th>Status</th></tr></thead>
          <tbody>${cpRows || '<tr><td colspan="3" class="text-muted text-center">No critical path calculated yet</td></tr>'}</tbody>
        </table>`;
    }

    /** Start the cutover clock (transition plan to executing). */
    async function startCutoverClock() {
        if (!_activePlan) { App.toast('No plan selected', 'warning'); return; }
        if (!confirm('Start the cutover clock? This transitions the plan to EXECUTING status.')) return;
        const scope = _resolveWarRoomScope();
        if (!scope) return;
        try {
            await API.post(`/cutover/plans/${scope.planId}/start-clock`, {
                program_id: scope.programId,
                tenant_id: scope.tenantId,
            });
            App.toast('Cutover clock started!', 'success');
            startWarRoomPolling(scope.planId, scope.programId, scope.tenantId);
            renderTab();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    /** Recalculate critical path for the active plan. */
    async function refreshCriticalPath() {
        if (!_activePlan) return;
        const scope = _resolveWarRoomScope();
        if (!scope) return;
        try {
            const res = await API.get(
                `/cutover/plans/${scope.planId}/critical-path?program_id=${scope.programId}&tenant_id=${scope.tenantId}`
            );
            App.toast(`Critical path: ${res.count} tasks identified`, 'success');
            _refreshWarRoom(scope.planId, scope.programId, scope.tenantId);
        } catch (e) { App.toast(e.message, 'error'); }
    }

    /** Start a runbook task from the war-room table. */
    async function startRunbookTask(taskId) {
        if (!_activePlan) return;
        const scope = _resolveWarRoomScope();
        if (!scope) return;
        try {
            await API.post(`/cutover/tasks/${taskId}/start-task`, {
                program_id: scope.programId,
                tenant_id: scope.tenantId,
            });
            App.toast('Task started', 'success');
            renderTab();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    /** Complete a runbook task from the war-room table. */
    async function completeRunbookTask(taskId) {
        if (!_activePlan) return;
        const scope = _resolveWarRoomScope();
        if (!scope) return;
        const notes = prompt('Optional completion notes:') || '';
        try {
            await API.post(`/cutover/tasks/${taskId}/complete-task`, {
                program_id: scope.programId,
                tenant_id: scope.tenantId,
                notes: notes || undefined,
            });
            App.toast('Task completed', 'success');
            renderTab();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    /** Flag an issue on a runbook task from the war-room table. */
    async function flagTaskIssue(taskId) {
        if (!_activePlan) return;
        const note = prompt('Describe the issue:');
        if (!note || !note.trim()) return;
        const scope = _resolveWarRoomScope();
        if (!scope) return;
        try {
            await API.post(`/cutover/tasks/${taskId}/flag-issue`, {
                program_id: scope.programId,
                tenant_id: scope.tenantId,
                note: note.trim(),
            });
            App.toast('Issue flagged', 'warning');
            renderTab();
        } catch (e) { App.toast(e.message, 'error'); }
    }

    // ═══════════════════════════════════════════════════════════════════
    //  PUBLIC API
    // ═══════════════════════════════════════════════════════════════════
    return {
        render,
        switchTab,
        selectPlan,
        // Plan
        showCreatePlan, submitCreatePlan,
        editPlan, submitEditPlan,
        deletePlan, transitionPlan,
        // Scope Item
        showCreateScopeItem, submitCreateScopeItem,
        deleteScopeItem,
        // Task
        showCreateTask, submitCreateTask,
        transitionTask, deleteTask,
        // Rehearsal
        showCreateRehearsal, submitCreateRehearsal,
        transitionRehearsal, computeMetrics, deleteRehearsal,
        // Go/No-Go
        showCreateGoNoGo, submitCreateGoNoGo,
        seedGoNoGo, updateGoNoGoVerdict, deleteGoNoGo,
        // Incident
        showCreateIncident, submitCreateIncident,
        transitionIncident, deleteIncident,
        // SLA
        seedSLA, deleteSLA,
        // War Room (FDD-I03)
        startCutoverClock,
        startWarRoomPolling, stopWarRoomPolling,
        refreshCriticalPath,
        startRunbookTask, completeRunbookTask, flagTaskIssue,
    };
})();
