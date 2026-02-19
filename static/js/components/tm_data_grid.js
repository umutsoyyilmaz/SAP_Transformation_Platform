var TMDataGrid = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    function render(container, config) {
        if (!container || !config) return;
        const {
            columns = [],
            rows = [],
            rowKey = 'id',
            selectedRowId = null,
            emptyText = 'No records',
            onRowClick = null,
        } = config;

        if (!rows.length) {
            container.innerHTML = `<div class="empty-state" style="padding:36px"><p>${esc(emptyText)}</p></div>`;
            return;
        }

        container.innerHTML = `
            <div class="tm-data-grid__wrap">
                <table class="tm-data-grid">
                    <thead>
                        <tr>
                            ${columns.map(c => `<th style="width:${c.width || 'auto'};text-align:${c.align || 'left'}">${esc(c.label || '')}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => {
                            const rowId = row[rowKey];
                            const isSel = selectedRowId !== null && String(selectedRowId) === String(rowId);
                            return `<tr data-row-id="${esc(String(rowId))}" class="${isSel ? 'is-selected' : ''}">
                                ${columns.map(c => {
                                    if (typeof c.render === 'function') {
                                        return `<td style="text-align:${c.align || 'left'}">${c.render(row)}</td>`;
                                    }
                                    return `<td style="text-align:${c.align || 'left'}">${esc(row[c.key] ?? '')}</td>`;
                                }).join('')}
                            </tr>`;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;

        if (typeof onRowClick === 'function') {
            container.querySelectorAll('tbody tr[data-row-id]').forEach(tr => {
                tr.addEventListener('click', () => {
                    onRowClick(tr.dataset.rowId);
                });
            });
        }
    }

    return { render };
})();
