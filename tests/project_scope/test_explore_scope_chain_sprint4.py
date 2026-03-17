import uuid

from app import create_app
from app.models import db
from app.models.auth import Tenant
from app.models.backlog import BacklogItem
from app.models.explore.process import ProcessLevel, ProcessStep
from app.models.explore.requirement import ExploreOpenItem, ExploreRequirement, RequirementOpenItemLink
from app.models.explore.workshop import ExploreWorkshop
from app.models.program import Program
from app.models.testing import Defect, TestCase
from app.services.fit_propagation import calculate_system_suggested_fit
from app.services.scope_resolution import resolve_l3_for_tc
from app.services.signoff import check_signoff_readiness
from app.services.traceability import trace_explore_requirement


def _uid():
    return str(uuid.uuid4())


def _ensure_tenant():
    tenant = Tenant.query.filter_by(slug="test-default").first()
    if not tenant:
        tenant = Tenant(name="Test Default", slug="test-default")
        db.session.add(tenant)
        db.session.flush()
    return tenant


def _make_program(name: str) -> Program:
    tenant = _ensure_tenant()
    program = Program(name=name, status="active", methodology="agile", tenant_id=tenant.id)
    db.session.add(program)
    db.session.flush()
    return program


def _make_hierarchy(project_id: int, suffix: str):
    l1 = ProcessLevel(
        id=_uid(),
        project_id=project_id,
        level=1,
        code=f"L1-{suffix}",
        name=f"L1 {suffix}",
        sort_order=1,
        scope_status="in_scope",
    )
    l2 = ProcessLevel(
        id=_uid(),
        project_id=project_id,
        parent_id=l1.id,
        level=2,
        code=f"L2-{suffix}",
        name=f"L2 {suffix}",
        sort_order=1,
        scope_status="in_scope",
    )
    l3 = ProcessLevel(
        id=_uid(),
        project_id=project_id,
        parent_id=l2.id,
        level=3,
        code=f"L3-{suffix}",
        name=f"L3 {suffix}",
        sort_order=1,
        scope_status="in_scope",
        scope_item_code=f"S{suffix[:3].upper()}",
    )
    l4 = ProcessLevel(
        id=_uid(),
        project_id=project_id,
        parent_id=l3.id,
        level=4,
        code=f"L4-{suffix}",
        name=f"L4 {suffix}",
        sort_order=1,
        scope_status="in_scope",
    )
    db.session.add_all([l1, l2, l3, l4])
    db.session.flush()
    return l3, l4


def _make_workshop(project_id: int, code: str):
    ws = ExploreWorkshop(
        id=_uid(),
        project_id=project_id,
        code=code,
        name=f"Workshop {code}",
        process_area="FI",
        status="draft",
        session_number=1,
        total_sessions=1,
    )
    db.session.add(ws)
    db.session.flush()
    return ws


def _make_requirement(project_id: int, code: str, **overrides):
    req = ExploreRequirement(
        id=overrides.pop("id", _uid()),
        project_id=project_id,
        code=code,
        title=overrides.pop("title", f"Requirement {code}"),
        created_by_id=overrides.pop("created_by_id", "test-user"),
        **overrides,
    )
    db.session.add(req)
    db.session.flush()
    return req


def _make_open_item(project_id: int, code: str, **overrides):
    oi = ExploreOpenItem(
        id=overrides.pop("id", _uid()),
        project_id=project_id,
        code=code,
        title=overrides.pop("title", f"Open Item {code}"),
        created_by_id=overrides.pop("created_by_id", "test-user"),
        **overrides,
    )
    db.session.add(oi)
    db.session.flush()
    return oi


app = create_app("testing")


def setup_module():
    with app.app_context():
        db.drop_all()
        db.create_all()


def teardown_module():
    with app.app_context():
        db.session.remove()
        db.drop_all()


def setup_function():
    with app.app_context():
        db.session.rollback()
        db.drop_all()
        db.create_all()


def test_signoff_readiness_ignores_foreign_project_blockers():
    with app.app_context():
        project_a = _make_program("Scope A")
        project_b = _make_program("Scope B")
        l3_a, l4_a = _make_hierarchy(project_a.id, "A")
        l4_a.fit_status = "fit"

        _make_open_item(
            project_b.id,
            "OI-FGN",
            process_level_id=l3_a.id,
            priority="P1",
            status="open",
        )
        _make_requirement(
            project_b.id,
            "REQ-FGN",
            scope_item_id=l3_a.id,
            status="draft",
        )
        db.session.flush()

        readiness = check_signoff_readiness(l3_a.id, project_id=project_a.id)
        assert readiness["ready"] is True
        assert readiness["stats"]["p1_open_count"] == 0
        assert readiness["stats"]["unapproved_req_count"] == 0


def test_fit_calculation_ignores_foreign_project_children():
    with app.app_context():
        project_a = _make_program("Fit A")
        project_b = _make_program("Fit B")
        l3_a, l4_a = _make_hierarchy(project_a.id, "FITA")
        l4_a.fit_status = "fit"

        foreign_l4 = ProcessLevel(
            id=_uid(),
            project_id=project_b.id,
            parent_id=l3_a.id,
            level=4,
            code="L4-FGN",
            name="Foreign L4",
            sort_order=2,
            scope_status="in_scope",
            fit_status="gap",
        )
        db.session.add(foreign_l4)
        db.session.flush()

        assert calculate_system_suggested_fit(l3_a) == "fit"


def test_scope_resolution_rejects_foreign_process_step_chain():
    with app.app_context():
        project_a = _make_program("Resolution A")
        project_b = _make_program("Resolution B")
        _l3_a, _l4_a = _make_hierarchy(project_a.id, "RESA")
        l3_b, l4_b = _make_hierarchy(project_b.id, "RESB")
        ws_b = _make_workshop(project_b.id, "WS-RES-B")
        step_b = ProcessStep(
            id=_uid(),
            workshop_id=ws_b.id,
            process_level_id=l4_b.id,
            project_id=project_b.id,
            sort_order=1,
        )
        db.session.add(step_b)
        db.session.flush()

        req_a = _make_requirement(
            project_a.id,
            "REQ-RES-A",
            scope_item_id=None,
            process_level_id=None,
            process_step_id=step_b.id,
        )
        db.session.flush()

        resolved = resolve_l3_for_tc({"explore_requirement_id": req_a.id}, project_id=project_a.id)
        assert resolved is None
        assert l3_b.id != resolved


def test_trace_explore_requirement_filters_foreign_project_descendants():
    with app.app_context():
        project_a = _make_program("Trace A")
        project_b = _make_program("Trace B")
        l3_a, l4_a = _make_hierarchy(project_a.id, "TRA")
        ws_a = _make_workshop(project_a.id, "WS-TRA-A")
        step_a = ProcessStep(
            id=_uid(),
            workshop_id=ws_a.id,
            process_level_id=l4_a.id,
            project_id=project_a.id,
            sort_order=1,
            fit_decision="fit",
        )
        db.session.add(step_a)
        db.session.flush()

        req_a = _make_requirement(
            project_a.id,
            "REQ-TRA-A",
            workshop_id=ws_a.id,
            process_step_id=step_a.id,
            scope_item_id=l3_a.id,
            process_level_id=l4_a.id,
            status="approved",
        )

        same_bi = BacklogItem(
            program_id=project_a.id,
            project_id=project_a.id,
            code="BI-A",
            title="Same Project BI",
            wricef_type="enhancement",
            explore_requirement_id=req_a.id,
        )
        foreign_bi = BacklogItem(
            program_id=project_b.id,
            project_id=project_b.id,
            code="BI-B",
            title="Foreign BI",
            wricef_type="enhancement",
            explore_requirement_id=req_a.id,
        )
        same_tc = TestCase(
            program_id=project_a.id,
            project_id=project_a.id,
            code="TC-A",
            title="Same Project TC",
            explore_requirement_id=req_a.id,
            backlog_item_id=None,
            status="ready",
        )
        foreign_tc = TestCase(
            program_id=project_b.id,
            project_id=project_b.id,
            code="TC-B",
            title="Foreign TC",
            explore_requirement_id=req_a.id,
            status="ready",
        )
        same_defect = Defect(
            program_id=project_a.id,
            project_id=project_a.id,
            code="DEF-A",
            title="Same Project Defect",
            explore_requirement_id=req_a.id,
            status="new",
        )
        foreign_defect = Defect(
            program_id=project_b.id,
            project_id=project_b.id,
            code="DEF-B",
            title="Foreign Defect",
            explore_requirement_id=req_a.id,
            status="new",
        )
        same_oi = _make_open_item(project_a.id, "OI-A", status="open")
        foreign_oi = _make_open_item(project_b.id, "OI-B", status="open")
        db.session.add_all([
            same_bi,
            foreign_bi,
            same_tc,
            foreign_tc,
            same_defect,
            foreign_defect,
            RequirementOpenItemLink(
                requirement_id=req_a.id,
                open_item_id=same_oi.id,
                project_id=project_a.id,
            ),
            RequirementOpenItemLink(
                requirement_id=req_a.id,
                open_item_id=foreign_oi.id,
                project_id=project_b.id,
            ),
        ])
        db.session.flush()

        graph = trace_explore_requirement(req_a.id)
        assert [item["code"] for item in graph["backlog_items"]] == ["BI-A"]
        assert [item["code"] for item in graph["test_cases"]] == ["TC-A"]
        assert [item["code"] for item in graph["defects"]] == ["DEF-A"]
        assert [item["code"] for item in graph["open_items"]] == ["OI-A"]
