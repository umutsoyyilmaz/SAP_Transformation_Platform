"""
Home Dashboard Service — aggregates KPIs across the active program.

Used by home_bp for the landing dashboard (/api/v1/dashboard/*).
All queries are read-only; no commits.
"""

import logging

from app.models import db
from app.models.audit import AuditLog
from app.models.backlog import BacklogItem
from app.models.explore.requirement import ExploreRequirement
from app.models.program import Program
from app.models.raid import Risk
from app.models.testing import Defect, TestCase

logger = logging.getLogger(__name__)

_DEFECT_OPEN = {"open", "in_progress", "reopened"}
_RISK_OPEN = {"open", "in_progress"}


def _latest_program() -> Program | None:
    """Return the most recently created program, or None."""
    return Program.query.order_by(Program.id.desc()).first()


def get_home_summary() -> dict:
    """
    Return aggregate KPIs for the landing dashboard.

    Returns:
        Dict with health_score, requirements, test_coverage,
        wricef_items, test_cases, open_defects, open_risks.
    """
    prog = _latest_program()
    if not prog:
        return {
            "health_score": 0,
            "requirements": 0,
            "test_coverage": 0,
            "wricef_items": 0,
            "test_cases": 0,
            "open_defects": 0,
            "open_risks": 0,
        }

    # Aggregate across ALL programs for a platform-wide summary
    # ExploreRequirement links to workshops (no direct program_id column)
    req_count = ExploreRequirement.query.count()
    wricef_count = BacklogItem.query.count()
    tc_count = TestCase.query.count()
    open_defects = (
        Defect.query
        .filter(Defect.status.in_(_DEFECT_OPEN))
        .count()
    )
    open_risks = (
        Risk.query
        .filter(Risk.status.in_(_RISK_OPEN))
        .count()
    )

    # Simple health score: start at 80, penalise for open issues
    health = 80
    if open_defects > 5:
        health -= 15
    elif open_defects > 2:
        health -= 8
    if open_risks > 5:
        health -= 10
    elif open_risks > 2:
        health -= 5
    health = max(0, min(100, health))

    # Rough test coverage: % of requirements with at least 1 test case
    test_coverage = 0.0
    if req_count > 0 and tc_count > 0:
        test_coverage = min(100.0, round(tc_count / req_count * 100, 1))

    return {
        "health_score": health,
        "requirements": req_count,
        "test_coverage": test_coverage,
        "wricef_items": wricef_count,
        "test_cases": tc_count,
        "open_defects": open_defects,
        "open_risks": open_risks,
    }


def get_home_actions() -> list[dict]:
    """
    Return a list of actionable items that need attention.

    Returns:
        List of dicts with message, view, severity keys.
    """
    actions: list[dict] = []

    open_defects = (
        Defect.query
        .filter(Defect.status.in_(_DEFECT_OPEN))
        .count()
    )
    if open_defects:
        severity = "critical" if open_defects > 5 else "warning"
        actions.append({
            "message": f"{open_defects} açık defect bekliyor",
            "view": "defect-management",
            "severity": severity,
        })

    open_risks = (
        Risk.query
        .filter(Risk.status.in_(_RISK_OPEN))
        .count()
    )
    if open_risks:
        actions.append({
            "message": f"{open_risks} risk değerlendirme bekliyor",
            "view": "raid",
            "severity": "warning",
        })

    wricef_count = BacklogItem.query.count()
    if wricef_count:
        actions.append({
            "message": f"{wricef_count} WRICEF kalemi backlog'da",
            "view": "backlog",
            "severity": "info",
        })

    return actions


def get_home_recent_activity() -> list[dict]:
    """
    Return the 10 most recent audit log entries for the dashboard feed.

    Returns:
        List of dicts with user_name, action, object_code, created_at.
    """
    logs = (
        AuditLog.query
        .order_by(AuditLog.timestamp.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "user_name": log.actor or "Sistem",
            "action": log.action or "",
            "object_code": log.entity_type or "",
            "created_at": (
                log.timestamp.isoformat() if log.timestamp else None
            ),
        }
        for log in logs
    ]
