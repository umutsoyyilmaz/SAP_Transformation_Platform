/**
 * F3 — Approval Inbox & Workflow Management View.
 *
 * Provides:
 *  - "My Pending Approvals" inbox
 *  - Approval / Reject actions with comments
 *  - Approval status banner component (reusable)
 */
const ApprovalsView = (function () {
    'use strict';

    const _esc = (s) => {
        const d = document.createElement('div');
        d.textContent = s ?? '';
        return d.innerHTML;
    };

    let _pendingRecords = [];
    let _tab = 'pending'; // pending | workflows

    // ── Data loading ────────────────────────────────────────────────────

    async function _loadPending() {
        const pid = App.activeProgramId;
        const url = pid
            ? `/api/v1/approvals/pending?program_id=${pid}`
            : '/api/v1/approvals/pending';
        _pendingRecords = await API.get(url).catch(() => []);
    }

    // ── Render ──────────────────────────────────────────────────────────

    async function render() {
        const main = document.getElementById('mainContent');
        if (!main) return;
        main.innerHTML = '<div class="spinner"></div>';

        await _loadPending();

        main.innerHTML = `
            <div style="max-width:960px;margin:0 auto;padding:var(--sp-md)">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--sp-md)">
                    <h2 style="margin:0;font-size:var(--tm-font-lg, 16px)">✅ Approval Inbox</h2>
                    <span class="tm-badge" style="background:var(--tm-info-light, #e8f0fe);color:var(--tm-info, #174ea6)">
                        ${_pendingRecords.length} pending
                    </span>
                </div>

                <div id="approvalTabBar" style="margin-bottom:var(--sp-md)"></div>
                <div id="approvalContent"></div>
            </div>
        `;

        TMTabBar.render(document.getElementById('approvalTabBar'), {
            tabs: [
                { id: 'pending', label: 'Pending', icon: '⏳' },
                { id: 'history', label: 'History', icon: '📜' },
            ],
            active: _tab,
            onSwitch: (id) => { _tab = id; _renderTab(); },
        });

        _renderTab();
    }

    function _renderTab() {
        const el = document.getElementById('approvalContent');
        if (!el) return;

        if (_tab === 'pending') {
            _renderPending(el);
        } else {
            _renderHistory(el);
        }
    }

    function _renderPending(el) {
        if (_pendingRecords.length === 0) {
            el.innerHTML = `
                <div class="tm-card" style="padding:var(--sp-lg);text-align:center">
                    <div style="font-size:40px;margin-bottom:var(--sp-sm)">🎉</div>
                    <p class="tm-muted">No pending approvals. You're all caught up!</p>
                </div>`;
            return;
        }

        el.innerHTML = '<div id="approvalGrid"></div>';
        TMDataGrid.render(document.getElementById('approvalGrid'), {
            columns: [
                { key: 'entity_type', label: 'Type', width: '100px', render: (r) => `<span class="tm-badge">${_esc(r.entity_type)}</span>` },
                { key: 'entity_id', label: 'Entity ID', width: '80px', render: (r) => `#${r.entity_id}` },
                { key: 'workflow_name', label: 'Workflow', width: '160px' },
                { key: 'stage', label: 'Stage', width: '60px', render: (r) => `L${r.stage}` },
                { key: 'stage_role', label: 'Role', width: '120px' },
                { key: 'created_at', label: 'Submitted', width: '140px', render: (r) => _esc((r.created_at || '').slice(0, 16)) },
                { key: '_actions', label: 'Actions', width: '180px', render: (r) => `
                    <button class="tm-toolbar__btn tm-toolbar__btn--primary" style="font-size:11px" onclick="ApprovalsView.decide(${r.id}, 'approved')">✓ Approve</button>
                    <button class="tm-toolbar__btn" style="font-size:11px;color:var(--tm-fail)" onclick="ApprovalsView.decide(${r.id}, 'rejected')">✗ Reject</button>
                ` },
            ],
            rows: _pendingRecords,
        });
    }

    async function _renderHistory(el) {
        // Load all records (not just pending) for the current program
        const pid = App.activeProgramId;
        let url = '/api/v1/approvals/pending'; // fallback
        // We'll fetch history via entity status endpoint—since there's no "all records" endpoint,
        // we show a summary based on pending count
        el.innerHTML = `
            <div class="tm-card" style="padding:var(--sp-md)">
                <p class="tm-muted">
                    Approval history is shown in each entity's detail page → History tab.<br>
                    Use "Submit for Approval" from Test Planning or Test Case Detail to start a workflow.
                </p>
            </div>`;
    }

    // ── Actions ─────────────────────────────────────────────────────────

    async function decide(recordId, decision) {
        let comment = '';
        if (decision === 'rejected') {
            comment = prompt('Rejection reason (optional):') || '';
        }

        try {
            await API.post(`/api/v1/approvals/${recordId}/decide`, {
                decision,
                comment,
            });
            App.toast(`Approval ${decision}`, decision === 'approved' ? 'success' : 'warning');
            await render(); // re-render
        } catch (err) {
            App.toast(err?.message || 'Decision failed', 'error');
        }
    }

    // ── Reusable: Approval Status Banner ────────────────────────────────

    /**
     * Render an approval status banner inside a container element.
     * Fetches status from API and shows banner + action buttons.
     *
     * Usage: ApprovalsView.renderStatusBanner(containerEl, 'test_case', 42)
     */
    async function renderStatusBanner(containerEl, entityType, entityId) {
        if (!containerEl) return;

        try {
            const data = await API.get(`/api/v1/${entityType}/${entityId}/approval-status`);
            if (data.status === 'not_submitted') {
                containerEl.innerHTML = `
                    <div class="tm-approval-banner tm-approval-banner--draft">
                        <span class="tm-approval-banner__icon">📝</span>
                        <span class="tm-approval-banner__text">Not submitted for approval</span>
                        <button class="tm-toolbar__btn tm-toolbar__btn--primary" style="font-size:11px"
                            onclick="ApprovalsView.submitEntity('${_esc(entityType)}', ${entityId})">
                            Submit for Approval
                        </button>
                    </div>`;
                return;
            }

            const statusColors = {
                pending:  { bg: '#fef7cd', color: '#7c6900', icon: '⏳' },
                approved: { bg: '#e6f4ea', color: '#137333', icon: '✅' },
                rejected: { bg: '#fce8e6', color: '#a50e0e', icon: '❌' },
                completed:{ bg: '#e8f0fe', color: '#174ea6', icon: '📋' },
            };
            const s = statusColors[data.status] || statusColors.pending;

            const recordsHtml = (data.records || []).map(r => `
                <div class="tm-approval-stage">
                    <span class="tm-approval-stage__badge" style="background:${r.status === 'approved' ? '#e6f4ea' : r.status === 'rejected' ? '#fce8e6' : '#fef7cd'}">${
                        r.status === 'approved' ? '✓' : r.status === 'rejected' ? '✗' : r.status === 'skipped' ? '⊘' : '…'
                    }</span>
                    <span style="font-size:var(--tm-font-xs)">
                        L${r.stage} ${_esc(r.stage_role)} — <strong>${_esc(r.status)}</strong>
                        ${r.approver ? ` by ${_esc(r.approver)}` : ''}
                        ${r.comment ? ` — "${_esc(r.comment)}"` : ''}
                    </span>
                </div>
            `).join('');

            containerEl.innerHTML = `
                <div class="tm-approval-banner" style="background:${s.bg};border-color:${s.color}20">
                    <div style="display:flex;align-items:center;gap:var(--sp-sm);margin-bottom:${data.records?.length ? 'var(--sp-xs)' : '0'}">
                        <span class="tm-approval-banner__icon">${s.icon}</span>
                        <span class="tm-approval-banner__text" style="color:${s.color}">
                            Approval Status: <strong>${_esc(data.status.toUpperCase())}</strong>
                        </span>
                    </div>
                    ${recordsHtml ? `<div class="tm-approval-stages">${recordsHtml}</div>` : ''}
                </div>`;
        } catch {
            containerEl.innerHTML = '';
        }
    }

    async function submitEntity(entityType, entityId) {
        try {
            await API.post('/api/v1/approvals/submit', {
                entity_type: entityType,
                entity_id: entityId,
            });
            App.toast('Submitted for approval', 'success');
            // Re-render whichever view is active
            const main = document.getElementById('mainContent');
            if (main) {
                const banner = main.querySelector('.tm-approval-banner')?.parentElement;
                if (banner) {
                    await renderStatusBanner(banner, entityType, entityId);
                }
            }
        } catch (err) {
            App.toast(err?.message || 'Submit failed', 'error');
        }
    }

    return {
        render,
        decide,
        renderStatusBanner,
        submitEntity,
    };
})();
