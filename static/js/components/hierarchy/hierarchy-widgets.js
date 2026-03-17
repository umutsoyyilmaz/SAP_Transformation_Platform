var HierarchyWidgets = window.HierarchyWidgets || (() => {
    'use strict';

    function filterToolbar({
        id,
        searchPlaceholder = 'Search...',
        searchValue = '',
        onSearch = '',
        onChange = '',
        filters = [],
        actionsHtml = '',
        testId = '',
    } = {}) {
        return `
            <div class="hierarchy-filter-toolbar"${testId ? ` data-testid="${testId}"` : ''}>
                ${ExpUI.filterBar({
                    id,
                    searchPlaceholder,
                    searchValue,
                    onSearch,
                    onChange,
                    filters,
                    actionsHtml,
                })}
            </div>
        `;
    }

    function treeShell({
        bodyHtml = '',
        footerHtml = '',
        emptyText = 'No results found.',
        testId = '',
    } = {}) {
        const safeBody = bodyHtml && bodyHtml.trim()
            ? bodyHtml
            : `<div class="hierarchy-tree-shell__empty">${emptyText}</div>`;

        return `
            <div class="card hierarchy-tree-shell"${testId ? ` data-testid="${testId}"` : ''}>
                <div class="hierarchy-tree-shell__body">${safeBody}</div>
                ${footerHtml ? `<div class="hierarchy-tree-shell__footer">${footerHtml}</div>` : ''}
            </div>
        `;
    }

    function detailPanel({
        headerHtml = '',
        tabsHtml = '',
        contentHtml = '',
        collapsed = false,
        testId = '',
    } = {}) {
        return `
            <div class="exp-layout-split__panel hierarchy-detail-panel${collapsed ? ' exp-layout-split__panel--collapsed hierarchy-detail-panel--collapsed' : ''}" id="expDetailPanel"${testId ? ` data-testid="${testId}"` : ''}>
                ${collapsed ? '' : `
                    <div class="hierarchy-detail-panel__header">${headerHtml}</div>
                    ${tabsHtml ? `<div class="hierarchy-detail-panel__tabs">${tabsHtml}</div>` : ''}
                    <div class="hierarchy-detail-panel__content">${contentHtml}</div>
                `}
            </div>
        `;
    }

    function modalFrame({
        testId = '',
        title = '',
        subtitle = '',
        bodyHtml = '',
        footerHtml = '',
        maxWidth = '720px',
        compact = false,
    } = {}) {
        return `
            <div class="hierarchy-modal${compact ? ' hierarchy-modal--compact' : ''}"${testId ? ` data-testid="${testId}"` : ''} style="max-width:${maxWidth}">
                <div class="hierarchy-modal__header">
                    <div>
                        ${title ? `<h2 class="hierarchy-modal__title">${title}</h2>` : ''}
                        ${subtitle ? `<p class="hierarchy-modal__subtitle">${subtitle}</p>` : ''}
                    </div>
                </div>
                <div class="hierarchy-modal__body">${bodyHtml}</div>
                ${footerHtml ? `<div class="hierarchy-modal__footer">${footerHtml}</div>` : ''}
            </div>
        `;
    }

    function choiceGrid({ testId = '', cards = [] } = {}) {
        return `
            <div class="hierarchy-choice-grid"${testId ? ` data-testid="${testId}"` : ''}>
                ${cards.map((card) => `
                    <button
                        type="button"
                        class="card hierarchy-choice-card${card.comingSoon ? ' hierarchy-choice-card--coming' : ''}"
                        onclick="${card.onclick || ''}"
                    >
                        ${card.badge ? `<span class="hierarchy-choice-card__badge">${card.badge}</span>` : ''}
                        <div class="hierarchy-choice-card__icon">${card.icon || '📋'}</div>
                        <div class="hierarchy-choice-card__title">${card.title || ''}</div>
                        <div class="hierarchy-choice-card__body">${card.body || ''}</div>
                        ${card.footerHtml ? `<div class="hierarchy-choice-card__footer">${card.footerHtml}</div>` : ''}
                    </button>
                `).join('')}
            </div>
        `;
    }

    return {
        filterToolbar,
        treeShell,
        detailPanel,
        modalFrame,
        choiceGrid,
    };
})();

window.HierarchyWidgets = HierarchyWidgets;
