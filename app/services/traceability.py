"""
SAP Transformation Management Platform
Traceability Engine v2 — Sprint 9 scope.

Provides the ability to trace from any entity up and down the full chain:
    Scenario → Requirement → WRICEF Item / Config Item → FS → TS
                           → Interface → ConnectivityTest / SwitchPlan

The engine builds a chain dict showing upstream (parents) and downstream
(children) links for a given entity.
"""

import logging

from app.models import db
from app.models.backlog import BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec
# ExploreRequirement is the canonical requirement model (ADR-001).
# ExploreRequirement replaces the legacy Requirement table as the single source
# of truth for all new requirement data.
from app.models.explore import ExploreRequirement
from app.models.integration import Interface, Wave, ConnectivityTest, SwitchPlan
# Legacy Requirement kept for backward-compatible read paths only (write-blocked).
from app.models.requirement import Requirement
from app.models.scenario import Scenario, Workshop
from app.models.scope import Process, Analysis
from app.models.testing import TestCase, Defect, TestExecution
from app.services.helpers.scoped_queries import get_scoped_or_none

logger = logging.getLogger(__name__)

# Supported entity types for chain traversal.
# ExploreRequirement is the canonical path (UUID PK) and is served by the
# dedicated trace_explore_requirement() function in the blueprint.
# "requirement" (integer PK) is the legacy path — kept for backward compat only.
ENTITY_TYPES = {
    "scenario": Scenario,
    "workshop": Workshop,
    "process": Process,
    "analysis": Analysis,
    "explore_requirement": ExploreRequirement,  # canonical — ADR-001
    "requirement": Requirement,                 # legacy — read-only, no new writes
    "backlog_item": BacklogItem,
    "config_item": ConfigItem,
    "functional_spec": FunctionalSpec,
    "technical_spec": TechnicalSpec,
    "test_case": TestCase,
    "defect": Defect,
    # Sprint 9 — Integration Factory
    "interface": Interface,
    "wave": Wave,
    "connectivity_test": ConnectivityTest,
    "switch_plan": SwitchPlan,
}


def get_chain(
    entity_type: str,
    entity_id: int,
    *,
    program_id: int | None = None,
) -> dict:
    """
    Build a traceability chain for the given entity.

    Returns a dict with:
        - entity: the entity itself
        - upstream: list of parent entities (towards Scenario)
        - downstream: list of child entities (towards TS/Test)
        - links_summary: counts of linked items by type

    Args:
        entity_type: one of ENTITY_TYPES keys
        entity_id: primary key of the entity
        program_id: Scope for models with a direct ``program_id`` column.
            When provided, scopes the initial entity lookup to enforce tenant
            isolation. Models without ``program_id`` (Scenario, Process, etc.)
            fall back to an unscoped lookup; add project_id scoping separately
            once those models carry the column.

    Returns:
        dict with chain information, or None if entity not found.
    """
    model = ENTITY_TYPES.get(entity_type)
    if not model:
        return None

    # Scope the initial lookup by program_id when available on the model.
    # FK-nav helpers further in the chain traverse DB-stored FK values from
    # the verified entity, so only the entry point needs user-supplied scoping.
    if program_id is not None and hasattr(model, "__table__") and "program_id" in model.__table__.c:
        entity = get_scoped_or_none(model, entity_id, program_id=program_id)
    else:
        entity = db.session.get(model, entity_id)
    if not entity:
        return None

    upstream = []
    downstream = []

    if entity_type == "technical_spec":
        _trace_ts_upstream(entity, upstream)
    elif entity_type == "functional_spec":
        _trace_fs_upstream(entity, upstream)
        _trace_fs_downstream(entity, downstream)
    elif entity_type == "backlog_item":
        _trace_backlog_upstream(entity, upstream)
        _trace_backlog_downstream(entity, downstream)
    elif entity_type == "config_item":
        _trace_config_upstream(entity, upstream)
        _trace_config_downstream(entity, downstream)
    elif entity_type == "explore_requirement":
        # Canonical path (ADR-001) — upstream via ProcessLevel hierarchy + downstream via explore_requirement_id FK
        _build_explore_upstream_inline(entity, upstream)
        _trace_requirement_downstream(entity, downstream)
    elif entity_type == "requirement":
        _trace_requirement_upstream(entity, upstream)
        _trace_requirement_downstream(entity, downstream)
    elif entity_type == "scenario":
        _trace_scenario_downstream(entity, downstream)
    elif entity_type == "process":
        _trace_process_upstream(entity, upstream)
        _trace_process_downstream(entity, downstream)
    elif entity_type == "analysis":
        _trace_analysis_upstream(entity, upstream)
    elif entity_type == "test_case":
        _trace_test_case_upstream(entity, upstream)
        _trace_test_case_downstream(entity, downstream)
    elif entity_type == "defect":
        _trace_defect_upstream(entity, upstream)
    # Sprint 9 — Integration Factory
    elif entity_type == "interface":
        _trace_interface_upstream(entity, upstream)
        _trace_interface_downstream(entity, downstream)
    elif entity_type == "wave":
        _trace_wave_downstream(entity, downstream)
    elif entity_type == "connectivity_test":
        _trace_connectivity_test_upstream(entity, upstream)
    elif entity_type == "switch_plan":
        _trace_switch_plan_upstream(entity, upstream)

    links_summary = {}
    for item in upstream + downstream:
        t = item["type"]
        links_summary[t] = links_summary.get(t, 0) + 1

    return {
        "entity": {
            "type": entity_type,
            "id": entity_id,
            "title": getattr(entity, "title", getattr(entity, "name", str(entity_id))),
        },
        "upstream": upstream,
        "downstream": downstream,
        "links_summary": links_summary,
    }


def get_requirement_links(requirement_id: int, *, program_id: int | None = None) -> dict:
    """
    Get all WRICEF items and Config items linked to a requirement.

    Args:
        requirement_id: Requirement primary key (user-supplied).
        program_id: Scope for the Requirement lookup when provided.

    Returns:
        dict with backlog_items and config_items lists.
    """
    req = (
        get_scoped_or_none(Requirement, requirement_id, program_id=program_id)
        if program_id is not None
        else db.session.get(Requirement, requirement_id)
    )
    if not req:
        return None

    backlog_items = BacklogItem.query.filter_by(requirement_id=requirement_id).all()
    config_items = ConfigItem.query.filter_by(requirement_id=requirement_id).all()

    return {
        "requirement": {"id": req.id, "code": req.code, "title": req.title},
        "backlog_items": [
            {"id": b.id, "code": b.code, "title": b.title,
             "wricef_type": b.wricef_type, "status": b.status}
            for b in backlog_items
        ],
        "config_items": [
            {"id": c.id, "code": c.code, "title": c.title,
             "module": c.module, "status": c.status}
            for c in config_items
        ],
        "total_linked": len(backlog_items) + len(config_items),
    }


def get_program_traceability_summary(program_id: int) -> dict:
    """Build a program-level traceability summary showing coverage.

    ADR-001: Uses ExploreRequirement (canonical) as the requirement source.
    BacklogItem.explore_requirement_id and ConfigItem.explore_requirement_id
    are the canonical FKs; legacy requirement_id FKs are ignored here.

    Returns counts of linked vs unlinked items across the chain.
    """
    # Canonical requirement source (ADR-001)
    requirements = ExploreRequirement.query.filter_by(project_id=program_id).all()
    backlog_items = BacklogItem.query.filter_by(program_id=program_id).all()
    config_items = ConfigItem.query.filter_by(program_id=program_id).all()

    # Use canonical explore_requirement_id FK (not legacy requirement_id)
    req_with_backlog = set()
    req_with_config = set()
    for b in backlog_items:
        if b.explore_requirement_id:
            req_with_backlog.add(b.explore_requirement_id)
    for c in config_items:
        if c.explore_requirement_id:
            req_with_config.add(c.explore_requirement_id)

    linked_req_ids = req_with_backlog | req_with_config
    backlog_with_fs = sum(1 for b in backlog_items if b.functional_spec is not None)
    config_with_fs = sum(1 for c in config_items if c.functional_spec is not None)

    fs_list = FunctionalSpec.query.join(
        BacklogItem, FunctionalSpec.backlog_item_id == BacklogItem.id, isouter=True
    ).join(
        ConfigItem, FunctionalSpec.config_item_id == ConfigItem.id, isouter=True
    ).filter(
        db.or_(
            BacklogItem.program_id == program_id,
            ConfigItem.program_id == program_id,
        )
    ).all()
    fs_with_ts = sum(1 for fs in fs_list if fs.technical_spec is not None)

    # Test coverage via explore_requirement_id (canonical)
    test_cases = TestCase.query.filter_by(program_id=program_id).all()
    defects = Defect.query.filter_by(program_id=program_id).all()
    req_ids_with_tests = set(
        tc.explore_requirement_id for tc in test_cases if tc.explore_requirement_id
    )

    return {
        "requirements": {
            "total": len(requirements),
            "linked_to_backlog_or_config": len(linked_req_ids),
            "unlinked": len(requirements) - len(linked_req_ids),
            "coverage_pct": round(len(linked_req_ids) / len(requirements) * 100) if requirements else 0,
        },
        "backlog_items": {
            "total": len(backlog_items),
            "with_requirement": sum(1 for b in backlog_items if b.explore_requirement_id),
            "with_functional_spec": backlog_with_fs,
        },
        "config_items": {
            "total": len(config_items),
            "with_requirement": sum(1 for c in config_items if c.explore_requirement_id),
            "with_functional_spec": config_with_fs,
        },
        "functional_specs": {
            "total": len(fs_list),
            "with_technical_spec": fs_with_ts,
        },
        "test_cases": {
            "total": len(test_cases),
            "with_requirement": sum(1 for tc in test_cases if tc.explore_requirement_id),
            "regression_flagged": sum(1 for tc in test_cases if tc.is_regression),
        },
        "defects": {
            "total": len(defects),
            "open": sum(1 for d in defects if d.status not in ("closed", "rejected")),
            "with_test_case": sum(1 for d in defects if d.test_case_id),
        },
        "test_coverage": {
            "requirements_with_tests": len(req_ids_with_tests),
            "requirements_without_tests": len(requirements) - len(req_ids_with_tests),
            "coverage_pct": round(
                len(req_ids_with_tests) / len(requirements) * 100
            ) if requirements else 0,
        },
        # Sprint 9 — Integration Factory
        "interfaces": _program_interface_summary(program_id),
    }


# ── Private helpers ──────────────────────────────────────────────────────────

def _trace_ts_upstream(ts, chain):
    """TS → FS → BacklogItem/ConfigItem → Requirement → Scenario."""
    fs = ts.functional_spec
    if fs:
        chain.append({"type": "functional_spec", "id": fs.id, "title": fs.title})
        _trace_fs_upstream(fs, chain)


def _trace_fs_upstream(fs, chain):
    """FS → BacklogItem/ConfigItem → Requirement → Scenario."""
    if fs.backlog_item_id:
        bi = db.session.get(BacklogItem, fs.backlog_item_id)
        if bi:
            chain.append({"type": "backlog_item", "id": bi.id, "title": bi.title,
                          "wricef_type": bi.wricef_type})
            _trace_backlog_upstream(bi, chain)
    elif fs.config_item_id:
        ci = db.session.get(ConfigItem, fs.config_item_id)
        if ci:
            chain.append({"type": "config_item", "id": ci.id, "title": ci.title})
            _trace_config_upstream(ci, chain)


def _trace_fs_downstream(fs, chain):
    """FS → TS."""
    if fs.technical_spec:
        chain.append({"type": "technical_spec", "id": fs.technical_spec.id,
                       "title": fs.technical_spec.title})


def _trace_backlog_upstream(bi, chain):
    """BacklogItem → Requirement → Scenario."""
    if bi.requirement_id:
        req = db.session.get(Requirement, bi.requirement_id)
        if req:
            chain.append({"type": "requirement", "id": req.id, "title": req.title})
            _trace_requirement_upstream(req, chain)


def _trace_backlog_downstream(bi, chain):
    """BacklogItem → FS → TS + Interfaces."""
    if bi.functional_spec:
        chain.append({"type": "functional_spec", "id": bi.functional_spec.id,
                       "title": bi.functional_spec.title})
        _trace_fs_downstream(bi.functional_spec, chain)
    # Sprint 9: linked interfaces
    interfaces = Interface.query.filter_by(backlog_item_id=bi.id).all()
    for iface in interfaces:
        chain.append({"type": "interface", "id": iface.id, "title": iface.name,
                       "code": iface.code, "direction": iface.direction})


def _trace_config_upstream(ci, chain):
    """ConfigItem → Requirement → Scenario."""
    if ci.requirement_id:
        req = db.session.get(Requirement, ci.requirement_id)
        if req:
            chain.append({"type": "requirement", "id": req.id, "title": req.title})
            _trace_requirement_upstream(req, chain)


def _trace_config_downstream(ci, chain):
    """ConfigItem → FS → TS."""
    if ci.functional_spec:
        chain.append({"type": "functional_spec", "id": ci.functional_spec.id,
                       "title": ci.functional_spec.title})
        _trace_fs_downstream(ci.functional_spec, chain)


def _trace_requirement_upstream(req, chain):
    """Requirement → Process (via RequirementProcessMapping) → Scenario."""
    from app.models.scope import RequirementProcessMapping
    # Trace via actual requirement→process mappings
    mappings = RequirementProcessMapping.query.filter_by(requirement_id=req.id).all()
    seen_scenarios = set()
    for mapping in mappings:
        process = db.session.get(Process, mapping.process_id)
        if process:
            chain.append({"type": "process", "id": process.id, "title": process.name,
                          "level": process.level})
            # Walk up to find the scenario via the top-level process's scenario_id
            root = process
            while root.parent_id:
                root = db.session.get(Process, root.parent_id)
                if not root:
                    break
            if root and root.scenario_id and root.scenario_id not in seen_scenarios:
                seen_scenarios.add(root.scenario_id)
                scenario = db.session.get(Scenario, root.scenario_id)
                if scenario:
                    chain.append({"type": "scenario", "id": scenario.id, "title": scenario.name})
    # Fallback: if no mappings found, use scenario_id from requirement if it exists
    if not mappings:
        scenario_id = getattr(req, 'scenario_id', None)
        if scenario_id:
            scenario = db.session.get(Scenario, scenario_id)
            if scenario:
                chain.append({"type": "scenario", "id": scenario.id, "title": scenario.name})


def _trace_requirement_downstream(req, chain):
    """Requirement (legacy or ExploreRequirement) → BacklogItems + ConfigItems → TestCases → Defects.

    ADR-001: If req.id is a UUID string (ExploreRequirement), use explore_requirement_id
    as the canonical FK on child models.  If req.id is an integer (legacy Requirement),
    fall back to the legacy requirement_id FK for backward compatibility.
    """
    is_explore = isinstance(req.id, str)  # UUID string → ExploreRequirement

    if is_explore:
        backlog_items = BacklogItem.query.filter_by(explore_requirement_id=req.id).all()
    else:
        backlog_items = BacklogItem.query.filter_by(requirement_id=req.id).all()

    for bi in backlog_items:
        chain.append({"type": "backlog_item", "id": bi.id, "title": bi.title,
                       "wricef_type": bi.wricef_type})
        _trace_backlog_downstream(bi, chain)

    if is_explore:
        config_items = ConfigItem.query.filter_by(explore_requirement_id=req.id).all()
    else:
        config_items = ConfigItem.query.filter_by(requirement_id=req.id).all()

    for ci in config_items:
        chain.append({"type": "config_item", "id": ci.id, "title": ci.title})
        _trace_config_downstream(ci, chain)

    # Test Cases — prefer explore_requirement_id
    if is_explore:
        test_cases = TestCase.query.filter_by(explore_requirement_id=req.id).all()
    else:
        test_cases = TestCase.query.filter_by(requirement_id=req.id).all()

    for tc in test_cases:
        chain.append({"type": "test_case", "id": tc.id, "title": tc.title,
                       "code": tc.code, "test_layer": tc.test_layer})
        _trace_test_case_downstream(tc, chain)


def _trace_scenario_downstream(scenario, chain):
    """Scenario → Processes → Requirements → BacklogItems + ConfigItems → FS → TS → TestCases → Defects."""
    # Only trace requirements linked to this scenario (via workshop or process mappings)
    from app.models.scope import Process
    from app.models.requirement import RequirementProcessMapping

    # 1. Requirements directly linked via workshop
    seen_req_ids = set()
    workshop_reqs = (
        Requirement.query
        .join(Workshop, Requirement.workshop_id == Workshop.id)
        .filter(Workshop.scenario_id == scenario.id)
        .all()
    )
    for req in workshop_reqs:
        if req.id not in seen_req_ids:
            seen_req_ids.add(req.id)
            chain.append({"type": "requirement", "id": req.id, "title": req.title})
            _trace_requirement_downstream(req, chain)

    # 2. Requirements linked via process mappings to processes in this scenario
    process_reqs = (
        Requirement.query
        .join(RequirementProcessMapping, Requirement.id == RequirementProcessMapping.requirement_id)
        .join(Process, RequirementProcessMapping.process_id == Process.id)
        .filter(Process.scenario_id == scenario.id)
        .all()
    )
    for req in process_reqs:
        if req.id not in seen_req_ids:
            seen_req_ids.add(req.id)
            chain.append({"type": "requirement", "id": req.id, "title": req.title})
            _trace_requirement_downstream(req, chain)


# ── Sprint 5 — Test Case & Defect tracing ────────────────────────────────────

def _trace_test_case_upstream(tc, chain):
    """TestCase → ExploreRequirement (or standard Requirement) → upstream hierarchy."""
    if tc.explore_requirement_id:
        from app.models.explore import ExploreRequirement
        req = db.session.get(ExploreRequirement, tc.explore_requirement_id)
        if req:
            chain.append({
                "type": "explore_requirement",
                "id": str(req.id),
                "title": req.title,
                "code": req.code,
                "fit_status": req.fit_status,
            })
            # Walk the explore upstream hierarchy (workshop → process steps → levels)
            _build_explore_upstream_inline(req, chain)
    elif tc.requirement_id:
        req = db.session.get(Requirement, tc.requirement_id)
        if req:
            chain.append({"type": "requirement", "id": req.id, "title": req.title})
            _trace_requirement_upstream(req, chain)
    if tc.backlog_item_id:
        bi = db.session.get(BacklogItem, tc.backlog_item_id)
        if bi:
            chain.append({"type": "backlog_item", "id": bi.id, "title": bi.title,
                          "wricef_type": bi.wricef_type})
    if tc.config_item_id:
        ci = db.session.get(ConfigItem, tc.config_item_id)
        if ci:
            chain.append({"type": "config_item", "id": ci.id, "title": ci.title})


def _build_explore_upstream_inline(req, chain):
    """Walk ExploreRequirement's workshop + process level hierarchy into chain.

    Inlines the process-level walk to avoid a circular import with the
    traceability blueprint's private _walk_process_level_hierarchy helper.
    """
    from app.models.explore import ExploreWorkshop, ProcessStep, ProcessLevel

    if req.workshop_id:
        ws = db.session.get(ExploreWorkshop, req.workshop_id)
        if ws:
            chain.append({"type": "workshop", "id": ws.id, "title": ws.name, "code": ws.code})

    # Determine starting process_level_id
    start_level_id = None
    if req.process_step_id:
        ps = db.session.get(ProcessStep, req.process_step_id)
        if ps:
            chain.append({"type": "process_step", "id": str(ps.id), "title": f"Step {str(ps.id)[:8]}"})
            start_level_id = ps.process_level_id
    elif req.process_level_id:
        start_level_id = req.process_level_id

    # Walk up through ProcessLevel ancestors
    visited: set = set()
    current_id = start_level_id
    while current_id and current_id not in visited:
        visited.add(current_id)
        pl = db.session.get(ProcessLevel, current_id)
        if not pl:
            break
        chain.append({
            "type": f"process_l{pl.level}" if pl.level else "process_level",
            "id": str(pl.id),
            "title": pl.name,
            "code": pl.code,
        })
        current_id = pl.parent_id


def _trace_test_case_downstream(tc, chain):
    """TestCase → Defects."""
    defects = Defect.query.filter_by(test_case_id=tc.id).all()
    for d in defects:
        chain.append({"type": "defect", "id": d.id, "title": d.title,
                       "code": d.code, "severity": d.severity, "status": d.status})


def _trace_defect_upstream(defect, chain):
    """Defect → TestCase → Requirement → Scenario."""
    if defect.test_case_id:
        tc = db.session.get(TestCase, defect.test_case_id)
        if tc:
            chain.append({"type": "test_case", "id": tc.id, "title": tc.title,
                          "code": tc.code, "test_layer": tc.test_layer})
            _trace_test_case_upstream(tc, chain)
    if defect.backlog_item_id:
        bi = db.session.get(BacklogItem, defect.backlog_item_id)
        if bi:
            chain.append({"type": "backlog_item", "id": bi.id, "title": bi.title,
                          "wricef_type": bi.wricef_type})
    if defect.config_item_id:
        ci = db.session.get(ConfigItem, defect.config_item_id)
        if ci:
            chain.append({"type": "config_item", "id": ci.id, "title": ci.title})


# ── Scope chain tracing (Process L2/L3 / Analysis) ───────────────────────

def _trace_process_upstream(process, chain):
    """Process → Scenario."""
    scenario = db.session.get(Scenario, process.scenario_id)
    if scenario:
        chain.append({"type": "scenario", "id": scenario.id, "title": scenario.name})
    if process.parent_id:
        parent = db.session.get(Process, process.parent_id)
        if parent:
            chain.append({"type": "process", "id": parent.id, "title": parent.name,
                          "level": parent.level})
            _trace_process_upstream(parent, chain)


def _trace_process_downstream(process, chain):
    """Process → child processes / Analyses (L3 → Analyses)."""
    # L3 processes have analyses directly
    analyses = Analysis.query.filter_by(process_id=process.id).all()
    for a in analyses:
        chain.append({"type": "analysis", "id": a.id, "title": a.name,
                       "status": a.status, "fit_gap_result": a.fit_gap_result})
    children = Process.query.filter_by(parent_id=process.id).all()
    for child in children:
        chain.append({"type": "process", "id": child.id, "title": child.name,
                       "level": child.level})
        _trace_process_downstream(child, chain)


def _trace_analysis_upstream(analysis, chain):
    """Analysis → Process (L3) → Process (L2) → Scenario."""
    process = db.session.get(Process, analysis.process_id)
    if process:
        chain.append({"type": "process", "id": process.id, "title": process.name,
                       "level": process.level})
        _trace_process_upstream(process, chain)


# ── Sprint 9 — Interface / Wave / ConnectivityTest / SwitchPlan tracing ──

def _trace_interface_upstream(iface, chain):
    """Interface → BacklogItem → Requirement → Scenario  (+ Wave)."""
    if iface.wave_id:
        wave = db.session.get(Wave, iface.wave_id)
        if wave:
            chain.append({"type": "wave", "id": wave.id, "title": wave.name})
    if iface.backlog_item_id:
        bi = db.session.get(BacklogItem, iface.backlog_item_id)
        if bi:
            chain.append({"type": "backlog_item", "id": bi.id, "title": bi.title,
                          "wricef_type": bi.wricef_type})
            _trace_backlog_upstream(bi, chain)


def _trace_interface_downstream(iface, chain):
    """Interface → ConnectivityTests + SwitchPlans."""
    for ct in iface.connectivity_tests:
        chain.append({"type": "connectivity_test", "id": ct.id,
                       "title": f"{ct.environment}: {ct.result}",
                       "environment": ct.environment, "result": ct.result})
    for sp in iface.switch_plans:
        chain.append({"type": "switch_plan", "id": sp.id,
                       "title": f"#{sp.sequence} {sp.action}",
                       "action": sp.action, "status": sp.status})


def _trace_wave_downstream(wave, chain):
    """Wave → Interfaces → ConnectivityTests + SwitchPlans."""
    for iface in wave.interfaces:
        chain.append({"type": "interface", "id": iface.id, "title": iface.name,
                       "code": iface.code, "direction": iface.direction,
                       "status": iface.status})
        _trace_interface_downstream(iface, chain)


def _trace_connectivity_test_upstream(ct, chain):
    """ConnectivityTest → Interface → BacklogItem → Requirement."""
    iface = db.session.get(Interface, ct.interface_id)
    if iface:
        chain.append({"type": "interface", "id": iface.id, "title": iface.name,
                       "code": iface.code})
        _trace_interface_upstream(iface, chain)


def _trace_switch_plan_upstream(sp, chain):
    """SwitchPlan → Interface → BacklogItem → Requirement."""
    iface = db.session.get(Interface, sp.interface_id)
    if iface:
        chain.append({"type": "interface", "id": iface.id, "title": iface.name,
                       "code": iface.code})
        _trace_interface_upstream(iface, chain)


# ── Program-level interface summary helper ────────────────────────────────

def _program_interface_summary(program_id):
    """Build interface/wave summary for program traceability report."""
    interfaces = Interface.query.filter_by(program_id=program_id).all()
    waves = Wave.query.filter_by(program_id=program_id).all()

    by_status = {}
    by_direction = {}
    with_backlog = 0
    with_wave = 0
    connectivity_tested = 0

    for iface in interfaces:
        by_status[iface.status] = by_status.get(iface.status, 0) + 1
        by_direction[iface.direction] = by_direction.get(iface.direction, 0) + 1
        if iface.backlog_item_id:
            with_backlog += 1
        if iface.wave_id:
            with_wave += 1
        # Check if any successful connectivity test exists
        success = ConnectivityTest.query.filter_by(
            interface_id=iface.id, result="success",
        ).first()
        if success:
            connectivity_tested += 1

    return {
        "total": len(interfaces),
        "by_status": by_status,
        "by_direction": by_direction,
        "with_backlog_item": with_backlog,
        "assigned_to_wave": with_wave,
        "connectivity_tested": connectivity_tested,
        "waves": {
            "total": len(waves),
            "by_status": {w.status: sum(1 for ww in waves if ww.status == w.status) for w in waves},
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# WR-2.4 — Explore Requirement FK-chain traceability (NO new table)
# Chain: ExploreRequirement → BacklogItem / ConfigItem → TestCase → Defect
#                           ↔ ExploreOpenItem (via RequirementOpenItemLink)
# ══════════════════════════════════════════════════════════════════════════════

from app.models.explore import (
    ExploreOpenItem,
    ExploreRequirement,
    RequirementOpenItemLink,
)


def trace_explore_requirement(requirement_id: str) -> dict:
    """
    Build a full traceability graph for a single *ExploreRequirement*.

    Returns:
        {
            "requirement": {id, code, title, status, priority, type},
            "backlog_items": [...],
            "config_items": [...],
            "test_cases": [...],
            "defects": [...],
            "open_items": [...],
            "coverage": {backlog, config, test, defect, open_item},
            "chain_depth": int,     # max downstream depth reached
        }

    Raises ``ValueError`` if the requirement does not exist.
    """
    req = db.session.get(ExploreRequirement, requirement_id)
    if not req:
        raise ValueError(f"Explore requirement not found: {requirement_id}")

    # ── 1. Backlog items (WRICEF) ────────────────────────────────────────
    backlog_items = BacklogItem.query.filter_by(
        explore_requirement_id=requirement_id,
    ).all()

    # ── 2. Config items ──────────────────────────────────────────────────
    config_items = ConfigItem.query.filter_by(
        explore_requirement_id=requirement_id,
    ).all()

    # ── 3. Test cases (via backlog_item_id OR direct explore_req FK) ─────
    backlog_ids = [b.id for b in backlog_items]

    tc_via_backlog: list[TestCase] = []
    if backlog_ids:
        tc_via_backlog = TestCase.query.filter(
            TestCase.backlog_item_id.in_(backlog_ids),
        ).all()

    tc_via_direct = TestCase.query.filter_by(
        explore_requirement_id=requirement_id,
    ).all()

    tc_map: dict[int, TestCase] = {}
    for tc in tc_via_backlog + tc_via_direct:
        tc_map[tc.id] = tc
    test_cases = list(tc_map.values())

    # ── 4. Defects (via test_case_id OR direct explore_req FK) ───────────
    tc_ids = [tc.id for tc in test_cases]

    d_via_tc: list[Defect] = []
    if tc_ids:
        d_via_tc = Defect.query.filter(
            Defect.test_case_id.in_(tc_ids),
        ).all()

    d_via_direct = Defect.query.filter_by(
        explore_requirement_id=requirement_id,
    ).all()

    d_map: dict[int, Defect] = {}
    for d in d_via_tc + d_via_direct:
        d_map[d.id] = d
    defects = list(d_map.values())

    # ── 5. Open items (M:N via RequirementOpenItemLink) ──────────────────
    links = RequirementOpenItemLink.query.filter_by(
        requirement_id=requirement_id,
    ).all()
    oi_ids = [lnk.open_item_id for lnk in links]
    open_items: list[ExploreOpenItem] = []
    if oi_ids:
        open_items = ExploreOpenItem.query.filter(
            ExploreOpenItem.id.in_(oi_ids),
        ).all()

    # ── 6. Coverage & depth ──────────────────────────────────────────────
    coverage = {
        "backlog": len(backlog_items),
        "config": len(config_items),
        "test": len(test_cases),
        "defect": len(defects),
        "open_item": len(open_items),
    }

    depth = 1  # requirement itself
    if backlog_items or config_items:
        depth = 2
    if test_cases:
        depth = 3
    if defects:
        depth = 4

    return {
        "requirement": {
            "id": req.id,
            "code": req.code,
            "title": req.title,
            "status": req.status,
            "priority": req.priority,
            "type": req.type,
        },
        "backlog_items": [
            {"id": b.id, "code": getattr(b, "code", ""), "title": b.title,
             "status": b.status, "type": getattr(b, "wricef_type", "")}
            for b in backlog_items
        ],
        "config_items": [
            {"id": c.id, "code": c.code, "title": c.title, "status": c.status}
            for c in config_items
        ],
        "test_cases": [
            {"id": tc.id, "code": getattr(tc, "code", ""), "title": tc.title,
             "status": tc.status, "result": getattr(tc, "result", None)}
            for tc in test_cases
        ],
        "defects": [
            {"id": d.id, "code": getattr(d, "code", ""), "title": d.title,
             "status": d.status, "severity": getattr(d, "severity", "")}
            for d in defects
        ],
        "open_items": [
            {"id": oi.id, "code": oi.code, "title": oi.title,
             "status": oi.status, "priority": oi.priority}
            for oi in open_items
        ],
        "coverage": coverage,
        "chain_depth": depth,
    }


def trace_explore_batch(requirement_ids: list[str]) -> list[dict]:
    """Trace multiple explore requirements in one call."""
    results = []
    for rid in requirement_ids:
        try:
            results.append(trace_explore_requirement(rid))
        except ValueError:
            results.append({"requirement_id": rid, "error": "not_found"})
    return results


# ══════════════════════════════════════════════════════════════════════════════
# Lateral link helpers (Open Items, Decisions, Interfaces)
# Moved here from the blueprint layer to keep ORM access service-side.
# ══════════════════════════════════════════════════════════════════════════════

def build_explore_lateral(requirement_id: int) -> dict:
    """Return Open Items and Decisions laterally linked to an ExploreRequirement.

    Queries the RequirementOpenItemLink M:N table and the ExploreDecision table
    via the requirement's ProcessStep, giving callers a flat lateral context
    dict without needing direct ORM access in the blueprint.

    Args:
        requirement_id: PK of the ExploreRequirement.

    Returns:
        Dict with keys ``open_items`` and ``decisions``, each a list of dicts.
    """
    from app.models import db
    from app.models.explore import (
        ExploreDecision,
        ExploreOpenItem,
        ExploreRequirement,
        ProcessStep,
        RequirementOpenItemLink,
    )

    lateral: dict = {"open_items": [], "decisions": []}

    # Open Items (M:N via RequirementOpenItemLink)
    links = RequirementOpenItemLink.query.filter_by(
        requirement_id=requirement_id,
    ).all()
    for lnk in links:
        oi = db.session.get(ExploreOpenItem, lnk.open_item_id)
        if oi:
            lateral["open_items"].append({
                "id": oi.id,
                "code": oi.code,
                "title": oi.title,
                "status": oi.status,
                "priority": oi.priority,
                "link_type": lnk.link_type,
            })

    # Decisions (via ProcessStep)
    req = db.session.get(ExploreRequirement, requirement_id)
    if req and req.process_step_id:
        ps = db.session.get(ProcessStep, req.process_step_id)
        if ps:
            decisions = ExploreDecision.query.filter_by(process_step_id=ps.id).all()
            for d in decisions:
                lateral["decisions"].append({
                    "id": d.id,
                    "code": d.code,
                    "text": d.text,
                    "decided_by": d.decided_by,
                    "category": d.category,
                    "status": d.status,
                })

    return lateral


def build_lateral_links(entity_type: str, entity_id: int) -> dict:
    """Return lateral link data for standard (non-explore) entities.

    Handles three entity types:
    - ``requirement``: linked Open Items via RequirementOpenItemLink
    - ``backlog_item``: linked Interfaces
    - ``interface``: linked ConnectivityTests and SwitchPlans

    Keeping this in the service layer centralises ORM access and allows
    blueprint helpers to stay query-free.

    Args:
        entity_type: One of ``requirement``, ``backlog_item``, ``interface``.
        entity_id: PK of the entity instance.

    Returns:
        Dict whose keys depend on entity_type (e.g. ``open_items``, ``interfaces``).
    """
    from app.models import db

    lateral: dict = {}

    if entity_type == "requirement":
        from app.models.requirement import Requirement

        req = db.session.get(Requirement, entity_id)
        if req:
            try:
                from app.models.explore import ExploreOpenItem, RequirementOpenItemLink

                links = RequirementOpenItemLink.query.filter_by(
                    requirement_id=str(entity_id),
                ).all()
                lateral["open_items"] = []
                for lnk in links:
                    oi = db.session.get(ExploreOpenItem, lnk.open_item_id)
                    if oi:
                        lateral["open_items"].append({
                            "id": oi.id,
                            "code": oi.code,
                            "title": oi.title,
                            "status": oi.status,
                        })
            except Exception:
                logger.warning(
                    "Could not load open-item links for requirement_id=%s", entity_id
                )

    elif entity_type == "backlog_item":
        from app.models.integration import Interface

        interfaces = Interface.query.filter_by(backlog_item_id=entity_id).all()
        lateral["interfaces"] = [
            {
                "id": i.id,
                "code": i.code,
                "name": i.name,
                "direction": i.direction,
                "status": i.status,
            }
            for i in interfaces
        ]

    elif entity_type == "interface":
        from app.models.integration import ConnectivityTest, SwitchPlan

        lateral["connectivity_tests"] = [
            {
                "id": ct.id,
                "environment": ct.environment,
                "result": ct.result,
            }
            for ct in ConnectivityTest.query.filter_by(interface_id=entity_id).all()
        ]
        lateral["switch_plans"] = [
            {
                "id": sp.id,
                "action": sp.action,
                "status": sp.status,
                "sequence": sp.sequence,
            }
            for sp in SwitchPlan.query.filter_by(interface_id=entity_id).all()
        ]

    return lateral


# ══════════════════════════════════════════════════════════════════════════════
# S2-01 (F-01) — ConfigItem → TestCase Traceability
#
# Audit A2 compliance: tenant_id is explicitly passed and applied to the
# initial ConfigItem lookup, preventing cross-tenant data exposure.
# Audit A3: no SQLAlchemy relationship overlaps warnings — we use direct
# FK queries via TestCase.config_item_id rather than a viewonly relationship.
# ══════════════════════════════════════════════════════════════════════════════


def trace_config_item(config_item_id: int, project_id: int, tenant_id: int | None) -> dict:
    """Build the downstream traceability chain for a single ConfigItem.

    Chain: ConfigItem → TestCase → last TestExecution + open Defects.

    Tenant isolation is enforced at the ConfigItem lookup: if the item
    does not belong to both project_id AND tenant_id a ValueError is raised,
    which the blueprint maps to 404 (preventing existence disclosure).

    Args:
        config_item_id: ConfigItem.id
        project_id: Owning program / project for scope enforcement.
        tenant_id: Row-level tenant isolation.

    Returns:
        {
          "config_item": {...},
          "test_cases": [
            {"id", "title", "status", "last_execution": {...} | null,
             "open_defects": [...]}
          ],
          "coverage_summary": {"total_test_cases", "passed", "failed", "not_run"}
        }

    Raises:
        ValueError: If ConfigItem not found in the given project/tenant.
    """
    ci = ConfigItem.query.filter_by(
        id=config_item_id,
        program_id=project_id,
        tenant_id=tenant_id,
    ).first()
    if not ci:
        raise ValueError(
            f"ConfigItem {config_item_id} not found in project {project_id}"
        )

    test_cases = TestCase.query.filter_by(config_item_id=config_item_id).all()

    tc_results = []
    for tc in test_cases:
        last_exec = (
            TestExecution.query.filter_by(test_case_id=tc.id)
            .order_by(TestExecution.created_at.desc())
            .first()
        )
        open_defects = Defect.query.filter(
            Defect.test_case_id == tc.id,
            Defect.status.notin_(["closed", "resolved", "cancelled"]),
        ).all()
        tc_results.append({
            "id": tc.id,
            "code": getattr(tc, "code", ""),
            "title": tc.title,
            "status": tc.status,
            "last_execution": {
                "id": last_exec.id,
                "result": last_exec.result,
                "executed_at": (
                    last_exec.created_at.isoformat() if last_exec.created_at else None
                ),
            } if last_exec else None,
            "open_defects": [
                {
                    "id": d.id,
                    "title": d.title,
                    "severity": getattr(d, "severity", None),
                    "status": d.status,
                }
                for d in open_defects
            ],
        })

    total = len(tc_results)
    passed = sum(
        1 for t in tc_results
        if t["last_execution"] and t["last_execution"]["result"] == "passed"
    )
    failed = sum(
        1 for t in tc_results
        if t["last_execution"] and t["last_execution"]["result"] == "failed"
    )

    return {
        "config_item": ci.to_dict(),
        "test_cases": tc_results,
        "coverage_summary": {
            "total_test_cases": total,
            "passed": passed,
            "failed": failed,
            "not_run": total - passed - failed,
        },
    }


def get_config_items_without_tests(project_id: int, tenant_id: int | None) -> list[dict]:
    """Return ConfigItems with no linked TestCase rows — coverage gap list.

    Uses a NOT IN subquery rather than a loop to avoid N+1 queries.

    Args:
        project_id: Owning project for scope.
        tenant_id: Row-level isolation.

    Returns:
        [{"id", "code", "title", "module", "config_status"}]
    """
    from sqlalchemy import select

    tested_ids_sub = select(TestCase.config_item_id).where(
        TestCase.config_item_id.isnot(None)
    )
    untested = ConfigItem.query.filter_by(
        program_id=project_id,
        tenant_id=tenant_id,
    ).filter(~ConfigItem.id.in_(tested_ids_sub)).all()

    return [
        {
            "id": ci.id,
            "code": ci.code,
            "title": ci.title,
            "module": ci.module,
            "config_status": ci.status,
        }
        for ci in untested
    ]


def get_config_coverage_summary(project_id: int, tenant_id: int | None) -> dict:
    """Return config-item test coverage summary broken down by SAP module.

    Two queries total: one for all config items (tenant-scoped), one for the
    set of config_item IDs that have at least one TestCase.

    Args:
        project_id: Project scope.
        tenant_id: Tenant isolation.

    Returns:
        {
          "total_config_items", "with_tests", "without_tests",
          "coverage_pct",
          "by_module": {"FI": {"total", "covered", "pct"}, ...}
        }
    """
    from sqlalchemy import select

    all_ci = ConfigItem.query.filter_by(
        program_id=project_id, tenant_id=tenant_id
    ).all()
    total = len(all_ci)

    tested_ids: set[int] = {
        row[0]
        for row in db.session.execute(
            select(TestCase.config_item_id).where(
                TestCase.config_item_id.isnot(None)
            )
        ).fetchall()
    }

    with_tests = sum(1 for ci in all_ci if ci.id in tested_ids)
    without_tests = total - with_tests
    coverage_pct = round(with_tests / total * 100, 1) if total else 0.0

    by_module: dict[str, dict] = {}
    for ci in all_ci:
        mod = (ci.module or "unknown").upper()
        if mod not in by_module:
            by_module[mod] = {"total": 0, "covered": 0}
        by_module[mod]["total"] += 1
        if ci.id in tested_ids:
            by_module[mod]["covered"] += 1

    for mod_data in by_module.values():
        t = mod_data["total"]
        mod_data["pct"] = round(mod_data["covered"] / t * 100, 1) if t else 0.0

    return {
        "total_config_items": total,
        "with_tests": with_tests,
        "without_tests": without_tests,
        "coverage_pct": coverage_pct,
        "by_module": by_module,
    }


# ══════════════════════════════════════════════════════════════════════════════
# S2-02 (F-02) — Upstream Defect Trace
#
# Audit A1: Broken chain handled gracefully — each hop is nullable; missing
#   links produce null nodes instead of raising 500.
# Audit A2: N+1 warning documented — designed for single-defect use.
# Audit A3: B-01 canonical — works with ExploreRequirement only.
# ══════════════════════════════════════════════════════════════════════════════


def trace_upstream_from_defect(
    defect_id: int,
    project_id: int,
    tenant_id: int | None,
) -> dict:
    """Traverse the full upstream traceability chain starting from a Defect.

    Chain (upstream direction):
        Defect → TestExecution → TestCase
               → [BacklogItem | ConfigItem | ExploreRequirement]
               → ExploreRequirement → ProcessLevel (L4 → L3 → L2 → L1)

    Broken-chain contract: if any link is missing (orphaned FK, NULL), the
    corresponding node is returned as null and traversal continues where
    possible. Callers receive a partial trace rather than a 500 error.

    N+1 warning: this function executes multiple single-row lookups. It is
    designed for single-defect detail pages. For bulk analysis, build a
    dedicated batch query instead of calling this in a loop.

    Args:
        defect_id: Defect.id
        project_id: For tenant scope enforcement on the Defect entry point.
        tenant_id: Row-level isolation — same semantics as other trace functions.

    Returns:
        Full upstream trace dict (see FDD-F02 §4.1 for shape).

    Raises:
        ValueError: Defect not found in project/tenant scope.
    """
    from app.models.explore import ExploreRequirement, ProcessLevel

    # 1. Defect — entry point, tenant-scoped
    defect = Defect.query.filter_by(
        id=defect_id, program_id=project_id, tenant_id=tenant_id
    ).first()
    if not defect:
        raise ValueError(f"Defect {defect_id} not found in project {project_id}")

    result: dict = {
        "defect": {
            "id": defect.id,
            "title": defect.title,
            "severity": getattr(defect, "severity", None),
            "status": defect.status,
        },
        "test_execution": None,
        "test_case": None,
        "linked_artifacts": [],
        "explore_requirement": None,
        "process_chain": [],
        "impact_summary": {
            "affected_l3_processes": [],
            "affected_sap_modules": [],
            "severity": getattr(defect, "severity", None),
            "is_critical_path": False,
        },
    }

    # 2. TestCase (direct FK) — broken chain → null node
    tc: TestCase | None = (
        db.session.get(TestCase, defect.test_case_id) if defect.test_case_id else None
    )
    if tc:
        result["test_case"] = {
            "id": tc.id,
            "code": getattr(tc, "code", ""),
            "title": tc.title,
            "type": getattr(tc, "type", None),
        }
        last_exec = (
            TestExecution.query.filter_by(test_case_id=tc.id)
            .order_by(TestExecution.created_at.desc())
            .first()
        )
        if last_exec:
            result["test_execution"] = {
                "id": last_exec.id,
                "result": last_exec.result,
                "executed_at": (
                    last_exec.created_at.isoformat() if last_exec.created_at else None
                ),
            }

    # 3. Linked artifacts + ExploreRequirement resolution
    explore_req_id: str | None = None

    # Priority order: defect direct link → TC direct link → via BacklogItem → via ConfigItem
    if defect.explore_requirement_id:
        explore_req_id = str(defect.explore_requirement_id)

    if tc:
        if tc.explore_requirement_id and not explore_req_id:
            explore_req_id = str(tc.explore_requirement_id)

        if tc.backlog_item_id:
            bi = db.session.get(BacklogItem, tc.backlog_item_id)
            if bi:
                result["linked_artifacts"].append({
                    "type": "backlog_item",
                    "id": bi.id,
                    "title": bi.title,
                    "wricef_type": getattr(bi, "wricef_type", None),
                })
                if bi.explore_requirement_id and not explore_req_id:
                    explore_req_id = str(bi.explore_requirement_id)

        if tc.config_item_id:
            ci = db.session.get(ConfigItem, tc.config_item_id)
            if ci:
                result["linked_artifacts"].append({
                    "type": "config_item",
                    "id": ci.id,
                    "title": ci.title,
                    "wricef_type": None,
                })
                if ci.explore_requirement_id and not explore_req_id:
                    explore_req_id = str(ci.explore_requirement_id)

    # 4. ExploreRequirement — may be null if chain is broken
    if explore_req_id:
        req: ExploreRequirement | None = db.session.get(ExploreRequirement, explore_req_id)
        if req:
            result["explore_requirement"] = {
                "id": req.id,
                "title": req.title,
                "classification": getattr(req, "fit_status", None),
                "status": req.status,
            }
            result["linked_artifacts"].append({
                "type": "explore_requirement",
                "id": req.id,
                "title": req.title,
                "wricef_type": None,
            })

            # 5. Walk ProcessLevel hierarchy upward (L4 → L3 → L2 → L1)
            pl_id = req.process_level_id
            if pl_id:
                chain: list[dict] = []
                visited: set[int] = set()
                current_pl: ProcessLevel | None = db.session.get(ProcessLevel, pl_id)
                while current_pl and current_pl.id not in visited:
                    visited.add(current_pl.id)
                    chain.append({
                        "level": current_pl.level,
                        "id": current_pl.id,
                        "code": current_pl.code,
                        "name": current_pl.name,
                        "fit_decision": getattr(current_pl, "fit_status", None),
                    })
                    current_pl = (
                        db.session.get(ProcessLevel, current_pl.parent_id)
                        if current_pl.parent_id
                        else None
                    )

                # Normalise to ascending level (L1 first)
                result["process_chain"] = sorted(chain, key=lambda x: x["level"])

                l3_nodes = [c for c in result["process_chain"] if c["level"] == 3]
                l4_nodes = [c for c in result["process_chain"] if c["level"] == 4]
                result["impact_summary"]["affected_l3_processes"] = [
                    f"{c['code']} {c['name']}" for c in l3_nodes
                ]
                result["impact_summary"]["is_critical_path"] = any(
                    c.get("fit_decision") == "gap" for c in l4_nodes
                )

            if req.sap_module:
                result["impact_summary"]["affected_sap_modules"] = [req.sap_module]

    return result


def trace_defects_by_process(
    project_id: int,
    tenant_id: int | None,
    process_level_id: int,
) -> list[dict]:
    """Return all defects linked (upstream) to a given ProcessLevel.

    Traversal: ProcessLevel → child L4 ProcessLevels → ExploreRequirements
               → TestCases → Defects.

    Includes the node itself plus its direct children so that querying an
    L3 node returns defects from all of its L4 children.

    Args:
        project_id: Tenant scope for the Defect query.
        tenant_id: Row-level isolation.
        process_level_id: ProcessLevel.id to start from.

    Returns:
        [{"defect_id", "title", "severity", "status", "test_case_title"}]
    """
    from sqlalchemy import select
    from app.models.explore import ExploreRequirement, ProcessLevel

    # Direct children of this level (covers both L3→L4 and querying an L4)
    child_ids: list[int] = [
        row[0]
        for row in db.session.execute(
            select(ProcessLevel.id).where(ProcessLevel.parent_id == process_level_id)
        ).fetchall()
    ]
    all_level_ids = [process_level_id, *child_ids]

    # ExploreRequirements attached to these levels
    req_ids: list[str] = [
        row[0]
        for row in db.session.execute(
            select(ExploreRequirement.id).where(
                ExploreRequirement.process_level_id.in_(all_level_ids)
            )
        ).fetchall()
    ]
    if not req_ids:
        return []

    # TestCases linked to those requirements
    tc_ids: list[int] = [
        row[0]
        for row in db.session.execute(
            select(TestCase.id).where(
                TestCase.explore_requirement_id.in_(req_ids)
            )
        ).fetchall()
    ]
    if not tc_ids:
        return []

    defects = Defect.query.filter(
        Defect.test_case_id.in_(tc_ids),
        Defect.program_id == project_id,
        Defect.tenant_id == tenant_id,
    ).all()

    results = []
    for d in defects:
        tc = db.session.get(TestCase, d.test_case_id)
        results.append({
            "defect_id": d.id,
            "title": d.title,
            "severity": getattr(d, "severity", None),
            "status": d.status,
            "test_case_title": tc.title if tc else None,
        })
    return results
