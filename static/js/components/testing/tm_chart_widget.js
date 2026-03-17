/* F1 — TMChartWidget: Dashboard chart component (bar, line, pie, donut) using Chart.js */
var TMChartWidget = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    /**
     * Render a chart inside a container.
     * @param {HTMLElement} container
     * @param {Object}  config
     * @param {string}  config.type      — 'bar'|'line'|'pie'|'doughnut'|'radar'
     * @param {string}  config.title     — chart title
     * @param {Array}   config.labels    — x-axis labels
     * @param {Array}   config.datasets  — [{label, data:[], backgroundColor?, borderColor?}]
     * @param {Object}  [config.options] — extra Chart.js options
     * @param {string}  [config.height]  — canvas height (default '240px')
     * @returns {Object|null} Chart.js instance or null if Chart is unavailable
     */
    function render(container, config) {
        if (!container) return null;
        const {
            type = 'bar',
            title = '',
            labels = [],
            datasets = [],
            options = {},
            height = '240px',
        } = config || {};

        container.innerHTML = `
            <div class="tm-chart-widget">
                ${title ? `<div class="tm-chart-widget__title">${esc(title)}</div>` : ''}
                <div class="tm-chart-widget__canvas-wrap">
                    <canvas id="tmChart_${Date.now()}" style="height:${height};width:100%"></canvas>
                </div>
            </div>
        `;

        const canvas = container.querySelector('canvas');
        if (!canvas) return null;

        // Use Chart.js if available
        if (typeof Chart !== 'undefined') {
            return new Chart(canvas.getContext('2d'), {
                type,
                data: { labels, datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                    },
                    ...options,
                },
            });
        }

        // Fallback: simple text summary
        canvas.parentElement.innerHTML = `<div class="tm-chart-widget__fallback">
            <p style="color:var(--tm-text-tertiary);font-size:12px">Chart.js not loaded. Data: ${labels.length} labels, ${datasets.length} series.</p>
        </div>`;
        return null;
    }

    return { render };
})();
