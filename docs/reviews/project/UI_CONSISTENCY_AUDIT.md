# UI Consistency Audit Report

**Date:** 2026-02-13 (last updated)  
**Scope:** All 21 view files in `static/js/views/`, plus `static/js/app.js`, `static/js/mobile.js`, and `static/css/main.css`  
**Auditor:** Automated analysis  
**Status:** Point-in-time audit — many findings addressed via UI-Sprint + S24 Final Polish

---

## Executive Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 6 |
| 🟠 Major | 28 |
| 🟡 Minor | 19 |

**Top systemic issues:**
1. **`form-control` class used in 6 files but NOT defined in CSS** — only `form-input` exists. All form inputs in those files are unstyled.
2. **Two views bypass `App.openModal()` with custom modal functions** — breaking ESC to close, backdrop clicks, and z-index consistency.
3. **Hardcoded hex colors epidemic** — 17 of 19 view files use hardcoded colors instead of CSS variables.
4. **Undefined CSS variables** referenced by multiple views (`--sap-accent`, `--sap-shadow-sm`, `--sap-bg-secondary`, etc.).

---

## Category 1: Wrong/Undefined CSS Variable Names

### 🔴 Critical

#### C1-1: `data_factory.js` — Undefined `--sap-accent`
- **Line ~460** (inside `_modal()` close button): `color: var(--sap-accent)`
- `--sap-accent` is **not defined** in `:root`. Will fall back to browser default (no color applied).
- **Fix:** Replace with `var(--sap-blue)`.

#### C1-2: `data_factory.js` — Undefined `--sap-shadow-sm`
- **Line ~460** (modal box-shadow): `box-shadow: var(--sap-shadow-sm)`
- `--sap-shadow-sm` is **not defined**. Only `--shadow` and `--shadow-md` exist.
- **Fix:** Replace with `var(--shadow)`.

#### C1-3: `integration.js` — Undefined SAP Fiori variable names
- **Lines 148, 155:** `var(--sapGroup_ContentBorderColor)` — NOT DEFINED
- **Lines 257, 397, 524:** `var(--sapContent_LabelColor)` — NOT DEFINED
- **Lines 257, 304:** `var(--sapNegativeColor)` — NOT DEFINED
- These appear to be SAP Fiori Fundamentals variable names, but this project uses custom `--sap-*` variables.
- **Fix:** Map to `--sap-border`, `--sap-text-secondary`, and `--sap-negative` respectively.

### 🟠 Major

#### C1-4: `program.js` — Wrong variable prefix `--text-secondary`
- **Lines ~227, 232, 267, 294, 324, 356:** `color: var(--text-secondary)`
- Should be `var(--sap-text-secondary)`. Missing `--sap-` prefix means the value resolves to nothing.
- **Fix:** Replace all `var(--text-secondary)` with `var(--sap-text-secondary)`.

#### C1-5: `backlog.js` — Undefined `--sap-bg-secondary`
- **Line ~843** (_renderDetailSpecs): `background: var(--sap-bg-secondary)`
- `--sap-bg-secondary` is **not defined**. Only `--sap-bg` (#f5f6f7) exists.
- **Fix:** Replace with `var(--sap-bg)`.

#### C1-6: `cutover.js` — Undefined `--card-bg` with fallback
- **Line ~480:** Uses `var(--card-bg)` (not defined), though some instances use `var(--sap-card-bg)` correctly.
- **Fix:** Standardize to `var(--sap-card-bg)`.

---

## Category 2: Inconsistent Modal Implementations

### 🔴 Critical

#### C2-1: `data_factory.js` — Custom `_modal()` function bypasses App.openModal()
- **Line ~460:** Defines its own `_modal(title, body)` function.
- Uses `z-index: 1000` (App.openModal uses `z-index: 200`) — inconsistent stacking.
- **No ESC key handler** — user cannot press ESC to close.
- **No backdrop click** to close.
- Custom close button styling instead of `class="modal-close"`.
```js
// data_factory.js ~line 460
function _modal(title, body) {
    // ... z-index: 1000, custom close button
}
```
- **Fix:** Refactor to use `App.openModal(html)`.

#### C2-2: `cutover.js` — Custom `_modal()` function bypasses App.openModal()
- **Line ~472:** Defines its own `_modal(title, body)` function.
- Uses `z-index: 9999` — extremely inconsistent with the app standard of 200.
- **No ESC key handler.**
- **No backdrop click.**
- Injects dynamic `<style>` blocks for `.fiori-field`/`.fiori-row` classes.
```js
// cutover.js ~line 472
function _modal(title, body) {
    // ... z-index: 9999
}
```
- **Fix:** Refactor to use `App.openModal(html)`.

### 🟠 Major

#### C2-3: Explore views — Missing modal-close X button
All 4 Explore views that use modals rely exclusively on `ExpUI.actionButton` for Cancel instead of including the standard `<button class="modal-close">` X button:
- **explore_workshops.js** — Create Workshop dialog
- **explore_workshop_detail.js** — Document view modal
- **explore_hierarchy.js** — Sign-off dialog, seed dialog
- **explore_requirements.js** — Create/convert dialogs

The standard pattern (used by program.js, raid.js, test_planning.js, test_execution.js) is:
```html
<div class="modal-header"><h2>Title</h2>
    <button class="modal-close" onclick="App.closeModal()">&times;</button>
</div>
```
- **Fix:** Add `<button class="modal-close" onclick="App.closeModal()">&times;</button>` to all Explore modal headers.

#### C2-4: `project_setup.js` — Missing modal-close X button in all dialogs
- Create dialog (line ~773), edit dialog (line ~829), delete confirm (line ~867), template import (line ~899), bulk entry (line ~392), AI suggested (line ~943)
- All use `App.openModal()` correctly but lack the modal-close X button.
- **Fix:** Add modal-close button to each dialog.

---

## Category 3: Wrong Table Classes

### 🟠 Major

#### C3-1: `raid.js` — Uses `class="table"` instead of `class="data-table"`
- **Line 170:** `<table class="table">` — in heatmap cell detail popup
- **Line 505:** `<table class="table">` — in item detail view fields
- `class="table"` has NO styles in main.css. Only `class="data-table"` (line 296 of main.css) is defined.
```js
// raid.js line 170
<table class="table"><thead><tr><th>Code</th>...
// raid.js line 505
<table class="table">${fields}</table>
```
- **Fix:** Replace `class="table"` with `class="data-table"`.

---

## Category 4: Undefined/Wrong CSS Classes (Non-variable)

### 🔴 Critical

#### C4-1: `form-control` class used across 6 files — NOT DEFINED in main.css
Only `form-input` (line 381) is defined. The following files use the nonexistent `form-control`:

| File | Approximate Lines | Occurrences |
|------|------------------|-------------|
| raid.js | 564-643 | ~19 |
| defect_management.js | 70-234 | ~18 |
| test_execution.js | 129-700+ | ~20+ |
| test_planning.js | 740-870 | ~12 |
| ai_admin.js | 343 | 1 |

**All form inputs/selects/textareas in these files receive NO custom styling.** They render with browser defaults.

Files using the **correct** `form-input` class: `backlog.js`, `project_setup.js`.

- **Fix:** Global find-and-replace `class="form-control"` → `class="form-input"` in all view files.

### 🟠 Major

#### C4-2: `ai_admin.js` — Uses `class="view-header"` instead of `class="page-header"`
- **Line 14:** `<div class="view-header">` 
- Every other view uses `class="page-header"` (defined at line 569 of main.css). `view-header` is not defined.
- **Fix:** Replace with `class="page-header"`.

### 🟡 Minor

#### C4-3: `ai_admin.js` — Uses `class="text-muted"` (not defined)
- Used for subtle text. `text-muted` is not defined in main.css.
- **Fix:** Use inline `style="color: var(--sap-text-secondary)"` or define the class.

#### C4-4: Tab class inconsistency — `class="tab"` vs `class="tab-btn"`
Both `.tab` (main.css line 1557) and `.tab-btn` (line 602) are defined with different styles:
- `ai_admin.js` lines 52-56: uses `class="tab"`
- `program.js`: uses `class="tab-btn"`
- Explore views: use `class="exp-tab"` (their own design system)
- **Recommendation:** Standardize core views on one class. `.tab-btn` is the earlier, more complete definition.

---

## Category 5: Excessive Inline Styles

### 🟠 Major

#### C5-1: `data_factory.js` — Heavy inline styles on KPI cards
- **Lines 139-155:** Each KPI card has 4-5 inline style attributes for padding, border-radius, borders, and text.
```js
// data_factory.js ~line 139
`<div style="background:var(--sap-card-bg);border-radius:var(--radius);padding:20px;
  border-left:4px solid ${color};min-width:160px;flex:1">
  <div style="font-size:13px;color:var(--sap-text-secondary)">${label}</div>
  <div style="font-size:28px;font-weight:700;color:${color}">${value}</div>
</div>`
```
- **Fix:** Use the existing `kpi-card` class or create a reusable component.

#### C5-2: `explore_hierarchy.js` — Inline styles on sign-off dialog inputs
- Sign-off dialog inputs use full inline styles instead of form classes:
```js
style="width:100%;padding:8px;border:1px solid var(--sap-border);border-radius:var(--exp-radius-md)"
```
- **Fix:** Use `class="form-input"` or `class="exp-inline-form"` input styles.

#### C5-3: `cutover.js` — Dynamic `<style>` injection
- **Line ~480:** Injects a `<style>` block for `.fiori-field` and `.fiori-row` classes into the modal body.
- **Fix:** Move these styles to main.css.

### 🟡 Minor

#### C5-4: Widespread `style="color:#999"` / `style="color:#666"` patterns
Found across test_planning.js, test_execution.js, defect_management.js, and raid.js as fallback text colors. Should use `var(--sap-text-secondary)`.

#### C5-5: `project_setup.js` — Inline hover handlers
- **Lines ~272-300** (empty state cards): Uses `onmouseenter`/`onmouseleave` JS for hover effects instead of CSS `:hover`.
```js
onmouseenter="this.style.borderColor='var(--sap-blue)';this.style.boxShadow='var(--exp-shadow-md)'"
onmouseleave="this.style.borderColor='transparent';this.style.boxShadow=''"
```
- **Fix:** Define a CSS class like `.setup-card:hover { ... }`.

---

## Category 6: Hardcoded Colors

### 🟠 Major

This is the most pervasive issue. Nearly every view hardcodes hex colors instead of using CSS variables.

#### C6-1: `executive_cockpit.js` — Hardcoded RAG colors map
- **Lines 19-21:**
```js
const RAG_COLORS = { green: '#30914c', amber: '#e76500', red: '#cc1919' };
```
- These match `--sap-positive`, `--sap-warning`, `--sap-negative` respectively.
- Also hardcoded in Chart.js datasets: `'#30914c'`, `'#cc1919'`, `'#e76500'`, `'#d9d9d9'`.
- KPI cards use inline `border-left: 4px solid ${border}` with hardcoded RAG color.
- **Fix:** Use `getComputedStyle` to read CSS variables, or define a shared RAG color utility.

#### C6-2: `reports.js` — Different hardcoded RAG colors
- **Line ~10:**
```js
const RAG_COLORS = { green: '#27AE60', amber: '#F39C12', red: '#E74C3C' };
```
- These are **different hex values** from executive_cockpit.js and from the CSS variables.
- `--sap-positive` is `#30914c`, not `#27AE60`. `--sap-negative` is `#cc1919`, not `#E74C3C`.
- **Fix:** Align with CSS variable values.

#### C6-3: `data_factory.js` — Four hardcoded color maps
- STATUS_COLORS, WAVE_COLORS, LOAD_COLORS, RECON_COLORS — all use hardcoded hex values.
- Table cells at lines ~278-280: hardcoded `#30914c`, `#bb0000`.
- **Fix:** Extract to shared CSS variables or a JS utility using CSS variable values.

#### C6-4: `explore_dashboard.js` — Hardcoded colors throughout
- Chart.js: `'#30914c'`, `'#e76500'`, `'#0070f2'`, `'#d9d9d9'`
- renderReqPipeline(): 6 hardcoded colors inline (`'#a9b4be'`, `'#e76500'`, `'#0070f2'`, `'#6c3483'`, `'#30914c'`, `'#1e8449'`)
- renderReadinessCard(): `'#f0f0f0'`, `'#e2e8f0'` borders
- renderCoverageMatrix(): hardcoded statusColors map
- renderGapHeatmap(): inline background/color styles

#### C6-5: `explore_workshops.js` — Hardcoded colors
- kpiBlock: `'#3b82f6'`
- areaMilestoneTracker: `'#94a3b8'`, `'#3b82f6'`, `'#f59e0b'`, `'#10b981'`

#### C6-6: `explore_workshop_detail.js` — Hardcoded colors
- `'#f1f5f9'`, `'#e2e8f0'` borders
- `'#f0f9ff'` background for current session

#### C6-7: `explore_requirements.js` — Hardcoded colors
- `'#e2e8f0'` border-top in expanded details
- `'#3b82f6'` in kpiBlocks and metric bars

#### C6-8: `explore_hierarchy.js` — Hardcoded colors
- `'#e2e8f0'`, `'#fafbfc'` in L3 consolidated card

#### C6-9: `ai_admin.js` — Hardcoded chart colors
- `'#0070f2'`, `'#e76500'`, `'#107e3e'`, `'#bb0000'`, `'#1a9898'`

#### C6-10: `test_planning.js` — Hardcoded badge colors throughout
- typeBadge(): `{ SIT: '#0070f3', UAT: '#107e3e', Regression: '#a93e7e', ... }`
- statusBadge(): `{ draft: '#888', active: '#0070f3', locked: '#e9730c', ... }`
- resultBadge(): `{ pass: '#107e3e', fail: '#c4314b', blocked: '#e9730c', ... }`
- Performance chart: `'#0070f3'`, `'#c4314b'`
- Dependency headings: hardcoded `color:#c4314b`, `color:#e9730c`

#### C6-11: `test_execution.js` — Hardcoded badge/chart colors throughout
- statusBadge, resultBadge redefine same color maps as test_planning.js
- Entry/exit criteria: `'#107e3e'`, `'#c4314b'`, `'#f0f0f0'`, `'#e0e0e0'`
- Go/No-Go scorecard: `'#107e3e'`, `'#e5a800'`, `'#c4314b'`
- Snapshot chart: `'#107e3e'`, `'#c4314b'`
- KPI card conditional color: `style="color:${value >= 80 ? '#107e3e' : '#c4314b'}"`

#### C6-12: `defect_management.js` — Hardcoded badge colors
- sevBadge: `{ S1: '#c4314b', S2: '#e9730c', S3: '#0070f3', S4: '#888' }`
- statusBadge: `{ new: '#0070f3', in_progress: '#e9730c', resolved: '#107e3e', ... }`
- slaBadge: hardcoded background in breach conditions
- Border: `'#e0e0e0'`

#### C6-13: `raid.js` — Hardcoded status/priority colors
- statusBadge, priorityBadge, ragDot, scoreBadge — all use inline hardcoded colors.

#### C6-14: `backlog.js` — Hardcoded Tailwind-like hex colors
- _priorityBadge(): `'#dc2626'`, `'#ea580c'`, `'#2563eb'`, `'#9ca3af'`
- _statusBadge(): `'#6b7280'`, `'#2563eb'`, `'#d97706'`, `'#16a34a'`, `'#7c3aed'`, `'#dc2626'`

### 🟡 Minor

#### C6-15: `integration.js` — Badge colors with solid background pattern
- Badges use hardcoded `background: #color; color: #fff` pattern.

#### C6-16: `program.js` — Mostly clean, minor hardcoded usage
- Uses CSS variables for most styling ✓
- Some Chart.js datasets may have hardcoded colors.

---

## Category 7: Inconsistent Badge Usage

### 🟠 Major

#### C7-1: Duplicate badge color maps across test_planning.js and test_execution.js
- Both files define identical `statusBadge()` and `resultBadge()` local functions with the same hardcoded color maps.
- Pattern used:
```js
`<span class="badge" style="background:${c[status]||'#888'};color:#fff">${status}</span>`
```
- **Fix:** Extract to `TestingShared` as a reusable utility.

#### C7-2: Inconsistent badge pattern — CSS class vs inline style
- **Standard pattern** (program.js, executive_cockpit.js): `class="badge badge-${status}"` — uses CSS-defined badge variants.
- **Inline override pattern** (raid.js, defect_management.js, test_planning.js, test_execution.js, data_factory.js, cutover.js): `class="badge" style="background:#hex;color:#fff"` — overrides all badge CSS.
- **Fix:** Define `badge-pass`, `badge-fail`, `badge-blocked`, `badge-draft`, `badge-active` etc. in main.css and stop using inline backgrounds.

#### C7-3: `backlog.js` — Non-standard badge colors
- Uses Tailwind-like hex colors (`#dc2626`, `#ea580c`, `#2563eb`) that don't match the SAP variable palette used elsewhere.

---

## Category 8: Inconsistent Button Styling

### 🟡 Minor

#### C8-1: `raid.js` — Non-standard modal close buttons
- **Lines ~163, 502, 528, 542:** Uses `class="btn btn-sm"` with `onclick="App.closeModal()"` for close buttons, instead of the standard `class="modal-close"`.
```js
// raid.js ~line 163
<button class="btn btn-sm" onclick="App.closeModal()">Close</button>
```
- Standard X button pattern: `<button class="modal-close" onclick="App.closeModal()">&times;</button>`
- These render as regular buttons instead of the minimal X close button.
- **Fix:** Add proper `modal-close` X button in modal headers.

#### C8-2: `test_execution.js` — Inline button colors for run actions
- **Run execution modal (~line 720):** Complete/Fail/Abort buttons use inline styles:
```js
<button class="btn btn-sm" style="background:#107e3e;color:#fff">✅ Complete (Pass)</button>
<button class="btn btn-sm" style="background:#c4314b;color:#fff">❌ Complete (Fail)</button>
```
- **Fix:** Use `class="btn btn-sm btn-success"` and `class="btn btn-sm btn-danger"`.

#### C8-3: `test_planning.js` — Inline button colors in suite detail footer
- **Suite detail modal (~line 870):**
```js
<button class="btn btn-sm" style="background:#6a4fa0;color:#fff">⚙ Generate from WRICEF</button>
<button class="btn btn-sm" style="background:#0070f3;color:#fff">🔄 Generate from Process</button>
```
- **Fix:** Use `class="btn btn-sm btn-primary"` or define appropriate variant classes.

---

## Category 9: Missing Accessibility

### 🟠 Major

#### C9-1: Tables without `<caption>` or `aria-label` across all views
- No view file includes table accessibility attributes. All `<table class="data-table">` elements lack `aria-label`, `<caption>`, or `role="table"`.

#### C9-2: Custom modals (data_factory.js, cutover.js) lack `role="dialog"` and `aria-modal`
- The standard `App.openModal()` has the overlay but custom implementations have no ARIA attributes.

### 🟡 Minor

#### C9-3: Clickable table rows lack keyboard accessibility
- **raid.js, test_planning.js, program.js:** Rows with `onclick` handlers use `style="cursor:pointer"` but have no `tabindex="0"`, `role="button"`, or `onkeydown` handler.

#### C9-4: Icon-only buttons without `aria-label`
- Across nearly all views, emoji-based action buttons (✏️, 🗑, ▶) lack `aria-label` describing the action.
```js
<button class="btn btn-sm" onclick="...">✏️</button>  // No aria-label
```

#### C9-5: Color-only status indicators
- RAG badges and status badges convey meaning through color alone with no textual/icon alternative for color-blind users. (Some do include text labels, which partially mitigates this.)

---

## Category 10: Other UI Consistency Issues

### 🟡 Minor

#### C10-1: Duplicate `esc()` / `escHtml()` helper definitions
Multiple files define their own HTML-escaping helpers instead of sharing one:
- `testing_shared.js`: `esc()` — Used by test_planning.js, test_execution.js, defect_management.js via `TestingShared.esc`
- `program.js`: Own local `escHtml()` and `escAttr()`
- `ai_query.js`: Own local `escHtml()`
- `backlog.js`: Uses `escHtml` (unknown source)
- `data_factory.js`: Own implementation
- Explore views: Use `ExpUI.esc`
- **Recommendation:** Extract to a single shared utility.

#### C10-2: KPI card class naming variants
- **executive_cockpit.js:** Uses `cockpit-kpi`, `cockpit-kpi__value`, `cockpit-kpi__label` (BEM, defined in CSS)
- **test_execution.js traceability:** Uses `kpi-card`, `kpi-value`, `kpi-label` — but CSS defines `kpi-card__value` and `kpi-card__label` (with `__`). `kpi-value` and `kpi-label` without the BEM prefix are **not defined**.
- Explore views: Use `ExpUI.kpiBlock()` component (generates exp-specific markup)
- **Fix:** Standardize KPI card class names or use a shared component.

#### C10-3: Header class pattern varies
- Most views: `class="page-header"` ✓
- `ai_admin.js` line 14: `class="view-header"` ✗
- Explore views: own heading patterns via ExpUI
- `data_factory.js`: uses `class="page-header"` ✓

#### C10-4: `project_setup.js` paste mode uses `form-input` while the grid mode uses `inline-input`
- Paste textarea (line ~440): `class="form-input"` ✓
- Grid inputs: `class="inline-input"` ✓ (different purpose, this is acceptable)
- **This is correct behavior**, just noting the two different form input classes.

#### C10-5: Inconsistent empty state patterns
- Some views use `<div class="empty-state">` (defined in CSS) with BEM sub-elements.
- Others use ad-hoc styling with `style="text-align:center;padding:40px"`.

---

## Summary Table by File

| File | Critical | Major | Minor | Key Issues |
|------|----------|-------|-------|-----------|
| data_factory.js | 2 | 2 | 1 | Custom modal, undefined CSS vars, hardcoded colors |
| integration.js | 1 | 0 | 1 | Undefined SAP Fiori variables |
| test_planning.js | 1* | 2 | 2 | `form-control` undefined, hardcoded badges |
| test_execution.js | 1* | 2 | 2 | `form-control` undefined, hardcoded badges |
| backlog.js | 0 | 2 | 1 | Undefined `--sap-bg-secondary`, non-standard colors |
| raid.js | 1* | 2 | 1 | `form-control` undefined, `class="table"`, hardcoded colors |
| cutover.js | 1 | 1 | 1 | Custom modal z-index:9999, dynamic styles |
| defect_management.js | 1* | 1 | 0 | `form-control` undefined, hardcoded badges |
| reports.js | 0 | 1 | 0 | Different RAG color values from CSS vars |
| program.js | 0 | 1 | 1 | Wrong `--text-secondary` prefix |
| executive_cockpit.js | 0 | 1 | 0 | Hardcoded RAG_COLORS |
| explore_dashboard.js | 0 | 2 | 0 | Hardcoded colors, no modal-close |
| explore_workshops.js | 0 | 1 | 1 | Missing modal-close X, hardcoded colors |
| explore_workshop_detail.js | 0 | 1 | 1 | Missing modal-close X, hardcoded colors |
| explore_hierarchy.js | 0 | 1 | 1 | Missing modal-close X, inline form styles |
| explore_requirements.js | 0 | 1 | 1 | Missing modal-close X, hardcoded colors |
| ai_query.js | 0 | 0 | 1 | Duplicate escHtml |
| ai_admin.js | 0 | 2 | 1 | `view-header`, `form-control`, `text-muted` |
| project_setup.js | 0 | 1 | 1 | Missing modal-close X, inline hover handlers |
| testing_shared.js | 0 | 0 | 0 | Clean ✓ |

*\* Shares the critical `form-control` issue (C4-1)*

---

## Recommended Fix Priority

### Sprint 1 (Immediate — all Critical)
1. **Global replace `form-control` → `form-input`** in raid.js, defect_management.js, test_execution.js, test_planning.js, ai_admin.js (fixes unstyled forms)
2. **Refactor custom `_modal()` in data_factory.js and cutover.js** to use `App.openModal()`
3. **Fix undefined CSS variables**: `--sap-accent` → `--sap-blue`, `--sap-shadow-sm` → `--shadow`, `--text-secondary` → `--sap-text-secondary`, integration.js Fiori vars → standard `--sap-*` vars

### Sprint 2 (Major — consistency)
4. **Add `modal-close` X buttons** to all Explore view modals and project_setup.js dialogs
5. **Fix `class="table"`** → `class="data-table"` in raid.js (lines 170, 505)
6. **Fix `class="view-header"`** → `class="page-header"` in ai_admin.js
7. **Create shared badge utility** (extracting duplicate statusBadge/resultBadge from test_planning + test_execution into TestingShared)
8. **Standardize RAG color values** across reports.js and executive_cockpit.js to match CSS variables

### Sprint 3 (Minor — polish & hardcoded colors)
9. **Extract hardcoded hex colors to CSS variables** across all files (biggest effort item)
10. **Consolidate `esc()`/`escHtml()` helpers** into one shared utility
11. **Add ARIA attributes** to modals, tables, and icon buttons
12. **Replace inline hover JS** with CSS `:hover` rules in project_setup.js
