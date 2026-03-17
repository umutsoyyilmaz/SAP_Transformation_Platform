var HierarchyUI = window.HierarchyUI || (() => {
    'use strict';

    function actionCluster(content, extraClass = '') {
        return `<div class="hierarchy-actions${extraClass ? ` ${extraClass}` : ''}">${content || ''}</div>`;
    }

    function bridgeCard({ testId = '', eyebrow = '', title = '', body = '', actionsHtml = '' } = {}) {
        return `
            <div class="card hierarchy-bridge"${testId ? ` data-testid="${testId}"` : ''}>
                <div class="hierarchy-bridge__header">
                    <div class="hierarchy-bridge__copy">
                        ${eyebrow ? `<div class="hierarchy-bridge__eyebrow">${eyebrow}</div>` : ''}
                        ${title ? `<div class="hierarchy-bridge__title">${title}</div>` : ''}
                        ${body ? `<p class="hierarchy-bridge__body">${body}</p>` : ''}
                    </div>
                    ${actionsHtml ? actionCluster(actionsHtml, 'hierarchy-actions--top') : ''}
                </div>
            </div>
        `;
    }

    function loading({ label = 'Loading hierarchy…', icon = '⏳' } = {}) {
        return `
            <div class="hierarchy-loading" data-testid="hierarchy-loading">
                <div class="hierarchy-loading__content">
                    <div class="hierarchy-loading__icon">${icon}</div>
                    <div class="hierarchy-loading__label">${label}</div>
                </div>
            </div>
        `;
    }

    function emptyState({ testId = '', icon = '📋', title = '', text = '', actionsHtml = '' } = {}) {
        return `
            <div class="hierarchy-empty"${testId ? ` data-testid="${testId}"` : ''}>
                <div class="hierarchy-empty__icon">${icon}</div>
                <div class="hierarchy-empty__title">${title}</div>
                ${text ? `<p class="hierarchy-empty__text">${text}</p>` : ''}
                ${actionsHtml ? actionCluster(actionsHtml, 'hierarchy-actions--center') : ''}
            </div>
        `;
    }

    return {
        actionCluster,
        bridgeCard,
        loading,
        emptyState,
    };
})();

window.HierarchyUI = HierarchyUI;
