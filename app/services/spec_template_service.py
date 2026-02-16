"""
FS/TS Template Service — template registry + draft generation.

Transaction policy: methods use flush(), never commit().
Caller (route handler) is responsible for db.session.commit().
"""

import logging
import re
from datetime import datetime, timezone

from app.models import db
from app.models.backlog import (
    BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec, SpecTemplate,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE LOOKUP
# ═══════════════════════════════════════════════════════════════════

def find_active_template(wricef_type: str, spec_kind: str) -> SpecTemplate | None:
    """Find the active template for a given WRICEF type + spec kind (FS/TS).

    Falls back to 'enhancement' type if no exact match found.
    """
    tpl = SpecTemplate.query.filter_by(
        wricef_type=wricef_type.lower(),
        spec_kind=spec_kind.upper(),
        is_active=True,
    ).first()

    # Fallback: use enhancement template as generic default
    if tpl is None and wricef_type.lower() != "enhancement":
        logger.info(f"No template for {wricef_type}/{spec_kind}, falling back to enhancement")
        tpl = SpecTemplate.query.filter_by(
            wricef_type="enhancement",
            spec_kind=spec_kind.upper(),
            is_active=True,
        ).first()

    return tpl


# ═══════════════════════════════════════════════════════════════════
# CONTEXT BUILDER
# ═══════════════════════════════════════════════════════════════════

def build_template_context(item) -> dict:
    """
    Build the variable context dict from a BacklogItem or ConfigItem.

    Gathers data from the item itself + linked requirement + linked process
    for populating {{variable}} placeholders in templates.
    """
    ctx = {
        # ── Item fields
        "code": item.code or "",
        "title": item.title or "",
        "description": item.description or "",
        "module": getattr(item, "module", "") or "",
        "priority": getattr(item, "priority", "medium") or "medium",
        "status": item.status or "new",
        "transaction_code": getattr(item, "transaction_code", "") or "",
        "acceptance_criteria": getattr(item, "acceptance_criteria", "") or "",
        "technical_notes": getattr(item, "technical_notes", "") or "",
        "notes": getattr(item, "notes", "") or "",
        "sub_type": getattr(item, "sub_type", "") or "",
        "assigned_to": getattr(item, "assigned_to", "") or "",
    }

    # ── WRICEF-specific fields
    if isinstance(item, BacklogItem):
        ctx["wricef_type"] = (item.wricef_type or "enhancement").capitalize()
        ctx["wricef_type_full"] = _wricef_type_label(item.wricef_type)
        ctx["package"] = item.package or ""
        ctx["transport_request"] = item.transport_request or ""
        ctx["complexity"] = item.complexity or "medium"
        ctx["estimated_hours"] = str(item.estimated_hours or "—")
        ctx["story_points"] = str(item.story_points or "—")
    elif isinstance(item, ConfigItem):
        ctx["wricef_type"] = "Configuration"
        ctx["wricef_type_full"] = "Configuration Item"
        ctx["config_key"] = item.config_key or ""
        ctx["package"] = ""
        ctx["transport_request"] = getattr(item, "transport_request", "") or ""
        ctx["complexity"] = getattr(item, "complexity", "low") or "low"
        ctx["estimated_hours"] = str(getattr(item, "estimated_hours", None) or "—")
        ctx["story_points"] = "—"

    # ── Linked Requirement (upstream traceability)
    ctx["requirement_code"] = ""
    ctx["requirement_title"] = ""
    ctx["requirement_classification"] = ""

    if getattr(item, "requirement_id", None):
        try:
            from app.models.requirement import Requirement
            req = db.session.get(Requirement, item.requirement_id)
            if req:
                ctx["requirement_code"] = req.code or ""
                ctx["requirement_title"] = req.title or ""
                ctx["requirement_classification"] = getattr(req, "classification", "") or ""
        except Exception:
            pass

    if getattr(item, "explore_requirement_id", None):
        try:
            from app.models.explore import ExploreRequirement
            ereq = db.session.get(ExploreRequirement, item.explore_requirement_id)
            if ereq:
                ctx["requirement_code"] = ctx["requirement_code"] or (ereq.code or "")
                ctx["requirement_title"] = ctx["requirement_title"] or (ereq.title or "")
                ctx["requirement_classification"] = ctx["requirement_classification"] or (
                    getattr(ereq, "fit_gap_status", "") or ""
                )
        except Exception:
            pass

    # ── Linked Process Step (L3/L4 → L2 → L1 path)
    ctx["process_path"] = ""
    ctx["process_step"] = ""

    if getattr(item, "process_id", None):
        try:
            from app.models.scope import Process
            ps = db.session.get(Process, item.process_id)
            if ps:
                ctx["process_step"] = ps.name or ""
                path_parts = [ps.name or ""]
                parent = ps
                while getattr(parent, "parent_id", None):
                    parent = db.session.get(Process, parent.parent_id)
                    if parent:
                        path_parts.append(parent.name or "")
                    else:
                        break
                path_parts.reverse()
                ctx["process_path"] = " → ".join(path_parts)
        except Exception:
            pass

    # ── Today's date for header
    ctx["date_generated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return ctx


def _wricef_type_label(wtype: str) -> str:
    """Map short wricef_type to full label."""
    labels = {
        "workflow": "Workflow (W)",
        "report": "Report (R)",
        "interface": "Interface (I)",
        "conversion": "Conversion (C)",
        "enhancement": "Enhancement (E)",
        "form": "Form (F)",
    }
    return labels.get((wtype or "").lower(), wtype or "")


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE RENDERING
# ═══════════════════════════════════════════════════════════════════

def render_template(template_content: str, context: dict) -> str:
    """
    Replace {{variable}} placeholders with context values.

    Simple Mustache-style rendering. Unknown variables are left as
    {{variable_name}} so the user sees what needs to be filled in.
    """
    def replacer(match):
        key = match.group(1).strip()
        value = context.get(key)
        if value is not None and str(value).strip():
            return str(value)
        # Leave placeholder visible for user to fill
        return "{{" + key + "}}"

    return re.sub(r"\{\{(\s*[\w.]+\s*)\}\}", replacer, template_content)


# ═══════════════════════════════════════════════════════════════════
# GENERATE SPECS (main orchestrator)
# ═══════════════════════════════════════════════════════════════════

def generate_specs_for_backlog_item(item_id: int):
    """
    Generate FS + TS drafts for a BacklogItem using templates matched to its wricef_type.

    Rules:
      - If FS already exists → skip FS generation (do not overwrite)
      - If TS already exists → skip TS generation
      - If no matching template found → return error
      - Created docs get status='draft', template_id + template_version set

    Returns:
        (result_dict, None) on success
        (None, error_dict) on failure
    """
    item = db.session.get(BacklogItem, item_id)
    if not item:
        return None, {"error": f"BacklogItem {item_id} not found", "status": 404}

    wtype = (item.wricef_type or "enhancement").lower()
    context = build_template_context(item)
    result = {"backlog_item_id": item_id, "wricef_type": wtype, "fs": None, "ts": None}

    # ── FS Generation
    if item.functional_spec:
        result["fs"] = {"status": "already_exists", "id": item.functional_spec.id}
    else:
        fs_tpl = find_active_template(wtype, "FS")
        if not fs_tpl:
            return None, {"error": f"No active FS template for type '{wtype}'", "status": 404}

        fs_content = render_template(fs_tpl.content_template, context)
        fs_title = f"FS — {item.code or item.title[:60]}"

        fs = FunctionalSpec(
            backlog_item_id=item_id,
            tenant_id=item.tenant_id,
            title=fs_title,
            description=f"Auto-generated from {fs_tpl.title}",
            content=fs_content,
            version="0.1",
            status="draft",
            template_id=fs_tpl.id,
            template_version=fs_tpl.version,
        )
        db.session.add(fs)
        db.session.flush()
        result["fs"] = {"status": "generated", "id": fs.id, "template": fs_tpl.title}

    # ── TS Generation
    # TS requires an FS parent — use existing or just-created FS
    fs_obj = item.functional_spec  # refreshed after flush
    if not fs_obj:
        # Edge case: should not happen since we just created it
        result["ts"] = {"status": "skipped", "reason": "no_fs_parent"}
    elif fs_obj.technical_spec:
        result["ts"] = {"status": "already_exists", "id": fs_obj.technical_spec.id}
    else:
        ts_tpl = find_active_template(wtype, "TS")
        if not ts_tpl:
            result["ts"] = {"status": "skipped", "reason": "no_template"}
        else:
            ts_content = render_template(ts_tpl.content_template, context)
            ts_title = f"TS — {item.code or item.title[:60]}"

            ts = TechnicalSpec(
                functional_spec_id=fs_obj.id,
                tenant_id=item.tenant_id,
                title=ts_title,
                description=f"Auto-generated from {ts_tpl.title}",
                content=ts_content,
                version="0.1",
                status="draft",
                template_id=ts_tpl.id,
                template_version=ts_tpl.version,
            )
            db.session.add(ts)
            db.session.flush()
            result["ts"] = {"status": "generated", "id": ts.id, "template": ts_tpl.title}

    return result, None


def generate_specs_for_config_item(item_id: int):
    """
    Generate FS + TS drafts for a ConfigItem.
    Config items use the enhancement template set as a fallback.

    Returns:
        (result_dict, None) on success
        (None, error_dict) on failure
    """
    item = db.session.get(ConfigItem, item_id)
    if not item:
        return None, {"error": f"ConfigItem {item_id} not found", "status": 404}

    context = build_template_context(item)
    result = {"config_item_id": item_id, "fs": None, "ts": None}
    wtype = "enhancement"

    if item.functional_spec:
        result["fs"] = {"status": "already_exists", "id": item.functional_spec.id}
    else:
        fs_tpl = find_active_template(wtype, "FS")
        if not fs_tpl:
            return None, {"error": "No active FS template found", "status": 404}

        fs_content = render_template(fs_tpl.content_template, context)
        fs_title = f"FS — {item.code or item.title[:60]}"

        fs = FunctionalSpec(
            config_item_id=item_id,
            tenant_id=item.tenant_id,
            title=fs_title,
            description=f"Auto-generated from {fs_tpl.title}",
            content=fs_content,
            version="0.1",
            status="draft",
            template_id=fs_tpl.id,
            template_version=fs_tpl.version,
        )
        db.session.add(fs)
        db.session.flush()
        result["fs"] = {"status": "generated", "id": fs.id, "template": fs_tpl.title}

    fs_obj = item.functional_spec
    if not fs_obj:
        result["ts"] = {"status": "skipped", "reason": "no_fs_parent"}
    elif fs_obj.technical_spec:
        result["ts"] = {"status": "already_exists", "id": fs_obj.technical_spec.id}
    else:
        ts_tpl = find_active_template(wtype, "TS")
        if not ts_tpl:
            result["ts"] = {"status": "skipped", "reason": "no_template"}
        else:
            ts_content = render_template(ts_tpl.content_template, context)
            ts_title = f"TS — {item.code or item.title[:60]}"

            ts = TechnicalSpec(
                functional_spec_id=fs_obj.id,
                tenant_id=item.tenant_id,
                title=ts_title,
                description=f"Auto-generated from {ts_tpl.title}",
                content=ts_content,
                version="0.1",
                status="draft",
                template_id=ts_tpl.id,
                template_version=ts_tpl.version,
            )
            db.session.add(ts)
            db.session.flush()
            result["ts"] = {"status": "generated", "id": ts.id, "template": ts_tpl.title}

    return result, None


# ═══════════════════════════════════════════════════════════════════
# SEED TEMPLATES
# ═══════════════════════════════════════════════════════════════════

def seed_default_templates():
    """
    Insert or update the 12 default templates (6 WRICEF types × FS + TS).
    Safe to run multiple times — skips existing (wricef_type, spec_kind, version) combos.

    Call this from a Flask CLI command or from init_db.
    """
    templates = _get_default_templates()
    created = 0

    for t in templates:
        exists = SpecTemplate.query.filter_by(
            wricef_type=t["wricef_type"],
            spec_kind=t["spec_kind"],
            version=t["version"],
        ).first()
        if not exists:
            db.session.add(SpecTemplate(**t))
            created += 1

    if created > 0:
        db.session.flush()
        logger.info(f"Seeded {created} spec templates")

    return created


def _get_default_templates() -> list[dict]:
    """Return all 12 default templates with SAP-specific content."""
    return [
        # ════════════════════════════════════════════
        # INTERFACE (I) — FS
        # ════════════════════════════════════════════
        {
            "wricef_type": "interface",
            "spec_kind": "FS",
            "version": "1.0",
            "title": "Interface — FS Template v1.0",
            "is_active": True,
            "content_template": """# Functional Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Priority** | {{priority}} |
| **Date** | {{date_generated}} |
| **Author** | {{assigned_to}} |

---

## 1. Executive Summary

{{description}}

## 2. Traceability

| Link | Reference |
|---|---|
| Requirement | {{requirement_code}} — {{requirement_title}} |
| Process Path | {{process_path}} |
| Classification | {{requirement_classification}} |

## 3. Business Context & Trigger

**Business Purpose:**
_Describe the business need for this interface._

**Trigger / Scheduling:**
- [ ] Real-time (event-driven)
- [ ] Scheduled (batch) — Frequency: ___
- [ ] On-demand (manual trigger)

**Direction:**
- [ ] Inbound (external → SAP)
- [ ] Outbound (SAP → external)
- [ ] Bidirectional

## 4. Source & Target Systems

| Attribute | Source System | Target System |
|---|---|---|
| System Name | | |
| Technology | | |
| Middleware | | |
| Protocol | | |
| Format | | |

## 5. Interface Mapping (Field-Level)

| # | Source Field | Source Type | Target Field | Target Type | Transformation Rule | Mandatory |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

_Add rows as needed._

## 6. Business Validation Rules

| Rule # | Description | Action on Failure |
|---|---|---|
| BV-01 | | |
| BV-02 | | |

## 7. Error Handling (Business)

**Reconciliation Approach:**
_How will data completeness be verified?_

**Business Error Notifications:**
_Who gets notified and how?_

## 8. Volume & Performance Expectations

| Metric | Expected Value |
|---|---|
| Records per run | |
| Frequency | |
| Peak volume | |
| Max acceptable latency | |

## 9. Security & Authorization

_Describe any authorization requirements, RFC users, or communication channels._

## 10. Non-Functional Requirements

_SLA expectations, availability, retry policy, monitoring needs._

## 11. Acceptance Criteria

{{acceptance_criteria}}

## 12. Open Points

| # | Description | Owner | Due Date | Status |
|---|---|---|---|---|
| 1 | | | | Open |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # INTERFACE (I) — TS
        # ════════════════════════════════════════════
        {
            "wricef_type": "interface",
            "spec_kind": "TS",
            "version": "1.0",
            "title": "Interface — TS Template v1.0",
            "is_active": True,
            "content_template": """# Technical Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Priority** | {{priority}} |
| **Date** | {{date_generated}} |

---

## 1. Technical Overview

**Technology Stack:**
_CPI / PI/PO / AIF / RFC / BAPI / IDoc / File / OData / REST_

**Communication Channel:**
_SFTP / HTTP / RFC / SOAP / REST / IDoc / etc._

**Message Protocol:**
_JSON / XML / Flat File / IDoc / CSV_

## 2. Object Inventory

| Object Type | Object Name | Package | Description |
|---|---|---|---|
| CPI iFlow | | | |
| RFC Function Module | | | |
| Custom Table | | | |
| ABAP Class | | | |

## 3. Detailed Design

### 3.1 Message Structure

_Define the message structure (segments, fields, types)._

### 3.2 Field Mapping (Technical)

| # | Source Field | Source Type/Length | Mapping Logic | Target Field | Target Type/Length |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |

### 3.3 Transformation Logic

_XSLT / Groovy / Graphical Mapping details._

### 3.4 Conversion Routines

_Any domain/value mapping, date format conversions, unit conversions._

## 4. Error Handling (Technical)

**Error Detection:**
- Message-level: _validation, schema checks_
- Record-level: _individual record failure handling_

**Error Processing:**
- AIF monitoring: _Yes / No_
- Custom error log table: _table name_
- Alert emails: _recipient(s)_
- Retry strategy: _auto-retry count, interval_
- Dead letter queue: _Yes / No_

**Error Codes:**

| Error Code | Description | Resolution |
|---|---|---|
| ERR-01 | | |
| ERR-02 | | |

## 5. Security & Authorization

| Aspect | Detail |
|---|---|
| RFC User (Technical) | |
| Authorization Object | |
| Communication Arrangement | |
| Certificate/OAuth | |

## 6. Performance & Volume

| Metric | Design Target |
|---|---|
| Max records per message | |
| Parallel processing | |
| Timeout setting | |
| Batch size | |

## 7. Monitoring

**Runtime Monitoring:**
_CPI monitoring / AIF / SXMB_MONI / WE02 / SM58 / SLG1_

**Alerting Setup:**
_Alert rules, thresholds, notification channels._

## 8. Deployment & Transport

| Item | Value |
|---|---|
| Transport Request | {{transport_request}} |
| Package | {{package}} |
| Target System(s) | |
| Deploy Sequence | |
| Activation Steps | |

## 9. Unit Test Plan

| Test # | Scenario | Input | Expected Output | Pass/Fail |
|---|---|---|---|---|
| UT-01 | Happy path | | | |
| UT-02 | Error/invalid data | | | |
| UT-03 | Empty/no data | | | |
| UT-04 | Large volume | | | |

## 10. Open Points

| # | Description | Owner | Due Date | Status |
|---|---|---|---|---|
| 1 | | | | Open |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # REPORT (R) — FS
        # ════════════════════════════════════════════
        {
            "wricef_type": "report",
            "spec_kind": "FS",
            "version": "1.0",
            "title": "Report — FS Template v1.0",
            "is_active": True,
            "content_template": """# Functional Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Priority** | {{priority}} |
| **Date** | {{date_generated}} |
| **Author** | {{assigned_to}} |

---

## 1. Executive Summary

{{description}}

## 2. Traceability

| Link | Reference |
|---|---|
| Requirement | {{requirement_code}} — {{requirement_title}} |
| Process Path | {{process_path}} |

## 3. Report Purpose & Business Context

**Business Need:**
_What question does this report answer?_

**Target Users / Roles:**
_Who will run this report and how often?_

**Frequency:**
- [ ] Daily
- [ ] Weekly
- [ ] Monthly
- [ ] On-demand

## 4. Selection Screen Parameters

| Parameter | Description | Type | Mandatory | Default Value |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## 5. Output Layout

### 5.1 Columns / KPIs

| # | Column Header | Source Table.Field | Aggregation | Format |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

### 5.2 Sorting & Grouping

_Default sort order, subtotals, grouping criteria._

### 5.3 Drilldown Behavior

_What happens when user clicks a line item?_

## 6. Data Sources

| Source | Table / CDS View | Join Condition |
|---|---|---|
| Primary | | |
| Secondary | | |

## 7. Business Rules & Calculations

| Rule # | Description | Formula / Logic |
|---|---|---|
| BR-01 | | |
| BR-02 | | |

## 8. Variants

| Variant Name | Parameters | Purpose |
|---|---|---|
| | | |

## 9. Authorization Requirements

_Authorization objects, org-level checks, data visibility rules._

## 10. Non-Functional Requirements

_Performance expectations (max execution time), volume estimates._

## 11. Acceptance Criteria

{{acceptance_criteria}}

## 12. Open Points

| # | Description | Owner | Due Date | Status |
|---|---|---|---|---|
| 1 | | | | Open |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # REPORT (R) — TS
        # ════════════════════════════════════════════
        {
            "wricef_type": "report",
            "spec_kind": "TS",
            "version": "1.0",
            "title": "Report — TS Template v1.0",
            "is_active": True,
            "content_template": """# Technical Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Date** | {{date_generated}} |

---

## 1. Technical Overview

**Report Technology:**
- [ ] CDS Analytical Query + Fiori Elements
- [ ] ALV Grid Report (classic)
- [ ] SAP Analytics Cloud (SAC)
- [ ] Adobe Form (list report)
- [ ] Other: ___

## 2. Object Inventory

| Object Type | Object Name | Package | Description |
|---|---|---|---|
| CDS View | | | |
| ABAP Report / Class | | | |
| Fiori App | | | |
| Authorization Object | | | |

## 3. Data Model & Query Design

### 3.1 CDS / Data Source

_CDS view definition, base tables, associations._

### 3.2 Selection Logic

_WHERE clauses, filters, aggregations._

### 3.3 Performance Strategy

_Indexes, buffering, pagination, CDS annotations for optimization._

## 4. Authorization Checks

| Auth Object | Field | Check Logic |
|---|---|---|
| | | |

## 5. Error Handling

_No data found handling, timeout handling, large dataset warning._

## 6. Deployment & Transport

| Item | Value |
|---|---|
| Transport Request | {{transport_request}} |
| Package | {{package}} |
| Activation Sequence | |

## 7. Unit Test Plan

| Test # | Scenario | Selection Params | Expected Rows | Pass/Fail |
|---|---|---|---|---|
| UT-01 | Happy path | | | |
| UT-02 | No data | | | |
| UT-03 | Large volume | | | |
| UT-04 | Auth restriction | | | |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # ENHANCEMENT (E) — FS
        # ════════════════════════════════════════════
        {
            "wricef_type": "enhancement",
            "spec_kind": "FS",
            "version": "1.0",
            "title": "Enhancement — FS Template v1.0",
            "is_active": True,
            "content_template": """# Functional Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Priority** | {{priority}} |
| **Date** | {{date_generated}} |
| **Author** | {{assigned_to}} |

---

## 1. Executive Summary

{{description}}

## 2. Traceability

| Link | Reference |
|---|---|
| Requirement | {{requirement_code}} — {{requirement_title}} |
| Process Path | {{process_path}} |

## 3. Current Behavior (As-Is)

_Describe the standard SAP behavior being enhanced._

**Transaction:** {{transaction_code}}

## 4. Desired Behavior (To-Be)

_Describe what should change and under what conditions._

## 5. Business Rules

| Rule # | Condition | Action | Exception |
|---|---|---|---|
| BR-01 | | | |
| BR-02 | | | |

## 6. Affected Processes & Impact

_Which processes are affected? What is the regression risk?_

## 7. User Interface Changes

_Any screen changes, additional fields, messages, or popups?_

## 8. Error Handling (Business)

| Error Scenario | Message Text | Severity |
|---|---|---|
| | | Error / Warning / Info |

## 9. Authorization Requirements

_Any new or changed authorization checks?_

## 10. Non-Functional Requirements

_Performance impact, volume considerations._

## 11. Acceptance Criteria

{{acceptance_criteria}}

## 12. Open Points

| # | Description | Owner | Due Date | Status |
|---|---|---|---|---|
| 1 | | | | Open |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # ENHANCEMENT (E) — TS
        # ════════════════════════════════════════════
        {
            "wricef_type": "enhancement",
            "spec_kind": "TS",
            "version": "1.0",
            "title": "Enhancement — TS Template v1.0",
            "is_active": True,
            "content_template": """# Technical Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Date** | {{date_generated}} |

---

## 1. Technical Overview

**Enhancement Technique:**
- [ ] BAdI (New)
- [ ] BAdI (Classic)
- [ ] User Exit
- [ ] Enhancement Spot / Section
- [ ] BRFplus Rule
- [ ] Custom Code (new program)
- [ ] Other: ___

**Enhancement Point:**
_BAdI name, User Exit name, or Enhancement Spot._

## 2. Object Inventory

| Object Type | Object Name | Package | Description |
|---|---|---|---|
| BAdI Implementation | | | |
| ABAP Class | | | |
| Function Module | | | |
| Custom Table | | | |
| Data Element | | | |
| Domain | | | |

## 3. Detailed Design

### 3.1 Enhancement Point Details

_BAdI/Exit interface, importing/exporting parameters._

### 3.2 Pseudo-Code / Logic

```abap
* Enhancement logic
IF <condition>.
  " Business rule implementation
ENDIF.
```

### 3.3 Custom Tables / Structures

_Any new Z-tables or structures required._

## 4. Error Handling (Technical)

| Error Code | Message Class | Number | Text | Type |
|---|---|---|---|---|
| | | | | E / W / I |

## 5. Regression Risk Assessment

| Risk | Affected Area | Mitigation |
|---|---|---|
| | | |

## 6. Deployment & Transport

| Item | Value |
|---|---|
| Transport Request | {{transport_request}} |
| Package | {{package}} |
| Activation Sequence | |

## 7. Unit Test Plan

| Test # | Scenario | Pre-condition | Steps | Expected Result | Pass/Fail |
|---|---|---|---|---|---|
| UT-01 | Happy path | | | | |
| UT-02 | Edge case | | | | |
| UT-03 | Negative test | | | | |
| UT-04 | Regression | | | | |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # CONVERSION (C) — FS
        # ════════════════════════════════════════════
        {
            "wricef_type": "conversion",
            "spec_kind": "FS",
            "version": "1.0",
            "title": "Conversion — FS Template v1.0",
            "is_active": True,
            "content_template": """# Functional Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Priority** | {{priority}} |
| **Date** | {{date_generated}} |
| **Author** | {{assigned_to}} |

---

## 1. Executive Summary

{{description}}

## 2. Traceability

| Link | Reference |
|---|---|
| Requirement | {{requirement_code}} — {{requirement_title}} |
| Process Path | {{process_path}} |

## 3. Migration Scope

**Data Object:**
_Master data / Transactional data / Configuration / Historical_

**Source System:**
_Legacy system name and version_

**Volume Estimates:**

| Object | Estimated Records | Notes |
|---|---|---|
| | | |

## 4. Legacy → S/4HANA Field Mapping

| # | Legacy Field | Legacy Format | S/4HANA Field | S/4 Format | Transformation Rule | Default |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |

## 5. Business Validation Rules

| Rule # | Description | Action on Failure |
|---|---|---|
| BV-01 | Mandatory field check | Reject record |
| BV-02 | | |

## 6. Data Cleansing Requirements

_What data cleansing must happen before or during migration?_

## 7. Reconciliation Strategy

**Reconciliation Approach:**

| Check | Source Count | Target Count | Delta Tolerance |
|---|---|---|---|
| Record count | | | |
| Key value totals | | | |

## 8. Cutover Dependencies

_Sequence constraints, prerequisites, freeze periods._

## 9. Acceptance Criteria

{{acceptance_criteria}}

## 10. Open Points

| # | Description | Owner | Due Date | Status |
|---|---|---|---|---|
| 1 | | | | Open |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # CONVERSION (C) — TS
        # ════════════════════════════════════════════
        {
            "wricef_type": "conversion",
            "spec_kind": "TS",
            "version": "1.0",
            "title": "Conversion — TS Template v1.0",
            "is_active": True,
            "content_template": """# Technical Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Date** | {{date_generated}} |

---

## 1. Technical Overview

**Migration Tooling:**
- [ ] LTMC (Legacy Transfer Migration Cockpit)
- [ ] SAP Data Services
- [ ] LSMW
- [ ] Custom ABAP Program
- [ ] S/4HANA Migration Cockpit — Staging Tables
- [ ] Other: ___

## 2. Object Inventory

| Object Type | Object Name | Package | Description |
|---|---|---|---|
| Migration Object | | | |
| Staging Table | | | |
| ABAP Program | | | |
| Mapping Table | | | |

## 3. Detailed Design

### 3.1 Extract Logic

_How data is extracted from source system._

### 3.2 Transform Logic

_Transformation rules, value mapping, derivation logic._

### 3.3 Load Logic

_Load method (direct insert / BAPI / IDoc / staging), batch size, error handling._

### 3.4 Restartability

_How to restart after failure — checkpoint logic, resume from last successful record._

## 4. Error Handling & Logging

| Error Type | Handling | Log Location |
|---|---|---|
| Validation failure | | |
| Duplicate record | | |
| Reference data missing | | |
| System error | | |

**Error Log Table:**
_Z-table or SLG1 object for error tracking._

## 5. Performance & Batch Strategy

| Parameter | Value |
|---|---|
| Batch size (records per commit) | |
| Parallel threads | |
| Estimated runtime per 1000 records | |
| Total estimated runtime | |

## 6. Deployment & Transport

| Item | Value |
|---|---|
| Transport Request | {{transport_request}} |
| Package | {{package}} |
| Dry Run Environment | |
| Mock Run Date | |

## 7. Unit Test Plan

| Test # | Scenario | Records | Expected Result | Pass/Fail |
|---|---|---|---|---|
| UT-01 | Small set (10 records) | | | |
| UT-02 | Validation failures | | | |
| UT-03 | Duplicate handling | | | |
| UT-04 | Large volume | | | |
| UT-05 | Restart after failure | | | |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # WORKFLOW (W) — FS
        # ════════════════════════════════════════════
        {
            "wricef_type": "workflow",
            "spec_kind": "FS",
            "version": "1.0",
            "title": "Workflow — FS Template v1.0",
            "is_active": True,
            "content_template": """# Functional Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Priority** | {{priority}} |
| **Date** | {{date_generated}} |
| **Author** | {{assigned_to}} |

---

## 1. Executive Summary

{{description}}

## 2. Traceability

| Link | Reference |
|---|---|
| Requirement | {{requirement_code}} — {{requirement_title}} |
| Process Path | {{process_path}} |

## 3. Workflow Trigger

**Triggering Event:**
_What business event starts this workflow?_

**Trigger Object:**
_Document type, transaction, or event._

## 4. Approval Steps

| Step # | Approver Role | Condition | Action on Approve | Action on Reject | SLA |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

## 5. Escalation Rules

| Rule | Condition | Action |
|---|---|---|
| Timeout | No action in ___ hours | Escalate to ___ |
| Delegation | Approver absent | Forward to ___ |

## 6. Notification Requirements

| Event | Recipient | Channel | Template |
|---|---|---|---|
| New item | Approver | Email + Fiori | |
| Approved | Requester | Email | |
| Rejected | Requester | Email | |

## 7. Business Rules

| Rule # | Condition | Action |
|---|---|---|
| BR-01 | | |

## 8. Acceptance Criteria

{{acceptance_criteria}}

## 9. Open Points

| # | Description | Owner | Due Date | Status |
|---|---|---|---|---|
| 1 | | | | Open |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # WORKFLOW (W) — TS
        # ════════════════════════════════════════════
        {
            "wricef_type": "workflow",
            "spec_kind": "TS",
            "version": "1.0",
            "title": "Workflow — TS Template v1.0",
            "is_active": True,
            "content_template": """# Technical Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Date** | {{date_generated}} |

---

## 1. Technical Overview

**Workflow Technology:**
- [ ] SAP Flexible Workflow
- [ ] SAP Business Workflow (WS prefix)
- [ ] BRFplus + Workflow
- [ ] SAP BPA (Build Process Automation)
- [ ] Custom ABAP
- [ ] Other: ___

## 2. Object Inventory

| Object Type | Object Name | Description |
|---|---|---|
| Workflow Template | | |
| Task (TS) | | |
| BOR Object | | |
| BRFplus Application | | |
| ABAP Class | | |

## 3. Detailed Design

### 3.1 Workflow Definition

_Step-by-step workflow structure with decision points._

### 3.2 Agent Determination

| Step | Agent Rule | Rule Type | Details |
|---|---|---|---|
| | | Org unit / Role / Expression | |

### 3.3 BRFplus Rules (if applicable)

_Decision table, formula, or rule logic._

### 3.4 Fiori Inbox Integration

_My Inbox app configuration, custom task UI, approve/reject actions._

## 4. Error Handling

_Workflow error handling, orphaned work items, restart strategy._

## 5. Deployment & Transport

| Item | Value |
|---|---|
| Transport Request | {{transport_request}} |
| Workflow activation | SWDD / SWU3 |
| Event linkage | SWE2 |

## 6. Unit Test Plan

| Test # | Scenario | Steps | Expected Result | Pass/Fail |
|---|---|---|---|---|
| UT-01 | Normal approval | | | |
| UT-02 | Rejection flow | | | |
| UT-03 | Timeout escalation | | | |
| UT-04 | Delegation | | | |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # FORM (F) — FS
        # ════════════════════════════════════════════
        {
            "wricef_type": "form",
            "spec_kind": "FS",
            "version": "1.0",
            "title": "Form — FS Template v1.0",
            "is_active": True,
            "content_template": """# Functional Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Priority** | {{priority}} |
| **Date** | {{date_generated}} |
| **Author** | {{assigned_to}} |

---

## 1. Executive Summary

{{description}}

## 2. Traceability

| Link | Reference |
|---|---|
| Requirement | {{requirement_code}} — {{requirement_title}} |
| Process Path | {{process_path}} |

## 3. Form Purpose & Usage

**Form Type:**
- [ ] Invoice / Billing document
- [ ] Purchase Order
- [ ] Delivery Note
- [ ] Payment Advice
- [ ] Label / Barcode
- [ ] Other: ___

**Trigger Transaction:** {{transaction_code}}

**Output Channel:**
- [ ] Print
- [ ] Email (PDF attachment)
- [ ] EDI
- [ ] Fax

## 4. Layout Requirements

### 4.1 Page Structure

| Section | Content |
|---|---|
| Header | Company logo, address, document number, date |
| Body | Line items table |
| Footer | Totals, signatures, legal text |

### 4.2 Language Requirements

| Language | Required |
|---|---|
| EN | [ ] |
| TR | [ ] |
| DE | [ ] |
| Other | |

### 4.3 Paper Size & Orientation

_A4 / Letter / Custom — Portrait / Landscape_

## 5. Data Fields

| # | Field | Source Table.Field | Format | Notes |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

## 6. Print Conditions / Output Determination

| Condition | Output Type | Medium | Timing |
|---|---|---|---|
| | | Print / Email / Fax | Immediate / Batch |

## 7. Acceptance Criteria

{{acceptance_criteria}}

## 8. Open Points

| # | Description | Owner | Due Date | Status |
|---|---|---|---|---|
| 1 | | | | Open |

---
*Generated from template — review and complete all sections.*
""",
        },

        # ════════════════════════════════════════════
        # FORM (F) — TS
        # ════════════════════════════════════════════
        {
            "wricef_type": "form",
            "spec_kind": "TS",
            "version": "1.0",
            "title": "Form — TS Template v1.0",
            "is_active": True,
            "content_template": """# Technical Specification
## {{code}} — {{title}}

| Field | Value |
|---|---|
| **Type** | {{wricef_type_full}} |
| **Module** | {{module}} |
| **Date** | {{date_generated}} |

---

## 1. Technical Overview

**Form Technology:**
- [ ] Adobe Forms (Interactive)
- [ ] Adobe Forms (Print)
- [ ] SmartForms
- [ ] SAPscript
- [ ] RAP-based Output Management
- [ ] Other: ___

## 2. Object Inventory

| Object Type | Object Name | Package | Description |
|---|---|---|---|
| Form Template | | | |
| Form Interface | | | |
| Print Program | | | |
| Output Type (NACE) | | | |
| Custom Table | | | |

## 3. Detailed Design

### 3.1 Form Interface

_Import / export parameters, global definitions._

### 3.2 Form Layout

_Windows, pages, text elements, graphic elements._

### 3.3 Data Binding

| Form Field | Interface Parameter | Formatting |
|---|---|---|
| | | |

### 3.4 Spool & Output Configuration

_Spool parameters, device type, output configuration._

## 4. Error Handling

_Missing data handling, spool errors, email bounce handling._

## 5. Deployment & Transport

| Item | Value |
|---|---|
| Transport Request | {{transport_request}} |
| Package | {{package}} |
| NACE Configuration | |

## 6. Unit Test Plan

| Test # | Scenario | Expected Output | Pass/Fail |
|---|---|---|---|
| UT-01 | Print preview | | |
| UT-02 | Email output | | |
| UT-03 | Multi-language | | |
| UT-04 | Edge case (empty lines) | | |

---
*Generated from template — review and complete all sections.*
""",
        },
    ]
