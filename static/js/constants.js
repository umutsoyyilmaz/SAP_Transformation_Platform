/**
 * SAP Transformation Platform — Shared Constants (ADR-3)
 */
const SAPConstants = (() => {
    'use strict';

    const SAP_MODULES = [
        { code: 'SD',     label: 'SD — Sales & Distribution' },
        { code: 'MM',     label: 'MM — Materials Management' },
        { code: 'FI',     label: 'FI — Financial Accounting' },
        { code: 'CO',     label: 'CO — Controlling' },
        { code: 'PP',     label: 'PP — Production Planning' },
        { code: 'PM',     label: 'PM — Plant Maintenance' },
        { code: 'QM',     label: 'QM — Quality Management' },
        { code: 'PS',     label: 'PS — Project System' },
        { code: 'WM',     label: 'WM — Warehouse Management' },
        { code: 'EWM',    label: 'EWM — Extended WM' },
        { code: 'HR',     label: 'HR — Human Resources' },
        { code: 'HCM',    label: 'HCM — Human Capital Mgmt' },
        { code: 'TM',     label: 'TM — Transportation Mgmt' },
        { code: 'GTS',    label: 'GTS — Global Trade Services' },
        { code: 'BTP',    label: 'BTP — Business Technology' },
        { code: 'BASIS',  label: 'BASIS — System Admin' },
        { code: 'FICO',   label: 'FICO — Finance & Controlling' },
        { code: 'MDG',    label: 'MDG — Master Data Governance' },
        { code: 'S4CORE', label: 'S4CORE — Core Modules' },
    ];

    /**
     * Generate <option> HTML for SAP module dropdown.
     * @param {string} [selectedValue] — pre-select this value
     * @returns {string} HTML string
     */
    function moduleOptionsHTML(selectedValue) {
        const sel = (selectedValue || '').toUpperCase();
        let html = '<option value="">— Select Module —</option>';
        for (const m of SAP_MODULES) {
            const selected = m.code === sel ? ' selected' : '';
            html += `<option value="${m.code}"${selected}>${m.label}</option>`;
        }
        return html;
    }

    return { SAP_MODULES, moduleOptionsHTML };
})();
