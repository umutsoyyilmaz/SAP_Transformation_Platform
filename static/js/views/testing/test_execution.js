/**
 * SAP Transformation Management Platform
 * Test Execution View — Plans & Cycles, Test Runs, Traceability
 * Extracted from testing.js (Sprint refactor)
 */

const TestExecutionView = (() => {
    const esc = TestingShared.esc;
    let currentTab = 'queue';

    function _canonicalDefectStatus(status) {
        const normalized = String(status || '').trim().toLowerCase();
        if (normalized === 'open') return 'assigned';
        if (normalized === 'fixed') return 'resolved';
        return normalized;
    }

    function _defectStatusLabel(status) {
        const canonical = _canonicalDefectStatus(status) || 'unknown';
        return canonical.charAt(0).toUpperCase() + canonical.slice(1).replace(/_/g, ' ');
    }

    function _openConfirmModal(title, message, confirmAction, opts = {}) {
        const testId = opts.testId || 'execution-confirm-modal';
        const submitTestId = opts.submitTestId || 'execution-confirm-submit';
        const cancelTestId = opts.cancelTestId || 'execution-confirm-cancel';
        const confirmLabel = opts.confirmLabel || 'Delete';
        App.openModal(`
            <div class="modal" data-testid="${esc(testId)}">
                <div class="modal-header">
                    <h2>${esc(title)}</h2>
                    <button class="modal-close" onclick="App.closeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <p class="pg-confirm-copy">${esc(message)}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-testid="${esc(cancelTestId)}" onclick="App.closeModal()">Cancel</button>
                    <button class="btn btn-danger" data-testid="${esc(submitTestId)}" onclick="${confirmAction}">${esc(confirmLabel)}</button>
                </div>
            </div>
        `)
    }

    // State
    let testPlans = [];
    let _selectedPlanId = null;
    let _planSearch = '';
    let _planTreeFilter = 'all';
    let _planCyclesById = {};
    let _cycleDetailCache = {};
    let _cycleSignoffCache = {};
    let _executionOpsRows = [];
    let _executionOpsSummary = {};
    let _cycleRiskCache = [];
    let _retestReadinessCache = [];
    let _retestSummary = {};
    let _releaseReadinessCache = [];
    let _releaseReadinessSummary = {};
    let _tabLoadToken = 0;

    // ── Main render ───────────────────────────────────────────────────
    async function render() {
        const pid = TestingShared.getProgram();
        const main = document.getElementById('mainContent');

        if (!pid) {
            main.innerHTML = TestingShared.noProgramHtml('Test Execution');
            return;
        }

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{label:'Programs',onclick:'App.navigate("programs")'},{label:'Execution Center'}])}
                <h2 class="pg-view-title">Execution Center</h2>
            </div>
            ${TestingShared.renderModuleNav('execution-center')}
            <div class="tabs" id="testExecTabs">
                <div class="tab active" data-tab="queue" onclick="TestExecutionView.switchTab('queue')">▶ My Queue</div>
                <div class="tab" data-tab="failed" onclick="TestExecutionView.switchTab('failed')">❌ Failed</div>
                <div class="tab" data-tab="blocked" onclick="TestExecutionView.switchTab('blocked')">⛔ Blocked</div>
                <div class="tab" data-tab="retest" onclick="TestExecutionView.switchTab('retest')">🔁 Retest</div>
                <div class="tab" data-tab="plans" onclick="TestExecutionView.switchTab('plans')">📅 Plans & Cycles</div>
                <div class="tab" data-tab="traceability" onclick="TestExecutionView.switchTab('traceability')">🔗 Traceability</div>
            </div>
            <div class="card" id="testContent">
                <div class="pg-loading-state"><div class="spinner"></div></div>
            </div>
        `;
        await TestingShared.ensureOperationalPermissions();
        await loadTabData();
    }

    async function switchTab(tab) {
        currentTab = tab;
        document.querySelectorAll('#testExecTabs .tab').forEach(t => {
            t.classList.toggle('active', t.dataset.tab === tab);
        });
        if (TestingShared.getProgram()) return loadTabData();
    }

    async function loadTabData() {
        const container = document.getElementById('testContent');
        container.innerHTML = '<div class="pg-loading-state"><div class="spinner"></div></div>';
        const tab = currentTab;
        const loadToken = ++_tabLoadToken;
        try {
            switch (tab) {
                case 'queue': await renderExecutionOps('queue', loadToken); break;
                case 'failed': await renderExecutionOps('failed', loadToken); break;
                case 'blocked': await renderExecutionOps('blocked', loadToken); break;
                case 'retest': await renderExecutionOps('retest', loadToken); break;
                case 'plans': await renderPlans(); break;
                case 'traceability': await renderTraceability(); break;
            }
        } catch (e) {
            if (loadToken !== _tabLoadToken) return;
            container.innerHTML = `<div class="empty-state"><p>⚠️ ${e.message}</p></div>`;
        }
    }

    async function _loadExecutionOpsData() {
        const pid = TestingShared.getProgram();
        const payload = await API.get(`/programs/${pid}/testing/execution-center`);
        _executionOpsRows = payload?.execution_rows || [];
        _executionOpsSummary = payload?.summary || {};
        _cycleRiskCache = payload?.cycle_risk || [];
        _retestReadinessCache = payload?.retest_readiness || [];
        _retestSummary = payload?.retest_summary || {};
        _releaseReadinessCache = payload?.release_readiness || [];
        _releaseReadinessSummary = payload?.release_readiness_summary || {};
    }

    function _allExecutions() {
        return Array.isArray(_executionOpsRows) ? _executionOpsRows : [];
    }

    function _opsSummary() {
        return {
            total: 0,
            queued: 0,
            active: 0,
            failed: 0,
            blocked: 0,
            passed: 0,
            retest: _retestSummary.total || 0,
            ...(_executionOpsSummary || {}),
        };
    }

    function _filterOpsRows(mode) {
        const user = (typeof Auth !== 'undefined' && Auth.getUser) ? Auth.getUser() : null;
        const allRows = _allExecutions();
        if (mode === 'failed') return allRows.filter(r => r.result === 'fail');
        if (mode === 'blocked') return allRows.filter(r => r.result === 'blocked');
        if (mode === 'queue') {
            const mine = allRows.filter(r => {
                const actor = String(r.executed_by_id || r.executed_by || '').toLowerCase();
                const userKeys = [user?.id, user?.email, user?.full_name].filter(Boolean).map(v => String(v).toLowerCase());
                return userKeys.some(key => actor && actor.includes(key));
            });
            const queued = allRows.filter(r => !r.result || ['not_run', 'deferred'].includes(r.result));
            return mine.length ? [...mine, ...queued.filter(r => !mine.some(m => Number(m.id) === Number(r.id)))] : queued;
        }
        return allRows;
    }

    function _renderOpsKpis(mode, rows) {
        const summary = _opsSummary();
        const modeLabels = {
            queue: 'Ready or deferred executions',
            failed: 'Failures awaiting action',
            blocked: 'Blocked executions',
            retest: 'Defects waiting for retest',
        };
        return `
            <div class="exp-kpi-strip">
                ${ExpUI.kpiBlock({ value: summary.queued, label: 'Queue', accent: '#0070f2' })}
                ${ExpUI.kpiBlock({ value: summary.failed, label: 'Failed', accent: '#dc2626' })}
                ${ExpUI.kpiBlock({ value: summary.blocked, label: 'Blocked', accent: '#f59e0b' })}
                ${ExpUI.kpiBlock({ value: summary.retest, label: 'Retest Queue', accent: '#7c3aed' })}
                ${ExpUI.kpiBlock({ value: summary.passed, label: 'Passed', accent: '#107e3e' })}
            </div>
            <div class="explore-stage-nav tm-heading-reset">
                <span class="tm-muted">${modeLabels[mode] || 'Execution operations'}</span>
                ${ExpUI.actionButton({ label: 'Plans & Cycles', variant: 'secondary', size: 'sm', onclick: "TestExecutionView.switchTab('plans')" })}
                ${ExpUI.actionButton({ label: 'Traceability', variant: 'ghost', size: 'sm', onclick: "TestExecutionView.switchTab('traceability')" })}
            </div>
        `;
    }

    function _cycleRiskRows() {
        return (_cycleRiskCache || []).map((row) => ({
            cycleId: row.cycle_id,
            planId: row.plan_id,
            planName: row.plan_name,
            cycleName: row.cycle_name,
            layer: row.layer,
            failed: row.failed || 0,
            blocked: row.blocked || 0,
            pending: row.pending || 0,
            openDefects: row.open_defects || 0,
            pendingApprovals: row.pending_approvals || 0,
            approvedSignoffs: row.approved_signoffs || 0,
            pendingSignoffs: row.pending_signoffs || 0,
            readiness: row.readiness || 0,
            risk: row.risk || 'low',
            riskScore: row.risk_score || 0,
        }));
    }

    function _mergedRetestRows() {
        return [...(_retestReadinessCache || [])].sort((a, b) => Number(b.defect_id || 0) - Number(a.defect_id || 0));
    }

    function _releaseReadinessRows() {
        return [...(_releaseReadinessCache || [])];
    }

    function _releaseReadinessMeta(readiness) {
        const meta = {
            ready_now: { label: 'Ready Now', accent: '#107e3e' },
            missing_metadata: { label: 'Missing Metadata', accent: '#b45309' },
            execution_incomplete: { label: 'Execution Incomplete', accent: '#c2410c' },
            blocked_by_defects: { label: 'Blocked by Defects', accent: '#b91c1c' },
            awaiting_approval: { label: 'Awaiting Approval', accent: '#0f766e' },
            awaiting_signoff: { label: 'Awaiting Sign-off', accent: '#7c3aed' },
            missing_evidence: { label: 'Missing Evidence', accent: '#1d4ed8' },
        };
        return meta[readiness] || { label: readiness || 'Unknown', accent: '#6b7280' };
    }

    function _renderCycleRiskDashboard() {
        const riskRows = _cycleRiskRows();
        if (!riskRows.length) return '';
        return `
            <div class="exp-card tm-block--md">
                <div class="exp-card__header">Cycle Sign-off Risk & Approval Readiness</div>
                <div class="exp-card__body tm-risk-grid">
                    ${riskRows.slice(0, 6).map((row) => `
                        <div class="explore-spotlight-card tm-risk-card">
                            <div class="tm-risk-card__head">
                                <div>
                                    <div class="explore-spotlight-card__title tm-risk-card__title">${esc(row.cycleName)}</div>
                                    <div class="explore-spotlight-card__copy">${esc(row.planName)} · ${esc(String(row.layer).toUpperCase())}</div>
                                </div>
                                ${PGStatusRegistry.badge(row.risk || 'low', { label: `${String(row.risk || 'low').toUpperCase()} RISK` })}
                            </div>
                            <div class="tm-risk-card__stats">
                                <div class="exp-detail-row"><span class="exp-detail-row__label">Readiness</span><span class="exp-detail-row__value">${row.readiness}%</span></div>
                                <div class="exp-detail-row"><span class="exp-detail-row__label">Failed</span><span class="exp-detail-row__value">${row.failed}</span></div>
                                <div class="exp-detail-row"><span class="exp-detail-row__label">Blocked</span><span class="exp-detail-row__value">${row.blocked}</span></div>
                                <div class="exp-detail-row"><span class="exp-detail-row__label">Open Defects</span><span class="exp-detail-row__value">${row.openDefects}</span></div>
                                <div class="exp-detail-row"><span class="exp-detail-row__label">Pending Approvals</span><span class="exp-detail-row__value">${row.pendingApprovals}</span></div>
                                <div class="exp-detail-row"><span class="exp-detail-row__label">UAT Sign-offs</span><span class="exp-detail-row__value">${row.approvedSignoffs}/${row.approvedSignoffs + row.pendingSignoffs || 0}</span></div>
                            </div>
                            <div class="tm-risk-card__actions">
                                <button class="btn btn-sm btn-primary" onclick="TestExecutionView.viewCycleExecs(${row.cycleId})">Open Cycle</button>
                                <button class="btn btn-sm" onclick="App.navigate('signoff-approvals')">Approvals</button>
                                <button class="btn btn-sm" onclick="App.navigate('defects-retest')">Defects</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    function _renderReleaseReadinessPanel() {
        const rows = _releaseReadinessRows();
        if (!rows.length) return '';
        const summary = {
            totalCycles: _releaseReadinessSummary.total_cycles || rows.length,
            readyNow: _releaseReadinessSummary.ready_now || rows.filter((row) => row.readiness === 'ready_now').length,
            goNoGo: _releaseReadinessSummary.go_no_go_overall || 'n/a',
        };
        return `
            <div class="exp-card tm-block--md" data-testid="release-readiness-board">
                <div class="exp-card__header">Release Readiness Chain</div>
                <div class="exp-card__body" style="display:grid;gap:12px">
                    <div class="exp-detail-row">
                        <span class="exp-detail-row__label">Ready cycles / Total / Go-No-Go</span>
                        <span class="exp-detail-row__value">${summary.readyNow} / ${summary.totalCycles} / ${esc(String(summary.goNoGo).toUpperCase())}</span>
                    </div>
                    ${rows.slice(0, 6).map((row) => {
                        const meta = _releaseReadinessMeta(row.readiness);
                        const ownerLabel = row.owner || '—';
                        const envLabel = row.environment || '—';
                        const transportLabel = row.transport_request || '—';
                        const buildLabel = row.build_tag || '—';
                        const deploymentLabel = row.deployment_batch || '—';
                        return `
                            <div class="explore-spotlight-card" style="padding:14px">
                                <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">
                                    <div>
                                        <div class="explore-spotlight-card__title" style="font-size:15px">${esc(row.cycle_name || 'Cycle')}</div>
                                        <div class="explore-spotlight-card__copy">${esc(row.plan_name || 'Unplanned')} · ${esc((row.layer || '').toUpperCase())} · ${esc(envLabel)}</div>
                                    </div>
                                    <span style="font-weight:700;color:${meta.accent}">${esc(meta.label)}</span>
                                </div>
                                <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:10px">
                                    <div class="exp-detail-row"><span class="exp-detail-row__label">Owner</span><span class="exp-detail-row__value">${esc(ownerLabel)}</span></div>
                                    <div class="exp-detail-row"><span class="exp-detail-row__label">Build</span><span class="exp-detail-row__value">${esc(buildLabel)}</span></div>
                                    <div class="exp-detail-row"><span class="exp-detail-row__label">Transport</span><span class="exp-detail-row__value">${esc(transportLabel)}</span></div>
                                    <div class="exp-detail-row"><span class="exp-detail-row__label">Deploy Batch</span><span class="exp-detail-row__value">${esc(deploymentLabel)}</span></div>
                                    <div class="exp-detail-row"><span class="exp-detail-row__label">Approvals</span><span class="exp-detail-row__value">${row.pending_approvals || 0}</span></div>
                                    <div class="exp-detail-row"><span class="exp-detail-row__label">Evidence</span><span class="exp-detail-row__value">${row.evidence_count || 0}</span></div>
                                </div>
                                <div class="tm-muted tm-block">${esc(row.next_action || '')}</div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    function _renderExecutionGrid(rows) {
        if (!rows.length) {
            return `<div class="empty-state tm-empty-state-compact"><p>No items in this queue.</p></div>`;
        }
        const sorted = [...rows].sort((a, b) => {
            const aUrgency = a.result === 'fail' ? 0 : a.result === 'blocked' ? 1 : 2;
            const bUrgency = b.result === 'fail' ? 0 : b.result === 'blocked' ? 1 : 2;
            if (aUrgency !== bUrgency) return aUrgency - bUrgency;
            return Number(a.id) - Number(b.id);
        });
        return `
            <div class="tm-card tm-overflow-hidden">
                <div class="tm-data-grid__wrap">
                    <table class="tm-data-grid">
                        <thead>
                            <tr>
                                <th>Execution</th>
                                <th>Plan / Cycle</th>
                                <th>Layer</th>
                                <th>Result</th>
                                <th>Tester</th>
                                <th>Steps</th>
                                <th>Chain</th>
                                <th>Defects</th>
                                <th>Duration</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                                ${sorted.map((row) => `
                                <tr>
                                    <td><strong>#${row.id}</strong><div class="tm-muted">TC#${row.test_case_id || '-'}</div></td>
                                    <td><strong>${esc(row.plan_name || '-')}</strong><div class="tm-muted">${esc(row.cycle_name || '-')}</div></td>
                                    <td>${esc((row.test_layer || '-').toUpperCase())}</td>
                                    <td>${PGStatusRegistry.badge(row.result || 'not_run', { label: (row.result || 'not_run').replace(/_/g, ' ') })}</td>
                                    <td>${esc(row.executed_by || '-')}</td>
                                    <td>${row.step_result_count || 0}</td>
                                    <td>
                                        ${row.related_pending_approvals ? `<span class="tm-text-success tm-text-strong">${row.related_pending_approvals} approval</span>` : '<span class="tm-muted">clear</span>'}
                                    </td>
                                    <td>${row.related_open_defects ? `<span class="tm-text-danger tm-text-strong">${row.related_open_defects} open</span>` : row.related_defect_count ? `${row.related_defect_count} total` : '—'}</td>
                                    <td>${row.duration_minutes ? `${row.duration_minutes}m` : '-'}</td>
                                    <td>
                                        <button class="btn btn-sm btn-primary" onclick="TestExecutionView.openExecStepExecution(${row.id}, ${row.cycle_id})">▶ Open</button>
                                        <button class="btn btn-sm" onclick="TestExecutionView.openExecutionCase(${row.test_case_id})">TC</button>
                                        <button class="btn btn-sm" onclick="TestExecutionView.reportExecutionDefect(${row.id})">🐛</button>
                                        <button class="btn btn-sm" onclick="TestExecutionView.openExecutionEvidence(${row.id})">📎</button>
                                        ${row.related_pending_approvals ? `<button class="btn btn-sm" onclick="App.navigate('signoff-approvals')">✅</button>` : ''}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    function _renderRetestGrid() {
        const rows = _mergedRetestRows();
        if (!rows.length) return `<div class="empty-state tm-empty-state-compact"><p>No defects waiting for retest.</p></div>`;
        const readinessMeta = {
            ready_now: { label: 'Ready now', color: '#107e3e' },
            awaiting_approval: { label: 'Awaiting approval', color: '#0f766e' },
            contested: { label: 'Contested path', color: '#dc2626' },
            case_only: { label: 'Case linked only', color: '#2563eb' },
            needs_linkage: { label: 'Needs linkage', color: '#f59e0b' },
        };
        return `
            <div class="tm-card tm-overflow-hidden">
                <div class="tm-data-grid__wrap">
                    <table class="tm-data-grid">
                        <thead>
                            <tr>
                                <th>Defect</th>
                                <th>Title</th>
                                <th>Retest Readiness</th>
                                <th>Plan / Cycle</th>
                                <th>Severity</th>
                                <th>Status</th>
                                <th>Chain</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.map((row) => `
                                <tr>
                                    <td><strong>${esc(row.defect_code || `DEF-${row.defect_id}`)}</strong></td>
                                    <td>${esc(row.title || '-')}</td>
                                    <td>
                                        ${PGStatusRegistry.badge(row.readiness || 'info', { label: readinessMeta[row.readiness]?.label || row.readiness || 'Unknown' })}
                                        <div class="tm-muted tm-block">${esc(row.next_action || '')}</div>
                                    </td>
                                    <td>
                                        <strong>${esc(row.plan_name || 'Unplanned')}</strong>
                                        <div class="tm-muted">${esc(row.cycle_name || 'No cycle linked')}</div>
                                    </td>
                                    <td>${esc(row.severity || '-')}</td>
                                    <td>${PGStatusRegistry.badge(_canonicalDefectStatus(row.status || 'retest'), { label: _defectStatusLabel(row.status || 'retest') })}</td>
                                    <td>
                                        <div>${row.latest_execution_result ? `Execution: ${esc(row.latest_execution_result)}` : 'Execution: —'}</div>
                                        <div class="tm-muted">Approvals: ${row.pending_approvals || 0} · Open defects: ${row.open_defects_on_path || 0}</div>
                                    </td>
                                    <td>
                                        <button class="btn btn-sm" onclick="App.navigate('defects-retest')">Open Defect</button>
                                        ${row.execution_id && row.cycle_id ? `<button class="btn btn-sm btn-primary" onclick="TestExecutionView.openExecStepExecution(${row.execution_id}, ${row.cycle_id})">Execution</button>` : ''}
                                        ${row.cycle_id ? `<button class="btn btn-sm" onclick="TestExecutionView.viewCycleExecs(${row.cycle_id})">Cycle</button>` : ''}
                                        ${row.test_case_id ? `<button class="btn btn-sm" onclick="TestExecutionView.openExecutionCase(${row.test_case_id})">TC</button>` : ''}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    async function renderExecutionOps(mode, loadToken = null) {
        await _loadExecutionOpsData();
        if (loadToken != null && loadToken !== _tabLoadToken) return;
        const container = document.getElementById('testContent');
        const rows = _filterOpsRows(mode);
        container.innerHTML = `
            <div data-testid="execution-center-ops">
                ${_renderOpsKpis(mode, rows)}
                ${_renderCycleRiskDashboard()}
                ${_renderReleaseReadinessPanel()}
                ${mode === 'retest' ? _renderRetestGrid() : _renderExecutionGrid(rows)}
            </div>
        `;
    }

    function openExecutionCase(testCaseId) {
        if (!testCaseId) {
            App.toast('No linked test case for this record', 'warning');
            return;
        }
        if (typeof TestCaseDetailView !== 'undefined' && typeof TestCaseDetailView.open === 'function') {
            TestCaseDetailView.open(testCaseId);
            return;
        }
        App.navigate('test-case-detail', testCaseId);
    }

    async function reportExecutionDefect(execId) {
        try {
            const execution = await API.get(`/testing/executions/${execId}`);
            const defectSeed = {
                title: execution.result === 'blocked' ? `Blocked execution ${execId}` : `Failure in execution ${execId}`,
                severity: execution.result === 'blocked' ? 'S2' : 'S1',
                status: 'new',
                description: execution.notes || '',
                test_case_id: execution.test_case_id || null,
                execution_id: execution.id || execId,
                found_in_cycle_id: execution.cycle_id || null,
                reported_by: execution.executed_by || '',
            };
            App.navigate('defects-retest');
            setTimeout(() => {
                if (typeof DefectManagementView !== 'undefined' && typeof DefectManagementView.showDefectModal === 'function') {
                    DefectManagementView.showDefectModal(defectSeed);
                }
            }, 50);
        } catch (err) {
            App.toast(err.message || 'Could not load execution for defect creation', 'error');
        }
    }

    function openExecutionEvidence(execId) {
        App.navigate('evidence');
        setTimeout(() => {
            if (typeof EvidenceCaptureView !== 'undefined' && typeof EvidenceCaptureView.openForExecution === 'function') {
                EvidenceCaptureView.openForExecution(execId);
            }
        }, 50);
    }

    // ── Progress Bar ─────────────────────────────────────────────────────
    function _renderProgressBar({ total, pass, fail, blocked, not_run }) {
        const pctPass    = total ? Math.round(pass    / total * 100) : 0;
        const pctFail    = total ? Math.round(fail    / total * 100) : 0;
        const pctBlocked = total ? Math.round(blocked / total * 100) : 0;
        const pctNotRun  = total ? Math.round(not_run / total * 100) : 0;

        return `
            <div class="pg-progress-bar" title="${pass} passed · ${fail} failed · ${blocked} blocked · ${not_run} not run">
                <div class="pg-progress-bar__seg pg-progress-bar__seg--pass"    style="width:${pctPass}%"   ></div>
                <div class="pg-progress-bar__seg pg-progress-bar__seg--fail"    style="width:${pctFail}%"   ></div>
                <div class="pg-progress-bar__seg pg-progress-bar__seg--blocked" style="width:${pctBlocked}%"></div>
                <div class="pg-progress-bar__seg pg-progress-bar__seg--not-run" style="width:${pctNotRun}%" ></div>
            </div>
            <div class="pg-progress-legend">
                <span class="pg-progress-legend__item pg-progress-legend__item--pass">${pass} Passed</span>
                <span class="pg-progress-legend__item pg-progress-legend__item--fail">${fail} Failed</span>
                <span class="pg-progress-legend__item pg-progress-legend__item--blocked">${blocked} Blocked</span>
                <span class="pg-progress-legend__item pg-progress-legend__item--not-run">${not_run} Pending</span>
            </div>
        `;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // PLANS & CYCLES TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderPlans() {
        const pid = TestingShared.pid;
        const _pres = await API.get(`/programs/${pid}/testing/plans`);
        testPlans = _pres.items || _pres || [];
        const container = document.getElementById('testContent');

        if (testPlans.length === 0) {
            container.innerHTML = PGEmptyState.html({ icon: 'test', title: 'No test plans yet', description: 'Create a test plan to manage test cycles.', action: { label: '+ New Test Plan', onclick: 'TestExecutionView.showPlanModal()' } });
            return;
        }
        if (!_selectedPlanId || !testPlans.some(p => Number(p.id) === Number(_selectedPlanId))) {
            _selectedPlanId = testPlans[0]?.id || null;
        }

        const detailPairs = await Promise.all(testPlans.map(async (plan) => {
            const detail = await API.get(`/testing/plans/${plan.id}`).catch(() => ({ cycles: [] }));
            return [plan.id, detail?.cycles || []];
        }));
        _planCyclesById = Object.fromEntries(detailPairs);

        container.innerHTML = `
            <div class="tm-toolbar">
                <div class="tm-toolbar__left">
                    <button class="btn btn-primary btn-sm" onclick="TestExecutionView.showPlanModal()">+ New Test Plan</button>
                    ${_selectedPlanId ? `<button class="btn btn-sm" onclick="TestExecutionView.showCycleModal(${_selectedPlanId})">+ Cycle</button>` : ''}
                    ${_selectedPlanId ? `<button class="btn btn-sm tm-btn-analytics" onclick="TestPlanDetailView.open(${_selectedPlanId}, {from:'execution'})">📊 Detail</button>` : ''}
                </div>
                <div class="tm-toolbar__right">
                    <input class="tm-input" placeholder="Search plans…" value="${esc(_planSearch)}" oninput="TestExecutionView.setPlanSearch(this.value)">
                </div>
            </div>
            <div id="execPlansSplit"></div>
        `;

        _renderPlanSplit();
    }

    function setPlanSearch(val) {
        _planSearch = val || '';
        _renderPlanSplit();
    }

    function setPlanTreeFilter(val) {
        _planTreeFilter = val || 'all';
        _renderPlanSplit();
    }

    function selectPlan(planId) {
        _selectedPlanId = Number(planId);
        _renderPlanSplit();
    }

    async function openQuickRunCycle(planId, cycleId) {
        if (planId != null) _selectedPlanId = Number(planId);
        currentTab = 'plans';

        const tabs = document.querySelectorAll('#testExecTabs .tab');
        if (!tabs.length || !document.getElementById('testContent')) {
            await render();
        } else {
            await switchTab('plans');
        }

        if (_selectedPlanId) _renderPlanSplit();
        if (cycleId != null) await viewCycleExecs(Number(cycleId));
    }

    function _buildPlanTreeNodes(plans) {
        const statusBucket = plans.reduce((acc, plan) => {
            const key = plan.status || 'unknown';
            acc[key] = (acc[key] || 0) + 1;
            return acc;
        }, {});
        return [{ id: 'all', label: 'All Plans', count: plans.length }]
            .concat(Object.keys(statusBucket).sort().map(k => ({ id: k, label: k, count: statusBucket[k] })));
    }

    function _renderPlanSplit() {
        const shell = document.getElementById('execPlansSplit');
        if (!shell) return;

        const query = (_planSearch || '').trim().toLowerCase();
        const leftNodes = _buildPlanTreeNodes(testPlans);

        const filteredPlans = testPlans.filter(plan => {
            if (_planTreeFilter !== 'all' && (plan.status || 'unknown') !== _planTreeFilter) return false;
            if (!query) return true;
            return (plan.name || '').toLowerCase().includes(query)
                || (plan.description || '').toLowerCase().includes(query)
                || (plan.plan_type || '').toLowerCase().includes(query);
        });

        if (!_selectedPlanId || !filteredPlans.some(p => Number(p.id) === Number(_selectedPlanId))) {
            _selectedPlanId = filteredPlans[0]?.id || null;
        }

        TMSplitPane.mount(shell, {
            leftHtml: '<div id="execPlanTree"></div>',
            rightHtml: '<div id="execPlanGrid"></div>',
            leftWidth: 260,
            minLeft: 200,
            maxLeft: 420,
        });

        TMTreePanel.render(document.getElementById('execPlanTree'), {
            title: 'Plan Status',
            nodes: leftNodes,
            selectedId: _planTreeFilter,
            searchPlaceholder: 'Filter statuses…',
            onSelect: (nodeId) => setPlanTreeFilter(nodeId),
        });

        const grid = document.getElementById('execPlanGrid');
        if (!grid) return;

        if (!_selectedPlanId) {
            grid.innerHTML = '<div class="empty-state tm-empty-state-compact"><p>No plans match your filters.</p></div>';
            return;
        }

        const selectedPlan = filteredPlans.find(p => Number(p.id) === Number(_selectedPlanId));
        const cycles = _planCyclesById[_selectedPlanId] || [];

        grid.innerHTML = `
            <div class="tm-panel-head">
                <div class="tm-panel-head__title">
                    <strong>${esc(selectedPlan?.name || '')}</strong>
                    <span class="badge">${esc(selectedPlan?.status || '-')}</span>
                    <span class="tm-muted">${cycles.length} cycle(s)</span>
                </div>
                <div class="tm-panel-head__actions">
                    <button class="btn btn-sm" onclick="TestExecutionView.showCycleModal(${_selectedPlanId})">+ Cycle</button>
                    <button class="btn btn-sm btn-danger" onclick="TestExecutionView.deletePlan(${_selectedPlanId})">🗑</button>
                </div>
            </div>
            <div id="execCyclesGrid" class="tm-panel-body-pad"></div>
            <div id="execPlansListGrid" class="tm-panel-body-pad--top"></div>
        `;

        TMDataGrid.render(document.getElementById('execCyclesGrid'), {
            columns: [
                { key: 'name', label: 'Cycle', width: '28%' },
                { key: 'test_layer', label: 'Layer', width: '14%', render: row => esc((row.test_layer || '-').toUpperCase()) },
                { key: 'status', label: 'Status', width: '14%' },
                { key: 'start_date', label: 'Start', width: '14%' },
                { key: 'end_date', label: 'End', width: '14%' },
                {
                    key: 'actions',
                    label: 'Actions',
                    width: '16%',
                    render: row => `<button class="btn btn-sm btn-danger" onclick="event.stopPropagation();TestExecutionView.deleteCycle(${row.id})">🗑</button>`,
                },
            ],
            rows: cycles,
            rowKey: 'id',
            emptyText: 'No cycles yet.',
            onRowClick: (rowId) => viewCycleExecs(Number(rowId)),
        });

        TMDataGrid.render(document.getElementById('execPlansListGrid'), {
            columns: [
                { key: 'name', label: 'Plan', width: '38%' },
                { key: 'plan_type', label: 'Type', width: '14%', render: row => esc((row.plan_type || '-').toUpperCase()) },
                { key: 'status', label: 'Status', width: '14%' },
                { key: 'environment', label: 'Env', width: '14%' },
                {
                    key: 'cycle_count',
                    label: 'Cycles',
                    width: '10%',
                    align: 'right',
                    render: row => String((_planCyclesById[row.id] || []).length),
                },
                {
                    key: 'detail',
                    label: ' ',
                    width: '10%',
                    render: row => `<button class="btn btn-sm tm-btn-analytics" onclick="event.stopPropagation();TestPlanDetailView.open(${row.id}, {from:'execution'})">📊</button>`,
                },
            ],
            rows: filteredPlans,
            rowKey: 'id',
            selectedRowId: _selectedPlanId,
            emptyText: 'No plans match your filters.',
            onRowClick: (rowId) => selectPlan(Number(rowId)),
        });
    }

    function showPlanModal() {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>New Test Plan</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body tm-modal-body tm-modal-body--form">
                <div class="form-group"><label>Plan Name *</label>
                    <input id="planName" class="form-control" placeholder="e.g. SIT Master Plan"></div>
                <div class="form-group"><label>Description</label>
                    <textarea id="planDesc" class="form-control" rows="2"></textarea></div>
                <div class="form-row">
                    <div class="form-group"><label>Plan Type *</label>
                        <select id="planType" class="form-control">
                            <option value="unit">UNIT — Unit Test</option>
                            <option value="sit">SIT — System Integration Test</option>
                            <option value="uat">UAT — User Acceptance Test</option>
                            <option value="regression">Regression</option>
                            <option value="e2e">E2E — End-to-End</option>
                            <option value="cutover_rehearsal">Cutover Rehearsal</option>
                            <option value="performance">Performance</option>
                        </select></div>
                    <div class="form-group"><label>Environment</label>
                        <select id="planEnv" class="form-control">
                            <option value="">— Select —</option>
                            <option value="DEV">DEV</option>
                            <option value="QAS">QAS</option>
                            <option value="PRE">PRE-PROD</option>
                            <option value="PRD">PRD</option>
                        </select></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Start Date</label>
                        <input id="planStart" type="date" class="form-control"></div>
                    <div class="form-group"><label>End Date</label>
                        <input id="planEnd" type="date" class="form-control"></div>
                </div>
                <div class="form-group"><label>Entry Criteria</label>
                    <textarea id="planEntry" class="form-control" rows="2" placeholder="Conditions that must be met before testing begins"></textarea></div>
                <div class="form-group"><label>Exit Criteria</label>
                    <textarea id="planExit" class="form-control" rows="2" placeholder="Conditions to close this test plan"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestExecutionView.savePlan()">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function savePlan() {
        const pid = TestingShared.pid;
        const body = {
            name: document.getElementById('planName').value,
            description: document.getElementById('planDesc').value,
            plan_type: document.getElementById('planType').value,
            environment: document.getElementById('planEnv').value || null,
            start_date: document.getElementById('planStart').value || null,
            end_date: document.getElementById('planEnd').value || null,
            entry_criteria: document.getElementById('planEntry').value,
            exit_criteria: document.getElementById('planExit').value,
        };
        if (!body.name) return App.toast('Plan name is required', 'error');
        try {
            const created = await API.post(`/programs/${pid}/testing/plans`, body);
            App.toast('Test plan created! Redirecting to detail view…', 'success');
            App.closeModal();
            TestPlanDetailView.open(created.id, {from:'execution'});
        } catch (e) {
            App.toast(e.message || 'Failed to create plan', 'error');
        }
    }

    async function deletePlan(id) {
        _openConfirmModal('Delete Test Plan', 'Delete this test plan and all its cycles?', `TestExecutionView.deletePlanConfirmed(${id})`)
    }

    async function deletePlanConfirmed(id) {
        await API.delete(`/testing/plans/${id}`);
        App.closeModal();
        App.toast('Test plan deleted', 'success');
        await renderPlans();
    }

    async function showCycleModal(planId) {
        const pid = TestingShared.pid;
        const members = await TeamMemberPicker.fetchMembers(pid);
        const ownerHtml = TeamMemberPicker.renderSelect('cycleOwner', members, '', { cssClass: 'form-control', placeholder: '— Select Owner —' });
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>New Test Cycle</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body tm-modal-body tm-modal-body--form">
                <div class="form-group"><label>Name *</label>
                    <input id="cycleName" class="form-control" placeholder="e.g. SIT Cycle 1"></div>
                <div class="form-row">
                    <div class="form-group"><label>Test Layer</label>
                        <select id="cycleLayer" class="form-control">
                            ${['sit','uat','unit','regression','performance','cutover_rehearsal'].map(l =>
                                `<option value="${l}">${l.toUpperCase()}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Start Date</label>
                        <input id="cycleStart" type="date" class="form-control"></div>
                    <div class="form-group"><label>End Date</label>
                        <input id="cycleEnd" type="date" class="form-control"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Environment</label>
                        <select id="cycleEnv" class="form-control">
                            <option value="">— Select —</option>
                            <option value="DEV">DEV</option>
                            <option value="QAS">QAS</option>
                            <option value="PRE">PRE-PROD</option>
                            <option value="PRD">PRD</option>
                        </select></div>
                    <div class="form-group"><label>Build Tag</label>
                        <input id="cycleBuildTag" class="form-control" placeholder="e.g. 2026.03.12.1"></div>
                    <div class="form-group"><label>Transport Request</label>
                        <input id="cycleTransportRequest" class="form-control" placeholder="e.g. DEVK900123"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>Deployment Batch</label>
                        <input id="cycleDeploymentBatch" class="form-control" placeholder="e.g. Batch-A"></div>
                    <div class="form-group"><label>Release Train</label>
                        <input id="cycleReleaseTrain" class="form-control" placeholder="e.g. 2026-Q2"></div>
                    <div class="form-group"><label>Operational Owner</label>
                        ${ownerHtml}</div>
                </div>
                <div class="form-group"><label>Description</label>
                    <textarea id="cycleDesc" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestExecutionView.saveCycle(${planId})">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function saveCycle(planId) {
        const body = {
            name: document.getElementById('cycleName').value,
            test_layer: document.getElementById('cycleLayer').value,
            start_date: document.getElementById('cycleStart').value || null,
            end_date: document.getElementById('cycleEnd').value || null,
            environment: document.getElementById('cycleEnv').value || null,
            build_tag: document.getElementById('cycleBuildTag').value || '',
            transport_request: document.getElementById('cycleTransportRequest').value || '',
            deployment_batch: document.getElementById('cycleDeploymentBatch').value || '',
            release_train: document.getElementById('cycleReleaseTrain').value || '',
            owner_id: document.getElementById('cycleOwner')?.value ? parseInt(document.getElementById('cycleOwner').value, 10) : null,
            description: document.getElementById('cycleDesc').value,
        };
        if (!body.name) return App.toast('Name is required', 'error');
        await API.post(`/testing/plans/${planId}/cycles`, body);
        App.toast('Test cycle created', 'success');
        App.closeModal();
        await renderPlans();
    }

    async function deleteCycle(id) {
        _openConfirmModal('Delete Test Cycle', 'Delete this test cycle?', `TestExecutionView.deleteCycleConfirmed(${id})`)
    }

    async function deleteCycleConfirmed(id) {
        await API.delete(`/testing/cycles/${id}`);
        App.closeModal();
        App.toast('Test cycle deleted', 'success');
        await renderPlans();
    }

    async function viewCycleExecs(cycleId) {
        const data = await API.get(`/testing/cycles/${cycleId}`);
        const execs = data.executions || [];
        const canManageSignoff = TestingShared.canPerform('signoff_manage');
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');

        const resultBadge = (r) => PGStatusRegistry.badge(r);

        const passCount    = execs.filter(e => e.result === 'pass').length;
        const failCount    = execs.filter(e => e.result === 'fail').length;
        const blockedCount = execs.filter(e => e.result === 'blocked').length;
        const notRunCount  = execs.filter(e => !e.result || e.result === 'not_run' || e.result === 'deferred').length;

        modal.innerHTML = `
            <div class="modal-header"><h2>${data.name} — Executions</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body tm-modal-body">
                <div class="tm-inline-actions tm-inline-actions--spaced">
                    <button class="btn btn-primary btn-sm" onclick="TestExecutionView.showExecModal(${cycleId})">+ Add Execution</button>
                    <button class="btn btn-sm tm-btn-primary-solid" onclick="TestExecutionView.viewCycleRuns(${cycleId})">▶ Test Runs</button>
                </div>
                <div class="tm-meta-row tm-block">
                    <span><strong>Environment:</strong> ${esc(data.environment || '—')}</span>
                    <span><strong>Build:</strong> ${esc(data.build_tag || '—')}</span>
                    <span><strong>Transport:</strong> ${esc(data.transport_request || '—')}</span>
                    <span><strong>Deploy Batch:</strong> ${esc(data.deployment_batch || '—')}</span>
                    <span><strong>Release Train:</strong> ${esc(data.release_train || '—')}</span>
                    <span><strong>Owner:</strong> ${esc(data.owner_member?.name || '—')}</span>
                </div>
                ${execs.length > 0 ? `<div class="pg-progress-wrap">${_renderProgressBar({ total: execs.length, pass: passCount, fail: failCount, blocked: blockedCount, not_run: notRunCount })}</div>` : ''}
                ${execs.length === 0 ? '<p class="tm-empty-copy">No executions yet. Add test case executions to this cycle.</p>' : `
                <table class="data-table">
                    <thead><tr><th>Test Case</th><th>Result</th><th>Steps</th><th>Attempt</th><th>Tester</th><th>Duration</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${execs.map(e => `<tr>
                            <td>TC#${e.test_case_id}</td>
                            <td>${resultBadge(e.result)}</td>
                            <td>${e.step_result_count > 0 ? `<span class="tm-text-info">${e.step_result_count} steps</span>` : '<span class="tm-text-muted">—</span>'}</td>
                            <td>${e.attempt_number || 1}</td>
                            <td>${e.executed_by || '-'}</td>
                            <td>${e.duration_minutes ? e.duration_minutes + 'min' : '-'}</td>
                            <td>
                                <button class="btn btn-sm btn-primary" onclick="TestExecutionView.openExecStepExecution(${e.id}, ${cycleId})">▶ Execute</button>
                                <button class="btn btn-sm" onclick="TestExecutionView.showExecEditModal(${e.id}, ${cycleId})">✏️</button>
                                <button class="btn btn-sm btn-danger" onclick="TestExecutionView.deleteExec(${e.id}, ${cycleId})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}

                <!-- Entry/Exit Criteria -->
                <div class="tm-section-block">
                    <h3 class="tm-section-heading">📋 Entry / Exit Criteria</h3>
                    <div class="tm-criteria-grid">
                        <div>
                            <h4 class="tm-section-heading tm-section-heading--tight">Entry Criteria</h4>
                            <div id="entryCriteriaList_${cycleId}">
                                ${(data.entry_criteria && data.entry_criteria.length > 0)
                                    ? data.entry_criteria.map((c, i) => `
                                        <div class="tm-criteria-item">
                                            <span class="tm-criteria-icon">${c.met ? '✅' : '❌'}</span>
                                            <span class="${c.met ? 'tm-criteria-status--met' : 'tm-criteria-status--unmet'}">${esc(c.criterion || 'Unknown')}</span>
                                        </div>`).join('')
                                    : '<p class="tm-empty-copy">No entry criteria defined for this cycle.</p>'}
                            </div>
                            <div class="tm-inline-actions tm-block">
                                <button class="btn btn-sm" onclick="TestExecutionView.validateEntry(${cycleId}, false)">✓ Validate Entry</button>
                                <button class="btn btn-sm" onclick="TestExecutionView.validateEntry(${cycleId}, true)" title="Force override">⚡ Force</button>
                            </div>
                        </div>
                        <div>
                            <h4 class="tm-section-heading tm-section-heading--tight">Exit Criteria</h4>
                            <div id="exitCriteriaList_${cycleId}">
                                ${(data.exit_criteria && data.exit_criteria.length > 0)
                                    ? data.exit_criteria.map((c, i) => `
                                        <div class="tm-criteria-item">
                                            <span class="tm-criteria-icon">${c.met ? '✅' : '❌'}</span>
                                            <span class="${c.met ? 'tm-criteria-status--met' : 'tm-criteria-status--unmet'}">${esc(c.criterion || 'Unknown')}</span>
                                        </div>`).join('')
                                    : '<p class="tm-empty-copy">No exit criteria defined for this cycle.</p>'}
                            </div>
                            <div class="tm-inline-actions tm-block">
                                <button class="btn btn-sm" onclick="TestExecutionView.validateExit(${cycleId}, false)">✓ Validate Exit</button>
                                <button class="btn btn-sm" onclick="TestExecutionView.validateExit(${cycleId}, true)" title="Force override">⚡ Force</button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- UAT Sign-off -->
                <div class="tm-section-block">
                    <div class="tm-section-block__head">
                        <h3 class="tm-section-heading tm-section-heading--reset">🔏 UAT Sign-off</h3>
                        ${canManageSignoff
                            ? `<button class="btn btn-sm btn-primary" onclick="TestExecutionView.showSignoffModal(${cycleId})">+ Initiate Sign-off</button>`
                            : `<span class="tm-muted">Operational sign-off role required</span>`}
                    </div>
                    <div id="uatSignoffList_${cycleId}"><div class="spinner tm-stack-spinner"></div></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Close</button>
            </div>
        `;
        overlay.classList.add('open');
        _loadUatSignoffs(cycleId);
    }

    async function showExecModal(cycleId) {
        const pid = TestingShared.pid;
        const members = await TeamMemberPicker.fetchMembers(pid);
        const execByHtml = TeamMemberPicker.renderSelect('execBy', members, '', { cssClass: 'form-control', placeholder: '— Select Tester —' });
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>Add Test Execution</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body tm-modal-body tm-modal-body--form">
                <div class="form-group"><label>Test Case ID *</label>
                    <input id="execCaseId" class="form-control" type="number" placeholder="Test case ID"></div>
                <div class="form-group"><label>Result</label>
                    <select id="execResult" class="form-control">
                        ${['not_run','pass','fail','blocked','deferred'].map(r =>
                            `<option value="${r}">${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                    </select></div>
                <div class="form-row">
                    <div class="form-group"><label>Executed By</label>
                        ${execByHtml}</div>
                    <div class="form-group"><label>Duration (min)</label>
                        <input id="execDuration" class="form-control" type="number"></div>
                </div>
                <div class="form-group"><label>Notes</label>
                    <textarea id="execNotes" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestExecutionView.saveExec(${cycleId})">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function saveExec(cycleId) {
        const body = {
            test_case_id: parseInt(document.getElementById('execCaseId').value),
            result: document.getElementById('execResult').value,
            executed_by: TeamMemberPicker.selectedMemberName('execBy'),
            executed_by_id: document.getElementById('execBy').value ? parseInt(document.getElementById('execBy').value) : null,
            duration_minutes: parseInt(document.getElementById('execDuration').value) || null,
            notes: document.getElementById('execNotes').value,
        };
        if (!body.test_case_id) return App.toast('Test case ID is required', 'error');
        await API.post(`/testing/cycles/${cycleId}/executions`, body);
        App.toast('Execution added', 'success');
        App.closeModal();
        await viewCycleExecs(cycleId);
    }

    async function showExecEditModal(execId, cycleId) {
        const e = await API.get(`/testing/executions/${execId}`);
        const pid = TestingShared.pid;
        const members = await TeamMemberPicker.fetchMembers(pid);
        const execByHtml = TeamMemberPicker.renderSelect('execBy', members, e.executed_by_id || e.executed_by || '', { cssClass: 'form-control', placeholder: '— Select Tester —' });
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>Edit Execution</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body tm-modal-body tm-modal-body--form">
                <div class="form-group"><label>Result</label>
                    <select id="execResult" class="form-control">
                        ${['not_run','pass','fail','blocked','deferred'].map(r =>
                            `<option value="${r}" ${e.result === r ? 'selected' : ''}>${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                    </select></div>
                <div class="form-row">
                    <div class="form-group"><label>Executed By</label>
                        ${execByHtml}</div>
                    <div class="form-group"><label>Duration (min)</label>
                        <input id="execDuration" class="form-control" type="number" value="${e.duration_minutes || ''}"></div>
                </div>
                <div class="form-group"><label>Notes</label>
                    <textarea id="execNotes" class="form-control" rows="2">${e.notes || ''}</textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="TestExecutionView.updateExec(${execId}, ${cycleId})">Update</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function updateExec(execId, cycleId) {
        const body = {
            result: document.getElementById('execResult').value,
            executed_by: TeamMemberPicker.selectedMemberName('execBy'),
            executed_by_id: document.getElementById('execBy').value ? parseInt(document.getElementById('execBy').value) : null,
            duration_minutes: parseInt(document.getElementById('execDuration').value) || null,
            notes: document.getElementById('execNotes').value,
        };
        await API.put(`/testing/executions/${execId}`, body);
        App.toast('Execution updated', 'success');
        App.closeModal();
        await viewCycleExecs(cycleId);
    }

    async function deleteExec(execId, cycleId) {
        _openConfirmModal('Delete Execution', 'Delete this execution?', `TestExecutionView.deleteExecConfirmed(${execId}, ${cycleId})`)
    }

    async function deleteExecConfirmed(execId, cycleId) {
        await API.delete(`/testing/executions/${execId}`);
        App.closeModal();
        App.toast('Execution deleted', 'success');
        await viewCycleExecs(cycleId);
    }

    // ── UAT Sign-off ─────────────────────────────────────────────────────
    async function _loadUatSignoffs(cycleId) {
        try {
            const signoffs = await API.get(`/testing/cycles/${cycleId}/uat-signoffs`);
            const canManageSignoff = TestingShared.canPerform('signoff_manage');
            const el = document.getElementById(`uatSignoffList_${cycleId}`);
            if (!el) return;
            if (signoffs.length === 0) {
                el.innerHTML = '<p class="tm-empty-copy">No sign-offs initiated yet.</p>';
                return;
            }
            const statusIcon = { pending: '⏳', approved: '✅', rejected: '❌' };
            el.innerHTML = `
                <table class="data-table">
                    <thead><tr><th>Process Area</th><th>Signed By</th><th>Role</th><th>Status</th><th>Date</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${signoffs.map(s => `<tr>
                            <td>${esc(s.process_area)}</td>
                            <td>${esc(s.signed_off_by || '-')}</td>
                            <td>${esc(s.role || '-')}</td>
                            <td>${PGStatusRegistry.badge(s.status || 'pending', { label: `${statusIcon[s.status] || ''} ${s.status}`.trim() })}</td>
                            <td>${s.sign_off_date ? new Date(s.sign_off_date).toLocaleDateString() : '-'}</td>
                            <td>
                                ${canManageSignoff && s.status === 'pending' ? `
                                    <button class="btn btn-sm tm-btn-success" onclick="TestExecutionView.updateSignoff(${s.id}, 'approved', ${cycleId})">Approve</button>
                                    <button class="btn btn-sm btn-danger" onclick="TestExecutionView.updateSignoff(${s.id}, 'rejected', ${cycleId})">Reject</button>
                                ` : ''}
                                ${canManageSignoff ? `<button class="btn btn-sm btn-danger" onclick="TestExecutionView.deleteSignoff(${s.id}, ${cycleId})">🗑</button>` : '<span class="tm-muted">Locked</span>'}
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`;
        } catch(e) {
            const el = document.getElementById(`uatSignoffList_${cycleId}`);
            if (el) el.innerHTML = `<p class="tm-empty-message tm-empty-message--danger">Error: ${esc(e.message)}</p>`;
        }
    }

    function showSignoffModal(cycleId) {
        if (!TestingShared.canPerform('signoff_manage')) {
            App.toast('Operational sign-off role required', 'warning');
            return;
        }
        App.closeModal();
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>🔏 New UAT Sign-off</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body tm-modal-body tm-modal-body--form">
                <div class="form-group"><label>Process Area *</label>
                    <input id="signoffArea" class="form-control" placeholder="e.g. FI, MM, SD"></div>
                <div class="form-row">
                    <div class="form-group"><label>Signed Off By *</label>
                        <input id="signoffBy" class="form-control" placeholder="Name"></div>
                    <div class="form-group"><label>Role *</label>
                        <select id="signoffRole" class="form-control">
                            <option value="BPO">BPO</option><option value="PM">PM</option>
                        </select></div>
                </div>
                <div class="form-group"><label>Comments</label>
                    <textarea id="signoffComments" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="TestExecutionView.viewCycleExecs(${cycleId})">Cancel</button>
                <button class="btn btn-primary" onclick="TestExecutionView.createSignoff(${cycleId})">Create</button>
            </div>
        `;
        overlay.classList.add('open');
    }

    async function createSignoff(cycleId) {
        if (!TestingShared.canPerform('signoff_manage')) {
            App.toast('Operational sign-off role required', 'warning');
            return;
        }
        const body = {
            process_area: document.getElementById('signoffArea').value,
            signed_off_by: document.getElementById('signoffBy').value,
            role: document.getElementById('signoffRole').value,
            comments: document.getElementById('signoffComments').value,
        };
        if (!body.process_area || !body.signed_off_by) return App.toast('Process area and signer are required', 'error');
        try {
            await API.post(`/testing/cycles/${cycleId}/uat-signoffs`, body);
            App.toast('Sign-off initiated', 'success');
            App.closeModal();
            await viewCycleExecs(cycleId);
        } catch(e) {
            App.toast('Failed: ' + e.message, 'error');
        }
    }

    async function updateSignoff(signoffId, status, cycleId) {
        if (!TestingShared.canPerform('signoff_manage')) {
            App.toast('Operational sign-off role required', 'warning');
            return;
        }
        try {
            await API.put(`/testing/uat-signoffs/${signoffId}`, { status });
            App.toast(`Sign-off ${status}`, 'success');
            await _loadUatSignoffs(cycleId);
        } catch(e) {
            App.toast('Failed: ' + e.message, 'error');
        }
    }

    async function deleteSignoff(signoffId, cycleId) {
        if (!TestingShared.canPerform('signoff_manage')) {
            App.toast('Operational sign-off role required', 'warning');
            return;
        }
        _openConfirmModal('Delete Sign-off', 'Delete this sign-off?', `TestExecutionView.deleteSignoffConfirmed(${signoffId}, ${cycleId})`)
    }

    async function deleteSignoffConfirmed(signoffId, cycleId) {
        try {
            await API.delete(`/testing/uat-signoffs/${signoffId}`);
            App.closeModal();
            App.toast('Sign-off deleted', 'success');
            await _loadUatSignoffs(cycleId);
        } catch(e) {
            App.toast('Failed: ' + e.message, 'error');
        }
    }

    // ── Entry/Exit Criteria Validation ────────────────────────────────────
    async function validateEntry(cycleId, force) {
        try {
            const result = await API.post(`/testing/cycles/${cycleId}/validate-entry`, { force });
            if (result.valid) {
                App.toast(result.message || 'Entry criteria met — cycle started!', 'success');
                await viewCycleExecs(cycleId);
            } else {
                const unmet = result.unmet_criteria || [];
                App.toast(`Entry blocked: ${unmet.join(', ')}`, 'error');
            }
        } catch(e) {
            App.toast('Validation failed: ' + e.message, 'error');
        }
    }

    async function validateExit(cycleId, force) {
        try {
            const result = await API.post(`/testing/cycles/${cycleId}/validate-exit`, { force });
            if (result.valid) {
                App.toast(result.message || 'Exit criteria met — cycle completed!', 'success');
                await viewCycleExecs(cycleId);
            } else {
                const unmet = result.unmet_criteria || [];
                App.toast(`Exit blocked: ${unmet.join(', ')}`, 'error');
            }
        } catch(e) {
            App.toast('Validation failed: ' + e.message, 'error');
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // STEP-BY-STEP EXECUTION (ADR-FINAL: under Executions, not Runs)
    // ═══════════════════════════════════════════════════════════════════════
    async function openExecStepExecution(execId, cycleId) {
        const exe = await API.get(`/testing/executions/${execId}?include_step_results=1`);
        const stepResults = exe.step_results || [];
        let steps = [];
        try {
            const tc = await API.get(`/testing/catalog/${exe.test_case_id}`);
            steps = tc.steps || [];
        } catch(e) { /* test case may not have steps */ }

        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');

        const resultBadge = (r) => PGStatusRegistry.badge(r);

        const resultMap = {};
        stepResults.forEach(sr => { resultMap[sr.step_no] = sr; });

        let stepRowsHtml = '';
        const stepList = steps.length > 0 ? steps : [];

        if (stepList.length > 0) {
            stepRowsHtml = stepList.map((s, idx) => {
                const no = idx + 1;
                const sr = resultMap[no];
                const currentResult = sr ? sr.result : 'not_run';
                const actualResult = sr ? (sr.actual_result || '') : '';
                const notes = sr ? (sr.notes || '') : '';
                return `<tr data-step-no="${no}" data-step-id="${s.id || ''}" data-sr-id="${sr ? sr.id : ''}">
                    <td><strong>${no}</strong></td>
                    <td>${esc(s.action || s.description || '-')}</td>
                    <td>${esc(s.expected_result || '-')}</td>
                    <td>
                        <select class="form-control exec-step-result tm-step-select" data-step-no="${no}">
                            ${['not_run','pass','fail','blocked','skipped'].map(r =>
                                `<option value="${r}" ${r===currentResult?'selected':''}>${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                        </select>
                    </td>
                    <td><input class="form-control exec-step-actual tm-input-fill" value="${esc(actualResult)}" data-step-no="${no}" placeholder="Actual result..."></td>
                    <td><input class="form-control exec-step-notes tm-input-fill" value="${esc(notes)}" data-step-no="${no}" placeholder="Notes..."></td>
                </tr>`;
            }).join('');
        } else if (stepResults.length > 0) {
            stepRowsHtml = stepResults.map(sr => `<tr data-step-no="${sr.step_no}" data-sr-id="${sr.id}">
                <td><strong>${sr.step_no}</strong></td>
                <td>—</td><td>—</td>
                <td>
                    <select class="form-control exec-step-result tm-step-select" data-step-no="${sr.step_no}">
                        ${['not_run','pass','fail','blocked','skipped'].map(r =>
                            `<option value="${r}" ${r===sr.result?'selected':''}>${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                    </select>
                </td>
                <td><input class="form-control exec-step-actual tm-input-fill" value="${esc(sr.actual_result||'')}" data-step-no="${sr.step_no}"></td>
                <td><input class="form-control exec-step-notes tm-input-fill" value="${esc(sr.notes||'')}" data-step-no="${sr.step_no}"></td>
            </tr>`).join('');
        } else {
            stepRowsHtml = `<tr data-step-no="1" data-sr-id="">
                <td><strong>1</strong></td><td>—</td><td>—</td>
                <td><select class="form-control exec-step-result tm-step-select" data-step-no="1">
                    ${['not_run','pass','fail','blocked','skipped'].map(r => `<option value="${r}">${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                </select></td>
                <td><input class="form-control exec-step-actual tm-input-fill" data-step-no="1" placeholder="Actual result..."></td>
                <td><input class="form-control exec-step-notes tm-input-fill" data-step-no="1" placeholder="Notes..."></td>
            </tr>`;
        }

        modal.innerHTML = `
            <div class="modal-header">
                <h2>▶ Execution #${exe.id} — TC#${exe.test_case_id} ${resultBadge(exe.result)}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <div class="modal-body tm-modal-body-scroll tm-modal-body-scroll--execution">
                <div class="tm-meta-row">
                    <span><strong>Tester:</strong> ${exe.executed_by || '-'}</span>
                    <span><strong>Attempt:</strong> #${exe.attempt_number || 1}</span>
                    ${exe.executed_at ? `<span><strong>Executed:</strong> ${new Date(exe.executed_at).toLocaleString()}</span>` : ''}
                    ${exe.duration_minutes ? `<span><strong>Duration:</strong> ${exe.duration_minutes} min</span>` : ''}
                </div>

                <h3 class="tm-section-heading">Step-by-Step Execution</h3>
                <table class="data-table" id="execStepsTable">
                    <thead><tr><th class="tm-table-col-icon">#</th><th>Action</th><th>Expected</th><th class="tm-table-col-result">Result</th><th>Actual Result</th><th>Notes</th></tr></thead>
                    <tbody>${stepRowsHtml}</tbody>
                </table>
                <div class="tm-inline-actions tm-block--md">
                    <button class="btn btn-primary btn-sm" onclick="TestExecutionView.saveExecStepResults(${exe.id}, ${cycleId})">💾 Save & Auto-Derive Result</button>
                    <button class="btn btn-sm" onclick="TestExecutionView.addExecStepRow()">+ Add Step Row</button>
                    <button class="btn btn-sm tm-btn-success" onclick="TestExecutionView.quickSetAllSteps('pass')">✅ All Pass</button>
                    <button class="btn btn-sm tm-btn-danger-solid" onclick="TestExecutionView.quickSetAllSteps('fail')">❌ All Fail</button>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="TestExecutionView.viewCycleExecs(${cycleId})">← Back to Executions</button>
                <button class="btn" onclick="App.closeModal()">Close</button>
            </div>`;
        overlay.classList.add('open');
    }

    function addExecStepRow() {
        const tbody = document.querySelector('#execStepsTable tbody');
        if (!tbody) return;
        const rows = tbody.querySelectorAll('tr');
        const nextNo = rows.length + 1;
        const tr = document.createElement('tr');
        tr.setAttribute('data-step-no', nextNo);
        tr.setAttribute('data-sr-id', '');
        tr.innerHTML = `
            <td><strong>${nextNo}</strong></td><td>—</td><td>—</td>
            <td><select class="form-control exec-step-result tm-step-select" data-step-no="${nextNo}">
                ${['not_run','pass','fail','blocked','skipped'].map(r => `<option value="${r}">${r.replace('_',' ').toUpperCase()}</option>`).join('')}
            </select></td>
            <td><input class="form-control exec-step-actual tm-input-fill" data-step-no="${nextNo}" placeholder="Actual result..."></td>
            <td><input class="form-control exec-step-notes tm-input-fill" data-step-no="${nextNo}" placeholder="Notes..."></td>`;
        tbody.appendChild(tr);
    }

    function quickSetAllSteps(result) {
        document.querySelectorAll('#execStepsTable .exec-step-result').forEach(sel => {
            sel.value = result;
        });
    }

    async function saveExecStepResults(execId, cycleId) {
        const rows = document.querySelectorAll('#execStepsTable tbody tr');
        for (const row of rows) {
            const stepNo = parseInt(row.dataset.stepNo);
            const srId = row.dataset.srId;
            const stepId = row.dataset.stepId || null;
            const result = row.querySelector('.exec-step-result')?.value || 'not_run';
            const actualResult = row.querySelector('.exec-step-actual')?.value || '';
            const notes = row.querySelector('.exec-step-notes')?.value || '';

            const body = {
                step_no: stepNo,
                result: result,
                actual_result: actualResult,
                notes: notes,
            };
            if (stepId) body.step_id = parseInt(stepId);

            if (srId) {
                await API.put(`/testing/step-results/${srId}`, body);
            } else {
                const created = await API.post(`/testing/executions/${execId}/step-results`, body);
                row.dataset.srId = created.id;
            }
        }

        // Auto-derive execution result from step results (ADR-FINAL)
        try {
            await API.post(`/testing/executions/${execId}/derive-result`);
        } catch(e) { /* ignore */ }

        App.toast('Step results saved — result auto-derived', 'success');
        await openExecStepExecution(execId, cycleId);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TEST RUNS (Optional metadata — ADR-FINAL)
    // ═══════════════════════════════════════════════════════════════════════
    async function viewCycleRuns(cycleId) {
        const _rres = await API.get(`/testing/cycles/${cycleId}/runs`);
        const runs = _rres.items || _rres || [];
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');

        const statusBadge = (s) => PGStatusRegistry.badge(s, { label: (s || '').replace(/_/g, ' ') });
        const resultBadge = (r) => PGStatusRegistry.badge(r);

        modal.innerHTML = `
            <div class="modal-header"><h2>Test Runs — Cycle #${cycleId}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body tm-modal-body">
                <div class="tm-inline-actions tm-inline-actions--spaced">
                    <button class="btn btn-primary btn-sm" onclick="TestExecutionView.showNewRunModal(${cycleId})">+ New Run</button>
                    <button class="btn btn-sm" onclick="TestExecutionView.viewCycleExecs(${cycleId})">← Back to Executions</button>
                </div>
                ${runs.length === 0 ? '<p class="tm-empty-copy">No test runs yet. Start a new run to begin step-by-step execution.</p>' : `
                <table class="data-table">
                    <thead><tr><th>Run</th><th>Test Case</th><th>Type</th><th>Status</th><th>Result</th><th>Tester</th><th>Environment</th><th>Actions</th></tr></thead>
                    <tbody>
                        ${runs.map(r => `<tr>
                            <td>#${r.id}</td>
                            <td>TC#${r.test_case_id}</td>
                            <td>${r.run_type || 'manual'}</td>
                            <td>${statusBadge(r.status)}</td>
                            <td>${resultBadge(r.result)}</td>
                            <td>${r.tester || '-'}</td>
                            <td>${r.environment || '-'}</td>
                            <td>
                                <button class="btn btn-sm btn-primary" onclick="TestExecutionView.openRunExecution(${r.id}, ${cycleId})">▶ Execute</button>
                                <button class="btn btn-sm btn-danger" onclick="TestExecutionView.deleteRun(${r.id}, ${cycleId})">🗑</button>
                            </td>
                        </tr>`).join('')}
                    </tbody>
                </table>`}
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="App.closeModal()">Close</button>
            </div>`;
        overlay.classList.add('open');
    }

    function showNewRunModal(cycleId) {
        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');
        modal.innerHTML = `
            <div class="modal-header"><h2>New Test Run</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button></div>
            <div class="modal-body tm-modal-body tm-modal-body--form">
                <div class="form-group"><label>Test Case ID *</label>
                    <input id="runCaseId" class="form-control" type="number" placeholder="Test case ID"></div>
                <div class="form-row">
                    <div class="form-group"><label>Run Type</label>
                        <select id="runType" class="form-control">
                            ${['manual','automated','exploratory'].map(t =>
                                `<option value="${t}">${t.charAt(0).toUpperCase()+t.slice(1)}</option>`).join('')}
                        </select></div>
                    <div class="form-group"><label>Tester</label>
                        <input id="runTester" class="form-control" placeholder="Tester name"></div>
                    <div class="form-group"><label>Environment</label>
                        <input id="runEnv" class="form-control" placeholder="DEV / QAS / PRD"></div>
                </div>
                <div class="form-group"><label>Notes</label>
                    <textarea id="runNotes" class="form-control" rows="2"></textarea></div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="TestExecutionView.viewCycleRuns(${cycleId})">Cancel</button>
                <button class="btn btn-primary" onclick="TestExecutionView.saveNewRun(${cycleId})">Create & Open</button>
            </div>`;
        overlay.classList.add('open');
    }

    async function saveNewRun(cycleId) {
        const body = {
            test_case_id: parseInt(document.getElementById('runCaseId').value),
            run_type: document.getElementById('runType').value,
            tester: document.getElementById('runTester').value || null,
            environment: document.getElementById('runEnv').value || null,
            notes: document.getElementById('runNotes').value || null,
        };
        if (!body.test_case_id) return App.toast('Test Case ID is required', 'error');
        const run = await API.post(`/testing/cycles/${cycleId}/runs`, body);
        App.toast('Run created', 'success');
        await openRunExecution(run.id, cycleId);
    }

    async function openRunExecution(runId, cycleId) {
        const run = await API.get(`/testing/runs/${runId}`);
        const stepResults = await API.get(`/testing/runs/${runId}/step-results`);
        let steps = [];
        try {
            const tc = await API.get(`/testing/catalog/${run.test_case_id}`);
            steps = tc.steps || [];
        } catch(e) { /* test case may not have steps */ }

        const overlay = document.getElementById('modalOverlay');
        const modal = document.getElementById('modalContainer');

        const statusBadge = (s) => PGStatusRegistry.badge(s || 'not_started', { label: (s || 'not_started').replace(/_/g, ' ') });
        const resultBadge = (r) => PGStatusRegistry.badge(r || 'not_run');

        const resultMap = {};
        stepResults.forEach(sr => { resultMap[sr.step_no] = sr; });

        let stepRowsHtml = '';
        const stepList = steps.length > 0 ? steps : [];

        if (stepList.length > 0) {
            stepRowsHtml = stepList.map((s, idx) => {
                const no = idx + 1;
                const sr = resultMap[no];
                const currentResult = sr ? sr.result : 'not_run';
                const actualResult = sr ? (sr.actual_result || '') : '';
                const notes = sr ? (sr.notes || '') : '';
                return `<tr data-step-no="${no}" data-step-id="${s.id || ''}" data-sr-id="${sr ? sr.id : ''}">
                    <td><strong>${no}</strong></td>
                    <td>${esc(s.action || s.description || '-')}</td>
                    <td>${esc(s.expected_result || '-')}</td>
                    <td>
                        <select class="form-control run-step-result tm-step-select--run" data-step-no="${no}">
                            ${['not_run','pass','fail','blocked','skipped'].map(r =>
                                `<option value="${r}" ${r===currentResult?'selected':''}>${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                        </select>
                    </td>
                    <td><input class="form-control run-step-actual tm-input-fill" value="${esc(actualResult)}" data-step-no="${no}" placeholder="Actual result..."></td>
                    <td><input class="form-control run-step-notes tm-input-fill" value="${esc(notes)}" data-step-no="${no}" placeholder="Notes..."></td>
                </tr>`;
            }).join('');
        } else {
            if (stepResults.length > 0) {
                stepRowsHtml = stepResults.map(sr => `<tr data-step-no="${sr.step_no}" data-sr-id="${sr.id}">
                    <td><strong>${sr.step_no}</strong></td>
                    <td>—</td><td>—</td>
                    <td>
                        <select class="form-control run-step-result tm-step-select--run" data-step-no="${sr.step_no}">
                            ${['not_run','pass','fail','blocked','skipped'].map(r =>
                                `<option value="${r}" ${r===sr.result?'selected':''}>${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                        </select>
                    </td>
                    <td><input class="form-control run-step-actual tm-input-fill" value="${esc(sr.actual_result||'')}" data-step-no="${sr.step_no}"></td>
                    <td><input class="form-control run-step-notes tm-input-fill" value="${esc(sr.notes||'')}" data-step-no="${sr.step_no}"></td>
                </tr>`).join('');
            } else {
                stepRowsHtml = `<tr data-step-no="1" data-sr-id="">
                    <td><strong>1</strong></td><td>—</td><td>—</td>
                    <td><select class="form-control run-step-result tm-step-select--run" data-step-no="1">
                        ${['not_run','pass','fail','blocked','skipped'].map(r => `<option value="${r}">${r.replace('_',' ').toUpperCase()}</option>`).join('')}
                    </select></td>
                    <td><input class="form-control run-step-actual tm-input-fill" data-step-no="1" placeholder="Actual result..."></td>
                    <td><input class="form-control run-step-notes tm-input-fill" data-step-no="1" placeholder="Notes..."></td>
                </tr>`;
            }
        }

        modal.innerHTML = `
            <div class="modal-header">
                <h2>▶ Run #${run.id} — TC#${run.test_case_id} ${statusBadge(run.status)} ${resultBadge(run.result)}</h2>
                <button class="modal-close" onclick="App.closeModal()">&times;</button>
            </div>
            <div class="modal-body tm-modal-body-scroll tm-modal-body-scroll--execution">
                <div class="tm-meta-row">
                    <span><strong>Type:</strong> ${run.run_type || 'manual'}</span>
                    <span><strong>Tester:</strong> ${run.tester || '-'}</span>
                    <span><strong>Environment:</strong> ${run.environment || '-'}</span>
                    ${run.started_at ? `<span><strong>Started:</strong> ${new Date(run.started_at).toLocaleString()}</span>` : ''}
                    ${run.finished_at ? `<span><strong>Finished:</strong> ${new Date(run.finished_at).toLocaleString()}</span>` : ''}
                </div>

                <div class="tm-inline-actions tm-inline-actions--lg">
                    ${run.status === 'not_started' ? `<button class="btn btn-primary btn-sm" onclick="TestExecutionView.updateRunStatus(${run.id}, ${cycleId}, 'in_progress')">▶ Start Run</button>` : ''}
                    ${run.status === 'in_progress' ? `
                        <button class="btn btn-sm tm-btn-success" onclick="TestExecutionView.completeRun(${run.id}, ${cycleId}, 'pass')">✅ Complete (Pass)</button>
                        <button class="btn btn-sm tm-btn-danger-solid" onclick="TestExecutionView.completeRun(${run.id}, ${cycleId}, 'fail')">❌ Complete (Fail)</button>
                        <button class="btn btn-sm" onclick="TestExecutionView.updateRunStatus(${run.id}, ${cycleId}, 'aborted')">⛔ Abort</button>
                    ` : ''}
                    ${run.status === 'completed' || run.status === 'aborted' ? `<span class="tm-inline-helper tm-inline-helper--muted">Run is ${run.status}</span>` : ''}
                </div>

                <h3 class="tm-section-heading">Step Results</h3>
                <table class="data-table" id="runStepsTable">
                    <thead><tr><th>#</th><th>Action</th><th>Expected</th><th class="tm-table-col-result">Result</th><th>Actual Result</th><th>Notes</th></tr></thead>
                    <tbody>${stepRowsHtml}</tbody>
                </table>
                <div class="tm-inline-actions tm-block--md">
                    <button class="btn btn-primary btn-sm" onclick="TestExecutionView.saveStepResults(${run.id}, ${cycleId})">💾 Save Step Results</button>
                    <button class="btn btn-sm" onclick="TestExecutionView.addStepResultRow()">+ Add Step Row</button>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="TestExecutionView.viewCycleRuns(${cycleId})">← Back to Runs</button>
                <button class="btn" onclick="App.closeModal()">Close</button>
            </div>`;
        overlay.classList.add('open');
    }

    function addStepResultRow() {
        const tbody = document.querySelector('#runStepsTable tbody');
        if (!tbody) return;
        const rows = tbody.querySelectorAll('tr');
        const nextNo = rows.length + 1;
        const tr = document.createElement('tr');
        tr.setAttribute('data-step-no', nextNo);
        tr.setAttribute('data-sr-id', '');
        tr.innerHTML = `
            <td><strong>${nextNo}</strong></td><td>—</td><td>—</td>
            <td><select class="form-control run-step-result tm-step-select--run" data-step-no="${nextNo}">
                ${['not_run','pass','fail','blocked','skipped'].map(r => `<option value="${r}">${r.replace('_',' ').toUpperCase()}</option>`).join('')}
            </select></td>
            <td><input class="form-control run-step-actual tm-input-fill" data-step-no="${nextNo}" placeholder="Actual result..."></td>
            <td><input class="form-control run-step-notes tm-input-fill" data-step-no="${nextNo}" placeholder="Notes..."></td>`;
        tbody.appendChild(tr);
    }

    async function saveStepResults(runId, cycleId) {
        const rows = document.querySelectorAll('#runStepsTable tbody tr');
        for (const row of rows) {
            const stepNo = parseInt(row.dataset.stepNo);
            const srId = row.dataset.srId;
            const stepId = row.dataset.stepId || null;
            const result = row.querySelector('.run-step-result')?.value || 'not_run';
            const actualResult = row.querySelector('.run-step-actual')?.value || '';
            const notes = row.querySelector('.run-step-notes')?.value || '';

            const body = {
                step_no: stepNo,
                result: result,
                actual_result: actualResult,
                notes: notes,
            };
            if (stepId) body.step_id = stepId;

            if (srId) {
                await API.put(`/testing/step-results/${srId}`, body);
            } else {
                const created = await API.post(`/testing/runs/${runId}/step-results`, body);
                row.dataset.srId = created.id;
            }
        }
        App.toast('Step results saved', 'success');
        await openRunExecution(runId, cycleId);
    }

    async function updateRunStatus(runId, cycleId, status) {
        await API.put(`/testing/runs/${runId}`, { status });
        App.toast(`Run status → ${status}`, 'success');
        await openRunExecution(runId, cycleId);
    }

    async function completeRun(runId, cycleId, result) {
        await API.put(`/testing/runs/${runId}`, { status: 'completed', result });
        App.toast(`Run completed — ${result}`, 'success');
        await openRunExecution(runId, cycleId);
    }

    async function deleteRun(runId, cycleId) {
        _openConfirmModal('Delete Test Run', 'Delete this test run?', `TestExecutionView.deleteRunConfirmed(${runId}, ${cycleId})`)
    }

    async function deleteRunConfirmed(runId, cycleId) {
        await API.delete(`/testing/runs/${runId}`);
        App.closeModal();
        App.toast('Run deleted', 'success');
        await viewCycleRuns(cycleId);
    }

    // ═══════════════════════════════════════════════════════════════════════
    // TRACEABILITY MATRIX TAB
    // ═══════════════════════════════════════════════════════════════════════
    async function renderTraceability() {
        const pid = TestingShared.pid;
        const data = await API.get(`/programs/${pid}/testing/traceability-matrix`);
        const container = document.getElementById('testContent');
        const s = data.summary;

        let html = `
            <div class="tm-kpi-row">
                <div class="kpi-card"><div class="kpi-value">${s.total_requirements}</div><div class="kpi-label">Requirements</div></div>
                <div class="kpi-card"><div class="kpi-value">${s.requirements_with_tests}</div><div class="kpi-label">With Tests</div></div>
                <div class="kpi-card"><div class="kpi-value ${s.coverage_pct >= 80 ? 'tm-kpi-value--success' : 'tm-kpi-value--danger'}">${s.coverage_pct}%</div><div class="kpi-label">Coverage</div></div>
                <div class="kpi-card"><div class="kpi-value">${s.total_test_cases}</div><div class="kpi-label">Test Cases</div></div>
                <div class="kpi-card"><div class="kpi-value">${s.total_defects}</div><div class="kpi-label">Defects</div></div>
            </div>
        `;

        if (data.matrix.length === 0) {
            html += '<div class="empty-state"><p>No requirements found.</p></div>';
        } else {
            html += `
                <table class="data-table">
                    <thead><tr>
                        <th>Requirement</th><th>Priority</th><th>Test Cases</th><th>Defects</th><th>Status</th>${typeof TraceChain !== 'undefined' ? '<th>Trace</th>' : ''}
                    </tr></thead>
                    <tbody>
                        ${data.matrix.map(row => {
                            const r = row.requirement;
                            const hasTests = row.total_test_cases > 0;
                            const hasDefects = row.total_defects > 0;
                            const traceBtn = typeof TraceChain !== 'undefined' ? `<td><button class="btn btn-sm tm-trace-btn" onclick="TraceChain.show('backlog_item', ${r.id})">🔍</button></td>` : '';
                            return `<tr>
                                <td><strong>${r.code || '-'}</strong> ${r.title}</td>
                                <td>${r.priority || '-'}</td>
                                <td>${hasTests ? `<span class="tm-text-success">${row.total_test_cases} case(s)</span>` : '<span class="tm-text-danger">—</span>'}</td>
                                <td>${hasDefects ? `<span class="tm-text-danger">${row.total_defects} defect(s)</span>` : '<span class="tm-text-success">Clean</span>'}</td>
                                <td>${hasTests ? '✅ Covered' : '⚠️ Uncovered'}</td>
                                ${traceBtn}
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>`;
        }
        container.innerHTML = html;
    }

    // ── Go/No-Go Scorecard ───────────────────────────────────────────────
    async function loadGoNoGo() {
        const pid = TestingShared.pid;
        try {
            const data = await API.get(`/programs/${pid}/testing/dashboard/go-no-go`);
            const el = document.getElementById('goNoGoContent');
            if (!el) return;
            const overallColor = data.overall === 'go' ? '#107e3e' : '#c4314b';
            const overallText = data.overall === 'go' ? '✅ GO' : '🛑 NO-GO';

            el.innerHTML = `
                <div class="tm-score-banner ${data.overall === 'go' ? 'tm-score-banner--go' : 'tm-score-banner--no-go'}">
                    <div class="tm-score-banner__value ${data.overall === 'go' ? 'tm-kpi-value--success' : 'tm-kpi-value--danger'}">${overallText}</div>
                    <div class="tm-inline-helper tm-inline-helper--muted">${data.green_count} green · ${data.yellow_count} yellow · ${data.red_count} red</div>
                </div>
                <table class="data-table">
                    <thead><tr><th>Criterion</th><th>Target</th><th>Actual</th><th>Status</th></tr></thead>
                    <tbody>
                        ${data.scorecard.map(s => {
                            const si = { green: '✅', yellow: '⚠️', red: '❌' };
                            return `<tr class="tm-score-row--${s.status}">
                                <td><strong>${esc(s.criterion)}</strong></td>
                                <td>${esc(s.target)}</td>
                                <td><strong>${typeof s.actual === 'number' ? (s.actual % 1 === 0 ? s.actual : s.actual + '%') : s.actual}</strong></td>
                                <td>${si[s.status]} ${PGStatusRegistry.badge(s.status || 'red', { label: String(s.status || 'red').toUpperCase() })}</td>
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>`;
        } catch(e) {
            const el = document.getElementById('goNoGoContent');
            if (el) el.innerHTML = `<p class="tm-empty-message tm-empty-message--danger">Error loading scorecard: ${esc(e.message)}</p>`;
        }
    }

    // ── Daily Snapshots ──────────────────────────────────────────────────
    async function loadSnapshots() {
        const pid = TestingShared.pid;
        try {
            const snapshots = await API.get(`/programs/${pid}/testing/snapshots`);
            const el = document.getElementById('snapshotsContent');
            if (!el) return;
            if (snapshots.length === 0) {
                el.innerHTML = '<p class="tm-empty-copy tm-empty-copy--center">No snapshots yet. Click "Capture Snapshot" to take the first one.</p>';
                return;
            }
            el.innerHTML = `
                <table class="data-table">
                    <thead><tr><th>Date</th><th>Total</th><th>Passed</th><th>Failed</th><th>Blocked</th><th>Pass Rate</th><th>Open Defects</th></tr></thead>
                    <tbody>
                        ${snapshots.slice(0, 14).map(s => {
                            const total = s.passed + s.failed + s.blocked + s.not_run;
                            const pr = total > 0 ? Math.round(s.passed / total * 100) : 0;
                            const openDef = (s.open_defects_s1 || 0) + (s.open_defects_s2 || 0) + (s.open_defects_s3 || 0) + (s.open_defects_s4 || 0);
                            return `<tr>
                                <td>${s.snapshot_date}</td>
                                <td>${s.total_cases}</td>
                                <td class="tm-cell-pass">${s.passed}</td>
                                <td class="tm-cell-fail">${s.failed}</td>
                                <td class="tm-cell-blocked">${s.blocked}</td>
                                <td><strong class="${pr >= 80 ? 'tm-kpi-value--success' : 'tm-kpi-value--danger'}">${pr}%</strong></td>
                                <td>${openDef}</td>
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>`;

            _renderSnapshotChart(snapshots.slice(0, 30).reverse());
        } catch(e) {
            const el = document.getElementById('snapshotsContent');
            if (el) el.innerHTML = `<p class="tm-empty-message tm-empty-message--danger">Error loading snapshots: ${esc(e.message)}</p>`;
        }
    }

    function _renderSnapshotChart(snapshots) {
        const ctx = document.getElementById('chartSnapshots');
        if (!ctx || !snapshots.length) return;
        const labels = snapshots.map(s => s.snapshot_date);
        const passRates = snapshots.map(s => {
            const total = s.passed + s.failed + s.blocked + s.not_run;
            return total > 0 ? Math.round(s.passed / total * 100) : 0;
        });
        const openDefs = snapshots.map(s =>
            (s.open_defects_s1 || 0) + (s.open_defects_s2 || 0) + (s.open_defects_s3 || 0) + (s.open_defects_s4 || 0));

        new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Pass Rate %', data: passRates, borderColor: '#107e3e', backgroundColor: 'rgba(16,126,62,0.1)', fill: true, yAxisID: 'y', tension: 0.3 },
                    { label: 'Open Defects', data: openDefs, borderColor: '#c4314b', backgroundColor: 'rgba(196,49,75,0.1)', fill: false, yAxisID: 'y1', tension: 0.3 },
                ],
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, max: 100, position: 'left', title: { display: true, text: 'Pass Rate %' } },
                    y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Open Defects' } },
                },
                plugins: { legend: { position: 'bottom' } },
            },
        });
    }

    async function captureSnapshot() {
        const pid = TestingShared.pid;
        try {
            await API.post(`/programs/${pid}/testing/snapshots`, {});
            App.toast('Snapshot captured', 'success');
            await loadSnapshots();
        } catch(e) {
            App.toast('Failed to capture snapshot: ' + e.message, 'error');
        }
    }

    // ── Public API ─────────────────────────────────────────────────────────
    return {
        render,
        switchTab,
        setPlanSearch,
        setPlanTreeFilter,
        selectPlan,
        openQuickRunCycle,
        openExecutionEvidence,
        // Plans & Cycles
        showPlanModal, savePlan, deletePlan, deletePlanConfirmed,
        showCycleModal, saveCycle, deleteCycle, deleteCycleConfirmed,
        viewCycleExecs, showExecModal, saveExec, showExecEditModal, updateExec, deleteExec, deleteExecConfirmed,
        // Step-by-step execution (ADR-FINAL: under Executions)
        openExecStepExecution, addExecStepRow, quickSetAllSteps, saveExecStepResults,
        // Runs (optional metadata)
        viewCycleRuns, showNewRunModal, saveNewRun, openRunExecution,
        addStepResultRow, saveStepResults, updateRunStatus, completeRun, deleteRun, deleteRunConfirmed,
        // Sign-off & Criteria
        showSignoffModal, createSignoff, updateSignoff, deleteSignoff, deleteSignoffConfirmed,
        validateEntry, validateExit,
        // Go/No-Go & Snapshots
        loadGoNoGo, loadSnapshots, captureSnapshot,
    };
})();
