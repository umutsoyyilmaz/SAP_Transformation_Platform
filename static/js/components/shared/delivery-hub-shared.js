/* DeliveryHubUI — shared secondary navigation for Build and Release hubs */
const DeliveryHubUI = (() => {
    'use strict';

    const HUBS = {
        build: {
            testId: 'build-hub-nav',
            items: [
                { id: 'backlog', label: 'Backlog', sublabel: 'WRICEF backlog, board, and sprint planning', icon: '⚙' },
                { id: 'integration', label: 'Integration Factory', sublabel: 'Interfaces, waves, and connectivity status', icon: '⇄' },
                { id: 'data-factory', label: 'Data Factory', sublabel: 'Migration objects, cleansing, and load cycles', icon: '◫' },
            ],
        },
        release: {
            testId: 'release-hub-nav',
            items: [
                { id: 'cutover', label: 'Cutover', sublabel: 'Plans, runbook, rehearsals, and go/no-go pack', icon: '▲' },
            ],
        },
    };

    function esc(value) {
        const d = document.createElement('div');
        d.textContent = value ?? '';
        return d.innerHTML;
    }

    function nav(hubId, current) {
        const hub = HUBS[hubId];
        if (!hub) return '';
        return `
            <div class="workspace-nav" data-testid="${esc(hub.testId)}">
                ${hub.items.map((item) => `
                    <button
                        type="button"
                        class="workspace-nav__item${item.id === current ? ' workspace-nav__item--active' : ''}"
                        data-delivery-view="${item.id}"
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

    return { nav };
})();
