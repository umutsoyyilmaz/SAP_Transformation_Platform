/* UI-S02-T02 — PGForm: Standart form element HTML helper'ları */
const PGForm = (() => {
    /**
     * Standart form input HTML helper'ları.
     * Her view'da doğrudan `<input class="pg-input">` veya bu helper'lar ile kullanılır.
     * Tüm elementler --pg-* tokenlarını kullanır; hardcoded renk/boyut yasak.
     */

    /** Tek satır metin inputu */
    function input({ name, label, value, placeholder, required, disabled, type, helpText, errorText }) {
        value = value || '';
        placeholder = placeholder || '';
        required = required || false;
        disabled = disabled || false;
        type = type || 'text';
        helpText = helpText || '';
        errorText = errorText || '';
        const id = `pg-input-${name}`;
        return `
            <div class="pg-field${errorText ? ' pg-field--error' : ''}">
                ${label ? `<label class="pg-label" for="${id}">${_esc(label)}${required ? '<span class="pg-label__req" aria-hidden="true">*</span>' : ''}</label>` : ''}
                <input
                    class="pg-input"
                    id="${id}" name="${name}" type="${type}"
                    value="${_esc(String(value))}"
                    placeholder="${_esc(placeholder)}"
                    ${required ? 'required' : ''}
                    ${disabled ? 'disabled' : ''}
                >
                ${helpText && !errorText ? `<p class="pg-hint">${_esc(helpText)}</p>` : ''}
                ${errorText ? `<p class="pg-error-msg" role="alert">${_esc(errorText)}</p>` : ''}
            </div>
        `;
    }

    /** Textarea */
    function textarea({ name, label, value, rows, required, disabled, helpText }) {
        value = value || '';
        rows = rows || 3;
        required = required || false;
        disabled = disabled || false;
        helpText = helpText || '';
        const id = `pg-textarea-${name}`;
        return `
            <div class="pg-field">
                ${label ? `<label class="pg-label" for="${id}">${_esc(label)}${required ? '<span class="pg-label__req" aria-hidden="true">*</span>' : ''}</label>` : ''}
                <textarea
                    class="pg-input pg-input--textarea"
                    id="${id}" name="${name}"
                    rows="${rows}"
                    ${required ? 'required' : ''}
                    ${disabled ? 'disabled' : ''}
                >${_esc(String(value))}</textarea>
                ${helpText ? `<p class="pg-hint">${_esc(helpText)}</p>` : ''}
            </div>
        `;
    }

    /** Select dropdown */
    function select({ name, label, value, options, required, disabled, placeholder }) {
        value = value || '';
        options = options || [];
        required = required || false;
        disabled = disabled || false;
        placeholder = placeholder !== undefined ? placeholder : 'Seç...';
        const id = `pg-select-${name}`;
        const opts = [
            placeholder ? `<option value="" disabled ${!value ? 'selected' : ''}>${_esc(placeholder)}</option>` : '',
            ...options.map(o => {
                const v = typeof o === 'object' ? o.value : o;
                const l = typeof o === 'object' ? o.label : o;
                return `<option value="${_esc(String(v))}" ${String(v) === String(value) ? 'selected' : ''}>${_esc(String(l))}</option>`;
            })
        ].join('');
        return `
            <div class="pg-field">
                ${label ? `<label class="pg-label" for="${id}">${_esc(label)}${required ? '<span class="pg-label__req" aria-hidden="true">*</span>' : ''}</label>` : ''}
                <select class="pg-select" id="${id}" name="${name}" ${required ? 'required' : ''} ${disabled ? 'disabled' : ''}>${opts}</select>
            </div>
        `;
    }

    /** Checkbox */
    function checkbox({ name, label, checked, disabled }) {
        checked = checked || false;
        disabled = disabled || false;
        return `
            <label class="pg-checkbox">
                <input type="checkbox" name="${name}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''}>
                <span class="pg-checkbox__label">${_esc(label || '')}</span>
            </label>
        `;
    }

    function _esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    return { input, textarea, select, checkbox };
})();
