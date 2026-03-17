const ProjectSetupShell = (() => {
    const TABS = [
        { id: 'project-info', label: '📌 Project Info' },
        { id: 'methodology', label: '🧭 Methodology' },
        { id: 'team', label: '👥 Team' },
        { id: 'workstreams', label: '🔧 Workstreams' },
        { id: 'committees', label: '🏛️ Committees' },
        { id: 'timeline', label: '📅 Timeline' },
        { id: 'scope-hierarchy', label: '🏗️ Scope & Hierarchy' },
    ];

    function tabs() {
        return TABS.slice();
    }

    function normalizeTab(tab) {
        if (tab === 'governance') return 'workstreams';
        return TABS.some((item) => item.id === tab) ? tab : 'project-info';
    }

    function renderTabs(activeTab) {
        const normalized = normalizeTab(activeTab);
        return `
            <div class="exp-tabs" data-testid="project-setup-tabs" style="margin-bottom:16px">
                ${TABS.map((tab) => `
                    <button
                        class="exp-tab ${normalized === tab.id ? 'exp-tab--active' : ''}"
                        data-setup-tab="${tab.id}"
                        onclick="ProjectSetupView.switchTab('${tab.id}')"
                    >${tab.label}</button>
                `).join('')}
            </div>
        `;
    }

    function renderProfileStrip(project) {
        if (!project) return '';
        const items = [
            { label: 'Methodology',   value: project.methodology || 'Not set',        icon: '🧭', iconBg: '#eff6ff', iconColor: '#3b82f6' },
            { label: 'Project Type',  value: project.project_type || 'Not set',        icon: '🏗️', iconBg: '#f0fdf4', iconColor: '#16a34a' },
            { label: 'Deployment',    value: project.deployment_option || 'Not set',   icon: '☁️', iconBg: '#faf5ff', iconColor: '#9333ea' },
            { label: 'Wave',          value: project.wave_number != null ? `Wave ${project.wave_number}` : 'Not set', icon: '〜', iconBg: '#fff7ed', iconColor: '#ea580c' },
        ];
        return `
            <div class="ps-profile-strip" data-testid="project-setup-profile">
                ${items.map((item) => `
                    <div class="ps-profile-card">
                        <span class="ps-profile-card__icon" style="background:${item.iconBg};color:${item.iconColor}">${item.icon}</span>
                        <div class="ps-profile-card__body">
                            <div class="ps-profile-card__value">${item.value}</div>
                            <div class="ps-profile-card__label">${item.label}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    return {
        tabs,
        normalizeTab,
        renderTabs,
        renderProfileStrip,
    };
})();
