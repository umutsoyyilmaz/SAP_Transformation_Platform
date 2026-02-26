/* UI-S02-T04 — PGSkeleton: Loading skeleton animation */
const PGSkeleton = (() => {
    /**
     * Single row skeleton block.
     * @param {number} [widthPct=100] — Width (%)
     * @param {number} [heightPx=14] — Height (px)
     * @returns {string} HTML
     */
    function line(widthPct, heightPx) {
        widthPct = widthPct !== undefined ? widthPct : 100;
        heightPx = heightPx !== undefined ? heightPx : 14;
        return `<div class="pg-skeleton" style="width:${widthPct}%;height:${heightPx}px"></div>`;
    }

    /**
     * Table row skeleton.
     * @param {number} [rows=5] — Row count
     * @param {number} [cols=4] — Column count
     * @returns {string} HTML
     */
    function table(rows, cols) {
        rows = rows || 5;
        cols = cols || 4;
        const header = `<div class="pg-skeleton-row">${Array(cols).fill(line(80, 12)).join('')}</div>`;
        const rowHtml = Array(rows).fill(0).map(() => {
            const cells = Array(cols).fill(0).map(() => line(Math.floor(Math.random() * 40 + 50), 12)).join('');
            return `<div class="pg-skeleton-row">${cells}</div>`;
        }).join('');
        return `<div class="pg-skeleton-table">${header}${rowHtml}</div>`;
    }

    /**
     * KPI card skeleton.
     * @returns {string} HTML
     */
    function card() {
        return `
            <div class="pg-skeleton-card">
                ${line(40, 16)}
                ${line(100, 12)}
                ${line(75, 12)}
                ${line(55, 12)}
            </div>
        `;
    }

    /**
     * Grid skeleton for KPI cards (N cards).
     * @param {number} [count=4]
     * @returns {string} HTML
     */
    function cards(count) {
        count = count || 4;
        return `<div class="pg-skeleton-cards">${Array(count).fill(0).map(card).join('')}</div>`;
    }

    return { line, table, card, cards };
})();
