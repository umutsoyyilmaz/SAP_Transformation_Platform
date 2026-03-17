const BacklogAI = (() => {
    let _items = [];
    let _currentItem = null;
    let _defaultItemId = null;

    function _esc(s) {
        const el = document.createElement('span');
        el.textContent = s || '';
        return el.innerHTML;
    }

    function _renderList(title, items, renderItem) {
        const list = Array.isArray(items) ? items.filter(Boolean) : [];
        if (!list.length) return '';
        return `
            <div style="margin-top:16px">
                <h3 style="margin:0 0 8px">${_esc(title)}</h3>
                <ul style="margin:0;padding-left:18px;display:grid;gap:6px">
                    ${list.map((item) => `<li>${renderItem ? renderItem(item) : _esc(String(item))}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    function openWricefSpecModal({ items, currentItem, defaultItemId = null }) {
        _items = Array.isArray(items) ? items : [];
        _currentItem = currentItem || null;
        _defaultItemId = defaultItemId;

        if (!_items.length) {
            App.toast('Load or create a backlog item first', 'warning');
            return;
        }

        const selectedId = _defaultItemId || _currentItem?.id || _items[0]?.id || '';
        App.openModal(`
            <h2>AI WRICEF Specification</h2>
            <div style="display:grid;gap:12px;margin-top:16px">
                <div class="form-group">
                    <label>Backlog Item</label>
                    <select id="aiWricefItemId" class="form-input">
                        ${_items.map((item) => `<option value="${item.id}" ${String(item.id) === String(selectedId) ? 'selected' : ''}>${_esc(item.code || 'BL')} — ${_esc(item.title || '')}</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label>Specification Type</label>
                    <select id="aiWricefSpecType" class="form-input">
                        <option value="functional">Functional</option>
                        <option value="technical">Technical</option>
                        <option value="integration">Integration</option>
                    </select>
                </div>
            </div>
            <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px">
                <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="BacklogAI.runWricefSpec()">Generate</button>
            </div>
            <div id="aiWricefSpecResult" style="margin-top:16px"></div>
        `);
    }

    async function runWricefSpec() {
        const container = document.getElementById('aiWricefSpecResult');
        if (!container) return;

        const backlogItemId = parseInt(document.getElementById('aiWricefItemId')?.value, 10);
        const specType = document.getElementById('aiWricefSpecType')?.value || 'functional';
        if (!backlogItemId) {
            container.innerHTML = '<div class="empty-state" style="padding:24px"><p>Select a backlog item first.</p></div>';
            return;
        }

        container.innerHTML = '<div style="min-height:180px;display:flex;align-items:center;justify-content:center"><div class="spinner"></div></div>';

        try {
            const data = await API.post('/ai/doc-gen/wricef-spec', {
                backlog_item_id: backlogItemId,
                spec_type: specType,
                create_suggestion: true,
            });

            container.innerHTML = `
                <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
                    ${PGStatusRegistry.badge('ai', { label: _esc(data.title || 'WRICEF Spec') })}
                    ${PGStatusRegistry.badge('info', { label: _esc(specType) })}
                    ${data.confidence != null ? PGStatusRegistry.badge('info', { label: `${Math.round((data.confidence || 0) * 100)}% confidence` }) : ''}
                    ${data.suggestion_id ? PGStatusRegistry.badge('pending', { label: 'Suggestion queued' }) : ''}
                </div>
                <div style="margin-top:16px;padding:16px;border:1px solid #e2e8f0;border-radius:12px;background:#fff">
                    <div style="font-size:12px;color:#64748b;text-transform:uppercase;margin-bottom:6px">Overview</div>
                    <p style="margin:0;line-height:1.5">${_esc(data.overview || 'No overview returned.')}</p>
                </div>
                ${_renderList('Functional Requirements', data.functional_requirements)}
                ${data.technical_details ? `
                    <div style="margin-top:16px;padding:16px;border:1px solid #e2e8f0;border-radius:12px;background:#fff">
                        <div style="font-size:12px;color:#64748b;text-transform:uppercase;margin-bottom:6px">Technical Details</div>
                        <p style="margin:0;line-height:1.5">${_esc(data.technical_details)}</p>
                    </div>
                ` : ''}
                ${_renderList('Integration Points', data.integration_points, (item) => _esc(typeof item === 'object' ? JSON.stringify(item) : String(item)))}
                ${_renderList('Data Mapping', data.data_mapping, (item) => _esc(typeof item === 'object' ? JSON.stringify(item) : String(item)))}
                ${data.test_approach ? `
                    <div style="margin-top:16px;padding:16px;border:1px solid #e2e8f0;border-radius:12px;background:#fff">
                        <div style="font-size:12px;color:#64748b;text-transform:uppercase;margin-bottom:6px">Test Approach</div>
                        <p style="margin:0;line-height:1.5">${_esc(data.test_approach)}</p>
                    </div>
                ` : ''}
                ${_renderList('Assumptions', data.assumptions)}
            `;
        } catch (err) {
            container.innerHTML = `<div class="empty-state" style="padding:24px"><p>⚠️ ${_esc(err.message)}</p></div>`;
        }
    }

    return { openWricefSpecModal, runWricefSpec };
})();
