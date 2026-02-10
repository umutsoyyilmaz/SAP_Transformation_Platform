/**
 * Explore Phase — Shared UI Components
 * F-043: Pill, F-044: FitBadge, F-045: FitBarMini,
 * F-046: KpiBlock, F-047: FilterGroup, F-048: ActionButton,
 * F-049: CountChip
 *
 * Pure render functions — each returns an HTML string.
 * Usage: element.innerHTML = ExpUI.pill({ ... });
 */
const ExpUI = (() => {
    'use strict';

    // ── Helpers ──────────────────────────────────────────────────────
    function esc(str) {
        const d = document.createElement('div');
        d.textContent = str ?? '';
        return d.innerHTML;
    }

    // ────────────────────────────────────────────────────────────────
    // F-043  Pill — generic pill / tag component
    // ────────────────────────────────────────────────────────────────
    /**
     * @param {Object} opts
     * @param {string} opts.label
     * @param {string} [opts.color]    — CSS color for bg
     * @param {string} [opts.textColor] — CSS color for text
     * @param {string} [opts.variant]  — named variant: fit|gap|partial|pending|p1|p2|p3|p4
     *                                  |open_item|decision|requirement|draft|info
     * @param {string} [opts.size]     — sm (default) | md | lg
     * @param {boolean} [opts.removable]
     * @param {string}  [opts.title]   — tooltip
     * @returns {string} HTML string
     */
    const PILL_VARIANTS = {
        fit:         { bg: 'var(--exp-fit-bg)',         color: 'var(--exp-fit-text)' },
        gap:         { bg: 'var(--exp-gap-bg)',         color: 'var(--exp-gap-text)' },
        partial:     { bg: 'var(--exp-partial-bg)',     color: 'var(--exp-partial-text)' },
        partial_fit: { bg: 'var(--exp-partial-bg)',     color: 'var(--exp-partial-text)' },
        pending:     { bg: 'var(--exp-pending-bg)',     color: 'var(--exp-pending-text)' },
        p1:          { bg: 'var(--exp-p1-bg)',          color: '#991b1b' },
        p2:          { bg: 'var(--exp-p2-bg)',          color: '#92400e' },
        p3:          { bg: 'var(--exp-p3-bg)',          color: '#1e40af' },
        p4:          { bg: 'var(--exp-p4-bg)',          color: '#475569' },
        open_item:   { bg: 'var(--exp-open-item-bg)',   color: 'var(--exp-open-item-text)' },
        decision:    { bg: 'var(--exp-decision-bg)',    color: 'var(--exp-decision-text)' },
        requirement: { bg: 'var(--exp-requirement-bg)', color: 'var(--exp-requirement-text)' },
        draft:       { bg: '#f1f5f9',                   color: '#64748b' },
        info:        { bg: '#dbeafe',                   color: '#1e40af' },
        success:     { bg: '#d1fae5',                   color: '#065f46' },
        warning:     { bg: '#fef3c7',                   color: '#92400e' },
        danger:      { bg: '#fee2e2',                   color: '#991b1b' },
    };

    const PILL_SIZES = {
        sm: 'font-size:11px;padding:2px 8px;',
        md: 'font-size:12px;padding:3px 10px;',
        lg: 'font-size:13px;padding:4px 12px;',
    };

    function pill(opts = {}) {
        const v = PILL_VARIANTS[opts.variant] || {};
        const bg = opts.color || v.bg || '#f1f5f9';
        const fg = opts.textColor || v.color || '#475569';
        const sz = PILL_SIZES[opts.size || 'sm'] || PILL_SIZES.sm;
        const title = opts.title ? ` title="${esc(opts.title)}"` : '';
        const removeBtn = opts.removable
            ? ' <span class="exp-pill__remove" style="cursor:pointer;margin-left:4px;opacity:0.6">&times;</span>'
            : '';
        return `<span class="exp-pill" style="display:inline-flex;align-items:center;gap:2px;border-radius:9999px;font-weight:600;white-space:nowrap;line-height:1.4;background:${bg};color:${fg};${sz}"${title}>${esc(opts.label || '')}${removeBtn}</span>`;
    }

    // ────────────────────────────────────────────────────────────────
    // F-044  FitBadge — fit / gap / partial_fit / pending badge
    // ────────────────────────────────────────────────────────────────
    const FIT_LABELS = {
        fit: 'Fit', gap: 'Gap', partial_fit: 'Partial Fit', pending: 'Pending',
    };
    const FIT_ICONS = {
        fit: '●', gap: '●', partial_fit: '◐', pending: '○',
    };

    /**
     * @param {string} status — fit | gap | partial_fit | pending
     * @param {Object} [opts]
     * @param {boolean} [opts.compact] — icon only
     * @returns {string}
     */
    function fitBadge(status, opts = {}) {
        const v = PILL_VARIANTS[status] || PILL_VARIANTS.pending;
        const label = FIT_LABELS[status] || esc(status || 'Pending');
        const icon = FIT_ICONS[status] || '○';
        if (opts.compact) {
            return `<span class="exp-fit-badge exp-fit-badge--compact" style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;background:${v.bg};color:${v.color};font-size:12px" title="${label}">${icon}</span>`;
        }
        return `<span class="exp-fit-badge" style="display:inline-flex;align-items:center;gap:4px;border-radius:9999px;padding:2px 10px;font-size:11px;font-weight:600;background:${v.bg};color:${v.color};white-space:nowrap"><span style="font-size:8px">${icon}</span>${label}</span>`;
    }

    // ────────────────────────────────────────────────────────────────
    // F-045  FitBarMini — mini stacked bar (fit/gap/partial/pending)
    // ────────────────────────────────────────────────────────────────
    /**
     * @param {Object} counts  { fit:N, gap:N, partial_fit:N, pending:N }
     * @param {Object} [opts]
     * @param {number} [opts.height]  — px, default 6
     * @param {number} [opts.width]   — px or '100%'
     * @returns {string}
     */
    function fitBarMini(counts = {}, opts = {}) {
        const fit   = counts.fit || 0;
        const gap   = counts.gap || 0;
        const part  = counts.partial_fit || 0;
        const pend  = counts.pending || 0;
        const total = fit + gap + part + pend;
        if (total === 0) {
            return `<div class="exp-fit-bar-mini" style="height:${opts.height||6}px;width:${opts.width||'100%'};border-radius:3px;background:#e2e8f0" title="No data"></div>`;
        }
        const pFit  = (fit / total * 100).toFixed(1);
        const pGap  = (gap / total * 100).toFixed(1);
        const pPart = (part / total * 100).toFixed(1);
        const pPend = (pend / total * 100).toFixed(1);
        const h = opts.height || 6;
        const w = opts.width || '100%';
        const titleText = `Fit: ${fit}  Gap: ${gap}  Partial: ${part}  Pending: ${pend}`;
        return `<div class="exp-fit-bar-mini" style="display:flex;height:${h}px;width:${typeof w === 'number' ? w+'px' : w};border-radius:3px;overflow:hidden;background:#e2e8f0" title="${titleText}">` +
            (fit   ? `<div style="width:${pFit}%;background:var(--exp-fit)"></div>` : '') +
            (part  ? `<div style="width:${pPart}%;background:var(--exp-partial)"></div>` : '') +
            (gap   ? `<div style="width:${pGap}%;background:var(--exp-gap)"></div>` : '') +
            (pend  ? `<div style="width:${pPend}%;background:var(--exp-pending)"></div>` : '') +
            `</div>`;
    }

    // ────────────────────────────────────────────────────────────────
    // F-046  KpiBlock — reusable KPI card
    // ────────────────────────────────────────────────────────────────
    /**
     * @param {Object} opts
     * @param {string|number} opts.value
     * @param {string}        opts.label
     * @param {string}        [opts.icon]    — emoji or char
     * @param {string}        [opts.accent]  — CSS color for value
     * @param {string}        [opts.trend]   — up | down | flat
     * @param {string}        [opts.trendValue] — e.g. "+12%"
     * @param {string}        [opts.suffix]  — e.g. "%"
     * @returns {string}
     */
    function kpiBlock(opts = {}) {
        const accent = opts.accent ? `color:${opts.accent}` : '';
        const iconHtml = opts.icon ? `<div style="font-size:20px;margin-bottom:4px">${opts.icon}</div>` : '';
        const trendColors = { up: '#10B981', down: '#EF4444', flat: '#94A3B8' };
        const trendIcons  = { up: '↑', down: '↓', flat: '→' };
        const trendHtml = opts.trend
            ? `<span style="font-size:11px;font-weight:600;color:${trendColors[opts.trend] || '#94A3B8'};margin-left:6px">${trendIcons[opts.trend] || ''}${opts.trendValue ? ' ' + esc(opts.trendValue) : ''}</span>`
            : '';
        const suffix = opts.suffix ? `<span style="font-size:14px;font-weight:400">${esc(opts.suffix)}</span>` : '';

        return `<div class="exp-kpi-card">
            ${iconHtml}
            <div class="exp-kpi-card__value" style="${accent}">${esc(String(opts.value ?? '—'))}${suffix}${trendHtml}</div>
            <div class="exp-kpi-card__label">${esc(opts.label || '')}</div>
        </div>`;
    }

    // ────────────────────────────────────────────────────────────────
    // F-047  FilterGroup — reusable filter chip group
    // ────────────────────────────────────────────────────────────────
    /**
     * @param {Object} opts
     * @param {string}   opts.id       — unique group id
     * @param {string}   [opts.label]  — group label
     * @param {Array}    opts.options  — [{value, label, count?}]
     * @param {string|Array} opts.selected — selected value(s)
     * @param {boolean}  [opts.multi]  — allow multiple
     * @param {string}   [opts.onChange] — JS callback name, will be called with (groupId, value)
     * @returns {string}
     */
    function filterGroup(opts = {}) {
        const selected = Array.isArray(opts.selected) ? opts.selected : [opts.selected].filter(Boolean);
        const groupLabel = opts.label ? `<span style="font-size:12px;font-weight:600;color:var(--sap-text-secondary);margin-right:6px">${esc(opts.label)}:</span>` : '';
        const chips = (opts.options || []).map(o => {
            const isActive = selected.includes(o.value);
            const bg = isActive ? 'var(--exp-chip-bg-active)' : 'var(--exp-chip-bg)';
            const fg = isActive ? 'var(--exp-chip-text-active)' : 'var(--exp-chip-text)';
            const countHtml = o.count != null ? ` <span style="opacity:0.7;font-size:10px">(${o.count})</span>` : '';
            const onclick = opts.onChange ? ` onclick="${opts.onChange}('${esc(opts.id)}','${esc(o.value)}')"` : '';
            return `<button class="exp-filter-chip${isActive ? ' exp-filter-chip--active' : ''}" style="display:inline-flex;align-items:center;gap:2px;padding:4px 12px;border-radius:var(--exp-chip-radius);font-size:12px;font-weight:500;border:1px solid ${isActive ? 'var(--exp-chip-bg-active)' : '#e2e8f0'};background:${bg};color:${fg};cursor:pointer;transition:all 0.15s ease;white-space:nowrap"${onclick}>${esc(o.label)}${countHtml}</button>`;
        }).join('');

        return `<div class="exp-filter-group" data-group-id="${esc(opts.id || '')}" style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">${groupLabel}${chips}</div>`;
    }

    // ────────────────────────────────────────────────────────────────
    // F-048  ActionButton — styled action button
    // ────────────────────────────────────────────────────────────────
    /**
     * @param {Object} opts
     * @param {string} opts.label
     * @param {string} [opts.variant] — primary|secondary|success|warning|danger|ghost
     * @param {string} [opts.size]    — sm|md|lg
     * @param {string} [opts.icon]    — left icon (emoji/char)
     * @param {boolean}[opts.disabled]
     * @param {string} [opts.onclick] — JS callback string
     * @param {string} [opts.id]
     * @param {string} [opts.title]
     * @returns {string}
     */
    const BTN_VARIANTS = {
        primary:   { bg: 'var(--sap-blue)',      color: '#fff',     border: 'var(--sap-blue)' },
        secondary: { bg: '#ffffff',               color: 'var(--sap-text-primary)', border: '#d1d5db' },
        success:   { bg: 'var(--exp-fit)',        color: '#fff',     border: 'var(--exp-fit)' },
        warning:   { bg: 'var(--exp-partial)',    color: '#fff',     border: 'var(--exp-partial)' },
        danger:    { bg: 'var(--exp-gap)',         color: '#fff',     border: 'var(--exp-gap)' },
        ghost:     { bg: 'transparent',           color: 'var(--sap-blue)', border: 'transparent' },
    };

    const BTN_SIZES = {
        sm: 'font-size:12px;padding:4px 12px;',
        md: 'font-size:13px;padding:6px 16px;',
        lg: 'font-size:14px;padding:8px 20px;',
    };

    function actionButton(opts = {}) {
        const v = BTN_VARIANTS[opts.variant || 'primary'] || BTN_VARIANTS.primary;
        const sz = BTN_SIZES[opts.size || 'md'] || BTN_SIZES.md;
        const disabled = opts.disabled ? ' disabled' : '';
        const opacity = opts.disabled ? 'opacity:0.5;cursor:not-allowed;' : 'cursor:pointer;';
        const onclick = opts.onclick ? ` onclick="${opts.onclick}"` : '';
        const id = opts.id ? ` id="${esc(opts.id)}"` : '';
        const title = opts.title ? ` title="${esc(opts.title)}"` : '';
        const iconHtml = opts.icon ? `<span style="margin-right:4px">${opts.icon}</span>` : '';

        return `<button class="exp-action-btn"${id}${title}${onclick}${disabled} style="display:inline-flex;align-items:center;gap:2px;border-radius:var(--exp-radius-md);font-weight:600;border:1px solid ${v.border};background:${v.bg};color:${v.color};${sz}${opacity}transition:all 0.15s ease;white-space:nowrap;font-family:inherit">${iconHtml}${esc(opts.label || '')}</button>`;
    }

    // ────────────────────────────────────────────────────────────────
    // F-049  CountChip — inline count indicator
    // ────────────────────────────────────────────────────────────────
    /**
     * @param {number} count
     * @param {Object} [opts]
     * @param {string} [opts.variant] — default|fit|gap|partial|pending|open_item|decision|requirement
     * @param {string} [opts.label]   — prepended text
     * @param {string} [opts.title]   — tooltip
     * @returns {string}
     */
    const CHIP_COLORS = {
        default:     { bg: '#e2e8f0', color: '#475569' },
        fit:         { bg: 'var(--exp-fit-bg)',       color: 'var(--exp-fit-text)' },
        gap:         { bg: 'var(--exp-gap-bg)',       color: 'var(--exp-gap-text)' },
        partial:     { bg: 'var(--exp-partial-bg)',   color: 'var(--exp-partial-text)' },
        pending:     { bg: 'var(--exp-pending-bg)',   color: 'var(--exp-pending-text)' },
        open_item:   { bg: 'var(--exp-open-item-bg)', color: 'var(--exp-open-item-text)' },
        decision:    { bg: 'var(--exp-decision-bg)',  color: 'var(--exp-decision-text)' },
        requirement: { bg: 'var(--exp-requirement-bg)', color: 'var(--exp-requirement-text)' },
    };

    function countChip(count, opts = {}) {
        const c = CHIP_COLORS[opts.variant || 'default'] || CHIP_COLORS.default;
        const title = opts.title ? ` title="${esc(opts.title)}"` : '';
        const label = opts.label ? `${esc(opts.label)} ` : '';
        return `<span class="exp-count-chip" style="display:inline-flex;align-items:center;gap:2px;padding:1px 8px;border-radius:9999px;font-size:11px;font-weight:700;background:${c.bg};color:${c.color};white-space:nowrap"${title}>${label}${count ?? 0}</span>`;
    }

    // ────────────────────────────────────────────────────────────────
    // Composite Helpers (used across views)
    // ────────────────────────────────────────────────────────────────

    /** Level badge (L1/L2/L3/L4) */
    function levelBadge(level) {
        const colors = { L1: 'var(--exp-l1)', L2: 'var(--exp-l2)', L3: 'var(--exp-l3)', L4: 'var(--exp-l4)' };
        return `<span class="exp-tree-node__level" style="background:${colors[level] || '#94A3B8'}">${esc(level)}</span>`;
    }

    /** Priority pill */
    function priorityPill(priority) {
        const map = { P1: 'p1', P2: 'p2', P3: 'p3', P4: 'p4', critical: 'p1', high: 'p2', medium: 'p3', low: 'p4' };
        return pill({ label: priority || '—', variant: map[priority] || 'draft' });
    }

    /** Status pill (workshop) */
    function workshopStatusPill(status) {
        const map = {
            draft: 'draft', scheduled: 'info', in_progress: 'warning', completed: 'success',
        };
        const labels = {
            draft: 'Draft', scheduled: 'Scheduled', in_progress: 'In Progress', completed: 'Completed',
        };
        return pill({ label: labels[status] || status || '—', variant: map[status] || 'draft' });
    }

    /** Wave pill */
    function wavePill(wave) {
        if (!wave) return pill({ label: '—', variant: 'draft' });
        const num = String(wave).replace(/\D/g, '');
        const bgVar = `var(--exp-wave${num}-bg, #f1f5f9)`;
        const fgVar = `var(--exp-wave${num}, #475569)`;
        return pill({ label: `Wave ${num || wave}`, color: bgVar, textColor: fgVar });
    }

    /** Area pill with SAP area color */
    function areaPill(area) {
        if (!area) return '';
        const colorVar = `var(--exp-area-${esc(area)}, #64748B)`;
        return `<span class="exp-pill" style="display:inline-flex;align-items:center;border-radius:9999px;padding:2px 8px;font-size:11px;font-weight:600;background:${colorVar}15;color:${colorVar};white-space:nowrap">${esc(area)}</span>`;
    }

    /** Status flow indicator (8-step requirement lifecycle) */
    const REQ_STATUSES = ['draft','under_review','approved','in_backlog','realized','verified'];
    const REQ_STATUS_DEFERRED = 'deferred';
    const REQ_STATUS_REJECTED = 'rejected';

    function statusFlowIndicator(currentStatus) {
        if (currentStatus === REQ_STATUS_REJECTED) {
            return `<div class="exp-status-flow"><span class="exp-status-flow__dot exp-status-flow__dot--rejected" title="Rejected"></span><span style="font-size:11px;color:var(--exp-gap);margin-left:4px;font-weight:600">Rejected</span></div>`;
        }
        if (currentStatus === REQ_STATUS_DEFERRED) {
            return `<div class="exp-status-flow"><span class="exp-status-flow__dot exp-status-flow__dot--deferred" title="Deferred"></span><span style="font-size:11px;color:var(--exp-p4);margin-left:4px;font-weight:600">Deferred</span></div>`;
        }
        const idx = REQ_STATUSES.indexOf(currentStatus);
        const dots = REQ_STATUSES.map((s, i) => {
            let cls = 'exp-status-flow__dot';
            if (i < idx) cls += ' exp-status-flow__dot--reached';
            if (i === idx) cls += ' exp-status-flow__dot--current';
            return `<span class="${cls}" title="${s.replace(/_/g,' ')}"></span>`;
        });
        const connectors = [];
        for (let i = 0; i < dots.length; i++) {
            connectors.push(dots[i]);
            if (i < dots.length - 1) {
                const reached = i < idx;
                connectors.push(`<span class="exp-status-flow__connector${reached ? ' exp-status-flow__connector--reached' : ''}"></span>`);
            }
        }
        return `<div class="exp-status-flow">${connectors.join('')}</div>`;
    }

    /** Open Item status pill */
    function oiStatusPill(status) {
        const map = {
            open: 'warning', in_progress: 'info', blocked: 'danger', resolved: 'success', closed: 'draft',
        };
        return pill({ label: (status || 'open').replace(/_/g, ' '), variant: map[status] || 'draft' });
    }

    // ── Public API ──────────────────────────────────────────────────
    return {
        esc,
        pill,
        fitBadge,
        fitBarMini,
        kpiBlock,
        filterGroup,
        actionButton,
        countChip,
        levelBadge,
        priorityPill,
        workshopStatusPill,
        wavePill,
        areaPill,
        statusFlowIndicator,
        oiStatusPill,
        // Constants
        PILL_VARIANTS,
        FIT_LABELS,
        REQ_STATUSES,
    };
})();
