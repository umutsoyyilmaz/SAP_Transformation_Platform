/**
 * F6 — Suite Folders View
 * Hierarchical folder tree with drag-drop, bulk operations, and saved searches.
 */
const SuiteFoldersView = (() => {
    let suites = [];
    let selectedIds = new Set();
    let currentFolder = null;

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    // ── Render ───────────────────────────────────────────────────────────
    async function render() {
        const main = document.getElementById('mainContent');
        const prog = App.getActiveProgram();
        if (!prog) {
            main.innerHTML = `
                <div class="page-header"><h1>Suite Folders</h1></div>
                <div class="empty-state">
                    <div class="empty-state__icon">📁</div>
                    <div class="empty-state__title">No Program Selected</div>
                </div>`;
            return;
        }

        main.innerHTML = `
            <div class="page-header">
                <h1>📁 Suite Folders</h1>
                <div class="page-header__actions">
                    <button class="btn btn-primary" onclick="SuiteFoldersView.createFolder()">+ New Folder</button>
                </div>
            </div>
            <div class="f6-layout">
                <div class="f6-sidebar">
                    <div class="f6-search-box">
                        <input type="text" id="f6FolderSearch" placeholder="Search folders..."
                               oninput="SuiteFoldersView.filterTree(this.value)" />
                    </div>
                    <div id="f6FolderTree" class="f6-folder-tree">Loading...</div>
                    <div class="f6-saved-searches" id="f6SavedSearches"></div>
                </div>
                <div class="f6-main">
                    <div class="f6-bulk-toolbar" id="f6BulkToolbar" style="display:none">
                        <span id="f6SelectCount">0 selected</span>
                        <button class="btn btn-sm" onclick="SuiteFoldersView.bulkAction('status')">Status</button>
                        <button class="btn btn-sm" onclick="SuiteFoldersView.bulkAction('assign')">Assign</button>
                        <button class="btn btn-sm" onclick="SuiteFoldersView.bulkAction('move')">Move</button>
                        <button class="btn btn-sm" onclick="SuiteFoldersView.bulkAction('clone')">Clone</button>
                        <button class="btn btn-sm" onclick="SuiteFoldersView.bulkAction('tag')">Tag</button>
                        <button class="btn btn-sm" onclick="SuiteFoldersView.bulkAction('export')">Export</button>
                        <button class="btn btn-sm btn-danger" onclick="SuiteFoldersView.bulkAction('delete')">Delete</button>
                    </div>
                    <div id="f6FolderContent" class="f6-folder-content">
                        <div class="empty-state">
                            <div class="empty-state__icon">📂</div>
                            <div class="empty-state__title">Select a folder to view test cases</div>
                        </div>
                    </div>
                </div>
            </div>`;

        await loadTree();
        await loadSavedSearches();
    }

    // ── Tree Loading ─────────────────────────────────────────────────────
    async function loadTree() {
        const prog = App.getActiveProgram();
        try {
            const resp = await fetch(`/api/v1/programs/${prog.id}/testing/suites/tree`);
            const data = await resp.json();
            suites = data.tree || [];
            renderTree(suites);
        } catch (e) {
            document.getElementById('f6FolderTree').innerHTML =
                `<div class="f6-error">Failed to load folder tree</div>`;
        }
    }

    function renderTree(nodes, container) {
        const el = container || document.getElementById('f6FolderTree');
        if (!nodes.length) {
            el.innerHTML = '<div class="f6-empty-tree">No folders yet. Create one above.</div>';
            return;
        }
        el.innerHTML = _buildTreeHtml(nodes, 0);
    }

    function _buildTreeHtml(nodes, depth) {
        let html = '<ul class="f6-tree-list">';
        for (const node of nodes) {
            const hasChildren = node.children && node.children.length > 0;
            const icon = hasChildren ? '📁' : '📄';
            const expanded = depth < 2 ? 'open' : '';
            const activeClass = currentFolder && currentFolder.id === node.id ? 'f6-tree-active' : '';

            html += `<li class="f6-tree-item ${activeClass}" data-id="${node.id}" draggable="true"
                         ondragstart="SuiteFoldersView.onDragStart(event, ${node.id})"
                         ondragover="SuiteFoldersView.onDragOver(event)"
                         ondrop="SuiteFoldersView.onDrop(event, ${node.id})">
                <details ${expanded}>
                    <summary class="f6-tree-label" onclick="SuiteFoldersView.selectFolder(${node.id}, event)"
                             oncontextmenu="SuiteFoldersView.showContextMenu(event, ${node.id})">
                        <span class="f6-tree-icon">${icon}</span>
                        <span class="f6-tree-name">${esc(node.name)}</span>
                        <span class="f6-tree-badge">${node.case_count || 0}</span>
                    </summary>
                    ${hasChildren ? _buildTreeHtml(node.children, depth + 1) : ''}
                </details>
            </li>`;
        }
        html += '</ul>';
        return html;
    }

    function filterTree(query) {
        if (!query) { renderTree(suites); return; }
        const q = query.toLowerCase();
        const filtered = _filterNodes(suites, q);
        renderTree(filtered);
    }

    function _filterNodes(nodes, q) {
        const result = [];
        for (const n of nodes) {
            const match = n.name.toLowerCase().includes(q);
            const childMatches = _filterNodes(n.children || [], q);
            if (match || childMatches.length) {
                result.push({ ...n, children: match ? (n.children || []) : childMatches });
            }
        }
        return result;
    }

    // ── Folder Selection ─────────────────────────────────────────────────
    async function selectFolder(id, event) {
        if (event) event.stopPropagation();
        const node = _findNode(suites, id);
        currentFolder = node;
        selectedIds.clear();
        updateBulkToolbar();

        // Re-render tree to highlight
        renderTree(suites);

        const content = document.getElementById('f6FolderContent');
        if (!node) {
            content.innerHTML = '<div class="f6-error">Folder not found</div>';
            return;
        }

        const prog = App.getActiveProgram();
        try {
            const resp = await fetch(`/api/v1/testing/suites/${id}/cases`);
            const data = await resp.json();
            const cases = data.items || data || [];
            renderFolderContent(node, cases);
        } catch (e) {
            content.innerHTML = `<div class="f6-error">Failed to load cases: ${e.message}</div>`;
        }
    }

    function renderFolderContent(folder, cases) {
        const content = document.getElementById('f6FolderContent');
        if (!cases.length) {
            content.innerHTML = `
                <div class="f6-folder-header">
                    <h3>${esc(folder.name)}</h3>
                    <span class="f6-tree-badge">${folder.module || ''}</span>
                </div>
                <div class="empty-state">
                    <div class="empty-state__icon">📋</div>
                    <div class="empty-state__title">No test cases in this folder</div>
                </div>`;
            return;
        }

        let rows = '';
        for (const tc of cases) {
            const checked = selectedIds.has(tc.id) ? 'checked' : '';
            const statusClass = `f6-status-${(tc.status || 'draft').toLowerCase()}`;
            rows += `<tr>
                <td><input type="checkbox" ${checked}
                    onchange="SuiteFoldersView.toggleSelect(${tc.id}, this.checked)" /></td>
                <td class="f6-tc-id">${tc.id}</td>
                <td class="f6-tc-title">${esc(tc.title)}</td>
                <td>${esc(tc.module || '')}</td>
                <td><span class="f6-status-pill ${statusClass}">${esc(tc.status || 'draft')}</span></td>
                <td>${esc(tc.priority || '')}</td>
                <td>${esc(tc.test_layer || '')}</td>
            </tr>`;
        }

        content.innerHTML = `
            <div class="f6-folder-header">
                <h3>${esc(folder.name)}</h3>
                <span class="f6-tree-badge">${cases.length} cases</span>
            </div>
            <table class="f6-tc-table">
                <thead>
                    <tr>
                        <th><input type="checkbox" onchange="SuiteFoldersView.toggleAll(this.checked)" /></th>
                        <th>ID</th>
                        <th>Title</th>
                        <th>Module</th>
                        <th>Status</th>
                        <th>Priority</th>
                        <th>Layer</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>`;
    }

    function _findNode(nodes, id) {
        for (const n of nodes) {
            if (n.id === id) return n;
            if (n.children) {
                const found = _findNode(n.children, id);
                if (found) return found;
            }
        }
        return null;
    }

    // ── Selection & Bulk ─────────────────────────────────────────────────
    function toggleSelect(id, checked) {
        if (checked) selectedIds.add(id);
        else selectedIds.delete(id);
        updateBulkToolbar();
    }

    function toggleAll(checked) {
        const checkboxes = document.querySelectorAll('.f6-tc-table tbody input[type="checkbox"]');
        checkboxes.forEach(cb => {
            cb.checked = checked;
            const row = cb.closest('tr');
            const id = parseInt(row.querySelector('.f6-tc-id')?.textContent) || 0;
            if (checked) selectedIds.add(id);
            else selectedIds.delete(id);
        });
        updateBulkToolbar();
    }

    function updateBulkToolbar() {
        const toolbar = document.getElementById('f6BulkToolbar');
        const count = document.getElementById('f6SelectCount');
        if (selectedIds.size > 0) {
            toolbar.style.display = 'flex';
            count.textContent = `${selectedIds.size} selected`;
        } else {
            toolbar.style.display = 'none';
        }
    }

    async function bulkAction(action) {
        const prog = App.getActiveProgram();
        if (!prog || !selectedIds.size) return;

        const ids = Array.from(selectedIds);

        if (action === 'delete' && !confirm(`Delete ${ids.length} test case(s)?`)) return;

        let body = { ids };
        let endpoint = `/api/v1/programs/${prog.id}/testing/bulk/${action}`;

        // Gather additional input for specific actions
        if (action === 'status') {
            const status = prompt('Enter new status (draft, ready, approved, deprecated):');
            if (!status) return;
            body.status = status;
        } else if (action === 'assign') {
            const assignee = prompt('Enter assignee name:');
            if (!assignee) return;
            body.assigned_to = assignee;
        } else if (action === 'move') {
            const suiteId = prompt('Enter target Suite ID:');
            if (!suiteId) return;
            body.suite_id = parseInt(suiteId);
        } else if (action === 'tag') {
            const tags = prompt('Enter tags (comma-separated):');
            if (!tags) return;
            body.tags = tags;
        } else if (action === 'export') {
            body.format = 'json';
        }

        try {
            const resp = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            const result = await resp.json();

            if (resp.ok) {
                if (action === 'export') {
                    // Download exported data
                    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url; a.download = 'test_cases_export.json'; a.click();
                    URL.revokeObjectURL(url);
                } else {
                    App.showToast?.(`Bulk ${action}: ${result.updated || result.moved || result.cloned || result.deleted || 0} items`, 'success');
                    selectedIds.clear();
                    updateBulkToolbar();
                    if (currentFolder) {
                        selectFolder(currentFolder.id);
                    }
                    await loadTree();
                }
            } else {
                App.showToast?.(result.error || 'Bulk operation failed', 'error');
            }
        } catch (e) {
            App.showToast?.('Bulk operation failed: ' + e.message, 'error');
        }
    }

    // ── Drag & Drop ──────────────────────────────────────────────────────
    let dragSuiteId = null;

    function onDragStart(event, id) {
        dragSuiteId = id;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', id.toString());
    }

    function onDragOver(event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }

    async function onDrop(event, targetId) {
        event.preventDefault();
        if (!dragSuiteId || dragSuiteId === targetId) return;

        try {
            const resp = await fetch(`/api/v1/testing/suites/${dragSuiteId}/move`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ parent_id: targetId }),
            });
            if (resp.ok) {
                App.showToast?.('Folder moved', 'success');
                await loadTree();
            } else {
                const err = await resp.json();
                App.showToast?.(err.error || 'Move failed', 'error');
            }
        } catch (e) {
            App.showToast?.('Move failed: ' + e.message, 'error');
        }
        dragSuiteId = null;
    }

    // ── Context Menu ─────────────────────────────────────────────────────
    function showContextMenu(event, id) {
        event.preventDefault();
        event.stopPropagation();

        // Remove existing
        document.querySelectorAll('.f6-context-menu').forEach(m => m.remove());

        const menu = document.createElement('div');
        menu.className = 'f6-context-menu';
        menu.style.left = event.pageX + 'px';
        menu.style.top = event.pageY + 'px';
        menu.innerHTML = `
            <div class="f6-ctx-item" onclick="SuiteFoldersView.createSubfolder(${id})">📁 New Subfolder</div>
            <div class="f6-ctx-item" onclick="SuiteFoldersView.renameFolder(${id})">✏️ Rename</div>
            <div class="f6-ctx-item" onclick="SuiteFoldersView.moveToRoot(${id})">⬆️ Move to Root</div>
            <div class="f6-ctx-item f6-ctx-danger" onclick="SuiteFoldersView.deleteFolder(${id})">🗑️ Delete</div>
        `;
        document.body.appendChild(menu);
        setTimeout(() => document.addEventListener('click', () => menu.remove(), { once: true }), 50);
    }

    // ── Folder CRUD ──────────────────────────────────────────────────────
    async function createFolder() {
        const prog = App.getActiveProgram();
        if (!prog) return;
        const name = prompt('Folder name:');
        if (!name) return;

        const resp = await fetch(`/api/v1/programs/${prog.id}/testing/suites`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, status: 'active' }),
        });
        if (resp.ok) {
            App.showToast?.('Folder created', 'success');
            await loadTree();
        }
    }

    async function createSubfolder(parentId) {
        const prog = App.getActiveProgram();
        if (!prog) return;
        const name = prompt('Subfolder name:');
        if (!name) return;

        const resp = await fetch(`/api/v1/programs/${prog.id}/testing/suites`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, parent_id: parentId, status: 'active' }),
        });
        if (resp.ok) {
            App.showToast?.('Subfolder created', 'success');
            await loadTree();
        }
    }

    async function renameFolder(id) {
        const name = prompt('New name:');
        if (!name) return;
        const resp = await fetch(`/api/v1/testing/suites/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name }),
        });
        if (resp.ok) {
            App.showToast?.('Folder renamed', 'success');
            await loadTree();
        }
    }

    async function moveToRoot(id) {
        const resp = await fetch(`/api/v1/testing/suites/${id}/move`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ parent_id: null }),
        });
        if (resp.ok) {
            App.showToast?.('Moved to root', 'success');
            await loadTree();
        }
    }

    async function deleteFolder(id) {
        if (!confirm('Delete this folder and its contents?')) return;
        const resp = await fetch(`/api/v1/testing/suites/${id}`, { method: 'DELETE' });
        if (resp.ok) {
            if (currentFolder && currentFolder.id === id) currentFolder = null;
            App.showToast?.('Folder deleted', 'success');
            await loadTree();
        }
    }

    // ── Saved Searches ───────────────────────────────────────────────────
    async function loadSavedSearches() {
        const prog = App.getActiveProgram();
        if (!prog) return;

        try {
            const resp = await fetch(`/api/v1/programs/${prog.id}/saved-searches`);
            const data = await resp.json();
            const searches = data.items || [];
            renderSavedSearches(searches);
        } catch (e) {
            // Silently fail for saved searches
        }
    }

    function renderSavedSearches(searches) {
        const el = document.getElementById('f6SavedSearches');
        if (!searches.length) {
            el.innerHTML = '<div class="f6-saved-header">Saved Searches</div><div class="f6-empty-tree">No saved searches</div>';
            return;
        }

        let html = '<div class="f6-saved-header">Saved Searches</div><ul class="f6-saved-list">';
        for (const s of searches) {
            const pinIcon = s.is_pinned ? '📌' : '';
            const pubIcon = s.is_public ? '🌐' : '🔒';
            html += `<li class="f6-saved-item" onclick="SuiteFoldersView.applySavedSearch(${s.id})">
                <span>${pinIcon}${pubIcon} ${esc(s.name)}</span>
                <span class="f6-saved-count">${s.usage_count || 0}</span>
            </li>`;
        }
        html += '</ul>';
        el.innerHTML = html;
    }

    async function applySavedSearch(id) {
        try {
            const resp = await fetch(`/api/v1/saved-searches/${id}/apply`, { method: 'POST' });
            const data = await resp.json();
            App.showToast?.(`Applied filter: ${data.entity_type}`, 'info');
            // In full implementation, this would apply the filters to the current view
        } catch (e) {
            App.showToast?.('Failed to apply search', 'error');
        }
    }

    // ── Public API ───────────────────────────────────────────────────────
    return {
        render,
        selectFolder,
        toggleSelect,
        toggleAll,
        bulkAction,
        filterTree,
        createFolder,
        createSubfolder,
        renameFolder,
        moveToRoot,
        deleteFolder,
        onDragStart,
        onDragOver,
        onDrop,
        showContextMenu,
        applySavedSearch,
    };
})();
