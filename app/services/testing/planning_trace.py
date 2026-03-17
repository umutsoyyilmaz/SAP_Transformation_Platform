"""Shared traceability helpers for test planning services."""

import logging

from sqlalchemy import or_

from app.models import db
from app.models.explore.requirement import ExploreRequirement
from app.models.testing import TestCase

logger = logging.getLogger(__name__)


def canonical_explore_requirements():
    """Return canonical explore requirements for planning/test traceability."""
    return ExploreRequirement.query.filter(
        or_(
            ExploreRequirement.trigger_reason.is_(None),
            ExploreRequirement.trigger_reason != "standard_observation",
        ),
    )


def apply_plan_scope(query, model, plan):
    """Apply program/project filters for a plan-scoped read query."""
    if hasattr(model, "program_id"):
        query = query.filter(model.program_id == plan.program_id)
    if plan.project_id is not None and hasattr(model, "project_id"):
        query = query.filter(model.project_id == plan.project_id)
    return query


def canonical_explore_requirements_for_plan(plan):
    """Return canonical explore requirements limited to the plan scope."""
    return apply_plan_scope(canonical_explore_requirements(), ExploreRequirement, plan)


def scoped_test_case_query(plan):
    """Return test cases limited to the plan scope."""
    return apply_plan_scope(TestCase.query, TestCase, plan)


def trace_scope_to_test_cases(scope, plan):
    """Trace a single PlanScope item to its linked TestCases."""
    results = []
    ref_id = scope.scope_ref_id

    if scope.scope_type == "requirement":
        results.extend(_trace_from_requirement(ref_id, scope.scope_label, plan))
    elif scope.scope_type == "l3_process":
        results.extend(_trace_from_l3_process(ref_id, scope.scope_label, plan))
    elif scope.scope_type == "scenario":
        results.extend(_trace_from_scenario(ref_id, scope.scope_label, plan))

    return results


def _trace_from_requirement(ref_id, label, plan):
    """Requirement -> BacklogItem/ConfigItem -> TestCase."""
    results = []

    from app.models.backlog import BacklogItem, ConfigItem

    ereq = canonical_explore_requirements_for_plan(plan).filter_by(id=str(ref_id)).first()
    if ereq and ereq.effective_trigger_reason != "standard_observation":
        for tc in scoped_test_case_query(plan).filter_by(explore_requirement_id=ereq.id).all():
            results.append(_tc_dict(tc, f"Requirement {label} -> TC"))

        for backlog_item in apply_plan_scope(
            BacklogItem.query.filter_by(explore_requirement_id=ereq.id),
            BacklogItem,
            plan,
        ).all():
            for tc in scoped_test_case_query(plan).filter_by(backlog_item_id=backlog_item.id).all():
                results.append(_tc_dict(tc, f"Req {label} -> {backlog_item.code or 'BI'} -> TC"))

        for config_item in apply_plan_scope(
            ConfigItem.query.filter_by(explore_requirement_id=ereq.id),
            ConfigItem,
            plan,
        ).all():
            for tc in scoped_test_case_query(plan).filter_by(config_item_id=config_item.id).all():
                results.append(_tc_dict(tc, f"Req {label} -> {config_item.code or 'CI'} -> TC"))
        return results

    try:
        req_id = int(ref_id)
    except (ValueError, TypeError):
        return results

    from app.models.requirement import Requirement

    req = db.session.get(Requirement, req_id)
    if not req:
        return results

    ereq = canonical_explore_requirements_for_plan(plan).filter_by(legacy_requirement_id=req_id).first()
    if not ereq:
        return results

    for tc in scoped_test_case_query(plan).filter_by(explore_requirement_id=ereq.id).all():
        results.append(_tc_dict(tc, f"Requirement {label} -> TC"))

    for backlog_item in apply_plan_scope(
        BacklogItem.query.filter_by(explore_requirement_id=ereq.id),
        BacklogItem,
        plan,
    ).all():
        for tc in scoped_test_case_query(plan).filter_by(backlog_item_id=backlog_item.id).all():
            results.append(_tc_dict(tc, f"Req {label} -> {backlog_item.code or 'BI'} -> TC"))

    for config_item in apply_plan_scope(
        ConfigItem.query.filter_by(explore_requirement_id=ereq.id),
        ConfigItem,
        plan,
    ).all():
        for tc in scoped_test_case_query(plan).filter_by(config_item_id=config_item.id).all():
            results.append(_tc_dict(tc, f"Req {label} -> {config_item.code or 'CI'} -> TC"))

    return results


def _trace_from_l3_process(ref_id, label, plan):
    """L3 Process -> Requirement chain -> TestCase."""
    results = []

    try:
        proc_id_int = int(ref_id)
        from app.models.scope import RequirementProcessMapping
        from app.models.requirement import Requirement
        from app.models.backlog import BacklogItem, ConfigItem

        mappings = RequirementProcessMapping.query.filter_by(process_id=proc_id_int).all()
        for mapping in mappings:
            req = db.session.get(Requirement, mapping.requirement_id)
            if not req:
                continue
            ereq = canonical_explore_requirements_for_plan(plan).filter_by(legacy_requirement_id=req.id).first()
            if not ereq:
                continue
            for backlog_item in apply_plan_scope(
                BacklogItem.query.filter_by(explore_requirement_id=ereq.id),
                BacklogItem,
                plan,
            ).all():
                for tc in scoped_test_case_query(plan).filter_by(backlog_item_id=backlog_item.id).all():
                    results.append(_tc_dict(tc, f"L3 {label} -> Req -> {backlog_item.code or 'BI'} -> TC"))
            for config_item in apply_plan_scope(
                ConfigItem.query.filter_by(explore_requirement_id=ereq.id),
                ConfigItem,
                plan,
            ).all():
                for tc in scoped_test_case_query(plan).filter_by(config_item_id=config_item.id).all():
                    results.append(_tc_dict(tc, f"L3 {label} -> Req -> {config_item.code or 'CI'} -> TC"))
            for tc in scoped_test_case_query(plan).filter_by(explore_requirement_id=ereq.id).all():
                results.append(_tc_dict(tc, f"L3 {label} -> Req -> TC"))
    except (ValueError, TypeError):
        logger.debug("Non-integer ref_id for L3 process scope: %s", ref_id)

    try:
        from app.models.backlog import BacklogItem, ConfigItem

        explore_reqs = canonical_explore_requirements_for_plan(plan).filter_by(scope_item_id=ref_id).all()
        for ereq in explore_reqs:
            for backlog_item in apply_plan_scope(
                BacklogItem.query.filter_by(explore_requirement_id=ereq.id),
                BacklogItem,
                plan,
            ).all():
                for tc in scoped_test_case_query(plan).filter_by(backlog_item_id=backlog_item.id).all():
                    results.append(_tc_dict(tc, f"L3 {label} -> {ereq.code} -> {backlog_item.code or 'BI'} -> TC"))
            for config_item in apply_plan_scope(
                ConfigItem.query.filter_by(explore_requirement_id=ereq.id),
                ConfigItem,
                plan,
            ).all():
                for tc in scoped_test_case_query(plan).filter_by(config_item_id=config_item.id).all():
                    results.append(_tc_dict(tc, f"L3 {label} -> {ereq.code} -> {config_item.code or 'CI'} -> TC"))
            for tc in scoped_test_case_query(plan).filter_by(explore_requirement_id=ereq.id).all():
                results.append(_tc_dict(tc, f"L3 {label} -> {ereq.code} -> TC"))
    except Exception:
        logger.debug("Explore path not available for L3 scope %s", ref_id)

    return results


def _trace_from_scenario(ref_id, label, plan):
    """Scenario -> Workshop -> Requirement chain -> TestCase."""
    results = []

    try:
        scen_id_int = int(ref_id)
        from app.models.scenario import Scenario, Workshop
        from app.models.requirement import Requirement
        from app.models.backlog import BacklogItem, ConfigItem

        scenario = db.session.get(Scenario, scen_id_int)
        if scenario:
            workshops = Workshop.query.filter_by(scenario_id=scen_id_int).all()
            for workshop in workshops:
                requirements = Requirement.query.filter_by(workshop_id=workshop.id).all()
                for req in requirements:
                    ereq = canonical_explore_requirements_for_plan(plan).filter_by(legacy_requirement_id=req.id).first()
                    if not ereq:
                        continue
                    for backlog_item in apply_plan_scope(
                        BacklogItem.query.filter_by(explore_requirement_id=ereq.id),
                        BacklogItem,
                        plan,
                    ).all():
                        for tc in scoped_test_case_query(plan).filter_by(backlog_item_id=backlog_item.id).all():
                            results.append(_tc_dict(tc, f"Scenario {label} -> WS -> Req -> TC"))
                    for config_item in apply_plan_scope(
                        ConfigItem.query.filter_by(explore_requirement_id=ereq.id),
                        ConfigItem,
                        plan,
                    ).all():
                        for tc in scoped_test_case_query(plan).filter_by(config_item_id=config_item.id).all():
                            results.append(_tc_dict(tc, f"Scenario {label} -> WS -> Req -> TC"))
                    for tc in scoped_test_case_query(plan).filter_by(explore_requirement_id=ereq.id).all():
                        results.append(_tc_dict(tc, f"Scenario {label} -> WS -> Req -> TC"))
    except (ValueError, TypeError):
        logger.debug("Non-integer ref_id for scenario scope: %s", ref_id)

    return results


def _tc_dict(tc, reason):
    """Build a suggestion dict from a TestCase model."""
    return {
        "test_case_id": tc.id,
        "code": tc.code,
        "title": tc.title,
        "test_layer": tc.test_layer,
        "priority": tc.priority,
        "reason": reason,
    }
