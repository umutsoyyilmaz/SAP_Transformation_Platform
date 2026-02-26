/**
 * Personalized "My Projects" landing view.
 * Shows authorized projects only, with pin/favorite + recent context support.
 */

const MyProjectsView = (() => {
    const PREFS_KEY = 'sap_my_projects_prefs_v1';
    const MAX_RECENT = 8;

    let _projects = [];
    let _renderStartedAt = 0;
    let _firstActionTracked = false;

    function escHtml(s) {
        const d = document.createElement('div');
        d.textContent = s ?? '';
        return d.innerHTML;
    }

    function _tenantId() {
        const user = (typeof Auth !== 'undefined' && Auth.getUser) ? Auth.getUser() : null;
        return user ? user.tenant_id : null;
    }

    function _safeReadPrefs() {
        const raw = localStorage.getItem(PREFS_KEY);
        if (!raw) return { tenant_id: _tenantId(), pinned: [], recent: [] };
        try {
            const parsed = JSON.parse(raw);
            if (!parsed || parsed.tenant_id !== _tenantId()) {
                return { tenant_id: _tenantId(), pinned: [], recent: [] };
            }
            return {
                tenant_id: parsed.tenant_id,
                pinned: Array.isArray(parsed.pinned) ? parsed.pinned : [],
                recent: Array.isArray(parsed.recent) ? parsed.recent : [],
            };
        } catch {
            return { tenant_id: _tenantId(), pinned: [], recent: [] };
        }
    }

    function _writePrefs(prefs) {
        localStorage.setItem(PREFS_KEY, JSON.stringify({
            tenant_id: _tenantId(),
            pinned: prefs.pinned || [],
            recent: prefs.recent || [],
        }));
    }

    function _trackTffa(actionName) {
        if (_firstActionTracked) return;
        _firstActionTracked = true;
        const elapsedMs = Math.max(0, Date.now() - _renderStartedAt);
        const payload = { action: actionName, elapsed_ms: elapsedMs };
        if (typeof Analytics !== 'undefined' && typeof Analytics.track === 'function') {
            try { Analytics.track('ux_time_to_first_action', payload); } catch {}
        }
        window.__uxMetrics = window.__uxMetrics || [];
        window.__uxMetrics.push({ event: 'ux_time_to_first_action', ...payload });
    }

    function _projectIndexById() {
        const map = new Map();
        _projects.forEach((p) => map.set(Number(p.project_id), p));
        return map;
    }

    function _sortByPinnedAndName(list, pinnedIds) {
        return [...list].sort((a, b) => {
            const ap = pinnedIds.has(Number(a.project_id)) ? 0 : 1;
            const bp = pinnedIds.has(Number(b.project_id)) ? 0 : 1;
            if (ap !== bp) return ap - bp;
            if ((a.program_name || '') !== (b.program_name || '')) {
                return (a.program_name || '').localeCompare(b.program_name || '');
            }
            return (a.project_name || '').localeCompare(b.project_name || '');
        });
    }

    function _recordRecent(programId, projectId) {
        const prefs = _safeReadPrefs();
        const filtered = prefs.recent.filter(
            (r) => !(Number(r.program_id) === Number(programId) && Number(r.project_id) === Number(projectId))
        );
        filtered.unshift({
            program_id: Number(programId),
            project_id: Number(projectId),
            ts: Date.now(),
        });
        prefs.recent = filtered.slice(0, MAX_RECENT);
        _writePrefs(prefs);
    }

    function _restoreLastContextIfMissing() {
        const activeProgram = App.getActiveProgram();
        const activeProject = App.getActiveProject();
        if (activeProgram && activeProject) return;

        const prefs = _safeReadPrefs();
        const last = (prefs.recent || [])[0];
        if (!last) return;
        const target = _projects.find(
            (p) => Number(p.program_id) === Number(last.program_id) && Number(p.project_id) === Number(last.project_id)
        );
        if (!target) return;

        App.setActiveProgram({
            id: target.program_id,
            name: target.program_name,
            tenant_id: target.tenant_id,
        });
        App.setActiveProject({
            id: target.project_id,
            name: target.project_name,
            code: target.project_code,
            program_id: target.program_id,
            tenant_id: target.tenant_id,
        });
        if (typeof App.toast === 'function') {
            App.toast(`Last context restored: ${target.program_name} / ${target.project_name}`, 'info');
        }
    }

    async function _openProject(item) {
        _trackTffa('open_project');
        _recordRecent(item.program_id, item.project_id);
        App.setActiveProgram({
            id: item.program_id,
            name: item.program_name,
            tenant_id: item.tenant_id,
        });
        App.setActiveProject({
            id: item.project_id,
            name: item.project_name,
            code: item.project_code,
            program_id: item.program_id,
            tenant_id: item.tenant_id,
        });
        App.navigate('dashboard');
    }

    function _togglePinned(projectId) {
        _trackTffa('pin_toggle');
        const prefs = _safeReadPrefs();
        const pid = Number(projectId);
        if (prefs.pinned.includes(pid)) {
            prefs.pinned = prefs.pinned.filter((id) => Number(id) !== pid);
        } else {
            prefs.pinned.unshift(pid);
        }
        _writePrefs(prefs);
        renderCards();
    }

    function renderCards() {
        const main = document.getElementById('myProjectsGrid');
        if (!main) return;

        const prefs = _safeReadPrefs();
        const pinnedIds = new Set((prefs.pinned || []).map((x) => Number(x)));
        const sorted = _sortByPinnedAndName(_projects, pinnedIds);

        if (!sorted.length) {
            main.innerHTML = PGEmptyState.html({
                icon: 'programs',
                title: 'No accessible projects',
                description: 'You currently have no project access. Contact your tenant admin.',
            });
            return;
        }

        main.innerHTML = `
            <div class="program-card-grid">
                ${sorted.map((p) => `
                    <div class="program-card" style="cursor:default">
                        <div class="program-card__header">
                            <div class="program-card__title">${escHtml(p.project_name)}</div>
                            ${p.is_default ? '<span class="badge badge-active">DEFAULT</span>' : ''}
                        </div>
                        <div class="program-card__body">
                            <div class="program-card__meta">
                                <span>📁 ${escHtml(p.program_name)}</span>
                                <span>🏷️ ${escHtml(p.project_code || 'PRJ')}</span>
                                <span>📊 ${escHtml(p.project_status || 'active')}</span>
                            </div>
                        </div>
                        <div class="program-card__actions">
                            <button class="btn btn-secondary btn-sm" onclick="MyProjectsView.togglePinned(${Number(p.project_id)})">
                                ${pinnedIds.has(Number(p.project_id)) ? '★ Pinned' : '☆ Pin'}
                            </button>
                            <button class="btn btn-primary btn-sm" onclick="MyProjectsView.openProject(${Number(p.project_id)})">Open</button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        const projectIndex = _projectIndexById();
        const recent = (prefs.recent || [])
            .map((r) => projectIndex.get(Number(r.project_id)))
            .filter(Boolean)
            .slice(0, 5);
        const recentWrap = document.getElementById('myProjectsRecent');
        if (recentWrap) {
            recentWrap.innerHTML = recent.length
                ? recent.map((r) => `
                    <button class="btn btn-secondary btn-sm" onclick="MyProjectsView.openProject(${Number(r.project_id)})">
                        ${escHtml(r.program_name)} / ${escHtml(r.project_name)}
                    </button>
                `).join(' ')
                : '<span style="color:var(--sap-text-secondary)">No recent context</span>';
        }
    }

    async function render() {
        _renderStartedAt = Date.now();
        _firstActionTracked = false;
        const main = document.getElementById('mainContent');
        main.innerHTML = `
            <div class="pg-view-header">
                ${PGBreadcrumb.html([{ label: 'My Projects' }])}
                <h2 class="pg-view-title">My Projects</h2>
                <p style="color:var(--sap-text-secondary);margin-top:4px">Only projects you are authorized to access are shown.</p>
            </div>
            <div class="card" style="margin-bottom:12px">
                <strong>Recent Contexts</strong>
                <div id="myProjectsRecent" style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px"></div>
            </div>
            <div id="myProjectsGrid"><div style="text-align:center;padding:40px"><div class="spinner"></div></div></div>
        `;

        try {
            const res = await API.get('/me/projects');
            _projects = Array.isArray(res?.items) ? res.items : [];
            _restoreLastContextIfMissing();
            renderCards();
        } catch (err) {
            document.getElementById('myProjectsGrid').innerHTML = PGEmptyState.html({
                icon: 'programs',
                title: 'Failed to load projects',
                description: err?.message || 'Unknown error',
            });
        }
    }

    function openProject(projectId) {
        const p = _projects.find((x) => Number(x.project_id) === Number(projectId));
        if (!p) {
            App.toast('Unauthorized or missing project link', 'warning');
            return;
        }
        return _openProject(p);
    }

    function togglePinned(projectId) {
        _togglePinned(projectId);
    }

    // App-level hook for any context switch.
    function recordRecentContext(programId, projectId) {
        if (!programId || !projectId) return;
        _recordRecent(programId, projectId);
    }

    return {
        render,
        openProject,
        togglePinned,
        recordRecentContext,
    };
})();
