var TMTabBar = (() => {
    function esc(str) {
        const el = document.createElement('span');
        el.textContent = str ?? '';
        return el.innerHTML;
    }

    function render(container, options) {
        if (!container) return;
        const { tabs = [], active = null, onChange = null } = options || {};
        container.innerHTML = `
            <div class="tm-tabbar">
                ${tabs.map(t => `
                    <button class="tm-tabbar__item ${t.id === active ? 'is-active' : ''}" data-tab-id="${esc(t.id)}">${esc(t.label)}</button>
                `).join('')}
            </div>
        `;
        if (typeof onChange === 'function') {
            container.querySelectorAll('[data-tab-id]').forEach(btn => {
                btn.addEventListener('click', () => onChange(btn.dataset.tabId));
            });
        }
    }

    return { render };
})();
