from datetime import date, datetime, timezone

from app.models import db
from app.models.program import Program, Phase
from app.models.explore import (
    ExploreWorkshop as Workshop,
    ExploreRequirement as Requirement,
    ExploreOpenItem as OpenItem,
)
from app.models.testing import TestCase, TestPlan, TestCycle, TestExecution, Defect
from app.models.backlog import BacklogItem
from app.models.raid import Risk, Action, Issue
from app.models.integration import Interface


def compute_program_health(program_id: int) -> dict:
    """
    Aggregate all module stats into a single program health snapshot.
    Returns RAG status per area + overall program RAG.
    """
    pid = program_id

    # ── 1. Explore Phase Health ────────────────────────────────────────
    ws_total = Workshop.query.filter_by(project_id=pid).count()
    ws_completed = Workshop.query.filter_by(project_id=pid, status="completed").count()
    ws_pct = round(ws_completed / ws_total * 100) if ws_total else 0

    req_total = Requirement.query.filter_by(project_id=pid).count()
    req_approved = Requirement.query.filter_by(project_id=pid, status="approved").count()
    req_pct = round(req_approved / req_total * 100) if req_total else 0

    oi_total = OpenItem.query.filter_by(project_id=pid).count()
    oi_open = OpenItem.query.filter_by(project_id=pid).filter(
        OpenItem.status.in_(["open", "in_progress"])
    ).count()
    oi_overdue = OpenItem.query.filter_by(project_id=pid).filter(
        OpenItem.status.in_(["open", "in_progress"]),
        OpenItem.due_date < date.today(),
    ).count()

    explore_rag = _rag(ws_pct, thresholds=(70, 40))

    # ── 2. Delivery — Backlog Health ──────────────────────────────────
    bl_total = BacklogItem.query.filter_by(program_id=pid).count()
    bl_done = BacklogItem.query.filter_by(program_id=pid).filter(
        BacklogItem.status.in_(["done", "deployed"])
    ).count()
    bl_pct = round(bl_done / bl_total * 100) if bl_total else 0

    backlog_rag = _rag(bl_pct, thresholds=(60, 30))

    # ── 3. Testing Health ─────────────────────────────────────────────
    tc_total = TestCase.query.filter_by(program_id=pid).count()

    plan_ids = [p.id for p in TestPlan.query.filter_by(program_id=pid).all()]
    cycle_ids = [
        c.id
        for c in TestCycle.query.filter(TestCycle.plan_id.in_(plan_ids)).all()
    ] if plan_ids else []

    exec_total = (
        TestExecution.query.filter(TestExecution.cycle_id.in_(cycle_ids)).count()
        if cycle_ids
        else 0
    )
    exec_pass = (
        TestExecution.query.filter(
            TestExecution.cycle_id.in_(cycle_ids),
            TestExecution.result == "pass",
        ).count()
        if cycle_ids
        else 0
    )
    exec_fail = (
        TestExecution.query.filter(
            TestExecution.cycle_id.in_(cycle_ids),
            TestExecution.result == "fail",
        ).count()
        if cycle_ids
        else 0
    )

    pass_rate = (
        round(exec_pass / (exec_pass + exec_fail) * 100)
        if (exec_pass + exec_fail)
        else 0
    )

    defect_total = Defect.query.filter_by(program_id=pid).count()
    defect_open = Defect.query.filter_by(program_id=pid).filter(
        Defect.status.notin_(["closed", "rejected", "resolved"])
    ).count()
    defect_s1 = Defect.query.filter_by(program_id=pid, severity="S1").filter(
        Defect.status.notin_(["closed", "rejected", "resolved"])
    ).count()

    testing_rag = _rag(pass_rate, thresholds=(80, 50))
    if defect_s1 > 0:
        testing_rag = "red"

    # ── 4. RAID Health ────────────────────────────────────────────────
    risk_open = Risk.query.filter_by(program_id=pid).filter(
        Risk.status.notin_(["closed", "expired"])
    ).count()
    risk_red = Risk.query.filter_by(program_id=pid, rag_status="red").filter(
        Risk.status.notin_(["closed", "expired"])
    ).count()
    action_overdue = Action.query.filter_by(program_id=pid).filter(
        Action.status.in_(["open", "in_progress"]),
        Action.due_date < date.today(),
    ).count()
    issue_critical = Issue.query.filter_by(program_id=pid, severity="critical").filter(
        Issue.status.notin_(["resolved", "closed"])
    ).count()

    raid_rag = "green"
    if risk_red > 0 or issue_critical > 0:
        raid_rag = "red"
    elif action_overdue > 2 or risk_open > 5:
        raid_rag = "amber"

    # ── 5. Integration Health ─────────────────────────────────────────
    if_total = Interface.query.filter_by(program_id=pid).count()
    if_live = Interface.query.filter_by(program_id=pid, status="live").count()
    if_pct = round(if_live / if_total * 100) if if_total else 0

    integration_rag = _rag(if_pct, thresholds=(70, 30))

    # ── 6. Overall RAG ───────────────────────────────────────────────
    area_rags = [explore_rag, backlog_rag, testing_rag, raid_rag, integration_rag]
    if "red" in area_rags:
        overall_rag = "red"
    elif area_rags.count("amber") >= 2:
        overall_rag = "red"
    elif "amber" in area_rags:
        overall_rag = "amber"
    else:
        overall_rag = "green"

    # ── 7. Phase/Timeline Info ────────────────────────────────────────
    program = db.session.get(Program, pid)
    phases = Phase.query.filter_by(program_id=pid).order_by(Phase.order).all()
    current_phase = next((p for p in phases if p.status == "active"), None)

    days_to_golive = None
    if program and program.go_live_date:
        days_to_golive = (program.go_live_date - date.today()).days

    return {
        "program_id": pid,
        "program_name": program.name if program else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_rag": overall_rag,
        "days_to_go_live": days_to_golive,
        "current_phase": current_phase.name if current_phase else None,
        "areas": {
            "explore": {
                "rag": explore_rag,
                "workshops": {"total": ws_total, "completed": ws_completed, "pct": ws_pct},
                "requirements": {"total": req_total, "approved": req_approved, "pct": req_pct},
                "open_items": {"total": oi_total, "open": oi_open, "overdue": oi_overdue},
            },
            "backlog": {
                "rag": backlog_rag,
                "items": {"total": bl_total, "done": bl_done, "pct": bl_pct},
            },
            "testing": {
                "rag": testing_rag,
                "test_cases": tc_total,
                "executions": exec_total,
                "pass_rate": pass_rate,
                "defects": {"total": defect_total, "open": defect_open, "s1_open": defect_s1},
            },
            "raid": {
                "rag": raid_rag,
                "risks_open": risk_open,
                "risks_red": risk_red,
                "actions_overdue": action_overdue,
                "issues_critical": issue_critical,
            },
            "integration": {
                "rag": integration_rag,
                "interfaces": {"total": if_total, "live": if_live, "pct": if_pct},
            },
        },
        "phases": [
            {
                "name": p.name,
                "status": p.status,
                "completion_pct": p.completion_pct,
                "planned_start": p.planned_start.isoformat() if p.planned_start else None,
                "planned_end": p.planned_end.isoformat() if p.planned_end else None,
            }
            for p in phases
        ],
    }


def _rag(pct: int, thresholds: tuple = (70, 40)) -> str:
    """Convert a percentage to RAG status. thresholds = (green_min, amber_min)."""
    if pct >= thresholds[0]:
        return "green"
    if pct >= thresholds[1]:
        return "amber"
    return "red"
