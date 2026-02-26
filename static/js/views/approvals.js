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
            ? `/approvals/pending?program_id=${pid}`
            : '/approvals/pending';
        _pendingRecords = await API.get(url).catch(() => []);
    }

    // ── Render ──────────────────────────────────────────────────────────

    async function render() {
        const main = document.getElementById('mainContent');
        if (!main) return;
        main.innerHTML = '<div class="spinner"></div>';

        await _loadPending();

        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Approval Inbox' }])}
                <h2 class="pg-view-title">Approval Inbox</h2>
            </div>
            <div style="max-width:960px;margin:0 auto;padding:var(--pg-sp-4)">
                <div style="display:flex;justify-content:flex-end;align-items:center;margin-bottom:var(--pg-sp-4)">
                    ${PGStatusRegistry.badge('pending', { label: _pendingRecords.length + ' pending' })}
                </div>

                <div id="approvalTabBar" style="margin-bottom:var(--pg-sp-4)"></div>
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
            el.innerHTML = PGEmptyState.html({ icon: 'approvals', title: 'No pending approvals', description: 'All approvals have been processed.' });
            return;
        }

        el.innerHTML = '<div id="approvalGrid"></div>';
        TMDataGrid.render(document.getElementById('approvalGrid'), {
            columns: [
                { key: 'entity_type', label: 'Type', width: '100px', render: (r) => PGStatusRegistry.badge(r.entity_type, { label: _esc(r.entity_type) }) },
                { key: 'entity_id', label: 'Entity ID', width: '80px', render: (r) => `#${r.entity_id}` },
                { key: 'workflow_name', label: 'Workflow', width: '160px' },
                { key: 'stage', label: 'Stage', width: '60px', render: (r) => `L${r.stage}` },
                { key: 'stage_role', label: 'Role', width: '120px' },
                { key: 'created_at', label: 'Submitted', width: '140px', render: (r) => _esc((r.created_at || '').slice(0, 16)) },
                { key: '_actions', label: 'Actions', width: '180px', render: (r) => `
                    <button class="pg-btn pg-btn--primary pg-btn--sm" onclick="ApprovalsView.decide(${r.id}, 'approved')">Approve</button>
                    <button class="pg-btn pg-btn--danger pg-btn--sm" onclick="ApprovalsView.decide(${r.id}, 'rejected')">Reject</button>
                ` },
            ],
            rows: _pendingRecords,
        });
    }

    async function _renderHistory(el) {
        // Load all records (not just pending) for the current program
        const pid = App.activeProgramId;
        let url = '/approvals/pending'; // fallback
        // We'll fetch history via entity status endpoint—since there's no "all records" endpoint,
        // we show a summary based on pending count
        el.innerHTML = `
            <div class="pg-card" style="padding:var(--pg-sp-5)">
                <p style="color:var(--pg-color-text-secondary);font-size:13px">
                    Approval history is shown on each entity's detail page under the History tab.<br>
                    To start a new approval, use "Submit for Approval" from Test Planning or Test Case Detail.
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
            await API.post(`/approvals/${recordId}/decide`, {
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
            const data = await API.get(`/${entityType}/${entityId}/approval-status`);
            if (data.status === 'not_submitted') {
                containerEl.innerHTML = `
                    <div class="tm-approval-banner tm-approval-banner--draft">
                        <span class="tm-approval-banner__text" style="color:var(--pg-color-text-secondary)">Not submitted for approval</span>
                        <button class="pg-btn pg-btn--primary pg-btn--sm"
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
            await API.post('/approvals/submit', {
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
