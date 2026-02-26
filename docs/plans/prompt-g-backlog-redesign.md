# PROMPT G — Backlog (WRICEF) UI Redesign

## File: static/js/views/backlog.js (REWRITE — 1058 LOC, ~1100 LOC after)

### Context files (must read):
- `static/js/components/explore-shared.js` → ExpUI.filterBar, ExpUI.kpiBlock, ExpUI.metricBar, ExpUI.actionButton, ExpUI.pill
- `static/css/explore-tokens.css` → CSS variables, design tokens
- `static/css/main.css` → .backlog-*, .kanban-*, .wricef-badge, .data-table, .badge-*, .tabs, .tab-btn

---

## Identified Issues (from 4 screenshots)

### 1. Tab Style Inconsistency
- **Backlog:** `.backlog-tab` (custom CSS) + emoji icons (🗂️📋⚙️🏃)
- **Other pages:** Using `.tab-btn` class (RAID, Hierarchy, Workshops)
- **Fix:** Use `.tab-btn`, replace emojis with CSS dot or clean text

### 2. KPI / Summary Style Inconsistency
- **Kanban Board:** `.backlog-summary` + `.backlog-kpi` → inline text "28 Items 185 Points 23 Done 12% Complete"
- **Other pages:** Using `ExpUI.kpiBlock` or `.exp-kpi-strip`
- **Fix:** Use `ExpUI.kpiBlock` or `ExpUI.metricBar`

### 3. List Filter Style Inconsistency
- **WRICEF List:** 3x HTML `<select>` (backlog-filters class)
- **Other pages:** `ExpUI.filterBar` (dropdown + active chips)
- **Fix:** Use `ExpUI.filterBar`

### 4. Actions Column
- **WRICEF List:** Only "Delete" (large red button) — no Edit
- **Config Items:** "Edit" + "Delete" (2 large buttons side by side = takes too much space)
- **Fix:** SVG icon buttons (`.btn-icon`) — like in RAID

### 5. Sprint View Buttons
- **Sprint cards:** "Edit" + "Delete" (red button) — raw appearance
- **Fix:** `.btn-icon` SVG + compact styling

### 6. Kanban Board KPI
- **Current:** `.backlog-summary` → 4 inline text items
- **Fix:** `exp-kpi-strip` with 4 blocks (consistent)

---

## Change 1: render() — Tab + Page Header

```javascript
async function render() {
    currentItem = null;
    const prog = App.getActiveProgram();
    programId = prog ? prog.id : null;
    const main = document.getElementById('mainContent');

    if (!programId) {
        main.innerHTML = `
            <div class="empty-state">
                <div class="empty-state__icon">⚙️</div>
                <div class="empty-state__title">Backlog (WRICEF)</div>
                <p>Go to <a href="#" onclick="App.navigate('programs');return false">Programs</a> to select one first.</p>
            </div>`;
        return;
    }

    main.innerHTML = `
        <div class="page-header" style="margin-bottom:20px">
            <div>
                <h2 style="margin:0">Backlog (WRICEF)</h2>
                <p style="color:#64748b;margin:4px 0 0;font-size:13px">Development objects, config items, and sprint planning</p>
            </div>
            <div class="page-header__actions">
                ${ExpUI.actionButton({ label: '📈 Stats', variant: 'secondary', size: 'md', onclick: 'BacklogView.showStats()' })}
                ${ExpUI.actionButton({ label: '+ New Item', variant: 'primary', size: 'md', onclick: 'BacklogView.showCreateModal()' })}
            </div>
        </div>

        <div class="tabs" style="margin-bottom:16px">
            <button class="tab-btn ${currentTab === 'board' ? 'active' : ''}" data-tab="board" onclick="BacklogView.switchTab('board')">Kanban Board</button>
            <button class="tab-btn ${currentTab === 'list' ? 'active' : ''}" data-tab="list" onclick="BacklogView.switchTab('list')">WRICEF List</button>
            <button class="tab-btn ${currentTab === 'config' ? 'active' : ''}" data-tab="config" onclick="BacklogView.switchTab('config')">Config Items</button>
            <button class="tab-btn ${currentTab === 'sprints' ? 'active' : ''}" data-tab="sprints" onclick="BacklogView.switchTab('sprints')">Sprints</button>
        </div>

        <div id="backlogContent">
            <div style="text-align:center;padding:40px"><div class="spinner"></div></div>
        </div>`;

    await loadData();
}
```

**Changes:**
- `<h1>` → `<h2>` (consistent with other pages)
- Subtitle added
- `ExpUI.actionButton` used (instead of raw `<button>`)
- `.backlog-tab` → `.tab-btn` (platform standard tab class)
- Emoji icons removed from tabs

## Change 2: switchTab() — tab-btn class toggle

```javascript
function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tabs .tab-btn').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    renderCurrentTab();
}
```

## Change 3: Kanban Board — KPI Strip

In renderBoard(), replace `.backlog-summary` with ExpUI.kpiBlock:

```javascript
function renderBoard() {
    const c = document.getElementById('backlogContent');
    const visibleColumns = ['new', 'design', 'build', 'test', 'deploy'];
    const summary = boardData.summary;

    c.innerHTML = `
        <div class="exp-kpi-strip" style="margin-bottom:16px">
            ${ExpUI.kpiBlock({ value: summary.total_items, label: 'Items', accent: 'var(--exp-l2, #3b82f6)' })}
            ${ExpUI.kpiBlock({ value: summary.total_points, label: 'Story Points', accent: '#8b5cf6' })}
            ${ExpUI.kpiBlock({ value: summary.done_points, label: 'Done', accent: 'var(--exp-fit, #22c55e)' })}
            ${ExpUI.kpiBlock({ value: summary.completion_pct + '%', label: 'Complete', accent: summary.completion_pct >= 80 ? 'var(--exp-fit)' : summary.completion_pct >= 50 ? '#f59e0b' : 'var(--exp-gap, #ef4444)' })}
        </div>
        <div class="kanban-board">
            ${visibleColumns.map(status => `
                <div class="kanban-column" data-status="${status}">
                    <div class="kanban-column__header">
                        <span class="kanban-column__title">${STATUS_LABELS[status]}</span>
                        <span class="kanban-column__count">${(boardData.columns[status] || []).length}</span>
                    </div>
                    <div class="kanban-column__body" data-status="${status}">
                        ${(boardData.columns[status] || []).map(item => _renderKanbanCard(item)).join('')}
                    </div>
                </div>
            `).join('')}
        </div>`;
}
```

**Changes:**
- `.backlog-summary` → `exp-kpi-strip` + `ExpUI.kpiBlock`
- Removed 'closed', 'blocked', 'cancelled' from visibleColumns (only active flow in Kanban)
- Accent colors consistent (same palette as other pages)

## Change 4: WRICEF List — FilterBar + Table Styling

```javascript
function renderList() {
    const c = document.getElementById('backlogContent');
    if (items.length === 0) {
        c.innerHTML = `
            <div class="empty-state" style="padding:40px">
                <div class="empty-state__icon">⚙️</div>
                <div class="empty-state__title">No backlog items yet</div>
                <p>Create your first WRICEF item to build the development backlog.</p><br>
                ${ExpUI.actionButton({ label: '+ New Item', variant: 'primary', size: 'md', onclick: 'BacklogView.showCreateModal()' })}
            </div>`;
        return;
    }

    c.innerHTML = `
        <div id="blFilterBar" style="margin-bottom:8px"></div>
        <div id="blListTable"></div>`;

    renderListFilterBar();
    applyListFilter();
}

function renderListFilterBar() {
    document.getElementById('blFilterBar').innerHTML = ExpUI.filterBar({
        id: 'blFB',
        searchPlaceholder: 'Search items…',
        searchValue: _listSearch,
        onSearch: 'BacklogView.setListSearch(this.value)',
        onChange: 'BacklogView.onListFilterChange',
        filters: [
            {
                id: 'wricef_type', label: 'Type', type: 'multi', color: '#3b82f6',
                options: Object.entries(WRICEF).map(([k, v]) => ({ value: k, label: v.label })),
                selected: _listFilters.wricef_type || [],
            },
            {
                id: 'status', label: 'Status', type: 'multi', color: '#10b981',
                options: Object.entries(STATUS_LABELS).map(([k, v]) => ({ value: k, label: v })),
                selected: _listFilters.status || [],
            },
            {
                id: 'priority', label: 'Priority', type: 'multi', color: '#ef4444',
                options: ['critical','high','medium','low'].map(p => ({ value: p, label: p.charAt(0).toUpperCase() + p.slice(1) })),
                selected: _listFilters.priority || [],
            },
            {
                id: 'module', label: 'Module', type: 'multi', color: '#8b5cf6',
                options: [...new Set(items.map(i => i.module).filter(Boolean))].sort().map(m => ({ value: m, label: m })),
                selected: _listFilters.module || [],
            },
        ],
        actionsHtml: `<span style="font-size:12px;color:#94a3b8" id="blItemCount"></span>`,
    });
}
```

**New state variables (add to top of IIFE):**
```javascript
let _listSearch = '';
let _listFilters = {};
```

**New handlers:**
```javascript
function setListSearch(val) {
    _listSearch = val;
    applyListFilter();
}

function onListFilterChange(update) {
    if (update._clearAll) {
        _listFilters = {};
    } else {
        Object.keys(update).forEach(key => {
            const val = update[key];
            if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
                delete _listFilters[key];
            } else {
                _listFilters[key] = val;
            }
        });
    }
    renderListFilterBar();
    applyListFilter();
}
```

**Updated applyListFilter:**
```javascript
function applyListFilter() {
    let filtered = [...items];

    // Search
    if (_listSearch) {
        const q = _listSearch.toLowerCase();
        filtered = filtered.filter(i =>
            (i.title || '').toLowerCase().includes(q) ||
            (i.code || '').toLowerCase().includes(q) ||
            (i.assigned_to || '').toLowerCase().includes(q) ||
            (i.module || '').toLowerCase().includes(q)
        );
    }

    // Filters
    Object.entries(_listFilters).forEach(([key, val]) => {
        if (!val) return;
        const values = Array.isArray(val) ? val : [val];
        if (values.length === 0) return;
        filtered = filtered.filter(i => values.includes(String(i[key])));
    });

    const countEl = document.getElementById('blItemCount');
    if (countEl) countEl.textContent = `${filtered.length} of ${items.length}`;

    const tableEl = document.getElementById('blListTable');
    if (!tableEl) return;

    if (filtered.length === 0) {
        tableEl.innerHTML = `<div class="empty-state" style="padding:40px"><p>No items match your filters.</p></div>`;
        return;
    }
    tableEl.innerHTML = _renderListTable(filtered);
}
```

## Change 5: _renderTableRows → _renderListTable (Professional Styling)

```javascript
function _renderListTable(list) {
    const priorityBadge = (p) => {
        const colors = { critical:'#dc2626', high:'#f97316', medium:'#f59e0b', low:'#22c55e' };
        const bg = { critical:'#fee2e2', high:'#fff7ed', medium:'#fefce8', low:'#f0fdf4' };
        const label = (p || '').charAt(0).toUpperCase() + (p || '').slice(1);
        return `<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:${bg[p]||'#f1f5f9'};color:${colors[p]||'#64748b'}">
            <span style="width:6px;height:6px;border-radius:50%;background:${colors[p]||'#94a3b8'}"></span>${label}
        </span>`;
    };

    const statusBadge = (s) => {
        const map = {
            new:'#dbeafe', design:'#e0e7ff', build:'#fef3c7', test:'#fce7f3',
            deploy:'#d1fae5', closed:'#f1f5f9', blocked:'#fee2e2', cancelled:'#f1f5f9',
        };
        const textMap = {
            new:'#1e40af', design:'#3730a3', build:'#92400e', test:'#9d174d',
            deploy:'#065f46', closed:'#475569', blocked:'#991b1b', cancelled:'#475569',
        };
        const label = STATUS_LABELS[s] || s || '—';
        return `<span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:${map[s]||'#f1f5f9'};color:${textMap[s]||'#475569'};white-space:nowrap">${label}</span>`;
    };

    let html = `<table class="data-table" style="font-size:13px">
        <thead><tr>
            <th style="width:90px">Type</th>
            <th style="width:110px">Code</th>
            <th>Title</th>
            <th style="width:60px">Module</th>
            <th style="width:80px">Status</th>
            <th style="width:85px">Priority</th>
            <th style="width:40px">SP</th>
            <th style="width:110px">Assigned</th>
            <th style="width:60px;text-align:right"></th>
        </tr></thead><tbody>`;

    list.forEach(i => {
        const w = WRICEF[i.wricef_type] || WRICEF.enhancement;
        const linkCount = (i.requirement_id ? 1 : 0) + (i.functional_spec ? 1 : 0) + (i.technical_spec ? 1 : 0);

        html += `<tr style="cursor:pointer" onclick="BacklogView.openDetail(${i.id})">
            <td><span class="wricef-badge" style="background:${w.color}">${w.icon} ${w.label[0]}</span></td>
            <td><code style="font-size:12px;color:#475569">${escHtml(i.code || '—')}</code></td>
            <td>
                <span style="font-weight:500">${escHtml(i.title)}</span>
                ${linkCount > 0 ? `<span style="margin-left:4px;font-size:10px;color:#94a3b8">🔗${linkCount}</span>` : ''}
            </td>
            <td><span style="font-size:12px;color:#64748b">${escHtml(i.module || '—')}</span></td>
            <td>${statusBadge(i.status)}</td>
            <td>${priorityBadge(i.priority)}</td>
            <td style="text-align:center;font-weight:600;color:#64748b">${i.story_points || '—'}</td>
            <td><span style="font-size:12px;color:#64748b">${escHtml(i.assigned_to || '—')}</span></td>
            <td style="text-align:right" onclick="event.stopPropagation()">
                <button class="btn-icon" onclick="BacklogView.openDetail(${i.id})" title="View">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
                </button>
                <button class="btn-icon btn-icon--danger" onclick="BacklogView.deleteItem(${i.id})" title="Delete">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
                </button>
            </td>
        </tr>`;
    });

    html += '</tbody></table>';
    return html;
}
```

**Changes:**
- Raw `<button class="btn btn-danger">Delete</button>` → `.btn-icon` SVG (like in RAID)
- Priority badge: color dot + label (like in RAID)
- Status badge: semantic color system (like in RAID)
- WRICEF badge: short form (first letter only) — more compact in table
- Code: `<code>` tag for monospace

## Change 6: Config Items — Action Buttons

In renderConfigItems() table Actions column:

**FIND (current):**
```html
<td>
    <button class="btn btn-secondary btn-sm" onclick="...">Edit</button>
    <button class="btn btn-danger btn-sm" onclick="...">Delete</button>
</td>
```

**REPLACE:**
```html
<td style="text-align:right" onclick="event.stopPropagation()">
    <button class="btn-icon" onclick="BacklogView.showEditConfigModal(${ci.id})" title="Edit">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
    </button>
    <button class="btn-icon btn-icon--danger" onclick="BacklogView.deleteConfigItem(${ci.id})" title="Delete">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
    </button>
</td>
```

## Change 7: Sprint Cards — Compact Styling

In renderSprints() sprint card header:

**FIND:**
```html
<div>
    <button class="btn btn-secondary btn-sm" onclick="BacklogView.showEditSprintModal(${s.id})">Edit</button>
    <button class="btn btn-danger btn-sm" onclick="BacklogView.deleteSprint(${s.id})">Delete</button>
</div>
```

**REPLACE:**
```html
<div style="display:flex;gap:4px">
    <button class="btn-icon" onclick="BacklogView.showEditSprintModal(${s.id})" title="Edit">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
    </button>
    <button class="btn-icon btn-icon--danger" onclick="BacklogView.deleteSprint(${s.id})" title="Delete">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
    </button>
</div>
```

Sprint metrics → ExpUI.kpiBlock style inline:

**FIND:**
```html
<div class="sprint-metrics">
    <span><strong>${sprintItems.length}</strong> items</span>
    <span><strong>${totalPts}</strong> points</span>
    <span><strong>${donePts}</strong> done</span>
    ...
</div>
```

Keep this as is — inline metrics are appropriate for sprint cards. Only shrink the buttons.

However, remove the emoji from Sprint Unassigned Backlog header:

**FIND:** `<h3>📦 Unassigned Backlog</h3>`
**REPLACE:** `<h3>Unassigned Backlog</h3>`

## Change 8: "+ New Sprint" / "+ New Config Item" buttons

Replace buttons in Sprints and Config tabs with ExpUI.actionButton:

**Sprints:**
```javascript
<div style="margin-top:12px;display:flex;justify-content:flex-end">
    ${ExpUI.actionButton({ label: '+ New Sprint', variant: 'primary', size: 'sm', onclick: 'BacklogView.showCreateSprintModal()' })}
</div>
```

**Config:**
```javascript
<div style="margin-top:12px;display:flex;justify-content:flex-end">
    ${ExpUI.actionButton({ label: '+ New Config Item', variant: 'primary', size: 'sm', onclick: 'BacklogView.showCreateConfigModal()' })}
</div>
```

## Change 9: Updated Public API

```javascript
return {
    render, switchTab, applyListFilter,
    setListSearch, onListFilterChange,         // NEW
    showCreateModal, showEditModal, saveItem,
    openDetail, deleteItem, switchDetailTab,
    showMoveModal, doMove,
    showStats,
    showCreateSprintModal, showEditSprintModal, saveSprint, deleteSprint,
    showCreateConfigModal, showEditConfigModal, saveConfigItem, deleteConfigItem,
    openConfigDetail,
};
```

## CSS Cleanup (main.css)

The following classes will no longer be used but do not remove them for backward compatibility:
- `.backlog-tabs`, `.backlog-tab` → now using `.tabs`, `.tab-btn`
- `.backlog-summary`, `.backlog-kpi` → now using `exp-kpi-strip`
- `.backlog-filters` → now using `ExpUI.filterBar`

No need to delete these classes, the new code simply won't use them.

---

## Verification Checklist

- [ ] Tabs: `.tab-btn` class (no emojis), active tab underline
- [ ] Kanban KPI: `exp-kpi-strip` + 4x `ExpUI.kpiBlock`
- [ ] WRICEF List: `ExpUI.filterBar` (search + type/status/priority/module dropdowns)
- [ ] WRICEF List: active filter chips + "Clear All"
- [ ] WRICEF List: `_renderListTable` with professional badges
- [ ] WRICEF List: `.btn-icon` SVG actions (edit pencil + delete trash)
- [ ] Config Items: `.btn-icon` SVG actions
- [ ] Sprint Cards: `.btn-icon` SVG actions
- [ ] Sprint Cards: emojis removed
- [ ] "+ New Sprint" / "+ New Config Item" → `ExpUI.actionButton`
- [ ] "📈 Stats" / "+ New Item" → `ExpUI.actionButton`
- [ ] Filter state persistent per tab switch (reset on tab change)
- [ ] Item count badge: "12 of 28"

## Commit
```
refactor(backlog): standardize UI — tabs, filterBar, kpiBlock, btn-icon actions
```

## Effort: ~4h
