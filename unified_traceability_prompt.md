# 🔗 UNIFIED TRACEABILITY — Full SAP Activate Chain
## Copilot Implementation Prompt (3 Blocks)

**Date:** 2026-02-13
**Priority:** P0 — Traceability is the backbone of SAP transformation projects
**Scope:** Full SAP Activate: Scope Item → Process → Workshop → Requirement → WRICEF/Config → FS/TS → Test → Defect + Open Items + Decisions + Interfaces + Cutover

---

## PROBLEM STATEMENT

Two traceability systems exist, both broken or incomplete:

1. **Explore Trace** (`trace_explore_requirement` in `app/services/traceability.py`):
   - Endpoint: `GET /api/v1/trace/requirement/<id>` (audit_bp.py line 88)
   - Works but shallow: depth 2/4, missing upstream (Workshop, Scope Item, Process Step)
   - Only traces ExploreRequirement → BacklogItem/ConfigItem → TestCase → Defect

2. **Program-Domain Trace** (`get_chain` in `app/services/traceability.py`):
   - Service function exists with 14 entity types and full up/downstream traversal
   - **NO ROUTE REGISTERED** — frontend calls `API.get('/traceability/backlog_item/${id}')` → 404
   - backlog.js lines 881, 925 hit this missing endpoint → "Could not load traceability data."

**Result:** Backlog item trace completely broken. Requirement trace partially working but missing the full SAP chain.

---

## TARGET ARCHITECTURE

### Unified Trace Endpoint
```
GET /api/v1/traceability/<entity_type>/<entity_id>
```

Supports ALL entity types from a single endpoint. Returns a structured graph with:
- `entity` — the requested entity
- `upstream` — ordered chain towards Scenario/Scope Item (parents)
- `downstream` — ordered chain towards Test/Defect (children)
- `lateral` — related entities at same level (Open Items, Decisions)
- `chain_depth` — max depth reached (1-6 scale for full SAP chain)
- `coverage` — counts by type
- `gaps` — where the chain breaks (missing links)

### Full SAP Activate Chain (6-level depth)
```
Level 1: Scope Item (1YG) / Scenario (O2C)
Level 2: L3 Process / Process Step → Workshop
Level 3: Requirement (REQ-014)
Level 4: WRICEF Item (ENH-009) / Config Item (CFG-003)
Level 5: Functional Spec → Technical Spec
Level 6: Test Case → Test Execution → Defect

Lateral links at each level:
  Requirement → Open Items, Decisions
  WRICEF Item → Interfaces → Connectivity Tests, Switch Plans
  Workshop → Attendees, Agenda, Minutes
```

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 1: BACKEND — Unified Traceability Endpoint
# ═══════════════════════════════════════════════════════════════

## CONTEXT

```
Platform: SAP Transformation Platform (Flask + PostgreSQL + SQLAlchemy)
Repo: umutsoyyilmaz/SAP_Transformation_Platform
Key files:
  - app/services/traceability.py   — existing trace engine (get_chain, trace_explore_requirement)
  - app/blueprints/audit_bp.py     — has /trace/requirement/<id> endpoint
  - app/blueprints/backlog_bp.py   — backlog CRUD, NO trace endpoint
  - app/blueprints/testing_bp.py   — has /traceability-matrix endpoint
  - static/js/views/backlog.js     — calls missing /traceability/backlog_item/<id>
  - static/js/components/trace-view.js — TraceView modal component

Models (app/models/):
  - scenario.py: Scenario, Workshop
  - scope.py: Process (L1-L4), Analysis, RequirementProcessMapping
  - requirement.py: Requirement
  - explore.py: ExploreRequirement, ExploreOpenItem, RequirementOpenItemLink
  - backlog.py: BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec
  - testing.py: TestCase, Defect (has test_case_id, backlog_item_id, config_item_id, explore_requirement_id)
  - integration.py: Interface, Wave, ConnectivityTest, SwitchPlan
```

## TASK 1.1: Register Unified Traceability Blueprint

Create `app/blueprints/traceability_bp.py`:

```python
"""
Unified Traceability API — Full SAP Activate Chain
GET /api/v1/traceability/<entity_type>/<entity_id>

Supported entity_type values:
  scenario, workshop, process, analysis, requirement,
  explore_requirement, backlog_item, config_item,
  functional_spec, technical_spec, test_case, defect,
  interface, wave, connectivity_test, switch_plan
"""
from flask import Blueprint, jsonify, request
from app.services.traceability import get_chain, trace_explore_requirement

traceability_bp = Blueprint("traceability_bp", __name__)


@traceability_bp.route("/traceability/<entity_type>/<entity_id>", methods=["GET"])
def unified_trace(entity_type, entity_id):
    """
    Unified traceability endpoint.
    
    Returns the full upstream + downstream chain for any entity.
    
    Query params:
      - depth: max traversal depth (default: 10, max: 20)
      - include_lateral: include Open Items, Decisions, etc. (default: true)
    """
    try:
        max_depth = min(int(request.args.get("depth", 10)), 20)
        include_lateral = request.args.get("include_lateral", "true").lower() == "true"
    except (ValueError, TypeError):
        max_depth = 10
        include_lateral = True

    # Special handling for explore_requirement (uses string IDs like "REQ-014")
    if entity_type == "explore_requirement":
        try:
            graph = trace_explore_requirement(entity_id)
            # Enhance with upstream context (Workshop → Process → Scenario)
            graph["upstream"] = _build_explore_upstream(entity_id)
            if include_lateral:
                graph["lateral"] = _build_explore_lateral(entity_id)
            graph["chain_depth"] = _calculate_full_depth(graph)
            graph["gaps"] = _find_chain_gaps(graph)
            return jsonify(graph), 200
        except ValueError as e:
            return jsonify({"error": str(e)}), 404

    # Standard entity trace (uses integer IDs)
    try:
        eid = int(entity_id)
    except (ValueError, TypeError):
        return jsonify({"error": f"Invalid entity_id: {entity_id}"}), 400

    chain = get_chain(entity_type, eid)
    if chain is None:
        return jsonify({"error": f"{entity_type} with id {eid} not found"}), 404

    # Enhance chain with lateral links
    if include_lateral:
        chain["lateral"] = _build_lateral_links(entity_type, eid)

    # Calculate full SAP chain depth
    chain["chain_depth"] = _calculate_chain_depth(chain)
    chain["gaps"] = _find_gaps_in_chain(entity_type, eid, chain)

    return jsonify(chain), 200


def _build_explore_upstream(requirement_id):
    """
    Build upstream context for an ExploreRequirement.
    ExploreRequirement → Workshop → Scenario/Process
    """
    from app.models.explore import ExploreRequirement
    from app.models.scenario import Workshop
    from app.models import db

    req = db.session.get(ExploreRequirement, requirement_id)
    if not req:
        return []

    upstream = []
    
    # Workshop link
    if req.workshop_id:
        ws = db.session.get(Workshop, req.workshop_id)
        if ws:
            upstream.append({
                "type": "workshop",
                "id": ws.id,
                "title": ws.title or ws.name,
                "code": getattr(ws, "code", ""),
                "status": getattr(ws, "status", ""),
            })
            # Workshop → Scenario
            if ws.scenario_id:
                from app.models.scenario import Scenario
                scenario = db.session.get(Scenario, ws.scenario_id)
                if scenario:
                    upstream.append({
                        "type": "scenario",
                        "id": scenario.id,
                        "title": scenario.name,
                        "code": getattr(scenario, "code", ""),
                    })

    # Process Step link (via requirement → process mapping or direct field)
    if hasattr(req, "process_step_id") and req.process_step_id:
        from app.models.scope import Process
        ps = db.session.get(Process, req.process_step_id)
        if ps:
            upstream.append({
                "type": "process_step",
                "id": ps.id,
                "title": ps.name,
                "level": ps.level,
            })
            # Walk up process hierarchy
            parent = ps
            while parent.parent_id:
                parent = db.session.get(Process, parent.parent_id)
                if parent:
                    upstream.append({
                        "type": f"process_l{parent.level}" if hasattr(parent, 'level') else "process",
                        "id": parent.id,
                        "title": parent.name,
                        "level": getattr(parent, "level", None),
                    })
                else:
                    break

    # Scope Item link (if available on requirement or via scenario)
    if hasattr(req, "scope_item_id") and req.scope_item_id:
        upstream.append({
            "type": "scope_item",
            "id": req.scope_item_id,
            "title": getattr(req, "scope_item_code", req.scope_item_id),
        })

    return upstream


def _build_explore_lateral(requirement_id):
    """Get Open Items and Decisions linked to an ExploreRequirement."""
    from app.models.explore import RequirementOpenItemLink, ExploreOpenItem
    from app.models import db

    lateral = {"open_items": [], "decisions": []}

    # Open Items (M:N)
    links = RequirementOpenItemLink.query.filter_by(requirement_id=requirement_id).all()
    for lnk in links:
        oi = db.session.get(ExploreOpenItem, lnk.open_item_id)
        if oi:
            lateral["open_items"].append({
                "id": oi.id, "code": oi.code, "title": oi.title,
                "status": oi.status, "priority": oi.priority,
            })

    # Decisions (if ExploreDecision model exists)
    try:
        from app.models.explore import ExploreDecision
        decisions = ExploreDecision.query.filter_by(requirement_id=requirement_id).all()
        for d in decisions:
            lateral["decisions"].append({
                "id": d.id, "code": getattr(d, "code", ""),
                "title": d.title, "status": getattr(d, "status", ""),
            })
    except Exception:
        pass  # Model may not exist yet

    return lateral


def _build_lateral_links(entity_type, entity_id):
    """Build lateral links for standard entities."""
    lateral = {}
    
    if entity_type == "requirement":
        from app.models import db
        from app.models.requirement import Requirement
        req = db.session.get(Requirement, entity_id)
        if req:
            # Check for open items via traces
            try:
                from app.models.explore import RequirementOpenItemLink, ExploreOpenItem
                links = RequirementOpenItemLink.query.filter_by(requirement_id=entity_id).all()
                lateral["open_items"] = []
                for lnk in links:
                    oi = db.session.get(ExploreOpenItem, lnk.open_item_id)
                    if oi:
                        lateral["open_items"].append({
                            "id": oi.id, "code": oi.code, "title": oi.title,
                            "status": oi.status,
                        })
            except Exception:
                pass

    elif entity_type == "backlog_item":
        from app.models import db
        from app.models.integration import Interface
        interfaces = Interface.query.filter_by(backlog_item_id=entity_id).all()
        lateral["interfaces"] = [
            {"id": i.id, "code": i.code, "name": i.name,
             "direction": i.direction, "status": i.status}
            for i in interfaces
        ]

    return lateral


def _calculate_full_depth(graph):
    """
    Calculate chain depth on a 1-6 scale for full SAP Activate.
    1 = Requirement only
    2 = + WRICEF/Config
    3 = + FS/TS
    4 = + Test Cases
    5 = + Defects
    6 = Full chain with upstream (Scenario/Process/Workshop)
    """
    depth = 1
    if graph.get("backlog_items") or graph.get("config_items"):
        depth = 2
    if graph.get("test_cases"):
        depth = max(depth, 4)
    if graph.get("defects"):
        depth = max(depth, 5)
    if graph.get("upstream"):
        depth = max(depth, 6)
    return depth


def _calculate_chain_depth(chain):
    """Calculate chain depth from upstream/downstream lists."""
    types_found = set()
    for item in chain.get("upstream", []) + chain.get("downstream", []):
        types_found.add(item.get("type"))
    
    depth = 1
    if "backlog_item" in types_found or "config_item" in types_found:
        depth = max(depth, 2)
    if "functional_spec" in types_found or "technical_spec" in types_found:
        depth = max(depth, 3)
    if "test_case" in types_found:
        depth = max(depth, 4)
    if "defect" in types_found:
        depth = max(depth, 5)
    if "scenario" in types_found or "process" in types_found:
        depth = max(depth, 6)
    return depth


def _find_chain_gaps(graph):
    """Identify where the chain breaks (missing links)."""
    gaps = []
    
    # Requirement has no WRICEF/Config → gap at level 2
    if not graph.get("backlog_items") and not graph.get("config_items"):
        gaps.append({"level": 2, "message": "No WRICEF or Config items linked"})
    
    # Has WRICEF but no tests → gap at level 4
    if (graph.get("backlog_items") or graph.get("config_items")) and not graph.get("test_cases"):
        gaps.append({"level": 4, "message": "No test cases found for linked items"})
    
    # Has tests but no executions/defects → potential gap
    if graph.get("test_cases") and not graph.get("defects"):
        gaps.append({"level": 5, "message": "No defects recorded (may be expected if tests pass)"})
    
    # No upstream context
    if not graph.get("upstream"):
        gaps.append({"level": 0, "message": "Missing upstream context (Workshop/Process/Scenario)"})
    
    return gaps


def _find_gaps_in_chain(entity_type, entity_id, chain):
    """Find gaps in a standard entity chain."""
    gaps = []
    types_found = set(item.get("type") for item in chain.get("upstream", []) + chain.get("downstream", []))
    
    if entity_type in ("backlog_item", "config_item"):
        if "requirement" not in types_found:
            gaps.append({"level": "upstream", "message": "Not linked to a Requirement"})
        if "test_case" not in types_found:
            gaps.append({"level": "downstream", "message": "No Test Cases created"})
        if "functional_spec" not in types_found:
            gaps.append({"level": "downstream", "message": "No Functional Spec written"})
    
    elif entity_type == "requirement":
        if "backlog_item" not in types_found and "config_item" not in types_found:
            gaps.append({"level": "downstream", "message": "Not converted to WRICEF or Config item"})
        if "scenario" not in types_found:
            gaps.append({"level": "upstream", "message": "Not linked to a Scenario"})
    
    elif entity_type == "test_case":
        if "requirement" not in types_found and "backlog_item" not in types_found:
            gaps.append({"level": "upstream", "message": "Not linked to a Requirement or Backlog item"})
    
    return gaps
```

## TASK 1.2: Register the Blueprint

In `app/__init__.py` or wherever blueprints are registered, add:

```python
from app.blueprints.traceability_bp import traceability_bp
app.register_blueprint(traceability_bp, url_prefix="/api/v1")
```

**IMPORTANT:** Check how existing blueprints are registered and follow the same pattern.
Search: `grep -n "register_blueprint" app/__init__.py app/main.py run.py 2>/dev/null`

## TASK 1.3: Verify & Test

```bash
# Restart server
# Then test:

# 1. Backlog item trace (was broken — Image 1)
curl -s http://localhost:5000/api/v1/traceability/backlog_item/1 | python3 -m json.tool

# 2. Explore requirement trace (was shallow — Image 2)  
curl -s http://localhost:5000/api/v1/traceability/explore_requirement/REQ-014 | python3 -m json.tool

# 3. Scenario trace (full tree)
curl -s http://localhost:5000/api/v1/traceability/scenario/1 | python3 -m json.tool

# 4. Test case trace (upstream to requirement)
curl -s http://localhost:5000/api/v1/traceability/test_case/1 | python3 -m json.tool

# 5. Defect trace (full upstream chain)
curl -s http://localhost:5000/api/v1/traceability/defect/1 | python3 -m json.tool

# All should return 200 with upstream/downstream/lateral/gaps
```

## TASK 1.4: Fix Frontend API Calls

In `static/js/views/backlog.js`, the calls at lines ~881 and ~925 use:
```javascript
const chain = await API.get(`/traceability/backlog_item/${i.id}`);
```

This now works because the new endpoint matches `/api/v1/traceability/backlog_item/<id>`.

**VERIFY:** Check if `API.get()` prepends `/api/v1` automatically.
```bash
grep -n "baseURL\|API_BASE\|prefix.*api" static/js/api.js static/js/explore-api.js 2>/dev/null | head -10
```

If API.get already prepends `/api/v1`, the frontend call works as-is.
If NOT, update backlog.js line 881 and 925 to use the correct path:
```javascript
const chain = await API.get(`/traceability/backlog_item/${i.id}`);
// OR if prefix not automatic:
const chain = await fetch(`/api/v1/traceability/backlog_item/${i.id}`).then(r => r.json());
```

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 2: FRONTEND — Unified TraceChain Visual Component
# ═══════════════════════════════════════════════════════════════

## CONTEXT

```
Existing component: static/js/components/trace-view.js
  - TraceView.showForRequirement(reqId) — opens modal
  - TraceView.renderInline(reqId) — returns HTML promise
  - Only works for ExploreRequirement, uses /api/v1/trace/requirement/<id>

Frontend stack: Vanilla JS, no framework
Design system: Perga brand (navy #0B1623, gold #C08B5C, marble #F7F5F0)
CSS approach: Utility classes + component CSS in <style> blocks
```

## TASK 2.1: Create Unified Trace Component

Create `static/js/components/trace-chain.js`:

The component should expose:
```javascript
const TraceChain = (() => {
    /**
     * Show full trace chain in a modal for any entity type.
     * @param {string} entityType - e.g. 'backlog_item', 'explore_requirement', 'test_case'
     * @param {string|number} entityId - the entity's ID
     */
    async function show(entityType, entityId) { ... }

    /**
     * Render inline trace summary (for detail page tabs).
     * @param {string} entityType
     * @param {string|number} entityId
     * @param {HTMLElement} container - DOM element to render into
     */
    async function renderInTab(entityType, entityId, container) { ... }

    return { show, renderInTab };
})();
```

### Visual Design Requirements

The trace chain should render as a **horizontal/vertical flow diagram** showing:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Scenario │───▶│ Process  │───▶│ Workshop │───▶│   Req    │───▶│  WRICEF  │───▶│   Test   │
│  O2C     │    │ L3 Step  │    │  WS-003  │    │ REQ-014  │    │ ENH-009  │    │ TC-001   │
│          │    │          │    │          │    │ ■ Gap    │    │ ■ Active │    │ ■ Pass   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                      │
                                                      ├──▶ [Open Items: 2]
                                                      └──▶ [Decisions: 1]
```

**Color coding by entity type:**
- Scenario/Process: `#3B82F6` (blue)
- Workshop: `#8B5CF6` (purple)
- Requirement: based on type — Fit=`#10B981` (green), Gap=`#EF4444` (red), Partial=`#F59E0B` (amber)
- WRICEF/Config: `#C08B5C` (Perga gold)
- FS/TS: `#6B7280` (gray)
- Test: based on result — Pass=`#10B981`, Fail=`#EF4444`, Pending=`#6B7280`
- Defect: based on severity — Critical=`#EF4444`, High=`#F59E0B`, Medium=`#3B82F6`
- Open Item: `#F97316` (orange)
- Interface: `#06B6D4` (cyan)

**Chain depth indicator:**
Show a progress bar: `█████░` 5/6 — with label explaining what's missing.

**Gaps section:**
Highlight missing links with warning icons:
```
⚠️ Missing: No Functional Spec written
⚠️ Missing: No Test Cases created
```

**Clickable nodes:**
Each box in the chain should be clickable → navigates to that entity's detail page.
Use the existing `showView('entity-detail', {id: X})` navigation pattern.

### Modal Structure

```html
<div id="traceChainModal" class="modal-overlay" style="display:none">
  <div class="modal-panel" style="max-width:900px; max-height:85vh; overflow:auto">
    <div class="modal-header">
      <h3>🔗 Traceability Chain</h3>
      <span class="modal-subtitle"><!-- entity code + title --></span>
      <button onclick="TraceChain.close()" class="modal-close">✕</button>
    </div>
    
    <div class="chain-depth-bar">
      <!-- 6-segment progress bar -->
    </div>
    
    <div class="chain-flow">
      <!-- Upstream boxes (right-to-left or top-to-bottom) -->
      <!-- Current entity (highlighted) -->
      <!-- Downstream boxes -->
    </div>
    
    <div class="chain-lateral" style="display:none">
      <!-- Open Items, Decisions, Interfaces -->
    </div>
    
    <div class="chain-gaps" style="display:none">
      <!-- Warning messages for missing links -->
    </div>
  </div>
</div>
```

## TASK 2.2: Include the Component

In `templates/base.html` or wherever scripts are loaded, add:
```html
<script src="/static/js/components/trace-chain.js"></script>
```

Check existing script loading:
```bash
grep -n "trace-view\|components/" templates/base.html templates/*.html 2>/dev/null | head -10
```

Add the new script AFTER `trace-view.js` (if it exists) so it can optionally delegate.

## TASK 2.3: Wire Up Backlog Detail Traceability Tab

In `static/js/views/backlog.js`, find the `_renderDetailTrace` function (around line 921) and update:

```javascript
async _renderDetailTrace(container, item) {
    // Use new unified TraceChain component
    if (typeof TraceChain !== 'undefined') {
        await TraceChain.renderInTab('backlog_item', item.id, container);
    } else {
        // Fallback: direct API call
        try {
            const chain = await API.get(`/traceability/backlog_item/${item.id}`);
            // render basic chain view
            container.innerHTML = this._renderBasicChain(chain);
        } catch (err) {
            container.innerHTML = `<div class="card" style="margin-top:12px">
                <p>Could not load traceability data.</p>
            </div>`;
        }
    }
}
```

## TASK 2.4: Wire Up Requirements Trace Button

In `static/js/views/explore_requirements.js`, update the Trace button (around line 231):

```javascript
// Replace:
actions.push(ExpUI.actionButton({ 
    label: '🔍 Trace', variant: 'ghost', size: 'sm', 
    onclick: `TraceView.showForRequirement('${r.id}')` 
}));

// With:
actions.push(ExpUI.actionButton({ 
    label: '🔍 Trace', variant: 'ghost', size: 'sm', 
    onclick: `TraceChain.show('explore_requirement', '${r.id}')` 
}));
```

Keep TraceView as fallback — the new TraceChain internally calls the unified endpoint.

## TASK 2.5: Add Trace Buttons to Test Case & Defect Views

In `static/js/views/test_execution.js`, the traceability tab (line 28) should use:
```javascript
case 'traceability': 
    if (typeof TraceChain !== 'undefined') {
        await TraceChain.renderInTab('test_case', testCaseId, container);
    } else {
        await renderTraceability(); // existing fallback
    }
    break;
```

---

# ═══════════════════════════════════════════════════════════════
# BLOCK 3: INTEGRATION — Testing, Migration & Validation
# ═══════════════════════════════════════════════════════════════

## TASK 3.1: API Contract Tests

Create or extend test script to validate the unified endpoint:

```bash
#!/bin/bash
echo "═══ Unified Traceability API Tests ═══"
BASE="http://localhost:5000/api/v1"

# Test each entity type
for TYPE in scenario requirement backlog_item config_item test_case defect; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/traceability/$TYPE/1")
    if [ "$STATUS" = "200" ] || [ "$STATUS" = "404" ]; then
        echo "  ✅ GET /traceability/$TYPE/1 → $STATUS"
    else
        echo "  ❌ GET /traceability/$TYPE/1 → $STATUS (expected 200 or 404)"
    fi
done

# Test explore_requirement with string ID
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/traceability/explore_requirement/REQ-001")
echo "  ✅ GET /traceability/explore_requirement/REQ-001 → $STATUS"

# Test invalid type
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/traceability/invalid_type/1")
if [ "$STATUS" = "404" ]; then
    echo "  ✅ Invalid type returns 404"
else
    echo "  ❌ Invalid type should return 404, got $STATUS"
fi

# Verify response structure
echo ""
echo "═══ Response Structure Check ═══"
RESP=$(curl -s "$BASE/traceability/backlog_item/1")
for FIELD in entity upstream downstream chain_depth gaps; do
    if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$FIELD' in d" 2>/dev/null; then
        echo "  ✅ Response has '$FIELD'"
    else
        echo "  ❌ Response missing '$FIELD'"
    fi
done
```

## TASK 3.2: Verify Frontend Fix (Manual)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1 | Backlog trace loads | Open any WRICEF item → Traceability tab | Chain renders (not "Could not load") |
| 2 | Requirement trace | Requirements → click Trace button | Modal shows full chain with upstream |
| 3 | Chain depth | REQ with linked WRICEF + Test | Depth shows 4/6 or higher |
| 4 | Gaps shown | REQ with WRICEF but no Test | Gap warning: "No Test Cases" |
| 5 | Clickable nodes | Click a node in the chain | Navigates to that entity's detail |
| 6 | Lateral links | REQ with Open Items | Open Items shown as lateral branch |

## TASK 3.3: Update Notion Defect Tracker

Mark these defects as resolved:
- **Backlog Traceability broken** — fixed by adding unified endpoint
- **Requirement trace shallow (depth 2/4)** — fixed by adding upstream context

## TASK 3.4: Git Commit

```bash
git add -A
git commit -m "feat: Unified traceability endpoint + visual chain component

- New: GET /api/v1/traceability/<entity_type>/<entity_id>
- Supports 16 entity types with full upstream/downstream/lateral traversal
- Full SAP Activate chain: Scenario → Process → Workshop → Req → WRICEF → FS/TS → Test → Defect
- Includes: Open Items, Decisions, Interfaces, Connectivity Tests
- Chain depth indicator (1-6 scale)
- Gap detection (missing links highlighted)
- New TraceChain.js visual component with flow diagram
- Fixes: Backlog item traceability 404 error
- Fixes: Requirement trace shallow depth (was 2/4, now 6/6 when full chain exists)"
```

---

## DEPENDENCY ORDER

```
Block 1 (Backend) ──── must be first
    │
    ├──▶ Block 2 (Frontend) ──── depends on Block 1 endpoints
    │
    └──▶ Block 3 (Testing) ──── depends on both
```

Block 1 can be tested independently with curl.
Block 2 requires Block 1 endpoints to be live.
Block 3 validates everything together.

---

## CRITICAL RULES

1. ❌ Do NOT remove existing trace-view.js — keep as fallback
2. ❌ Do NOT modify existing traceability.py service functions — the new endpoint WRAPS them
3. ✅ Use the existing `get_chain()` and `trace_explore_requirement()` functions
4. ✅ New blueprint file — don't modify audit_bp.py or testing_bp.py
5. ✅ Check API prefix pattern before wiring frontend
6. ✅ Test with curl before touching frontend
7. ✅ Use Perga brand colors (navy, gold, marble) for the visual component
