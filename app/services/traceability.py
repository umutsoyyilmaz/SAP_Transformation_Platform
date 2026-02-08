"""
SAP Transformation Management Platform
Traceability Engine v1 — Sprint 4 scope.

Provides the ability to trace from any entity up and down the full chain:
    Scenario → Requirement → WRICEF Item / Config Item → FS → TS

The engine builds a chain dict showing upstream (parents) and downstream
(children) links for a given entity.
"""

from app.models import db
from app.models.backlog import BacklogItem, ConfigItem, FunctionalSpec, TechnicalSpec
from app.models.requirement import Requirement
from app.models.scenario import Scenario, Workshop
from app.models.scope import Process, ScopeItem, Analysis
from app.models.testing import TestCase, Defect


# Supported entity types for chain traversal
ENTITY_TYPES = {
    "scenario": Scenario,
    "workshop": Workshop,
    "process": Process,
    "scope_item": ScopeItem,
    "analysis": Analysis,
    "requirement": Requirement,
    "backlog_item": BacklogItem,
    "config_item": ConfigItem,
    "functional_spec": FunctionalSpec,
    "technical_spec": TechnicalSpec,
    "test_case": TestCase,
    "defect": Defect,
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
    elif entity_type == "scope_item":
        _trace_scope_item_upstream(entity, upstream)
        _trace_scope_item_downstream(entity, downstream)
    elif entity_type == "analysis":
        _trace_analysis_upstream(entity, upstream)
    elif entity_type == "test_case":
        _trace_test_case_upstream(entity, upstream)
        _trace_test_case_downstream(entity, downstream)
    elif entity_type == "defect":
        _trace_defect_upstream(entity, upstream)

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
    """BacklogItem → FS → TS."""
    if bi.functional_spec:
        chain.append({"type": "functional_spec", "id": bi.functional_spec.id,
                       "title": bi.functional_spec.title})
        _trace_fs_downstream(bi.functional_spec, chain)


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
    """Requirement → Scenario (via program)."""
    # Requirements link to scenarios via program_id — find scenarios in same program
    scenarios = Scenario.query.filter_by(program_id=req.program_id).all()
    for s in scenarios:
        chain.append({"type": "scenario", "id": s.id, "title": s.name})


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
    """Scenario → Requirements → BacklogItems + ConfigItems → FS → TS → TestCases → Defects."""
    requirements = Requirement.query.filter_by(program_id=scenario.program_id).all()
    for req in requirements:
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


# ── Scope chain tracing (Process / ScopeItem / Analysis) ─────────────────

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
    """Process → ScopeItems → Analyses."""
    scope_items = ScopeItem.query.filter_by(process_id=process.id).all()
    for si in scope_items:
        chain.append({"type": "scope_item", "id": si.id, "title": si.name,
                       "code": si.code, "status": si.status})
        _trace_scope_item_downstream(si, chain)
    children = Process.query.filter_by(parent_id=process.id).all()
    for child in children:
        chain.append({"type": "process", "id": child.id, "title": child.name,
                       "level": child.level})
        _trace_process_downstream(child, chain)


def _trace_scope_item_upstream(scope_item, chain):
    """ScopeItem → Process → Scenario."""
    process = db.session.get(Process, scope_item.process_id)
    if process:
        chain.append({"type": "process", "id": process.id, "title": process.name,
                       "level": process.level})
        _trace_process_upstream(process, chain)


def _trace_scope_item_downstream(scope_item, chain):
    """ScopeItem → Analyses."""
    analyses = Analysis.query.filter_by(scope_item_id=scope_item.id).all()
    for a in analyses:
        chain.append({"type": "analysis", "id": a.id, "title": a.name,
                       "status": a.status, "fit_gap_result": a.fit_gap_result})


def _trace_analysis_upstream(analysis, chain):
    """Analysis → ScopeItem → Process → Scenario."""
    si = db.session.get(ScopeItem, analysis.scope_item_id)
    if si:
        chain.append({"type": "scope_item", "id": si.id, "title": si.name,
                       "code": si.code})
        _trace_scope_item_upstream(si, chain)
