# ADR-008: Test Management Architecture Redesign
## Full SAP Activate Traceability

**Status:** Approved  
**Date:** 2026-02-18  
**Author:** Umut Soyyılmaz + Claude  
**Scope:** TestCase, TestSuite, TestPlan, TestCycle, TestExecution  
**Impact:** Model changes, new service layer, migration, frontend updates

---

## 1. Decision Summary

Three architectural changes to make test management fully traceable per SAP Activate methodology:

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | **L3 scope item mandatory** for unit/sit/uat test cases | Every test must answer "which L3 am I testing?" |
| D2 | **TestCase ↔ Suite becomes N:M** (junction table) | A TC can belong to OTC E2E + SD Regression suites simultaneously |
| D3 | **Suite loses `suite_type`**, becomes pure library package | Suite is a reusable grouping; test phase is determined by Plan/Cycle |

---

## 2. Context — SAP Activate Test Hierarchy

```
SAP Activate Phase      Platform Entity         Test Relevance
─────────────────       ───────────────         ──────────────
Discover                Program                 —
Prepare                 L1 Value Chain          —
                        L2 Process Area         Scope grouping
                        L3 E2E Process ◄────────────── TEST SCOPE ANCHOR
                        L4 Sub-Process          Detailed steps
Explore                 ProcessStep             Fit/Gap origin
                        Workshop                Analysis context
                        ExploreRequirement      Gap/Partial → development need
Realize                 BacklogItem (WRICEF)    Custom development
                        ConfigItem              Standard config
                        FunctionalSpec          Design doc
                        TechnicalSpec           Technical design
Test                    TestCase ◄──────────────── MUST TRACE TO L3
                        TestSuite               Reusable TC package
                        TestPlan                Execution strategy
                        TestCycle               Execution round
                        TestExecution           Individual run
                        Defect                  Failure record
Deploy                  CutoverPlan             Go-live readiness
                        UATSignOff              Business acceptance
```

**Core principle: L3 is the atomic unit of scope.** Go-live decisions, coverage reports, UAT sign-offs — all are L3-based. A test case without L3 linkage is invisible to governance.

---

## 3. Current State — Problems

### 3.1 TestCase → L3: Optional (nullable)

```python
# Current: app/models/testing.py line ~405
process_level_id = db.Column(
    db.String(36), ForeignKey("process_levels.id", ondelete="SET NULL"),
    nullable=True,  # ← PROBLEM: no enforcement
)
```

**Consequence:** Manual catalog TC creation bypasses scope. Coverage gaps go undetected.

### 3.2 TestCase → Suite: 1:N (single suite_id FK)

```python
# Current: app/models/testing.py line ~406
suite_id = db.Column(
    db.Integer, ForeignKey("test_suites.id", ondelete="SET NULL"),
    nullable=True,  # TC belongs to at most ONE suite
)
```

**Consequence:** A VA01 "Create Sales Order" TC cannot be in both "OTC E2E Suite" and "SD Regression Suite" without duplication. In real projects this forces either:
- Duplicate TCs (maintenance nightmare, divergent results)
- Flat suite structure (one mega-suite, defeats purpose)

### 3.3 Suite has `suite_type` competing with Plan `plan_type`

```python
# Suite:
suite_type = db.Column(db.String(30), default="SIT")  # SIT|UAT|Regression|E2E|Performance|Custom

# Plan:
plan_type = db.Column(db.String(30), default="sit")   # sit|uat|regression|e2e|cutover_rehearsal|performance
```

**Consequence:** Ambiguous ownership. Is the suite SIT-only or can it be used in UAT? In practice, suites like "FI Period Close" run in both SIT and UAT. Locking suite_type prevents reuse.

### 3.4 generate_from_wricef() doesn't set process_level_id

```python
# Current: app/services/testing_service.py, generate_from_wricef()
tc = TestCase(
    backlog_item_id=item.id if is_backlog else None,
    config_item_id=item.id if not is_backlog else None,
    requirement_id=item.requirement_id if hasattr(item, "requirement_id") else None,
    # ← MISSING: process_level_id not resolved from WRICEF → Requirement → L3 chain
)
```

### 3.5 TestCycleSuite junction is decorative

`TestCycleSuite` links suites to cycles but `populate_cycle_from_plan()` ignores it entirely — it reads from `PlanTestCase` only. Suite assignment to cycle has no functional effect.

---

## 4. Target Architecture

### 4.1 Entity Relationship Diagram

```
                    ┌──────────────────────────────────┐
                    │        TEST CASE CATALOG          │
                    │   (L3 mandatory for unit/sit/uat) │
                    │                                    │
                    │  TC-SD-0012: Create Sales Order    │
                    │    → process_level_id: L3-OTC-010  │
                    │    → backlog_item_id: ENH-009       │
                    │    → explore_requirement_id: REQ-014 │
                    └──────────┬───────────┬─────────────┘
                               │           │
                    ┌──────────┘           └──────────┐
                    ▼                                  ▼
          ┌─────────────────┐               ┌─────────────────┐
          │ TestCaseSuiteLink│               │ TestCaseSuiteLink│
          │ (N:M junction)  │               │ (N:M junction)  │
          └────────┬────────┘               └────────┬────────┘
                   ▼                                  ▼
          ┌─────────────────┐               ┌─────────────────┐
          │   Suite A       │               │   Suite B       │
          │  "OTC E2E Flow" │               │ "SD Regression" │
          │   (no type)     │               │   (no type)     │
          └─────────────────┘               └─────────────────┘
                   │                                  │
          ┌────────┴─────────────────────────────────┘
          ▼
   ┌──────────────┐       ┌──────────────┐
   │  SIT Plan    │       │  UAT Plan    │
   │              │       │              │
   │ PlanScope:   │       │ PlanScope:   │
   │  L3-OTC-010  │       │  L3-OTC-010  │
   │  L3-FI-020   │       │  L3-FI-020   │
   │              │       │              │
   │ TC Pool:     │       │ TC Pool:     │
   │ (from scope  │       │ (from scope  │
   │  suggest +   │       │  suggest +   │
   │  suite       │       │  suite       │
   │  import)     │       │  import)     │
   └──────┬───────┘       └──────┬───────┘
          │                      │
     ┌────┴────┐            ┌────┴────┐
     │Cycle 1  │            │Cycle 1  │
     │Cycle 2  │            │Cycle 2  │
     └────┬────┘            └─────────┘
          │
     TestExecution
          │
     TestStepResult
```

### 4.2 Data Flow — Real SAP Project Example

```
1. CATALOG CREATION
   SA consultant creates TCs in catalog, each linked to L3:
   
   TC-SD-0012 "Create Standard Order"  → L3: OTC-010 (Order to Cash)
   TC-SD-0013 "Create Return Order"    → L3: OTC-010
   TC-FI-0045 "Post Invoice"           → L3: OTC-010 (cross-module)
   TC-FI-0046 "Period Close"           → L3: FI-020 (Month End Close)

2. SUITE ORGANIZATION
   Test lead groups TCs into reusable suites:
   
   "OTC E2E Flow"     = {TC-SD-0012, TC-SD-0013, TC-FI-0045}
   "SD Regression"    = {TC-SD-0012, TC-SD-0013}           ← TC-SD-0012 in BOTH
   "FI Period Close"  = {TC-FI-0045, TC-FI-0046}           ← TC-FI-0045 in BOTH

3. PLAN CREATION
   Test manager creates SIT Plan:
   
   SIT Plan — Wave 1
     Scope: L3-OTC-010, L3-FI-020
     Import Suite "OTC E2E Flow"     → 3 TCs added to pool
     Import Suite "FI Period Close"  → TC-FI-0046 added (TC-FI-0045 already in pool)
     Suggest from scope              → finds any TC linked to L3-OTC-010/FI-020 not yet in pool
     TC Pool: {TC-SD-0012, TC-SD-0013, TC-FI-0045, TC-FI-0046}

4. CYCLE EXECUTION
   SIT Cycle 1: populate from plan → 4 TestExecutions
     TC-SD-0012: Pass
     TC-SD-0013: Fail → DEF-001
     TC-FI-0045: Pass
     TC-FI-0046: Blocked (DEF-001 blocks FI close)
   
   SIT Cycle 2: carry forward failed+blocked → 2 TestExecutions
     TC-SD-0013: Pass (DEF-001 fixed)
     TC-FI-0046: Pass (unblocked)
   
   → SIT EXIT ✅

5. COVERAGE REPORT (L3-based)
   L3-OTC-010: 3/3 TC passed (100%) ✅
   L3-FI-020:  2/2 TC passed (100%) ✅
   Overall: 4/4 (100%) — Ready for UAT
```

---

## 5. Implementation Specification

### 5.1 New Model: TestCaseSuiteLink (N:M Junction)

**File:** `app/models/testing.py`

```python
class TestCaseSuiteLink(db.Model):
    """N:M junction: a test case can belong to multiple suites.
    
    Replaces the direct TestCase.suite_id FK (1:N) pattern.
    Tracks how the TC was added to the suite for audit purposes.
    """
    __tablename__ = "test_case_suite_links"
    __table_args__ = (
        db.UniqueConstraint("test_case_id", "suite_id", name="uq_tc_suite"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(
        db.Integer, db.ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    test_case_id = db.Column(
        db.Integer, db.ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    suite_id = db.Column(
        db.Integer, db.ForeignKey("test_suites.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    added_method = db.Column(
        db.String(30), default="manual",
        comment="manual | auto_wricef | auto_process | import | clone",
    )
    notes = db.Column(db.Text, default="")
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    test_case = db.relationship("TestCase", backref=db.backref("suite_links", lazy="dynamic"))
    suite = db.relationship("TestSuite", backref=db.backref("case_links", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "test_case_id": self.test_case_id,
            "suite_id": self.suite_id,
            "added_method": self.added_method,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "test_case_code": self.test_case.code if self.test_case else None,
            "test_case_title": self.test_case.title if self.test_case else None,
            "suite_name": self.suite.name if self.suite else None,
        }
```

### 5.2 TestCase Model Changes

```python
# DEPRECATE (keep for migration, remove in future release):
suite_id = db.Column(
    db.Integer, db.ForeignKey("test_suites.id", ondelete="SET NULL"),
    nullable=True, index=True,
    comment="DEPRECATED: Use test_case_suite_links. Kept for backward compat.",
)

# ADD helper property:
@property
def suites(self):
    """All suites this TC belongs to (via N:M junction)."""
    return [link.suite for link in self.suite_links]

@property
def suite_ids(self):
    """List of suite IDs for serialization."""
    return [link.suite_id for link in self.suite_links]
```

**to_dict() update:**
```python
def to_dict(self, include_steps=False):
    result = {
        ...
        # Old field (deprecated, backward compat)
        "suite_id": self.suite_id,
        # New field
        "suite_ids": self.suite_ids,
        "suites": [
            {"id": link.suite_id, "name": link.suite.name if link.suite else None}
            for link in self.suite_links
        ],
        ...
    }
```

### 5.3 TestSuite Model Changes

```python
# REMOVE suite_type, REPLACE with purpose:
# suite_type = db.Column(db.String(30), default="SIT")  ← DELETE

purpose = db.Column(
    db.String(200), default="",
    comment="Free-text purpose: 'E2E order flow', 'Regression pack for pricing', etc.",
)
tags = db.Column(
    db.Text, default="",
    comment="Comma-separated tags for filtering: 'e2e,otc,cross-module'",
)

# ADD helper:
@property
def test_cases_via_links(self):
    """All TCs in this suite via N:M junction."""
    return [link.test_case for link in self.case_links]

@property 
def case_count_via_links(self):
    """Count of TCs via junction (replaces old suite_id-based count)."""
    return self.case_links.count()
```

**to_dict() update:**
```python
def to_dict(self, include_cases=False):
    result = {
        ...
        "suite_type": self.suite_type,  # Keep for backward compat during transition
        "purpose": self.purpose,
        "case_count": self.case_count_via_links,  # Use junction-based count
        ...
    }
    if include_cases:
        result["test_cases"] = [
            link.test_case.to_dict() for link in self.case_links if link.test_case
        ]
    return result
```

### 5.4 Scope Resolution Service (New)

**File:** `app/services/scope_resolution.py`

```python
"""
Scope Resolution Service — resolves L3 process_level_id for any test-related entity.

Chain traversal:
  BacklogItem  → explore_requirement_id → ExploreRequirement.scope_item_id → L3
  ConfigItem   → explore_requirement_id → ExploreRequirement.scope_item_id → L3
  ExploreReq   → scope_item_id → L3
  ProcessStep  → process_level_id → L4 → parent_id → L3
  TestCase     → backlog_item_id / config_item_id / explore_requirement_id → resolve
"""
import logging
from app.models import db

logger = logging.getLogger(__name__)

# Test layers that REQUIRE L3 linkage
L3_REQUIRED_LAYERS = {"unit", "sit", "uat"}

# Test layers where L3 is recommended but not enforced
L3_RECOMMENDED_LAYERS = {"regression"}

# Test layers where L3 is optional
L3_OPTIONAL_LAYERS = {"performance", "cutover_rehearsal"}


def resolve_l3_for_tc(tc_data: dict) -> str | None:
    """
    Given TC creation/update data, resolve the L3 scope item ID.
    
    Resolution order (first match wins):
    1. Explicit process_level_id (if it IS an L3)
    2. process_level_id is L4 → walk up to parent L3
    3. backlog_item_id → ExploreRequirement.scope_item_id
    4. config_item_id → ExploreRequirement.scope_item_id
    5. explore_requirement_id → ExploreRequirement.scope_item_id
    
    Returns L3 process_level_id (string UUID) or None.
    """
    # Path 1: Explicit process_level_id
    pl_id = tc_data.get("process_level_id")
    if pl_id:
        resolved = _ensure_l3(pl_id)
        if resolved:
            return resolved

    # Path 2: Via BacklogItem (WRICEF)
    bi_id = tc_data.get("backlog_item_id")
    if bi_id:
        resolved = _resolve_from_backlog_item(bi_id)
        if resolved:
            return resolved

    # Path 3: Via ConfigItem
    ci_id = tc_data.get("config_item_id")
    if ci_id:
        resolved = _resolve_from_config_item(ci_id)
        if resolved:
            return resolved

    # Path 4: Via ExploreRequirement
    ereq_id = tc_data.get("explore_requirement_id")
    if ereq_id:
        resolved = _resolve_from_explore_requirement(ereq_id)
        if resolved:
            return resolved

    return None


def validate_l3_for_layer(test_layer: str, process_level_id: str | None) -> tuple[bool, str]:
    """
    Validate L3 requirement based on test layer.
    
    Returns (is_valid, error_message).
    """
    if test_layer in L3_REQUIRED_LAYERS:
        if not process_level_id:
            return False, (
                f"L3 scope item (process_level_id) is required for '{test_layer}' test layer. "
                f"Provide process_level_id directly, or link a backlog_item_id / config_item_id / "
                f"explore_requirement_id that traces to an L3."
            )
    return True, ""


def _ensure_l3(process_level_id: str) -> str | None:
    """If given ID is L3, return it. If L4, walk up to parent L3."""
    from app.models.explore.process import ProcessLevel

    pl = db.session.get(ProcessLevel, str(process_level_id))
    if not pl:
        return None

    if pl.level == 3:
        return pl.id

    if pl.level == 4 and pl.parent_id:
        parent = db.session.get(ProcessLevel, pl.parent_id)
        if parent and parent.level == 3:
            return parent.id

    # Walk up until L3 found (handles deeper nesting if any)
    current = pl
    visited = set()
    while current and current.parent_id and current.id not in visited:
        visited.add(current.id)
        current = db.session.get(ProcessLevel, current.parent_id)
        if current and current.level == 3:
            return current.id

    return None


def _resolve_from_backlog_item(backlog_item_id: int) -> str | None:
    """BacklogItem → ExploreRequirement.scope_item_id → L3."""
    from app.models.backlog import BacklogItem

    bi = db.session.get(BacklogItem, backlog_item_id)
    if not bi:
        return None

    if bi.explore_requirement_id:
        return _resolve_from_explore_requirement(bi.explore_requirement_id)

    return None


def _resolve_from_config_item(config_item_id: int) -> str | None:
    """ConfigItem → ExploreRequirement.scope_item_id → L3."""
    from app.models.backlog import ConfigItem

    ci = db.session.get(ConfigItem, config_item_id)
    if not ci:
        return None

    if ci.explore_requirement_id:
        return _resolve_from_explore_requirement(ci.explore_requirement_id)

    return None


def _resolve_from_explore_requirement(requirement_id: str) -> str | None:
    """ExploreRequirement.scope_item_id → L3 (already denormalized)."""
    from app.models.explore.requirement import ExploreRequirement

    ereq = db.session.get(ExploreRequirement, str(requirement_id))
    if not ereq:
        return None

    # scope_item_id is the denormalized L3 reference
    if ereq.scope_item_id:
        return _ensure_l3(ereq.scope_item_id)

    # Fallback: process_level_id on requirement (might be L4)
    if ereq.process_level_id:
        return _ensure_l3(ereq.process_level_id)

    # Fallback: process_step → L4 → L3
    if ereq.process_step_id:
        return _resolve_from_process_step(ereq.process_step_id)

    return None


def _resolve_from_process_step(process_step_id: str) -> str | None:
    """ProcessStep → process_level_id (L4) → parent_id → L3."""
    from app.models.explore.process import ProcessStep

    ps = db.session.get(ProcessStep, str(process_step_id))
    if not ps or not ps.process_level_id:
        return None

    return _ensure_l3(ps.process_level_id)
```

### 5.5 Endpoint Changes — create_test_case

**File:** `app/blueprints/testing_bp.py`

```python
from app.services.scope_resolution import resolve_l3_for_tc, validate_l3_for_layer

def create_test_case(pid):
    """Create a new test case with auto-generated code and L3 scope resolution."""
    program, err = _get_or_404(Program, pid)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    test_layer = data.get("test_layer", "sit")

    # ── L3 Scope Resolution ──
    resolved_l3 = resolve_l3_for_tc(data)
    if resolved_l3:
        data["process_level_id"] = resolved_l3

    # ── L3 Validation ──
    is_valid, error_msg = validate_l3_for_layer(test_layer, data.get("process_level_id"))
    if not is_valid:
        return jsonify({
            "error": error_msg,
            "resolution_attempted": True,
            "hint": "Ensure the linked WRICEF/Config/Requirement has a scope_item_id (L3) assigned."
        }), 400

    # ... rest of creation logic unchanged ...
    
    # ── Suite assignment via junction (if suite_ids provided) ──
    suite_ids = data.get("suite_ids", [])
    if data.get("suite_id"):
        suite_ids.append(data["suite_id"])  # backward compat
    
    for sid in set(suite_ids):
        link = TestCaseSuiteLink(
            test_case_id=tc.id,
            suite_id=sid,
            added_method="manual",
            tenant_id=tc.tenant_id,
        )
        db.session.add(link)
    
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(tc.to_dict()), 201
```

### 5.6 Service Changes — generate_from_wricef

```python
def generate_from_wricef(suite, wricef_ids=None, config_ids=None, scope_item_id=None):
    from app.services.scope_resolution import resolve_l3_for_tc
    
    # ... existing item gathering logic ...
    
    for item in items:
        is_backlog = isinstance(item, BacklogItem)
        
        # ── NEW: Resolve L3 from WRICEF → Requirement chain ──
        tc_data = {
            "backlog_item_id": item.id if is_backlog else None,
            "config_item_id": item.id if not is_backlog else None,
        }
        resolved_l3 = resolve_l3_for_tc(tc_data)
        
        tc = TestCase(
            program_id=suite.program_id,
            # ... existing fields ...
            backlog_item_id=item.id if is_backlog else None,
            config_item_id=item.id if not is_backlog else None,
            process_level_id=resolved_l3,  # ← NEW: auto-resolved L3
            requirement_id=item.requirement_id if hasattr(item, "requirement_id") else None,
        )
        db.session.add(tc)
        db.session.flush()
        
        # ── NEW: Create suite link via junction ──
        link = TestCaseSuiteLink(
            test_case_id=tc.id,
            suite_id=suite.id,
            added_method="auto_wricef",
            tenant_id=suite.tenant_id,
        )
        db.session.add(link)
        
        # ... existing step generation ...
```

### 5.7 Suite API Endpoint Changes

**New endpoints for N:M management:**

```python
@testing_bp.route("/testing/suites/<int:suite_id>/cases", methods=["GET"])
def list_suite_cases(suite_id):
    """List all test cases in a suite (via junction)."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    links = TestCaseSuiteLink.query.filter_by(suite_id=suite_id).all()
    return jsonify([link.to_dict() for link in links])


@testing_bp.route("/testing/suites/<int:suite_id>/cases", methods=["POST"])
def add_case_to_suite(suite_id):
    """Add a test case to a suite (N:M link)."""
    suite, err = _get_or_404(TestSuite, suite_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    tc_id = data.get("test_case_id")
    if not tc_id:
        return jsonify({"error": "test_case_id is required"}), 400
    
    existing = TestCaseSuiteLink.query.filter_by(
        test_case_id=tc_id, suite_id=suite_id
    ).first()
    if existing:
        return jsonify({"error": "Test case already in this suite"}), 409
    
    link = TestCaseSuiteLink(
        test_case_id=tc_id,
        suite_id=suite_id,
        added_method=data.get("added_method", "manual"),
        notes=data.get("notes", ""),
        tenant_id=suite.tenant_id,
    )
    db.session.add(link)
    err = db_commit_or_error()
    if err:
        return err
    return jsonify(link.to_dict()), 201


@testing_bp.route("/testing/suites/<int:suite_id>/cases/<int:tc_id>", methods=["DELETE"])
def remove_case_from_suite(suite_id, tc_id):
    """Remove a test case from a suite."""
    link = TestCaseSuiteLink.query.filter_by(
        test_case_id=tc_id, suite_id=suite_id
    ).first()
    if not link:
        return jsonify({"error": "Link not found"}), 404
    db.session.delete(link)
    err = db_commit_or_error()
    if err:
        return err
    return "", 204


@testing_bp.route("/testing/catalog/<int:case_id>/suites", methods=["GET"])
def list_tc_suites(case_id):
    """List all suites a test case belongs to."""
    tc, err = _get_or_404(TestCase, case_id)
    if err:
        return err
    links = TestCaseSuiteLink.query.filter_by(test_case_id=case_id).all()
    return jsonify([
        {"suite_id": l.suite_id, "suite_name": l.suite.name if l.suite else None,
         "added_method": l.added_method, "created_at": l.created_at.isoformat() if l.created_at else None}
        for l in links
    ])
```

### 5.8 L3 Scope Coverage Endpoint (New)

**File:** `app/blueprints/testing_bp.py`

```python
@testing_bp.route("/programs/<int:pid>/testing/scope-coverage/<string:l3_id>", methods=["GET"])
def l3_scope_coverage(pid, l3_id):
    """
    Full test coverage view for a single L3 scope item.
    
    Returns:
    - Standard process steps and their TC coverage
    - Requirements (gap/partial) and their WRICEF/Config → TC chains
    - Interfaces and their TC coverage
    - Overall readiness score
    """
    from app.models.explore.process import ProcessLevel, ProcessStep
    from app.models.explore.requirement import ExploreRequirement
    from app.models.backlog import BacklogItem, ConfigItem
    from app.models.integration import Interface

    l3 = db.session.get(ProcessLevel, str(l3_id))
    if not l3 or l3.level != 3:
        return jsonify({"error": "L3 process level not found"}), 404

    result = {
        "l3": {"id": l3.id, "code": l3.code, "name": l3.name, "scope_item_code": l3.scope_item_code},
        "process_steps": [],
        "requirements": [],
        "interfaces": [],
        "summary": {},
    }

    # ── 1. Standard Process Steps (L4 → ProcessStep → TC) ──
    l4_children = ProcessLevel.query.filter_by(parent_id=l3.id, level=4).all()
    total_steps = 0
    covered_steps = 0
    
    for l4 in l4_children:
        steps = ProcessStep.query.filter_by(process_level_id=l4.id).order_by(ProcessStep.sort_order).all()
        for step in steps:
            total_steps += 1
            # Find TCs linked to this L3 that cover this step area
            tcs = TestCase.query.filter_by(process_level_id=l3.id).all()
            step_tcs = [tc for tc in tcs if not tc.backlog_item_id and not tc.config_item_id]
            
            latest_result = _get_latest_execution_result(step_tcs)
            if latest_result in ("pass",):
                covered_steps += 1

            result["process_steps"].append({
                "l4_code": l4.code,
                "l4_name": l4.name,
                "step_name": step.name,
                "fit_decision": step.fit_decision,
                "test_cases": [
                    {"id": tc.id, "code": tc.code, "title": tc.title,
                     "latest_result": _get_latest_execution_result([tc])}
                    for tc in step_tcs
                ],
            })

    # ── 2. Requirements (Gap/Partial) → WRICEF/Config → TC ──
    explore_reqs = ExploreRequirement.query.filter_by(scope_item_id=l3.id).all()
    total_reqs = len(explore_reqs)
    covered_reqs = 0
    
    for ereq in explore_reqs:
        req_entry = {
            "id": ereq.id, "code": ereq.code, "title": ereq.title,
            "fit_status": ereq.fit_status, "status": ereq.status,
            "backlog_items": [], "config_items": [],
        }
        
        req_covered = True
        
        # WRICEF items
        for bi in (ereq.linked_backlog_items or []):
            bi_tcs = TestCase.query.filter_by(backlog_item_id=bi.id).all()
            bi_result = _get_latest_execution_result(bi_tcs)
            if bi_result != "pass":
                req_covered = False
            req_entry["backlog_items"].append({
                "id": bi.id, "code": bi.code, "title": bi.title,
                "wricef_type": bi.wricef_type,
                "test_cases": [
                    {"id": tc.id, "code": tc.code, "latest_result": _get_latest_execution_result([tc])}
                    for tc in bi_tcs
                ],
            })
        
        # Config items
        for ci in (ereq.linked_config_items or []):
            ci_tcs = TestCase.query.filter_by(config_item_id=ci.id).all()
            ci_result = _get_latest_execution_result(ci_tcs)
            if ci_result != "pass":
                req_covered = False
            req_entry["config_items"].append({
                "id": ci.id, "code": ci.code, "title": ci.title,
                "test_cases": [
                    {"id": tc.id, "code": tc.code, "latest_result": _get_latest_execution_result([tc])}
                    for tc in ci_tcs
                ],
            })
        
        if not req_entry["backlog_items"] and not req_entry["config_items"]:
            req_covered = False  # No items to test
        
        if req_covered:
            covered_reqs += 1
        
        result["requirements"].append(req_entry)

    # ── 3. Interfaces ──
    # Find interfaces linked to WRICEF items under this L3
    bi_ids = [bi.id for ereq in explore_reqs for bi in (ereq.linked_backlog_items or [])]
    if bi_ids:
        interfaces = Interface.query.filter(Interface.backlog_item_id.in_(bi_ids)).all()
        for iface in interfaces:
            iface_tcs = TestCase.query.filter(
                TestCase.title.contains(iface.code) | TestCase.description.contains(iface.code)
            ).all()
            result["interfaces"].append({
                "id": iface.id, "code": iface.code, "name": iface.name,
                "direction": iface.direction,
                "test_cases": [
                    {"id": tc.id, "code": tc.code, "latest_result": _get_latest_execution_result([tc])}
                    for tc in iface_tcs
                ],
            })

    # ── 4. Summary ──
    all_tcs = TestCase.query.filter_by(process_level_id=l3.id).all()
    total_tcs = len(all_tcs)
    passed_tcs = sum(1 for tc in all_tcs if _get_latest_execution_result([tc]) == "pass")
    failed_tcs = sum(1 for tc in all_tcs if _get_latest_execution_result([tc]) == "fail")
    not_run_tcs = sum(1 for tc in all_tcs if _get_latest_execution_result([tc]) in ("not_run", None))

    pass_rate = (passed_tcs / total_tcs * 100) if total_tcs > 0 else 0
    readiness = "ready" if pass_rate >= 95 and failed_tcs == 0 else "not_ready"

    result["summary"] = {
        "total_test_cases": total_tcs,
        "passed": passed_tcs,
        "failed": failed_tcs,
        "not_run": not_run_tcs,
        "pass_rate": round(pass_rate, 1),
        "readiness": readiness,
        "process_step_coverage": f"{covered_steps}/{total_steps}",
        "requirement_coverage": f"{covered_reqs}/{total_reqs}",
    }

    return jsonify(result)


def _get_latest_execution_result(test_cases):
    """Get the most recent execution result for a list of TCs."""
    if not test_cases:
        return None
    tc_ids = [tc.id for tc in test_cases]
    latest = TestExecution.query.filter(
        TestExecution.test_case_id.in_(tc_ids)
    ).order_by(TestExecution.executed_at.desc().nullslast()).first()
    return latest.result if latest else "not_run"
```

---

## 6. Migration Plan

### 6.1 Database Migration (Alembic)

```python
"""ADR-008: Test architecture redesign — N:M suite, L3 enforcement."""

def upgrade():
    # 1. Create junction table
    op.create_table(
        "test_case_suite_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tenant_id", sa.Integer, sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("test_case_id", sa.Integer, sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("suite_id", sa.Integer, sa.ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("added_method", sa.String(30), default="manual"),
        sa.Column("notes", sa.Text, default=""),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("test_case_id", "suite_id", name="uq_tc_suite"),
    )

    # 2. Migrate existing suite_id data to junction
    op.execute("""
        INSERT INTO test_case_suite_links (test_case_id, suite_id, added_method, created_at)
        SELECT id, suite_id, 'migration', CURRENT_TIMESTAMP
        FROM test_cases
        WHERE suite_id IS NOT NULL
    """)

    # 3. Add purpose column to test_suites
    op.add_column("test_suites", sa.Column("purpose", sa.String(200), default=""))

    # 4. Migrate suite_type to purpose
    op.execute("""
        UPDATE test_suites SET purpose = suite_type WHERE suite_type IS NOT NULL
    """)

    # 5. Backfill process_level_id where possible
    # This is best done in application code (scope_resolution service)
    # after migration, via a management command


def downgrade():
    op.drop_table("test_case_suite_links")
    op.drop_column("test_suites", "purpose")
```

### 6.2 Data Backfill Script

```python
"""Management command: backfill process_level_id on existing TCs."""

def backfill_tc_scope():
    from app.services.scope_resolution import resolve_l3_for_tc
    
    orphan_tcs = TestCase.query.filter(
        TestCase.process_level_id.is_(None),
        TestCase.test_layer.in_(["unit", "sit", "uat"]),
    ).all()
    
    resolved = 0
    unresolved = []
    
    for tc in orphan_tcs:
        tc_data = {
            "backlog_item_id": tc.backlog_item_id,
            "config_item_id": tc.config_item_id,
            "explore_requirement_id": tc.explore_requirement_id,
            "process_level_id": tc.process_level_id,
        }
        l3_id = resolve_l3_for_tc(tc_data)
        if l3_id:
            tc.process_level_id = l3_id
            resolved += 1
        else:
            unresolved.append({"id": tc.id, "code": tc.code, "title": tc.title})
    
    db.session.commit()
    
    return {
        "total_orphans": len(orphan_tcs),
        "resolved": resolved,
        "unresolved": unresolved,
    }
```

---

## 7. Test Plan

### 7.1 Unit Tests — Scope Resolution

```
test_resolve_l3_from_explicit_l3_id          → returns same ID
test_resolve_l3_from_l4_id                   → walks up to parent L3
test_resolve_l3_from_backlog_item            → WRICEF → Req → scope_item_id
test_resolve_l3_from_config_item             → Config → Req → scope_item_id
test_resolve_l3_from_explore_requirement     → direct scope_item_id
test_resolve_l3_from_process_step            → step → L4 → L3
test_resolve_l3_returns_none_for_orphan      → no chain found
test_validate_l3_required_for_unit           → unit without L3 → error
test_validate_l3_required_for_sit            → sit without L3 → error
test_validate_l3_required_for_uat            → uat without L3 → error
test_validate_l3_optional_for_performance    → performance without L3 → ok
test_validate_l3_optional_for_cutover        → cutover without L3 → ok
```

### 7.2 Integration Tests — N:M Suite

```
test_add_tc_to_multiple_suites               → same TC in 2 suites
test_remove_tc_from_suite_keeps_other_links  → remove from A, still in B
test_duplicate_link_returns_409              → unique constraint
test_suite_case_count_via_junction           → count matches links
test_tc_to_dict_includes_suite_ids           → serialization correct
test_backward_compat_suite_id_still_works    → old field still readable
test_generate_from_wricef_creates_links      → auto-link, not suite_id
```

### 7.3 Integration Tests — Scope Coverage

```
test_l3_coverage_includes_process_steps      → standard flow TCs
test_l3_coverage_includes_gap_requirements   → WRICEF unit TCs
test_l3_coverage_includes_interfaces         → integration TCs
test_l3_coverage_readiness_calculation       → pass_rate threshold
test_l3_coverage_missing_tc_shown_as_gap     → gap detection
```

---

## 8. Implementation Order

```
Step 1: TestCaseSuiteLink model + migration
        (no existing code breaks — additive only)

Step 2: scope_resolution.py service
        (new file, no dependencies on existing code)

Step 3: Update create_test_case endpoint
        (add L3 resolution + validation)

Step 4: Update generate_from_wricef / generate_from_process
        (add L3 resolution + junction link creation)

Step 5: Suite API endpoints (N:M management)
        (new endpoints, old ones still work)

Step 6: L3 scope coverage endpoint
        (new endpoint)

Step 7: Backfill script for existing TCs
        (data migration)

Step 8: Frontend updates
        (suite picker → multi-select, coverage view)

Step 9: Deprecation cleanup
        (remove suite_id FK usage from new code paths)
```

Each step is independently deployable and testable. No step breaks existing functionality.

---

## 9. Backward Compatibility

| Component | Old Behavior | New Behavior | Transition |
|-----------|-------------|-------------|------------|
| `TestCase.suite_id` | Direct FK | Deprecated, still readable | Junction is SSOT, suite_id kept for reads |
| `TestSuite.suite_type` | `SIT\|UAT\|...` | `purpose` free text | Both fields available during transition |
| `TestSuite.case_count` | `test_cases.count()` via FK | `case_links.count()` via junction | to_dict uses junction count |
| TC creation without L3 | Allowed | Blocked for unit/sit/uat | Auto-resolve first, fail only if unresolvable |
| `generate_from_wricef` | No L3, direct suite_id | L3 resolved, junction link | Fully backward compatible output |

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Existing TCs with no L3 | L3 validation would block updates | Backfill script + validation only on CREATE (not UPDATE, initially) |
| N:M migration data loss | TCs lose suite assignment | Migration INSERT copies all existing suite_id → junction |
| Performance of junction queries | Slower than direct FK | Indexes on both FKs, lazy="dynamic" for counting |
| Frontend multi-select complexity | Suite picker needs rework | Incremental: keep single-select, add multi-select as enhancement |

---

*ADR-008 — Approved 2026-02-18*
