"""
SAP Transformation Management Platform
Traceability Engine v2 — Sprint 9 scope.

Provides the ability to trace from any entity up and down the full chain:
    Scenario → Requirement → WRICEF Item / Config Item → FS → TS
                           → Interface → ConnectivityTest / SwitchPlan

The engine builds a chain dict showing upstream (parents) and downstream
(children) links for a given entity.
"""

from app.models import db
from app.models.backlog import BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec
from app.models.integration import Interface, Wave, ConnectivityTest, SwitchPlan
from app.models.requirement import Requirement
from app.models.scenario import Scenario, Workshop
from app.models.scope import Process, Analysis
from app.models.testing import TestCase, Defect


# Supported entity types for chain traversal
ENTITY_TYPES = {
    "scenario": Scenario,
    "workshop": Workshop,
    "process": Process,
    "analysis": Analysis,
    "requirement": Requirement,
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


def get_chain(entity_type: str, entity_id: int) -> dict:
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

    Returns:
        dict with chain information, or None if entity not found.
    """
    model = ENTITY_TYPES.get(entity_type)
    if not model:
        return None

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


def get_requirement_links(requirement_id: int) -> dict:
    """
    Get all WRICEF items and Config items linked to a requirement.

    Returns:
        dict with backlog_items and config_items lists.
    """
    req = db.session.get(Requirement, requirement_id)
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
    """
    Build a program-level traceability summary showing coverage.

    Returns counts of linked vs unlinked items across the chain.
    """
    requirements = Requirement.query.filter_by(program_id=program_id).all()
    backlog_items = BacklogItem.query.filter_by(program_id=program_id).all()
    config_items = ConfigItem.query.filter_by(program_id=program_id).all()

    req_with_backlog = set()
    req_with_config = set()
    for b in backlog_items:
        if b.requirement_id:
            req_with_backlog.add(b.requirement_id)
    for c in config_items:
        if c.requirement_id:
            req_with_config.add(c.requirement_id)

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

    # Sprint 5 — Test coverage
    test_cases = TestCase.query.filter_by(program_id=program_id).all()
    defects = Defect.query.filter_by(program_id=program_id).all()
    req_ids_with_tests = set(tc.requirement_id for tc in test_cases if tc.requirement_id)

    return {
        "requirements": {
            "total": len(requirements),
            "linked_to_backlog_or_config": len(linked_req_ids),
            "unlinked": len(requirements) - len(linked_req_ids),
            "coverage_pct": round(len(linked_req_ids) / len(requirements) * 100) if requirements else 0,
        },
        "backlog_items": {
            "total": len(backlog_items),
            "with_requirement": sum(1 for b in backlog_items if b.requirement_id),
            "with_functional_spec": backlog_with_fs,
        },
        "config_items": {
            "total": len(config_items),
            "with_requirement": sum(1 for c in config_items if c.requirement_id),
            "with_functional_spec": config_with_fs,
        },
        "functional_specs": {
            "total": len(fs_list),
            "with_technical_spec": fs_with_ts,
        },
        "test_cases": {
            "total": len(test_cases),
            "with_requirement": sum(1 for tc in test_cases if tc.requirement_id),
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
    """Requirement → BacklogItems + ConfigItems → FS → TS + TestCases → Defects."""
    backlog_items = BacklogItem.query.filter_by(requirement_id=req.id).all()
    for bi in backlog_items:
        chain.append({"type": "backlog_item", "id": bi.id, "title": bi.title,
                       "wricef_type": bi.wricef_type})
        _trace_backlog_downstream(bi, chain)

    config_items = ConfigItem.query.filter_by(requirement_id=req.id).all()
    for ci in config_items:
        chain.append({"type": "config_item", "id": ci.id, "title": ci.title})
        _trace_config_downstream(ci, chain)

    # Sprint 5 extension: Requirement → Test Cases → Defects
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
    """TestCase → Requirement → Scenario."""
    if tc.requirement_id:
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
