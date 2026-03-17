var HierarchyRenderers = window.HierarchyRenderers || (() => {
    'use strict';

    function treeChevron({
        hasChildren = false,
        expanded = false,
        onclick = '',
        className = '',
        openClass = '',
        leafClass = '',
    } = {}) {
        if (!hasChildren) {
            const leafClasses = leafClass || `hierarchy-tree-chevron hierarchy-tree-chevron--leaf${className ? ` ${className}` : ''}`;
            return `<span class="${leafClasses}"></span>`;
        }
        return `<span class="hierarchy-tree-chevron${expanded ? ' hierarchy-tree-chevron--open' : ''}${className ? ` ${className}` : ''}${expanded && openClass ? ` ${openClass}` : ''}"${onclick ? ` onclick="${onclick}"` : ''}>▶</span>`;
    }

    function levelToken({
        label = '',
        className = '',
        labelClass = '',
        style = '',
        attrs = '',
    } = {}) {
        return `
            <span class="hierarchy-level-token${className ? ` ${className}` : ''}"${style ? ` style="${style}"` : ''}${attrs ? ` ${attrs}` : ''}>
                <span class="hierarchy-level-token__label${labelClass ? ` ${labelClass}` : ''}">${label}</span>
            </span>
        `;
    }

    function treeRow({
        wrapperClass = '',
        attrs = '',
        rowClass = '',
        rowStyle = '',
        chevronHtml = '',
        leadingHtml = '',
        codeHtml = '',
        codeClass = '',
        codeTag = 'code',
        nameHtml = '',
        nameClass = '',
        nameAttrs = '',
        metaHtml = '',
        metaClass = '',
        actionsHtml = '',
        actionsClass = '',
        childrenHtml = '',
    } = {}) {
        const wrapperClassAttr = wrapperClass ? ` class="${wrapperClass}"` : '';
        const rowClassAttr = rowClass ? ` class="${rowClass}"` : '';
        const codeClassAttr = codeClass ? ` class="${codeClass}"` : '';
        const nameClassAttr = nameClass ? ` class="${nameClass}"` : '';
        const metaClassAttr = metaClass ? ` class="${metaClass}"` : '';
        const actionsClassAttr = actionsClass ? ` class="${actionsClass}"` : '';
        return `
            <div${wrapperClassAttr}${attrs ? ` ${attrs}` : ''}>
                <div${rowClassAttr}${rowStyle ? ` style="${rowStyle}"` : ''}>
                    ${chevronHtml}
                    ${leadingHtml || ''}
                    ${codeHtml ? `<${codeTag}${codeClassAttr}>${codeHtml}</${codeTag}>` : ''}
                    ${nameHtml ? `<span${nameClassAttr}${nameAttrs ? ` ${nameAttrs}` : ''}>${nameHtml}</span>` : ''}
                    ${metaHtml ? `<span${metaClassAttr}>${metaHtml}</span>` : ''}
                    ${actionsHtml ? `<span${actionsClassAttr}>${actionsHtml}</span>` : ''}
                </div>
                ${childrenHtml || ''}
            </div>
        `;
    }

    function tableCell({
        html = '',
        className = '',
        attrs = '',
        tag = 'td',
    } = {}) {
        return `<${tag}${className ? ` class="${className}"` : ''}${attrs ? ` ${attrs}` : ''}>${html}</${tag}>`;
    }

    function tableRow({
        cells = [],
        rowClass = '',
        onclick = '',
        attrs = '',
    } = {}) {
        return `<tr${rowClass ? ` class="${rowClass}"` : ''}${onclick ? ` onclick="${onclick}"` : ''}${attrs ? ` ${attrs}` : ''}>${cells.map((cell) => tableCell(cell)).join('')}</tr>`;
    }

    function tableCard({
        tableHtml = '',
        wrapperClass = 'card hierarchy-table-card',
        bodyClass = 'hierarchy-table-card__scroll',
        testId = '',
    } = {}) {
        return `
            <div class="${wrapperClass}"${testId ? ` data-testid="${testId}"` : ''}>
                <div class="${bodyClass}">
                    ${tableHtml}
                </div>
            </div>
        `;
    }

    function detailSection({
        title = '',
        bodyHtml = '',
        className = '',
        testId = '',
    } = {}) {
        return `
            <div class="exp-detail-section${className ? ` ${className}` : ''}"${testId ? ` data-testid="${testId}"` : ''}>
                ${title ? `<div class="exp-detail-section__title">${title}</div>` : ''}
                ${bodyHtml}
            </div>
        `;
    }

    function detailRow({
        label = '',
        valueHtml = '',
        className = '',
        labelClass = '',
        valueClass = '',
    } = {}) {
        return `
            <div class="exp-detail-row${className ? ` ${className}` : ''}">
                <span class="exp-detail-row__label${labelClass ? ` ${labelClass}` : ''}">${label}</span>
                <span class="exp-detail-row__value${valueClass ? ` ${valueClass}` : ''}">${valueHtml}</span>
            </div>
        `;
    }

    function detailCopy({
        text = '',
        className = '',
    } = {}) {
        return `<p class="hierarchy-detail-copy${className ? ` ${className}` : ''}">${text}</p>`;
    }

    function detailActions({
        actionsHtml = '',
        className = '',
    } = {}) {
        return `<div class="hierarchy-detail-actions${className ? ` ${className}` : ''}">${actionsHtml}</div>`;
    }

    function detailLegend({
        items = [],
        className = '',
    } = {}) {
        return `
            <div class="hierarchy-detail-legend${className ? ` ${className}` : ''}">
                ${items.map((item) => `
                    <span class="hierarchy-detail-legend__item${item.tone ? ` hierarchy-detail-legend__item--${item.tone}` : ''}">
                        ${item.label || item.html || ''}
                    </span>
                `).join('')}
            </div>
        `;
    }

    return {
        treeChevron,
        levelToken,
        treeRow,
        tableCell,
        tableRow,
        tableCard,
        detailSection,
        detailRow,
        detailCopy,
        detailActions,
        detailLegend,
    };
})();

window.HierarchyRenderers = HierarchyRenderers;
