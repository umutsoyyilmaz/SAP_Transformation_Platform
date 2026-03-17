"""
FS/TS Template Service — template registry + draft generation.

Transaction policy: methods use flush(), never commit().
Caller (route handler) is responsible for db.session.commit().
"""

import logging
import re
from datetime import datetime, timezone
from textwrap import dedent

from app.models import db
from app.models.backlog import (
    BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec, SpecTemplate,
)
from app.services.helpers.scoped_queries import get_scoped_or_none

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# TEMPLATE LOOKUP
# ═══════════════════════════════════════════════════════════════════

def _ensure_default_templates_available() -> None:
    """Seed defaults on demand when the current database has no active templates."""
    try:
        has_active_templates = SpecTemplate.query.filter_by(is_active=True).first() is not None
    except Exception:
        logger.debug("Spec template availability check failed", exc_info=True)
        return

    if has_active_templates:
        return

    created = seed_default_templates()
    if created > 0:
        db.session.flush()
        logger.info("Seeded %s default spec templates on demand", created)

def find_active_template(wricef_type: str, spec_kind: str) -> SpecTemplate | None:
    """Find the active template for a given WRICEF type + spec kind (FS/TS).

    Falls back to 'enhancement' type if no exact match found.
    """
    _ensure_default_templates_available()

    tpl = SpecTemplate.query.filter_by(
        wricef_type=wricef_type.lower(),
        spec_kind=spec_kind.upper(),
        is_active=True,
    ).order_by(SpecTemplate.id.desc()).first()

    # Fallback: use enhancement template as generic default
    if tpl is None and wricef_type.lower() != "enhancement":
        logger.info(f"No template for {wricef_type}/{spec_kind}, falling back to enhancement")
        tpl = SpecTemplate.query.filter_by(
            wricef_type="enhancement",
            spec_kind=spec_kind.upper(),
            is_active=True,
        ).order_by(SpecTemplate.id.desc()).first()

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
            logger.debug("Optional requirement context enrichment failed", exc_info=True)

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
            logger.debug("Optional explore requirement context enrichment failed", exc_info=True)

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
            logger.debug("Optional process path context enrichment failed", exc_info=True)

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

def generate_specs_for_backlog_item(item_id: int, *, program_id: int | None = None):
    """
    Generate FS + TS drafts for a BacklogItem using templates matched to its wricef_type.

    Rules:
      - If FS already exists → skip FS generation (do not overwrite)
      - If TS already exists → skip TS generation
      - If no matching template found → return error
      - Created docs get status='draft', template_id + template_version set

    Args:
        item_id: BacklogItem primary key (user-supplied).
        program_id: Program scope — scopes the BacklogItem lookup when provided.
            Callers should always pass this to enforce tenant isolation.

    Returns:
        (result_dict, None) on success
        (None, error_dict) on failure
    """
    item = (
        get_scoped_or_none(BacklogItem, item_id, program_id=program_id)
        if program_id is not None
        else db.session.get(BacklogItem, item_id)
    )
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


def generate_specs_for_config_item(item_id: int, *, program_id: int | None = None):
    """
    Generate FS + TS drafts for a ConfigItem.
    Config items use the enhancement template set as a fallback.

    Args:
        item_id: ConfigItem primary key (user-supplied).
        program_id: Program scope — scopes the ConfigItem lookup when provided.
            Callers should always pass this to enforce tenant isolation.

    Returns:
        (result_dict, None) on success
        (None, error_dict) on failure
    """
    item = (
        get_scoped_or_none(ConfigItem, item_id, program_id=program_id)
        if program_id is not None
        else db.session.get(ConfigItem, item_id)
    )
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


DEFAULT_TEMPLATE_VERSION = "2.0"


def _render_numbered_sections(sections: list[tuple[str, str]]) -> str:
    """Render numbered markdown sections from ordered tuples."""
    rendered: list[str] = []
    for index, (title, body) in enumerate(sections, start=1):
        rendered.append(f"## {index}. {title}\n\n{dedent(body).strip()}")
    rendered.append("---\n*Generated from default SAP-aligned template — complete every section before review or sign-off.*")
    return "\n\n".join(rendered)


def _fs_header() -> str:
    return dedent(
        """\
        # Functional Specification
        ## {{code}} — {{title}}

        | Field | Value |
        |---|---|
        | **Type** | {{wricef_type_full}} |
        | **Module** | {{module}} |
        | **Priority** | {{priority}} |
        | **Date** | {{date_generated}} |
        | **Author** | {{assigned_to}} |
        """
    ).strip()


def _ts_header() -> str:
    return dedent(
        """\
        # Technical Specification
        ## {{code}} — {{title}}

        | Field | Value |
        |---|---|
        | **Type** | {{wricef_type_full}} |
        | **Module** | {{module}} |
        | **Priority** | {{priority}} |
        | **Date** | {{date_generated}} |
        """
    ).strip()


def _common_fs_sections() -> list[tuple[str, str]]:
    return [
        (
            "Document Control",
            """
            | Item | Value |
            |---|---|
            | Document ID | {{code}} |
            | Version | """ + DEFAULT_TEMPLATE_VERSION + """ |
            | Status | Draft |
            | Functional Owner | {{assigned_to}} |
            | Reviewer | |
            | Planned Approval Date | |
            """,
        ),
        (
            "Business Context & Scope",
            """
            **Business Purpose:**
            {{description}}

            **In Scope:**
            - Business process step(s) covered by this specification
            - Required user roles and organizational units
            - Required master data, transactional triggers, and reporting outputs

            **Out of Scope:**
            - Legacy workaround retirement tasks not required for this design
            - Non-approved process deviations or local variants without sign-off
            """,
        ),
        (
            "Traceability & Upstream References",
            """
            | Reference | Value |
            |---|---|
            | Requirement | {{requirement_code}} — {{requirement_title}} |
            | Classification | {{requirement_classification}} |
            | Process Path | {{process_path}} |
            | SAP Transaction / App | {{transaction_code}} |
            | Related Notes | {{notes}} |
            """,
        ),
        (
            "Assumptions & Dependencies",
            """
            | Type | Description | Owner | Status |
            |---|---|---|---|
            | Assumption | | | Open |
            | Dependency | | | Open |
            | Upstream Decision | | | Open |
            """,
        ),
    ]


def _common_fs_tail_sections() -> list[tuple[str, str]]:
    return [
        (
            "Security & Authorization",
            """
            | Topic | Detail |
            |---|---|
            | Business Role(s) | |
            | SAP Authorization Objects | |
            | Sensitive Data / Compliance Notes | |
            | Audit / Logging Requirement | |
            """,
        ),
        (
            "Non-Functional Requirements",
            """
            | Requirement | Target |
            |---|---|
            | Performance / Response Time | |
            | Volume / Throughput | |
            | Availability Window | |
            | Support / Monitoring Expectation | |
            """,
        ),
        (
            "Test Scenarios & Acceptance Coverage",
            """
            _Capture representative business scenarios that will later drive SIT, UAT, or unit-test derivation._

            1. _Happy path — expected business outcome_
            2. _Negative / validation scenario — expected control behavior_
            3. _Exception or high-volume scenario — expected business outcome_

            **Acceptance Criteria:**
            {{acceptance_criteria}}
            """,
        ),
        (
            "Open Points & Risks",
            """
            | # | Description | Owner | Due Date | Type | Status |
            |---|---|---|---|---|---|
            | 1 | | | | Open Point / Risk | Open |
            """,
        ),
        (
            "Review & Sign-Off",
            """
            | Role | Name | Date | Decision |
            |---|---|---|---|
            | Functional Consultant | | | |
            | Business Process Owner | | | |
            | Solution Architect / Lead | | | |
            """,
        ),
    ]


def _common_ts_sections() -> list[tuple[str, str]]:
    return [
        (
            "Technical Document Control",
            """
            | Item | Value |
            |---|---|
            | Document ID | {{code}} |
            | Version | """ + DEFAULT_TEMPLATE_VERSION + """ |
            | Status | Draft |
            | Technical Owner | {{assigned_to}} |
            | Reviewer | |
            | Linked Functional Spec | {{requirement_code}} / {{title}} |
            """,
        ),
        (
            "Solution Overview & Architecture",
            """
            **Technical Purpose:**
            _Summarize how the approved functional design will be realized in SAP / BTP / middleware._

            **Landscape / Components:**
            - Source system(s):
            - Target system(s):
            - Middleware / Runtime:
            - Key integration or extension pattern:
            """,
        ),
        (
            "Technical Object Inventory",
            """
            | Object Type | Object Name | Package / Namespace | Description | New / Change |
            |---|---|---|---|---|
            | ABAP Class / Program | | {{package}} | | |
            | CDS / Table / Structure | | {{package}} | | |
            | Fiori / UI / Workflow Object | | | | |
            | Integration / Middleware Object | | | | |
            """,
        ),
    ]


def _common_ts_tail_sections() -> list[tuple[str, str]]:
    return [
        (
            "Error Handling, Monitoring & Operations",
            """
            | Topic | Design |
            |---|---|
            | Error Detection | |
            | Logging / SLG1 / AIF / Monitoring Tool | |
            | Alerting & Notification | |
            | Restart / Reprocessing Strategy | |
            """,
        ),
        (
            "Security & Authorization",
            """
            | Topic | Detail |
            |---|---|
            | Technical User / Communication User | |
            | Authorization Object(s) | |
            | Secrets / Certificates / OAuth | |
            | Audit Requirement | |
            """,
        ),
        (
            "Performance & Volume",
            """
            | Parameter | Target |
            |---|---|
            | Expected Volume | |
            | Peak Load | |
            | Batch Size / Parallelism | |
            | Timeout / SLA | |
            """,
        ),
        (
            "Deployment & Transport",
            """
            | Item | Value |
            |---|---|
            | Transport Request | {{transport_request}} |
            | Package | {{package}} |
            | Target Landscape | DEV → QAS → PRD |
            | Activation / Post-Deploy Steps | |
            | Rollback Considerations | |
            """,
        ),
        (
            "Unit Test & Technical Verification",
            """
            | Test # | Scenario | Input / Preconditions | Expected Result | Evidence |
            |---|---|---|---|---|
            | UT-01 | Happy path | | | |
            | UT-02 | Negative / error path | | | |
            | UT-03 | Volume / edge condition | | | |

            **Technical Evidence Reference:**
            {{technical_notes}}
            """,
        ),
        (
            "Open Points",
            """
            | # | Description | Owner | Due Date | Status |
            |---|---|---|---|---|
            | 1 | | | | Open |
            """,
        ),
    ]


def _build_fs_template(type_sections: list[tuple[str, str]]) -> str:
    sections = _common_fs_sections() + type_sections + _common_fs_tail_sections()
    return f"{_fs_header()}\n\n---\n\n{_render_numbered_sections(sections)}"


def _build_ts_template(type_sections: list[tuple[str, str]]) -> str:
    sections = _common_ts_sections() + type_sections + _common_ts_tail_sections()
    return f"{_ts_header()}\n\n---\n\n{_render_numbered_sections(sections)}"


def _get_default_templates() -> list[dict]:
    """Return SAP-aligned WRICEF FS/TS defaults.

    Version 2.0 normalizes every template around a common document-control shell
    so lifecycle-driven drafts and manual template generation stay consistent.
    """
    return [
        {
            "wricef_type": "interface",
            "spec_kind": "FS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Interface — FS Template v2.0",
            "is_active": True,
            "content_template": _build_fs_template([
                (
                    "Interface Business Context",
                    """
                    **Trigger / Frequency:**
                    - [ ] Real-time
                    - [ ] Scheduled / batch
                    - [ ] On-demand

                    **Direction:**
                    - [ ] Inbound
                    - [ ] Outbound
                    - [ ] Bidirectional

                    **Business Event / Driver:**
                    _Describe the event, document, or process milestone that starts the interface._
                    """,
                ),
                (
                    "Source & Target Systems",
                    """
                    | Attribute | Source System | Target System |
                    |---|---|---|
                    | System Name | | |
                    | Technology | | |
                    | Middleware / Tenant | | |
                    | Protocol | | |
                    | Message Format | | |
                    """,
                ),
                (
                    "Business Mapping & Validation Rules",
                    """
                    | # | Source Field / Concept | Target Field / Concept | Business Rule | Mandatory |
                    |---|---|---|---|---|
                    | 1 | | | | |
                    | 2 | | | | |

                    | Validation Rule | Description | Action on Failure |
                    |---|---|---|
                    | BV-01 | | |
                    | BV-02 | | |
                    """,
                ),
                (
                    "Reconciliation & Business Exception Handling",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Reconciliation Method | |
                    | Business Notification Recipient | |
                    | Manual Recovery Procedure | |
                    | Audit Requirement | |
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "interface",
            "spec_kind": "TS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Interface — TS Template v2.0",
            "is_active": True,
            "content_template": _build_ts_template([
                (
                    "Integration Pattern & Runtime Design",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Technology Stack | CPI / PI-PO / AIF / RFC / OData / REST / File |
                    | Communication Channel | |
                    | Message Protocol | |
                    | Scheduling / Event Handling | |
                    """,
                ),
                (
                    "Message Structure & Technical Mapping",
                    """
                    **Message Structure / Segment Design:**
                    _Define the envelope, payload structure, mandatory segments, and occurrence rules._

                    | # | Source Field | Source Type/Length | Mapping Logic | Target Field | Target Type/Length |
                    |---|---|---|---|---|---|
                    | 1 | | | | | |
                    | 2 | | | | | |
                    """,
                ),
                (
                    "Transformation, Validation & Reprocessing Logic",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Transformation Routine / Groovy / XSLT | |
                    | Lookup / Value Mapping Tables | |
                    | Technical Validation | |
                    | Reprocessing / Dead Letter Queue | |
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "report",
            "spec_kind": "FS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Report — FS Template v2.0",
            "is_active": True,
            "content_template": _build_fs_template([
                (
                    "Report Purpose & Consumers",
                    """
                    **Business Question:**
                    _What operational or management question does this report answer?_

                    **Target Users / Roles:**
                    _Who consumes it, how often, and what decisions depend on it?_
                    """,
                ),
                (
                    "Selection Parameters & Variants",
                    """
                    | Parameter | Description | Type | Mandatory | Default / Variant |
                    |---|---|---|---|---|
                    | | | | | |
                    | | | | | |
                    """,
                ),
                (
                    "Output Layout & Business Rules",
                    """
                    | # | Column / KPI | Source | Aggregation / Formula | Format |
                    |---|---|---|---|---|
                    | 1 | | | | |
                    | 2 | | | | |

                    **Sorting / Grouping / Drilldown:**
                    _Describe default sort order, subtotaling, and drilldown behavior._
                    """,
                ),
                (
                    "Data Sources & Reconciliation",
                    """
                    | Source | Table / CDS / API | Join / Selection Logic |
                    |---|---|---|
                    | Primary | | |
                    | Secondary | | |
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "report",
            "spec_kind": "TS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Report — TS Template v2.0",
            "is_active": True,
            "content_template": _build_ts_template([
                (
                    "Report Technology & Delivery Pattern",
                    """
                    - [ ] CDS Analytical Query + Fiori Elements
                    - [ ] Classic ALV / ABAP Report
                    - [ ] SAC / Datasphere / BW output
                    - [ ] Other: ___
                    """,
                ),
                (
                    "Data Model, Selection Logic & Query Design",
                    """
                    **Base Objects / CDS Design:**
                    _Document source tables, joins, associations, and derivations._

                    **Selection Logic:**
                    _Document filter logic, selection-screen behavior, pagination, and aggregation rules._
                    """,
                ),
                (
                    "Authorization & Performance Design",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Authorization Object / DCL | |
                    | Row / Org-Level Restriction | |
                    | Performance Strategy / Index Use | |
                    | Scheduling / Background Execution | |
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "enhancement",
            "spec_kind": "FS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Enhancement — FS Template v2.0",
            "is_active": True,
            "content_template": _build_fs_template([
                (
                    "Current SAP Standard Behavior",
                    """
                    **Current Process / Transaction:** {{transaction_code}}

                    _Describe the standard SAP behavior, user interaction, and current control points._
                    """,
                ),
                (
                    "Target Business Behavior",
                    """
                    _Describe what must change, which condition triggers the enhancement, and the intended business outcome._
                    """,
                ),
                (
                    "Business Rules, Messages & User Impact",
                    """
                    | Rule # | Condition | Action | Exception / Message |
                    |---|---|---|---|
                    | BR-01 | | | |
                    | BR-02 | | | |

                    **UI / User Impact:**
                    _Any screen changes, new fields, or user decisions introduced by the enhancement._
                    """,
                ),
                (
                    "Regression & Process Impact",
                    """
                    _Identify impacted transactions, interfaces, reports, or downstream controls that must be regression-tested._
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "enhancement",
            "spec_kind": "TS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Enhancement — TS Template v2.0",
            "is_active": True,
            "content_template": _build_ts_template([
                (
                    "Enhancement Technique & Entry Point",
                    """
                    - [ ] BAdI (New)
                    - [ ] BAdI (Classic)
                    - [ ] User Exit / Customer Exit
                    - [ ] Enhancement Spot / Section
                    - [ ] BRFplus Rule
                    - [ ] Custom Program / RAP Logic

                    **Enhancement Point:**
                    _Document the BAdI, exit, enhancement spot, or rule object._
                    """,
                ),
                (
                    "Detailed Logic Design",
                    """
                    **Pseudo Code / Processing Logic:**
                    _Document validations, branching, database access, and update behavior._

                    **Custom Data Structures / Tables:**
                    _List any new tables, structures, domains, or data elements._
                    """,
                ),
                (
                    "Regression, Logging & Supportability",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Regression Risk Area | |
                    | Message Class / Error Handling | |
                    | Debug / Trace Point | |
                    | Support Ownership | |
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "conversion",
            "spec_kind": "FS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Conversion — FS Template v2.0",
            "is_active": True,
            "content_template": _build_fs_template([
                (
                    "Migration Scope & Source Landscape",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Data Object Type | Master / Transaction / Historical / Configuration |
                    | Source System / Version | |
                    | Business Cutover Window | |
                    | Record Volume Estimate | |
                    """,
                ),
                (
                    "Legacy to SAP Mapping & Business Rules",
                    """
                    | # | Legacy Field | Legacy Meaning | S/4HANA Field | Transformation Rule | Default / Derivation |
                    |---|---|---|---|---|---|
                    | 1 | | | | | |
                    | 2 | | | | | |

                    | Validation Rule | Description | Action on Failure |
                    |---|---|---|
                    | BV-01 | Mandatory field check | Reject record |
                    | BV-02 | | |
                    """,
                ),
                (
                    "Data Cleansing, Reconciliation & Mock Load Strategy",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Data Cleansing Requirement | |
                    | Reconciliation Control | |
                    | Mock / Dress Rehearsal Expectation | |
                    | Business Sign-Off Condition | |
                    """,
                ),
                (
                    "Cutover Dependencies",
                    """
                    _List sequencing constraints, business freeze windows, prerequisite transports, and downstream handover dependencies._
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "conversion",
            "spec_kind": "TS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Conversion — TS Template v2.0",
            "is_active": True,
            "content_template": _build_ts_template([
                (
                    "Migration Tooling & Execution Pattern",
                    """
                    - [ ] SAP Migration Cockpit
                    - [ ] SAP Data Services
                    - [ ] Custom ABAP Program
                    - [ ] Staging Tables / Direct Transfer
                    - [ ] Other: ___
                    """,
                ),
                (
                    "Extract, Transform & Load Design",
                    """
                    | Phase | Design |
                    |---|---|
                    | Extract Logic | |
                    | Transform / Mapping Logic | |
                    | Load Method (BAPI / Staging / IDoc) | |
                    | Commit / Restart Strategy | |
                    """,
                ),
                (
                    "Batch Control, Logging & Recovery",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Batch Size | |
                    | Parallel Processing | |
                    | Error Log Table / SLG1 Object | |
                    | Restart / Resume Rule | |
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "workflow",
            "spec_kind": "FS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Workflow — FS Template v2.0",
            "is_active": True,
            "content_template": _build_fs_template([
                (
                    "Workflow Trigger & Business Scope",
                    """
                    **Triggering Event:**
                    _Describe the document, exception, or approval milestone that starts the workflow._

                    **Trigger Object / Transaction:**
                    {{transaction_code}}
                    """,
                ),
                (
                    "Approval / Decision Flow",
                    """
                    | Step # | Approver Role | Entry Condition | Action on Approve | Action on Reject | SLA |
                    |---|---|---|---|---|---|
                    | 1 | | | | | |
                    | 2 | | | | | |
                    | 3 | | | | | |
                    """,
                ),
                (
                    "Escalation, Delegation & Notification Rules",
                    """
                    | Rule | Condition | Action |
                    |---|---|---|
                    | Timeout | | |
                    | Delegation | | |

                    | Event | Recipient | Channel | Template |
                    |---|---|---|---|
                    | New work item | | | |
                    | Approved | | | |
                    | Rejected | | | |
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "workflow",
            "spec_kind": "TS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Workflow — TS Template v2.0",
            "is_active": True,
            "content_template": _build_ts_template([
                (
                    "Workflow Platform & Runtime",
                    """
                    - [ ] SAP Flexible Workflow
                    - [ ] SAP Business Workflow
                    - [ ] BRFplus + Workflow
                    - [ ] SAP Build Process Automation
                    - [ ] Custom ABAP / RAP Flow
                    """,
                ),
                (
                    "Workflow Definition, Agents & Rules",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Workflow Template / WS Object | |
                    | Task / Approval Step Objects | |
                    | Agent Determination Logic | |
                    | BRFplus / Rule Service | |
                    """,
                ),
                (
                    "Inbox, Event Linkage & Recovery",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Fiori My Inbox / UI Integration | |
                    | Event Linkage | |
                    | Error / Orphan Work Item Handling | |
                    | Restart / Admin Recovery | |
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "form",
            "spec_kind": "FS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Form — FS Template v2.0",
            "is_active": True,
            "content_template": _build_fs_template([
                (
                    "Form Purpose, Trigger & Output Channels",
                    """
                    **Form Type / Business Use:**
                    _Invoice, PO, delivery note, payment advice, label, etc._

                    **Trigger Transaction / App:** {{transaction_code}}

                    **Output Channel:**
                    - [ ] Print
                    - [ ] Email PDF
                    - [ ] EDI / XML
                    - [ ] Archive / Portal
                    """,
                ),
                (
                    "Layout, Languages & Branding",
                    """
                    | Section | Content / Rule |
                    |---|---|
                    | Header | |
                    | Body | |
                    | Footer | |

                    | Language | Required |
                    |---|---|
                    | EN | |
                    | TR | |
                    | Other | |
                    """,
                ),
                (
                    "Data Fields & Output Determination",
                    """
                    | # | Field | Source | Format / Rule | Mandatory |
                    |---|---|---|---|---|
                    | 1 | | | | |
                    | 2 | | | | |

                    | Condition | Output Type | Medium | Timing |
                    |---|---|---|---|
                    | | | | |
                    """,
                ),
            ]),
        },
        {
            "wricef_type": "form",
            "spec_kind": "TS",
            "version": DEFAULT_TEMPLATE_VERSION,
            "title": "Form — TS Template v2.0",
            "is_active": True,
            "content_template": _build_ts_template([
                (
                    "Form Technology & Output Stack",
                    """
                    - [ ] Adobe Forms
                    - [ ] SmartForms
                    - [ ] SAPscript
                    - [ ] Output Management / BRFplus
                    - [ ] Other: ___
                    """,
                ),
                (
                    "Form Interface, Layout & Binding",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Form Interface | |
                    | Layout / Window Structure | |
                    | Data Binding Rules | |
                    | Device / Spool Configuration | |
                    """,
                ),
                (
                    "Output Management & Operational Controls",
                    """
                    | Topic | Detail |
                    |---|---|
                    | Output Type / BRFplus Rule | |
                    | NAST / NACE / Output Parameter Determination | |
                    | Email / Archive Integration | |
                    | Error Handling / Reprint Strategy | |
                    """,
                ),
            ]),
        },
    ]
