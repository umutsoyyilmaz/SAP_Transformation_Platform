# SAP Signavio & BPMN 2.0 Integration — Design Draft

> **Status:** 🟡 PARKED — Awaiting design approval before implementation  
> **Created:** 2026-02-09  
> **Version:** Draft v0.1  
> **Related Commit:** `579576f` (current HEAD at time of analysis)  
> **Platform Version:** v1.2 (436 tests, 35 tables, ~186 endpoints)

---

## 1. Objective

Build a Signavio-compatible scenario/process/scope item/analysis structure that enables:

1. **Native Signavio import** — Parse BPMN 2.0 XML exports from SAP Signavio
2. **SAP documentation-compatible exports** — Produce outputs aligned with SAP deliverable formats
3. **SAP Activate alignment** — Map scope items to Activate methodology phases
4. **BPMN 2.0 global traceability** — Full element-level traceability from diagram to requirement

---

## 2. Analysis Summary

### 2.1 SAP Signavio Architecture (4-Layer)

| Layer | Signavio Concept | Description |
|-------|-----------------|-------------|
| L0 | **Process House / Navigation Map** | Top-level categorization (Value Chain) |
| L1 | **Process Group** | End-to-end scenarios (e.g., Order-to-Cash) |
| L2 | **Process** | BPMN 2.0 diagrams with pools, lanes, tasks |
| L3 | **Process Step / Activity** | Individual BPMN tasks, events, gateways |

### 2.2 Current Platform Hierarchy (v1.2)

| Layer | Platform Entity | Notes |
|-------|----------------|-------|
| L1 | **Scenario** | End-to-end scenario |
| L2 | **Process (level=L2)** | Business process group |
| L3 | **Process (level=L3)** | Process step — scope fields absorbed from old ScopeItem |
| — | *ScopeItem removed* | Was absorbed into L3 in hierarchy refactoring (commit `5428088`) |

### 2.3 Gap Analysis

| Gap | Current State | Required State |
|-----|--------------|----------------|
| **ScopeItem** | Absorbed into L3 Process | Needs to be a separate entity for SAP Best Practice mapping |
| **BPMN metadata** | None | L3 needs `bpmn_element_id`, `bpmn_element_type`, `bpmn_lane` |
| **Signavio linking** | None | L2/Scenario need `signavio_model_id`, `signavio_revision` |
| **BPMN XML storage** | None | L2 needs `bpmn_xml` blob for round-trip fidelity |
| **SAP Activate phase** | None | ScopeItem needs `activate_phase` field |
| **Scope ↔ L3 cardinality** | 1:1 (embedded) | N:M needed (one scope item can map to multiple L3 steps) |
| **Requirement ↔ Scope** | Via L3 only | Direct N:M `Requirement ↔ ScopeItem` mapping needed |

---

## 3. Proposed Target Design (v2.0)

### 3.1 Entity Relationship Diagram

```
Program
  └── Scenario (L1)
        ├── signavio_model_id          ← NEW
        ├── Workshop → Requirement
        │                └── OpenItem
        └── Process L2
              ├── bpmn_xml             ← NEW (BPMN 2.0 XML blob)
              ├── signavio_model_id    ← NEW
              ├── signavio_revision    ← NEW
              ├── Analysis
              └── Process L3
                    ├── bpmn_element_id    ← NEW
                    ├── bpmn_element_type  ← NEW (task/event/gateway/subprocess)
                    ├── bpmn_lane          ← NEW
                    ├── Analysis
                    └──── ScopeItemProcessMapping (N:M) ──── ScopeItem ← RESTORED
                                                                ├── code (e.g., "4FS")
                                                                ├── sap_bp_id
                                                                ├── scope_decision
                                                                ├── fit_gap
                                                                ├── activate_phase ← NEW
                                                                ├── module
                                                                ├── priority
                                                                └── Analysis
                                                                
Requirement ──── RequirementScopeMapping (N:M) ──── ScopeItem   ← NEW junction
Requirement ──── RequirementProcessMapping (N:M) ──── Process L3  (existing)
```

### 3.2 New & Modified Tables

| # | Table | Type | Description |
|---|-------|------|-------------|
| 1 | `scope_item` | **NEW** | Restored as separate entity — SAP Best Practice ref, scope decision, fit-gap, activate_phase |
| 2 | `scope_item_process_mapping` | **NEW** | N:M junction: ScopeItem ↔ Process L3 |
| 3 | `requirement_scope_mapping` | **NEW** | N:M junction: Requirement ↔ ScopeItem |
| 4 | `process` (L3 fields) | **MODIFY** | Remove: `scope_decision`, `fit_gap`, `sap_reference`, `priority` → moved to ScopeItem |
| 5 | `process` (L3 BPMN) | **MODIFY** | Add: `bpmn_element_id`, `bpmn_element_type`, `bpmn_lane` |
| 6 | `process` (L2 BPMN) | **MODIFY** | Add: `bpmn_xml`, `signavio_model_id`, `signavio_revision` |
| 7 | `scenario` | **MODIFY** | Add: `signavio_model_id` |
| 8 | `analysis` | **MODIFY** | Add: `scope_item_id` FK (nullable, dual-target: L3 or ScopeItem) |

### 3.3 New Services

| Service | Purpose |
|---------|---------|
| `BpmnImportService` | Parse Signavio BPMN 2.0 XML → auto-create L2/L3/ScopeItem hierarchy |
| `BpmnExportService` | Platform data → BPMN 2.0 XML output |
| `SignavioSyncService` (future) | REST API integration with Signavio for live sync |

### 3.4 New API Endpoints (~15)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/scope-items` | List all scope items (with filters) |
| POST | `/scope-items` | Create scope item |
| GET | `/scope-items/<id>` | Get scope item detail |
| PUT | `/scope-items/<id>` | Update scope item |
| DELETE | `/scope-items/<id>` | Delete scope item |
| POST | `/scope-items/<id>/map-process` | Link scope item to L3 process |
| DELETE | `/scope-item-process-mappings/<id>` | Remove scope-process link |
| POST | `/requirements/<id>/map-scope-item` | Link requirement to scope item |
| DELETE | `/requirement-scope-mappings/<id>` | Remove requirement-scope link |
| POST | `/processes/<id>/import-bpmn` | Upload BPMN XML → parse into L3s |
| GET | `/processes/<id>/export-bpmn` | Export process as BPMN 2.0 XML |
| GET | `/scenarios/<id>/export-bpmn` | Export full scenario as BPMN |
| POST | `/scenarios/<id>/import-signavio` | Import from Signavio export package |
| GET | `/scope-items/<id>/analysis` | Get analyses linked to scope item |
| POST | `/scope-items/<id>/analysis` | Create analysis for scope item |

---

## 4. Design Decision Points (Awaiting Approval)

### Decision 1: ScopeItem as Separate Table

| Option | Description | Recommendation |
|--------|-------------|----------------|
| **A** ⭐ | Restore ScopeItem as independent entity | **Recommended** — SAP Best Practice scope items have their own lifecycle |
| B | Keep scope fields embedded in L3 | Not Signavio-compatible |

**Rationale:** SAP Best Practice scope items (e.g., "4FS — Scope Item Fit/Gap Analysis") are independent deliverables that may span multiple process steps. They need their own status tracking, SAP BP ID reference, and Activate phase mapping.

---

### Decision 2: BPMN Metadata Scope

| Option | Description | Recommendation |
|--------|-------------|----------------|
| A | Minimal — only `bpmn_element_id` | Insufficient for round-trip |
| **B+C** ⭐ | Rich metadata + XML blob | **Recommended** — enables both element-level tracing AND full diagram round-trip |
| D | Full BPMN object model in DB | Over-engineered for our needs |

**Fields for B+C hybrid:**
- L3: `bpmn_element_id` (str), `bpmn_element_type` (enum: task/event/gateway/subprocess), `bpmn_lane` (str)
- L2: `bpmn_xml` (text blob), `signavio_model_id` (str), `signavio_revision` (str)

---

### Decision 3: ScopeItem ↔ L3 Relationship

| Option | Description | Recommendation |
|--------|-------------|----------------|
| **A** ⭐ | N:M via junction table | **Recommended** — one scope item can cover multiple L3 steps |
| B | 1:N (ScopeItem has L3 FK) | Limits flexibility |
| C | 1:1 (ScopeItem is child of L3) | Same as current absorbed model |

**Rationale:** In SAP projects, a scope item like "Order Management" might touch multiple process steps across different L2 processes. N:M is the only relationship that models this correctly.

---

### Decision 4: Signavio Import Strategy

| Option | Description | Recommendation |
|--------|-------------|----------------|
| A | REST API integration only | Requires Signavio API access, complex auth |
| B | BPMN XML file upload only | Limited to export files |
| **C** ⭐ | XML file upload now + API connector later | **Recommended** — pragmatic phased approach |

**Phase 1:** BPMN 2.0 XML file upload parser  
**Phase 2:** Signavio REST API connector (future)

---

### Decision 5: SAP Activate Alignment

| Option | Description | Recommendation |
|--------|-------------|----------------|
| **A** ⭐ | `activate_phase` field on ScopeItem | **Recommended** — simple, maps directly to SAP Activate phases |
| B | Separate ActivatePhase entity | Over-engineered unless tracking phase transitions |

**activate_phase values:** `Discover`, `Prepare`, `Explore`, `Realize`, `Deploy`, `Run`

---

## 5. BPMN 2.0 Element Type Reference

For the `bpmn_element_type` enum on L3 processes:

| BPMN Type | XML Element | Platform Mapping |
|-----------|-------------|------------------|
| User Task | `<bpmn:userTask>` | Manual activity |
| Service Task | `<bpmn:serviceTask>` | Automated/integration step |
| Script Task | `<bpmn:scriptTask>` | System calculation |
| Start Event | `<bpmn:startEvent>` | Process trigger |
| End Event | `<bpmn:endEvent>` | Process completion |
| Exclusive Gateway | `<bpmn:exclusiveGateway>` | Decision point |
| Parallel Gateway | `<bpmn:parallelGateway>` | Parallel split/join |
| Intermediate Event | `<bpmn:intermediateCatchEvent>` | Wait/message point |
| Sub-Process | `<bpmn:subProcess>` | Embedded sub-process |
| Call Activity | `<bpmn:callActivity>` | Reusable sub-process reference |

---

## 6. Implementation Plan (Estimated)

Once design is approved, implementation follows this order:

| Step | Task | Estimated Effort |
|------|------|-----------------|
| 1 | Update `scope.py` models (ScopeItem, junctions, BPMN fields) | ~2 hours |
| 2 | Create Alembic migration | ~30 min |
| 3 | Update `scope_bp.py` (ScopeItem CRUD + mapping endpoints) | ~2 hours |
| 4 | Update `scenario_bp.py` & `requirement_bp.py` (new mappings) | ~1 hour |
| 5 | Create `BpmnImportService` (XML parser) | ~3 hours |
| 6 | Create BPMN export endpoint | ~2 hours |
| 7 | Update all tests + add new tests (~30-40 new) | ~3 hours |
| 8 | Update UI views (scope item list, BPMN import dialog) | ~2 hours |
| 9 | Run full test suite, fix regressions, commit | ~1 hour |
| **Total** | | **~16 hours** |

---

## 7. Signavio BPMN XML Import — Technical Notes

### 7.1 XML Structure (Signavio Export)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:signavio="http://www.signavio.com"
                  id="Definitions_1">
  <bpmn:process id="Process_1" name="Order-to-Cash">
    <bpmn:laneSet>
      <bpmn:lane id="Lane_1" name="Sales Department">
        <bpmn:flowNodeRef>Task_1</bpmn:flowNodeRef>
      </bpmn:lane>
    </bpmn:laneSet>
    <bpmn:startEvent id="Start_1" name="Order Received"/>
    <bpmn:userTask id="Task_1" name="Validate Order">
      <bpmn:extensionElements>
        <signavio:signavioMetaData metaKey="bgcolor" metaValue="#FFFFFF"/>
      </bpmn:extensionElements>
    </bpmn:userTask>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_1"/>
  </bpmn:process>
</bpmn:definitions>
```

### 7.2 Import Mapping Logic

```
BPMN <process>        → Platform Process L2
BPMN <lane>           → L3.bpmn_lane  
BPMN <*Task>          → Platform Process L3 (bpmn_element_type=task)
BPMN <*Event>         → Platform Process L3 (bpmn_element_type=event)
BPMN <*Gateway>       → Platform Process L3 (bpmn_element_type=gateway)
BPMN <subProcess>     → Platform Process L3 (bpmn_element_type=subprocess)
BPMN <callActivity>   → Platform Process L3 (bpmn_element_type=call_activity)
Signavio extensions   → Stored in bpmn_xml blob for round-trip
```

---

## 8. References

- **SAP Signavio Process Manager:** https://www.signavio.com/products/process-manager/
- **BPMN 2.0 Specification (OMG):** https://www.omg.org/spec/BPMN/2.0.2/
- **SAP Activate Methodology:** https://support.sap.com/en/offerings-programs/methodology.html
- **Signavio BPMN Guide:** https://www.signavio.com/post/bpmn-introductory-guide/
- **SAP Best Practices Explorer:** https://rapid.sap.com/bp/

---

*This document is a design draft. No code changes have been made. Implementation will begin only after explicit approval of the 5 design decisions above.*
