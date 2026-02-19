const TestCaseDetailView = (() => {
    let _caseId = null;
    let _activeTab = 'details';
    let _treeMode = 'suite';
    let _isEditing = false;
    let _draft = null;
    let _draftSteps = [];
    let _tc = null;
    let _catalog = [];
    let _suites = [];
    let _steps = [];
    let _derived = null;
    let _deps = [];
    let _perf = [];
    let _defects = [];
    let _executionRows = [];
    let _execLoaded = false;
    let _versions = [];
    let _versionDiff = null;
    let _versionFrom = null;
    let _versionTo = null;

    function _esc(str) {
        const d = document.createElement('div');
        d.textContent = str ?? '';
        return d.innerHTML;
    }

    function _parseHash() {
        const hash = window.location.hash || '';
        const m = hash.match(/^#test-case-detail\/(\d+)(?:\/tab\/([a-z-]+))?/);
        if (!m) return { caseId: null, tab: null };
        return { caseId: Number(m[1]), tab: m[2] || null };
    }

    function _updateHash() {
        if (!_caseId) return;
        const url = `#test-case-detail/${_caseId}/tab/${_activeTab}`;
        try {
            window.history.replaceState(null, '', url);
        } catch {
            window.location.hash = url;
        }
    }

    async function render(caseId) {
        const pid = TestingShared.pid;
        if (!pid) {
            App.toast('Please select a program first', 'warning');
            App.navigate('programs');
            return;
        }

        const fromHash = _parseHash();
        _caseId = Number(caseId) || fromHash.caseId || null;
        _activeTab = fromHash.tab || 'details';
        _treeMode = 'suite';
        _isEditing = false;
        _draft = null;
        _draftSteps = [];
        _executionRows = [];
        _execLoaded = false;
        _versions = [];
        _versionDiff = null;
        _versionFrom = null;
        _versionTo = null;

        const main = document.getElementById('mainContent');
        main.innerHTML = '<div class="spinner"></div>';

        try {
            await _loadData(pid, _caseId);
            if (!_tc) {
                main.innerHTML = '<div class="empty-state"><div class="empty-state__title">Test case not found</div></div>';
                return;
            }
            _renderShell();
            _renderTree();
            _renderTab();
            _updateHash();
        } catch (err) {
            console.error('TestCaseDetailView render error:', err);
            main.innerHTML = `<div class="empty-state"><div class="empty-state__title">Failed to load test case</div><p>${_esc(err?.message || 'Unknown error')}</p></div>`;
        }
    }

    async function _loadData(pid, id) {
        const [tcRes, catalogRes, suitesRes, defectsRes] = await Promise.all([
            API.get(`/testing/catalog/${id}`),
            API.get(`/programs/${pid}/testing/catalog`).catch(() => ({ items: [] })),
            API.get(`/programs/${pid}/testing/suites`).catch(() => ({ items: [] })),
            API.get(`/programs/${pid}/testing/defects`).catch(() => ({ items: [] })),
        ]);

        _tc = tcRes || null;
        _catalog = catalogRes?.items || catalogRes || [];
        _suites = suitesRes?.items || suitesRes || [];
        _defects = defectsRes?.items || defectsRes || [];

        const [stepsRes, derivedRes, depsRes, perfRes] = await Promise.all([
            API.get(`/testing/catalog/${id}/steps`).catch(() => ([])),
            API.get(`/testing/catalog/${id}/traceability-derived`).catch(() => (null)),
            API.get(`/testing/catalog/${id}/dependencies`).catch(() => ({ blocked_by: [], blocks: [] })),
            API.get(`/testing/catalog/${id}/perf-results`).catch(() => ({ items: [] })),
        ]);

        _steps = (stepsRes?.items || stepsRes || []).sort((a, b) => (a.step_no || 0) - (b.step_no || 0));
        _derived = derivedRes;
        _deps = [
            ...((depsRes?.blocked_by || []).map(x => ({ ...x, direction: 'blocked_by' }))),
            ...((depsRes?.blocks || []).map(x => ({ ...x, direction: 'blocks' }))),
        ];
        _perf = perfRes?.items || perfRes || [];
    }

    async function _ensureExecutionRows() {
        if (_execLoaded) return;
        const pid = TestingShared.pid;
        const planRes = await API.get(`/programs/${pid}/testing/plans`).catch(() => ({ items: [] }));
        const plans = planRes?.items || planRes || [];

        const details = await Promise.all(plans.map(p => API.get(`/testing/plans/${p.id}`).catch(() => ({ cycles: [] }))));
        const cycles = details.flatMap(d => d.cycles || []);
        const cycleNameById = {};
        cycles.forEach(c => { cycleNameById[c.id] = c.name || `Cycle #${c.id}`; });

        const execAndRunBatches = await Promise.all(cycles.map(async c => {
            const [executions, runsRes] = await Promise.all([
                API.get(`/testing/cycles/${c.id}/executions`).catch(() => ([])),
                API.get(`/testing/cycles/${c.id}/runs`).catch(() => ([])),
            ]);
            const runs = Array.isArray(runsRes) ? runsRes : (runsRes?.items || []);
            return {
                cycleId: c.id,
                cycleName: cycleNameById[c.id],
                executions: Array.isArray(executions) ? executions : (executions?.items || []),
                runs: runs,
            };
        }));

        _executionRows = execAndRunBatches.flatMap(batch => {
            const fromExec = (batch.executions || [])
                .filter(e => Number(e.test_case_id) === Number(_caseId))
                .map(e => ({
                    kind: 'execution',
                    id: e.id,
                    cycle_id: batch.cycleId,
                    cycle_name: batch.cycleName,
                    result: e.result,
                    actor: e.executed_by || '-',
                    when: e.executed_at || e.created_at || null,
                    notes: e.notes || '',
                    evidence_url: e.evidence_url || '',
                }));

            const fromRuns = (batch.runs || [])
                .filter(r => Number(r.test_case_id) === Number(_caseId))
                .map(r => ({
                    kind: 'run',
                    id: r.id,
                    cycle_id: batch.cycleId,
                    cycle_name: batch.cycleName,
                    result: r.result,
                    actor: r.tester || '-',
                    when: r.finished_at || r.started_at || r.created_at || null,
                    notes: r.notes || '',
                    evidence_url: r.evidence_url || '',
                }));

            return [...fromExec, ...fromRuns];
        }).sort((a, b) => new Date(b.when || 0) - new Date(a.when || 0));

        _execLoaded = true;
    }

    async function _ensureVersions() {
        if (_versions.length) return;
        const rows = await API.get(`/testing/catalog/${_caseId}/versions`).catch(() => []);
        _versions = Array.isArray(rows) ? rows : [];
        if (_versions.length >= 2) {
            _versionTo = _versionTo || _versions[0].version_no;
            _versionFrom = _versionFrom || _versions[1].version_no;
        } else if (_versions.length === 1) {
            _versionTo = _versions[0].version_no;
            _versionFrom = _versions[0].version_no;
        }
    }

    function _renderShell() {
        const main = document.getElementById('mainContent');
        const code = _tc.code || `TC-${_tc.id}`;
        const current = _isEditing ? _draft : _tc;

        main.innerHTML = `
            <div style="margin-bottom:var(--sp-sm)">
                <div id="tcBreadcrumb"></div>
            </div>
            <div class="tm-card" style="padding:var(--sp-md);margin-bottom:var(--sp-sm)">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:var(--sp-sm)">
                    <div style="display:flex;align-items:center;gap:var(--sp-sm)">
                        <h1 style="margin:0;font-size:var(--tm-font-lg)">${_esc(code)}</h1>
                        <span style="color:var(--tm-text-secondary);font-size:var(--tm-font-sm)">${_esc(_tc.title || 'Untitled Test Case')}</span>
                    </div>
                    <div id="tcHeaderToolbar"></div>
                </div>
                <div style="display:flex;gap:var(--sp-md);margin-top:var(--sp-sm);flex-wrap:wrap;align-items:center">
                    <span>${TMStatusBadge.html(current.status || 'draft')}</span>
                    <span>${TMStatusBadge.html((current.test_layer || '').toUpperCase(), {customBg:'#e8f0fe',customFg:'#174ea6'})}</span>
                    <span>${TMStatusBadge.html(current.priority || 'medium')}</span>
                    <span style="font-size:var(--tm-font-xs);color:var(--tm-text-secondary)">Module: <strong>${_esc(current.module || '-')}</strong></span>
                    <span style="font-size:var(--tm-font-xs);color:var(--tm-text-secondary)">Updated: <strong>${_esc((current.updated_at || current.created_at || '-').slice(0, 10))}</strong></span>
                </div>
            </div>

            <div id="tcSplitContainer"></div>
        `;

        // Breadcrumb
        TMBreadcrumbBar.render(document.getElementById('tcBreadcrumb'), {
            items: [
                { label: 'Test Planning', onClick: () => App.navigate('test-planning') },
                { label: 'Test Cases', onClick: () => App.navigate('test-planning') },
                { label: code },
            ],
        });

        // Header toolbar
        TMToolbar.render(document.getElementById('tcHeaderToolbar'), {
            leftActions: _isEditing
                ? [
                    { id: 'cancel', label: 'Cancel', onClick: () => TestCaseDetailView.cancelEdit() },
                    { id: 'save', label: 'Save', primary: true, onClick: () => TestCaseDetailView.saveEdit() },
                  ]
                : [
                    { id: 'edit', label: 'Edit', primary: true, onClick: () => TestCaseDetailView.startEdit() },
                    { id: 'legacy', label: 'Legacy Editor', onClick: () => TestCaseDetailView.openLegacyEditor() },
                  ],
            rightActions: [
                { id: 'back', label: '← Back', onClick: () => App.navigate('test-planning') },
            ],
        });

        // Split pane: tree left, tabbed detail right
        TMSplitPane.mount(document.getElementById('tcSplitContainer'), {
            leftWidth: 260,
            minLeft: 180,
            maxLeft: 400,
            leftHtml: `
                <div style="padding:10px 12px;border-bottom:1px solid var(--tm-border)">
                    <div style="font-weight:700;margin-bottom:8px;font-size:var(--tm-font-sm)">Test Case Tree</div>
                    <div id="tcTreeModeBtns" style="display:flex;gap:6px;flex-wrap:wrap"></div>
                </div>
                <div id="tcDetailTree"></div>
            `,
            rightHtml: `
                <div id="tcTabBarContainer"></div>
                <div id="tcDetailTabContent" style="padding:var(--sp-md)"></div>
            `,
        });

        // Tree mode buttons as toolbar
        TMToolbar.render(document.getElementById('tcTreeModeBtns'), {
            leftActions: [
                { id: 'suite', label: 'By Suite', primary: _treeMode === 'suite', onClick: () => TestCaseDetailView.switchTreeMode('suite') },
                { id: 'l3', label: 'By L3', primary: _treeMode === 'l3', onClick: () => TestCaseDetailView.switchTreeMode('l3') },
                { id: 'layer', label: 'By Layer', primary: _treeMode === 'layer', onClick: () => TestCaseDetailView.switchTreeMode('layer') },
            ],
        });

        // Tab bar using TMTabBar
        TMTabBar.render(document.getElementById('tcTabBarContainer'), {
            tabs: [
                { id: 'details', label: 'Details' },
                { id: 'script', label: 'Test Script' },
                { id: 'traceability', label: 'Traceability' },
                { id: 'executions', label: 'Executions' },
                { id: 'defects', label: 'Defects' },
                { id: 'attachments', label: 'Attachments' },
                { id: 'history', label: 'History' },
            ],
            active: _activeTab,
            onChange: (tab) => TestCaseDetailView.switchTab(tab),
        });
    }

    function _tabBtn(_key, _label) {
        // Legacy — no longer used; TMTabBar handles tabs
        return '';
    }

    function _renderTree() {
        const el = document.getElementById('tcDetailTree');
        if (!el) return;

        let groups = [];
        if (_treeMode === 'suite') groups = _buildSuiteGroups();
        else if (_treeMode === 'l3') groups = _buildGenericGroups(tc => tc.process_level_id || 'Unassigned L3');
        else groups = _buildGenericGroups(tc => (tc.test_layer || 'unknown').toUpperCase());

        // Flatten groups into TMTreePanel nodes
        const nodes = [];
        groups.forEach(g => {
            (g.items || []).forEach(tc => {
                nodes.push({
                    id: String(tc.id),
                    label: `${tc.code || 'TC-' + tc.id}`,
                    count: g.label,
                });
            });
        });

        // Deduplicate and use group-style tree
        const groupNodes = groups.map(g => ({
            id: `grp_${g.label}`,
            label: `${g.label} (${g.items.length})`,
            count: '',
        }));

        // Build flat list with section headers
        const allNodes = [{ id: 'all', label: 'All Test Cases', count: _catalog.length }];
        groups.forEach(g => {
            allNodes.push({ id: `grp_${g.label}`, label: g.label, count: g.items.length });
        });

        TMTreePanel.render(el, {
            title: _treeMode === 'suite' ? 'Suites' : _treeMode === 'l3' ? 'L3 Scopes' : 'Layers',
            nodes: allNodes,
            selectedId: 'all',
            searchPlaceholder: 'Filter test cases…',
            onSelect: (nodeId) => {
                if (nodeId === 'all') return;
                // Find first TC in that group's items
                const grpLabel = nodeId.replace('grp_', '');
                const grp = groups.find(g => g.label === grpLabel);
                if (grp && grp.items.length) {
                    App.navigate('test-case-detail', Number(grp.items[0].id));
                }
            },
        });

        // Also render the sibling TC list below the tree
        const siblingHtml = groups.map(g => _renderGroup(g.label, g.items)).join('');
        const siblingContainer = document.createElement('div');
        siblingContainer.style.maxHeight = '50vh';
        siblingContainer.style.overflow = 'auto';
        siblingContainer.innerHTML = siblingHtml;
        el.appendChild(siblingContainer);
    }

    function _buildSuiteGroups() {
        const memberships = _getMembershipMap();
        const groups = _suites.map(s => ({ label: s.name || `Suite #${s.id}`, items: memberships[s.id] || [] }));
        const unassigned = (_catalog || []).filter(tc => {
            const ids = Array.isArray(tc.suite_ids) ? tc.suite_ids : [];
            return ids.length === 0 && !tc.suite_id;
        });
        if (unassigned.length) groups.push({ label: 'Unassigned', items: unassigned });
        return groups;
    }

    function _buildGenericGroups(keyFn) {
        const buckets = {};
        (_catalog || []).forEach(tc => {
            const key = String(keyFn(tc));
            if (!buckets[key]) buckets[key] = [];
            buckets[key].push(tc);
        });
        return Object.keys(buckets).sort((a, b) => a.localeCompare(b)).map(label => ({ label, items: buckets[label] }));
    }

    function _renderGroup(label, items) {
        const selected = (items || []).some(tc => Number(tc.id) === Number(_caseId));
        return `
            <div style="padding:8px 12px;border-bottom:1px solid #f1f5f9">
                <div style="font-size:12px;font-weight:700;color:${selected ? '#1d4ed8' : '#111827'}">${_esc(label)} <span style="color:#64748b">(${items.length})</span></div>
                <div style="margin-top:6px;display:flex;flex-direction:column;gap:4px">
                    ${items.slice(0, 10).map(tc => `
                        <button class="btn btn-sm ${Number(tc.id) === Number(_caseId) ? 'btn-primary' : 'btn-secondary'}" style="text-align:left;justify-content:flex-start" onclick="App.navigate('test-case-detail', ${Number(tc.id)})">
                            ${_esc(tc.code || `TC-${tc.id}`)}
                        </button>
                    `).join('')}
                    ${items.length > 10 ? `<div style="font-size:11px;color:#64748b">+${items.length - 10} more</div>` : ''}
                </div>
            </div>
        `;
    }

    function _getMembershipMap() {
        const map = {};
        const add = (suiteId, tc) => {
            if (!suiteId) return;
            if (!map[suiteId]) map[suiteId] = [];
            map[suiteId].push(tc);
        };
        (_catalog || []).forEach(tc => {
            if (Array.isArray(tc.suite_ids) && tc.suite_ids.length) tc.suite_ids.forEach(sid => add(Number(sid), tc));
            else if (tc.suite_id) add(Number(tc.suite_id), tc);
        });
        return map;
    }

    function switchTab(tab) {
        _activeTab = tab;
        _renderShell();
        _renderTree();
        _renderTab();
        _updateHash();
    }

    function switchTreeMode(mode) {
        _treeMode = mode;
        _renderShell();
        _renderTree();
        _renderTab();
    }

    function startEdit() {
        _isEditing = true;
        _draft = {
            ..._tc,
            suite_ids: Array.isArray(_tc.suite_ids) ? [..._tc.suite_ids] : (_tc.suite_id ? [_tc.suite_id] : []),
        };
        _draftSteps = (_steps || []).map(s => ({ ...s }));
        _renderShell();
        _renderTree();
        _renderTab();
    }

    function cancelEdit() {
        _isEditing = false;
        _draft = null;
        _draftSteps = [];
        _renderShell();
        _renderTree();
        _renderTab();
    }

    function setDraftField(field, value) {
        if (!_isEditing || !_draft) return;
        _draft[field] = value;
    }

    function toggleDraftSuite(suiteId) {
        if (!_isEditing || !_draft) return;
        const id = Number(suiteId);
        const set = new Set((_draft.suite_ids || []).map(Number));
        if (set.has(id)) set.delete(id);
        else set.add(id);
        _draft.suite_ids = Array.from(set);
        _renderTab();
    }

    function setDraftStepField(index, field, value) {
        if (!_isEditing) return;
        if (!_draftSteps[index]) return;
        _draftSteps[index][field] = value;
    }

    function addDraftStep() {
        if (!_isEditing) return;
        _draftSteps.push({ id: null, step_no: _draftSteps.length + 1, action: '', test_data: '', expected_result: '', notes: '' });
        _renderTab();
    }

    function removeDraftStep(index) {
        if (!_isEditing) return;
        _draftSteps.splice(index, 1);
        _renderTab();
    }

    function moveDraftStep(index, direction) {
        if (!_isEditing) return;
        const target = direction === 'up' ? index - 1 : index + 1;
        if (target < 0 || target >= _draftSteps.length) return;
        const tmp = _draftSteps[index];
        _draftSteps[index] = _draftSteps[target];
        _draftSteps[target] = tmp;
        _renderTab();
    }

    async function _syncSteps(caseId) {
        const existing = _steps || [];
        const existingIds = new Set(existing.map(s => Number(s.id)));
        const kept = new Set();

        for (let i = 0; i < _draftSteps.length; i += 1) {
            const s = _draftSteps[i];
            const action = (s.action || '').trim();
            const expected = (s.expected_result || '').trim();
            if (!action && !expected) continue;

            const body = {
                step_no: i + 1,
                action,
                test_data: s.test_data || '',
                expected_result: expected,
                notes: s.notes || '',
            };

            if (s.id) {
                await API.put(`/testing/steps/${s.id}`, body);
                kept.add(Number(s.id));
            } else {
                const created = await API.post(`/testing/catalog/${caseId}/steps`, body);
                if (created?.id) kept.add(Number(created.id));
            }
        }

        const toDelete = [...existingIds].filter(id => !kept.has(id));
        for (const id of toDelete) {
            await API.delete(`/testing/steps/${id}`);
        }
    }

    async function saveEdit() {
        if (!_isEditing || !_draft || !_caseId) return;
        const body = {
            title: (_draft.title || '').trim(),
            description: _draft.description || '',
            preconditions: _draft.preconditions || '',
            module: _draft.module || '',
            priority: _draft.priority || 'medium',
            status: _draft.status || 'draft',
            test_layer: _draft.test_layer || 'sit',
            test_type: _draft.test_type || 'functional',
            execution_type: _draft.execution_type || 'manual',
            assigned_to: _draft.assigned_to || '',
            suite_ids: Array.isArray(_draft.suite_ids) ? _draft.suite_ids : [],
        };
        if (!body.title) {
            App.toast('Title is required', 'warning');
            return;
        }

        await API.put(`/testing/catalog/${_caseId}`, body);
        await _syncSteps(_caseId);

        App.toast('Test case updated', 'success');
        _isEditing = false;
        _draft = null;
        _draftSteps = [];
        _execLoaded = false;
        await _loadData(TestingShared.pid, _caseId);
        _renderShell();
        _renderTree();
        _renderTab();
    }

    async function linkDefect(defectId) {
        await API.put(`/testing/defects/${defectId}`, { test_case_id: _caseId, changed_by: 'TestCaseDetailView' });
        const pid = TestingShared.pid;
        const defectsRes = await API.get(`/programs/${pid}/testing/defects`).catch(() => ({ items: [] }));
        _defects = defectsRes?.items || defectsRes || [];
        _renderTab();
    }

    async function unlinkDefect(defectId) {
        await API.put(`/testing/defects/${defectId}`, { test_case_id: null, changed_by: 'TestCaseDetailView' });
        const pid = TestingShared.pid;
        const defectsRes = await API.get(`/programs/${pid}/testing/defects`).catch(() => ({ items: [] }));
        _defects = defectsRes?.items || defectsRes || [];
        _renderTab();
    }

    async function _renderTab() {
        const el = document.getElementById('tcDetailTabContent');
        if (!el) return;
        const current = _isEditing ? _draft : _tc;

        if (_activeTab === 'details') {
            el.innerHTML = `<div id="tcApprovalBanner" style="margin-bottom:var(--sp-sm)"></div><div id="tcPropPanel"></div><div id="tcSuiteSection" style="margin-top:var(--sp-md)"></div>`;

            // Render approval status banner (F3)
            if (typeof ApprovalsView !== 'undefined' && _caseId) {
                ApprovalsView.renderStatusBanner(document.getElementById('tcApprovalBanner'), 'test_case', _caseId);
            }

            const suites = _suites || [];
            const suiteIds = new Set((Array.isArray(current.suite_ids) ? current.suite_ids : (current.suite_id ? [current.suite_id] : [])).map(Number));

            TMPropertyPanel.render(document.getElementById('tcPropPanel'), {
                editing: _isEditing,
                sections: [
                    {
                        title: 'Description & Preconditions',
                        fields: [
                            { key: 'description', label: 'Description', value: current.description || '', type: 'textarea', onChange: (v) => TestCaseDetailView.setDraftField('description', v) },
                            { key: 'preconditions', label: 'Preconditions', value: current.preconditions || '', type: 'textarea', onChange: (v) => TestCaseDetailView.setDraftField('preconditions', v) },
                        ],
                    },
                    {
                        title: 'Core Properties',
                        fields: [
                            { key: 'title', label: 'Title', value: current.title || '', onChange: (v) => TestCaseDetailView.setDraftField('title', v) },
                            { key: 'test_type', label: 'Type', value: current.test_type || '', onChange: (v) => TestCaseDetailView.setDraftField('test_type', v) },
                            { key: 'execution_type', label: 'Execution', value: current.execution_type || '', onChange: (v) => TestCaseDetailView.setDraftField('execution_type', v) },
                            { key: 'module', label: 'Module', value: current.module || '', onChange: (v) => TestCaseDetailView.setDraftField('module', v) },
                            { key: 'assigned_to', label: 'Assignee', value: current.assigned_to || '', onChange: (v) => TestCaseDetailView.setDraftField('assigned_to', v) },
                            { key: 'process_level_id', label: 'L3 Scope', value: current.process_level_id || '', editable: false },
                            { key: 'test_layer', label: 'Layer', value: current.test_layer || '', onChange: (v) => TestCaseDetailView.setDraftField('test_layer', v) },
                            { key: 'priority', label: 'Priority', value: current.priority || 'medium', type: 'select', options: [{value:'low',text:'Low'},{value:'medium',text:'Medium'},{value:'high',text:'High'},{value:'critical',text:'Critical'}], onChange: (v) => TestCaseDetailView.setDraftField('priority', v) },
                            { key: 'status', label: 'Status', value: current.status || 'draft', type: 'select', options: [{value:'draft',text:'Draft'},{value:'ready',text:'Ready'},{value:'approved',text:'Approved'},{value:'in_review',text:'In Review'},{value:'deprecated',text:'Deprecated'}], onChange: (v) => TestCaseDetailView.setDraftField('status', v) },
                        ],
                    },
                ],
            });

            // Suite assignments section
            const suiteSec = document.getElementById('tcSuiteSection');
            if (_isEditing) {
                suiteSec.innerHTML = `<div style="font-weight:600;font-size:var(--tm-header-font-size);text-transform:uppercase;color:var(--tm-text-secondary);margin-bottom:var(--sp-sm)">Suite Assignments</div><div id="tcSuiteDropdown"></div>`;
                TMDropdownSelect.render(document.getElementById('tcSuiteDropdown'), {
                    options: suites.map(s => ({ value: String(s.id), text: s.name || `Suite #${s.id}`, selected: suiteIds.has(Number(s.id)) })),
                    multi: true,
                    placeholder: 'Select suites…',
                    onChange: (vals) => { if (_draft) _draft.suite_ids = vals.map(Number); },
                });
            } else {
                const linked = suites.filter(s => suiteIds.has(Number(s.id)));
                suiteSec.innerHTML = `<div style="font-weight:600;font-size:var(--tm-header-font-size);text-transform:uppercase;color:var(--tm-text-secondary);margin-bottom:var(--sp-sm)">Suite Assignments</div>
                    <div style="display:flex;gap:var(--sp-xs);flex-wrap:wrap">${linked.length ? linked.map(s => TMStatusBadge.html(s.name || `Suite #${s.id}`, {customBg:'#e8f0fe',customFg:'#174ea6'})).join('') : '<span class="tm-muted">No suites assigned</span>'}</div>`;
            }
            return;
        }

        if (_activeTab === 'script') {
            el.innerHTML = '<div id="tcStepEditor"></div>';
            const steps = _isEditing ? _draftSteps : _steps;
            TMStepEditor.render(document.getElementById('tcStepEditor'), {
                steps,
                editable: _isEditing,
                onAdd: () => TestCaseDetailView.addDraftStep(),
                onRemove: (idx) => TestCaseDetailView.removeDraftStep(idx),
                onMove: (idx, dir) => TestCaseDetailView.moveDraftStep(idx, dir),
                onFieldChange: (idx, field, value) => TestCaseDetailView.setDraftStepField(idx, field, value),
            });
            return;
        }

        if (_activeTab === 'traceability') {
            const d = _derived || {};
            const summary = d.summary || {};
            el.innerHTML = '<div id="tcTracePanel"></div>';
            TMPropertyPanel.render(document.getElementById('tcTracePanel'), {
                editing: false,
                sections: [
                    {
                        title: 'Derived Chain',
                        fields: [
                            { key: 'process', label: 'Process', value: summary.process_level_name || '-' },
                            { key: 'requirement', label: 'Requirement', value: summary.explore_requirement_code || '-' },
                            { key: 'source', label: 'Source', value: summary.source_type || '-' },
                        ],
                    },
                    {
                        title: 'Dependencies',
                        fields: _deps.length
                            ? _deps.map((dep, i) => ({ key: `dep_${i}`, label: dep.direction === 'blocked_by' ? 'Blocked By' : 'Blocks', value: dep.code || dep.id || '' }))
                            : [{ key: 'none', label: 'Status', value: 'No dependencies' }],
                    },
                    {
                        title: 'Performance',
                        fields: [
                            { key: 'perf_count', label: 'Records', value: `${_perf.length} performance result(s)` },
                        ],
                    },
                ],
            });
            return;
        }

        if (_activeTab === 'executions') {
            await _ensureExecutionRows();
            el.innerHTML = '<div id="tcExecGrid"></div>';
            TMDataGrid.render(document.getElementById('tcExecGrid'), {
                columns: [
                    { key: 'kind', label: 'Type', width: '70px' },
                    { key: 'id', label: 'ID', width: '60px', render: (r) => `#${r.id}` },
                    { key: 'cycle_name', label: 'Cycle', width: '140px' },
                    { key: 'result', label: 'Result', width: '80px', render: (r) => TMStatusBadge.html(r.result || '-') },
                    { key: 'actor', label: 'Tester', width: '100px' },
                    { key: 'when', label: 'Date', width: '140px', render: (r) => _esc((r.when || '').toString().slice(0, 19) || '-') },
                    { key: 'evidence_url', label: 'Evidence', width: '80px', render: (r) => r.evidence_url ? `<a href="${_esc(r.evidence_url)}" target="_blank" rel="noopener noreferrer">Open</a>` : '-' },
                ],
                rows: _executionRows,
                emptyText: 'No execution records found.',
            });
            return;
        }

        if (_activeTab === 'defects') {
            const linked = (_defects || []).filter(d => Number(d.test_case_id) === Number(_caseId));
            const pool = (_defects || []).filter(d => !d.test_case_id || Number(d.test_case_id) !== Number(_caseId)).slice(0, 20);
            el.innerHTML = `
                <div style="margin-bottom:var(--sp-md)">
                    <div style="font-weight:600;font-size:var(--tm-font-sm);margin-bottom:var(--sp-sm)">Linked Defects</div>
                    <div id="tcLinkedDefectsGrid"></div>
                </div>
                <div>
                    <div style="font-weight:600;font-size:var(--tm-font-sm);margin-bottom:var(--sp-sm)">Link Existing Defect</div>
                    <div id="tcPoolDefectsGrid"></div>
                </div>
            `;
            TMDataGrid.render(document.getElementById('tcLinkedDefectsGrid'), {
                columns: [
                    { key: 'code', label: 'Code', width: '100px', render: (d) => _esc(d.code || `DEF-${d.id}`) },
                    { key: 'title', label: 'Title' },
                    { key: 'status', label: 'Status', width: '90px', render: (d) => TMStatusBadge.html(d.status || '-') },
                    { key: 'severity', label: 'Severity', width: '90px', render: (d) => TMStatusBadge.html(d.severity || '-') },
                    { key: '_actions', label: '', width: '70px', render: (d) => `<button class="tm-toolbar__btn" style="font-size:11px" onclick="TestCaseDetailView.unlinkDefect(${d.id})">Unlink</button>` },
                ],
                rows: linked,
                emptyText: 'No linked defects.',
            });
            TMDataGrid.render(document.getElementById('tcPoolDefectsGrid'), {
                columns: [
                    { key: 'code', label: 'Code', width: '100px', render: (d) => _esc(d.code || `DEF-${d.id}`) },
                    { key: 'title', label: 'Title' },
                    { key: 'status', label: 'Status', width: '90px', render: (d) => TMStatusBadge.html(d.status || '-') },
                    { key: '_actions', label: '', width: '70px', render: (d) => `<button class="tm-toolbar__btn tm-toolbar__btn--primary" style="font-size:11px" onclick="TestCaseDetailView.linkDefect(${d.id})">Link</button>` },
                ],
                rows: pool,
                emptyText: 'No available defects to link.',
            });
            return;
        }

        if (_activeTab === 'attachments') {
            await _ensureExecutionRows();
            const fromExec = _executionRows.filter(r => r.evidence_url).map(r => ({
                id: `${r.kind}_${r.id}`,
                source: `${r.kind} #${r.id}`,
                url: r.evidence_url,
                when: r.when,
            }));
            const fromPerf = (_perf || []).filter(p => p.evidence_url).map(p => ({
                id: `perf_${p.id || 0}`,
                source: `perf #${p.id || '-'}`,
                url: p.evidence_url,
                when: p.created_at || p.updated_at,
            }));
            const all = [...fromExec, ...fromPerf];
            el.innerHTML = '<div id="tcAttachGrid"></div>';
            TMDataGrid.render(document.getElementById('tcAttachGrid'), {
                columns: [
                    { key: 'source', label: 'Source', width: '120px' },
                    { key: 'url', label: 'URL', render: (a) => `<a href="${_esc(a.url)}" target="_blank" rel="noopener noreferrer">${_esc(a.url)}</a>` },
                    { key: 'when', label: 'Date', width: '140px', render: (a) => _esc((a.when || '').toString().slice(0, 19) || '-') },
                ],
                rows: all,
                emptyText: 'No evidence attachments found.',
            });
            return;
        }

        // History tab
        await _ensureExecutionRows();
        await _ensureVersions();
        const recent = _executionRows.slice(0, 8);
        const diff = _versionDiff?.diff;
        const summary = diff?.summary || null;

        el.innerHTML = `
            <div id="tcAuditPanel" style="margin-bottom:var(--sp-md)"></div>
            <div style="margin-bottom:var(--sp-md)">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--sp-sm)">
                    <strong style="font-size:var(--tm-font-sm)">Versions</strong>
                    <div style="display:flex;gap:var(--sp-sm);align-items:center">
                        <button class="tm-toolbar__btn" onclick="TestCaseDetailView.loadVersionDiff()">Compare</button>
                    </div>
                </div>
                ${_versions.length ? `
                    <div style="display:grid;grid-template-columns:1fr 1fr auto;gap:var(--sp-sm);align-items:end;margin-bottom:var(--sp-sm)">
                        <div>
                            <label style="font-size:var(--tm-font-xs);color:var(--tm-text-secondary)">From</label>
                            <select class="tm-input" style="width:100%" onchange="TestCaseDetailView.setVersionFrom(this.value)">
                                ${_versions.map(v => `<option value="${v.version_no}" ${v.version_no === _versionFrom ? 'selected' : ''}>v${v.version_no} • ${_esc(v.change_summary || '')}</option>`).join('')}
                            </select>
                        </div>
                        <div>
                            <label style="font-size:var(--tm-font-xs);color:var(--tm-text-secondary)">To</label>
                            <select class="tm-input" style="width:100%" onchange="TestCaseDetailView.setVersionTo(this.value)">
                                ${_versions.map(v => `<option value="${v.version_no}" ${v.version_no === _versionTo ? 'selected' : ''}>v${v.version_no} • ${_esc(v.change_summary || '')}</option>`).join('')}
                            </select>
                        </div>
                        <button class="tm-toolbar__btn" onclick="TestCaseDetailView.restoreVersion(${_versionFrom || _versionTo})">Restore Selected</button>
                    </div>
                    <div id="tcVersionGrid"></div>
                ` : '<p class="tm-muted">No version snapshots yet.</p>'}
            </div>
            ${summary ? `
                <div class="tm-card tm-diff-viewer" style="padding:var(--sp-md);margin-bottom:var(--sp-md)">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--sp-sm)">
                        <strong style="font-size:var(--tm-font-sm)">Diff: v${_versionFrom} → v${_versionTo}</strong>
                        <div style="display:flex;gap:var(--sp-sm);flex-wrap:wrap">
                            <span class="tm-badge" style="background:#e8f0fe;color:#174ea6">Fields: ${summary.field_change_count}</span>
                            <span class="tm-badge" style="background:#e6f4ea;color:#137333">+${summary.step_added_count} steps</span>
                            <span class="tm-badge" style="background:#fce8e6;color:#a50e0e">-${summary.step_removed_count} steps</span>
                            <span class="tm-badge" style="background:#fef7cd;color:#7c6900">Δ${summary.step_changed_count} steps</span>
                        </div>
                    </div>

                    ${(diff.field_changes || []).length ? `
                    <div class="tm-diff-section">
                        <div class="tm-diff-section__title">Field Changes</div>
                        <table class="tm-diff-table">
                            <thead>
                                <tr>
                                    <th style="width:120px">Field</th>
                                    <th class="tm-diff-col-old">v${_versionFrom} (Old)</th>
                                    <th class="tm-diff-col-new">v${_versionTo} (New)</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${(diff.field_changes || []).map(fc => `
                                <tr>
                                    <td class="tm-diff-field-name">${_esc(fc.field)}</td>
                                    <td class="tm-diff-cell tm-diff-cell--removed">${_esc(String(fc.from ?? '—'))}</td>
                                    <td class="tm-diff-cell tm-diff-cell--added">${_esc(String(fc.to ?? '—'))}</td>
                                </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                    ` : '<div class="tm-muted" style="margin-bottom:var(--sp-sm)">No field-level changes.</div>'}

                    ${(diff.steps?.added?.length || diff.steps?.removed?.length || diff.steps?.changed?.length) ? `
                    <div class="tm-diff-section">
                        <div class="tm-diff-section__title">Step Changes</div>
                        <table class="tm-diff-table">
                            <thead>
                                <tr>
                                    <th style="width:60px">Step</th>
                                    <th class="tm-diff-col-old">v${_versionFrom} (Old)</th>
                                    <th class="tm-diff-col-new">v${_versionTo} (New)</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${(diff.steps.removed || []).map(s => `
                                <tr class="tm-diff-row--removed">
                                    <td class="tm-diff-step-no">${s.step_no}</td>
                                    <td class="tm-diff-cell tm-diff-cell--removed">
                                        <div class="tm-diff-step-content">
                                            <div><strong>Action:</strong> ${_esc(s.from?.action || '')}</div>
                                            <div><strong>Data:</strong> ${_esc(s.from?.test_data || '')}</div>
                                            <div><strong>Expected:</strong> ${_esc(s.from?.expected_result || '')}</div>
                                        </div>
                                    </td>
                                    <td class="tm-diff-cell tm-diff-cell--empty">—</td>
                                </tr>`).join('')}
                                ${(diff.steps.added || []).map(s => `
                                <tr class="tm-diff-row--added">
                                    <td class="tm-diff-step-no">${s.step_no}</td>
                                    <td class="tm-diff-cell tm-diff-cell--empty">—</td>
                                    <td class="tm-diff-cell tm-diff-cell--added">
                                        <div class="tm-diff-step-content">
                                            <div><strong>Action:</strong> ${_esc(s.to?.action || '')}</div>
                                            <div><strong>Data:</strong> ${_esc(s.to?.test_data || '')}</div>
                                            <div><strong>Expected:</strong> ${_esc(s.to?.expected_result || '')}</div>
                                        </div>
                                    </td>
                                </tr>`).join('')}
                                ${(diff.steps.changed || []).map(s => {
                                    const cols = Object.keys(s.changes || {});
                                    return `
                                <tr class="tm-diff-row--changed">
                                    <td class="tm-diff-step-no">${s.step_no}</td>
                                    <td class="tm-diff-cell tm-diff-cell--removed">
                                        <div class="tm-diff-step-content">
                                            ${cols.map(c => `<div><strong>${_esc(c)}:</strong> ${_esc(String(s.changes[c].from ?? ''))}</div>`).join('')}
                                        </div>
                                    </td>
                                    <td class="tm-diff-cell tm-diff-cell--added">
                                        <div class="tm-diff-step-content">
                                            ${cols.map(c => `<div><strong>${_esc(c)}:</strong> ${_esc(String(s.changes[c].to ?? ''))}</div>`).join('')}
                                        </div>
                                    </td>
                                </tr>`;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                    ` : ''}
                </div>
            ` : ''}
            <div>
                <strong style="font-size:var(--tm-font-sm)">Recent Activity</strong>
                <div id="tcRecentActivityGrid" style="margin-top:var(--sp-sm)"></div>
            </div>
        `;

        // Audit panel
        TMPropertyPanel.render(document.getElementById('tcAuditPanel'), {
            editing: false,
            sections: [{
                title: 'Audit Snapshot',
                fields: [
                    { key: 'created_at', label: 'Created', value: (current.created_at || '-').slice(0, 19) },
                    { key: 'updated_at', label: 'Updated', value: (current.updated_at || '-').slice(0, 19) },
                    { key: 'created_by', label: 'Created By', value: current.created_by || '-' },
                ],
            }],
        });

        // Version grid
        if (_versions.length) {
            TMDataGrid.render(document.getElementById('tcVersionGrid'), {
                columns: [
                    { key: 'version_no', label: 'Version', width: '70px', render: (v) => `<strong>v${v.version_no}</strong>` },
                    { key: 'change_summary', label: 'Summary' },
                    { key: 'created_by', label: 'By', width: '90px' },
                    { key: 'created_at', label: 'Date', width: '140px', render: (v) => _esc((v.created_at || '').slice(0, 19) || '-') },
                    { key: 'is_current', label: 'Current', width: '60px', render: (v) => v.is_current ? '✅' : '' },
                    { key: '_actions', label: '', width: '70px', render: (v) => `<button class="tm-toolbar__btn" style="font-size:11px" onclick="TestCaseDetailView.restoreVersion(${v.version_no})">Restore</button>` },
                ],
                rows: _versions,
            });
        }

        // Recent activity grid
        TMDataGrid.render(document.getElementById('tcRecentActivityGrid'), {
            columns: [
                { key: 'when', label: 'Date', width: '140px', render: (r) => _esc((r.when || '').toString().slice(0, 19) || '-') },
                { key: 'kind', label: 'Type', width: '80px' },
                { key: 'id', label: 'ID', width: '60px', render: (r) => `#${r.id}` },
                { key: 'result', label: 'Result', width: '80px', render: (r) => TMStatusBadge.html(r.result || '-') },
            ],
            rows: recent,
            emptyText: 'No execution history yet.',
        });
    }

    async function openLegacyEditor() {
        if (!_caseId) return;
        try {
            const tc = await API.get(`/testing/catalog/${_caseId}`);
            if (typeof TestPlanningView !== 'undefined' && TestPlanningView.showCaseModal) TestPlanningView.showCaseModal(tc);
        } catch (err) {
            App.toast(err?.message || 'Unable to open editor', 'error');
        }
    }

    async function loadVersionDiff() {
        if (!_caseId || !_versionFrom || !_versionTo) return;
        _versionDiff = await API.get(`/testing/catalog/${_caseId}/versions/diff?from=${_versionFrom}&to=${_versionTo}`).catch(() => null);
        _renderTab();
    }

    async function restoreVersion(versionNo) {
        if (!_caseId) return;
        if (!confirm(`Restore version ${versionNo}? Current state will be snapshotted automatically.`)) return;

        await API.post(`/testing/catalog/${_caseId}/versions/${versionNo}/restore`, {
            change_summary: `restored from version ${versionNo}`,
        });
        App.toast(`Version ${versionNo} restored`, 'success');

        _versions = [];
        _versionDiff = null;
        _execLoaded = false;
        await _loadData(TestingShared.pid, _caseId);
        await _ensureVersions();
        _renderShell();
        _renderTree();
        _renderTab();
    }

    return {
        render,
        switchTab,
        setVersionFrom: (val) => { _versionFrom = Number(val); },
        setVersionTo: (val) => { _versionTo = Number(val); },
        loadVersionDiff,
        restoreVersion,
        switchTreeMode,
        startEdit,
        cancelEdit,
        setDraftField,
        toggleDraftSuite,
        setDraftStepField,
        addDraftStep,
        removeDraftStep,
        moveDraftStep,
        saveEdit,
        linkDefect,
        unlinkDefect,
        openLegacyEditor,
    };
})();
