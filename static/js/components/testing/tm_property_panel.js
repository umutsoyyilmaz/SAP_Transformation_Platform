/* F1 — TMPropertyPanel: Key-value detail panel with collapsible sections & inline edit */
var TMPropertyPanel = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    /**
     * @param {HTMLElement} container
     * @param {Object}  config
     * @param {Array}   config.sections — [{title, collapsed?, fields:[{key,label,value,editable?,type?,options?,onChange?}]}]
     * @param {boolean} config.editing  — global edit mode
     */
    function render(container, config) {
        if (!container) return;
        const { sections = [], editing = false } = config || {};

        container.innerHTML = `<div class="tm-property-panel">
            ${sections.map((sec, si) => {
                const collapsed = sec.collapsed ? 'is-collapsed' : '';
                return `
                    <div class="tm-property-panel__section ${collapsed}" data-section="${si}">
                        <div class="tm-property-panel__section-header" data-toggle-section="${si}">
                            <span class="tm-property-panel__chevron">${sec.collapsed ? '▸' : '▾'}</span>
                            <span>${esc(sec.title || '')}</span>
                        </div>
                        <div class="tm-property-panel__section-body">
                            ${(sec.fields || []).map((f, fi) => _renderField(f, editing, si, fi)).join('')}
                        </div>
                    </div>
                `;
            }).join('')}
        </div>`;

        // Section toggle
        container.querySelectorAll('[data-toggle-section]').forEach(hdr => {
            hdr.addEventListener('click', () => {
                const sec = hdr.closest('.tm-property-panel__section');
                sec.classList.toggle('is-collapsed');
                const chevron = sec.querySelector('.tm-property-panel__chevron');
                chevron.textContent = sec.classList.contains('is-collapsed') ? '▸' : '▾';
            });
        });

        // Edit handlers
        if (editing) {
            container.querySelectorAll('[data-field-section][data-field-index]').forEach(el => {
                const si = Number(el.dataset.fieldSection);
                const fi = Number(el.dataset.fieldIndex);
                const field = sections[si]?.fields?.[fi];
                if (field && typeof field.onChange === 'function') {
                    el.addEventListener('change', (e) => field.onChange(e.target.value));
                }
            });
        }
    }

    function _renderField(field, editing, si, fi) {
        const { key, label, value, editable, type, options } = field;
        const displayVal = value != null ? String(value) : '-';

        let valueHtml;
        if (editing && editable !== false) {
            if (type === 'select' && Array.isArray(options)) {
                valueHtml = `<select class="tm-input tm-property-panel__input" data-field-section="${si}" data-field-index="${fi}">
                    ${options.map(o => `<option value="${esc(o.value)}" ${o.value === value ? 'selected' : ''}>${esc(o.text || o.value)}</option>`).join('')}
                </select>`;
            } else if (type === 'textarea') {
                valueHtml = `<textarea class="tm-input tm-property-panel__input" data-field-section="${si}" data-field-index="${fi}" rows="3">${esc(displayVal === '-' ? '' : displayVal)}</textarea>`;
            } else {
                valueHtml = `<input class="tm-input tm-property-panel__input" type="${type || 'text'}" value="${esc(displayVal === '-' ? '' : displayVal)}" data-field-section="${si}" data-field-index="${fi}" />`;
            }
        } else {
            valueHtml = `<span class="tm-property-panel__value">${esc(displayVal)}</span>`;
        }

        return `
            <div class="tm-property-panel__row">
                <span class="tm-property-panel__label">${esc(label || key || '')}</span>
                ${valueHtml}
            </div>
        `;
    }

    return { render };
})();
