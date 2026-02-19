/* F1 — TMStepEditor: Drag-reorder step list with inline edit and numbering */
var TMStepEditor = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    /**
     * @param {HTMLElement} container
     * @param {Object}   config
     * @param {Array}    config.steps     — [{step_no, action, test_data, expected_result, notes}]
     * @param {boolean}  config.editable  — enable inline editing (default false)
     * @param {Function} config.onChange  — (steps) => void  (called on any change)
     * @param {Function} config.onAdd    — () => void
     * @param {Function} config.onRemove — (index) => void
     * @param {Function} config.onMove   — (index, direction:'up'|'down') => void
     * @param {Function} config.onFieldChange — (index, field, value) => void
     */
    function render(container, config) {
        if (!container) return;
        const {
            steps = [],
            editable = false,
            onAdd = null,
            onRemove = null,
            onMove = null,
            onFieldChange = null,
        } = config || {};

        if (!steps.length && !editable) {
            container.innerHTML = '<div class="tm-step-editor__empty">No test steps defined.</div>';
            return;
        }

        container.innerHTML = `
            <div class="tm-step-editor">
                <div class="tm-step-editor__header">
                    <span class="tm-step-editor__title">Test Steps (${steps.length})</span>
                    ${editable ? '<button class="tm-toolbar__btn tm-toolbar__btn--primary tm-step-editor__add" data-step-add>+ Add Step</button>' : ''}
                </div>
                <table class="tm-data-grid">
                    <thead>
                        <tr>
                            <th style="width:40px">#</th>
                            <th>Action / Description</th>
                            <th>Test Data</th>
                            <th>Expected Result</th>
                            ${editable ? '<th style="width:110px">Actions</th>' : ''}
                        </tr>
                    </thead>
                    <tbody>
                        ${steps.map((s, idx) => _renderStepRow(s, idx, editable)).join('')}
                    </tbody>
                </table>
            </div>
        `;

        // Bind Add
        if (editable && onAdd) {
            const addBtn = container.querySelector('[data-step-add]');
            if (addBtn) addBtn.addEventListener('click', onAdd);
        }

        // Bind inline edits
        if (editable && onFieldChange) {
            container.querySelectorAll('[data-step-idx][data-step-field]').forEach(inp => {
                inp.addEventListener('change', () => {
                    onFieldChange(Number(inp.dataset.stepIdx), inp.dataset.stepField, inp.value);
                });
            });
        }

        // Bind move & remove
        if (editable) {
            container.querySelectorAll('[data-step-move-up]').forEach(btn => {
                btn.addEventListener('click', () => { if (onMove) onMove(Number(btn.dataset.stepMoveUp), 'up'); });
            });
            container.querySelectorAll('[data-step-move-down]').forEach(btn => {
                btn.addEventListener('click', () => { if (onMove) onMove(Number(btn.dataset.stepMoveDown), 'down'); });
            });
            container.querySelectorAll('[data-step-remove]').forEach(btn => {
                btn.addEventListener('click', () => { if (onRemove) onRemove(Number(btn.dataset.stepRemove)); });
            });
        }
    }

    function _renderStepRow(step, idx, editable) {
        if (editable) {
            return `<tr class="tm-step-editor__row" data-row-idx="${idx}">
                <td class="tm-step-editor__num">${idx + 1}</td>
                <td><input class="tm-input" value="${esc(step.action || '')}" data-step-idx="${idx}" data-step-field="action" /></td>
                <td><input class="tm-input" value="${esc(step.test_data || '')}" data-step-idx="${idx}" data-step-field="test_data" /></td>
                <td><input class="tm-input" value="${esc(step.expected_result || '')}" data-step-idx="${idx}" data-step-field="expected_result" /></td>
                <td>
                    <button class="tm-step-editor__btn" data-step-move-up="${idx}" title="Move Up">↑</button>
                    <button class="tm-step-editor__btn" data-step-move-down="${idx}" title="Move Down">↓</button>
                    <button class="tm-step-editor__btn tm-step-editor__btn--danger" data-step-remove="${idx}" title="Remove">🗑</button>
                </td>
            </tr>`;
        }
        return `<tr class="tm-step-editor__row">
            <td class="tm-step-editor__num">${idx + 1}</td>
            <td>${esc(step.action || '-')}</td>
            <td>${esc(step.test_data || '-')}</td>
            <td>${esc(step.expected_result || '-')}</td>
        </tr>`;
    }

    return { render };
})();
