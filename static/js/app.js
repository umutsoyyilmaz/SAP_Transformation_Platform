/**
 * SAP Transformation Management Platform
 * SPA Router — Handles sidebar navigation and view rendering.
 */

const App = (() => {
    // ── Utility ──────────────────────────────────────────────────────────
    function esc(str) {
        const d = document.createElement('div');
        d.textContent = str ?? '';
        return d.innerHTML;
    }

    // ── Chart references for cleanup ─────────────────────────────────
    let _charts = [];

    function _destroyCharts() {
        _charts.forEach(c => { try { c.destroy(); } catch {} });
        _charts = [];
    }

    // ── View registry ────────────────────────────────────────────────────
    const views = {
        dashboard:    () => renderDashboard(),
        'executive-cockpit': () => ExecutiveCockpitView.render(),
        programs:     () => ProgramView.render(),
        // Legacy SCOPE views removed — FE-Sprint 1
        backlog:      () => BacklogView.render(),
        'test-planning':      () => TestPlanningView.render(),
        'test-case-detail':   (id) => TestCaseDetailView.render(id),
        'test-execution':     () => TestExecutionView.render(),
        'defect-management':  () => DefectManagementView.render(),
        'approvals':          () => ApprovalsView.render(),
        integration:  () => IntegrationView.render(),
        'data-factory': () => DataFactoryView.render(),
        cutover:      () => CutoverView.render(),
        raid:         () => RaidView.render(),
        reports:      () => ReportsView.render(),
        'dashboard-f5': () => DashboardView.render(),
        'suite-folders': () => SuiteFoldersView.render(),
        'env-matrix': () => EnvMatrixView.render(),
        'bdd-editor': () => BddEditorView.render(),
        'data-driven': () => DataDrivenView.render(),
        'exploratory': () => ExploratoryView.render(),
        'evidence': () => EvidenceCaptureView.render(),
        'custom-fields': () => CustomFieldsView.render(),
        'integrations': () => IntegrationsView.init(window.currentProgramId),
        'observability': () => ObservabilityView.init(),
        'gate-criteria': () => GateCriteriaView.render(document.getElementById('main-content')),
        'discover':     () => DiscoverView.render(document.getElementById('mainContent')),
        'timeline':     () => TimelineView.render(document.getElementById('mainContent')),
        'raci':         () => RaciView.render(document.getElementById('mainContent')),
        'project-setup': () => ProjectSetupView.render(),
        'ai-insights': () => AIInsightsView.render(),
        'ai-query':   () => AIQueryView.render(),
        'ai-admin':   () => AIAdminView.render(),
        // Explore Phase views
        'explore-dashboard':       () => ExploreDashboardView.render(),
        'explore-hierarchy':       () => ExploreHierarchyView.render(),
        'explore-workshops':       () => ExploreWorkshopHubView.render(),
        'explore-workshop-detail': () => ExploreWorkshopDetailView.render(),
        'explore-requirements':    () => ExploreRequirementHubView.render(),
    };

    let currentView = 'dashboard';

    // ── Program Context ─────────────────────────────────────────────────
    // Views that require a program to be selected
    const programRequiredViews = new Set([
        'executive-cockpit',
        'backlog', 'test-planning', 'test-execution', 'defect-management', 'approvals', 'integration', 'data-factory', 'cutover', 'raid',
        'test-case-detail',
        'reports', 'dashboard-f5', 'suite-folders', 'env-matrix', 'bdd-editor', 'data-driven', 'exploratory', 'evidence', 'custom-fields', 'integrations', 'observability', 'gate-criteria', 'project-setup', 'ai-insights', 'ai-query', 'discover', 'timeline', 'raci',
        'explore-dashboard', 'explore-hierarchy', 'explore-workshops', 'explore-workshop-detail', 'explore-requirements',
    ]);

    function getActiveProgram() {
        const stored = localStorage.getItem('sap_active_program');
        if (!stored) return null;
        try { return JSON.parse(stored); } catch { return null; }
    }

    function setActiveProgram(program) {
        if (program) {
            localStorage.setItem('sap_active_program', JSON.stringify({
                id: program.id,
                name: program.name,
                status: program.status,
                project_type: program.project_type,
            }));
        } else {
            localStorage.removeItem('sap_active_program');
        }
        updateProgramBadge();
        updateSidebarState();
        // Refresh team member cache for new program
        TeamMemberPicker.invalidateCache();
    }

    function updateProgramBadge() {
        const prog = getActiveProgram();
        const nameEl = document.getElementById('activeProgramName');
        const badge = document.getElementById('activeProgramBadge');
        if (prog) {
            nameEl.textContent = prog.name;
            badge.classList.add('shell-header__program-badge--active');
            badge.title = `${prog.name} (${prog.project_type}) — Click to switch`;
        } else {
            nameEl.textContent = 'No program selected';
            badge.classList.remove('shell-header__program-badge--active');
            badge.title = 'Click to select a program';
        }
    }

    function updateSidebarState() {
        const hasProgram = !!getActiveProgram();
        document.querySelectorAll('.sidebar__item').forEach(item => {
            const view = item.dataset.view;
            if (programRequiredViews.has(view)) {
                item.classList.toggle('sidebar__item--disabled', !hasProgram);
            }
        });

        // Hide AI suggestion badge button when no program selected
        const suggBtn = document.querySelector('.shell-header__actions .shell-header__icon-btn[title="AI Suggestions"]');
        if (suggBtn) {
            suggBtn.style.opacity = hasProgram ? '1' : '0.3';
            suggBtn.style.pointerEvents = hasProgram ? 'auto' : 'none';
        }
        const suggDropdown = document.getElementById('suggDropdown');
        if (suggDropdown && !hasProgram) suggDropdown.style.display = 'none';
    }

    // ── Navigation ───────────────────────────────────────────────────────
    function navigate(viewName, ...args) {
        if (!views[viewName]) return;

        // Guard: program-required views need an active program
        if (programRequiredViews.has(viewName) && !getActiveProgram()) {
            toast('Please select a program first', 'warning');
            navigate('programs');
            return;
        }

        // Cleanup previous charts
        _destroyCharts();

        currentView = viewName;

        // Update sidebar active state
        document.querySelectorAll('.sidebar__item').forEach(item => {
            item.classList.toggle('active', item.dataset.view === viewName);
        });

        // Render the view
        views[viewName](...args);
    }

    // ── Dashboard ────────────────────────────────────────────────────────
    async function renderDashboard() {
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'Dashboard' }])}
                <h2 class="pg-view-title">Dashboard</h2>
            </div>
            <div id="dashboard-grid" class="pg-dashboard-grid">
                ${PGSkeleton.card()}${PGSkeleton.card()}${PGSkeleton.card()}
            </div>
        `;

        try {
            const [summary, actions, recent] = await Promise.all([
                API.get('/api/v1/dashboard/summary'),
                API.get('/api/v1/dashboard/actions'),
                API.get('/api/v1/dashboard/recent-activity'),
            ]);
            _renderDashboardContent(summary, actions, recent);
        } catch (err) {
            document.getElementById('dashboard-grid').innerHTML =
                PGEmptyState.html({ icon: 'dashboard', title: 'Veri yüklenemedi', description: err.message });
        }
    }

    function _renderDashboardContent(summary, actions, recent) {
        const score = summary.health_score || 0;
        const scoreColor = score >= 75 ? '#16a34a' : score >= 50 ? '#ca8a04' : '#dc2626';
        const circumference = Math.round(2 * Math.PI * 34);

        document.getElementById('dashboard-grid').innerHTML = `
            <!-- Health Score Card -->
            <div class="pg-dash-card pg-dash-card--health">
                <div class="pg-dash-card__header">Program Sağlığı</div>
                <div class="pg-health-score">
                    <svg class="pg-health-score__ring" viewBox="0 0 80 80">
                        <circle cx="40" cy="40" r="34" fill="none" stroke="var(--pg-color-border)" stroke-width="6"/>
                        <circle cx="40" cy="40" r="34" fill="none" stroke="${scoreColor}" stroke-width="6"
                            stroke-dasharray="${Math.round(circumference * score / 100)} ${Math.round(circumference * (1 - score / 100))}"
                            stroke-dashoffset="${Math.round(circumference * 0.25)}"
                            stroke-linecap="round"/>
                        <text x="40" y="40" dominant-baseline="middle" text-anchor="middle"
                            font-size="16" font-weight="700" fill="${scoreColor}">${score}</text>
                    </svg>
                    <div class="pg-health-score__meta">
                        <span style="color:${scoreColor};font-weight:700">${_healthLabel(score)}</span>
                        <span class="pg-health-score__items">${summary.requirements || 0} gereksinim · ${Math.round(summary.test_coverage || 0)}% test</span>
                    </div>
                </div>
            </div>

            <!-- KPI Cards -->
            <div class="pg-dash-kpis">
                ${_kpi('Gereksinim', summary.requirements, 'requirements', 'requirements')}
                ${_kpi('WRICEF', summary.wricef_items, 'backlog', 'build')}
                ${_kpi('Test Case', summary.test_cases, 'test-management', 'test')}
                ${_kpi('Defect', summary.open_defects, 'defects', 'defect')}
                ${_kpi('RAID', summary.open_risks, 'raid', 'raid')}
            </div>

            <!-- Actions -->
            <div class="pg-dash-card pg-dash-card--actions">
                <div class="pg-dash-card__header">Aksiyon Gerektiren</div>
                ${!actions.length
                    ? '<p class="pg-dash-empty">Bekleyen aksiyon yok 🎉</p>'
                    : actions.slice(0, 5).map(a => `
                        <div class="pg-dash-action" onclick="App.navigate('${a.view}')">
                            <span class="pg-dash-action__icon">${PGStatusRegistry.badge(a.severity || 'warning')}</span>
                            <span class="pg-dash-action__text">${esc(a.message)}</span>
                            <span class="pg-dash-action__arrow">→</span>
                        </div>
                    `).join('')
                }
            </div>

            <!-- Recent Activity -->
            <div class="pg-dash-card pg-dash-card--activity">
                <div class="pg-dash-card__header">Son Aktivite <span class="pg-dash-card__meta">24 saat</span></div>
                ${!recent.length
                    ? '<p class="pg-dash-empty">Aktivite bulunamadı</p>'
                    : recent.slice(0, 8).map(r => `
                        <div class="pg-dash-activity-row">
                            <div class="pg-dash-activity-row__avatar">${(r.user_name || 'U')[0].toUpperCase()}</div>
                            <div class="pg-dash-activity-row__body">
                                <span class="pg-dash-activity-row__user">${esc(r.user_name || 'Sistem')}</span>
                                <span class="pg-dash-activity-row__action">${esc(r.action)}</span>
                                <span class="pg-dash-activity-row__object">${esc(r.object_code || '')}</span>
                            </div>
                            <span class="pg-dash-activity-row__time">${_relTime(r.created_at)}</span>
                        </div>
                    `).join('')
                }
            </div>
        `;
    }

    function _kpi(label, value, view, icon) {
        return `
            <div class="pg-kpi-card" onclick="App.navigate('${view}')" role="button" tabindex="0">
                <div class="pg-kpi-card__icon">${typeof PGIcon !== 'undefined' ? PGIcon.html(icon, 20) : ''}</div>
                <div class="pg-kpi-card__value">${value ?? '–'}</div>
                <div class="pg-kpi-card__label">${label}</div>
            </div>
        `;
    }

    function _healthLabel(score) {
        if (score >= 85) return 'Mükemmel';
        if (score >= 70) return 'İyi';
        if (score >= 50) return 'Orta';
        return 'İyileştirme Gerekli';
    }

    function _relTime(iso) {
        if (!iso) return '';
        const diff = Date.now() - new Date(iso).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'Az önce';
        if (mins < 60) return `${mins}d önce`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}s önce`;
        return `${Math.floor(hrs / 24)}g önce`;
    }

    // ── Placeholder for future modules ───────────────────────────────────
    function placeholder(title, sprint) {
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="empty-state">
                <div class="empty-state__icon">🚧</div>
                <div class="empty-state__title">${esc(title)}</div>
                <p>This module will be implemented in <strong>${esc(sprint)}</strong>.</p>
            </div>
        `;
    }

    // ── Toast notifications ──────────────────────────────────────────────
    function toast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    }

    // ── Modal ────────────────────────────────────────────────────────────
    function openModal(html) {
        document.getElementById('modalContainer').innerHTML = html;
        document.getElementById('modalOverlay').classList.add('open');
    }

    function closeModal() {
        document.getElementById('modalOverlay').classList.remove('open');
    }

    // ── Init ─────────────────────────────────────────────────────────────
    function init() {
        // Sidebar click handlers
        document.querySelectorAll('.sidebar__item').forEach(item => {
            item.addEventListener('click', () => {
                const view = item.dataset.view;
                if (view) navigate(view);
            });
        });

        // Close modal on overlay click
        document.getElementById('modalOverlay').addEventListener('click', e => {
            if (e.target.id === 'modalOverlay') closeModal();
        });

        // Close modal on ESC key
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape' && document.getElementById('modalOverlay').classList.contains('open')) {
                closeModal();
            }
        });

        // Initialize notification panel (Sprint 6)
        if (typeof NotificationPanel !== 'undefined') {
            NotificationPanel.init();
        }

        // Initialize AI suggestion badge (Sprint 7)
        if (typeof SuggestionBadge !== 'undefined') {
            SuggestionBadge.init();
        }

        // Auth guard — redirect to login if not authenticated
        if (typeof Auth !== 'undefined' && !Auth.guard()) {
            return; // guard() will redirect
        }

        // Initialize profile dropdown (replaces demo user switcher)
        _initProfileDropdown();

        // Initialize role-based navigation from JWT user
        if (typeof RoleNav !== 'undefined') {
            const user = Auth.getUser();
            if (user) {
                RoleNav.setUser({
                    id: String(user.id),
                    name: user.full_name || user.email,
                    default_role: (user.roles && user.roles[0]) || 'viewer',
                });
            }
            RoleNav.preload();
        }

        // Set up program context from localStorage
        updateProgramBadge();
        updateSidebarState();

        // Initialize sidebar collapse (UI-S03-T03)
        initSidebarCollapse();

        // Render default view
        navigate('dashboard');
    }

    // ── Sidebar Collapse (UI-S03-T03) ─────────────────────────────

    function initSidebarCollapse() {
        const sidebar = document.getElementById('sidebar');
        const collapseBtn = document.getElementById('sidebarCollapseBtn');
        if (!sidebar || !collapseBtn) return;

        const stored = localStorage.getItem('pg_sidebar_collapsed') === 'true';
        if (stored) sidebar.classList.add('sidebar--collapsed');

        collapseBtn.addEventListener('click', () => {
            const isCollapsed = sidebar.classList.toggle('sidebar--collapsed');
            localStorage.setItem('pg_sidebar_collapsed', isCollapsed);
        });
    }

    // ── Profile Dropdown ──────────────────────────────────────────

    function _initProfileDropdown() {
        const btn = document.getElementById('profileBtn');
        const menu = document.getElementById('profileMenu');
        if (!btn || !menu) return;

        // Populate from stored JWT user
        _updateProfileDisplay();

        // Fetch fresh profile from backend (async)
        _refreshProfile();

        // Toggle dropdown
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.classList.toggle('open');
        });

        // Close on outside click
        document.addEventListener('click', () => menu.classList.remove('open'));
    }

    function _updateProfileDisplay() {
        const user = Auth.getUser();
        if (!user) return;

        const fullName = user.full_name || user.email || 'User';
        const initials = _getInitials(fullName);
        const email = user.email || '';
        const roles = user.roles || [];
        const roleName = roles.length ? roles.map(r => r.replace(/_/g, ' ')).join(', ') : 'User';

        const avatarEl = document.getElementById('profileAvatar');
        const nameEl = document.getElementById('profileName');
        const fullNameEl = document.getElementById('profileFullName');
        const emailEl = document.getElementById('profileEmail');
        const roleEl = document.getElementById('profileRole');

        if (avatarEl) avatarEl.textContent = initials;
        if (nameEl) nameEl.textContent = fullName.split(' ')[0]; // First name only
        if (fullNameEl) fullNameEl.textContent = fullName;
        if (emailEl) emailEl.textContent = email;
        if (roleEl) roleEl.textContent = roleName;
    }

    async function _refreshProfile() {
        try {
            const data = await Auth.fetchUserProfile();
            if (data && data.user) {
                _updateProfileDisplay();
                // Update tenant info
                if (data.tenant) {
                    const tenantEl = document.getElementById('profileTenantName');
                    if (tenantEl) tenantEl.textContent = data.tenant.name || data.tenant.slug;
                }
            }
        } catch { /* ignore — stored user data is fine */ }
    }

    function _getInitials(name) {
        if (!name) return '?';
        const parts = name.trim().split(/\s+/);
        if (parts.length >= 2) {
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }
        return name.substring(0, 2).toUpperCase();
    }

    // Start
    document.addEventListener('DOMContentLoaded', init);

    // Public API
    return {
        navigate, toast, openModal, closeModal,
        getActiveProgram, setActiveProgram,
        updateProgramBadge, updateSidebarState,
    };
})();
