/* GovernanceUI — shared shell for RAID and Reports */
const GovernanceUI = (() => {
    'use strict';

    const NAV_ITEMS = [
        {
            id: 'raid',
            label: 'RAID',
            sublabel: 'Cross-project risks, actions, issues, and decisions',
            icon: '🛡',
        },
        {
            id: 'reports',
            label: 'Reports',
            sublabel: 'Library, snapshots, and SteerCo report lifecycle',
            icon: '▤',
        },
    ];

    function esc(value) {
        const d = document.createElement('div');
        d.textContent = value ?? '';
        return d.innerHTML;
    }

    function _chip(label, value, variant = 'neutral') {
        return `
            <span class="workspace-chip workspace-chip--${variant}">
                <span class="workspace-chip__label">${esc(label)}</span>
                <span class="workspace-chip__value">${esc(value || '—')}</span>
            </span>
        `;
    }

    function _valueKind(value) {
        const text = String(value ?? '—').trim();
        if (!text) return 'empty';
        if (/^[-+]?[\d.,]+%?$/.test(text)) return 'numeric';
        if (/^\d+\/\d+$/.test(text)) return 'ratio';
        return 'text';
    }

    function nav(current) {
        return `
            <div class="workspace-nav" data-testid="governance-nav">
                ${NAV_ITEMS.map((item) => `
                    <button
                        type="button"
                        class="workspace-nav__item${item.id === current ? ' workspace-nav__item--active' : ''}"
                        data-governance-view="${item.id}"
                        ${item.id === current ? 'aria-current="page"' : ''}
                        onclick="App.navigate('${item.id}')"
                    >
                        <span class="workspace-nav__icon" aria-hidden="true">${item.icon}</span>
                        <span class="workspace-nav__body">
                            <span class="workspace-nav__label">${esc(item.label)}</span>
                            <span class="workspace-nav__sub">${esc(item.sublabel)}</span>
                        </span>
                    </button>
                `).join('')}
            </div>
        `;
    }

    function spotlightCard(opts = {}) {
        const kind = _valueKind(opts.value);
        return `
            <div class="workspace-spotlight-card workspace-spotlight-card--${kind}">
                <div class="workspace-spotlight-card__value">${esc(String(opts.value ?? '—'))}</div>
                <div class="workspace-spotlight-card__label">${esc(opts.label || '')}</div>
                ${opts.sub ? `<div class="workspace-spotlight-card__sub">${esc(opts.sub)}</div>` : ''}
            </div>
        `;
    }

    function shell(opts = {}) {
        const context = opts.context || {};
        const chips = [
            context.program ? _chip('Program', context.program, 'primary') : '',
            context.project ? _chip('Project', context.project, 'neutral') : '',
            context.status ? _chip('Status', context.status, 'status') : '',
            context.phase ? _chip('Focus', context.phase, 'neutral') : '',
        ].filter(Boolean).join('');

        return `
            <div class="workspace-page governance-page" data-testid="${esc(opts.testId || 'governance-page')}" data-workspace="${esc(opts.current || '')}">
                <div class="pg-view-header workspace-view-header">
                    ${opts.breadcrumbs ? PGBreadcrumb.html(opts.breadcrumbs) : ''}
                    <div class="workspace-hero">
                        <div class="workspace-hero__content">
                            <div class="workspace-eyebrow">${esc(opts.eyebrow || 'Governance')}</div>
                            <div class="workspace-hero__heading-row">
                                <div>
                                    <h1 class="workspace-title">${esc(opts.title || '')}</h1>
                                    ${opts.subtitle ? `<p class="workspace-subtitle">${esc(opts.subtitle)}</p>` : ''}
                                </div>
                                ${opts.actionsHtml ? `<div class="workspace-actions">${opts.actionsHtml}</div>` : ''}
                            </div>
                        </div>
                        <div class="workspace-context" data-testid="governance-context">
                            ${chips}
                        </div>
                    </div>
                    ${nav(opts.current)}
                </div>
                ${Array.isArray(opts.spotlights) && opts.spotlights.length
                    ? `<div class="workspace-spotlight-grid">${opts.spotlights.map(spotlightCard).join('')}</div>`
                    : ''}
                ${opts.preBodyHtml || ''}
                <div class="workspace-body">
                    ${opts.bodyHtml || ''}
                </div>
            </div>
        `;
    }

    return { shell, nav, spotlightCard };
})();
