/* F1 — TMDropdownSelect: Searchable dropdown with multi-select and tags */
var TMDropdownSelect = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    /**
     * @param {HTMLElement} container
     * @param {Object}  config
     * @param {Array}   config.options     — [{value, text, selected?}]
     * @param {boolean} config.multi       — allow multiple selections (default false)
     * @param {string}  config.placeholder — placeholder text
     * @param {boolean} config.searchable  — show search input (default true)
     * @param {Function} config.onChange   — (selectedValues: string[]) => void
     */
    function render(container, config) {
        if (!container) return;
        const {
            options = [],
            multi = false,
            placeholder = 'Select…',
            searchable = true,
            onChange = null,
        } = config || {};

        const selected = new Set(options.filter(o => o.selected).map(o => String(o.value)));
        let isOpen = false;
        let query = '';

        const draw = () => {
            const selLabels = options.filter(o => selected.has(String(o.value)));
            const displayText = selLabels.length
                ? (multi ? selLabels.map(o => o.text).join(', ') : selLabels[0].text)
                : placeholder;

            const filtered = options.filter(o =>
                !query || (o.text || '').toLowerCase().includes(query.toLowerCase())
            );

            const tagsHtml = multi && selLabels.length
                ? `<div class="tm-dropdown__tags">
                    ${selLabels.map(o => `<span class="tm-dropdown__tag">${esc(o.text)}<button class="tm-dropdown__tag-x" data-remove="${esc(String(o.value))}">×</button></span>`).join('')}
                  </div>`
                : '';

            container.innerHTML = `
                <div class="tm-dropdown ${isOpen ? 'is-open' : ''}">
                    ${tagsHtml}
                    <div class="tm-dropdown__trigger">
                        <span class="tm-dropdown__display">${esc(displayText)}</span>
                        <span class="tm-dropdown__arrow">${isOpen ? '▴' : '▾'}</span>
                    </div>
                    ${isOpen ? `
                        <div class="tm-dropdown__panel">
                            ${searchable ? `<input class="tm-input tm-dropdown__search" placeholder="Search…" value="${esc(query)}" />` : ''}
                            <div class="tm-dropdown__list">
                                ${filtered.length ? filtered.map(o => {
                                    const isSel = selected.has(String(o.value));
                                    return `<div class="tm-dropdown__option ${isSel ? 'is-selected' : ''}" data-value="${esc(String(o.value))}">
                                        ${multi ? `<span class="tm-dropdown__check">${isSel ? '☑' : '☐'}</span>` : ''}
                                        <span>${esc(o.text)}</span>
                                    </div>`;
                                }).join('') : '<div class="tm-dropdown__empty">No results</div>'}
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;

            // Bind trigger
            const trigger = container.querySelector('.tm-dropdown__trigger');
            if (trigger) trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                isOpen = !isOpen;
                draw();
            });

            // Bind search
            const searchInput = container.querySelector('.tm-dropdown__search');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    query = e.target.value;
                    draw();
                    // Re-focus after redraw
                    const newInput = container.querySelector('.tm-dropdown__search');
                    if (newInput) { newInput.focus(); newInput.selectionStart = newInput.value.length; }
                });
                searchInput.addEventListener('click', (e) => e.stopPropagation());
            }

            // Bind options
            container.querySelectorAll('.tm-dropdown__option').forEach(opt => {
                opt.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const val = opt.dataset.value;
                    if (multi) {
                        if (selected.has(val)) selected.delete(val);
                        else selected.add(val);
                    } else {
                        selected.clear();
                        selected.add(val);
                        isOpen = false;
                    }
                    draw();
                    if (typeof onChange === 'function') onChange(Array.from(selected));
                });
            });

            // Bind tag remove
            container.querySelectorAll('.tm-dropdown__tag-x').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    selected.delete(btn.dataset.remove);
                    draw();
                    if (typeof onChange === 'function') onChange(Array.from(selected));
                });
            });
        };

        draw();

        // Close on outside click
        const closeHandler = () => { if (isOpen) { isOpen = false; draw(); } };
        document.addEventListener('click', closeHandler);
    }

    return { render };
})();
