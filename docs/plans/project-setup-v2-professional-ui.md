# Project Setup — Professional UI Prompt (v2)

## 3 İyileştirme
1. **Profesyonel UI** — Mevcut ExpUI component system + explore-tokens.css kullan
2. **🤖 AI Suggested** butonu — placeholder olarak ekle (Sprint 13'te aktif olacak)
3. **Tablo modu** — Manuel giriş için inline-editable data-table (tree + table toggle)

---

## PROMPT B-v2: Frontend — Professional Project Setup Page (~8h)

### Dosya: static/js/views/project_setup.js (YENİ, ~600 LOC)

#### Context dosyaları (mutlaka oku):
- `static/js/components/explore-shared.js` → ExpUI component library (kpiBlock, pill, fitBadge, actionButton, filterGroup, levelBadge)
- `static/css/explore-tokens.css` → CSS variables (--exp-l1 through --exp-l4, --exp-radius-*, --exp-shadow-*, --exp-font-*)
- `static/css/main.css` → .data-table, .card, .kpi-card, .btn, .tabs, .tab-btn classes
- `static/js/views/explore_hierarchy.js` → Existing tree rendering pattern (referans)
- `static/js/views/data_factory.js` → Tab + data-table pattern (referans)
- `static/js/explore-api.js` → ExploreAPI.levels.* methods

#### Existing Design System Rules:
```
Colors: --exp-l1: #8B5CF6 (purple), --exp-l2: #3B82F6 (blue), --exp-l3: #10B981 (green), --exp-l4: #F59E0B (amber)
Radius: --exp-radius-md: 6px, --exp-radius-lg: 8px
Shadows: --exp-shadow-sm, --exp-shadow-md
Fonts: --exp-font-family (72/DM Sans), --exp-font-mono
Spacing: --exp-space-xs: 4px, --exp-space-sm: 8px, --exp-space-md: 16px, --exp-space-lg: 24px
```

### Page Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  ⚙ Project Setup                                                     │
│  Configure project structure and process hierarchy                    │
├──────────────────────────────────────────────────────────────────────┤
│  [🏗️ Process Hierarchy]  [👥 Team]  [📅 Phases]  [⚙ Settings]      │
│   ^^^ active tab-btn                                                  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─ KPI Row ──────────────────────────────────────────────────────┐  │
│  │  🏛 5        📁 10       📋 50       ⚙ 200     ● 78%         │  │
│  │  L1 Areas   L2 Groups   L3 Items   L4 Steps   In Scope       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─ Toolbar ──────────────────────────────────────────────────────┐  │
│  │  🔍 Search...    [Area: All ▼] [Scope: All ▼]                 │  │
│  │                                                                 │  │
│  │  View: [🌳 Tree] [📊 Table]   [🤖 AI Suggested] [📚 Import]  │  │
│  │                                 [➕ Add L1 Area]                │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─ Tree View (default) ─────────────────────────────────────────┐  │
│  │                                                                 │  │
│  │  ▼ 🟣 L1-OTC  Order to Cash              SD   W1  [+][✏][🗑] │  │
│  │    ▼ 🔵 L2-SD-SALES  Sales Order Mgmt    SD   W1  [+][✏][🗑] │  │
│  │      ▸ 🟢 L3-1OC  Standard Sales Order   SD   W1  [+][✏][🗑] │  │
│  │      ▸ 🟢 L3-2OC  Credit Management      SD   W1  [+][✏][🗑] │  │
│  │      ▸ 🟢 L3-3OC  Third-Party Sales      SD   W1  [+][✏][🗑] │  │
│  │    ▸ 🔵 L2-SD-SHIP  Delivery & Shipping  SD   W1  [+][✏][🗑] │  │
│  │  ▸ 🟣 L1-PTP  Procure to Pay             MM   W1  [+][✏][🗑] │  │
│  │  ▸ 🟣 L1-RTR  Record to Report           FI   W1  [+][✏][🗑] │  │
│  │  ────────────────────────────────────────────────────           │  │
│  │  [➕ Add L1 Area]                                               │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─ OR: Table View (toggle) ─────────────────────────────────────┐  │
│  │  Level │ Code     │ Name              │ Module │ Parent    │ ⊕  │  │
│  │  ──────┼──────────┼───────────────────┼────────┼───────────┼──  │  │
│  │  🟣 L1 │ L1-OTC   │ Order to Cash     │ SD     │ —         │ ✏🗑│  │
│  │  🔵 L2 │ L2-SD..  │ Sales Order Mgmt  │ SD     │ L1-OTC   │ ✏🗑│  │
│  │  🟢 L3 │ L3-1OC   │ Standard Sales O. │ SD     │ L2-SD..  │ ✏🗑│  │
│  │  ────── INLINE ADD ROW ──────────────────────────────────────── │  │
│  │  [L?▼] │ [code  ] │ [name           ] │ [mod▼] │ [parent▼] │ ✓  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### Empty State (boş proje)

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                    │
│                         🏗️                                        │
│                                                                    │
│              No Process Hierarchy Defined                          │
│    Build your L1 → L4 process structure to start your project     │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │ 📚 Import SAP    │  │ 🤖 AI Suggested  │  │ ✍️ Start from  │  │
│  │    Template       │  │    Hierarchy      │  │    Scratch      │  │
│  │                   │  │                   │  │                 │  │
│  │ Pre-built L1→L4  │  │ AI generates a    │  │ Manually create │  │
│  │ from SAP Best    │  │ hierarchy based   │  │ your process    │  │
│  │ Practice catalog │  │ on your industry  │  │ areas one by one│  │
│  │                   │  │ (Coming Soon)     │  │                 │  │
│  └──────────────────┘  └──────────────────┘  └────────────────┘  │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Detaylı Implementation Talimatları

```javascript
/**
 * Project Setup — Configuration hub
 * Tab 1: Process Hierarchy (tree + table views, CRUD, template import)
 * Tab 2-4: Placeholders
 *
 * Uses: ExpUI components, explore-tokens.css variables, ExploreAPI.levels.*
 * Route: project-setup (via App.navigate)
 */
const ProjectSetupView = (() => {
    'use strict';
    const esc = ExpUI.esc;

    let _pid = null;
    let _currentTab = 'hierarchy';
    let _viewMode = 'tree';       // 'tree' | 'table'
    let _tree = [];
    let _flatList = [];           // all levels flat for table view
    let _expandedNodes = new Set();
    let _searchQuery = '';
    let _filters = { area: null, scope: null };
    let _l1List = [], _l2List = [], _l3List = [], _l4List = [];
```

#### 1. KPI Row — Use ExpUI.kpiBlock

```javascript
function renderKpiRow() {
    const inScopeCount = _flatList.filter(n => n.scope_status === 'in_scope').length;
    const totalCount = _flatList.length;
    const inScopePct = totalCount > 0 ? Math.round(inScopeCount / totalCount * 100) : 0;
    
    return `<div class="kpi-row" style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:20px">
        ${ExpUI.kpiBlock({ value: _l1List.length, label: 'L1 Areas', icon: '🏛' })}
        ${ExpUI.kpiBlock({ value: _l2List.length, label: 'L2 Groups', icon: '📁' })}
        ${ExpUI.kpiBlock({ value: _l3List.length, label: 'L3 Scope Items', icon: '📋' })}
        ${ExpUI.kpiBlock({ value: _l4List.length, label: 'L4 Steps', icon: '⚙' })}
        ${ExpUI.kpiBlock({ value: inScopePct + '%', label: 'In Scope', icon: '✅' })}
    </div>`;
}
```

#### 2. Toolbar — Search + Filters + View Toggle + Actions

```javascript
function renderToolbar() {
    return `<div class="card" style="padding:12px 16px;margin-bottom:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <div style="flex:1;min-width:200px;max-width:280px">
            <input type="text" class="form-input" placeholder="🔍 Search processes..." 
                   value="${esc(_searchQuery)}"
                   oninput="ProjectSetupView.setSearch(this.value)" 
                   style="padding:6px 10px;font-size:13px">
        </div>
        
        ${ExpUI.filterGroup({
            id: 'area', label: 'Area:',
            options: [{value:null,label:'All'},{value:'FI',label:'FI'},{value:'MM',label:'MM'},
                      {value:'SD',label:'SD'},{value:'PP',label:'PP'},{value:'HR',label:'HR'}],
            active: _filters.area,
            onSelect: "ProjectSetupView.setFilter('area', VALUE)"
        })}
        
        <div style="margin-left:auto;display:flex;gap:8px;align-items:center">
            <!-- View toggle -->
            <div style="display:flex;border:1px solid #e2e8f0;border-radius:var(--exp-radius-md);overflow:hidden">
                <button class="view-toggle-btn${_viewMode==='tree' ? ' active' : ''}" 
                    onclick="ProjectSetupView.setViewMode('tree')">🌳 Tree</button>
                <button class="view-toggle-btn${_viewMode==='table' ? ' active' : ''}" 
                    onclick="ProjectSetupView.setViewMode('table')">📊 Table</button>
            </div>
            
            <!-- Actions -->
            ${ExpUI.actionButton({ label: '🤖 AI Suggested', variant: 'ghost', size: 'sm',
                onclick: "ProjectSetupView.openAISuggested()" })}
            ${ExpUI.actionButton({ label: '📚 Import Template', variant: 'secondary', size: 'sm',
                onclick: "ProjectSetupView.openTemplateImport()" })}
            ${ExpUI.actionButton({ label: '➕ Add L1 Area', variant: 'primary', size: 'sm',
                onclick: "ProjectSetupView.openCreateDialog(1, null)" })}
        </div>
    </div>`;
}
```

CSS for view-toggle-btn:
```css
.view-toggle-btn {
    padding: 4px 12px; font-size: 12px; font-weight: 600; border: none;
    background: #fff; color: #64748b; cursor: pointer; transition: all 0.15s;
}
.view-toggle-btn.active { background: var(--sap-blue); color: #fff; }
.view-toggle-btn:hover:not(.active) { background: #f1f5f9; }
```

#### 3. Tree View — Professional with level color indicators

Each tree row uses level-colored left border + proper indentation:

```javascript
function renderTreeNode(node, depth) {
    const lvl = node.level || (depth + 1);
    const hasChildren = node.children && node.children.length > 0;
    const isExpanded = _expandedNodes.has(node.id);
    const indent = 16 + depth * 28;
    const levelColor = `var(--exp-l${lvl})`;
    const levelBg = `var(--exp-l${lvl}-bg)`;
    
    // Filter check
    if (_searchQuery && !matchesSearch(node)) return '';
    if (_filters.area && node.process_area_code !== _filters.area) return '';

    return `
        <div class="setup-node" data-id="${node.id}" data-level="${lvl}">
            <div class="setup-node__row" 
                 style="padding:0 16px 0 ${indent}px;display:flex;align-items:center;height:42px;border-left:3px solid transparent;transition:all 0.15s"
                 onmouseenter="this.style.background='var(--exp-tree-hover-bg)';this.style.borderLeftColor='${levelColor}';this.querySelector('.node-acts').style.opacity=1"
                 onmouseleave="this.style.background='';this.style.borderLeftColor='transparent';this.querySelector('.node-acts').style.opacity=0">
                
                <!-- Expand/Collapse -->
                ${hasChildren 
                    ? `<span class="setup-chevron${isExpanded?' setup-chevron--open':''}" 
                        onclick="event.stopPropagation();ProjectSetupView.toggleNode('${node.id}')"
                        style="width:20px;text-align:center;font-size:10px;color:#999;cursor:pointer;transition:transform 0.2s;${isExpanded?'transform:rotate(90deg)':''}">▶</span>`
                    : '<span style="width:20px"></span>'}
                
                <!-- Level badge -->
                <span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:6px;background:${levelBg};margin-right:8px">
                    <span style="font-size:11px;font-weight:700;color:${levelColor}">L${lvl}</span>
                </span>
                
                <!-- Code -->
                <code style="font-family:var(--exp-font-mono);font-size:11px;color:#64748b;min-width:80px;margin-right:8px">${esc(node.code || '')}</code>
                
                <!-- Name -->
                <span style="flex:1;font-weight:${lvl <= 2 ? 600 : 400};font-size:14px;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                      onclick="ProjectSetupView.openEditDialog('${node.id}',${lvl})"
                      title="${esc(node.name)}">${esc(node.name)}</span>
                
                <!-- Scope badge (if not in_scope) -->
                ${node.scope_status && node.scope_status !== 'in_scope' 
                    ? ExpUI.pill({ label: node.scope_status.replace(/_/g,' '), variant: node.scope_status === 'out_of_scope' ? 'danger' : 'warning', size: 'sm' })
                    : ''}
                
                <!-- Module -->
                ${node.process_area_code 
                    ? `<span style="font-size:11px;font-weight:600;color:#94a3b8;min-width:28px;text-align:center">${esc(node.process_area_code)}</span>` 
                    : ''}
                
                <!-- Wave -->
                ${node.wave ? `<span style="font-size:10px;color:#94a3b8;margin-left:4px">W${node.wave}</span>` : ''}
                
                <!-- Actions (hover) -->
                <span class="node-acts" style="opacity:0;transition:opacity 0.15s;display:flex;gap:2px;margin-left:8px">
                    ${lvl < 4 ? `<button class="btn-icon" title="Add L${lvl+1}"
                        onclick="event.stopPropagation();ProjectSetupView.openCreateDialog(${lvl+1},'${node.id}')">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M8 3v10M3 8h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
                    </button>` : ''}
                    <button class="btn-icon" title="Edit"
                        onclick="event.stopPropagation();ProjectSetupView.openEditDialog('${node.id}',${lvl})">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
                    </button>
                    <button class="btn-icon btn-icon--danger" title="Delete"
                        onclick="event.stopPropagation();ProjectSetupView.confirmDelete('${node.id}','${esc(node.name)}')">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
                    </button>
                </span>
            </div>
            ${hasChildren && isExpanded ? node.children.map(c => renderTreeNode(c, depth + 1)).join('') : ''}
        </div>`;
}
```

CSS additions:
```css
.btn-icon { 
    background: none; border: none; cursor: pointer; padding: 4px;
    border-radius: var(--exp-radius-sm); color: #94a3b8; transition: all 0.15s;
    display: inline-flex; align-items: center; justify-content: center;
}
.btn-icon:hover { background: #f1f5f9; color: #475569; }
.btn-icon--danger:hover { background: #fee2e2; color: #dc2626; }
.setup-node__row { border-bottom: 1px solid #f1f5f9; }
```

#### 4. Table View — Inline-Editable data-table

When _viewMode === 'table', render a flat sortable table with inline add row:

```javascript
function renderTableView() {
    // Flatten tree into sorted list: L1, then its L2s, then L3s under each L2, etc.
    const flat = flattenTree(_tree);
    
    return `
        <div class="card" style="padding:0;overflow:hidden">
            <table class="data-table" style="font-size:13px;width:100%">
                <thead>
                    <tr>
                        <th style="width:50px">Level</th>
                        <th style="width:100px">Code</th>
                        <th style="min-width:200px">Name</th>
                        <th style="width:70px">Module</th>
                        <th style="width:80px">Scope</th>
                        <th style="width:50px">Wave</th>
                        <th style="width:120px">Parent</th>
                        <th style="width:80px;text-align:right">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${flat.map(node => renderTableRow(node)).join('')}
                </tbody>
                <tfoot>
                    <tr id="inlineAddRow" style="background:#f8fafc">
                        <td>
                            <select id="addLevel" class="inline-input" style="width:100%">
                                <option value="1">L1</option><option value="2">L2</option>
                                <option value="3">L3</option><option value="4">L4</option>
                            </select>
                        </td>
                        <td><input id="addCode" class="inline-input" placeholder="Auto" style="width:100%"></td>
                        <td><input id="addName" class="inline-input" placeholder="Name *" style="width:100%" 
                            onkeydown="if(event.key==='Enter')ProjectSetupView.submitInlineAdd()"></td>
                        <td>
                            <select id="addModule" class="inline-input" style="width:100%">
                                <option value="">—</option>
                                ${['FI','CO','MM','SD','PP','QM','EWM','HR','BC'].map(m => 
                                    `<option value="${m}">${m}</option>`).join('')}
                            </select>
                        </td>
                        <td>
                            <select id="addScope" class="inline-input" style="width:100%">
                                <option value="in_scope">In Scope</option>
                                <option value="out_of_scope">Out</option>
                                <option value="deferred">Deferred</option>
                            </select>
                        </td>
                        <td><input id="addWave" class="inline-input" type="number" min="1" max="9" placeholder="1" style="width:100%"></td>
                        <td>
                            <select id="addParent" class="inline-input" style="width:100%">
                                <option value="">— None (L1) —</option>
                                ${_flatList.filter(n => n.level < 4).map(n =>
                                    `<option value="${n.id}">${esc(n.code)} — ${esc(n.name?.substring(0,20))}</option>`
                                ).join('')}
                            </select>
                        </td>
                        <td style="text-align:right">
                            ${ExpUI.actionButton({ label: '✓ Add', variant: 'success', size: 'sm',
                                onclick: 'ProjectSetupView.submitInlineAdd()' })}
                        </td>
                    </tr>
                </tfoot>
            </table>
        </div>`;
}

function renderTableRow(node) {
    const lvl = node.level;
    const levelColor = `var(--exp-l${lvl})`;
    const levelBg = `var(--exp-l${lvl}-bg)`;
    const parentNode = _flatList.find(n => n.id === node.parent_id);
    
    return `<tr style="cursor:pointer" onclick="ProjectSetupView.openEditDialog('${node.id}',${lvl})">
        <td>
            <span style="display:inline-flex;align-items:center;justify-content:center;width:26px;height:20px;border-radius:4px;background:${levelBg};color:${levelColor};font-size:11px;font-weight:700">L${lvl}</span>
        </td>
        <td><code style="font-family:var(--exp-font-mono);font-size:11px">${esc(node.code || '')}</code></td>
        <td style="font-weight:${lvl <= 2 ? 600 : 400}">${esc(node.name || '')}</td>
        <td style="font-size:11px;color:#64748b">${esc(node.process_area_code || '—')}</td>
        <td>${ExpUI.pill({ label: (node.scope_status||'pending').replace(/_/g,' '), 
            variant: node.scope_status === 'in_scope' ? 'success' : node.scope_status === 'out_of_scope' ? 'danger' : 'warning', size: 'sm' })}</td>
        <td style="font-size:12px;color:#64748b">${node.wave ? 'W'+node.wave : '—'}</td>
        <td style="font-size:11px;color:#94a3b8">${parentNode ? esc(parentNode.code) : '—'}</td>
        <td style="text-align:right" onclick="event.stopPropagation()">
            <button class="btn-icon" onclick="ProjectSetupView.openEditDialog('${node.id}',${lvl})">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M11.5 1.5l3 3L5 14H2v-3L11.5 1.5z" stroke="currentColor" stroke-width="1.5"/></svg>
            </button>
            <button class="btn-icon btn-icon--danger" onclick="ProjectSetupView.confirmDelete('${node.id}','${esc(node.name)}')">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M3 4h10M6 4V3h4v1M5 4v9h6V4" stroke="currentColor" stroke-width="1.5"/></svg>
            </button>
        </td>
    </tr>`;
}
```

CSS for inline inputs:
```css
.inline-input {
    padding: 4px 6px; border: 1px solid #e2e8f0; border-radius: 4px;
    font-size: 12px; font-family: inherit; background: #fff;
}
.inline-input:focus { border-color: var(--sap-blue); outline: none; box-shadow: 0 0 0 2px rgba(37,99,235,0.1); }
```

#### 5. Inline Add (table mode)

```javascript
async function submitInlineAdd() {
    const level = parseInt(document.getElementById('addLevel')?.value);
    const name = document.getElementById('addName')?.value.trim();
    if (!name) { App.toast('Name is required', 'error'); return; }
    
    const parentId = document.getElementById('addParent')?.value || null;
    
    // Validate parent-level match
    if (level === 1 && parentId) { App.toast('L1 cannot have a parent', 'error'); return; }
    if (level > 1 && !parentId) { App.toast(`L${level} requires a parent`, 'error'); return; }
    
    const payload = {
        level, name, parent_id: parentId,
        code: document.getElementById('addCode')?.value.trim() || undefined,
        process_area_code: document.getElementById('addModule')?.value || undefined,
        scope_status: document.getElementById('addScope')?.value || 'in_scope',
        wave: parseInt(document.getElementById('addWave')?.value) || undefined,
    };
    
    try {
        await ExploreAPI.levels.create(_pid, payload);
        App.toast(`${name} created`, 'success');
        // Clear inputs
        ['addCode','addName','addWave'].forEach(id => { const el = document.getElementById(id); if(el) el.value = ''; });
        await reloadHierarchy();
    } catch (e) {
        App.toast(e.message || 'Creation failed', 'error');
    }
}
```

#### 6. AI Suggested — Placeholder Button

```javascript
function openAISuggested() {
    const html = `<div class="modal-content" style="max-width:480px;padding:32px;text-align:center">
        <div style="font-size:48px;margin-bottom:16px">🤖</div>
        <h2 style="margin-bottom:8px">AI-Suggested Hierarchy</h2>
        <p style="color:#64748b;margin-bottom:20px;line-height:1.6">
            AI will analyze your project's industry, SAP modules, and company profile to generate 
            a customized L1→L2→L3 process hierarchy.
        </p>
        <div style="background:#f8fafc;border-radius:var(--exp-radius-lg);padding:16px;margin-bottom:20px;text-align:left">
            <div style="font-size:13px;font-weight:600;margin-bottom:8px">What AI will do:</div>
            <div style="font-size:13px;color:#64748b;line-height:1.8">
                ✦ Analyze your industry & company profile<br>
                ✦ Map relevant SAP modules to processes<br>
                ✦ Generate L1→L2→L3 hierarchy with SAP Best Practice codes<br>
                ✦ Preview before import — you review & edit first
            </div>
        </div>
        ${ExpUI.pill({ label: 'Coming in Sprint 13', variant: 'info', size: 'md' })}
        <div style="margin-top:20px">
            ${ExpUI.actionButton({ label: 'Close', variant: 'secondary', onclick: 'App.closeModal()' })}
        </div>
    </div>`;
    App.openModal(html);
}
```

#### 7. Empty State — Three Cards

```javascript
function renderEmptyState(container) {
    container.innerHTML = `
        <div style="padding:60px 20px;text-align:center;max-width:800px;margin:0 auto">
            <div style="font-size:56px;margin-bottom:12px">🏗️</div>
            <h2 style="margin-bottom:8px;font-size:22px">No Process Hierarchy Defined</h2>
            <p style="color:#64748b;margin-bottom:32px;font-size:14px">
                Build your L1 → L4 process structure to start your SAP project
            </p>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;text-align:left">
                
                <!-- Card 1: Import Template -->
                <div class="card" style="padding:24px;cursor:pointer;border:2px solid transparent;transition:all 0.2s"
                     onclick="ProjectSetupView.openTemplateImport()"
                     onmouseenter="this.style.borderColor='var(--sap-blue)';this.style.boxShadow='var(--exp-shadow-md)'"
                     onmouseleave="this.style.borderColor='transparent';this.style.boxShadow=''">
                    <div style="font-size:32px;margin-bottom:12px">📚</div>
                    <div style="font-weight:700;margin-bottom:6px">Import SAP Template</div>
                    <div style="font-size:13px;color:#64748b;line-height:1.5">
                        Pre-built L1→L4 hierarchy from SAP Best Practice catalog. 
                        Select areas to import.
                    </div>
                    <div style="margin-top:12px">${ExpUI.pill({label:'5 areas · 265 items', variant:'info', size:'sm'})}</div>
                </div>
                
                <!-- Card 2: AI Suggested -->
                <div class="card" style="padding:24px;cursor:pointer;border:2px solid transparent;transition:all 0.2s;position:relative"
                     onclick="ProjectSetupView.openAISuggested()"
                     onmouseenter="this.style.borderColor='#8B5CF6';this.style.boxShadow='var(--exp-shadow-md)'"
                     onmouseleave="this.style.borderColor='transparent';this.style.boxShadow=''">
                    <div style="position:absolute;top:12px;right:12px">${ExpUI.pill({label:'Coming Soon', variant:'pending', size:'sm'})}</div>
                    <div style="font-size:32px;margin-bottom:12px">🤖</div>
                    <div style="font-weight:700;margin-bottom:6px">AI-Suggested Hierarchy</div>
                    <div style="font-size:13px;color:#64748b;line-height:1.5">
                        AI generates a customized hierarchy based on your industry, 
                        SAP modules, and company profile.
                    </div>
                    <div style="margin-top:12px">${ExpUI.pill({label:'Powered by AI', variant:'decision', size:'sm'})}</div>
                </div>
                
                <!-- Card 3: Manual -->
                <div class="card" style="padding:24px;cursor:pointer;border:2px solid transparent;transition:all 0.2s"
                     onclick="ProjectSetupView.openCreateDialog(1, null)"
                     onmouseenter="this.style.borderColor='var(--exp-l3)';this.style.boxShadow='var(--exp-shadow-md)'"
                     onmouseleave="this.style.borderColor='transparent';this.style.boxShadow=''">
                    <div style="font-size:32px;margin-bottom:12px">✍️</div>
                    <div style="font-weight:700;margin-bottom:6px">Start from Scratch</div>
                    <div style="font-size:13px;color:#64748b;line-height:1.5">
                        Manually create your process areas one by one. 
                        Full control over structure.
                    </div>
                    <div style="margin-top:12px">${ExpUI.pill({label:'Flexible', variant:'draft', size:'sm'})}</div>
                </div>
            </div>
        </div>`;
}
```

#### 8. Helper functions

```javascript
function flattenTree(nodes, result = []) {
    for (const n of nodes) {
        result.push(n);
        if (n.children) flattenTree(n.children, result);
    }
    return result;
}

function matchesSearch(node) {
    const q = _searchQuery.toLowerCase();
    return (node.name || '').toLowerCase().includes(q) || 
           (node.code || '').toLowerCase().includes(q);
}

function setSearch(val) { _searchQuery = val; rerenderContent(); }
function setFilter(key, val) { _filters[key] = val === _filters[key] ? null : val; rerenderContent(); }
function setViewMode(mode) { _viewMode = mode; rerenderContent(); }

function rerenderContent() {
    const el = document.getElementById('hierarchyContent');
    if (!el) return;
    el.innerHTML = _viewMode === 'tree' ? renderTreeContent() : renderTableView();
}
```

#### 9. Return (public API)

```javascript
return {
    render, switchTab, toggleNode,
    setSearch, setFilter, setViewMode,
    openCreateDialog, submitCreate,
    openEditDialog, submitEdit,
    confirmDelete, executeDelete,
    openTemplateImport, submitTemplateImport,
    openAISuggested,
    submitInlineAdd,
};
```

### Diğer Dosya Değişiklikleri

**index.html — sidebar:** Programs ile RAID arasına:
```html
<div class="sidebar__item" data-view="project-setup">
    <span class="sidebar__item-icon">⚙️</span>
    Project Setup
</div>
```

**index.html — script tag:** Diğer view script'lerinin yanına:
```html
<script src="/static/js/views/project_setup.js"></script>
```

**app.js — views registry:**
```javascript
'project-setup': () => ProjectSetupView.render(),
```

**app.js — programRequiredViews:**
```javascript
'project-setup'
```

### Verification Checklist

1. Sidebar "⚙️ Project Setup" → sayfa yüklenir, 4 tab gösterilir
2. Boş proje → 3 kartlı empty state (Import, AI Coming Soon, Manual)
3. "📚 Import Template" → checkbox dialog → import → KPI'lar güncellenir
4. "🤖 AI Suggested" → "Coming in Sprint 13" modal
5. "✍️ Start from Scratch" → Create L1 modal
6. Tree view: level-colored L1-L4, hover actions (➕ ✏️ 🗑)
7. Table view: data-table, inline add row (tfoot), sortable columns
8. Inline add: level seç, ad gir, parent seç, Enter → oluşturulur
9. Search: tree ve table'da filtreler
10. Delete: cascade preview → confirm

### Commit
```
feat(ui): add professional Project Setup page with tree/table views, template import, AI placeholder
```

---

## Summary

| Deliverable | Detail |
|-------------|--------|
| **KPI row** | 5 metric: L1/L2/L3/L4 counts + In Scope % |
| **Toolbar** | Search, area filter, tree/table toggle, 3 action buttons |
| **Tree view** | Level-colored borders, expand/collapse, hover action SVG icons |
| **Table view** | data-table with inline add row (tfoot), click-to-edit |
| **Empty state** | 3 clickable cards (Import, AI Coming Soon, Manual) |
| **AI button** | "Coming in Sprint 13" info modal |
| **Effort** | ~8h (frontend), Prompt A (backend ~4h) ayrı |
