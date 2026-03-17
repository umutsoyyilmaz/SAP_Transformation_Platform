const ReportsAI = (() => {
    let _program = null;

    function _esc(s) {
        const el = document.createElement('div');
        el.textContent = s || '';
        return el.innerHTML;
    }

    function _renderList(title, items, renderItem) {
        const list = Array.isArray(items) ? items.filter(Boolean) : [];
        if (!list.length) return '';
        return `
            <div class="reports-ai-result__list">
                <h3 class="reports-ai-result__list-title">${_esc(title)}</h3>
                <ul class="reports-ai-result__list-items">
                    ${list.map((item) => `<li>${renderItem ? renderItem(item) : _esc(String(item))}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    function openSteeringPackModal({ program }) {
        _program = program || null;
        App.openModal(`
            <div class="modal-content reports-ai-modal reports-ai-modal--padded" data-testid="reports-ai-steering-pack-modal">
                <div class="reports-ai-modal__header">
                    <h2 class="reports-ai-modal__title">AI Steering Pack</h2>
                    <button class="btn btn-secondary btn-sm" onclick="App.closeModal()">Close</button>
                </div>
                <div class="reports-ai-modal__form">
                    <div>
                        <label for="aiSteeringPeriod" class="reports-ai-modal__field-label">Period</label>
                        <select id="aiSteeringPeriod" class="form-control">
                            <option value="weekly">Weekly</option>
                            <option value="monthly">Monthly</option>
                            <option value="milestone">Milestone</option>
                        </select>
                    </div>
                    <div class="reports-ai-modal__actions">
                        <button class="btn btn-primary" data-testid="reports-ai-steering-pack-generate" onclick="ReportsAI.runSteeringPack()">Generate</button>
                    </div>
                </div>
                <div id="aiSteeringPackResult" class="reports-ai-result" data-testid="reports-ai-steering-pack-result"></div>
            </div>
        `);
    }

    async function runSteeringPack() {
        const container = document.getElementById('aiSteeringPackResult');
        if (!_program || !container) return;

        const period = document.getElementById('aiSteeringPeriod')?.value || 'weekly';
        container.innerHTML = '<div class="reports-ai-result--loading"><div class="spinner"></div></div>';

        try {
            const data = await API.post('/ai/doc-gen/steering-pack', {
                program_id: _program.id,
                period,
                create_suggestion: true,
            });
            container.innerHTML = `
                <div class="reports-ai-result__badges">
                    ${PGStatusRegistry.badge('ai', { label: _esc(data.title || 'Steering Pack') })}
                    ${data.confidence != null ? PGStatusRegistry.badge('info', { label: `${Math.round((data.confidence || 0) * 100)}% confidence` }) : ''}
                    ${data.suggestion_id ? PGStatusRegistry.badge('pending', { label: 'Suggestion queued' }) : ''}
                </div>
                <div class="reports-ai-result__summary">
                    <div class="reports-ai-result__summary-label">Executive Summary</div>
                    <p class="reports-ai-result__summary-text">${_esc(data.executive_summary || 'No executive summary returned.')}</p>
                </div>
                ${_renderList('Workstream Status', data.workstream_status, (item) => _esc(typeof item === 'object' ? JSON.stringify(item) : String(item)))}
                ${_renderList('KPI Highlights', data.kpi_highlights)}
                ${_renderList('Risk Escalations', data.risk_escalations)}
                ${_renderList('Decisions Needed', data.decisions_needed)}
                ${_renderList('Next Steps', data.next_steps)}
            `;
        } catch (err) {
            container.innerHTML = `<div class="card reports-ai-result__error">Error: ${_esc(err.message)}</div>`;
        }
    }

    return { openSteeringPackModal, runSteeringPack };
})();
